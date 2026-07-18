"""
Research Synthesizer - Synthesizes research from multiple agents into coherent outputs.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

from .thesis_generator import ThesisComponent, ThesisType, InvestmentThesis
from .evidence_ranker import RankedEvidenceSet, EvidenceBundle
from .confidence_scorer import ConfidenceAssessment
from .contradiction_detector import ContradictionAnalysis

logger = logging.getLogger(__name__)


class SynthesisType(str, Enum):
    """Types of research synthesis."""
    COMPREHENSIVE = "comprehensive"       # Full research report
    EXECUTIVE = "executive"               # Executive summary
    INVESTMENT_MEMO = "investment_memo"   # Investment committee memo
    QUICK_TAKE = "quick_take"             # Rapid assessment
    RISK_FOCUSED = "risk_focused"         # Risk-focused analysis
    CATALYST_FOCUSED = "catalyst_focused" # Catalyst-driven


@dataclass
class SynthesisConfig:
    """Configuration for research synthesis."""
    synthesis_type: SynthesisType = SynthesisType.COMPREHENSIVE
    include_evidence_details: bool = True
    include_methodology: bool = True
    include_contradictions: bool = True
    include_confidence: bool = True
    include_agent_debate: bool = True
    max_length_tokens: int = 16000
    target_audience: str = "institutional"  # institutional, retail, internal
    format: str = "markdown"  # markdown, html, json


@dataclass
class SynthesizedReport:
    """Final synthesized research report."""
    id: str
    company: str
    ticker: str
    synthesis_type: SynthesisType
    title: str
    executive_summary: str
    sections: Dict[str, str]
    thesis: Optional[InvestmentThesis] = None
    evidence_bundles: List[Any] = field(default_factory=list)
    confidence_assessment: Optional[ConfidenceAssessment] = None
    contradiction_analysis: Optional[ContradictionAnalysis] = None
    debate_summary: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "company": self.company,
            "ticker": self.ticker,
            "synthesis_type": self.synthesis_type.value,
            "title": self.title,
            "executive_summary": self.executive_summary,
            "sections": self.sections,
            "thesis": self.thesis.to_dict() if self.thesis else None,
            "evidence_bundles": [b.to_dict() if hasattr(b, 'to_dict') else str(b) for b in self.evidence_bundles],
            "confidence_assessment": self.confidence_assessment.__dict__ if self.confidence_assessment else None,
            "contradiction_analysis": self.contradiction_analysis.__dict__ if self.contradiction_analysis else None,
            "debate_summary": self.debate_summary,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


class ResearchSynthesizer:
    """
    Synthesizes research from multiple agents into coherent, publication-ready outputs.
    """
    
    def __init__(self):
        self._report_templates = self._load_templates()
    
    def _load_templates(self) -> Dict[SynthesisType, Dict[str, Any]]:
        """Load report templates for different synthesis types."""
        return {
            SynthesisType.COMPREHENSIVE: {
                "sections": [
                    "executive_summary",
                    "company_overview",
                    "investment_thesis",
                    "key_investment_drivers",
                    "financial_analysis",
                    "valuation_analysis",
                    "catalysts_and_timeline",
                    "risk_assessment",
                    "esg_considerations",
                    "comparative_analysis",
                    "conclusion_and_recommendation",
                    "appendix_evidence",
                    "appendix_methodology"
                ],
                "section_weights": {
                    "executive_summary": 1.0,
                    "investment_thesis": 1.0,
                    "key_investment_drivers": 1.0,
                    "financial_analysis": 0.9,
                    "valuation_analysis": 1.0,
                    "risk_assessment": 1.0,
                    "catalysts_and_timeline": 0.8
                }
            },
            SynthesisType.EXECUTIVE: {
                "sections": [
                    "executive_summary",
                    "investment_thesis",
                    "key_drivers",
                    "valuation_snapshot",
                    "key_risks",
                    "recommendation"
                ],
                "section_weights": {
                    "executive_summary": 1.0,
                    "investment_thesis": 1.0,
                    "recommendation": 1.0
                }
            },
            SynthesisType.INVESTMENT_MEMO: {
                "sections": [
                    "memo_header",
                    "investment_recommendation",
                    "investment_thesis",
                    "key_drivers",
                    "financial_summary",
                    "valuation",
                    "catalysts",
                    "risk_factors",
                    "esg_factors",
                    "capital_allocation",
                    "conclusion"
                ],
                "section_weights": {}
            },
            SynthesisType.QUICK_TAKE: {
                "sections": [
                    "tldr",
                    "thesis",
                    "key_numbers",
                    "bull_case",
                    "bear_case",
                    "verdict"
                ],
                "section_weights": {}
            },
            SynthesisType.RISK_FOCUSED: {
                "sections": [
                    "executive_summary",
                    "risk_overview",
                    "financial_risks",
                    "business_risks",
                    "market_risks",
                    "regulatory_risks",
                    "esg_risks",
                    "risk_mitigation",
                    "downside_scenarios",
                    "conclusion"
                ],
                "section_weights": {
                    "risk_overview": 1.0,
                    "financial_risks": 1.0,
                    "business_risks": 1.0,
                    "downside_scenarios": 1.0
                }
            },
            SynthesisType.CATALYST_FOCUSED: {
                "sections": [
                    "executive_summary",
                    "catalyst_overview",
                    "near_term_catalysts",
                    "medium_term_catalysts",
                    "long_term_catalysts",
                    "catalyst_probability",
                    "positioning",
                    "timeline",
                    "conclusion"
                ],
                "section_weights": {
                    "catalyst_overview": 1.0,
                    "near_term_catalysts": 1.0,
                    "catalyst_probability": 1.0,
                    "timeline": 1.0
                }
            }
        }
    
    async def synthesize_research(
        self,
        company: str,
        ticker: str,
        thesis: Optional[Any] = None,
        evidence_set: Optional[Any] = None,
        confidence: Optional[Any] = None,
        contradictions: Optional[Any] = None,
        debate_result: Optional[Any] = None,
        agent_outputs: Optional[Dict[str, Any]] = None,
        config: Optional[SynthesisConfig] = None
    ) -> SynthesizedReport:
        """Synthesize complete research report from all inputs."""
        
        config = config or SynthesisConfig()
        
        # Get template
        template = self._report_templates.get(config.synthesis_type, self._report_templates[SynthesisType.COMPREHENSIVE])
        
        # Build sections
        sections = {}
        
        for section_name in template["sections"]:
            section_content = await self._generate_section(
                section_name, company, ticker, thesis, evidence_set,
                confidence, contradictions, debate_result, agent_outputs, config
            )
            sections[section_name] = section_content
        
        # Generate executive summary (special handling)
        executive_summary = await self._generate_executive_summary(
            company, ticker, thesis, evidence_set, confidence, config
        )
        
        # Create title
        title = self._generate_title(company, ticker, thesis, config.synthesis_type)
        
        # Build report
        report = SynthesizedReport(
            id=f"report_{ticker}_{datetime.utcnow().timestamp()}",
            company=company,
            ticker=ticker,
            synthesis_type=config.synthesis_type,
            title=title,
            executive_summary=executive_summary,
            sections=sections,
            thesis=thesis,
            evidence_bundles=evidence_set.bundles if evidence_set else [],
            confidence_assessment=confidence,
            contradiction_analysis=contradictions,
            debate_summary=self._summarize_debate(debate_result) if debate_result else None,
            metadata={
                "config": config.__dict__,
                "agent_outputs_used": list(agent_outputs.keys()) if agent_outputs else [],
                "evidence_count": len(evidence_set.supporting) + len(evidence_set.opposing) if evidence_set else 0,
                "template": config.synthesis_type.value
            }
        )
        
        return report
    
    async def _generate_section(
        self,
        section_name: str,
        company: str,
        ticker: str,
        thesis: Optional[Any],
        evidence_set: Optional[Any],
        confidence: Optional[Any],
        contradictions: Optional[Any],
        debate_result: Optional[Any],
        agent_outputs: Optional[Dict[str, Any]],
        config: SynthesisConfig
    ) -> str:
        """Generate a single report section."""
        
        # This is a template-based approach
        # In production, would use LLM with section-specific prompts
        
        section_generators = {
            "executive_summary": self._gen_executive_summary_section,
            "company_overview": self._gen_company_overview_section,
            "investment_thesis": self._gen_investment_thesis_section,
            "key_investment_drivers": self._gen_key_drivers_section,
            "financial_analysis": self._gen_financial_analysis_section,
            "valuation_analysis": self._gen_valuation_section,
            "catalysts_and_timeline": self._gen_catalysts_section,
            "risk_assessment": self._gen_risk_section,
            "esg_considerations": self._gen_esg_section,
            "comparative_analysis": self._gen_comparative_section,
            "conclusion_and_recommendation": self._gen_conclusion_section,
            "appendix_evidence": self._gen_evidence_appendix,
            "appendix_methodology": self._gen_methodology_appendix,
            "memo_header": self._gen_memo_header,
            "investment_recommendation": self._gen_recommendation_section,
            "key_drivers": self._gen_key_drivers_section,
            "valuation_snapshot": self._gen_valuation_snapshot,
            "key_risks": self._gen_key_risks_section,
            "recommendation": self._gen_recommendation_section,
            "tldr": self._gen_tldr_section,
            "thesis": self._gen_thesis_section,
            "key_numbers": self._gen_key_numbers_section,
            "bull_case": self._gen_bull_case_section,
            "bear_case": self._gen_bear_case_section,
            "verdict": self._gen_verdict_section,
            "risk_overview": self._gen_risk_overview_section,
            "financial_risks": self._gen_financial_risks_section,
            "business_risks": self._gen_business_risks_section,
            "market_risks": self._gen_market_risks_section,
            "regulatory_risks": self._gen_regulatory_risks_section,
            "esg_risks": self._gen_esg_risks_section,
            "risk_mitigation": self._gen_risk_mitigation_section,
            "downside_scenarios": self._gen_downside_scenarios_section,
            "catalyst_overview": self._gen_catalyst_overview_section,
            "near_term_catalysts": self._gen_near_term_catalysts_section,
            "medium_term_catalysts": self._gen_medium_term_catalysts_section,
            "long_term_catalysts": self._gen_long_term_catalysts_section,
            "catalyst_probability": self._gen_catalyst_probability_section,
            "positioning": self._gen_positioning_section,
            "timeline": self._gen_timeline_section,
            "capital_allocation": self._gen_capital_allocation_section,
        }
        
        generator = section_generators.get(section_name)
        if generator:
            return await generator(company, ticker, thesis, evidence_set, confidence, contradictions, debate_result, agent_outputs, config)
        
        return f"## {section_name.replace('_', ' ').title()}\n\n[Section content would be generated here]"
    
    # Section generators (simplified - would use LLM in production)
    
    async def _gen_executive_summary_section(self, company, ticker, thesis, evidence_set, confidence, contradictions, debate_result, agent_outputs, config) -> str:
        return f"# Executive Summary\n\n{self._build_exec_summary(company, ticker, thesis, evidence_set, confidence, contradictions)}"
    
    async def _gen_company_overview_section(self, company, ticker, thesis, evidence_set, confidence, contradictions, debate_result, agent_outputs, config) -> str:
        return f"# Company Overview\n\n{company} ({ticker}) is a publicly traded company. Detailed overview would be generated from agent outputs and evidence."
    
    async def _gen_investment_thesis_section(self, company, ticker, thesis, evidence_set, confidence, contradictions, debate_result, agent_outputs, config) -> str:
        if thesis:
            return f"# Investment Thesis\n\n**Thesis Type:** {thesis.thesis_type.value if hasattr(thesis.thesis_type, 'value') else thesis.thesis_type}\n\n**Title:** {thesis.title}\n\n**Summary:** {thesis.summary}\n\n**Confidence:** {thesis.confidence.value if hasattr(thesis.confidence, 'value') else thesis.confidence} ({thesis.confidence_score:.0%})"
        return f"# Investment Thesis\n\nThesis would be generated from evidence and agent analysis."
    
    async def _gen_key_drivers_section(self, company, ticker, thesis, evidence_set, confidence, contradictions, debate_result, agent_outputs, config) -> str:
        content = "# Key Investment Drivers\n\n"
        if thesis and thesis.components:
            for comp in thesis.components:
                content += f"## {comp.title} (Weight: {comp.weight:.0%})\n{comp.description}\n\n"
        else:
            content += "Key drivers would be extracted from evidence and thesis components.\n"
        return content
    
    async def _gen_financial_analysis_section(self, company, ticker, thesis, evidence_set, confidence, contradictions, debate_result, agent_outputs, config) -> str:
        return f"# Financial Analysis\n\nDetailed financial analysis based on {len(evidence_set.supporting) if evidence_set else 0} supporting evidence pieces. Metrics, trends, and peer comparisons."
    
    async def _gen_valuation_section(self, company, ticker, thesis, evidence_set, confidence, contradictions, debate_result, agent_outputs, config) -> str:
        content = "# Valuation Analysis\n\n"
        if thesis and thesis.valuation_summary:
            content += thesis.valuation_summary
        else:
            content += "Valuation analysis using DCF, comparable multiples, and precedent transactions."
        
        if thesis and thesis.target_price:
            content += f"\n\n**Target Price:** ${thesis.target_price:.2f}"
        return content
    
    async def _gen_catalysts_section(self, company, ticker, thesis, evidence_set, confidence, contradictions, debate_result, agent_outputs, config) -> str:
        content = "# Catalysts and Timeline\n\n"
        if thesis and thesis.key_catalysts:
            content += "## Key Catalysts\n"
            for i, catalyst in enumerate(thesis.key_catalysts, 1):
                content += f"{i}. {catalyst}\n"
        else:
            content += "Key catalysts identified from evidence and agent analysis.\n"
        return content
    
    async def _gen_risk_section(self, company, ticker, thesis, evidence_set, confidence, contradictions, debate_result, agent_outputs, config) -> str:
        content = "# Risk Assessment\n\n"
        if thesis and thesis.key_risks:
            content += "## Key Risks\n"
            for i, risk in enumerate(thesis.key_risks, 1):
                content += f"{i}. {risk}\n"
        
        if contradictions and contradictions.contradictions:
            content += "\n## Identified Contradictions\n"
            for c in contradictions.contradictions[:5]:
                content += f"- {c.severity.value}: {c.description}\n"
        
        if evidence_set:
            content += f"\n\nBased on {len(evidence_set.supporting)} supporting and {len(evidence_set.opposing)} opposing evidence pieces."
        return content
    
    async def _gen_esg_section(self, company, ticker, thesis, evidence_set, confidence, contradictions, debate_result, agent_outputs, config) -> str:
        return f"# ESG Considerations\n\nESG analysis would be synthesized from agent outputs and evidence."
    
    async def _gen_comparative_section(self, company, ticker, thesis, evidence_set, confidence, contradictions, debate_result, agent_outputs, config) -> str:
        return f"# Comparative Analysis\n\nPeer comparison and relative valuation analysis."
    
    async def _gen_conclusion_section(self, company, ticker, thesis, evidence_set, confidence, contradictions, debate_result, agent_outputs, config) -> str:
        content = "# Conclusion and Recommendation\n\n"
        
        if thesis:
            rec = "BUY" if thesis.thesis_type in [ThesisType.LONG, ThesisType.VALUE, ThesisType.GROWTH] else "SELL" if thesis.thesis_type == ThesisType.SHORT else "HOLD"
            content += f"**Recommendation: {rec}**\n\n"
            content += f"**Thesis:** {thesis.title}\n\n"
            content += f"**Confidence:** {thesis.confidence.value if hasattr(thesis.confidence, 'value') else thesis.confidence} ({thesis.confidence_score:.0%})\n\n"
        
        if confidence:
            content += f"**Overall Confidence:** {confidence.overall_score:.0%}\n\n"
        
        content += "\n*This report is generated by the Autonomous Financial Intelligence Platform.*"
        return content
    
    async def _gen_evidence_appendix(self, company, ticker, thesis, evidence_set, confidence, contradictions, debate_result, agent_outputs, config) -> str:
        if not evidence_set:
            return "# Appendix: Evidence\n\nNo evidence set provided."
        
        content = "# Appendix: Evidence Details\n\n"
        content += f"## Supporting Evidence ({len(evidence_set.supporting)})\n"
        for i, ev in enumerate(evidence_set.supporting[:20], 1):
            content += f"{i}. **{ev.evidence.title or 'Untitled'}** (Score: {ev.relevance_score:.2f})\n"
            content += f"   Source: {ev.evidence.source} | Type: {ev.evidence.type.value}\n"
            content += f"   {ev.evidence.summary[:200]}...\n\n"
        
        content += f"\n## Opposing Evidence ({len(evidence_set.opposing)})\n"
        for i, ev in enumerate(evidence_set.opposing[:10], 1):
            content += f"{i}. **{ev.evidence.title or 'Untitled'}** (Score: {ev.relevance_score:.2f})\n"
            content += f"   Source: {ev.evidence.source} | Type: {ev.evidence.type.value}\n"
            content += f"   {ev.evidence.summary[:200]}...\n\n"
        
        return content
    
    async def _gen_methodology_appendix(self, company, ticker, thesis, evidence_set, confidence, contradictions, debate_result, agent_outputs, config) -> str:
        return """# Appendix: Methodology

## Data Sources
- SEC filings (10-K, 10-Q, 8-K, DEF 14A)
- Earnings call transcripts
- News articles (Reuters, Bloomberg, WSJ, etc.)
- Analyst reports
- Market data (prices, volumes, fundamentals)

## Analysis Framework
1. Multi-agent research orchestration
2. Evidence retrieval and ranking
3. Thesis generation with evidence grounding
4. Contradiction detection
5. Confidence scoring
6. Multi-agent debate for consensus

## Confidence Scoring
Eight dimensions assessed: Evidence Quality, Quantity, Source Credibility, Methodology Rigor, Consensus, Recency, Completeness, Consistency.

## Limitations
- Based on publicly available data
- Model limitations in reasoning
- Temporal scope of evidence
"""
    
    # Additional section generators (simplified)
    async def _gen_memo_header(self, *args, **kwargs) -> str:
        return "# Investment Memo\n\n**To:** Investment Committee\n**From:** Autonomous Research Engine\n**Date:** " + datetime.utcnow().strftime("%Y-%m-%d")
    
    async def _gen_recommendation_section(self, *args, **kwargs) -> str:
        return "# Recommendation\n\nRecommendation based on thesis and evidence."
    
    async def _gen_valuation_snapshot(self, *args, **kwargs) -> str:
        return "# Valuation Snapshot\n\nKey valuation metrics and target price."
    
    async def _gen_key_risks_section(self, *args, **kwargs) -> str:
        return "# Key Risks\n\nTop risks identified from evidence and contradictions."
    
    async def _gen_tldr_section(self, *args, **kwargs) -> str:
        return "## TL;DR\n\nQuick summary of the investment case."
    
    async def _gen_thesis_section(self, *args, **kwargs) -> str:
        return "# Thesis\n\nMain investment thesis statement."
    
    async def _gen_key_numbers_section(self, *args, **kwargs) -> str:
        return "# Key Numbers\n\nCritical financial metrics and ratios."
    
    async def _gen_bull_case_section(self, *args, **kwargs) -> str:
        return "# Bull Case\n\nArguments supporting the investment."
    
    async def _gen_bear_case_section(self, *args, **kwargs) -> str:
        return "# Bear Case\n\nArguments against the investment."
    
    async def _gen_verdict_section(self, *args, **kwargs) -> str:
        return "# Verdict\n\nFinal recommendation."
    
    async def _gen_risk_overview_section(self, *args, **kwargs) -> str:
        return "# Risk Overview\n\nComprehensive risk assessment."
    
    async def _gen_financial_risks_section(self, *args, **kwargs) -> str:
        return "# Financial Risks\n\nBalance sheet, liquidity, leverage risks."
    
    async def _gen_business_risks_section(self, *args, **kwargs) -> str:
        return "# Business Risks\n\nCompetitive, operational, strategic risks."
    
    async def _gen_market_risks_section(self, *args, **kwargs) -> str:
        return "# Market Risks\n\nMacro, sector, liquidity risks."
    
    async def _gen_regulatory_risks_section(self, *args, **kwargs) -> str:
        return "# Regulatory Risks\n\nCompliance, policy, legal risks."
    
    async def _gen_esg_risks_section(self, *args, **kwargs) -> str:
        return "# ESG Risks\n\nEnvironmental, social, governance risks."
    
    async def _gen_risk_mitigation_section(self, *args, **kwargs) -> str:
        return "# Risk Mitigation\n\nStrategies to mitigate identified risks."
    
    async def _gen_downside_scenarios_section(self, *args, **kwargs) -> str:
        return "# Downside Scenarios\n\nBear case modeling and stress tests."
    
    async def _gen_catalyst_overview_section(self, *args, **kwargs) -> str:
        return "# Catalyst Overview\n\nSummary of all identified catalysts."
    
    async def _gen_near_term_catalysts_section(self, *args, **kwargs) -> str:
        return "# Near-Term Catalysts (0-3 months)\n\nImmediate catalysts."
    
    async def _gen_medium_term_catalysts_section(self, *args, **kwargs) -> str:
        return "# Medium-Term Catalysts (3-12 months)\n\nUpcoming catalysts."
    
    async def _gen_long_term_catalysts_section(self, *args, **kwargs) -> str:
        return "# Long-Term Catalysts (12+ months)\n\nStrategic catalysts."
    
    async def _gen_catalyst_probability_section(self, *args, **kwargs) -> str:
        return "# Catalyst Probability\n\nLikelihood and impact assessment."
    
    async def _gen_positioning_section(self, *args, **kwargs) -> str:
        return "# Positioning\n\nHow to position for catalysts."
    
    async def _gen_timeline_section(self, *args, **kwargs) -> str:
        return "# Timeline\n\nCatalyst timeline and key dates."
    
    async def _gen_capital_allocation_section(self, *args, **kwargs) -> str:
        return "# Capital Allocation\n\nManagement's capital allocation track record."
    
    async def _generate_executive_summary(
        self,
        company: str,
        ticker: str,
        thesis: Optional[Any],
        evidence_set: Optional[Any],
        confidence: Optional[Any],
        config: SynthesisConfig
    ) -> str:
        """Generate executive summary."""
        
        summary = f"# Executive Summary: {company} ({ticker})\n\n"
        
        if thesis:
            rec = "BUY" if thesis.thesis_type in [ThesisType.LONG, ThesisType.VALUE, ThesisType.GROWTH] else "SELL" if thesis.thesis_type == ThesisType.SHORT else "HOLD"
            summary += f"**Recommendation: {rec}**  \n"
            summary += f"**Thesis:** {thesis.title}  \n"
            summary += f"**Confidence:** {thesis.confidence.value if hasattr(thesis.confidence, 'value') else thesis.confidence} ({thesis.confidence_score:.0%})  \n\n"
        
        if confidence:
            summary += f"**Overall Confidence:** {confidence.overall_score:.0%}  \n"
            summary += f"**Confidence Interval:** [{confidence.confidence_interval[0]:.0%}, {confidence.confidence_interval[1]:.0%}]  \n\n"
        
        if evidence_set:
            total_ev = len(evidence_set.supporting) + len(evidence_set.opposing)
            summary += f"**Evidence Base:** {total_ev} pieces ({len(evidence_set.supporting)} supporting, {len(evidence_set.opposing)} opposing)  \n"
        
        if thesis and thesis.key_catalysts:
            summary += f"\n**Key Catalysts:** {', '.join(thesis.key_catalysts[:3])}  \n"
        
        if thesis and thesis.key_risks:
            summary += f"\n**Key Risks:** {', '.join(thesis.key_risks[:3])}  \n"
        
        summary += "\n---\n*Generated by Autonomous Financial Intelligence Platform v2.0*"
        
        return summary
    
    def _generate_title(self, company: str, ticker: str, thesis: Optional[Any], synthesis_type: SynthesisType) -> str:
        """Generate report title."""
        base = f"{company} ({ticker})"
        
        if thesis:
            type_label = {
                ThesisType.LONG: "Long",
                ThesisType.SHORT: "Short",
                ThesisType.VALUE: "Value",
                ThesisType.GROWTH: "Growth",
                ThesisType.TURNAROUND: "Turnaround",
                ThesisType.EVENT_DRIVEN: "Event-Driven"
            }.get(thesis.thesis_type, "Investment")
            base += f" - {type_label} Thesis"
        
        type_suffix = {
            SynthesisType.COMPREHENSIVE: "Comprehensive Research Report",
            SynthesisType.EXECUTIVE: "Executive Summary",
            SynthesisType.INVESTMENT_MEMO: "Investment Memo",
            SynthesisType.QUICK_TAKE: "Quick Take",
            SynthesisType.RISK_FOCUSED: "Risk-Focused Analysis",
            SynthesisType.CATALYST_FOCUSED: "Catalyst-Focused Analysis"
        }.get(synthesis_type, "Research Report")
        
        return f"{base}: {type_suffix}"
    
    def _summarize_debate(self, debate_result: Optional[Any]) -> str:
        """Summarize debate result."""
        if not debate_result:
            return "No debate conducted."
        
        return (
            f"Debate conducted with {len(debate_result.participants)} participants over "
            f"{len(debate_result.rounds)} rounds. "
            f"Consensus: {'Reached' if debate_result.consensus_reached else 'Not reached'}. "
            f"Final confidence: {debate_result.confidence:.0%}."
        )
    
    def _build_exec_summary(self, company, ticker, thesis, evidence_set, confidence, contradictions) -> str:
        """Build executive summary content."""
        content = ""
        
        if thesis:
            rec = "BUY" if thesis.thesis_type in [ThesisType.LONG, ThesisType.VALUE, ThesisType.GROWTH] else "SELL" if thesis.thesis_type == ThesisType.SHORT else "HOLD"
            content += f"**Recommendation: {rec}**  \n"
            content += f"**Thesis:** {thesis.title}  \n"
            content += f"**Confidence:** {thesis.confidence.value if hasattr(thesis.confidence, 'value') else thesis.confidence} ({thesis.confidence_score:.0%})  \n\n"
        
        if evidence_set:
            total = len(evidence_set.supporting) + len(evidence_set.opposing)
            content += f"Based on {total} pieces of evidence ({len(evidence_set.supporting)} supporting, {len(evidence_set.opposing)} opposing).  \n\n"
        
        if thesis and thesis.summary:
            content += f"{thesis.summary}  \n\n"
        
        return content
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "synthesis_types": [st.value for st in SynthesisType],
            "templates": {k.value: v["sections"] for k, v in self._report_templates.items()}
        }


# Global research synthesizer instance
_research_synthesizer: Optional[ResearchSynthesizer] = None


def get_research_synthesizer() -> ResearchSynthesizer:
    global _research_synthesizer
    if _research_synthesizer is None:
        _research_synthesizer = ResearchSynthesizer()
    return _research_synthesizer


async def close_research_synthesizer() -> None:
    global _research_synthesizer
    if _research_synthesizer:
        _research_synthesizer = None