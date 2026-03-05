import logging
from telegram import Update
from telegram.ext import ContextTypes
from crypto_agent.core.skill_system import SkillSystem
from crypto_agent.core.evolution_engine import EvolutionEngine

logger = logging.getLogger(__name__)

async def skills_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View the bot's current skills and their performance stats."""
    ss = SkillSystem()
    stats = ss.get_skill_stats()
    
    message = "🛠️ BOT SKILL REGISTRY\n\n"
    
    if not stats:
        message += "No skills registered yet."
    else:
        for stat in stats[:10]:
            status = "✅" if stat['enabled'] else "❌"
            message += f"{status} {stat['name']} ({stat['category'].upper()})\n"
            message += f"   Uses: {stat['uses']} | Win Rate: {stat['win_rate']}\n\n"
            
    message += "💡 Note: Skills trigger automatically based on your questions."
    
    await update.message.reply_text(message)

async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View the current state of the bot's long-term memory."""
    # This would interact with the 7-layer memory system
    message = "🧠 BOT MEMORY STATE\n\n"
    message += "Working Memory: [BTC, ETH, 4H, Long]\n"
    message += "Short-Term Memory: [Recent RSI values, 24h News]\n"
    message += "Long-Term Memory: [Journaled lessons, Historical biases]\n"
    message += "Procedural Memory: [Risk management protocols, TA flows]\n"
    message += "Semantic Memory: [Asset definitions, Sector mappings]\n"
    message += "Episodic Memory: [Previous trade outcomes, Error logs]\n"
    message += "Sensory Buffer: [Real-time price feed stream]\n"
    message += "\nUse /evolution to see how memory drives learning."
    
    await update.message.reply_text(message)

async def evolution_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View the evolution engine results and self-improvement logs."""
    ee = EvolutionEngine()
    history = ee.get_evolution_history()
    report = ee.get_evolution_report()
    
    message = "🧬 **EVOLUTION ENGINE TRACKER**\n\n"
    
    message += f"📊 **System Status:**\n"
    message += f"• Prediction Accuracy: {report['prediction_accuracy']}\n"
    message += f"• Total Predictions: {report['total_predictions']}\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if report['top_mistakes']:
        message += "⚠️ **RECURRING MISTAKES:**\n"
        for m in report['top_mistakes'][:3]:
            message += f"• {m['category']}: {m['description']} (x{m['repeats']})\n"
        message += "\n"

    if history:
        message += "🎯 **RECENT EVOLUTION STEPS:**\n"
        for h in history[:5]:
            status = "✅" if h['accuracy_score'] >= 0.7 else "🔬"
            message += f"{status} {h['pattern_name']}\n"
            message += f"  Score: {h['accuracy_score']*100:.0f}% | {h['insight']}\n"
    else:
        message += "System is in early calibration phase. Keep using the bot to generate evolution data."
    
    message += "\nUse /skills to see currently active reasoning patterns."
    
    await update.message.reply_text(message, parse_mode='Markdown')
