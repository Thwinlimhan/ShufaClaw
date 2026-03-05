"""
Macro Correlation Engine - Level 32

Tracks correlations between crypto and traditional markets:
- S&P 500 (SPX) - Risk appetite indicator
- Gold (GLD) - Safe haven / inflation hedge
- US Dollar Index (DXY) - Inverse correlation typically
- VIX - Fear gauge
- 10Y Treasury Yield - Risk-free rate

Uses correlations to predict crypto moves based on macro conditions.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import aiohttp
from dataclasses import dataclass
import statistics

logger = logging.getLogger(__name__)


@dataclass
class MacroData:
    """Traditional market data point"""
    symbol: str
    price: float
    change_1d: float
    change_7d: float
    change_30d: float
    timestamp: datetime


@dataclass
class CorrelationData:
    """Correlation between crypto and macro asset"""
    crypto_symbol: str
    macro_symbol: str
    correlation_30d: float
    correlation_90d: float
    strength: str  # strong, moderate, weak
    direction: str  # positive, negative, neutral
    confidence: float


class MacroMonitor:
    """Monitors macro markets and their correlation with crypto"""
    
    def __init__(self, db, price_service):
        self.db = db
        self.price = price_service
        
        # Macro symbols to track
        self.macro_symbols = {
            'SPX': 'S&P 500',
            'GLD': 'Gold',
            'DXY': 'US Dollar Index',
            'VIX': 'Volatility Index',
            'TNX': '10Y Treasury Yield'
        }
        
        # Known correlation patterns
        self.typical_correlations = {
            'BTC': {
                'SPX': {'correlation': 0.65, 'note': 'Risk-on asset, follows equities'},
                'GLD': {'correlation': 0.35, 'note': 'Partial inflation hedge'},
                'DXY': {'correlation': -0.55, 'note': 'Inverse to dollar strength'},
                'VIX': {'correlation': -0.45, 'note': 'Sells with fear spikes'},
                'TNX': {'correlation': -0.30, 'note': 'Competes with risk-free rate'}
            },
            'ETH': {
                'SPX': {'correlation': 0.70, 'note': 'Higher beta to risk-on'},
                'GLD': {'correlation': 0.25, 'note': 'Weaker inflation hedge'},
                'DXY': {'correlation': -0.60, 'note': 'Strong inverse to dollar'},
                'VIX': {'correlation': -0.50, 'note': 'Risk-off sensitive'},
                'TNX': {'correlation': -0.35, 'note': 'Rate sensitive'}
            }
        }
        
        # Macro regime definitions
        self.regimes = {
            'risk_on': {
                'conditions': 'SPX rising, VIX <20, DXY neutral/falling',
                'crypto_impact': 'Bullish - crypto rallies with risk assets',
                'confidence': 0.75
            },
            'risk_off': {
                'conditions': 'SPX falling, VIX >30, DXY rising',
                'crypto_impact': 'Bearish - crypto sells with equities',
                'confidence': 0.78
            },
            'liquidity_expansion': {
                'conditions': 'Fed balance sheet growing, yields falling',
                'crypto_impact': 'Very Bullish - historically strong for BTC',
                'confidence': 0.82
            },
            'dollar_weakness': {
                'conditions': 'DXY below 50-week MA and falling',
                'crypto_impact': 'Bullish - BTC outperforms in weak dollar',
                'confidence': 0.70
            },
            'dollar_strength': {
                'conditions': 'DXY above 50-week MA and rising',
                'crypto_impact': 'Bearish - headwind for crypto',
                'confidence': 0.68
            },
            'high_volatility': {
                'conditions': 'VIX >30, elevated market stress',
                'crypto_impact': 'Bearish - risk-off environment',
                'confidence': 0.72
            }
        }

    async def fetch_macro_data(self) -> Dict[str, MacroData]:
        """
        Fetch current traditional market data
        
        Returns:
            Dict of symbol -> MacroData
        """
        macro_data = {}
        
        try:
            # In production, use yfinance or similar
            # For now, simulate with realistic data
            
            # S&P 500
            macro_data['SPX'] = MacroData(
                symbol='SPX',
                price=5100.0,
                change_1d=0.8,
                change_7d=2.3,
                change_30d=5.2,
                timestamp=datetime.now()
            )
            
            # Gold
            macro_data['GLD'] = MacroData(
                symbol='GLD',
                price=2050.0,
                change_1d=0.3,
                change_7d=1.1,
                change_30d=3.5,
                timestamp=datetime.now()
            )
            
            # US Dollar Index
            macro_data['DXY'] = MacroData(
                symbol='DXY',
                price=103.5,
                change_1d=-0.2,
                change_7d=-0.8,
                change_30d=-2.1,
                timestamp=datetime.now()
            )
            
            # VIX
            macro_data['VIX'] = MacroData(
                symbol='VIX',
                price=15.2,
                change_1d=-2.5,
                change_7d=-8.3,
                change_30d=-15.2,
                timestamp=datetime.now()
            )
            
            # 10Y Yield
            macro_data['TNX'] = MacroData(
                symbol='TNX',
                price=4.25,
                change_1d=0.05,
                change_7d=0.12,
                change_30d=0.35,
                timestamp=datetime.now()
            )
            
            # Store in database
            await self._store_macro_data(macro_data)
            
            logger.info(f"Fetched macro data for {len(macro_data)} symbols")
            return macro_data
            
        except Exception as e:
            logger.error(f"Failed to fetch macro data: {e}")
            return {}

    async def calculate_correlations(
        self, 
        crypto_symbol: str, 
        lookback_days: int = 90
    ) -> List[CorrelationData]:
        """
        Calculate correlations between crypto and macro assets
        
        Args:
            crypto_symbol: Crypto to analyze (e.g., 'BTC')
            lookback_days: Days of history to use
            
        Returns:
            List of CorrelationData objects
        """
        correlations = []
        
        try:
            # Get historical crypto prices
            crypto_prices = await self._get_historical_prices(
                crypto_symbol, 
                lookback_days
            )
            
            if not crypto_prices:
                logger.warning(f"No historical data for {crypto_symbol}")
                return []
            
            # Calculate correlation with each macro asset
            for macro_symbol in self.macro_symbols.keys():
                # Get historical macro prices
                macro_prices = await self._get_historical_macro_prices(
                    macro_symbol,
                    lookback_days
                )
                
                if not macro_prices:
                    continue
                
                # Calculate 30-day and 90-day correlations
                corr_30d = self._calculate_correlation(
                    crypto_prices[-30:],
                    macro_prices[-30:]
                )
                
                corr_90d = self._calculate_correlation(
                    crypto_prices,
                    macro_prices
                )
                
                # Classify strength and direction
                strength = self._classify_strength(corr_90d)
                direction = self._classify_direction(corr_90d)
                
                # Calculate confidence based on consistency
                confidence = self._calculate_confidence(corr_30d, corr_90d)
                
                correlation = CorrelationData(
                    crypto_symbol=crypto_symbol,
                    macro_symbol=macro_symbol,
                    correlation_30d=corr_30d,
                    correlation_90d=corr_90d,
                    strength=strength,
                    direction=direction,
                    confidence=confidence
                )
                
                correlations.append(correlation)
            
            # Store in database
            await self._store_correlations(correlations)
            
            logger.info(f"Calculated {len(correlations)} correlations for {crypto_symbol}")
            return correlations
            
        except Exception as e:
            logger.error(f"Failed to calculate correlations: {e}")
            return []

    async def detect_macro_regime(self) -> Dict:
        """
        Detect current macro regime
        
        Returns:
            Dict with regime classification and crypto implications
        """
        try:
            # Fetch current macro data
            macro_data = await self.fetch_macro_data()
            
            if not macro_data:
                return {'regime': 'unknown', 'confidence': 0}
            
            # Extract key metrics
            spx = macro_data.get('SPX')
            vix = macro_data.get('VIX')
            dxy = macro_data.get('DXY')
            
            # Score each regime
            regime_scores = {}
            
            # Risk-on: SPX rising, VIX low, DXY neutral
            if spx and vix and dxy:
                risk_on_score = 0
                if spx.change_7d > 0:
                    risk_on_score += 1
                if vix.price < 20:
                    risk_on_score += 1
                if dxy.change_7d <= 0:
                    risk_on_score += 1
                regime_scores['risk_on'] = risk_on_score / 3
            
            # Risk-off: SPX falling, VIX high, DXY rising
            if spx and vix and dxy:
                risk_off_score = 0
                if spx.change_7d < 0:
                    risk_off_score += 1
                if vix.price > 30:
                    risk_off_score += 1
                if dxy.change_7d > 0:
                    risk_off_score += 1
                regime_scores['risk_off'] = risk_off_score / 3
            
            # Dollar weakness
            if dxy:
                dollar_weak_score = 0
                if dxy.change_30d < -1.5:
                    dollar_weak_score += 1
                if dxy.change_7d < 0:
                    dollar_weak_score += 0.5
                regime_scores['dollar_weakness'] = dollar_weak_score / 1.5
            
            # Dollar strength
            if dxy:
                dollar_strong_score = 0
                if dxy.change_30d > 1.5:
                    dollar_strong_score += 1
                if dxy.change_7d > 0:
                    dollar_strong_score += 0.5
                regime_scores['dollar_strength'] = dollar_strong_score / 1.5
            
            # High volatility
            if vix:
                vol_score = 0
                if vix.price > 30:
                    vol_score = 1.0
                elif vix.price > 25:
                    vol_score = 0.7
                elif vix.price > 20:
                    vol_score = 0.4
                regime_scores['high_volatility'] = vol_score
            
            # Find dominant regime
            if regime_scores:
                dominant_regime = max(regime_scores, key=regime_scores.get)
                confidence = regime_scores[dominant_regime]
                
                regime_info = self.regimes.get(dominant_regime, {})
                
                result = {
                    'regime': dominant_regime,
                    'confidence': confidence,
                    'conditions': regime_info.get('conditions', ''),
                    'crypto_impact': regime_info.get('crypto_impact', ''),
                    'base_confidence': regime_info.get('confidence', 0),
                    'all_scores': regime_scores,
                    'macro_data': {
                        'SPX': f"{spx.price:.0f} ({spx.change_7d:+.1f}% 7d)" if spx else 'N/A',
                        'VIX': f"{vix.price:.1f}" if vix else 'N/A',
                        'DXY': f"{dxy.price:.2f} ({dxy.change_7d:+.1f}% 7d)" if dxy else 'N/A'
                    }
                }
                
                # Store regime
                await self._store_regime(result)
                
                return result
            
            return {'regime': 'unknown', 'confidence': 0}
            
        except Exception as e:
            logger.error(f"Failed to detect macro regime: {e}")
            return {'regime': 'error', 'confidence': 0}

    async def analyze_dollar_cycle(self) -> Dict:
        """
        Analyze US Dollar cycle and crypto implications
        
        Returns:
            Dict with dollar analysis and crypto outlook
        """
        try:
            macro_data = await self.fetch_macro_data()
            dxy = macro_data.get('DXY')
            
            if not dxy:
                return {'status': 'unavailable'}
            
            # Get 50-week MA (approximate with 30d * 1.67)
            dxy_50w_ma = 105.0  # Simulated
            
            # Analyze position relative to MA
            vs_ma = ((dxy.price - dxy_50w_ma) / dxy_50w_ma) * 100
            
            # Determine cycle phase
            if dxy.price < dxy_50w_ma and dxy.change_30d < 0:
                phase = 'Weakening'
                crypto_outlook = 'Bullish'
                confidence = 0.70
                note = 'BTC historically outperforms when DXY falls below 50w MA'
            elif dxy.price > dxy_50w_ma and dxy.change_30d > 0:
                phase = 'Strengthening'
                crypto_outlook = 'Bearish'
                confidence = 0.68
                note = 'Strong dollar typically headwind for crypto'
            elif dxy.price < dxy_50w_ma:
                phase = 'Weak but stabilizing'
                crypto_outlook = 'Neutral to Bullish'
                confidence = 0.55
                note = 'Below MA but momentum unclear'
            else:
                phase = 'Strong but stabilizing'
                crypto_outlook = 'Neutral to Bearish'
                confidence = 0.55
                note = 'Above MA but momentum unclear'
            
            analysis = {
                'current_dxy': dxy.price,
                'dxy_50w_ma': dxy_50w_ma,
                'vs_ma': f"{vs_ma:+.1f}%",
                'change_30d': f"{dxy.change_30d:+.1f}%",
                'phase': phase,
                'crypto_outlook': crypto_outlook,
                'confidence': confidence,
                'note': note
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze dollar cycle: {e}")
            return {'status': 'error'}

    def _calculate_correlation(
        self, 
        series1: List[float], 
        series2: List[float]
    ) -> float:
        """Calculate Pearson correlation coefficient"""
        try:
            if len(series1) != len(series2) or len(series1) < 2:
                return 0.0
            
            # Calculate means
            mean1 = statistics.mean(series1)
            mean2 = statistics.mean(series2)
            
            # Calculate correlation
            numerator = sum((x - mean1) * (y - mean2) for x, y in zip(series1, series2))
            
            denom1 = sum((x - mean1) ** 2 for x in series1)
            denom2 = sum((y - mean2) ** 2 for y in series2)
            
            if denom1 == 0 or denom2 == 0:
                return 0.0
            
            correlation = numerator / (denom1 * denom2) ** 0.5
            
            return round(correlation, 3)
            
        except Exception as e:
            logger.error(f"Correlation calculation failed: {e}")
            return 0.0

    def _classify_strength(self, correlation: float) -> str:
        """Classify correlation strength"""
        abs_corr = abs(correlation)
        if abs_corr >= 0.7:
            return 'strong'
        elif abs_corr >= 0.4:
            return 'moderate'
        else:
            return 'weak'

    def _classify_direction(self, correlation: float) -> str:
        """Classify correlation direction"""
        if correlation > 0.2:
            return 'positive'
        elif correlation < -0.2:
            return 'negative'
        else:
            return 'neutral'

    def _calculate_confidence(self, corr_30d: float, corr_90d: float) -> float:
        """Calculate confidence based on consistency"""
        # If both have same sign and similar magnitude, high confidence
        if (corr_30d * corr_90d) > 0:  # Same sign
            diff = abs(corr_30d - corr_90d)
            if diff < 0.2:
                return 0.85
            elif diff < 0.4:
                return 0.70
            else:
                return 0.55
        else:
            return 0.40  # Inconsistent

    async def _get_historical_prices(
        self, 
        symbol: str, 
        days: int
    ) -> List[float]:
        """Get historical crypto prices (simulated)"""
        # In production, fetch from database or API
        # For now, generate realistic data
        base_price = 97500 if symbol == 'BTC' else 3100
        prices = []
        for i in range(days):
            # Add some realistic variation
            variation = (hash(f"{symbol}{i}") % 1000 - 500) / 10000
            price = base_price * (1 + variation)
            prices.append(price)
        return prices

    async def _get_historical_macro_prices(
        self,
        symbol: str,
        days: int
    ) -> List[float]:
        """Get historical macro prices (simulated)"""
        base_prices = {
            'SPX': 5100,
            'GLD': 2050,
            'DXY': 103.5,
            'VIX': 15.2,
            'TNX': 4.25
        }
        base = base_prices.get(symbol, 100)
        prices = []
        for i in range(days):
            variation = (hash(f"{symbol}{i}") % 1000 - 500) / 10000
            price = base * (1 + variation)
            prices.append(price)
        return prices

    async def _store_macro_data(self, macro_data: Dict[str, MacroData]):
        """Store macro data in database"""
        try:
            for symbol, data in macro_data.items():
                await self.db.execute(
                    """
                    INSERT INTO macro_data 
                    (symbol, price, change_1d, change_7d, change_30d, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (symbol, data.price, data.change_1d, data.change_7d,
                     data.change_30d, data.timestamp.isoformat())
                )
            await self.db.commit()
        except Exception as e:
            logger.error(f"Failed to store macro data: {e}")

    async def _store_correlations(self, correlations: List[CorrelationData]):
        """Store correlations in database"""
        try:
            for corr in correlations:
                await self.db.execute(
                    """
                    INSERT INTO macro_correlations
                    (crypto_symbol, macro_symbol, correlation_30d, correlation_90d,
                     strength, direction, confidence, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (corr.crypto_symbol, corr.macro_symbol, corr.correlation_30d,
                     corr.correlation_90d, corr.strength, corr.direction,
                     corr.confidence, datetime.now().isoformat())
                )
            await self.db.commit()
        except Exception as e:
            logger.error(f"Failed to store correlations: {e}")

    async def _store_regime(self, regime: Dict):
        """Store macro regime in database"""
        try:
            await self.db.execute(
                """
                INSERT INTO macro_regimes
                (regime, confidence, conditions, crypto_impact, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (regime['regime'], regime['confidence'], regime['conditions'],
                 regime['crypto_impact'], datetime.now().isoformat())
            )
            await self.db.commit()
        except Exception as e:
            logger.error(f"Failed to store regime: {e}")

    def format_macro_dashboard(self, macro_data: Dict[str, MacroData]) -> str:
        """Format macro data as dashboard message"""
        if not macro_data:
            return "📊 **MACRO DASHBOARD**\n\nData unavailable"
        
        msg = "📊 **MACRO DASHBOARD**\n\n"
        
        for symbol, data in macro_data.items():
            name = self.macro_symbols.get(symbol, symbol)
            emoji = self._get_macro_emoji(symbol, data.change_1d)
            
            msg += f"{emoji} **{name}** ({symbol})\n"
            msg += f"   Price: {data.price:.2f}\n"
            msg += f"   1D: {data.change_1d:+.2f}% | 7D: {data.change_7d:+.2f}% | 30D: {data.change_30d:+.2f}%\n\n"
        
        return msg

    def format_correlation_report(
        self, 
        correlations: List[CorrelationData]
    ) -> str:
        """Format correlation analysis"""
        if not correlations:
            return "📊 **CORRELATION ANALYSIS**\n\nNo data available"
        
        crypto = correlations[0].crypto_symbol
        msg = f"📊 **{crypto} MACRO CORRELATIONS**\n\n"
        
        for corr in correlations:
            macro_name = self.macro_symbols.get(corr.macro_symbol, corr.macro_symbol)
            
            # Emoji based on strength and direction
            if corr.strength == 'strong':
                emoji = '🔴' if corr.direction == 'positive' else '🔵'
            elif corr.strength == 'moderate':
                emoji = '🟠' if corr.direction == 'positive' else '🟣'
            else:
                emoji = '⚪'
            
            msg += f"{emoji} **{macro_name}**\n"
            msg += f"   30D: {corr.correlation_30d:+.2f} | 90D: {corr.correlation_90d:+.2f}\n"
            msg += f"   Strength: {corr.strength.title()} | Direction: {corr.direction.title()}\n"
            msg += f"   Confidence: {corr.confidence*100:.0f}%\n\n"
        
        return msg

    def format_regime_report(self, regime: Dict) -> str:
        """Format macro regime analysis"""
        if regime.get('regime') == 'unknown':
            return "🌡️ **MACRO REGIME**\n\nUnable to determine"
        
        msg = "🌡️ **MACRO REGIME ANALYSIS**\n\n"
        msg += f"**Current Regime:** {regime['regime'].replace('_', ' ').title()}\n"
        msg += f"**Confidence:** {regime['confidence']*100:.0f}%\n\n"
        
        msg += f"**Conditions:**\n{regime['conditions']}\n\n"
        msg += f"**Crypto Impact:**\n{regime['crypto_impact']}\n\n"
        
        if 'macro_data' in regime:
            msg += "**Current Macro:**\n"
            for symbol, value in regime['macro_data'].items():
                msg += f"• {symbol}: {value}\n"
        
        return msg

    def _get_macro_emoji(self, symbol: str, change: float) -> str:
        """Get emoji for macro symbol"""
        emojis = {
            'SPX': '📈' if change > 0 else '📉',
            'GLD': '🥇',
            'DXY': '💵',
            'VIX': '😱' if change > 0 else '😌',
            'TNX': '📊'
        }
        return emojis.get(symbol, '📊')
