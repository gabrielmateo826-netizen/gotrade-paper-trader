# Trading Engine Confirmation & Binance Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Telegram confirmation loop for GoTrade, audit Binance order execution, and create a crypto backtester.

**Architecture:**
- **Confirmation Loop:** `tracker.py` will poll `getUpdates` via `urllib` to process `callback_query`. Signals will be stored in `pending_trades.json` and only moved to `trades.csv` upon "✅ Executed" confirmation.
- **Binance Audit:** `binance_executor.py` will use `amount_to_precision` and enforce a 5.5 USDT minimum notional check before `create_market_order`.
- **Backtester:** `backtest_binance.py` will use `backtesting.py` and `yfinance` to evaluate crypto rules on BTC/ETH data.

**Tech Stack:** `ccxt`, `backtesting`, `yfinance`, `pandas`, `urllib`.

**Spec:** User prompt (2026-11-20)

## Global Constraints
- Minimum Binance Notional: 5.5 USDT.
- Backtest Commission: 0.10%.
- Backtest Data: 2 years BTC/USDT, ETH/USDT.
- Telegram Interface: Inline keyboard with "✅ Executed" and "❌ Skipped".

## Review Focus
- **Callback Latency:** Callbacks arriving days after signal; must be handled by `pending_trades.json` lookup.
- **Precision Error:** Invalid amount formats for different Binance pairs; must use `amount_to_precision`.
- **Notional Floor:** Orders < 5.5 USDT being sent; must be blocked by auditor.
- **Backtest Leakage:** Future look-ahead bias in crypto rules.
- **State Sync:** `trades.csv` updates must be atomic to prevent corruption during confirmation move.

---

### Task 1: Binance Executor Audit & Fix

**Files:**
- Modify: `binance_executor.py`
- Test: `tests/test_trading_engine.py`

**Interfaces:**
- Produces: `execute_trade(symbol, side, amount)` now enforces notional and precision.

- [ ] **Step 1: Write failing tests**
    - Test `execute_trade` raises error or returns None for amount < 5.5 USDT notional.
    - Test `execute_trade` calls `amount_to_precision` (mock `ccxt` exchange).
- [ ] **Step 2: Implement Notional & Precision checks**
    - In `execute_trade`:
        - Call `self.exchange.amount_to_precision(symbol, amount)`.
        - Calculate `notional = amount * current_price` (fetch price via `fetch_ticker`).
        - If `notional < 5.5`, print error and return `None`.
- [ ] **Step 3: Verify tests pass**
- [ ] **Step 4: Commit**

### Task 2: Binance Backend Backtest

**Files:**
- Create: `backtest_binance.py`

**Interfaces:**
- Produces: Performance summary (Equity curve, CAGR, Max Drawdown) printed to console.

- [ ] **Step 1: Implement data fetcher**
    - Use `yf.download` for BTC-USD and ETH-USD for 2 years.
- [ ] **Step 2: Implement `BinanceStrategy` class (Backtesting.py)**
    - Logic: Implement the "Crypto Rules" (as derived from current `tracker.py` logic or specified crypto rules).
    - Set commission to 0.001 (0.10%).
- [ ] **Step 3: Run Backtest**
    - Execute `bt.run()` and `bt.plot()`.
- [ ] **Step 4: Print summary metrics**
- [ ] **Step 5: Commit**

### Task 3: GoTrade Telegram Confirmation Loop

**Files:**
- Modify: `tracker.py`
- Create: `pending_trades.json`
- Test: `tests/test_trading_engine.py`

**Interfaces:**
- Consumes: Telegram `getUpdates` callback queries.
- Produces: Confirmed entries/exits in `trades.csv`.

- [ ] **Step 1: Update `send_telegram` for Inline Keyboards**
    - Add `reply_markup` with `inline_keyboard` containing buttons:
        - `{"text": "✅ Executed", "callback_data": f"exec_{trade_id}"}`
        - `{"text": "❌ Skipped", "callback_data": f"skip_{trade_id}"}`
- [ ] **Step 2: Implement `process_telegram_callbacks()`**
    - Call `getUpdates` with `allowed_updates=["callback_query"]`.
    - If `exec_{id}`, move trade from `pending_trades.json` to `trades.csv`.
    - If `skip_{id}`, remove from `pending_trades.json`.
- [ ] **Step 3: Defer Logging**
    - Modify entry/exit logic: Instead of `trades_df = pd.concat(...)`, write to `pending_trades.json`.
- [ ] **Step 4: Integrate polling at start of `tracker.py`**
    - Run `process_telegram_callbacks()` before evaluating new entries.
- [ ] **Step 5: Verify with unit tests**
    - Mock `getUpdates` response and verify `trades.csv` update.
- [ ] **Step 6: Commit**

### Task 4: Final Verification & Push

- [ ] **Step 1: Run full test suite**
    - `python -m unittest discover -s tests`
- [ ] **Step 2: Push to origin main**
