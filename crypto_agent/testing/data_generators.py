"""
Data Generators for Testing (Level 38)

Generate realistic market scenarios and price histories for testing.
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import math


def generate_price_history(
    symbol: str,
    start_price: float,
    days: int = 30,
    volatility: float = 0.02,
    trend: float = 0.0,
    interval: str = '1h'
) -> List[Dict[str, Any]]:
    """
    Generate realistic price history using geometric Brownian motion.
    
    Args:
        symbol: Coin symbol
        start_price: Starting price
        days: Number of days of history
        volatility: Daily volatility (0.02 = 2%)
        trend: Daily trend (0.01 = 1% daily growth)
        interval: Time interval (1h, 4h, 1d)
    
    Returns:
        List of OHLCV candles
    """
    intervals = {'1h': 24, '4h': 6, '1d': 1}
    candles_per_day = intervals.get(interval, 24)
    total_candles = days * candles_per_day
    
    candles = []
    current_price = start_price
    current_time = datetime.now() - timedelta(days=days)
    
    for i in range(total_candles):
        # Geometric Brownian motion
        dt = 1 / candles_per_day  # Fraction of day
        drift = trend * dt
        shock = volatility * math.sqrt(dt) * random.gauss(0, 1)
        
        price_change = current_price * (drift + shock)
        new_price = current_price + price_change
        
        # Generate OHLC
        high = max(current_price, new_price) * random.uniform(1.0, 1.01)
        low = min(current_price, new_price) * random.uniform(0.99, 1.0)
        open_price = current_price
        close_price = new_price
        
        # Generate volume (higher volume on bigger moves)
        base_volume = start_price * random.uniform(1e6, 5e6)
        volume_multiplier = 1 + abs(price_change / current_price) * 10
        volume = base_volume * volume_multiplier
        
        candles.append({
            'timestamp': current_time.isoformat(),
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume
        })
        
        current_price = new_price
        current_time += timedelta(hours=24 // candles_per_day)
    
    return candles


def generate_market_scenario(scenario_type: str) -> Dict[str, Any]:
    """
    Generate predefined market scenarios for testing.
    
    Scenarios:
    - bull_run: Strong uptrend, high greed
    - bear_market: Strong downtrend, high fear
    - sideways: Range-bound, neutral sentiment
    - volatile: High volatility, mixed signals
    - crash: Sudden drop, extreme fear
    - recovery: Bounce from lows, improving sentiment
    """
    scenarios = {
        'bull_run': {
            'name': 'Bull Run',
            'description': 'Strong uptrend with high greed',
            'fear_greed': 75,
            'trend': 0.03,  # 3% daily growth
            'volatility': 0.02,
            'btc_price': 105000,
            'eth_price': 3800,
            'market_sentiment': 'positive',
            'volume_multiplier': 1.5,
            'ta_signals': {
                'rsi': 65,
                'trend': 'up',
                'macd': 'bullish'
            }
        },
        'bear_market': {
            'name': 'Bear Market',
            'description': 'Strong downtrend with high fear',
            'fear_greed': 25,
            'trend': -0.02,  # -2% daily decline
            'volatility': 0.03,
            'btc_price': 85000,
            'eth_price': 2800,
            'market_sentiment': 'negative',
            'volume_multiplier': 0.8,
            'ta_signals': {
                'rsi': 35,
                'trend': 'down',
                'macd': 'bearish'
            }
        },
        'sideways': {
            'name': 'Sideways Market',
            'description': 'Range-bound with neutral sentiment',
            'fear_greed': 50,
            'trend': 0.0,
            'volatility': 0.015,
            'btc_price': 97500,
            'eth_price': 3400,
            'market_sentiment': 'neutral',
            'volume_multiplier': 1.0,
            'ta_signals': {
                'rsi': 50,
                'trend': 'neutral',
                'macd': 'neutral'
            }
        },
        'volatile': {
            'name': 'High Volatility',
            'description': 'Large swings, mixed signals',
            'fear_greed': 45,
            'trend': 0.0,
            'volatility': 0.05,  # 5% volatility
            'btc_price': 97500,
            'eth_price': 3400,
            'market_sentiment': 'mixed',
            'volume_multiplier': 2.0,
            'ta_signals': {
                'rsi': 55,
                'trend': 'neutral',
                'macd': 'mixed'
            }
        },
        'crash': {
            'name': 'Market Crash',
            'description': 'Sudden drop, extreme fear',
            'fear_greed': 10,
            'trend': -0.10,  # -10% daily
            'volatility': 0.08,
            'btc_price': 75000,
            'eth_price': 2500,
            'market_sentiment': 'panic',
            'volume_multiplier': 3.0,
            'ta_signals': {
                'rsi': 20,
                'trend': 'down',
                'macd': 'bearish'
            }
        },
        'recovery': {
            'name': 'Recovery',
            'description': 'Bounce from lows, improving sentiment',
            'fear_greed': 55,
            'trend': 0.04,  # 4% daily growth
            'volatility': 0.03,
            'btc_price': 92000,
            'eth_price': 3200,
            'market_sentiment': 'improving',
            'volume_multiplier': 1.3,
            'ta_signals': {
                'rsi': 58,
                'trend': 'up',
                'macd': 'bullish'
            }
        }
    }
    
    return scenarios.get(scenario_type, scenarios['sideways'])


def generate_portfolio_scenario(
    scenario_type: str,
    portfolio_value: float = 10000
) -> Dict[str, Any]:
    """
    Generate portfolio scenarios for testing.
    
    Scenarios:
    - diversified: Well-balanced portfolio
    - concentrated: Heavy in 1-2 assets
    - risky: High-risk altcoins
    - conservative: BTC/ETH heavy
    - losing: Underwater positions
    - winning: All positions in profit
    """
    scenarios = {
        'diversified': {
            'name': 'Diversified Portfolio',
            'total_value': portfolio_value,
            'positions': [
                {'symbol': 'BTC', 'amount': 0.3, 'entry_price': 95000, 'weight': 0.30},
                {'symbol': 'ETH', 'amount': 5.0, 'entry_price': 3200, 'weight': 0.25},
                {'symbol': 'SOL', 'amount': 80, 'entry_price': 120, 'weight': 0.15},
                {'symbol': 'BNB', 'amount': 15, 'entry_price': 570, 'weight': 0.15},
                {'symbol': 'ADA', 'amount': 10000, 'entry_price': 0.62, 'weight': 0.10},
                {'symbol': 'AVAX', 'amount': 50, 'entry_price': 36, 'weight': 0.05}
            ],
            'risk_level': 'medium',
            'expected_return': 0.15
        },
        'concentrated': {
            'name': 'Concentrated Portfolio',
            'total_value': portfolio_value,
            'positions': [
                {'symbol': 'BTC', 'amount': 0.7, 'entry_price': 94000, 'weight': 0.70},
                {'symbol': 'ETH', 'amount': 7.0, 'entry_price': 3100, 'weight': 0.30}
            ],
            'risk_level': 'low',
            'expected_return': 0.12
        },
        'risky': {
            'name': 'High-Risk Portfolio',
            'total_value': portfolio_value,
            'positions': [
                {'symbol': 'SOL', 'amount': 200, 'entry_price': 115, 'weight': 0.30},
                {'symbol': 'AVAX', 'amount': 300, 'entry_price': 35, 'weight': 0.25},
                {'symbol': 'MATIC', 'amount': 15000, 'entry_price': 0.88, 'weight': 0.20},
                {'symbol': 'DOT', 'amount': 1500, 'entry_price': 8.0, 'weight': 0.15},
                {'symbol': 'LINK', 'amount': 500, 'entry_price': 17, 'weight': 0.10}
            ],
            'risk_level': 'high',
            'expected_return': 0.25
        },
        'conservative': {
            'name': 'Conservative Portfolio',
            'total_value': portfolio_value,
            'positions': [
                {'symbol': 'BTC', 'amount': 0.8, 'entry_price': 96000, 'weight': 0.80},
                {'symbol': 'ETH', 'amount': 5.0, 'entry_price': 3300, 'weight': 0.20}
            ],
            'risk_level': 'low',
            'expected_return': 0.10
        },
        'losing': {
            'name': 'Losing Portfolio',
            'total_value': portfolio_value * 0.7,  # Down 30%
            'positions': [
                {'symbol': 'BTC', 'amount': 0.3, 'entry_price': 105000, 'weight': 0.30},
                {'symbol': 'ETH', 'amount': 5.0, 'entry_price': 3800, 'weight': 0.25},
                {'symbol': 'SOL', 'amount': 80, 'entry_price': 145, 'weight': 0.20},
                {'symbol': 'ADA', 'amount': 10000, 'entry_price': 0.85, 'weight': 0.15},
                {'symbol': 'MATIC', 'amount': 8000, 'entry_price': 1.20, 'weight': 0.10}
            ],
            'risk_level': 'high',
            'expected_return': -0.30
        },
        'winning': {
            'name': 'Winning Portfolio',
            'total_value': portfolio_value * 1.5,  # Up 50%
            'positions': [
                {'symbol': 'BTC', 'amount': 0.3, 'entry_price': 85000, 'weight': 0.35},
                {'symbol': 'ETH', 'amount': 5.0, 'entry_price': 2800, 'weight': 0.30},
                {'symbol': 'SOL', 'amount': 80, 'entry_price': 95, 'weight': 0.20},
                {'symbol': 'BNB', 'amount': 15, 'entry_price': 480, 'weight': 0.15}
            ],
            'risk_level': 'medium',
            'expected_return': 0.50
        }
    }
    
    return scenarios.get(scenario_type, scenarios['diversified'])


def generate_trade_setup_scenario(setup_type: str, symbol: str = 'BTC') -> Dict[str, Any]:
    """
    Generate specific trade setup scenarios for testing proposals.
    
    Setup types:
    - breakout: Price near resistance with volume
    - pullback: Uptrend with oversold RSI
    - reversal: RSI extreme
    - range: Clear support/resistance
    - momentum: Strong trend
    """
    base_price = 97500 if symbol == 'BTC' else 3400 if symbol == 'ETH' else 100
    
    setups = {
        'breakout': {
            'symbol': symbol,
            'price': base_price,
            'rsi': 58,
            'trend': 'up',
            'support': base_price * 0.95,
            'resistance': base_price * 0.98,  # Near resistance
            'volume_ratio': 2.5,  # High volume
            'sma_20': base_price * 0.97,
            'sma_50': base_price * 0.94,
            'expected_setup': 'breakout'
        },
        'pullback': {
            'symbol': symbol,
            'price': base_price,
            'rsi': 35,  # Oversold
            'trend': 'up',
            'support': base_price * 0.97,
            'resistance': base_price * 1.08,
            'volume_ratio': 0.8,
            'sma_20': base_price * 0.98,
            'sma_50': base_price * 0.96,
            'expected_setup': 'pullback'
        },
        'reversal': {
            'symbol': symbol,
            'price': base_price,
            'rsi': 22,  # Extreme oversold
            'trend': 'down',
            'support': base_price * 0.92,
            'resistance': base_price * 1.08,
            'volume_ratio': 1.5,
            'sma_20': base_price * 1.02,
            'sma_50': base_price * 1.05,
            'expected_setup': 'reversal'
        },
        'range': {
            'symbol': symbol,
            'price': base_price,
            'rsi': 50,
            'trend': 'neutral',
            'support': base_price * 0.95,
            'resistance': base_price * 1.05,
            'volume_ratio': 0.9,
            'sma_20': base_price * 0.99,
            'sma_50': base_price * 0.98,
            'expected_setup': 'range_trade'
        },
        'momentum': {
            'symbol': symbol,
            'price': base_price,
            'rsi': 62,
            'trend': 'up',
            'support': base_price * 0.93,
            'resistance': base_price * 1.12,
            'volume_ratio': 1.3,
            'sma_20': base_price * 0.96,
            'sma_50': base_price * 0.92,
            'expected_setup': 'momentum'
        }
    }
    
    return setups.get(setup_type, setups['breakout'])


def generate_event_scenario(event_type: str) -> Dict[str, Any]:
    """
    Generate event scenarios for testing event predictor.
    
    Event types:
    - token_unlock: Large token unlock
    - upgrade: Protocol upgrade
    - macro: Fed meeting
    - options_expiry: Monthly expiry
    """
    events = {
        'token_unlock': {
            'type': 'unlock',
            'symbol': 'ARB',
            'date': datetime.now() + timedelta(days=14),
            'impact': 'bearish',
            'severity': 8,
            'details': {
                'amount': 1.1e9,
                'percent_of_supply': 11.5,
                'value_usd': 890e6
            }
        },
        'upgrade': {
            'type': 'upgrade',
            'symbol': 'ETH',
            'date': datetime.now() + timedelta(days=30),
            'impact': 'bullish',
            'severity': 7,
            'details': {
                'name': 'Dencun Upgrade',
                'improvements': ['Lower fees', 'Higher throughput']
            }
        },
        'macro': {
            'type': 'macro',
            'symbol': 'BTC',
            'date': datetime.now() + timedelta(days=7),
            'impact': 'mixed',
            'severity': 9,
            'details': {
                'event': 'FOMC Meeting',
                'expected': 'Rate hold',
                'market_reaction': 'Volatile'
            }
        },
        'options_expiry': {
            'type': 'options_expiry',
            'symbol': 'BTC',
            'date': datetime.now() + timedelta(days=5),
            'impact': 'neutral',
            'severity': 6,
            'details': {
                'notional_value': 5e9,
                'max_pain': 95000,
                'put_call_ratio': 0.8
            }
        }
    }
    
    return events.get(event_type, events['token_unlock'])
