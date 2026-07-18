"""
Confidence Scorer - Quantifies confidence in research outputs and decisions.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

import numpy as np

logger = logging.getLogger(__name__)


class ConfidenceDimension(str, Enum):
    """Dimensions of confidence assessment."""
    EVIDENCE_QUALITY = "evidence_quality"       # Quality and relevance of evidence
    EVIDENCE_QUANTITY = "evidence_quantity"     # Amount of evidence
    SOURCE_CREDIBILITY = "source_credibility"   # Credibility of sources
    METHODOLOGY_RIGOR = "methodology_rigor"     # Rigor of analysis method
    CONSENSUS = "consensus"                     # Agreement among agents/sources
    RECENCY = "recency"                         # Timeliness of information
    COMPLETENESS = "completeness"               # Coverage of key aspects
    CONSISTENCY = "consistency"                 # Internal consistency


@dataclass
class ConfidenceScore:
    """Score for a single confidence dimension."""
    dimension: ConfidenceDimension
    score: float  # 0-1
    weight: float  # 0-1
    rationale: str
    sub_scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class ConfidenceAssessment:
    """Complete confidence assessment for a research output."""
    overall_score: float  # 0-1
    dimensions: List[ConfidenceScore]
    confidence_interval: Tuple[float, float]  # (lower, upper) 95% CI
    risk_factors: List[str]  # Factors that reduce confidence
    strength_factors: List[str]  # Factors that increase confidence
    recommendation: str  # How to interpret/use this confidence
    assessed_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConfidenceScorer:
    """
    Quantifies confidence in research outputs using multi-dimensional assessment.
    """
    
    def __init__(self):
        # Default dimension weights (sum to 1.0)
        self._dimension_weights = {
            ConfidenceDimension.EVIDENCE_QUALITY: 0.25,
            ConfidenceDimension.EVIDENCE_QUANTITY: 0.15,
            ConfidenceDimension.SOURCE_CREDIBILITY: 0.20,
            ConfidenceDimension.METHODOLOGY_RIGOR: 0.15,
            ConfidenceDimension.CONSENSUS: 0.10,
            ConfidenceDimension.RECENCY: 0.05,
            ConfidenceDimension.COMPLETENESS: 0.05,
            ConfidenceDimension.CONSISTENCY: 0.05,
        }
        
        # Thresholds for confidence levels
        self._level_thresholds = {
            "very_high": 0.85,
            "high": 0.70,
            "medium": 0.50,
            "low": 0.30,
            "very_low": 0.0
        }
    
    def set_dimension_weights(self, weights: Dict[ConfidenceDimension, float]) -> None:
        """Set custom dimension weights."""
        # Normalize to sum to 1.0
        total = sum(weights.values())
        self._dimension_weights = {k: v/total for k, v in weights.items()}
    
    async def assess_confidence(
        self,
        research_output: Dict[str, Any],
        evidence: List[Any],
        methodology: Optional[str] = None,
        agent_consensus: Optional[Dict[str, float]] = None,
        custom_weights: Optional[Dict[ConfidenceDimension, float]] = None
    ) -> ConfidenceAssessment:
        """Perform comprehensive confidence assessment."""
        
        weights = custom_weights or self._dimension_weights
        
        # Assess each dimension
        dimensions = []
        
        # 1. Evidence Quality
        eq_score = await self._assess_evidence_quality(evidence)
        dimensions.append(ConfidenceScore(
            dimension=ConfidenceDimension.EVIDENCE_QUALITY,
            score=eq_score["score"],
            weight=weights.get(ConfidenceDimension.EVIDENCE_QUALITY, 0),
            rationale=eq_score["rationale"],
            sub_scores=eq_score.get("sub_scores", {})
        ))
        
        # 2. Evidence Quantity
        eqty_score = await self._assess_evidence_quantity(evidence)
        dimensions.append(ConfidenceScore(
            dimension=ConfidenceDimension.EVIDENCE_QUANTITY,
            score=eqty_score["score"],
            weight=weights.get(ConfidenceDimension.EVIDENCE_QUANTITY, 0),
            rationale=eqty_score["rationale"],
            sub_scores=eqty_score.get("sub_scores", {})
        ))
        
        # 3. Source Credibility
        sc_score = await self._assess_source_credibility(evidence)
        dimensions.append(ConfidenceScore(
            dimension=ConfidenceDimension.SOURCE_CREDIBILITY,
            score=sc_score["score"],
            weight=weights.get(ConfidenceDimension.SOURCE_CREDIBILITY, 0),
            rationale=sc_score["rationale"],
            sub_scores=sc_score.get("sub_scores", {})
        ))
        
        # 4. Methodology Rigor
        mr_score = await self._assess_methodology_rigor(research_output, methodology)
        dimensions.append(ConfidenceScore(
            dimension=ConfidenceDimension.METHODOLOGY_RIGOR,
            score=mr_score["score"],
            weight=weights.get(ConfidenceDimension.METHODOLOGY_RIGOR, 0),
            rationale=mr_score["rationale"],
            sub_scores=mr_score.get("sub_scores", {})
        ))
        
        # 5. Consensus
        cs_score = await self._assess_consensus(agent_consensus, evidence)
        dimensions.append(ConfidenceScore(
            dimension=ConfidenceDimension.CONSENSUS,
            score=cs_score["score"],
            weight=weights.get(ConfidenceDimension.CONSENSUS, 0),
            rationale=cs_score["rationale"],
            sub_scores=cs_score.get("sub_scores", {})
        ))
        
        # 6. Recency
        rc_score = await self._assess_recency(evidence)
        dimensions.append(ConfidenceScore(
            dimension=ConfidenceDimension.RECENCY,
            score=rc_score["score"],
            weight=weights.get(ConfidenceDimension.RECENCY, 0),
            rationale=rc_score["rationale"],
            sub_scores=rc_score.get("sub_scores", {})
        ))
        
        # 7. Completeness
        cp_score = await self._assess_completeness(research_output, evidence)
        dimensions.append(ConfidenceScore(
            dimension=ConfidenceDimension.COMPLETENESS,
            score=cp_score["score"],
            weight=weights.get(ConfidenceDimension.COMPLETENESS, 0),
            rationale=cp_score["rationale"],
            sub_scores=cp_score.get("sub_scores", {})
        ))
        
        # 8. Consistency
        ct_score = await self._assess_consistency(research_output, evidence)
        dimensions.append(ConfidenceScore(
            dimension=ConfidenceDimension.CONSISTENCY,
            score=ct_score["score"],
            weight=weights.get(ConfidenceDimension.CONSISTENCY, 0),
            rationale=ct_score["rationale"],
            sub_scores=ct_score.get("sub_scores", {})
        ))
        
        # Calculate weighted overall score
        overall_score = sum(d.score * d.weight for d in dimensions)
        
        # Calculate confidence interval (bootstrap approximation)
        ci = self._calculate_confidence_interval(dimensions)
        
        # Identify risk and strength factors
        risk_factors = self._identify_risk_factors(dimensions)
        strength_factors = self._identify_strength_factors(dimensions)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(overall_score, dimensions)
        
        return ConfidenceAssessment(
            overall_score=overall_score,
            dimensions=dimensions,
            confidence_interval=ci,
            risk_factors=risk_factors,
            strength_factors=strength_factors,
            recommendation=recommendation,
            metadata={
                "weights_used": {k.value: v for k, v in weights.items()},
                "num_evidence_pieces": len(evidence) if evidence else 0
            }
        )
    
    async def _assess_evidence_quality(self, evidence: List[Any]) -> Dict[str, Any]:
        """Assess quality of evidence."""
        if not evidence:
            return {"score": 0.0, "rationale": "No evidence provided", "sub_scores": {}}
        
        # Extract quality indicators
        relevance_scores = []
        confidence_scores = []
        specificity_scores = []
        
        for ev in evidence:
            # Relevance (if available)
            if hasattr(ev, 'relevance_score'):
                relevance_scores.append(ev.relevance_score)
            elif isinstance(ev, dict) and 'relevance_score' in ev:
                relevance_scores.append(ev['relevance_score'])
            
            # Confidence (if available)
            if hasattr(ev, 'evidence') and hasattr(ev.evidence, 'confidence'):
                confidence_scores.append(ev.evidence.confidence)
            elif isinstance(ev, dict) and 'confidence' in ev:
                confidence_scores.append(ev['confidence'])
            elif hasattr(ev, 'confidence'):
                confidence_scores.append(ev.confidence)
            
            # Specificity - length and detail of content
            content = ""
            if hasattr(ev, 'evidence') and hasattr(ev.evidence, 'content'):
                content = ev.evidence.content
            elif isinstance(ev, dict) and 'content' in ev:
                content = ev['content']
            elif hasattr(ev, 'content'):
                content = ev.content
            
            if content:
                specificity_scores.append(min(len(content) / 500, 1.0))  # Normalize
        
        sub_scores = {}
        if relevance_scores:
            sub_scores["avg_relevance"] = float(np.mean(relevance_scores))
        if confidence_scores:
            sub_scores["avg_confidence"] = float(np.mean(confidence_scores))
        if specificity_scores:
            sub_scores["avg_specificity"] = float(np.mean(specificity_scores))
        
        # Weighted combination
        weights = {"relevance": 0.4, "confidence": 0.4, "specificity": 0.2}
        score = 0.0
        total_weight = 0.0
        
        if relevance_scores:
            score += weights["relevance"] * np.mean(relevance_scores)
            total_weight += weights["relevance"]
        if confidence_scores:
            score += weights["confidence"] * np.mean(confidence_scores)
            total_weight += weights["confidence"]
        if specificity_scores:
            score += weights["specificity"] * np.mean(specificity_scores)
            total_weight += weights["specificity"]
        
        if total_weight > 0:
            score /= total_weight
        
        rationale = (
            f"Evidence quality assessed across {len(evidence)} pieces. "
            f"Avg relevance: {sub_scores.get('avg_relevance', 0):.2f}, "
            f"Avg confidence: {sub_scores.get('avg_confidence', 0):.2f}, "
            f"Avg specificity: {sub_scores.get('avg_specificity', 0):.2f}"
        )
        
        return {"score": float(score), "rationale": rationale, "sub_scores": sub_scores}
    
    async def _assess_evidence_quantity(self, evidence: List[Any]) -> Dict[str, Any]:
        """Assess quantity and diversity of evidence."""
        if not evidence:
            return {"score": 0.0, "rationale": "No evidence provided", "sub_scores": {}}
        
        count = len(evidence)
        
        # Diversity by type
        types = set()
        sources = set()
        for ev in evidence:
            if hasattr(ev, 'evidence') and hasattr(ev.evidence, 'type'):
                types.add(ev.evidence.type.value if hasattr(ev.evidence.type, 'value') else str(ev.evidence.type))
            elif isinstance(ev, dict) and 'type' in ev:
                types.add(ev['type'])
            
            if hasattr(ev, 'evidence') and hasattr(ev.evidence, 'source'):
                sources.add(ev.evidence.source)
            elif isinstance(ev, dict) and 'source' in ev:
                sources.add(ev['source'])
        
        # Score based on count (logarithmic) and diversity
        count_score = min(np.log(count + 1) / np.log(20), 1.0)  # Saturates at ~20 pieces
        type_diversity = min(len(types) / 8, 1.0)  # Expect ~8 types
        source_diversity = min(len(sources) / 10, 1.0)  # Expect ~10 sources
        
        sub_scores = {
            "count": count,
            "count_score": count_score,
            "type_diversity": len(types),
            "type_diversity_score": type_diversity,
            "source_diversity": len(sources),
            "source_diversity_score": source_diversity
        }
        
        score = (count_score * 0.5) + (type_diversity * 0.3) + (source_diversity * 0.2)
        
        rationale = (
            f"Found {count} pieces of evidence across {len(types)} types "
            f"from {len(sources)} sources. "
            f"Count score: {count_score:.2f}, Type diversity: {type_diversity:.2f}, "
            f"Source diversity: {source_diversity:.2f}"
        )
        
        return {"score": float(score), "rationale": rationale, "sub_scores": sub_scores}
    
    async def _assess_source_credibility(self, evidence: List[Any]) -> Dict[str, Any]:
        """Assess credibility of evidence sources."""
        if not evidence:
            return {"score": 0.0, "rationale": "No evidence to assess", "sub_scores": {}}
        
        # Source authority mapping
        source_authority = {
            "sec": 1.0, "reuters": 0.95, "bloomberg": 0.95, "wsj": 0.9,
            "ft": 0.9, "cnbc": 0.8, "marketwatch": 0.75, "seeking_alpha": 0.7,
            "benzinga": 0.65, "analyst_report": 0.9, "earnings_call": 0.95,
            "sec_filing": 1.0, "model_output": 0.8, "agent_output": 0.7,
            "news": 0.7, "general": 0.5
        }
        
        authority_scores = []
        for ev in evidence:
            source = ""
            if hasattr(ev, 'evidence') and hasattr(ev.evidence, 'source'):
                source = ev.evidence.source.lower()
            elif isinstance(ev, dict) and 'source' in ev:
                source = ev['source'].lower()
            elif hasattr(ev, 'source'):
                source = ev.source.lower()
            
            # Match source to authority
            matched = False
            for key, score in source_authority.items():
                if key in source:
                    authority_scores.append(score)
                    matched = True
                    break
            
            if not matched:
                authority_scores.append(0.5)  # Unknown source
        
        avg_authority = float(np.mean(authority_scores)) if authority_scores else 0.5
        
        sub_scores = {
            "avg_authority": avg_authority,
            "min_authority": min(authority_scores) if authority_scores else 0.5,
            "max_authority": max(authority_scores) if authority_scores else 0.5,
            "high_credibility_sources": sum(1 for s in authority_scores if s > 0.8)
        }
        
        score = avg_authority
        
        rationale = (
            f"Source credibility assessed across {len(evidence)} pieces. "
            f"Average authority: {avg_authority:.2f}. "
            f"High credibility sources: {sub_scores['high_credibility_sources']}/{len(evidence)}"
        )
        
        return {"score": score, "rationale": rationale, "sub_scores": sub_scores}
    
    async def _assess_methodology_rigor(
        self,
        research_output: Dict[str, Any],
        methodology: Optional[str]
    ) -> Dict[str, Any]:
        """Assess rigor of methodology used."""
        if not methodology and not research_output.get("methodology"):
            return {
                "score": 0.3,
                "rationale": "No methodology documented",
                "sub_scores": {"documented": 0.0}
            }
        
        method_text = methodology or research_output.get("methodology", "")
        
        # Check for key rigor indicators
        rigor_indicators = {
            "systematic": ["systematic", "structured", "framework", "methodology"],
            "quantitative": ["quantitative", "model", "calculation", "statistical", "regression"],
            "validation": ["validat", "cross-check", "verify", "backtest", "out-of-sample"],
            "peer_review": ["peer review", "reviewed", "validated by", "independent"],
            "transparent": ["transparent", "disclosed", "assumptions", "limitations"],
            "reproducible": ["reproduc", "code available", "data available", "replicable"]
        }
        
        method_lower = method_text.lower()
        indicator_scores = {}
        
        for category, keywords in rigor_indicators.items():
            matches = sum(1 for kw in keywords if kw in method_lower)
            indicator_scores[category] = min(matches / 2, 1.0)  # Max 2 matches per category
        
        # Overall methodology score
        score = float(np.mean(list(indicator_scores.values()))) if indicator_scores else 0.3
        
        # Boost if formal methodology document exists
        if research_output.get("methodology_document"):
            score = min(score + 0.1, 1.0)
        
        rationale = (
            f"Methodology rigor assessed. "
            f"Indicators: {', '.join(f'{k}: {v:.2f}' for k, v in indicator_scores.items())}"
        )
        
        return {"score": score, "rationale": rationale, "sub_scores": indicator_scores}
    
    async def _assess_consensus(
        self,
        agent_consensus: Optional[Dict[str, float]],
        evidence: List[Any]
    ) -> Dict[str, Any]:
        """Assess consensus among agents and sources."""
        if not agent_consensus and not evidence:
            return {"score": 0.5, "rationale": "No consensus data available", "sub_scores": {}}
        
        scores = []
        
        # Agent consensus
        if agent_consensus:
            agreements = sum(1 for v in agent_consensus.values() if v > 0.6)
            disagreements = sum(1 for v in agent_consensus.values() if v < 0.4)
            total = len(agent_consensus)
            
            if total > 0:
                consensus_score = agreements / total
                disagreement_penalty = disagreements / total
                scores.append(max(0, consensus_score - disagreement_penalty * 0.5))
        
        # Source consensus (evidence agreement)
        if evidence:
            # Check for contradictory evidence
            stances = []
            for ev in evidence:
                if hasattr(ev, 'evidence') and ev.evidence.metadata.get("stance"):
                    stances.append(ev.evidence.metadata["stance"])
                elif isinstance(ev, dict) and 'stance' in ev.get('evidence', {}):
                    stances.append(ev['evidence']['stance'])
            
            if stances:
                support = stances.count("support")
                oppose = stances.count("oppose")
                neutral = stances.count("neutral")
                total = len(stances)
                
                if total > 0:
                    source_consensus = (support - oppose) / total
                    scores.append((source_consensus + 1) / 2)  # Normalize to 0-1
        
        if not scores:
            return {"score": 0.5, "rationale": "Insufficient data for consensus assessment", "sub_scores": {}}
        
        avg_score = float(np.mean(scores))
        
        rationale = (
            f"Consensus assessed from {len(scores)} sources. "
            f"Average consensus score: {avg_score:.2f}"
        )
        
        return {"score": avg_score, "rationale": rationale, "sub_scores": {"consensus_score": avg_score}}
    
    async def _assess_recency(self, evidence: List[Any]) -> Dict[str, Any]:
        """Assess recency of evidence."""
        if not evidence:
            return {"score": 0.0, "rationale": "No evidence to assess recency", "sub_scores": {}}
        
        now = datetime.utcnow()
        recency_scores = []
        
        for ev in evidence:
            timestamp = None
            if hasattr(ev, 'evidence') and hasattr(ev.evidence, 'timestamp'):
                timestamp = ev.evidence.timestamp
            elif isinstance(ev, dict) and 'timestamp' in ev.get('evidence', {}):
                timestamp = ev['evidence']['timestamp']
            elif hasattr(ev, 'timestamp'):
                timestamp = ev.timestamp
            
            if timestamp:
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except Exception:
                        continue
                
                age_days = (now - timestamp).days
                
                # Recency scoring
                if age_days <= 7:
                    recency_scores.append(1.0)
                elif age_days <= 30:
                    recency_scores.append(0.8)
                elif age_days <= 90:
                    recency_scores.append(0.6)
                elif age_days <= 180:
                    recency_scores.append(0.4)
                elif age_days <= 365:
                    recency_scores.append(0.2)
                else:
                    recency_scores.append(0.1)
        
        if not recency_scores:
            return {"score": 0.5, "rationale": "No timestamp data available", "sub_scores": {}}
        
        avg_recency = float(np.mean(recency_scores))
        min_recency = min(recency_scores)
        max_recency = max(recency_scores)
        
        rationale = (
            f"Recency assessed across {len(recency_scores)} timestamped pieces. "
            f"Average: {avg_recency:.2f}, Range: [{min_recency:.2f}, {max_recency:.2f}]"
        )
        
        return {
            "score": avg_recency,
            "rationale": rationale,
            "sub_scores": {
                "avg_recency": avg_recency,
                "min_recency": min_recency,
                "max_recency": max_recency,
                "recent_count": sum(1 for s in recency_scores if s > 0.8)
            }
        }
    
    async def _assess_completeness(
        self,
        research_output: Dict[str, Any],
        evidence: List[Any]
    ) -> Dict[str, Any]:
        """Assess completeness of research coverage."""
        # Expected sections for comprehensive research
        expected_sections = [
            "executive_summary", "company_overview", "investment_thesis",
            "key_drivers", "financial_analysis", "valuation",
            "risks", "catalysts", "conclusion"
        ]
        
        present_sections = 0
        for section in expected_sections:
            if research_output.get(section) or any(section in str(ev).lower() for ev in evidence):
                present_sections += 1
        
        coverage = present_sections / len(expected_sections)
        
        # Also check entity coverage if entities specified
        entities_covered = set()
        for ev in evidence:
            if hasattr(ev, 'evidence') and hasattr(ev.evidence, 'entities'):
                entities_covered.update(ev.evidence.entities)
            elif isinstance(ev, dict) and 'entities' in ev.get('evidence', {}):
                entities_covered.update(ev['evidence']['entities'])
        
        sub_scores = {
            "section_coverage": coverage,
            "sections_present": present_sections,
            "total_sections": len(expected_sections),
            "entities_covered": len(entities_covered)
        }
        
        score = coverage
        
        rationale = (
            f"Completeness: {present_sections}/{len(expected_sections)} expected sections covered. "
            f"Entities mentioned: {len(entities_covered)}"
        )
        
        return {"score": score, "rationale": rationale, "sub_scores": sub_scores}
    
    async def _assess_consistency(
        self,
        research_output: Dict[str, Any],
        evidence: List[Any]
    ) -> Dict[str, Any]:
        """Assess internal consistency."""
        # Check for contradictions in research output
        contradictions = 0
        
        # Extract claims from research output
        claims = []
        for key, value in research_output.items():
            if isinstance(value, str) and len(value) > 50:
                claims.append(value.lower())
        
        # Simple contradiction detection
        contradiction_pairs = [
            ("bullish", "bearish"), ("buy", "sell"), ("upgrade", "downgrade"),
            ("increase", "decrease"), ("growth", "decline"), ("outperform", "underperform")
        ]
        
        for claim in claims:
            for pos, neg in contradiction_pairs:
                if pos in claim and neg in claim:
                    contradictions += 1
        
        # Also check evidence for contradictions
        evidence_contradictions = 0
        for ev in evidence:
            if hasattr(ev, 'evidence') and ev.evidence.content:
                content = ev.evidence.content.lower()
                for pos, neg in contradiction_pairs:
                    if pos in content and neg in content:
                        evidence_contradictions += 1
        
        total_contradictions = contradictions + evidence_contradictions
        
        # Score: 1.0 if no contradictions, decreases with contradictions
        score = max(0.0, 1.0 - (total_contradictions * 0.2))
        
        rationale = (
            f"Consistency check found {total_contradictions} potential contradictions "
            f"({contradictions} in output, {evidence_contradictions} in evidence). "
            f"Score: {score:.2f}"
        )
        
        return {
            "score": score,
            "rationale": rationale,
            "sub_scores": {
                "output_contradictions": contradictions,
                "evidence_contradictions": evidence_contradictions
            }
        }
    
    def _calculate_confidence_interval(
        self,
        dimensions: List[ConfidenceScore]
    ) -> Tuple[float, float]:
        """Calculate approximate 95% confidence interval."""
        scores = [d.score for d in dimensions]
        if not scores:
            return (0.0, 1.0)
        
        mean = np.mean(scores)
        std = np.std(scores) if len(scores) > 1 else 0.1
        
        # Approximate CI
        margin = 1.96 * std / np.sqrt(len(scores))
        lower = max(0.0, mean - margin)
        upper = min(1.0, mean + margin)
        
        return (lower, upper)
    
    def _identify_risk_factors(self, dimensions: List[ConfidenceScore]) -> List[str]:
        """Identify factors reducing confidence."""
        risks = []
        
        for dim in dimensions:
            if dim.score < 0.5:
                risks.append(f"Low {dim.dimension.value}: {dim.score:.2f} - {dim.rationale[:100]}")
            elif dim.score < 0.6:
                risks.append(f"Moderate {dim.dimension.value}: {dim.score:.2f}")
        
        return risks[:5]  # Top 5 risks
    
    def _identify_strength_factors(self, dimensions: List[ConfidenceScore]) -> List[str]:
        """Identify factors increasing confidence."""
        strengths = []
        
        for dim in dimensions:
            if dim.score > 0.8:
                strengths.append(f"Strong {dim.dimension.value}: {dim.score:.2f}")
            elif dim.score > 0.7:
                strengths.append(f"Good {dim.dimension.value}: {dim.score:.2f}")
        
        return strengths[:5]  # Top 5 strengths
    
    def _generate_recommendation(
        self,
        overall_score: float,
        dimensions: List[ConfidenceScore]
    ) -> str:
        """Generate recommendation based on confidence."""
        level = "very_low"
        for threshold_name, threshold in reversed(self._level_thresholds.items()):
            if overall_score >= threshold:
                level = threshold_name
                break
        
        recommendations = {
            "very_high": "High confidence - suitable for critical decisions with minimal additional validation.",
            "high": "Good confidence - suitable for most decisions, consider targeted validation on weakest dimensions.",
            "medium": "Moderate confidence - recommend additional evidence gathering before major decisions.",
            "low": "Low confidence - significant additional research required before decision making.",
            "very_low": "Very low confidence - do not base decisions on this output without substantial further research."
        }
        
        base_rec = recommendations.get(level, recommendations["medium"])
        
        # Add dimension-specific guidance
        weak_dims = [d.dimension.value for d in dimensions if d.score < 0.5]
        if weak_dims:
            base_rec += f" Priority areas for improvement: {', '.join(weak_dims[:3])}."
        
        return base_rec
    
    def get_confidence_level(self, score: float) -> str:
        """Get confidence level label from score."""
        for level, threshold in reversed(self._level_thresholds.items()):
            if score >= threshold:
                return level
        return "very_low"
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "dimension_weights": {k.value: v for k, v in self._dimension_weights.items()},
            "level_thresholds": self._level_thresholds
        }


# Global confidence scorer instance
_confidence_scorer: Optional[ConfidenceScorer] = None


def get_confidence_scorer() -> ConfidenceScorer:
    global _confidence_scorer
    if _confidence_scorer is None:
        _confidence_scorer = ConfidenceScorer()
    return _confidence_scorer


async def close_confidence_scorer() -> None:
    global _confidence_scorer
    if _confidence_scorer:
        _confidence_scorer = None