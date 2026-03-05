# Market Orchestrator - Setup Guide

## What Is This?

The Market Orchestrator is the **master brain** of your crypto bot. It monitors market conditions and intelligently adapts all bot systems in real-time.

Think of it as your bot's "autopilot" that adjusts its behavior based on whether the market is bullish, bearish, volatile, or ranging.

---

## 🎯 What It Does

### Automatic Market Regime Detection

Every hour, the orchestrator analyzes the market and classifies it into one of 4 regimes:

**1. BULL TREND 🐂**
- BTC above 50-day moving average
- Fear & Greed Index > 60
- 3+ consecutive green days
- **Bot becomes:** Optimistic, relaxed alerts, focuses on momentum

**2. BEAR TREND 🐻**
- BTC below 50-day moving average
- Fear & Greed Index < 40
- 3+ consecutive red days
- **Bot becomes:** Cautious, heightened alerts, focuses on risk

**3. HIGH VOLATILITY ⚡**
- ATR (volatility) > 2x normal
- Multiple 5%+ daily swings
- **Bot becomes:** Alert mode, scans every 2 minutes, warns about volatility

**4. RANGING 📊**
- Low volatility, tight price range
- Volume declining
- **Bot becomes:** Relaxed, scans less often, focuses on breakouts

### Adaptive Behavior

Based on the regime, your bot automatically adjusts:

| Setting | Bull | Bear | High Vol | Ranging |
|---------|------|------|----------|---------|
| Alert Sensitivity | Relaxed | Heightened | High | Normal |
| Scan Frequency | 5 min | 3 min | 2 min | 10 min |
| Scanner Focus | Momentum | Risk | Volatility | Breakouts |
| Briefing Tone | Optimistic | Cautious | Alert | Neutral |
| Message Throttle | Normal | Normal | Increased | Reduced |

### Operating Modes

You can manually override with 4 modes:

**NORMAL 🔵** - Standard operation, adapts to regime
**AGGRESSIVE 🔴** - Lower thresholds, more scans, all opportunities (auto-reverts in 4 hours)
**QUIET 🔇** - Critical alerts only, minimal messages (auto-reverts in 4 hours)
**NIGHT 🌙** - Critical only (auto-enabled 12am-7am anyway)

### Priority System

All notifications are filtered by priority:

- **CRITICAL** - Portfolio down 10%+, liquidation risk, exchange hack
- **HIGH** - Coin down 5%+ in hour, major technical break, big news
- **MEDIUM** - Alert triggered, opportunity found, scanner finding
- **LOW** - Weekly summaries, general market commentary

**Filtering rules:**
- Night hours (12am-7am): Critical only
- Busy hours (9am-5pm): Critical + High
- Other times: All priorities
- Quiet mode: Critical only
- Aggressive mode: All priorities

---

## 📦 What Was Created

**3 New Files:**

1. `crypto_agent/core/orchestrator.py` (600+ lines)
   - Main orchestrator class
   - Regime detection logic
   - Behavior adaptation
   - Priority filtering

2. `crypto_agent/bot/orchestrator_handlers.py` (300+ lines)
   - Telegram command handlers
   - `/regime`, `/orchestrator`, `/mode` commands

3. Database functions added to `crypto_agent/storage/workflow_db.py`
   - `init_orchestrator_tables()`
   - `save_market_regime()`
   - `log_orchestrator_decision()`

**2 New Database Tables:**
- `market_regimes` - Track regime changes over time
- `orchestrator_decisions` - Log all orchestrator decisions

---

## 🚀 Setup (4 Steps)

### Step 1: Initialize Database Tables

Run this command once:
```bash
python -c "from crypto_agent.storage import workflow_db, database; workflow_db.init_orchestrator_tables(database.get_connection())"
```

This creates the 2 new database tables.

### Step 2: Register Command Handlers

Open `crypto_agent/main.py` and add:

**Import (at the top):**
```python
from crypto_agent.bot import orchestrator_handlers
from crypto_agent.core.orchestrator import orchestrator
```

**Commands (where other handlers are):**
```python
# Orchestrator commands
application.add_handler(CommandHandler("regime", orchestrator_handlers.regime_command))
application.add_handler(CommandHandler("orchestrator", orchestrator_handlers.orchestrator_command))
application.add_handler(CommandHandler("mode", orchestrator_handlers.mode_command))
application.add_handler(CommandHandler("settings", orchestrator_handlers.settings_command))
application.add_handler(CommandHandler("prioritytest", orchestrator_handlers.priority_test_command))
application.add_handler(CommandHandler("claudeprompt", orchestrator_handlers.claude_prompt_command))
```

### Step 3: Set Up Hourly Regime Check

Add this scheduler (before `application.run_polling()`):

```python
# Orchestrator - check regime every hour
async def check_regime(context):
    """Check and update market regime."""
    regime_changed = await orchestrator.update_regime()
    
    if regime_changed:
        # Optionally notify user of regime change
        report = orchestrator.get_regime_report()
        await context.bot.send_message(
            chat_id=config.MY_TELEGRAM_ID,
            text=f"⚠️ **REGIME CHANGE**\n\n{report}",
            parse_mode='Markdown'
        )

# Check regime every hour
job_queue = application.job_queue
job_queue.run_repeating(check_regime, interval=3600, first=10)

# Also check mode expiry every 30 minutes
async def check_mode_expiry(context):
    orchestrator.check_mode_expiry()

job_queue.run_repeating(check_mode_expiry, interval=1800, first=60)
```

### Step 4: Integrate with Existing Systems

**For workflows** - Use orchestrator scan frequency:
```python
scan_freq = orchestrator.get_scan_frequency()
```

**For alerts** - Use orchestrator sensitivity:
```python
sensitivity = orchestrator.get_alert_threshold()
```

**For notifications** - Check priority:
```python
from crypto_agent.core.orchestrator import Priority
if orchestrator.should_send_notification(Priority.MEDIUM):
    # Send the notification
```

**For Claude** - Add regime context:
```python
system_prompt_addition = orchestrator.get_claude_system_prompt_addition()
```

---

## ✅ Test It

1. **Start your bot:**
   ```
   python crypto_agent/main.py
   ```

2. **Check current regime:**
   ```
   /regime
   ```
   Should analyze market and show regime

3. **Check orchestrator status:**
   ```
   /orchestrator
   ```
   Should show mode, regime, and recent decisions

4. **Change mode:**
   ```
   /mode aggressive
   ```
   Should activate aggressive mode for 4 hours

5. **Test priority system:**
   ```
   /prioritytest critical
   /prioritytest low
   ```
   Should show if notifications would be sent

---

## 📱 Commands Reference

### `/regime`
Shows current market regime analysis:
```
🌡️ MARKET REGIME ANALYSIS

Current: 🐂 BULL TREND (High Confidence)

Supporting factors:
• BTC above 50-day SMA ($65,000)
• Fear & Greed: 68 (Greed)
• 5 green days
• ATR 1.2x historical

Bot behavior:
• Alert threshold: relaxed
• Scan frequency: Every 5 min
• Scanner focus: momentum
• Briefing tone: optimistic

In effect since: Feb 19 (4 days)
Previous regime: Ranging (14 days)
```

### `/orchestrator`
Shows orchestrator status and recent decisions:
```
🧠 ORCHESTRATOR STATUS

Mode: 🔵 NORMAL
Current Regime: Bull Trend
Confidence: 85%

Decisions (Last 24h): 3

• 03:00 PM - Regime changed to bull_trend
• 09:00 AM - Mode reverted to normal
• 08:00 AM - Scan frequency adjusted

Active Settings:
• Scan frequency: 5 min
• Alert sensitivity: relaxed
• Message throttle: normal
```

### `/mode [type]`
Change operating mode:
```
/mode aggressive  - Lower thresholds, more scans
/mode quiet       - Critical only, minimal messages
/mode normal      - Standard operation
/mode night       - Critical only
```

### `/settings`
Show current settings:
```
⚙️ CURRENT SETTINGS

Regime: Bull Trend
Mode: Normal

Active Configuration:
• Alert sensitivity: relaxed
• Scan frequency: Every 5 min
• Scanner focus: momentum
• Briefing tone: optimistic
• Portfolio advice: ride_trends
• Message throttle: normal
```

### `/prioritytest [level]`
Test if a notification would be sent:
```
/prioritytest critical
/prioritytest high
/prioritytest medium
/prioritytest low
```

### `/claudeprompt`
Show Claude system prompt addition (for debugging):
```
🤖 CLAUDE SYSTEM PROMPT ADDITION

Current regime: Bull Trend

```
MARKET CONTEXT: The market is in a bullish trend.
Be optimistic but remind about taking profits.
Focus on identifying continuation setups and momentum plays.
Warn against FOMO and overleveraging.
```
```

---

## 🎨 How It Works

### Regime Detection Flow

```
Every Hour
    ↓
Analyze 6 Factors:
  1. BTC vs 50-day SMA
  2. Fear & Greed Index
  3. Consecutive green/red days
  4. Volatility (ATR)
  5. Recent price swings
  6. Price range tightness
    ↓
Score Each Regime:
  Bull: +2 +2 +2 = 6
  Bear: +0 +0 +0 = 0
  High Vol: +0 +0 +0 = 0
  Ranging: +0 +0 +0 = 0
    ↓
Select Highest Score
    ↓
Apply Regime Settings:
  - Alert sensitivity: relaxed
  - Scan frequency: 5 min
  - Scanner focus: momentum
  - Briefing tone: optimistic
    ↓
Log to Database
    ↓
Notify if Changed
```

### Priority Filtering Flow

```
Notification Created
    ↓
Assign Priority:
  - Portfolio down 10%? → CRITICAL
  - Coin down 5%? → HIGH
  - Alert triggered? → MEDIUM
  - Weekly summary? → LOW
    ↓
Check Current Mode:
  - Quiet mode? → Only CRITICAL
  - Night mode? → Only CRITICAL
  - Normal mode? → Continue
    ↓
Check Time of Day:
  - 12am-7am? → Only CRITICAL
  - 9am-5pm? → CRITICAL + HIGH
  - Other? → All priorities
    ↓
Send or Block
```

---

## 🔥 Real-World Examples

### Example 1: Bull Market

**Market Conditions:**
- BTC at $70,000 (above $65,000 SMA)
- Fear & Greed: 72 (Greed)
- 5 consecutive green days
- Low volatility

**Orchestrator Response:**
- Regime: BULL TREND 🐂
- Scan frequency: Every 5 minutes
- Alert sensitivity: Relaxed
- Scanner focus: Momentum opportunities
- Briefing tone: "Market is strong, look for continuation"
- Portfolio advice: "Ride the trend, consider taking some profits"

**User Experience:**
- Fewer false alarm alerts
- More momentum opportunity notifications
- Optimistic morning briefings
- Suggestions to let winners run

### Example 2: Bear Market

**Market Conditions:**
- BTC at $58,000 (below $65,000 SMA)
- Fear & Greed: 28 (Fear)
- 4 consecutive red days
- Moderate volatility

**Orchestrator Response:**
- Regime: BEAR TREND 🐻
- Scan frequency: Every 3 minutes
- Alert sensitivity: Heightened
- Scanner focus: Risk warnings and short setups
- Briefing tone: "Market is weak, protect capital"
- Portfolio advice: "Consider reducing risk, tighten stops"

**User Experience:**
- More frequent risk warnings
- Alerts trigger more easily
- Cautious morning briefings
- Suggestions to reduce position sizes

### Example 3: High Volatility

**Market Conditions:**
- BTC swinging 7% daily
- ATR 2.5x normal
- Multiple 5%+ moves in past week
- Fear & Greed: 55 (Neutral)

**Orchestrator Response:**
- Regime: HIGH VOLATILITY ⚡
- Scan frequency: Every 2 minutes
- Alert sensitivity: High
- Scanner focus: Volatility warnings
- Briefing tone: "Market is choppy, be careful"
- Portfolio advice: "Widen stops, reduce position sizes"

**User Experience:**
- Very frequent updates
- Volatility warnings
- Alert briefings
- Suggestions to adjust risk management

### Example 4: Ranging Market

**Market Conditions:**
- BTC between $66,000-$68,000 for 10 days
- Low volume
- Tight 3% range
- Fear & Greed: 50 (Neutral)

**Orchestrator Response:**
- Regime: RANGING 📊
- Scan frequency: Every 10 minutes
- Alert sensitivity: Normal
- Scanner focus: Breakout setups
- Briefing tone: "Market is quiet, watch for breakout"
- Portfolio advice: "Good time to accumulate"

**User Experience:**
- Fewer notifications (less happening)
- Shorter morning briefings
- Focus on breakout opportunities
- Suggestions to accumulate positions

---

## 🐛 Troubleshooting

### Regime shows "Unknown"

**Problem:** `/regime` shows "Unknown" regime

**Solution:**
1. Check that market data APIs are working
2. Run `/regime` again to force detection
3. Check bot logs for errors
4. Verify Fear & Greed API is accessible

### Mode doesn't change

**Problem:** `/mode aggressive` doesn't seem to work

**Solution:**
1. Check that command handler is registered
2. Verify orchestrator is imported in main.py
3. Check bot logs for errors
4. Try `/orchestrator` to see current mode

### Notifications still coming in quiet mode

**Problem:** Getting notifications in quiet mode

**Solution:**
1. Check that priority system is integrated
2. Verify notifications are checking `orchestrator.should_send_notification()`
3. Some notifications might be CRITICAL priority
4. Check `/prioritytest` to verify filtering

### Regime doesn't update

**Problem:** Regime stays the same for days

**Solution:**
1. Check that hourly scheduler is running
2. Verify `check_regime` function is defined
3. Check bot logs for scheduler errors
4. Manually run `/regime` to force update

---

## 💡 Advanced Usage

### Custom Regime Logic

Edit `orchestrator.py` to customize regime detection:

```python
# Add your own factors
if my_custom_indicator > threshold:
    scores[MarketRegime.BULL_TREND] += 3
```

### Custom Mode

Add a new mode to `BotMode` enum:

```python
class BotMode(Enum):
    NORMAL = "normal"
    AGGRESSIVE = "aggressive"
    QUIET = "quiet"
    NIGHT = "night"
    CUSTOM = "custom"  # Your new mode
```

### Integration with Other Systems

**In your scanner:**
```python
from crypto_agent.core.orchestrator import orchestrator

# Get current scan frequency
freq = orchestrator.get_scan_frequency()

# Get scanner focus
settings = orchestrator.get_current_settings()
focus = settings['scanner_focus']
```

**In your alert system:**
```python
from crypto_agent.core.orchestrator import orchestrator, Priority

# Check if alert should be sent
if orchestrator.should_send_notification(Priority.HIGH):
    send_alert()
```

**In your Claude integration:**
```python
from crypto_agent.core.orchestrator import orchestrator

# Add regime context to Claude
system_prompt = base_prompt + orchestrator.get_claude_system_prompt_addition()
```

---

## 📊 Monitoring

### Check Regime History

Query the database:
```sql
SELECT regime, confidence, timestamp 
FROM market_regimes 
ORDER BY timestamp DESC 
LIMIT 10;
```

### Check Decisions

Query the database:
```sql
SELECT decision_type, description, timestamp 
FROM orchestrator_decisions 
ORDER BY timestamp DESC 
LIMIT 20;
```

### Track Regime Changes

See how often regime changes:
```sql
SELECT regime, COUNT(*) as count 
FROM market_regimes 
GROUP BY regime;
```

---

## ✅ Quick Start Checklist

- [ ] Database tables initialized
- [ ] Command handlers registered
- [ ] Hourly regime check scheduled
- [ ] Mode expiry check scheduled
- [ ] Bot restarted
- [ ] `/regime` shows current regime
- [ ] `/orchestrator` shows status
- [ ] `/mode aggressive` works
- [ ] Priority system integrated

---

## 🎉 What's Next?

Once the orchestrator is running:

1. **Monitor regime changes** - Watch how it adapts to market
2. **Test different modes** - Try aggressive/quiet modes
3. **Integrate with systems** - Connect scanner, alerts, workflows
4. **Customize thresholds** - Adjust regime detection logic
5. **Add custom factors** - Include your own indicators

The orchestrator makes your bot truly intelligent and adaptive!

---

Need help? Check `/orchestrator` status and share any error messages!
