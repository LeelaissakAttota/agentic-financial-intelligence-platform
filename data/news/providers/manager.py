"""
Provider Manager for News Intelligence

Handles provider orchestration, fallback chains, health monitoring,
and unified article fetching with deduplication and ranking.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from data.news.schemas import (
    NewsArticle, NewsSource, NewsCategory, SentimentLabel,
    CompanyMention, EventDetection, NewsSummary
)
from data.news.providers.base import (
    NewsProviderBase, ProviderConfig, ProviderHealth,
    NewsProviderError
)
from data.news.providers.yahoo import YahooFinanceNewsProvider
from data.news.providers.finnhub import FinnhubNewsProvider
from data.news.providers.alpha_vantage import AlphaVantageNewsProvider
from data.news.providers.newsapi import NewsAPIProvider
from data.news.providers.rss import (
    RSSProvider, create_marketwatch_provider, create_cnbc_provider,
    create_cnbc_top_provider, create_reuters_business_provider,
    create_bloomberg_provider, create_marketwatch_top_provider,
    create_financial_times_provider, create_wall_street_journal_provider,
    create_seeking_alpha_provider, create_benzinga_provider,
    create_google_news_provider
)

logger = logging.getLogger(__name__)


class CompositeNewsProvider:
    """
    Composite news provider with automatic fallback chain,
    health monitoring, deduplication, and ranking.
    """

    def __init__(
        self,
        finnhub_key: Optional[str] = None,
        alpha_vantage_key: Optional[str] = None,
        newsapi_key: Optional[str] = None
    ):
        self.providers: List[NewsProviderBase] = []
        self._health_check_interval = 300  # 5 minutes
        self._health_check_task: Optional[asyncio.Task] = None

        # Initialize providers in priority order
        self._initialize_providers(finnhub_key, alpha_vantage_key, newsapi_key)

    def _initialize_providers(
        self,
        finnhub_key: Optional[str],
        alpha_vantage_key: Optional[str],
        newsapi_key: Optional[str]
    ):
        """Initialize all providers in priority order."""
        # Primary providers (best first)
        self.providers.append(YahooFinanceNewsProvider(
            ProviderConfig(name="yahoo_finance", priority=1, rate_limit_per_min=30)
        ))

        if finnhub_key:
            self.providers.append(FinnhubNewsProvider(
                ProviderConfig(
                    name="finnhub",
                    priority=2,
                    rate_limit_per_min=60,
                    api_key=finnhub_key
                )
            ))

        if alpha_vantage_key:
            self.providers.append(AlphaVantageNewsProvider(
                ProviderConfig(
                    name="alpha_vantage",
                    priority=3,
                    rate_limit_per_min=5,
                    api_key=alpha_vantage_key
                )
            ))

        if newsapi_key:
            self.providers.append(NewsAPIProvider(
                ProviderConfig(
                    name="newsapi",
                    priority=4,
                    rate_limit_per_min=30,
                    api_key=newsapi_key
                )
            ))

        # RSS fallback providers
        self.providers.append(create_google_news_provider())

        # Financial RSS feeds
        self.providers.append(create_marketwatch_provider())
        self.providers.append(create_cnbc_provider())
        self.providers.append(create_cnbc_top_provider())
        self.providers.append(create_reuters_business_provider())
        self.providers.append(create_bloomberg_provider())
        self.providers.append(create_marketwatch_top_provider())
        self.providers.append(create_financial_times_provider())
        self.providers.append(create_wall_street_journal_provider())
        self.providers.append(create_seeking_alpha_provider())
        self.providers.append(create_benzinga_provider())

    async def fetch_news(
        self,
        company: str,
        ticker: Optional[str] = None,
        lookback_hours: int = 24,
        max_articles: int = 50,
        min_providers: int = 2
    ) -> List[NewsArticle]:
        """
        Fetch news from multiple providers with fallback.

        Args:
            company: Company name
            ticker: Optional stock ticker
            lookback_hours: How far back to fetch news
            max_articles: Maximum articles to return
            min_providers: Minimum successful providers required

        Returns:
            Merged, deduplicated, and ranked articles
        """
        all_articles = []
        successful_providers = 0

        # Fetch from all providers concurrently
        tasks = [
            self._fetch_with_error_handling(provider, company, ticker, lookback_hours, max_articles)
            for provider in self.providers
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for provider, result in zip(self.providers, results):
            if isinstance(result, Exception):
                logger.warning(f"Provider {provider.config.name} failed: {result}")
                continue
            elif result:
                all_articles.extend(result)
                successful_providers += 1
                logger.info(f"Provider {provider.config.name} returned {len(result)} articles")

        # Check minimum providers
        if successful_providers < min_providers:
            logger.warning(f"Only {successful_providers}/{len(self.providers)} providers succeeded")

        # Deduplicate
        deduplicated = self._deduplicate_articles(all_articles)

        # Rank by relevance and importance
        ranked = self._rank_articles(deduplicated, company, ticker)

        logger.info(
            f"Fetched {len(ranked)} unique articles for {company} "
            f"from {successful_providers}/{len(self.providers)} providers"
        )

        return ranked[:max_articles]

    async def _fetch_with_error_handling(
        self,
        provider: NewsProviderBase,
        company: str,
        ticker: Optional[str],
        lookback_hours: int,
        max_articles: int
    ) -> List[NewsArticle]:
        """Fetch with error handling and health tracking."""
        start_time = datetime.utcnow()
        try:
            result = await provider.fetch_news(company, ticker, lookback_hours, max_articles)
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            provider.health.record_success(latency_ms)
            return result
        except Exception as e:
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            provider.health.record_failure(str(e))
            logger.warning(f"Provider {provider.config.name} failed: {e}")
            raise

    def _deduplicate_articles(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Remove duplicate articles using content hash and title similarity."""
        seen_hashes: Set[str] = set()
        seen_titles: Set[str] = set()
        unique = []

        for article in articles:
            # Check hash
            if article.content_hash and article.content_hash in seen_hashes:
                continue

            # Check title similarity (simple approach)
            title_key = article.title.lower().strip()
            title_words = set(title_key.split())

            is_duplicate = False
            for seen_title in seen_titles:
                seen_words = set(seen_title.split())
                if title_words and seen_words:
                    overlap = len(title_words & seen_words) / len(title_words | seen_words)
                    if overlap > 0.7:  # 70% word overlap
                        is_duplicate = True
                        break

            if is_duplicate:
                continue

            if article.content_hash:
                seen_hashes.add(article.content_hash)
            seen_titles.add(title_key)
            unique.append(article)

        return unique

    def _rank_articles(
        self,
        articles: List[NewsArticle],
        company: str,
        ticker: Optional[str]
    ) -> List[NewsArticle]:
        """Rank articles by composite score."""
        # Use first provider's relevance calculator as reference
        reference_provider = self.providers[0] if self.providers else None

        for article in articles:
            relevance = reference_provider._calculate_relevance(article, company, ticker) if reference_provider else 0.5

            composite = (
                relevance * 0.35 +
                article.importance_score * 0.25 +
                article.freshness_score * 0.20 +
                article.market_impact_score * 0.20
            )

            # Boost for credible sources
            credible = {
                NewsSource.REUTERS, NewsSource.BLOOMBERG,
                NewsSource.FINANCIAL_TIMES, NewsSource.WALL_STREET_JOURNAL
            }
            if article.source in credible:
                composite *= 1.15

            article.metadata = article.metadata or {}
            article.metadata['composite_score'] = round(composite, 3)

        return sorted(articles, key=lambda a: a.metadata.get('composite_score', 0), reverse=True)

    async def get_provider_health(self) -> List[ProviderHealth]:
        """Get health status of all providers."""
        return [p.health for p in self.providers]

    async def start_health_monitoring(self, interval: int = 300):
        """Start background health monitoring."""
        if self._health_check_task is not None:
            return

        async def health_check_loop():
            while True:
                await asyncio.sleep(interval)
                await self._check_all_providers()

        self._health_check_task = asyncio.create_task(health_check_loop())

    async def stop_health_monitoring(self):
        """Stop background health monitoring."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

    async def _check_all_providers(self):
        """Check health of all providers."""
        for provider in self.providers:
            try:
                await provider._ensure_session()
                start = datetime.utcnow()
                async with provider.session.get("https://httpbin.org/get", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    latency = (datetime.utcnow() - start).total_seconds() * 1000
                    if resp.status == 200:
                        provider.health.record_success(latency)
                        provider.health.healthy = True
                    else:
                        provider.health.record_failure(f"HTTP {resp.status}")
            except Exception as e:
                provider.health.record_failure(str(e))

    async def close_all(self):
        """Close all provider sessions."""
        for provider in self.providers:
            await provider.close()

    async def get_provider_stats(self) -> Dict[str, Any]:
        """Get statistics for all providers."""
        stats = {}
        for provider in self.providers:
            h = provider.health
            stats[provider.config.name] = {
                "healthy": h.healthy,
                "success_rate": h.success_rate,
                "total_requests": h.total_requests,
                "successful_requests": h.successful_requests,
                "failed_requests": h.failed_requests,
                "avg_latency_ms": round(h.avg_latency_ms, 2),
                "consecutive_failures": h.consecutive_failures,
                "last_check": h.last_check.isoformat() if h.last_check else None,
                "last_error": h.last_error
            }
        return stats


# Global provider instance
_composite_provider: Optional[CompositeNewsProvider] = None


def get_news_provider(
    finnhub_key: Optional[str] = None,
    alpha_vantage_key: Optional[str] = None,
    newsapi_key: Optional[str] = None
) -> CompositeNewsProvider:
    """Get or create global composite news provider."""
    global _composite_provider
    if _composite_provider is None:
        _composite_provider = CompositeNewsProvider(
            finnhub_key=finnhub_key,
            alpha_vantage_key=alpha_vantage_key,
            newsapi_key=newsapi_key
        )
    return _composite_provider


async def close_news_provider():
    """Close global news provider."""
    global _composite_provider
    if _composite_provider:
        await _composite_provider.close_all()
        _composite_provider = None