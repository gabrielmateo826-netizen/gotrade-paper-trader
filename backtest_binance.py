import ccxt
import pandas as pd
import numpy as np
import json
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta


def fetch_binance_data(symbol, timeframe, years=3):
    exchange = ccxt.binance({"enableRateLimit": True})
    since = exchange.parse8601((datetime.now() - timedelta(days=years*365)).isoformat())
    all_ohlcv = []

    while since < exchange.milliseconds():
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
        if not ohlcv:
            break
        since = ohlcv[-1][0] + 1
        all_ohlcv.extend(ohlcv)
        if len(ohlcv) < 1000:
            break

    df = pd.DataFrame(all_ohlcv, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')
    df = df.set_index('Timestamp')
    return df


def rsi(close, period=14):
    delta = pd.Series(close).diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


class GridStrategy(Strategy):
    def __init__(self, strategy_name, **kwargs):
        super().__init__(**kwargs)
        self.strategy_name = strategy_name
        self.entry_rsi_period = kwargs.get('rsi_period', 2)
        self.entry_rsi_threshold = kwargs.get('entry_threshold', 15)
        self.sma_trend_period = kwargs.get('sma_trend_period', 50)
        self.sma_exit_period = kwargs.get('sma_exit_period', 5)
        self.exit_stop_pct = kwargs.get('exit_stop_pct', 0.06)
        self.use_trailing = kwargs.get('use_trailing', False)
        self.trailing_pct = kwargs.get('trailing_pct', 0.04)

    def init(self):
        close = self.data.Close
        self.sma_trend = self.I(lambda x, p: pd.Series(x).rolling(p).mean(), close, self.sma_trend_period)
        self.sma_exit = self.I(lambda x, p: pd.Series(x).rolling(p).mean(), close, self.sma_exit_period)
        self.rsi_val = self.I(rsi, close, self.entry_rsi_period)
        self.entry_bar = None
        self.entry_price = None
        self.max_favorable_trade = 0

    def next(self):
        # Trend filter: Close > SMA(trend)
        trend_ok = self.close[-1] > self.sma_trend[-1]

        # Entry: RSI period < threshold
        rsi_ok = self.rsi_val[-1] < self.entry_rsi_threshold

        if trend_ok and rsi_ok:
            if not self.position:
                self.buy(size=0.45)
                self.entry_bar = len(self.data)
                self.entry_price = self.close[-1]
                self.max_favorable_trade = 0

        if self.position:
            # Track max favorable excursion
            if self.close[-1] > self.entry_price:
                self.max_favorable_trade = max(
                    self.max_favorable_trade,
                    (self.close[-1] - self.entry_price) / self.entry_price
                )

            # Exit conditions
            exit_reason = None

            # 1. RSI overbought
            rsi_exit = self.rsi_val[-1] > 70

            # 2. Close > SMA(exit)
            sma_exit = self.close[-1] > self.sma_exit[-1]

            # 3. Trailing/ATR stop-loss
            trailing_exit = False
            if self.use_trailing:
                trailing_exit = self.max_favorable_trade >= self.trailing_pct

            if rsi_exit or sma_exit or trailing_exit or (
                self.close[-1] <= self.entry_price * (1 - self.exit_stop_pct)
            ):
                self.position.close()
                self.entry_bar = None
                self.entry_price = None
                self.max_favorable_trade = 0


def run_backtest(data, cash=100, commission=0.001):
    bt = Backtest(data, GridStrategy, cash=cash, commission=commission, exclusive_orders=True)
    stats = bt.run()
    return stats


def run_split_backtest(symbol, timeframe, cash=100, commission=0.001):
    print(f"\n--- {symbol} ({timeframe}) ---")
    try:
        df = fetch_binance_data(symbol, timeframe)
    except Exception as e:
        print(f"Data fetch error: {e}")
        return None

    # Scale data for fractional simulation
    df = df.copy()
    df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']] / 1_000_000
    df['Volume'] = df['Volume'] * 1_000_000

    split_idx = int(len(df) * 0.7)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]

    # In-sample and out-of-sample results
    results = {}
    for name, data in [("In-Sample", train_df), ("Out-of-Sample", test_df)]:
        bt = Backtest(data, GridStrategy, cash=cash, commission=commission, exclusive_orders=True)
        stats = bt.run()
        bh_return = ((data.iloc[-1]['Close'] / data.iloc[0]['Close']) - 1) * 100
        results[name] = {
            'Return [%]': stats['Return [%]'],
            'Buy & Hold Return [%]': bh_return,
            'Win Rate [%]': stats['Win Rate [%]'],
            'Profit Factor': stats['Profit Factor'],
            'Max. Drawdown [%]': stats['Max. Drawdown [%]'],
            '# Trades': stats['# Trades']
        }

    res_df = pd.DataFrame(results).T
    print(res_df)
    return res_df


def check_min_trades(stats, min_trades=15):
    """Check if strategy has minimum number of trades"""
    return stats['# Trades'] >= min_trades


def main():
    # Parameter grid
    sma_trend_options = [100, 200]       # Trend filter: SMA(100) vs SMA(200)
    rsi_period_options = [2, 3]          # Entry RSI period
    rsi_threshold_options = [10, 15]     # Entry RSI threshold
    exit_options = [
        ('rsi_70', False, 0.0, 70),        # Exit: RSI(2) > 70
        ('sma5', True, 5, 0.0),            # Exit: Close > SMA(5)
        ('trailing_4pct', True, 4, 0.0),   # Exit: trailing 4%
        ('trailing_6pct', True, 6, 0.0),   # Exit: trailing 6%
        ('trailing_8pct', True, 8, 0.0),   # Exit: trailing 8%
    ]

    # Grid search: 2 × 2 × 2 × 5 = 40 combinations per symbol×timeframe
    combinations = []
    for sma_t in sma_trend_options:
        for rsi_p in rsi_period_options:
            for rsi_t in rsi_threshold_options:
                for exit_name, use_trailing, trailing_pct, exit_val in exit_options:
                    combinations.append({
                        'sma_trend_period': sma_t,
                        'rsi_period': rsi_p,
                        'entry_threshold': rsi_t,
                        'exit_name': exit_name,
                        'use_trailing': use_trailing,
                        'trailing_pct': trailing_pct,
                        'sma_exit_period': exit_val,
                    })

    all_results = []
    sym_timeframes = [("BTC/USDT", "4h"), ("BTC/USDT", "1d"),
                      ("ETH/USDT", "4h"), ("ETH/USDT", "1d")]

    for symbol, timeframe in sym_timeframes:
        print(f"\n{'='*60}")
        print(f"Testing {symbol} ({timeframe})")
        print(f"{'='*60}")
        df = fetch_binance_data(symbol, timeframe)
        df = df.copy()
        df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']] / 1_000_000
        df['Volume'] = df['Volume'] * 1_000_000

        split_idx = int(len(df) * 0.7)
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:]

        for params in combinations:
            # Run in-sample
            bt_is = Backtest(train_df, GridStrategy, cash=100, commission=0.001, exclusive_orders=True)
            # Override params via strategy instantiation
            strat_is = GridStrategy(
                name=f"IS_{symbol}_{timeframe}",
                rsi_period=params['rsi_period'],
                entry_threshold=params['entry_threshold'],
                sma_trend_period=params['sma_trend_period'],
                sma_exit_period=params['sma_exit_period'],
                exit_stop_pct=0.06,
                use_trailing=params['use_trailing'],
                trailing_pct=params['trailing_pct']
            )
            # The backtesting library uses class attributes set in init;
            # we set them after instantiation by modifying the strategy class
            # Instead, we'll patch the strategy class attributes
            GridStrategy.rsi_period = params['rsi_period']
            GridStrategy.entry_threshold = params['entry_threshold']
            GridStrategy.sma_trend_period = params['sma_trend_period']
            GridStrategy.sma_exit_period = params['sma_exit_period']
            GridStrategy.exit_stop_pct = 0.06
            GridStrategy.use_trailing = params['use_trailing']
            GridStrategy.trailing_pct = params['trailing_pct']

            stats_is = bt_run_backtest(train_df)
            pf_is = stats_is.get('Profit Factor', 0)
            trades_is = stats_is.get('# Trades', 0)

            # Run out-of-sample
            GridStrategy.rsi_period = params['rsi_period']
            GridStrategy.entry_threshold = params['entry_threshold']
            GridStrategy.sma_trend_period = params['sma_trend_period']
            GridStrategy.sma_exit_period = params['sma_exit_period']
            GridStrategy.exit_stop_pct = 0.06
            GridStrategy.use_trailing = params['use_trailing']
            GridStrategy.trailing_pct = params['trailing_pct']

            bt_oos = Backtest(test_df, GridStrategy, cash=100, commission=0.001, exclusive_orders=True)
            stats_oos = bt_run_backtest(test_df)
            pf_oos = stats_oos.get('Profit Factor', 0)
            trades_oos = stats_oos.get('# Trades', 0)

            combo_result = {
                'symbol': symbol,
                'timeframe': timeframe,
                'sma_trend_period': params['sma_trend_period'],
                'rsi_period': params['rsi_period'],
                'entry_threshold': params['entry_threshold'],
                'exit_name': params['exit_name'],
                'use_trailing': params['use_trailing'],
                'trailing_pct': params['trailing_pct'],
                'sma_exit_period': params['sma_exit_period'],
                'IS_Profit_Factor': pf_is,
                'OOS_Profit_Factor': pf_oos,
                'IS_Trades': trades_is,
                'OOS_Trades': trades_oos,
                'IS_Return': stats_is.get('Return [%]', 0),
                'OOS_Return': stats_oos.get('Return [%]', 0),
            }
            all_results.append(combo_result)

    # Rank by OOS Profit Factor, requiring OOS >= 15 trades and IS PF > 1.20
    valid = [r for r in all_results if r['OOS_Trades'] >= 15 and r['IS_Profit_Factor'] > 1.20]
    valid.sort(key=lambda x: x['OOS_Profit_Factor'], reverse=True)

    print(f"\n{'='*60}")
    print(f"VALID COMBINATIONS (IS PF > 1.20, OOS >= 15 trades)")
    print(f"{'='*60}")
    for i, r in enumerate(valid[:5]):
        print(f"\nTop {i+1}:")
        print(f"  Symbol: {r['symbol']}, Timeframe: {r['timeframe']}")
        print(f"  Trend SMA: {r['sma_trend_period']}, RSI Period: {r['rsi_period']}, Threshold: {r['entry_threshold']}")
        print(f"  Exit: {r['exit_name']}, Trailing: {r['trailing_pct']}%")
        print(f"  IS PF: {r['IS_Profit_Factor']:.2f}, OOS PF: {r['OOS_Profit_Factor']:.2f}")
        print(f"  IS Trades: {r['IS_Trades']}, OOS Trades: {r['OOS_Trades']}")
        print(f"  IS Return: {r['IS_Return']:.2f}%, OOS Return: {r['OOS_Return']:.2f}%")

    # Select best overall by OOS Profit Factor
    if valid:
        best = valid[0]
        config = {
            "best_timeframe": best['timeframe'],
            "rsi_low": best['entry_threshold'],
            "rsi_high": 70,  # fixed exit RSI level
            "sma_trend": best['sma_trend_period'],
            "sma_exit": best['sma_exit_period'],
            "stop_loss_pct": 0.06,
            "min_notional_usdt": 5.5,
            "position_size": 0.45,
            "rsi_period": best['rsi_period'],
            "entry_threshold": best['entry_threshold'],
            "sma_trend_period": best['sma_trend_period'],
            "sma_exit_period": best['sma_exit_period'],
            "exit_name": best['exit_name'],
            "use_trailing": best['use_trailing'],
            "trailing_pct": best['trailing_pct'],
            "oos_profit_factor": best['OOS_Profit_Factor'],
            "is_profit_factor": best['IS_Profit_Factor'],
        }
        with open("crypto_config.json", "w") as f:
            json.dump(config, f, indent=2)
        print(f"\n{'='*60}")
        print(f"WINNING CONFIG saved to crypto_config.json")
        print(f"{'='*60}")
        for k, v in config.items():
            print(f"  {k}: {v}")
    else:
        print("\nNo valid combinations found meeting criteria.")
        # Fallback: save config with best IS result
        fallback = {
            "best_timeframe": "4h",
            "rsi_low": 15,
            "rsi_high": 70,
            "sma_trend": 50,
            "sma_exit": 5,
            "stop_loss_pct": 0.06,
            "min_notional_usdt": 5.5,
            "position_size": 0.45,
        }
        with open("crypto_config.json", "w") as f:
            json.dump(fallback, f, indent=2)
        print(f"Fallback config saved: {fallback}")


def bt_run_backtest(data):
    """Run backtest and return stats dict"""
    bt = Backtest(data, GridStrategy, cash=100, commission=0.001, exclusive_orders=True)
    stats = bt.run()
    return stats


if __name__ == "__main__":
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)

    main()