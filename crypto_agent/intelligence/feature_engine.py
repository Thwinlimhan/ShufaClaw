"""
ShufaClaw V2 — Feature Engineering Service

This service compiles raw market and on-chain data into standardized, versioned
Feature Vectors that AI models and strategies can securely consume.
It also exposes a REST API for the dashboard/backtester.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import logging

from crypto_agent.data import technical as tech

logger = logging.getLogger(__name__)

# --- SCHEMA ---

class FeatureVector(BaseModel):
    """The canonical 'snapshot' of a market's state at a point in time."""
    feature_version: str = "v1.0"
    symbol: str
    interval: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Trend Features
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    adx_14: Optional[float] = None
    
    # Momentum Features
    rsi_14: Optional[float] = None
    macd_hist: Optional[float] = None
    
    # Volatility Features
    atr_14: Optional[float] = None
    realized_vol_20: Optional[float] = None
    bb_width: Optional[float] = None
    
    # Microstructure
    volume_delta: Optional[float] = None
    ob_imbalance: Optional[float] = None
    
    # Advanced
    funding_rate_zscore: Optional[float] = None

# --- ENGINE ---

class FeatureEngine:
    def __init__(self):
        self.version = "v1.0"

    def compute_features(self, symbol: str, interval: str, klines: list, trades=None, orderbook=None, funding_rates=None) -> FeatureVector:
        """
        Takes raw data and computes all mathematical transformations.
        Returns a strict, versioned FeatureVector.
        """
        if not klines or len(klines) < 200:
            logger.warning(f"Not enough klines to compute features for {symbol}.")
            return FeatureVector(symbol=symbol, interval=interval, feature_version=self.version)
            
        closes = [float(k[4]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        
        # 1. Base calculations
        rsi = tech.calculate_rsi(closes)
        macd = tech.calculate_macd(closes)
        adx = tech.calculate_adx(klines)
        atr = tech.calculate_atr(klines)
        bb = tech.calculate_bollinger_bands(closes)
        realized_vol = tech.calculate_realized_volatility(closes)
        smas = {p: tech.calculate_sma(closes, p) for p in [20, 50, 200]}
        
        # Derived Volatility
        bb_width = None
        if bb:
            bb_width = (bb['upper'] - bb['lower']) / bb['mid'] if bb['mid'] != 0 else 0
            
        # 2. Microstructure (if available)
        volume_delta = None
        if trades:
            buys = sum(t['amount'] for t in trades if t['side'] == 'buy')
            sells = sum(t['amount'] for t in trades if t['side'] == 'sell')
            volume_delta = tech.calculate_volume_delta(buys, sells)
            
        ob_imbalance = None
        if orderbook:
            ob_imbalance = tech.calculate_ob_imbalance(orderbook['bids'], orderbook['asks'])
            
        # 3. Macro (if available)
        funding_zscore = None
        if funding_rates and len(funding_rates) > 20:
            current_funding = funding_rates[-1]
            funding_zscore = tech.calculate_zscore(current_funding, funding_rates)

        return FeatureVector(
            feature_version=self.version,
            symbol=symbol,
            interval=interval,
            sma_20=smas[20],
            sma_50=smas[50],
            sma_200=smas[200],
            adx_14=adx,
            rsi_14=rsi,
            macd_hist=macd['hist'] if macd else None,
            atr_14=atr,
            realized_vol_20=realized_vol,
            bb_width=bb_width,
            volume_delta=volume_delta,
            ob_imbalance=ob_imbalance,
            funding_rate_zscore=funding_zscore
        )

# Global Instance
feature_engine = FeatureEngine()
