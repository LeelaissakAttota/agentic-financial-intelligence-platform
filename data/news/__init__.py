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
]