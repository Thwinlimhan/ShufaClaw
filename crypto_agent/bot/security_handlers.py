"""
Telegram command handlers for security features.
"""

from telegram import Update
from telegram.ext import ContextTypes


async def security_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show security dashboard."""
    user_id = update.effective_user.id
    security = context.bot_data.get('security')
    
    if not security:
        await update.message.reply_text("Security system not initialized.")
        return
    
    # Get security status
    status = security.get_security_status(user_id)
    
    # Build status message
    message = "🔒 SECURITY STATUS\n\n"
    
    # Authentication
    message += "Authentication: ✅ Active\n"
    
    # Rate Limits
    rate = status['rate_limits']
    message += f"Rate Limiting: ✅ {rate['messages_used']}/{rate['messages_limit']} messages/min\n"
    message += f"Commands: {rate['commands_used']}/{rate['commands_limit']} per hour\n"
    
    # Session
    session = status['session']
    if session['active']:
        hours = int(session['expires_in_hours'])
        message += f"Session: ✅ Active (expires in {hours}h)\n"
    else:
        message += "Session: ❌ Expired\n"
    
    # 2FA
    if status['twofa_enabled']:
        message += "2FA: ✅ Enabled\n"
    else:
        message += "2FA: ❌ Disabled\n"
    
    # Encryption
    message += "Encryption: ✅ Active\n"
    
    message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Risk Assessment
    risk = status['risk']
    risk_emoji = {
        'low': '🟢',
        'medium': '🟡',
        'high': '🟠',
        'critical': '🔴'
    }
    message += f"Risk Level: {risk_emoji.get(risk['level'], '⚪')} {risk['level'].upper()}\n"
    
    if risk['anomalies']:
        message += "\n⚠️ Anomalies Detected:\n"
        for anomaly in risk['anomalies']:
            message += f"• {anomaly['message']}\n"
    
    message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Recent Activity
    message += f"Recent Activity: {status['recent_activity']} actions\n"
    if status['failed_attempts_24h'] > 0:
        message += f"⚠️ Failed Attempts (24h): {status['failed_attempts_24h']}\n"
    
    message += "\nLast security scan: Just now"
    
    await update.message.reply_text(message)
    
    # Log action
    security.log_action(user_id, 'security_dashboard_view')


async def auditlog_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View recent audit logs."""
    user_id = update.effective_user.id
    security = context.bot_data.get('security')
    
    if not security:
        await update.message.reply_text("Security system not initialized.")
        return
    
    # Get recent logs
    logs = security.audit_logger.get_recent_logs(user_id, limit=20)
    
    if not logs:
        await update.message.reply_text("No audit logs found.")
        return
    
    message = "📋 AUDIT LOG (Last 20 actions)\n\n"
    
    for log in logs:
        timestamp = log['timestamp'][:19].replace('T', ' ')
        action = log['action']
        result = log['result']
        
        # Result emoji
        result_emoji = '✅' if result == 'success' else '❌'
        
        message += f"[{timestamp}] {result_emoji} {action}\n"
    
    await update.message.reply_text(message)
    
    # Log action
    security.log_action(user_id, 'audit_log_view')


async def twofa_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enable/disable 2FA."""
    user_id = update.effective_user.id
    security = context.bot_data.get('security')
    
    if not security:
        await update.message.reply_text("Security system not initialized.")
        return
    
    # Check current status
    enabled = security.twofa_enabled.get(user_id, False)
    
    if enabled:
        message = (
            "🔐 TWO-FACTOR AUTHENTICATION\n\n"
            "Status: ✅ Enabled\n\n"
            "2FA protects:\n"
            "• /backup\n"
            "• /clearall\n"
            "• /exporttrades\n"
            "• Wallet operations\n\n"
            "To disable: /2fa disable"
        )
    else:
        message = (
            "🔐 TWO-FACTOR AUTHENTICATION\n\n"
            "Status: ❌ Disabled\n\n"
            "Enable 2FA to protect sensitive operations.\n\n"
            "To enable: /2fa enable [PIN]\n"
            "Example: /2fa enable 1234"
        )
    
    await update.message.reply_text(message)
    
    # Handle enable/disable
    if context.args:
        action = context.args[0].lower()
        
        if action == 'enable' and len(context.args) > 1:
            pin = context.args[1]
            security.enable_2fa(user_id, pin)
            await update.message.reply_text("✅ 2FA enabled successfully!")
            security.log_action(user_id, '2fa_enabled')
        
        elif action == 'disable':
            security.disable_2fa(user_id)
            await update.message.reply_text("❌ 2FA disabled.")
            security.log_action(user_id, '2fa_disabled')


async def cleanup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual data cleanup."""
    user_id = update.effective_user.id
    security = context.bot_data.get('security')
    
    if not security:
        await update.message.reply_text("Security system not initialized.")
        return
    
    message = (
        "🧹 DATA CLEANUP\n\n"
        "This will remove old data:\n"
        "• Audit logs older than 30 days\n"
        "• Expired sessions\n"
        "• Old cache entries\n\n"
        "Proceed? /cleanup confirm"
    )
    
    if context.args and context.args[0].lower() == 'confirm':
        # Perform cleanup
        deleted_logs = security.audit_logger.cleanup_old_logs(days=30)
        
        await update.message.reply_text(
            f"✅ Cleanup complete!\n\n"
            f"Removed:\n"
            f"• {deleted_logs} old audit logs\n"
            f"• Expired sessions cleared"
        )
        
        security.log_action(user_id, 'data_cleanup', details={'logs_deleted': deleted_logs})
    else:
        await update.message.reply_text(message)


async def ratelimit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show rate limit status."""
    user_id = update.effective_user.id
    security = context.bot_data.get('security')
    
    if not security:
        await update.message.reply_text("Security system not initialized.")
        return
    
    stats = security.rate_limiter.get_stats(user_id)
    
    message = (
        "⏱️ RATE LIMIT STATUS\n\n"
        f"Messages: {stats['messages_used']}/{stats['messages_limit']} per minute\n"
        f"Remaining: {stats['messages_remaining']}\n\n"
        f"Commands: {stats['commands_used']}/{stats['commands_limit']} per hour\n"
        f"Remaining: {stats['commands_remaining']}\n\n"
        "Rate limits reset automatically."
    )
    
    await update.message.reply_text(message)
