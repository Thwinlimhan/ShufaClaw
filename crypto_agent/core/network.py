"""
Advanced Network Utilities for ShufaClaw.
Implements Rate Limiting, Circuit Breakers, and Robust Retries.
"""

import logging
import asyncio
import time
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"      # Failing, block requests
    HALF_OPEN = "HALF_OPEN" # Testing recovery

class CircuitBreaker:
    """Prevents system cascade by stopping requests to failing services."""
    def __init__(self, name, failure_threshold=3, recovery_timeout=60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = CircuitState.CLOSED

    def record_success(self):
        if self.state != CircuitState.CLOSED:
            logger.info(f"Circuit Breaker [{self.name}] CLOSED (Recovered)")
        self.failures = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(f"Circuit Breaker [{self.name}] OPENED (Too many failures)")

    def can_request(self):
        if self.state == CircuitState.CLOSED:
            return True
        
        # Check if recovery timeout has passed
        if time.time() - self.last_failure_time > self.recovery_timeout:
            self.state = CircuitState.HALF_OPEN
            logger.info(f"Circuit Breaker [{self.name}] HALF_OPEN (Testing recovery)")
            return True
            
        return False

class RateLimiter:
    """Token bucket style rate limiter for API compliance."""
    def __init__(self, calls_per_minute):
        self.calls_per_minute = calls_per_minute
        self.interval = 60.0 / calls_per_minute
        self.last_call = 0

    async def wait(self):
        now = time.time()
        time_since_last = now - self.last_call
        if time_since_last < self.interval:
            wait_time = self.interval - time_since_last
            logger.debug(f"Rate limiter sleeping for {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        self.last_call = time.time()

# --- Registry of Breakers & Limiters ---
REGISTRY = {
    'binance': {
        'breaker': CircuitBreaker('BinanceAPI'),
        'limiter': RateLimiter(600) # 600 calls per min
    },
    'coingecko': {
        'breaker': CircuitBreaker('CoinGeckoAPI'),
        'limiter': RateLimiter(30) # Free tier coingecko is very strict
    },
    'etherscan': {
        'breaker': CircuitBreaker('EtherscanAPI'),
        'limiter': RateLimiter(5) # 5 calls per second / 300 per min
    },
    'openrouter': {
        'breaker': CircuitBreaker('OpenRouterAPI'),
        'limiter': RateLimiter(60) # 60 per min
    }
}

async def robust_fetch(service_name, fetch_func, *args, **kwargs):
    """
    Higher-order function to wrap any fetch with protection.
    """
    config = REGISTRY.get(service_name)
    if not config:
        return await fetch_func(*args, **kwargs)

    breaker = config['breaker']
    limiter = config['limiter']

    if not breaker.can_request():
        logger.warning(f"Request to {service_name} blocked by Circuit Breaker.")
        return None

    await limiter.wait()

    try:
        result = await fetch_func(*args, **kwargs)
        if result is not None:
            breaker.record_success()
            return result
        else:
            breaker.record_failure()
            return None
    except Exception as e:
        logger.error(f"Error in robust_fetch for {service_name}: {e}")
        breaker.record_failure()
        return None
