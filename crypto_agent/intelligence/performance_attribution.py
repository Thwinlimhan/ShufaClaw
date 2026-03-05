"""
Performance attribution analysis for trading strategy.
Breaks down returns into components: selection, allocation, timing.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics


class PerformanceAttributor:
    """Analyzes trading performance by component."""
    
    def __init__(self, db_path: str = "data/crypto_agent.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize performance tracking tables."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Daily portfolio snapshots
        c.execute('''
            CREATE TABLE IF NOT EXISTS performance_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                portfolio_value REAL NOT NULL,
                benchmark_value REAL NOT NULL,
                daily_return REAL,
                benchmark_return REAL,
                alpha REAL,
                beta REAL,
                sharpe_ratio REAL
            )
        ''')
        
        # Attribution history
        c.execute('''
            CREATE TABLE IF NOT EXISTS attribution_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                selection_effect REAL,
                allocation_effect REAL,
                timing_effect REAL,
                interaction_effect REAL,
                total_alpha REAL,
                benchmark_name TEXT
            )
        ''')
        
        # Factor exposures
        c.execute('''
            CREATE TABLE IF NOT EXISTS factor_exposures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                size_factor REAL,
                momentum_factor REAL,
                value_factor REAL,
                quality_factor REAL,
                volatility_factor REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def calculate_attribution(
        self,
        portfolio_positions: List[Dict],
        benchmark_weights: Dict[str, float],
        period_days: int = 30
    ) -> Dict:
        """
        Calculate full performance attribution.
        
        Args:
            portfolio_positions: List of {symbol, amount, entry_price, current_price}
            benchmark_weights: Dict of {symbol: weight} for benchmark
            period_days: Analysis period
            
        Returns:
            Attribution breakdown with all effects
        """
        # Calculate portfolio returns
        portfolio_return = self._calculate_portfolio_return(portfolio_positions)
        
        # Calculate benchmark return
        benchmark_return = self._calculate_benchmark_return(benchmark_weights)
        
        # Calculate attribution effects
        selection = self._asset_selection_effect(portfolio_positions, benchmark_weights)
        allocation = self._allocation_effect(portfolio_positions, benchmark_weights)
        timing = self._timing_effect(portfolio_positions)
        interaction = self._interaction_effect(portfolio_positions, benchmark_weights)
        
        # Total alpha
        total_alpha = portfolio_return - benchmark_return
        
        return {
            'portfolio_return': portfolio_return,
            'benchmark_return': benchmark_return,
            'total_alpha': total_alpha,
            'selection_effect': selection,
            'allocation_effect': allocation,
            'timing_effect': timing,
            'interaction_effect': interaction,
            'period_days': period_days
        }
    
    def _calculate_portfolio_return(self, positions: List[Dict]) -> float:
        """Calculate total portfolio return."""
        if not positions:
            return 0.0
        
        total_value = sum(p['amount'] * p['current_price'] for p in positions)
        total_cost = sum(p['amount'] * p['entry_price'] for p in positions)
        
        if total_cost == 0:
            return 0.0
        
        return ((total_value - total_cost) / total_cost) * 100
    
    def _calculate_benchmark_return(self, weights: Dict[str, float]) -> float:
        """Calculate benchmark return (simplified)."""
        # In production, fetch actual benchmark returns
        # For now, use BTC as proxy
        return 12.0  # Placeholder: 12% benchmark return
    
    def _asset_selection_effect(
        self,
        positions: List[Dict],
        benchmark_weights: Dict[str, float]
    ) -> float:
        """
        Calculate asset selection effect.
        Formula: (Asset return - Benchmark return) × Benchmark weight
        """
        selection_effect = 0.0
        
        for position in positions:
            symbol = position['symbol']
            asset_return = self._calculate_position_return(position)
            benchmark_return = 12.0  # Placeholder
            
            # Use benchmark weight if available, else 0
            benchmark_weight = benchmark_weights.get(symbol, 0.0)
            
            selection_effect += (asset_return - benchmark_return) * benchmark_weight
        
        return selection_effect
    
    def _allocation_effect(
        self,
        positions: List[Dict],
        benchmark_weights: Dict[str, float]
    ) -> float:
        """
        Calculate allocation effect.
        Formula: (Portfolio weight - Benchmark weight) × Benchmark return
        """
        allocation_effect = 0.0
        
        # Calculate portfolio weights
        total_value = sum(p['amount'] * p['current_price'] for p in positions)
        
        for position in positions:
            symbol = position['symbol']
            position_value = position['amount'] * position['current_price']
            portfolio_weight = position_value / total_value if total_value > 0 else 0
            
            benchmark_weight = benchmark_weights.get(symbol, 0.0)
            benchmark_return = 12.0  # Placeholder
            
            allocation_effect += (portfolio_weight - benchmark_weight) * benchmark_return
        
        return allocation_effect
    
    def _timing_effect(self, positions: List[Dict]) -> float:
        """
        Calculate timing effect.
        Measures if entries/exits were at good prices.
        """
        timing_effect = 0.0
        
        for position in positions:
            # Compare entry price to average price over period
            entry_price = position['entry_price']
            current_price = position['current_price']
            
            # Simplified: if bought below current, good timing
            if entry_price < current_price:
                timing_effect += ((current_price - entry_price) / entry_price) * 100
        
        return timing_effect / len(positions) if positions else 0.0
    
    def _interaction_effect(
        self,
        positions: List[Dict],
        benchmark_weights: Dict[str, float]
    ) -> float:
        """
        Calculate interaction effect.
        Formula: (Portfolio weight - Benchmark weight) × (Asset return - Benchmark return)
        """
        interaction_effect = 0.0
        
        total_value = sum(p['amount'] * p['current_price'] for p in positions)
        
        for position in positions:
            symbol = position['symbol']
            position_value = position['amount'] * position['current_price']
            portfolio_weight = position_value / total_value if total_value > 0 else 0
            
            benchmark_weight = benchmark_weights.get(symbol, 0.0)
            asset_return = self._calculate_position_return(position)
            benchmark_return = 12.0  # Placeholder
            
            interaction_effect += (portfolio_weight - benchmark_weight) * (asset_return - benchmark_return)
        
        return interaction_effect
    
    def _calculate_position_return(self, position: Dict) -> float:
        """Calculate return for a single position."""
        entry = position['entry_price']
        current = position['current_price']
        
        if entry == 0:
            return 0.0
        
        return ((current - entry) / entry) * 100
    
    def save_attribution(self, attribution: Dict, benchmark_name: str = "BTC"):
        """Save attribution analysis to database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        period_end = datetime.now().isoformat()
        period_start = (datetime.now() - timedelta(days=attribution['period_days'])).isoformat()
        
        c.execute('''
            INSERT INTO attribution_history 
            (period_start, period_end, selection_effect, allocation_effect, 
             timing_effect, interaction_effect, total_alpha, benchmark_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            period_start, period_end,
            attribution['selection_effect'],
            attribution['allocation_effect'],
            attribution['timing_effect'],
            attribution['interaction_effect'],
            attribution['total_alpha'],
            benchmark_name
        ))
        
        conn.commit()
        conn.close()
    
    def get_attribution_history(self, limit: int = 10) -> List[Dict]:
        """Get historical attribution analyses."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT * FROM attribution_history 
            ORDER BY period_end DESC 
            LIMIT ?
        ''', (limit,))
        
        rows = c.fetchall()
        conn.close()
        
        return [
            {
                'period_start': row[1],
                'period_end': row[2],
                'selection_effect': row[3],
                'allocation_effect': row[4],
                'timing_effect': row[5],
                'interaction_effect': row[6],
                'total_alpha': row[7],
                'benchmark_name': row[8]
            }
            for row in rows
        ]


class BenchmarkComparator:
    """Compare portfolio performance to benchmarks."""
    
    BENCHMARKS = {
        'BTC': {'BTC': 1.0},
        '60/40': {'BTC': 0.6, 'ETH': 0.4},
        'EQUAL': {},  # Equal weight top 10
        'MARKET': {}  # Market cap weighted
    }
    
    def __init__(self, db_path: str = "data/crypto_agent.db"):
        self.db_path = db_path
    
    def compare_to_benchmark(
        self,
        portfolio_return: float,
        benchmark_name: str = 'BTC',
        period_days: int = 30
    ) -> Dict:
        """
        Compare portfolio to benchmark.
        
        Returns:
            Comparison metrics including alpha, beta, Sharpe ratio
        """
        # Get benchmark return (simplified)
        benchmark_return = self._get_benchmark_return(benchmark_name, period_days)
        
        # Calculate metrics
        alpha = portfolio_return - benchmark_return
        beta = self._calculate_beta(portfolio_return, benchmark_return)
        sharpe = self._calculate_sharpe(portfolio_return)
        
        return {
            'portfolio_return': portfolio_return,
            'benchmark_return': benchmark_return,
            'benchmark_name': benchmark_name,
            'alpha': alpha,
            'beta': beta,
            'sharpe_ratio': sharpe,
            'outperformance': alpha > 0
        }
    
    def _get_benchmark_return(self, benchmark_name: str, period_days: int) -> float:
        """Get benchmark return for period."""
        # Simplified: return placeholder values
        benchmarks = {
            'BTC': 12.0,
            '60/40': 10.5,
            'EQUAL': 15.0,
            'MARKET': 11.0
        }
        return benchmarks.get(benchmark_name, 12.0)
    
    def _calculate_beta(self, portfolio_return: float, benchmark_return: float) -> float:
        """Calculate beta (volatility relative to benchmark)."""
        # Simplified: assume 1.0 for now
        # In production, calculate from daily returns
        if benchmark_return == 0:
            return 1.0
        return portfolio_return / benchmark_return
    
    def _calculate_sharpe(self, portfolio_return: float, risk_free_rate: float = 2.0) -> float:
        """Calculate Sharpe ratio (risk-adjusted return)."""
        # Simplified calculation
        # In production, use standard deviation of returns
        excess_return = portfolio_return - risk_free_rate
        volatility = 15.0  # Placeholder: 15% volatility
        
        if volatility == 0:
            return 0.0
        
        return excess_return / volatility


class FactorAnalyzer:
    """Analyze factor exposures and returns."""
    
    def __init__(self, db_path: str = "data/crypto_agent.db"):
        self.db_path = db_path
    
    def calculate_factor_exposures(self, positions: List[Dict]) -> Dict:
        """
        Calculate factor exposures.
        
        Factors:
        - Size: Large cap vs small cap
        - Momentum: Trending vs mean-reverting
        - Value: Undervalued vs overvalued
        - Quality: Fundamentally strong vs weak
        - Volatility: Low vol vs high vol
        """
        if not positions:
            return {
                'size': 0.0,
                'momentum': 0.0,
                'value': 0.0,
                'quality': 0.0,
                'volatility': 0.0
            }
        
        # Simplified factor calculation
        # In production, use market cap, price momentum, etc.
        
        size_factor = self._calculate_size_factor(positions)
        momentum_factor = self._calculate_momentum_factor(positions)
        value_factor = 0.1  # Placeholder
        quality_factor = 0.4  # Placeholder
        volatility_factor = -0.2  # Placeholder
        
        return {
            'size': size_factor,
            'momentum': momentum_factor,
            'value': value_factor,
            'quality': quality_factor,
            'volatility': volatility_factor
        }
    
    def _calculate_size_factor(self, positions: List[Dict]) -> float:
        """Calculate size factor exposure."""
        # Negative = small cap tilt, Positive = large cap tilt
        # Simplified: based on position in top 10
        large_cap_symbols = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP']
        
        large_cap_weight = sum(
            1 for p in positions if p['symbol'] in large_cap_symbols
        ) / len(positions)
        
        # Convert to factor score (-1 to +1)
        return (large_cap_weight - 0.5) * 2
    
    def _calculate_momentum_factor(self, positions: List[Dict]) -> float:
        """Calculate momentum factor exposure."""
        # Positive = momentum bias, Negative = mean reversion
        
        momentum_scores = []
        for position in positions:
            # If position is profitable, it has momentum
            return_pct = self._calculate_position_return(position)
            if return_pct > 0:
                momentum_scores.append(1)
            else:
                momentum_scores.append(-1)
        
        if not momentum_scores:
            return 0.0
        
        return statistics.mean(momentum_scores)
    
    def _calculate_position_return(self, position: Dict) -> float:
        """Calculate return for a position."""
        entry = position['entry_price']
        current = position['current_price']
        
        if entry == 0:
            return 0.0
        
        return ((current - entry) / entry) * 100
    
    def save_factor_exposures(self, exposures: Dict):
        """Save factor exposures to database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        date = datetime.now().isoformat()
        
        c.execute('''
            INSERT INTO factor_exposures 
            (date, size_factor, momentum_factor, value_factor, quality_factor, volatility_factor)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            date,
            exposures['size'],
            exposures['momentum'],
            exposures['value'],
            exposures['quality'],
            exposures['volatility']
        ))
        
        conn.commit()
        conn.close()
