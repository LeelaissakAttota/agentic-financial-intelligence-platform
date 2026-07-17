"""
LLM Validator for Financial Entity Recognition

Uses LLM (via OpenRouter) to validate and disambiguate entities when local extraction
confidence is below threshold. Handles alias resolution, entity disambiguation,
and relationship inference.
"""

import json
import logging
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass
from enum import Enum

from data.news.entity_recognition.schemas import (
    Entity, EntityType, EntitySubType, ConfidenceLevel
)
from data.news.entity_recognition.dictionary import FinancialDictionary

logger = logging.getLogger(__name__)


class ValidationAction(Enum):
    """Actions the LLM validator can take."""
    CONFIRM = "confirm"              # Entity is correct as-is
    CORRECT = "correct"              # Fix entity type/normalization
    MERGE = "merge"                  # Merge with another entity
    SPLIT = "split"                  # Split into multiple entities
    REJECT = "reject"                # Remove false positive
    ENRICH = "enrich"                # Add missing metadata (ticker, CIK, etc.)
    DISAMBIGUATE = "disambiguate"    # Resolve ambiguous entity


@dataclass
class ValidationResult:
    """Result of LLM validation for an entity."""
    entity: Entity
    action: ValidationAction
    confidence: float
    reasoning: str
    corrected_entity: Optional[Entity] = None
    merged_with: Optional[str] = None  # Entity ID to merge with
    enriched_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.enriched_metadata is None:
            self.enriched_metadata = {}


class LLMValidator:
    """
    LLM-based entity validator for financial NER.
    
    Uses OpenRouter to:
    1. Disambiguate entities with low local confidence
    2. Resolve aliases (Apple -> Apple Inc. / AAPL)
    3. Validate entity types and relationships
    4. Enrich entities with metadata (ticker, CIK, exchange)
    5. Detect and merge duplicate entities
    """
    
    # Confidence threshold below which LLM validation is triggered
    DEFAULT_CONFIDENCE_THRESHOLD = 0.75
    
    # Maximum entities to send to LLM in one batch
    MAX_BATCH_SIZE = 20
    
    # System prompt for financial entity validation
    SYSTEM_PROMPT = """You are a financial entity validation expert. Your task is to validate, correct, and enrich financial entities extracted from news articles.

You will receive a list of entities with their extracted text, entity type, confidence score, and context. For each entity, you must:

1. **Validate** - Is this entity correctly identified and typed?
2. **Disambiguate** - Resolve ambiguous names (e.g., "Apple" -> "Apple Inc." / AAPL, "Google" -> "Alphabet Inc." / GOOGL)
3. **Enrich** - Add missing metadata (ticker, CIK, exchange, sector, industry)
4. **Detect Duplicates** - Identify entities that refer to the same real-world entity
5. **Correct** - Fix incorrect entity types or normalizations

Entity Types:
- COMPANY: Public/private companies, financial institutions
- TICKER: Stock ticker symbols (AAPL, MSFT, BRK.A)
- PERSON: Executives, investors, analysts, regulators
- EXCHANGE: Stock exchanges (NYSE, NASDAQ, LSE, etc.)
- INDEX: Market indices (S&P 500, DJIA, NASDAQ 100, etc.)
- CURRENCY: Fiat currencies (USD, EUR, GBP, etc.)
- CRYPTOCURRENCY: Digital assets (BTC, ETH, etc.)
- COMMODITY: Physical commodities (Gold, Oil, etc.)
- METRIC: Financial metrics (Revenue, EPS, EBITDA, etc.)
- EVENT: Financial events (earnings, M&A, IPO, etc.)
- REGULATOR: Regulatory bodies (SEC, FED, ECB, etc.)
- CENTRAL_BANK: Central banks (Federal Reserve, ECB, etc.)
- SECTOR: Market sectors (Technology, Healthcare, etc.)
- DATE: Financial dates (quarters, fiscal years, etc.)
- MONEY: Monetary amounts
- PERCENTAGE: Percentages and basis points
- COUNTRY: Countries
- CITY: Cities
- PRODUCT: Products/brands

For companies, always provide:
- canonical_name: Official company name
- ticker: Primary ticker symbol (if public)
- exchange: Primary exchange (if public)
- cik: SEC CIK number (if available)
- sector: GICS sector
- industry: GICS industry

For people, provide:
- canonical_name: Full official name
- role: Title/position (CEO, CFO, Founder, Investor, Analyst)
- company: Associated company

Return JSON with validation results for each entity."""

    def __init__(
        self,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        max_batch_size: int = MAX_BATCH_SIZE,
        openrouter_client=None,
        model: str = "anthropic/claude-3.5-sonnet",
    ):
        self.confidence_threshold = confidence_threshold
        self.max_batch_size = max_batch_size
        self.openrouter_client = openrouter_client
        self.model = model
        self._dictionary = FinancialDictionary()
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize the validator."""
        if self._initialized:
            return
            
        # Initialize dictionary
        self._dictionary.initialize()
        
        # Initialize OpenRouter client if not provided
        if self.openrouter_client is None:
            try:
                from core.llm import get_openrouter_client
                self.openrouter_client = await get_openrouter_client()
            except Exception as e:
                logger.warning(f"Could not initialize OpenRouter client: {e}")
                
        self._initialized = True
        logger.info("LLM Validator initialized")
        
    def _should_validate(self, entity: Entity) -> bool:
        """Determine if an entity should be validated by LLM."""
        # Always validate low confidence entities
        if entity.confidence < self.confidence_threshold:
            return True
            
        # Validate ambiguous entity types
        if entity.entity_type in [EntityType.COMPANY, EntityType.PERSON, EntityType.TICKER]:
            # Check if it's a known alias that needs resolution
            if self._is_ambiguous(entity):
                return True
                
        # Validate entities that might need enrichment
        if entity.entity_type == EntityType.COMPANY and not entity.ticker:
            return True
            
        return False
        
    def _is_ambiguous(self, entity: Entity) -> bool:
        """Check if entity text is ambiguous (common names, abbreviations)."""
        ambiguous_terms = {
            "apple", "microsoft", "amazon", "google", "meta", "facebook",
            "tesla", "nvidia", "intel", "amd", "ibm", "oracle", "salesforce",
            "netflix", "uber", "lyft", "airbnb", "twitter", "x", "snap",
            "jpmorgan", "jpm", "chase", "goldman", "morgan stanley", "ms",
            "citi", "citigroup", "wells fargo", "wfc", "bofa", "bank of america",
            "visa", "mastercard", "amex", "paypal", "square", "block",
            "berkshire", "brk", "buffett", "munger",
        }
        return entity.text.lower() in ambiguous_terms
        
    def _build_validation_prompt(self, entities: List[Entity], text: str) -> str:
        """Build the validation prompt for the LLM."""
        entity_data = []
        for i, ent in enumerate(entities):
            entity_data.append({
                "id": i,
                "text": ent.text,
                "entity_type": ent.entity_type.value,
                "sub_type": ent.sub_type.value if ent.sub_type else None,
                "confidence": ent.confidence,
                "start_char": ent.start_char,
                "end_char": ent.end_char,
                "normalized_value": ent.normalized_value,
                "metadata": ent.metadata,
            })
            
        prompt = f"""Validate the following financial entities extracted from this text:

TEXT:
{text[:3000]}

ENTITIES:
{json.dumps(entity_data, indent=2)}

For each entity, return a validation result with:
- id: entity index
- action: one of [confirm, correct, merge, split, reject, enrich, disambiguate]
- confidence: your confidence in this validation (0.0-1.0)
- reasoning: brief explanation
- corrected_entity: if action is correct/merge/split, provide corrected entity data
- merged_with: if action is merge, provide the id of entity to merge with
- enriched_metadata: additional metadata to add (ticker, cik, exchange, sector, industry, role, company, etc.)

Return as JSON array of validation results."""
        
        return prompt
        
    async def validate_entities(
        self,
        entities: List[Entity],
        text: str,
    ) -> List[ValidationResult]:
        """
        Validate entities using LLM.
        
        Args:
            entities: List of entities to validate
            text: Source text for context
            
        Returns:
            List of validation results
        """
        if not self._initialized:
            await self.initialize()
            
        # Filter entities that need validation
        to_validate = [e for e in entities if self._should_validate(e)]
        
        if not to_validate:
            # All entities pass validation
            return [
                ValidationResult(
                    entity=e,
                    action=ValidationAction.CONFIRM,
                    confidence=e.confidence,
                    reasoning="High confidence, no validation needed"
                )
                for e in entities
            ]
            
        # Batch if too many
        batches = [
            to_validate[i:i + self.max_batch_size]
            for i in range(0, len(to_validate), self.max_batch_size)
        ]
        
        all_results = []
        
        for batch in batches:
            results = await self._validate_batch(batch, text)
            all_results.extend(results)
            
        # Map results back to original entities
        entity_to_result = {id(r.entity): r for r in all_results}
        
        final_results = []
        for entity in entities:
            if id(entity) in entity_to_result:
                final_results.append(entity_to_result[id(entity)])
            else:
                final_results.append(ValidationResult(
                    entity=entity,
                    action=ValidationAction.CONFIRM,
                    confidence=entity.confidence,
                    reasoning="High confidence, no validation needed"
                ))
                
        return final_results
        
    async def _validate_batch(
        self,
        entities: List[Entity],
        text: str,
    ) -> List[ValidationResult]:
        """Validate a batch of entities."""
        if not self.openrouter_client:
            # Fallback: dictionary-based validation
            return await self._fallback_validate(entities, text)
            
        prompt = self._build_validation_prompt(entities, text)
        
        try:
            response = await self.openrouter_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=4000,
                response_format={"type": "json_object"},
            )
            
            content = response.choices[0].message.content
            results_data = json.loads(content)
            
            # Parse results
            results = []
            for item in results_data.get("results", []):
                entity_idx = item.get("id", 0)
                if entity_idx < len(entities):
                    entity = entities[entity_idx]
                    
                    action = ValidationAction(item.get("action", "confirm"))
                    confidence = float(item.get("confidence", entity.confidence))
                    reasoning = item.get("reasoning", "")
                    
                    corrected_entity = None
                    if "corrected_entity" in item and item["corrected_entity"]:
                        corrected_entity = Entity(**item["corrected_entity"])
                        
                    enriched_metadata = item.get("enriched_metadata", {})
                    merged_with = item.get("merged_with")
                    
                    results.append(ValidationResult(
                        entity=entity,
                        action=action,
                        confidence=confidence,
                        reasoning=reasoning,
                        corrected_entity=corrected_entity,
                        merged_with=str(merged_with) if merged_with is not None else None,
                        enriched_metadata=enriched_metadata,
                    ))
                    
            return results
            
        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            # Fallback to dictionary-based validation
            return await self._fallback_validate(entities, text)
            
    async def _fallback_validate(
        self,
        entities: List[Entity],
        text: str,
    ) -> List[ValidationResult]:
        """Fallback validation using dictionary lookup."""
        results = []
        
        for entity in entities:
            # Try dictionary lookup
            dict_entry = self._dictionary.lookup(entity.text)
            
            if dict_entry:
                # Dictionary match found
                corrected = dict_entry.to_entity(
                    entity.text, entity.start_char, entity.end_char, 0.95
                )
                
                # Merge metadata
                for k, v in entity.metadata.items():
                    if k not in corrected.metadata:
                        corrected.metadata[k] = v
                        
                results.append(ValidationResult(
                    entity=entity,
                    action=ValidationAction.ENRICH,
                    confidence=0.95,
                    reasoning=f"Matched dictionary entry: {dict_entry.canonical_name}",
                    corrected_entity=corrected,
                    enriched_metadata=corrected.metadata,
                ))
            else:
                # No dictionary match, confirm with slightly lower confidence
                results.append(ValidationResult(
                    entity=entity,
                    action=ValidationAction.CONFIRM,
                    confidence=min(entity.confidence, 0.7),
                    reasoning="No dictionary match, confirming with reduced confidence"
                ))
                
        return results
        
    async def apply_validations(
        self,
        entities: List[Entity],
        validations: List[ValidationResult],
    ) -> List[Entity]:
        """Apply validation results to produce final entity list."""
        # Map entity to validation
        entity_id_to_validation = {id(v.entity): v for v in validations}
        
        final_entities = []
        merged_ids = set()
        
        for entity in entities:
            validation = entity_id_to_validation.get(id(entity))
            
            if not validation:
                final_entities.append(entity)
                continue
                
            action = validation.action
            
            if action == ValidationAction.REJECT:
                # Skip this entity
                continue
                
            elif action == ValidationAction.CONFIRM:
                # Keep entity, optionally update confidence
                entity.confidence = max(entity.confidence, validation.confidence)
                if validation.enriched_metadata:
                    entity.metadata.update(validation.enriched_metadata)
                final_entities.append(entity)
                
            elif action == ValidationAction.CORRECT:
                # Replace with corrected entity
                if validation.corrected_entity:
                    corrected = validation.corrected_entity
                    corrected.confidence = validation.confidence
                    if validation.enriched_metadata:
                        corrected.metadata.update(validation.enriched_metadata)
                    corrected.metadata.update(entity.metadata)
                    final_entities.append(corrected)
                else:
                    final_entities.append(entity)
                    
            elif action == ValidationAction.ENRICH:
                # Add enriched metadata
                entity.confidence = max(entity.confidence, validation.confidence)
                if validation.enriched_metadata:
                    entity.metadata.update(validation.enriched_metadata)
                if validation.corrected_entity:
                    for k, v in validation.corrected_entity.metadata.items():
                        if k not in entity.metadata:
                            entity.metadata[k] = v
                final_entities.append(entity)
                
            elif action == ValidationAction.MERGE:
                # Mark for merging (handled in second pass)
                merged_ids.add(id(entity))
                # Keep for now, will merge in post-processing
                final_entities.append(entity)
                
            elif action == ValidationAction.SPLIT:
                # Replace with split entities
                if validation.corrected_entity:
                    # For simplicity, treat as correction
                    final_entities.append(validation.corrected_entity)
                else:
                    final_entities.append(entity)
                    
            elif action == ValidationAction.DISAMBIGUATE:
                # Apply disambiguation
                if validation.corrected_entity:
                    corrected = validation.corrected_entity
                    corrected.confidence = validation.confidence
                    if validation.enriched_metadata:
                        corrected.metadata.update(validation.enriched_metadata)
                    final_entities.append(corrected)
                else:
                    final_entities.append(entity)
                    
        # Post-process merges
        # (In a full implementation, this would merge entities with same merged_with id)
        
        return final_entities
        
    async def validate_and_apply(
        self,
        entities: List[Entity],
        text: str,
    ) -> List[Entity]:
        """Validate entities and apply results in one call."""
        validations = await self.validate_entities(entities, text)
        return await self.apply_validations(entities, validations)


# Singleton instance
_llm_validator: Optional[LLMValidator] = None


async def get_llm_validator(
    confidence_threshold: float = LLMValidator.DEFAULT_CONFIDENCE_THRESHOLD,
    **kwargs
) -> LLMValidator:
    """Get or create the default LLM validator."""
    global _llm_validator
    if _llm_validator is None:
        _llm_validator = LLMValidator(confidence_threshold=confidence_threshold, **kwargs)
        await _llm_validator.initialize()
    return _llm_validator