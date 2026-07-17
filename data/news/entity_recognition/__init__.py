"""
Financial Entity Recognition Package

Hybrid NLP pipeline for extracting financial entities from news text.
"""

from data.news.entity_recognition.schemas import (
    # Enums
    EntityType,
    EntitySubType,
    RelationshipType,
    ConfidenceLevel,
    ValidationMethod,
    
    # Data classes
    Entity,
    EntityRelationship,
    EntityExtractionResult,
    ExtractionConfig,
    ConfidenceFactor,
    ConfidenceFactors,
    
    # Type aliases
    EntityID,
    Position,
)

from data.news.entity_recognition.entity_extractor import (
    FinancialEntityExtractor,
    ExtractionPipelineConfig,
    get_entity_extractor,
    extract_entities,
)

from data.news.entity_recognition.rule_based_extractor import (
    RuleBasedExtractor,
    RegexPattern,
    get_rule_extractor,
)

from data.news.entity_recognition.dictionary import (
    FinancialDictionary,
    DictionaryEntry,
    get_financial_dictionary,
)

from data.news.entity_recognition.local_ner import (
    LocalNerExtractor,
    SpacyNERConfig,
    get_local_ner_extractor,
)

from data.news.entity_recognition.llm_validator import (
    LLMValidator,
    ValidationAction,
    ValidationResult,
    get_llm_validator,
)

from data.news.entity_recognition.ticker_resolver import (
    TickerResolver,
    TickerMatch,
    get_ticker_resolver,
)

from data.news.entity_recognition.company_resolver import (
    CompanyResolver,
    CompanyMatch,
    get_company_resolver,
)

from data.news.entity_recognition.alias_resolver import (
    AliasResolver,
    AliasMatch,
    get_alias_resolver,
)

from data.news.entity_recognition.relationship_builder import (
    RelationshipBuilder,
    get_relationship_builder,
)

from data.news.entity_recognition.confidence_engine import (
    ConfidenceEngine,
    get_confidence_engine,
)

from data.news.entity_recognition.entity_graph import (
    EntityGraph,
    GraphNode,
    GraphEdge,
    GraphQueryType,
    get_entity_graph,
)

__version__ = "2.3.0"

__all__ = [
    # Schemas
    "EntityType",
    "EntitySubType", 
    "RelationshipType",
    "ConfidenceLevel",
    "ValidationMethod",
    "Entity",
    "EntityRelationship",
    "EntityExtractionResult",
    "ExtractionConfig",
    "ConfidenceFactor",
    "ConfidenceFactors",
    "EntityID",
    "Position",
    
    # Main extractor
    "FinancialEntityExtractor",
    "ExtractionPipelineConfig",
    "get_entity_extractor",
    "extract_entities",
    
    # Entity Recognition Components
    "RuleBasedExtractor",
    "RegexPattern",
    "get_rule_extractor",
    
    "FinancialDictionary",
    "DictionaryEntry",
    "get_financial_dictionary",
    
    "LocalNerExtractor",
    "SpacyNERConfig",
    "get_local_ner_extractor",
    
    "LLMValidator",
    "ValidationAction",
    "ValidationResult",
    "get_llm_validator",
    
    "TickerResolver",
    "TickerMatch",
    "get_ticker_resolver",
    
    "CompanyResolver",
    "CompanyMatch",
    "get_company_resolver",
    
    "AliasResolver",
    "AliasMatch",
    "get_alias_resolver",
    
    "RelationshipBuilder",
    "get_relationship_builder",
    
    "ConfidenceEngine",
    "get_confidence_engine",
    
    "EntityGraph",
    "GraphNode",
    "GraphEdge",
    "GraphQueryType",
    "get_entity_graph",
]