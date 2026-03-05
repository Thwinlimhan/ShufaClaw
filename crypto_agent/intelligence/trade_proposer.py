"""
Autonomous Trade Proposal System (Level 36)

Generates complete trade setups with entry, targets, stops, position sizing,
and risk/reward calculations. Tracks outcomes to improve over time.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class SetupType(Enum):
    """Types of trade setups"""
    BREAKOUT = "breakout"
    PULLBACK = "pullback"
    REVERSAL = "reversal"
    RANGE_TRADE = "range_trade"
    MOMENTUM = "momentum"


class ProposalStatus(Enum):
    """Status of trade proposals"""
    PENDING = "pending"
    ACTIVE = "active"
    HIT_TARGET = "hit_target"
    HIT_STOP = "hit_stop"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class TradeProposal:
    """Complete trade setup proposal"""
    proposal_id: str
    symbol: str
    setup_type: SetupType
    direction: str  # "LONG" or "SHORT"
    
    # Entry
    entry_price: float
    entry_zone_low: float
    entry_zone_high: float
    
    # Targets
    target_1: float
    target_2: float
    target_3: Optional[float]
    
    # Risk management
    stop_loss: float
    position_size_usd: float
    risk_amount: float
    risk_percent: float
    
    # Reward calculations
    reward_risk_ratio: float
    expected_value: float
    win_probability: float
    
    # Context
    reasoning: str
    key_levels: Dict[str, float]
    invalidation: str
    timeframe: str
    
    # Tracking
    created_at: datetime
    expires_at: datetime
    status: ProposalStatus
    entry_filled: bool = False
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None


class TradeProposer:
    """
    Generates autonomous trade proposals based on technical analysis,
    market conditions, and risk parameters.
    """
    
    def __init__(self, db, price_service, ta_service, portfolio_value: float = 10000):
        self.db = db
        self.price_service = price_service
        self.ta_service = ta_service
        self.portfolio_value = portfolio_value
        self.default_risk_percent = 1.0  # Risk 1% per trade
        
    async def generate_proposal(
        self,
        symbol: str,
        timeframe: str = "4h",
        risk_percent: Optional[float] = None
    ) -> Optional[TradeProposal]:
        """
        Generate a complete trade proposal for a symbol.
        
        Returns None if no valid setup found.
        """
        # Get current price and TA
        price_data = await self.price_service.get_price(symbol)
        if not price_data:
            return None
            
        current_price = price_data['price']
        
        # Get technical analysis
        ta = await self.ta_service.analyze(symbol, timeframe)
        if not ta:
            return None
        
        # Identify setup type
        setup_type = self._identify_setup(ta, current_price)
        if not setup_type:
            return None
        
        # Generate proposal based on setup type
        if setup_type == SetupType.BREAKOUT:
            return await self._generate_breakout_proposal(
                symbol, current_price, ta, timeframe, risk_percent
            )
        elif setup_type == SetupType.PULLBACK:
            return await self._generate_pullback_proposal(
                symbol, current_price, ta, timeframe, risk_percent
            )
        elif setup_type == SetupType.REVERSAL:
            return await self._generate_reversal_proposal(
                symbol, current_price, ta, timeframe, risk_percent
            )
        elif setup_type == SetupType.RANGE_TRADE:
            return await self._generate_range_proposal(
                symbol, current_price, ta, timeframe, risk_percent
            )
        elif setup_type == SetupType.MOMENTUM:
            return await self._generate_momentum_proposal(
                symbol, current_price, ta, timeframe, risk_percent
            )
        
        return None
    
    def _identify_setup(self, ta: Dict, current_price: float) -> Optional[SetupType]:
        """Identify which setup type is present"""
        rsi = ta.get('rsi', 50)
        trend = ta.get('trend', 'neutral')
        support = ta.get('support', current_price * 0.95)
        resistance = ta.get('resistance', current_price * 1.05)
        volume_ratio = ta.get('volume_ratio', 1.0)
        
        # Breakout: Near resistance with volume
        if current_price > resistance * 0.98 and volume_ratio > 1.5:
            return SetupType.BREAKOUT
        
        # Pullback: Uptrend but RSI oversold
        if trend == 'up' and 30 < rsi < 40:
            return SetupType.PULLBACK
        
        # Reversal: Oversold/overbought extremes
        if rsi < 25 or rsi > 75:
            return SetupType.REVERSAL
        
        # Range: Between support and resistance
        if support < current_price < resistance:
            range_size = (resistance - support) / support
            if 0.03 < range_size < 0.15:  # 3-15% range
                return SetupType.RANGE_TRADE
        
        # Momentum: Strong trend with momentum
        if trend in ['up', 'down'] and 40 < rsi < 70:
            return SetupType.MOMENTUM
        
        return None
    
    async def _generate_breakout_proposal(
        self,
        symbol: str,
        current_price: float,
        ta: Dict,
        timeframe: str,
        risk_percent: Optional[float]
    ) -> TradeProposal:
        """Generate breakout trade proposal"""
        resistance = ta.get('resistance', current_price * 1.05)
        support = ta.get('support', current_price * 0.95)
        
        # Entry: Just above resistance
        entry_price = resistance * 1.01
        entry_zone_low = resistance * 0.995
        entry_zone_high = resistance * 1.015
        
        # Stop: Below resistance (now support)
        stop_loss = resistance * 0.97
        
        # Targets: Measured move
        move_size = resistance - support
        target_1 = entry_price + (move_size * 0.5)
        target_2 = entry_price + move_size
        target_3 = entry_price + (move_size * 1.5)
        
        # Calculate position size
        risk_pct = risk_percent or self.default_risk_percent
        risk_per_unit = entry_price - stop_loss
        risk_amount = self.portfolio_value * (risk_pct / 100)
        position_size_usd = (risk_amount / risk_per_unit) * entry_price
        
        # R:R calculation
        avg_target = (target_1 + target_2 + target_3) / 3
        reward_risk_ratio = (avg_target - entry_price) / (entry_price - stop_loss)
        
        # Win probability (breakouts: 55-60%)
        win_probability = 0.57
        expected_value = (win_probability * reward_risk_ratio) - (1 - win_probability)
        
        proposal_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return TradeProposal(
            proposal_id=proposal_id,
            symbol=symbol,
            setup_type=SetupType.BREAKOUT,
            direction="LONG",
            entry_price=entry_price,
            entry_zone_low=entry_zone_low,
            entry_zone_high=entry_zone_high,
            target_1=target_1,
            target_2=target_2,
            target_3=target_3,
            stop_loss=stop_loss,
            position_size_usd=position_size_usd,
            risk_amount=risk_amount,
            risk_percent=risk_pct,
            reward_risk_ratio=reward_risk_ratio,
            expected_value=expected_value,
            win_probability=win_probability,
            reasoning=f"Breakout above resistance at ${resistance:.2f} with volume confirmation. "
                     f"Measured move projects to ${target_2:.2f}.",
            key_levels={
                'resistance': resistance,
                'support': support,
                'entry': entry_price,
                'stop': stop_loss
            },
            invalidation=f"Price closes below ${stop_loss:.2f}",
            timeframe=timeframe,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=7),
            status=ProposalStatus.PENDING
        )
    
    async def _generate_pullback_proposal(
        self,
        symbol: str,
        current_price: float,
        ta: Dict,
        timeframe: str,
        risk_percent: Optional[float]
    ) -> TradeProposal:
        """Generate pullback trade proposal"""
        support = ta.get('support', current_price * 0.95)
        resistance = ta.get('resistance', current_price * 1.10)
        sma_50 = ta.get('sma_50', current_price * 0.98)
        
        # Entry: At support or 50 SMA
        entry_price = max(support, sma_50)
        entry_zone_low = entry_price * 0.98
        entry_zone_high = entry_price * 1.02
        
        # Stop: Below support
        stop_loss = support * 0.96
        
        # Targets: Back to resistance and beyond
        target_1 = current_price * 1.05
        target_2 = resistance
        target_3 = resistance * 1.08
        
        # Calculate position size
        risk_pct = risk_percent or self.default_risk_percent
        risk_per_unit = entry_price - stop_loss
        risk_amount = self.portfolio_value * (risk_pct / 100)
        position_size_usd = (risk_amount / risk_per_unit) * entry_price
        
        # R:R calculation
        avg_target = (target_1 + target_2 + target_3) / 3
        reward_risk_ratio = (avg_target - entry_price) / (entry_price - stop_loss)
        
        # Win probability (pullbacks in uptrend: 65-70%)
        win_probability = 0.67
        expected_value = (win_probability * reward_risk_ratio) - (1 - win_probability)
        
        proposal_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return TradeProposal(
            proposal_id=proposal_id,
            symbol=symbol,
            setup_type=SetupType.PULLBACK,
            direction="LONG",
            entry_price=entry_price,
            entry_zone_low=entry_zone_low,
            entry_zone_high=entry_zone_high,
            target_1=target_1,
            target_2=target_2,
            target_3=target_3,
            stop_loss=stop_loss,
            position_size_usd=position_size_usd,
            risk_amount=risk_amount,
            risk_percent=risk_pct,
            reward_risk_ratio=reward_risk_ratio,
            expected_value=expected_value,
            win_probability=win_probability,
            reasoning=f"Pullback to support at ${support:.2f} in uptrend. "
                     f"RSI oversold, expecting bounce to ${target_2:.2f}.",
            key_levels={
                'support': support,
                'resistance': resistance,
                'sma_50': sma_50,
                'entry': entry_price,
                'stop': stop_loss
            },
            invalidation=f"Price closes below ${stop_loss:.2f}",
            timeframe=timeframe,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=5),
            status=ProposalStatus.PENDING
        )
    
    async def _generate_reversal_proposal(
        self,
        symbol: str,
        current_price: float,
        ta: Dict,
        timeframe: str,
        risk_percent: Optional[float]
    ) -> TradeProposal:
        """Generate reversal trade proposal"""
        rsi = ta.get('rsi', 50)
        support = ta.get('support', current_price * 0.92)
        resistance = ta.get('resistance', current_price * 1.08)
        
        # Determine direction based on RSI
        if rsi < 30:
            direction = "LONG"
            entry_price = current_price * 1.01
            stop_loss = support * 0.97
            target_1 = current_price * 1.08
            target_2 = current_price * 1.15
            target_3 = resistance
        else:  # rsi > 70
            direction = "SHORT"
            entry_price = current_price * 0.99
            stop_loss = resistance * 1.03
            target_1 = current_price * 0.92
            target_2 = current_price * 0.85
            target_3 = support
        
        entry_zone_low = entry_price * 0.99
        entry_zone_high = entry_price * 1.01
        
        # Calculate position size
        risk_pct = risk_percent or self.default_risk_percent
        risk_per_unit = abs(entry_price - stop_loss)
        risk_amount = self.portfolio_value * (risk_pct / 100)
        position_size_usd = (risk_amount / risk_per_unit) * entry_price
        
        # R:R calculation
        avg_target = (target_1 + target_2 + target_3) / 3
        reward_risk_ratio = abs(avg_target - entry_price) / abs(entry_price - stop_loss)
        
        # Win probability (reversals: 50-55%, riskier)
        win_probability = 0.52
        expected_value = (win_probability * reward_risk_ratio) - (1 - win_probability)
        
        proposal_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return TradeProposal(
            proposal_id=proposal_id,
            symbol=symbol,
            setup_type=SetupType.REVERSAL,
            direction=direction,
            entry_price=entry_price,
            entry_zone_low=entry_zone_low,
            entry_zone_high=entry_zone_high,
            target_1=target_1,
            target_2=target_2,
            target_3=target_3,
            stop_loss=stop_loss,
            position_size_usd=position_size_usd,
            risk_amount=risk_amount,
            risk_percent=risk_pct,
            reward_risk_ratio=reward_risk_ratio,
            expected_value=expected_value,
            win_probability=win_probability,
            reasoning=f"RSI extreme at {rsi:.1f} suggests {direction} reversal. "
                     f"Targeting mean reversion to ${target_2:.2f}.",
            key_levels={
                'support': support,
                'resistance': resistance,
                'rsi': rsi,
                'entry': entry_price,
                'stop': stop_loss
            },
            invalidation=f"Price closes beyond ${stop_loss:.2f}",
            timeframe=timeframe,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=3),
            status=ProposalStatus.PENDING
        )
    
    async def _generate_range_proposal(
        self,
        symbol: str,
        current_price: float,
        ta: Dict,
        timeframe: str,
        risk_percent: Optional[float]
    ) -> TradeProposal:
        """Generate range trade proposal"""
        support = ta.get('support', current_price * 0.95)
        resistance = ta.get('resistance', current_price * 1.05)
        mid_range = (support + resistance) / 2
        
        # Determine direction based on current position in range
        if current_price < mid_range:
            # Near support, go long
            direction = "LONG"
            entry_price = support * 1.01
            stop_loss = support * 0.97
            target_1 = mid_range
            target_2 = resistance * 0.98
            target_3 = resistance
        else:
            # Near resistance, go short
            direction = "SHORT"
            entry_price = resistance * 0.99
            stop_loss = resistance * 1.03
            target_1 = mid_range
            target_2 = support * 1.02
            target_3 = support
        
        entry_zone_low = entry_price * 0.99
        entry_zone_high = entry_price * 1.01
        
        # Calculate position size
        risk_pct = risk_percent or self.default_risk_percent
        risk_per_unit = abs(entry_price - stop_loss)
        risk_amount = self.portfolio_value * (risk_pct / 100)
        position_size_usd = (risk_amount / risk_per_unit) * entry_price
        
        # R:R calculation
        avg_target = (target_1 + target_2 + target_3) / 3
        reward_risk_ratio = abs(avg_target - entry_price) / abs(entry_price - stop_loss)
        
        # Win probability (range trades: 60-65%)
        win_probability = 0.62
        expected_value = (win_probability * reward_risk_ratio) - (1 - win_probability)
        
        proposal_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return TradeProposal(
            proposal_id=proposal_id,
            symbol=symbol,
            setup_type=SetupType.RANGE_TRADE,
            direction=direction,
            entry_price=entry_price,
            entry_zone_low=entry_zone_low,
            entry_zone_high=entry_zone_high,
            target_1=target_1,
            target_2=target_2,
            target_3=target_3,
            stop_loss=stop_loss,
            position_size_usd=position_size_usd,
            risk_amount=risk_amount,
            risk_percent=risk_pct,
            reward_risk_ratio=reward_risk_ratio,
            expected_value=expected_value,
            win_probability=win_probability,
            reasoning=f"Range-bound between ${support:.2f} and ${resistance:.2f}. "
                     f"{direction} from edge to opposite side.",
            key_levels={
                'support': support,
                'resistance': resistance,
                'mid_range': mid_range,
                'entry': entry_price,
                'stop': stop_loss
            },
            invalidation=f"Price breaks range beyond ${stop_loss:.2f}",
            timeframe=timeframe,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=5),
            status=ProposalStatus.PENDING
        )
    
    async def _generate_momentum_proposal(
        self,
        symbol: str,
        current_price: float,
        ta: Dict,
        timeframe: str,
        risk_percent: Optional[float]
    ) -> TradeProposal:
        """Generate momentum trade proposal"""
        trend = ta.get('trend', 'neutral')
        sma_20 = ta.get('sma_20', current_price * 0.98)
        sma_50 = ta.get('sma_50', current_price * 0.95)
        
        if trend == 'up':
            direction = "LONG"
            entry_price = current_price * 1.005
            stop_loss = sma_20 * 0.97
            target_1 = current_price * 1.08
            target_2 = current_price * 1.15
            target_3 = current_price * 1.25
        else:  # down
            direction = "SHORT"
            entry_price = current_price * 0.995
            stop_loss = sma_20 * 1.03
            target_1 = current_price * 0.92
            target_2 = current_price * 0.85
            target_3 = current_price * 0.75
        
        entry_zone_low = entry_price * 0.995
        entry_zone_high = entry_price * 1.005
        
        # Calculate position size
        risk_pct = risk_percent or self.default_risk_percent
        risk_per_unit = abs(entry_price - stop_loss)
        risk_amount = self.portfolio_value * (risk_pct / 100)
        position_size_usd = (risk_amount / risk_per_unit) * entry_price
        
        # R:R calculation
        avg_target = (target_1 + target_2 + target_3) / 3
        reward_risk_ratio = abs(avg_target - entry_price) / abs(entry_price - stop_loss)
        
        # Win probability (momentum: 60-65%)
        win_probability = 0.63
        expected_value = (win_probability * reward_risk_ratio) - (1 - win_probability)
        
        proposal_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return TradeProposal(
            proposal_id=proposal_id,
            symbol=symbol,
            setup_type=SetupType.MOMENTUM,
            direction=direction,
            entry_price=entry_price,
            entry_zone_low=entry_zone_low,
            entry_zone_high=entry_zone_high,
            target_1=target_1,
            target_2=target_2,
            target_3=target_3,
            stop_loss=stop_loss,
            position_size_usd=position_size_usd,
            risk_amount=risk_amount,
            risk_percent=risk_pct,
            reward_risk_ratio=reward_risk_ratio,
            expected_value=expected_value,
            win_probability=win_probability,
            reasoning=f"Strong {trend}trend with momentum. Riding the trend to ${target_2:.2f}.",
            key_levels={
                'sma_20': sma_20,
                'sma_50': sma_50,
                'entry': entry_price,
                'stop': stop_loss
            },
            invalidation=f"Trend breaks, price closes beyond ${stop_loss:.2f}",
            timeframe=timeframe,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=10),
            status=ProposalStatus.PENDING
        )
    
    async def save_proposal(self, proposal: TradeProposal):
        """Save proposal to database"""
        await self.db.execute("""
            INSERT INTO trade_proposals (
                proposal_id, symbol, setup_type, direction,
                entry_price, entry_zone_low, entry_zone_high,
                target_1, target_2, target_3, stop_loss,
                position_size_usd, risk_amount, risk_percent,
                reward_risk_ratio, expected_value, win_probability,
                reasoning, invalidation, timeframe,
                created_at, expires_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            proposal.proposal_id, proposal.symbol, proposal.setup_type.value,
            proposal.direction, proposal.entry_price, proposal.entry_zone_low,
            proposal.entry_zone_high, proposal.target_1, proposal.target_2,
            proposal.target_3, proposal.stop_loss, proposal.position_size_usd,
            proposal.risk_amount, proposal.risk_percent, proposal.reward_risk_ratio,
            proposal.expected_value, proposal.win_probability, proposal.reasoning,
            proposal.invalidation, proposal.timeframe, proposal.created_at.isoformat(),
            proposal.expires_at.isoformat(), proposal.status.value
        ))
    
    async def get_active_proposals(self) -> List[TradeProposal]:
        """Get all active proposals"""
        rows = await self.db.fetch_all("""
            SELECT * FROM trade_proposals
            WHERE status IN ('pending', 'active')
            AND expires_at > ?
            ORDER BY created_at DESC
        """, (datetime.now().isoformat(),))
        
        return [self._row_to_proposal(row) for row in rows]
    
    async def update_proposal_status(
        self,
        proposal_id: str,
        status: ProposalStatus,
        exit_price: Optional[float] = None,
        pnl: Optional[float] = None,
        pnl_percent: Optional[float] = None
    ):
        """Update proposal status and outcome"""
        await self.db.execute("""
            UPDATE trade_proposals
            SET status = ?, exit_price = ?, pnl = ?, pnl_percent = ?
            WHERE proposal_id = ?
        """, (status.value, exit_price, pnl, pnl_percent, proposal_id))
    
    def _row_to_proposal(self, row: Dict) -> TradeProposal:
        """Convert database row to TradeProposal"""
        return TradeProposal(
            proposal_id=row['proposal_id'],
            symbol=row['symbol'],
            setup_type=SetupType(row['setup_type']),
            direction=row['direction'],
            entry_price=row['entry_price'],
            entry_zone_low=row['entry_zone_low'],
            entry_zone_high=row['entry_zone_high'],
            target_1=row['target_1'],
            target_2=row['target_2'],
            target_3=row.get('target_3'),
            stop_loss=row['stop_loss'],
            position_size_usd=row['position_size_usd'],
            risk_amount=row['risk_amount'],
            risk_percent=row['risk_percent'],
            reward_risk_ratio=row['reward_risk_ratio'],
            expected_value=row['expected_value'],
            win_probability=row['win_probability'],
            reasoning=row['reasoning'],
            key_levels={},  # Reconstruct if needed
            invalidation=row['invalidation'],
            timeframe=row['timeframe'],
            created_at=datetime.fromisoformat(row['created_at']),
            expires_at=datetime.fromisoformat(row['expires_at']),
            status=ProposalStatus(row['status']),
            entry_filled=row.get('entry_filled', False),
            exit_price=row.get('exit_price'),
            pnl=row.get('pnl'),
            pnl_percent=row.get('pnl_percent')
        )
    
    async def get_proposal_stats(self) -> Dict:
        """Get statistics on proposal performance"""
        rows = await self.db.fetch_all("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'hit_target' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN status = 'hit_stop' THEN 1 ELSE 0 END) as losses,
                AVG(CASE WHEN pnl IS NOT NULL THEN pnl END) as avg_pnl,
                AVG(CASE WHEN pnl_percent IS NOT NULL THEN pnl_percent END) as avg_pnl_pct,
                SUM(CASE WHEN pnl IS NOT NULL THEN pnl ELSE 0 END) as total_pnl
            FROM trade_proposals
            WHERE status IN ('hit_target', 'hit_stop')
        """)
        
        if not rows or not rows[0]['total']:
            return {
                'total': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'avg_pnl': 0,
                'avg_pnl_pct': 0,
                'total_pnl': 0
            }
        
        row = rows[0]
        total = row['total']
        wins = row['wins']
        
        return {
            'total': total,
            'wins': wins,
            'losses': row['losses'],
            'win_rate': (wins / total * 100) if total > 0 else 0,
            'avg_pnl': row['avg_pnl'] or 0,
            'avg_pnl_pct': row['avg_pnl_pct'] or 0,
            'total_pnl': row['total_pnl'] or 0
        }
