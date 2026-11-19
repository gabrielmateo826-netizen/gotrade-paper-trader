## 3-Broker Upgrade Project Plan

### Project Overview
Implement a comprehensive multi-broker trading system upgrade for GoTrade Paper Trading Arena, integrating three brokers: GoTrade (existing US ETFs), Binance (crypto), and DragonFi (Philippine equities).

### Current State
- **GoTrade**: Automated signal generation + Telegram alerts + Exposure Coach ($42.50 / $21.25)
- **Tracker.py**: Current engine with VIX gate, Exposure Coach, and daily logging
- **README.md**: Dynamic scoreboard with strategy performance metrics

### Upgrade Requirements

#### Phase 1: GoTrade Optimization (CURRENT STATE)
- Keep existing automated signal + Telegram alert + Exposure Coach tranche sizing ($42.50 / $21.25)
- Ensure backward compatibility with current RSI-2 and Dual-Momentum strategies
- Maintain VIX gate (VIX < 25.0) and drawdown circuit breaker (-$8.50)

#### Phase 2: Binance Integration (NEW)
- Create `binance_executor.py` lightweight ccxt spot module
- Use environment variables for API keys: `BINANCE_API_KEY`, `BINANCE_SECRET_KEY`
- Default to Binance Spot Testnet / demo trading mode
- Implement standard order execution with paper trading simulation
- Add USDT/BTC trading pairs support

#### Phase 3: DragonFi Integration (NEW)
- Add capital-gated signal filter for PSE alerts
- Filter condition: PHP capital >= 25,000 required for activation
- Suppress signals when PHP capital < 25,000
- Maintain existing GoTrade signals unchanged

### Technical Specifications

#### File Structure
- `tracker.py`: Core engine (unchanged)
- `binance_executor.py`: New Binance integration (35-40 lines)
- `README.md`: Enhanced with broker status indicators
- `trades.csv`: All trades from all brokers
- `tests/test_trading_engine.py`: New unit tests (6 tests implemented)

#### Environment Variables
```
# Binance Configuration
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key
BINANCE_SANDBOX=true  # Default for demo trading

# DragonFi Configuration  
PHP_CAPITAL=25000  # Minimum PHP capital for signal activation
```

#### Broker Signal Flow
1. **GoTrade**: Continue existing signal detection (RSI-2, Dual-Momentum)
2. **Binance**: Monitor USDT/BTC pairs when GoTrade signals detected
3. **DragonFi**: Validate PHP capital >= 25,000 before executing PSE alerts

#### Testing Requirements
- VIX gate test: Verify VIX < 25.0 requirement
- Exposure Coach test: Confirm 50% reduction after two consecutive losses
- Binance sandbox test: Validate demo trading mode
- DragonFi capital gate test: Confirm PHP >= 25,000 requirement

### Success Criteria
- [ ] Binance module operational in testnet mode
- [ ] DragonFi capital gate filtering implemented
- [ ] All existing tests passing
- [ ] Backward compatibility maintained
- [ ] Integration with existing GoTrade engine

### Implementation Priority
1. **Binance**: Lightweight ccxt module (fastest integration)
2. **DragonFi**: Capital gate filter (simple condition)
3. **Enhancements**: Maintain and improve existing functionality

### Current Phase Status
**Phase 1 (GoTrade)**: ✅ COMPLETE - Existing functionality preserved
**Phase 2 (Binance)**: ⏳ PENDING - Module creation in progress
**Phase 3 (DragonFi)**: ⏳ PENDING - Capital gate implementation

### Risk Assessment
- **Medium**: Integration changes could break existing GoTrade signals
- **Low**: Binance testnet isolation reduces risk
- **Low**: DragonFi gate is simple conditional logic

### Next Steps
1. Create `binance_executor.py` module
2. Implement DragonFi capital gate logic
3. Update tracker.py to include new broker integrations
4. Run comprehensive test suite
5. Deploy with GoNoChangesToMain branch