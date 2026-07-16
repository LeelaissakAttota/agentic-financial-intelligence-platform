"""
News Providers - Multi-source Financial News Intelligence

Implements providers for:
1. Yahoo Finance News
2. Finnhub News API
3. Alpha Vantage News API
4. NewsAPI.org
5. RSS Feeds (MarketWatch, CNBC, etc.)
6. Google News RSS

Features:
- Automatic fallback chain
- Rate limiting per provider
- Deduplication across sources
- Sentiment analysis
- Company/ticker extraction
- Event detection
"""

import asyncio
import hashlib
import logging
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from urllib.parse import urlparse, quote_plus

import aiohttp
import yfinance as yf
import feedparser
from bs4 import BeautifulSoup

from data.news.schemas import (
    NewsArticle, NewsSource, NewsCategory, ArticleSentiment, 
    SentimentLabel, CompanyMention, PersonMention, EventDetection,
    NewsAgentInput
)
from data.news.cache import get_news_cache

logger = logging.getLogger(__name__)


@dataclass
class RateLimiter:
    """Simple rate limiter for API calls."""
    calls_per_minute: int
    calls_per_day: int = 5000
    _calls: List[float] = None
    _daily_calls: int = 0
    _day_start: float = 0
    _lock: asyncio.Lock = None
    
    def __post_init__(self):
        self._calls = []
        self._lock = asyncio.Lock()
        self._day_start = time.time()
    
    async def acquire(self):
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


class NewsProviderBase(ABC):
    """Abstract base class for news providers."""
    
    def __init__(
        self, 
        name: str,
        rate_limit_per_min: int = 30,
        timeout: int = 30,
        api_key: Optional[str] = None
    ):
        self.name = name
        self.rate_limiter = RateLimiter(rate_limit_per_min)
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self._cache = get_news_cache()
    
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
        # Pattern for tickers: $AAPL, (AAPL), AAPL:US, etc.
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
            # Check for ticker mentions
            ticker_pattern = rf'\b{ticker}\b|\${ticker}\b|\({ticker}\)'
            ticker_matches = len(re.findall(ticker_pattern, text, re.IGNORECASE))
            
            # Check for company name mentions
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
        
        # High impact events
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
        confidence = min(total / 10, 1.0) * 0.7 + 0.3  # Base confidence
        
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


class YahooFinanceNewsProvider(NewsProviderBase):
    """Yahoo Finance News Provider using yfinance."""
    
    def __init__(self):
        super().__init__("yahoo_finance", rate_limit_per_min=30)
    
    async def fetch_news(
        self, 
        company: str, 
        ticker: Optional[str] = None,
        lookback_hours: int = 24,
        max_articles: int = 50
    ) -> List[NewsArticle]:
        """Fetch news from Yahoo Finance."""
        cache_key = f"yahoo:{company.lower()}:{lookback_hours}"
        cached = await self._cache.get_provider_data("yahoo_finance", company, lookback_hours)
        if cached:
            logger.info(f"Yahoo Finance cache hit for {company}")
            return cached[:max_articles]
        
        await self.rate_limiter.acquire()
        
        try:
            # Use yfinance to get news
            symbol = ticker or company
            ticker_obj = yf.Ticker(symbol)
            
            # Get news - yfinance doesn't have direct news API, use workaround
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
            
            # Cache results
            await self._cache.set_provider_data("yahoo_finance", company, lookback_hours, articles)
            
            logger.info(f"Fetched {len(articles)} articles from Yahoo Finance for {company}")
            return articles
            
        except Exception as e:
            logger.error(f"Yahoo Finance news fetch failed for {company}: {e}")
            return []


class FinnhubNewsProvider(NewsProviderBase):
    """Finnhub News API Provider."""
    
    BASE_URL = "https://finnhub.io/api/v1"
    
    def __init__(self, api_key: str):
        super().__init__("finnhub", rate_limit_per_min=60, api_key=api_key)
    
    async def fetch_news(
        self, 
        company: str, 
        ticker: Optional[str] = None,
        lookback_hours: int = 24,
        max_articles: int = 50
    ) -> List[NewsArticle]:
        """Fetch news from Finnhub."""
        if not self.api_key:
            logger.warning("Finnhub API key not configured")
            return []
        
        cache_key = f"finnhub:{company.lower()}:{lookback_hours}"
        cached = await self._cache.get_provider_data("finnhub", company, lookback_hours)
        if cached:
            logger.info(f"Finnhub cache hit for {company}")
            return cached[:max_articles]
        
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
                'token': self.api_key
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
            
            await self._cache.set_provider_data("finnhub", company, lookback_hours, articles)
            logger.info(f"Fetched {len(articles)} articles from Finnhub for {company}")
            return articles
            
        except Exception as e:
            logger.error(f"Finnhub news fetch failed for {company}: {e}")
            return []


class AlphaVantageNewsProvider(NewsProviderBase):
    """Alpha Vantage News & Sentiment API Provider."""
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self, api_key: str):
        super().__init__("alpha_vantage", rate_limit_per_min=5, api_key=api_key)
    
    async def fetch_news(
        self, 
        company: str, 
        ticker: Optional[str] = None,
        lookback_hours: int = 24,
        max_articles: int = 50
    ) -> List[NewsArticle]:
        """Fetch news from Alpha Vantage."""
        if not self.api_key:
            logger.warning("Alpha Vantage API key not configured")
            return []
        
        cache_key = f"av:{company.lower()}:{lookback_hours}"
        cached = await self._cache.get_provider_data("alpha_vantage", company, lookback_hours)
        if cached:
            logger.info(f"Alpha Vantage cache hit for {company}")
            return cached[:max_articles]
        
        await self.rate_limiter.acquire()
        await self._ensure_session()
        
        try:
            symbol = ticker or company
            
            params = {
                'function': 'NEWS_SENTIMENT',
                'tickers': symbol,
                'time_from': (datetime.utcnow() - timedelta(hours=lookback_hours)).strftime('%Y%m%dT%H%M'),
                'limit': max_articles,
                'apikey': self.api_key
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
            
            await self._cache.set_provider_data("alpha_vantage", company, lookback_hours, articles)
            logger.info(f"Fetched {len(articles)} articles from Alpha Vantage for {company}")
            return articles
            
        except Exception as e:
            logger.error(f"Alpha Vantage news fetch failed for {company}: {e}")
            return []


class NewsAPIProvider(NewsProviderBase):
    """NewsAPI.org Provider."""
    
    BASE_URL = "https://newsapi.org/v2/everything"
    
    def __init__(self, api_key: str):
        super().__init__("newsapi", rate_limit_per_min=30, api_key=api_key)
    
    async def fetch_news(
        self, 
        company: str, 
        ticker: Optional[str] = None,
        lookback_hours: int = 24,
        max_articles: int = 50
    ) -> List[NewsArticle]:
        """Fetch news from NewsAPI.org."""
        if not self.api_key:
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
                'apiKey': self.api_key
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
            return []


class RSSProvider(NewsProviderBase):
    """Generic RSS Feed Provider for financial news sources."""
    
    def __init__(
        self, 
        name: str, 
        feed_url: str,
        source_type: NewsSource,
        rate_limit_per_min: int = 10
    ):
        super().__init__(name, rate_limit_per_min)
        self.feed_url = feed_url
        self.source_type = source_type
    
    async def fetch_news(
        self, 
        company: str, 
        ticker: Optional[str] = None,
        lookback_hours: int = 24,
        max_articles: int = 50
    ) -> List[NewsArticle]:
        """Fetch news from RSS feed."""
        await self.rate_limiter.acquire()
        await self._ensure_session()
        
        try:
            async with self.session.get(self.feed_url) as resp:
                if resp.status != 200:
                    logger.error(f"RSS fetch error for {self.name}: {resp.status}")
                    return []
                content = await resp.text()
            
            feed = feedparser.parse(content)
            
            if feed.bozo:
                logger.warning(f"RSS feed parsing issue for {self.name}: {feed.bozo_exception}")
            
            articles = []
            cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
            company_lower = company.lower()
            ticker_lower = ticker.lower() if ticker else ""
            
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
                    text = f"{title} {summary}".lower()
                    if company_lower not in text and (not ticker_lower or ticker_lower not in text):
                        continue
                    
                    article = NewsArticle(
                        title=title,
                        summary=summary[:500],
                        content=None,
                        url=url,
                        source=self.source_type,
                        source_name=self.name,
                        published_at=pub_time,
                        author=entry.get('author'),
                        content_hash=self._create_article_hash(title, url)
                    )
                    
                    article.sentiment = await self._analyze_sentiment(title, summary)
                    article.events = self._detect_events(title, summary)
                    article.tickers = self._extract_tickers(text)
                    article.importance_score = self._calculate_importance(article)
                    article.market_impact_score = self._calculate_market_impact(article)
                    article.freshness_score = self._calculate_freshness(pub_time)
                    article.relevance_score = self._calculate_relevance(article, company, ticker)
                    
                    articles.append(article)
                    
                except Exception as e:
                    logger.warning(f"Error parsing RSS entry from {self.name}: {e}")
                    continue
            
            logger.info(f"Fetched {len(articles)} articles from {self.name} for {company}")
            return articles
            
        except Exception as e:
            logger.error(f"RSS fetch failed for {self.name}: {e}")
            return []


class GoogleNewsRSSProvider(RSSProvider):
    """Google News RSS Provider."""
    
    def __init__(self):
        # Google News RSS for finance
        super().__init__(
            "google_news",
            "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
            NewsSource.GOOGLE_NEWS,
            rate_limit_per_min=20
        )
    
    async def fetch_news(
        self, 
        company: str, 
        ticker: Optional[str] = None,
        lookback_hours: int = 24,
        max_articles: int = 50
    ) -> List[NewsArticle]:
        """Fetch company-specific news from Google News RSS."""
        await self.rate_limiter.acquire()
        await self._ensure_session()
        
        try:
            # Build company-specific Google News RSS URL
            query = quote_plus(f"{company} stock" + (f" {ticker}" if ticker else ""))
            url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
            
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return []
                content = await resp.text()
            
            feed = feedparser.parse(content)
            
            articles = []
            cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
            
            for entry in feed.entries[:max_articles]:
                try:
                    pub_time = None
                    for time_field in ['published_parsed', 'updated_parsed']:
                        if getattr(entry, time_field, None):
                            pub_time = datetime(*entry[time_field][:6])
                            break
                    
                    if not pub_time or pub_time < cutoff:
                        continue
                    
                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    url = entry.get('link', '')
                    
                    if not title or not url:
                        continue
                    
                    article = NewsArticle(
                        title=title,
                        summary=summary[:500],
                        content=None,
                        url=url,
                        source=NewsSource.GOOGLE_NEWS,
                        source_name="Google News",
                        published_at=pub_time,
                        author=None,
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
                    logger.warning(f"Error parsing Google News entry: {e}")
                    continue
            
            logger.info(f"Fetched {len(articles)} articles from Google News for {company}")
            return articles
            
        except Exception as e:
            logger.error(f"Google News RSS fetch failed: {e}")
            return []


class CompositeNewsProvider:
    """
    Composite provider with automatic fallback chain.
    
    Priority order:
    1. Yahoo Finance (free, comprehensive)
    2. Finnhub (free tier, real-time)
    3. Alpha Vantage (free tier, sentiment)
    4. NewsAPI (free tier, broad coverage)
    5. Google News RSS (free, broad)
    6. Financial RSS feeds
    """
    
    def __init__(
        self,
        finnhub_key: Optional[str] = None,
        alpha_vantage_key: Optional[str] = None,
        newsapi_key: Optional[str] = None
    ):
        self.providers: List[NewsProviderBase] = []
        
        # Primary providers (best first)
        self.providers.append(YahooFinanceNewsProvider())
        
        if finnhub_key:
            self.providers.append(FinnhubNewsProvider(finnhub_key))
        
        if alpha_vantage_key:
            self.providers.append(AlphaVantageNewsProvider(alpha_vantage_key))
        
        if newsapi_key:
            self.providers.append(NewsAPIProvider(newsapi_key))
        
        # Fallback RSS providers
        self.providers.append(GoogleNewsRSSProvider())
        
        # Add financial RSS feeds
        self.providers.append(RSSProvider(
            "marketwatch", 
            "https://feeds.marketwatch.com/marketwatch/topstories/",
            NewsSource.MARKETWATCH
        ))
        self.providers.append(RSSProvider(
            "cnbc",
            "https://www.cnbc.com/id/100003114/device/rss/rss.html",
            NewsSource.CNBC
        ))
        self.providers.append(RSSProvider(
            "reuters_business",
            "https://feeds.reuters.com/reuters/businessNews",
            NewsSource.REUTERS
        ))
        self.providers.append(RSSProvider(
            "bloomberg",
            "https://feeds.bloomberg.com/markets/news.rss",
            NewsSource.BLOOMBERG
        ))
        
        # Add a working CNBC alternative
        self.providers.append(RSSProvider(
            "cnbc_top",
            "https://www.cnbc.com/id/10001147/device/rss/rss.html",
            NewsSource.CNBC
        ))
    
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
        
        Returns merged, deduplicated, and ranked articles.
        """
        all_articles = []
        successful_providers = 0
        
        # Fetch from all providers concurrently
        tasks = [
            provider.fetch_news(company, ticker, lookback_hours, max_articles)
            for provider in self.providers
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for provider, result in zip(self.providers, results):
            if isinstance(result, Exception):
                logger.warning(f"Provider {provider.name} failed: {result}")
                continue
            elif result:
                all_articles.extend(result)
                successful_providers += 1
                logger.info(f"Provider {provider.name} returned {len(result)} articles")
        
        # Deduplicate
        deduplicated = self._deduplicate_articles(all_articles)
        
        # Rank by relevance and importance
        ranked = self._rank_articles(deduplicated, company, ticker)
        
        logger.info(
            f"Fetched {len(ranked)} unique articles for {company} "
            f"from {successful_providers}/{len(self.providers)} providers"
        )
        
        return ranked[:max_articles]
    
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
        for article in articles:
            # Composite score: relevance * importance * freshness * market_impact
            article.relevance_score = self.providers[0]._calculate_relevance(
                article, company, ticker
            ) if self.providers else 0.5
            
            composite = (
                article.relevance_score * 0.35 +
                article.importance_score * 0.25 +
                article.freshness_score * 0.20 +
                article.market_impact_score * 0.20
            )
            
            # Boost for credible sources
            credible = {NewsSource.REUTERS, NewsSource.BLOOMBERG, NewsSource.FINANCIAL_TIMES, NewsSource.WALL_STREET_JOURNAL}
            if article.source in credible:
                composite *= 1.15
            
            # Store composite score in metadata
            article.metadata = article.metadata or {}
            article.metadata['composite_score'] = round(composite, 3)
        
        # Sort by composite score descending
        return sorted(articles, key=lambda a: a.metadata.get('composite_score', 0), reverse=True)
    
    async def close_all(self):
        """Close all provider sessions."""
        for provider in self.providers:
            await provider.close()


# Global composite provider
_composite_provider: Optional[CompositeNewsProvider] = None


def get_news_provider(
    finnhub_key: Optional[str] = None,
    alpha_vantage_key: Optional[str] = None,
    newsapi_key: Optional[str] = None
) -> CompositeNewsProvider:
    """Get or create global composite news provider."""
    global _composite_provider
    if _composite_provider is None:
        import os
        _composite_provider = CompositeNewsProvider(
            finnhub_key=finnhub_key or os.getenv('FINNHUB_API_KEY'),
            alpha_vantage_key=alpha_vantage_key or os.getenv('ALPHA_VANTAGE_API_KEY'),
            newsapi_key=newsapi_key or os.getenv('NEWSAPI_KEY')
        )
    return _composite_provider


async def close_news_provider():
    """Close global news provider."""
    global _composite_provider
    if _composite_provider:
        await _composite_provider.close_all()
        _composite_provider = None