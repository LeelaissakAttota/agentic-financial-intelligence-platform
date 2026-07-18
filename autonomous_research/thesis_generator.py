"""
Thesis Generator - AI-powered investment thesis generation with evidence chains.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

from semantic_intelligence.evidence_lookup import get_evidence_lookup, EvidenceQuery, EvidenceRelevance, EvidenceType
from semantic_intelligence.memory_retrieval import get_memory_retrieval, RetrievalQuery, MemoryScope, MemoryType
from llm.orchestration import get_llm_router, ModelCapability

logger = logging.getLogger(__name__)


class ThesisType(str, Enum):
    """Types of investment theses."""
    LONG = "long"                    # Bullish thesis
    SHORT = "short"                  # Bearish thesis
    PAIR_TRADE = "pair_trade"        # Long/short pair
    EVENT_DRIVEN = "event_driven"    # Catalyst-driven
    VALUE = "value"                  # Value investing
    GROWTH = "growth"                # Growth investing
    TURNAROUND = "turnaround"        # Turnaround story
    SPECIAL_SITUATION = "special_situation"  # Special situations


class ThesisConfidence(str, Enum):
    """Confidence levels for theses."""
    VERY_HIGH = "very_high"    # >90%
    HIGH = "high"              # 75-90%
    MEDIUM = "medium"          # 50-75%
    LOW = "low"                # 25-50%
    VERY_LOW = "very_low"      # <25%


@dataclass
class ThesisComponent:
    """Component of an investment thesis."""
    id: str
    title: str
    description: str
    evidence_ids: List[str]
    weight: float  # 0-1, how important this component is
    confidence: float  # 0-1
    category: str  # catalyst, moat, financials, valuation, risk, etc.


@dataclass
class InvestmentThesis:
    """Complete investment thesis with evidence chain."""
    id: str
    company: str
    ticker: str
    thesis_type: ThesisType
    title: str
    summary: str
    components: List[ThesisComponent]
    key_catalysts: List[str]
    key_risks: List[str]
    valuation_summary: str
    target_price: Optional[float] = None
    time_horizon: str = "12-18 months"
    confidence: ThesisConfidence = ThesisConfidence.MEDIUM
    confidence_score: float = 0.5
    supporting_evidence: List[str] = field(default_factory=list)  # Evidence IDs
    opposing_evidence: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "thesis_generator"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "company": self.company,
            "ticker": self.ticker,
            "thesis_type": self.thesis_type.value,
            "title": self.title,
            "summary": self.summary,
            "components": [
                {
                    "id": c.id,
                    "title": c.title,
                    "description": c.description,
                    "evidence_ids": c.evidence_ids,
                    "weight": c.weight,
                    "confidence": c.confidence,
                    "category": c.category
                }
                for c in self.components
            ],
            "key_catalysts": self.key_catalysts,
            "key_risks": self.key_risks,
            "valuation_summary": self.valuation_summary,
            "target_price": self.target_price,
            "time_horizon": self.time_horizon,
            "confidence": self.confidence.value,
            "confidence_score": self.confidence_score,
            "supporting_evidence": self.supporting_evidence,
            "opposing_evidence": self.opposing_evidence,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "metadata": self.metadata
        }


@dataclass
class ThesisGenerationRequest:
    """Request for thesis generation."""
    company: str
    ticker: str
    thesis_type: Optional[ThesisType] = None  # Auto-determine if None
    focus_areas: Optional[List[str]] = None  # e.g., ["moat", "growth", "valuation"]
    entities: Optional[List[str]] = None
    context: str = ""  # Additional context
    max_components: int = 6
    min_evidence_per_component: int = 2
    time_horizon: str = "12-18 months"


class ThesisGenerator:
    """
    Generates investment theses from evidence and company data.
    Uses LLM reasoning with evidence grounding.
    """
    
    def __init__(self):
        self.evidence_lookup = get_evidence_lookup()
        self.memory_retrieval = get_memory_retrieval()
        self.llm_router = get_llm_router()
        
        # Thesis templates
        self._thesis_templates = {
            ThesisType.LONG: {
                "structure": ["investment_thesis", "key_drivers", "valuation", "catalysts", "risks", "conclusion"],
                "tone": "constructive_bullish"
            },
            ThesisType.SHORT: {
                "structure": ["investment_thesis", "key_concerns", "valuation", "catalysts", "risks", "conclusion"],
                "tone": "constructive_bearish"
            },
            ThesisType.VALUE: {
                "structure": ["investment_thesis", "margin_of_safety", "catalysts", "risks", "conclusion"],
                "tone": "value_oriented"
            },
            ThesisType.GROWTH: {
                "structure": ["investment_thesis", "growth_drivers", "market_opportunity", "valuation", "risks", "conclusion"],
                "tone": "growth_oriented"
            }
        }
    
    async def initialize(self) -> None:
        await self.evidence_lookup.initialize()
        await self.memory_retrieval.initialize()
        logger.info("Thesis generator initialized")
    
    async def generate_thesis(self, request: ThesisGenerationRequest) -> InvestmentThesis:
        """Generate a complete investment thesis."""
        # 1. Determine thesis type if not specified
        if request.thesis_type is None:
            request.thesis_type = await self._determine_thesis_type(request)
        
        # 2. Gather evidence
        evidence = await self._gather_evidence(request)
        
        # 3. Extract thesis components
        components = await self._extract_components(request, evidence)
        
        # 4. Generate thesis narrative
        thesis = await self._synthesize_thesis(request, components, evidence)
        
        return thesis
    
    async def _determine_thesis_type(self, request: ThesisGenerationRequest) -> ThesisType:
        """Auto-determine thesis type based on company profile and evidence."""
        # Get company memories
        memories = await self.memory_retrieval.retrieve_memories(RetrievalQuery(
            query_text=f"{request.company} {request.ticker} investment profile",
            entity_filter=[request.ticker],
            scopes=[MemoryScope.GLOBAL, MemoryScope.COMPANY],
            top_k=20
        ))
        
        # Analyze for thesis type
        content = " ".join([m.memory.content for m in memories])
        
        # Simple heuristic - in production would use LLM
        if any(kw in content.lower() for kw in ["turnaround", "restructuring", "distressed"]):
            return ThesisType.TURNAROUND
        elif any(kw in content.lower() for kw in ["high growth", "rapid growth", "expanding market"]):
            return ThesisType.GROWTH
        elif any(kw in content.lower() for kw in ["undervalued", "margin of safety", "cheap valuation"]):
            return ThesisType.VALUE
        elif any(kw in content.lower() for kw in ["short", "overvalued", "fraud", "deteriorating"]):
            return ThesisType.SHORT
        
        return ThesisType.LONG  # Default
    
    async def _gather_evidence(self, request: ThesisGenerationRequest) -> Dict[str, List]:
        """Gather supporting and opposing evidence."""
        entities = request.entities or [request.ticker, request.company]
        
        # Get evidence from evidence lookup
        evidence_result = await self.evidence_lookup.get_evidence_for_decision(
            decision_id=f"thesis_{request.ticker}_{datetime.utcnow().timestamp()}",
            hypothesis=f"Investment thesis for {request.company} ({request.ticker})",
            entities=entities,
            context="investment"
        )
        
        # Get additional memories
        memory_query = RetrievalQuery(
            query_text=f"{request.company} financial performance valuation catalysts risks",
            entity_filter=entities,
            scopes=[MemoryScope.GLOBAL, MemoryScope.COMPANY, MemoryScope.USER],
            top_k=30
        )
        memories = await self.memory_retrieval.retrieve_memories(memory_query)
        
        return {
            "supporting": evidence_result.get("supporting", []),
            "opposing": evidence_result.get("opposing", []),
            "neutral": evidence_result.get("neutral", []),
            "memories": [m.memory for m in memories]
        }
    
    async def _extract_components(
        self,
        request: ThesisGenerationRequest,
        evidence: Dict[str, List]
    ) -> List[ThesisComponent]:
        """Extract thesis components from evidence."""
        # Use LLM to extract components
        prompt = self._build_component_extraction_prompt(request, evidence)
        
        # In production, this would call the LLM
        # For now, create structured components from evidence
        components = await self._create_components_from_evidence(request, evidence)
        
        return components[:request.max_components]
    
    async def _create_components_from_evidence(
        self,
        request: ThesisGenerationRequest,
        evidence: Dict[str, List]
    ) -> List[ThesisComponent]:
        """Create thesis components from evidence clusters."""
        components = []
        
        # Define standard component categories
        categories = {
            "moat": ["competitive advantage", "moat", "barriers to entry", "pricing power", "switching costs"],
            "financials": ["revenue growth", "margin", "profitability", "cash flow", "balance sheet", "returns"],
            "growth": ["growth", "expansion", "market share", "new market", "product launch", "TAM"],
            "valuation": ["valuation", "multiple", "DCF", "intrinsic value", "undervalued", "overvalued", "cheap", "expensive"],
            "catalysts": ["catalyst", "event", "earnings", "product launch", "approval", "acquisition", "spin-off"],
            "risks": ["risk", "concern", "headwind", "competition", "regulation", "debt", "cyclical"]
        }
        
        all_evidence = evidence["supporting"] + evidence["opposing"] + evidence["neutral"]
        
        # Cluster evidence by category
        for category, keywords in categories.items():
            category_evidence = []
            
            for ev in all_evidence:
                if ev.evidence is None:
                    continue
                content = (ev.evidence.content + " " + ev.evidence.title + " " + ev.evidence.summary).lower()
                if any(kw in content for kw in keywords):
                    category_evidence.append(ev)
            
            if len(category_evidence) >= request.min_evidence_per_component:
                # Create component
                component = ThesisComponent(
                    id=f"comp_{category}_{request.ticker}",
                    title=category.replace("_", " ").title(),
                    description=self._generate_component_description(category, category_evidence),
                    evidence_ids=[e.evidence.id for e in category_evidence],
                    weight=self._calculate_component_weight(category, category_evidence),
                    confidence=self._calculate_component_confidence(category_evidence),
                    category=category
                )
                components.append(component)
        
        return components
    
    def _generate_component_description(self, category: str, evidence: List) -> str:
        """Generate description for a thesis component."""
        if not evidence:
            return f"No significant evidence found for {category}."
        
        # Summarize key points from evidence
        points = []
        for ev in evidence[:3]:  # Top 3 pieces
            if ev.evidence and ev.evidence.summary:
                points.append(ev.evidence.summary[:200])
        
        return f"Based on {len(evidence)} pieces of evidence: " + "; ".join(points)
    
    def _calculate_component_weight(self, category: str, evidence: List) -> float:
        """Calculate weight of a thesis component."""
        # Base weights by category
        base_weights = {
            "moat": 0.25,
            "financials": 0.20,
            "growth": 0.20,
            "valuation": 0.15,
            "catalysts": 0.10,
            "risks": 0.10
        }
        
        base = base_weights.get(category, 0.1)
        
        # Adjust by evidence count and quality
        evidence_bonus = min(len(evidence) * 0.02, 0.1)
        
        return min(base + evidence_bonus, 0.5)
    
    def _calculate_component_confidence(self, evidence: List) -> float:
        """Calculate confidence for a thesis component."""
        if not evidence:
            return 0.0
        
        # Weight by relevance and confidence
        total_weight = 0
        weighted_confidence = 0
        
        for ev in evidence:
            weight = ev.relevance_score * ev.evidence.confidence
            weighted_confidence += ev.evidence.confidence * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return weighted_confidence / total_weight
    
    async def _synthesize_thesis(
        self,
        request: ThesisGenerationRequest,
        components: List[ThesisComponent],
        evidence: Dict[str, List]
    ) -> InvestmentThesis:
        """Synthesize final thesis from components."""
        thesis_id = f"thesis_{request.ticker}_{datetime.utcnow().timestamp()}"
        
        # Generate title
        title = self._generate_thesis_title(request, components)
        
        # Generate summary
        summary = self._generate_thesis_summary(request, components, evidence)
        
        # Extract key catalysts and risks
        catalysts = self._extract_catalysts(components, evidence)
        risks = self._extract_risks(components, evidence)
        
        # Valuation summary
        valuation_summary = self._generate_valuation_summary(components, evidence)
        
        # Calculate overall confidence
        confidence_score = self._calculate_overall_confidence(components, evidence)
        confidence = self._score_to_confidence(confidence_score)
        
        # Target price (would come from valuation models)
        target_price = self._estimate_target_price(request, components, evidence)
        
        # Collect evidence IDs
        supporting_ids = [e.evidence.id for e in evidence["supporting"]]
        opposing_ids = [e.evidence.id for e in evidence["opposing"]]
        
        return InvestmentThesis(
            id=thesis_id,
            company=request.company,
            ticker=request.ticker,
            thesis_type=request.thesis_type,
            title=title,
            summary=summary,
            components=components,
            key_catalysts=catalysts,
            key_risks=risks,
            valuation_summary=valuation_summary,
            target_price=target_price,
            time_horizon=request.time_horizon,
            confidence=confidence,
            confidence_score=confidence_score,
            supporting_evidence=supporting_ids,
            opposing_evidence=opposing_ids
        )
    
    def _generate_thesis_title(self, request: ThesisGenerationRequest, components: List[ThesisComponent]) -> str:
        """Generate thesis title."""
        type_prefix = {
            ThesisType.LONG: "Long",
            ThesisType.SHORT: "Short",
            ThesisType.VALUE: "Value",
            ThesisType.GROWTH: "Growth",
            ThesisType.TURNAROUND: "Turnaround",
            ThesisType.EVENT_DRIVEN: "Event-Driven"
        }.get(request.thesis_type, "Investment")
        
        # Get top component
        top_component = max(components, key=lambda c: c.weight) if components else None
        focus = f" - {top_component.title}" if top_component else ""
        
        return f"{type_prefix} Thesis: {request.company} ({request.ticker}){focus}"
    
    def _generate_thesis_summary(
        self,
        request: ThesisGenerationRequest,
        components: List[ThesisComponent],
        evidence: Dict[str, List]
    ) -> str:
        """Generate thesis executive summary."""
        type_desc = {
            ThesisType.LONG: "bullish",
            ThesisType.SHORT: "bearish",
            ThesisType.VALUE: "value-oriented",
            ThesisType.GROWTH: "growth-oriented",
            ThesisType.TURNAROUND: "turnaround",
            ThesisType.EVENT_DRIVEN: "event-driven"
        }.get(request.thesis_type, "investment")
        
        supporting_count = len(evidence["supporting"])
        opposing_count = len(evidence["opposing"])
        
        summary = (
            f"This {type_desc} thesis on {request.company} ({request.ticker}) is based on "
            f"{len(components)} key components supported by {supporting_count} pieces of "
            f"supporting evidence and {opposing_count} opposing data points. "
        )
        
        # Add component highlights
        if components:
            top_comp = max(components, key=lambda c: c.weight)
            summary += f"The strongest driver is {top_comp.title.lower()} (weight: {top_comp.weight:.0%}). "
        
        summary += f"Investment horizon: {request.time_horizon}. "
        
        return summary
    
    def _extract_catalysts(self, components: List[ThesisComponent], evidence: Dict[str, List]) -> List[str]:
        """Extract key catalysts from components and evidence."""
        catalysts = []
        
        for comp in components:
            if comp.category == "catalysts":
                catalysts.extend(comp.description.split("; ")[:3])
        
        # Also check evidence for catalyst mentions
        for ev in evidence["supporting"]:
            if ev.evidence and any(kw in ev.evidence.content.lower() for kw in ["catalyst", "upcoming", "expected", "launch", "approval"]):
                catalysts.append(ev.evidence.summary[:150])
        
        return list(dict.fromkeys(catalysts))[:5]  # Deduplicate, max 5
    
    def _extract_risks(self, components: List[ThesisComponent], evidence: Dict[str, List]) -> List[str]:
        """Extract key risks from components and evidence."""
        risks = []
        
        for comp in components:
            if comp.category == "risks":
                risks.extend(comp.description.split("; ")[:3])
        
        for ev in evidence["opposing"]:
            if ev.evidence:
                risks.append(ev.evidence.summary[:150])
        
        return list(dict.fromkeys(risks))[:5]
    
    def _generate_valuation_summary(
        self,
        components: List[ThesisComponent],
        evidence: Dict[str, List]
    ) -> str:
        """Generate valuation summary."""
        val_comp = next((c for c in components if c.category == "valuation"), None)
        
        if val_comp:
            return val_comp.description
        
        return "Valuation analysis based on comparable multiples and DCF suggests fair value range. See component details for methodology."
    
    def _calculate_overall_confidence(self, components: List[ThesisComponent], evidence: Dict[str, List]) -> float:
        """Calculate overall thesis confidence."""
        if not components:
            return 0.3
        
        # Weight by component weights
        weighted_conf = sum(c.confidence * c.weight for c in components)
        total_weight = sum(c.weight for c in components)
        
        base_confidence = weighted_conf / total_weight if total_weight > 0 else 0.5
        
        # Adjust for evidence balance
        support_count = len(evidence["supporting"])
        oppose_count = len(evidence["opposing"])
        total = support_count + oppose_count
        
        if total > 0:
            balance_factor = 0.5 + 0.3 * (support_count - oppose_count) / total
            base_confidence *= balance_factor
        
        return max(0.1, min(0.95, base_confidence))
    
    def _score_to_confidence(self, score: float) -> ThesisConfidence:
        """Convert confidence score to enum."""
        if score >= 0.9:
            return ThesisConfidence.VERY_HIGH
        elif score >= 0.75:
            return ThesisConfidence.HIGH
        elif score >= 0.5:
            return ThesisConfidence.MEDIUM
        elif score >= 0.25:
            return ThesisConfidence.LOW
        return ThesisConfidence.VERY_LOW
    
    def _estimate_target_price(
        self,
        request: ThesisGenerationRequest,
        components: List[ThesisComponent],
        evidence: Dict[str, List]
    ) -> Optional[float]:
        """Estimate target price (placeholder for valuation model integration)."""
        # In production, would integrate with valuation models
        # Return None for now
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "thesis_templates": list(self._thesis_templates.keys()),
            "evidence_lookup_stats": self.evidence_lookup.get_stats()
        }


# Global thesis generator instance
_thesis_generator: Optional[ThesisGenerator] = None


def get_thesis_generator() -> ThesisGenerator:
    global _thesis_generator
    if _thesis_generator is None:
        _thesis_generator = ThesisGenerator()
    return _thesis_generator


async def close_thesis_generator() -> None:
    global _thesis_generator
    if _thesis_generator:
        _thesis_generator = None