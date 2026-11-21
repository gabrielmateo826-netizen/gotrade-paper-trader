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

class CryptoSwingStrategy(Strategy):
    def init(self):
        self.close = self.data.Close
        # Trend filter: Close > SMA(50)
        self.sma50 = self.I(lambda x: pd.Series(x).rolling(50).mean(), self.data.Close)

        def RSI2(close):
            delta = pd.Series(close).diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.ewm(alpha=0.5, min_periods=2, adjust=False).mean()
            avg_loss = loss.ewm(alpha=0.5, min_periods=2, adjust=False).mean()
            rs = avg_gain / avg_loss
            return 100.0 - (100.0 / (1.0 + rs))

        self.rsi2 = self.I(RSI2, self.data.Close)
        self.sma5 = self.I(lambda x: pd.Series(x).rolling(5).mean(), self.data.Close)
        self.entry_bar = None
        self.entry_price = None

    def next(self):
        # Entry: Close > SMA(50) and RSI(2) < 15
        if self.close[-1] > self.sma50[-1] and self.rsi2[-1] < 15:
            if not self.position:
                self.buy(size=0.45)
                self.entry_bar = len(self.data)
                self.entry_price = self.close[-1]

        if self.position:
            # Exit: RSI(2) > 70 OR Close > SMA(5) OR 5-bar time stop OR 6% hard SL
            price = self.entry_price if self.entry_price is not None else self.close[-1]
            if (self.rsi2[-1] > 70 or
                self.close[-1] > self.sma5[-1] or
                (self.entry_bar is not None and len(self.data) - self.entry_bar >= 5) or
                self.close[-1] <= price * 0.94):
                self.position.close()
                self.entry_bar = None
                self.entry_price = None

def run_split_backtest(symbol, timeframe):
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

    results = {}
    for name, data in [("In-Sample", train_df), ("Out-of-Sample", test_df)]:
        bt = Backtest(data, CryptoSwingStrategy, cash=100, commission=0.001, exclusive_orders=True)
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

if __name__ == "__main__":
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)

    best_metrics = None
    best_tf = "1d"

    for sym in ["BTC/USDT", "ETH/USDT"]:
        for tf in ["4h", "1d"]:
            res = run_split_backtest(sym, tf)
            if res is not None:
                # Use Out-of-Sample Return as primary metric for config
                if best_metrics is None or res.loc["Out-of-Sample", 'Return [%]'] > best_metrics['Return [%]']:
                    best_metrics = res.loc["Out-of-Sample"]
                    best_tf = tf

    config = {
        "best_timeframe": best_tf,
        "rsi_low": 15,
        "rsi_high": 70,
        "sma_trend": 50,
        "sma_exit": 5,
        "stop_loss_pct": 0.06,
        "min_notional_usdt": 5.5,
        "position_size": 0.45
    }

    with open("crypto_config.json", "w") as f:
        json.dump(config, f, indent=2)
    print("\nConfig saved to crypto_config.json")
