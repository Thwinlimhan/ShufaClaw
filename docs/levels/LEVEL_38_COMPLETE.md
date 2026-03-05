# ✅ Level 38 Complete: Simulation Environment

## Summary

Implemented comprehensive testing framework with mock services, data generators, and scenario testing for validating bot behavior without real API calls.

## What It Does

Provides complete testing infrastructure:
- **Mock Services**: Realistic implementations of all external services
- **Data Generators**: Create price histories and market scenarios
- **Scenario Tester**: Test bot components against predefined scenarios
- **Regression Testing**: Ensure features work correctly across updates

## Files Created (4 new files)

```
crypto_agent/testing/
├── __init__.py                  (Module exports)
├── mock_services.py             (600+ lines)
├── data_generators.py           (400+ lines)
└── scenario_tester.py           (400+ lines)

test_simulation.py               (300+ lines)
```

## Mock Services

### 1. MockPriceService
- Realistic price movements using random walk
- Configurable trend and volatility
- Supports all major coins
- 24h change and volume generation

### 2. MockMarketService
- Fear & Greed index simulation
- Market overview data
- Top coins by market cap
- Configurable sentiment

### 3. MockTAService
- Technical analysis generation
- Predefined scenario support
- RSI, trend, support/resistance
- Volume and indicator data

### 4. MockDatabase
- In-memory database
- All CRUD operations
- Positions, alerts, journal, notes
- Fast and isolated

### 5. MockNewsService
- News article generation
- Sentiment analysis
- Symbol-specific filtering

### 6. MockOnChainService
- Network statistics
- Whale activity tracking
- Gas prices and fees

## Data Generators

### 1. generate_price_history()
Generate realistic OHLCV candles:
- Geometric Brownian motion
- Configurable trend and volatility
- Multiple timeframes (1h, 4h, 1d)
- Volume correlation with price moves

### 2. generate_market_scenario()
6 predefined market scenarios:
- **Bull Run**: Strong uptrend, high greed
- **Bear Market**: Strong downtrend, high fear
- **Sideways**: Range-bound, neutral
- **Volatile**: High volatility, mixed signals
- **Crash**: Sudden drop, extreme fear
- **Recovery**: Bounce from lows

### 3. generate_portfolio_scenario()
6 portfolio types:
- **Diversified**: Well-balanced
- **Concentrated**: Heavy in 1-2 assets
- **Risky**: High-risk altcoins
- **Conservative**: BTC/ETH heavy
- **Losing**: Underwater positions
- **Winning**: All positions in profit

### 4. generate_trade_setup_scenario()
5 trade setups:
- **Breakout**: Near resistance with volume
- **Pullback**: Uptrend with oversold RSI
- **Reversal**: RSI extremes
- **Range**: Clear support/resistance
- **Momentum**: Strong trend

### 5. generate_event_scenario()
4 event types:
- **Token Unlock**: Large supply release
- **Upgrade**: Protocol upgrade
- **Macro**: Fed meeting, CPI
- **Options Expiry**: Monthly expiry

## Scenario Tester

### Test Suites

1. **Trade Proposal Scenarios**
   - Tests all 5 setup types
   - Verifies correct setup detection
   - Validates entry/stop/target logic

2. **Market Scenarios**
   - Tests 6 market conditions
   - Verifies Fear & Greed accuracy
   - Validates trend detection

3. **Portfolio Scenarios**
   - Tests 6 portfolio types
   - Verifies position management
   - Validates risk calculations

4. **Alert System**
   - Tests alert creation
   - Tests alert retrieval
   - Tests alert deactivation

5. **Journal System**
   - Tests entry creation
   - Tests entry retrieval
   - Tests filtering

### Usage

```python
from crypto_agent.testing import ScenarioTester
from crypto_agent.intelligence.trade_proposer import TradeProposer

# Create tester
tester = ScenarioTester()

# Get mock services
services = tester.get_mock_services()

# Create components with mock services
proposer = TradeProposer(
    db=services['db'],
    price_service=services['price_service'],
    ta_service=services['ta_service']
)

# Run full test suite
components = {'proposer': proposer}
results = await tester.run_full_test_suite(components)

# Results
print(f"Passed: {results['total_passed']}/{results['total_tests']}")
```

## Example Usage

### Mock Price Service

```python
from crypto_agent.testing import MockPriceService

service = MockPriceService()

# Get price
btc_data = await service.get_price('BTC')
print(f"BTC: ${btc_data['price']:,.2f}")

# Set bullish trend
service.set_trend(0.03)  # 3% daily growth

# Set high volatility
service.set_volatility(0.05)  # 5% volatility

# Reset to base prices
service.reset_prices()
```

### Generate Price History

```python
from crypto_agent.testing import generate_price_history

# Generate 30 days of hourly candles
history = generate_price_history(
    symbol='BTC',
    start_price=90000,
    days=30,
    volatility=0.02,
    trend=0.01  # 1% daily growth
)

# Use for backtesting
for candle in history:
    print(f"{candle['timestamp']}: ${candle['close']:,.2f}")
```

### Market Scenarios

```python
from crypto_agent.testing import generate_market_scenario

# Generate bull run scenario
scenario = generate_market_scenario('bull_run')

# Configure services
market_service.set_fear_greed(scenario['fear_greed'])
price_service.set_trend(scenario['trend'])

# Test bot behavior
# ...
```

### Portfolio Scenarios

```python
from crypto_agent.testing import generate_portfolio_scenario

# Generate risky portfolio
scenario = generate_portfolio_scenario('risky', 10000)

# Add positions to database
for pos in scenario['positions']:
    await db.add_position(
        user_id=123,
        symbol=pos['symbol'],
        amount=pos['amount'],
        entry_price=pos['entry_price']
    )

# Test portfolio optimizer
# ...
```

## Testing Workflow

### 1. Unit Testing
```python
# Test individual components with mocks
from crypto_agent.testing import MockPriceService

service = MockPriceService()
data = await service.get_price('BTC')
assert data is not None
```

### 2. Integration Testing
```python
# Test multiple components together
tester = ScenarioTester()
services = tester.get_mock_services()

proposer = TradeProposer(
    db=services['db'],
    price_service=services['price_service'],
    ta_service=services['ta_service']
)

proposal = await proposer.generate_proposal('BTC', '4h')
assert proposal is not None
```

### 3. Scenario Testing
```python
# Test against predefined scenarios
results = await tester.test_trade_proposal_scenarios(proposer)
print(f"Passed: {results['passed']}/{results['total_tests']}")
```

### 4. Regression Testing
```python
# Run full suite before releases
results = await tester.run_full_test_suite(components)
assert results['total_failed'] == 0
```

## Benefits

### For Development
- **Fast Testing**: No API calls, instant results
- **Reproducible**: Same scenarios every time
- **Isolated**: No external dependencies
- **Comprehensive**: Test all edge cases

### For Quality Assurance
- **Regression Testing**: Catch breaking changes
- **Scenario Coverage**: Test all market conditions
- **Automated**: Run on every commit
- **Measurable**: Track test coverage

### For Debugging
- **Controlled Environment**: Reproduce bugs easily
- **Step-by-Step**: Debug without rate limits
- **Scenario Replay**: Test specific conditions
- **Fast Iteration**: Quick feedback loop

### For Learning
- **Understand Behavior**: See how bot reacts
- **Experiment Safely**: No real money at risk
- **Test Strategies**: Validate before live trading
- **Build Confidence**: Know it works

## Test Results

Run the test suite:
```bash
python test_simulation.py
```

Expected output:
```
==================================================
SIMULATION ENVIRONMENT TEST SUITE
==================================================

🧪 Testing Mock Price Service...
✅ BTC Price: $97,500.00 (+2.5%)
✅ Trend test: $97,500.00 → $102,350.00
✅ Unknown symbol handling: Correct

🧪 Testing Mock Market Service...
✅ Fear & Greed: 50 (Neutral)
✅ Market Cap: $2.50T
✅ Top 5 coins: BTC, ETH, BNB, SOL, ADA

🧪 Testing Mock TA Service...
✅ BTC Analysis: RSI=55.0, Trend=up
✅ Custom scenario: Applied correctly
✅ Clear scenarios: Working

🧪 Testing Mock Database...
✅ Add position: 0.5 BTC
✅ Create alert: ID=1
✅ Journal entry: Test entry
✅ Clear all: Working

🧪 Testing Price History Generator...
✅ Generated 720 candles
✅ Uptrend: $90,000 → $98,500
✅ Downtrend: $100,000 → $92,000

🧪 Testing Market Scenario Generator...
✅ Bull Run: F&G=75, Trend=+3.00%
✅ Bear Market: F&G=25, Trend=-2.00%
✅ Sideways: F&G=50, Trend=+0.00%
✅ Volatile: F&G=45, Trend=+0.00%
✅ Crash: F&G=10, Trend=-10.00%
✅ Recovery: F&G=55, Trend=+4.00%

🧪 Testing Portfolio Scenario Generator...
✅ Diversified Portfolio: 6 positions, Risk=medium
✅ Concentrated Portfolio: 2 positions, Risk=low
✅ High-Risk Portfolio: 5 positions, Risk=high
✅ Conservative Portfolio: 2 positions, Risk=low
✅ Losing Portfolio: 5 positions, Risk=high
✅ Winning Portfolio: 4 positions, Risk=medium

🧪 Testing Scenario Tester...
[Full scenario test output...]

==================================================
✅ ALL TESTS PASSED
==================================================
```

## Integration

### Add to CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run simulation tests
        run: python test_simulation.py
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running simulation tests..."
python test_simulation.py

if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
```

## Use Cases

### 1. Feature Development
Test new features without API calls:
```python
# Develop new feature
proposer = TradeProposer(mock_db, mock_price, mock_ta)

# Test immediately
proposal = await proposer.generate_proposal('BTC', '4h')
assert proposal.setup_type == SetupType.BREAKOUT
```

### 2. Bug Reproduction
Reproduce bugs with specific scenarios:
```python
# Set up exact conditions that caused bug
ta_service.set_scenario('BTC', {
    'rsi': 25,
    'trend': 'down',
    'support': 90000
})

# Reproduce bug
proposal = await proposer.generate_proposal('BTC', '4h')
# Debug...
```

### 3. Performance Testing
Test with large datasets:
```python
# Generate 1 year of data
history = generate_price_history('BTC', 90000, days=365)

# Test backtester performance
start = time.time()
results = await backtester.run(history)
duration = time.time() - start

print(f"Processed {len(history)} candles in {duration:.2f}s")
```

### 4. Strategy Validation
Test trading strategies:
```python
# Test strategy in bull market
scenario = generate_market_scenario('bull_run')
# Configure and test...

# Test same strategy in bear market
scenario = generate_market_scenario('bear_market')
# Configure and test...

# Compare results
```

## Status

✅ Mock services implemented (6 services)
✅ Data generators created (5 generators)
✅ Scenario tester built
✅ Test suite complete
✅ Documentation complete
⏳ CI/CD integration pending

---

**Next**: Level 39 - Personal Crypto Academy

## Progress Update

**Completed**: 38/40 levels (95%)

**Remaining**:
- Level 39: Personal Crypto Academy
- Level 40: Unified Intelligence Hub

**Achievement**: Built a complete testing framework enabling fast, reliable, and comprehensive testing without external dependencies.
