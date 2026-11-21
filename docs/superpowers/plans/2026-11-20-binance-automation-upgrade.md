# Binance Automation Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `backtest_binance.py` for fractional simulation, automate `binance_executor.py` with state persistence, and integrate into the daily `tracker.py` cycle.

**Architecture:** Backtester generates `crypto_config.json`. Executor uses this config and `crypto_state.json` to manage positions autonomously. Tracker triggers the cycle and reports via Telegram.

**Tech Stack:** Python, ccxt, pandas, backtesting.py, GitHub Actions.

**Spec:** User prompt (pasted_content id="aa35")

## Global Constraints
- Binance Minimum Notional: 5.5 USDT.
- Testnet Default: `BINANCE_USE_TESTNET=True` (`https://testnet.binance.vision/api`).
- Backtest Cash: $100.
- Commission: 0.001.
- Scaling: Prices / 1,000,000; Volume * 1,000,000.

## Review Focus
- Order size < 5.5 USDT: Must reject cleanly with log warning.
- Precision: Must use `amount_to_precision` before `create_market_order`.
- State persistence: `crypto_state.json` must survive GH Action restarts.
- Backtest scaling: DataFrame must be scaled before `Backtest()` initialization.
- Data pagination: `fetch_ohlcv` must use `since` loop to get 3 years of data.

---

### Task 1: Complete `backtest_binance.py`

**Files:**
- Modify: `backtest_binance.py`
- Create: `crypto_config.json`

**Interfaces:**
- Produces: `crypto_config.json` (contains `best_timeframe`, `rsi_low`, `rsi_high`, `sma_trend`, `sma_exit`, `stop_loss_pct`, `min_notional_usdt`)

- [ ] **Step 1: Rewrite `fetch_binance_data` for pagination**
  Implement loop: `while since < exchange.milliseconds():` advancing `since = last_candle_ts + 1` with `limit=1000`.

- [ ] **Step 2: Implement Scaling and `CryptoSwingStrategy`**
  - Scale OHLCV: `df[['Open', 'High', 'Low', 'Close']] /= 1_000_000`, `df['Volume'] *= 1_000_000`.
  - Strategy: `Trend: Close > SMA(50)`, `Entry: RSI(2) < 15` with `size=0.45`.
  - Exit: `RSI(2) > 70` OR `Close > SMA(5)` OR 5-bar stop OR 6% hard SL (`sl=price * 0.94`).

- [ ] **Step 3: Implement Split Backtest and Table Printing**
  - Split 70% In-Sample / 30% Out-of-Sample.
  - Print table with `['Return [%]', 'Buy & Hold Return [%]', 'Win Rate [%]', 'Profit Factor', 'Max. Drawdown [%]', '# Trades']`.

- [ ] **Step 4: Implement `crypto_config.json` export**
  Save validated params and `min_notional_usdt: 5.5`.

- [ ] **Step 5: Run backtest and verify `crypto_config.json` creation**
  Run: `python backtest_binance.py`

- [ ] **Step 6: Commit**

### Task 2: Autonomous `binance_executor.py`

**Files:**
- Modify: `binance_executor.py`
- Create: `crypto_state.json`

**Interfaces:**
- Consumes: `crypto_config.json`
- Produces: `crypto_state.json` (tracks `symbol`, `entry_price`, `entry_ts`, `bars_held`)

- [ ] **Step 1: Implement state and config loading**
  Load `crypto_config.json` and `crypto_state.json` in `__init__`.

- [ ] **Step 2: Implement `run_automated_crypto_cycle()`**
  - Fetch closed candles for `BTC/USDT`, `ETH/USDT`.
  - Apply `CryptoSwingStrategy` rules (Trend, RSI, Exit).
  - Use `crypto_state.json` to track open positions and bar counts.

- [ ] **Step 3: Implement Binance Safety Guards**
  - Check free `USDT` balance.
  - Enforce `order_usdt >= 5.5`.
  - Use `exchange.amount_to_precision(symbol, qty)`.
  - Default `BINANCE_USE_TESTNET=True` and set `urls['api']` to `https://testnet.binance.vision/api`.

- [ ] **Step 4: Commit**

### Task 3: Integration in `tracker.py` and Workflow

**Files:**
- Modify: `tracker.py`
- Modify: `.github/workflows/paper_trade.yml`

**Interfaces:**
- Consumes: `binance_executor.run_automated_crypto_cycle()`

- [ ] **Step 1: Update `tracker.py` to call crypto cycle**
  Invoke `binance_executor.run_automated_crypto_cycle()` and capture summary.

- [ ] **Step 2: Update Telegram Notification**
  Add Binance summary block (Mode, Balance, Positions, Fills) to daily heartbeat.

- [ ] **Step 3: Update GitHub Actions Workflow**
  Add `crypto_state.json` and `crypto_config.json` to `git add`.

- [ ] **Step 4: Commit**

### Task 4: Test Coverage

**Files:**
- Modify: `tests/test_trading_engine.py`

- [ ] **Step 1: Write tests for Micro-coin scaling in `backtest_binance.py`**
  Assert prices are divided by 1M and volume multiplied by 1M.

- [ ] **Step 2: Write tests for Minimum Notional and Precision in `binance_executor.py`**
  Mock `fetch_ticker` and `amount_to_precision`, assert rejection for `< 5.5 USDT`.

- [ ] **Step 3: Write tests for State Persistence in `crypto_state.json`**
  Verify position state is saved and loaded correctly.

- [ ] **Step 4: Run tests and verify 100% pass rate**
  Run: `python -m unittest discover -s tests`

- [ ] **Step 5: Commit**

### Task 5: Finalization

**Files:**
- Modify: `progress.md`

- [ ] **Step 1: Final verification run**
  Run `python backtest_binance.py` and `python -m unittest discover -s tests`.

- [ ] **Step 2: Update `progress.md`**
  Mark Binance automation as complete.

- [ ] **Step 3: Push to origin main**
  `git push origin main`
