"""
ShufaClaw V2 — Specialized AI Agents

Automated, asynchronous agents that conduct research, analyze the market, 
and suggest adaptations directly to the V2 Database models.
"""

import logging
import time
import json
from typing import Dict, Any

from crypto_agent.intelligence.analyst import get_ai_response
from crypto_agent.schemas.agents import AgentReport, AgentType, AgentPriority
from crypto_agent.data import technical as tech
from crypto_agent.intelligence.feature_engine import feature_engine
from crypto_agent.intelligence.regime_detector import regime_detector
from crypto_agent.intelligence.strategy_discovery import discovery_engine

logger = logging.getLogger(__name__)

class BaseAgent:
    """Superclass for background AI tasks."""
    agent_type = AgentType.MARKET_ANALYST
    priority = AgentPriority.NORMAL

    async def _generate_report(self, trigger: str, summary: str, analysis: str, recommendations: list, data_snap: dict, duration: float) -> AgentReport:
        report = AgentReport(
            agent_type=self.agent_type,
            trigger=trigger,
            priority=self.priority,
            summary=summary,
            analysis=analysis,
            recommendations=recommendations,
            data_snapshot=data_snap,
            execution_time_seconds=duration,
        )
        # In full V2, this gets saved to TimescaleDB `agent_reports` table
        logger.info(f"✅ {self.agent_type.value.upper()} Generated Report: {summary}")
        return report

class MarketAnalystAgent(BaseAgent):
    """Summarizes market regime, key levels, and notable feature alerts."""
    agent_type = AgentType.MARKET_ANALYST

    async def run(self, symbol: str = "BTCUSDT") -> AgentReport:
        start = time.time()
        logger.info(f"🤖 MarketAnalystAgent running for {symbol}...")
        
        try:
            klines = await tech.fetch_klines(symbol, "1h", limit=200)
            if not klines:
                return None
                
            features = feature_engine.compute_features(symbol, "1h", klines)
            regime = regime_detector.detect_regime(features)
            
            # Formulate prompt for LLM
            prompt = f"""
            Act as a Senior Market Analyst for a Crypto Hedge Fund.
            Analyze this 1-Hour data for {symbol}:
            - Market Regime: {regime.value}
            - RSI (14): {features.rsi_14:.1f} if features.rsi_14 else 'N/A'
            - 20 SMA vs 200 SMA: {features.sma_20} vs {features.sma_200}
            - Bolinger Band Width: {features.bb_width if features.bb_width else 'N/A'}
            
            Provide:
            1. Unemotional summary of current conditions.
            2. Actionable tactical recommendation (Short-term context).
            Format constraints: No rambling. Provide 2 paragraphs.
            """
            
            messages = [{"role": "system", "content": "You are a quant analyst."}, {"role": "user", "content": prompt}]
            analysis = await get_ai_response(messages, feature_name="agent_market_analyst")
            
            if not analysis:
                analysis = "LLM Generation Failed."
                
            return await self._generate_report(
                trigger="scheduled_4h",
                summary=f"Regime is {regime.value}. RSI: {features.rsi_14:.1f if features.rsi_14 else 0}",
                analysis=analysis,
                recommendations=["Monitor support bands"],
                data_snap={"regime": regime.value, "rsi": features.rsi_14 if features.rsi_14 else 0},
                duration=time.time() - start
            )
            
        except Exception as e:
            logger.error(f"MarketAnalystAgent failed: {e}")
            return None


class StrategyResearchAgent(BaseAgent):
    """Automatically hunts for new Alpha using the VectorBT Strategy Discovery Engine."""
    agent_type = AgentType.STRATEGY_RESEARCH
    priority = AgentPriority.LOW # Computation heavy, run in deep background

    async def run(self, symbol: str = "BTCUSDT") -> AgentReport:
        start = time.time()
        logger.info(f"🤖 StrategyResearchAgent sweeping grids for {symbol}...")
        
        try:
            # Trigger the massive underlying vector BT optimizer
            candidate_dict = await discovery_engine.discover_sma_cross(symbol, "1h")
            
            if candidate_dict:
                summary = f"Discovered highly profitable SMA Cross for {symbol}"
                analysis = f"Walk-forward analysis passed with Sharpe {candidate_dict['best_sharpe']:.2f}. " \
                           f"Params: {candidate_dict['params']}."
                recs = [f"Promote Candidate {candidate_dict['id']} to live Paper Trading."]
            else:
                summary = f"No new profitable SMA Cross strategies found for {symbol}"
                analysis = "Grid search completed. All models failed Walk-Forward generalization testing or fell below minimum Sharpe of 1.0."
                recs = ["Expand parameter search window next run."]
                
            return await self._generate_report(
                trigger="scheduled_daily",
                summary=summary,
                analysis=analysis,
                recommendations=recs,
                data_snap=candidate_dict if candidate_dict else {},
                duration=time.time() - start
            )
        except Exception as e:
            logger.error(f"StrategyResearchAgent failed: {e}")
            return None
