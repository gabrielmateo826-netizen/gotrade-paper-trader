import datetime
import json
import os
import urllib.parse
import urllib.request
import numpy as np
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURATION & UNIVERSE (INCLUDES EPHE)
# ==============================================================================
UNIVERSE = ["QQQ", "SPY", "AAPL", "MSFT", "NVDA", "EPHE"]
MACRO_TICKER = "SPY"
VIX_TICKER = "^VIX"
COMMISSION_ROUND_TRIP = 0.0060  # 0.30% buy + 0.30% sell (GoTrade)
BASE_TRANCHE_USD = 42.50
MAX_TRANCHES_PER_STRATEGY = 2
MAX_PORTFOLIO_DRAWDOWN_USD = -8.50  # Drawdown Circuit Breaker: -10% of $85
CSV_FILE = "trades.csv"

# DragonFi Gate
DRAGONFI_ALLOCATED_PHP = float(os.environ.get("DRAGONFI_ALLOCATED_PHP") or "0")
DRAGONFI_CAPITAL_GATE = 25000.0

# Telegram Secrets
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def send_telegram(message):
  """Dispatches alert messages to Telegram without f-strings."""
  if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("Telegram credentials not configured. Skipping alert dispatch.")
    return False

  endpoint = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"
  payload = json.dumps({
      "chat_id": TELEGRAM_CHAT_ID,
      "text": message,
      "parse_mode": "Markdown",
  }).encode("utf-8")

  req = urllib.request.Request(
      endpoint, data=payload, headers={"Content-Type": "application/json"}
  )
  try:
    with urllib.request.urlopen(req, timeout=10) as resp:
      pass
    print("Telegram alert delivered successfully.")
    return True
  except Exception as e:
    print("Telegram dispatch error: " + str(e))
    return False


def is_earnings_blackout(ticker):
  """Earnings Blackout Gate: skips single stocks reporting within 3 days."""
  if ticker in ["QQQ", "SPY", "EPHE"]:
    return False, "ETF (No Earnings)"
  try:
    t = yf.Ticker(ticker)
    cal = t.calendar
    earnings_date = None
    if isinstance(cal, dict) and "Earnings Date" in cal:
      ed = cal["Earnings Date"]
      if isinstance(ed, list) and len(ed) > 0:
        earnings_date = pd.to_datetime(ed[0]).date()
      elif isinstance(ed, (datetime.date, datetime.datetime)):
        earnings_date = pd.to_datetime(ed).date()
    elif isinstance(cal, pd.DataFrame) and not cal.empty:
      if "Earnings Date" in cal.index:
        val = cal.loc["Earnings Date"].iloc[0]
        earnings_date = pd.to_datetime(val).date()

    if earnings_date:
      days_diff = (earnings_date - datetime.date.today()).days
      if 0 <= days_diff <= 3:
        return True, (
            "Earnings in "
            + str(days_diff)
            + " days ("
            + str(earnings_date)
            + ")"
        )
    return False, "Clear"
  except Exception:
    return False, "Clear (Data Fallback)"


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

# 2. Load trades with strict string schema
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
# 1b. TELEGRAM CONFIRMATION & PENDING TRADES
# ==============================================================================
PENDING_TRADES_FILE = "pending_trades.json"

def get_telegram_updates():
    """Polls Telegram for /✅_Executed or /❌_Skipped callbacks via getUpdates."""
    if not TELEGRAM_BOT_TOKEN:
        return []

    endpoint = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        req = urllib.request.Request(endpoint)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if not data.get("ok"):
                return []

            confirmed_tickers = []
            skipped_tickers = []

            for update in data.get("result", []):
                # Check for callback queries or message text as fallbacks
                callback = update.get("callback_query")
                if callback:
                    cb_data = callback.get("data", "")
                    if cb_data.startswith("exec_"):
                        confirmed_tickers.append(cb_data.replace("exec_", ""))
                    elif cb_data.startswith("skip_"):
                        skipped_tickers.append(cb_data.replace("skip_", ""))

                # Also handle text commands if callback fails
                msg = update.get("message")
                if msg and msg.get("text"):
                    text = msg.get("text")
                    if text.startswith("/executed_"):
                        confirmed_tickers.append(text.replace("/executed_", ""))
                    elif text.startswith("/skipped_"):
                        skipped_tickers.append(text.replace("/skipped_", ""))

            return list(set(confirmed_tickers)), list(set(skipped_tickers))
    except Exception as e:
        print(f"Telegram polling error: {e}")
        return [], []

def load_pending_trades():
    if os.path.exists(PENDING_TRADES_FILE):
        try:
            with open(PENDING_TRADES_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_pending_trades(pending):
    with open(PENDING_TRADES_FILE, "w") as f:
        json.dump(pending, f, indent=2)

def send_telegram_with_inline_keyboard(message, ticker):
    """Sends message with inline buttons for execution confirmation."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    endpoint = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    # Simple inline keyboard for confirmation
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Executed", "callback_data": f"exec_{ticker}"},
            {"text": "❌ Skipped", "callback_data": f"skip_{ticker}"}
        ]]
    }

    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "reply_markup": keyboard
    }).encode("utf-8")

    req = urllib.request.Request(
        endpoint, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            pass
        return True
    except Exception as e:
        print(f"Telegram keyboard dispatch error: {e}")
        # Fallback to plain message
        return send_telegram(message)

# Initialize pending trades and poll for confirmations
updates = get_telegram_updates()
confirmed_list, skipped_list = updates if updates else ([], [])
pending_trades = load_pending_trades()

# Move confirmed pending trades into trades_df
for ticker in confirmed_list:
    if ticker in pending_trades:
        trade_data = pending_trades[ticker]
        # Only add if not already in trades_df (prevent duplicates from re-polling)
        exists = any((trades_df["Ticker"] == ticker) & (trades_df["Status"] == "Open"))
        if not exists:
            trades_df = pd.concat([trades_df, pd.DataFrame([trade_data])], ignore_index=True)
        del pending_trades[ticker]

# Remove skipped trades
for ticker in skipped_list:
    if ticker in pending_trades:
        del pending_trades[ticker]

# Save updated pending list
save_pending_trades(pending_trades)

# ==============================================================================
# 3. EXPOSURE COACH & DRAWDOWN CIRCUIT BREAKER
# ==============================================================================
closed_trades_history = trades_df[
    trades_df["Status"].isin(
        ["Target Hit (5 SMA)", "Target Hit (2R)", "Stop Hit"]
    )
].copy()

# A. Drawdown Circuit Breaker (-10% cap)
total_closed_pnl = 0.0
if not closed_trades_history.empty:
  numeric_pnl = pd.to_numeric(
      closed_trades_history["Net_PnL"], errors="coerce"
  ).dropna()
  total_closed_pnl = float(numeric_pnl.sum())

circuit_breaker_active = total_closed_pnl <= MAX_PORTFOLIO_DRAWDOWN_USD

# B. Exposure Coach (Dynamic Sizing)
tranche_usd = BASE_TRANCHE_USD
exposure_coach_reduced = False

if len(closed_trades_history) >= 2:
  last_two = closed_trades_history.tail(2)
  last_two_pnl = pd.to_numeric(last_two["Net_PnL"], errors="coerce").dropna()
  if len(last_two_pnl) == 2 and all(last_two_pnl < 0):
    tranche_usd = round(BASE_TRANCHE_USD * 0.50, 2)  # Cut by 50% to $21.25
    exposure_coach_reduced = True

# ==============================================================================
# 4. FETCH HISTORICAL DATA & COMPUTE TECHNICAL METRICS
# ==============================================================================
fetch_list = list(UNIVERSE) + [VIX_TICKER]
universe_str = ", ".join(UNIVERSE)
print(
    "Fetching market data for universe: "
    + universe_str
    + " and "
    + VIX_TICKER
    + "..."
)
market_data = {}

for ticker in fetch_list:
  try:
    df = yf.download(ticker, period="1y", interval="1d", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
      df = df.xs(ticker, level=1, axis=1)
    df = df.dropna().copy()

    # Core Technical Indicators
    df["SMA200"] = df["Close"].rolling(200).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA5"] = df["Close"].rolling(5).mean()
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["Vol_SMA20"] = df["Volume"].rolling(20).mean()
    df["High20"] = df["High"].shift(1).rolling(20).max()

    # Wilder's 2-period RSI
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=0.5, min_periods=2, adjust=False).mean()
    avg_loss = loss.ewm(alpha=0.5, min_periods=2, adjust=False).mean()
    rs = avg_gain / avg_loss
    df["RSI2"] = 100.0 - (100.0 / (1.0 + rs))

    market_data[ticker] = df
  except Exception as e:
    print("Error loading " + str(ticker) + ": " + str(e))

# ==============================================================================
# MACRO REGIME & VIX VOLATILITY GATE (SPY > 200 SMA AND VIX < 25)
# ==============================================================================
spy_above_sma200 = False
vix_calm = False
spy_close = 0.0
spy_sma200 = 0.0
vix_close = 0.0

if MACRO_TICKER in market_data:
  spy_latest = market_data[MACRO_TICKER].iloc[-1]
  spy_close = float(spy_latest["Close"])
  spy_sma200 = float(spy_latest["SMA200"])
  spy_above_sma200 = spy_close > spy_sma200

if VIX_TICKER in market_data:
  vix_latest = market_data[VIX_TICKER].iloc[-1]
  vix_close = float(vix_latest["Close"])
  vix_calm = vix_close < 25.0

macro_regime_green = (
    spy_above_sma200 and vix_calm and not circuit_breaker_active
)

if circuit_breaker_active:
  gate_status = "RED (Circuit Breaker Tripped: -$8.50 hit)"
elif not spy_above_sma200:
  gate_status = "RED (SPY <= 200 SMA)"
elif not vix_calm:
  gate_status = "RED (VIX >= 25.0 High Volatility)"
else:
  gate_status = "GREEN"

print(
    "--- MACRO GATE: SPY $"
    + str(round(spy_close, 2))
    + " | 200 SMA: $"
    + str(round(spy_sma200, 2))
    + " | VIX: "
    + str(round(vix_close, 2))
    + " | Gate: "
    + gate_status
    + " ---"
)

# ==============================================================================
# 4b. BINANCE SPOT TESTNET STATUS CHECK (runs regardless of Macro Gate)
# ==============================================================================
binance_status = "Testnet: OFFLINE"
binance_usdt = None
try:
  from binance_executor import BinanceExecutor
  executor = BinanceExecutor()
  binance_usdt = executor.get_usdt_balance()
  if binance_usdt is not None:
    binance_status = "Testnet: ONLINE"
except Exception as e:
  print("Binance Spot Testnet check skipped: " + str(e))

print(
    "--- BINANCE SPOT TESTNET: "
    + binance_status
    + " | Virtual USDT Balance: "
    + str(binance_usdt)
    + " ---"
)

# ==============================================================================
# 5. EVALUATE EXITS ON OPEN POSITIONS
# ==============================================================================
open_indices = trades_df[trades_df["Status"] == "Open"].index
exits_triggered = 0

for idx in open_indices:
  strategy = str(trades_df.loc[idx, "Strategy"])
  ticker = str(trades_df.loc[idx, "Ticker"])
  entry_p = float(trades_df.loc[idx, "Entry_Price"])
  allocated_tranche = (
      float(trades_df.loc[idx, "Tranche_USD"])
      if pd.notna(trades_df.loc[idx, "Tranche_USD"])
      else BASE_TRANCHE_USD
  )

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
    shares_owned = allocated_tranche / entry_p
    market_value_usd = shares_owned * exit_price

    gross_pnl = (exit_price - entry_p) * shares_owned
    fees = allocated_tranche * COMMISSION_ROUND_TRIP
    net_pnl = gross_pnl - fees
    ret_pct = (net_pnl / allocated_tranche) * 100.0

    # Post-Mortem Taxonomy Tagging
    post_mortem_tag = "Target Reached"
    if "Stop" in str(exit_status):
      if vix_close >= 22.0:
        post_mortem_tag = (
            "High Volatility Drag (VIX " + str(round(vix_close, 1)) + ")"
        )
      elif not spy_above_sma200:
        post_mortem_tag = "Macro Downtrend Drag"
      else:
        post_mortem_tag = "Technical Whipsaw"

    trades_df.loc[idx, "Status"] = str(exit_status)
    trades_df.loc[idx, "Exit_Date"] = str(today_str)
    trades_df.loc[idx, "Exit_Price"] = round(exit_price, 2)
    trades_df.loc[idx, "Gross_PnL"] = round(gross_pnl, 2)
    trades_df.loc[idx, "Fees_USD"] = round(fees, 2)
    trades_df.loc[idx, "Net_PnL"] = round(net_pnl, 2)
    trades_df.loc[idx, "Return_Pct"] = (
        ("+" if ret_pct >= 0 else "") + str(round(ret_pct, 2)) + "%"
    )
    existing_notes = (
        str(trades_df.loc[idx, "Notes"])
        if pd.notna(trades_df.loc[idx, "Notes"])
        else ""
    )
    trades_df.loc[idx, "Notes"] = (
        existing_notes + " | PostMortem: " + post_mortem_tag
    )
    exits_triggered += 1

    icon = "🟢" if net_pnl >= 0 else "🔴"
    pnl_sign = "+" if net_pnl >= 0 else ""

    # Check if another position in the same ticker is active
    other_open_in_same_ticker = any(
        (trades_df["Ticker"] == ticker)
        & (trades_df["Status"] == "Open")
        & (trades_df.index != idx)
    )

    shared_ticker_note = ""
    if other_open_in_same_ticker:
      shared_ticker_note = (
          "\n⚠️ *Note:* You have another open trade in "
          + ticker
          + ". Do NOT tap 'Sell 100%'. Use Method 1 or Method 2 below."
      )

    exit_msg = (
        icon
        + " *EXIT ALERT: ["
        + strategy
        + "]*\n"
        + "• *Ticker:* "
        + ticker
        + "\n"
        + "• *Reason:* "
        + str(exit_status)
        + " @ $"
        + str(round(exit_price, 2))
        + " ("
        + post_mortem_tag
        + ")\n"
        + "• *Net P&L:* $"
        + pnl_sign
        + str(round(net_pnl, 2))
        + " ("
        + str(trades_df.loc[idx, "Return_Pct"])
        + " net after fees)\n"
        + shared_ticker_note
        + "\n"
        + "📋 *WHAT TO DO ON GOTRADE AT 9:30 PM PHT:*\n"
        + "1. Open GoTrade -> Portfolio -> *"
        + ticker
        + "* -> Tap *Sell*\n"
        + "2. Choose either method:\n"
        + "   • *Method 1 (By Shares - Recommended):* Tap 'Shares' -> Enter *"
        + str(round(shares_owned, 4))
        + "* shares\n"
        + "   • *Method 2 (By USD Amount):* Tap 'USD ($)' -> Enter *$"
        + str(round(market_value_usd, 2))
        + "*\n"
        + "   • *(Or tap 'Sell 100%' if "
        + ticker
        + " is your only active trade)*"
    )
    send_telegram(exit_msg)

# ==============================================================================
# 6. EVALUATE NEW ENTRIES ACROSS THE UNIVERSE (GATED BY MACRO, VIX, EARNINGS)
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
entries_triggered = 0

if macro_regime_green:
  for ticker, df in market_data.items():
    if ticker == VIX_TICKER or len(df) < 200:
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

    # Cross-Strategy Exclusion Rule
    is_already_held = any(
        (trades_df["Ticker"] == ticker) & (trades_df["Status"] == "Open")
    )

    # Earnings Blackout Gate Check
    has_earnings_conflict, earnings_desc = is_earnings_blackout(ticker)
    if has_earnings_conflict:
      print(
          "-> Skipping "
          + ticker
          + " due to Earnings Blackout: "
          + earnings_desc
      )
      continue

    # Model A: RSI-2 Dip
    if rsi2_open < MAX_TRANCHES_PER_STRATEGY and not is_already_held:
      if (c > sma200) and (prev_rsi2 < 10.0):
        # DragonFi Gate Check for PSE (simulated via ticker check)
        if "PSE" in ticker or ticker == "EPHE": # Example PSE indicator
            if DRAGONFI_ALLOCATED_PHP < DRAGONFI_CAPITAL_GATE:
                print(f"-> Skipping {ticker} (DragonFi): PHP {DRAGONFI_ALLOCATED_PHP} < {DRAGONFI_CAPITAL_GATE}")
                continue

        new_id = (
            int(trades_df["Trade_ID"].max()) + 1
            if len(trades_df) > 0 and pd.notna(trades_df["Trade_ID"].max())
            else 1
        )
        shares_to_buy = tranche_usd / c
        coach_note = (
            " (Exposure Coach: 50% Sized)" if exposure_coach_reduced else ""
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
            "Tranche_USD": tranche_usd,
            "Gross_PnL": np.nan,
            "Fees_USD": np.nan,
            "Net_PnL": np.nan,
            "Return_Pct": "",
            "Notes": "RSI2: " + str(round(prev_rsi2, 1)) + coach_note,
        }
        # Store in pending trades instead of trades_df
        pending_trades[str(new_id)] = new_row
        save_pending_trades(pending_trades)
        rsi2_open += 1
        entries_triggered += 1
        is_already_held = True

        entry_msg = (
            "🛒 *ENTRY ALERT: [RSI-2 Dip]*"
            + coach_note
            + "\n"
            + "• *Ticker:* "
            + ticker
            + "\n"
            + "• *Setup Price:* $"
            + str(round(c, 2))
            + " | RSI(2): "
            + str(round(prev_rsi2, 1))
            + "\n"
            + "• *Exit Target:* Close > 5 SMA | Hard Stop: -5.0%\n\n"
            + "📋 *WHAT TO DO ON GOTRADE AT 9:30 PM PHT:*\n"
            + "1. Open GoTrade -> Search *"
            + ticker
            + "* -> Tap *Buy*\n"
            + "2. Select *Market Buy*\n"
            + "3. Enter either:\n"
            + "   • *Method 1 (Easiest):* Tap 'USD ($)' -> Enter *$"
            + str(round(tranche_usd, 2))
            + "*\n"
            + "   • *Method 2:* Tap 'Shares' -> Enter *"
            + str(round(shares_to_buy, 4))
            + "* shares"
        )
        send_telegram_with_inline_keyboard(entry_msg, new_id)

    # Model B: Dual Momentum
    if mom_open < MAX_TRANCHES_PER_STRATEGY and not is_already_held:
      if c > ema50:
        is_breakout = (c >= high20) and (vol >= 1.75 * vol_sma20)
        is_pullback = (low_c <= ema20) and (c > ema20) and (c > o)

        if is_breakout or is_pullback:
          raw_risk = c - low_c
          stop_loss = (
              round(c * 0.94, 2)
              if (raw_risk / c > 0.06 or raw_risk <= 0)
              else round(low_c, 2)
          )
          target_val = round(c + (2.0 * (c - stop_loss)), 2)
          setup_type = "Breakout" if is_breakout else "Pullback"

          new_id = (
              int(trades_df["Trade_ID"].max()) + 1
              if len(trades_df) > 0 and pd.notna(trades_df["Trade_ID"].max())
              else 1
          )
          shares_to_buy = tranche_usd / c
          coach_note = (
              " (Exposure Coach: 50% Sized)" if exposure_coach_reduced else ""
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
              "Tranche_USD": tranche_usd,
              "Gross_PnL": np.nan,
              "Fees_USD": np.nan,
              "Net_PnL": np.nan,
              "Return_Pct": "",
              "Notes": (
                  "Stop:"
                  + str(stop_loss)
                  + " | Target:"
                  + str(target_val)
                  + " | "
                  + setup_type
                  + coach_note
              ),
          }
          # Store in pending trades instead of trades_df
          pending_trades[str(new_id)] = new_row
          save_pending_trades(pending_trades)
          mom_open += 1
          entries_triggered += 1

          entry_msg = (
              "🚀 *ENTRY ALERT: [Dual-Momentum]*"
              + coach_note
              + "\n"
              + "• *Ticker:* "
              + ticker
              + "\n"
              + "• *Setup:* "
              + setup_type
              + " @ $"
              + str(round(c, 2))
              + "\n"
              + "• *Stop-Loss:* $"
              + str(stop_loss)
              + " | *Target (2R):* $"
              + str(target_val)
              + "\n\n"
              + "📋 *WHAT TO DO ON GOTRADE AT 9:30 PM PHT:*\n"
              + "1. Open GoTrade -> Search *"
              + ticker
              + "* -> Tap *Buy*\n"
              + "2. Select *Market Buy*\n"
              + "3. Enter either:\n"
              + "   • *Method 1 (Easiest):* Tap 'USD ($)' -> Enter *$"
              + str(round(tranche_usd, 2))
              + "*\n"
              + "   • *Method 2:* Tap 'Shares' -> Enter *"
              + str(round(shares_to_buy, 4))
              + "* shares"
          )
          send_telegram_with_inline_keyboard(entry_msg, new_id)

trades_df.to_csv(CSV_FILE, index=False)

# ==============================================================================
# 7. DAILY TELEGRAM HEARTBEAT
# ==============================================================================
if exits_triggered == 0 and entries_triggered == 0:
  open_count = len(trades_df[trades_df["Status"] == "Open"])
  coach_status = (
      "50% Size ($21.25)" if exposure_coach_reduced else "100% Size ($42.50)"
  )
  heartbeat_msg = (
      "🤖 *GoTrade Paper Bot: Daily Status Update*\n"
      + "• *Date:* "
      + today_str
      + "\n"
      + "• *Macro Gate:* "
      + gate_status
      + "\n"
      + "• *VIX Level:* "
      + str(round(vix_close, 2))
      + " (Cap: <25.0)\n"
      + "• *Tranche Sizing:* "
      + coach_status
      + "\n"
      + "• *Tranches Deployed:* "
      + str(open_count)
      + "/4 active positions\n"
      + "• *Action:* No exits or entries triggered. All stop/target levels"
      " intact."
  )
  send_telegram(heartbeat_msg)

# ==============================================================================
# 8. BUILD DYNAMIC README SCOREBOARD
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
  wr = (
      str(round((len(wins) / total) * 100.0, 1))
      + "% ("
      + str(len(wins))
      + "/"
      + str(total)
      + ")"
  )
  pnl_sum = round(pnl_series.sum(), 2)
  pnl_sign = "+" if pnl_sum >= 0 else ""
  net_pnl = "$" + pnl_sign + str(pnl_sum)
  pf = (
      str(round(wins.sum() / abs(losses.sum()), 2))
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
    "GREEN (Active)" if macro_regime_green else "RED **" + gate_status + "**"
)

coach_badge = (
    "DEFENSIVE (50% Sizing - $21.25 Tranches)"
    if exposure_coach_reduced
    else "NORMAL (100% Sizing - $42.50 Tranches)"
)

readme_content = (
    """# 30-Day Forward Paper Trading Arena (GoTrade Setup)

Simulating automated swing trades across **"""
    + universe_str
    + """** with live US market feeds.

### Macro Market Regime Gate: """
    + gate_badge
    + """
*New entries are only permitted when the S&P 500 (`SPY`) trades above its 200-day SMA, CBOE Volatility Index (`^VIX`) < 25.0, and 30-day cumulative drawdown > -$8.50.*

### Exposure Coach Status: """
    + coach_badge
    + """

---

### Comparative Strategy Scoreboard

| Metric | Model A: RSI-2 Dip Buyer | Model B: Dual Momentum Swing |
| :--- | :--- | :--- |
| **Philosophy** | Mean Reversion (Buy Oversold Panics) | Trend-Following (Breakouts & Pullbacks) |
| **Virtual Capital** | $85.00 USD (2x $42.50 tranches) | $85.00 USD (2x $42.50 tranches) |
| **Total Closed Trades** | """
    + str(m_rsi["total"])
    + """ | """
    + str(m_mom["total"])
    + """ |
| **Win Rate %** | """
    + str(m_rsi["wr"])
    + """ | """
    + str(m_mom["wr"])
    + """ |
| **Profit Factor** | """
    + str(m_rsi["pf"])
    + """ | """
    + str(m_mom["pf"])
    + """ |
| **Cumulative Net P&L** | **"""
    + str(m_rsi["pnl"])
    + """ USD** | **"""
    + str(m_mom["pnl"])
    + """ USD** |

*All results deduct GoTrade's 0.60% round-trip commission friction (0.30% buy + 0.30% sell).*

---

### Currently Open Positions
"""
    + open_trades_table
    + """

---

### Recent Closed Trade History
"""
    + closed_trades_table
    + """

*Automated via GitHub Actions. Runs daily at 5:05 AM PHT after US market close.*
"""
)

with open("README.md", "w") as f:
  f.write(readme_content)

print("Engine run complete. README.md scoreboard refreshed successfully.")
