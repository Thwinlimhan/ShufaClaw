"""
ShufaClaw V2 — Strategy Discovery Engine

Automates the process of finding, testing, and logging profitable trading
strategies using VectorBT for parameter sweeps.

Automatically transitions strategies to CANDIDATE status in the Database Model.
"""

import logging
import uuid
from datetime import datetime, timezone

from crypto_agent.intelligence.optimizer import optimizer
from crypto_agent.schemas.strategy import Strategy, StrategyType, StrategyStatus
from crypto_agent.data import technical as tech

logger = logging.getLogger(__name__)

class StrategyDiscoveryEngine:
    """Discovers parameter combos that yield high Sharpe/Sortino ratios."""

    def __init__(self):
        self.min_trades = 30
        self.min_sharpe = 1.0

    async def discover_sma_cross(self, symbol: str, timeframe: str = "1h"):
        """
        Runs a massive grid search over SMA combinations to find the best 
        performing parameters for the given asset.
        """
        logger.info(f"🔍 Starting Strategy Discovery (SMA Cross) for {symbol} ({timeframe})")
        
        # 1. Fetch high-quality historical data (in V2, we pull from TimescaleDB)
        # Using the tech.fetch_klines as our reliable fallback layer
        klines = await tech.fetch_klines(symbol, interval=timeframe, limit=1000)
        
        if not klines or len(klines) < 300:
            logger.error(f"Not enough data to discover strategies for {symbol}.")
            return None
            
        # 2. Convert to Pandas / VectorBT format
        df = optimizer.prepare_data(klines)
        
        # 3. Walk Forward Split (70% train, 30% test)
        train_df, test_df = optimizer.walk_forward_analysis(df, train_ratio=0.7)
        logger.info(f"   Train set: {len(train_df)} periods | Test set: {len(test_df)} periods")
        
        # 4. Define Parameter Grid
        fast_windows = [5, 10, 15, 20, 25]
        slow_windows = [50, 100, 150, 200]
        
        # 5. Run Vectorized Optimization (In-Sample / Train)
        logger.info(f"   Sweeping {len(fast_windows) * len(slow_windows)} parameter combinations...")
        train_result = optimizer.optimize_sma_cross(train_df, fast_windows, slow_windows)
        
        best_params = train_result['best_params']
        train_metrics = train_result['metrics']
        
        logger.info(f"   Best Train Params: Fast MA {best_params['fast_window']}, Slow MA {best_params['slow_window']}")
        logger.info(f"   Train Sharpe: {train_metrics['sharpe_ratio']:.2f} | Trades: {train_metrics['total_trades']}")
        
        # 6. Overfitting Prevention Checks
        if train_metrics['total_trades'] < self.min_trades:
            logger.warning("   ❌ Rejected: Not enough trades (Curve fitting risk)")
            return None
            
        if train_metrics['sharpe_ratio'] < self.min_sharpe:
            logger.warning(f"   ❌ Rejected: Sharpe {train_metrics['sharpe_ratio']:.2f} is below minimum {self.min_sharpe}")
            return None
            
        # 7. Out-Of-Sample Validation (Test)
        # We test the BEST parameters found in training on the UNSEEN test data.
        logger.info("   Testing best params on unseen Walk-Forward data...")
        test_result = optimizer.optimize_sma_cross(
            test_df, 
            fast_windows=[best_params['fast_window']], 
            slow_windows=[best_params['slow_window']]
        )
        test_metrics = test_result['metrics']
        
        logger.info(f"   OOS Sharpe: {test_metrics['sharpe_ratio']:.2f} | Returns: {test_metrics['total_return_pct']:.2f}%")
        
        # 8. Promote to CANDIDATE if it survived
        if test_metrics['sharpe_ratio'] > 0.5: # Lower bar for OOS, but must still be positive
            logger.info("   ✅ Validation Passed! Creating Strategy Candidate.")
            
            # Create strict Schema defining the strategy
            candidate = Strategy(
                id=uuid.uuid4(),
                name=f"SMA_Cross_{best_params['fast_window']}x{best_params['slow_window']}_{symbol}",
                type=StrategyType.RULE_BASED,
                version="v1.0.0",
                status=StrategyStatus.CANDIDATE,
                params={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "fast_window": best_params['fast_window'],
                    "slow_window": best_params['slow_window']
                },
                best_sharpe=test_metrics['sharpe_ratio'],
                best_win_rate=test_metrics['win_rate_pct'],
                max_drawdown=test_metrics['max_drawdown_pct'],
                total_backtests=len(fast_windows) * len(slow_windows)
            )
            
            # In fully deployed V2, we would write this to TimescaleDB `strategies` table here.
            return candidate.model_dump()
            
        else:
            logger.warning("   ❌ Validation Failed: Strategy broke down in Out-Of-Sample data.")
            return None

# Global Instance
discovery_engine = StrategyDiscoveryEngine()
