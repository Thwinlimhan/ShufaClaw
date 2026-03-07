"""
ShufaClaw V2 — AI Agent Orchestrator

Manages the lifecycle, scheduling, and error recovery for all 
background AI Agents. Guarantees critical agents do not block 
data flow pipelines by using APScheduler's async execution.
"""

import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from crypto_agent.intelligence.agents import MarketAnalystAgent, StrategyResearchAgent

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """Manages the lifecycle of background AI Tasks."""
    
    def __init__(self):
        # We need an Async scheduler so it doesn't block the main FastAPI loop
        self.scheduler = AsyncIOScheduler()
        self.market_analyst = MarketAnalystAgent()
        self.strategy_researcher = StrategyResearchAgent()
        
    def start(self):
        """Bind all agents to their respective schedules and boot."""
        logger.info("⚙️ Booting AI Agent Orchestrator...")
        
        # 1. Market Analyst - Every 4 Hours
        # We track "0 */4 * * *" using interval for simpler demo config:
        self.scheduler.add_job(
            self._run_market_analyst, 
            IntervalTrigger(hours=4), 
            id="market_analyst_job", 
            replace_existing=True,
            coalesce=True, # Prevent it from piling up if the bot crashes
            max_instances=1
        )
        
        # 2. Strategy Research Agent - Daily at 02:00 UTC (Low Traffic)
        self.scheduler.add_job(
            self._run_strategy_research,
            CronTrigger(hour=2, minute=0, timezone="UTC"),
            id="strategy_research_job",
            replace_existing=True,
            coalesce=True,
            max_instances=1
        )
        
        # In a fully deployed V2, we also map:
        # - RegimeAdaptationAgent -> Subscribes to Kafka `regime.changes`
        # - RiskReviewAgent -> Subscribes to Kafka `risk.alerts`
        
        self.scheduler.start()
        logger.info("   ✅ Agent Orchestrator online. 2 Active Scheduled Roles.")

    async def _run_market_analyst(self):
        """Wrapper for APScheduler."""
        try:
            await self.market_analyst.run("BTCUSDT")
        except Exception as e:
            logger.error(f"Orchestrator caught failure in Market Analyst: {e}")
            
    async def _run_strategy_research(self):
        """Wrapper for APScheduler."""
        try:
            # Huge compute job, runs in background thread/task natively 
            await self.strategy_researcher.run("BTCUSDT")
            await self.strategy_researcher.run("ETHUSDT")
        except Exception as e:
            logger.error(f"Orchestrator caught failure in Strategy Researcher: {e}")

    def shutdown(self):
        """Gracefully stop background agents."""
        logger.info("Stopping AI Agent Orchestrator...")
        self.scheduler.shutdown()

# Global Singleton
orchestrator = AgentOrchestrator()
