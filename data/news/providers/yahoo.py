"""
Yahoo Finance News Provider
"""

import asyncio
import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Optional

from data.news.schemas import NewsArticle, NewsSource, ArticleSentiment, SentimentLabel
from data.news.providers.base import NewsProviderBase, ProviderConfig, NewsProviderError


class YahooFinanceNewsProvider(NewsProviderBase):
    """Yahoo Finance News Provider using yfinance library."""

    def __init__(self, config: Optional[ProviderConfig] = None):
        if config is None:
            config = ProviderConfig(
                name="yahoo_finance",
                priority=1,
                rate_limit_per_min=30,
                timeout_seconds=30
            )
        super().__init__(config)

    async def fetch_news(
        self,
        company: str,
        ticker: Optional[str] = None,
        lookback_hours: int = 24,
        max_articles: int = 50
    ) -> List[NewsArticle]:
        """Fetch news from Yahoo Finance."""
        symbol = ticker or company

        try:
            await self.rate_limiter.acquire()
            await self._ensure_session()

            # Use yfinance to get news
            ticker_obj = yf.Ticker(symbol)
            news = ticker_obj.news

            if not news:
                logger.info(f"No news from Yahoo Finance for {company}")
                return []

            articles = []
            cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)

            for item in news[:max_articles]:
                try:
                    # Parse publish time
                    pub_time = datetime.fromtimestamp(item.get('providerPublishTime', 0))
                    if pub_time < cutoff:
                        continue

                    title = item.get('title', '')
                    summary = item.get('summary', '')
                    url = item.get('link', '')

                    if not title or not url:
                        continue

                    # Create article
                    article = NewsArticle(
                        title=title,
                        summary=summary,
                        content=None,
                        url=url,
                        source=NewsSource.YAHOO_FINANCE,
                        source_name="Yahoo Finance",
                        published_at=pub_time,
                        author=item.get('publisher'),
                        content_hash=self._create_article_hash(title, url)
                    )

                    # Analyze
                    article.sentiment = await self._analyze_sentiment(title, summary)
                    article.events = self._detect_events(title, summary)
                    article.tickers = self._extract_tickers(f"{title} {summary}")
                    article.importance_score = self._calculate_importance(article)
                    article.market_impact_score = self._calculate_market_impact(article)
                    article.freshness_score = self._calculate_freshness(pub_time)
                    article.relevance_score = self._calculate_relevance(article, company, ticker)

                    articles.append(article)

                except Exception as e:
                    logger.warning(f"Error parsing Yahoo Finance article: {e}")
                    continue

            logger.info(f"Fetched {len(articles)} articles from Yahoo Finance for {company}")
            return articles

        except Exception as e:
            logger.error(f"Yahoo Finance news fetch failed for {company}: {e}")
            raise NewsProviderError(f"Yahoo Finance fetch failed: {e}")