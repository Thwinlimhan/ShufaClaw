import logging
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from crypto_agent import config
from crypto_agent.storage import database
from crypto_agent.alerts import engine as alert_engine
from crypto_agent.storage import backup as backup_service
from crypto_agent.journal import reviewer
from crypto_agent.autonomous import reporter as briefing_service
from crypto_agent.autonomous import reporter as briefing_service
from crypto_agent.autonomous import watcher as wallet_watcher
from crypto_agent.intelligence import performance_tracker
from crypto_agent.core.cognitive_loop import CognitiveLoop
from crypto_agent.core.orchestrator import orchestrator

logger = logging.getLogger(__name__)

def setup_scheduler(application):
    """Configures all background tasks and periodic reports."""
    scheduler = AsyncIOScheduler()
    my_tz = pytz.timezone('Asia/Yangon') # UTC+6:30
    
    # 1. Alert Checker (Every 30s)
    engine = alert_engine.start_alert_checker(application.bot, config.MY_TELEGRAM_ID)
    scheduler.add_job(engine.check_all_alerts, 'interval', seconds=30)
    
    # 2. Automated Weekly Review (Sunday 6:00 PM)
    scheduler.add_job(
        reviewer.perform_review, 
        CronTrigger(day_of_week='sun', hour=18, minute=0, timezone=my_tz),
        args=[application.bot, config.MY_TELEGRAM_ID, 7, True]
    )
    
    # 3. Weekly Backup (Monday 7:55 AM - offset to avoid conflict with morning briefing)
    scheduler.add_job(
        backup_service.BackupService.run_full_backup,
        CronTrigger(day_of_week='mon', hour=7, minute=55, timezone=my_tz),
        args=[application.bot, config.MY_TELEGRAM_ID]
    )
    
    # 4. Morning Briefing (Daily 8:00 AM)
    scheduler.add_job(
        briefing_service.Reporter.send_morning_briefing,
        CronTrigger(hour=8, minute=0, timezone=my_tz),
        args=[application.bot, config.MY_TELEGRAM_ID]
    )

    # 5. Evening Summary (Daily 9:00 PM)
    scheduler.add_job(
        briefing_service.Reporter.send_evening_summary,
        CronTrigger(hour=21, minute=0, timezone=my_tz),
        args=[application.bot, config.MY_TELEGRAM_ID]
    )

    # 6. Wallet Watcher (Every 5 mins, offset by 30 seconds to avoid conflict with scanner)
    watcher = wallet_watcher.WalletWatcher()
    scheduler.add_job(
        watcher.check_all_wallets,
        'interval',
        minutes=5,
        seconds=30,
        args=[application.bot, config.MY_TELEGRAM_ID]
    )
    
    # 7. Market Scanner (Every 5 mins)
    from crypto_agent.autonomous import scanner as market_scanner
    scanner = market_scanner.MarketScanner(application.bot, config.MY_TELEGRAM_ID)
    scheduler.add_job(
        scanner.run_scan,
        'interval',
        minutes=5
    )

    # 8. Smart Money Tracker (Every 15 mins)
    from crypto_agent.autonomous import smart_money
    sm_tracker = smart_money.SmartMoneyTracker(application.bot, config.MY_TELEGRAM_ID)
    scheduler.add_job(
        sm_tracker.run_checks,
        'interval',
        minutes=15
    )
    
    # 9. Weekly Deep Research (Friday 10:00 AM)
    from crypto_agent.intelligence import research_agent
    r_agent = research_agent.ResearchAgent(application.bot, config.MY_TELEGRAM_ID)
    scheduler.add_job(
        r_agent.run_automated_research,
        CronTrigger(day_of_week='fri', hour=10, minute=0, timezone=my_tz)
    )
    
    # 10. Prediction Accuracy Checker (Every hour)
    tracker = performance_tracker.PerformanceTracker()
    scheduler.add_job(
        tracker.check_pending_predictions,
        'interval',
        hours=1
    )
    
    # 11. AI Self-Learning Session (Saturday 10:00 AM)
    scheduler.add_job(
        tracker.run_learning_session,
        CronTrigger(day_of_week='sat', hour=10, minute=0, timezone=my_tz),
        args=[application.bot, config.MY_TELEGRAM_ID]
    )
    
    # 12. Cognitive Loop Cycle (Every 15 mins)
    cog_loop = CognitiveLoop()
    scheduler.add_job(
        cog_loop.run_cycle_proactive,
        'interval',
        minutes=15
    )
    
    # 13. Market Regime Update (Every 60 mins)
    scheduler.add_job(
        orchestrator.update_regime,
        'interval',
        minutes=60
    )
    
    scheduler.start()
    logger.info("Scheduler started with all automated tasks.")
    return scheduler
