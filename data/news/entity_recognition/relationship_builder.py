"""
Relationship Builder for Financial Entity Recognition

Builds entity relationship graphs from extracted entities.
Creates connections between companies, executives, tickers, exchanges, 
products, competitors, financial metrics, and events.
"""

import logging
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

from data.news.entity_recognition.schemas import (
    Entity, EntityType, EntitySubType, EntityRelationship, RelationshipType
)
from data.news.entity_recognition.dictionary import (
    FinancialDictionary, get_financial_dictionary
)
from data.news.entity_recognition.company_resolver import get_company_resolver
from data.news.entity_recognition.ticker_resolver import get_ticker_resolver

logger = logging.getLogger(__name__)


class RelationshipStrength(Enum):
    """Strength of relationship between entities."""
    STRONG = "strong"      # Direct, explicit relationship (CEO of, listed on)
    MEDIUM = "medium"      # Implied or contextual (mentioned together, subsidiary)
    WEAK = "weak"          # Co-occurrence only (same article, same paragraph)


@dataclass
class RelationshipCandidate:
    """A candidate relationship between two entities."""
    source_entity: Entity
    target_entity: Entity
    relationship_type: RelationshipType
    strength: RelationshipStrength
    confidence: float
    evidence: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class RelationshipBuilder:
    """
    Builds relationships between extracted financial entities.
    
    Relationship types:
    - Company -> CEO/CFO/Founder (executive roles)
    - Company -> Ticker (listed as)
    - Company -> Exchange (listed on)
    - Company -> Country (headquartered in)
    - Company -> Sector/Industry (operates in)
    - Company -> Product (produces)
    - Company -> Company (competitor, partner, subsidiary, parent)
    - Company -> Metric (reported)
    - Company -> Event (involved in)
    - Person -> Company (works at, founded, invested in)
    - Ticker -> Exchange (traded on)
    - Index -> Component (contains)
    - Currency -> Country (used in)
    - Central Bank -> Country (regulates)
    - Regulator -> Country (jurisdiction)
    """
    
    def __init__(self, dictionary: Optional[FinancialDictionary] = None):
        self.dictionary = dictionary or get_financial_dictionary()
        self.dictionary.initialize()
        self.company_resolver = get_company_resolver(self.dictionary)
        self.ticker_resolver = get_ticker_resolver(self.dictionary)
        
        # Relationship rules
        self._rules = self._build_rules()
        
    def _build_rules(self) -> List[Dict]:
        """Build relationship extraction rules."""
        return [
            # Company -> Person (executive roles)
            {
                "source_types": [EntityType.COMPANY],
                "target_types": [EntityType.PERSON],
                "target_subtypes": [EntitySubType.CEO, EntitySubType.CFO, EntitySubType.CXO, 
                                    EntitySubType.FOUNDER, EntitySubType.PRESIDENT, EntitySubType.CHAIRMAN],
                "relationship": RelationshipType.HAS_CEO,  # Will be determined by sub_type
                "strength": RelationshipStrength.STRONG,
                "keywords": ["ceo", "cfo", "cto", "coo", "president", "chairman", "founder", "co-founder", "executive", "officer"],
                "proximity_window": 100,
            },
            # Company -> Ticker
            {
                "source_types": [EntityType.COMPANY],
                "target_types": [EntityType.TICKER],
                "relationship": RelationshipType.HAS_TICKER,
                "strength": RelationshipStrength.STRONG,
                "keywords": ["ticker", "symbol", "trades as", "listed as", "trading under"],
                "proximity_window": 50,
            },
            # Company -> Exchange
            {
                "source_types": [EntityType.COMPANY],
                "target_types": [EntityType.EXCHANGE],
                "relationship": RelationshipType.LISTED_ON,
                "strength": RelationshipStrength.STRONG,
                "keywords": ["listed on", "trades on", "exchange", "nyse", "nasdaq", "lse", "tse", "hkex"],
                "proximity_window": 100,
            },
            # Company -> Country
            {
                "source_types": [EntityType.COMPANY],
                "target_types": [EntityType.COUNTRY],
                "relationship": RelationshipType.HEADQUARTERED_IN,
                "strength": RelationshipStrength.MEDIUM,
                "keywords": ["headquartered in", "based in", "incorporated in", "domiciled in", "headquarters in"],
                "proximity_window": 100,
            },
            # Company -> Sector/Industry
            {
                "source_types": [EntityType.COMPANY],
                "target_types": [EntityType.SECTOR, EntityType.INDUSTRY],
                "relationship": RelationshipType.OPERATES_IN,
                "strength": RelationshipStrength.MEDIUM,
                "keywords": ["sector", "industry", "operates in", "belongs to", "segment"],
                "proximity_window": 100,
            },
            # Company -> Product
            {
                "source_types": [EntityType.COMPANY],
                "target_types": [EntityType.PRODUCT],
                "relationship": RelationshipType.PRODUCES,
                "strength": RelationshipStrength.MEDIUM,
                "keywords": ["product", "launches", "released", "introduced", "unveiled", "offers", "sells"],
                "proximity_window": 100,
            },
            # Company -> Company (competitor)
            {
                "source_types": [EntityType.COMPANY],
                "target_types": [EntityType.COMPANY],
                "relationship": RelationshipType.COMPETES_WITH,
                "strength": RelationshipStrength.MEDIUM,
                "keywords": ["competes with", "rival", "competitor", "vs", "versus", "competing", "battle"],
                "proximity_window": 100,
            },
            # Company -> Company (partner)
            {
                "source_types": [EntityType.COMPANY],
                "target_types": [EntityType.COMPANY],
                "relationship": RelationshipType.PARTNERS_WITH,
                "strength": RelationshipStrength.MEDIUM,
                "keywords": ["partners with", "partnership", "collaboration", "alliance", "joint venture", "strategic alliance"],
                "proximity_window": 100,
            },
            # Company -> Company (subsidiary/parent)
            {
                "source_types": [EntityType.COMPANY],
                "target_types": [EntityType.COMPANY],
                "relationship": RelationshipType.SUBSIDIARY_OF,
                "strength": RelationshipStrength.STRONG,
                "keywords": ["subsidiary", "acquired", "acquisition", "bought", "owns", "parent company", "division of", "unit of"],
                "proximity_window": 100,
            },
            # Company -> Metric
            {
                "source_types": [EntityType.COMPANY],
                "target_types": [EntityType.METRIC],
                "relationship": RelationshipType.REPORTED,
                "strength": RelationshipStrength.STRONG,
                "keywords": ["reported", "announced", "posted", "achieved", "delivered", "recorded"],
                "proximity_window": 200,
            },
            # Company -> Event
            {
                "source_types": [EntityType.COMPANY],
                "target_types": [EntityType.EVENT],
                "relationship": RelationshipType.INVOLVED_IN,
                "strength": RelationshipStrength.MEDIUM,
                "keywords": ["announced", "filed", "launched", "completed", "closed", "approved", "rejected"],
                "proximity_window": 100,
            },
            # Person -> Company
            {
                "source_types": [EntityType.PERSON],
                "target_types": [EntityType.COMPANY],
                "relationship": RelationshipType.WORKS_AT,
                "strength": RelationshipStrength.STRONG,
                "keywords": ["ceo of", "cfo of", "president of", "chairman of", "founder of", "works at", "joined", "appointed", "hired by"],
                "proximity_window": 100,
            },
            # Ticker -> Exchange
            {
                "source_types": [EntityType.TICKER],
                "target_types": [EntityType.EXCHANGE],
                "relationship": RelationshipType.TRADES_ON,
                "strength": RelationshipStrength.STRONG,
                "keywords": ["nyse", "nasdaq", "listed", "trades", "exchange"],
                "proximity_window": 50,
            },
            # Index -> Component
            {
                "source_types": [EntityType.INDEX],
                "target_types": [EntityType.COMPANY, EntityType.TICKER],
                "relationship": RelationshipType.HAS_COMPONENT,
                "strength": RelationshipStrength.MEDIUM,
                "keywords": ["component", "constituent", "member of", "included in", "added to", "removed from"],
                "proximity_window": 100,
            },
        ]
        
    def build_relationships(
        self, 
        entities: List[Entity], 
        text: str,
        max_relationships: int = 100
    ) -> List[EntityRelationship]:
        """
        Build relationships between entities based on text context.
        
        Args:
            entities: List of extracted entities
            text: Original text
            max_relationships: Maximum relationships to return
            
        Returns:
            List of EntityRelationship objects
        """
        relationships = []
        
        # Sort entities by position
        sorted_entities = sorted(entities, key=lambda e: e.start_char)
        
        # Check each pair of entities
        for i, source in enumerate(sorted_entities):
            for target in sorted_entities[i+1:]:
                # Check proximity
                distance = target.start_char - source.end_char
                if distance > 500:  # Too far apart
                    break
                    
                # Try to find relationship
                rel = self._find_relationship(source, target, text, distance)
                if rel:
                    relationships.append(rel)
                    
                    if len(relationships) >= max_relationships:
                        break
                        
            if len(relationships) >= max_relationships:
                break
                
        # Add dictionary-based relationships
        dict_relationships = self._build_dictionary_relationships(entities)
        relationships.extend(dict_relationships)
        
        # Deduplicate
        relationships = self._deduplicate_relationships(relationships)
        
        # Sort by confidence
        relationships.sort(key=lambda r: r.confidence, reverse=True)
        
        return relationships[:max_relationships]
        
    def _find_relationship(
        self, 
        source: Entity, 
        target: Entity, 
        text: str, 
        distance: int
    ) -> Optional[EntityRelationship]:
        """Find relationship between two entities."""
        
        # Check each rule
        for rule in self._rules:
            if not self._matches_rule(source, target, rule):
                continue
                
            # Check proximity
            if distance > rule.get("proximity_window", 100):
                continue
                
            # Check keywords in between
            context = text[source.end_char:target.start_char].lower()
            keywords = rule.get("keywords", [])
            if keywords and not any(kw in context for kw in keywords):
                continue
                
            # Determine relationship type based on subtypes
            rel_type = self._determine_relationship_type(source, target, rule)
            if not rel_type:
                continue
                
            # Calculate confidence
            confidence = self._calculate_confidence(source, target, rule, distance, context)
            
            # Create relationship
            relationship = EntityRelationship(
                source_entity_id=source.entity_id,
                target_entity_id=target.entity_id,
                relationship_type=rel_type,
                confidence=confidence,
                evidence=context[:200],
                metadata={
                    "distance": distance,
                    "rule": rule.get("relationship", "").value if hasattr(rule.get("relationship"), "value") else str(rule.get("relationship")),
                    "source_type": source.entity_type.value,
                    "target_type": target.entity_type.value,
                }
            )
            
            return relationship
            
        return None
        
    def _matches_rule(self, source: Entity, target: Entity, rule: Dict) -> bool:
        """Check if entity pair matches rule."""
        source_types = rule.get("source_types", [])
        target_types = rule.get("target_types", [])
        target_subtypes = rule.get("target_subtypes", [])
        
        if source_types and source.entity_type not in source_types:
            return False
        if target_types and target.entity_type not in target_types:
            return False
        if target_subtypes and target.sub_type not in target_subtypes:
            return False
            
        return True
        
    def _determine_relationship_type(
        self, 
        source: Entity, 
        target: Entity, 
        rule: Dict
    ) -> Optional[RelationshipType]:
        """Determine specific relationship type."""
        base_type = rule.get("relationship")
        
        # Special handling for executive roles
        if base_type == RelationshipType.HAS_CEO and target.sub_type:
            exec_map = {
                EntitySubType.CEO: RelationshipType.HAS_CEO,
                EntitySubType.CFO: RelationshipType.HAS_CFO,
                EntitySubType.CXO: RelationshipType.HAS_EXECUTIVE,
                EntitySubType.FOUNDER: RelationshipType.HAS_FOUNDER,
                EntitySubType.PRESIDENT: RelationshipType.HAS_EXECUTIVE,
                EntitySubType.CHAIRMAN: RelationshipType.HAS_EXECUTIVE,
            }
            return exec_map.get(target.sub_type, RelationshipType.HAS_EXECUTIVE)
            
        # Special handling for subsidiary vs parent
        if base_type == RelationshipType.SUBSIDIARY_OF:
            # Determine direction based on context
            return RelationshipType.SUBSIDIARY_OF
            
        return base_type
        
    def _calculate_confidence(
        self, 
        source: Entity, 
        target: Entity, 
        rule: Dict, 
        distance: int,
        context: str
    ) -> float:
        """Calculate relationship confidence."""
        base_confidence = 0.7
        
        # Adjust for entity confidence
        entity_conf = (source.confidence + target.confidence) / 2
        base_confidence *= entity_conf
        
        # Adjust for distance
        if distance < 50:
            base_confidence *= 1.1
        elif distance < 100:
            base_confidence *= 1.0
        elif distance < 200:
            base_confidence *= 0.9
        else:
            base_confidence *= 0.8
            
        # Adjust for keyword presence
        keywords = rule.get("keywords", [])
        if keywords:
            kw_count = sum(1 for kw in keywords if kw in context)
            if kw_count > 0:
                base_confidence *= (1.0 + 0.1 * min(kw_count, 3))
                
        # Cap at 1.0
        return min(base_confidence, 1.0)
        
    def _build_dictionary_relationships(self, entities: List[Entity]) -> List[EntityRelationship]:
        """Build relationships from dictionary metadata."""
        relationships = []
        
        for entity in entities:
            # Company -> Ticker
            if entity.entity_type == EntityType.COMPANY and entity.ticker:
                ticker_entities = [e for e in entities 
                                  if e.entity_type == EntityType.TICKER and e.normalized_value == entity.ticker]
                for ticker_entity in ticker_entities:
                    relationships.append(EntityRelationship(
                        source_entity_id=entity.entity_id,
                        target_entity_id=ticker_entity.entity_id,
                        relationship_type=RelationshipType.HAS_TICKER,
                        confidence=0.95,
                        evidence=f"Dictionary: {entity.canonical_name} has ticker {entity.ticker}",
                        metadata={"source": "dictionary"}
                    ))
                    
            # Company -> Exchange
            if entity.entity_type == EntityType.COMPANY and entity.metadata.get("exchange"):
                exchange_name = entity.metadata["exchange"]
                exchange_entities = [e for e in entities 
                                   if e.entity_type == EntityType.EXCHANGE and 
                                   exchange_name.lower() in e.normalized_value.lower()]
                for exch_entity in exchange_entities:
                    relationships.append(EntityRelationship(
                        source_entity_id=entity.entity_id,
                        target_entity_id=exch_entity.entity_id,
                        relationship_type=RelationshipType.LISTED_ON,
                        confidence=0.9,
                        evidence=f"Dictionary: {entity.canonical_name} listed on {exchange_name}",
                        metadata={"source": "dictionary"}
                    ))
                    
            # Company -> Sector
            if entity.entity_type == EntityType.COMPANY and entity.metadata.get("sector"):
                sector_name = entity.metadata["sector"]
                sector_entities = [e for e in entities 
                                 if e.entity_type == EntityType.SECTOR and 
                                 sector_name.lower() in e.normalized_value.lower()]
                for sector_entity in sector_entities:
                    relationships.append(EntityRelationship(
                        source_entity_id=entity.entity_id,
                        target_entity_id=sector_entity.entity_id,
                        relationship_type=RelationshipType.OPERATES_IN,
                        confidence=0.85,
                        evidence=f"Dictionary: {entity.canonical_name} in {sector_name} sector",
                        metadata={"source": "dictionary"}
                    ))
                    
            # Company -> Industry
            if entity.entity_type == EntityType.COMPANY and entity.metadata.get("industry"):
                industry_name = entity.metadata["industry"]
                industry_entities = [e for e in entities 
                                   if e.entity_type == EntityType.INDUSTRY and 
                                   industry_name.lower() in e.normalized_value.lower()]
                for ind_entity in industry_entities:
                    relationships.append(EntityRelationship(
                        source_entity_id=entity.entity_id,
                        target_entity_id=ind_entity.entity_id,
                        relationship_type=RelationshipType.OPERATES_IN,
                        confidence=0.85,
                        evidence=f"Dictionary: {entity.canonical_name} in {industry_name} industry",
                        metadata={"source": "dictionary"}
                    ))
                    
            # Company -> Country
            if entity.entity_type == EntityType.COMPANY and entity.metadata.get("country"):
                country_code = entity.metadata["country"]
                country_entities = [e for e in entities 
                                  if e.entity_type == EntityType.COUNTRY and 
                                  country_code.lower() in e.normalized_value.lower()]
                for country_entity in country_entities:
                    relationships.append(EntityRelationship(
                        source_entity_id=entity.entity_id,
                        target_entity_id=country_entity.entity_id,
                        relationship_type=RelationshipType.HEADQUARTERED_IN,
                        confidence=0.85,
                        evidence=f"Dictionary: {entity.canonical_name} headquartered in {country_code}",
                        metadata={"source": "dictionary"}
                    ))
                    
        return relationships
        
    def _deduplicate_relationships(self, relationships: List[EntityRelationship]) -> List[EntityRelationship]:
        """Remove duplicate relationships."""
        seen = set()
        unique = []
        
        for rel in relationships:
            key = (rel.source_entity_id, rel.target_entity_id, rel.relationship_type)
            if key not in seen:
                seen.add(key)
                unique.append(rel)
            else:
                # Keep the one with higher confidence
                existing_idx = next(i for i, r in enumerate(unique) 
                                  if (r.source_entity_id, r.target_entity_id, r.relationship_type) == key)
                if rel.confidence > unique[existing_idx].confidence:
                    unique[existing_idx] = rel
                    
        return unique
        
    async def build_relationships_async(
        self, 
        entities: List[Entity], 
        text: str,
        max_relationships: int = 100
    ) -> List[EntityRelationship]:
        """Async version of build_relationships."""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None, self.build_relationships, entities, text, max_relationships
        )


# Singleton instance
_relationship_builder: Optional[RelationshipBuilder] = None


def get_relationship_builder(dictionary: Optional[FinancialDictionary] = None) -> RelationshipBuilder:
    """Get or create the default relationship builder."""
    global _relationship_builder
    if _relationship_builder is None:
        _relationship_builder = RelationshipBuilder(dictionary)
    return _relationship_builder