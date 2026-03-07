# Market Orchestrator - Master Brain of the Bot
# Coordinates all systems and adapts behavior based on market regime

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json

from crypto_agent.storage import database, workflow_db
from crypto_agent.data import prices as price_service, market as market_service
from crypto_agent.data import technical as tech

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Market regime classifications."""
    BULL_TREND = "bull_trend"
    BEAR_TREND = "bear_trend"
    HIGH_VOLATILITY = "high_volatility"
    RANGING = "ranging"
    UNKNOWN = "unknown"

class BotMode(Enum):
    """Bot operating modes."""
    NORMAL = "normal"
    AGGRESSIVE = "aggressive"
    QUIET = "quiet"
    NIGHT = "night"

class Priority(Enum):
    """Notification priority levels."""
    CRITICAL = 1  # Portfolio down 10%+, liquidation risk, exchange hack
    HIGH = 2      # Coin down 5%+ in hour, major break, big news
    MEDIUM = 3    # Alert triggered, opportunity found, scanner finding
    LOW = 4       # Weekly summaries, general commentary

class MarketOrchestrator:
    """
    Master brain that coordinates all bot systems.
    Detects market regime and adapts bot behavior accordingly.
    """
    
    def __init__(self):
        self.current_regime = MarketRegime.UNKNOWN
        self.regime_confidence = 0.0
        self.regime_since = None
        self.previous_regime = None
        self.regime_factors = {}
        
        self.current_mode = BotMode.NORMAL
        self.mode_override_until = None
        
        self.last_regime_check = None
        self.decisions_log = []
        
        # Behavior settings per regime
        self.regime_settings = {
            MarketRegime.BULL_TREND: {
                'alert_sensitivity': 'relaxed',
                'scan_frequency_minutes': 5,
                'scanner_focus': 'momentum',
                'briefing_tone': 'optimistic',
                'portfolio_advice': 'ride_trends',
                'message_throttle': 'normal'
            },
            MarketRegime.BEAR_TREND: {
                'alert_sensitivity': 'heightened',
                'scan_frequency_minutes': 3,
                'scanner_focus': 'risk',
                'briefing_tone': 'cautious',
                'portfolio_advice': 'reduce_risk',
                'message_throttle': 'normal'
            },
            MarketRegime.HIGH_VOLATILITY: {
                'alert_sensitivity': 'high',
                'scan_frequency_minutes': 2,
                'scanner_focus': 'volatility',
                'briefing_tone': 'alert',
                'portfolio_advice': 'adjust_stops',
                'message_throttle': 'increased'
            },
            MarketRegime.RANGING: {
                'alert_sensitivity': 'normal',
                'scan_frequency_minutes': 10,
                'scanner_focus': 'breakouts',
                'briefing_tone': 'neutral',
                'portfolio_advice': 'accumulate',
                'message_throttle': 'reduced'
            }
        }
    
    # ==================== REGIME DETECTION ====================
    
    async def detect_market_regime(self) -> Tuple[MarketRegime, float, Dict]:
        """
        Analyze market conditions and determine current regime.
        Returns: (regime, confidence, factors)
        """
        logger.info("Detecting market regime...")
        
        factors = {}
        scores = {
            MarketRegime.BULL_TREND: 0,
            MarketRegime.BEAR_TREND: 0,
            MarketRegime.HIGH_VOLATILITY: 0,
            MarketRegime.RANGING: 0
        }
        
        # Factor 1: BTC vs 50-day SMA
        try:
            btc_price, _ = await price_service.get_price('BTC')
            sma_50 = await self._calculate_sma('BTC', days=50)
            
            if btc_price and sma_50:
                if btc_price > sma_50:
                    scores[MarketRegime.BULL_TREND] += 2
                    factors['btc_vs_sma'] = f"Above 50-day SMA (${sma_50:,.0f})"
                else:
                    scores[MarketRegime.BEAR_TREND] += 2
                    factors['btc_vs_sma'] = f"Below 50-day SMA (${sma_50:,.0f})"
        except Exception as e:
            logger.error(f"Error checking BTC SMA: {e}")
        
        # Factor 2: Fear & Greed Index
        try:
            fng = await price_service.get_fear_greed_index()
            if fng:
                value = fng['value']
                factors['fear_greed'] = f"{value} ({fng['classification']})"
                
                if value > 60:
                    scores[MarketRegime.BULL_TREND] += 2
                elif value < 40:
                    scores[MarketRegime.BEAR_TREND] += 2
                else:
                    scores[MarketRegime.RANGING] += 1
        except Exception as e:
            logger.error(f"Error checking Fear & Greed: {e}")
        
        # Factor 3: Consecutive green/red days
        try:
            consecutive = await self._count_consecutive_days('BTC')
            factors['consecutive_days'] = f"{abs(consecutive)} {'green' if consecutive > 0 else 'red'} days"
            
            if consecutive >= 3:
                scores[MarketRegime.BULL_TREND] += 2
            elif consecutive <= -3:
                scores[MarketRegime.BEAR_TREND] += 2
        except Exception as e:
            logger.error(f"Error checking consecutive days: {e}")
        
        # Factor 4: Volatility (ATR)
        try:
            atr = await self._calculate_atr('BTC', days=14)
            historical_atr = await self._calculate_atr('BTC', days=90)
            
            if atr and historical_atr:
                volatility_ratio = atr / historical_atr
                factors['volatility'] = f"ATR {volatility_ratio:.2f}x historical"
                
                if volatility_ratio > 2.0:
                    scores[MarketRegime.HIGH_VOLATILITY] += 3
                elif volatility_ratio < 0.7:
                    scores[MarketRegime.RANGING] += 2
        except Exception as e:
            logger.error(f"Error checking volatility: {e}")
        
        # Factor 5: Recent price swings
        try:
            swings = await self._count_large_swings('BTC', days=7, threshold=5.0)
            factors['large_swings'] = f"{swings} swings >5% in 7 days"
            
            if swings >= 4:
                scores[MarketRegime.HIGH_VOLATILITY] += 2
            elif swings <= 1:
                scores[MarketRegime.RANGING] += 1
        except Exception as e:
            logger.error(f"Error checking swings: {e}")
        
        # Factor 6: Price range tightness
        try:
            range_tightness = await self._calculate_range_tightness('BTC', days=7)
            factors['range_tightness'] = f"{range_tightness:.1f}% range"
            
            if range_tightness < 5:
                scores[MarketRegime.RANGING] += 2
        except Exception as e:
            logger.error(f"Error checking range: {e}")
        
        # Determine regime with highest score
        max_score = max(scores.values())
        if max_score == 0:
            return MarketRegime.UNKNOWN, 0.0, factors
        
        regime = max(scores, key=scores.get)
        confidence = min(max_score / 10.0, 1.0)  # Normalize to 0-1
        
        return regime, confidence, factors
    
    async def update_regime(self) -> bool:
        """
        Update the current market regime.
        Returns True if regime changed.
        """
        new_regime, confidence, factors = await self.detect_market_regime()
        
        regime_changed = False
        
        if new_regime != self.current_regime:
            self.previous_regime = self.current_regime
            self.current_regime = new_regime
            self.regime_since = datetime.now()
            regime_changed = True
            
            logger.info(f"Market regime changed: {self.previous_regime.value} → {new_regime.value}")
            
            # Log the regime change
            self._log_decision(
                'regime_change',
                f"Regime changed from {self.previous_regime.value} to {new_regime.value}",
                {'confidence': confidence, 'factors': factors}
            )
        
        self.regime_confidence = confidence
        self.regime_factors = factors
        self.last_regime_check = datetime.now()
        
        # Save to database
        workflow_db.save_market_regime(
            regime=new_regime.value,
            confidence=confidence,
            factors=json.dumps(factors),
            timestamp=datetime.now().isoformat()
        )
        
        return regime_changed
    
    # ==================== BEHAVIOR ADAPTATION ====================
    
    def get_current_settings(self) -> Dict:
        """Get current behavior settings based on regime and mode."""
        base_settings = self.regime_settings.get(
            self.current_regime,
            self.regime_settings[MarketRegime.RANGING]
        )
        
        # Apply mode overrides
        settings = base_settings.copy()
        
        if self.current_mode == BotMode.AGGRESSIVE:
            settings['alert_sensitivity'] = 'high'
            settings['scan_frequency_minutes'] = 2
            settings['message_throttle'] = 'increased'
        
        elif self.current_mode == BotMode.QUIET:
            settings['alert_sensitivity'] = 'critical_only'
            settings['scan_frequency_minutes'] = 15
            settings['message_throttle'] = 'minimal'
        
        elif self.current_mode == BotMode.NIGHT:
            settings['alert_sensitivity'] = 'critical_only'
            settings['message_throttle'] = 'critical_only'
        
        return settings
    
    def get_claude_system_prompt_addition(self) -> str:
        """Get additional system prompt based on current regime."""
        regime_prompts = {
            MarketRegime.BULL_TREND: (
                "MARKET CONTEXT: The market is in a bullish trend. "
                "Be optimistic but remind about taking profits. "
                "Focus on identifying continuation setups and momentum plays. "
                "Warn against FOMO and overleveraging."
            ),
            MarketRegime.BEAR_TREND: (
                "MARKET CONTEXT: The market is in a bearish trend. "
                "Emphasize capital preservation and risk management. "
                "Focus on identifying bottoming signals and oversold bounces. "
                "Suggest reducing position sizes and tightening stops."
            ),
            MarketRegime.HIGH_VOLATILITY: (
                "MARKET CONTEXT: The market is experiencing high volatility. "
                "Emphasize caution and proper position sizing. "
                "Warn about whipsaws and false breakouts. "
                "Suggest wider stops and smaller positions."
            ),
            MarketRegime.RANGING: (
                "MARKET CONTEXT: The market is ranging with low volatility. "
                "Focus on range-bound strategies and breakout setups. "
                "Suggest accumulation opportunities. "
                "Warn about low volume and potential for sudden moves."
            )
        }
        
        return regime_prompts.get(self.current_regime, "")
    
    def should_send_notification(self, priority: Priority) -> bool:
        """Determine if a notification should be sent based on priority and mode."""
        settings = self.get_current_settings()
        
        # Check mode override
        if self.current_mode == BotMode.QUIET:
            return priority == Priority.CRITICAL
        
        if self.current_mode == BotMode.NIGHT:
            return priority == Priority.CRITICAL
        
        # Check time of day
        hour = datetime.now().hour
        
        # Night hours (12am - 7am): Only critical
        if 0 <= hour < 7:
            return priority == Priority.CRITICAL
        
        # Busy hours (9am - 5pm): Critical and high
        if 9 <= hour < 17:
            return priority.value <= Priority.HIGH.value
        
        # Other times: All priorities
        return True
    
    def get_scan_frequency(self) -> int:
        """Get current scan frequency in minutes."""
        settings = self.get_current_settings()
        return settings['scan_frequency_minutes']
    
    def get_alert_threshold(self) -> str:
        """Get current alert sensitivity level."""
        settings = self.get_current_settings()
        return settings['alert_sensitivity']
    
    # ==================== MODE MANAGEMENT ====================
    
    def set_mode(self, mode: BotMode, duration_hours: Optional[int] = None):
        """Set bot operating mode, optionally with auto-revert."""
        self.current_mode = mode
        
        if duration_hours:
            self.mode_override_until = datetime.now() + timedelta(hours=duration_hours)
        else:
            self.mode_override_until = None
        
        self._log_decision(
            'mode_change',
            f"Mode changed to {mode.value}",
            {'duration_hours': duration_hours}
        )
        
        logger.info(f"Bot mode set to: {mode.value}")
    
    def check_mode_expiry(self):
        """Check if mode override has expired and revert to normal."""
        if self.mode_override_until and datetime.now() >= self.mode_override_until:
            self.current_mode = BotMode.NORMAL
            self.mode_override_until = None
            
            self._log_decision(
                'mode_revert',
                "Mode reverted to normal after timeout",
                {}
            )
            
            logger.info("Bot mode reverted to normal")
    
    # ==================== DECISION LOGGING ====================
    
    def _log_decision(self, decision_type: str, description: str, metadata: Dict):
        """Log an orchestrator decision."""
        decision = {
            'timestamp': datetime.now().isoformat(),
            'type': decision_type,
            'description': description,
            'metadata': metadata
        }
        
        self.decisions_log.append(decision)
        
        # Keep only last 100 decisions
        if len(self.decisions_log) > 100:
            self.decisions_log = self.decisions_log[-100:]
        
        # Save to database
        workflow_db.log_orchestrator_decision(
            decision_type=decision_type,
            description=description,
            metadata=json.dumps(metadata),
            timestamp=datetime.now().isoformat()
        )
    
    def get_recent_decisions(self, hours: int = 24) -> List[Dict]:
        """Get decisions made in the last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        recent = [
            d for d in self.decisions_log
            if datetime.fromisoformat(d['timestamp']) >= cutoff
        ]
        
        return recent
    
    # ==================== REPORTING ====================
    
    def get_regime_report(self) -> str:
        """Generate a formatted regime report."""
        if self.current_regime == MarketRegime.UNKNOWN:
            return "🌡️ **MARKET REGIME ANALYSIS**\n\nStatus: Unknown (not enough data)"
        
        # Regime emoji
        regime_emoji = {
            MarketRegime.BULL_TREND: "🐂",
            MarketRegime.BEAR_TREND: "🐻",
            MarketRegime.HIGH_VOLATILITY: "⚡",
            MarketRegime.RANGING: "📊"
        }
        
        emoji = regime_emoji.get(self.current_regime, "❓")
        regime_name = self.current_regime.value.replace('_', ' ').upper()
        
        confidence_text = "High" if self.regime_confidence > 0.7 else "Medium" if self.regime_confidence > 0.4 else "Low"
        
        report = f"🌡️ **MARKET REGIME ANALYSIS**\n\n"
        report += f"Current: {emoji} **{regime_name}** ({confidence_text} Confidence)\n\n"
        
        # Supporting factors
        report += "**Supporting factors:**\n"
        for key, value in self.regime_factors.items():
            report += f"• {value}\n"
        
        # Bot behavior
        settings = self.get_current_settings()
        report += f"\n**Bot behavior:**\n"
        report += f"• Alert threshold: {settings['alert_sensitivity']}\n"
        report += f"• Scan frequency: Every {settings['scan_frequency_minutes']} min\n"
        report += f"• Scanner focus: {settings['scanner_focus']}\n"
        report += f"• Briefing tone: {settings['briefing_tone']}\n"
        
        # Duration
        if self.regime_since:
            duration = datetime.now() - self.regime_since
            days = duration.days
            hours = duration.seconds // 3600
            
            if days > 0:
                report += f"\n**In effect since:** {self.regime_since.strftime('%b %d')} ({days} days ago)\n"
            else:
                report += f"\n**In effect since:** {hours} hours ago\n"
        
        # Previous regime
        if self.previous_regime and self.previous_regime != MarketRegime.UNKNOWN:
            prev_name = self.previous_regime.value.replace('_', ' ').title()
            report += f"**Previous regime:** {prev_name}\n"
        
        return report
    
    async def route_message(self, update, context):
        """Routes incoming messages through the orchestrator to the agent."""
        from crypto_agent.core.agent import handle_message
        
        # Add regime and mode context to the message handling process
        # (The agent will fetch this via prompts/context_builder)
        
        # Determine if we should respond based on priority (if applicable to messages)
        # For direct user messages, we usually always respond unless it's a critical-only mode
        if not self.should_send_notification(Priority.MEDIUM):
             # You might still want to reply if it's a direct message, 
             # but here we follow the orchestrator's rules.
             pass

        return await handle_message(update, context)
    
    def get_orchestrator_status(self) -> str:
        """Generate orchestrator status report."""
        report = "🧠 **ORCHESTRATOR STATUS**\n\n"
        
        # Current mode
        mode_emoji = {
            BotMode.NORMAL: "🔵",
            BotMode.AGGRESSIVE: "🔴",
            BotMode.QUIET: "🔇",
            BotMode.NIGHT: "🌙"
        }
        
        emoji = mode_emoji.get(self.current_mode, "⚪")
        report += f"**Mode:** {emoji} {self.current_mode.value.upper()}\n"
        
        if self.mode_override_until:
            time_left = self.mode_override_until - datetime.now()
            hours_left = time_left.seconds // 3600
            report += f"Auto-revert in: {hours_left} hours\n"
        
        report += f"\n**Current Regime:** {self.current_regime.value.replace('_', ' ').title()}\n"
        report += f"**Confidence:** {self.regime_confidence:.0%}\n"
        
        # Recent decisions
        recent = self.get_recent_decisions(hours=24)
        
        if recent:
            report += f"\n**Decisions (Last 24h):** {len(recent)}\n\n"
            
            # Show last 5
            for decision in recent[-5:]:
                time = datetime.fromisoformat(decision['timestamp']).strftime("%I:%M %p")
                report += f"• {time} - {decision['description']}\n"
        else:
            report += f"\n**Decisions (Last 24h):** None\n"
        
        # Settings
        settings = self.get_current_settings()
        report += f"\n**Active Settings:**\n"
        report += f"• Scan frequency: {settings['scan_frequency_minutes']} min\n"
        report += f"• Alert sensitivity: {settings['alert_sensitivity']}\n"
        report += f"• Message throttle: {settings['message_throttle']}\n"
        
        return report
    
    # ==================== HELPER METHODS ====================
    
    async def _calculate_sma(self, symbol: str, days: int) -> Optional[float]:
        """Calculate Simple Moving Average."""
        try:
            klines = await tech.fetch_klines(symbol, interval="1d", limit=max(days + 5, 60))
            if not klines or len(klines) < days:
                return None
            closes = [float(k[4]) for k in klines]
            sma = tech.calculate_sma(closes, days)
            return float(sma) if sma is not None else None
        except Exception as e:
            logger.error(f"SMA calc failed for {symbol}: {e}")
            return None
    
    async def _count_consecutive_days(self, symbol: str) -> int:
        """Count consecutive green or red days (positive = green, negative = red)."""
        try:
            klines = await tech.fetch_klines(symbol, interval="1d", limit=60)
            if not klines or len(klines) < 3:
                return 0

            # Binance kline: [open_time, open, high, low, close, ...]
            candles = [(float(k[1]), float(k[4])) for k in klines]

            count = 0
            # walk backwards from most recent closed candle
            for o, c in reversed(candles):
                if o == 0:
                    break
                is_green = c > o
                is_red = c < o
                if count == 0:
                    if is_green:
                        count = 1
                    elif is_red:
                        count = -1
                    else:
                        break
                else:
                    if count > 0 and is_green:
                        count += 1
                    elif count < 0 and is_red:
                        count -= 1
                    else:
                        break
            return count
        except Exception as e:
            logger.error(f"Consecutive-days calc failed for {symbol}: {e}")
            return 0
    
    async def _calculate_atr(self, symbol: str, days: int) -> Optional[float]:
        """Calculate Average True Range."""
        try:
            period = max(1, days)
            klines = await tech.fetch_klines(symbol, interval="1d", limit=max(period + 50, 120))
            if not klines or len(klines) < period + 2:
                return None
            atr = tech.calculate_atr(klines, period=period)
            return float(atr) if atr is not None else None
        except Exception as e:
            logger.error(f"ATR calc failed for {symbol}: {e}")
            return None
    
    async def _count_large_swings(self, symbol: str, days: int, threshold: float) -> int:
        """Count number of days with price swings above threshold."""
        try:
            klines = await tech.fetch_klines(symbol, interval="1d", limit=max(days + 5, 30))
            if not klines:
                return 0
            recent = klines[-days:]
            swings = 0
            for k in recent:
                o = float(k[1])
                h = float(k[2])
                l = float(k[3])
                if o <= 0:
                    continue
                pct = ((h - l) / o) * 100.0
                if pct >= threshold:
                    swings += 1
            return swings
        except Exception as e:
            logger.error(f"Swing-count failed for {symbol}: {e}")
            return 0
    
    async def _calculate_range_tightness(self, symbol: str, days: int) -> float:
        """Calculate how tight the price range is (percentage)."""
        try:
            klines = await tech.fetch_klines(symbol, interval="1d", limit=max(days + 5, 30))
            if not klines:
                return 0.0
            recent = klines[-days:]
            highs = [float(k[2]) for k in recent]
            lows = [float(k[3]) for k in recent]
            if not highs or not lows:
                return 0.0
            hi = max(highs)
            lo = min(lows)
            if lo <= 0:
                return 0.0
            return ((hi - lo) / lo) * 100.0
        except Exception as e:
            logger.error(f"Range-tightness calc failed for {symbol}: {e}")
            return 0.0

# Global orchestrator instance
orchestrator = MarketOrchestrator()
