"""
News Provider Base Module

Core abstractions for news provider infrastructure.
"""

import asyncio
import hashlib
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

import aiohttp

from data.news.schemas import (
    NewsArticle, NewsSource, NewsCategory, ArticleSentiment,
    SentimentLabel, CompanyMention, PersonMention, EventDetection
)

logger = logging.getLogger(__name__)


@dataclass
class RateLimiter:
    """Async rate limiter with per-minute and per-day limits."""
    calls_per_minute: int
    calls_per_day: int = 5000
    _calls: List[float] = field(default_factory=list)
    _daily_calls: int = 0
    _day_start: float = field(default_factory=time.time)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def acquire(self) -> None:
        """Wait until a call is allowed."""
        async with self._lock:
            now = time.time()

            # Reset daily counter
            if now - self._day_start > 86400:
                self._daily_calls = 0
                self._day_start = now

            # Check daily limit
            if self._daily_calls >= self.calls_per_day:
                sleep_time = 86400 - (now - self._day_start)
                if sleep_time > 0:
                    logger.warning(f"Daily rate limit reached, sleeping {sleep_time:.0f}s")
                    await asyncio.sleep(sleep_time)
                    self._daily_calls = 0
                    self._day_start = time.time()

            # Clean old minute calls
            self._calls = [t for t in self._calls if now - t < 60]

            # Check minute limit
            if len(self._calls) >= self.calls_per_minute:
                sleep_time = 60 - (now - self._calls[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    now = time.time()
                    self._calls = [t for t in self._calls if now - t < 60]

            self._calls.append(now)
            self._daily_calls += 1


@dataclass
class ProviderConfig:
    """Configuration for a news provider."""
    name: str
    priority: int  # Lower number = higher priority
    rate_limit_per_min: int
    rate_limit_per_day: int = 5000
    timeout_seconds: int = 30
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    enabled: bool = True
    api_key: Optional[str] = None
    source_type: NewsSource = NewsSource.GOOGLE_NEWS
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderHealth:
    """Health status of a news provider."""
    name: str
    healthy: bool = True
    last_check: datetime = field(default_factory=datetime.utcnow)
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    last_error: Optional[str] = None

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    def record_success(self, latency_ms: float) -> None:
        self.total_requests += 1
        self.successful_requests += 1
        self.consecutive_failures = 0
        self.last_success = datetime.utcnow()
        # Update rolling average
        self.avg_latency_ms = (
            (self.avg_latency_ms * (self.successful_requests - 1) + latency_ms)
            / self.successful_requests
        )

    def record_failure(self, error: str) -> None:
        self.total_requests += 1
        self.failed_requests += 1
        self.consecutive_failures += 1
        self.last_failure = datetime.utcnow()
        self.last_error = error
        if self.consecutive_failures >= 3:
            self.healthy = False


class NewsProviderError(Exception):
    """Base exception for news provider errors."""
    pass


class NewsProviderTimeoutError(NewsProviderError):
    """Timeout error for news provider."""
    pass


class NewsProviderRateLimitError(NewsProviderError):
    """Rate limit exceeded for news provider."""
    pass


class NewsProviderAuthError(NewsProviderError):
    """Authentication error for news provider."""
    pass


class NewsProviderBase(ABC):
    """Abstract base class for news providers."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.rate_limiter = RateLimiter(config.rate_limit_per_min, config.rate_limit_per_day)
        self.timeout = aiohttp.ClientTimeout(total=config.timeout_seconds)
        self.api_key = config.api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self.health = ProviderHealth(config.name)

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self):
        """Close the session."""
        if self.session and not self.session.closed:
            await self.session.close()

    @abstractmethod
    async def fetch_news(
        self,
        company: str,
        ticker: Optional[str] = None,
        lookback_hours: int = 24,
        max_articles: int = 50
    ) -> List[NewsArticle]:
        """Fetch news articles for a company."""
        pass

    def _create_article_hash(self, title: str, url: str) -> str:
        """Create unique hash for deduplication."""
        content = f"{title.lower().strip()}{url}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _extract_tickers(self, text: str) -> List[str]:
        """Extract stock tickers from text."""
        patterns = [
            r'\$([A-Z]{1,5})\b',  # $AAPL
            r'\b([A-Z]{1,5}):\w{2}\b',  # AAPL:US
            r'\(([A-Z]{1,5})\)',  # (AAPL)
            r'\bNYSE:\s*([A-Z]{1,5})\b',
            r'\bNASDAQ:\s*([A-Z]{1,5})\b',
        ]

        tickers = set()
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            tickers.update(m.upper() for m in matches)

        # Filter out common false positives
        false_positives = {
            'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM', 'HIS', 'HOW', 'ITS', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WHO', 'BOY', 'DID', 'ITS', 'LET', 'PUT', 'SAY', 'SHE', 'TOO', 'USE'
        }
        return [t for t in tickers if t not in false_positives and len(t) >= 2]

    def _extract_companies(self, text: str, known_tickers: Dict[str, str]) -> List[CompanyMention]:
        """Extract company mentions from text."""
        companies = []
        text_lower = text.lower()

        for ticker, name in known_tickers.items():
            ticker_pattern = rf'\b{ticker}\b|\${ticker}\b|\({ticker}\)'
            ticker_matches = len(re.findall(ticker_pattern, text, re.IGNORECASE))

            name_escaped = re.escape(name)
            name_matches = len(re.findall(name_escaped, text, re.IGNORECASE))

            total_mentions = ticker_matches + name_matches
            if total_mentions > 0:
                companies.append(CompanyMention(
                    name=name,
                    ticker=ticker,
                    mention_count=total_mentions,
                    is_primary=total_mentions >= 3
                ))

        return companies

    def _detect_events(self, title: str, summary: str) -> List[EventDetection]:
        """Detect financial events in article."""
        events = []
        text = f"{title} {summary}".lower()

        event_patterns = {
            NewsCategory.EARNINGS: [
                r'earnings', r'quarterly results', r'q[1-4] results',
                r'beat estimates', r'missed estimates', r'guidance'
            ],
            NewsCategory.GUIDANCE: [
                r'guidance', r'outlook', r'forecast', r'raised guidance',
                r'lowered guidance', r'updated guidance'
            ],
            NewsCategory.MERGERS_ACQUISITIONS: [
                r'merger', r'acquisition', r'acquire', r'acquires',
                r'takeover', r'buyout', r'deal worth', r'agreed to buy'
            ],
            NewsCategory.PRODUCT_LAUNCH: [
                r'launch', r'unveil', r'announces new', r'introduces',
                r'new product', r'new service', r'rollout'
            ],
            NewsCategory.LAYOFFS: [
                r'layoff', r'layoffs', r'job cuts', r'restructuring',
                r'reducing workforce', r'headcount reduction'
            ],
            NewsCategory.PARTNERSHIP: [
                r'partnership', r'partner with', r'collaboration',
                r'strategic alliance', r'joint venture'
            ],
            NewsCategory.LAWSUIT: [
                r'lawsuit', r'sued', r'litigation', r'legal action',
                r'class action', r'sec investigation'
            ],
            NewsCategory.SEC_FILING: [
                r'8-k', r'10-k', r'10-q', r'form 4', r'schedule 13',
                r'sec filing', r'filed with sec'
            ],
            NewsCategory.MANAGEMENT_CHANGE: [
                r'ceo', r'cfo', r'chief executive', r'chief financial',
                r'resigns', r'appointed', r'named.*president', r'stepping down'
            ],
            NewsCategory.DIVIDEND: [
                r'dividend', r'increases dividend', r'dividend yield',
                r'ex-dividend', r'declares dividend'
            ],
            NewsCategory.STOCK_SPLIT: [
                r'stock split', r'split ratio', r'forward split', r'reverse split'
            ],
            NewsCategory.ANALYST_RATING: [
                r'upgrade', r'downgrade', r'price target', r'rating',
                r'buy rating', r'sell rating', r'hold rating',
                r'outperform', r'underperform', r'overweight', r'underweight'
            ],
            NewsCategory.SHARE_BUYBACK: [
                r'buyback', r'share repurchase', r'repurchase program',
                r'authorized.*buyback'
            ],
        }

        for category, patterns in event_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    confidence = 0.8 if category in [NewsCategory.EARNINGS, NewsCategory.MERGERS_ACQUISITIONS] else 0.6
                    events.append(EventDetection(
                        event_type=category,
                        confidence=confidence,
                        details={"matched_pattern": pattern}
                    ))
                    break  # One event per category max

        return events

    def _calculate_importance(self, article: NewsArticle) -> float:
        """Calculate importance score for article."""
        score = 0.0

        # Base score from events
        for event in article.events:
            if event.event_type in [NewsCategory.EARNINGS, NewsCategory.MERGERS_ACQUISITIONS]:
                score += 0.3
            elif event.event_type in [NewsCategory.GUIDANCE, NewsCategory.LAWSUIT, NewsCategory.SEC_FILING]:
                score += 0.2
            else:
                score += 0.1

        # Boost for primary company mentions
        primary_companies = [c for c in article.companies if c.is_primary]
        score += len(primary_companies) * 0.1

        # Sentiment strength boost
        if article.sentiment:
            score += abs(article.sentiment.score) * 0.1

        # Source credibility
        credible_sources = {NewsSource.REUTERS, NewsSource.BLOOMBERG, NewsSource.FINANCIAL_TIMES, NewsSource.WALL_STREET_JOURNAL}
        if article.source in credible_sources:
            score += 0.15

        return min(score, 1.0)

    def _calculate_market_impact(self, article: NewsArticle) -> float:
        """Calculate potential market impact score."""
        score = 0.0

        high_impact = {
            NewsCategory.EARNINGS, NewsCategory.MERGERS_ACQUISITIONS,
            NewsCategory.GUIDANCE, NewsCategory.LAWSUIT,
            NewsCategory.MANAGEMENT_CHANGE, NewsCategory.BANKRUPTCY
        }

        for event in article.events:
            if event.event_type in high_impact:
                score += 0.25 * event.confidence
            else:
                score += 0.1 * event.confidence

        # Sentiment extremity
        if article.sentiment:
            score += abs(article.sentiment.score) * 0.2

        return min(score, 1.0)

    def _calculate_freshness(self, published_at: datetime) -> float:
        """Calculate freshness score (1.0 = just published)."""
        age_hours = (datetime.utcnow() - published_at).total_seconds() / 3600
        if age_hours <= 1:
            return 1.0
        elif age_hours <= 6:
            return 0.8
        elif age_hours <= 24:
            return 0.6
        elif age_hours <= 72:
            return 0.4
        else:
            return 0.2

    def _calculate_relevance(self, article: NewsArticle, company: str, ticker: Optional[str]) -> float:
        """Calculate relevance to target company."""
        score = 0.0
        text = f"{article.title} {article.summary}".lower()
        company_lower = company.lower()
        ticker_lower = ticker.lower() if ticker else ""

        # Direct mentions
        if company_lower in text:
            score += 0.5
        if ticker_lower and ticker_lower in text:
            score += 0.4
        if ticker_lower and f"${ticker_lower}" in text:
            score += 0.3

        # Company in extracted entities
        for c in article.companies:
            if c.ticker and c.ticker.lower() == ticker_lower:
                score += 0.3
            if c.name.lower() == company_lower:
                score += 0.3

        return min(score, 1.0)

    async def _analyze_sentiment(self, title: str, summary: str, content: Optional[str] = None) -> ArticleSentiment:
        """Analyze sentiment using keyword-based approach (can be replaced with LLM)."""
        text = f"{title} {summary}".lower()
        if content:
            text += f" {content[:1000]}"

        # Financial sentiment keywords
        positive_keywords = {
            'beat', 'beats', 'exceeds', 'exceeded', 'strong', 'growth', 'surge', 'surges',
            'rally', 'rallies', 'bullish', 'upgrade', 'upgrades', 'outperform', 'buy',
            'positive', 'record', 'high', 'profit', 'profits', 'revenue growth',
            'expansion', 'expanding', 'partnership', 'deal', 'acquisition', 'merger',
            'dividend increase', 'buyback', 'share repurchase', 'guidance raised',
            'outlook raised', 'optimistic', 'confident', 'milestone', 'breakthrough'
        }

        negative_keywords = {
            'miss', 'misses', 'missed', 'weak', 'decline', 'declines', 'fall', 'falls',
            'drop', 'drops', 'bearish', 'downgrade', 'downgrades', 'underperform', 'sell',
            'negative', 'loss', 'losses', 'revenue decline', 'contraction', 'contracting',
            'layoff', 'layoffs', 'restructuring', 'lawsuit', 'investigation', 'probe',
            'guidance lowered', 'outlook lowered', 'pessimistic', 'concern', 'concerns',
            'risk', 'risks', 'challenge', 'challenges', 'headwind', 'headwinds',
            'bankruptcy', 'default', 'recall', 'delay', 'delays', 'caution'
        }

        words = set(re.findall(r'\b\w+\b', text))

        pos_count = len(words & positive_keywords)
        neg_count = len(words & negative_keywords)
        total = pos_count + neg_count

        if total == 0:
            return ArticleSentiment(
                label=SentimentLabel.NEUTRAL,
                score=0.0,
                confidence=0.3,
                positive_score=0.0,
                negative_score=0.0,
                neutral_score=1.0
            )

        score = (pos_count - neg_count) / total
        confidence = min(total / 10, 1.0) * 0.7 + 0.3

        if score > 0.1:
            label = SentimentLabel.POSITIVE
        elif score < -0.1:
            label = SentimentLabel.NEGATIVE
        else:
            label = SentimentLabel.NEUTRAL

        return ArticleSentiment(
            label=label,
            score=round(score, 3),
            confidence=round(confidence, 3),
            positive_score=round(pos_count / max(total, 1), 3),
            negative_score=round(neg_count / max(total, 1), 3),
            neutral_score=round(1 - (pos_count + neg_count) / max(total, 1), 3)
        )


# Provider registry
_PROVIDER_REGISTRY: Dict[str, type] = {}


def register_provider(name: str, provider_class: type) -> None:
    """Register a news provider class."""
    _PROVIDER_REGISTRY[name.lower()] = provider_class


def get_provider_class(name: str) -> Optional[type]:
    """Get provider class by name."""
    return _PROVIDER_REGISTRY.get(name.lower())


def list_providers() -> List[str]:
    """List all registered providers."""
    return list(_PROVIDER_REGISTRY.keys())