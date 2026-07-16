"""
Finnhub News Provider
"""

import aiohttp
from datetime import datetime, timedelta
from typing import List, Optional

from data.news.schemas import NewsArticle, NewsSource, NewsCategory
from data.news.providers.base import NewsProviderBase, ProviderConfig, NewsProviderError


class FinnhubNewsProvider(NewsProviderBase):
    """Finnhub News API Provider."""

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, config: Optional[ProviderConfig] = None):
        if config is None:
            config = ProviderConfig(
                name="finnhub",
                priority=2,
                rate_limit_per_min=60,
                rate_limit_per_day=5000,
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
        """Fetch news from Finnhub."""
        if not self.config.api_key:
            logger.warning("Finnhub API key not configured")
            return []

        await self.rate_limiter.acquire()
        await self._ensure_session()

        try:
            symbol = ticker or company

            # Get company news
            from_ts = int((datetime.utcnow() - timedelta(hours=lookback_hours)).timestamp())
            to_ts = int(datetime.utcnow().timestamp())

            params = {
                'symbol': symbol,
                'from': datetime.fromtimestamp(from_ts).strftime('%Y-%m-%d'),
                'to': datetime.fromtimestamp(to_ts).strftime('%Y-%m-%d'),
                'token': self.config.api_key
            }

            async with self.session.get(
                f"{self.BASE_URL}/company-news",
                params=params
            ) as resp:
                if resp.status != 200:
                    logger.error(f"Finnhub API error: {resp.status}")
                    return []
                data = await resp.json()

            articles = []
            cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)

            for item in data[:max_articles]:
                try:
                    pub_time = datetime.fromtimestamp(item.get('datetime', 0))
                    if pub_time < cutoff:
                        continue

                    title = item.get('headline', '')
                    summary = item.get('summary', '')
                    url = item.get('url', '')

                    if not title or not url:
                        continue

                    article = NewsArticle(
                        title=title,
                        summary=summary,
                        content=None,
                        url=url,
                        source=NewsSource.FINNHUB,
                        source_name="Finnhub",
                        published_at=pub_time,
                        author=item.get('source'),
                        content_hash=self._create_article_hash(title, url)
                    )

                    # Categorize based on Finnhub category
                    category_map = {
                        'earnings': NewsCategory.EARNINGS,
                        'merger': NewsCategory.MERGERS_ACQUISITIONS,
                        'product': NewsCategory.PRODUCT_LAUNCH,
                        'analyst': NewsCategory.ANALYST_RATING,
                        'dividend': NewsCategory.DIVIDEND,
                        'ipo': NewsCategory.IPO,
                    }
                    finnhub_cat = item.get('category', '').lower()
                    article.category = category_map.get(finnhub_cat)

                    article.sentiment = await self._analyze_sentiment(title, summary)
                    article.events = self._detect_events(title, summary)
                    article.tickers = self._extract_tickers(f"{title} {summary}")
                    article.importance_score = self._calculate_importance(article)
                    article.market_impact_score = self._calculate_market_impact(article)
                    article.freshness_score = self._calculate_freshness(pub_time)
                    article.relevance_score = self._calculate_relevance(article, company, ticker)

                    articles.append(article)

                except Exception as e:
                    logger.warning(f"Error parsing Finnhub article: {e}")
                    continue

            logger.info(f"Fetched {len(articles)} articles from Finnhub for {company}")
            return articles

        except Exception as e:
            logger.error(f"Finnhub news fetch failed for {company}: {e}")
            raise NewsProviderError(f"Finnhub fetch failed: {e}")