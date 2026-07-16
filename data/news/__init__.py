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
    CompositeNewsProvider,
    YahooFinanceNewsProvider,
    FinnhubNewsProvider,
    AlphaVantageNewsProvider,
    NewsAPIProvider,
    RSSProvider,
    GoogleNewsRSSProvider
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
    "CompositeNewsProvider",
    "YahooFinanceNewsProvider",
    "FinnhubNewsProvider",
    "AlphaVantageNewsProvider",
    "NewsAPIProvider",
    "RSSNewsProvider",
    "GoogleNewsRSSProvider"
]