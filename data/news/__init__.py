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

from data.news.aggregator import (
    NewsAggregator,
    AggregatorConfig,
    ArticleEnrichment,
)

from data.news.intelligence import (
    CompanyNewsIntelligence,
    IntelligenceConfig,
    CompanyIntelligence,
    ArticleIntelligence,
    FinancialEventDetector,
    CompanyResolver,
    extract_company_intelligence,
)

from data.news.summarizer import (
    NewsSummarizer,
    SummarizationConfig,
    NewsSummaryResult,
)

from data.news.database import (
    NewsArticleModel,
    CompanyModel,
    ArticleCompanyLink,
    NewsSummaryModel,
    NewsEmbeddingModel,
    NewsWatchlistModel,
    upsert_article,
    upsert_company,
    link_article_company,
    get_articles_for_company,
    get_recent_articles,
    get_sentiment_trend,
    get_top_companies_by_mentions,
    create_news_summary,
    get_latest_summary,
)

from data.news.pipeline import (
    NewsPipeline,
    PipelineConfig,
    run_news_pipeline,
)

from data.news.dashboard import (
    render_news_dashboard_tab,
    fetch_news_data,
    render_latest_news,
    render_news_timeline,
    render_news_sentiment,
    render_source_breakdown,
    render_related_companies,
    get_source_credibility,
    get_source_tier,
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
    
    # News Aggregator
    "NewsAggregator",
    "AggregatorConfig",
    "ArticleEnrichment",
    
    # News Intelligence
    "CompanyNewsIntelligence",
    "IntelligenceConfig",
    "CompanyIntelligence",
    "ArticleIntelligence",
    "FinancialEventDetector",
    "CompanyResolver",
    "extract_company_intelligence",
    
    # News Summarizer
    "NewsSummarizer",
    "SummarizationConfig",
    "NewsSummaryResult",
    
    # News Database
    "NewsArticleModel",
    "CompanyModel",
    "ArticleCompanyLink",
    "NewsSummaryModel",
    "NewsEmbeddingModel",
    "NewsWatchlistModel",
    "upsert_article",
    "upsert_company",
    "link_article_company",
    "get_articles_for_company",
    "get_recent_articles",
    "get_sentiment_trend",
    "get_top_companies_by_mentions",
    "create_news_summary",
    "get_latest_summary",
    
    # News Pipeline
    "NewsPipeline",
    "PipelineConfig",
    "run_news_pipeline",
    
    # News Dashboard
    "render_news_dashboard_tab",
    "fetch_news_data",
    "render_latest_news",
    "render_news_timeline",
    "render_news_sentiment",
    "render_source_breakdown",
    "render_related_companies",
    "get_source_credibility",
    "get_source_tier",
]