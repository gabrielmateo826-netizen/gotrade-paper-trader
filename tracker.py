import datetime
import json
import os
import urllib.parse
import urllib.request
import numpy as np
import pandas as pd
import yfinance as yf

# ==============================================================================
# CONFIGURATION & UNIVERSE (VIEWPOINT 1: EPHE INCLUDED)
# ==============================================================================
UNIVERSE = ["QQQ", "SPY", "AAPL", "MSFT", "NVDA", "EPHE"]
MACRO_TICKER = "SPY"
COMMISSION_ROUND_TRIP = 0.0060  # 0.30% buy + 0.30% sell (GoTrade)
TRANCHE_USD = 42.50
MAX_TRANCHES_PER_STRATEGY = 2
CSV_FILE = "trades.csv"

# Telegram Secrets
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def send_telegram(message):
  """Sends structured trading alerts directly to Telegram."""
  if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("Telegram tokens not detected. Skipping message dispatch.")
    return
  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  payload = json.dumps({
      "chat_id": TELEGRAM_CHAT_ID,
      "text": message,
      "parse_mode": "Markdown",
  }).encode("utf-8")
  req = urllib.request.Request(
      url, data=payload, headers={"Content-Type": "application/json"}
  )
  try:
    with urllib.request.urlopen(req, timeout=10) as response:
      pass
    print("Telegram notification delivered successfully.")
  except Exception as e:
    print(f"Failed to deliver Telegram notification: {e}")


# 1. Initialize CSV structure if not present
if not os.path.exists(CSV_FILE):
  df_init = pd.DataFrame(columns=[
      "Trade_ID",
      "Strategy",
      "Ticker",
      "Status",
      "Entry_Date",
      "Entry_Price",
      "Exit_Date",
      "Exit_Price",
      "Tranche_USD",
      "Gross_PnL",
      "Fees_USD",
      "Net_PnL",
      "Return_Pct",
      "Notes",
  ])
  df_init.to_csv(CSV_FILE, index=False)

# 2. Load trades with explicit string schema
trades_df = pd.read_csv(
    CSV_FILE,
    dtype={
        "Trade_ID": "Int64",
        "Strategy": "str",
        "Ticker": "str",
        "Status": "str",
        "Entry_Date": "str",
        "Exit_Date": "str",
        "Return_Pct": "str",
        "Notes": "str",
    },
)

today_str = datetime.date.today().strftime("%Y-%m-%d")

# ==============================================================================
# 3. FETCH HISTORICAL DATA & COMPUTE INDICATORS
# ==============================================================================
print(f"Fetching market data for universe: {UNIVERSE}...")
market_data = {}

for ticker in UNIVERSE:
  try:
    df = yf.download(ticker, period="1y", interval="1d", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
      df = df.xs(ticker, level=1, axis=1)
    df = df.dropna().copy()

    # Technical Indicators
    df["SMA200"] = df["Close"].rolling(200).mean()
    df["SMA5"] = df["Close"].rolling(5).mean()
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["Vol_SMA20"] = df["Volume"].rolling(20).mean()
    df["High20"] = df["High"].shift(1).rolling(20).max()

    # Wilder's 2-period RSI
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 2, min_periods=2, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 2, min_periods=2, adjust=False).mean()
    rs = avg_gain / avg_loss
    df["RSI2"] = 100 - (100 / (1 + rs))

    market_data[ticker] = df
  except Exception as e:
    print(f"Error loading {ticker}: {e}")

# ==============================================================================
# VIEWPOINT 2: MACRO REGIME GATE (SPY > 200 SMA)
# ==============================================================================
macro_regime_green = False
if MACRO_TICKER in market_data:
  spy_latest = market_data[MACRO_TICKER].iloc[-1]
  spy_close = float(spy_latest["Close"])
  spy_sma200 = float(spy_latest["SMA200"])
  macro_regime_green = spy_close > spy_sma200
  print(
      f"--- MACRO GATE CHECK: SPY Close: ${spy_close:.2f} | 200 SMA:"
      f" ${spy_sma200:.2f} | Gate: {'GREEN' if macro_regime_green else 'RED'}"
      " ---"
  )

# ==============================================================================
# 4. EVALUATE EXITS ON OPEN POSITIONS
# ==============================================================================
open_indices = trades_df[trades_df["Status"] == "Open"].index

for idx in open_indices:
  strategy = str(trades_df.loc[idx, "Strategy"])
  ticker = str(trades_df.loc[idx, "Ticker"])
  entry_p = float(trades_df.loc[idx, "Entry_Price"])

  if ticker not in market_data:
    continue

  df = market_data[ticker]
  latest = df.iloc[-1]
  curr_close = float(latest["Close"])
  curr_low = float(latest["Low"])
  curr_high = float(latest["High"])

  exit_status = None
  exit_price = None

  if strategy == "RSI-2":
    sma5_val = float(latest["SMA5"])
    stop_loss = entry_p * 0.95  # 5% Hard Stop

    if curr_low <= stop_loss:
      exit_status = "Stop Hit"
      exit_price = stop_loss
    elif curr_close > sma5_val:
      exit_status = "Target Hit (5 SMA)"
      exit_price = curr_close

  elif strategy == "Dual-Momentum":
    try:
      notes_parts = str(trades_df.loc[idx, "Notes"]).split("|")
      stop_loss = float(notes_parts[0].replace("Stop:", "").strip())
      target_price = float(notes_parts[1].replace("Target:", "").strip())
    except Exception:
      stop_loss = entry_p * 0.94
      target_price = entry_p * 1.08

    if curr_high >= target_price:
      exit_status = "Target Hit (2R)"
      exit_price = target_price
    elif curr_low <= stop_loss:
      exit_status = "Stop Hit"
      exit_price = stop_loss

  if exit_status:
    gross_pnl = (exit_price - entry_p) * (TRANCHE_USD / entry_p)
    fees = TRANCHE_USD * COMMISSION_ROUND_TRIP
    net_pnl = gross_pnl - fees
    ret_pct = (net_pnl / TRANCHE_USD) * 100

    trades_df.loc[idx, "Status"] = str(exit_status)
    trades_df.loc[idx, "Exit_Date"] = str(today_str)
    trades_df.loc[idx, "Exit_Price"] = round(exit_price, 2)
    trades_df.loc[idx, "Gross_PnL"] = round(gross_pnl, 2)
    trades_df.loc[idx, "Fees_USD"] = round(fees, 2)
    trades_df.loc[idx, "Net_PnL"] = round(net_pnl, 2)
    trades_df.loc[idx, "Return_Pct"] = f"{ret_pct:+.2f}%"

    # Send Telegram Exit Alert
    icon = "🟢" if net_pnl >= 0 else "🔴"
    exit_msg = (
        f"{icon} *EXIT ALERT: [{strategy}]*\n"
        f"• *Ticker:* {ticker}\n"
        f"• *Action:* SELL ALL SHARES (Market Sell)\n"
        f"• *Exit Price:* ${exit_price:.2f}\n"
        f"• *Reason:* {exit_status}\n"
        f"• *Net P&L:* ${net_pnl:+.2f} ({ret_pct:+.2f}% net)\n"
        f"_(GoTrade: Open Portfolio -> {ticker} -> Market Sell 100%)_"
    )
    send_telegram(exit_msg)

# ==============================================================================
# 5. EVALUATE NEW ENTRIES ACROSS THE UNIVERSE (GATED BY MACRO)
# ==============================================================================
rsi2_open = len(
    trades_df[
        (trades_df["Strategy"] == "RSI-2") & (trades_df["Status"] == "Open")
    ]
)
mom_open = len(
    trades_df[
        (trades_df["Strategy"] == "Dual-Momentum")
        & (trades_df["Status"] == "Open")
    ]
)

if not macro_regime_green:
  print(
      "-> MACRO REGIME IS RED (SPY <= 200 SMA). New entries paused to protect"
      " capital."
  )
else:
  for ticker, df in market_data.items():
    if len(df) < 200:
      continue

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    c = float(latest["Close"])
    o = float(latest["Open"])
    low_c = float(latest["Low"])
    vol = float(latest["Volume"])

    sma200 = float(latest["SMA200"])
    ema20 = float(latest["EMA20"])
    ema50 = float(latest["EMA50"])
    vol_sma20 = float(latest["Vol_SMA20"])
    high20 = float(latest["High20"])
    prev_rsi2 = float(prev["RSI2"])

    # --- MODEL A: RSI-2 Dip Setup ---
    if rsi2_open < MAX_TRANCHES_PER_STRATEGY:
      already_holding = any(
          (trades_df["Strategy"] == "RSI-2")
          & (trades_df["Ticker"] == ticker)
          & (trades_df["Status"] == "Open")
      )
      if not already_holding and (c > sma200) and (prev_rsi2 < 10.0):
        new_id = (
            int(trades_df["Trade_ID"].max()) + 1
            if len(trades_df) > 0 and pd.notna(trades_df["Trade_ID"].max())
            else 1
        )
        new_row = {
            "Trade_ID": new_id,
            "Strategy": "RSI-2",
            "Ticker": ticker,
            "Status": "Open",
            "Entry_Date": today_str,
            "Entry_Price": round(c, 2),
            "Exit_Date": "",
            "Exit_Price": np.nan,
            "Tranche_USD": TRANCHE_USD,
            "Gross_PnL": np.nan,
            "Fees_USD": np.nan,
            "Net_PnL": np.nan,
            "Return_Pct": "",
            "Notes": f"RSI2: {prev_rsi2:.1f}",
        }
        trades_df = pd.concat(
            [trades_df, pd.DataFrame([new_row])], ignore_index=True
        )
        rsi2_open += 1

        # Send Telegram Entry Alert
        entry_msg = (
            f"🛒 *ENTRY ALERT: [RSI-2 Dip]*\n"
            f"• *Ticker:* {ticker}\n"
            f"• *Action:* BUY $42.50 USD (Market Buy)\n"
            f"• *Current Price:* ${c:.2f}\n"
            f"• *Condition:* 2-Period RSI @ {prev_rsi2:.1f} (Oversold)\n"
            f"• *Target:* Close > 5 SMA | Hard Stop: -5.0%\n"
            f"_(GoTrade: Open App at 9:30 PM PHT -> Market Buy $42.50)_"
        )
        send_telegram(entry_msg)

    # --- MODEL B: Dual Momentum Setup ---
    if mom_open < MAX_TRANCHES_PER_STRATEGY:
      already_holding_mom = any(
          (trades_df["Strategy"] == "Dual-Momentum")
          & (trades_df["Ticker"] == ticker)
          & (trades_df["Status"] == "Open")
      )
      if not already_holding_mom and (c > ema50):
        is_breakout = (c >= high20) and (vol >= 1.75 * vol_sma20)
        is_pullback = (low_c <= ema20) and (c > ema20) and (c > o)

        if is_breakout or is_pullback:
          raw_risk = c - low_c
          if (raw_risk / c > 0.06) or (raw_risk <= 0):
            stop_loss = round(c * 0.94, 2)
          else:
            stop_loss = round(low_c, 2)

          risk_val = c - stop_loss
          target_val = round(c + (2.0 * risk_val), 2)
          setup_type = "Breakout" if is_breakout else "Pullback"

          new_id = (
              int(trades_df["Trade_ID"].max()) + 1
              if len(trades_df) > 0 and pd.notna(trades_df["Trade_ID"].max())
              else 1
          )
          new_row = {
              "Trade_ID": new_id,
              "Strategy": "Dual-Momentum",
              "Ticker": ticker,
              "Status": "Open",
              "Entry_Date": today_str,
              "Entry_Price": round(c, 2),
              "Exit_Date": "",
              "Exit_Price": np.nan,
              "Tranche_USD": TRANCHE_USD,
              "Gross_PnL": np.nan,
              "Fees_USD": np.nan,
              "Net_PnL": np.nan,
              "Return_Pct": "",
              "Notes": f"Stop:{stop_loss} | Target:{target_val} | {setup_type}",
          }
          trades_df = pd.concat(
              [trades_df, pd.DataFrame([new_row])], ignore_index=True
          )
          mom_open += 1

          # Send Telegram Entry Alert
          entry_msg = (
              f"🚀 *ENTRY ALERT: [Dual-Momentum]*\n"
              f"• *Ticker:* {ticker}\n"
              f"• *Action:* BUY $42.50 USD (Market Buy)\n"
              f"• *Setup:* {setup_type} @ ${c:.2f}\n"
              f"• *Stop-Loss:* ${stop_loss:.2f} \vert{} *Target (2R):*${target_val:.2f}\n"
              f"_(GoTrade: Open App at 9:30 PM PHT -> Market Buy $42.50)_"
          )
          send_telegram(entry_msg)

trades_df.to_csv(CSV_FILE, index=False)

# ==============================================================================
# 6. BUILD DYNAMIC README SCOREBOARD
# ==============================================================================


def calc_metrics(strat_name):
  subset = trades_df[
      (trades_df["Strategy"] == strat_name)
      & (
          trades_df["Status"].isin(
              ["Target Hit (5 SMA)", "Target Hit (2R)", "Stop Hit"]
          )
      )
  ]
  total = len(subset)
  if total == 0:
    return {"total": 0, "wr": "0.0%", "pnl": "$0.00", "pf": "N/A"}

  pnl_series = pd.to_numeric(subset["Net_PnL"], errors="coerce").dropna()
  wins = pnl_series[pnl_series > 0]
  losses = pnl_series[pnl_series < 0]
  wr = f"{(len(wins) / total) * 100:.1f}% ({len(wins)}/{total})"
  net_pnl = f"${pnl_series.sum():+.2f}"
  pf = (
      f"{wins.sum() / abs(losses.sum()):.2f}"
      if abs(losses.sum()) > 0
      else ("Inf" if wins.sum() > 0 else "N/A")
  )
  return {"total": total, "wr": wr, "pnl": net_pnl, "pf": pf}


m_rsi = calc_metrics("RSI-2")
m_mom = calc_metrics("Dual-Momentum")

open_trades = trades_df[trades_df["Status"] == "Open"]
closed_trades = trades_df[trades_df["Status"] != "Open"]

open_trades_table = (
    open_trades[
        ["Trade_ID", "Strategy", "Ticker", "Entry_Date", "Entry_Price", "Notes"]
    ].to_markdown(index=False)
    if len(open_trades) > 0
    else "_No active open positions. Cash intact._"
)

closed_trades_table = (
    closed_trades.tail(10).to_markdown(index=False)
    if len(closed_trades) > 0
    else "_No closed trades yet._"
)

gate_badge = (
    "🟢 **GREEN (Active)**"
    if macro_regime_green
    else "🔴 **RED (Paused - Cash Protected)**"
)

readme_content = f"""# 30-Day Forward Paper Trading Arena (GoTrade Setup)

Simulating automated swing trades across **{', '.join(UNIVERSE)}** with live US market feeds.

### Macro Market Regime Gate: {gate_badge}
*New entries are only permitted when the S&P 500 (`SPY`) trades above its 200-day Simple Moving Average.*

---

### Comparative Strategy Scoreboard

| Metric | Model A: RSI-2 Dip Buyer | Model B: Dual Momentum Swing |
| :--- | :--- | :--- |
| **Philosophy** | Mean Reversion (Buy Oversold Panics) | Trend-Following (Breakouts & Pullbacks) |
| **Virtual Capital** | $85.00 USD (2x $42.50 tranches) | $85.00 USD (2x $42.50 tranches) |
| **Total Closed Trades** | {m_rsi['total']} | {m_mom['total']} |
| **Win Rate %** | {m_rsi['wr']} | {m_mom['wr']} |
| **Profit Factor** | {m_rsi['pf']} | {m_mom['pf']} |
| **Cumulative Net P&L** | **{m_rsi['pnl']} USD** | **{m_mom['pnl']} USD** |

*All results deduct GoTrade's 0.60% round-trip commission friction (0.30% buy + 0.30% sell).*

---

### Currently Open Positions
{open_trades_table}

---

### Recent Closed Trade History
{closed_trades_table}

*Automated via GitHub Actions. Runs daily at 5:05 AM PHT after US market close.*
"""

with open("README.md", "w") as f:
  f.write(readme_content)

print("Engine run complete. README.md scoreboard refreshed successfully.")
