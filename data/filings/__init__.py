"""
Data Filings Package - Financial Filings Processing

Phase 4: Real Financial Documents Intelligence
"""

from data.filings.cache import (
    DocumentCache,
    DocumentCache as BaseDocumentCache,
    MemoryCacheBackend,
    SQLiteCacheBackend,
    CacheBackend,
    CacheEntry,
    CacheStats,
    DocumentVersion,
    VersionedDocumentCache,
    create_document_cache,
)

from data.filings.incremental import (
    IncrementalUpdater,
    UpdateConfig,
    UpdateResult,
    UpdateStatus,
    IncrementalRAGUpdater,
    create_incremental_updater,
)

__all__ = [
    # Cache
    "DocumentCache",
    "BaseDocumentCache",
    "MemoryCacheBackend",
    "SQLiteCacheBackend",
    "CacheBackend",
    "CacheEntry",
    "CacheStats",
    "DocumentVersion",
    "VersionedDocumentCache",
    "create_document_cache",
    
    # Incremental
    "IncrementalUpdater",
    "UpdateConfig",
    "UpdateResult",
    "UpdateStatus",
    "IncrementalRAGUpdater",
    "create_incremental_updater",
]