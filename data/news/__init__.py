"""
Data News Package - Real Financial News Intelligence
"""

from data.news.schemas import (
    NewsArticle,
    NewsSummary,
    NewsCategory,
    SentimentLabel,
    NewsSource,
    NewsAgentInput,
    NewsAgentOutput,
    WorkerResponse,
    CompanyMention,
    PersonMention,
    EventDetection,
    ArticleSentiment
)

from data.news.cache import (
    NewsCache,
    get_news_cache,
    close_news_cache
)

from data.news.providers import (
    get_news_provider,
    close_news_provider,
    CompositeNewsProvider,
    YahooFinanceNewsProvider,
    FinnhubNewsProvider,
    AlphaVantageNewsProvider,
    NewsAPIProvider,
    RSSProvider,
    create_google_news_provider,
    create_marketwatch_provider,
    create_cnbc_provider,
    create_reuters_business_provider,
    create_bloomberg_provider,
    create_financial_times_provider,
    create_wall_street_journal_provider,
    create_seeking_alpha_provider,
    create_benzinga_provider,
)

from data.news.entity_recognition import (
    FinancialEntityExtractor,
    ExtractionPipelineConfig,
    get_entity_extractor,
    extract_entities,
    # Components
    RuleBasedExtractor,
    RegexPattern,
    get_rule_extractor,
    FinancialDictionary,
    DictionaryEntry,
    get_financial_dictionary,
    LocalNerExtractor,
    SpacyNERConfig,
    get_local_ner_extractor,
    LLMValidator,
    ValidationAction,
    ValidationResult,
    get_llm_validator,
    TickerResolver,
    TickerMatch,
    get_ticker_resolver,
    CompanyResolver,
    CompanyMatch,
    get_company_resolver,
    AliasResolver,
    AliasMatch,
    get_alias_resolver,
    RelationshipBuilder,
    get_relationship_builder,
    ConfidenceEngine,
    ConfidenceFactors,
    get_confidence_engine,
    EntityGraph,
    GraphNode,
    GraphEdge,
    GraphQueryType,
    get_entity_graph,
    # Schemas
    EntityType,
    EntitySubType,
    RelationshipType,
    ConfidenceLevel,
    ValidationMethod,
    Entity,
    EntityRelationship,
    EntityExtractionResult,
    ExtractionConfig,
    EntityID,
    Position,
)

__all__ = [
    # Schemas
    "NewsArticle",
    "NewsSummary",
    "NewsCategory",
    "SentimentLabel",
    "NewsSource",
    "NewsAgentInput",
    "NewsAgentOutput",
    "WorkerResponse",
    "CompanyMention",
    "PersonMention",
    "EventDetection",
    "ArticleSentiment",
    
    # Cache
    "NewsCache",
    "get_news_cache",
    "close_news_cache",
    
    # Providers
    "get_news_provider",
    "close_news_provider",
    "CompositeNewsProvider",
    "YahooFinanceNewsProvider",
    "FinnhubNewsProvider",
    "AlphaVantageNewsProvider",
    "NewsAPIProvider",
    "RSSProvider",
    "create_google_news_provider",
    "create_marketwatch_provider",
    "create_cnbc_provider",
    "create_reuters_business_provider",
    "create_bloomberg_provider",
    "create_financial_times_provider",
    "create_wall_street_journal_provider",
    "create_seeking_alpha_provider",
    "create_benzinga_provider",
    
    # Entity Recognition
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
    "ConfidenceFactors",
    "get_confidence_engine",
    
    "EntityGraph",
    "GraphNode",
    "GraphEdge",
    "GraphQueryType",
    "get_entity_graph",
    
    # Entity Recognition Schemas
    "EntityType",
    "EntitySubType",
    "RelationshipType",
    "ConfidenceLevel",
    "ValidationMethod",
    "Entity",
    "EntityRelationship",
    "EntityExtractionResult",
    "ExtractionConfig",
    "EntityID",
    "Position",
]