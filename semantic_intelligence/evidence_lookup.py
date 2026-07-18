"""
Evidence Lookup - Semantic evidence retrieval and ranking for decisions.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

import numpy as np

from .embeddings import get_embedding_service
from .vector_store import get_vector_store, SearchQuery, SearchResult
from .memory_retrieval import get_memory_retrieval, Memory, MemoryType, MemoryScope

logger = logging.getLogger(__name__)


class EvidenceType(str, Enum):
    """Types of evidence for decision support."""
    DOCUMENT = "document"              # SEC filings, reports
    NEWS = "news"                      # News articles
    MARKET_DATA = "market_data"        # Price, volume, indicators
    ANALYST_REPORT = "analyst_report"  # Analyst opinions
    METRIC = "metric"                  # Financial metrics
    INDICATOR = "indicator"            # Technical indicators
    RELATIONSHIP = "relationship"      # Entity relationships
    PATTERN = "pattern"                # Historical patterns
    MODEL = "model"                    # Model outputs
    EXPERT_OPINION = "expert_opinion"  # Human expert input
    AGENT_OUTPUT = "agent_output"      # Other agent conclusions


class EvidenceRelevance(str, Enum):
    """Relevance levels for evidence."""
    CRITICAL = "critical"    # Directly addresses the question
    HIGH = "high"            # Strongly relevant
    MEDIUM = "medium"        # Moderately relevant
    LOW = "low"              # Tangentially relevant
    IRRELEVANT = "irrelevant"  # Not relevant


@dataclass
class Evidence:
    """Piece of evidence for decision making."""
    id: str
    type: EvidenceType
    content: str
    source: str
    source_url: Optional[str] = None
    title: Optional[str] = None
    summary: str = ""
    relevance: EvidenceRelevance = EvidenceRelevance.MEDIUM
    confidence: float = 1.0  # 0-1
    supporting_query: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    entities: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    embedding: Optional[np.ndarray] = None
    
    def to_memory(self) -> Memory:
        """Convert evidence to memory for storage."""
        return Memory(
            id=self.id,
            type=MemoryType.FACT,
            scope=MemoryScope.GLOBAL,
            content=self.content,
            summary=self.summary,
            embedding=self.embedding.tolist() if self.embedding is not None else None,
            metadata={
                "evidence_type": self.type.value,
                "source": self.source,
                "source_url": self.source_url,
                "title": self.title,
                "relevance": self.relevance.value,
                "confidence": self.confidence,
                "supporting_query": self.supporting_query,
                **self.metadata
            },
            importance=self.confidence,
            confidence=self.confidence,
            related_entities=self.entities,
            tags=["evidence", self.type.value]
        )


@dataclass
class EvidenceQuery:
    """Query for evidence lookup."""
    query_text: str
    query_embedding: Optional[np.ndarray] = None
    evidence_types: Optional[List[EvidenceType]] = None
    entities: Optional[List[str]] = None
    time_range: Optional[Tuple[datetime, datetime]] = None
    min_confidence: float = 0.5
    min_relevance: EvidenceRelevance = EvidenceRelevance.MEDIUM
    top_k: int = 20
    include_opposing: bool = True  # Include contradictory evidence
    context: str = ""  # Additional context for ranking


@dataclass
class RankedEvidence:
    """Evidence with relevance ranking."""
    evidence: Evidence
    relevance_score: float
    rank: int
    matched_terms: List[str] = field(default_factory=list)
    explains: List[str] = field(default_factory=list)  # What this explains
    contradicts: List[str] = field(default_factory=list)  # What this contradicts


class EvidenceLookup:
    """
    Semantic evidence lookup and ranking for decision support.
    Retrieves and ranks evidence from multiple sources.
    """
    
    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()
        self.memory_retrieval = get_memory_retrieval()
        
        # Evidence type weights for different query contexts
        self._type_weights = {
            "investment": {
                EvidenceType.METRIC: 1.5,
                EvidenceType.ANALYST_REPORT: 1.3,
                EvidenceType.MARKET_DATA: 1.2,
                EvidenceType.DOCUMENT: 1.1,
                EvidenceType.NEWS: 1.0,
                EvidenceType.PATTERN: 1.0,
            },
            "risk": {
                EvidenceType.DOCUMENT: 1.5,
                EvidenceType.NEWS: 1.3,
                EvidenceType.METRIC: 1.2,
                EvidenceType.PATTERN: 1.1,
                EvidenceType.RELATIONSHIP: 1.0,
            },
            "competitive": {
                EvidenceType.NEWS: 1.5,
                EvidenceType.DOCUMENT: 1.3,
                EvidenceType.RELATIONSHIP: 1.2,
                EvidenceType.MARKET_DATA: 1.0,
            },
            "general": {
                EvidenceType.DOCUMENT: 1.0,
                EvidenceType.NEWS: 1.0,
                EvidenceType.METRIC: 1.0,
                EvidenceType.ANALYST_REPORT: 1.0,
                EvidenceType.MARKET_DATA: 1.0,
            }
        }
    
    async def initialize(self) -> None:
        """Initialize evidence lookup."""
        await self.embedding_service.initialize()
        await self.vector_store.initialize()
        await self.memory_retrieval.initialize()
        logger.info("Evidence lookup initialized")
    
    def set_context_weights(self, context: str, weights: Dict[EvidenceType, float]) -> None:
        """Set custom evidence type weights for a context."""
        self._type_weights[context] = weights
    
    async def lookup_evidence(self, query: EvidenceQuery) -> List[RankedEvidence]:
        """Lookup and rank evidence for a query."""
        # Generate query embedding if not provided
        if query.query_embedding is None:
            result = await self.embedding_service.embed_texts([query.query_text])
            query.query_embedding = result.embeddings[0]
        
        # Search vector store for each evidence type
        all_results = []
        
        search_types = query.evidence_types or list(EvidenceType)
        
        for ev_type in search_types:
            type_results = await self._search_evidence_type(query, ev_type)
            all_results.extend(type_results)
        
        # Rank and filter
        ranked = self._rank_evidence(all_results, query)
        
        # Apply min relevance filter
        min_relevance_score = self._relevance_to_score(query.min_relevance)
        ranked = [r for r in ranked if r.relevance_score >= min_relevance_score]
        
        # Apply min confidence filter
        ranked = [r for r in ranked if r.evidence.confidence >= query.min_confidence]
        
        # Sort by relevance score
        ranked.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Assign ranks
        for i, r in enumerate(ranked):
            r.rank = i + 1
        
        return ranked[:query.top_k]
    
    async def _search_evidence_type(
        self,
        query: EvidenceQuery,
        ev_type: EvidenceType
    ) -> List[Tuple[Evidence, float]]:
        """Search for evidence of a specific type."""
        # Build filter metadata
        filter_metadata = {"evidence_type": ev_type.value}
        
        if query.entities:
            filter_metadata["entities"] = {"$in": query.entities}
        
        if query.time_range:
            start, end = query.time_range
            filter_metadata["timestamp"] = {"$gte": start.isoformat(), "$lte": end.isoformat()}
        
        # Search vector store
        search_query = SearchQuery(
            query_embedding=query.query_embedding,
            top_k=query.top_k,
            filter_metadata=filter_metadata,
            min_score=0.3,  # Low initial threshold
            include_embeddings=True
        )
        
        results = await self.vector_store.search(search_query)
        
        # Convert to Evidence objects
        evidence_list = []
        for result in results:
            metadata = result.metadata
            
            evidence = Evidence(
                id=result.id,
                type=ev_type,
                content=result.content,
                source=metadata.get("source", "unknown"),
                source_url=metadata.get("source_url"),
                title=metadata.get("title"),
                summary=metadata.get("summary", ""),
                relevance=EvidenceRelevance(metadata.get("relevance", "medium")),
                confidence=metadata.get("confidence", 1.0),
                supporting_query=metadata.get("supporting_query", ""),
                metadata={k: v for k, v in metadata.items() if k not in [
                    "evidence_type", "source", "source_url", "title",
                    "summary", "relevance", "confidence", "supporting_query"
                ]},
                entities=metadata.get("entities", []),
                timestamp=datetime.fromisoformat(metadata["timestamp"]) if metadata.get("timestamp") else datetime.utcnow(),
                embedding=result.embedding if result.embedding is not None else None
            )
            
            evidence_list.append((evidence, result.score))
        
        return evidence_list
    
    def _rank_evidence(
        self,
        candidates: List[Tuple[Evidence, float]],
        query: EvidenceQuery
    ) -> List[RankedEvidence]:
        """Rank evidence by combined relevance score."""
        ranked = []
        
        # Get context weights
        context = query.context.lower() if query.context else "general"
        weights = self._type_weights.get(context, self._type_weights["general"])
        
        for evidence, similarity in candidates:
            # Base relevance from similarity
            base_score = similarity
            
            # Apply evidence type weight
            type_weight = weights.get(evidence.type, 1.0)
            
            # Confidence factor
            conf_factor = evidence.confidence
            
            # Recency factor
            recency_factor = self._calculate_recency(evidence.timestamp)
            
            # Entity match bonus
            entity_bonus = 1.0
            if query.entities:
                matched = sum(1 for e in query.entities if e in evidence.entities)
                entity_bonus = 1.0 + (matched / max(len(query.entities), 1)) * 0.2
            
            # Source credibility (could be enhanced)
            source_factor = 1.0
            
            # Calculate combined relevance
            relevance = (
                base_score * 0.35 +
                type_weight * 0.15 +
                conf_factor * 0.2 +
                recency_factor * 0.1 +
                entity_bonus * 0.1 +
                source_factor * 0.1
            )
            
            # Extract matched terms
            matched_terms = self._extract_matched_terms(query.query_text, evidence.content)
            
            # Determine what this explains/contradicts
            explains, contradicts = self._analyze_evidence_role(evidence, query)
            
            ranked.append(RankedEvidence(
                evidence=evidence,
                relevance_score=relevance,
                rank=0,
                matched_terms=matched_terms,
                explains=explains,
                contradicts=contradicts
            ))
        
        return ranked
    
    def _calculate_recency(self, timestamp: datetime) -> float:
        """Calculate recency factor (1.0 = very recent, decays over time)."""
        age_hours = (datetime.utcnow() - timestamp).total_seconds() / 3600
        if age_hours <= 24:
            return 1.0
        elif age_hours <= 168:  # 1 week
            return 0.8
        elif age_hours <= 720:  # 1 month
            return 0.6
        elif age_hours <= 2160:  # 3 months
            return 0.4
        else:
            return 0.2
    
    def _extract_matched_terms(self, query: str, content: str) -> List[str]:
        """Extract query terms that appear in content."""
        query_terms = set(query.lower().split())
        content_lower = content.lower()
        return [term for term in query_terms if term in content_lower]
    
    def _analyze_evidence_role(
        self,
        evidence: Evidence,
        query: EvidenceQuery
    ) -> Tuple[List[str], List[str]]:
        """Analyze what this evidence explains or contradicts."""
        explains = []
        contradicts = []
        
        # Simple keyword-based analysis
        content_lower = evidence.content.lower()
        
        # Positive indicators
        if any(word in content_lower for word in ["support", "confirm", "validate", "evidence shows", "indicates"]):
            explains.append("supports hypothesis")
        
        if any(word in content_lower for word in ["growth", "increase", "positive", "bullish", "outperform"]):
            explains.append("positive outlook")
        
        # Negative indicators
        if any(word in content_lower for word in ["contradict", "refute", "challenge", "despite", "however"]):
            contradicts.append("contradicts prevailing view")
        
        if any(word in content_lower for word in ["decline", "decrease", "negative", "bearish", "underperform", "risk"]):
            contradicts.append("negative indicators")
        
        return explains, contradicts
    
    def _relevance_to_score(self, relevance: EvidenceRelevance) -> float:
        """Convert relevance enum to score threshold."""
        mapping = {
            EvidenceRelevance.CRITICAL: 0.8,
            EvidenceRelevance.HIGH: 0.6,
            EvidenceRelevance.MEDIUM: 0.4,
            EvidenceRelevance.LOW: 0.2,
            EvidenceRelevance.IRRELEVANT: 0.0
        }
        return mapping.get(relevance, 0.4)
    
    async def get_evidence_for_decision(
        self,
        decision_id: str,
        hypothesis: str,
        entities: List[str],
        context: str = "investment"
    ) -> Dict[str, List[RankedEvidence]]:
        """Get organized evidence for a decision."""
        # Search for supporting evidence
        supporting_query = EvidenceQuery(
            query_text=hypothesis,
            entities=entities,
            evidence_types=[EvidenceType.DOCUMENT, EvidenceType.METRIC, EvidenceType.ANALYST_REPORT, EvidenceType.MARKET_DATA, EvidenceType.PATTERN],
            context=context,
            top_k=10
        )
        supporting = await self.lookup_evidence(supporting_query)
        
        # Search for opposing evidence
        opposing_query = EvidenceQuery(
            query_text=f"risks challenges bearish case against {hypothesis}",
            entities=entities,
            evidence_types=[EvidenceType.NEWS, EvidenceType.DOCUMENT, EvidenceType.METRIC, EvidenceType.PATTERN],
            context=context,
            top_k=10,
            include_opposing=True
        )
        opposing = await self.lookup_evidence(opposing_query)
        
        # Search for neutral/contextual evidence
        neutral_query = EvidenceQuery(
            query_text=f"background context {entities[0] if entities else ''} sector industry",
            entities=entities,
            evidence_types=[EvidenceType.DOCUMENT, EvidenceType.RELATIONSHIP, EvidenceType.INDICATOR],
            context=context,
            top_k=5
        )
        neutral = await self.lookup_evidence(neutral_query)
        
        return {
            "supporting": supporting,
            "opposing": opposing,
            "neutral": neutral,
            "all": supporting + opposing + neutral
        }
    
    async def find_related_evidence(
        self,
        evidence_id: str,
        top_k: int = 10
    ) -> List[RankedEvidence]:
        """Find evidence related to a specific piece of evidence."""
        # Get the original evidence
        result = await self.vector_store.get_document(evidence_id)
        if not result:
            return []
        
        # Use its content as query
        query = EvidenceQuery(
            query_text=result.content,
            query_embedding=result.embedding,
            top_k=top_k + 1  # +1 to exclude self
        )
        
        results = await self.lookup_evidence(query)
        
        # Filter out self
        return [r for r in results if r.evidence.id != evidence_id][:top_k]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get evidence lookup statistics."""
        return {
            "type_weights": {
                context: {k.value: v for k, v in weights.items()}
                for context, weights in self._type_weights.items()
            },
            "vector_store_stats": self.vector_store.get_stats()
        }


# Global evidence lookup instance
_evidence_lookup: Optional[EvidenceLookup] = None


def get_evidence_lookup() -> EvidenceLookup:
    """Get or create the global evidence lookup instance."""
    global _evidence_lookup
    if _evidence_lookup is None:
        _evidence_lookup = EvidenceLookup()
    return _evidence_lookup


async def close_evidence_lookup() -> None:
    """Close the global evidence lookup instance."""
    global _evidence_lookup
    if _evidence_lookup:
        _evidence_lookup = None