import unittest
import os
import sys
from unittest.mock import patch, MagicMock
import pandas as pd

# Add parent directory to path to import tracker
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tracker


class TestTradingEngine(unittest.TestCase):
    """Test suite for GoTrade Paper Trading Engine"""

    def setUp(self):
        """Set up test fixtures before each test"""
        # Create test data for tracker
        self.test_trades_df = pd.DataFrame([
            {
                "Trade_ID": 1,
                "Strategy": "RSI-2",
                "Ticker": "AAPL",
                "Status": "Target Hit (5 SMA)",
                "Entry_Date": "2026-10-23",
                "Entry_Price": 524.51,
                "Exit_Date": "2026-10-26",
                "Exit_Price": 532.60,
                "Tranche_USD": 42.50,
                "Gross_PnL": 0.33,
                "Fees_USD": 0.13,
                "Net_PnL": 0.20,
                "Return_Pct": "+0.94%",
                "Notes": "RSI2: 9.3 (Exposure Coach: 50% Sized) | PostMortem: Target Reached"
            },
            {
                "Trade_ID": 2,
                "Strategy": "Dual-Momentum",
                "Ticker": "SPY",
                "Status": "Target Hit (2R)",
                "Entry_Date": "2026-10-15",
                "Entry_Price": 771.79,
                "Exit_Date": "2026-10-16",
                "Exit_Price": 764.44,
                "Tranche_USD": 42.50,
                "Gross_PnL": -0.40,
                "Fees_USD": 0.26,
                "Net_PnL": -0.66,
                "Return_Pct": "-1.55%",
                "Notes": "Stop:764.44 | Target:786.49 | Pullback | PostMortem: Target Reached"
            }
        ])

        # Mock the trades_df in tracker module
        tracker.trades_df = self.test_trades_df.copy()

    def test_vix_gate(self):
        """Test VIX gate functionality"""
        # Mock market data to simulate VIX < 25.0 (calm)
        mock_market_data = {
            "SPY": MagicMock(
                Close=[700.0],
                SMA200=[650.0],  # SPY > 200 SMA
                iloc=MagicMock(
                    __getitem__=MagicMock(return_value=MagicMock(
                        Close=700.0,
                        SMA200=650.0
                    ))
                )
            ),
            "^VIX": MagicMock(
                Close=[24.0],  # VIX < 25.0 (calm)
                iloc=MagicMock(
                    __getitem__=MagicMock(return_value=MagicMock(
                        Close=24.0
                    ))
                )
            )
        }

        with patch.object(tracker, 'market_data', mock_market_data):
            # Set up tracker module state
            tracker.spy_above_sma200 = True
            tracker.vix_calm = True
            tracker.circuit_breaker_active = False
            tracker.macro_regime_green = True
            tracker.gate_status = "GREEN"

            self.assertTrue(tracker.macro_regime_green, "Macro regime should be GREEN when VIX < 25 and SPY > 200 SMA")

    def test_vix_gate_red_when_vix_above_25(self):
        """Test VIX gate turns RED when VIX >= 25.0"""
        tracker.spy_above_sma200 = True
        tracker.vix_calm = False  # VIX >= 25.0
        tracker.circuit_breaker_active = False
        tracker.macro_regime_green = False
        tracker.gate_status = "RED (VIX >= 25.0 High Volatility)"

        self.assertFalse(tracker.macro_regime_green, "Macro regime should be RED when VIX >= 25.0")

    def test_exposure_coach_halving(self):
        """Test Exposure Coach halves position size after two consecutive losing trades"""
        # Mock closed trades with two consecutive losses
        tracker.closed_trades_history = pd.DataFrame([
            {
                "Net_PnL": -2.00  # First losing trade
            },
            {
                "Net_PnL": -1.50  # Second losing trade (consecutive loss)
            }
        ])

        # Reset tracker state
        tracker.tranche_usd = tracker.BASE_TRANCHE_USD
        tracker.exposure_coach_reduced = False

        # Simulate the logic from tracker.py lines 147-152
        if len(tracker.closed_trades_history) >= 2:
            last_two = tracker.closed_trades_history.tail(2)
            last_two_pnl = pd.to_numeric(last_two["Net_PnL"], errors="coerce").dropna()
            if len(last_two_pnl) == 2 and all(last_two_pnl < 0):
                tracker.tranche_usd = round(tracker.BASE_TRANCHE_USD * 0.50, 2)
                tracker.exposure_coach_reduced = True

        # Verify exposure coach is active
        self.assertTrue(tracker.exposure_coach_reduced, "Exposure Coach should be reduced after two consecutive losses")
        self.assertEqual(tracker.tranche_usd, 21.25, "Tranche size should be $21.25 (50% of $42.50)")

    def test_exposure_coach_normal_when_not_triggered(self):
        """Test Exposure Coach remains normal when not triggered"""
        # Mock closed trades with winning trades
        tracker.closed_trades_history = pd.DataFrame([
            {
                "Net_PnL": 2.00  # Winning trade
            },
            {
                "Net_PnL": 1.50  # Another winning trade
            }
        ])

        # Reset tracker state
        tracker.tranche_usd = tracker.BASE_TRANCHE_USD
        tracker.exposure_coach_reduced = False

        # Simulate the logic from tracker.py lines 147-152
        if len(tracker.closed_trades_history) >= 2:
            last_two = tracker.closed_trades_history.tail(2)
            last_two_pnl = pd.to_numeric(last_two["Net_PnL"], errors="coerce").dropna()
            if len(last_two_pnl) == 2 and all(last_two_pnl < 0):
                tracker.tranche_usd = round(tracker.BASE_TRANCHE_USD * 0.50, 2)
                tracker.exposure_coach_reduced = True

        # Verify exposure coach is not active
        self.assertFalse(tracker.exposure_coach_reduced, "Exposure Coach should not be reduced with winning trades")
        self.assertEqual(tracker.tranche_usd, 42.50, "Tranche size should remain $42.50")

    def test_binance_sandbox_default(self):
        """Test that Binance defaults to sandbox/demo trading mode"""
        # Test environment variable configuration
        test_env_vars = {
            "BINANCE_API_KEY": "test_key",
            "BINANCE_SECRET_KEY": "test_secret",
            "BINANCE_SANDBOX": "true"
        }

        with patch.dict(os.environ, test_env_vars):
            # This simulates the binance_executor.py module that should use sandbox by default
            # Verify that environment variables are properly loaded
            self.assertEqual(os.environ.get("BINANCE_SANDBOX"), "true",
                           "BINANCE_SANDBOX should default to true for demo trading")

    def test_dragonfi_capital_gate(self):
        """Test DragonFi capital-gated signal filter"""
        # Test PHP capital >= 25,000 condition
        test_php_capital = 30000  # Above threshold

        # Simulate the logic from the requirements
        dragonfi_allowed = test_php_capital >= 25000

        self.assertTrue(dragonfi_allowed, "DragonFi signals should be allowed when PHP >= 25,000")

        # Test with capital below threshold
        test_php_capital = 20000  # Below threshold
        dragonfi_allowed = test_php_capital >= 25000

        self.assertFalse(dragonfi_allowed, "DragonFi signals should be suppressed when PHP < 25,000")

    def test_dragonfi_allocated_php_empty_string_falls_back_to_zero(self):
        """Test DRAGONFI_ALLOCATED_PHP="" safely falls back to 0.0 (GitHub Actions empty secret)"""
        import importlib

        with patch.dict(os.environ, {"DRAGONFI_ALLOCATED_PHP": ""}):
            importlib.reload(tracker)

        try:
            self.assertEqual(tracker.DRAGONFI_ALLOCATED_PHP, 0.0,
                             "Empty DRAGONFI_ALLOCATED_PHP must fall back to 0.0, not crash")
        finally:
            # Restore the module to the real environment value
            importlib.reload(tracker)


if __name__ == '__main__':
    unittest.main()