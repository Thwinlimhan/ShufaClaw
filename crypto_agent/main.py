import logging
import asyncio

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from crypto_agent import config
from crypto_agent.storage import database
from crypto_agent.bot import (
    handlers, middleware, quant_handlers, backtest_handlers, defi_handlers, 
    ml_handlers, social_handlers, institutional_handlers, chain_handlers, 
    voice_handlers, sizer_handlers, orchestrator_handlers, options_handlers, 
    debate_handlers, event_handlers, macro_handlers, security_handlers, 
    attribution_handlers, proposal_handlers, workflow_handlers, 
    airdrop_handlers, hub_handlers, skill_handlers, education_handlers, 
    frontier_handlers
)
from crypto_agent.core import agent, scheduler
from crypto_agent.core.cognitive_loop import CognitiveLoop
from crypto_agent.core.skill_system import SkillSystem
from crypto_agent.core.orchestrator import orchestrator as core_orchestrator # Renamed to avoid conflict
from crypto_agent.core.evolution_engine import EvolutionEngine
from crypto_agent.core.workflow_engine import WorkflowEngine
from crypto_agent.intelligence.hub import IntelligenceHub
from crypto_agent.intelligence.event_predictor import EventPredictor
from crypto_agent.intelligence.orchestrator import orchestrator as intelligence_orchestrator # Added new import
from crypto_agent.data import market as market_service, prices as price_service # Modified import
import pytz
from crypto_agent.infrastructure.database import create_tables, close_pool as close_db_pool
from crypto_agent.infrastructure.cache import redis_cache
from crypto_agent.infrastructure.event_bus import event_bus
from crypto_agent.data.market_streamer import market_streamer


# --- LOGGING SETUP ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

import subprocess
import os
import sys

def start_dashboard():
    logger.info("Starting Web Dashboard on port 8000...")
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_file = open("dashboard.log", "w")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "crypto_agent.dashboard.app:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=log_file,
        stderr=log_file,
        cwd=cwd
    )
    logger.info(f"Dashboard started (PID: {proc.pid}). Logs: dashboard.log")
    return proc

def start_discord():
    logger.info("Starting Discord Agent...")
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_file = open("discord_bot.log", "w")
    proc = subprocess.Popen(
        [sys.executable, "-m", "crypto_agent.discord_agent.bot"],
        stdout=log_file,
        stderr=log_file,
        cwd=cwd
    )
    logger.info(f"Discord bot started (PID: {proc.pid}). Logs: discord_bot.log")
    return proc



# --- DASHBOARD SETUP ---


async def post_init(application):
    """Called after bot starts to register database, commands and scheduler."""
    # 0. Initialize V2 Infrastructure
    logger.info("Initializing V2 Infrastructure (TimescaleDB, Redis, Kafka)...")
    try:
        await create_tables()
        await redis_cache.connect()
        await event_bus.connect()
        logger.info("✅ V2 Infrastructure ready!")
        
        # Start market data streams
        default_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        await market_streamer.start(default_symbols)
        
        # Power up the Agents
        intelligence_orchestrator.start()

        # Wire risk event persistence + Kafka
        from crypto_agent.trading.risk_manager import risk_manager
        from crypto_agent.trading.risk_logger import persist_and_publish_risk_event

        def _on_risk_event(event):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(persist_and_publish_risk_event(event))
            except RuntimeError:
                pass

        risk_manager.set_event_handler(_on_risk_event)
        
    except Exception as e:
        logger.warning(f"⚠️ V2 infrastructure not available: {e}")
        logger.warning("   Bot will continue with V1 functionality.")

    # 0.1 Initialize V1 Database (SQLite — still used for chat history etc.)
    logger.info("Initializing V1 Database...")
    await database.init_db()
    # 1. Initialize Intelligence Services
    logger.info("Initializing Intelligence services...")
    event_predictor = EventPredictor(database, market_service, price_service)
    skill_system = SkillSystem()
    evolution_engine = EvolutionEngine()
    
    # Store in bot_data for shared access
    application.bot_data['event_predictor'] = event_predictor
    application.bot_data['skill_system'] = skill_system
    application.bot_data['evolution_engine'] = evolution_engine
    application.bot_data['intelligence_hub'] = IntelligenceHub({
        'event_predictor': event_predictor,
        'market_service': market_service,
        'price_service': price_service,
        'skill_system': skill_system,
        'evolution_engine': evolution_engine
    })

    # 2. Register Scheduler
    scheduler.setup_scheduler(application)
    
    # 2. Register Telegram Menu Commands
    from telegram import BotCommand
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show help menu"),
        BotCommand("quickstart", "Guided tour"),
        BotCommand("portfolio", "View portfolio"),
        BotCommand("market", "Market overview"),
        BotCommand("log", "Log trade"),
        BotCommand("alert", "Set alert"),
        BotCommand("onchain", "On-chain intelligence"),
        BotCommand("smartmoney", "Track whale moves"),
        BotCommand("news", "Latest news & sentiment"),
        BotCommand("sentiment", "Market mood dashboard"),
        BotCommand("optimize", "Full portfolio optimization"),
        BotCommand("accuracy", "Bot prediction track record"),
        BotCommand("predictions", "Recent AI calls & outcomes"),
        BotCommand("risk", "Quick risk dashboard"),
        BotCommand("rebalance", "Calculate rebalance trades"),
        BotCommand("gas", "ETH gas prices"),
        BotCommand("edge", "Mean reversion calculator"),
        BotCommand("quant", "Quantitative dashboard"),
        BotCommand("ev", "Manual EV calculator"),
        BotCommand("backtest", "Run historical backtest"),
        BotCommand("strategies", "Available backtest strategies"),
        BotCommand("yields", "DeFi yield opportunities"),
        BotCommand("protocol", "DeFi protocol health"),
        BotCommand("il", "Impermanent loss calculator"),
        BotCommand("gasbest", "Optimal gas times"),
        BotCommand("estimate", "Swap gas USD estimate"),
        BotCommand("ml", "Machine learning signals"),
        BotCommand("anomaly", "Isolation forest detector"),
        BotCommand("forecast", "Gradient boosting targets"),
        BotCommand("social", "Reddit & trends sentiment"),
        BotCommand("fomo", "Retail panic/fomo detector"),
        BotCommand("institutional", "Corporate & derivative flow"),
        BotCommand("etfflows", "Public BTC treasuries"),
        BotCommand("cot", "Institutional sentiment (DVOL)"),
        BotCommand("chains", "Global L1/L2 dominance"),
        BotCommand("chain", "Deep dive a specific network"),
        BotCommand("bridges", "Capital bridge rotations"),
        BotCommand("voice", "Toggle voice mode ON/OFF"),
        BotCommand("size", "Volatility position sizing"),
        BotCommand("kelly", "Mathematical bet sizing"),
        BotCommand("heat", "Global portfolio exposure"),
        BotCommand("sizing", "Full sizing dashboard"),
        BotCommand("status", "Bot health"),
        BotCommand("regime", "Current market regime"),
        BotCommand("mode", "Orchestrator mode settings"),
        BotCommand("options", "Derivatives flow data"),
        BotCommand("debate", "AI Bull/Bear debate"),
        BotCommand("quickdebate", "One-shot debate summary"),
        BotCommand("calendar", "Upcoming crypto events"),
        BotCommand("predict", "Event impact prediction"),
        BotCommand("imminent", "Highly likely events soon"),
        BotCommand("macro", "Global macro overview"),
        BotCommand("correlation", "BTC vs TradFi correlation"),
        BotCommand("dxy", "Dollar index monitor"),
        BotCommand("security", "Full security dashboard"),
        BotCommand("auditlog", "View recent security logs"),
        BotCommand("2fa", "Toggle 2FA PIN protection"),
        BotCommand("attribution", "Performance attribution (30d)"),
        BotCommand("benchmark", "Compare to BTC/Market"),
        BotCommand("factors", "Factor exposure analysis"),
        BotCommand("proposal", "Get automated trade proposal"),
        BotCommand("workflows", "Manage multi-step workflows"),
        BotCommand("runworkflow", "Execute specific workflow"),
        BotCommand("airdrop", "Airdrop intelligence hub"),
        BotCommand("airdroptasks", "Daily airdrop action plan"),
        BotCommand("airdropstrategy", "AI-driven airdrop research briefing"),
        BotCommand("hub", "Unified intelligence summary"),
        BotCommand("signals", "Deep dive all signals"),
        BotCommand("agenda", "Your daily action agenda"),
        BotCommand("weeklyreport", "Full weekly intel briefing"),
        BotCommand("skills", "Bot skill performance"),
        BotCommand("memory", "Bot memory state (7 layers)"),
        BotCommand("evolution", "Learning calibration stats"),
        BotCommand("academy", "Crypto learning paths"),
        BotCommand("learn", "Start a lesson"),
        BotCommand("quiz", "Take a lesson quiz"),
        BotCommand("arbitrage", "Cross-market arb scanner"),
        BotCommand("behavior", "Trading psychology analysis"),
        BotCommand("infrastructure", "Infra ROI advisor"),
        BotCommand("finalform", "System maturity assessment"),
        BotCommand("prompts", "Prompt optimization tracker")
    ]
    await application.bot.set_my_commands(commands)
    
    # 3. Notify Owner
    try:
        await application.bot.send_message(
            chat_id=config.MY_TELEGRAM_ID, 
            text="[RESTART] Bot Refactored & Restarted! Everything is now running modularly."
        )
    except Exception as e:
        logger.error(f"Startup notification failed: {e}")

def start_bot():
    """Main entry point to start the whole system."""
    # 1. Start Dashboard & Discord in background
    try:
        start_dashboard()
        start_discord()
    except Exception as e:
        logger.error(f"Failed to start secondary services: {e}")

    # 3. Build Telegram App
    application = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    
    # 4. Register Handlers
    # General
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("clear", handlers.clear))
    application.add_handler(CommandHandler("status", handlers.status))
    application.add_handler(CommandHandler("health", handlers.health_command))
    application.add_handler(CommandHandler("stats", handlers.stats_command))
    
    # Portfolio
    application.add_handler(CommandHandler("add", handlers.add_position))
    application.add_handler(CommandHandler("portfolio", handlers.portfolio))
    application.add_handler(CommandHandler("remove", handlers.remove))
    application.add_handler(CommandHandler("update", handlers.update_pos))
    
    # Alerts
    application.add_handler(CommandHandler("alert", handlers.set_alert))
    application.add_handler(CommandHandler("alerts", handlers.list_alerts))
    application.add_handler(CommandHandler("cancelalert", handlers.cancel_alert))
    application.add_handler(CommandHandler("alerthistory", handlers.alert_history))
    
    # Market & Analysis
    application.add_handler(CommandHandler("market", handlers.market_overview_command))
    application.add_handler(CommandHandler("top", handlers.top_cryptos_command))
    application.add_handler(CommandHandler("fear", handlers.fear_greed_command))
    application.add_handler(CommandHandler("ta", handlers.ta_command))
    application.add_handler(CommandHandler("analyze", handlers.analyze_command))
    application.add_handler(CommandHandler("research", handlers.research_command))
    application.add_handler(CommandHandler("compare", handlers.compare_multi_command))
    application.add_handler(CommandHandler("onchain", handlers.onchain_command))
    application.add_handler(CommandHandler("optimize", handlers.optimize_command))
    application.add_handler(CommandHandler("accuracy", handlers.accuracy_command))
    application.add_handler(CommandHandler("predictions", handlers.predictions_command))
    application.add_handler(CommandHandler("risk", handlers.risk_command))
    application.add_handler(CommandHandler("rebalance", handlers.rebalance_command))
    application.add_handler(CommandHandler("gas", handlers.gas_command))
    application.add_handler(CommandHandler("smartmoney", handlers.smartmoney_command))
    application.add_handler(CommandHandler("news", handlers.news_command))
    application.add_handler(CommandHandler("sentiment", handlers.sentiment_command))
    
    # Journal & Notes
    application.add_handler(CommandHandler("log", handlers.log_entry))
    application.add_handler(CommandHandler("journal", handlers.show_journal))
    application.add_handler(CommandHandler("note", handlers.add_permanent_note))
    application.add_handler(CommandHandler("notes", handlers.show_notes))
    application.add_handler(CommandHandler("deletenote", handlers.delete_permanent_note))
    application.add_handler(CommandHandler("search", handlers.search_all))
    
    # Autonomous Reports
    application.add_handler(CommandHandler("briefing", handlers.briefing_command))
    application.add_handler(CommandHandler("evening", handlers.evening_command))
    application.add_handler(CommandHandler("weeklyreview", handlers.weekly_review_command))
    application.add_handler(CommandHandler("dailyreview", handlers.daily_review_command))
    
    # Wallet Watcher
    application.add_handler(CommandHandler("watchallet", handlers.watch_wallet_command))
    application.add_handler(CommandHandler("wallets", handlers.wallet_watchlist_command))
    application.add_handler(CommandHandler("watchlist", handlers.watchlist_command)) # research watchlist
    application.add_handler(CommandHandler("removewallet", handlers.remove_wallet_command))
    
    # Special Tools
    application.add_handler(CommandHandler("backup", handlers.backup_command))
    application.add_handler(CommandHandler("exporttrades", handlers.export_trades_command))
    application.add_handler(CommandHandler("scanner", handlers.scanner_command))
    application.add_handler(CommandHandler("opportunities", handlers.opportunities_command))
    application.add_handler(CommandHandler("complexalerts", handlers.complex_alerts_list))
    
    # Quant Models
    application.add_handler(CommandHandler("edge", quant_handlers.handle_edge))
    application.add_handler(CommandHandler("quant", quant_handlers.handle_quant))
    application.add_handler(CommandHandler("ev", quant_handlers.handle_ev))
    
    # Backtesting
    application.add_handler(CommandHandler("backtest", backtest_handlers.handle_backtest))
    application.add_handler(CommandHandler("strategies", backtest_handlers.handle_strategies))
    
    # DeFi Intelligence
    application.add_handler(CommandHandler("yields", defi_handlers.handle_yields))
    application.add_handler(CommandHandler("protocol", defi_handlers.handle_protocol))
    application.add_handler(CommandHandler("il", defi_handlers.handle_il))
    application.add_handler(CommandHandler("gasbest", defi_handlers.handle_gasbest))
    application.add_handler(CommandHandler("estimate", defi_handlers.handle_estimate))
    
    # ML Signals
    application.add_handler(CommandHandler("ml", ml_handlers.handle_ml))
    application.add_handler(CommandHandler("anomaly", ml_handlers.handle_anomaly))
    application.add_handler(CommandHandler("forecast", ml_handlers.handle_forecast))
    
    # Social Intelligence
    application.add_handler(CommandHandler("social", social_handlers.handle_social))
    application.add_handler(CommandHandler("fomo", social_handlers.handle_fomo))
    
    # Institutional Tracker
    application.add_handler(CommandHandler("institutional", institutional_handlers.handle_institutional))
    application.add_handler(CommandHandler("etfflows", institutional_handlers.handle_etfflows))
    application.add_handler(CommandHandler("cot", institutional_handlers.handle_cot))
    
    # Cross-Chain Monitor
    application.add_handler(CommandHandler("chains", chain_handlers.handle_chains))
    application.add_handler(CommandHandler("chain", chain_handlers.handle_chain))
    application.add_handler(CommandHandler("bridges", chain_handlers.handle_bridges))
    
    # Voice Interface
    application.add_handler(CommandHandler("voice", voice_handlers.toggle_voice))
    application.add_handler(MessageHandler(filters.VOICE, voice_handlers.handle_voice_message))
    
    # Position Sizing & Risk Management
    application.add_handler(CommandHandler("size", sizer_handlers.handle_size))
    application.add_handler(CommandHandler("kelly", sizer_handlers.handle_kelly))
    application.add_handler(CommandHandler("heat", sizer_handlers.handle_heat))
    application.add_handler(CommandHandler("sizing", sizer_handlers.handle_sizing))
    
    # Orchestrator (Level 20)
    application.add_handler(CommandHandler("regime", orchestrator_handlers.regime_command))
    application.add_handler(CommandHandler("mode", orchestrator_handlers.mode_command))
    application.add_handler(CommandHandler("orchestrator", orchestrator_handlers.orchestrator_command))
    application.add_handler(CommandHandler("settings", orchestrator_handlers.settings_command))
    
    # Options (Level 29)
    application.add_handler(CommandHandler("options", options_handlers.options_command))
    application.add_handler(CommandHandler("maxpain", options_handlers.maxpain_command))
    application.add_handler(CommandHandler("iv", options_handlers.iv_command))
    
    # Debate System (Level 30)
    application.add_handler(CommandHandler("debate", debate_handlers.debate_command))
    application.add_handler(CommandHandler("quickdebate", debate_handlers.quickdebate_command))
    
    # Event Predictor (Level 31)
    application.add_handler(CommandHandler("calendar", event_handlers.calendar_command))
    application.add_handler(CommandHandler("predict", event_handlers.predict_command))
    application.add_handler(CommandHandler("imminent", event_handlers.imminent_command))
    
    # Macro Monitor (Level 32)
    application.add_handler(CommandHandler("macro", macro_handlers.macro_command))
    application.add_handler(CommandHandler("correlation", macro_handlers.correlation_command))
    application.add_handler(CommandHandler("dxy", macro_handlers.dxy_command))
    
    # Security Hardening (Level 34)
    application.add_handler(CommandHandler("security", security_handlers.security_command))
    application.add_handler(CommandHandler("auditlog", security_handlers.auditlog_command))
    application.add_handler(CommandHandler("2fa", security_handlers.twofa_command))
    application.add_handler(CommandHandler("cleanup", security_handlers.cleanup_command))
    application.add_handler(CommandHandler("ratelimit", security_handlers.ratelimit_command))
    
    # Performance Attribution (Level 35)
    application.add_handler(CommandHandler("attribution", attribution_handlers.attribution_command))
    application.add_handler(CommandHandler("benchmark", attribution_handlers.benchmark_command))
    application.add_handler(CommandHandler("factors", attribution_handlers.factors_command))
    application.add_handler(CommandHandler("alpha", attribution_handlers.alpha_command))
    application.add_handler(CommandHandler("winners", attribution_handlers.winners_command))
    application.add_handler(CommandHandler("losers", attribution_handlers.losers_command))
    
    # Trade Proposals (Level 36)
    application.add_handler(CommandHandler("proposal", proposal_handlers.propose_command))
    application.add_handler(CommandHandler("proposals", proposal_handlers.proposals_command))
    application.add_handler(CommandHandler("proposalstats", proposal_handlers.proposalstats_command))
    
    # Workflow Engine (Level 20/33)
    workflow_conv = ConversationHandler(
        entry_points=[CommandHandler("createworkflow", workflow_handlers.create_workflow_start)],
        states={
            workflow_handlers.WF_TRIGGER: [MessageHandler(filters.TEXT & (~filters.COMMAND), workflow_handlers.workflow_choose_trigger)],
            workflow_handlers.WF_TRIGGER_PARAMS: [MessageHandler(filters.TEXT & (~filters.COMMAND), workflow_handlers.workflow_set_trigger_params)],
            workflow_handlers.WF_STEPS: [MessageHandler(filters.TEXT & (~filters.COMMAND), workflow_handlers.workflow_choose_steps)],
            workflow_handlers.WF_NAME: [MessageHandler(filters.TEXT & (~filters.COMMAND), workflow_handlers.workflow_set_name)],
            workflow_handlers.WF_CONFIRM: [MessageHandler(filters.TEXT & (~filters.COMMAND), workflow_handlers.workflow_confirm)],
        },
        fallbacks=[CommandHandler("cancel", workflow_handlers.workflow_cancel)]
    )
    application.add_handler(workflow_conv)
    application.add_handler(CommandHandler("workflows", workflow_handlers.workflows_command))
    application.add_handler(CommandHandler("runworkflow", workflow_handlers.run_workflow_command))
    application.add_handler(CommandHandler("workflowhistory", workflow_handlers.workflow_history_command))
    
    # Airdrop Intelligence (Part 7)
    application.add_handler(CommandHandler("airdrop", airdrop_handlers.airdrop_command))
    application.add_handler(CommandHandler("airdroptasks", airdrop_handlers.airdrop_tasks_command))
    application.add_handler(CommandHandler("airdropstrategy", airdrop_handlers.airdrop_strategy_command))
    application.add_handler(CommandHandler("airdropstats", airdrop_handlers.airdrop_stats_command))
    application.add_handler(CommandHandler("addsnapshot", airdrop_handlers.add_snapshot_command))
    application.add_handler(CommandHandler("recordairdrop", airdrop_handlers.record_airdrop_command))
    application.add_handler(CommandHandler("linkwallet", airdrop_handlers.link_wallet_command))
    application.add_handler(CommandHandler("mywallet", airdrop_handlers.my_wallet_command))
    application.add_handler(CommandHandler("updatewallet", airdrop_handlers.update_wallet_command))
    
    # Unified Intelligence Hub (Level 40)
    application.add_handler(CommandHandler("hub", hub_handlers.hub_command))
    application.add_handler(CommandHandler("signals", hub_handlers.signals_command))
    application.add_handler(CommandHandler("agenda", hub_handlers.agenda_command))
    application.add_handler(CommandHandler("weeklyreport", hub_handlers.weekly_report_command))
    
    # The Living Agent (Part 8)
    application.add_handler(CommandHandler("skills", skill_handlers.skills_command))
    application.add_handler(CommandHandler("memory", skill_handlers.memory_command))
    application.add_handler(CommandHandler("evolution", skill_handlers.evolution_command))
    
    # Personal Crypto Academy (Level 39)
    application.add_handler(CommandHandler("academy", education_handlers.academy_command))
    application.add_handler(CommandHandler("learn", education_handlers.learn_command))
    application.add_handler(CommandHandler("quiz", education_handlers.quiz_command))
    application.add_handler(CommandHandler("answer", education_handlers.answer_command))
    
    # Frontier Tiers (Tiers 5-10)
    application.add_handler(CommandHandler("arbitrage", frontier_handlers.arbitrage_command))
    application.add_handler(CommandHandler("behavior", frontier_handlers.behavior_command))
    application.add_handler(CommandHandler("infrastructure", frontier_handlers.infrastructure_command))
    application.add_handler(CommandHandler("finalform", frontier_handlers.final_form_command))
    application.add_handler(CommandHandler("prompts", frontier_handlers.prompts_command))
    
    # Conversations
    complex_conv = ConversationHandler(
        entry_points=[CommandHandler("complexalert", handlers.start_complex_alert)],
        states={
            handlers.CHOOSING_TYPE: [MessageHandler(filters.TEXT & (~filters.COMMAND), handlers.choose_type)],
            handlers.GETTING_S1: [MessageHandler(filters.TEXT & (~filters.COMMAND), handlers.get_s1)],
            handlers.GETTING_T1: [MessageHandler(filters.TEXT & (~filters.COMMAND), handlers.get_t1)],
            handlers.GETTING_D1: [MessageHandler(filters.TEXT & (~filters.COMMAND), handlers.get_d1)],
            handlers.GETTING_OP: [MessageHandler(filters.TEXT & (~filters.COMMAND), handlers.get_op)],
            handlers.GETTING_S2: [MessageHandler(filters.TEXT & (~filters.COMMAND), handlers.get_s2)],
            handlers.GETTING_T2: [MessageHandler(filters.TEXT & (~filters.COMMAND), handlers.get_t2)],
            handlers.GETTING_D2: [MessageHandler(filters.TEXT & (~filters.COMMAND), handlers.get_d2)],
            handlers.GETTING_NAME: [MessageHandler(filters.TEXT & (~filters.COMMAND), handlers.get_name_and_finish)],
        },
        fallbacks=[CommandHandler("cancel", handlers.cancel_conv)]
    )
    application.add_handler(complex_conv)
    
    quickstart_conv = ConversationHandler(
        entry_points=[CommandHandler("quickstart", handlers.quickstart_start)],
        states={
            handlers.QS_PORTFOLIO: [CommandHandler("add", handlers.qs_portfolio_step)],
            handlers.QS_ALERT: [CommandHandler("alert", handlers.qs_alert_step)],
            handlers.QS_JOURNAL: [CommandHandler("log", handlers.qs_journal_step)],
            handlers.QS_BRIEFING: [CommandHandler("briefing", handlers.qs_briefing_step)],
        },
        fallbacks=[CommandHandler("cancel", handlers.qs_cancel)]
    )
    application.add_handler(quickstart_conv)
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(handlers.help_button_handler, pattern="^help_"))
    
    # Message Handler (AI Orchestrator)
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), core_orchestrator.route_message))
    
    # 5. Run Polling
    print("--- (^) ShufaClaw Bot is starting! ---")
    application.run_polling()
