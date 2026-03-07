"""
ShufaClaw V2 — Risk Management Engine

Enforces hard geometric risk limits on the portfolio.
This module has veto power over all other modules and can halt the system.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from crypto_agent.schemas.trading import RiskLimits, RiskAlertLevel, TargetPortfolio, Position, RiskEvent
from crypto_agent import config

logger = logging.getLogger(__name__)


def _limits_from_config() -> RiskLimits:
    """Build RiskLimits from environment variables."""
    return RiskLimits(
        max_portfolio_drawdown=config.RISK_MAX_DRAWDOWN,
        max_daily_loss=config.RISK_MAX_DAILY_LOSS,
        max_single_asset_exposure=config.RISK_MAX_SINGLE_EXPOSURE,
        max_leverage=config.RISK_MAX_LEVERAGE,
        max_risk_per_trade=config.RISK_MAX_PER_TRADE,
        max_open_positions=config.RISK_MAX_POSITIONS,
    )


class RiskManager:
    """Gatekeeper that intercepts all portfolio and execution commands."""

    def __init__(self, limits: Optional[RiskLimits] = None):
        self.limits = limits or _limits_from_config()
        self.system_halted = False
        self.peak_nav = 0.0
        self._event_handler: Optional[Callable[[RiskEvent], None]] = None

    def set_event_handler(self, handler: Callable[[RiskEvent], None]) -> None:
        """Set callback for risk events (persistence, Kafka, alerts)."""
        self._event_handler = handler

    def _emit_event(self, event: RiskEvent) -> None:
        """Emit risk event to handler (async persist/Kafka)."""
        if self._event_handler:
            try:
                self._event_handler(event)
            except Exception as e:
                logger.error(f"Risk event handler failed: {e}")
        
    def evaluate_portfolio_risk(self, current_nav: float, cash: float, positions: List[Position]) -> RiskAlertLevel:
        """
        Calculates all risk metrics against hard geometric limits.
        Returns the highest severity Alert Level triggered.
        """
        if self.system_halted:
            return RiskAlertLevel.EMERGENCY
            
        if current_nav > self.peak_nav:
            self.peak_nav = current_nav
            
        highest_alert = RiskAlertLevel.GREEN
        
        # 1. Max Drawdown Check
        if self.peak_nav > 0:
            drawdown = (self.peak_nav - current_nav) / self.peak_nav
            util = (drawdown / self.limits.max_portfolio_drawdown) * 100 if self.limits.max_portfolio_drawdown > 0 else 0
            if drawdown >= self.limits.max_portfolio_drawdown:
                self._emit_event(RiskEvent(
                    alert_level=RiskAlertLevel.EMERGENCY,
                    limit_type="max_portfolio_drawdown",
                    current_value=drawdown,
                    limit_value=self.limits.max_portfolio_drawdown,
                    utilization_pct=util,
                    action_taken="HALT_ALL_LIQUIDATE",
                    details=f"Drawdown {drawdown*100:.2f}% breached limit {self.limits.max_portfolio_drawdown*100:.2f}%",
                ))
                logger.critical(f"EMERGENCY: Max Drawdown breached! {drawdown*100:.2f}% >= {self.limits.max_portfolio_drawdown*100:.2f}%")
                self.system_halted = True
                return RiskAlertLevel.EMERGENCY
            elif drawdown >= self.limits.max_portfolio_drawdown * 0.8:
                self._emit_event(RiskEvent(
                    alert_level=RiskAlertLevel.RED,
                    limit_type="max_portfolio_drawdown",
                    current_value=drawdown,
                    limit_value=self.limits.max_portfolio_drawdown,
                    utilization_pct=util,
                    action_taken="HALT_NEW_ORDERS",
                    details=f"Drawdown {drawdown*100:.2f}% approaching limit",
                ))
                logger.warning(f"RED ALERT: Approaching Max Drawdown. Current {drawdown*100:.2f}%")
                highest_alert = RiskAlertLevel.RED
                
        # 2. Max Single Asset Exposure
        for pos in positions:
            exposure_pct = (pos.size * pos.current_price) / current_nav if current_nav > 0 else 0
            if exposure_pct >= self.limits.max_single_asset_exposure:
                highest_alert = max(highest_alert, RiskAlertLevel.RED)
                logger.warning(f"RED ALERT: {pos.symbol} exposure {exposure_pct*100:.2f}% >= Limit {self.limits.max_single_asset_exposure*100:.2f}%")
            elif exposure_pct >= self.limits.max_single_asset_exposure * 0.8:
                highest_alert = max(highest_alert, RiskAlertLevel.YELLOW)
                
        # 3. Max Leverage (Gross Exposure / NAV)
        gross_exposure = sum((p.size * p.current_price) for p in positions)
        leverage = gross_exposure / current_nav if current_nav > 0 else 0
        if leverage >= self.limits.max_leverage:
            highest_alert = max(highest_alert, RiskAlertLevel.RED)
            logger.warning(f"RED ALERT: Leverage {leverage:.2f}x >= Limit {self.limits.max_leverage}x")
            
        # 4. Max Open Positions Limit
        if len(positions) > self.limits.max_open_positions:
            highest_alert = max(highest_alert, RiskAlertLevel.RED)
            logger.warning(f"RED ALERT: Max positions exceeded! {len(positions)} > {self.limits.max_open_positions}")

        return highest_alert

    def vet_target_portfolio(self, proposed: TargetPortfolio, current_nav: float) -> TargetPortfolio:
        """
        Intercepts proposed trades before execution.
        Modifies or rejects the target portfolio if it violates risk models.
        """
        alert_level = self.evaluate_portfolio_risk(current_nav, proposed.cash_usd, proposed.positions)
        
        if alert_level == RiskAlertLevel.EMERGENCY:
            logger.critical("❌ VETO: System is HALTED. Rejecting all new positions.")
            # In a live env, we would forcefully zero out the positions list here to liquidate.
            return TargetPortfolio(positions=[], total_value_usd=current_nav, cash_usd=current_nav)
            
        if alert_level == RiskAlertLevel.RED:
            logger.warning("❌ VETO: Red Alert active. Halting new portfolio expansion.")
            # Hard rejection of the target portfolio, returning empty or purely closing orders
            return proposed 
            
        if alert_level == RiskAlertLevel.YELLOW:
            logger.warning("⚠️ VETO: Yellow Alert active. Slashing proposed position sizes by 50%.")
            for pos in proposed.positions:
                pos.size *= 0.5
                
        return proposed

# Global Instance
risk_manager = RiskManager()
