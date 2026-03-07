"""
ShufaClaw V2 — Market Regime Detector

This module takes a FeatureVector and classifies the overall market state into 
distinct regimes (Bullish, Bearish, Choppy, Breakout, etc.). 
Different regimes will eventually trigger different trading strategies.

Current Implementation: Rule-based classifier.
Future Implementation: Hidden Markov Model (HMM).
"""

from enum import Enum
import logging
from crypto_agent.intelligence.feature_engine import FeatureVector

logger = logging.getLogger(__name__)

class MarketRegime(str, Enum):
    BULL_TREND = "bull_trend"
    BEAR_TREND = "bear_trend"
    CHOP_ACCUMULATION = "chop_accumulation"
    CHOP_DISTRIBUTION = "chop_distribution"
    HIGH_VOLATILITY_EXPANSION = "high_volatility_expansion"
    UNKNOWN = "unknown"

class RegimeDetector:
    """Classifies the market into a standard Regime."""

    def __init__(self):
        self.version = "v1.0-rules"

    def detect_regime(self, features: FeatureVector) -> MarketRegime:
        """
        Rule-based regime detection.
        Uses ADX for trend strength, SMAs for direction, and Volatility for expansion.
        """
        try:
            # 1. Check for missing required data
            if any(v is None for v in [features.sma_20, features.sma_50, features.sma_200, features.adx_14, features.rsi_14]):
                return MarketRegime.UNKNOWN
            
            # Trend Strength
            is_trending = features.adx_14 > 25
            is_strong_trend = features.adx_14 > 40
            
            # Trend Direction
            price_above_fast = features.sma_20 > features.sma_50
            price_above_slow = features.sma_50 > features.sma_200
            
            is_bullish = price_above_fast and price_above_slow
            is_bearish = not price_above_fast and not price_above_slow
            
            # Volatility Expansion
            is_high_vol = False
            if features.bb_width is not None and features.realized_vol_20 is not None:
                # E.g. Bollinger width > 10% indicates expansion
                is_high_vol = features.bb_width > 0.10 
                
            # --- Classification Logic ---
            
            if is_high_vol and is_strong_trend:
                return MarketRegime.HIGH_VOLATILITY_EXPANSION
                
            if is_trending:
                if is_bullish and features.rsi_14 > 50:
                    return MarketRegime.BULL_TREND
                elif is_bearish and features.rsi_14 < 50:
                    return MarketRegime.BEAR_TREND
            
            # If not trending -> Choppy
            if features.rsi_14 > 50:
                return MarketRegime.CHOP_ACCUMULATION # Grinding up but weak trend
            else:
                return MarketRegime.CHOP_DISTRIBUTION # Grinding down but weak trend
                
        except Exception as e:
            logger.error(f"Regime detection failed: {e}")
            return MarketRegime.UNKNOWN

# --- Optional probability output (for persistence / dashboards) ---
    def detect_regime_probs(self, features: FeatureVector) -> dict[str, float]:
        """
        Returns a simple probability-like distribution over regimes.

        This is still rule-based (fast and interpretable). It converts rule signals
        into soft scores and normalizes to sum to 1.
        """
        regimes = {
            MarketRegime.BULL_TREND.value: 0.0,
            MarketRegime.BEAR_TREND.value: 0.0,
            MarketRegime.CHOP_ACCUMULATION.value: 0.0,
            MarketRegime.CHOP_DISTRIBUTION.value: 0.0,
            MarketRegime.HIGH_VOLATILITY_EXPANSION.value: 0.0,
            MarketRegime.UNKNOWN.value: 0.0,
        }

        # If required data missing, return UNKNOWN=1
        if any(
            v is None
            for v in [
                features.sma_20,
                features.sma_50,
                features.sma_200,
                features.adx_14,
                features.rsi_14,
            ]
        ):
            regimes[MarketRegime.UNKNOWN.value] = 1.0
            return regimes

        # Trend strength
        adx = float(features.adx_14 or 0.0)
        trend_strength = min(max((adx - 15.0) / 30.0, 0.0), 1.0)  # 15->0, 45->1

        # Direction
        bullish_stack = float(features.sma_20 > features.sma_50 and features.sma_50 > features.sma_200)
        bearish_stack = float(features.sma_20 < features.sma_50 and features.sma_50 < features.sma_200)

        # RSI tilt
        rsi = float(features.rsi_14 or 50.0)
        rsi_bull = min(max((rsi - 50.0) / 25.0, 0.0), 1.0)
        rsi_bear = min(max((50.0 - rsi) / 25.0, 0.0), 1.0)

        # Volatility expansion proxy
        bb_width = float(features.bb_width or 0.0)
        vol_expansion = min(max((bb_width - 0.06) / 0.10, 0.0), 1.0)  # ~6% to 16%

        regimes[MarketRegime.HIGH_VOLATILITY_EXPANSION.value] = vol_expansion * (0.4 + 0.6 * trend_strength)
        regimes[MarketRegime.BULL_TREND.value] = trend_strength * bullish_stack * (0.5 + 0.5 * rsi_bull)
        regimes[MarketRegime.BEAR_TREND.value] = trend_strength * bearish_stack * (0.5 + 0.5 * rsi_bear)

        # Choppy allocation when trend is weak
        chop_strength = 1.0 - trend_strength
        regimes[MarketRegime.CHOP_ACCUMULATION.value] = chop_strength * (0.4 + 0.6 * rsi_bull)
        regimes[MarketRegime.CHOP_DISTRIBUTION.value] = chop_strength * (0.4 + 0.6 * rsi_bear)

        total = sum(regimes.values())
        if total <= 0:
            regimes[MarketRegime.UNKNOWN.value] = 1.0
            return regimes

        return {k: (v / total) for k, v in regimes.items()}

# Global Instance
regime_detector = RegimeDetector()
