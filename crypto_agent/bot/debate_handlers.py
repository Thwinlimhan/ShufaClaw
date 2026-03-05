"""
Telegram handlers for Multi-Analyst Debate System
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def debate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /debate [COIN] [optional question]
    
    Examples:
    /debate ETH
    /debate BTC should I sell at $100k?
    """
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ Usage: `/debate [COIN] [optional question]`\n\n"
                "Examples:\n"
                "• `/debate ETH`\n"
                "• `/debate BTC should I sell at $100k?`\n"
                "• `/debate SOL is this a good entry?`",
                parse_mode='Markdown'
            )
            return
        
        # Parse arguments
        symbol = context.args[0].upper()
        question = " ".join(context.args[1:]) if len(context.args) > 1 else None
        
        # Send initial message
        status_msg = await update.message.reply_text(
            f"🎭 **Starting analyst debate for {symbol}...**\n\n"
            "⏳ Gathering data...",
            parse_mode='Markdown'
        )
        
        # Get debate system
        debate_system = context.bot_data.get('debate_system')
        if not debate_system:
            await status_msg.edit_text(
                "❌ Debate system not initialized. Contact admin."
            )
            return
        
        # Update status
        await status_msg.edit_text(
            f"🎭 **Analyst debate for {symbol}**\n\n"
            "✅ Data gathered\n"
            "⏳ Bull analyst analyzing...",
            parse_mode='Markdown'
        )
        
        # Run full debate
        result = await debate_system.run_debate(symbol, question)
        
        # Format and send result
        message = debate_system.format_debate_message(result, mode='full')
        
        # Split if too long (Telegram limit ~4096 chars)
        if len(message) > 4000:
            # Send in parts
            parts = _split_message(message, 4000)
            await status_msg.delete()
            for part in parts:
                await update.message.reply_text(part, parse_mode='Markdown')
        else:
            await status_msg.edit_text(message, parse_mode='Markdown')
        
        logger.info(f"Debate completed for {symbol}")
        
    except Exception as e:
        logger.error(f"Debate command failed: {e}")
        await update.message.reply_text(
            f"❌ Debate failed: {str(e)}\n\n"
            "Try again or contact support."
        )


async def quickdebate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /quickdebate [COIN] [optional question]
    
    Faster version: opening statements + synthesis only
    """
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ Usage: `/quickdebate [COIN] [optional question]`\n\n"
                "Examples:\n"
                "• `/quickdebate ETH`\n"
                "• `/quickdebate BTC should I buy now?`",
                parse_mode='Markdown'
            )
            return
        
        # Parse arguments
        symbol = context.args[0].upper()
        question = " ".join(context.args[1:]) if len(context.args) > 1 else None
        
        # Send initial message
        status_msg = await update.message.reply_text(
            f"⚡ **Quick debate for {symbol}...**\n\n"
            "⏳ Analyzing (60 seconds)...",
            parse_mode='Markdown'
        )
        
        # Get debate system
        debate_system = context.bot_data.get('debate_system')
        if not debate_system:
            await status_msg.edit_text(
                "❌ Debate system not initialized. Contact admin."
            )
            return
        
        # Run quick debate
        result = await debate_system.quick_debate(symbol, question)
        
        # Format and send result
        message = debate_system.format_debate_message(result, mode='quick')
        
        # Split if too long
        if len(message) > 4000:
            parts = _split_message(message, 4000)
            await status_msg.delete()
            for part in parts:
                await update.message.reply_text(part, parse_mode='Markdown')
        else:
            await status_msg.edit_text(message, parse_mode='Markdown')
        
        logger.info(f"Quick debate completed for {symbol}")
        
    except Exception as e:
        logger.error(f"Quick debate command failed: {e}")
        await update.message.reply_text(
            f"❌ Quick debate failed: {str(e)}\n\n"
            "Try again or contact support."
        )


def _split_message(message: str, max_length: int = 4000) -> list:
    """Split long message into parts at logical boundaries"""
    if len(message) <= max_length:
        return [message]
    
    parts = []
    current_part = ""
    
    # Split by double newlines (paragraphs)
    paragraphs = message.split('\n\n')
    
    for para in paragraphs:
        if len(current_part) + len(para) + 2 <= max_length:
            current_part += para + '\n\n'
        else:
            if current_part:
                parts.append(current_part.strip())
            current_part = para + '\n\n'
    
    if current_part:
        parts.append(current_part.strip())
    
    return parts


# Register handlers
def register_debate_handlers(application):
    """Register all debate command handlers"""
    from telegram.ext import CommandHandler
    
    application.add_handler(CommandHandler("debate", debate_command))
    application.add_handler(CommandHandler("quickdebate", quickdebate_command))
    
    logger.info("Debate handlers registered")
