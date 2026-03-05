import logging
from telegram import Update
from telegram.ext import ContextTypes
from crypto_agent.intelligence.arbitrage_scanner import ArbitrageScanner
from crypto_agent.intelligence.behavior_analyzer import BehaviorAnalyzer
from crypto_agent.intelligence.prompt_optimizer import PromptOptimizer
from crypto_agent.intelligence.infrastructure_advisor import InfrastructureAdvisor
from crypto_agent.intelligence.final_form import FinalFormAnalyzer

logger = logging.getLogger(__name__)

async def arbitrage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scan for arbitrage and premiums: /arbitrage [coin]"""
    symbol = context.args[0].upper() if context.args else "BTC"
    scanner = ArbitrageScanner()
    
    msg = await update.message.reply_text(f"Scanning cross-market arbitrage for {symbol}... 🔍")
    
    try:
        report = await scanner.get_full_arbitrage_report(symbol)
        
        message = f"⚖️ ARBITRAGE & PREMIUMS ({symbol})\n\n"
        
        basis = report['basis']
        if 'spot' in basis:
            message += "📈 FUTURES BASIS (Spot vs Perp):\n"
            message += f"• Spot: ${basis['spot']:,.2f}\n"
            message += f"• Perp: ${basis['perp']:,.2f}\n"
            message += f"• Basis: {basis['basis_pct']}% ({basis['sentiment']})\n\n"
            
        premium = report['premium']
        if 'binance' in premium:
            message += "🏛️ EXCHANGE PREMIUM (Coinbase vs Binance):\n"
            message += f"• Binance: ${premium['binance']:,.2f}\n"
            message += f"• Coinbase: ${premium['coinbase']:,.2f}\n"
            message += f"• Premium: {premium['premium_pct']}% ({premium['interpretation']})\n\n"
            
        peg = report['stable_peg']
        message += f"💵 STABLE PEG (USDT/USDC): {peg['status']} ({peg['price']:.4f})\n"
        
        await msg.edit_text(message)
    except Exception as e:
        logger.error(f"Arbitrage scan error: {e}")
        await msg.edit_text(f"Error scanning arbitrage for {symbol}. {e}")

async def behavior_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View behavioral psychology analysis of your trading."""
    analyzer = BehaviorAnalyzer()
    report = analyzer.generate_full_report()
    
    message = "🧠 TRADING BEHAVIOR ANALYSIS\n\n"
    
    message += "🕒 TIME-OF-DAY PERFORMANCE:\n"
    for slot in report["time_of_day"]:
        if slot['entries'] > 0:
            message += f"• {slot['time']}: {slot['entries']} entries ({slot['win_rate']} Win)\n"
    message += "\n"
    
    message += "🛑 POST-LOSS BEHAVIOR:\n"
    pl = report["post_loss"]
    message += f"• Revenge Patterns: {'⚠️ DETECTED' if pl['pattern_detected'] else '✅ NONE'}\n"
    message += f"• Recommendation: {pl['suggestion']}\n\n"
    
    message += "📋 CONSISTENCY GRADE:\n"
    c = report["consistency"]
    message += f"• Grade: {c.get('grade', 'N/A')}\n"
    message += f"• Streak: {c.get('longest_streak', 0)} days\n"
    
    message += "\nUse /journal to log more honest data for better analysis."
    
    await update.message.reply_text(message)

async def infrastructure_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View infrastructure ROI recommendations."""
    advisor = InfrastructureAdvisor()
    report = advisor.analyze_infrastructure_needs()
    
    message = "🏗️ INFRASTRUCTURE DECISION ADVISOR\n\n"
    
    state = report["current_state"]
    message += "📊 CURRENT STATE:\n"
    message += f"• DB Size: {state['database_size_mb']}MB\n"
    message += f"• API Costs: ~${state['api_costs']['estimated_monthly_usd']}/month\n\n"
    
    message += "💡 RECOMMENDATIONS:\n"
    for rec in report["recommendations"]:
        if rec["priority"] in ["HIGH", "CRITICAL"]:
            message += f"• {rec['upgrade']} ({rec['priority']})\n"
            message += f"  Verdict: {rec['verdict']}\n"
            message += f"  Reason: {rec['reason']}\n\n"
            
    message += "Use /status to check current system health."
    
    await update.message.reply_text(message)

async def final_form_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View the 'Final Form' system assessment."""
    analyzer = FinalFormAnalyzer()
    report = analyzer.generate_final_form_report()
    
    message = "💠 THE FINAL FORM: SYSTEM ASSESSMENT\n\n"
    
    m = report["maturity"]
    message += f"Stage: {m['stage'].upper()}\n"
    message += f"{m['description']}\n"
    message += f"Data Points: {m['total_data']}\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    message += "⭐ HIGHEST LEVERAGE ACTION:\n"
    top = report["highest_leverage_action"]
    if top:
        message += f"• {top['action']}\n"
        message += f"  Impact: {top['impact']} | Why: {top['reason']}\n\n"
        
    message += "🕯️ THE THREE TRUTHS:\n"
    for truth in report["the_three_truths"]:
        message += f"• {truth['truth']}\n"
        
    await update.message.reply_text(message)

async def prompts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View prompt optimization performance: /prompts [name]"""
    optimizer = PromptOptimizer()
    
    if not context.args:
        report = optimizer.generate_evolution_report()
        message = "🤖 PROMPT EVOLUTION TRACKER\n\n"
        message += f"Tracking {report['total_prompts_tracked']} prompt families.\n"
        message += "Use `/prompts [name]` for details.\n\n"
        message += "Prompt Families:\n"
        for name in report["prompts"].keys():
            message += f"• `{name}`\n"
        await update.message.reply_text(message)
        return
        
    name = context.args[0]
    perf = optimizer.get_prompt_performance(name)
    
    if not perf:
        await update.message.reply_text(f"Prompt '{name}' not found.")
        return
        
    message = f"🤖 PERFORMANCE: {name.upper()}\n\n"
    for p in perf:
        status = "✅ ACTIVE" if p['is_active'] else "❌ INACTIVE"
        message += f"V{p['version']} ({status}):\n"
        message += f"• Helpful: {p['helpfulness']} | Action Rate: {p['action_rate']}\n"
        message += f"• Used: {p['times_used']}x\n\n"
        
    await update.message.reply_text(message)
