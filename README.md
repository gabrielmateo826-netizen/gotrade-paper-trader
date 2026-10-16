# 30-Day Forward Paper Trading Arena (GoTrade Setup)

Simulating automated swing trades across **QQQ, SPY, AAPL, MSFT, NVDA, EPHE** with live US market feeds.

### Macro Market Regime Gate: 🟢 **GREEN (Active)**
*New entries are only permitted when the S&P 500 (`SPY`) trades above its 200-day Simple Moving Average.*

---

### Comparative Strategy Scoreboard

| Metric | Model A: RSI-2 Dip Buyer | Model B: Dual Momentum Swing |
| :--- | :--- | :--- |
| **Philosophy** | Mean Reversion (Buy Oversold Panics) | Trend-Following (Breakouts & Pullbacks) |
| **Virtual Capital** | $85.00 USD (2x $42.50 tranches) | $85.00 USD (2x $42.50 tranches) |
| **Total Closed Trades** | 1 | 3 |
| **Win Rate %** | 0.0% (0/1) | 0.0% (0/3) |
| **Profit Factor** | 0.0 | 0.0 |
| **Cumulative Net P&L** | **$-2.38 USD** | **$-1.85 USD** |

*All results deduct GoTrade's 0.60% round-trip commission friction (0.30% buy + 0.30% sell).*

---

### Currently Open Positions
|   Trade_ID | Strategy      | Ticker   | Entry_Date   |   Entry_Price | Notes                                 |
|-----------:|:--------------|:---------|:-------------|--------------:|:--------------------------------------|
|          1 | Dual-Momentum | AAPL     | 2026-10-11   |        336.64 | Stop:330.7 | Target:348.52 | Pullback |
|          4 | RSI-2         | QQQ      | 2026-10-15   |        723.63 | RSI2: 3.3                             |
|          5 | RSI-2         | SPY      | 2026-10-15   |        769.97 | RSI2: 7.5                             |

---

### Recent Closed Trade History
|   Trade_ID | Strategy      | Ticker   | Status   | Entry_Date   |   Entry_Price | Exit_Date   |   Exit_Price |   Tranche_USD |   Gross_PnL |   Fees_USD |   Net_PnL | Return_Pct   | Notes                                  |
|-----------:|:--------------|:---------|:---------|:-------------|--------------:|:------------|-------------:|--------------:|------------:|-----------:|----------:|:-------------|:---------------------------------------|
|          2 | RSI-2         | NVDA     | Stop Hit | 2026-10-12   |        226.32 | 2026-10-15  |       215    |          42.5 |       -2.13 |       0.26 |     -2.38 | -5.60%       | RSI2: 8.9                              |
|          3 | Dual-Momentum | QQQ      | Stop Hit | 2026-10-13   |        743.57 | 2026-10-15  |       738.84 |          42.5 |       -0.27 |       0.26 |     -0.53 | -1.24%       | Stop:738.84 | Target:753.03 | Pullback |
|          6 | Dual-Momentum | SPY      | Stop Hit | 2026-10-15   |        771.79 | 2026-10-16  |       764.44 |          42.5 |       -0.4  |       0.26 |     -0.66 | -1.55%       | Stop:764.44 | Target:786.49 | Pullback |
|          7 | Dual-Momentum | SPY      | Stop Hit | 2026-10-16   |        771.79 | 2026-10-16  |       764.43 |          42.5 |       -0.41 |       0.26 |     -0.66 | -1.55%       | Stop:764.43 | Target:786.51 | Pullback |

*Automated via GitHub Actions. Runs daily at 5:05 AM PHT after US market close.*
