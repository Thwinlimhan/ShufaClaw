import logging
from telegram import Update
from telegram.ext import ContextTypes
from crypto_agent.intelligence.hub import IntelligenceHub, format_unified_recommendation

logger = logging.getLogger(__name__)

# Note: In a real bot, you'd get these components from a central state (bot_data)
# But for now, we simulate the structure to register them.
COMPONENTS = {
    # 'ta_service': TAService(),
    # 'onchain_service': OnChainService(),
    # 'news_service': NewsService(),
    # etc.
}

async def hub_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View the unified intelligence hub status."""
    hub = context.bot_data.get('intelligence_hub')
    if not hub:
        hub = IntelligenceHub(context.bot_data)
        
    agenda = await hub.generate_daily_agenda(update.effective_user.id)
    
    message = "🧠 UNIFIED INTELLIGENCE HUB\n\n"
    message += f"Date: {agenda['date']}\n"
    message += f"Priority Actions: {len(agenda['priority_actions'])}\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if agenda['priority_actions']:
        message += "🎯 PRIORITY ACTIONS:\n"
        for i, task in enumerate(agenda['priority_actions'][:3], 1):
            message += f"{i}. {task['symbol']} ({task['action']})\n"
            message += f"   Confidence: {task['confidence']:.0f}%\n"
            message += f"   Reason: {task['reason']}\n\n"
            
    message += "📅 UPCOMING EVENTS:\n"
    for event in agenda['alerts'][:2]:
        message += f"• {event['time']} {event['event']} ({event['impact']})\n"
        
    message += "\nUse /signals [coin] for deep dive analysis."
    
    await update.message.reply_text(message)

async def signals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deep dive into all signals for a coin: /signals [coin]"""
    if not context.args:
        await update.message.reply_text("Usage: /signals [coin]")
        return
        
    symbol = context.args[0].upper()
    hub = context.bot_data.get('intelligence_hub')
    if not hub:
        hub = IntelligenceHub(context.bot_data)
    
    # Process
    msg = await update.message.reply_text(f"Gathering all intelligence for {symbol}... 🛰️")
    
    try:
        rec = await hub.generate_unified_signal(symbol)
        formatted = await format_unified_recommendation(rec)
        await msg.edit_text(formatted)
    except Exception as e:
        logger.error(f"Intelligence hub error for {symbol}: {e}")
        await msg.edit_text(f"Error gathering signals for {symbol}. {e}")

async def agenda_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View your daily action agenda."""
    hub = context.bot_data.get('intelligence_hub')
    if not hub:
        hub = IntelligenceHub(context.bot_data)
        
    agenda = await hub.generate_daily_agenda(update.effective_user.id)
    
    message = "📋 **DAILY ACTION AGENDA**\n\n"
    
    # 1. Trading Priorities
    if agenda['priority_actions']:
        message += "🎯 **TRADING OPPORTUNITIES**\n"
        for i, action in enumerate(agenda['priority_actions'][:3], 1):
            message += f"{i}. {action['action']} {action['symbol']} (Conf: {action['confidence']:.0f}%)\n"
            message += f"   Reason: {action['reason']}\n"
        message += "\n"
    
    # 2. Airdrop Tasks
    if agenda.get('airdrop_tasks'):
        message += "🪂 **AIRDROP TASKS**\n"
        for task in agenda['airdrop_tasks']:
            message += f"• [{task['protocol']}] {task['task']} (Prio: {task['priority']})\n"
        message += "\n"
    
    # 3. Watchlist
    if agenda['watchlist']:
        message += "🔭 **WATChLIST**\n"
        for item in agenda['watchlist'][:3]:
            message += f"• {item['symbol']} - {item['reason']}\n"
        message += "\n"
    
    # 4. Alerts & Events
    if agenda['alerts']:
        message += "📅 **UPCOMING EVENTS**\n"
        for event in agenda['alerts']:
            message += f"• {event['time']}: {event['event']} ({event['impact']})\n"
        message += "\n"
    
    # 5. Review
    message += "📊 **SYSTEM REVIEW**\n"
    review = agenda['review']
    message += f"• Open Positions: {review['open_positions']}\n"
    message += f"• Recommendation: {review['action_needed']}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def weekly_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate the comprehensive weekly intelligence report."""
    hub = context.bot_data.get('intelligence_hub')
    if not hub:
        hub = IntelligenceHub(context.bot_data)
        
    report = await hub.generate_weekly_intelligence_report(update.effective_user.id)
    
    message = f"📊 WEEKLY INTELLIGENCE REPORT ({report['week']})\n\n"
    
    message += "🪐 MARKET SUMMARY:\n"
    sumry = report['market_summary']
    message += f"Regime: {sumry['regime']}\n"
    message += f"Fear & Greed: {sumry['fear_greed']} ({sumry['sentiment']})\n"
    message += f"BTC Change: {sumry['btc_change']}\n\n"
    
    message += "🎯 TOP OPPORTUNITIES:\n"
    for opp in report['top_opportunities'][:3]:
        message += f"• {opp['symbol']}: {opp['action']} (Conf: {opp['confidence']:.0f}%)\n"
    message += "\n"
    
    message += "⚠️ RISK ASSESSMENT:\n"
    risk = report['risk_assessment']
    message += f"Risk level: {risk['overall_risk']}\n"
    message += f"Heat: {risk['portfolio_heat']}\n"
    for rec in risk['recommendations'][:2]:
        message += f"-> {rec}\n"
    
    message += "\nUse /backup to export all weekly analytics."
    
    await update.message.reply_text(message)
