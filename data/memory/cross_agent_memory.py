"""
Cross-Agent Memory Module - Phase 5: Knowledge Persistence & Advanced Analytics

Provides shared memory and knowledge sharing across all agents in the system.
"""

import asyncio
import logging
import json
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

import asyncpg
import numpy as np

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    """Types of memory entries."""
    FACT = "fact"                    # Verified factual information
    ANALYSIS = "analysis"            # Analytical conclusions
    INSIGHT = "insight"              # Strategic insights
    OBSERVATION = "observation"      # Raw observations
    CONCLUSION = "conclusion"        # Final conclusions
    RECOMMENDATION = "recommendation"  # Action recommendations
    PATTERN = "pattern"              # Detected patterns
    RISK = "risk"                    # Risk assessments
    OPPORTUNITY = "opportunity"      # Identified opportunities


class MemorySource(str, Enum):
    """Source of memory entry."""
    NEWS_AGENT = "news_agent"
    MARKET_AGENT = "market_agent"
    FINANCIAL_REPORT_AGENT = "financial_report_agent"
    SENTIMENT_AGENT = "sentiment_agent"
    RISK_AGENT = "risk_agent"
    COMPETITOR_AGENT = "competitor_agent"
    INVESTMENT_SUMMARY_AGENT = "investment_summary_agent"
    MANAGER_AGENT = "manager_agent"
    USER = "user"
    EXTERNAL = "external"
    SYSTEM = "system"


class MemoryScope(str, Enum):
    """Scope of memory applicability."""
    GLOBAL = "global"                    # Applies to all companies/contexts
    COMPANY = "company"                  # Specific to a company
    SECTOR = "sector"                    # Specific to a sector
    PORTFOLIO = "portfolio"              # Specific to a portfolio
    MARKET = "market"                    # Market-wide
    USER = "user"                        # User-specific


@dataclass
class MemoryEntry:
    """A single memory entry in the cross-agent memory system."""
    id: str = field(default_factory=lambda: str(uuid4()))
    content: str = ""
    memory_type: MemoryType = MemoryType.FACT
    source: MemorySource = MemorySource.SYSTEM
    scope: MemoryScope = MemoryScope.GLOBAL
    # Context keys
    company_id: str = ""
    sector: str = ""
    portfolio_id: str = ""
    symbols: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    # Quality
    confidence: float = 1.0
    credibility: float = 1.0
    verified: bool = False
    # Metadata
    context: dict = field(default_factory=dict)
    source_metadata: dict = field(default_factory=dict)
    # Lifecycle
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: Optional[datetime] = None
    access_count: int = 0
    expires_at: Optional[datetime] = None
    is_active: bool = True
    # Relationships
    references: list[str] = field(default_factory=list)  # IDs of referenced memories
    related_to: list[str] = field(default_factory=list)  # IDs of related memories
    supersedes: Optional[str] = None  # ID of memory this supersedes
    superseded_by: Optional[str] = None  # ID of memory that supersedes this
    
    def access(self) -> None:
        """Record access to this memory."""
        self.accessed_at = datetime.utcnow()
        self.access_count += 1
    
    def is_expired(self) -> bool:
        """Check if memory has expired."""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "source": self.source.value,
            "scope": self.scope.value,
            "company_id": self.company_id,
            "sector": self.sector,
            "portfolio_id": self.portfolio_id,
            "symbols": self.symbols,
            "tags": self.tags,
            "confidence": self.confidence,
            "credibility": self.credibility,
            "verified": self.verified,
            "context": self.context,
            "source_metadata": self.source_metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat() if self.accessed_at else None,
            "access_count": self.access_count,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "references": self.references,
            "related_to": self.related_to,
            "supersedes": self.supersedes,
            "superseded_by": self.superseded_by
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MemoryEntry":
        entry = cls(
            id=data.get("id", str(uuid4())),
            content=data.get("content", ""),
            memory_type=MemoryType(data.get("memory_type", "fact")),
            source=MemorySource(data.get("source", "system")),
            scope=MemoryScope(data.get("scope", "global")),
            company_id=data.get("company_id", ""),
            sector=data.get("sector", ""),
            portfolio_id=data.get("portfolio_id", ""),
            symbols=data.get("symbols", []),
            tags=data.get("tags", []),
            confidence=data.get("confidence", 1.0),
            credibility=data.get("credibility", 1.0),
            verified=data.get("verified", False),
            context=data.get("context", {}),
            source_metadata=data.get("source_metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
            accessed_at=datetime.fromisoformat(data["accessed_at"]) if data.get("accessed_at") else None,
            access_count=data.get("access_count", 0),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            is_active=data.get("is_active", True),
            references=data.get("references", []),
            related_to=data.get("related_to", []),
            supersedes=data.get("supersedes"),
            superseded_by=data.get("superseded_by")
        )
        return entry


class MemoryBackend(ABC):
    """Abstract backend for cross-agent memory storage."""
    
    @abstractmethod
    async def connect(self) -> None:
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        pass
    
    @abstractmethod
    async def store(self, entry: MemoryEntry) -> None:
        pass
    
    @abstractmethod
    async def get(self, memory_id: str) -> Optional[MemoryEntry]:
        pass
    
    @abstractmethod
    async def find(
        self,
        query: str = "",
        memory_type: MemoryType = None,
        source: MemorySource = None,
        scope: MemoryScope = None,
        company_id: str = None,
        sector: str = None,
        portfolio_id: str = None,
        symbols: list[str] = None,
        tags: list[str] = None,
        min_confidence: float = 0.0,
        verified_only: bool = False,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> list[MemoryEntry]:
        pass
    
    @abstractmethod
    async def update(self, entry: MemoryEntry) -> None:
        pass
    
    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        pass
    
    @abstractmethod
    async def get_stats(self) -> dict:
        pass


class PostgresMemoryBackend(MemoryBackend):
    """PostgreSQL backend for cross-agent memory storage."""
    
    def __init__(self, dsn: str, pool_size: int = 10):
        self.dsn = dsn
        self.pool_size = pool_size
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(
            self.dsn,
            min_size=2,
            max_size=self.pool_size,
        )
        await self._init_schema()
    
    async def disconnect(self) -> None:
        if self.pool:
            await self.pool.close()
    
    async def _init_schema(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS cross_agent_memory (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    memory_type TEXT NOT NULL DEFAULT 'fact',
                    source TEXT NOT NULL DEFAULT 'system',
                    scope TEXT NOT NULL DEFAULT 'global',
                    company_id TEXT,
                    sector TEXT,
                    portfolio_id TEXT,
                    symbols TEXT[] DEFAULT '{}',
                    tags TEXT[] DEFAULT '{}',
                    confidence REAL NOT NULL DEFAULT 1.0,
                    credibility REAL NOT NULL DEFAULT 1.0,
                    verified BOOLEAN NOT NULL DEFAULT FALSE,
                    context JSONB DEFAULT '{}',
                    source_metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    accessed_at TIMESTAMPTZ,
                    access_count INTEGER NOT NULL DEFAULT 0,
                    expires_at TIMESTAMPTZ,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    references TEXT[] DEFAULT '{}',
                    related_to TEXT[] DEFAULT '{}',
                    supersedes TEXT,
                    superseded_by TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_memory_company ON cross_agent_memory(company_id);
                CREATE INDEX IF NOT EXISTS idx_memory_sector ON cross_agent_memory(sector);
                CREATE INDEX IF NOT EXISTS idx_memory_portfolio ON cross_agent_memory(portfolio_id);
                CREATE INDEX IF NOT EXISTS idx_memory_symbols ON cross_agent_memory USING GIN(symbols);
                CREATE INDEX IF NOT EXISTS idx_memory_tags ON cross_agent_memory USING GIN(tags);
                CREATE INDEX IF NOT EXISTS idx_memory_type ON cross_agent_memory(memory_type);
                CREATE INDEX IF NOT EXISTS idx_memory_source ON cross_agent_memory(source);
                CREATE INDEX IF NOT EXISTS idx_memory_scope ON cross_agent_memory(scope);
                CREATE INDEX IF NOT EXISTS idx_memory_confidence ON cross_agent_memory(confidence);
                CREATE INDEX IF NOT EXISTS idx_memory_verified ON cross_agent_memory(verified);
                CREATE INDEX IF NOT EXISTS idx_memory_active ON cross_agent_memory(is_active);
                CREATE INDEX IF NOT EXISTS idx_memory_expires ON cross_agent_memory(expires_at);
                CREATE INDEX IF NOT EXISTS idx_memory_created ON cross_agent_memory(created_at);
                
                -- Full-text search
                ALTER TABLE cross_agent_memory 
                ADD COLUMN IF NOT EXISTS search_vector tsvector 
                GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;
                
                CREATE INDEX IF NOT EXISTS idx_memory_search ON cross_agent_memory USING GIN(search_vector);
                
                CREATE TABLE IF NOT EXISTS memory_access_log (
                    id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL REFERENCES cross_agent_memory(id) ON DELETE CASCADE,
                    agent_name TEXT NOT NULL,
                    access_type TEXT NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                );
                
                CREATE INDEX IF NOT EXISTS idx_access_memory ON memory_access_log(memory_id);
                CREATE INDEX IF NOT EXISTS idx_access_agent ON memory_access_log(agent_name);
                CREATE INDEX IF NOT EXISTS idx_access_timestamp ON memory_access_log(timestamp);
                
                CREATE TABLE IF NOT EXISTS memory_links (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL REFERENCES cross_agent_memory(id) ON DELETE CASCADE,
                    target_id TEXT NOT NULL REFERENCES cross_agent_memory(id) ON DELETE CASCADE,
                    link_type TEXT NOT NULL,
                    strength REAL NOT NULL DEFAULT 1.0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}',
                    UNIQUE(source_id, target_id, link_type)
                );
                
                CREATE INDEX IF NOT EXISTS idx_links_source ON memory_links(source_id);
                CREATE INDEX IF NOT EXISTS idx_links_target ON memory_links(target_id);
                CREATE INDEX IF NOT EXISTS idx_links_type ON memory_links(link_type);
            """)
    
    async def store(self, entry: MemoryEntry) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO cross_agent_memory (id, content, memory_type, source, scope,
                                               company_id, sector, portfolio_id, symbols, tags,
                                               confidence, credibility, verified, context, source_metadata,
                                               created_at, updated_at, accessed_at, access_count,
                                               expires_at, is_active, references, related_to, supersedes, superseded_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    memory_type = EXCLUDED.memory_type,
                    source = EXCLUDED.source,
                    scope = EXCLUDED.scope,
                    company_id = EXCLUDED.company_id,
                    sector = EXCLUDED.sector,
                    portfolio_id = EXCLUDED.portfolio_id,
                    symbols = EXCLUDED.symbols,
                    tags = EXCLUDED.tags,
                    confidence = EXCLUDED.confidence,
                    credibility = EXCLUDED.credibility,
                    verified = EXCLUDED.verified,
                    context = EXCLUDED.context,
                    source_metadata = EXCLUDED.source_metadata,
                    updated_at = EXCLUDED.updated_at,
                    accessed_at = EXCLUDED.accessed_at,
                    access_count = EXCLUDED.access_count,
                    expires_at = EXCLUDED.expires_at,
                    is_active = EXCLUDED.is_active,
                    references = EXCLUDED.references,
                    related_to = EXCLUDED.related_to,
                    supersedes = EXCLUDED.supersedes,
                    superseded_by = EXCLUDED.superseded_by
            """, entry.id, entry.content, entry.memory_type.value, entry.source.value,
               entry.scope.value, entry.company_id, entry.sector, entry.portfolio_id,
               entry.symbols, entry.tags, entry.confidence, entry.credibility,
               entry.verified, json.dumps(entry.context), json.dumps(entry.source_metadata),
               entry.created_at, entry.updated_at, entry.accessed_at, entry.access_count,
               entry.expires_at, entry.is_active, entry.references, entry.related_to,
               entry.supersedes, entry.superseded_by)
    
    async def get(self, memory_id: str) -> Optional[MemoryEntry]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM cross_agent_memory WHERE id = $1", memory_id)
            if not row:
                return None
            return self._row_to_entry(row)
    
    async def find(
        self,
        query: str = "",
        memory_type: MemoryType = None,
        source: MemorySource = None,
        scope: MemoryScope = None,
        company_id: str = None,
        sector: str = None,
        portfolio_id: str = None,
        symbols: list[str] = None,
        tags: list[str] = None,
        min_confidence: float = 0.0,
        verified_only: bool = False,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> list[MemoryEntry]:
        conditions = []
        params = []
        
        if query:
            params.append(query)
            conditions.append(f"search_vector @@ plainto_tsquery('english', ${len(params)})")
        
        if memory_type:
            params.append(memory_type.value)
            conditions.append(f"memory_type = ${len(params)}")
        
        if source:
            params.append(source.value)
            conditions.append(f"source = ${len(params)}")
        
        if scope:
            params.append(scope.value)
            conditions.append(f"scope = ${len(params)}")
        
        if company_id:
            params.append(company_id)
            conditions.append(f"company_id = ${len(params)}")
        
        if sector:
            params.append(sector)
            conditions.append(f"sector = ${len(params)}")
        
        if portfolio_id:
            params.append(portfolio_id)
            conditions.append(f"portfolio_id = ${len(params)}")
        
        if symbols:
            params.append(symbols)
            conditions.append(f"symbols && ${len(params)}")
        
        if tags:
            params.append(tags)
            conditions.append(f"tags && ${len(params)}")
        
        params.append(min_confidence)
        conditions.append(f"confidence >= ${len(params)}")
        
        if verified_only:
            conditions.append("verified = TRUE")
        
        if active_only:
            conditions.append("is_active = TRUE")
            conditions.append("(expires_at IS NULL OR expires_at > NOW())")
        
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        params.extend([limit, offset])
        
        query_sql = f"""
            SELECT * FROM cross_agent_memory 
            {where}
            ORDER BY 
                CASE WHEN $1 != '' THEN ts_rank(search_vector, plainto_tsquery('english', $1)) ELSE 0 END DESC,
                confidence DESC, created_at DESC
            LIMIT ${len(params)-1} OFFSET ${len(params)}
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query_sql, *params)
            return [self._row_to_entry(row) for row in rows]
    
    async def update(self, entry: MemoryEntry) -> None:
        entry.updated_at = datetime.utcnow()
        await self.store(entry)
    
    async def delete(self, memory_id: str) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM cross_agent_memory WHERE id = $1", memory_id)
            return result != "DELETE 0"
    
    async def get_stats(self) -> dict:
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_memories,
                    COUNT(*) FILTER (WHERE is_active) as active_memories,
                    COUNT(*) FILTER (WHERE verified) as verified_memories,
                    COUNT(DISTINCT company_id) as companies_covered,
                    COUNT(DISTINCT sector) as sectors_covered,
                    COUNT(DISTINCT source) as sources_count,
                    AVG(confidence) as avg_confidence,
                    AVG(credibility) as avg_credibility,
                    COUNT(*) FILTER (WHERE memory_type = 'fact') as facts,
                    COUNT(*) FILTER (WHERE memory_type = 'analysis') as analyses,
                    COUNT(*) FILTER (WHERE memory_type = 'insight') as insights,
                    COUNT(*) FILTER (WHERE memory_type = 'conclusion') as conclusions,
                    COUNT(*) FILTER (WHERE memory_type = 'recommendation') as recommendations,
                    COUNT(*) FILTER (WHERE memory_type = 'pattern') as patterns,
                    COUNT(*) FILTER (WHERE memory_type = 'risk') as risks,
                    COUNT(*) FILTER (WHERE memory_type = 'opportunity') as opportunities
                FROM cross_agent_memory
            """)
            return dict(stats) if stats else {}
    
    def _row_to_entry(self, row) -> MemoryEntry:
        return MemoryEntry(
            id=row["id"],
            content=row["content"],
            memory_type=MemoryType(row["memory_type"]),
            source=MemorySource(row["source"]),
            scope=MemoryScope(row["scope"]),
            company_id=row["company_id"] or "",
            sector=row["sector"] or "",
            portfolio_id=row["portfolio_id"] or "",
            symbols=row["symbols"] or [],
            tags=row["tags"] or [],
            confidence=row["confidence"],
            credibility=row["credibility"],
            verified=row["verified"],
            context=row["context"],
            source_metadata=row["source_metadata"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            accessed_at=row["accessed_at"],
            access_count=row["access_count"],
            expires_at=row["expires_at"],
            is_active=row["is_active"],
            references=row["references"] or [],
            related_to=row["related_to"] or [],
            supersedes=row["supersedes"],
            superseded_by=row["superseded_by"]
        )


class CrossAgentMemory:
    """
    Cross-agent memory system for sharing knowledge across all agents.
    Provides storage, retrieval, and intelligent querying of agent memories.
    """
    
    def __init__(self, backend: MemoryBackend):
        self.backend = backend
        self._cache: dict[str, MemoryEntry] = {}
        self._cache_ttl = 300  # 5 minutes
    
    async def initialize(self) -> None:
        await self.backend.connect()
    
    async def close(self) -> None:
        await self.backend.disconnect()
    
    # Core memory operations
    async def remember(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.FACT,
        source: MemorySource = MemorySource.SYSTEM,
        scope: MemoryScope = MemoryScope.GLOBAL,
        company_id: str = "",
        sector: str = "",
        portfolio_id: str = "",
        symbols: list[str] = None,
        tags: list[str] = None,
        confidence: float = 1.0,
        credibility: float = 1.0,
        verified: bool = False,
        context: dict = None,
        source_metadata: dict = None,
        expires_at: datetime = None,
        references: list[str] = None,
        related_to: list[str] = None,
        supersedes: str = None
    ) -> str:
        """Store a new memory entry."""
        entry = MemoryEntry(
            content=content,
            memory_type=memory_type,
            source=source,
            scope=scope,
            company_id=company_id,
            sector=sector,
            portfolio_id=portfolio_id,
            symbols=symbols or [],
            tags=tags or [],
            confidence=confidence,
            credibility=credibility,
            verified=verified,
            context=context or {},
            source_metadata=source_metadata or {},
            expires_at=expires_at,
            references=references or [],
            related_to=related_to or [],
            supersedes=supersedes
        )
        
        # Handle superseding
        if supersedes:
            old_entry = await self.backend.get(supersedes)
            if old_entry:
                old_entry.superseded_by = entry.id
                old_entry.is_active = False
                await self.backend.update(old_entry)
        
        await self.backend.store(entry)
        self._cache[entry.id] = entry
        return entry.id
    
    async def recall(
        self,
        memory_id: str,
        agent_name: str = ""
    ) -> Optional[MemoryEntry]:
        """Retrieve a specific memory by ID."""
        entry = self._cache.get(memory_id)
        if not entry:
            entry = await self.backend.get(memory_id)
            if entry:
                self._cache[memory_id] = entry
        
        if entry:
            entry.access()
            await self.backend.update(entry)
            # Log access
            await self._log_access(memory_id, agent_name, "recall")
        
        return entry
    
    async def search(
        self,
        query: str = "",
        **filters
    ) -> list[MemoryEntry]:
        """Search memories with various filters."""
        entries = await self.backend.find(query=query, **filters)
        return entries
    
    async def get_company_knowledge(
        self,
        company_id: str,
        memory_type: MemoryType = None,
        limit: int = 50
    ) -> list[MemoryEntry]:
        """Get all knowledge for a specific company."""
        return await self.backend.find(
            company_id=company_id,
            memory_type=memory_type,
            limit=limit
        )
    
    async def get_sector_knowledge(
        self,
        sector: str,
        memory_type: MemoryType = None,
        limit: int = 50
    ) -> list[MemoryEntry]:
        """Get all knowledge for a specific sector."""
        return await self.backend.find(
            sector=sector,
            memory_type=memory_type,
            limit=limit
        )
    
    async def get_portfolio_knowledge(
        self,
        portfolio_id: str,
        memory_type: MemoryType = None,
        limit: int = 50
    ) -> list[MemoryEntry]:
        """Get all knowledge for a specific portfolio."""
        return await self.backend.find(
            portfolio_id=portfolio_id,
            memory_type=memory_type,
            limit=limit
        )
    
    async def get_verified_facts(
        self,
        company_id: str = None,
        sector: str = None,
        limit: int = 50
    ) -> list[MemoryEntry]:
        """Get verified factual information."""
        return await self.backend.find(
            company_id=company_id,
            sector=sector,
            memory_type=MemoryType.FACT,
            verified_only=True,
            limit=limit
        )
    
    async def get_recent_insights(
        self,
        company_id: str = None,
        hours: int = 24,
        limit: int = 20
    ) -> list[MemoryEntry]:
        """Get recent insights and analyses."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        entries = await self.backend.find(
            company_id=company_id,
            memory_type=MemoryType.INSIGHT,
            limit=limit * 2  # Get more to filter by date
        )
        return [e for e in entries if e.created_at >= cutoff][:limit]
    
    async def find_related_memories(
        self,
        memory_id: str,
        max_depth: int = 2
    ) -> list[MemoryEntry]:
        """Find memories related to a given memory."""
        entry = await self.recall(memory_id)
        if not entry:
            return []
        
        related = []
        visited = set()
        to_visit = [(memory_id, 0)]
        
        while to_visit:
            current_id, depth = to_visit.pop(0)
            if current_id in visited or depth >= max_depth:
                continue
            visited.add(current_id)
            
            current = await self.recall(current_id)
            if current:
                for rel_id in current.related_to + current.references:
                    if rel_id not in visited:
                        to_visit.append((rel_id, depth + 1))
                        rel_entry = await self.recall(rel_id)
                        if rel_entry:
                            related.append(rel_entry)
        
        return related
    
    async def consolidate_memories(
        self,
        memory_ids: list[str],
        consolidated_content: str,
        consolidated_type: MemoryType = MemoryType.CONCLUSION
    ) -> str:
        """Consolidate multiple memories into a single conclusion."""
        if not memory_ids:
            raise ValueError("No memories to consolidate")
        
        # Get all memories
        memories = []
        for mid in memory_ids:
            entry = await self.recall(mid)
            if entry:
                memories.append(entry)
        
        if not memories:
            raise ValueError("No valid memories found")
        
        # Create consolidated memory
        new_id = await self.remember(
            content=consolidated_content,
            memory_type=consolidated_type,
            source=MemorySource.SYSTEM,
            scope=memories[0].scope,
            company_id=memories[0].company_id,
            sector=memories[0].sector,
            portfolio_id=memories[0].portfolio_id,
            symbols=list(set(s for m in memories for s in m.symbols)),
            tags=list(set(t for m in memories for t in m.tags)),
            confidence=np.mean([m.confidence for m in memories]),
            credibility=np.mean([m.credibility for m in memories]),
            verified=all(m.verified for m in memories),
            context={
                "consolidated_from": memory_ids,
                "consolidation_count": len(memories),
                "sources": list(set(m.source.value for m in memories))
            },
            references=memory_ids
        )
        
        # Mark original memories as superseded
        for mid in memory_ids:
            entry = await self.recall(mid)
            if entry:
                entry.superseded_by = new_id
                entry.is_active = False
                await self.backend.update(entry)
        
        return new_id
    
    async def link_memories(
        self,
        source_id: str,
        target_id: str,
        link_type: str = "related",
        strength: float = 1.0
    ) -> bool:
        """Create a bidirectional link between memories."""
        source = await self.recall(source_id)
        target = await self.recall(target_id)
        
        if not source or not target:
            return False
        
        if target_id not in source.related_to:
            source.related_to.append(target_id)
            await self.backend.update(source)
        
        if source_id not in target.related_to:
            target.related_to.append(source_id)
            await self.backend.update(target)
        
        return True
    
    async def get_memory_stats(self) -> dict:
        """Get memory system statistics."""
        return await self.backend.get_stats()
    
    async def cleanup_expired(self) -> int:
        """Remove expired memories."""
        stats = await self.backend.get_stats()
        # This would need a proper query to find and delete expired
        return 0
    
    async def _log_access(self, memory_id: str, agent_name: str, access_type: str) -> None:
        """Log memory access."""
        # Would insert into memory_access_log table
        pass


# Factory
async def create_cross_agent_memory(
    backend_type: str = "postgres",
    **kwargs
) -> CrossAgentMemory:
    """Factory function to create CrossAgentMemory with specified backend."""
    if backend_type == "postgres":
        backend = PostgresMemoryBackend(
            dsn=kwargs.get("dsn", "postgresql://localhost/financial_memory"),
            pool_size=kwargs.get("pool_size", 10)
        )
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")
    
    memory = CrossAgentMemory(backend)
    await memory.initialize()
    return memory


# Export
__all__ = [
    "MemoryType",
    "MemorySource",
    "MemoryScope",
    "MemoryEntry",
    "MemoryBackend",
    "PostgresMemoryBackend",
    "CrossAgentMemory",
    "create_cross_agent_memory",
]