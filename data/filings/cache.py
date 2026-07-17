"""
Document Cache for Financial Documents.

Provides caching with TTL, persistence, deduplication, and versioning
for financial documents (PDFs, HTML, etc.).
"""

import asyncio
import hashlib
import json
import logging
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, AsyncGenerator, Optional, TypeVar, Generic

import aiosqlite

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """A cached entry with metadata."""
    key: str
    value: T
    created_at: datetime
    expires_at: datetime
    version: int = 1
    tags: list[str] = field(default_factory=list)
    size_bytes: int = 0
    hit_count: int = 0
    last_accessed: Optional[datetime] = None


@dataclass
class CacheStats:
    """Cache statistics."""
    total_entries: int
    total_size_bytes: int
    hit_rate: float
    expired_entries: int
    memory_usage_mb: float
    disk_usage_mb: float


class CacheBackend(ABC):
    """Abstract cache backend."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: timedelta, tags: list[str] = None) -> None:
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    async def clear_expired(self) -> int:
        pass
    
    @abstractmethod
    async def get_stats(self) -> CacheStats:
        pass
    
    @abstractmethod
    async def close(self) -> None:
        pass


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend with LRU eviction."""
    
    def __init__(self, max_size_mb: int = 100, default_ttl: timedelta = timedelta(hours=24)):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self._cache: dict[str, CacheEntry] = {}
        self._access_order: list[str] = []
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0
    
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._cache.get(key)
            if not entry:
                self._misses += 1
                return None
            
            if datetime.now() > entry.expires_at:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                self._misses += 1
                return None
            
            # Update access stats
            entry.hit_count += 1
            entry.last_accessed = datetime.now()
            self._hits += 1
            
            # Update LRU order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            return entry.value
    
    async def set(self, key: str, value: Any, ttl: timedelta = None, tags: list[str] = None) -> None:
        async with self._lock:
            ttl = ttl or self.default_ttl
            now = datetime.now()
            expires_at = now + ttl
            
            # Estimate size
            import sys
            size_bytes = sys.getsizeof(str(value))
            
            # Evict if needed
            await self._evict_if_needed(sys.getsizeof(str(key)) + size_bytes)
            
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=expires_at,
                tags=tags or [],
                size_bytes=size_bytes
            )
            
            self._cache[key] = entry
            self._access_order.append(key)
    
    async def _evict_if_needed(self, needed_bytes: int):
        """Evict LRU entries if cache would exceed max size."""
        current_size = sum(e.size_bytes for e in self._cache.values())
        max_allowed = self.max_size_bytes - needed_bytes
        
        while current_size > max_allowed and self._access_order:
            lru_key = self._access_order.pop(0)
            entry = self._cache.pop(lru_key, None)
            if entry:
                current_size -= entry.size_bytes
    
    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return True
            return False
    
    async def clear_expired(self) -> int:
        async with self._lock:
            now = datetime.now()
            expired_keys = [
                k for k, e in self._cache.items()
                if now > e.expires_at
            ]
            for key in expired_keys:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
            return len(expired_keys)
    
    async def get_stats(self) -> CacheStats:
        async with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0
            total_size = sum(e.size_bytes for e in self._cache.values())
            
            return CacheStats(
                total_entries=len(self._cache),
                total_size_bytes=total_size,
                hit_rate=hit_rate,
                expired_entries=0,  # Not tracked in memory cache
                memory_usage_mb=total_size / (1024 * 1024),
                disk_usage_mb=0.0
            )
    
    async def close(self) -> None:
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()


class SQLiteCacheBackend(CacheBackend):
    """SQLite-based persistent cache backend with TTL and tagging."""
    
    def __init__(
        self,
        db_path: Path,
        default_ttl: timedelta = timedelta(days=30),
        max_size_mb: int = 1000,
        vacuum_interval_hours: int = 24
    ):
        self.db_path = db_path
        self.default_ttl = default_ttl
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.vacuum_interval = timedelta(hours=vacuum_interval_hours)
        self._last_vacuum = datetime.now()
        self._conn: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0
    
    async def _get_conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.db_path)
            self._conn.row_factory = aiosqlite.Row
            await self._init_schema()
        return self._conn
    
    async def _init_schema(self):
        conn = await self._get_conn()
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS cache_entries (
                key TEXT PRIMARY KEY,
                value BLOB NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                tags TEXT DEFAULT '[]',
                size_bytes INTEGER DEFAULT 0,
                hit_count INTEGER DEFAULT 0,
                last_accessed TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_entries(expires_at);
            CREATE INDEX IF NOT EXISTS idx_tags ON cache_entries(tags);
            CREATE INDEX IF NOT EXISTS idx_last_accessed ON cache_entries(last_accessed);
            
            CREATE TABLE IF NOT EXISTS cache_stats (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        await self._conn.commit()
    
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            conn = await self._get_conn()
            now = datetime.now().isoformat()
            
            cursor = await conn.execute(
                "SELECT value, expires_at FROM cache_entries WHERE key = ? AND expires_at > ?",
                (key, now)
            )
            row = await cursor.fetchone()
            
            if not row:
                self._misses += 1
                return None
            
            self._hits += 1
            
            # Update access stats
            await conn.execute(
                "UPDATE cache_entries SET hit_count = hit_count + 1, last_accessed = ? WHERE key = ?",
                (datetime.now().isoformat(), key)
            )
            await self._conn.commit()
            
            import pickle
            return pickle.loads(row['value'])
    
    async def set(self, key: str, value: Any, ttl: timedelta = None, tags: list[str] = None) -> None:
        async with self._lock:
            ttl = ttl or self.default_ttl
            now = datetime.now()
            expires_at = now + ttl
            
            import pickle
            value_bytes = pickle.dumps(value)
            size_bytes = len(value_bytes)
            
            tags_json = json.dumps(tags or [])
            
            conn = await self._get_conn()
            await conn.execute("""
                INSERT OR REPLACE INTO cache_entries 
                (key, value, created_at, expires_at, version, tags, size_bytes, hit_count, last_accessed)
                VALUES (?, ?, ?, ?, 1, ?, ?, 0, ?)
            """, (key, value_bytes, now.isoformat(), expires_at.isoformat(), 
                  tags_json, size_bytes, now.isoformat()))
            await self._conn.commit()
            
            # Check size and evict if needed
            await self._evict_if_needed()
    
    async def _evict_if_needed(self):
        conn = await self._get_conn()
        cursor = await conn.execute("SELECT SUM(size_bytes) FROM cache_entries")
        row = await cursor.fetchone()
        total_size = row[0] or 0
        
        if total_size > self.max_size_bytes:
            # Evict LRU entries
            to_remove = total_size - self.max_size_bytes + (100 * 1024 * 1024)  # Remove extra 100MB
            await conn.execute("""
                DELETE FROM cache_entries 
                WHERE key IN (
                    SELECT key FROM cache_entries 
                    ORDER BY last_accessed ASC NULLS FIRST, created_at ASC
                    LIMIT (
                        SELECT COUNT(*) FROM cache_entries 
                        WHERE size_bytes <= ?
                    )
                )
            """, (to_remove,))
            await self._conn.commit()
    
    async def delete(self, key: str) -> bool:
        async with self._lock:
            conn = await self._get_conn()
            cursor = await conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
            await self._conn.commit()
            return cursor.rowcount > 0
    
    async def clear_expired(self) -> int:
        async with self._lock:
            conn = await self._get_conn()
            now = datetime.now().isoformat()
            cursor = await conn.execute("DELETE FROM cache_entries WHERE expires_at <= ?", (now,))
            await self._conn.commit()
            
            # Vacuum if needed
            if datetime.now() - self._last_vacuum > self.vacuum_interval:
                await conn.execute("VACUUM")
                await self._conn.commit()
                self._last_vacuum = datetime.now()
            
            return cursor.rowcount
    
    async def get_stats(self) -> CacheStats:
        async with self._lock:
            conn = await self._get_conn()
            
            # Total entries
            cursor = await conn.execute("SELECT COUNT(*) FROM cache_entries")
            total_entries = (await cursor.fetchone())[0]
            
            # Total size
            cursor = await conn.execute("SELECT SUM(size_bytes) FROM cache_entries")
            total_size = (await cursor.fetchone())[0] or 0
            
            # Expired entries
            now = datetime.now().isoformat()
            cursor = await conn.execute("SELECT COUNT(*) FROM cache_entries WHERE expires_at <= ?", (datetime.now().isoformat(),))
            expired_entries = (await cursor.fetchone())[0]
            
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0
            
            return CacheStats(
                total_entries=total_entries,
                total_size_bytes=total_size,
                hit_rate=hit_rate,
                expired_entries=expired_entries,
                memory_usage_mb=0.0,
                disk_usage_mb=total_size / (1024 * 1024)
            )
    
    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None
    
    async def get_by_tag(self, tag: str) -> list[str]:
        """Get all keys with a specific tag."""
        async with self._lock:
            conn = await self._get_conn()
            cursor = await conn.execute(
                "SELECT key FROM cache_entries WHERE tags LIKE ?",
                (f'%"{tag}"%',)
            )
            return [row[0] for row in await cursor.fetchall()]
    
    async def invalidate_tag(self, tag: str) -> int:
        """Invalidate all entries with a specific tag."""
        async with self._lock:
            conn = await self._get_conn()
            cursor = await conn.execute(
                "DELETE FROM cache_entries WHERE tags LIKE ?",
                (f'%"{tag}"%',)
            )
            await self._conn.commit()
            return cursor.rowcount


class DocumentCache:
    """
    High-level document cache for financial documents.
    
    Features:
    - Multi-tier caching (memory + disk)
    - TTL with automatic expiration
    - Tag-based invalidation
    - Document versioning
    - Deduplication by content hash
    - Automatic company mapping
    """
    
    def __init__(
        self,
        memory_cache: Optional[CacheBackend] = None,
        disk_cache: Optional[CacheBackend] = None,
        default_ttl: timedelta = timedelta(days=30),
        enable_dedup: bool = True
    ):
        self.memory_cache = memory_cache or MemoryCacheBackend(max_size_mb=200)
        self.disk_cache = disk_cache or SQLiteCacheBackend(
            db_path=Path("./data/cache/documents.db"),
            max_size_mb=5000
        )
        self.default_ttl = default_ttl
        self.enable_dedup = enable_dedup
        self._dedup_index: dict[str, str] = {}  # content_hash -> cache_key
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (checks memory first, then disk)."""
        # Try memory cache first
        value = await self.memory_cache.get(key)
        if value is not None:
            return value
        
        # Try disk cache
        value = await self.disk_cache.get(key)
        if value is not None:
            # Promote to memory cache
            await self.memory_cache.set(key, value, timedelta(hours=24))
            return value
        
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: timedelta = None,
        tags: list[str] = None,
        content_hash: Optional[str] = None
    ) -> str:
        """Set value in both memory and disk cache."""
        ttl = ttl or timedelta(days=30)
        
        # Handle deduplication
        if self.enable_dedup and content_hash:
            async with asyncio.Lock():
                if content_hash in self._dedup_index:
                    # Return existing key
                    return self._dedup_index[content_hash]
                self._dedup_index[content_hash] = key
        
        # Set in both caches
        await asyncio.gather(
            self.memory_cache.set(key, value, ttl),
            self.disk_cache.set(key, value, ttl)
        )
        
        return key
    
    async def get_by_content_hash(self, content_hash: str) -> Optional[Any]:
        """Get cached value by content hash (for deduplication)."""
        async with self._lock:
            if content_hash in self._dedup_index:
                key = self._dedup_index[content_hash]
                return await self.get(key)
        return None
    
    async def set_with_dedup(
        self,
        content: bytes,
        value: Any,
        ttl: timedelta = None,
        tags: list[str] = None
    ) -> str:
        """Set value with automatic deduplication based on content hash."""
        content_hash = hashlib.sha256(content).hexdigest()
        
        # Check if already cached
        existing = await self.get_by_content_hash(content_hash)
        if existing is not None:
            logger.debug(f"Content deduplicated: {content_hash[:16]}...")
            return self._dedup_index[content_hash]
        
        # Generate new key
        key = hashlib.sha256(content).hexdigest()[:32]
        
        await self.set(key, value, ttl, tags=[], content_hash=content_hash)
        return key
    
    async def get(self, key: str) -> Optional[Any]:
        return await self.memory_cache.get(key) or await self.disk_cache.get(key)
    
    async def delete(self, key: str) -> bool:
        """Delete from both caches."""
        results = await asyncio.gather(
            self.memory_cache.delete(key),
            self.disk_cache.delete(key)
        )
        return any(results)
    
    async def invalidate_tag(self, tag: str) -> int:
        """Invalidate all entries with a specific tag."""
        # Memory cache doesn't support tag-based invalidation directly
        # Disk cache does
        return await self.disk_cache.invalidate_tag(tag)
    
    async def clear_expired(self) -> int:
        """Clear expired entries from both caches."""
        results = await asyncio.gather(
            self.memory_cache.clear_expired(),
            self.disk_cache.clear_expired()
        )
        return sum(results)
    
    async def get_stats(self) -> dict:
        """Get combined cache statistics."""
        mem_stats, disk_stats = await asyncio.gather(
            self.memory_cache.get_stats(),
            self.disk_cache.get_stats()
        )
        
        return {
            "memory": {
                "entries": mem_stats.total_entries,
                "size_mb": mem_stats.memory_usage_mb,
                "hit_rate": mem_stats.hit_rate
            },
            "disk": {
                "entries": disk_stats.total_entries,
                "size_mb": disk_stats.disk_usage_mb,
                "hit_rate": disk_stats.hit_rate
            },
            "combined": {
                "total_entries": mem_stats.total_entries + disk_stats.total_entries,
                "total_size_mb": mem_stats.memory_usage_mb + disk_stats.disk_usage_mb
            }
        }
    
    async def close(self):
        """Close both cache backends."""
        await asyncio.gather(
            self.memory_cache.close(),
            self.disk_cache.close()
        )


@dataclass
class DocumentVersion:
    """Document version metadata."""
    version: int
    content_hash: str
    created_at: datetime
    created_by: str
    changelog: str = ""
    previous_hash: Optional[str] = None


class VersionedDocumentCache:
    """
    High-level document cache with versioning, metadata, and automatic company mapping.
    
    Features:
    - Content-addressable storage with deduplication
    - Document versioning with history
    - Automatic company mapping from ticker/CIK
    - Metadata enrichment
    - RAG-ready chunking integration
    """
    
    def __init__(
        self,
        cache: Optional[DocumentCache] = None,
        version_dir: Path = Path("./data/filings/versions"),
        company_mapping_file: Optional[Path] = None
    ):
        self.cache = cache or DocumentCache()
        self.version_dir = version_dir
        self.version_dir.mkdir(parents=True, exist_ok=True)
        self._company_mapping: dict[str, str] = {}  # ticker/cik -> company_name
        self._company_mapping_file = company_mapping_file
        self._lock = asyncio.Lock()
    
    async def store_document(
        self,
        content: bytes,
        metadata: dict[str, Any],
        company_ticker: Optional[str] = None,
        company_cik: Optional[str] = None,
        version_changelog: str = ""
    ) -> str:
        """
        Store a document with versioning and metadata.
        
        Returns the document key.
        """
        # Generate content hash
        content_hash = hashlib.sha256(content).hexdigest()
        
        # Check if already exists
        existing_key = await self.cache.get_by_content_hash(content_hash)
        if existing_key:
            # Create new version
            return await self._create_new_version(
                existing_key, content, content_hash, metadata, version_changelog
            )
        
        # Generate new key
        key = hashlib.sha256(content).hexdigest()[:32]
        
        # Enrich metadata
        enriched_metadata = {
            **metadata,
            "content_hash": content_hash,
            "stored_at": datetime.now().isoformat(),
            "size_bytes": len(content)
        }
        
        # Auto-map company
        if company_ticker:
            company_name = await self._resolve_company(company_ticker)
            metadata["company_ticker"] = company_ticker
            metadata["company_name"] = company_name
        
        if company_cik:
            metadata["company_cik"] = company_cik
        
        # Store content
        key = await self.cache.set_with_dedup(content, {
            "content": content,
            "metadata": enriched_metadata
        })
        
        # Create initial version
        await self._save_version(key, 1, content_hash, "Initial version")
        
        # Save to versioned storage
        await self._save_document_file(key, content, enriched_metadata)
        
        return key
    
    async def _create_new_version(
        self,
        existing_key: str,
        new_content: bytes,
        new_hash: str,
        metadata: dict,
        changelog: str
    ) -> str:
        """Create a new version of an existing document."""
        # Get current version
        version_file = self.version_dir / f"{existing_key}_versions.json"
        versions = []
        if version_file.exists():
            with open(version_file) as f:
                versions = json.load(f)
        
        new_version = len(versions) + 1
        previous_hash = versions[-1]["content_hash"] if versions else None
        
        # Save new version
        await self._save_version(existing_key, new_version, new_hash, changelog)
        
        # Update cache
        await self.cache.set(
            existing_key,
            {"content": new_content, "metadata": metadata},
            content_hash=new_hash
        )
        
        return existing_key
    
    async def _save_version(
        self,
        key: str,
        version: int,
        content_hash: str,
        changelog: str
    ):
        """Save a document version."""
        version_file = self.version_dir / f"{key}_versions.json"
        versions = []
        if version_file.exists():
            with open(version_file) as f:
                versions = json.load(f)
        
        versions.append({
            "version": version,
            "content_hash": version,
            "created_at": datetime.now().isoformat(),
            "changelog": changelog,
            "previous_hash": versions[-1]["content_hash"] if versions else None
        })
        
        with open(version_file, 'w') as f:
            json.dump(versions, f, indent=2)
    
    async def _save_document_file(self, key: str, content: bytes, metadata: dict):
        """Save document to versioned file storage."""
        doc_dir = self.version_dir / key
        doc_dir.mkdir(exist_ok=True)
        
        # Save content
        content_path = doc_dir / "content.bin"
        with open(content_path, 'wb') as f:
            f.write(content)
        
        # Save metadata
        meta_path = doc_dir / "metadata.json"
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, default=str, indent=2)
    
    async def get_document(self, key: str) -> Optional[tuple[bytes, dict]]:
        """Get document content and metadata."""
        result = await self.cache.get(key)
        if result:
            return result["content"], result["metadata"]
        return None
    
    async def get_document_metadata(self, key: str) -> Optional[dict]:
        """Get document metadata without content."""
        result = await self.cache.get(key)
        if result:
            return result["metadata"]
        return None
    
    async def get_version_history(self, key: str) -> list[dict]:
        """Get version history for a document."""
        version_file = self.version_dir / f"{key}_versions.json"
        if version_file.exists():
            with open(version_file) as f:
                return json.load(f)
        return []
    
    async def get_document_versions(self, key: str) -> list[tuple[int, bytes, dict]]:
        """Get all versions of a document."""
        versions = await self.get_version_history(key)
        result = []
        for v in versions:
            ver_file = self.version_dir / key / f"v{v['version']}.bin"
            if ver_file.exists():
                with open(ver_file, 'rb') as f:
                    content = f.read()
                meta_file = self.version_dir / key / f"v{v['version']}_meta.json"
                metadata = {}
                if meta_file.exists():
                    with open(meta_file) as f:
                        metadata = json.load(f)
                results.append((v['version'], content, metadata))
        return result
    
    async def _resolve_company(self, ticker: str) -> Optional[str]:
        """Resolve ticker to company name."""
        async with self._lock:
            if ticker in self._company_mapping:
                return self._company_mapping[ticker]
            
            # Try to load from file
            if self._company_mapping_file and self._company_mapping_file.exists():
                with open(self._company_mapping_file) as f:
                    self._company_mapping = json.load(f)
                if ticker in self._company_mapping:
                    return self._company_mapping[ticker]
            
            return None
    
    async def add_company_mapping(self, ticker: str, company_name: str, cik: Optional[str] = None):
        """Add company ticker -> name mapping."""
        async with self._lock:
            self._company_mapping[ticker] = company_name
            if cik:
                self._company_mapping[cik] = company_name
            
            if self._company_mapping_file:
                with open(self._company_mapping_file, 'w') as f:
                    json.dump(self._company_mapping, f, indent=2)
    
    async def get_by_company(self, company_ticker: str) -> list[str]:
        """Get all document keys for a company."""
        # This would need a reverse index in production
        # For now, return empty list
        return []
    
    async def cleanup_old_versions(self, key: str, keep_versions: int = 10):
        """Remove old document versions beyond keep_versions."""
        versions = await self.get_version_history(key)
        if len(versions) > keep_versions:
            to_remove = versions[:-keep_versions]
            for v in to_remove:
                ver_file = self.version_dir / key / f"v{v['version']}.bin"
                if ver_file.exists():
                    ver_file.unlink()
                meta_file = self.version_dir / key / f"v{v['version']}_meta.json"
                if meta_file.exists():
                    meta_file.unlink()
                
                # Remove from version history
                versions = [v for v in versions if v not in to_remove]
                version_file = self.version_dir / f"{key}_versions.json"
                with open(version_file, 'w') as f:
                    json.dump(versions, f, indent=2)
    
    async def get_stats(self) -> dict:
        """Get cache statistics."""
        return await self.cache.get_stats()

    async def close(self):
        """Close the underlying cache."""
        await self.cache.close()


# Factory functions
async def create_document_cache(
    cache_dir: Path = Path("./data/cache/documents"),
    version_dir: Path = Path("./data/filings/versions"),
    company_mapping_file: Optional[Path] = None
) -> VersionedDocumentCache:
    """Create and initialize document cache."""
    memory_cache = MemoryCacheBackend(max_size_mb=200)
    disk_cache = SQLiteCacheBackend(
        db_path=cache_dir / "documents.db",
        max_size_mb=5000
    )
    
    base_cache = DocumentCache(
        memory_cache=memory_cache,
        disk_cache=disk_cache,
        default_ttl=timedelta(days=90),
        enable_dedup=True
    )
    
    doc_cache = VersionedDocumentCache(
        cache=base_cache,
        version_dir=Path("./data/filings/versions"),
        company_mapping_file=Path("./data/company_mapping.json")
    )
    
    # Initialize with some default company mappings
    default_mappings = {
        "AAPL": "Apple Inc.",
        "MSFT": "Microsoft Corporation",
        "GOOGL": "Alphabet Inc.",
        "GOOG": "Alphabet Inc.",
        "AMZN": "Amazon.com Inc.",
        "TSLA": "Tesla Inc.",
        "NVDA": "NVIDIA Corporation",
        "META": "Meta Platforms Inc.",
        "NFLX": "Netflix Inc.",
        "JPM": "JPMorgan Chase & Co.",
        "BAC": "Bank of America Corporation",
        "WFC": "Wells Fargo & Company",
        "GS": "Goldman Sachs Group Inc.",
        "MS": "Morgan Stanley",
        "BRK.A": "Berkshire Hathaway Inc.",
        "BRK.B": "Berkshire Hathaway Inc.",
        "JNJ": "Johnson & Johnson",
        "PFE": "Pfizer Inc.",
        "MRK": "Merck & Co. Inc.",
        "UNH": "UnitedHealth Group Inc.",
        "CVX": "Chevron Corporation",
        "XOM": "Exxon Mobil Corporation",
        "KO": "The Coca-Cola Company",
        "PEP": "PepsiCo Inc.",
        "WMT": "Walmart Inc.",
        "HD": "The Home Depot Inc.",
        "DIS": "The Walt Disney Company",
        "V": "Visa Inc.",
        "MA": "Mastercard Inc.",
        "INTC": "Intel Corporation",
        "AMD": "Advanced Micro Devices Inc.",
        "CRM": "Salesforce Inc.",
        "ADBE": "Adobe Inc.",
        "ORCL": "Oracle Corporation",
        "CSCO": "Cisco Systems Inc.",
        "IBM": "International Business Machines Corp.",
        "QCOM": "QUALCOMM Inc.",
        "TXN": "Texas Instruments Inc.",
        "AVGO": "Broadcom Inc.",
        "COST": "Costco Wholesale Corporation",
        "PYPL": "PayPal Holdings Inc.",
        "NKE": "Nike Inc.",
        "MCD": "McDonald's Corporation",
        "SBUX": "Starbucks Corporation",
        "T": "AT&T Inc.",
        "VZ": "Verizon Communications Inc.",
        "TMUS": "T-Mobile US Inc.",
    }
    
    for ticker, name in default_mappings.items():
        await doc_cache.add_company_mapping(ticker, name)
    
    return VersionedDocumentCache(
        cache=base_cache,
        version_dir=Path("./data/filings/versions"),
        company_mapping_file=Path("./data/company_mapping.json")
    )


# Export all
__all__ = [
    "DocumentCache",
    "DocumentCache",  # base cache
    "MemoryCacheBackend",
    "SQLiteCacheBackend",
    "CacheBackend",
    "CacheEntry",
    "CacheStats",
    "DocumentVersion",
    "VersionedDocumentCache",
    "create_document_cache",
]