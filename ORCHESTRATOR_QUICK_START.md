# Market Orchestrator - Quick Start

## What You Just Got

I built the **master brain** for your crypto bot - an intelligent orchestrator that monitors market conditions and adapts all bot systems automatically.

---

## 🎯 What It Does (Simple Version)

**The orchestrator watches the market and changes how your bot behaves:**

- **Bull market?** → Bot becomes optimistic, relaxed alerts, looks for momentum
- **Bear market?** → Bot becomes cautious, more alerts, focuses on risk
- **High volatility?** → Bot scans every 2 minutes, warns about volatility
- **Quiet market?** → Bot relaxes, scans less, looks for breakouts

**You can also manually control it:**
- `/mode aggressive` - More scans, all opportunities (4hr auto-revert)
- `/mode quiet` - Critical only, minimal messages (4hr auto-revert)
- `/mode normal` - Standard operation

---

## 📦 What Was Created

**3 New Files:**

1. `crypto_agent/core/orchestrator.py` (600+ lines)
   - Market regime detection
   - Behavior adaptation
   - Priority filtering

2. `crypto_agent/bot/orchestrator_handlers.py` (300+ lines)
   - Telegram commands
   - `/regime`, `/orchestrator`, `/mode`

3. Database functions in `crypto_agent/storage/workflow_db.py`
   - Regime tracking
   - Decision logging

**2 New Database Tables:**
- `market_regimes` - Track regime changes
- `orchestrator_decisions` - Log decisions

**2 Guide Files:**
- `ORCHESTRATOR_GUIDE.md` - Complete documentation
- `ORCHESTRATOR_QUICK_START.md` - This file

**1 Test File:**
- `test_orchestrator.py` - Verify it works

---

## 🚀 Setup (3 Steps)

### Step 1: Test It

Run this to verify everything works:
```bash
python test_orchestrator.py
```

You should see:
```
✅ Initial state loaded
✅ Regime detection works!
✅ Settings retrieved!
✅ Mode switching works!
✅ Priority filtering works!
✅ Claude prompt generation works!
✅ Decision logging works!
✅ Report generation works!
```

### Step 2: Initialize Database

Run this command once:
```bash
python -c "from crypto_agent.storage import workflow_db, database; workflow_db.init_orchestrator_tables(database.get_connection())"
```

### Step 3: Register Commands

Open `crypto_agent/main.py` and add:

**Imports:**
```python
from crypto_agent.bot import orchestrator_handlers
from crypto_agent.core.orchestrator import orchestrator
```

**Commands:**
```python
# Orchestrator commands
application.add_handler(CommandHandler("regime", orchestrator_handlers.regime_command))
application.add_handler(CommandHandler("orchestrator", orchestrator_handlers.orchestrator_command))
application.add_handler(CommandHandler("mode", orchestrator_handlers.mode_command))
application.add_handler(CommandHandler("settings", orchestrator_handlers.settings_command))
```

**Scheduler (before `application.run_polling()`):**
```python
# Check regime every hour
async def check_regime(context):
    await orchestrator.update_regime()

job_queue = application.job_queue
job_queue.run_repeating(check_regime, interval=3600, first=10)
```

---

## ✅ Test It

1. **Start bot:**
   ```
   python crypto_agent/main.py
   ```

2. **Check regime:**
   ```
   /regime
   ```

3. **Check status:**
   ```
   /orchestrator
   ```

4. **Change mode:**
   ```
   /mode aggressive
   ```

---

## 📱 Key Commands

### `/regime`
Shows what the market is doing and how the bot adapted:
```
🌡️ MARKET REGIME ANALYSIS

Current: 🐂 BULL TREND (High Confidence)

Supporting factors:
• BTC above 50-day SMA
• Fear & Greed: 68 (Greed)
• 5 green days

Bot behavior:
• Alert threshold: relaxed
• Scan frequency: Every 5 min
• Scanner focus: momentum
```

### `/mode [type]`
Change how the bot operates:
```
/mode aggressive  - More scans, all opportunities
/mode quiet       - Critical only, minimal messages
/mode normal      - Standard operation
```

### `/orchestrator`
See what the orchestrator is doing:
```
🧠 ORCHESTRATOR STATUS

Mode: 🔵 NORMAL
Current Regime: Bull Trend
Confidence: 85%

Decisions (Last 24h): 3
• 03:00 PM - Regime changed
• 09:00 AM - Mode reverted
```

---

## 🎨 How It Works (Simple)

```
Every Hour:
    ↓
Check Market:
  - Is BTC above/below moving average?
  - Is Fear & Greed high/low?
  - Are we seeing green/red days?
  - Is volatility high/low?
    ↓
Determine Regime:
  - Bull Trend 🐂
  - Bear Trend 🐻
  - High Volatility ⚡
  - Ranging 📊
    ↓
Adjust Bot Behavior:
  - Change scan frequency
  - Change alert sensitivity
  - Change scanner focus
  - Change briefing tone
    ↓
Apply to All Systems:
  - Workflows use new scan frequency
  - Alerts use new sensitivity
  - Scanner uses new focus
  - Briefings use new tone
```

---

## 🔥 Real Examples

### Bull Market Example

**Market:** BTC at $70k, Fear & Greed 72, 5 green days

**Orchestrator Does:**
- Detects: BULL TREND 🐂
- Scans every 5 minutes
- Relaxed alerts
- Looks for momentum opportunities
- Optimistic briefings

**You Experience:**
- Fewer false alarms
- More opportunity notifications
- "Market is strong" messages
- Suggestions to ride trends

### Bear Market Example

**Market:** BTC at $58k, Fear & Greed 28, 4 red days

**Orchestrator Does:**
- Detects: BEAR TREND 🐻
- Scans every 3 minutes
- Heightened alerts
- Looks for risks
- Cautious briefings

**You Experience:**
- More frequent warnings
- Easier alert triggers
- "Protect capital" messages
- Suggestions to reduce risk

### High Volatility Example

**Market:** BTC swinging 7% daily, ATR 2.5x normal

**Orchestrator Does:**
- Detects: HIGH VOLATILITY ⚡
- Scans every 2 minutes
- High alert sensitivity
- Warns about volatility
- Alert briefings

**You Experience:**
- Very frequent updates
- Volatility warnings
- "Be careful" messages
- Suggestions to widen stops

---

## 💡 Why This Is Powerful

**Before Orchestrator:**
- Bot runs the same way all the time
- You manually adjust settings
- Same alerts in bull and bear markets
- No adaptation to conditions

**After Orchestrator:**
- Bot adapts automatically
- Settings change based on market
- Different behavior for different conditions
- Intelligent coordination

**The Result:**
- Fewer false alarms in bull markets
- More warnings in bear markets
- Appropriate response to volatility
- Smarter, more helpful bot

---

## 🐛 Troubleshooting

**Test fails:**
- Check all files were created
- Look at error messages
- Some features need real market data

**`/regime` shows "Unknown":**
- Market data APIs may be down
- Run `/regime` again
- Check bot logs

**Mode doesn't change:**
- Check handlers are registered
- Verify imports in main.py
- Check bot logs

**Still getting notifications in quiet mode:**
- Check priority system is integrated
- Some notifications are CRITICAL priority
- Use `/prioritytest` to verify

---

## 📚 Learn More

- **Full Documentation:** `ORCHESTRATOR_GUIDE.md`
- **Integration Notes:** `integration_note.md`
- **Test File:** `test_orchestrator.py`

---

## ✅ Quick Checklist

- [ ] Test passes (`python test_orchestrator.py`)
- [ ] Database initialized
- [ ] Commands registered
- [ ] Scheduler set up
- [ ] Bot restarted
- [ ] `/regime` works
- [ ] `/mode` works
- [ ] `/orchestrator` works

---

## 🎉 You're Done!

Once setup is complete, your bot will:
- Automatically detect market regime every hour
- Adapt behavior to market conditions
- Filter notifications by priority
- Adjust Claude's personality
- Make intelligent decisions

This is the **brain** that makes everything else smarter!

---

**Next:** Test with `/regime` and watch your bot adapt to the market! 🧠
