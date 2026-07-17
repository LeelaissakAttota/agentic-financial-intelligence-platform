"""
Main Financial Entity Extractor

Orchestrates the hybrid extraction pipeline:
1. Rule-based extraction (regex patterns)
2. Dictionary lookup (known entities)
3. Local NER (spaCy/GLiNER)
4. LLM validation (for ambiguous cases)
5. Entity resolution (ticker, company, alias)
6. Relationship building
7. Confidence scoring
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Set, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from data.news.entity_recognition.schemas import (
    Entity, EntityType, EntitySubType, EntityRelationship, RelationshipType,
    EntityExtractionResult, ExtractionConfig, ConfidenceLevel
)
from data.news.entity_recognition.rule_based_extractor import RuleBasedExtractor, get_rule_extractor
from data.news.entity_recognition.dictionary import FinancialDictionary, get_financial_dictionary
from data.news.entity_recognition.local_ner import LocalNerExtractor, get_local_ner_extractor
from data.news.entity_recognition.llm_validator import LLMValidator, get_llm_validator
from data.news.entity_recognition.ticker_resolver import TickerResolver, get_ticker_resolver
from data.news.entity_recognition.company_resolver import CompanyResolver, get_company_resolver
from data.news.entity_recognition.alias_resolver import AliasResolver, get_alias_resolver
from data.news.entity_recognition.relationship_builder import RelationshipBuilder, get_relationship_builder
from data.news.entity_recognition.confidence_engine import ConfidenceEngine
from data.news.entity_recognition.entity_graph import EntityGraph, get_entity_graph

logger = logging.getLogger(__name__)


@dataclass
class ExtractionPipelineConfig:
    """Configuration for the extraction pipeline."""
    # Layer enablement
    enable_rule_based: bool = True
    enable_dictionary: bool = True
    enable_local_ner: bool = True
    enable_llm_validation: bool = True
    
    # Confidence thresholds
    local_ner_confidence_threshold: float = 0.7
    llm_validation_threshold: float = 0.6
    final_confidence_threshold: float = 0.5
    
    # LLM settings
    llm_model: str = "openai/gpt-4o-mini"
    llm_max_tokens: int = 2000
    llm_temperature: float = 0.1
    
    # Performance
    max_entities: int = 500
    max_relationships: int = 200
    enable_parallel: bool = True
    cache_results: bool = True
    
    # Entity filtering
    entity_types: Optional[List[EntityType]] = None
    min_entity_length: int = 2
    max_entity_length: int = 100


class FinancialEntityExtractor:
    """
    Main entry point for financial entity extraction.
    
    Implements the hybrid extraction pipeline:
    Layer 1: Rule-based (regex patterns for tickers, money, dates, metrics)
    Layer 2: Dictionary lookup (known companies, people, tickers, etc.)
    Layer 3: Local NER (spaCy/GLiNER for general entities)
    Layer 4: LLM validation (only for low-confidence/ambiguous entities)
    Layer 5: Entity resolution (tickers, companies, aliases)
    Layer 6: Relationship building
    Layer 7: Confidence scoring
    """
    
    def __init__(self, config: Optional[ExtractionPipelineConfig] = None):
        self.config = config or ExtractionPipelineConfig()
        
        # Initialize components
        self.rule_extractor = get_rule_extractor()
        self.dictionary = get_financial_dictionary()
        self.local_ner = None  # Lazy init
        self.llm_validator = None  # Lazy init
        self.ticker_resolver = get_ticker_resolver(self.dictionary)
        self.company_resolver = get_company_resolver(self.dictionary)
        self.alias_resolver = get_alias_resolver(self.dictionary)
        self.relationship_builder = get_relationship_builder(self.dictionary)
        self.confidence_engine = ConfidenceEngine()
        self.entity_graph = get_entity_graph()
        
        # Stats
        self.stats = {
            "extractions": 0,
            "entities_found": 0,
            "relationships_found": 0,
            "llm_calls": 0,
            "cache_hits": 0,
        }
        
    async def initialize(self) -> None:
        """Initialize async components."""
        self.dictionary.initialize()
        
        if self.config.enable_local_ner:
            self.local_ner = await get_local_ner_extractor()
            await self.local_ner.initialize()
            
        if self.config.enable_llm_validation:
            self.llm_validator = get_llm_validator(
                confidence_threshold=self.config.llm_validation_threshold,
                model=self.config.llm_model
            )
            await self.llm_validator.initialize()
            
        logger.info("Financial Entity Extractor initialized")
        
    async def extract(
        self, 
        text: str, 
        config: Optional[ExtractionConfig] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EntityExtractionResult:
        """
        Extract financial entities from text.
        
        Args:
            text: Input text to extract entities from
            config: Optional extraction configuration override
            metadata: Optional metadata (source, date, etc.)
            
        Returns:
            EntityExtractionResult with entities, relationships, and metadata
        """
        start_time = datetime.utcnow()
        config = config or ExtractionConfig()
        
        # Apply config overrides
        effective_config = self._merge_config(config)
        
        # Track all entities by extraction method
        entities_by_method: Dict[str, List[Entity]] = defaultdict(list)
        
        # ============================================================
        # Layer 1: Rule-based extraction
        # ============================================================
        if self.config.enable_rule_based:
            rule_entities = self.rule_extractor.extract(text)
            rule_entities = self._filter_entities(rule_entities, effective_config)
            for e in rule_entities:
                e.validation_method = "regex"
                entities_by_method["rule_based"].append(e)
            logger.debug(f"Rule-based: {len(rule_entities)} entities")
            
        # ============================================================
        # Layer 2: Dictionary lookup
        # ============================================================
        if self.config.enable_dictionary:
            dict_entities = await self._dictionary_extract(text)
            dict_entities = self._filter_entities(dict_entities, effective_config)
            for e in dict_entities:
                e.validation_method = "dictionary"
                entities_by_method["dictionary"].append(e)
            logger.debug(f"Dictionary: {len(dict_entities)} entities")
            
        # ============================================================
        # Layer 3: Local NER
        # ============================================================
        if self.config.enable_local_ner and self.local_ner:
            ner_entities = await self._local_ner_extract(text)
            ner_entities = self._filter_entities(ner_entities, effective_config)
            for e in ner_entities:
                e.validation_method = "local_ner"
                entities_by_method["local_ner"].append(e)
            logger.debug(f"Local NER: {len(ner_entities)} entities")
            
        # ============================================================
        # Merge and deduplicate entities
        # ============================================================
        merged_entities = self._merge_entities(entities_by_method)
        logger.debug(f"Merged: {len(merged_entities)} unique entities")
        
        # ============================================================
        # Layer 4: LLM validation (for low-confidence entities)
        # ============================================================
        if self.config.enable_llm_validation and self.llm_validator:
            validated_entities = await self._llm_validate(merged_entities, text, effective_config)
            merged_entities = validated_entities
            logger.debug(f"After LLM validation: {len(merged_entities)} entities")
            
        # ============================================================
        # Layer 5: Entity resolution
        # ============================================================
        resolved_entities = await self._resolve_entities(merged_entities, text)
        logger.debug(f"After resolution: {len(resolved_entities)} entities")
        
        # ============================================================
        # Layer 6: Confidence scoring
        # ============================================================
        scored_entities = self._score_confidence(resolved_entities, text, entities_by_method)
        logger.debug(f"Scored {len(scored_entities)} entities")
        
        # Filter by final confidence threshold
        final_entities = [
            e for e in scored_entities 
            if e.confidence >= self.config.final_confidence_threshold
        ]
        final_entities = final_entities[:self.config.max_entities]
        
        # ============================================================
        # Layer 7: Relationship building
        # ============================================================
        relationships = self.relationship_builder.build_relationships(
            final_entities, text, self.config.max_relationships
        )
        logger.debug(f"Built {len(relationships)} relationships")
        
        # Build entity graph
        self.entity_graph.add_entities(final_entities)
        self.entity_graph.add_relationships(relationships)
        
        # ============================================================
        # Prepare result
        # ============================================================
        elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Group entities by type
        entities_by_type = defaultdict(list)
        for e in final_entities:
            entities_by_type[e.entity_type].append(e)
            
        # Confidence summary
        confidence_summary = self._build_confidence_summary(final_entities)
        
        result = EntityExtractionResult(
            entities=final_entities,
            relationships=relationships,
            entities_by_type=dict(entities_by_type),
            confidence_summary=confidence_summary,
            extraction_time_ms=elapsed,
            metadata=metadata or {},
            text_length=len(text),
            config_used=effective_config.dict() if hasattr(effective_config, 'dict') else vars(effective_config),
        )
        
        # Update stats
        self.stats["extractions"] += 1
        self.stats["entities_found"] += len(final_entities)
        self.stats["relationships_found"] += len(relationships)
        
        return result
        
    def _merge_config(self, config: ExtractionConfig) -> ExtractionConfig:
        """Merge pipeline config with extraction config."""
        # For now, just return the extraction config
        return config
        
    def _filter_entities(self, entities: List[Entity], config: ExtractionConfig) -> List[Entity]:
        """Filter entities based on config."""
        filtered = []
        for e in entities:
            # Length filter
            if len(e.text) < self.config.min_entity_length:
                continue
            if len(e.text) > self.config.max_entity_length:
                continue
                
            # Type filter
            if config.entity_types and e.entity_type not in config.entity_types:
                continue
                
            # Confidence filter
            if e.confidence < config.confidence_threshold:
                continue
                
            filtered.append(e)
            
        return filtered
        
    async def _dictionary_extract(self, text: str) -> List[Entity]:
        """Extract entities using dictionary lookup."""
        entities = []
        words = text.split()
        
        # Check n-grams (up to 5 words)
        for n in range(5, 0, -1):
            for i in range(len(words) - n + 1):
                phrase = ' '.join(words[i:i+n])
                
                # Skip if already found as part of longer match
                if any(e.start_char <= i and e.end_char >= i + len(phrase) for e in entities):
                    continue
                    
                entry = self.dictionary.lookup(phrase)
                if entry:
                    entity = entry.to_entity(phrase, i, i + len(phrase), 0.95)
                    entities.append(entity)
                    
        return entities
        
    async def _local_ner_extract(self, text: str) -> List[Entity]:
        """Extract entities using local NER."""
        if not self.local_ner:
            return []
            
        return await self.local_ner.extract(text)
        
    def _merge_entities(self, entities_by_method: Dict[str, List[Entity]]) -> List[Entity]:
        """Merge entities from multiple extraction methods."""
        # Group by normalized value and type
        groups = defaultdict(list)
        
        for method, entities in entities_by_method.items():
            for entity in entities:
                key = (entity.normalized_value.lower(), entity.entity_type)
                groups[key].append((method, entity))
                
        merged = []
        
        for (norm_value, entity_type), entries in groups.items():
            if len(entries) == 1:
                # Single extraction - keep as is
                method, entity = entries[0]
                entity.metadata["extraction_methods"] = [method]
                merged.append(entity)
            else:
                # Multiple extractions - merge
                # Sort by confidence
                entries.sort(key=lambda x: x[1].confidence, reverse=True)
                
                best_method, best_entity = entries[0]
                methods = [m for m, _ in entries]
                
                # Merge metadata
                for method, entity in entries[1:]:
                    for k, v in entity.metadata.items():
                        if k not in best_entity.metadata:
                            best_entity.metadata[k] = v
                            
                best_entity.metadata["extraction_methods"] = methods
                best_entity.confidence = min(1.0, best_entity.confidence + 0.1 * (len(entries) - 1))
                best_entity.validation_method = "merged"
                
                merged.append(best_entity)
                
        return merged
        
    async def _llm_validate(
        self, 
        entities: List[Entity], 
        text: str,
        config: ExtractionConfig
    ) -> List[Entity]:
        """Validate low-confidence entities with LLM."""
        if not self.llm_validator:
            return entities
            
        # Find entities needing validation
        needs_validation = [
            e for e in entities 
            if e.confidence < self.config.llm_validation_threshold
        ]
        
        if not needs_validation:
            return entities
            
        logger.info(f"LLM validating {len(needs_validation)} entities")
        
        try:
            validated = await self.llm_validator.validate_and_apply(needs_validation, text)
            self.stats["llm_calls"] += 1
            
            # Replace validated entities
            validated_ids = {id(v) for v in validated}
            result = []
            for e in entities:
                if id(e) in validated_ids:
                    # Find matching validated entity
                    for v in validated:
                        if v.normalized_value == e.normalized_value and v.entity_type == e.entity_type:
                            result.append(v)
                            break
                else:
                    result.append(e)
                    
            return result
            
        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            return entities
            
    async def _resolve_entities(self, entities: List[Entity], text: str) -> List[Entity]:
        """Apply entity resolution (tickers, companies, aliases)."""
        resolved = []
        
        for entity in entities:
            # Ticker resolution
            if entity.entity_type == EntityType.TICKER:
                ticker_match = self.ticker_resolver.resolve(entity.text)
                if ticker_match:
                    entity = ticker_match.to_entity(entity.text, entity.start_char, entity.end_char)
                    
            # Company resolution
            elif entity.entity_type == EntityType.COMPANY:
                company_match = self.company_resolver.resolve(entity.text)
                if company_match:
                    entity = self.company_resolver.create_entity_from_company(
                        entity.text, entity.start_char, entity.end_char, company_match
                    )
                    
            # Alias resolution (for all types)
            alias_match = self.alias_resolver.resolve(entity.text)
            if alias_match and alias_match.canonical_name != entity.normalized_value:
                entity = self.alias_resolver.create_entity_from_alias(
                    entity.text, entity.start_char, entity.end_char, alias_match
                )
                
            resolved.append(entity)
            
        return resolved
        
    def _score_confidence(
        self, 
        entities: List[Entity], 
        text: str,
        entities_by_method: Dict[str, List[Entity]]
    ) -> List[Entity]:
        """Score entity confidence using confidence engine."""
        for entity in entities:
            # Determine extraction methods for this entity
            methods = entity.metadata.get("extraction_methods", ["rule_based"])
            
            # Count duplicates
            duplicate_count = sum(
                1 for e in entities 
                if e.normalized_value == entity.normalized_value and e.entity_id != entity.entity_id
            ) + 1
            
            # Section info
            section = "body"
            if entity.start_char < len(text) * 0.05:
                section = "headline" if entity.start_char < 100 else "lead"
                
            factors = self.confidence_engine.calculate_entity_confidence(
                entity=entity,
                text=text,
                all_entities=entities,
                extraction_methods=methods,
                section=section,
            )
            
            # Update entity with confidence factors
            entity.confidence = factors.final_confidence
            entity.metadata["confidence_factors"] = factors.dict()
            entity.metadata["confidence_level"] = factors.confidence_level.value
            
        return entities
        
    def _build_confidence_summary(self, entities: List[Entity]) -> Dict[str, Any]:
        """Build confidence summary statistics."""
        if not entities:
            return {}
            
        levels = defaultdict(int)
        type_confidence = defaultdict(list)
        
        for e in entities:
            levels[e.metadata.get("confidence_level", "unknown")] += 1
            type_confidence[e.entity_type.value].append(e.confidence)
            
        return {
            "by_level": dict(levels),
            "by_type": {
                t: {
                    "count": len(confidences),
                    "avg": sum(confidences) / len(confidences),
                    "min": min(confidences),
                    "max": max(confidences),
                }
                for t, confidences in type_confidence.items()
            },
            "total_entities": len(entities),
            "avg_confidence": sum(e.confidence for e in entities) / len(entities),
        }
        
    async def extract_batch(
        self, 
        texts: List[str], 
        config: Optional[ExtractionConfig] = None
    ) -> List[EntityExtractionResult]:
        """Extract entities from multiple texts in parallel."""
        if self.config.enable_parallel:
            tasks = [self.extract(text, config) for text in texts]
            return await asyncio.gather(*tasks)
        else:
            results = []
            for text in texts:
                results.append(await self.extract(text, config))
            return results
            
    async def extract_stream(
        self, 
        texts: AsyncIterator[str], 
        config: Optional[ExtractionConfig] = None
    ) -> AsyncIterator[EntityExtractionResult]:
        """Extract entities from a stream of texts."""
        async for text in texts:
            yield await self.extract(text, config)
            
    def get_stats(self) -> Dict[str, Any]:
        """Get extraction statistics."""
        return self.stats.copy()
        
    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = {
            "extractions": 0,
            "entities_found": 0,
            "relationships_found": 0,
            "llm_calls": 0,
            "cache_hits": 0,
        }
        
    def get_entity_graph(self) -> EntityGraph:
        """Get the built entity graph."""
        return self.entity_graph
        
    def clear_graph(self) -> None:
        """Clear the entity graph."""
        self.entity_graph = get_entity_graph()


# Global instance
_extractor: Optional[FinancialEntityExtractor] = None


async def get_entity_extractor(
    config: Optional[ExtractionPipelineConfig] = None
) -> FinancialEntityExtractor:
    """Get or create the global entity extractor."""
    global _extractor
    if _extractor is None:
        _extractor = FinancialEntityExtractor(config)
        await _extractor.initialize()
    return _extractor


async def extract_entities(
    text: str,
    config: Optional[ExtractionConfig] = None,
    metadata: Optional[Dict[str, Any]] = None,
    extractor_config: Optional[ExtractionPipelineConfig] = None
) -> EntityExtractionResult:
    """
    Convenience function to extract entities from text.
    
    Args:
        text: Input text
        config: Extraction configuration
        metadata: Optional metadata
        extractor_config: Pipeline configuration
        
    Returns:
        EntityExtractionResult
    """
    extractor = await get_entity_extractor(extractor_config)
    return await extractor.extract(text, config, metadata)