"""
ShufaClaw V2 — Feature & Intelligence Schemas

Schemas for computed features (technical indicators),
market regime detection, and signal aggregation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ─── Module 3: Feature Engineering ────────────────────────────

class FeatureVector(BaseModel):
    """
    A set of computed features for a symbol at a point in time.

    Features are derived from raw market data (candles, order book, etc.)
    and are used by strategies and ML models to make decisions.
    """
    symbol: str
    interval: str
    timestamp: datetime
    feature_version: str = Field("v1.0.0", description="Version of feature computation code")

    # Trend features
    ema_9: Optional[float] = None
    ema_21: Optional[float] = None
    ema_50: Optional[float] = None
    ema_200: Optional[float] = None
    sma_slope_20: Optional[float] = Field(None, description="Slope of 20-period SMA")
    price_vs_vwap: Optional[float] = Field(None, description="(close - VWAP) / VWAP")

    # Momentum features
    rsi_14: Optional[float] = None
    rsi_7: Optional[float] = None
    macd_hist: Optional[float] = None
    rate_of_change_10: Optional[float] = None

    # Volatility features
    atr_14_normalized: Optional[float] = Field(None, description="ATR / close price")
    bb_width: Optional[float] = Field(None, description="(upper - lower) / mid")
    realized_vol_20: Optional[float] = Field(None, description="20-period rolling std dev of log returns")

    # Order flow features (require tick/L2 data)
    volume_delta: Optional[float] = Field(None, description="Buy volume - sell volume")
    ob_imbalance: Optional[float] = Field(None, description="(bid_depth - ask_depth) / total")
    cvd_1h: Optional[float] = Field(None, description="Cumulative volume delta, 1h")

    # Derivatives features
    funding_rate: Optional[float] = None
    funding_vs_30d_mean: Optional[float] = Field(None, description="Z-score of funding vs 30d avg")
    oi_change_1h: Optional[float] = Field(None, description="% change in open interest, 1h")


# ─── Module 4: Market Regime ─────────────────────────────────

class MarketRegime(BaseModel):
    """
    The current "mood" of the market.

    Markets behave differently in different regimes:
    - Trend strategies work in trending markets
    - Mean-reversion strategies work in ranging markets
    - All strategies should reduce size in high volatility

    The regime probabilities should sum to ~1.0
    """
    symbol: str
    interval: str
    timestamp: datetime

    # Probability for each regime (should sum to ~1.0)
    trending_bull: float = Field(0.0, ge=0, le=1, description="Strong uptrend probability")
    trending_bear: float = Field(0.0, ge=0, le=1, description="Strong downtrend probability")
    choppy_ranging: float = Field(0.0, ge=0, le=1, description="Sideways/mean-reverting probability")
    high_volatility: float = Field(0.0, ge=0, le=1, description="Big swings probability")
    liquidity_crisis: float = Field(0.0, ge=0, le=1, description="Panic/crash probability")

    # Convenience fields
    dominant_regime: str = Field(..., description="Regime with highest probability")
    confidence: float = Field(..., ge=0, le=1, description="Probability of the dominant regime")
    method: str = Field("rule_based", description="'rule_based' or 'hmm'")


# ─── Module 10: Signal Aggregation ────────────────────────────

class TradingSignal(BaseModel):
    """
    A single trading signal from any source.

    Signals are combined by the Signal Aggregation Engine.
    Only signals above the minimum confidence threshold (0.65)
    are forwarded to the Portfolio Engine.
    """
    symbol: str
    direction: str = Field(..., description="'long', 'short', or 'neutral'")
    confidence: float = Field(..., ge=0, le=1, description="How confident the signal is (0-1)")
    expected_return: Optional[float] = Field(None, description="Expected % return")
    time_horizon: str = Field("4h", description="How long the signal is valid for")
    source: str = Field(..., description="Which module generated this signal")
    source_detail: Optional[str] = Field(None, description="Strategy name, model ID, etc.")
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AggregatedSignal(BaseModel):
    """
    Combined signal after merging all individual signals for the same asset.
    """
    symbol: str
    direction: str
    combined_confidence: float = Field(..., ge=0, le=1)
    contributing_signals: list[TradingSignal] = []
    passes_threshold: bool = Field(False, description="True if confidence >= 0.65")
    suggested_size_pct: Optional[float] = Field(None, description="Suggested position size as % of capital")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
