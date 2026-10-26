# 30-Day Forward Paper Trading Arena (GoTrade Setup)

Simulating automated swing trades across **QQQ, SPY, AAPL, MSFT, NVDA, EPHE** with live US market feeds.

### Macro Market Regime Gate: 🟢 **GREEN (Active)**
*New entries are only permitted when the S&P 500 (`SPY`) trades above its 200-day SMA, CBOE Volatility Index (`^VIX`) < 25.0, and 30-day cumulative drawdown > -$8.50.*

### Exposure Coach Status: ⚠️ **DEFENSIVE (50% Sizing - $21.25 Tranches)**

---

### Comparative Strategy Scoreboard

| Metric | Model A: RSI-2 Dip Buyer | Model B: Dual Momentum Swing |
| :--- | :--- | :--- |
| **Philosophy** | Mean Reversion (Buy Oversold Panics) | Trend-Following (Breakouts & Pullbacks) |
| **Virtual Capital** | $85.00 USD (2x $42.50 tranches) | $85.00 USD (2x $42.50 tranches) |
| **Total Closed Trades** | 4 | 5 |
| **Win Rate %** | 25.0% (1/4) | 20.0% (1/5) |
| **Profit Factor** | 0.07 | 0.53 |
| **Cumulative Net P&L** | **$-2.65 USD** | **$-1.12 USD** |

*All results deduct GoTrade's 0.60% round-trip commission friction (0.30% buy + 0.30% sell).*

---

### Currently Open Positions
_No active open positions. Cash intact._

---

### Recent Closed Trade History
|   Trade_ID | Strategy      | Ticker   | Status             | Entry_Date   |   Entry_Price | Exit_Date   |   Exit_Price |   Tranche_USD |   Gross_PnL |   Fees_USD |   Net_PnL | Return_Pct   | Notes                                                                 |
|-----------:|:--------------|:---------|:-------------------|:-------------|--------------:|:------------|-------------:|--------------:|------------:|-----------:|----------:|:-------------|:----------------------------------------------------------------------|
|          1 | Dual-Momentum | AAPL     | Target Hit (2R)    | 2026-10-11   |        336.64 | 2026-10-23  |       348.52 |         42.5  |        1.5  |       0.26 |      1.24 | +2.93%       | Stop:330.7 | Target:348.52 | Pullback | PostMortem: Target Reached    |
|          2 | RSI-2         | NVDA     | Stop Hit           | 2026-10-12   |        226.32 | 2026-10-15  |       215    |         42.5  |       -2.13 |       0.26 |     -2.38 | -5.60%       | RSI2: 8.9                                                             |
|          3 | Dual-Momentum | QQQ      | Stop Hit           | 2026-10-13   |        743.57 | 2026-10-15  |       738.84 |         42.5  |       -0.27 |       0.26 |     -0.53 | -1.24%       | Stop:738.84 | Target:753.03 | Pullback                                |
|          4 | RSI-2         | QQQ      | Target Hit (5 SMA) | 2026-10-15   |        723.63 | 2026-10-21  |       725.2  |         42.5  |        0.09 |       0.26 |     -0.16 | -0.38%       | RSI2: 3.3                                                             |
|          5 | RSI-2         | SPY      | Target Hit (5 SMA) | 2026-10-15   |        769.97 | 2026-10-20  |       769.05 |         42.5  |       -0.05 |       0.26 |     -0.31 | -0.72%       | RSI2: 7.5                                                             |
|          6 | Dual-Momentum | SPY      | Stop Hit           | 2026-10-15   |        771.79 | 2026-10-16  |       764.44 |         42.5  |       -0.4  |       0.26 |     -0.66 | -1.55%       | Stop:764.44 | Target:786.49 | Pullback                                |
|          7 | Dual-Momentum | SPY      | Stop Hit           | 2026-10-16   |        771.79 | 2026-10-16  |       764.43 |         42.5  |       -0.41 |       0.26 |     -0.66 | -1.55%       | Stop:764.43 | Target:786.51 | Pullback                                |
|          8 | Dual-Momentum | SPY      | Stop Hit           | 2026-10-21   |        773.09 | 2026-10-22  |       768.4  |         42.5  |       -0.26 |       0.26 |     -0.51 | -1.21%       | Stop:768.4 | Target:782.47 | Pullback | PostMortem: Technical Whipsaw |
|          9 | RSI-2         | MSFT     | Target Hit (5 SMA) | 2026-10-23   |        524.51 | 2026-10-26  |       532.6  |         21.25 |        0.33 |       0.13 |      0.2  | +0.94%       | RSI2: 9.3 (Exposure Coach: 50% Sized) | PostMortem: Target Reached    |

*Automated via GitHub Actions. Runs daily at 5:05 AM PHT after US market close.*
