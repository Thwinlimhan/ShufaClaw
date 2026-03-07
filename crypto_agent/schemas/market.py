"""
ShufaClaw V2 — Market Data Schemas

These Pydantic models define the exact shape of all market data.
Every incoming piece of data MUST match one of these schemas before
it's stored or forwarded. This prevents bad data from entering the system.

Think of schemas like "rules" for data — if data doesn't fit the rules,
it gets rejected automatically.
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ─── Enums (predefined choices) ───────────────────────────────

class Interval(str, Enum):
    """Allowed candle timeframes."""
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"


class DataSource(str, Enum):
    """Where data came from."""
    BINANCE = "binance"
    BYBIT = "bybit"
    COINGECKO = "coingecko"
    ETHERSCAN = "etherscan"
    DEFILLAMA = "defillama"
    BLOCKCHAIN_INFO = "blockchain_info"
    GLASSNODE = "glassnode"


# ─── Module 1: Market Data ────────────────────────────────────

class Candle(BaseModel):
    """
    One OHLCV candle (Open, High, Low, Close, Volume).
    This is the most fundamental data type in the system.
    Example: "BTC went from $60,000 to $61,000 in the last 1 hour"
    """
    symbol: str = Field(..., description="Trading pair, e.g. BTCUSDT")
    interval: Interval
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = Field(..., description="Base asset volume")
    quote_volume: Decimal = Field(..., description="Quote asset volume (USD value)")
    source: DataSource
    ingested_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {Decimal: str}


class FundingRate(BaseModel):
    """
    Funding rate for perpetual futures.
    Positive = longs pay shorts (market is bullish / overleveraged long).
    Negative = shorts pay longs (market is bearish / overleveraged short).
    """
    symbol: str
    rate: float = Field(..., description="Funding rate as decimal, e.g. 0.0001 = 0.01%")
    timestamp: datetime
    next_funding_time: Optional[datetime] = None
    source: DataSource


class OpenInterest(BaseModel):
    """
    Open interest = total value of all outstanding futures contracts.
    Rising OI + rising price = strong trend.
    Rising OI + falling price = selling pressure.
    """
    symbol: str
    value_usd: float
    change_1h_pct: Optional[float] = None
    timestamp: datetime
    source: DataSource


class Liquidation(BaseModel):
    """
    A forced closure of a leveraged position.
    Large liquidations can cause cascading sell-offs.
    """
    symbol: str
    side: str = Field(..., description="'long' or 'short' — which side got liquidated")
    quantity: float
    price: float
    value_usd: float
    timestamp: datetime
    source: DataSource


class OrderBookSnapshot(BaseModel):
    """
    A snapshot of the order book at a point in time.
    bids = buyers waiting, asks = sellers waiting.
    """
    symbol: str
    bids: list[list[float]] = Field(..., description="List of [price, quantity] for buyers")
    asks: list[list[float]] = Field(..., description="List of [price, quantity] for sellers")
    timestamp: datetime
    source: DataSource


class TradeTick(BaseModel):
    """
    A single executed trade on the exchange.
    Used to compute volume delta (buy volume vs sell volume).
    """
    symbol: str
    price: float
    quantity: float
    is_buyer_maker: bool = Field(..., description="True = sell (buyer was maker), False = buy")
    timestamp: datetime
    source: DataSource


# ─── Module 1: Data Quality ───────────────────────────────────

class DataQualityLog(BaseModel):
    """
    Tracks if our data has gaps, errors, or is delayed.
    Example: "We missed 5 candles for BTCUSDT between 3pm-4pm"
    """
    symbol: str
    interval: Optional[Interval] = None
    issue_type: str = Field(..., description="'gap', 'anomaly', 'latency', 'reconnect'")
    description: str
    gap_start: Optional[datetime] = None
    gap_end: Optional[datetime] = None
    records_affected: int = 0
    resolved: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)
