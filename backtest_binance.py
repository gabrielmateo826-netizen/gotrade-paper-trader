import yfinance as yf
import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

class CryptoRSIStrategy(Strategy):
    def init(self):
        # Loosened crypto rules: Close > SMA50 and RSI2 < 15
        self.close = self.data.Close
        self.sma50 = self.I(lambda x: pd.Series(x).rolling(50).mean(), self.data.Close)
        self.sma5 = self.I(lambda x: pd.Series(x).rolling(5).mean(), self.data.Close)

        def RSI2(close):
            delta = pd.Series(close).diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.ewm(alpha=0.5, min_periods=2, adjust=False).mean()
            avg_loss = loss.ewm(alpha=0.5, min_periods=2, adjust=False).mean()
            rs = avg_gain / avg_loss
            return 100.0 - (100.0 / (1.0 + rs))

        self.rsi2 = self.I(RSI2, self.data.Close)

    def next(self):
        # Entry: Close > SMA50 and RSI2 < 15
        if self.close[-1] > self.sma50[-1] and self.rsi2[-1] < 15:
            if not self.position:
                self.buy()

        # Exit: RSI2 > 70 or price spike (Close > SMA5)
        if self.position and (self.rsi2[-1] > 70 or self.close[-1] > self.sma5[-1]):
            self.position.close()

def run_backtest(ticker):
    print(f"\n--- Backtesting {ticker} ---")
    # Fetch 2 years of data
    data = yf.download(ticker, period="2y", interval="1d", progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        data = data.xs(ticker, level=1, axis=1)

    bt = Backtest(data, CryptoRSIStrategy, cash=10000, commission=.001)
    stats = bt.run()

    # Print specific requested metrics
    print(f"Win Rate: {stats['Win Rate [%]']:.2f}%")
    print(f"Return [%]: {stats['Return [%]']:.2f}%")
    print(f"Max Drawdown [%]: {stats['Max Drawdown [%]']:.2f}%")

    return stats

if __name__ == "__main__":
    run_backtest("BTC-USD")
    run_backtest("ETH-USD")
