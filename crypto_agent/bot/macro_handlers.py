"""
Telegram handlers for Macro Correlation Engine
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def macro_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /macro
    
    Show macro market dashboard
    """
    try:
        # Send loading message
        status_msg = await update.message.reply_text(
            "📊 Loading macro dashboard...",
            parse_mode='Markdown'
        )
        
        # Get macro monitor
        macro_monitor = context.bot_data.get('macro_monitor')
        if not macro_monitor:
            await status_msg.edit_text(
                "❌ Macro monitor not initialized. Contact admin."
            )
            return
        
        # Fetch macro data
        macro_data = await macro_monitor.fetch_macro_data()
        
        if not macro_data:
            await status_msg.edit_text(
                "❌ Failed to fetch macro data. Try again later."
            )
            return
        
        # Format message
        message = macro_monitor.format_macro_dashboard(macro_data)
        
        await status_msg.edit_text(message, parse_mode='Markdown')
        
        logger.info("Macro dashboard displayed")
        
    except Exception as e:
        logger.error(f"Macro command failed: {e}")
        await update.message.reply_text(
            f"❌ Failed to load macro dashboard: {str(e)}"
        )


async def correlation_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /correlation [SYMBOL]
    
    Show correlations between crypto and macro assets
    
    Examples:
    /correlation BTC
    /correlation ETH
    """
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ Usage: `/correlation [SYMBOL]`\n\n"
                "Examples:\n"
                "• `/correlation BTC`\n"
                "• `/correlation ETH`",
                parse_mode='Markdown'
            )
            return
        
        symbol = context.args[0].upper()
        
        # Send loading message
        status_msg = await update.message.reply_text(
            f"📊 Calculating {symbol} correlations...",
            parse_mode='Markdown'
        )
        
        # Get macro monitor
        macro_monitor = context.bot_data.get('macro_monitor')
        if not macro_monitor:
            await status_msg.edit_text(
                "❌ Macro monitor not initialized. Contact admin."
            )
            return
        
        # Calculate correlations
        correlations = await macro_monitor.calculate_correlations(symbol, lookback_days=90)
        
        if not correlations:
            await status_msg.edit_text(
                f"❌ Failed to calculate correlations for {symbol}"
            )
            return
        
        # Format message
        message = macro_monitor.format_correlation_report(correlations)
        
        # Add interpretation
        message += "\n**Legend:**\n"
        message += "🔴 Strong Positive | 🔵 Strong Negative\n"
        message += "🟠 Moderate Positive | 🟣 Moderate Negative\n"
        message += "⚪ Weak Correlation\n\n"
        message += "💡 Use `/regime` to see current macro environment"
        
        await status_msg.edit_text(message, parse_mode='Markdown')
        
        logger.info(f"Correlations displayed for {symbol}")
        
    except Exception as e:
        logger.error(f"Correlation command failed: {e}")
        await update.message.reply_text(
            f"❌ Failed to calculate correlations: {str(e)}"
        )


async def regime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /regime
    
    Show current macro regime and crypto implications
    """
    try:
        # Send loading message
        status_msg = await update.message.reply_text(
            "🌡️ Analyzing macro regime...",
            parse_mode='Markdown'
        )
        
        # Get macro monitor
        macro_monitor = context.bot_data.get('macro_monitor')
        if not macro_monitor:
            await status_msg.edit_text(
                "❌ Macro monitor not initialized. Contact admin."
            )
            return
        
        # Detect regime
        regime = await macro_monitor.detect_macro_regime()
        
        if regime.get('regime') == 'unknown':
            await status_msg.edit_text(
                "❌ Unable to determine macro regime. Insufficient data."
            )
            return
        
        # Format message
        message = macro_monitor.format_regime_report(regime)
        
        # Add context
        if 'all_scores' in regime:
            message += "\n**Regime Scores:**\n"
            for reg, score in sorted(regime['all_scores'].items(), key=lambda x: x[1], reverse=True):
                bar = '█' * int(score * 10)
                message += f"{reg.replace('_', ' ').title()}: {bar} {score*100:.0f}%\n"
        
        await status_msg.edit_text(message, parse_mode='Markdown')
        
        logger.info(f"Regime displayed: {regime['regime']}")
        
    except Exception as e:
        logger.error(f"Regime command failed: {e}")
        await update.message.reply_text(
            f"❌ Failed to analyze regime: {str(e)}"
        )


async def dxy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /dxy
    
    Analyze US Dollar cycle and crypto implications
    """
    try:
        # Send loading message
        status_msg = await update.message.reply_text(
            "💵 Analyzing dollar cycle...",
            parse_mode='Markdown'
        )
        
        # Get macro monitor
        macro_monitor = context.bot_data.get('macro_monitor')
        if not macro_monitor:
            await status_msg.edit_text(
                "❌ Macro monitor not initialized. Contact admin."
            )
            return
        
        # Analyze dollar cycle
        analysis = await macro_monitor.analyze_dollar_cycle()
        
        if analysis.get('status') == 'unavailable':
            await status_msg.edit_text(
                "❌ Dollar data unavailable"
            )
            return
        
        # Format message
        msg = "💵 **US DOLLAR CYCLE ANALYSIS**\n\n"
        msg += f"**Current DXY:** {analysis['current_dxy']:.2f}\n"
        msg += f"**50-Week MA:** {analysis['dxy_50w_ma']:.2f}\n"
        msg += f"**vs MA:** {analysis['vs_ma']}\n"
        msg += f"**30D Change:** {analysis['change_30d']}\n\n"
        
        msg += f"**Cycle Phase:** {analysis['phase']}\n"
        msg += f"**Crypto Outlook:** {analysis['crypto_outlook']}\n"
        msg += f"**Confidence:** {analysis['confidence']*100:.0f}%\n\n"
        
        msg += f"**Note:**\n{analysis['note']}"
        
        await status_msg.edit_text(msg, parse_mode='Markdown')
        
        logger.info("Dollar cycle analysis displayed")
        
    except Exception as e:
        logger.error(f"DXY command failed: {e}")
        await update.message.reply_text(
            f"❌ Failed to analyze dollar cycle: {str(e)}"
        )


# Register handlers
def register_macro_handlers(application):
    """Register all macro correlation command handlers"""
    from telegram.ext import CommandHandler
    
    application.add_handler(CommandHandler("macro", macro_command))
    application.add_handler(CommandHandler("correlation", correlation_command))
    application.add_handler(CommandHandler("regime", regime_command))
    application.add_handler(CommandHandler("dxy", dxy_command))
    
    logger.info("Macro correlation handlers registered")
