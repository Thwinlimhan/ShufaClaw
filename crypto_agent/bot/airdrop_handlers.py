import logging
from telegram import Update
from telegram.ext import ContextTypes
from crypto_agent.airdrop.tracker import AirdropTracker
from crypto_agent.airdrop.wallet_scorer import WalletScorer
from crypto_agent.airdrop.task_engine import AirdropTaskEngine
from crypto_agent.intelligence.airdrop_agent import AirdropIntelAgent

logger = logging.getLogger(__name__)

async def airdrop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View the airdrop intelligence dashboard."""
    tracker = AirdropTracker()
    dashboard = tracker.get_dashboard()
    
    # Get wallet reputation score (dummy or real if connected)
    from crypto_agent.storage import database
    linked_wallet = database.get_scanner_setting('linked_wallet', None)
    
    scorer = WalletScorer()
    if linked_wallet:
        metrics = database.get_wallet_metrics(linked_wallet)
        if metrics:
            result = scorer.score_wallet(metrics)
            rep_score = result['composite_score']
        else:
            rep_score = "N/A"
    else:
        rep_score = "N/A (Use /linkwallet)"
    
    message = "🪂 AIRDROP INTELLIGENCE HUB\n\n"
    message += f"Wallet Reputation: {rep_score}/100\n"
    message += f"Total Tracked: {dashboard['total_tracked']}\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    message += f"✅ CRITERIA MET ({dashboard['criteria_met']}):\n"
    for name, score in dashboard['met_list'][:5]:
        message += f"• {name}: {score}/100\n"
    message += "\n"
    
    message += f"⏳ CLOSE ({dashboard['close']}):\n"
    for name, score in dashboard['close_list'][:5]:
        message += f"• {name}: {score}/100\n"
    message += "\n"
    
    message += f"💰 TOTAL RECEIVED: ${dashboard['total_received_value']:,.2f}\n\n"
    
    if dashboard['upcoming_snapshots']:
        message += "📅 UPCOMING SNAPSHOTS:\n"
        for protocol, date in dashboard['upcoming_snapshots'][:3]:
            message += f"• {protocol}: {date}\n"
    
    message += "\nUse /airdroptasks for your daily action plan."
    
    await update.message.reply_text(message)

async def airdrop_tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get the daily prioritized airdrop action plan."""
    tracker = AirdropTracker()
    engine = AirdropTaskEngine()
    
    # 1. Get raw data
    protocols = tracker.get_all_protocol_data()
    
    # 2. Generate plan
    plan = engine.get_daily_plan(protocols)
    
    message = f"📋 DAILY AIRDROP ACTION PLAN ({plan['date']})\n"
    message += f"Est. Time: {plan['estimated_total_time']} | Gas: {plan['estimated_total_gas']}\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # 3. Urgent Tasks
    if plan["urgent"]:
        message += "🔴 URGENT:\n"
        for t in plan["urgent"]:
            message += f"• [{t['protocol']}] {t['task']} ({t['time']})\n"
        message += "\n"
        
    # 4. Regular Tasks
    if plan["regular"]:
        message += "🟠 REGULAR:\n"
        for t in plan["regular"]:
            message += f"• [{t['protocol']}] {t['task']} ({t['time']})\n"
        message += "\n"
        
    # 5. Maintenance
    if plan["maintenance"]:
        message += "🔵 MAINTENANCE:\n"
        for t in plan["maintenance"]:
            message += f"• [{t['protocol']}] {t['task']} ({t['time']})\n"
        message += "\n"
            
    if not plan["urgent"] and not plan["regular"] and not plan["maintenance"]:
        message += "✅ No tasks found. You're up to date on all tracked protocols!\n\n"
        
    message += "🛡️ ANTI-SYBIL TIPS:\n"
    for tip in plan["anti_sybil_tips"][:2]:
        message += f"• {tip}\n"
    
    await update.message.reply_text(message)

async def airdrop_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View detailed airdrop stats and history."""
    tracker = AirdropTracker()
    dashboard = tracker.get_dashboard()
    
    message = "📊 AIRDROP STATISTICS\n\n"
    message += f"Total Value Received: ${dashboard['total_received_value']:,.2f}\n"
    message += f"Tracked Protocols: {dashboard['total_tracked']}\n"
    message += f"Success Rate: {(dashboard['criteria_met'] / dashboard['total_tracked'] * 100):.1f}%\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Detailed breakdown could go here
    message += "Use /addsnapshot [protocol] [date] to track new dates."
    
    await update.message.reply_text(message)

async def add_snapshot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Track a new snapshot date: /addsnapshot [protocol] [YYYY-MM-DD]"""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /addsnapshot [protocol] [YYYY-MM-DD]")
        return
        
    protocol = context.args[0]
    date_str = context.args[1]
    notes = " ".join(context.args[2:]) if len(context.args) > 2 else ""
    
    tracker = AirdropTracker()
    tracker.add_snapshot(protocol, date_str, notes)
    
    await update.message.reply_text(f"✅ Tracked snapshot for {protocol} on {date_str}")

async def record_airdrop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Record received airdrop: /recordairdrop [protocol] [token] [amount] [value]"""
    if not context.args or len(context.args) < 4:
        await update.message.reply_text("Usage: /recordairdrop [protocol] [token] [amount] [value]")
        return
        
    try:
        protocol = context.args[0]
        token = context.args[1]
        amount = float(context.args[2])
        value = float(context.args[3])
        
        tracker = AirdropTracker()
        tracker.record_airdrop(protocol, token, amount, value)
        
        await update.message.reply_text(f"🎉 Recorded {amount} {token} (${value:,.2f}) airdrop from {protocol}!")
    except ValueError:
        await update.message.reply_text("Error: Amount and Value must be numbers.")

async def link_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Link your wallet for airdrop scoring: /linkwallet [address]"""
    if not context.args:
        await update.message.reply_text("Usage: /linkwallet [address]")
        return
        
    address = context.args[0].lower()
    from crypto_agent.storage import database
    database.update_scanner_setting('linked_wallet', address)
    
    # Initialize some dummy metrics if they don't exist so the scorer has something to work with
    existing = database.get_wallet_metrics(address)
    if not existing:
        dummy_metrics = {
            "wallet_address": address,
            "age_months": 0,
            "active_months_last_12": 0,
            "unique_protocols": 0,
            "unique_categories": 0,
            "lifetime_volume_usd": 0,
            "avg_tx_size_usd": 0,
            "governance_votes": 0,
            "lp_positions": 0,
            "staking_positions": 0,
            "contracts_deployed": 0,
            "has_ens": 0,
            "gitcoin_passport_score": 0,
            "poap_count": 0,
            "total_txns": 0,
            "failed_txns": 0,
            "identical_amounts_pct": 0
        }
        database.save_wallet_metrics(dummy_metrics)
    
    await update.message.reply_text(f"✅ Linked wallet: {address}\nI will now start tracking your reputation. (Use /mywallet to view detailed breakdown)")

async def my_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View your detailed wallet reputation breakdown."""
    from crypto_agent.storage import database
    address = database.get_scanner_setting('linked_wallet', None)
    
    if not address:
        await update.message.reply_text("No wallet linked. Use /linkwallet [address] first.")
        return
        
    metrics = database.get_wallet_metrics(address)
    if not metrics:
        await update.message.reply_text("Wallet linked but no metrics available yet. Just a moment...")
        return
        
    scorer = WalletScorer()
    result = scorer.score_wallet(metrics)
    
    message = f"🛡️ WALLET REPUTATION: {address[:6]}...{address[-4:]}\n"
    message += f"OVERALL: {result['composite_score']}/100 ({result['grade']})\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    message += "📊 BREAKDOWN:\n"
    for dim, score in result['breakdown'].items():
        message += f"• {dim.replace('_', ' ').title()}: {score}/100\n"
        
    if result['sybil_flags']:
        message += "\n⚠️ SYBIL FLAGS:\n"
        for flag in result['sybil_flags']:
            message += f"• {flag}\n"
            
    if result['gaps_to_address']:
        message += "\n🎯 GAPS TO ADDRESS:\n"
        for gap in result['gaps_to_address']:
            message += f"• {gap}\n"
            
    await update.message.reply_text(message)

async def update_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Refreshes your on-chain reputation data from the blockchain."""
    from crypto_agent.storage import database
    address = database.get_scanner_setting('linked_wallet', None)
    
    if not address:
        await update.message.reply_text("No wallet linked. Use /linkwallet [address] first.")
        return
        
    msg = await update.message.reply_text(f"Refreshing metrics for {address[:6]}...{address[-4:]} 🛰️\nScanning Ethereum blockchain...")
    
    try:
        from crypto_agent.airdrop.fetcher import fetch_wallet_onchain_metrics
        metrics = await fetch_wallet_onchain_metrics(address)
        
        if metrics:
            await msg.edit_text("✅ Metrics updated! Your reputation has been recalculated.\nUse /mywallet to see the new score.")
        else:
            await msg.edit_text("❌ Error: Could not fetch blockchain data. Check your Etherscan API key or address.")
    except Exception as e:
        logger.error(f"Wallet update error: {e}")
        await msg.edit_text(f"❌ Error during update: {e}")

async def airdrop_strategy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate a high-level airdrop research & strategy briefing."""
    msg = await update.message.reply_text("🔎 Analyzing global airdrop landscape and your wallet gaps...")
    
    try:
        agent = AirdropIntelAgent(bot=context.bot, chat_id=update.effective_chat.id)
        strategy = await agent.get_airdrop_strategy()
        await msg.edit_text(strategy, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Airdrop strategy error: {e}")
        await msg.edit_text(f"❌ Error generating airdrop strategy: {e}")
