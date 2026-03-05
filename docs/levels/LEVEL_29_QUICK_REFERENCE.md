# Level 29 - Options Intelligence Quick Reference

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/options` | Full options analysis for BTC | `/options` |
| `/options ETH` | Full options analysis for ETH | `/options ETH` |
| `/options SOL` | Full options analysis for SOL | `/options SOL` |
| `/maxpain` | Max pain level for BTC | `/maxpain` |
| `/maxpain ETH` | Max pain level for ETH | `/maxpain ETH` |
| `/iv` | Implied volatility for BTC | `/iv` |
| `/iv SOL` | Implied volatility for SOL | `/iv SOL` |

## Interpreting Signals

### Put/Call Ratio
| Ratio | Sentiment | Action |
|-------|-----------|--------|
| <0.5 | EXTREMELY BULLISH | ⚠️ Contrarian top signal |
| 0.5-0.7 | VERY BULLISH | Consider taking profits |
| 0.7-0.9 | MILDLY BULLISH | Bullish bias |
| 0.9-1.1 | NEUTRAL | No clear direction |
| 1.1-1.3 | MILDLY BEARISH | Bearish bias |
| 1.3-1.5 | VERY BEARISH | Consider buying dips |
| >1.5 | EXTREMELY BEARISH | ⚠️ Contrarian bottom signal |

### Max Pain
- **Near expiry (<7 days)**: Price gravitates toward max pain
- **Distance >5%**: Strong gravitational pull expected
- **Distance <2%**: Already at equilibrium

### Implied Volatility
| Condition | Meaning | Strategy |
|-----------|---------|----------|
| IV > 30d Avg | Options EXPENSIVE | Sell premium (covered calls, cash-secured puts) |
| IV < 30d Avg | Options CHEAP | Buy options for directional plays |
| IV >150% | EXTREME | High volatility expected, reduce size |
| IV <50% | LOW | Market expects calm, normal sizing |

### Gamma Exposure
| GEX | Effect | Action |
|-----|--------|--------|
| Positive | Price moves AMPLIFIED | Reduce position size, expect volatility |
| Negative | Price moves DAMPENED | Normal sizing, expect stability |
| Near zero | Neutral | No gamma effect |

## Alert Conditions

System automatically alerts on:
- ✅ P/C ratio <0.5 or >1.5 (extreme sentiment)
- ✅ Options trades >$10M (smart money)
- ✅ IV >200% (extreme volatility)
- ✅ 4-hour cooldown between alerts

## Integration Code Snippets

### Get Options Data
```python
from crypto_agent.derivatives.options_monitor import get_options_monitor

monitor = get_options_monitor()
data = monitor.get_options_data("BTC")

print(f"P/C Ratio: {data.put_call_ratio:.2f}")
print(f"Max Pain: ${data.max_pain:,.0f}")
print(f"IV: {data.iv_current*100:.1f}%")
```

### Check for Alerts
```python
alerts = monitor.check_for_alerts(data)
for alert in alerts:
    print(alert)
```

### Format Report
```python
report = monitor.format_options_report(data)
print(report)
```

### Quick Lookups
```python
max_pain = monitor.get_max_pain_only("BTC")
iv = monitor.get_iv_only("ETH")
```

## Trading Strategies

### 1. Contrarian Plays
- P/C <0.5 → Consider shorts/puts
- P/C >1.5 → Consider longs/calls

### 2. Max Pain Targeting
- Near expiry + far from max pain → Expect move toward max pain
- Set profit targets near max pain level

### 3. IV-Based Options Trading
- High IV → Sell premium (theta strategies)
- Low IV → Buy options (directional plays)

### 4. Unusual Activity Following
- Large call purchases → Bullish signal
- Large put purchases → Bearish signal
- Verify with other indicators

## Common Patterns

### Pre-Expiry Week
- Volatility increases
- Price gravitates toward max pain
- Unusual activity spikes
- **Action**: Reduce size, watch max pain

### Post-Expiry
- Volatility normalizes
- New max pain established
- Fresh positioning begins
- **Action**: Resume normal trading

### Extreme Sentiment
- P/C <0.5 often marks local tops
- P/C >1.5 often marks local bottoms
- **Action**: Fade the crowd

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Unable to fetch data" | Wait 5 minutes, check Deribit API status |
| Slow responses | Cache should make it fast, check logs |
| No alerts | Check cooldown, verify thresholds |
| Wrong symbol | Only BTC, ETH, SOL supported |

## Best Practices

1. ✅ Check options before major trades
2. ✅ Monitor P/C ratio daily
3. ✅ Watch max pain near expiry
4. ✅ Use IV for options strategy selection
5. ✅ Combine with TA for confirmation
6. ✅ Don't trade on options data alone
7. ✅ Track unusual activity for smart money signals

## Files Location

```
crypto_agent/
├── derivatives/options_monitor.py      # Core logic
├── bot/options_handlers.py             # Commands
└── tasks/options_monitor_task.py       # Scheduled monitoring
```

## Testing

```bash
# Run test suite
python test_options_monitor.py

# Expected: All checks pass ✅
```

## Next Level

**Level 30**: Multi-Analyst Debate System
- Three AI analysts debate trades
- Bull vs Bear vs Quant perspectives
- Synthesized recommendations

---

**Quick Tip**: Use `/options` before any significant trade to check market sentiment and positioning!
