"""
Contradiction Detector - Identifies and analyzes contradictions in research.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

import numpy as np

logger = logging.getLogger(__name__)


class ContradictionType(str, Enum):
    """Types of contradictions detected."""
    DIRECT = "direct"                    # Direct opposing statements
    NUMERICAL = "numerical"              # Conflicting numbers/values
    TEMPORAL = "temporal"                # Timeline inconsistencies
    LOGICAL = "logical"                  # Logical inconsistencies
    SOURCE = "source"                    # Source credibility conflicts
    METHODOLOGICAL = "methodological"    # Methodology disagreements


class ContradictionSeverity(str, Enum):
    """Severity levels for contradictions."""
    CRITICAL = "critical"    # Fundamental contradiction invalidating conclusion
    HIGH = "high"            # Significant contradiction requiring resolution
    MEDIUM = "medium"        # Notable contradiction affecting confidence
    LOW = "low"              # Minor contradiction, easily reconciled
    INFORMATIONAL = "informational"  # Noted for completeness


@dataclass
class Contradiction:
    """Detected contradiction between claims."""
    id: str
    type: ContradictionType
    severity: ContradictionSeverity
    claim_1: str
    claim_2: str
    source_1: str
    source_2: str
    evidence_1: List[str] = field(default_factory=list)
    evidence_2: List[str] = field(default_factory=list)
    description: str = ""
    resolution_suggestion: Optional[str] = None
    detected_at: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolution: Optional[str] = None


@dataclass
class ContradictionAnalysis:
    """Complete contradiction analysis for research."""
    contradictions: List[Contradiction]
    summary: Dict[str, Any]
    impact_assessment: str
    resolution_priority: List[str]
    confidence_impact: float  # How much contradictions reduce overall confidence
    analyzed_at: datetime = field(default_factory=datetime.utcnow)


class ContradictionDetector:
    """
    Detects and analyzes contradictions in research outputs and evidence.
    """
    
    def __init__(self):
        # Contradiction patterns
        self._direct_patterns = [
            # Financial direction
            (["bullish", "buy", "long", "positive", "outperform", "upgrade", "growth", "increase"],
             ["bearish", "sell", "short", "negative", "underperform", "downgrade", "decline", "decrease"]),
            
            # Valuation
            (["undervalued", "cheap", "discount", "margin of safety", "intrinsic value higher"],
             ["overvalued", "expensive", "premium", "intrinsic value lower", "bubble"]),
            
            # Quality
            (["strong moat", "competitive advantage", "pricing power", "high barriers"],
             ["no moat", "commodity", "low barriers", "intense competition"]),
            
            # Financial health
            (["strong balance sheet", "low debt", "high cash", "generating cash"],
             ["weak balance sheet", "high debt", "low cash", "burning cash"]),
            
            # Growth
            (["accelerating growth", "market share gains", "expanding TAM"],
             ["decelerating growth", "market share losses", "shrinking TAM"]),
        ]
        
        # Numerical contradiction tolerance
        self._numerical_tolerance = {
            "price_target": 0.15,        # 15% difference
            "revenue": 0.10,             # 10% difference
            "eps": 0.10,                 # 10% difference
            "margin": 0.05,              # 5% absolute difference
            "growth_rate": 0.20,         # 20% relative difference
            "market_cap": 0.10,          # 10% difference
            "pe_ratio": 0.20,            # 20% difference
            "default": 0.15
        }
        
        # Temporal patterns
        self._temporal_keywords = [
            "will", "expected to", "projected", "forecast", "estimate",
            "by 2024", "by 2025", "in 2024", "in 2025", "next quarter",
            "next year", "fiscal 2024", "fiscal 2025"
        ]
    
    async def detect_contradictions(
        self,
        research_output: Dict[str, Any],
        evidence: List[Any],
        claims: Optional[List[str]] = None
    ) -> ContradictionAnalysis:
        """Detect all contradictions in research and evidence."""
        
        all_claims = claims or []
        
        # Extract claims from research output
        if not all_claims:
            all_claims = self._extract_claims(research_output)
        
        # Add claims from evidence
        for ev in evidence:
            if hasattr(ev, 'evidence') and ev.evidence.content:
                all_claims.extend(self._extract_claims_from_text(ev.evidence.content))
            elif isinstance(ev, dict) and 'content' in ev.get('evidence', {}):
                all_claims.extend(self._extract_claims_from_text(ev['evidence']['content']))
        
        contradictions = []
        
        # 1. Direct contradictions (semantic opposites)
        contradictions.extend(await self._detect_direct_contradictions(all_claims, evidence))
        
        # 2. Numerical contradictions
        contradictions.extend(await self._detect_numerical_contradictions(research_output, evidence))
        
        # 3. Temporal contradictions
        contradictions.extend(await self._detect_temporal_contradictions(evidence))
        
        # 4. Logical contradictions
        contradictions.extend(await self._detect_logical_contradictions(all_claims))
        
        # 5. Source contradictions
        contradictions.extend(await self._detect_source_contradictions(evidence))
        
        # 6. Methodological contradictions
        contradictions.extend(await self._detect_methodological_contradictions(evidence))
        
        # Analyze impact
        analysis = self._analyze_contradictions(contradictions)
        
        return ContradictionAnalysis(
            contradictions=contradictions,
            summary=analysis["summary"],
            impact_assessment=analysis["impact"],
            resolution_priority=analysis["priority"],
            confidence_impact=analysis["confidence_impact"]
        )
    
    def _extract_claims(self, research_output: Dict[str, Any]) -> List[str]:
        """Extract key claims from research output."""
        claims = []
        
        for key, value in research_output.items():
            if isinstance(value, str) and len(value) > 30:
                # Split into sentences
                sentences = value.replace('\n', ' ').split('. ')
                for sent in sentences:
                    sent = sent.strip()
                    if len(sent) > 20:
                        claims.append(sent)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and len(item) > 20:
                        claims.append(item)
        
        return claims
    
    def _extract_claims_from_text(self, text: str) -> List[str]:
        """Extract claims from text."""
        claims = []
        sentences = text.replace('\n', ' ').split('. ')
        for sent in sentences:
            sent = sent.strip()
            if len(sent) > 20 and any(keyword in sent.lower() for keyword in [
                "is", "will", "expected", "projected", "estimated", "shows", "indicates",
                "suggests", "confirms", "reveals", "demonstrates", "outperforms", "underperforms"
            ]):
                claims.append(sent)
        return claims
    
    async def _detect_direct_contradictions(
        self,
        claims: List[str],
        evidence: List[Any]
    ) -> List[Contradiction]:
        """Detect direct semantic contradictions."""
        contradictions = []
        
        # Check claims against each other
        for i, claim1 in enumerate(claims):
            for claim2 in claims[i+1:]:
                for pos_group, neg_group in self._direct_patterns:
                    if self._has_opposite_terms(claim1, claim2, pos_group, neg_group):
                        contradiction = Contradiction(
                            id=f"direct_{len(contradictions)}_{datetime.utcnow().timestamp()}",
                            type=ContradictionType.DIRECT,
                            severity=self._assess_severity(claim1, claim2, "direct"),
                            claim_1=claim1[:500],
                            claim_2=claim2[:500],
                            source_1="research_output",
                            source_2="research_output",
                            description=f"Direct contradiction detected: '{claim1[:100]}...' vs '{claim2[:100]}...'"
                        )
                        contradiction.resolution_suggestion = (
                            "Review evidence supporting each claim. "
                            "Determine which claim is better supported by high-quality evidence."
                        )
                        contradictions.append(contradiction)
        
        # Check claims against evidence
        for claim in claims:
            for ev in evidence:
                ev_content = ""
                if hasattr(ev, 'evidence') and ev.evidence.content:
                    ev_content = ev.evidence.content
                elif isinstance(ev, dict) and 'content' in ev.get('evidence', {}):
                    ev_content = ev['evidence']['content']
                elif hasattr(ev, 'content'):
                    ev_content = ev.content
                
                if not ev_content:
                    continue
                
                for pos_group, neg_group in self._direct_patterns:
                    if self._has_opposite_terms(claim, ev_content, pos_group, neg_group):
                        source = ""
                        if hasattr(ev, 'evidence') and ev.evidence.source:
                            source = ev.evidence.source
                        elif isinstance(ev, dict) and 'source' in ev.get('evidence', {}):
                            source = ev['evidence']['source']
                        
                        contradiction = Contradiction(
                            id=f"direct_ev_{len(contradictions)}_{datetime.utcnow().timestamp()}",
                            type=ContradictionType.DIRECT,
                            severity=self._assess_severity(claim, ev_content, "direct"),
                            claim_1=claim[:500],
                            claim_2=ev_content[:500],
                            source_1="research_output",
                            source_2=source or "evidence",
                            evidence_1=[],
                            evidence_2=[ev.evidence.id] if hasattr(ev, 'evidence') and hasattr(ev.evidence, 'id') else [],
                            description=f"Claim contradicted by evidence: '{claim[:100]}...' vs evidence from {source}"
                        )
                        contradiction.resolution_suggestion = (
                            f"Evaluate evidence quality from {source}. "
                            "Consider recency, source credibility, and methodology."
                        )
                        contradictions.append(contradiction)
        
        return contradictions
    
    def _has_opposite_terms(
        self,
        text1: str,
        text2: str,
        pos_group: List[str],
        neg_group: List[str]
    ) -> bool:
        """Check if two texts contain opposite terms."""
        text1_lower = text1.lower()
        text2_lower = text2.lower()
        
        has_pos_1 = any(term in text1_lower for term in pos_group)
        has_neg_1 = any(term in text1_lower for term in neg_group)
        has_pos_2 = any(term in text2_lower for term in pos_group)
        has_neg_2 = any(term in text2_lower for term in neg_group)
        
        return (has_pos_1 and has_neg_2) or (has_neg_1 and has_pos_2)
    
    async def _detect_numerical_contradictions(
        self,
        research_output: Dict[str, Any],
        evidence: List[Any]
    ) -> List[Contradiction]:
        """Detect numerical value contradictions."""
        contradictions = []
        
        # Extract numerical claims from research output
        numerical_claims = self._extract_numerical_claims(research_output)
        
        # Extract numerical claims from evidence
        for ev in evidence:
            ev_content = ""
            if hasattr(ev, 'evidence') and ev.evidence.content:
                ev_content = ev.evidence.content
            elif isinstance(ev, dict) and 'content' in ev.get('evidence', {}):
                ev_content = ev['evidence']['content']
            elif hasattr(ev, 'content'):
                ev_content = ev.content
            
            if not ev_content:
                continue
            
            ev_numerical = self._extract_numerical_claims({"text": ev_content})
            
            # Compare numerical claims
            for rc_key, rc_value in numerical_claims.items():
                for ec_key, ec_value in ev_numerical.items():
                    if self._keys_match(rc_key, ec_key):
                        if self._values_contradict(rc_value, ec_value, rc_key):
                            source = ""
                            if hasattr(ev, 'evidence') and ev.evidence.source:
                                source = ev.evidence.source
                            elif isinstance(ev, dict) and 'source' in ev.get('evidence', {}):
                                source = ev['evidence']['source']
                            
                            contradiction = Contradiction(
                                id=f"num_{len(contradictions)}_{datetime.utcnow().timestamp()}",
                                type=ContradictionType.NUMERICAL,
                                severity=self._assess_severity(str(rc_value), str(ec_value), "numerical"),
                                claim_1=f"{rc_key}: {rc_value}",
                                claim_2=f"{ec_key}: {ec_value}",
                                source_1="research_output",
                                source_2=source or "evidence",
                                description=f"Numerical contradiction in {rc_key}: {rc_value} vs {ec_value}"
                            )
                            contradiction.resolution_suggestion = (
                                f"Verify {rc_key} from primary sources. "
                                f"Check methodology, time period, and definitions used."
                            )
                            contradictions.append(contradiction)
        
        # Also compare within evidence
        ev_list = [ev for ev in evidence if hasattr(ev, 'evidence') and ev.evidence.content]
        for i, ev1 in enumerate(ev_list):
            for ev2 in ev_list[i+1:]:
                num1 = self._extract_numerical_claims({"text": ev1.evidence.content})
                num2 = self._extract_numerical_claims({"text": ev2.evidence.content})
                
                for key1, val1 in num1.items():
                    for key2, val2 in num2.items():
                        if self._keys_match(key1, key2):
                            if self._values_contradict(val1, val2, key1):
                                source1 = ev1.evidence.source if hasattr(ev1.evidence, 'source') else "evidence1"
                                source2 = ev2.evidence.source if hasattr(ev2.evidence, 'source') else "evidence2"
                                
                                contradiction = Contradiction(
                                    id=f"num_ev_{len(contradictions)}_{datetime.utcnow().timestamp()}",
                                    type=ContradictionType.NUMERICAL,
                                    severity=self._assess_severity(str(val1), str(val2), "numerical"),
                                    claim_1=f"{key1}: {val1}",
                                    claim_2=f"{key2}: {val2}",
                                    source_1=source1,
                                    source_2=source2,
                                    description=f"Evidence sources disagree on {key1}: {val1} vs {val2}"
                                )
                                contradiction.resolution_suggestion = (
                                    "Compare methodologies, time periods, and definitions. "
                                    "Prioritize primary sources and more recent data."
                                )
                                contradictions.append(contradiction)
        
        return contradictions
    
    def _extract_numerical_claims(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract numerical claims from object."""
        import re
        claims = {}
        
        text = ""
        if isinstance(obj, dict):
            if "text" in obj:
                text = obj["text"]
            else:
                text = " ".join(str(v) for v in obj.values() if isinstance(v, str))
        elif isinstance(obj, str):
            text = obj
        
        # Patterns for financial numbers
        patterns = {
            "price_target": r'(?:price target|target price|pt)\s*(?:of|at|is)?\s*\$?(\d+(?:\.\d+)?)(?:\s*(?:billion|million|b|m))?',
            "revenue": r'(?:revenue|sales|turnover)\s*(?:of|is|at)?\s*\$?(\d+(?:\.\d+)?)\s*(?:billion|million|b|m)',
            "eps": r'(?:eps|earnings per share)\s*(?:of|is|at)?\s*\$?(\d+(?:\.\d+)?)',
            "margin": r'(?:margin|profitability)\s*(?:of|is|at)?\s*(\d+(?:\.\d+)?)\s*%',
            "growth_rate": r'(?:growth|growth rate|cagr)\s*(?:of|is|at)?\s*(\d+(?:\.\d+)?)\s*%',
            "market_cap": r'(?:market cap|market capitalization)\s*(?:of|is|at)?\s*\$?(\d+(?:\.\d+)?)\s*(?:billion|million|b|m)',
            "pe_ratio": r'(?:pe ratio|p/e|price to earnings)\s*(?:of|is|at)?\s*(\d+(?:\.\d+)?)',
            "debt": r'(?:debt|leverage)\s*(?:of|is|at)?\s*\$?(\d+(?:\.\d+)?)\s*(?:billion|million|b|m)',
            "cash": r'(?:cash|cash position)\s*(?:of|is|at)?\s*\$?(\d+(?:\.\d+)?)\s*(?:billion|million|b|m)',
        }
        
        for key, pattern in patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    claims[key] = float(matches[-1])  # Use last match
                except ValueError:
                    pass
        
        return claims
    
    def _keys_match(self, key1: str, key2: str) -> bool:
        """Check if two numerical keys refer to the same metric."""
        key1 = key1.lower()
        key2 = key2.lower()
        
        # Exact match
        if key1 == key2:
            return True
        
        # Synonyms
        synonyms = {
            "price_target": ["target_price", "pt"],
            "revenue": ["sales", "turnover"],
            "eps": ["earnings_per_share"],
            "margin": ["profit_margin", "profitability"],
            "growth_rate": ["growth", "cagr", "revenue_growth"],
            "market_cap": ["market_capitalization"],
            "pe_ratio": ["p/e", "price_to_earnings"],
        }
        
        for canonical, syns in synonyms.items():
            if (key1 == canonical or key1 in syns) and (key2 == canonical or key2 in syns):
                return True
        
        return False
    
    def _values_contradict(self, val1: float, val2: float, key: str) -> bool:
        """Check if two numerical values contradict beyond tolerance."""
        tolerance = self._numerical_tolerance.get(key, self._numerical_tolerance["default"])
        
        if val1 == 0 and val2 == 0:
            return False
        
        if val1 == 0 or val2 == 0:
            return abs(val1 - val2) > tolerance * max(abs(val1), abs(val2), 1)
        
        # Relative difference
        rel_diff = abs(val1 - val2) / max(abs(val1), abs(val2))
        return rel_diff > tolerance
    
    async def _detect_temporal_contradictions(self, evidence: List[Any]) -> List[Contradiction]:
        """Detect timeline contradictions."""
        contradictions = []
        
        # Extract temporal claims
        temporal_claims = []
        
        for ev in evidence:
            ev_content = ""
            if hasattr(ev, 'evidence') and ev.evidence.content:
                ev_content = ev.evidence.content
            elif isinstance(ev, dict) and 'content' in ev.get('evidence', {}):
                ev_content = ev['evidence']['content']
            elif hasattr(ev, 'content'):
                ev_content = ev.content
            
            if not ev_content:
                continue
            
            # Look for temporal statements
            import re
            temporal_patterns = [
                (r'by\s+(202\d|203\d)', "by_year"),
                (r'in\s+(202\d|203\d)', "in_year"),
                (r'by\s+(Q[1-4]\s*202\d)', "by_quarter"),
                (r'next\s+(quarter|year)', "next_period"),
                (r'fiscal\s+(202\d|203\d)', "fiscal_year"),
            ]
            
            for pattern, claim_type in temporal_patterns:
                matches = re.findall(pattern, ev_content, re.IGNORECASE)
                for match in matches:
                    temporal_claims.append({
                        "claim": f"{claim_type}: {match}",
                        "type": claim_type,
                        "value": match,
                        "source": ev.evidence.source if hasattr(ev.evidence, 'source') else "evidence",
                        "evidence_id": ev.evidence.id if hasattr(ev.evidence, 'id') else None,
                        "full_text": ev_content[:200]
                    })
        
        # Check for contradictions
        for i, tc1 in enumerate(temporal_claims):
            for tc2 in temporal_claims[i+1:]:
                if tc1["type"] == tc2["type"] and tc1["value"] != tc2["value"]:
                    contradiction = Contradiction(
                        id=f"temp_{len(contradictions)}_{datetime.utcnow().timestamp()}",
                        type=ContradictionType.TEMPORAL,
                        severity=ContradictionSeverity.MEDIUM,
                        claim_1=f"{tc1['type']}: {tc1['value']}",
                        claim_2=f"{tc2['type']}: {tc2['value']}",
                        source_1=tc1["source"],
                        source_2=tc2["source"],
                        evidence_1=[tc1["evidence_id"]] if tc1["evidence_id"] else [],
                        evidence_2=[tc2["evidence_id"]] if tc2["evidence_id"] else [],
                        description=f"Timeline contradiction: {tc1['claim']} vs {tc2['claim']}"
                    )
                    contradiction.resolution_suggestion = (
                        "Verify dates from primary sources. "
                        "Check if different fiscal calendars or reporting periods are used."
                    )
                    contradictions.append(contradiction)
        
        return contradictions
    
    async def _detect_logical_contradictions(self, claims: List[str]) -> List[Contradiction]:
        """Detect logical inconsistencies."""
        contradictions = []
        
        # Check for mutually exclusive claims
        exclusivity_patterns = [
            # Can't be both the best and worst
            (["best", "leader", "top", "#1", "dominant", "superior"],
             ["worst", "laggard", "bottom", "inferior", "weakest"]),
            
            # Can't have both high and low risk
            (["low risk", "safe", "conservative", "defensive"],
             ["high risk", "risky", "aggressive", "speculative"]),
            
            # Can't be both growing and shrinking
            (["growing", "expanding", "increasing", "accelerating"],
             ["shrinking", "contracting", "decreasing", "decelerating"]),
        ]
        
        for i, claim1 in enumerate(claims):
            for claim2 in claims[i+1:]:
                for pos_group, neg_group in exclusivity_patterns:
                    if self._has_opposite_terms(claim1, claim2, pos_group, neg_group):
                        contradiction = Contradiction(
                            id=f"logical_{len(contradictions)}_{datetime.utcnow().timestamp()}",
                            type=ContradictionType.LOGICAL,
                            severity=ContradictionSeverity.HIGH,
                            claim_1=claim1[:500],
                            claim_2=claim2[:500],
                            source_1="research_output",
                            source_2="research_output",
                            description=f"Logical contradiction: '{claim1[:100]}...' vs '{claim2[:100]}...'"
                        )
                        contradiction.resolution_suggestion = (
                            "These claims are mutually exclusive. "
                            "Determine which is correct and revise the other."
                        )
                        contradictions.append(contradiction)
        
        return contradictions
    
    async def _detect_source_contradictions(self, evidence: List[Any]) -> List[Contradiction]:
        """Detect contradictions based on source credibility."""
        contradictions = []
        
        # Group evidence by claim/stance
        claims_by_stance = defaultdict(list)
        
        for ev in evidence:
            if not hasattr(ev, 'evidence') or not ev.evidence.content:
                continue
            
            # Simple stance detection
            content = ev.evidence.content.lower()
            stance = "neutral"
            if any(w in content for w in ["buy", "bullish", "positive", "outperform", "upgrade"]):
                stance = "positive"
            elif any(w in content for w in ["sell", "bearish", "negative", "underperform", "downgrade"]):
                stance = "negative"
            
            claims_by_stance[stance].append(ev)
        
        # Check if high-credibility sources contradict low-credibility
        source_credibility = {
            "sec": 1.0, "reuters": 0.95, "bloomberg": 0.95, "wsj": 0.9,
            "ft": 0.9, "cnbc": 0.8, "marketwatch": 0.75, "seeking_alpha": 0.7,
            "benzinga": 0.65, "analyst_report": 0.9, "earnings_call": 0.95,
            "sec_filing": 1.0, "model_output": 0.8, "agent_output": 0.7,
            "news": 0.7, "general": 0.5
        }
        
        for stance, ev_list in claims_by_stance.items():
            if len(ev_list) < 2:
                continue
            
            # Sort by credibility
            scored = []
            for ev in ev_list:
                source = ev.evidence.source.lower() if hasattr(ev.evidence, 'source') else "general"
                cred = 0.5
                for key, score in source_credibility.items():
                    if key in source:
                        cred = score
                        break
                scored.append((cred, ev))
            
            scored.sort(key=lambda x: x[0], reverse=True)
            
            # High credibility vs low credibility on same stance - not a contradiction
            # But if they disagree on stance, that's different
        
        return contradictions
    
    async def _detect_methodological_contradictions(self, evidence: List[Any]) -> List[Contradiction]:
        """Detect methodology-based contradictions."""
        contradictions = []
        
        # Check for DCF vs multiples valuation disagreement
        methods_found = set()
        
        for ev in evidence:
            if not hasattr(ev, 'evidence') or not ev.evidence.content:
                continue
            
            content = ev.evidence.content.lower()
            if "dcf" in content or "discounted cash flow" in content:
                methods_found.add("dcf")
            if "multiple" in content or "pe ratio" in content or "ev/ebitda" in content:
                methods_found.add("multiples")
            if "comparable" in content or "comps" in content:
                methods_found.add("comparables")
            if "precedent" in content or "transaction" in content:
                methods_found.add("precedent")
        
        # If multiple valuation methods found, check if they'd give different results
        if len(methods_found) > 1:
            contradiction = Contradiction(
                id=f"method_{len(contradictions)}_{datetime.utcnow().timestamp()}",
                type=ContradictionType.METHODOLOGICAL,
                severity=ContradictionSeverity.INFORMATIONAL,
                claim_1=f"Valuation methods used: {', '.join(methods_found)}",
                claim_2="Different methods may yield different valuations",
                source_1="evidence_analysis",
                source_2="evidence_analysis",
                description=f"Multiple valuation methodologies detected: {', '.join(methods_found)}"
            )
            contradiction.resolution_suggestion = (
                "Acknowledge methodology differences. "
                "Present range of valuations or weight methods by appropriateness."
            )
            contradictions.append(contradiction)
        
        return contradictions
    
    def _assess_severity(self, claim1: str, claim2: str, contradiction_type: str) -> ContradictionSeverity:
        """Assess severity of a contradiction."""
        
        # Critical if it involves core investment thesis
        thesis_keywords = ["thesis", "investment", "recommendation", "buy", "sell", "target"]
        if any(kw in claim1.lower() or kw in claim2.lower() for kw in thesis_keywords):
            return ContradictionSeverity.CRITICAL
        
        # High for numerical contradictions in key metrics
        if contradiction_type == "numerical":
            return ContradictionSeverity.HIGH
        
        # High for direct contradictions
        if contradiction_type == "direct":
            return ContradictionSeverity.HIGH
        
        # Medium for temporal
        if contradiction_type == "temporal":
            return ContradictionSeverity.MEDIUM
        
        # Medium for logical
        if contradiction_type == "logical":
            return ContradictionSeverity.MEDIUM
        
        return ContradictionSeverity.LOW
    
    def _analyze_contradictions(self, contradictions: List[Contradiction]) -> Dict[str, Any]:
        """Analyze contradictions and assess impact."""
        
        if not contradictions:
            return {
                "summary": {
                    "total": 0,
                    "by_type": {},
                    "by_severity": {}
                },
                "impact": "No contradictions detected. Research is internally consistent.",
                "priority": [],
                "confidence_impact": 0.0
            }
        
        # Count by type and severity
        by_type = defaultdict(int)
        by_severity = defaultdict(int)
        
        for c in contradictions:
            by_type[c.type.value] += 1
            by_severity[c.severity.value] += 1
        
        # Calculate confidence impact
        severity_weights = {
            ContradictionSeverity.CRITICAL: 0.25,
            ContradictionSeverity.HIGH: 0.15,
            ContradictionSeverity.MEDIUM: 0.08,
            ContradictionSeverity.LOW: 0.03,
            ContradictionSeverity.INFORMATIONAL: 0.01
        }
        
        confidence_impact = sum(
            severity_weights.get(c.severity, 0) for c in contradictions
        )
        confidence_impact = min(confidence_impact, 0.8)  # Cap at 80%
        
        # Priority for resolution
        priority = []
        for c in sorted(contradictions, key=lambda x: severity_weights.get(x.severity, 0), reverse=True)[:5]:
            priority.append(f"{c.severity.value}: {c.description[:100]}")
        
        # Impact assessment
        if by_severity[ContradictionSeverity.CRITICAL.value] > 0:
            impact = "CRITICAL: Found contradictions that invalidate core conclusions. Must resolve before any decision."
        elif by_severity[ContradictionSeverity.HIGH.value] > 2:
            impact = "HIGH: Multiple significant contradictions. Requires thorough review and resolution."
        elif by_severity[ContradictionSeverity.HIGH.value] > 0:
            impact = "MODERATE-HIGH: Significant contradictions present. Address before finalizing."
        elif by_severity[ContradictionSeverity.MEDIUM.value] > 0:
            impact = "MODERATE: Some contradictions noted. Should be acknowledged and addressed."
        else:
            impact = "LOW: Minor contradictions. Can be noted in final report."
        
        return {
            "summary": {
                "total": len(contradictions),
                "by_type": dict(by_type),
                "by_severity": dict(by_severity)
            },
            "impact": impact,
            "priority": priority,
            "confidence_impact": confidence_impact
        }
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "contradiction_types": [ct.value for ct in ContradictionType],
            "severity_levels": [cs.value for cs in ContradictionSeverity],
            "direct_patterns_count": len(self._direct_patterns),
            "numerical_tolerance": self._numerical_tolerance
        }


# Global contradiction detector instance
_contradiction_detector: Optional[ContradictionDetector] = None


def get_contradiction_detector() -> ContradictionDetector:
    global _contradiction_detector
    if _contradiction_detector is None:
        _contradiction_detector = ContradictionDetector()
    return _contradiction_detector


async def close_contradiction_detector() -> None:
    global _contradiction_detector
    if _contradiction_detector:
        _contradiction_detector = None