"""
Telegram handlers for options intelligence commands.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from crypto_agent.derivatives.options_monitor import get_options_monitor

logger = logging.getLogger(__name__)


async def options_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /options command - show options intelligence.
    
    Usage:
        /options - BTC options data
        /options ETH - ETH options data
        /options SOL - SOL options data
    """
    try:
        # Parse symbol
        symbol = "BTC"
        if context.args and len(context.args) > 0:
            symbol = context.args[0].upper()
        
        # Validate symbol
        if symbol not in ["BTC", "ETH", "SOL"]:
            await update.message.reply_text(
                "❌ Invalid symbol. Supported: BTC, ETH, SOL\n"
                "Usage: /options [BTC|ETH|SOL]"
            )
            return
        
        # Send loading message
        loading_msg = await update.message.reply_text(
            f"📊 Fetching options data for {symbol}..."
        )
        
        # Get options monitor
        monitor = get_options_monitor()
        
        # Fetch data
        data = monitor.get_options_data(symbol)
        
        if not data:
            await loading_msg.edit_text(
                f"❌ Unable to fetch options data for {symbol}.\n"
                "Deribit API may be unavailable."
            )
            return
        
        # Format report
        report = monitor.format_options_report(data)
        
        # Check for alerts
        alerts = monitor.check_for_alerts(data)
        if alerts:
            report += "\n\n🔔 ALERTS:\n" + "\n".join(alerts)
        
        # Send report
        await loading_msg.edit_text(report)
        
    except Exception as e:
        logger.error(f"Error in options command: {e}")
        await update.message.reply_text(
            "❌ Error fetching options data. Please try again."
        )


async def maxpain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /maxpain command - show max pain level.
    
    Usage:
        /maxpain - BTC max pain
        /maxpain ETH - ETH max pain
    """
    try:
        # Parse symbol
        symbol = "BTC"
        if context.args and len(context.args) > 0:
            symbol = context.args[0].upper()
        
        if symbol not in ["BTC", "ETH", "SOL"]:
            await update.message.reply_text(
                "❌ Invalid symbol. Supported: BTC, ETH, SOL"
            )
            return
        
        # Get monitor
        monitor = get_options_monitor()
        
        # Fetch data
        data = monitor.get_options_data(symbol)
        
        if not data:
            await update.message.reply_text(
                f"❌ Unable to fetch max pain for {symbol}"
            )
            return
        
        # Calculate distance
        pain_distance = ((data.max_pain - data.current_price) / data.current_price) * 100
        direction = "above" if pain_distance > 0 else "below"
        
        # Format message
        message = f"""🎯 MAX PAIN — {symbol}

Current Price: ${data.current_price:,.0f}
Max Pain: ${data.max_pain:,.0f}

Distance: {abs(pain_distance):.1f}% {direction} current price

{"⚠️ Significant distance - price may gravitate toward max pain near expiry" if abs(pain_distance) > 5 else "✓ Close to max pain level"}

💡 Max pain is the strike where most options expire worthless.
Price tends to gravitate toward this level as expiry approaches.
"""
        
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"Error in maxpain command: {e}")
        await update.message.reply_text(
            "❌ Error fetching max pain data."
        )


async def iv_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /iv command - show implied volatility.
    
    Usage:
        /iv - BTC IV
        /iv ETH - ETH IV
    """
    try:
        # Parse symbol
        symbol = "BTC"
        if context.args and len(context.args) > 0:
            symbol = context.args[0].upper()
        
        if symbol not in ["BTC", "ETH", "SOL"]:
            await update.message.reply_text(
                "❌ Invalid symbol. Supported: BTC, ETH, SOL"
            )
            return
        
        # Get monitor
        monitor = get_options_monitor()
        
        # Fetch data
        data = monitor.get_options_data(symbol)
        
        if not data:
            await update.message.reply_text(
                f"❌ Unable to fetch IV for {symbol}"
            )
            return
        
        # Compare to average
        iv_diff = ((data.iv_current - data.iv_30d_avg) / data.iv_30d_avg) * 100
        status = "EXPENSIVE" if data.iv_current > data.iv_30d_avg else "CHEAP"
        
        # Format message
        message = f"""📊 IMPLIED VOLATILITY — {symbol}

Current IV: {data.iv_current*100:.1f}%
30d Average: {data.iv_30d_avg*100:.1f}%

Difference: {iv_diff:+.1f}%
Status: {status}

{"💡 Options are expensive - potential to sell premium" if status == "EXPENSIVE" else "💡 Options are cheap - potential to buy"}

⚡ Current IV vs Historical:
{"High IV = Market expects large moves" if data.iv_current > 1.0 else "Normal IV = Market expects typical volatility"}
"""
        
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"Error in iv command: {e}")
        await update.message.reply_text(
            "❌ Error fetching IV data."
        )


def register_options_handlers(application):
    """Register all options-related command handlers."""
    from telegram.ext import CommandHandler
    
    application.add_handler(CommandHandler("options", options_command))
    application.add_handler(CommandHandler("maxpain", maxpain_command))
    application.add_handler(CommandHandler("iv", iv_command))
    
    logger.info("Options handlers registered")
