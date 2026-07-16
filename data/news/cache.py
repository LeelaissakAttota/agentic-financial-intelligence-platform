"""
News Cache - High-performance caching for news articles with TTL support
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from threading import Lock
import pickle

from data.news.schemas import NewsArticle, NewsSummary

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry with metadata."""
    key: str
    value: Any
    created_at: float
    expires_at: float
    access_count: int = 0
    last_accessed: float = 0
    
    def is_expired(self) -> bool:
        return time.time() > self.expires_at
    
    def touch(self):
        self.access_count += 1
        self.last_accessed = time.time()


class NewsCache:
    """
    Thread-safe news cache with TTL and LRU eviction.
    
    Features:
    - TTL-based expiration
    - LRU eviction when max size reached
    - Separate caches for articles, summaries, and raw provider data
    - Statistics tracking
    """
    
    def __init__(
        self,
        default_ttl: int = 600,  # 10 minutes default
        max_size: int = 10000,
        cleanup_interval: int = 300  # 5 minutes
    ):
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.cleanup_interval = cleanup_interval
        
        # Separate caches for different data types
        self._articles_cache: Dict[str, CacheEntry] = {}
        self._summaries_cache: Dict[str, CacheEntry] = {}
        self._provider_cache: Dict[str, CacheEntry] = {}
        self._raw_cache: Dict[str, CacheEntry] = {}
        
        self._lock = Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "errors": 0
        }
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self):
        """Stop background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def _cleanup_loop(self):
        """Background task to clean expired entries."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    def _cleanup_expired(self):
        """Remove expired entries from all caches."""
        with self._lock:
            for cache in [self._articles_cache, self._summaries_cache, 
                         self._provider_cache, self._raw_cache]:
                expired_keys = [
                    k for k, v in cache.items() if v.is_expired()
                ]
                for key in expired_keys:
                    del cache[key]
                    self._stats["evictions"] += 1
                
                # If still over max size, evict LRU
                if len(cache) > self.max_size:
                    self._evict_lru(cache)
    
    def _evict_lru(self, cache: Dict[str, CacheEntry]):
        """Evict least recently used entries."""
        if not cache:
            return
        
        # Sort by last_accessed, evict oldest
        sorted_items = sorted(
            cache.items(), 
            key=lambda x: x[1].last_accessed
        )
        
        # Evict 20% of cache
        evict_count = max(1, len(cache) // 5)
        for key, _ in sorted_items[:evict_count]:
            del cache[key]
            self._stats["evictions"] += 1
    
    def _get_cache(self, cache_type: str) -> Dict[str, CacheEntry]:
        """Get the appropriate cache dict."""
        caches = {
            "articles": self._articles_cache,
            "summaries": self._summaries_cache,
            "provider": self._provider_cache,
            "raw": self._raw_cache
        }
        return caches.get(cache_type, self._raw_cache)
    
    def _generate_key(self, *parts) -> str:
        """Generate cache key from parts."""
        key_str = ":".join(str(p) for p in parts)
        return hashlib.sha256(key_str.encode()).hexdigest()[:32]
    
    # Article Cache Methods 
    async def get_articles(self, company: str, lookback_hours: int) -> Optional[List[NewsArticle]]:
        """Get cached articles for a company."""
        key = self._generate_key("articles", company.lower(), lookback_hours)
        return await self._get(key, "articles", list)
    
    async def set_articles(
        self, 
        company: str, 
        lookback_hours: int, 
        articles: List[NewsArticle],
        ttl: Optional[int] = None
    ):
        """Cache articles for a company."""
        key = self._generate_key("articles", company.lower(), lookback_hours)
        await self._set(key, "articles", articles, ttl or self.default_ttl)
    
    async def get_summary(self, company: str, period_hours: int) -> Optional[NewsSummary]:
        """Get cached news summary."""
        key = self._generate_key("summary", company.lower(), period_hours)
        return await self._get(key, "summaries", NewsSummary)
    
    async def set_summary(
        self, 
        company: str, 
        period_hours: int, 
        summary: NewsSummary,
        ttl: Optional[int] = None
    ):
        """Cache news summary."""
        key = self._generate_key("summary", company.lower(), period_hours)
        await self._set(key, "summaries", summary, ttl or self.default_ttl)
    
    async def get_provider_data(
        self, 
        provider: str, 
        company: str, 
        lookback_hours: int
    ) -> Optional[List[NewsArticle]]:
        """Get cached raw provider data."""
        key = self._generate_key("provider", provider, company.lower(), lookback_hours)
        return await self._get(key, "provider", list)
    
    async def set_provider_data(
        self,
        provider: str,
        company: str,
        lookback_hours: int,
        articles: List[NewsArticle],
        ttl: Optional[int] = None
    ):
        """Cache raw provider data."""
        key = self._generate_key("provider", provider, company.lower(), lookback_hours)
        await self._set(key, "provider", articles, ttl or self.default_ttl)
    
    async def get_raw(self, key: str) -> Optional[Any]:
        """Get arbitrary cached data."""
        return await self._get(key, "raw")
    
    async def set_raw(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set arbitrary cached data."""
        await self._set(key, "raw", value, ttl or self.default_ttl)
    
    async def _get(self, key: str, cache_type: str, expected_type: type) -> Optional[Any]:
        """Internal get with type checking."""
        with self._lock:
            cache = self._get_cache(cache_type)
            entry = cache.get(key)
            
            if entry is None:
                self._stats["misses"] += 1
                return None
            
            if entry.is_expired():
                del cache[key]
                self._stats["misses"] += 1
                self._stats["evictions"] += 1
                return None
            
            entry.touch()
            self._stats["hits"] += 1
            
            # Type check
            if expected_type == list and not isinstance(entry.value, list):
                logger.warning(f"Cache type mismatch for {key}: expected list, got {type(entry.value)}")
                return None
            
            return entry.value
    
    async def _set(self, key: str, cache_type: str, value: Any, ttl: int):
        """Internal set with size management."""
        with self._lock:
            cache = self._get_cache(cache_type)
            
            # Check size limit
            if len(cache) >= self.max_size:
                self._evict_lru(cache)
            
            now = time.time()
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=now + ttl,
                last_accessed=now
            )
            cache[key] = entry
    
    def invalidate_company(self, company: str):
        """Invalidate all cache entries for a company."""
        with self._lock:
            company_lower = company.lower()
            for cache in [self._articles_cache, self._summaries_cache, 
                         self._provider_cache, self._raw_cache]:
                keys_to_delete = [
                    k for k in cache.keys() 
                    if company_lower in k
                ]
                for key in keys_to_delete:
                    del cache[key]
                    self._stats["evictions"] += 1
    
    def clear(self):
        """Clear all caches."""
        with self._lock:
            self._articles_cache.clear()
            self._summaries_cache.clear()
            self._provider_cache.clear()
            self._raw_cache.clear()
            self._stats = {"hits": 0, "misses": 0, "evictions": 0, "errors": 0}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (
                self._stats["hits"] / total_requests 
                if total_requests > 0 else 0
            )
            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate": round(hit_rate, 4),
                "evictions": self._stats["evictions"],
                "errors": self._stats["errors"],
                "articles_cached": len(self._articles_cache),
                "summaries_cached": len(self._summaries_cache),
                "provider_cached": len(self._provider_cache),
                "raw_cached": len(self._raw_cache),
                "total_entries": (
                    len(self._articles_cache) + 
                    len(self._summaries_cache) + 
                    len(self._provider_cache) + 
                    len(self._raw_cache)
                )
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for cache."""
        stats = self.get_stats()
        return {
            "status": "healthy",
            "stats": stats,
            "max_size": self.max_size,
            "default_ttl": self.default_ttl
        }


# Global cache instance
_news_cache: Optional[NewsCache] = None


def get_news_cache(
    default_ttl: int = 600,
    max_size: int = 10000
) -> NewsCache:
    """Get or create global news cache."""
    global _news_cache
    if _news_cache is None:
        _news_cache = NewsCache(default_ttl=default_ttl, max_size=max_size)
    return _news_cache


async def close_news_cache():
    """Close global news cache."""
    global _news_cache
    if _news_cache:
        await _news_cache.stop()
        _news_cache = None