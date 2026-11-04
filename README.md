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
| **Total Closed Trades** | 5 | 7 |
| **Win Rate %** | 40.0% (2/5) | 14.3% (1/7) |
| **Profit Factor** | 0.17 | 0.36 |
| **Cumulative Net P&L** | **$-2.36 USD** | **$-2.19 USD** |

*All results deduct GoTrade's 0.60% round-trip commission friction (0.30% buy + 0.30% sell).*

---

### Currently Open Positions
|   Trade_ID | Strategy      | Ticker   | Entry_Date   |   Entry_Price | Notes                                                              |
|-----------:|:--------------|:---------|:-------------|--------------:|:-------------------------------------------------------------------|
|         12 | RSI-2         | QQQ      | 2026-11-02   |        681.09 | RSI2: 8.4 (Exposure Coach: 50% Sized)                              |
|         14 | Dual-Momentum | SPY      | 2026-11-04   |        766.81 | Stop:762.64 | Target:775.15 | Pullback (Exposure Coach: 50% Sized) |
|         15 | RSI-2         | AAPL     | 2026-11-04   |        349.51 | RSI2: 6.5 (Exposure Coach: 50% Sized)                              |
|         16 | Dual-Momentum | MSFT     | 2026-11-04   |        555.8  | Stop:542.34 | Target:582.72 | Breakout (Exposure Coach: 50% Sized) |

---

### Recent Closed Trade History
|   Trade_ID | Strategy      | Ticker   | Status             | Entry_Date   |   Entry_Price | Exit_Date   |   Exit_Price |   Tranche_USD |   Gross_PnL |   Fees_USD |   Net_PnL | Return_Pct   | Notes                                                                  |
|-----------:|:--------------|:---------|:-------------------|:-------------|--------------:|:------------|-------------:|--------------:|------------:|-----------:|----------:|:-------------|:-----------------------------------------------------------------------|
|          3 | Dual-Momentum | QQQ      | Stop Hit           | 2026-10-13   |        743.57 | 2026-10-15  |       738.84 |         42.5  |       -0.27 |       0.26 |     -0.53 | -1.24%       | Stop:738.84 | Target:753.03 | Pullback                                 |
|          4 | RSI-2         | QQQ      | Target Hit (5 SMA) | 2026-10-15   |        723.63 | 2026-10-21  |       725.2  |         42.5  |        0.09 |       0.26 |     -0.16 | -0.38%       | RSI2: 3.3                                                              |
|          5 | RSI-2         | SPY      | Target Hit (5 SMA) | 2026-10-15   |        769.97 | 2026-10-20  |       769.05 |         42.5  |       -0.05 |       0.26 |     -0.31 | -0.72%       | RSI2: 7.5                                                              |
|          6 | Dual-Momentum | SPY      | Stop Hit           | 2026-10-15   |        771.79 | 2026-10-16  |       764.44 |         42.5  |       -0.4  |       0.26 |     -0.66 | -1.55%       | Stop:764.44 | Target:786.49 | Pullback                                 |
|          7 | Dual-Momentum | SPY      | Stop Hit           | 2026-10-16   |        771.79 | 2026-10-16  |       764.43 |         42.5  |       -0.41 |       0.26 |     -0.66 | -1.55%       | Stop:764.43 | Target:786.51 | Pullback                                 |
|          8 | Dual-Momentum | SPY      | Stop Hit           | 2026-10-21   |        773.09 | 2026-10-22  |       768.4  |         42.5  |       -0.26 |       0.26 |     -0.51 | -1.21%       | Stop:768.4 | Target:782.47 | Pullback | PostMortem: Technical Whipsaw  |
|          9 | RSI-2         | MSFT     | Target Hit (5 SMA) | 2026-10-23   |        524.51 | 2026-10-26  |       532.6  |         21.25 |        0.33 |       0.13 |      0.2  | +0.94%       | RSI2: 9.3 (Exposure Coach: 50% Sized) | PostMortem: Target Reached     |
|         10 | Dual-Momentum | SPY      | Stop Hit           | 2026-10-27   |        769.66 | 2026-10-30  |       765.21 |         42.5  |       -0.25 |       0.26 |     -0.5  | -1.18%       | Stop:765.21 | Target:778.56 | Pullback | PostMortem: Technical Whipsaw |
|         11 | Dual-Momentum | QQQ      | Stop Hit           | 2026-10-28   |        725.61 | 2026-10-29  |       720.3  |         42.5  |       -0.31 |       0.26 |     -0.57 | -1.33%       | Stop:720.3 | Target:736.23 | Pullback | PostMortem: Technical Whipsaw  |
|         13 | RSI-2         | SPY      | Target Hit (5 SMA) | 2026-11-02   |        752.1  | 2026-11-04  |       766.81 |         21.25 |        0.42 |       0.13 |      0.29 | +1.36%       | RSI2: 9.3 (Exposure Coach: 50% Sized) | PostMortem: Target Reached     |

*Automated via GitHub Actions. Runs daily at 5:05 AM PHT after US market close.*
