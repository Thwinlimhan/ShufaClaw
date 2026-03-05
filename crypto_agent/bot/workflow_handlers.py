# Telegram command handlers for workflow management

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from crypto_agent.core.workflow_engine import workflow_engine
from crypto_agent.storage import workflow_db
from crypto_agent.bot.middleware import is_authorized, track_command

logger = logging.getLogger(__name__)

# Conversation states for workflow creation
WF_TRIGGER, WF_TRIGGER_PARAMS, WF_STEPS, WF_NAME, WF_CONFIRM = range(5)

async def workflows_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all workflows with their status."""
    if not await is_authorized(update): return
    track_command("workflows")
    
    workflows = workflow_engine.get_workflow_status()
    
    if not workflows:
        await update.message.reply_text(
            "⚙️ No workflows configured yet.\n\n"
            "Use `/createworkflow` to build your first automated workflow!",
            parse_mode='Markdown'
        )
        return
    
    msg = "⚙️ **AUTOMATED WORKFLOWS**\n\n"
    
    for wf in workflows:
        # Status emoji
        if wf['last_status'] == 'success':
            status_emoji = "✅"
        elif wf['last_status'] == 'failed':
            status_emoji = "❌"
        elif wf['last_status'] == 'partial':
            status_emoji = "⚠️"
        else:
            status_emoji = "⏳"
        
        msg += f"{status_emoji} **{wf['name'].replace('_', ' ').title()}**\n"
        msg += f"_{wf['description']}_\n"
        
        # Last run info
        if wf['last_run']:
            last_run_time = wf['last_run'].strftime("%b %d, %I:%M %p")
            msg += f"Last run: {last_run_time}"
            
            if wf['last_duration']:
                duration_min = int(wf['last_duration'] / 60)
                if duration_min > 0:
                    msg += f" ({duration_min} min)"
            
            if wf['last_status'] == 'failed' and wf['last_error']:
                msg += f"\nError: {wf['last_error'][:50]}..."
            
            msg += "\n"
        else:
            msg += "Last run: Never\n"
        
        # Next run info
        if wf['next_run']:
            next_run_time = wf['next_run'].strftime("%b %d, %I:%M %p")
            msg += f"Next run: {next_run_time}\n"
        
        msg += "\n"
    
    msg += "💡 Use `/runworkflow [name]` to run manually\n"
    msg += "💡 Use `/createworkflow` to build a custom workflow"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def run_workflow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually run a specific workflow."""
    if not await is_authorized(update): return
    track_command("runworkflow")
    
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: `/runworkflow [workflow_name]`\n\n"
            "Example: `/runworkflow morning_preparation`\n\n"
            "Use `/workflows` to see available workflows.",
            parse_mode='Markdown'
        )
        return
    
    workflow_name = "_".join(context.args).lower()
    
    await update.message.reply_text(
        f"🔄 Running workflow: **{workflow_name}**...\n"
        f"This may take a minute.",
        parse_mode='Markdown'
    )
    
    try:
        result = await workflow_engine.run_workflow(
            workflow_name,
            bot=context.bot,
            chat_id=update.effective_chat.id
        )
        
        if result['status'] == 'success':
            msg = (
                f"✅ **Workflow Complete!**\n\n"
                f"Workflow: {workflow_name}\n"
                f"Steps completed: {result['steps_completed']}/{result['total_steps']}\n"
                f"Duration: {result['duration']:.1f}s"
            )
        elif result['status'] == 'partial':
            msg = (
                f"⚠️ **Workflow Partially Complete**\n\n"
                f"Workflow: {workflow_name}\n"
                f"Steps completed: {result['steps_completed']}/{result['total_steps']}\n"
                f"Error: {result['error']}"
            )
        else:
            msg = (
                f"❌ **Workflow Failed**\n\n"
                f"Workflow: {workflow_name}\n"
                f"Error: {result['error']}"
            )
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        
    except ValueError as e:
        await update.message.reply_text(
            f"❌ Workflow not found: {workflow_name}\n\n"
            f"Use `/workflows` to see available workflows.",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error running workflow: {e}")
        await update.message.reply_text(
            f"❌ Error running workflow: {str(e)}",
            parse_mode='Markdown'
        )

async def workflow_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show execution history for a workflow."""
    if not await is_authorized(update): return
    track_command("workflowhistory")
    
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: `/workflowhistory [workflow_name]`",
            parse_mode='Markdown'
        )
        return
    
    workflow_name = "_".join(context.args).lower()
    history = workflow_db.get_workflow_history(workflow_name, limit=10)
    
    if not history:
        await update.message.reply_text(
            f"📜 No execution history for: {workflow_name}",
            parse_mode='Markdown'
        )
        return
    
    msg = f"📜 **WORKFLOW HISTORY: {workflow_name}**\n\n"
    
    for run in history:
        started = datetime.fromisoformat(run['started_at']).strftime("%b %d, %I:%M %p")
        
        if run['status'] == 'success':
            emoji = "✅"
        elif run['status'] == 'failed':
            emoji = "❌"
        else:
            emoji = "⚠️"
        
        msg += f"{emoji} {started}\n"
        msg += f"Steps: {run['steps_completed']}/{run['total_steps']}"
        
        if run['duration_seconds']:
            msg += f" • {run['duration_seconds']:.1f}s"
        
        if run['error_message']:
            msg += f"\nError: {run['error_message'][:50]}..."
        
        msg += "\n\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

# ==================== CUSTOM WORKFLOW CREATION ====================

async def create_workflow_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the custom workflow creation conversation."""
    if not await is_authorized(update): return
    track_command("createworkflow")
    
    msg = (
        "🛠️ **CUSTOM WORKFLOW BUILDER**\n\n"
        "Let's build an automated workflow together!\n\n"
        "**Step 1: Choose a trigger**\n\n"
        "What should trigger this workflow?\n\n"
        "1️⃣ Time-based (daily/weekly)\n"
        "2️⃣ Price event (when a coin hits a price)\n"
        "3️⃣ Manual (run with /runworkflow)\n\n"
        "Reply with 1, 2, or 3\n"
        "Or /cancel to stop"
    )
    
    await update.message.reply_text(msg, parse_mode='Markdown')
    return WF_TRIGGER

async def workflow_choose_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle trigger type selection."""
    choice = update.message.text.strip()
    
    if choice == "1":
        context.user_data['wf_trigger'] = 'time'
        msg = (
            "⏰ **TIME-BASED TRIGGER**\n\n"
            "When should this run?\n\n"
            "Examples:\n"
            "• `daily 08:00`\n"
            "• `daily 15:30`\n"
            "• `weekly monday 10:00`\n"
            "• `weekly sunday 20:00`\n\n"
            "Reply with your schedule:"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')
        return WF_TRIGGER_PARAMS
    elif choice == "2":
        context.user_data['wf_trigger'] = 'price'
        msg = (
            "💰 **PRICE EVENT TRIGGER**\n\n"
            "Format: `SYMBOL PRICE above/below`\n\n"
            "Examples:\n"
            "• `BTC 100000 above`\n"
            "• `ETH 5000 below`\n\n"
            "Reply with your trigger:"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')
        return WF_TRIGGER_PARAMS
    elif choice == "3":
        context.user_data['wf_trigger'] = 'manual'
        context.user_data['wf_trigger_params'] = {}
        msg = (
            "👆 **MANUAL TRIGGER**\n\n"
            "This workflow will only run when you use:\n"
            "`/runworkflow [name]`\n\n"
            "**Step 2: Choose actions**\n\n"
            "What should this workflow do?\n\n"
            "1️⃣ Fetch market data\n"
            "2️⃣ Analyze a specific coin\n"
            "3️⃣ Check my portfolio\n"
            "4️⃣ Send me a custom message\n"
            "5️⃣ Run technical analysis\n"
            "6️⃣ Check alerts\n\n"
            "Reply with numbers separated by commas\n"
            "Example: `1,3,4`"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')
        return WF_STEPS
    else:
        await update.message.reply_text(
            "❌ Invalid choice. Reply with 1, 2, or 3\n"
            "Or /cancel to stop"
        )
        return WF_TRIGGER
    
    await update.message.reply_text(msg, parse_mode='Markdown')
    return WF_TRIGGER

async def workflow_set_trigger_params(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle trigger parameter input."""
    trigger_type = context.user_data.get('wf_trigger')
    params_text = update.message.text.strip()
    
    try:
        if trigger_type == 'time':
            parts = params_text.lower().split()
            if len(parts) == 2 and parts[0] == 'daily':
                context.user_data['wf_trigger_params'] = {
                    'schedule': 'daily',
                    'time': parts[1]
                }
            elif len(parts) == 3 and parts[0] == 'weekly':
                context.user_data['wf_trigger_params'] = {
                    'schedule': 'weekly',
                    'day': parts[1],
                    'time': parts[2]
                }
            else:
                raise ValueError("Invalid format")
        
        elif trigger_type == 'price':
            parts = params_text.split()
            if len(parts) == 3:
                context.user_data['wf_trigger_params'] = {
                    'symbol': parts[0].upper(),
                    'price': float(parts[1]),
                    'direction': parts[2].lower()
                }
            else:
                raise ValueError("Invalid format")
        
        msg = (
            "✅ Trigger configured!\n\n"
            "**Step 2: Choose actions**\n\n"
            "What should this workflow do?\n\n"
            "1️⃣ Fetch market data\n"
            "2️⃣ Analyze a specific coin\n"
            "3️⃣ Check my portfolio\n"
            "4️⃣ Send me a custom message\n"
            "5️⃣ Run technical analysis\n"
            "6️⃣ Check alerts\n\n"
            "Reply with numbers separated by commas\n"
            "Example: `1,3,4`"
        )
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        return WF_STEPS
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Invalid format. Please try again.\n"
            f"Or /cancel to stop"
        )
        return WF_TRIGGER

async def workflow_choose_steps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle step selection."""
    steps_text = update.message.text.strip()
    
    try:
        step_numbers = [int(n.strip()) for n in steps_text.split(',')]
        
        step_map = {
            1: {'name': 'Fetch market data', 'action': 'fetch_market'},
            2: {'name': 'Analyze coin', 'action': 'analyze_coin'},
            3: {'name': 'Check portfolio', 'action': 'check_portfolio'},
            4: {'name': 'Send message', 'action': 'send_message'},
            5: {'name': 'Technical analysis', 'action': 'technical_analysis'},
            6: {'name': 'Check alerts', 'action': 'check_alerts'}
        }
        
        selected_steps = []
        for num in step_numbers:
            if num in step_map:
                selected_steps.append(step_map[num])
        
        if not selected_steps:
            raise ValueError("No valid steps selected")
        
        context.user_data['wf_steps'] = selected_steps
        
        msg = (
            f"✅ Selected {len(selected_steps)} actions!\n\n"
            f"**Step 3: Name your workflow**\n\n"
            f"Give this workflow a short name (no spaces):\n\n"
            f"Examples:\n"
            f"• `morning_check`\n"
            f"• `portfolio_review`\n"
            f"• `btc_monitor`\n\n"
            f"Reply with a name:"
        )
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        return WF_NAME
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Invalid format. Use numbers separated by commas.\n"
            f"Example: 1,3,4\n"
            f"Or /cancel to stop"
        )
        return WF_STEPS

async def workflow_set_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle workflow name input."""
    name = update.message.text.strip().lower().replace(' ', '_')
    
    if not name or len(name) < 3:
        await update.message.reply_text(
            "❌ Name too short. Please use at least 3 characters.\n"
            "Or /cancel to stop"
        )
        return WF_NAME
    
    context.user_data['wf_name'] = name
    
    # Show summary
    trigger = context.user_data.get('wf_trigger')
    trigger_params = context.user_data.get('wf_trigger_params', {})
    steps = context.user_data.get('wf_steps', [])
    
    msg = (
        f"📋 **WORKFLOW SUMMARY**\n\n"
        f"**Name:** {name}\n"
        f"**Trigger:** {trigger}\n"
    )
    
    if trigger == 'time':
        schedule = trigger_params.get('schedule')
        if schedule == 'daily':
            msg += f"Runs daily at {trigger_params.get('time')}\n"
        elif schedule == 'weekly':
            msg += f"Runs weekly on {trigger_params.get('day')} at {trigger_params.get('time')}\n"
    elif trigger == 'price':
        msg += f"Runs when {trigger_params.get('symbol')} goes {trigger_params.get('direction')} ${trigger_params.get('price')}\n"
    elif trigger == 'manual':
        msg += f"Runs manually with /runworkflow {name}\n"
    
    msg += f"\n**Actions ({len(steps)}):**\n"
    for i, step in enumerate(steps, 1):
        msg += f"{i}. {step['name']}\n"
    
    msg += f"\n**Ready to save?**\n"
    msg += f"Reply `yes` to save or `no` to cancel"
    
    await update.message.reply_text(msg, parse_mode='Markdown')
    return WF_CONFIRM

async def workflow_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle workflow confirmation."""
    response = update.message.text.strip().lower()
    
    if response == 'yes':
        name = context.user_data.get('wf_name')
        trigger = context.user_data.get('wf_trigger')
        trigger_params = context.user_data.get('wf_trigger_params', {})
        steps = context.user_data.get('wf_steps', [])
        
        # Save to database
        workflow_db.save_custom_workflow(
            name=name,
            description=f"Custom workflow: {name}",
            trigger_type=trigger,
            trigger_params=trigger_params,
            steps=steps
        )
        
        msg = (
            f"✅ **Workflow Saved!**\n\n"
            f"Your workflow `{name}` is now active.\n\n"
            f"Use `/workflows` to see all workflows\n"
            f"Use `/runworkflow {name}` to run it manually"
        )
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        
        # Clear user data
        context.user_data.clear()
        return ConversationHandler.END
    
    else:
        await update.message.reply_text(
            "❌ Workflow creation cancelled.\n"
            "Use `/createworkflow` to start over."
        )
        context.user_data.clear()
        return ConversationHandler.END

async def workflow_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel workflow creation."""
    await update.message.reply_text(
        "❌ Workflow creation cancelled.\n"
        "Use `/createworkflow` to start over."
    )
    context.user_data.clear()
    return ConversationHandler.END
