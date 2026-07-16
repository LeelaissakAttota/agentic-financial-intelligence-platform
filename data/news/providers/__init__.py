"""
News Providers Package
"""

from data.news.providers.base import (
    NewsProviderBase,
    ProviderConfig,
    ProviderHealth,
    RateLimiter,
    NewsProviderError,
    NewsProviderTimeoutError,
    NewsProviderRateLimitError,
    NewsProviderAuthError,
    register_provider,
    get_provider_class,
    list_providers
)

from data.news.providers.yahoo import YahooFinanceNewsProvider
from data.news.providers.finnhub import FinnhubNewsProvider
from data.news.providers.alpha_vantage import AlphaVantageNewsProvider
from data.news.providers.newsapi import NewsAPIProvider
from data.news.providers.rss import (
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
from data.news.providers.manager import (
    CompositeNewsProvider,
    get_news_provider,
    close_news_provider
)

__all__ = [
    # Base
    "NewsProviderBase",
    "ProviderConfig",
    "ProviderHealth",
    "RateLimiter",
    "NewsProviderError",
    "NewsProviderTimeoutError",
    "NewsProviderRateLimitError",
    "NewsProviderAuthError",
    "register_provider",
    "get_provider_class",
    "list_providers",
    # Providers
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
    # Manager
    "CompositeNewsProvider",
    "get_news_provider",
    "close_news_provider",
]

# Register all providers
register_provider("yahoo_finance", YahooFinanceNewsProvider)
register_provider("finnhub", FinnhubNewsProvider)
register_provider("alpha_vantage", AlphaVantageNewsProvider)
register_provider("newsapi", NewsAPIProvider)
register_provider("rss", RSSProvider)
register_provider("google_news", lambda: create_google_news_provider())
register_provider("marketwatch", create_marketwatch_provider)
register_provider("cnbc", create_cnbc_provider)
register_provider("reuters", create_reuters_business_provider)
register_provider("bloomberg", create_bloomberg_provider)
register_provider("financial_times", create_financial_times_provider)
register_provider("wall_street_journal", create_wall_street_journal_provider)
register_provider("seeking_alpha", create_seeking_alpha_provider)
register_provider("benzinga", create_benzinga_provider)

__all__ = [
    "NewsProviderBase",
    "ProviderConfig",
    "ProviderHealth",
    "RateLimiter",
    "NewsProviderError",
    "NewsProviderTimeoutError",
    "NewsProviderRateLimitError",
    "NewsProviderAuthError",
    "register_provider",
    "get_provider_class",
    "list_providers",
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