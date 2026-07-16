"""
NewsAPI.org Provider
"""

import aiohttp
from datetime import datetime, timedelta
from typing import List, Optional

from data.news.schemas import NewsArticle, NewsSource
from data.news.providers.base import NewsProviderBase, ProviderConfig, NewsProviderError


class NewsAPIProvider(NewsProviderBase):
    """NewsAPI.org Provider."""

    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self, config: Optional[ProviderConfig] = None):
        if config is None:
            config = ProviderConfig(
                name="newsapi",
                priority=4,
                rate_limit_per_min=30,
                rate_limit_per_day=1000,
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
        """Fetch news from NewsAPI.org."""
        if not self.config.api_key:
            logger.warning("NewsAPI key not configured")
            return []

        await self.rate_limiter.acquire()
        await self._ensure_session()

        try:
            # Build query
            query_parts = [company]
            if ticker:
                query_parts.append(ticker)
            query = " OR ".join(query_parts)

            params = {
                'q': query,
                'from': (datetime.utcnow() - timedelta(hours=lookback_hours)).strftime('%Y-%m-%d'),
                'to': datetime.utcnow().strftime('%Y-%m-%d'),
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': max_articles,
                'apiKey': self.config.api_key
            }

            async with self.session.get(self.BASE_URL, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"NewsAPI error: {resp.status}")
                    return []
                data = await resp.json()

            articles = []
            for item in data.get('articles', [])[:max_articles]:
                try:
                    pub_time = datetime.fromisoformat(
                        item.get('publishedAt', '').replace('Z', '+00:00')
                    )

                    title = item.get('title', '')
                    summary = item.get('description', '') or item.get('content', '')
                    url = item.get('url', '')

                    if not title or not url or title == '[Removed]':
                        continue

                    article = NewsArticle(
                        title=title,
                        summary=summary[:500] if summary else '',
                        content=item.get('content'),
                        url=url,
                        source=NewsSource.NEWSAPI,
                        source_name=item.get('source', {}).get('name', 'NewsAPI'),
                        published_at=pub_time,
                        author=item.get('author'),
                        content_hash=self._create_article_hash(title, url)
                    )

                    article.sentiment = await self._analyze_sentiment(title, summary or '')
                    article.events = self._detect_events(title, summary or '')
                    article.tickers = self._extract_tickers(f"{title} {summary or ''}")
                    article.importance_score = self._calculate_importance(article)
                    article.market_impact_score = self._calculate_market_impact(article)
                    article.freshness_score = self._calculate_freshness(pub_time)
                    article.relevance_score = self._calculate_relevance(article, company, ticker)

                    articles.append(article)

                except Exception as e:
                    logger.warning(f"Error parsing NewsAPI article: {e}")
                    continue

            logger.info(f"Fetched {len(articles)} articles from NewsAPI for {company}")
            return articles

        except Exception as e:
            logger.error(f"NewsAPI fetch failed for {company}: {e}")
            raise NewsProviderError(f"NewsAPI fetch failed: {e}")