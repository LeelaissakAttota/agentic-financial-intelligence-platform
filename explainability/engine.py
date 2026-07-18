"""
Explainability Module - Generates transparent explanations for AI decisions.

Provides evidence summaries, confidence assessments, alternative viewpoints,
and recommendation rationales without exposing internal reasoning chains.
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import logging

from config.settings import get_settings
from llm.openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)


class ExplanationType(str, Enum):
    """Types of explanations."""
    RECOMMENDATION = "recommendation"      # Why this recommendation
    RISK_ASSESSMENT = "risk_assessment"    # Why this risk level
    SENTIMENT = "sentiment"                # Why this sentiment
    PATTERN = "pattern"                    # Why this pattern detected
    CONSENSUS = "consensus"                # Why this consensus
    CONFLICT = "conflict"                  # Why conflicting signals
    TREND = "trend"                        # Why this trend identified


class EvidenceType(str, Enum):
    """Types of evidence."""
    DOCUMENT = "document"          # SEC filing, earnings transcript
    NEWS_ARTICLE = "news_article"  # News source
    MARKET_DATA = "market_data"    # Price, volume, indicators
    ANALYST_REPORT = "analyst_report"
    FINANCIAL_METRIC = "financial_metric"
    TECHNICAL_INDICATOR = "technical_indicator"
    ENTITY_RELATIONSHIP = "entity_relationship"
    HISTORICAL_PATTERN = "historical_pattern"
    STATISTICAL_MODEL = "statistical_model"
    EXPERT_OPINION = "expert_opinion"


@dataclass
class Evidence:
    """Single piece of evidence supporting a conclusion."""
    evidence_id: str
    type: EvidenceType
    source: str                    # Document title, article URL, etc.
    excerpt: str                   # Relevant excerpt (max 500 chars)
    relevance_score: float         # 0-1 relevance to conclusion
    citation: str                  # Formatted citation
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AlternativeScenario:
    """Alternative viewpoint or scenario."""
    scenario_id: str
    name: str                      # e.g., "Bear Case", "Base Case", "Bull Case"
    description: str
    probability: float             # 0-1 estimated probability
    key_drivers: List[str]
    supporting_evidence: List[str]  # Evidence IDs
    contradicting_evidence: List[str]
    impact_summary: str


@dataclass
class RiskFactor:
    """Identified risk factor."""
    risk_id: str
    category: str                  # market, credit, operational, liquidity, regulatory
    description: str
    severity: str                  # critical, high, medium, low
    likelihood: float              # 0-1
    impact: str                    # Description of potential impact
    mitigation: Optional[str]
    evidence_ids: List[str]


@dataclass
class Assumption:
    """Key assumption underlying the analysis."""
    assumption_id: str
    description: str
    confidence: float              # 0-1
    sensitivity: str               # high, medium, low - how much conclusion changes if wrong
    evidence_ids: List[str]
    if_wrong: str                  # What happens if this assumption is wrong


@dataclass
class Explanation:
    """Complete explanation for a decision/conclusion."""
    explanation_id: str
    explanation_type: ExplanationType
    question: str                  # Original question/decision context
    conclusion: str                # The decision or recommendation
    confidence: float              # Overall confidence 0-1

    # User-facing explanation
    summary: str                   # 2-3 sentence summary
    detailed_explanation: str      # Full explanation

    # Evidence and sources
    evidence: List[Evidence] = field(default_factory=list)
    sources_used: List[str] = field(default_factory=list)

    # Alternatives and risks
    alternatives: List[AlternativeScenario] = field(default_factory=list)
    risk_factors: List[RiskFactor] = field(default_factory=list)
    assumptions: List[Assumption] = field(default_factory=list)

    # Technical details (for debugging/audit)
    model_used: Optional[str] = None
    tokens_used: int = 0
    latency_ms: float = 0.0
    internal_reasoning: Optional[str] = None  # Not exposed to users

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    session_id: Optional[str] = None


class EvidenceCollector:
    """Collects and ranks evidence for explanations."""

    def __init__(self):
        self.evidence_store: Dict[str, Evidence] = {}

    def add_evidence(self, evidence: Evidence) -> str:
        """Add evidence to store."""
        self.evidence_store[evidence.evidence_id] = evidence
        return evidence.evidence_id

    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        """Get evidence by ID."""
        return self.evidence_store.get(evidence_id)

    def get_evidence_by_ids(self, ids: List[str]) -> List[Evidence]:
        """Get multiple evidence items."""
        return [self.evidence_store[eid] for eid in ids if eid in self.evidence_store]

    def find_relevant_evidence(
        self,
        query: str,
        company: Optional[str] = None,
        evidence_types: Optional[List[EvidenceType]] = None,
        min_relevance: float = 0.3,
        limit: int = 10
    ) -> List[Evidence]:
        """Find evidence relevant to a query."""
        # In production, would use semantic search
        # For now, simple keyword matching
        results = []
        query_lower = query.lower()
        query_terms = set(query_lower.split())

        for evidence in self.evidence_store.values():
            if evidence_types and evidence.type not in evidence_types:
                continue
            if company and company.lower() not in evidence.source.lower() and company.lower() not in evidence.excerpt.lower():
                continue

            # Simple relevance scoring
            excerpt_terms = set(evidence.excerpt.lower().split())
            overlap = len(query_terms & excerpt_terms)
            relevance = overlap / max(len(query_terms), 1)

            if relevance >= min_relevance:
                evidence.relevance_score = relevance
                results.append(evidence)

        results.sort(key=lambda e: e.relevance_score, reverse=True)
        return results[:limit]

    def extract_from_tool_result(
        self,
        tool_name: str,
        result: Dict[str, Any],
        company: str
    ) -> List[Evidence]:
        """Extract evidence from tool execution results."""
        evidence_list = []

        # Financial metrics
        if "financial_metrics" in result:
            for metric, value in result["financial_metrics"].items():
                evidence = Evidence(
                    evidence_id=str(uuid.uuid4())[:8],
                    type=EvidenceType.FINANCIAL_METRIC,
                    source=f"{tool_name} analysis",
                    excerpt=f"{metric}: {value}",
                    relevance_score=0.8,
                    citation=f"{tool_name} financial analysis for {company}",
                    metadata={"metric": metric, "value": value}
                )
                evidence_list.append(evidence)

        # Risk factors
        if "risk_factors" in result:
            for risk in result["risk_factors"]:
                evidence = Evidence(
                    evidence_id=str(uuid.uuid4())[:8],
                    type=EvidenceType.FINANCIAL_METRIC,
                    source=f"{tool_name} risk assessment",
                    excerpt=risk.get("description", str(risk))[:500],
                    relevance_score=0.7,
                    citation=f"{tool_name} risk analysis for {company}",
                    metadata=risk
                )
                evidence_list.append(evidence)

        # News/articles
        if "articles" in result:
            for article in result["articles"][:5]:
                evidence = Evidence(
                    evidence_id=str(uuid.uuid4())[:8],
                    type=EvidenceType.NEWS_ARTICLE,
                    source=article.get("source", "Unknown"),
                    excerpt=article.get("summary", article.get("title", ""))[:500],
                    relevance_score=0.6,
                    citation=f"{article.get('source', 'News')} - {article.get('title', 'Untitled')}",
                    metadata=article
                )
                evidence_list.append(evidence)

        # Technical indicators
        if "technical_indicators" in result:
            for indicator, value in result["technical_indicators"].items():
                evidence = Evidence(
                    evidence_id=str(uuid.uuid4())[:8],
                    type=EvidenceType.TECHNICAL_INDICATOR,
                    source=f"{tool_name} technical analysis",
                    excerpt=f"{indicator}: {value}",
                    relevance_score=0.7,
                    citation=f"{tool_name} technical analysis for {company}",
                    metadata={"indicator": indicator, "value": value}
                )
                evidence_list.append(evidence)

        # Store and return
        for ev in evidence_list:
            self.evidence_store[ev.evidence_id] = ev

        return evidence_list


class ExplanationGenerator:
    """Generates human-readable explanations for AI decisions."""

    def __init__(self):
        self.settings = get_settings()
        self.llm = OpenRouterClient()
        self.evidence_collector = EvidenceCollector()

        # Explanation templates by type
        self.templates = {
            ExplanationType.RECOMMENDATION: """
Generate a clear explanation for an investment recommendation.

Context:
- Company: {company}
- Question: {question}
- Recommendation: {conclusion}
- Confidence: {confidence}
- Evidence: {evidence_summary}

Provide:
1. 2-3 sentence summary
2. Detailed explanation with evidence citations
2. Key risk factors
3. Main assumptions
4. Alternative scenarios (bear/base/bull)
5. What would change the recommendation

Format as structured response.
""",
            ExplanationType.RISK_ASSESSMENT: """
Explain a risk assessment conclusion.

Context:
- Company: {company}
- Risk Category: {risk_category}
- Assessment: {conclusion}
- Confidence: {confidence}
- Evidence: {evidence_summary}

Provide clear explanation of risk level, key drivers, and mitigations.
""",
            ExplanationType.CONSENSUS: """
Explain how consensus was reached among multiple agents.

Context:
- Question: {question}
- Consensus: {conclusion}
- Agreement Level: {confidence}
- Participating Agents: {agents}
- Evidence: {evidence_summary}

Explain agreement/disagreement points and why consensus was reached.
"""
        }

    async def generate_explanation(
        self,
        explanation_type: ExplanationType,
        question: str,
        conclusion: str,
        confidence: float,
        evidence_ids: List[str],
        company: Optional[str] = None,
        alternatives: Optional[List[AlternativeScenario]] = None,
        risk_factors: Optional[List[RiskFactor]] = None,
        assumptions: Optional[List[Assumption]] = None,
        session_id: Optional[str] = None,
        internal_reasoning: Optional[str] = None
    ) -> Explanation:
        """Generate complete explanation."""

        # Get evidence
        evidence = self.evidence_collector.get_evidence_by_ids(evidence_ids)

        # Build evidence summary for LLM
        evidence_summary = self._format_evidence_summary(evidence)

        # Select template
        template = self.templates.get(explanation_type, self.templates[ExplanationType.RECOMMENDATION])

        # Fill template
        prompt = template.format(
            company=company or "the company",
            question=question,
            conclusion=conclusion,
            confidence=f"{confidence:.0%}",
            evidence_summary=evidence_summary,
            agents="financial_document, sentiment, risk, competitive, news, market_data, investment_summary"
        )

        # Generate explanation using LLM
        response = await self.llm.agenerate_json(prompt)

        # Parse response
        summary = response.get("summary", "")
        detailed = response.get("detailed_explanation", "")
        risks = response.get("risk_factors", [])
        assumptions = response.get("assumptions", [])
        alt_scenarios = response.get("alternatives", [])

        # Build alternative scenarios if not provided
        if not alternatives:
            alternatives = self._build_default_alternatives(conclusion, confidence)

        # Build risk factors if not provided
        if not risk_factors:
            risk_factors = self._extract_risk_factors(evidence, risks)

        # Build assumptions if not provided
        if not assumptions:
            assumptions = self._extract_assumptions(evidence, assumptions)

        # Create explanation
        explanation = Explanation(
            explanation_id=str(uuid.uuid4())[:8],
            explanation_type=explanation_type,
            question=question,
            conclusion=conclusion,
            confidence=confidence,
            summary=summary,
            detailed_explanation=detailed,
            evidence=evidence,
            sources_used=[e.source for e in evidence],
            alternatives=alternatives,
            risk_factors=risk_factors,
            assumptions=assumptions,
            internal_reasoning=internal_reasoning,
            session_id=session_id
        )

        return explanation

    def _format_evidence_summary(self, evidence: List[Evidence]) -> str:
        """Format evidence for LLM prompt."""
        if not evidence:
            return "No evidence provided."

        lines = []
        for i, e in enumerate(evidence, 1):
            lines.append(f"[{i}] {e.type.value}: {e.source}")
            lines.append(f"    Excerpt: {e.excerpt[:300]}")
            lines.append(f"    Relevance: {e.relevance_score:.0%}")
        return "\n".join(lines)

    def _build_default_alternatives(
        self,
        conclusion: str,
        confidence: float
    ) -> List[AlternativeScenario]:
        """Build default alternative scenarios."""
        return [
            AlternativeScenario(
                scenario_id="bear",
                name="Bear Case",
                description=f"Negative outcome where {conclusion.lower()} does not materialize",
                probability=max(0.1, (1 - confidence) * 0.6),
                key_drivers=["Earnings miss", "Market downturn", "Competitive pressure"],
                supporting_evidence=[],
                contradicting_evidence=[],
                impact_summary="Significant downside risk"
            ),
            AlternativeScenario(
                scenario_id="base",
                name="Base Case",
                description=f"Moderate outcome consistent with {conclusion.lower()}",
                probability=confidence * 0.7,
                key_drivers=["In-line earnings", "Stable margins", "Market performs as expected"],
                supporting_evidence=[],
                contradicting_evidence=[],
                impact_summary="Expected outcome"
            ),
            AlternativeScenario(
                scenario_id="bull",
                name="Bull Case",
                description=f"Positive outcome exceeding {conclusion.lower()}",
                probability=max(0.1, confidence * 0.4),
                key_drivers=["Earnings beat", "New product success", "Market expansion"],
                supporting_evidence=[],
                contradicting_evidence=[],
                impact_summary="Significant upside potential"
            )
        ]

    def _extract_risk_factors(self, evidence: List[Evidence], llm_risks: List[Dict]) -> List[RiskFactor]:
        """Extract risk factors from evidence and LLM output."""
        risks = []

        # Add LLM-identified risks
        for r in llm_risks:
            if isinstance(r, dict):
                risks.append(RiskFactor(
                    risk_id=str(uuid.uuid4())[:8],
                    category=r.get("category", "market"),
                    description=r.get("description", ""),
                    severity=r.get("severity", "medium"),
                    likelihood=r.get("likelihood", 0.5),
                    impact=r.get("impact", ""),
                    mitigation=r.get("mitigation"),
                    evidence_ids=r.get("evidence_ids", [])
                ))

        return risks

    def _extract_assumptions(self, evidence: List[Evidence], llm_assumptions: List[Dict]) -> List[Assumption]:
        """Extract key assumptions."""
        assumptions = []

        for a in llm_assumptions:
            if isinstance(a, dict):
                assumptions.append(Assumption(
                    assumption_id=str(uuid.uuid4())[:8],
                    description=a.get("description", ""),
                    confidence=a.get("confidence", 0.7),
                    sensitivity=a.get("sensitivity", "medium"),
                    evidence_ids=a.get("evidence_ids", []),
                    if_wrong=a.get("if_wrong", "")
                ))

        return assumptions


class ExplainabilityEngine:
    """Main engine for generating explanations across the system."""

    def __init__(self):
        self.generator = ExplanationGenerator()
        self.explanations: Dict[str, Explanation] = {}

    async def explain_recommendation(
        self,
        question: str,
        recommendation: str,
        confidence: float,
        evidence_ids: List[str],
        company: Optional[str] = None,
        session_id: Optional[str] = None,
        internal_reasoning: Optional[str] = None
    ) -> Explanation:
        """Explain an investment recommendation."""
        return await self.generator.generate_explanation(
            explanation_type=ExplanationType.RECOMMENDATION,
            question=question,
            conclusion=recommendation,
            confidence=confidence,
            evidence_ids=evidence_ids,
            company=company,
            session_id=session_id,
            internal_reasoning=internal_reasoning
        )

    async def explain_risk_assessment(
        self,
        company: str,
        risk_category: str,
        assessment: str,
        confidence: float,
        evidence_ids: List[str],
        session_id: Optional[str] = None
    ) -> Explanation:
        """Explain a risk assessment."""
        return await self.generator.generate_explanation(
            explanation_type=ExplanationType.RISK_ASSESSMENT,
            question=f"What is the {risk_category} risk for {company}?",
            conclusion=assessment,
            confidence=confidence,
            evidence_ids=evidence_ids,
            company=company,
            session_id=session_id
        )

    async def explain_consensus(
        self,
        question: str,
        consensus: str,
        agreement: float,
        agents: List[str],
        evidence_ids: List[str],
        company: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Explanation:
        """Explain multi-agent consensus."""
        return await self.generator.generate_explanation(
            explanation_type=ExplanationType.CONSENSUS,
            question=question,
            conclusion=consensus,
            confidence=agreement,
            evidence_ids=evidence_ids,
            company=company,
            session_id=session_id
        )

    async def explain_conflict(
        self,
        company: str,
        conflicting_views: List[Dict[str, Any]],
        evidence_ids: List[str],
        session_id: Optional[str] = None
    ) -> Explanation:
        """Explain conflicting signals."""
        return await self.generator.generate_explanation(
            explanation_type=ExplanationType.CONFLICT,
            question=f"Conflicting views on {company}",
            conclusion=f"Multiple perspectives identified for {company}",
            confidence=0.5,
            evidence_ids=evidence_ids,
            company=company,
            session_id=session_id
        )

    def get_explanation(self, explanation_id: str) -> Optional[Explanation]:
        """Get explanation by ID."""
        return self.explanations.get(explanation_id)

    def list_explanations(self, session_id: Optional[str] = None) -> List[Explanation]:
        """List explanations, optionally filtered by session."""
        if session_id:
            return [e for e in self.explanations.values() if e.session_id == session_id]
        return list(self.explanations.values())


# Global instance
_explainability_engine: Optional[ExplainabilityEngine] = None


def get_explainability_engine() -> ExplainabilityEngine:
    """Get global explainability engine."""
    global _explainability_engine
    if _explainability_engine is None:
        _explainability_engine = ExplainabilityEngine()
    return _explainability_engine