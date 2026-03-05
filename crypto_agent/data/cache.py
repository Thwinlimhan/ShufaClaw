# In-memory cache for API responses
# Reduces redundant API calls within the same request cycle

from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_TTL_SECONDS = 120
DEFAULT_MAX_SIZE = 1000

class InMemoryCache:
    """Simple in-memory cache with TTL support and size limits."""
    
    def __init__(self, default_ttl_seconds: int = DEFAULT_TTL_SECONDS, 
                 max_size: int = DEFAULT_MAX_SIZE):
        """
        Initialize cache with TTL and size limits.
        
        Args:
            default_ttl_seconds: Time-to-live for cached items
            max_size: Maximum number of items to cache
        """
        if default_ttl_seconds <= 0:
            raise ValueError("TTL must be positive")
        
        if max_size <= 0:
            raise ValueError("Max size must be positive")
        
        self._cache: Dict[str, Tuple[datetime, Any]] = {}
        self.default_ttl = timedelta(seconds=default_ttl_seconds)
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if not key or not isinstance(key, str):
            logger.warning("Invalid cache key")
            return None
        
        if key not in self._cache:
            self.misses += 1
            return None
        
        cached_time, value = self._cache[key]
        
        if datetime.now() - cached_time > self.default_ttl:
            # Expired
            del self._cache[key]
            self.misses += 1
            return None
        
        self.hits += 1
        return value
    
    def set(self, key: str, value: Any):
        """
        Store value in cache with current timestamp.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        if not key or not isinstance(key, str):
            logger.warning("Invalid cache key")
            return
        
        # Evict oldest if at capacity
        if len(self._cache) >= self.max_size and key not in self._cache:
            oldest_key = min(self._cache.keys(), 
                           key=lambda k: self._cache[k][0])
            del self._cache[oldest_key]
            self.evictions += 1
            logger.debug(f"Evicted oldest cache entry: {oldest_key}")
        
        self._cache[key] = (datetime.now(), value)
    
    def delete(self, key: str) -> bool:
        """
        Delete a specific key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self):
        """Clear all cached values and reset statistics."""
        self._cache.clear()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with hits, misses, hit_rate, size, evictions
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'size': len(self._cache),
            'max_size': self.max_size,
            'evictions': self.evictions
        }
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        now = datetime.now()
        expired_keys = [
            key for key, (cached_time, _) in self._cache.items()
            if now - cached_time > self.default_ttl
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)

# Global cache instances
price_cache = InMemoryCache(default_ttl_seconds=120, max_size=500)  # 2 minutes, 500 items
market_cache = InMemoryCache(default_ttl_seconds=300, max_size=200)  # 5 minutes, 200 items
