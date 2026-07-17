"""
Confidence Engine for Financial Entity Recognition

Calculates and manages confidence scores for extracted entities.
Combines multiple signals: extraction method, dictionary match, context, etc.
"""

import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from data.news.entity_recognition.schemas import (
    Entity, EntityType, EntitySubType, ConfidenceLevel, ConfidenceFactors
)

logger = logging.getLogger(__name__)


class ConfidenceSignal(Enum):
    """Sources of confidence signals."""
    RULE_BASED = "rule_based"
    DICTIONARY = "dictionary"
    LOCAL_NER = "local_ner"
    LLM_VALIDATED = "llm_validated"
    TICKER_RESOLVED = "ticker_resolved"
    COMPANY_RESOLVED = "company_resolved"
    ALIAS_RESOLVED = "alias_resolved"
    CONTEXTUAL = "contextual"
    CROSS_REFERENCE = "cross_reference"
    DUPLICATE = "duplicate"
    POSITION = "position"


@dataclass
class ConfidenceFactor:
    """A single confidence factor."""
    signal: ConfidenceSignal
    weight: float
    value: float
    description: str
    
    @property
    def contribution(self) -> float:
        """Weighted contribution to confidence."""
        return self.weight * self.value


class ConfidenceEngine:
    """
    Calculates confidence scores for extracted entities.
    
    Combines multiple signals:
    - Extraction method confidence (regex=0.8, dictionary=0.95, NER=0.85, LLM=0.9)
    - Dictionary match quality (exact=1.0, alias=0.9, fuzzy=0.7)
    - Context signals (financial context=+0.1, quoted=+0.05, etc.)
    - Cross-reference validation (ticker resolves, company resolves)
    - Position in text (title=+0.1, first paragraph=+0.05)
    - Duplicate mentions (multiple mentions=+0.05 each)
    """
    
    # Base confidence by extraction method
    METHOD_BASE_CONFIDENCE = {
        ConfidenceSignal.RULE_BASED: 0.80,
        ConfidenceSignal.DICTIONARY: 0.95,
        ConfidenceSignal.LOCAL_NER: 0.85,
        ConfidenceSignal.LLM_VALIDATED: 0.90,
        ConfidenceSignal.TICKER_RESOLVED: 0.95,
        ConfidenceSignal.COMPANY_RESOLVED: 0.95,
        ConfidenceSignal.ALIAS_RESOLVED: 0.90,
        ConfidenceSignal.CONTEXTUAL: 0.70,
        ConfidenceSignal.CROSS_REFERENCE: 0.85,
        ConfidenceSignal.DUPLICATE: 0.60,
        ConfidenceSignal.POSITION: 0.75,
    }
    
    # Signal weights for combining
    SIGNAL_WEIGHTS = {
        ConfidenceSignal.RULE_BASED: 1.0,
        ConfidenceSignal.DICTIONARY: 2.0,
        ConfidenceSignal.LOCAL_NER: 1.5,
        ConfidenceSignal.LLM_VALIDATED: 2.0,
        ConfidenceSignal.TICKER_RESOLVED: 1.5,
        ConfidenceSignal.COMPANY_RESOLVED: 1.5,
        ConfidenceSignal.ALIAS_RESOLVED: 1.0,
        ConfidenceSignal.CONTEXTUAL: 0.5,
        ConfidenceSignal.CROSS_REFERENCE: 1.0,
        ConfidenceSignal.DUPLICATE: 0.5,
        ConfidenceSignal.POSITION: 0.3,
    }
    
    # Context boosters
    CONTEXT_BOOSTERS = {
        "financial_keywords": 0.10,
        "quoted_price": 0.05,
        "earnings_context": 0.10,
        "sec_filing": 0.15,
        "analyst_rating": 0.10,
        "title_position": 0.10,
        "first_paragraph": 0.05,
        "headline": 0.10,
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.min_confidence = self.config.get("min_confidence", 0.3)
        self.max_confidence = self.config.get("max_confidence", 1.0)
        
    def calculate_confidence(
        self,
        entity: Entity,
        signals: List[ConfidenceSignal],
        context: Optional[Dict[str, Any]] = None,
        duplicate_count: int = 1,
        position_info: Optional[Dict[str, Any]] = None,
    ) -> ConfidenceFactors:
        """
        Calculate confidence for an entity.
        
        Args:
            entity: The entity to score
            signals: List of confidence signals present
            context: Contextual information (text, section, etc.)
            duplicate_count: Number of times entity appears
            position_info: Position metadata (title, paragraph, etc.)
            
        Returns:
            ConfidenceFactors with breakdown and final score
        """
        factors = []
        
        # Base method confidences
        for signal in signals:
            base = self.METHOD_BASE_CONFIDENCE.get(signal, 0.5)
            weight = self.SIGNAL_WEIGHTS.get(signal, 1.0)
            factors.append(ConfidenceFactor(
                signal=signal,
                weight=weight,
                value=base,
                description=f"{signal.value} extraction method"
            ))
            
        # Context boosters
        if context:
            for booster, value in self._evaluate_context_boosters(entity, context).items():
                factors.append(ConfidenceFactor(
                    signal=ConfidenceSignal.CONTEXTUAL,
                    weight=0.5,
                    value=value,
                    description=f"Context booster: {booster}"
                ))
                
        # Duplicate mention boost
        if duplicate_count > 1:
            dup_boost = min(0.05 * (duplicate_count - 1), 0.2)
            factors.append(ConfidenceFactor(
                signal=ConfidenceSignal.DUPLICATE,
                weight=0.5,
                value=dup_boost,
                description=f"Appears {duplicate_count} times"
            ))
            
        # Position boost
        if position_info:
            pos_boost = self._evaluate_position_boost(position_info)
            if pos_boost > 0:
                factors.append(ConfidenceFactor(
                    signal=ConfidenceSignal.POSITION,
                    weight=0.3,
                    value=pos_boost,
                    description=f"Position boost: {position_info}"
                ))
                
        # Entity-type specific adjustments
        type_adjustment = self._get_entity_type_adjustment(entity)
        if type_adjustment != 0:
            factors.append(ConfidenceFactor(
                signal=ConfidenceSignal.CONTEXTUAL,
                weight=0.5,
                value=type_adjustment,
                description=f"Entity type adjustment: {entity.entity_type.value}"
            ))
            
        # Calculate weighted average
        total_weight = sum(f.weight for f in factors)
        if total_weight > 0:
            weighted_sum = sum(f.contribution for f in factors)
            final_confidence = weighted_sum / total_weight
        else:
            final_confidence = 0.5
            
        # Apply bounds
        final_confidence = max(self.min_confidence, min(self.max_confidence, final_confidence))
        
        # Determine confidence level
        level = self._confidence_to_level(final_confidence)
        
        return ConfidenceFactors(
            base_confidence=self._get_base_confidence(signals),
            method_bonus=sum(f.contribution for f in factors if f.signal in [ConfidenceSignal.RULE_BASED, ConfidenceSignal.LOCAL_NER]),
            dictionary_bonus=sum(f.contribution for f in factors if f.signal == ConfidenceSignal.DICTIONARY),
            llm_bonus=sum(f.contribution for f in factors if f.signal == ConfidenceSignal.LLM_VALIDATED),
            context_bonus=sum(f.contribution for f in factors if f.signal == ConfidenceSignal.CONTEXTUAL),
            cross_ref_bonus=sum(f.contribution for f in factors if f.signal in [ConfidenceSignal.TICKER_RESOLVED, ConfidenceSignal.COMPANY_RESOLVED, ConfidenceSignal.CROSS_REFERENCE]),
            position_bonus=sum(f.contribution for f in factors if f.signal == ConfidenceSignal.POSITION),
            duplicate_penalty=0,  # We use boost, not penalty
            final_confidence=final_confidence,
            confidence_level=level,
        )
        
    def _get_base_confidence(self, signals: List[ConfidenceSignal]) -> float:
        """Get base confidence from signals."""
        if not signals:
            return 0.5
        return sum(self.METHOD_BASE_CONFIDENCE.get(s, 0.5) for s in signals) / len(signals)
        
    def _evaluate_context_boosters(self, entity: Entity, context: Dict[str, Any]) -> Dict[str, float]:
        """Evaluate context-based confidence boosters."""
        boosters = {}
        
        text = context.get("text", "").lower()
        section = context.get("section", "").lower()
        surrounding = context.get("surrounding_text", "").lower()
        
        # Financial keywords
        financial_terms = [
            "revenue", "earnings", "eps", "ebitda", "profit", "margin",
            "guidance", "forecast", "outlook", "dividend", "buyback",
            "acquisition", "merger", "ipo", "sec", "filing", "10-k", "10-q",
            "analyst", "rating", "target", "upgrade", "downgrade"
        ]
        if any(term in surrounding for term in financial_terms):
            boosters["financial_keywords"] = self.CONTEXT_BOOSTERS["financial_keywords"]
            
        # Quoted price
        if "$" in surrounding and any(c.isdigit() for c in surrounding):
            boosters["quoted_price"] = self.CONTEXT_BOOSTERS["quoted_price"]
            
        # Earnings context
        if any(term in surrounding for term in ["earnings", "quarter", "q1", "q2", "q3", "q4", "fiscal"]):
            boosters["earnings_context"] = self.CONTEXT_BOOSTERS["earnings_context"]
            
        # SEC filing
        if any(term in text for term in ["8-k", "10-k", "10-q", "s-1", "def 14a", "13f"]):
            boosters["sec_filing"] = self.CONTEXT_BOOSTERS["sec_filing"]
            
        # Analyst rating
        if any(term in surrounding for term in ["buy", "sell", "hold", "overweight", "underweight", "outperform", "underperform"]):
            boosters["analyst_rating"] = self.CONTEXT_BOOSTERS["analyst_rating"]
            
        # Section-based
        if section in ["title", "headline"]:
            boosters["title_position"] = self.CONTEXT_BOOSTERS["title_position"]
        elif section == "headline":
            boosters["headline"] = self.CONTEXT_BOOSTERS["headline"]
        elif section in ["first_paragraph", "lead"]:
            boosters["first_paragraph"] = self.CONTEXT_BOOSTERS["first_paragraph"]
            
        return boosters
        
    def _evaluate_position_boost(self, position_info: Dict[str, Any]) -> float:
        """Evaluate position-based confidence boost."""
        boost = 0.0
        
        if position_info.get("in_title"):
            boost += self.CONTEXT_BOOSTERS["title_position"]
        if position_info.get("in_headline"):
            boost += self.CONTEXT_BOOSTERS["headline"]
        if position_info.get("in_first_paragraph"):
            boost += self.CONTEXT_BOOSTERS["first_paragraph"]
        if position_info.get("early_in_text"):  # First 10%
            boost += 0.03
            
        return min(boost, 0.15)
        
    def _get_entity_type_adjustment(self, entity: Entity) -> float:
        """Get confidence adjustment based on entity type."""
        adjustments = {
            EntityType.TICKER: 0.05,        # Tickers are precise
            EntityType.MONEY: 0.05,         # Money amounts are precise
            EntityType.PERCENTAGE: 0.05,    # Percentages are precise
            EntityType.DATE: 0.03,          # Dates are precise
            EntityType.COMPANY: 0.0,        # Base
            EntityType.PERSON: -0.05,       # Names can be ambiguous
            EntityType.EVENT: -0.05,        # Events can be vague
            EntityType.METRIC: 0.0,         # Base
        }
        return adjustments.get(entity.entity_type, 0.0)
        
    def _confidence_to_level(self, confidence: float) -> ConfidenceLevel:
        """Convert numeric confidence to level."""
        if confidence >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif confidence >= 0.75:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.6:
            return ConfidenceLevel.MEDIUM
        elif confidence >= 0.4:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
            
    def calculate_entity_confidence(
        self,
        entity: Entity,
        text: str,
        all_entities: List[Entity],
        extraction_methods: List[str],
        section: str = "body",
    ) -> ConfidenceFactors:
        """
        High-level confidence calculation for an entity.
        
        Args:
            entity: Entity to score
            text: Full text
            all_entities: All extracted entities (for cross-reference)
            extraction_methods: Methods that extracted this entity
            section: Document section (title, headline, body, etc.)
            
        Returns:
            ConfidenceFactors
        """
        # Map extraction methods to signals
        method_to_signal = {
            "regex": ConfidenceSignal.RULE_BASED,
            "dictionary": ConfidenceSignal.DICTIONARY,
            "spacy": ConfidenceSignal.LOCAL_NER,
            "gliner": ConfidenceSignal.LOCAL_NER,
            "llm": ConfidenceSignal.LLM_VALIDATED,
            "ticker_resolver": ConfidenceSignal.TICKER_RESOLVED,
            "company_resolver": ConfidenceSignal.COMPANY_RESOLVED,
            "alias_resolver": ConfidenceSignal.ALIAS_RESOLVED,
        }
        
        signals = [method_to_signal.get(m, ConfidenceSignal.RULE_BASED) for m in extraction_methods]
        
        # Count duplicates
        duplicate_count = sum(
            1 for e in all_entities 
            if e.normalized_value == entity.normalized_value and e.entity_id != entity.entity_id
        ) + 1
        
        # Context
        start = max(0, entity.start_char - 200)
        end = min(len(text), entity.end_char + 200)
        surrounding = text[start:end]
        
        context = {
            "text": text[entity.start_char:entity.end_char],
            "surrounding_text": surrounding,
            "section": section,
        }
        
        # Position info
        position_info = {
            "in_title": section == "title",
            "in_headline": section == "headline",
            "in_first_paragraph": section in ["lead", "first_paragraph"],
            "early_in_text": entity.start_char < len(text) * 0.1,
        }
        
        return self.calculate_confidence(
            entity=entity,
            signals=signals,
            context=context,
            duplicate_count=duplicate_count,
            position_info=position_info,
        )
        
    def merge_confidences(self, factors_list: List[ConfidenceFactors]) -> ConfidenceFactors:
        """Merge multiple confidence factor sets (e.g., from multiple mentions)."""
        if not factors_list:
            return ConfidenceFactors()
            
        # Average final confidences
        avg_confidence = sum(f.final_confidence for f in factors_list) / len(factors_list)
        
        # Sum bonuses (capped)
        merged = ConfidenceFactors(
            base_confidence=sum(f.base_confidence for f in factors_list) / len(factors_list),
            method_bonus=min(sum(f.method_bonus for f in factors_list), 0.3),
            dictionary_bonus=min(sum(f.dictionary_bonus for f in factors_list), 0.3),
            llm_bonus=min(sum(f.llm_bonus for f in factors_list), 0.3),
            context_bonus=min(sum(f.context_bonus for f in factors_list), 0.2),
            cross_ref_bonus=min(sum(f.cross_ref_bonus for f in factors_list), 0.2),
            position_bonus=min(sum(f.position_bonus for f in factors_list), 0.15),
            duplicate_penalty=0,
            final_confidence=avg_confidence,
            confidence_level=self._confidence_to_level(avg_confidence),
        )
        
        return merged


# Singleton instance
_confidence_engine: Optional[ConfidenceEngine] = None


def get_confidence_engine(config: Optional[Dict[str, Any]] = None) -> ConfidenceEngine:
    """Get or create the default confidence engine."""
    global _confidence_engine
    if _confidence_engine is None:
        _confidence_engine = ConfidenceEngine(config)
    return _confidence_engine