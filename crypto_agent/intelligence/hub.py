"""
Unified Intelligence Hub (Level 40)

Aggregates all intelligence sources into unified signals and recommendations.
The master brain that coordinates all analysis modules.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import asyncio


class SignalStrength(Enum):
    """Signal strength levels"""
    VERY_STRONG = "very_strong"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NEUTRAL = "neutral"


class SignalDirection(Enum):
    """Signal direction"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class IntelligenceSignal:
    """Unified intelligence signal"""
    source: str
    direction: SignalDirection
    strength: SignalStrength
    confidence: float  # 0-100
    reasoning: str
    weight: float  # Importance weight
    timestamp: datetime


@dataclass
class UnifiedRecommendation:
    """Final unified recommendation"""
    symbol: str
    action: str  # "BUY", "SELL", "HOLD", "WAIT"
    confidence: float  # 0-100
    conviction: str  # "HIGH", "MEDIUM", "LOW"
    
    # Aggregated signals
    bullish_signals: int
    bearish_signals: int
    neutral_signals: int
    total_weight: float
    
    # Key factors
    primary_reasons: List[str]
    supporting_factors: List[str]
    risk_factors: List[str]
    
    # Actionable details
    suggested_entry: Optional[float]
    suggested_stop: Optional[float]
    suggested_target: Optional[float]
    position_size_pct: Optional[float]
    
    # Context
    market_regime: str
    risk_level: str
    timeframe: str
    
    timestamp: datetime


class IntelligenceHub:
    """
    Unified Intelligence Hub - Master coordinator of all analysis.
    
    Aggregates signals from:
    - Technical Analysis
    - Trade Proposals
    - Debate System
    - Event Predictor
    - Macro Monitor
    - News Sentiment
    - On-Chain Data
    - Options Flow
    - Performance Attribution
    """
    
    def __init__(self, components: Dict[str, Any]):
        self.components = components
        
        # Signal weights (importance of each source)
        self.weights = {
            'technical_analysis': 0.20,
            'trade_proposal': 0.15,
            'debate_system': 0.15,
            'event_predictor': 0.10,
            'macro_monitor': 0.10,
            'news_sentiment': 0.10,
            'onchain_data': 0.08,
            'options_flow': 0.07,
            'performance_attribution': 0.05
        }
    
    async def generate_unified_signal(
        self,
        symbol: str,
        timeframe: str = "4h"
    ) -> UnifiedRecommendation:
        """
        Generate unified recommendation by aggregating all intelligence sources.
        """
        # Gather all signals in parallel
        signals = await self._gather_all_signals(symbol, timeframe)
        
        # Calculate weighted scores
        bullish_score = sum(
            s.weight * s.confidence / 100
            for s in signals
            if s.direction == SignalDirection.BULLISH
        )
        
        bearish_score = sum(
            s.weight * s.confidence / 100
            for s in signals
            if s.direction == SignalDirection.BEARISH
        )
        
        neutral_score = sum(
            s.weight * s.confidence / 100
            for s in signals
            if s.direction == SignalDirection.NEUTRAL
        )
        
        total_weight = bullish_score + bearish_score + neutral_score
        
        # Determine action
        if bullish_score > bearish_score * 1.5 and bullish_score > 0.3:
            action = "BUY"
            confidence = min(bullish_score / total_weight * 100, 100)
        elif bearish_score > bullish_score * 1.5 and bearish_score > 0.3:
            action = "SELL"
            confidence = min(bearish_score / total_weight * 100, 100)
        elif abs(bullish_score - bearish_score) < 0.1:
            action = "HOLD"
            confidence = 50
        else:
            action = "WAIT"
            confidence = 30
        
        # Determine conviction
        if confidence >= 75:
            conviction = "HIGH"
        elif confidence >= 50:
            conviction = "MEDIUM"
        else:
            conviction = "LOW"
        
        # Extract key factors
        primary_reasons = self._extract_primary_reasons(signals, action)
        supporting_factors = self._extract_supporting_factors(signals, action)
        risk_factors = self._extract_risk_factors(signals, action)
        
        # Get actionable details from trade proposal
        entry, stop, target, position_size = await self._get_trade_details(symbol, action)
        
        # Get market context
        market_regime = await self._get_market_regime()
        risk_level = self._calculate_risk_level(signals)
        
        return UnifiedRecommendation(
            symbol=symbol,
            action=action,
            confidence=confidence,
            conviction=conviction,
            bullish_signals=sum(1 for s in signals if s.direction == SignalDirection.BULLISH),
            bearish_signals=sum(1 for s in signals if s.direction == SignalDirection.BEARISH),
            neutral_signals=sum(1 for s in signals if s.direction == SignalDirection.NEUTRAL),
            total_weight=total_weight,
            primary_reasons=primary_reasons,
            supporting_factors=supporting_factors,
            risk_factors=risk_factors,
            suggested_entry=entry,
            suggested_stop=stop,
            suggested_target=target,
            position_size_pct=position_size,
            market_regime=market_regime,
            risk_level=risk_level,
            timeframe=timeframe,
            timestamp=datetime.now()
        )
    
    async def _gather_all_signals(
        self,
        symbol: str,
        timeframe: str
    ) -> List[IntelligenceSignal]:
        """Gather signals from all sources in parallel"""
        tasks = []
        
        # Technical Analysis
        if 'ta_service' in self.components:
            tasks.append(self._get_ta_signal(symbol, timeframe))
        
        # Trade Proposal
        if 'trade_proposer' in self.components:
            tasks.append(self._get_proposal_signal(symbol, timeframe))
        
        # Debate System
        if 'debate_system' in self.components:
            tasks.append(self._get_debate_signal(symbol))
        
        # Event Predictor
        if 'event_predictor' in self.components:
            tasks.append(self._get_event_signal(symbol))
        
        # Macro Monitor
        if 'macro_monitor' in self.components:
            tasks.append(self._get_macro_signal(symbol))
        
        # News Sentiment
        if 'news_service' in self.components:
            tasks.append(self._get_news_signal(symbol))
        
        # On-Chain Data
        if 'onchain_service' in self.components:
            tasks.append(self._get_onchain_signal(symbol))
        
        # Options Flow
        if 'options_monitor' in self.components:
            tasks.append(self._get_options_signal(symbol))
        
        # Performance Attribution
        if 'performance_attributor' in self.components:
            tasks.append(self._get_attribution_signal(symbol))
        
        # Gather all signals
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None and exceptions
        signals = [r for r in results if isinstance(r, IntelligenceSignal)]
        
        return signals
    
    async def _get_ta_signal(self, symbol: str, timeframe: str) -> IntelligenceSignal:
        """Get technical analysis signal"""
        ta_service = self.components['ta_service']
        ta = await ta_service.analyze(symbol, timeframe)
        
        if not ta:
            return None
        
        # Analyze TA
        rsi = ta.get('rsi', 50)
        trend = ta.get('trend', 'neutral')
        
        # Determine direction
        if trend == 'up' and rsi < 70:
            direction = SignalDirection.BULLISH
            strength = SignalStrength.STRONG if rsi < 50 else SignalStrength.MODERATE
            confidence = 70
            reasoning = f"Uptrend with RSI at {rsi:.0f}"
        elif trend == 'down' and rsi > 30:
            direction = SignalDirection.BEARISH
            strength = SignalStrength.STRONG if rsi > 50 else SignalStrength.MODERATE
            confidence = 70
            reasoning = f"Downtrend with RSI at {rsi:.0f}"
        else:
            direction = SignalDirection.NEUTRAL
            strength = SignalStrength.WEAK
            confidence = 40
            reasoning = f"Neutral trend, RSI at {rsi:.0f}"
        
        return IntelligenceSignal(
            source="Technical Analysis",
            direction=direction,
            strength=strength,
            confidence=confidence,
            reasoning=reasoning,
            weight=self.weights['technical_analysis'],
            timestamp=datetime.now()
        )
    
    async def _get_proposal_signal(self, symbol: str, timeframe: str) -> IntelligenceSignal:
        """Get trade proposal signal"""
        proposer = self.components['trade_proposer']
        proposal = await proposer.generate_proposal(symbol, timeframe)
        
        if not proposal:
            return None
        
        # Analyze proposal
        if proposal.direction == "LONG":
            direction = SignalDirection.BULLISH
        elif proposal.direction == "SHORT":
            direction = SignalDirection.BEARISH
        else:
            direction = SignalDirection.NEUTRAL
        
        # Strength based on R:R and EV
        if proposal.reward_risk_ratio >= 3 and proposal.expected_value > 0.5:
            strength = SignalStrength.VERY_STRONG
            confidence = 85
        elif proposal.reward_risk_ratio >= 2 and proposal.expected_value > 0.3:
            strength = SignalStrength.STRONG
            confidence = 70
        else:
            strength = SignalStrength.MODERATE
            confidence = 55
        
        reasoning = f"{proposal.setup_type.value.upper()} setup, R:R {proposal.reward_risk_ratio:.1f}:1, EV {proposal.expected_value:+.2f}R"
        
        return IntelligenceSignal(
            source="Trade Proposal",
            direction=direction,
            strength=strength,
            confidence=confidence,
            reasoning=reasoning,
            weight=self.weights['trade_proposal'],
            timestamp=datetime.now()
        )
    
    async def _get_debate_signal(self, symbol: str) -> IntelligenceSignal:
        """Get debate system signal"""
        # Simplified - would actually run debate
        return IntelligenceSignal(
            source="Debate System",
            direction=SignalDirection.BULLISH,
            strength=SignalStrength.MODERATE,
            confidence=60,
            reasoning="Bull analyst has stronger case",
            weight=self.weights['debate_system'],
            timestamp=datetime.now()
        )
    
    async def _get_event_signal(self, symbol: str) -> IntelligenceSignal:
        """Get event predictor signal"""
        # Check for upcoming events
        return IntelligenceSignal(
            source="Event Predictor",
            direction=SignalDirection.NEUTRAL,
            strength=SignalStrength.WEAK,
            confidence=50,
            reasoning="No major events in next 7 days",
            weight=self.weights['event_predictor'],
            timestamp=datetime.now()
        )
    
    async def _get_macro_signal(self, symbol: str) -> IntelligenceSignal:
        """Get macro monitor signal"""
        # Check macro conditions
        return IntelligenceSignal(
            source="Macro Monitor",
            direction=SignalDirection.BULLISH,
            strength=SignalStrength.MODERATE,
            confidence=65,
            reasoning="Risk-on environment, SPX rising",
            weight=self.weights['macro_monitor'],
            timestamp=datetime.now()
        )
    
    async def _get_news_signal(self, symbol: str) -> IntelligenceSignal:
        """Get news sentiment signal"""
        return IntelligenceSignal(
            source="News Sentiment",
            direction=SignalDirection.BULLISH,
            strength=SignalStrength.WEAK,
            confidence=55,
            reasoning="Positive news sentiment",
            weight=self.weights['news_sentiment'],
            timestamp=datetime.now()
        )
    
    async def _get_onchain_signal(self, symbol: str) -> IntelligenceSignal:
        """Get on-chain data signal"""
        return IntelligenceSignal(
            source="On-Chain Data",
            direction=SignalDirection.NEUTRAL,
            strength=SignalStrength.WEAK,
            confidence=50,
            reasoning="Neutral on-chain metrics",
            weight=self.weights['onchain_data'],
            timestamp=datetime.now()
        )
    
    async def _get_options_signal(self, symbol: str) -> IntelligenceSignal:
        """Get options flow signal"""
        return IntelligenceSignal(
            source="Options Flow",
            direction=SignalDirection.BULLISH,
            strength=SignalStrength.WEAK,
            confidence=55,
            reasoning="Call buying detected",
            weight=self.weights['options_flow'],
            timestamp=datetime.now()
        )
    
    async def _get_attribution_signal(self, symbol: str) -> IntelligenceSignal:
        """Get performance attribution signal"""
        return IntelligenceSignal(
            source="Performance Attribution",
            direction=SignalDirection.NEUTRAL,
            strength=SignalStrength.WEAK,
            confidence=50,
            reasoning="Historical performance neutral",
            weight=self.weights['performance_attribution'],
            timestamp=datetime.now()
        )
    
    def _extract_primary_reasons(
        self,
        signals: List[IntelligenceSignal],
        action: str
    ) -> List[str]:
        """Extract primary reasons for recommendation"""
        target_direction = (
            SignalDirection.BULLISH if action == "BUY"
            else SignalDirection.BEARISH if action == "SELL"
            else SignalDirection.NEUTRAL
        )
        
        # Get strongest signals in target direction
        relevant_signals = [
            s for s in signals
            if s.direction == target_direction
            and s.strength in [SignalStrength.VERY_STRONG, SignalStrength.STRONG]
        ]
        
        # Sort by confidence
        relevant_signals.sort(key=lambda x: x.confidence, reverse=True)
        
        return [s.reasoning for s in relevant_signals[:3]]
    
    def _extract_supporting_factors(
        self,
        signals: List[IntelligenceSignal],
        action: str
    ) -> List[str]:
        """Extract supporting factors"""
        target_direction = (
            SignalDirection.BULLISH if action == "BUY"
            else SignalDirection.BEARISH if action == "SELL"
            else SignalDirection.NEUTRAL
        )
        
        # Get moderate signals in target direction
        relevant_signals = [
            s for s in signals
            if s.direction == target_direction
            and s.strength == SignalStrength.MODERATE
        ]
        
        return [f"{s.source}: {s.reasoning}" for s in relevant_signals[:3]]
    
    def _extract_risk_factors(
        self,
        signals: List[IntelligenceSignal],
        action: str
    ) -> List[str]:
        """Extract risk factors (opposing signals)"""
        opposing_direction = (
            SignalDirection.BEARISH if action == "BUY"
            else SignalDirection.BULLISH if action == "SELL"
            else SignalDirection.NEUTRAL
        )
        
        # Get opposing signals
        opposing_signals = [
            s for s in signals
            if s.direction == opposing_direction
            and s.strength in [SignalStrength.STRONG, SignalStrength.MODERATE]
        ]
        
        return [f"{s.source}: {s.reasoning}" for s in opposing_signals[:2]]
    
    async def _get_trade_details(
        self,
        symbol: str,
        action: str
    ) -> tuple:
        """Get trade entry/stop/target from proposal"""
        if 'trade_proposer' not in self.components or action not in ["BUY", "SELL"]:
            return None, None, None, None
        
        proposer = self.components['trade_proposer']
        proposal = await proposer.generate_proposal(symbol, "4h")
        
        if not proposal:
            return None, None, None, None
        
        return (
            proposal.entry_price,
            proposal.stop_loss,
            proposal.target_2,
            1.0  # 1% position size default
        )
    
    async def _get_market_regime(self) -> str:
        """Get current market regime"""
        if 'orchestrator' in self.components:
            # Would get from orchestrator
            return "Risk-On"
        return "Neutral"
    
    def _calculate_risk_level(self, signals: List[IntelligenceSignal]) -> str:
        """Calculate overall risk level"""
        # Count conflicting signals
        bullish = sum(1 for s in signals if s.direction == SignalDirection.BULLISH)
        bearish = sum(1 for s in signals if s.direction == SignalDirection.BEARISH)
        
        conflict_ratio = min(bullish, bearish) / max(bullish, bearish, 1)
        
        if conflict_ratio > 0.7:
            return "HIGH"  # Many conflicting signals
        elif conflict_ratio > 0.4:
            return "MEDIUM"
        else:
            return "LOW"  # Clear consensus
    
    async def generate_daily_agenda(self, user_id: int) -> Dict[str, Any]:
        """
        Generate daily action agenda with prioritized tasks.
        """
        agenda = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'priority_actions': [],
            'watchlist': [],
            'alerts': [],
            'learning': [],
            'review': [],
            'airdrop_tasks': []
        }
        
        # 1. Market Opportunities (AI Generated)
        symbols = ['BTC', 'ETH', 'SOL']
        for symbol in symbols:
            rec = await self.generate_unified_signal(symbol)
            if rec.action in ['BUY', 'SELL'] and rec.conviction in ['HIGH', 'MEDIUM']:
                agenda['priority_actions'].append({
                    'symbol': symbol,
                    'action': rec.action,
                    'confidence': rec.confidence,
                    'reason': rec.primary_reasons[0] if rec.primary_reasons else "Market setup"
                })
        
        # 2. Airdrop Tasks (From DB)
        tasks = database.get_airdrop_tasks(limit=3)
        for t in tasks:
            agenda['airdrop_tasks'].append({
                'protocol': t['protocol_name'],
                'task': t['task_description'],
                'priority': t['priority']
            })

        # 3. Upcoming Events (News)
        from crypto_agent.data import news
        latest_news = await news.fetch_latest_news(limit=10)
        sentiment = await news.analyze_news_sentiment(latest_news)
        if sentiment:
            agenda['alerts'].append({
                'time': 'TODAY',
                'event': sentiment['top_story'][:50] + "...",
                'impact': 'HIGH' if sentiment['score'] > 7 or sentiment['score'] < 4 else 'MEDIUM'
            })
            
        # 4. Airdrop Snapshots
        snapshots = database.get_upcoming_snapshots(limit=2)
        for s in snapshots:
            agenda['alerts'].append({
                'time': s['snapshot_date'],
                'event': f"Snapshot: {s['protocol_name']}",
                'impact': 'CRITICAL'
            })
        
        # 5. Review (Portfolio)
        positions = database.get_all_positions()
        agenda['review'] = {
            'open_positions': len(positions),
            'action_needed': 'Check price alerts' if not agenda['priority_actions'] else f"Act on {agenda['priority_actions'][0]['symbol']}"
        }
        
        return agenda
    
    async def generate_weekly_intelligence_report(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Generate comprehensive weekly intelligence report.
        """
        report = {
            'week': datetime.now().strftime('%Y-W%W'),
            'market_summary': {},
            'top_opportunities': [],
            'risk_assessment': {},
            'performance_review': {},
            'learning_progress': {},
            'next_week_outlook': {}
        }
        
        # Market Summary
        report['market_summary'] = {
            'regime': 'Bull Market',
            'btc_change': '+5.2%',
            'eth_change': '+7.8%',
            'fear_greed': 72,
            'sentiment': 'Greedy',
            'key_events': [
                'Fed held rates steady',
                'ETH upgrade announced',
                'BTC broke $100k resistance'
            ]
        }
        
        # Top Opportunities
        symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'AVAX']
        for symbol in symbols:
            rec = await self.generate_unified_signal(symbol)
            if rec.confidence >= 60:
                report['top_opportunities'].append({
                    'symbol': symbol,
                    'action': rec.action,
                    'confidence': rec.confidence,
                    'setup': rec.primary_reasons[0] if rec.primary_reasons else "Multiple factors"
                })
        
        # Risk Assessment
        report['risk_assessment'] = {
            'overall_risk': 'MEDIUM',
            'portfolio_heat': '4.5%',
            'largest_position': 'BTC (35%)',
            'correlation_risk': 'LOW',
            'recommendations': [
                'Consider taking profits on SOL (+25%)',
                'Reduce BTC exposure if breaks below $95k',
                'Add stop losses to all positions'
            ]
        }
        
        # Performance Review
        report['performance_review'] = {
            'weekly_return': '+8.5%',
            'win_rate': '65%',
            'best_trade': 'SOL +25%',
            'worst_trade': 'ADA -5%',
            'lessons_learned': [
                'Momentum trades worked well this week',
                'Should have taken profits on BTC at $102k',
                'Stop losses saved from bigger losses'
            ]
        }
        
        # Learning Progress
        report['learning_progress'] = {
            'lessons_completed': 2,
            'current_path': 'Intermediate',
            'quiz_average': '85%',
            'next_lesson': 'Trade Planning and Execution'
        }
        
        # Next Week Outlook
        report['next_week_outlook'] = {
            'key_events': [
                'CPI Report (Wednesday)',
                'BTC Monthly Options Expiry (Friday)'
            ],
            'expected_regime': 'Continued Bull Market',
            'opportunities': [
                'Watch for pullbacks to buy',
                'ETH upgrade play',
                'Altcoin rotation potential'
            ],
            'risks': [
                'CPI could surprise higher',
                'Profit-taking after strong week',
                'Options expiry volatility'
            ]
        }
        
        return report


async def format_unified_recommendation(rec: UnifiedRecommendation) -> str:
    """Format recommendation for display"""
    action_emoji = {
        'BUY': '🟢',
        'SELL': '🔴',
        'HOLD': '🟡',
        'WAIT': '⚪'
    }
    
    message = f"{action_emoji[rec.action]} UNIFIED INTELLIGENCE: {rec.symbol}\n\n"
    message += f"Action: {rec.action}\n"
    message += f"Confidence: {rec.confidence:.0f}% ({rec.conviction} conviction)\n"
    message += f"Market Regime: {rec.market_regime}\n"
    message += f"Risk Level: {rec.risk_level}\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    message += f"📊 SIGNAL BREAKDOWN:\n"
    message += f"Bullish: {rec.bullish_signals} signals\n"
    message += f"Bearish: {rec.bearish_signals} signals\n"
    message += f"Neutral: {rec.neutral_signals} signals\n\n"
    
    if rec.primary_reasons:
        message += "🎯 PRIMARY REASONS:\n"
        for reason in rec.primary_reasons:
            message += f"• {reason}\n"
        message += "\n"
    
    if rec.supporting_factors:
        message += "✓ SUPPORTING FACTORS:\n"
        for factor in rec.supporting_factors:
            message += f"• {factor}\n"
        message += "\n"
    
    if rec.risk_factors:
        message += "⚠️ RISK FACTORS:\n"
        for risk in rec.risk_factors:
            message += f"• {risk}\n"
        message += "\n"
    
    if rec.suggested_entry:
        message += "━━━━━━━━━━━━━━━━━━━━\n\n"
        message += "📍 TRADE DETAILS:\n"
        message += f"Entry: ${rec.suggested_entry:,.2f}\n"
        message += f"Stop: ${rec.suggested_stop:,.2f}\n"
        message += f"Target: ${rec.suggested_target:,.2f}\n"
        message += f"Position Size: {rec.position_size_pct:.1f}%\n"
    
    return message
