"""
ShufaClaw V2 — On-Chain Intelligence Schemas

These schemas define on-chain signals — data from blockchains
(Ethereum, Bitcoin, etc.) that can predict market moves.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from crypto_agent.schemas.market import DataSource


# ─── Module 2: On-Chain Signals ───────────────────────────────

class OnChainSignalType(str):
    """Common signal type constants."""
    EXCHANGE_NETFLOW = "exchange_netflow"
    WHALE_TRANSFER = "whale_transfer"
    STABLECOIN_MINT = "stablecoin_mint"
    SMART_MONEY_MOVE = "smart_money_move"
    EXCHANGE_RESERVE = "exchange_reserve"
    GAS_SPIKE = "gas_spike"
    TVL_CHANGE = "tvl_change"


class OnChainSignal(BaseModel):
    """
    A single on-chain signal.

    z_score: How unusual this value is compared to the last 30 days.
      - z_score > 2.0 = very unusual (anomaly)
      - z_score between -1 and 1 = normal
      - z_score < -2.0 = very unusual in the opposite direction

    is_anomaly: Automatically True if abs(z_score) > 2.0
    """
    symbol: str = Field(..., description="Which coin this relates to, e.g. BTC, ETH")
    signal_type: str = Field(..., description="Type like 'exchange_netflow', 'whale_transfer'")
    value: float = Field(..., description="Raw value of the signal")
    z_score: float = Field(0.0, description="How unusual vs 30-day average. >2 = anomaly")
    is_anomaly: bool = Field(False, description="True if z_score > 2 standard deviations")
    direction: Optional[str] = Field(None, description="'bullish' or 'bearish' interpretation")
    description: Optional[str] = Field(None, description="Human-readable explanation")
    timestamp: datetime
    source: DataSource

    def model_post_init(self, __context):
        """Auto-set is_anomaly based on z_score."""
        if abs(self.z_score) > 2.0:
            self.is_anomaly = True


class WhaleTransfer(BaseModel):
    """
    A large crypto transfer (>$1M).
    When whales move coins TO an exchange → they might sell.
    When whales move coins FROM an exchange → they're holding (bullish).
    """
    symbol: str
    from_address: str
    to_address: str
    value_usd: float = Field(..., description="USD value of the transfer")
    is_to_exchange: bool = Field(False, description="True if destination is a known exchange")
    is_from_exchange: bool = Field(False, description="True if source is a known exchange")
    tx_hash: str
    block_number: int
    timestamp: datetime
    source: DataSource


class ExchangeFlow(BaseModel):
    """
    Net flow of coins into/out of exchanges.
    Positive net_flow = more coins entering exchanges = selling pressure.
    Negative net_flow = coins leaving exchanges = bullish (hodling).
    """
    symbol: str
    inflow_usd: float
    outflow_usd: float
    net_flow_usd: float = Field(..., description="Positive = selling pressure, Negative = bullish")
    exchange: Optional[str] = None
    period: str = Field("1h", description="Time period: '1h', '24h', '7d'")
    timestamp: datetime
    source: DataSource
