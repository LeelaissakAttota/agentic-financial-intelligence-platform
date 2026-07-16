"""
Alpha Vantage News & Sentiment Provider
"""

import aiohttp
from datetime import datetime, timedelta
from typing import List, Optional

from data.news.schemas import NewsArticle, NewsSource, NewsCategory, SentimentLabel
from data.news.providers.base import NewsProviderBase, ProviderConfig, NewsProviderError


class AlphaVantageNewsProvider(NewsProviderBase):
    """Alpha Vantage News & Sentiment API Provider."""

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, config: Optional[ProviderConfig] = None):
        if config is None:
            config = ProviderConfig(
                name="alpha_vantage",
                priority=3,
                rate_limit_per_min=5,
                rate_limit_per_day=500,
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
        """Fetch news from Alpha Vantage."""
        if not self.config.api_key:
            logger.warning("Alpha Vantage API key not configured")
            return []

        await self.rate_limiter.acquire()
        await self._ensure_session()

        try:
            symbol = ticker or company

            params = {
                'function': 'NEWS_SENTIMENT',
                'tickers': symbol,
                'time_from': (datetime.utcnow() - timedelta(hours=lookback_hours)).strftime('%Y%m%dT%H%M'),
                'limit': max_articles,
                'apikey': self.config.api_key
            }

            async with self.session.get(self.BASE_URL, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"Alpha Vantage API error: {resp.status}")
                    return []
                data = await resp.json()

            articles = []
            feed = data.get('feed', [])

            for item in feed[:max_articles]:
                try:
                    pub_time = datetime.strptime(item.get('time_published', ''), '%Y%m%dT%H%M%S')

                    title = item.get('title', '')
                    summary = item.get('summary', '')
                    url = item.get('url', '')

                    if not title or not url:
                        continue

                    article = NewsArticle(
                        title=title,
                        summary=summary,
                        content=None,
                        url=url,
                        source=NewsSource.ALPHA_VANTAGE,
                        source_name="Alpha Vantage",
                        published_at=pub_time,
                        author=item.get('source'),
                        content_hash=self._create_article_hash(title, url)
                    )

                    # Alpha Vantage provides sentiment
                    sentiment_data = item.get('overall_sentiment_score', 0)
                    sentiment_label = item.get('overall_sentiment_label', 'Neutral')

                    label_map = {
                        'Bearish': SentimentLabel.NEGATIVE,
                        'Somewhat-Bearish': SentimentLabel.NEGATIVE,
                        'Neutral': SentimentLabel.NEUTRAL,
                        'Somewhat-Bullish': SentimentLabel.POSITIVE,
                        'Bullish': SentimentLabel.POSITIVE,
                    }

                    article.sentiment = ArticleSentiment(
                        label=label_map.get(sentiment_label, SentimentLabel.NEUTRAL),
                        score=sentiment_data,
                        confidence=0.8,
                        positive_score=max(0, sentiment_data),
                        negative_score=max(0, -sentiment_data),
                        neutral_score=1 - abs(sentiment_data)
                    )

                    # Topics from Alpha Vantage
                    topics = item.get('topics', [])
                    for topic in topics:
                        topic_name = topic.get('topic', '').lower()
                        if 'earnings' in topic_name:
                            article.events.append(EventDetection(NewsCategory.EARNINGS, 0.9))
                        elif 'merger' in topic_name or 'acquisition' in topic_name:
                            article.events.append(EventDetection(NewsCategory.MERGERS_ACQUISITIONS, 0.9))

                    article.tickers = self._extract_tickers(f"{title} {summary}")
                    article.importance_score = self._calculate_importance(article)
                    article.market_impact_score = self._calculate_market_impact(article)
                    article.freshness_score = self._calculate_freshness(pub_time)
                    article.relevance_score = self._calculate_relevance(article, company, ticker)

                    articles.append(article)

                except Exception as e:
                    logger.warning(f"Error parsing Alpha Vantage article: {e}")
                    continue

            logger.info(f"Fetched {len(articles)} articles from Alpha Vantage for {company}")
            return articles

        except Exception as e:
            logger.error(f"Alpha Vantage news fetch failed for {company}: {e}")
            raise NewsProviderError(f"Alpha Vantage fetch failed: {e}")