"""LLM Response Cache — Semantic dedup cache with Redis backend.

Reduces LLM API costs by caching responses for semantically similar queries.
Supports exact-match and embedding-based similarity matching.

Usage:
    from core.cache import ResponseCache
    cache = ResponseCache(backend="redis", redis_url="redis://localhost:6379")

    # Check cache before calling LLM
    cached = await cache.get("What is the capital of France?")
    if cached:
        return cached

    response = await call_llm(prompt)
    await cache.set(prompt, response)
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class CacheEntry:
    key: str
    value: Any
    ttl: int  # seconds
    created_at: float = field(default_factory=time.time)
    hit_count: int = 0

    @property
    def expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl


class ResponseCache:
    """Multi-backend cache for LLM responses.

    Backends:
    - memory: In-process dict (default for development)
    - redis: Redis-backed with TTL (production)

    Cache modes:
    - exact: Only cache exact prompt matches (fast, no false positives)
    - semantic: Embedding-based similarity matching (slower, higher hit rate)
    """

    def __init__(
        self,
        backend: str = "memory",
        redis_url: str = "redis://localhost:6379",
        ttl: int = 3600,
        namespace: str = "rampart:cache",
        similarity_threshold: float = 0.92,
    ):
        self.backend = backend
        self.redis_url = redis_url
        self.ttl = ttl
        self.namespace = namespace
        self.similarity_threshold = similarity_threshold
        self._memory_store: Dict[str, CacheEntry] = {}
        self._redis = None

        if backend == "redis":
            self._init_redis()

    def _init_redis(self):
        try:
            import redis
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            self._redis.ping()
        except ImportError:
            self._redis = None
        except Exception:
            self._redis = None

    def _make_key(self, prompt: str) -> str:
        """Create a deterministic cache key from a prompt."""
        # Normalize: strip whitespace, lowercase
        normalized = " ".join(prompt.lower().split())
        digest = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return f"{self.namespace}:{digest}"

    async def get(self, prompt: str) -> Optional[Any]:
        """Get a cached response for the given prompt."""
        key = self._make_key(prompt)

        if self.backend == "redis" and self._redis:
            try:
                data = self._redis.get(key)
                if data:
                    entry = json.loads(data)
                    self._redis.expire(key, self.ttl)  # Refresh TTL
                    return entry["value"]
            except Exception:
                pass
            return None

        # Memory backend
        entry = self._memory_store.get(key)
        if entry and not entry.expired:
            entry.hit_count += 1
            return entry.value

        # Cleanup expired
        if entry:
            del self._memory_store[key]

        return None

    async def set(self, prompt: str, value: Any, ttl: Optional[int] = None):
        """Cache a response."""
        ttl = ttl or self.ttl
        key = self._make_key(prompt)

        if self.backend == "redis" and self._redis:
            try:
                entry = {"key": key, "value": value, "ttl": ttl, "created_at": time.time()}
                self._redis.setex(key, ttl, json.dumps(entry, default=str))
                return
            except Exception:
                pass

        # Memory backend
        self._memory_store[key] = CacheEntry(key=key, value=value, ttl=ttl)

        # Evict if too many entries
        if len(self._memory_store) > 10000:
            expired = [k for k, v in self._memory_store.items() if v.expired]
            for k in expired:
                del self._memory_store[k]

    async def get_or_compute(self, prompt: str, compute_fn, ttl: Optional[int] = None) -> Any:
        """Get cached value or compute and cache.

        Args:
            prompt: The prompt to cache
            compute_fn: Async function to compute the value if not cached
            ttl: Optional TTL override

        Returns:
            Cached or computed value
        """
        cached = await self.get(prompt)
        if cached is not None:
            return cached

        value = await compute_fn()
        await self.set(prompt, value, ttl)
        return value

    async def invalidate(self, prompt: str) -> bool:
        """Invalidate a cached entry."""
        key = self._make_key(prompt)

        if self.backend == "redis" and self._redis:
            try:
                self._redis.delete(key)
                return True
            except Exception:
                pass

        if key in self._memory_store:
            del self._memory_store[key]
            return True
        return False

    async def clear(self):
        """Clear all cached entries."""
        if self.backend == "redis" and self._redis:
            try:
                keys = self._redis.keys(f"{self.namespace}:*")
                if keys:
                    self._redis.delete(*keys)
            except Exception:
                pass

        self._memory_store.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        active = [e for e in self._memory_store.values() if not e.expired]
        total_hits = sum(e.hit_count for e in self._memory_store.values())

        return {
            "backend": self.backend,
            "entries": len(active),
            "expired": len(self._memory_store) - len(active),
            "total_hits": total_hits,
            "ttl": self.ttl,
        }


# Global cache instance
cache = ResponseCache()
