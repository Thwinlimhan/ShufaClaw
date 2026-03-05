# Workflow Engine - Quick Start

## What You Just Got

I built a **sophisticated workflow automation system** for your crypto bot. Think of it as creating mini-programs that run automatically on a schedule.

---

## 🎯 What It Does

### 4 Pre-Built Workflows (Ready to Use)

1. **Morning Preparation** (7:45 AM daily)
   - Pre-loads all market data
   - Scans overnight movements
   - Checks alerts close to triggering
   - Sends morning briefing at 8:00 AM sharp

2. **Weekly Research** (Sunday 10:00 AM)
   - Researches your portfolio coins
   - Researches your watchlist
   - Generates week-in-review report
   - Sends comprehensive analysis

3. **Risk Review** (3:00 PM daily)
   - Calculates portfolio risk
   - Compares to yesterday
   - Alerts if risk increased
   - Tracks risk over time

4. **Opportunity Scanner** (9:00 AM & 9:00 PM)
   - Scans for oversold coins
   - Finds high volume spikes
   - Detects unusual patterns
   - Sends opportunity digest

### Custom Workflow Builder

You can create your own workflows with:
- Custom triggers (time, price, manual)
- Custom actions (analyze, check portfolio, etc.)
- Custom schedules

---

## 📦 What Was Created

**3 New Files:**

1. `crypto_agent/core/workflow_engine.py` (600+ lines)
   - Main workflow engine
   - All built-in workflows
   - Scheduling system

2. `crypto_agent/storage/workflow_db.py` (400+ lines)
   - Database functions
   - Workflow tracking
   - History logging

3. `crypto_agent/bot/workflow_handlers.py` (400+ lines)
   - Telegram commands
   - Interactive workflow builder

**5 New Database Tables:**
- `workflow_runs` - Execution history
- `custom_workflows` - User-created workflows
- `risk_history` - Daily risk tracking
- `scanner_settings` - Scanner config
- `scanner_events` - Scanner findings

**1 Test File:**
- `test_workflow_engine.py` - Verify it works

**2 Guide Files:**
- `WORKFLOW_ENGINE_GUIDE.md` - Complete documentation
- `WORKFLOW_QUICK_START.md` - This file

---

## 🚀 Setup (3 Steps)

### Step 1: Test the Engine

Run this to verify everything works:
```bash
python test_workflow_engine.py
```

You should see:
```
✅ All 4 built-in workflows registered!
✅ Test workflow executed successfully!
✅ Workflow status tracking works!
✅ Scheduling system works!
```

### Step 2: Initialize Database

Run this command once:
```bash
python -c "from crypto_agent.storage import workflow_db, database; workflow_db.init_workflow_tables(database.get_connection())"
```

This creates the 5 new database tables.

### Step 3: Register Commands

Open `crypto_agent/main.py` and add:

**Imports (at the top):**
```python
from crypto_agent.bot import workflow_handlers
from crypto_agent.core.workflow_engine import workflow_engine
from telegram.ext import ConversationHandler, MessageHandler, filters
```

**Commands (where other handlers are):**
```python
# Workflow commands
application.add_handler(CommandHandler("workflows", workflow_handlers.workflows_command))
application.add_handler(CommandHandler("runworkflow", workflow_handlers.run_workflow_command))
application.add_handler(CommandHandler("workflowhistory", workflow_handlers.workflow_history_command))

# Custom workflow builder
workflow_conv = ConversationHandler(
    entry_points=[CommandHandler("createworkflow", workflow_handlers.create_workflow_start)],
    states={
        workflow_handlers.WF_TRIGGER: [MessageHandler(filters.TEXT & ~filters.COMMAND, workflow_handlers.workflow_choose_trigger)],
        workflow_handlers.WF_STEPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, workflow_handlers.workflow_choose_steps)],
        workflow_handlers.WF_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, workflow_handlers.workflow_set_name)],
        workflow_handlers.WF_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, workflow_handlers.workflow_confirm)]
    },
    fallbacks=[CommandHandler("cancel", workflow_handlers.workflow_cancel)]
)
application.add_handler(workflow_conv)
```

**Scheduler (before `application.run_polling()`):**
```python
# Workflow scheduler - checks every minute
async def check_workflows(context):
    await workflow_engine.check_and_run_scheduled(
        bot=context.bot,
        chat_id=config.MY_TELEGRAM_ID  # Your chat ID
    )

job_queue = application.job_queue
job_queue.run_repeating(check_workflows, interval=60, first=10)
```

---

## ✅ Test It

1. **Start your bot:**
   ```
   python crypto_agent/main.py
   ```

2. **Check workflows:**
   ```
   /workflows
   ```
   Should show 4 built-in workflows

3. **Run one manually:**
   ```
   /runworkflow morning_preparation
   ```
   Should execute and show results

4. **Create a custom workflow:**
   ```
   /createworkflow
   ```
   Follow the prompts

---

## 📱 Commands

### `/workflows`
Shows all workflows with status:
```
⚙️ AUTOMATED WORKFLOWS

✅ Morning Preparation
Last run: Today 7:45 AM (Success)
Next run: Tomorrow 7:45 AM

✅ Weekly Research Refresh
Last run: Sunday (Success, 47 min)
Next run: Next Sunday
```

### `/runworkflow [name]`
Run a workflow manually:
```
/runworkflow morning_preparation
/runworkflow weekly_research
/runworkflow risk_review
/runworkflow opportunity_screen
```

### `/workflowhistory [name]`
See execution history:
```
/workflowhistory morning_preparation
```

### `/createworkflow`
Build a custom workflow (interactive):
1. Choose trigger
2. Select actions
3. Name it
4. Confirm

---

## 🎨 How It Works

```
┌─────────────────────────────────────┐
│  Scheduler (checks every minute)   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Is it time for any workflow?      │
└──────────────┬──────────────────────┘
               │ YES
               ▼
┌─────────────────────────────────────┐
│  Start Workflow                     │
│  ├─ Step 1: Fetch data             │
│  ├─ Step 2: Analyze                │
│  ├─ Step 3: Generate report        │
│  └─ Step 4: Send message           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Log to Database                    │
│  - Status (success/failed)          │
│  - Duration                         │
│  - Steps completed                  │
│  - Any errors                       │
└─────────────────────────────────────┘
```

---

## 🐛 Troubleshooting

### Test fails
- Check imports are correct
- Make sure all files were created
- Look at error messages

### `/workflows` shows nothing
- Database tables not initialized
- Run the database init command
- Restart bot

### Workflows don't run automatically
- Scheduler not set up
- Check job_queue is configured
- Verify chat_id is correct

### Workflow fails
- Use `/workflowhistory [name]` to see error
- Check bot logs
- Most common: API timeout or missing data

---

## 💡 What's Cool About This

1. **Automated Intelligence** - Your bot works while you sleep
2. **Customizable** - Build workflows for your specific needs
3. **Reliable** - Tracks all runs, logs errors, retries
4. **Flexible** - Time-based, price-based, or manual triggers
5. **Powerful** - Chain multiple actions together

---

## 📚 Learn More

- **Full Documentation:** `WORKFLOW_ENGINE_GUIDE.md`
- **Integration Notes:** `integration_note.md`
- **Test File:** `test_workflow_engine.py`

---

## 🎉 You're Done!

Once you complete the 3 setup steps:

1. ✅ Test passes
2. ✅ Database initialized
3. ✅ Commands registered

Your bot will have:
- 4 automated workflows running on schedule
- Ability to create unlimited custom workflows
- Full workflow monitoring and history
- Intelligent automation that learns and adapts

This is a **major upgrade** that makes your bot truly autonomous!

---

**Next:** Test it with `/workflows` and watch your bot work for you! 🚀
