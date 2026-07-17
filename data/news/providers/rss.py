"""
RSS Feed News Providers for Financial News Sources
"""

import asyncio
import feedparser
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict

import aiohttp

from data.news.schemas import NewsArticle, NewsSource
from data.news.providers.base import NewsProviderBase, ProviderConfig, NewsProviderError

logger = logging.getLogger(__name__)


class RSSProvider(NewsProviderBase):
    """Generic RSS Feed Provider for financial news sources."""

    def __init__(self, config: Optional[ProviderConfig] = None, feed_url: str = ""):
        if config is None:
            config = ProviderConfig(
                name="rss",
                priority=5,
                rate_limit_per_min=20,
                rate_limit_per_day=2000,
                timeout_seconds=30
            )
        super().__init__(config)
        self.feed_url = feed_url
        self._company_keywords: List[str] = []

    def _set_company_keywords(self, company: str, ticker: Optional[str] = None) -> None:
        """Set keywords for relevance filtering."""
        self._company_keywords = [company.lower()]
        if ticker:
            self._company_keywords.append(ticker.lower())
            self._company_keywords.append(f"${ticker.lower()}")

    def _is_relevant(self, title: str, summary: str) -> bool:
        """Check if article is relevant to target company/ticker."""
        text = f"{title} {summary}".lower()
        return any(keyword in text for keyword in self._company_keywords)

    async def fetch_news(
        self,
        company: str,
        ticker: Optional[str] = None,
        lookback_hours: int = 24,
        max_articles: int = 50
    ) -> List[NewsArticle]:
        """Fetch news from RSS feed."""
        self._set_company_keywords(company, ticker)
        await self.rate_limiter.acquire()
        await self._ensure_session()

        try:
            async with self.session.get(self.feed_url) as resp:
                if resp.status != 200:
                    logger.error(f"RSS fetch error for {self.config.name}: {resp.status}")
                    return []
                content = await resp.text()

            feed = feedparser.parse(content)

            if feed.bozo:
                logger.warning(f"RSS feed parsing issue for {self.config.name}: {feed.bozo_exception}")

            articles = []
            cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)

            for entry in feed.entries[:max_articles]:
                try:
                    # Parse publish time
                    pub_time = None
                    for time_field in ['published_parsed', 'updated_parsed']:
                        if getattr(entry, time_field, None):
                            pub_time = datetime(*entry[time_field][:6])
                            break

                    if not pub_time or pub_time < cutoff:
                        continue

                    title = entry.get('title', '')
                    summary = entry.get('summary', '') or entry.get('description', '')
                    url = entry.get('link', '')

                    if not title or not url:
                        continue

                    # Relevance check
                    if not self._is_relevant(title, summary):
                        continue

                    article = NewsArticle(
                        title=title,
                        summary=summary[:500],
                        content=None,
                        url=url,
                        source=self.config.source_type,
                        source_name=self.config.name,
                        published_at=pub_time,
                        author=entry.get('author'),
                        content_hash=self._create_article_hash(title, url)
                    )

                    article.sentiment = await self._analyze_sentiment(title, summary)
                    article.events = self._detect_events(title, summary)
                    article.tickers = self._extract_tickers(f"{title} {summary}")
                    article.importance_score = self._calculate_importance(article)
                    article.market_impact_score = self._calculate_market_impact(article)
                    article.freshness_score = self._calculate_freshness(pub_time)
                    article.relevance_score = self._calculate_relevance(article, company, ticker)

                    articles.append(article)

                except Exception as e:
                    logger.warning(f"Error parsing RSS entry from {self.config.name}: {e}")
                    continue

            logger.info(f"Fetched {len(articles)} articles from {self.config.name} for {company}")
            return articles

        except Exception as e:
            logger.error(f"RSS fetch failed for {self.config.name}: {e}")
            raise NewsProviderError(f"RSS fetch failed: {e}")


def create_google_news_provider() -> RSSProvider:
    """Create Google News RSS Provider."""
    config = ProviderConfig(
        name="google_news",
        priority=5,
        rate_limit_per_min=20,
        rate_limit_per_day=1000,
        timeout_seconds=30,
        source_type=NewsSource.GOOGLE_NEWS
    )
    return RSSProvider(
        config=config,
        feed_url="https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en"
    )


def create_marketwatch_provider() -> RSSProvider:
    """Create MarketWatch RSS Provider."""
    config = ProviderConfig(
        name="marketwatch",
        priority=6,
        rate_limit_per_min=15,
        rate_limit_per_day=500,
        timeout_seconds=30,
        source_type=NewsSource.MARKETWATCH
    )
    return RSSProvider(
        config=config,
        feed_url="https://feeds.marketwatch.com/marketwatch/topstories/"
    )


def create_marketwatch_top_provider() -> RSSProvider:
    """Create MarketWatch Top Stories RSS Provider."""
    config = ProviderConfig(
        name="marketwatch_top",
        priority=6,
        rate_limit_per_min=15,
        rate_limit_per_day=500,
        timeout_seconds=30,
        source_type=NewsSource.MARKETWATCH
    )
    return RSSProvider(
        config=config,
        feed_url="https://feeds.marketwatch.com/marketwatch/topstories/"
    )


def create_cnbc_provider() -> RSSProvider:
    """Create CNBC RSS Provider."""
    config = ProviderConfig(
        name="cnbc",
        priority=6,
        rate_limit_per_min=15,
        rate_limit_per_day=500,
        timeout_seconds=30,
        source_type=NewsSource.CNBC
    )
    return RSSProvider(
        config=config,
        feed_url="https://www.cnbc.com/id/100003114/device/rss/rss.html"
    )


def create_cnbc_top_provider() -> RSSProvider:
    """Create CNBC Top News RSS Provider."""
    config = ProviderConfig(
        name="cnbc_top",
        priority=6,
        rate_limit_per_min=15,
        rate_limit_per_day=500,
        timeout_seconds=30,
        source_type=NewsSource.CNBC
    )
    return RSSProvider(
        config=config,
        feed_url="https://www.cnbc.com/id/10001147/device/rss/rss.html"
    )


def create_reuters_business_provider() -> RSSProvider:
    """Create Reuters Business News RSS Provider."""
    config = ProviderConfig(
        name="reuters_business",
        priority=5,
        rate_limit_per_min=15,
        rate_limit_per_day=500,
        timeout_seconds=30,
        source_type=NewsSource.REUTERS
    )
    return RSSProvider(
        config=config,
        feed_url="https://feeds.reuters.com/reuters/businessNews"
    )


def create_bloomberg_provider() -> RSSProvider:
    """Create Bloomberg RSS Provider."""
    config = ProviderConfig(
        name="bloomberg",
        priority=5,
        rate_limit_per_min=15,
        rate_limit_per_day=500,
        timeout_seconds=30,
        source_type=NewsSource.BLOOMBERG
    )
    return RSSProvider(
        config=config,
        feed_url="https://feeds.bloomberg.com/markets/news.rss"
    )


def create_marketwatch_top_provider() -> RSSProvider:
    """Create MarketWatch Top Stories RSS Provider."""
    config = ProviderConfig(
        name="marketwatch_top",
        priority=6,
        rate_limit_per_min=15,
        rate_limit_per_day=500,
        timeout_seconds=30,
        source_type=NewsSource.MARKETWATCH
    )
    return RSSProvider(
        config=config,
        feed_url="https://feeds.marketwatch.com/marketwatch/topstories/"
    )


def create_financial_times_provider() -> RSSProvider:
    """Create Financial Times RSS Provider."""
    config = ProviderConfig(
        name="financial_times",
        priority=5,
        rate_limit_per_min=15,
        rate_limit_per_day=500,
        timeout_seconds=30,
        source_type=NewsSource.FINANCIAL_TIMES
    )
    return RSSProvider(
        config=config,
        feed_url="https://www.ft.com/rss/home"
    )


def create_wall_street_journal_provider() -> RSSProvider:
    """Create Wall Street Journal RSS Provider."""
    config = ProviderConfig(
        name="wall_street_journal",
        priority=5,
        rate_limit_per_min=15,
        rate_limit_per_day=500,
        timeout_seconds=30,
        source_type=NewsSource.WALL_STREET_JOURNAL
    )
    return RSSProvider(
        config=config,
        feed_url="https://feeds.wsj.com/xml/rss/3_7085.xml"
    )


def create_seeking_alpha_provider() -> RSSProvider:
    """Create Seeking Alpha RSS Provider."""
    config = ProviderConfig(
        name="seeking_alpha",
        priority=7,
        rate_limit_per_min=10,
        rate_limit_per_day=300,
        timeout_seconds=30,
        source_type=NewsSource.SEEKING_ALPHA
    )
    return RSSProvider(
        config=config,
        feed_url="https://seekingalpha.com/feed.xml"
    )


def create_benzinga_provider() -> RSSProvider:
    """Create Benzinga RSS Provider."""
    config = ProviderConfig(
        name="benzinga",
        priority=7,
        rate_limit_per_min=15,
        rate_limit_per_day=500,
        timeout_seconds=30,
        source_type=NewsSource.BENZINGA
    )
    return RSSProvider(
        config=config,
        feed_url="https://www.benzinga.com/feed"
    )