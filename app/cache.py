"""
Redis cache helpers — async get/set/flush with JSON serialization.
"""

import json
import os

import redis.asyncio as aioredis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

redis_client = None


async def get_redis():
    """Get or create the Redis client singleton."""
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    return redis_client


async def cache_get(key: str):
    """Get a cached value by key, returns parsed JSON or None."""
    r = await get_redis()
    val = await r.get(key)
    return json.loads(val) if val else None


async def cache_set(key: str, value, ttl: int = 60):
    """Set a cache value with TTL (default 60 seconds)."""
    r = await get_redis()
    await r.set(key, json.dumps(value, default=str), ex=ttl)


async def cache_flush_analytics():
    """Flush all analytics cache keys."""
    r = await get_redis()
    keys = await r.keys("analytics:*")
    if keys:
        await r.delete(*keys)


async def check_redis_health() -> bool:
    """Check if Redis is reachable."""
    try:
        r = await get_redis()
        await r.ping()
        return True
    except Exception:
        return False
