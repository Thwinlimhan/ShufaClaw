# Telegram command handlers for orchestrator

import logging
from telegram import Update
from telegram.ext import ContextTypes

from crypto_agent.core.orchestrator import orchestrator, BotMode, Priority
from crypto_agent.bot.middleware import is_authorized, track_command

logger = logging.getLogger(__name__)

async def regime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current market regime analysis."""
    if not await is_authorized(update): return
    track_command("regime")
    
    await update.message.reply_text("🔍 Analyzing market regime...")
    
    # Update regime detection
    regime_changed = await orchestrator.update_regime()
    
    # Get report
    report = orchestrator.get_regime_report()
    
    if regime_changed:
        report += "\n\n⚠️ **Regime just changed!** Bot behavior has been adjusted."
    
    await update.message.reply_text(report, parse_mode='Markdown')

async def orchestrator_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show orchestrator status and recent decisions."""
    if not await is_authorized(update): return
    track_command("orchestrator")
    
    report = orchestrator.get_orchestrator_status()
    await update.message.reply_text(report, parse_mode='Markdown')

async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change bot operating mode."""
    if not await is_authorized(update): return
    track_command("mode")
    
    if not context.args:
        # Show current mode
        current = orchestrator.current_mode.value
        msg = (
            f"🔵 **CURRENT MODE: {current.upper()}**\n\n"
            f"**Available modes:**\n\n"
            f"🔴 **Aggressive** - Lower thresholds, more frequent scans\n"
            f"   `/mode aggressive`\n\n"
            f"🔇 **Quiet** - Only critical alerts, minimal messages\n"
            f"   `/mode quiet`\n\n"
            f"🔵 **Normal** - Standard operation\n"
            f"   `/mode normal`\n\n"
            f"🌙 **Night** - Critical only (auto-enabled 12am-7am)\n"
            f"   `/mode night`"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')
        return
    
    mode_str = context.args[0].lower()
    
    # Map mode strings to BotMode enum
    mode_map = {
        'aggressive': BotMode.AGGRESSIVE,
        'quiet': BotMode.QUIET,
        'normal': BotMode.NORMAL,
        'night': BotMode.NIGHT
    }
    
    if mode_str not in mode_map:
        await update.message.reply_text(
            f"❌ Invalid mode: {mode_str}\n\n"
            f"Valid modes: aggressive, quiet, normal, night",
            parse_mode='Markdown'
        )
        return
    
    new_mode = mode_map[mode_str]
    
    # Aggressive and quiet modes auto-revert after 4 hours
    duration = 4 if new_mode in [BotMode.AGGRESSIVE, BotMode.QUIET] else None
    
    orchestrator.set_mode(new_mode, duration_hours=duration)
    
    # Mode descriptions
    mode_descriptions = {
        BotMode.AGGRESSIVE: (
            "🔴 **AGGRESSIVE MODE ACTIVATED**\n\n"
            "• Lower alert thresholds\n"
            "• Scans every 2 minutes\n"
            "• All opportunities reported\n"
            "• Increased message frequency\n\n"
            "⏰ Will auto-revert to normal in 4 hours"
        ),
        BotMode.QUIET: (
            "🔇 **QUIET MODE ACTIVATED**\n\n"
            "• Only critical alerts\n"
            "• No opportunity notifications\n"
            "• Minimal messages\n"
            "• Scans every 15 minutes\n\n"
            "⏰ Will auto-revert to normal in 4 hours"
        ),
        BotMode.NORMAL: (
            "🔵 **NORMAL MODE ACTIVATED**\n\n"
            "• Standard alert thresholds\n"
            "• Regime-based scanning\n"
            "• Balanced notifications\n\n"
            "Bot will adapt to market conditions automatically."
        ),
        BotMode.NIGHT: (
            "🌙 **NIGHT MODE ACTIVATED**\n\n"
            "• Critical alerts only\n"
            "• Minimal disturbance\n\n"
            "Note: Night mode auto-enables 12am-7am anyway."
        )
    }
    
    msg = mode_descriptions.get(new_mode, "Mode changed.")
    await update.message.reply_text(msg, parse_mode='Markdown')

async def priority_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test notification priority system (for debugging)."""
    if not await is_authorized(update): return
    track_command("prioritytest")
    
    if not context.args:
        await update.message.reply_text(
            "Usage: `/prioritytest [critical/high/medium/low]`",
            parse_mode='Markdown'
        )
        return
    
    priority_str = context.args[0].lower()
    
    priority_map = {
        'critical': Priority.CRITICAL,
        'high': Priority.HIGH,
        'medium': Priority.MEDIUM,
        'low': Priority.LOW
    }
    
    if priority_str not in priority_map:
        await update.message.reply_text(
            f"❌ Invalid priority: {priority_str}\n\n"
            f"Valid priorities: critical, high, medium, low",
            parse_mode='Markdown'
        )
        return
    
    priority = priority_map[priority_str]
    should_send = orchestrator.should_send_notification(priority)
    
    msg = (
        f"🧪 **PRIORITY TEST**\n\n"
        f"Priority: **{priority_str.upper()}**\n"
        f"Current mode: **{orchestrator.current_mode.value}**\n"
        f"Current regime: **{orchestrator.current_regime.value}**\n\n"
        f"Would send: **{'YES ✅' if should_send else 'NO ❌'}**\n\n"
    )
    
    # Explain why
    if orchestrator.current_mode == BotMode.QUIET:
        msg += "Reason: Quiet mode (only critical)\n"
    elif orchestrator.current_mode == BotMode.NIGHT:
        msg += "Reason: Night mode (only critical)\n"
    else:
        from datetime import datetime
        hour = datetime.now().hour
        if 0 <= hour < 7:
            msg += "Reason: Night hours (only critical)\n"
        elif 9 <= hour < 17:
            msg += "Reason: Busy hours (critical + high)\n"
        else:
            msg += "Reason: Normal hours (all priorities)\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current orchestrator settings."""
    if not await is_authorized(update): return
    track_command("settings")
    
    settings = orchestrator.get_current_settings()
    
    msg = (
        f"⚙️ **CURRENT SETTINGS**\n\n"
        f"**Regime:** {orchestrator.current_regime.value.replace('_', ' ').title()}\n"
        f"**Mode:** {orchestrator.current_mode.value.title()}\n\n"
        f"**Active Configuration:**\n"
        f"• Alert sensitivity: {settings['alert_sensitivity']}\n"
        f"• Scan frequency: Every {settings['scan_frequency_minutes']} min\n"
        f"• Scanner focus: {settings['scanner_focus']}\n"
        f"• Briefing tone: {settings['briefing_tone']}\n"
        f"• Portfolio advice: {settings['portfolio_advice']}\n"
        f"• Message throttle: {settings['message_throttle']}\n\n"
        f"💡 Use `/mode` to change operating mode\n"
        f"💡 Use `/regime` to see regime analysis"
    )
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def claude_prompt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the current Claude system prompt addition (for debugging)."""
    if not await is_authorized(update): return
    track_command("claudeprompt")
    
    prompt_addition = orchestrator.get_claude_system_prompt_addition()
    
    if prompt_addition:
        msg = (
            f"🤖 **CLAUDE SYSTEM PROMPT ADDITION**\n\n"
            f"Current regime: **{orchestrator.current_regime.value.replace('_', ' ').title()}**\n\n"
            f"```\n{prompt_addition}\n```"
        )
    else:
        msg = "No system prompt addition (regime unknown)"
    
    await update.message.reply_text(msg, parse_mode='Markdown')
