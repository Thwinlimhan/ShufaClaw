"""
ShufaClaw V2 — Vectorized Strategy Optimizer

Uses `vectorbt` to perform extremely fast parameter sweeps and walk-forward 
analysis across thousands of indicator combinations simultaneously.
This is "Strategy Discovery Layer 1".
"""

import logging
import numpy as np
import pandas as pd
import vectorbt as vbt

logger = logging.getLogger(__name__)

class StrategyOptimizer:
    def __init__(self):
        self.fee = 0.001  # Exchange fee/slippage (0.1%)

    def prepare_data(self, klines: list) -> pd.DataFrame:
        """Converts raw CCXT/Binance klines to a pandas DataFrame for vectorbt."""
        if not klines:
            return pd.DataFrame()
            
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume'
        ])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        # Ensure we only have numeric data
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        return df

    def optimize_sma_cross(self, df: pd.DataFrame, fast_windows: list, slow_windows: list):
        """
        Sweeps all combinations of fast and slow SMAs instantly.
        e.g. fast_windows=[10, 20, 30], slow_windows=[50, 100, 200]
        """
        closes = df['close']
        
        # Create parameter grids
        fast_ma = vbt.MA.run(closes, window=fast_windows, short_name='fast')
        slow_ma = vbt.MA.run(closes, window=slow_windows, short_name='slow')

        # Generate entry and exit signals (Cartesian product of all parameters)
        entries = fast_ma.ma_crossed_above(slow_ma)
        exits = fast_ma.ma_crossed_below(slow_ma)

        # Run vectorized backtester
        portfolio = vbt.Portfolio.from_signals(
            closes, 
            entries, 
            exits, 
            fees=self.fee,
            init_cash=10000,
            freq='1H' # Assuming 1H data for Sharpe calculation
        )
        
        # Get stats for all combinations
        stats = portfolio.stats()
        
        # We can extract the best parameters based on Sharpe Ratio
        metrics = portfolio.sharpe_ratio()
        
        # Safely extract the best parameters
        if isinstance(metrics, float): # Only 1 combination tested
            best_fast = fast_windows[0]
            best_slow = slow_windows[0]
            best_sharpe = metrics
        else:
            best_idx = metrics.idxmax()
            best_fast = best_idx[0]
            best_slow = best_idx[1]
            best_sharpe = metrics.max()

        # Isolate the best portfolio run for detailed metrics
        best_pf = portfolio.loc[best_fast, best_slow] if not isinstance(metrics, float) else portfolio

        return {
            "strategy": "SMA_CROSS",
            "best_params": {
                "fast_window": int(best_fast),
                "slow_window": int(best_slow)
            },
            "metrics": {
                "total_return_pct": float(best_pf.total_return() * 100),
                "win_rate_pct": float(best_pf.win_rate() * 100),
                "sharpe_ratio": float(best_sharpe),
                "sortino_ratio": float(best_pf.sortino_ratio()),
                "max_drawdown_pct": float(abs(best_pf.max_drawdown()) * 100),
                "total_trades": int(best_pf.trades.count())
            }
        }

    def walk_forward_analysis(self, df: pd.DataFrame, train_ratio: float = 0.7):
        """
        Splits data into a training (in-sample) and testing (out-of-sample) set 
        to prevent overfitting curve-fitted strategies.
        """
        split_idx = int(len(df) * train_ratio)
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:]
        
        return train_df, test_df

# Global Instance
optimizer = StrategyOptimizer()
