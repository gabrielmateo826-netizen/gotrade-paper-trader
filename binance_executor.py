import os
import ccxt
from dotenv import load_dotenv

load_dotenv()

class BinanceExecutor:
    def __init__(self):
        self.api_key = os.environ.get("BINANCE_TESTNET_API_KEY")
        self.secret = os.environ.get("BINANCE_TESTNET_SECRET")
        self.use_testnet = os.environ.get("BINANCE_USE_TESTNET", "True").lower() == "true"

        self.exchange = ccxt.binance({
            'apiKey': self.api_key,
            'secret': self.secret,
            'enableRateLimit': True,
        })

        if self.use_testnet:
            self.exchange.set_sandbox_mode(True)
            # Explicitly point to Spot Testnet API
            self.exchange.urls['api'] = {
                'public': 'https://testnet.binance.vision/api',
                'private': 'https://testnet.binance.vision/api',
            }

    def execute_trade(self, symbol, side, amount):
        """Executes a spot trade. symbol e.g. 'BTC/USDT'"""
        try:
            # Disable fetchCurrencies for testnet stability as requested
            self.exchange.options['defaultType'] = 'spot'

            # 1. Enforce precision
            precision_amount = self.exchange.amount_to_precision(symbol, amount)

            # 2. Enforce minimum notional (5.5 USDT)
            ticker = self.exchange.fetch_ticker(symbol)
            price = ticker['last']
            notional = float(precision_amount) * price
            if notional < 5.5:
                print(f"Order rejected: Notional {notional:.2f} USDT < 5.5 USDT minimum.")
                return None

            order = self.exchange.create_market_order(symbol, side, precision_amount)
            return order
        except Exception as e:
            print(f"Binance execution error: {e}")
            return None

    def get_usdt_balance(self):
        """Fetches the virtual USDT balance from the Spot Testnet wallet."""
        try:
            balance = self.exchange.fetch_balance()
            free = balance.get("free", {})
            usdt = free.get("USDT", 0.0)
            return float(usdt)
        except Exception as e:
            print(f"Binance balance fetch error: {e}")
            return None

if __name__ == "__main__":
    # Simple sanity check
    executor = BinanceExecutor()
    print(f"Binance initialized. Sandbox: {executor.use_testnet}")
