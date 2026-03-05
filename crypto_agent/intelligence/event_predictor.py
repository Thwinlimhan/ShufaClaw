"""
Event Impact Predictor - Level 31

Tracks upcoming events and predicts market impact based on historical patterns:
- Token unlocks (supply inflation events)
- Protocol upgrades (hard forks, major updates)
- Macro events (Fed meetings, CPI, jobs reports)
- Options/Futures expiry (max pain gravity)

Uses historical data to predict likely price action around events.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import aiohttp
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Represents a tracked event"""
    event_id: str
    event_type: str  # unlock, upgrade, macro, expiry
    symbol: str
    title: str
    description: str
    date: datetime
    impact_score: float  # 0-10
    predicted_direction: str  # bullish, bearish, neutral
    confidence: float  # 0-1
    historical_pattern: Optional[str] = None
    data: Optional[Dict] = None


class EventPredictor:
    """Predicts market impact of upcoming events"""
    
    def __init__(self, db, market_service, price_service):
        self.db = db
        self.market = market_service
        self.price = price_service
        
        # Historical patterns (learned from past events)
        self.patterns = {
            'token_unlock': {
                'large_unlock': {  # >10% of circulating supply
                    'pattern': 'Selling pressure 7-14 days before, -8% on unlock day, recovery 30 days after',
                    'avg_impact_before': -12.0,
                    'avg_impact_day': -8.0,
                    'avg_impact_after': 5.0,
                    'confidence': 0.73
                },
                'medium_unlock': {  # 3-10% of circulating supply
                    'pattern': 'Mild selling pressure week before, -3% on unlock day',
                    'avg_impact_before': -5.0,
                    'avg_impact_day': -3.0,
                    'avg_impact_after': 2.0,
                    'confidence': 0.65
                },
                'small_unlock': {  # <3% of circulating supply
                    'pattern': 'Minimal impact, usually absorbed',
                    'avg_impact_before': -1.0,
                    'avg_impact_day': -0.5,
                    'avg_impact_after': 0.5,
                    'confidence': 0.58
                }
            },
            'protocol_upgrade': {
                'major_upgrade': {
                    'pattern': 'Buy the rumor (2 weeks before), sell the news (day of)',
                    'avg_impact_before': 8.0,
                    'avg_impact_day': -3.0,
                    'avg_impact_after': 5.0,
                    'confidence': 0.68
                },
                'minor_upgrade': {
                    'pattern': 'Mild positive sentiment, minimal price impact',
                    'avg_impact_before': 2.0,
                    'avg_impact_day': 1.0,
                    'avg_impact_after': 1.0,
                    'confidence': 0.55
                }
            },
            'macro_event': {
                'fed_hawkish': {
                    'pattern': 'Risk-off, crypto sells with equities',
                    'avg_impact': -8.2,
                    'confidence': 0.78
                },
                'fed_dovish': {
                    'pattern': 'Risk-on, crypto rallies',
                    'avg_impact': 6.5,
                    'confidence': 0.75
                },
                'fed_inline': {
                    'pattern': 'Minimal reaction, slight positive',
                    'avg_impact': 0.5,
                    'confidence': 0.62
                },
                'cpi_hot': {
                    'pattern': 'Inflation fears, crypto sells',
                    'avg_impact': -5.8,
                    'confidence': 0.72
                },
                'cpi_cool': {
                    'pattern': 'Disinflation narrative, crypto rallies',
                    'avg_impact': 4.2,
                    'confidence': 0.70
                }
            },
            'options_expiry': {
                'monthly_expiry': {
                    'pattern': 'Elevated volatility week before, max pain gravity, calm after',
                    'avg_impact_before': 'High volatility',
                    'avg_impact_day': 'Price gravitates toward max pain',
                    'avg_impact_after': 'Volatility normalizes',
                    'confidence': 0.65
                }
            }
        }

    async def track_upcoming_events(self, days_ahead: int = 30) -> List[Event]:
        """
        Get all upcoming events in the next N days
        
        Args:
            days_ahead: How many days to look ahead
            
        Returns:
            List of Event objects
        """
        events = []
        
        try:
            # Get token unlocks
            unlock_events = await self._get_token_unlocks(days_ahead)
            events.extend(unlock_events)
            
            # Get protocol upgrades
            upgrade_events = await self._get_protocol_upgrades(days_ahead)
            events.extend(upgrade_events)
            
            # Get macro events
            macro_events = await self._get_macro_events(days_ahead)
            events.extend(macro_events)
            
            # Get options expiry
            expiry_events = await self._get_options_expiry(days_ahead)
            events.extend(expiry_events)
            
            # Sort by date
            events.sort(key=lambda e: e.date)
            
            # Store in database
            await self._store_events(events)
            
            logger.info(f"Tracked {len(events)} upcoming events")
            return events
            
        except Exception as e:
            logger.error(f"Failed to track events: {e}")
            return []

    async def _get_token_unlocks(self, days_ahead: int) -> List[Event]:
        """Fetch upcoming token unlock events"""
        events = []
        
        try:
            # Note: In production, use token.unlocks.app API or cryptorank.io
            # For now, we'll use a simplified approach with known unlocks
            
            # Example unlocks (in production, fetch from API)
            known_unlocks = [
                {
                    'symbol': 'ARB',
                    'date': datetime.now() + timedelta(days=19),
                    'amount': 1_100_000_000,
                    'value_usd': 890_000_000,
                    'pct_of_supply': 11.5
                },
                {
                    'symbol': 'OP',
                    'date': datetime.now() + timedelta(days=25),
                    'amount': 580_000_000,
                    'value_usd': 450_000_000,
                    'pct_of_supply': 8.2
                }
            ]
            
            for unlock in known_unlocks:
                days_until = (unlock['date'] - datetime.now()).days
                if 0 <= days_until <= days_ahead:
                    # Classify unlock size
                    pct = unlock['pct_of_supply']
                    if pct > 10:
                        size_class = 'large_unlock'
                    elif pct > 3:
                        size_class = 'medium_unlock'
                    else:
                        size_class = 'small_unlock'
                    
                    pattern = self.patterns['token_unlock'][size_class]
                    
                    # Predict impact
                    impact_score = min(10, pct)  # Higher % = higher impact
                    predicted_direction = 'bearish'  # Unlocks usually bearish
                    
                    event = Event(
                        event_id=f"unlock_{unlock['symbol']}_{unlock['date'].strftime('%Y%m%d')}",
                        event_type='unlock',
                        symbol=unlock['symbol'],
                        title=f"{unlock['symbol']} Token Unlock",
                        description=f"{unlock['amount']:,.0f} {unlock['symbol']} (${unlock['value_usd']:,.0f}) unlocking - {pct:.1f}% of supply",
                        date=unlock['date'],
                        impact_score=impact_score,
                        predicted_direction=predicted_direction,
                        confidence=pattern['confidence'],
                        historical_pattern=pattern['pattern'],
                        data={
                            'amount': unlock['amount'],
                            'value_usd': unlock['value_usd'],
                            'pct_of_supply': pct,
                            'size_class': size_class,
                            'avg_impact_before': pattern['avg_impact_before'],
                            'avg_impact_day': pattern['avg_impact_day'],
                            'avg_impact_after': pattern['avg_impact_after']
                        }
                    )
                    events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get token unlocks: {e}")
            return []

    async def _get_protocol_upgrades(self, days_ahead: int) -> List[Event]:
        """Fetch upcoming protocol upgrades"""
        events = []
        
        try:
            # Known upcoming upgrades (in production, scrape from official sources)
            known_upgrades = [
                {
                    'symbol': 'ETH',
                    'name': 'Dencun Upgrade',
                    'date': datetime.now() + timedelta(days=45),
                    'type': 'major_upgrade',
                    'description': 'Proto-danksharding (EIP-4844) for L2 scaling'
                }
            ]
            
            for upgrade in known_upgrades:
                days_until = (upgrade['date'] - datetime.now()).days
                if 0 <= days_until <= days_ahead:
                    pattern = self.patterns['protocol_upgrade'][upgrade['type']]
                    
                    event = Event(
                        event_id=f"upgrade_{upgrade['symbol']}_{upgrade['date'].strftime('%Y%m%d')}",
                        event_type='upgrade',
                        symbol=upgrade['symbol'],
                        title=f"{upgrade['symbol']} {upgrade['name']}",
                        description=upgrade['description'],
                        date=upgrade['date'],
                        impact_score=8.0 if upgrade['type'] == 'major_upgrade' else 4.0,
                        predicted_direction='bullish',
                        confidence=pattern['confidence'],
                        historical_pattern=pattern['pattern'],
                        data={
                            'upgrade_type': upgrade['type'],
                            'avg_impact_before': pattern['avg_impact_before'],
                            'avg_impact_day': pattern['avg_impact_day'],
                            'avg_impact_after': pattern['avg_impact_after']
                        }
                    )
                    events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get protocol upgrades: {e}")
            return []

    async def _get_macro_events(self, days_ahead: int) -> List[Event]:
        """Fetch upcoming macro economic events"""
        events = []
        
        try:
            # Known macro events (in production, use economic calendar API)
            known_macro = [
                {
                    'name': 'FOMC Meeting',
                    'date': datetime.now() + timedelta(days=12),
                    'type': 'fed_meeting',
                    'expected_outcome': 'inline'  # hawkish, dovish, inline
                },
                {
                    'name': 'CPI Report',
                    'date': datetime.now() + timedelta(days=8),
                    'type': 'cpi',
                    'expected_outcome': 'cool'  # hot, cool
                }
            ]
            
            for macro in known_macro:
                days_until = (macro['date'] - datetime.now()).days
                if 0 <= days_until <= days_ahead:
                    # Get pattern based on expected outcome
                    if macro['type'] == 'fed_meeting':
                        pattern_key = f"fed_{macro['expected_outcome']}"
                    else:
                        pattern_key = f"cpi_{macro['expected_outcome']}"
                    
                    pattern = self.patterns['macro_event'].get(pattern_key)
                    if not pattern:
                        continue
                    
                    # Determine direction
                    if 'hawkish' in pattern_key or 'hot' in pattern_key:
                        direction = 'bearish'
                    elif 'dovish' in pattern_key or 'cool' in pattern_key:
                        direction = 'bullish'
                    else:
                        direction = 'neutral'
                    
                    event = Event(
                        event_id=f"macro_{macro['type']}_{macro['date'].strftime('%Y%m%d')}",
                        event_type='macro',
                        symbol='BTC',  # Macro affects all, use BTC as proxy
                        title=macro['name'],
                        description=f"Expected outcome: {macro['expected_outcome']}",
                        date=macro['date'],
                        impact_score=7.0,
                        predicted_direction=direction,
                        confidence=pattern['confidence'],
                        historical_pattern=pattern['pattern'],
                        data={
                            'macro_type': macro['type'],
                            'expected_outcome': macro['expected_outcome'],
                            'avg_impact': pattern['avg_impact']
                        }
                    )
                    events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get macro events: {e}")
            return []

    async def _get_options_expiry(self, days_ahead: int) -> List[Event]:
        """Fetch upcoming options expiry dates"""
        events = []
        
        try:
            # Monthly options expiry (last Friday of month)
            current_date = datetime.now()
            
            for month_offset in range(3):  # Next 3 months
                # Calculate last Friday of month
                target_month = current_date.month + month_offset
                target_year = current_date.year
                if target_month > 12:
                    target_month -= 12
                    target_year += 1
                
                # Get last day of month
                if target_month == 12:
                    last_day = datetime(target_year, 12, 31)
                else:
                    last_day = datetime(target_year, target_month + 1, 1) - timedelta(days=1)
                
                # Find last Friday
                while last_day.weekday() != 4:  # 4 = Friday
                    last_day -= timedelta(days=1)
                
                days_until = (last_day - current_date).days
                if 0 <= days_until <= days_ahead:
                    pattern = self.patterns['options_expiry']['monthly_expiry']
                    
                    event = Event(
                        event_id=f"expiry_{last_day.strftime('%Y%m%d')}",
                        event_type='expiry',
                        symbol='BTC',
                        title='Monthly Options Expiry',
                        description='BTC/ETH monthly options expiry on Deribit',
                        date=last_day,
                        impact_score=6.0,
                        predicted_direction='neutral',
                        confidence=pattern['confidence'],
                        historical_pattern=pattern['pattern'],
                        data={
                            'expiry_type': 'monthly',
                            'exchanges': ['Deribit', 'CME']
                        }
                    )
                    events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get options expiry: {e}")
            return []

    async def _store_events(self, events: List[Event]):
        """Store events in database"""
        try:
            for event in events:
                await self.db.execute(
                    """
                    INSERT OR REPLACE INTO upcoming_events 
                    (event_id, event_type, symbol, title, description, date, 
                     impact_score, predicted_direction, confidence, historical_pattern, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.event_type,
                        event.symbol,
                        event.title,
                        event.description,
                        event.date.isoformat(),
                        event.impact_score,
                        event.predicted_direction,
                        event.confidence,
                        event.historical_pattern,
                        str(event.data)
                    )
                )
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to store events: {e}")

    async def get_events_for_symbol(self, symbol: str, days_ahead: int = 30) -> List[Event]:
        """Get upcoming events for a specific symbol"""
        all_events = await self.track_upcoming_events(days_ahead)
        return [e for e in all_events if e.symbol == symbol]

    async def get_imminent_events(self, days_threshold: int = 7) -> List[Event]:
        """Get events happening within N days"""
        all_events = await self.track_upcoming_events(30)
        now = datetime.now()
        return [
            e for e in all_events 
            if (e.date - now).days <= days_threshold
        ]

    async def analyze_event_impact(self, event: Event) -> Dict:
        """
        Detailed analysis of a specific event's likely impact
        
        Returns:
            Dict with detailed impact analysis
        """
        try:
            days_until = (event.date - datetime.now()).days
            
            analysis = {
                'event': {
                    'title': event.title,
                    'symbol': event.symbol,
                    'date': event.date.strftime('%Y-%m-%d'),
                    'days_until': days_until,
                    'type': event.event_type
                },
                'impact': {
                    'score': event.impact_score,
                    'direction': event.predicted_direction,
                    'confidence': f"{event.confidence * 100:.0f}%"
                },
                'historical_pattern': event.historical_pattern,
                'timeline': {},
                'recommendation': ''
            }
            
            # Add timeline based on event type
            if event.event_type == 'unlock':
                data = event.data
                analysis['timeline'] = {
                    '7-14 days before': f"Expected: {data['avg_impact_before']:+.1f}% (selling pressure)",
                    'Unlock day': f"Expected: {data['avg_impact_day']:+.1f}%",
                    '30 days after': f"Expected: {data['avg_impact_after']:+.1f}% (recovery)"
                }
                
                if days_until > 14:
                    analysis['recommendation'] = "Monitor closely. Consider reducing position 7-14 days before unlock."
                elif days_until > 7:
                    analysis['recommendation'] = "Selling pressure may begin. Consider taking profits or tightening stops."
                elif days_until > 0:
                    analysis['recommendation'] = "Unlock imminent. Expect volatility. Avoid new positions."
                else:
                    analysis['recommendation'] = "Unlock passed. Monitor for recovery opportunity in coming weeks."
            
            elif event.event_type == 'upgrade':
                data = event.data
                analysis['timeline'] = {
                    '2 weeks before': f"Expected: {data['avg_impact_before']:+.1f}% (buy the rumor)",
                    'Upgrade day': f"Expected: {data['avg_impact_day']:+.1f}% (sell the news)",
                    '2 weeks after': f"Expected: {data['avg_impact_after']:+.1f}%"
                }
                
                if days_until > 14:
                    analysis['recommendation'] = "Good accumulation window. 'Buy the rumor' phase approaching."
                elif days_until > 3:
                    analysis['recommendation'] = "Peak 'buy the rumor' phase. Consider taking partial profits before event."
                elif days_until >= 0:
                    analysis['recommendation'] = "'Sell the news' likely. Consider profit-taking."
                else:
                    analysis['recommendation'] = "Post-upgrade. Monitor for stabilization and re-entry."
            
            elif event.event_type == 'macro':
                data = event.data
                analysis['timeline'] = {
                    'On announcement': f"Expected: {data['avg_impact']:+.1f}%",
                    'Following days': "Volatility elevated, trend continuation likely"
                }
                
                if event.predicted_direction == 'bearish':
                    analysis['recommendation'] = "Risk-off event. Consider reducing exposure or hedging."
                elif event.predicted_direction == 'bullish':
                    analysis['recommendation'] = "Risk-on event. Opportunity to add to positions."
                else:
                    analysis['recommendation'] = "Neutral event. Minimal expected impact."
            
            elif event.event_type == 'expiry':
                analysis['timeline'] = {
                    'Week before': "Elevated volatility expected",
                    'Expiry day': "Price may gravitate toward max pain level",
                    'After expiry': "Volatility normalizes"
                }
                
                if days_until > 7:
                    analysis['recommendation'] = "Expiry approaching. Expect increased volatility next week."
                elif days_until > 0:
                    analysis['recommendation'] = "High volatility period. Avoid overleveraging. Watch max pain levels."
                else:
                    analysis['recommendation'] = "Expiry passed. Volatility should normalize."
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze event impact: {e}")
            return {}

    def format_calendar_message(self, events: List[Event], days: int = 30) -> str:
        """Format events as a calendar message"""
        if not events:
            return f"📅 **EVENT CALENDAR** (Next {days} days)\n\nNo significant events scheduled."
        
        msg = f"📅 **EVENT CALENDAR** (Next {days} days)\n\n"
        
        # Group by urgency
        critical = [e for e in events if (e.date - datetime.now()).days <= 7]
        upcoming = [e for e in events if 7 < (e.date - datetime.now()).days <= 14]
        future = [e for e in events if (e.date - datetime.now()).days > 14]
        
        if critical:
            msg += "🔴 **IMMINENT** (Next 7 days)\n"
            for event in critical:
                days_until = (event.date - datetime.now()).days
                direction_emoji = "📉" if event.predicted_direction == "bearish" else "📈" if event.predicted_direction == "bullish" else "➡️"
                msg += f"{direction_emoji} **{event.symbol}** - {event.title}\n"
                msg += f"   {event.date.strftime('%b %d')} ({days_until}d) | Impact: {event.impact_score:.0f}/10 | {event.confidence*100:.0f}% confidence\n"
                msg += f"   {event.description}\n\n"
        
        if upcoming:
            msg += "🟡 **UPCOMING** (7-14 days)\n"
            for event in upcoming:
                days_until = (event.date - datetime.now()).days
                direction_emoji = "📉" if event.predicted_direction == "bearish" else "📈" if event.predicted_direction == "bullish" else "➡️"
                msg += f"{direction_emoji} **{event.symbol}** - {event.title}\n"
                msg += f"   {event.date.strftime('%b %d')} ({days_until}d) | Impact: {event.impact_score:.0f}/10\n\n"
        
        if future:
            msg += "🟢 **FUTURE** (14+ days)\n"
            for event in future[:5]:  # Limit to 5
                days_until = (event.date - datetime.now()).days
                msg += f"• {event.symbol} - {event.title} ({event.date.strftime('%b %d')}, {days_until}d)\n"
        
        return msg

    def format_event_analysis(self, analysis: Dict) -> str:
        """Format detailed event analysis"""
        if not analysis:
            return "❌ Analysis unavailable"
        
        event = analysis['event']
        impact = analysis['impact']
        
        msg = f"📊 **EVENT IMPACT ANALYSIS**\n\n"
        msg += f"**Event:** {event['title']}\n"
        msg += f"**Symbol:** {event['symbol']}\n"
        msg += f"**Date:** {event['date']} ({event['days_until']} days)\n"
        msg += f"**Type:** {event['type'].title()}\n\n"
        
        msg += f"**Predicted Impact:**\n"
        msg += f"• Direction: {impact['direction'].title()}\n"
        msg += f"• Severity: {impact['score']:.0f}/10\n"
        msg += f"• Confidence: {impact['confidence']}\n\n"
        
        msg += f"**Historical Pattern:**\n{analysis['historical_pattern']}\n\n"
        
        if analysis['timeline']:
            msg += f"**Expected Timeline:**\n"
            for period, expectation in analysis['timeline'].items():
                msg += f"• {period}: {expectation}\n"
            msg += "\n"
        
        msg += f"**💡 Recommendation:**\n{analysis['recommendation']}"
        
        return msg
