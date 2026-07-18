"""
Memory Retrieval - Cross-session memory retrieval with semantic search.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

from .embeddings import get_embedding_service
from .vector_store import get_vector_store, VectorDocument, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class MemoryScope(str, Enum):
    """Memory scope levels."""
    GLOBAL = "global"          # System-wide knowledge
    USER = "user"              # User-specific
    SESSION = "session"        # Current session
    COMPANY = "company"        # Company-specific
    AGENT = "agent"            # Agent-specific


class MemoryType(str, Enum):
    """Types of memories."""
    FACT = "fact"                      # Factual knowledge
    INSIGHT = "insight"                # Derived insight
    PREFERENCE = "preference"          # User/agent preference
    PATTERN = "pattern"                # Observed pattern
    DECISION = "decision"              # Past decision
    OUTCOME = "outcome"                # Outcome of action
    CONVERSATION = "conversation"      # Conversation history
    TOOL_USAGE = "tool_usage"          # Tool usage analytics
    ERROR = "error"                    # Error/lesson learned
    HYPOTHESIS = "hypothesis"          # Research hypothesis


@dataclass
class Memory:
    """Memory unit with semantic embedding."""
    id: str
    type: MemoryType
    scope: MemoryScope
    content: str
    summary: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5  # 0-1
    confidence: float = 1.0  # 0-1
    access_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    source_agent: Optional[str] = None
    related_entities: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    def to_vector_document(self) -> VectorDocument:
        """Convert to vector document for storage."""
        return VectorDocument(
            id=self.id,
            embedding=np.array(self.embedding) if self.embedding else np.array([]),
            metadata={
                "type": self.type.value,
                "scope": self.scope.value,
                "summary": self.summary,
                "importance": self.importance,
                "confidence": self.confidence,
                "access_count": self.access_count,
                "source_agent": self.source_agent,
                "related_entities": self.related_entities,
                "tags": self.tags,
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
                "expires_at": self.expires_at.isoformat() if self.expires_at else None,
                **self.metadata
            },
            content=self.content
        )


@dataclass
class RetrievalQuery:
    """Query for memory retrieval."""
    query_text: str
    query_embedding: Optional[np.ndarray] = None
    scopes: List[MemoryScope] = field(default_factory=lambda: [MemoryScope.GLOBAL, MemoryScope.USER, MemoryScope.SESSION])
    types: Optional[List[MemoryType]] = None
    entity_filter: Optional[List[str]] = None
    agent_filter: Optional[str] = None
    min_importance: float = 0.0
    min_confidence: float = 0.0
    top_k: int = 10
    min_similarity: float = 0.3
    include_expired: bool = False
    time_range: Optional[Tuple[datetime, datetime]] = None


@dataclass
class RetrievalResult:
    """Result of memory retrieval."""
    memory: Memory
    similarity_score: float
    relevance_score: float  # Combined score
    matched_terms: List[str] = field(default_factory=list)


class MemoryRetrieval:
    """
    Cross-session memory retrieval with semantic search.
    Integrates with vector store for similarity search.
    """
    
    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()
        self._memory_cache: Dict[str, Memory] = {}
        _initialized = False
    
    async def initialize(self) -> None:
        """Initialize memory retrieval system."""
        await self.embedding_service.initialize()
        await self.vector_store.initialize()
        _initialized = True
        logger.info("Memory retrieval initialized")
    
    async def store_memory(self, memory: Memory) -> str:
        """Store a memory with semantic embedding."""
        # Generate embedding if not provided
        if memory.embedding is None:
            result = await self.embedding_service.embed_texts([memory.content])
            memory.embedding = result.embeddings[0].tolist()
        
        memory.updated_at = datetime.utcnow()
        
        # Store in vector store
        vector_doc = memory.to_vector_document()
        await self.vector_store.add_documents([vector_doc])
        
        # Update cache
        self._memory_cache[memory.id] = memory
        
        logger.debug(f"Stored memory: {memory.id} ({memory.type.value})")
        return memory.id
    
    async def store_memories(self, memories: List[Memory]) -> List[str]:
        """Store multiple memories efficiently."""
        # Generate embeddings for memories without them
        texts_to_embed = []
        indices = []
        for i, mem in enumerate(memories):
            if mem.embedding is None:
                texts_to_embed.append(mem.content)
                indices.append(i)
        
        if texts_to_embed:
            result = await self.embedding_service.embed_texts(texts_to_embed)
            for idx, emb in zip(indices, result.embeddings):
                memories[idx].embedding = emb.tolist()
        
        # Prepare vector documents
        vector_docs = [mem.to_vector_document() for mem in memories]
        await self.vector_store.add_documents(vector_docs)
        
        # Update cache
        for mem in memories:
            mem.updated_at = datetime.utcnow()
            self._memory_cache[mem.id] = mem
        
        return [mem.id for mem in memories]
    
    async def retrieve_memories(self, query: RetrievalQuery) -> List[RetrievalResult]:
        """Retrieve memories matching the query."""
        # Generate query embedding if not provided
        if query.query_embedding is None:
            result = await self.embedding_service.embed_texts([query.query_text])
            query.query_embedding = result.embeddings[0]
        
        # Build filter metadata
        filter_metadata = {}
        if query.types:
            filter_metadata["type"] = {"$in": [t.value for t in query.types]}
        
        if query.scopes:
            filter_metadata["scope"] = {"$in": [s.value for s in query.scopes]}
        
        if query.agent_filter:
            filter_metadata["source_agent"] = query.agent_filter
        
        # Search vector store
        search_query = SearchQuery(
            query_embedding=query.query_embedding,
            top_k=query.top_k * 3,  # Get more for post-filtering
            filter_metadata=filter_metadata if filter_metadata else None,
            min_score=query.min_similarity,
            include_embeddings=False
        )
        
        results = await self.vector_store.search(search_query)
        
        # Convert to retrieval results with post-filtering
        retrieval_results = []
        for result in results:
            # Reconstruct memory
            memory = self._result_to_memory(result)
            if not memory:
                continue
            
            # Apply additional filters
            if not self._passes_filters(memory, query):
                continue
            
            # Calculate relevance score (combines similarity + importance + recency)
            relevance = self._calculate_relevance(memory, result.score, query)
            
            retrieval_results.append(RetrievalResult(
                memory=memory,
                similarity_score=result.score,
                relevance_score=relevance,
                matched_terms=self._extract_matched_terms(query.query_text, memory.content)
            ))
        
        # Sort by relevance
        retrieval_results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Update access counts
        for ret in retrieval_results[:query.top_k]:
            ret.memory.access_count += 1
            # Could update in vector store here
        
        return retrieval_results[:query.top_k]
    
    def _result_to_memory(self, result: SearchResult) -> Optional[Memory]:
        """Convert search result to memory object."""
        metadata = result.metadata
        try:
            return Memory(
                id=result.id,
                type=MemoryType(metadata.get("type", "fact")),
                scope=MemoryScope(metadata.get("scope", "global")),
                content=result.content,
                summary=metadata.get("summary", ""),
                embedding=None,  # Not loaded by default
                metadata={k: v for k, v in metadata.items() if k not in [
                    "type", "scope", "summary", "importance", "confidence",
                    "access_count", "source_agent", "related_entities", "tags",
                    "created_at", "updated_at", "expires_at"
                ]},
                importance=metadata.get("importance", 0.5),
                confidence=metadata.get("confidence", 1.0),
                access_count=metadata.get("access_count", 0),
                created_at=datetime.fromisoformat(metadata["created_at"]) if metadata.get("created_at") else datetime.utcnow(),
                updated_at=datetime.fromisoformat(metadata["updated_at"]) if metadata.get("updated_at") else datetime.utcnow(),
                expires_at=datetime.fromisoformat(metadata["expires_at"]) if metadata.get("expires_at") else None,
                source_agent=metadata.get("source_agent"),
                related_entities=metadata.get("related_entities", []),
                tags=metadata.get("tags", [])
            )
        except Exception as e:
            logger.error(f"Failed to reconstruct memory from result: {e}")
            return None
    
    def _passes_filters(self, memory: Memory, query: RetrievalQuery) -> bool:
        """Check if memory passes all query filters."""
        # Importance filter
        if memory.importance < query.min_importance:
            return False
        
        # Confidence filter
        if memory.confidence < query.min_confidence:
            return False
        
        # Entity filter
        if query.entity_filter:
            if not any(entity in memory.related_entities for entity in query.entity_filter):
                return False
        
        # Expiration filter
        if not query.include_expired and memory.expires_at:
            if memory.expires_at < datetime.utcnow():
                return False
        
        # Time range filter
        if query.time_range:
            start, end = query.time_range
            if memory.created_at < start or memory.created_at > end:
                return False
        
        return True
    
    def _calculate_relevance(self, memory: Memory, similarity: float, query: RetrievalQuery) -> float:
        """Calculate combined relevance score."""
        # Weighted combination of similarity, importance, confidence, recency
        recency_factor = 1.0
        if memory.created_at:
            age_hours = (datetime.utcnow() - memory.created_at).total_seconds() / 3600
            recency_factor = max(0.1, 1.0 - (age_hours / (24 * 30)))  # Decay over 30 days
        
        access_factor = min(1.0, 1.0 + memory.access_count * 0.01)  # Slight boost for accessed
        
        relevance = (
            similarity * 0.5 +
            memory.importance * 0.2 +
            memory.confidence * 0.15 +
            recency_factor * 0.1 +
            access_factor * 0.05
        )
        
        return relevance
    
    def _extract_matched_terms(self, query: str, content: str) -> List[str]:
        """Extract terms from query that appear in content."""
        query_terms = set(query.lower().split())
        content_lower = content.lower()
        return [term for term in query_terms if term in content_lower]
    
    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Get a specific memory by ID."""
        # Check cache first
        if memory_id in self._memory_cache:
            return self._memory_cache[memory_id]
        
        # Fetch from vector store
        result = await self.vector_store.get_document(memory_id)
        if result:
            return self._result_to_memory(SearchResult(
                id=result.id,
                score=1.0,
                content=result.content,
                metadata=result.metadata
            ))
        return None
    
    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        importance: Optional[float] = None,
        confidence: Optional[float] = None
    ) -> bool:
        """Update an existing memory."""
        memory = await self.get_memory(memory_id)
        if not memory:
            return False
        
        if content is not None:
            memory.content = content
            # Regenerate embedding
            result = await self.embedding_service.embed_texts([content])
            memory.embedding = result.embeddings[0].tolist()
        
        if metadata is not None:
            memory.metadata.update(metadata)
        
        if importance is not None:
            memory.importance = importance
        
        if confidence is not None:
            memory.confidence = confidence
        
        memory.updated_at = datetime.utcnow()
        await self.store_memory(memory)
        return True
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory."""
        success = await self.vector_store.delete_documents([memory_id])
        self._memory_cache.pop(memory_id, None)
        return success
    
    async def get_memories_by_entity(
        self,
        entity: str,
        scopes: Optional[List[MemoryScope]] = None,
        limit: int = 50
    ) -> List[Memory]:
        """Get all memories related to an entity."""
        query = RetrievalQuery(
            query_text=entity,
            scopes=scopes or [MemoryScope.GLOBAL, MemoryScope.COMPANY],
            entity_filter=[entity],
            top_k=limit
        )
        results = await self.retrieve_memories(query)
        return [r.memory for r in results]
    
    async def get_memories_by_agent(
        self,
        agent: str,
        scopes: Optional[List[MemoryScope]] = None,
        limit: int = 50
    ) -> List[Memory]:
        """Get all memories from a specific agent."""
        query = RetrievalQuery(
            query_text="",
            scopes=scopes or [MemoryScope.GLOBAL, MemoryScope.AGENT],
            agent_filter=agent,
            top_k=limit
        )
        results = await self.retrieve_memories(query)
        return [r.memory for r in results]
    
    async def prune_memories(
        self,
        max_age_days: int = 90,
        min_importance: float = 0.1,
        min_access_count: int = 0
    ) -> int:
        """Prune old, unimportant, or unused memories."""
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        pruned = 0
        
        # This would require scanning all memories
        # In production, use a scheduled job with vector store queries
        logger.info(f"Memory pruning requested (max_age={max_age_days}d, min_importance={min_importance})")
        return pruned
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory retrieval statistics."""
        cache_by_type = defaultdict(int)
        cache_by_scope = defaultdict(int)
        
        for mem in self._memory_cache.values():
            cache_by_type[mem.type.value] += 1
            cache_by_scope[mem.scope.value] += 1
        
        return {
            "cached_memories": len(self._memory_cache),
            "by_type": dict(cache_by_type),
            "by_scope": dict(cache_by_scope),
            "vector_store_stats": self.vector_store.get_stats()
        }


# Global memory retrieval instance
_memory_retrieval: Optional[MemoryRetrieval] = None


def get_memory_retrieval() -> MemoryRetrieval:
    """Get or create the global memory retrieval instance."""
    global _memory_retrieval
    if _memory_retrieval is None:
        _memory_retrieval = MemoryRetrieval()
    return _memory_retrieval


import numpy as np  # Moved here to avoid circular import