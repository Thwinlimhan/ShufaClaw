"""
ShufaClaw V2 — Portfolio, Risk & Execution Schemas

Schemas for portfolio management, risk controls,
and order execution.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel, Field


# ─── Module 7: Portfolio ──────────────────────────────────────

class SizingMethod(str, Enum):
    """Position sizing methods."""
    FIXED_FRACTIONAL = "fixed_fractional"   # Risk X% per trade
    VOLATILITY_TARGET = "volatility_target" # Constant vol contribution
    HALF_KELLY = "half_kelly"               # Kelly criterion / 2
    RISK_PARITY = "risk_parity"             # Equal risk across strategies


class Position(BaseModel):
    """A single open position in the portfolio."""
    symbol: str
    side: str = Field(..., description="'long' or 'short'")
    size: float = Field(..., description="Quantity of the asset")
    entry_price: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    strategy_id: Optional[str] = None
    opened_at: datetime = Field(default_factory=datetime.utcnow)


class TargetPortfolio(BaseModel):
    """
    The desired portfolio state. The Execution Engine reads this
    and executes orders to match it.
    """
    positions: list[Position] = []
    total_value_usd: float = 0.0
    cash_usd: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─── Module 8: Risk Management ───────────────────────────────

class RiskAlertLevel(str, Enum):
    """Risk alert severity levels."""
    GREEN = "green"      # All good
    YELLOW = "yellow"    # At 80% of limit — reduce new positions by 50%
    RED = "red"          # Limit breached — halt new orders, reduce existing by 50%
    EMERGENCY = "emergency"  # Drawdown > 20% — close all, halt system


class RiskLimits(BaseModel):
    """
    Configurable risk limits. These are HARD limits that
    CANNOT be bypassed by any other module.
    """
    max_portfolio_drawdown: float = Field(0.15, description="15% max portfolio drawdown")
    max_daily_loss: float = Field(0.03, description="3% of NAV max daily loss")
    max_single_asset_exposure: float = Field(0.25, description="25% of NAV per asset")
    max_leverage: float = Field(3.0, description="3x max portfolio leverage")
    max_risk_per_trade: float = Field(0.01, description="1% of NAV per trade")
    max_open_positions: int = Field(20, description="Max simultaneous positions")


class RiskEvent(BaseModel):
    """
    Logged when a risk limit is approached or breached.
    Every risk event is saved — never deleted.
    """
    id: UUID = Field(default_factory=uuid4)
    alert_level: RiskAlertLevel
    limit_type: str = Field(..., description="Which limit was triggered")
    current_value: float = Field(..., description="Current value of the metric")
    limit_value: float = Field(..., description="The limit that was approached/breached")
    utilization_pct: float = Field(..., description="Current / limit * 100")
    action_taken: str = Field(..., description="What the system did in response")
    details: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─── Module 9: Execution Engine ──────────────────────────────

class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"
    RETRY = "retry"
    DEAD_LETTER = "dead_letter"


class ExecutionAlgorithm(str, Enum):
    MARKET = "market"           # Immediate execution
    TWAP = "twap"               # Time-weighted average price
    VWAP = "vwap"               # Volume-weighted average price
    PASSIVE_LIMIT = "passive_limit"  # Post at mid-price


class Order(BaseModel):
    """
    A single order in the system.
    Tracks full lifecycle from PENDING → FILLED/CANCELLED/DEAD_LETTER.
    """
    id: UUID = Field(default_factory=uuid4)
    symbol: str
    side: str = Field(..., description="'buy' or 'sell'")
    order_type: str = Field("market", description="'market', 'limit'")
    quantity: float
    price: Optional[float] = None
    algorithm: ExecutionAlgorithm = ExecutionAlgorithm.MARKET
    status: OrderStatus = OrderStatus.PENDING

    # Fill info
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0
    total_fees: float = 0.0

    # Execution quality
    arrival_price: Optional[float] = Field(None, description="Price when order was created")
    slippage_bps: Optional[float] = Field(None, description="Actual slippage in basis points")

    # Lifecycle
    strategy_id: Optional[str] = None
    exchange: str = "binance"
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    is_paper: bool = Field(True, description="True = simulated, False = real money")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
