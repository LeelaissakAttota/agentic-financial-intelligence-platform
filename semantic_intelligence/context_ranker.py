"""
Context Ranker - Ranks and filters context for agent consumption.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

import numpy as np

from .embeddings import get_embedding_service
from .vector_store import get_vector_store
from .memory_retrieval import get_memory_retrieval, Memory, RetrievalQuery
from .evidence_lookup import get_evidence_lookup, EvidenceQuery, EvidenceRelevance

logger = logging.getLogger(__name__)


class RankingStrategy(str, Enum):
    """Context ranking strategies."""
    RELEVANCE = "relevance"           # Pure relevance to query
    DIVERSITY = "diversity"           # Maximize diversity of sources/types
    RECENCY = "recency"               # Prioritize recent information
    AUTHORITY = "authority"           # Prioritize authoritative sources
    BALANCED = "balanced"             # Balanced across all factors
    AGENT_SPECIALIZED = "agent_specialized"  # Tailored to agent role


@dataclass
class ContextItem:
    """Item in the context window."""
    id: str
    content: str
    source: str
    type: str  # memory, evidence, document, etc.
    relevance_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_estimate: int = 0
    rank: int = 0


@dataclass
class ContextWindow:
    """Ranked context window for agent consumption."""
    query: str
    items: List[ContextItem]
    total_tokens: int
    strategy: RankingStrategy
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RankingConfig:
    """Configuration for context ranking."""
    max_tokens: int = 8000
    max_items: int = 50
    strategy: RankingStrategy = RankingStrategy.BALANCED
    min_relevance: float = 0.3
    diversity_factor: float = 0.3
    recency_weight: float = 0.2
    authority_weight: float = 0.2
    relevance_weight: float = 0.5
    agent_role: Optional[str] = None
    include_metadata: bool = True


class ContextRanker:
    """
    Ranks and filters context for optimal agent consumption.
    Balances relevance, diversity, recency, and authority.
    """
    
    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()
        self.memory_retrieval = get_memory_retrieval()
        self.evidence_lookup = get_evidence_lookup()
        
        # Source authority scores (can be configured)
        self._source_authority = {
            "sec": 1.0,
            "reuters": 0.95,
            "bloomberg": 0.95,
            "wsj": 0.9,
            "ft": 0.9,
            "cnbc": 0.8,
            "marketwatch": 0.75,
            "seeking_alpha": 0.7,
            "benzinga": 0.65,
            "analyst_report": 0.9,
            "earnings_call": 0.95,
            "sec_filing": 1.0,
            "model_output": 0.8,
            "agent_output": 0.7,
            "news": 0.7,
            "general": 0.5
        }
        
        # Agent role preferences
        self._agent_preferences = {
            "market_agent": {
                "preferred_types": ["market_data", "metric", "indicator", "pattern"],
                "preferred_sources": ["market_data", "exchange", "bloomberg", "reuters"],
                "recency_boost": 0.3
            },
            "news_agent": {
                "preferred_types": ["news", "event", "earnings_call"],
                "preferred_sources": ["reuters", "bloomberg", "wsj", "cnbc"],
                "recency_boost": 0.4
            },
            "financial_report_agent": {
                "preferred_types": ["document", "metric", "sec_filing", "earnings_call"],
                "preferred_sources": ["sec", "company_filing", "earnings_call"],
                "authority_boost": 0.3
            },
            "sentiment_agent": {
                "preferred_types": ["news", "social", "earnings_call", "analyst_report"],
                "preferred_sources": ["news", "twitter", "reddit", "analyst_report"],
                "recency_boost": 0.3
            },
            "risk_agent": {
                "preferred_types": ["document", "metric", "pattern", "news"],
                "preferred_sources": ["sec", "risk_model", "rating_agency"],
                "authority_boost": 0.4
            },
            "competitor_agent": {
                "preferred_types": ["news", "document", "relationship", "market_data"],
                "preferred_sources": ["news", "sec", "company_filing", "press_release"],
                "diversity_boost": 0.3
            },
            "investment_summary_agent": {
                "preferred_types": ["all"],
                "preferred_sources": ["all"],
                "balanced": True
            }
        }
    
    async def initialize(self) -> None:
        """Initialize context ranker."""
        await self.embedding_service.initialize()
        await self.vector_store.initialize()
        await self.memory_retrieval.initialize()
        await self.evidence_lookup.initialize()
        logger.info("Context ranker initialized")
    
    def set_agent_role(self, agent_role: str) -> None:
        """Set the agent role for specialized ranking."""
        self._current_agent_role = agent_role
    
    async def build_context(
        self,
        query: str,
        config: Optional[RankingConfig] = None,
        additional_sources: Optional[List[Dict[str, Any]]] = None
    ) -> ContextWindow:
        """Build ranked context window for a query."""
        config = config or RankingConfig()
        
        # Gather candidates from multiple sources
        candidates = await self._gather_candidates(query, config)
        
        # Add additional sources if provided
        if additional_sources:
            for src in additional_sources:
                candidates.append(ContextItem(
                    id=src.get("id", f"ext_{len(candidates)}"),
                    content=src.get("content", ""),
                    source=src.get("source", "external"),
                    type=src.get("type", "external"),
                    relevance_score=src.get("relevance", 0.5),
                    metadata=src.get("metadata", {}),
                    token_estimate=self._estimate_tokens(src.get("content", ""))
                ))
        
        # Filter by minimum relevance
        candidates = [c for c in candidates if c.relevance_score >= config.min_relevance]
        
        # Rank candidates
        ranked = self._rank_candidates(candidates, query, config)
        
        # Apply token budget
        final_items = self._apply_token_budget(ranked, config)
        
        # Assign final ranks
        for i, item in enumerate(final_items):
            item.rank = i + 1
        
        return ContextWindow(
            query=query,
            items=final_items,
            total_tokens=sum(item.token_estimate for item in final_items),
            strategy=config.strategy,
            metadata={
                "candidates_considered": len(candidates),
                "items_selected": len(final_items),
                "agent_role": config.agent_role
            }
        )
    
    async def _gather_candidates(
        self,
        query: str,
        config: RankingConfig
    ) -> List[ContextItem]:
        """Gather candidate context items from all sources."""
        candidates = []
        
        # 1. Memories
        memory_query = RetrievalQuery(
            query_text=query,
            scopes=[MemoryScope.GLOBAL, MemoryScope.USER, MemoryScope.SESSION, MemoryScope.COMPANY, MemoryScope.AGENT],
            top_k=20,
            min_similarity=0.3
        )
        memories = await self.memory_retrieval.retrieve_memories(memory_query)
        for mem_result in memories:
            mem = mem_result.memory
            candidates.append(ContextItem(
                id=mem.id,
                content=mem.content,
                source=mem.metadata.get("source", "memory"),
                type=f"memory_{mem.type.value}",
                relevance_score=mem_result.relevance_score,
                metadata={
                    **mem.metadata,
                    "scope": mem.scope.value,
                    "importance": mem.importance,
                    "confidence": mem.confidence,
                    "access_count": mem.access_count
                },
                token_estimate=self._estimate_tokens(mem.content)
            ))
        
        # 2. Evidence
        evidence_query = EvidenceQuery(
            query_text=query,
            top_k=15,
            min_relevance=EvidenceRelevance.MEDIUM
        )
        evidence_results = await self.evidence_lookup.lookup_evidence(evidence_query)
        for ev_result in evidence_results:
            ev = ev_result.evidence
            candidates.append(ContextItem(
                id=ev.id,
                content=ev.content,
                source=ev.source,
                type=f"evidence_{ev.type.value}",
                relevance_score=ev_result.relevance_score,
                metadata={
                    **ev.metadata,
                    "evidence_type": ev.type.value,
                    "evidence_relevance": ev.relevance.value,
                    "confidence": ev.confidence
                },
                token_estimate=self._estimate_tokens(ev.content)
            ))
        
        # 3. Vector store documents
        query_embedding_result = await self.embedding_service.embed_texts([query])
        search_results = await self.vector_store.search(
            SearchQuery(
                query_embedding=query_embedding_result.embeddings[0],
                top_k=15,
                min_score=0.3
            )
        )
        for result in search_results:
            candidates.append(ContextItem(
                id=result.id,
                content=result.content,
                source=result.metadata.get("source", "document"),
                type="document",
                relevance_score=result.score,
                metadata=result.metadata,
                token_estimate=self._estimate_tokens(result.content)
            ))
        
        return candidates
    
    def _rank_candidates(
        self,
        candidates: List[ContextItem],
        query: str,
        config: RankingConfig
    ) -> List[ContextItem]:
        """Rank candidates using the specified strategy."""
        if config.strategy == RankingStrategy.RELEVANCE:
            return self._rank_by_relevance(candidates)
        elif config.strategy == RankingStrategy.DIVERSITY:
            return self._rank_by_diversity(candidates)
        elif config.strategy == RankingStrategy.RECENCY:
            return self._rank_by_recency(candidates)
        elif config.strategy == RankingStrategy.AUTHORITY:
            return self._rank_by_authority(candidates)
        elif config.strategy == RankingStrategy.AGENT_SPECIALIZED:
            return self._rank_for_agent(candidates, config)
        else:  # BALANCED
            return self._rank_balanced(candidates, query, config)
    
    def _rank_by_relevance(self, candidates: List[ContextItem]) -> List[ContextItem]:
        """Rank purely by relevance score."""
        return sorted(candidates, key=lambda x: x.relevance_score, reverse=True)
    
    def _rank_by_diversity(self, candidates: List[ContextItem]) -> List[ContextItem]:
        """Rank to maximize diversity of sources and types."""
        if not candidates:
            return []
        
        selected = []
        remaining = candidates.copy()
        
        # Start with highest relevance
        remaining.sort(key=lambda x: x.relevance_score, reverse=True)
        selected.append(remaining.pop(0))
        
        # Greedily select items that maximize diversity
        while remaining and len(selected) < 50:
            best_idx = -1
            best_score = -1
            
            for i, candidate in enumerate(remaining):
                # Calculate diversity score
                type_diversity = 1.0 if candidate.type not in [s.type for s in selected] else 0.0
                source_diversity = 1.0 if candidate.source not in [s.source for s in selected] else 0.0
                
                diversity_score = (type_diversity + source_diversity) / 2
                combined_score = candidate.relevance_score * 0.5 + diversity_score * 0.5
                
                if combined_score > best_score:
                    best_score = combined_score
                    best_idx = i
            
            if best_idx >= 0:
                selected.append(remaining.pop(best_idx))
            else:
                break
        
        return selected
    
    def _rank_by_recency(self, candidates: List[ContextItem]) -> List[ContextItem]:
        """Rank by recency with relevance as tiebreaker."""
        def get_recency(item: ContextItem) -> float:
            created = item.metadata.get("created_at") or item.metadata.get("timestamp")
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    age_hours = (datetime.utcnow() - dt).total_seconds() / 3600
                    return max(0, 1.0 - age_hours / (24 * 30))  # Decay over 30 days
                except Exception:
                    pass
            return 0.5
        
        return sorted(
            candidates,
            key=lambda x: (get_recency(x) * 0.7 + x.relevance_score * 0.3),
            reverse=True
        )
    
    def _rank_by_authority(self, candidates: List[ContextItem]) -> List[ContextItem]:
        """Rank by source authority."""
        def get_authority(item: ContextItem) -> float:
            source = item.source.lower()
            for key, score in self._source_authority.items():
                if key in source:
                    return score
            return 0.5
        
        return sorted(
            candidates,
            key=lambda x: (get_authority(x) * 0.6 + x.relevance_score * 0.4),
            reverse=True
        )
    
    def _rank_for_agent(self, candidates: List[ContextItem], config: RankingConfig) -> List[ContextItem]:
        """Rank tailored to agent role."""
        agent_role = config.agent_role or getattr(self, '_current_agent_role', None)
        if not agent_role or agent_role not in self._agent_preferences:
            return self._rank_balanced(candidates, "", config)
        
        prefs = self._agent_preferences[agent_role]
        
        def agent_score(item: ContextItem) -> float:
            score = item.relevance_score
            
            # Type preference
            if prefs.get("preferred_types") != ["all"]:
                if any(pt in item.type for pt in prefs["preferred_types"]):
                    score *= 1.3
            
            # Source preference
            if prefs.get("preferred_sources") != ["all"]:
                if any(ps in item.source.lower() for ps in prefs["preferred_sources"]):
                    score *= 1.2
            
            # Recency boost
            if prefs.get("recency_boost"):
                created = item.metadata.get("created_at") or item.metadata.get("timestamp")
                if created:
                    try:
                        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        age_hours = (datetime.utcnow() - dt).total_seconds() / 3600
                        if age_hours < 24:
                            score *= (1 + prefs["recency_boost"])
                    except Exception:
                        pass
            
            # Authority boost
            if prefs.get("authority_boost"):
                authority = self._source_authority.get(item.source.lower(), 0.5)
                score *= (1 + prefs["authority_boost"] * authority)
            
            # Diversity boost
            if prefs.get("diversity_boost"):
                # Handled in balanced strategy
                pass
            
            return score
        
        return sorted(candidates, key=agent_score, reverse=True)
    
    def _rank_balanced(
        self,
        candidates: List[ContextItem],
        query: str,
        config: RankingConfig
    ) -> List[ContextItem]:
        """Balanced ranking across all factors."""
        
        def balanced_score(item: ContextItem) -> float:
            # Base relevance
            score = item.relevance_score * config.relevance_weight
            
            # Authority
            authority = self._source_authority.get(item.source.lower(), 0.5)
            score += authority * config.authority_weight
            
            # Recency
            created = item.metadata.get("created_at") or item.metadata.get("timestamp")
            recency = 0.5
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    age_hours = (datetime.utcnow() - dt).total_seconds() / 3600
                    recency = max(0, 1.0 - age_hours / (24 * 30))
                except Exception:
                    pass
            score += recency * config.recency_weight
            
            # Diversity bonus (approximate)
            # In practice, would use MMR or similar
            diversity_bonus = 0.0
            
            # Agent role adjustment
            if config.agent_role and config.agent_role in self._agent_preferences:
                prefs = self._agent_preferences[config.agent_role]
                if prefs.get("preferred_types") != ["all"]:
                    if any(pt in item.type for pt in prefs["preferred_types"]):
                        score *= 1.1
                if prefs.get("preferred_sources") != ["all"]:
                    if any(ps in item.source.lower() for ps in prefs["preferred_sources"]):
                        score *= 1.1
            
            return score
        
        return sorted(candidates, key=balanced_score, reverse=True)
    
    def _apply_token_budget(
        self,
        ranked: List[ContextItem],
        config: RankingConfig
    ) -> List[ContextItem]:
        """Apply token budget to ranked candidates."""
        selected = []
        total_tokens = 0
        
        for item in ranked:
            if total_tokens + item.token_estimate > config.max_tokens:
                break
            if len(selected) >= config.max_items:
                break
            
            selected.append(item)
            total_tokens += item.token_estimate
        
        return selected
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        # Rough estimate: ~4 chars per token for English
        return max(1, len(text) // 4)
    
    async def rank_for_agent(
        self,
        agent_role: str,
        query: str,
        max_tokens: int = 8000
    ) -> ContextWindow:
        """Convenience method to rank context for a specific agent."""
        config = RankingConfig(
            agent_role=agent_role,
            max_tokens=max_tokens,
            strategy=RankingStrategy.AGENT_SPECIALIZED
        )
        return await self.build_context(query, config)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get context ranker statistics."""
        return {
            "source_authority": self._source_authority,
            "agent_preferences": {
                role: {k: v for k, v in prefs.items() if k != "preferred_types" or isinstance(v, list)}
                for role, prefs in self._agent_preferences.items()
            }
        }


# Global context ranker instance
_context_ranker: Optional[ContextRanker] = None


def get_context_ranker() -> ContextRanker:
    """Get or create the global context ranker instance."""
    global _context_ranker
    if _context_ranker is None:
        _context_ranker = ContextRanker()
    return _context_ranker


async def close_context_ranker() -> None:
    """Close the global context ranker instance."""
    global _context_ranker
    if _context_ranker:
        _context_ranker = None