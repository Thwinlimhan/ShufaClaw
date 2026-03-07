"""
ShufaClaw V2 — Strategy & Backtesting Schemas

Schemas for backtesting results, strategy definitions,
and the strategy discovery engine.
"""

from datetime import datetime, date
from typing import Optional
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel, Field


# ─── Module 5: Backtesting ────────────────────────────────────

class BacktestResult(BaseModel):
    """
    Complete results from running a backtest.

    Key metrics explained:
    - Sharpe ratio: Risk-adjusted return. >1.0 is good, >2.0 is excellent.
    - Sortino ratio: Like Sharpe but only penalizes downside risk. Higher = better.
    - Max drawdown: Worst peak-to-trough decline. Lower = less scary.
    - Profit factor: Gross profit / gross loss. >1.5 is good.
    - Win rate: % of trades that were profitable.
    - Expectancy: Average $ made per trade (including losers).
    """
    id: UUID = Field(default_factory=uuid4)
    strategy_id: str
    symbol: str
    interval: str
    start_date: date
    end_date: date

    # Core performance
    total_return: float = Field(..., description="Total return as decimal, e.g. 0.25 = 25%")
    annualized_return: float = Field(..., description="Annual return as decimal")
    sharpe_ratio: float = Field(..., description="Risk-adjusted return. >1 good, >2 excellent")
    sortino_ratio: float = Field(..., description="Downside-risk-adjusted return")
    max_drawdown: float = Field(..., description="Worst peak-to-trough drop as decimal, e.g. 0.15 = 15%")
    max_drawdown_duration_days: int = Field(0, description="How many days the worst drawdown lasted")
    profit_factor: float = Field(..., description="Gross profit / gross loss. >1.5 is good")

    # Trade stats
    win_rate: float = Field(..., description="% of winning trades as decimal")
    expectancy: float = Field(0.0, description="Average profit per trade in $")
    num_trades: int
    avg_holding_period_hours: float = 0.0

    # Advanced
    regime_breakdown: dict = Field(default_factory=dict, description="Performance by market regime")
    monthly_returns: list[float] = Field(default_factory=list)

    # Metadata
    initial_capital: float = 10000.0
    final_capital: float = 0.0
    slippage_bps: float = 10.0
    fee_rate: float = 0.001
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Module 6: Strategy Discovery ─────────────────────────────

class StrategyType(str, Enum):
    RULE_BASED = "rule_based"
    ML_SIGNAL = "ml_signal"
    RL_AGENT = "rl_agent"


class StrategyStatus(str, Enum):
    CANDIDATE = "candidate"       # Just discovered, untested
    VALIDATED = "validated"       # Passed walk-forward + out-of-sample
    LIVE = "live"                 # Currently trading
    RETIRED = "retired"           # No longer active


class Strategy(BaseModel):
    """
    A trading strategy with its definition and current status.
    """
    id: UUID = Field(default_factory=uuid4)
    name: str
    type: StrategyType
    version: str = "v1.0.0"
    feature_version: str = "v1.0.0"
    status: StrategyStatus = StrategyStatus.CANDIDATE

    # Strategy parameters — different for each type
    params: dict = Field(default_factory=dict, description="Strategy-specific parameters as JSON")

    # Performance summary
    best_sharpe: Optional[float] = None
    best_win_rate: Optional[float] = None
    max_drawdown: Optional[float] = None
    total_backtests: int = 0

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StrategyBacktestLink(BaseModel):
    """Links a strategy to its backtest results."""
    strategy_id: UUID
    backtest_result_id: UUID
    is_validation: bool = Field(False, description="True if this was a validation (out-of-sample) test")
