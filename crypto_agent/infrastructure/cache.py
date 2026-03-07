"""
ShufaClaw V2 — Redis Cache

This replaces the old in-memory cache (_cache = {}) with Redis.

WHY REDIS INSTEAD OF A PYTHON DICT?
1. Data survives restarts (dict is lost when you close the app)
2. Multiple services can share the same cache
3. Redis has built-in expiration (auto-cleanup of old data)
4. Much faster than SQLite for quick lookups

HOW TO USE:
    from crypto_agent.infrastructure.cache import redis_cache

    # Store something (expires in 5 minutes)
    await redis_cache.set("btc_price", 61000.50, ttl=300)

    # Retrieve it
    price = await redis_cache.get("btc_price")

    # Store JSON/dict data
    await redis_cache.set_json("market_data", {"btc": 61000, "eth": 3200})
    data = await redis_cache.get_json("market_data")
"""

import os
import json
import logging
from typing import Optional, Any
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class RedisCache:
    """Async Redis cache wrapper with simple get/set methods."""

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None

    def _get_url(self) -> str:
        host = os.getenv("REDIS_HOST", "localhost")
        port = os.getenv("REDIS_PORT", "6379")
        return f"redis://{host}:{port}/0"

    async def connect(self):
        """Connect to Redis. Call this once at startup."""
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    self._get_url(),
                    decode_responses=True,   # Return strings, not bytes
                    socket_timeout=5
                )
                # Test connection
                await self._redis.ping()
                logger.info("✅ Redis connected")
            except Exception as e:
                logger.error(f"❌ Failed to connect to Redis: {e}")
                logger.error("   Make sure Docker is running: docker-compose up -d")
                self._redis = None
                raise

    async def close(self):
        """Close Redis connection. Call this on shutdown."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis connection closed")

    async def _ensure_connected(self):
        if self._redis is None:
            await self.connect()

    # ─── Basic Operations ─────────────────────────────────────

    async def get(self, key: str) -> Optional[str]:
        """Get a string value by key. Returns None if not found or expired."""
        await self._ensure_connected()
        try:
            return await self._redis.get(key)
        except Exception as e:
            logger.warning(f"Redis GET error for '{key}': {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 300):
        """
        Store a value with optional expiration.

        Args:
            key: Cache key
            value: Value to store (will be converted to string)
            ttl: Time-to-live in seconds (default: 5 minutes)
        """
        await self._ensure_connected()
        try:
            await self._redis.set(key, str(value), ex=ttl)
        except Exception as e:
            logger.warning(f"Redis SET error for '{key}': {e}")

    async def delete(self, key: str):
        """Delete a cached value."""
        await self._ensure_connected()
        try:
            await self._redis.delete(key)
        except Exception as e:
            logger.warning(f"Redis DELETE error for '{key}': {e}")

    # ─── JSON Operations (for dicts/lists) ────────────────────

    async def get_json(self, key: str) -> Optional[Any]:
        """Get a JSON value (dict or list) by key."""
        raw = await self.get(key)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None
        return None

    async def set_json(self, key: str, value: Any, ttl: int = 300):
        """Store a dict or list as JSON."""
        await self._ensure_connected()
        try:
            await self._redis.set(key, json.dumps(value), ex=ttl)
        except Exception as e:
            logger.warning(f"Redis SET_JSON error for '{key}': {e}")

    # ─── Utility ──────────────────────────────────────────────

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        await self._ensure_connected()
        try:
            return bool(await self._redis.exists(key))
        except Exception:
            return False

    async def ttl(self, key: str) -> int:
        """Get the remaining time-to-live for a key in seconds. -1 if no expiry."""
        await self._ensure_connected()
        try:
            return await self._redis.ttl(key)
        except Exception:
            return -2

    async def flush_all(self):
        """Clear ALL cached data. Use with caution!"""
        await self._ensure_connected()
        await self._redis.flushdb()
        logger.warning("⚠️ Redis cache flushed (all data cleared)")

    async def health_check(self) -> bool:
        """Check if Redis is reachable."""
        try:
            await self._ensure_connected()
            return await self._redis.ping()
        except Exception:
            return False


# Global cache instance — import and use this throughout the app
redis_cache = RedisCache()
