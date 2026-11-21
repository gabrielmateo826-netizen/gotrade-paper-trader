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
    sma_trend_period = 100
    rsi_period = 2
    rsi_threshold = 10
    exit_type = 'rsi'  # 'rsi', 'sma', 'trailing'
    exit_sma_period = 5
    trailing_pct = 0.04
    stop_loss_pct = 0.06

    def init(self):
        close = self.data.Close
        self.sma_trend = self.I(lambda x, p: pd.Series(x).rolling(p).mean(), close, self.sma_trend_period)
        self.sma_exit = self.I(lambda x, p: pd.Series(x).rolling(p).mean(), close, self.exit_sma_period)
        self.rsi_val = self.I(rsi, close, self.rsi_period)
        self.entry_price = None
        self.max_price = 0

    def next(self):
        if not self.position:
            if self.data.Close[-1] > self.sma_trend[-1] and self.rsi_val[-1] < self.rsi_threshold:
                self.buy()
                self.entry_price = self.data.Close[-1]
                self.max_price = self.data.Close[-1]
        else:
            self.max_price = max(self.max_price, self.data.Close[-1])
            do_exit = False

            if self.data.Close[-1] <= self.entry_price * (1 - self.stop_loss_pct):
                do_exit = True

            if self.exit_type == 'rsi':
                if self.rsi_val[-1] > 70:
                    do_exit = True
            elif self.exit_type == 'sma':
                if self.data.Close[-1] > self.sma_exit[-1]:
                    do_exit = True
            elif self.exit_type == 'trailing':
                if self.data.Close[-1] <= self.max_price * (1 - self.trailing_pct):
                    do_exit = True

            if do_exit:
                self.position.close()
                self.entry_price = None
                self.max_price = 0

def main():
    sma_trends = [100, 200]
    entries = [
        {'rsi_period': 2, 'rsi_threshold': 10},
        {'rsi_period': 2, 'rsi_threshold': 15},
        {'rsi_period': 3, 'rsi_threshold': 15},
    ]
    exits = [
        {'exit_type': 'rsi'},
        {'exit_type': 'sma', 'exit_sma_period': 5},
        {'exit_type': 'trailing', 'trailing_pct': 0.04},
        {'exit_type': 'trailing', 'trailing_pct': 0.06},
        {'exit_type': 'trailing', 'trailing_pct': 0.08},
    ]

    combinations = []
    for sma_t in sma_trends:
        for entry in entries:
            for ex in exits:
                params = entry.copy()
                params.update(ex)
                params['sma_trend_period'] = sma_t
                combinations.append(params)

    all_results = []
    symbols = ["BTC/USDT", "ETH/USDT"]
    timeframes = ["4h", "1d"]

    for symbol in symbols:
        for tf in timeframes:
            print(f"Testing {symbol} {tf}...")
            try:
                df = fetch_binance_data(symbol, tf)
            except Exception as e:
                print(f"Error fetching {symbol} {tf}: {e}")
                continue

            if df.empty: continue
            df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']] / 1_000_000

            split = int(len(df) * 0.7)
            train_df = df.iloc[:split]
            test_df = df.iloc[split:]

            for params in combinations:
                bt_is = Backtest(train_df, GridStrategy, cash=100, commission=0.001, exclusive_orders=True)
                stats_is = bt_is.run(**params)

                if stats_is['Profit Factor'] <= 1.20:
                    continue

                bt_oos = Backtest(test_df, GridStrategy, cash=100, commission=0.001, exclusive_orders=True)
                stats_oos = bt_oos.run(**params)

                if stats_oos['# Trades'] < 15:
                    continue

                all_results.append({
                    'symbol': symbol,
                    'timeframe': tf,
                    'params': params,
                    'is_pf': stats_is['Profit Factor'],
                    'oos_pf': stats_oos['Profit Factor'],
                    'oos_trades': stats_oos['# Trades'],
                    'oos_return': stats_oos['Return [%]']
                })

    all_results.sort(key=lambda x: x['oos_pf'], reverse=True)

    print("\nTOP 5 COMBINATIONS:")
    for r in all_results[:5]:
        print(f"{r['symbol']} {r['timeframe']} | OOS PF: {r['oos_pf']:.2f} | IS PF: {r['is_pf']:.2f} | Trades: {r['oos_trades']} | Params: {r['params']}")

    if all_results:
        best = all_results[0]
        config = {
            "best_symbol": best['symbol'],
            "best_timeframe": best['timeframe'],
            "rsi_period": best['params'].get('rsi_period', 2),
            "rsi_low": best['params'].get('rsi_threshold', 15),
            "sma_trend": best['params'].get('sma_trend_period', 100),
            "exit_type": best['params'].get('exit_type', 'rsi'),
            "sma_exit": best['params'].get('exit_sma_period', 5),
            "trailing_pct": best['params'].get('trailing_pct', 0.06),
            "stop_loss_pct": 0.06,
            "min_notional_usdt": 5.5,
            "position_size": 0.45
        }
        with open("crypto_config.json", "w") as f:
            json.dump(config, f, indent=2)
        print("\nConfig updated.")
    else:
        print("\nNo valid setup found.")

if __name__ == "__main__":
    main()
