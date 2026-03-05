# Workflow Engine Setup Guide

## What Is This?

The Workflow Engine lets you create **automated multi-step tasks** that run on a schedule or when triggered. Think of it like creating your own custom bots within your bot!

---

## 🎯 What You Can Do

### Built-in Workflows (Already Configured)

1. **Morning Preparation** - Runs daily at 7:45 AM
   - Pre-fetches all market data
   - Scans for overnight movements
   - Checks alerts that are close to triggering
   - Sends your morning briefing at exactly 8:00 AM

2. **Weekly Research** - Runs Sunday at 10:00 AM
   - Researches all coins in your portfolio
   - Researches all coins in your watchlist
   - Generates a "Week in Review" report
   - Sends you the full report

3. **Risk Review** - Runs daily at 3:00 PM
   - Calculates your portfolio risk score
   - Compares to yesterday
   - Alerts you if risk increased significantly
   - Tracks risk history over time

4. **Opportunity Screen** - Runs at 9:00 AM and 9:00 PM
   - Scans for oversold coins
   - Scans for high volume spikes
   - Scans for unusual patterns
   - Sends you a digest of opportunities

### Custom Workflows (You Build These)

You can create your own workflows with:
- Custom triggers (time, price, manual)
- Custom actions (analyze, check portfolio, send messages)
- Custom schedules

---

## 📦 Files Created

1. **crypto_agent/core/workflow_engine.py**
   - The main workflow engine
   - Contains all built-in workflows
   - Manages scheduling and execution

2. **crypto_agent/storage/workflow_db.py**
   - Database functions for workflows
   - Tracks workflow runs
   - Stores custom workflows

3. **crypto_agent/bot/workflow_handlers.py**
   - Telegram command handlers
   - `/workflows`, `/runworkflow`, `/createworkflow`

---

## 🔧 Setup Steps

### Step 1: Initialize Database Tables

The workflow engine needs new database tables. Add this to your database initialization:

**Find your database setup file** (likely `crypto_agent/storage/database.py`)

**Add this import at the top:**
```python
from crypto_agent.storage import workflow_db
```

**Find where tables are created** (look for `CREATE TABLE` statements)

**Add this line:**
```python
workflow_db.init_workflow_tables(conn)
```

**Or run this once manually:**
```python
python -c "from crypto_agent.storage import workflow_db, database; workflow_db.init_workflow_tables(database.get_connection())"
```

### Step 2: Register Command Handlers

Open your main bot file (likely `crypto_agent/main.py`)

**Add this import:**
```python
from crypto_agent.bot import workflow_handlers
from telegram.ext import ConversationHandler, MessageHandler, filters
```

**Add these command handlers:**
```python
# Workflow commands
application.add_handler(CommandHandler("workflows", workflow_handlers.workflows_command))
application.add_handler(CommandHandler("runworkflow", workflow_handlers.run_workflow_command))
application.add_handler(CommandHandler("workflowhistory", workflow_handlers.workflow_history_command))

# Custom workflow creation (conversation)
workflow_conv = ConversationHandler(
    entry_points=[CommandHandler("createworkflow", workflow_handlers.create_workflow_start)],
    states={
        workflow_handlers.WF_TRIGGER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, workflow_handlers.workflow_choose_trigger)
        ],
        workflow_handlers.WF_STEPS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, workflow_handlers.workflow_choose_steps)
        ],
        workflow_handlers.WF_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, workflow_handlers.workflow_set_name)
        ],
        workflow_handlers.WF_CONFIRM: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, workflow_handlers.workflow_confirm)
        ]
    },
    fallbacks=[CommandHandler("cancel", workflow_handlers.workflow_cancel)]
)
application.add_handler(workflow_conv)
```

### Step 3: Set Up Workflow Scheduler

The workflows need to check every minute if they should run.

**Add this import:**
```python
from crypto_agent.core.workflow_engine import workflow_engine
```

**Add this function before `application.run_polling()`:**
```python
async def check_workflows(context):
    """Check and run scheduled workflows."""
    await workflow_engine.check_and_run_scheduled(
        bot=context.bot,
        chat_id=YOUR_TELEGRAM_CHAT_ID  # Replace with your actual chat ID
    )

# Schedule workflow checker to run every minute
from telegram.ext import JobQueue
job_queue = application.job_queue
job_queue.run_repeating(check_workflows, interval=60, first=10)
```

**Replace `YOUR_TELEGRAM_CHAT_ID`** with your actual Telegram chat ID (the number from `config.MY_TELEGRAM_ID`)

### Step 4: Test It

1. **Start your bot:**
   ```
   python crypto_agent/main.py
   ```

2. **Check workflows:**
   ```
   /workflows
   ```
   You should see all 4 built-in workflows listed

3. **Run a workflow manually:**
   ```
   /runworkflow morning_preparation
   ```
   This will execute the morning prep workflow immediately

4. **Create a custom workflow:**
   ```
   /createworkflow
   ```
   Follow the interactive prompts

---

## 📊 Commands Reference

### `/workflows`
Shows all workflows with their status:
- Last run time
- Next scheduled run
- Success/failure status
- Duration
- Error messages (if any)

### `/runworkflow [name]`
Manually run a specific workflow:
```
/runworkflow morning_preparation
/runworkflow weekly_research
/runworkflow risk_review
/runworkflow opportunity_screen
```

### `/workflowhistory [name]`
Show execution history for a workflow:
```
/workflowhistory morning_preparation
```
Shows last 10 runs with status and duration

### `/createworkflow`
Interactive workflow builder:
1. Choose trigger type (time/price/manual)
2. Select actions to perform
3. Name your workflow
4. Confirm and save

---

## 🎨 How Workflows Work

### Workflow Structure

```
Workflow
├── Name: "morning_preparation"
├── Description: "Prepares data and sends briefing"
├── Steps:
│   ├── Step 1: Warm Cache
│   ├── Step 2: Scan Overnight
│   ├── Step 3: Check Alerts
│   ├── Step 4: Fetch Portfolio
│   ├── Step 5: Generate Briefing
│   └── Step 6: Send Briefing
└── Schedule: Daily at 7:45 AM
```

### Execution Flow

1. **Scheduler checks** every minute if any workflow should run
2. **Workflow starts** and creates a context (shared data)
3. **Each step executes** in sequence:
   - Step runs its action
   - Result is stored in context
   - Next step can access previous results
4. **Workflow completes** and logs to database:
   - Success/failure status
   - Steps completed
   - Duration
   - Any errors

### Context Sharing

Steps can share data through the context:

```python
# Step 1 stores data
context['portfolio_value'] = 50000

# Step 2 can access it
total = context['portfolio_value']
```

---

## 🛠️ Creating Custom Workflows

### Example: Daily BTC Check

```
/createworkflow

Bot: What should trigger this workflow?
You: 1 (time-based)

Bot: When should this run?
You: daily 09:00

Bot: What should this workflow do?
You: 2,5 (analyze coin + technical analysis)

Bot: Give this workflow a name:
You: btc_morning_check

Bot: Ready to save?
You: yes
```

Now this workflow will:
- Run every day at 9:00 AM
- Analyze BTC
- Run technical analysis
- Send you the results

### Available Actions

When creating a workflow, you can choose:

1. **Fetch market data** - Get current market overview
2. **Analyze a specific coin** - Deep analysis of one coin
3. **Check my portfolio** - Get portfolio status
4. **Send me a custom message** - Send a notification
5. **Run technical analysis** - TA on a coin
6. **Check alerts** - See which alerts are close

---

## 🐛 Troubleshooting

### Workflows don't appear

**Problem:** `/workflows` shows "No workflows configured"

**Solution:**
1. Check that workflow_engine is imported in main.py
2. Make sure database tables were created
3. Restart your bot

### Workflows don't run automatically

**Problem:** Workflows show up but never run on schedule

**Solution:**
1. Check that you added the job_queue scheduler
2. Make sure `check_workflows` function is defined
3. Verify the scheduler is running (check logs)
4. Ensure chat_id is correct in the scheduler

### Workflow fails with error

**Problem:** Workflow shows "failed" status

**Solution:**
1. Use `/workflowhistory [name]` to see the error
2. Check bot logs for detailed error messages
3. Most common issues:
   - API timeout (increase timeout)
   - Missing data (check data sources)
   - Database error (check database connection)

### Custom workflow doesn't save

**Problem:** `/createworkflow` conversation doesn't complete

**Solution:**
1. Make sure ConversationHandler is registered
2. Check that all states are defined
3. Don't use other commands during workflow creation
4. Use `/cancel` to restart if stuck

---

## 📈 Monitoring Workflows

### Check Status
```
/workflows
```
Shows all workflows with last run status

### View History
```
/workflowhistory morning_preparation
```
Shows last 10 executions with details

### Database Queries

You can also query the database directly:

```sql
-- See all workflow runs
SELECT * FROM workflow_runs ORDER BY started_at DESC LIMIT 10;

-- See failed runs
SELECT * FROM workflow_runs WHERE status = 'failed';

-- See average duration
SELECT workflow_name, AVG(duration_seconds) 
FROM workflow_runs 
GROUP BY workflow_name;
```

---

## 🚀 Advanced Usage

### Modify Built-in Workflows

Edit `crypto_agent/core/workflow_engine.py` to:
- Change schedule times
- Add/remove steps
- Modify step logic

### Create Complex Workflows

You can create workflows that:
- Run multiple analyses in parallel
- Make decisions based on previous step results
- Send different messages based on conditions
- Chain multiple workflows together

### Add New Step Types

Add new step implementations in `workflow_engine.py`:

```python
async def _my_custom_step(self, context: Dict) -> Any:
    """My custom workflow step."""
    # Your logic here
    return result
```

Then use it in a workflow:
```python
WorkflowStep("My Custom Step", self._my_custom_step)
```

---

## ✅ Quick Start Checklist

- [ ] Database tables initialized
- [ ] Command handlers registered
- [ ] Scheduler set up with job_queue
- [ ] Bot restarted
- [ ] `/workflows` shows 4 built-in workflows
- [ ] `/runworkflow morning_preparation` works
- [ ] Workflows run automatically on schedule

---

## 💡 Tips

1. **Start simple** - Test built-in workflows before creating custom ones
2. **Monitor regularly** - Check `/workflows` daily to catch failures
3. **Use manual runs** - Test workflows with `/runworkflow` before scheduling
4. **Check history** - Use `/workflowhistory` to debug issues
5. **Be patient** - Some workflows take 1-2 minutes to complete

---

## 🎉 What's Next?

Once workflows are running:

1. **Customize schedules** - Change times to fit your routine
2. **Create custom workflows** - Build workflows for your specific needs
3. **Monitor performance** - Track which workflows are most useful
4. **Add more steps** - Extend workflows with new actions
5. **Chain workflows** - Have one workflow trigger another

The workflow engine is powerful and flexible. Start with the built-ins, then build your own!

---

Need help? Check the logs, use `/workflowhistory`, and share any error messages!
