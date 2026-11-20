import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# Add parent directory to path to import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from binance_executor import BinanceExecutor

class TestBinanceExecutor(unittest.TestCase):
    def setUp(self):
        # Patch environment variables to avoid real API interactions
        with patch.dict(os.environ, {
            "BINANCE_TESTNET_API_KEY": "test_key",
            "BINANCE_TESTNET_SECRET": "test_secret",
            "BINANCE_USE_TESTNET": "True"
        }):
            self.executor = BinanceExecutor()

    def test_execute_trade_blocks_low_notional(self):
        """Test execute_trade returns None for notional < 5.5 USDT"""
        # Mock exchange and fetch_ticker
        self.executor.exchange = MagicMock()
        self.executor.exchange.amount_to_precision.return_value = "0.001"
        self.executor.exchange.fetch_ticker.return_value = {'last': 100.0} # Notional = 0.001 * 100 = 0.1 < 5.5

        result = self.executor.execute_trade("BTC/USDT", "buy", 0.001)
        self.assertIsNone(result, "Order should be rejected for notional < 5.5 USDT")
        self.executor.exchange.create_market_order.assert_not_called()

    def test_execute_trade_uses_precision(self):
        """Test execute_trade calls amount_to_precision"""
        self.executor.exchange = MagicMock()
        self.executor.exchange.amount_to_precision.return_value = "0.002"
        self.executor.exchange.fetch_ticker.return_value = {'last': 3000.0} # Notional = 0.002 * 3000 = 6.0 > 5.5

        self.executor.execute_trade("BTC/USDT", "buy", 0.002)
        self.executor.exchange.amount_to_precision.assert_called_with("BTC/USDT", 0.002)
        self.executor.exchange.create_market_order.assert_called_once()

if __name__ == "__main__":
    unittest.main()
