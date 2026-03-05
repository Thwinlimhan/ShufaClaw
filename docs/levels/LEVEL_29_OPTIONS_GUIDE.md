# Level 29 - Options Intelligence Guide

## Overview

Level 29 adds comprehensive options market monitoring using Deribit's free public API. This provides insights into market sentiment, positioning, and potential price targets through options data.

## Features Implemented

### 1. Options Data Monitoring
- **Put/Call Ratio**: Sentiment indicator
  - <0.7: Very bullish
  - 0.7-0.9: Mildly bullish
  - 1.1-1.3: Mildly bearish
  - >1.3: Very bearish
  - Extremes (<0.5 or >1.5) are contrarian signals

- **Max Pain**: Strike where most options expire worthless
  - Price tends to gravitate toward max pain near expiry
  - Useful for predicting short-term price action

- **Implied Volatility (IV)**: Market's expectation of future volatility
  - IV > Historical Vol: Options expensive (sell premium)
  - IV < Historical Vol: Options cheap (buy options)

- **Gamma Exposure (GEX)**: Impact on price volatility
  - Positive GEX: Price moves amplified
  - Negative GEX: Price moves dampened

- **Unusual Activity Detection**: Large trades and IV spikes
  - Alerts on >$5M volume
  - Alerts on IV >150%

### 2. Telegram Commands

#### `/options [symbol]`
Full options intelligence report for BTC, ETH, or SOL.

```
/options          # BTC options data
/options ETH      # ETH options data
/options SOL      # SOL options data
```

**Output includes:**
- Current price
- Put/Call ratio with sentiment
- Max pain level and distance
- IV metrics and comparison
- Gamma exposure
- Unusual activity alerts

#### `/maxpain [symbol]`
Quick max pain lookup.

```
/maxpain          # BTC max pain
/maxpain ETH      # ETH max pain
```

Shows current price, max pain level, and distance.

#### `/iv [symbol]`
Quick implied volatility check.

```
/iv               # BTC IV
/iv ETH           # ETH IV
```

Shows current IV, 30-day average, and whether options are expensive or cheap.

### 3. Automated Monitoring

The system checks options data every 4 hours and sends alerts for:
- Extreme put/call ratios (contrarian signals)
- Large unusual options trades (>$10M)
- Extreme IV levels (>200%)

Alerts have a 4-hour cooldown to prevent spam.

### 4. Morning Briefing Integration

Options data is included in the morning briefing:
- Put/Call ratio and sentiment
- Max pain level
- Current IV

## Technical Details

### Data Source
- **Deribit Public API**: No authentication required
- **Endpoints used**:
  - `/get_index_price`: Current spot price
  - `/get_book_summary_by_currency`: Options book data

### Caching
- Options data cached for 1 hour
- Reduces API calls and improves response time

### Supported Symbols
- BTC (Bitcoin)
- ETH (Ethereum)
- SOL (Solana)

## Usage Examples

### Check BTC Options Before Trading
```
/options BTC
```

This shows you:
- Market sentiment (bullish/bearish)
- Where price might gravitate (max pain)
- Whether options are expensive or cheap
- Any unusual large trades

### Monitor Max Pain Near Expiry
```
/maxpain BTC
```

If expiry is approaching and price is far from max pain, expect gravitational pull toward that level.

### Assess Volatility for Options Trading
```
/iv ETH
```

If IV is high vs historical, consider selling premium (covered calls, cash-secured puts).
If IV is low, consider buying options for directional plays.

## Integration with Other Modules

### With Technical Analysis
Combine options sentiment with TA:
- Bullish TA + Low P/C ratio = Strong buy signal
- Bearish TA + High P/C ratio = Strong sell signal

### With Portfolio Management
Use max pain for:
- Setting profit targets near expiry
- Avoiding entries far from max pain before expiry

### With Risk Management
Use GEX for position sizing:
- High positive GEX = Reduce size (volatile)
- Negative GEX = Normal size (stable)

## Interpreting Signals

### Contrarian Signals
- **P/C < 0.5**: Extreme bullishness often marks tops
- **P/C > 1.5**: Extreme bearishness often marks bottoms

### Confirmation Signals
- **P/C + Max Pain**: If both point same direction, higher confidence
- **P/C + IV**: High IV + extreme P/C = market uncertainty

### Timing Signals
- **Max Pain Distance**: >5% with <7 days to expiry = strong pull
- **IV Spike**: Sudden IV increase = event expected

## Best Practices

1. **Check Before Major Trades**
   - Always check options data before significant positions
   - Extreme sentiment can signal reversals

2. **Monitor Near Expiry**
   - Last week before monthly expiry is most important
   - Max pain gravity strongest in final 3 days

3. **Combine with Other Data**
   - Don't use options data in isolation
   - Confirm with TA, on-chain, and macro data

4. **Watch for Unusual Activity**
   - Large trades often precede moves
   - Smart money positioning shows up here first

5. **Use IV for Options Strategy**
   - High IV: Sell premium strategies
   - Low IV: Buy options for leverage

## Troubleshooting

### "Unable to fetch options data"
- Deribit API may be temporarily down
- Check internet connection
- Try again in a few minutes

### No unusual activity showing
- This is normal - unusual activity is rare
- Only shows when significant trades occur

### Max pain seems wrong
- Max pain calculation uses current open interest
- Can change rapidly as positions open/close
- Most accurate near expiry

## Next Steps

After mastering Level 29, you can:
1. **Level 30**: Multi-Analyst Debate System
2. **Level 31**: Event Impact Predictor
3. Integrate options signals into trade proposals
4. Build options-based trading strategies

## Code Structure

```
crypto_agent/
├── derivatives/
│   ├── __init__.py
│   └── options_monitor.py       # Core options logic
├── bot/
│   └── options_handlers.py      # Telegram commands
└── tasks/
    └── options_monitor_task.py  # Scheduled monitoring
```

## API Reference

### OptionsMonitor Class

```python
from crypto_agent.derivatives.options_monitor import get_options_monitor

monitor = get_options_monitor()

# Get full options data
data = monitor.get_options_data("BTC")

# Quick lookups
max_pain = monitor.get_max_pain_only("BTC")
iv = monitor.get_iv_only("BTC")

# Format report
report = monitor.format_options_report(data)

# Check for alerts
alerts = monitor.check_for_alerts(data)
```

### OptionsData Structure

```python
@dataclass
class OptionsData:
    symbol: str                    # BTC, ETH, SOL
    put_call_ratio: float          # P/C ratio
    max_pain: float                # Max pain strike
    current_price: float           # Current spot price
    iv_current: float              # Current IV (0-1 scale)
    iv_30d_avg: float              # 30-day average IV
    gamma_exposure: float          # GEX value
    unusual_activity: List[Dict]   # Unusual trades
    timestamp: datetime            # Data timestamp
```

## Resources

- [Deribit API Docs](https://docs.deribit.com/)
- [Options Greeks Explained](https://www.investopedia.com/trading/using-the-greeks-to-understand-options/)
- [Max Pain Theory](https://www.investopedia.com/terms/m/maxpain.asp)
- [Implied Volatility Guide](https://www.investopedia.com/terms/i/iv.asp)

## Support

For issues or questions:
1. Check logs: `crypto_agent/logs/`
2. Verify Deribit API is accessible
3. Test with `/options BTC` command
4. Check cache is working (responses should be fast)

---

**Level 29 Complete!** You now have professional-grade options intelligence integrated into your crypto agent.
