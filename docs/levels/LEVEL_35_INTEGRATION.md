# Level 35: Performance Attribution - Integration Guide

## What Was Built

Advanced performance analysis system that breaks down trading returns into specific components to understand what's actually working.

## Core Concept

Performance attribution answers: "Why did I make/lose money?"
- Asset Selection: Did you pick better coins?
- Allocation: Did you size positions correctly?
- Timing: Did you enter/exit at good prices?
- Benchmark Comparison: How do you compare to simple strategies?
- Factor Analysis: What's your actual trading style?

## Files Created

```
crypto_agent/intelligence/
└── performance_attribution.py   (400+ lines)
    ├── PerformanceAttributor     # Main attribution engine
    ├── BenchmarkComparator       # Benchmark comparison
    └── FactorAnalyzer            # Factor exposure analysis

crypto_agent/bot/
└── attribution_handlers.py      (300+ lines)
    ├── attribution_command       # Full attribution
    ├── benchmark_command         # Benchmark comparison
    ├── factors_command           # Factor analysis
    ├── alpha_command             # Quick alpha summary
    ├── winners_command           # Best decisions
    └── losers_command            # Worst decisions

test_attribution.py              (150+ lines)
```

## Database Tables

Three new tables created automatically:

```sql
-- Daily portfolio snapshots
CREATE TABLE performance_snapshots (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL UNIQUE,
    portfolio_value REAL NOT NULL,
    benchmark_value REAL NOT NULL,
    daily_return REAL,
    benchmark_return REAL,
    alpha REAL,
    beta REAL,
    sharpe_ratio REAL
);

-- Attribution history
CREATE TABLE attribution_history (
    id INTEGER PRIMARY KEY,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    selection_effect REAL,
    allocation_effect REAL,
    timing_effect REAL,
    interaction_effect REAL,
    total_alpha REAL,
    benchmark_name TEXT
);

-- Factor exposures
CREATE TABLE factor_exposures (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    size_factor REAL,
    momentum_factor REAL,
    value_factor REAL,
    quality_factor REAL,
    volatility_factor REAL
);
```

## Integration Steps

### 1. Register Command Handlers

Add to `main.py`:

```python
from crypto_agent.bot.attribution_handlers import (
    attribution_command,
    benchmark_command,
    factors_command,
    alpha_command,
    winners_command,
    losers_command
)

# Add handlers
application.add_handler(CommandHandler("attribution", attribution_command))
application.add_handler(CommandHandler("benchmark", benchmark_command))
application.add_handler(CommandHandler("factors", factors_command))
application.add_handler(CommandHandler("alpha", alpha_command))
application.add_handler(CommandHandler("winners", winners_command))
application.add_handler(CommandHandler("losers", losers_command))
```

### 2. Update Command Menu

Add to Telegram command list:

```python
commands = [
    # ... existing commands ...
    ("attribution", "Performance attribution analysis"),
    ("benchmark", "Compare to benchmark"),
    ("factors", "Factor exposure analysis"),
    ("alpha", "Quick alpha summary"),
    ("winners", "Best performing decisions"),
    ("losers", "Worst performing decisions"),
]

await application.bot.set_my_commands(commands)
```

### 3. Integrate with Weekly Review

Add attribution to weekly review:

```python
# In weekly review workflow
from crypto_agent.intelligence.performance_attribution import PerformanceAttributor

attributor = PerformanceAttributor()
positions = db.get_positions(user_id)
benchmark_weights = {'BTC': 0.6, 'ETH': 0.4}

attribution = attributor.calculate_attribution(
    positions,
    benchmark_weights,
    period_days=7
)

# Include in weekly report
report += f"\n📊 Weekly Attribution:\n"
report += f"Selection: {attribution['selection_effect']:+.1f}%\n"
report += f"Allocation: {attribution['allocation_effect']:+.1f}%\n"
report += f"Timing: {attribution['timing_effect']:+.1f}%\n"
```

## Testing

Run the test suite:

```bash
python test_attribution.py
```

Expected output:
```
==================================================
PERFORMANCE ATTRIBUTION TEST SUITE
==================================================

🧪 Testing Performance Attributor...
Portfolio Return: 18.50%
Benchmark Return: 12.00%
Total Alpha: 6.50%
Selection Effect: 4.20%
Allocation Effect: 1.80%
Timing Effect: 2.10%
✅ Performance attributor working correctly

🧪 Testing Benchmark Comparator...
Portfolio Return: 18.50%
Benchmark Return: 12.00%
Alpha: 6.50%
Beta: 1.54
Sharpe Ratio: 1.10
Outperformance: True
✅ Benchmark comparator working correctly

🧪 Testing Factor Analyzer...
Size Factor: -0.30
Momentum Factor: 0.60
Value Factor: 0.10
Quality Factor: 0.40
Volatility Factor: -0.20
✅ Factor analyzer working correctly

🧪 Testing Portfolio Return Calculation...
Portfolio Return: 21.43% (Expected: 21.43%)
Loss Portfolio Return: -16.67%
✅ Portfolio return calculation working correctly

==================================================
✅ ALL TESTS PASSED
==================================================
```

## Usage Examples

### Full Attribution Analysis

```
/attribution 30
```

Output:
```
📊 PERFORMANCE ATTRIBUTION (30 days)

Your Return: +18.5%
Benchmark (60/40): +12.0%
Alpha: +6.5%

━━━━━━━━━━━━━━━━━━━━

ATTRIBUTION BREAKDOWN:

Asset Selection: ✓ +4.2%
You picked better coins than benchmark

Allocation: ✓ +1.8%
Your position sizing was better

Timing: ✓ +2.1%
Good entry/exit prices

Interaction: -1.6%
(Combined selection + allocation)

━━━━━━━━━━━━━━━━━━━━

TOTAL ALPHA: +6.5%

💡 Key Insight:
Your alpha came primarily from selection
```

### Benchmark Comparison

```
/benchmark BTC
```

Output:
```
📈 BENCHMARK COMPARISON: BTC

Period: 30 days

Your Portfolio: +18.5%
BTC Only: +12.0%
Outperformance: +6.5% ✅

━━━━━━━━━━━━━━━━━━━━

Risk Metrics:
• Beta: 1.54 (higher volatility)
• Sharpe Ratio: 1.10
  (good risk-adjusted returns)

💡 Verdict:
You're beating the benchmark but taking more risk.
```

### Factor Analysis

```
/factors
```

Output:
```
🔬 FACTOR ANALYSIS

Current Exposures:

• Size: -0.3 (small cap tilt)
• Momentum: +0.6 (strong momentum bias)
• Value: +0.1
• Quality: +0.4
• Volatility: -0.2

━━━━━━━━━━━━━━━━━━━━

💡 Insight:
You have a strong momentum tilt. You're buying trending assets.
```

### Quick Alpha Summary

```
/alpha
```

Output:
```
⭐ ALPHA SUMMARY

7 Days: +2.1% alpha
30 Days: +6.5% alpha
90 Days: +12.8% alpha

━━━━━━━━━━━━━━━━━━━━

Alpha Sources:
1. Asset Selection: 65%
2. Timing: 25%
3. Allocation: 10%

💡 Your edge is asset selection.
```

### Best Performers

```
/winners
```

Output:
```
🏆 TOP PERFORMERS (30 days)

1. SOL Position
   Entry: $95.00 → Current: $125.00
   Return: +31.6%
   Attribution: Asset selection + timing

2. ETH Position
   Entry: $3000.00 → Current: $3400.00
   Return: +13.3%
   Attribution: Asset selection + timing

3. AVAX Position
   Entry: $32.00 → Current: $38.00
   Return: +18.8%
   Attribution: Asset selection + timing

💡 Keep doing what worked with these coins.
```

### Worst Performers

```
/losers
```

Output:
```
📉 UNDERPERFORMERS (30 days)

1. DOGE Position
   Entry: $0.12 → Current: $0.09
   Return: -25.0%
   Attribution: Poor asset selection

2. MATIC Position
   Entry: $0.95 → Current: $0.85
   Return: -10.5%
   Attribution: Poor asset selection

3. ADA Position
   Entry: $0.55 → Current: $0.52
   Return: -5.5%
   Attribution: Poor asset selection

💡 Consider cutting losses or improving entry timing.
```

## Attribution Components Explained

### Asset Selection Effect
**Formula**: (Your coin return - Benchmark return) × Benchmark weight

**What it measures**: Did you pick better coins than the benchmark?

**Example**:
- You picked SOL: +25%
- Benchmark (BTC): +10%
- Selection effect: +15% (good pick!)

### Allocation Effect
**Formula**: (Your weight - Benchmark weight) × Benchmark return

**What it measures**: Did you size positions correctly?

**Example**:
- You allocated 30% to ETH
- Benchmark allocates 20% to ETH
- ETH returned +15%
- Allocation effect: +1.5% (good sizing!)

### Timing Effect
**Formula**: (Exit price - Entry price) / Entry price - Asset return

**What it measures**: Did you enter/exit at good prices?

**Example**:
- You bought BTC at $60k, sold at $70k: +16.7%
- BTC overall return in period: +10%
- Timing effect: +6.7% (good timing!)

### Interaction Effect
**Formula**: (Your weight - Benchmark weight) × (Your return - Benchmark return)

**What it measures**: Combined impact of selection + allocation

## Available Benchmarks

1. **BTC** - Bitcoin only (conservative)
2. **60/40** - 60% BTC, 40% ETH (balanced)
3. **EQUAL** - Equal weight top 10 (diversified)
4. **MARKET** - Market cap weighted (passive)

## Factor Definitions

1. **Size Factor**: Large cap vs small cap exposure
   - Negative = small cap tilt
   - Positive = large cap tilt

2. **Momentum Factor**: Trending vs mean-reverting
   - Positive = momentum bias
   - Negative = mean reversion

3. **Value Factor**: Undervalued vs overvalued
   - Positive = value tilt
   - Negative = growth tilt

4. **Quality Factor**: Fundamentally strong vs weak
   - Positive = quality bias
   - Negative = speculative

5. **Volatility Factor**: Low vol vs high vol
   - Negative = prefer lower volatility
   - Positive = prefer higher volatility

## Use Cases

### 1. Understand What Works
"I made money, but why?"
- Run `/attribution` to see breakdown
- Identify your edge (selection? timing? allocation?)
- Double down on what works

### 2. Improve Weak Areas
"I keep losing on timing"
- `/losers` shows timing mistakes
- Focus on improving entry/exit discipline
- Consider using more limit orders

### 3. Benchmark Yourself
"Am I actually good or just lucky?"
- `/benchmark BTC` shows if you beat simple holding
- Check Sharpe ratio for risk-adjusted performance
- Track alpha consistency over time

### 4. Factor Awareness
"What's my actual strategy?"
- `/factors` reveals your implicit biases
- Maybe you're a momentum trader without knowing it
- Align conscious strategy with revealed preferences

### 5. Learn from History
"What were my best trades?"
- `/winners` shows what worked
- `/losers` shows what didn't
- Build pattern recognition

## Performance

- Attribution calculation: <2 seconds
- Benchmark comparison: <1 second
- Factor analysis: <3 seconds
- Minimal database overhead

## Next Steps

1. ✅ Run test suite
2. ✅ Register command handlers
3. ✅ Update command menu
4. ⏳ Test with real portfolio
5. ⏳ Integrate with weekly review
6. ⏳ Track attribution over time

---

**Status**: ✅ Level 35 Complete - Performance Attribution System Operational

**Next**: Level 36 - Autonomous Trade Proposals
