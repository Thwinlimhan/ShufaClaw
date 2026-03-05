import logging
import json
import os
import aiohttp
from datetime import datetime
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from crypto_agent import config
from crypto_agent.storage import database, backup as backup_service
from crypto_agent.data import prices as price_service, market as market_service, technical as technical_analysis, onchain as onchain_data, news as news_service
from crypto_agent.core import error_handler
from crypto_agent.core.context_builder import build_full_context
from crypto_agent.intelligence import advisor as strategy_advisor, research_agent, portfolio_optimizer, performance_tracker, memory as memory_system
from crypto_agent.journal import reviewer
from crypto_agent.autonomous import reporter as briefing_service
from crypto_agent.autonomous import watcher as wallet_watcher
from crypto_agent.autonomous import smart_money
from crypto_agent.bot import keyboards
from crypto_agent.bot.middleware import is_authorized, track_command, track_error, track_api, metrics, BOT_START_TIME

logger = logging.getLogger(__name__)

# --- CONVERSATION STATES ---
CHOOSING_TYPE, GETTING_S1, GETTING_T1, GETTING_D1, GETTING_OP, GETTING_S2, GETTING_T2, GETTING_D2, GETTING_NAME = range(9)
QS_PORTFOLIO, QS_ALERT, QS_JOURNAL, QS_BRIEFING = range(10, 14)

# --- HELP DATA ---
HELP_SECTIONS = {
    "portfolio": {
        "title": "💼 PORTFOLIO COMMANDS",
        "text": (
            "/add [COIN] [AMOUNT] [PRICE]\nAdd a position to track\nExample: `/add BTC 0.5 95000`\n\n"
            "/portfolio\nView all positions with P&L\n\n"
            "/update [COIN] [AMOUNT] [PRICE]\nUpdate an existing position\n\n"
            "/remove [COIN]\nRemove a position"
        )
    },
    "alerts": {
        "title": "🔔 ALERT COMMANDS",
        "text": (
            "/alert [COIN] [PRICE] [above/below]\nSet a price alert\nExample: `/alert BTC 100000 above`\n\n"
            "/alerts — View all active alerts\n\n"
            "/cancelalert [ID] — Cancel an alert\n\n"
            "/complexalert — Set multi-condition alert"
        )
    },
    "market": {
        "title": "📊 MARKET & ON-CHAIN",
        "text": (
            "/market — Overall market intelligence\n\n"
            "/top — Top 20 cryptos by market cap\n\n"
            "/fear — Crypto Fear & Greed Index\n"
            "/onchain — Blockchain network intelligence\n\n"
            "/gas — Real-time ETH gas prices\n\n"
            "/smartmoney — Track whale & exchange moves\n\n"
            "/news [coin] — Latest crypto news"
        )
    },
    "journal": {
        "title": "📔 JOURNAL & NOTES",
        "text": (
            "/log [text] — Add a journal entry\n\n"
            "/journal — View your recent log history\n\n"
            "/note [text] — Save a permanent trading rule\n\n"
            "/notes — List all your saved rules\n\n"
            "/search [keyword] — Search journal & notes"
        )
    },
    "analysis": {
        "title": "🧪 ANALYSIS COMMANDS",
        "text": (
            "/ta [COIN] — Get technical analysis\n\n"
            "/analyze [COIN] — AI Strategic research\n\n"
            "/research [COIN] — Deep autonomous investigation\n\n"
            "/compare [C1] [C2] — Side-by-side battle\n\n"
            "/optimize — Full portfolio optimization\n\n"
            "/risk — Quick risk dashboard\n\n"
            "/rebalance [target] — Calculate rebalance trades\n\n"
            "/accuracy — View AI prediction track record\n\n"
            "/predictions — List recent AI calls\n\n"
            "/profile — View your inferred trading profile\n\n"
            "/insights — View stored market insights\n\n"
            "/addinsight — Store a new market observation\n\n"
            "/watchlist — Manage auto-research list\n\n"
            "/sentiment — Market mood dashboard\n\n"
            "/stats — View your trading statistics"
        )
    },
    "airdrop": {
        "title": "🪂 AIRDROP COMMANDS",
        "text": (
            "/airdrop — Main intelligence hub\n\n"
            "/airdroptasks — Daily action plan\n\n"
            "/airdropstrategy — AI-driven research briefing\n\n"
            "/linkwallet [address] — Connect your wallet\n\n"
            "/mywallet — View your reputation score\n\n"
            "/recordairdrop — Track your wins"
        )
    },
    "settings": {
        "title": "⚙️ SETTINGS & SYSTEM",
        "text": (
            "/status or /health — Check bot health\n\n"
            "/scanner [on/off] — 24/7 Market Monitor\n\n"
            "/opportunities — Opportunity Radar settings\n\n"
            "/backup — Export all data to file\n\n"
            "/clear — Wipe chat history memory\n\n"
            "/exporttrades — Export journal to CSV"
        )
    }
}

# --- GENERAL COMMANDS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    welcome = (
        "📊 **Welcome to your Crypto Assistant!**\n\n"
        "I am ready to help you analyze the markets and track your portfolio.\n\n"
        "💡 **NEW?** Type `/quickstart` for a 60-second tour!\n\n"
        "Type `/help` to see all commands."
    )
    await update.message.reply_text(welcome, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    track_command("help")
    if context.args:
        topic = context.args[0].lower()
        if topic in HELP_SECTIONS:
            section = HELP_SECTIONS[topic]
            await update.message.reply_text(f"{section['title']}\n\n{section['text']}", parse_mode='Markdown', reply_markup=keyboards.get_back_keyboard())
            return
    msg = "🤖 **SHUFACLAW — HELP MENU**\n\nChoose a category below:"
    await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=keyboards.get_help_menu_keyboard())

async def help_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "help_main":
        await query.edit_message_text("🤖 **SHUFACLAW — HELP MENU**\n\nChoose a category below:", parse_mode='Markdown', reply_markup=keyboards.get_help_menu_keyboard())
    elif query.data.startswith("help_"):
        topic = query.data.replace("help_", "")
        if topic in HELP_SECTIONS:
            section = HELP_SECTIONS[topic]
            await query.edit_message_text(f"{section['title']}\n\n{section['text']}", parse_mode='Markdown', reply_markup=keyboards.get_back_keyboard())

async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    uptime = datetime.now() - BOT_START_TIME
    msg = (
        "🏥 **BOT HEALTH STATUS**\n"
        "──────────────────\n"
        f"⏱ Uptime: {str(uptime).split('.')[0]}\n"
        f"📩 Msgs: {metrics['messages_processed']}\n"
        f"📊 API: {metrics['api_calls_total']} calls\n"
        f"✅ Success: {((metrics['api_calls_total']-metrics['api_calls_failed'])/metrics['api_calls_total']*100 if metrics['api_calls_total']>0 else 100):.1f}%\n"
        f"❌ Errors: {metrics['errors_occurred']}\n"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await health_command(update, context)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    stats = backup_service.BackupService.get_trading_stats()
    await update.message.reply_text(stats, parse_mode='Markdown')

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wipes the local conversation history in the database."""
    if not await is_authorized(update): return
    database.clear_all_messages()
    await update.message.reply_text("🧹 **Memory Cleared!** I have forgotten our previous conversation (local history wiped).", parse_mode='Markdown')

# --- PORTFOLIO HANDLERS ---

async def add_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    track_command("add")
    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text("❌ Usage: `/add BTC 0.5 95000`")
            return
        symbol, qty_str, price_str = args[0].upper(), args[1], args[2]
        if not error_handler.validate_crypto_symbol(symbol):
            raise error_handler.ValidationError("Invalid symbol.")
        qty = error_handler.validate_price(qty_str)
        price_val = error_handler.validate_price(price_str)
        if qty is None or price_val is None:
            raise error_handler.ValidationError("Quantity and price must be numbers.")
        
        notes = " ".join(args[3:]) if len(args) > 3 else None
        database.add_or_update_position(symbol, qty, price_val, notes)
        
        cur_price, _ = await price_service.get_price(symbol)
        track_api(success=True)
        summary = f"✅ **Position Saved!**\n\n🪙 **{symbol}**\nQty: {qty}\nAvg Price: ${price_val:,.2f}"
        if cur_price:
            val = qty * cur_price
            pnl = val - (qty * price_val)
            summary += f"\nCurrent Value: ${val:,.2f} ({pnl:+.2f})"
        await update.message.reply_text(summary, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in /add: {e}")
        track_error()
        await update.message.reply_text(error_handler.format_error_for_user(e))

async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    track_command("portfolio")
    try:
        positions = database.get_all_positions()
        if not positions:
            await update.message.reply_text("💼 Your portfolio is empty.")
            return
        msg = "💼 **YOUR PORTFOLIO**\n\n"
        total_val = 0
        for p in positions:
            price, change = await price_service.get_price(p['symbol'])
            val = p['quantity'] * (price or 0)
            total_val += val
            cost = p['quantity'] * p['avg_price']
            pnl = val - cost
            emoji = "🟢" if pnl >= 0 else "🔴"
            msg += f"**{p['symbol']}** {emoji}\nQty: {p['quantity']} • Avg: ${p['avg_price']}\nNow: ${price or 'N/A'} • Value: ${val:,.2f} ({pnl:+.2f})\n\n"
        msg += f"━━━━━━━━━━━━━━\n**TOTAL VALUE: ${total_val:,.2f}**"
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in /portfolio: {e}")
        track_error()
        await update.message.reply_text("❌ Error loading portfolio.")

async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    if not context.args:
        await update.message.reply_text("❌ Usage: `/remove BTC`")
        return
    sym = context.args[0].upper()
    database.delete_position(sym)
    await update.message.reply_text(f"✅ Removed **{sym}** from portfolio.", parse_mode='Markdown')

async def update_pos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await add_position(update, context)

# --- ALERT HANDLERS ---

async def set_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    track_command("alert")
    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text("❌ Usage: `/alert BTC 100000 above`")
            return
        symbol, price_str, direction = args[0].upper(), args[1], args[2].lower()
        price_val = error_handler.validate_price(price_str)
        if price_val is None or direction not in ['above', 'below']:
            raise error_handler.ValidationError("Usage: /alert SYMBOL PRICE ABOVE/BELOW")
        
        database.create_alert(symbol, price_val, direction)
        await update.message.reply_text(f"🔔 **Alert Set!** I'll ping you when **{symbol}** goes {direction} ${price_val:,.2f}", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(error_handler.format_error_for_user(e))

async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    alerts = database.get_active_alerts()
    if not alerts:
        await update.message.reply_text("🔔 No active alerts.")
        return
    msg = "🔔 **ACTIVE ALERTS**\n\n"
    for a in alerts:
        msg += f"#{a['id']} • **{a['symbol']}** {a['direction']} ${a['target_price']:,.2f}\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def cancel_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    if not context.args:
        await update.message.reply_text("❌ Usage: `/cancelalert ID`")
        return
    try:
        aid = int(context.args[0])
        database.delete_alert(aid)
        await update.message.reply_text(f"✅ Alert #{aid} removed.")
    except Exception:
        await update.message.reply_text("❌ Invalid Alert ID.")

async def alert_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    alerts = database.get_all_alerts()
    msg = "📜 **ALERT HISTORY (Last 50)**\n\n"
    for a in alerts:
        status = "✅ SHOT" if a['is_active'] == 0 else "⏳ ACTIVE"
        msg += f"{status} • **{a['symbol']}** ${a['target_price']:,.2f}\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

# --- JOURNAL & NOTES HANDLERS ---

async def log_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    content = " ".join(context.args)
    if not content:
        await update.message.reply_text("❌ Usage: `/log [your trade details]`")
        return
    symbol = None
    common_symbols = ["BTC", "ETH", "SOL", "BNB"]
    for s in common_symbols:
        if s in content.upper():
            symbol = s
            break
    database.add_journal_entry("trade", content, symbol=symbol)
    await update.message.reply_text("📔 **Logged!** Your future self will thank you for this data.", parse_mode='Markdown')

async def show_journal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    try:
        journal = database.get_journal_entries(limit=10)
        if not journal:
            await update.message.reply_text("📔 Journal is empty.")
            return
        msg = "📔 **RECENT JOURNAL ENTRIES**\n\n"
        for e in journal:
            dt = datetime.strptime(e['timestamp'], "%Y-%m-%d %H:%M:%S").strftime("%b %d")
            msg += f"#{e['id']} • {dt} • {e['symbol'] or 'General'}\n\"{e['content'][:100]}\"\n\n"
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text("❌ Error loading journal.")

async def add_permanent_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    content = " ".join(context.args)
    if not content:
        await update.message.reply_text("❌ Usage: `/note [your rule or note]`")
        return
    database.add_note(content)
    await update.message.reply_text("📌 **Note Saved!** I'll remember this rule for our strategic reviews.", parse_mode='Markdown')

async def show_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    notes = database.get_all_notes(active_only=True)
    if not notes:
        await update.message.reply_text("📌 No active notes.")
        return
    msg = "📌 **YOUR TRADING RULES**\n\n"
    for n in notes:
        msg += f"#{n['id']} • {n['content']}\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def delete_permanent_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    if not context.args:
        await update.message.reply_text("❌ Usage: `/deletenote ID`")
        return
    try:
        nid = int(context.args[0])
        database.delete_note(nid)
        await update.message.reply_text(f"✅ Note #{nid} deactivated.")
    except Exception:
        await update.message.reply_text("❌ Invalid Note ID.")

async def search_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    keyword = " ".join(context.args)
    if not keyword:
        await update.message.reply_text("❌ Usage: `/search [keyword]`")
        return
    jrats = database.search_journal(keyword)
    notes = database.get_all_notes(active_only=True)
    nrats = [n for n in notes if keyword.lower() in n['content'].lower()]
    
    if not jrats and not nrats:
        await update.message.reply_text("🔍 No results found.")
        return
    msg = f"🔍 **SEARCH RESULTS: '{keyword}'**\n\n"
    if jrats:
        msg += "📔 **JOURNAL:**\n"
        for r in jrats[:3]:
            msg += f"• {r['content'][:70]}...\n"
    if nrats:
        msg += "\n📌 **NOTES:**\n"
        for n in nrats[:3]:
            msg += f"• {n['content'][:70]}...\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

# --- MARKET & ANALYSIS HANDLERS ---

async def market_overview_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    track_command("market")
    await update.message.reply_text("📊 Gathering global market data...", parse_mode='Markdown')
    overview = await market_service.build_market_context_for_claude()
    await update.message.reply_text(overview, parse_mode='Markdown')

async def top_cryptos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    track_command("top")
    top = await market_service.get_top_cryptos(20)
    msg = "🏆 **TOP 20 CRYPTOCURRENCIES**\n\n"
    for c in top:
        emoji = "🟢" if c['change_24h'] >= 0 else "🔴"
        msg += f"{c['rank']}. **{c['symbol']}** ${c['price']:,.2f} ({c['change_24h']:+.1f}% {emoji})\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def fear_greed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    fng = await price_service.get_fear_greed_index()
    if fng:
        val = fng['value']
        cls = fng['classification']
        emoji = "😱" if val<25 else "😨" if val<45 else "😐" if val<55 else "🤑" if val<75 else "🚀"
        await update.message.reply_text(f"📉 **Fear & Greed Index**\nScore: **{val}**\nStatus: **{cls}** {emoji}", parse_mode='Markdown')

async def ta_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    if not context.args:
        await update.message.reply_text("❌ Usage: `/ta SYMBOL [TIMEFRAME]` (e.g. `/ta BTC 4h`)")
        return
    sym = context.args[0].upper()
    tf = context.args[1] if len(context.args) > 1 else '4h'
    await update.message.reply_text(f"📊 Analyzing **{sym}** on **{tf}** timeframe...", parse_mode='Markdown')
    analysis = await technical_analysis.analyze_coin(sym, tf)
    await update.message.reply_text(technical_analysis.format_analysis_for_telegram(analysis), parse_mode='Markdown')

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    if not context.args:
        await update.message.reply_text("❌ Usage: `/analyze SYMBOL` (e.g. `/analyze BTC`)")
        return
    sym = context.args[0].upper()
    await update.message.reply_text(f"🕵️‍♂️ Performing strategic analysis on **{sym}**...", parse_mode='Markdown')
    result = await strategy_advisor.analyze_trade_idea(sym, f"Should I buy or sell {sym} right now?")
    await update.message.reply_text(f"💡 **STRATEGY ADVISOR: {sym}**\n\n{result}", parse_mode='Markdown')

async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: `/compare BTC ETH`")
        return
    s1, s2 = context.args[0].upper(), context.args[1].upper()
    await update.message.reply_text(f"⚔️ Battling **{s1}** vs **{s2}**...", parse_mode='Markdown')
    result = await strategy_advisor.compare_assets(s1, s2)
    await update.message.reply_text(f"🏆 **BATTLE RESULT**\n\n{result}", parse_mode='Markdown')

async def optimize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    track_command("optimize")
    await update.message.reply_text("⚖️ **Starting Portfolio Optimization Analysis...**\nThis will take 1-2 minutes. I'm crunching risk, correlation, and performance data.", parse_mode='Markdown')
    
    optimizer = portfolio_optimizer.PortfolioOptimizer()
    report = await optimizer.analyze_portfolio_health()
    await update.message.reply_text(report, parse_mode='Markdown')

async def risk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    track_command("risk")
    optimizer = portfolio_optimizer.PortfolioOptimizer()
    report = await optimizer.get_risk_dashboard()
    await update.message.reply_text(report, parse_mode='Markdown')

async def rebalance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    track_command("rebalance")
    if not context.args:
        await update.message.reply_text("❌ Usage: `/rebalance BTC:40 ETH:30 SOL:20 CASH:10`", parse_mode='Markdown')
        return
    
    target_params = " ".join(context.args)
    optimizer = portfolio_optimizer.PortfolioOptimizer()
    report = await optimizer.calculate_rebalance(target_params)
    await update.message.reply_text(report, parse_mode='Markdown')

async def accuracy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    track_command("accuracy")
    tracker = performance_tracker.PerformanceTracker()
    report = tracker.generate_accuracy_report()
    await update.message.reply_text(report, parse_mode='Markdown')

async def predictions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    track_command("predictions")
    preds = database.get_all_predictions(limit=15)
    if not preds:
        await update.message.reply_text("📊 No predictions found.")
        return
        
    msg = "📊 **RECENT AI PREDICTIONS**\n\n"
    for p in preds:
        date = datetime.strptime(p['created_at'], "%Y-%m-%d %H:%M:%S").strftime("%b %d")
        emoji = "⏳"
        if p['result_24h'] == 'correct': emoji = "✅"
        elif p['result_24h'] == 'incorrect': emoji = "❌"
        
        result_text = "Checking..."
        if p['result_24h']:
            change = ((p['price_24h'] - p['price']) / p['price']) * 100
            result_text = f"24h: ${p['price_24h']:,.2f} ({change:+.1f}%)"
            
        msg += f"{emoji} {date} — **{p['symbol']}** {p['type'].capitalize()} at ${p['price']:,.2f}\n   {result_text}\n\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    track_command("profile")
    mem = memory_system.MemorySystem()
    report = mem.get_profile_summary()
    await update.message.reply_text(report, parse_mode='Markdown')

async def insights_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    track_command("insights")
    insights = database.get_all_market_insights()
    if not insights:
        await update.message.reply_text("🧠 No market insights stored yet. Use `/addinsight` to start!")
        return
        
    msg = "🧠 **STORED MARKET INSIGHTS**\n\n"
    current_sym = ""
    for i in insights:
        if i['symbol'] != current_sym:
            current_sym = i['symbol']
            msg += f"\n**{current_sym}:**\n"
        msg += f"• {i['insight_text']} (Confidence: {i['confidence']}/5)\n"
    
    msg += "\n💡 Use `/addinsight BTC pattern The pump is real`"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def addinsight_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    track_command("addinsight")
    if len(context.args) < 3:
        await update.message.reply_text("❌ Usage: `/addinsight [COIN] [TYPE] [INSIGHT]`\nExample: `/addinsight ETH news ETH tends to pump 2 days before upgrades`", parse_mode='Markdown')
        return
        
    sym = context.args[0].upper()
    i_type = context.args[1].lower()
    text = " ".join(context.args[2:])
    
    database.add_market_insight(sym, i_type, text)
    await update.message.reply_text(f"✅ Stored insight for **{sym}**! I'll reference this in future analysis.", parse_mode='Markdown')

# --- AUTONOMOUS & REPORT COMMANDS ---

async def briefing_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    await update.message.reply_text("☕ Brewing your morning briefing...")
    await briefing_service.Reporter.send_morning_briefing(context.bot, config.MY_TELEGRAM_ID)

async def evening_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    await update.message.reply_text("🌙 Gathering evening data...")
    await briefing_service.Reporter.send_evening_summary(context.bot, config.MY_TELEGRAM_ID)

async def weekly_review_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    await update.message.reply_text("🔎 Gathering 7-day data for review...")
    await reviewer.perform_review(context.bot, config.MY_TELEGRAM_ID, days=7, is_weekly=True)

async def daily_review_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    await reviewer.perform_review(context.bot, config.MY_TELEGRAM_ID, days=1, is_weekly=False)

# --- WALLET WATCHER HANDLERS ---

async def watch_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("❌ Usage: `/watchallet [ADDRESS] [NAME] [MIN_USD]`")
        return
    addr, name, min_usd = args[0].lower(), args[1], float(args[2])
    chain = 'eth' if addr.startswith('0x') else 'btc'
    database.add_watched_wallet(addr, name, chain, min_usd)
    await update.message.reply_text(f"👀 **Watching!** I'll alert you if **{name}** moves more than ${min_usd:,.0f} on {chain.upper()}", parse_mode='Markdown')

async def wallet_watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    wallets = database.get_watched_wallets()
    if not wallets:
        await update.message.reply_text("👀 No watched wallets.")
        return
    msg = "👀 **WATCHED WALLETS**\n\n"
    for w in wallets:
        msg += f"👤 **{w['nickname']}** ({w['chain'].upper()})\nLimit: ${w['min_usd']:,.0f}\n`{w['address'][:8]}...{w['address'][-6:]}`\n\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def remove_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    if not context.args:
        await update.message.reply_text("❌ Usage: `/removewallet [ADDRESS]`")
        return
    database.remove_watched_wallet(context.args[0])
    await update.message.reply_text(f"✅ Stopped watching.")

# --- BACKUP & EXPORT ---

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    await backup_service.BackupService.run_full_backup(context.bot, config.MY_TELEGRAM_ID)

async def export_trades_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    fname = await backup_service.BackupService.generate_trades_csv()
    with open(fname, 'rb') as f:
        await context.bot.send_document(chat_id=config.MY_TELEGRAM_ID, document=f)
    os.remove(fname)

# --- COMPLEX ALERT CONVERSATION ---

async def start_complex_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    kb = [['1', '2', '3', '4']]
    await update.message.reply_text(
        "🧠 **Complex Alert Setup**\n\n1. Two prices (AND/OR)\n2. Price + Fear & Greed\n3. Portfolio drop %\n4. Coin move % (24h)\n\nReply with 1-4 or /cancel",
        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
    )
    return CHOOSING_TYPE

async def choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    context.user_data['ctype_id'] = choice
    if choice == '1':
        context.user_data['ctype'] = 'price_and_price'
        await update.message.reply_text("First coin (e.g. BTC):", reply_markup=ReplyKeyboardRemove())
        return GETTING_S1
    elif choice == '2':
        context.user_data['ctype'] = 'price_and_fear_greed'
        await update.message.reply_text("Coin (e.g. BTC):", reply_markup=ReplyKeyboardRemove())
        return GETTING_S1
    elif choice == '3':
        context.user_data['ctype'] = 'portfolio_change'
        await update.message.reply_text("Alert on % change (e.g. 10):", reply_markup=ReplyKeyboardRemove())
        return GETTING_T1
    elif choice == '4':
        context.user_data['ctype'] = 'price_percentage_move'
        await update.message.reply_text("Coin (e.g. SOL):", reply_markup=ReplyKeyboardRemove())
        return GETTING_S1
    return CHOOSING_TYPE

async def get_s1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['s1'] = update.message.text.upper()
    await update.message.reply_text(f"Threshold for {context.user_data['s1']}:")
    return GETTING_T1

async def get_t1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['t1'] = float(update.message.text)
        kb = [['above', 'below']]
        await update.message.reply_text("Direction?", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
        return GETTING_D1
    except: return GETTING_T1

async def get_d1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['d1'] = update.message.text.lower()
    ctype = context.user_data['ctype']
    if ctype in ['price_and_price', 'price_and_fear_greed']:
        kb = [['AND', 'OR']]
        await update.message.reply_text("Join operator?", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
        return GETTING_OP
    await update.message.reply_text("Alert name:", reply_markup=ReplyKeyboardRemove())
    return GETTING_NAME

async def get_op(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['op'] = update.message.text.upper()
    ctype = context.user_data['ctype']
    if ctype == 'price_and_price':
        await update.message.reply_text("Second coin:", reply_markup=ReplyKeyboardRemove())
        return GETTING_S2
    await update.message.reply_text("F&G Threshold (0-100):", reply_markup=ReplyKeyboardRemove())
    return GETTING_T2

async def get_s2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['s2'] = update.message.text.upper()
    await update.message.reply_text(f"Threshold for {context.user_data['s2']}:")
    return GETTING_T2

async def get_t2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['t2'] = float(update.message.text)
        kb = [['above', 'below']]
        await update.message.reply_text("Second Direction?", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
        return GETTING_D2
    except: return GETTING_T2

async def get_d2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['d2'] = update.message.text.lower()
    await update.message.reply_text("Alert name:", reply_markup=ReplyKeyboardRemove())
    return GETTING_NAME

async def get_name_and_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    ud = context.user_data
    desc = f"Complex alert: {ud['ctype']}"
    database.create_complex_alert(name, desc, ud['ctype'], ud.get('s1'), ud.get('t1'), ud.get('d1'), ud.get('s2'), ud.get('t2'), ud.get('d2'), ud.get('op', 'AND'))
    await update.message.reply_text(f"✅ **Complex Alert '{name}' Saved!**", parse_mode='Markdown')
    return ConversationHandler.END

async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- QUICKSTART CONVERSATION ---

async def quickstart_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    msg = "🚀 **WELCOME TO QUICKSTART!**\n\n1. Add Portfolio\n2. Set Alert\n3. Log Journal\n4. Get Briefing\n\n**STEP 1: ADD PORTFOLIO**\n`/add BTC 0.5 95000`"
    await update.message.reply_text(msg, parse_mode='Markdown')
    return QS_PORTFOLIO

async def qs_portfolio_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await add_position(update, context)
    msg = "✅ **Portfolio Saved.**\n\n**STEP 2: SET ALERT**\n`/alert BTC 100000 above`"
    await update.message.reply_text(msg, parse_mode='Markdown')
    return QS_ALERT

async def qs_alert_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_alert(update, context)
    msg = "✅ **Alert Live.**\n\n**STEP 3: LOG JOURNAL**\n`/log Watching BTC...`"
    await update.message.reply_text(msg, parse_mode='Markdown')
    return QS_JOURNAL

async def qs_journal_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await log_entry(update, context)
    msg = "✅ **Journaled.**\n\n**STEP 4: BRIEFING**\n`/briefing`"
    await update.message.reply_text(msg, parse_mode='Markdown')
    return QS_BRIEFING

async def qs_briefing_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await briefing_command(update, context)
    await update.message.reply_text("🎉 **QUICKSTART COMPLETE!** Type `/help` for more.", parse_mode='Markdown')
    return ConversationHandler.END

async def qs_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled. Restart with `/quickstart`.")
    return ConversationHandler.END

async def complex_alerts_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    alerts = database.get_active_complex_alerts()
    if not alerts:
        await update.message.reply_text("🧠 No active complex alerts.")
        return
    msg = "🧠 **ACTIVE COMPLEX ALERTS**\n\n"
    for a in alerts:
        msg += f"#{a['id']} • **{a['name']}**\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def scanner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /scanner status and 24/7 scanning controls."""
    if not await is_authorized(update): return
    
    args = context.args
    if args:
        sub = args[0].lower()
        if sub == 'on':
            database.update_scanner_setting('status', 'on')
            await update.message.reply_text("🔍 **Market Scanner: ON**\nI am now monitoring the market for opportunities.", parse_mode='Markdown')
            return
        elif sub == 'off':
            database.update_scanner_setting('status', 'off')
            await update.message.reply_text("⏸ **Market Scanner: OFF**\nScanning paused.", parse_mode='Markdown')
            return
            
    # Default: Show Status
    status = database.get_scanner_setting('status', 'on')
    scans_today = database.get_scan_count_today()
    findings = database.get_recent_scanner_events(limit=5, hours=6)
    
    status_emoji = "✅ Active" if status == 'on' else "⏸ Paused"
    msg = (
        f"🔍 **MARKET SCANNER STATUS**\n\n"
        f"Status: {status_emoji}\n"
        f"Scans Today: {scans_today}\n"
        "──────────────────\n"
        "📜 **RECENT FINDINGS (6H):**\n"
    )
    
    if findings:
        for f in findings:
            try:
                # Format: 07:45 PM
                dt = datetime.strptime(f['timestamp'], "%Y-%m-%d %H:%M:%S").strftime("%I:%M %p")
                # Try to pick a descriptive line from the notification message
                details = f['details'].split('\n')
                desc = details[2] if len(details) > 2 else details[0][:40]
                msg += f"• {dt} — {desc}\n"
            except:
                msg += f"• {f['timestamp'][11:16]} — Market event\n"
    else:
        msg += "• No major events detected yet."
        
    msg += "\n\n💡 Use `/scanner on` or `/scanner off`"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def opportunities_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows all recent opportunity alerts and configuration."""
    if not await is_authorized(update): return
    
    args = context.args
    if args:
        sub = args[0].lower()
        if sub in ['oversold', 'funding', 'ath', 'rotation']:
            key = f"scan_{sub}"
            current = database.get_scanner_setting(key, 'on')
            new_val = 'off' if current == 'on' else 'on'
            database.update_scanner_setting(key, new_val)
            await update.message.reply_text(f"✅ **Opportunity Scan '{sub}'** is now **{new_val.upper()}**.", parse_mode='Markdown')
            return

    # Show Status and recent opportunities
    findings = database.get_recent_scanner_events(limit=10, hours=24)
    oversold = database.get_scanner_setting('scan_oversold', 'on')
    funding = database.get_scanner_setting('scan_funding', 'on')
    ath = database.get_scanner_setting('scan_ath', 'on')
    rotation = database.get_scanner_setting('scan_rotation', 'on')
    
    msg = (
        "💡 **OPPORTUNITY DETECTOR STATUS**\n"
        "──────────────────\n"
        f"1. Oversold Radar: {'✅ ON' if oversold == 'on' else '⏸ OFF'}\n"
        f"2. Funding Extremes: {'✅ ON' if funding == 'on' else '⏸ OFF'}\n"
        f"3. 90-Day Highs: {'✅ ON' if ath == 'on' else '⏸ OFF'}\n"
        f"4. Sector Rotation: {'✅ ON' if rotation == 'on' else '⏸ OFF'}\n"
        "──────────────────\n"
        "📜 **RECENT OPPORTUNITIES (24H):**\n"
    )
    
    opps = [f for f in findings if f['scan_type'] in ['opportunity', 'funding', 'ath', 'rotation']]
    if opps:
        for o in opps:
            try:
                dt = datetime.strptime(o['timestamp'], "%Y-%m-%d %H:%M:%S").strftime("%I:%M %p")
                lines = o['details'].split('\n')
                # Find first non-empty line with content
                desc = next((l for l in lines if l.strip() and not l.startswith('💡') and not l.startswith('🚀') and not l.startswith('🔄')), o['details'][:40])
                msg += f"• {dt} — {desc}\n"
            except:
                msg += f"• {o['timestamp'][11:16]} — Opportunity\n"
    else:
        msg += "• No specific opportunities detected yet."
        
    msg += "\n\n💡 Use `/opportunities [scan_name]` to toggle."
    await update.message.reply_text(msg, parse_mode='Markdown')

async def smartmoney_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows recent notable on-chain movements."""
    if not await is_authorized(update): return
    track_command("smartmoney")
    
    await update.message.reply_text("🧠 Analyzing recent whale and exchange movements...")
    tracker = smart_money.SmartMoneyTracker(context.bot, config.MY_TELEGRAM_ID)
    summary = await tracker.build_smart_money_summary()
    await update.message.reply_text(summary, parse_mode='Markdown')

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows current news sentiment briefing or news for a specific coin."""
    if not await is_authorized(update): return
    track_command("news")
    
    args = context.args
    if args:
        symbol = args[0].upper()
        await update.message.reply_text(f"🔍 Searching for latest news about **{symbol}**...", parse_mode='Markdown')
        articles = await news_service.get_news_for_symbol(symbol, limit=5)
        if not articles:
            await update.message.reply_text(f"No recent news found for {symbol}.")
            return
        
        # Analyze sentiment for this specific coin
        sentiment = await news_service.analyze_news_sentiment(articles)
        
        msg = f"📰 **{symbol} NEWS BREAKDOWN**\n\n"
        if sentiment:
            mood = sentiment['sentiment'].replace("_", " ")
            msg += f"Sentiment: **{mood}**\n\n"
            msg += f"🔥 **Top Story:**\n{sentiment['top_story']}\n\n"
        
        msg += "📜 **LATEST HEADLINES:**\n"
        for a in articles:
            msg += f"• {a['title']} — {a['source']}\n"
        
        await update.message.reply_text(msg, parse_mode='Markdown')
    else:
        await update.message.reply_text("📰 Fetching global crypto news briefing...")
        briefing = await news_service.generate_news_briefing()
        await update.message.reply_text(briefing, parse_mode='Markdown')

async def sentiment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick sentiment overview dashboard."""
    if not await is_authorized(update): return
    track_command("sentiment")
    
    await update.message.reply_text("🎭 Gathering market sentiment data...")
    
    # 1. News Sentiment
    articles = await news_service.fetch_latest_news(limit=15)
    news_dat = await news_service.analyze_news_sentiment(articles)
    
    # 2. Fear & Greed
    fng = await price_service.get_fear_greed_index()
    
    # 3. Smart Money
    tracker = smart_money.SmartMoneyTracker(context.bot, config.MY_TELEGRAM_ID)
    sm_summary = await tracker.build_smart_money_summary()
    
    msg = "🎭 **MARKET SENTIMENT DASHBOARD**\n"
    msg += "──────────────────────\n"
    
    if news_dat:
        score_emoji = "🟢" if news_dat['score'] >= 6 else "🔴" if news_dat['score'] <= 4 else "🟡"
        msg += f"News Sentiment: {score_emoji} **{news_dat['sentiment']}** ({news_dat['score']}/10)\n"
    
    if fng:
        fng_emoji = "🔥" if fng['value'] > 75 else "😨" if fng['value'] < 25 else "⚖️"
        msg += f"Fear & Greed: {fng_emoji} **{fng['value']}** ({fng['classification']})\n"
    
    # Extract Net Sentiment from smart money summary
    if "Net sentiment from on-chain:" in sm_summary:
        net_sm = sm_summary.split("Net sentiment from on-chain:")[1].strip()
        msg += f"Whale Sentiment: {net_sm}\n"
    
    # Combined Signal (Simplified)
    total_score = 0
    count = 0
    if news_dat:
        total_score += news_dat['score']
        count += 1
    if fng:
        # Scale F&G 0-100 to 0-10
        total_score += fng['value'] / 10
        count += 1
    
    avg_score = total_score / count if count > 0 else 5
    combined = "BULLISH" if avg_score > 6.5 else "BEARISH" if avg_score < 3.5 else "NEUTRAL"
    c_emoji = "🚀" if combined == "BULLISH" else "🧊" if combined == "BEARISH" else "🤝"
    
    msg += "──────────────────────\n"
    msg += f"Combined Signal: {c_emoji} **{combined}**\n\n"
    msg += "💡 This signal combines news, retail sentiment, and on-chain whale activity."
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def research_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggers deep autonomous research."""
    if not await is_authorized(update): return
    track_command("research")
    
    args = context.args
    if not args:
        await update.message.reply_text("Usage: `/research [COIN]`\nExample: `/research BTC`")
        return
        
    symbol = args[0].upper()
    agent = research_agent.ResearchAgent(context.bot, update.effective_chat.id)
    await agent.research_coin(symbol)

async def compare_multi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Improved compare for multi-coin battle."""
    if not await is_authorized(update): return
    track_command("compare")
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: `/compare [COIN1] [COIN2] ...`\nExample: `/compare BTC ETH SOL`")
        return
        
    symbols = [s.upper() for s in args]
    agent = research_agent.ResearchAgent(context.bot, update.effective_chat.id)
    await agent.compare_coins(symbols)

async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manages the research watchlist."""
    if not await is_authorized(update): return
    track_command("watchlist")
    
    args = context.args
    if args:
        cmd = args[0].lower()
        if cmd == 'add' and len(args) > 1:
            symbol = args[1].upper()
            database.add_to_research_watchlist(symbol)
            await update.message.reply_text(f"✅ Added **{symbol}** to research watchlist for weekly auto-reports.", parse_mode='Markdown')
            return
        elif cmd == 'remove' and len(args) > 1:
            symbol = args[1].upper()
            database.remove_from_research_watchlist(symbol)
            await update.message.reply_text(f"❌ Removed **{symbol}** from research watchlist.")
            return

    # Default: Show list
    wl = database.get_research_watchlist()
    if not wl:
        await update.message.reply_text("Your research watchlist is empty.\n\nUse `/watchlist add BTC` to start.")
        return
        
    msg = "📋 **RESEARCH WATCHLIST**\n"
    msg += "Auto-researching these weekly:\n\n"
    for item in wl:
        msg += f"• **{item['symbol']}**\n"
    
    msg += "\n💡 Use `/watchlist add [COIN]` or `remove [COIN]` to manage."
    await update.message.reply_text(msg, parse_mode='Markdown')

async def onchain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the full on-chain summary in Telegram."""
    if not await is_authorized(update): return
    track_command("onchain")
    await update.message.reply_text("🔗 Pulling real-time blockchain intelligence...")
    summary = await onchain_data.build_onchain_summary()
    await update.message.reply_text(summary, parse_mode='Markdown')

async def gas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick gas price check."""
    if not await is_authorized(update): return
    track_command("gas")
    gas = await onchain_data.get_eth_gas_prices()
    if gas:
        status = "LOW" if gas['standard'] < 20 else "MODERATE" if gas['standard'] < 50 else "HIGH"
        tips = "good time for DeFi!" if status == "LOW" else "wait if you can."
        msg = (
            "⛽ **ETHEREUM GAS PRICES**\n\n"
            f"🐢 Slow: {gas['slow']} gwei\n"
            f"🚶 Standard: {gas['standard']} gwei\n"
            f"🚀 Fast: {gas['fast']} gwei\n\n"
            f"Current gas is **{status}** — {tips}"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Failed to fetch gas prices.")
