"""
Telegram handlers for Event Impact Predictor
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def calendar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /calendar [days]
    
    Show upcoming events calendar
    
    Examples:
    /calendar - Next 30 days
    /calendar 60 - Next 60 days
    """
    try:
        # Parse days argument
        days = 30
        if context.args:
            try:
                days = int(context.args[0])
                if days < 1 or days > 90:
                    await update.message.reply_text(
                        "❌ Days must be between 1 and 90"
                    )
                    return
            except ValueError:
                await update.message.reply_text(
                    "❌ Invalid number. Usage: `/calendar [days]`",
                    parse_mode='Markdown'
                )
                return
        
        # Send loading message
        status_msg = await update.message.reply_text(
            f"📅 Loading event calendar (next {days} days)...",
            parse_mode='Markdown'
        )
        
        # Get event predictor
        predictor = context.bot_data.get('event_predictor')
        if not predictor:
            await status_msg.edit_text(
                "❌ Event predictor not initialized. Contact admin."
            )
            return
        
        # Get events
        events = await predictor.track_upcoming_events(days)
        
        # Format message
        message = predictor.format_calendar_message(events, days)
        
        await status_msg.edit_text(message, parse_mode='Markdown')
        
        logger.info(f"Calendar displayed: {len(events)} events")
        
    except Exception as e:
        logger.error(f"Calendar command failed: {e}")
        await update.message.reply_text(
            f"❌ Failed to load calendar: {str(e)}"
        )


async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /predict [SYMBOL] [event_type]
    
    Analyze impact of upcoming events for a symbol
    
    Examples:
    /predict ARB unlock
    /predict ETH upgrade
    /predict BTC macro
    """
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ Usage: `/predict [SYMBOL] [event_type]`\n\n"
                "Event types: unlock, upgrade, macro, expiry\n\n"
                "Examples:\n"
                "• `/predict ARB unlock`\n"
                "• `/predict ETH upgrade`\n"
                "• `/predict BTC macro`",
                parse_mode='Markdown'
            )
            return
        
        symbol = context.args[0].upper()
        event_type = context.args[1].lower() if len(context.args) > 1 else None
        
        # Send loading message
        status_msg = await update.message.reply_text(
            f"🔮 Analyzing upcoming events for {symbol}...",
            parse_mode='Markdown'
        )
        
        # Get event predictor
        predictor = context.bot_data.get('event_predictor')
        if not predictor:
            await status_msg.edit_text(
                "❌ Event predictor not initialized. Contact admin."
            )
            return
        
        # Get events for symbol
        events = await predictor.get_events_for_symbol(symbol, days_ahead=60)
        
        # Filter by type if specified
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if not events:
            await status_msg.edit_text(
                f"📅 No upcoming events found for {symbol}" +
                (f" (type: {event_type})" if event_type else "")
            )
            return
        
        # Analyze first event (most imminent)
        event = events[0]
        analysis = await predictor.analyze_event_impact(event)
        
        # Format message
        message = predictor.format_event_analysis(analysis)
        
        # Add other events if multiple
        if len(events) > 1:
            message += f"\n\n**Other upcoming events:**\n"
            for e in events[1:4]:  # Show up to 3 more
                days_until = (e.date - datetime.now()).days
                message += f"• {e.title} ({e.date.strftime('%b %d')}, {days_until}d)\n"
        
        await status_msg.edit_text(message, parse_mode='Markdown')
        
        logger.info(f"Event prediction for {symbol}: {event.title}")
        
    except Exception as e:
        logger.error(f"Predict command failed: {e}")
        await update.message.reply_text(
            f"❌ Prediction failed: {str(e)}"
        )


async def imminent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /imminent
    
    Show events happening in the next 7 days
    """
    try:
        # Send loading message
        status_msg = await update.message.reply_text(
            "⚠️ Checking imminent events (next 7 days)...",
            parse_mode='Markdown'
        )
        
        # Get event predictor
        predictor = context.bot_data.get('event_predictor')
        if not predictor:
            await status_msg.edit_text(
                "❌ Event predictor not initialized. Contact admin."
            )
            return
        
        # Get imminent events
        events = await predictor.get_imminent_events(days_threshold=7)
        
        if not events:
            await status_msg.edit_text(
                "✅ No critical events in the next 7 days"
            )
            return
        
        # Format message
        msg = "⚠️ **IMMINENT EVENTS** (Next 7 days)\n\n"
        
        for event in events:
            from datetime import datetime
            days_until = (event.date - datetime.now()).days
            
            direction_emoji = {
                'bearish': '📉',
                'bullish': '📈',
                'neutral': '➡️'
            }.get(event.predicted_direction, '❓')
            
            msg += f"{direction_emoji} **{event.symbol}** - {event.title}\n"
            msg += f"📅 {event.date.strftime('%b %d, %Y')} ({days_until} days)\n"
            msg += f"💥 Impact: {event.impact_score:.0f}/10 | Confidence: {event.confidence*100:.0f}%\n"
            msg += f"📊 {event.description}\n"
            msg += f"📖 Pattern: {event.historical_pattern}\n\n"
        
        msg += "💡 Use `/predict [SYMBOL]` for detailed analysis"
        
        await status_msg.edit_text(msg, parse_mode='Markdown')
        
        logger.info(f"Imminent events: {len(events)}")
        
    except Exception as e:
        logger.error(f"Imminent command failed: {e}")
        await update.message.reply_text(
            f"❌ Failed to check imminent events: {str(e)}"
        )


# Register handlers
def register_event_handlers(application):
    """Register all event prediction command handlers"""
    from telegram.ext import CommandHandler
    
    application.add_handler(CommandHandler("calendar", calendar_command))
    application.add_handler(CommandHandler("predict", predict_command))
    application.add_handler(CommandHandler("imminent", imminent_command))
    
    logger.info("Event prediction handlers registered")
