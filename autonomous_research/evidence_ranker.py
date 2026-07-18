"""
Evidence Ranker - Advanced ranking and filtering of evidence for decisions.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

import numpy as np

from semantic_intelligence.evidence_lookup import get_evidence_lookup, EvidenceQuery, EvidenceRelevance, EvidenceType, RankedEvidence, Evidence
from semantic_intelligence.memory_retrieval import get_memory_retrieval, RetrievalQuery, MemoryScope, MemoryType

logger = logging.getLogger(__name__)


class RankingObjective(str, Enum):
    """Objectives for evidence ranking."""
    DECISION_SUPPORT = "decision_support"     # Balanced for decision making
    RISK_ASSESSMENT = "risk_assessment"       # Emphasize risks
    OPPORTUNITY_ID = "opportunity_id"         # Emphasize upside
    VALIDATION = "validation"                  # Verify existing hypothesis
    EXPLORATION = "exploration"                # Broad discovery
    DUE_DILIGENCE = "due_diligence"           # Comprehensive coverage


@dataclass
class EvidenceBundle:
    """Bundle of related evidence."""
    id: str
    theme: str
    evidence: List[RankedEvidence]
    coherence_score: float  # How well evidence hangs together
    coverage_score: float   # How much of theme is covered
    consensus_level: float  # Agreement among sources


@dataclass
class RankedEvidenceSet:
    """Complete ranked evidence set for a decision."""
    query: str
    objective: RankingObjective
    supporting: List[RankedEvidence]
    opposing: List[RankedEvidence]
    neutral: List[RankedEvidence]
    bundles: List[EvidenceBundle]
    summary_stats: Dict[str, Any]
    generated_at: datetime = field(default_factory=datetime.utcnow)


class EvidenceRanker:
    """
    Advanced evidence ranking with multiple objectives and clustering.
    """
    
    def __init__(self):
        self.evidence_lookup = get_evidence_lookup()
        self.memory_retrieval = get_memory_retrieval()
        
        # Objective-specific weights
        self._objective_weights = {
            RankingObjective.DECISION_SUPPORT: {
                "supporting": 1.0,
                "opposing": 1.0,
                "recency": 0.2,
                "authority": 0.3,
                "diversity": 0.2
            },
            RankingObjective.RISK_ASSESSMENT: {
                "supporting": 0.5,
                "opposing": 1.5,
                "recency": 0.3,
                "authority": 0.4,
                "diversity": 0.3
            },
            RankingObjective.OPPORTUNITY_ID: {
                "supporting": 1.5,
                "opposing": 0.5,
                "recency": 0.2,
                "authority": 0.2,
                "diversity": 0.2
            },
            RankingObjective.VALIDATION: {
                "supporting": 1.2,
                "opposing": 1.2,
                "recency": 0.1,
                "authority": 0.4,
                "diversity": 0.1
            },
            RankingObjective.EXPLORATION: {
                "supporting": 1.0,
                "opposing": 1.0,
                "recency": 0.3,
                "authority": 0.2,
                "diversity": 0.5
            },
            RankingObjective.DUE_DILIGENCE: {
                "supporting": 1.0,
                "opposing": 1.0,
                "recency": 0.2,
                "authority": 0.3,
                "diversity": 0.4
            }
        }
    
    async def initialize(self) -> None:
        await self.evidence_lookup.initialize()
        await self.memory_retrieval.initialize()
        logger.info("Evidence ranker initialized")
    
    async def rank_evidence_for_decision(
        self,
        hypothesis: str,
        entities: List[str],
        objective: RankingObjective = RankingObjective.DECISION_SUPPORT,
        context: str = "investment",
        top_k: int = 30,
        include_opposing: bool = True,
        min_confidence: float = 0.4
    ) -> RankedEvidenceSet:
        """Rank evidence for a specific decision/hypothesis."""
        
        # Search for evidence
        supporting_query = EvidenceQuery(
            query_text=hypothesis,
            entities=entities,
            context=context,
            top_k=top_k,
            min_confidence=min_confidence,
            evidence_types=[
                EvidenceType.DOCUMENT, EvidenceType.METRIC, EvidenceType.ANALYST_REPORT,
                EvidenceType.MARKET_DATA, EvidenceType.NEWS, EvidenceType.PATTERN
            ]
        )
        
        opposing_query = EvidenceQuery(
            query_text=f"risks challenges bearish case against {hypothesis}",
            entities=entities,
            context=context,
            top_k=top_k,
            min_confidence=min_confidence,
            evidence_types=[
                EvidenceType.NEWS, EvidenceType.DOCUMENT, EvidenceType.METRIC,
                EvidenceType.PATTERN, EvidenceType.INDICATOR
            ],
            include_opposing=True
        ) if include_opposing else None
        
        neutral_query = EvidenceQuery(
            query_text=f"background {entities[0] if entities else ''} sector industry",
            entities=entities,
            context=context,
            top_k=min(10, top_k // 3),
            min_confidence=min_confidence,
            evidence_types=[
                EvidenceType.DOCUMENT, EvidenceType.RELATIONSHIP, EvidenceType.INDICATOR
            ]
        )
        
        # Execute searches
        supporting = await self.evidence_lookup.lookup_evidence(supporting_query)
        opposing = await self.evidence_lookup.lookup_evidence(opposing_query) if opposing_query else []
        neutral = await self.evidence_lookup.lookup_evidence(neutral_query)
        
        # Apply objective-specific ranking
        weights = self._objective_weights[objective]
        
        supporting = self._apply_objective_weights(supporting, weights, "supporting")
        opposing = self._apply_objective_weights(opposing, weights, "opposing")
        neutral = self._apply_objective_weights(neutral, weights, "neutral")
        
        # Re-sort
        supporting.sort(key=lambda x: x.relevance_score, reverse=True)
        opposing.sort(key=lambda x: x.relevance_score, reverse=True)
        neutral.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Create evidence bundles (thematic clusters)
        bundles = await self._create_evidence_bundles(supporting + opposing + neutral)
        
        # Calculate summary stats
        summary_stats = self._calculate_summary_stats(supporting, opposing, neutral, bundles)
        
        return RankedEvidenceSet(
            query=hypothesis,
            objective=objective,
            supporting=supporting,
            opposing=opposing,
            neutral=neutral,
            bundles=bundles,
            summary_stats=summary_stats
        )
    
    def _apply_objective_weights(
        self,
        evidence_list: List[RankedEvidence],
        weights: Dict[str, float],
        stance: str
    ) -> List[RankedEvidence]:
        """Apply objective-specific weights to evidence."""
        stance_weight = weights.get(stance, 1.0)
        
        for ev in evidence_list:
            # Adjust relevance score
            ev.relevance_score *= stance_weight
            
            # Apply diversity bonus for different source types
            source_type = ev.evidence.metadata.get("source_type", "unknown")
            # In practice, would track diversity more carefully
        
        return evidence_list
    
    async def _create_evidence_bundles(
        self,
        all_evidence: List[RankedEvidence]
    ) -> List[EvidenceBundle]:
        """Cluster evidence into thematic bundles."""
        if not all_evidence:
            return []
        
        # Group by entities and evidence types
        clusters = defaultdict(list)
        
        for ev in all_evidence:
            if not ev.evidence.entities:
                clusters["general"].append(ev)
            else:
                for entity in ev.evidence.entities:
                    clusters[entity].append(ev)
        
        bundles = []
        for theme, evidences in clusters.items():
            if len(evidences) < 2:
                continue
            
            # Calculate coherence (similarity within cluster)
            coherence = self._calculate_coherence(evidences)
            
            # Calculate coverage (how much of theme is covered)
            coverage = self._calculate_coverage(evidences)
            
            # Calculate consensus (agreement among sources)
            consensus = self._calculate_consensus(evidences)
            
            bundles.append(EvidenceBundle(
                id=f"bundle_{theme}_{datetime.utcnow().timestamp()}",
                theme=theme,
                evidence=evidences,
                coherence_score=coherence,
                coverage_score=coverage,
                consensus_level=consensus
            ))
        
        return bundles
    
    def _calculate_coherence(self, evidences: List[RankedEvidence]) -> float:
        """Calculate how coherent a bundle of evidence is."""
        if len(evidences) < 2:
            return 1.0
        
        # Check embedding similarity if available
        embeddings = [e.evidence.embedding for e in evidences if e.evidence.embedding is not None]
        if len(embeddings) < 2:
            return 0.7  # Default
        
        # Average pairwise cosine similarity
        similarities = []
        for i, emb1 in enumerate(embeddings):
            for emb2 in embeddings[i+1:]:
                norm1 = np.linalg.norm(emb1)
                norm2 = np.linalg.norm(emb2)
                if norm1 > 0 and norm2 > 0:
                    sim = np.dot(emb1, emb2) / (norm1 * norm2)
                    similarities.append(sim)
        
        return float(np.mean(similarities)) if similarities else 0.7
    
    def _calculate_coverage(self, evidences: List[RankedEvidence]) -> float:
        """Calculate how well evidence covers the theme."""
        if not evidences:
            return 0.0
        
        # More evidence + higher relevance = better coverage
        total_relevance = sum(e.relevance_score for e in evidences)
        max_possible = len(evidences) * 1.0
        
        # Also consider diversity of evidence types
        types = set(e.evidence.type for e in evidences)
        type_diversity = len(types) / 10  # Normalize by expected max types
        
        coverage = (total_relevance / max_possible * 0.7) + (type_diversity * 0.3)
        return min(coverage, 1.0)
    
    def _calculate_consensus(self, evidences: List[RankedEvidence]) -> float:
        """Calculate consensus level among evidence sources."""
        if len(evidences) < 2:
            return 0.5
        
        # Check stance agreement (supporting vs opposing)
        stances = [e.evidence.metadata.get("stance", "neutral") for e in evidences]
        
        if not stances:
            return 0.5
        
        most_common = max(set(stances), key=stances.count)
        consensus = stances.count(most_common) / len(stances)
        
        return consensus
    
    def _calculate_summary_stats(
        self,
        supporting: List[RankedEvidence],
        opposing: List[RankedEvidence],
        neutral: List[RankedEvidence],
        bundles: List[EvidenceBundle]
    ) -> Dict[str, Any]:
        """Calculate summary statistics."""
        all_ev = supporting + opposing + neutral
        
        return {
            "total_evidence": len(all_ev),
            "supporting_count": len(supporting),
            "opposing_count": len(opposing),
            "neutral_count": len(neutral),
            "supporting_avg_relevance": np.mean([e.relevance_score for e in supporting]) if supporting else 0,
            "opposing_avg_relevance": np.mean([e.relevance_score for e in opposing]) if opposing else 0,
            "neutral_avg_relevance": np.mean([e.relevance_score for e in neutral]) if neutral else 0,
            "avg_confidence": np.mean([e.evidence.confidence for e in all_ev]) if all_ev else 0,
            "bundles_count": len(bundles),
            "avg_bundle_coherence": np.mean([b.coherence_score for b in bundles]) if bundles else 0,
            "avg_bundle_consensus": np.mean([b.consensus_level for b in bundles]) if bundles else 0,
            "entity_coverage": len(set().union(*[set(e.evidence.entities) for e in all_ev if e.evidence.entities])),
            "evidence_types_covered": len(set(e.evidence.type for e in all_ev))
        }


# Global evidence ranker instance
_evidence_ranker: Optional[EvidenceRanker] = None


def get_evidence_ranker() -> EvidenceRanker:
    global _evidence_ranker
    if _evidence_ranker is None:
        _evidence_ranker = EvidenceRanker()
    return _evidence_ranker


async def close_evidence_ranker() -> None:
    global _evidence_ranker
    if _evidence_ranker:
        _evidence_ranker = None