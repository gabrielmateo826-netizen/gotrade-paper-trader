# 30-Day Forward Paper Trading Arena (GoTrade Setup)

Simulating automated swing trades across **QQQ, SPY, AAPL, MSFT, NVDA** with live US market feeds.

### Comparative Strategy Scoreboard

| Metric | Model A: RSI-2 Dip Buyer | Model B: Dual Momentum Swing |
| :--- | :--- | :--- |
| **Philosophy** | Mean Reversion (Buy Oversold Panics) | Trend-Following (Breakouts & Pullbacks) |
| **Virtual Capital** | $85.00 USD (2x $42.50 tranches) | $85.00 USD (2x $42.50 tranches) |
| **Total Closed Trades** | 0 | 0 |
| **Win Rate %** | 0.0% | 0.0% |
| **Profit Factor** | N/A | N/A |
| **Cumulative Net P&L** | **$0.00 USD** | **$0.00 USD** |

*All results deduct GoTrade's 0.60% round-trip commission friction (0.30% buy + 0.30% sell).*

---

### Currently Open Positions
|   Trade_ID | Strategy      | Ticker   | Entry_Date   |   Entry_Price | Notes                                 |
|-----------:|:--------------|:---------|:-------------|--------------:|:--------------------------------------|
|          1 | Dual-Momentum | AAPL     | 2026-10-11   |        336.64 | Stop:330.7 | Target:348.52 | Pullback |

---

### Recent Closed Trade History
| Trade_ID   | Strategy   | Ticker   | Status   | Entry_Date   | Entry_Price   | Exit_Date   | Exit_Price   | Tranche_USD   | Gross_PnL   | Fees_USD   | Net_PnL   | Return_Pct   | Notes   |
|------------|------------|----------|----------|--------------|---------------|-------------|--------------|---------------|-------------|------------|-----------|--------------|---------|

*Automated via GitHub Actions. Runs daily at 5:05 AM PHT after US market close.*
