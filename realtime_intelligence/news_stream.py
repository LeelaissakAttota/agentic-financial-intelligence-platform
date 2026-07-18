"""
News Stream - Real-time news streaming and distribution.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import hashlib

from .server import get_websocket_server, MessageType, WSMessage

logger = logging.getLogger(__name__)


class NewsSource(str, Enum):
    """News source types."""
    REUTERS = "reuters"
    BLOOMBERG = "bloomberg"
    WSJ = "wsj"
    FT = "ft"
    CNBC = "cnbc"
    MARKETWATCH = "marketwatch"
    SEEKING_ALPHA = "seeking_alpha"
    BENZINGA = "benzinga"
    PR_NEWSWIRE = "prnewswire"
    BUSINESS_WIRE = "businesswire"
    SEC = "sec"
    CUSTOM = "custom"


class NewsCategory(str, Enum):
    """News categories."""
    EARNINGS = "earnings"
    MERGERS_ACQUISITIONS = "mergers_acquisitions"
    PRODUCT_LAUNCH = "product_launch"
    REGULATORY = "regulatory"
    MANAGEMENT_CHANGE = "management_change"
    GUIDANCE = "guidance"
    DIVIDEND = "dividend"
    SPLIT = "split"
    BUYBACK = "buyback"
    ANALYST_RATING = "analyst_rating"
    MARKET_MOVER = "market_mover"
    SECTOR_NEWS = "sector_news"
    MACRO = "macro"
    GEOPOLITICAL = "geopolitical"
    GENERAL = "general"


@dataclass
class NewsArticle:
    """Real-time news article."""
    id: str
    title: str
    summary: str
    content: str
    source: NewsSource
    category: NewsCategory
    symbols: List[str]  # Related tickers
    entities: List[Dict[str, Any]]  # Named entities
    url: str
    published_at: datetime
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    relevance_score: float = 1.0
    language: str = "en"
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "content": self.content,
            "source": self.source.value,
            "category": self.category.value,
            "symbols": self.symbols,
            "entities": self.entities,
            "url": self.url,
            "published_at": self.published_at.isoformat(),
            "sentiment_score": self.sentiment_score,
            "sentiment_label": self.sentiment_label,
            "relevance_score": self.relevance_score,
            "language": self.language,
            "author": self.author,
            "tags": self.tags,
            "metadata": self.metadata
        }
    
    @classmethod
    def create(
        cls,
        title: str,
        summary: str,
        content: str,
        source: NewsSource,
        category: NewsCategory,
        symbols: List[str],
        url: str,
        published_at: datetime,
        **kwargs
    ) -> "NewsArticle":
        """Factory method to create a news article with auto-generated ID."""
        # Generate deterministic ID from URL
        article_id = hashlib.sha256(url.encode()).hexdigest()[:16]
        return cls(
            id=article_id,
            title=title,
            summary=summary,
            content=content,
            source=source,
            category=category,
            symbols=[s.upper() for s in symbols],
            entities=kwargs.get("entities", []),
            url=url,
            published_at=published_at,
            **{k: v for k, v in kwargs.items() if k in [
                "sentiment_score", "sentiment_label", "relevance_score",
                "language", "author", "tags", "metadata"
            ]}
        )


class NewsStream:
    """
    Real-time news streaming service.
    Ingests news from providers and distributes via WebSocket.
    """
    
    def __init__(self):
        self.ws_server = get_websocket_server()
        self._running = False
        self._subscriptions: Dict[str, Set[str]] = defaultdict(set)
        self._data_providers: Dict[str, Callable] = {}
        self._latest_articles: Dict[str, NewsArticle] = {}
        self._symbol_index: Dict[str, Set[str]] = defaultdict(set)  # symbol -> article_ids
        self._source_index: Dict[NewsSource, Set[str]] = defaultdict(set)
        self._category_index: Dict[NewsCategory, Set[str]] = defaultdict(set)
        self._update_callbacks: List[Callable] = []
        self._dedup_cache: Set[str] = set()
        self._dedup_ttl: timedelta = timedelta(hours=24)
        self._stats = {
            "articles_received": 0,
            "articles_published": 0,
            "duplicates_filtered": 0,
            "broadcasts_sent": 0,
            "errors": 0
        }
        
        # Register WebSocket handlers
        self.ws_server.register_handler(MessageType.SUBSCRIBE, self._handle_subscribe)
        self.ws_server.register_handler(MessageType.UNSUBSCRIBE, self._handle_unsubscribe)
    
    async def start(self) -> None:
        """Start the news stream."""
        self._running = True
        await self.ws_server.start_heartbeat()
        # Start deduplication cache cleanup
        asyncio.create_task(self._dedup_cleanup_loop())
        logger.info("News stream started")
    
    async def stop(self) -> None:
        """Stop the news stream."""
        self._running = False
        logger.info("News stream stopped")
    
    def register_provider(self, name: str, provider: Callable) -> None:
        """Register a news data provider."""
        self._data_providers[name] = provider
        logger.info(f"Registered news provider: {name}")
    
    def register_update_callback(self, callback: Callable) -> None:
        """Register a callback for news updates."""
        self._update_callbacks.append(callback)
    
    async def _handle_subscribe(self, client, message: WSMessage) -> None:
        """Handle news subscription."""
        topics = message.payload.get("topics", [])
        if isinstance(topics, str):
            topics = [topics]
        
        for topic in topics:
            if topic.startswith("news:"):
                parts = topic.split(":")
                if len(parts) >= 2:
                    filter_type = parts[1]
                    client.subscriptions.add(topic)
                    self._subscriptions[topic].add(client.client_id)
                    
                    # Send recent articles for this filter
                    await self._send_recent_articles(client, filter_type, parts[2] if len(parts) > 2 else None)
    
    async def _handle_unsubscribe(self, client, message: WSMessage) -> None:
        """Handle news unsubscription."""
        topics = message.payload.get("topics", [])
        if isinstance(topics, str):
            topics = [topics]
        
        for topic in topics:
            if topic.startswith("news:"):
                self._subscriptions[topic].discard(client.client_id)
                if not self._subscriptions[topic]:
                    del self._subscriptions[topic]
                client.subscriptions.discard(topic)
    
    async def _send_recent_articles(
        self, 
        client, 
        filter_type: str, 
        filter_value: Optional[str] = None
    ) -> None:
        """Send recent articles matching filter to client."""
        articles = []
        
        if filter_type == "symbol" and filter_value:
            article_ids = self._symbol_index.get(filter_value.upper(), set())
            articles = [self._latest_articles[aid] for aid in article_ids if aid in self._latest_articles]
        elif filter_type == "source" and filter_value:
            try:
                source = NewsSource(filter_value)
                article_ids = self._source_index.get(source, set())
                articles = [self._latest_articles[aid] for aid in article_ids if aid in self._latest_articles]
            except ValueError:
                pass
        elif filter_type == "category" and filter_value:
            try:
                category = NewsCategory(filter_value)
                article_ids = self._category_index.get(category, set())
                articles = [self._latest_articles[aid] for aid in article_ids if aid in self._latest_articles]
            except ValueError:
                pass
        elif filter_type == "all":
            articles = list(self._latest_articles.values())
        
        # Sort by published date, most recent first
        articles.sort(key=lambda a: a.published_at, reverse=True)
        
        # Send up to 20 most recent
        for article in articles[:20]:
            await client.send(WSMessage(
                type=MessageType.NEWS_ARTICLE,
                payload=article.to_dict()
            ))
    
    async def _dedup_cleanup_loop(self) -> None:
        """Periodically clean up deduplication cache."""
        while self._running:
            await asyncio.sleep(3600)  # Every hour
            cutoff = datetime.utcnow() - self._dedup_ttl
            # Note: In production, would track timestamps with IDs
            # For now, limit cache size
            if len(self._dedup_cache) > 100000:
                # Keep newest 50000 (approximate)
                self._dedup_cache = set(list(self._dedup_cache)[-50000:])
    
    def _is_duplicate(self, article: NewsArticle) -> bool:
        """Check if article is a duplicate."""
        # Create fingerprint from title + source + published time (rounded)
        time_bucket = article.published_at.replace(minute=0, second=0, microsecond=0)
        fingerprint = f"{article.title}|{article.source.value}|{time_bucket.isoformat()}"
        fingerprint_hash = hashlib.sha256(fingerprint.encode()).hexdigest()[:32]
        
        if fingerprint_hash in self._dedup_cache:
            return True
        
        self._dedup_cache.add(fingerprint_hash)
        return False
    
    async def publish_article(self, article: NewsArticle) -> None:
        """Publish a news article to subscribers."""
        self._stats["articles_received"] += 1
        
        # Check for duplicates
        if self._is_duplicate(article):
            self._stats["duplicates_filtered"] += 1
            logger.debug(f"Filtered duplicate article: {article.title[:50]}")
            return
        
        # Store article
        self._latest_articles[article.id] = article
        self._symbol_index[article.symbols[0] if article.symbols else "general"].add(article.id)
        for symbol in article.symbols:
            self._symbol_index[symbol.upper()].add(article.id)
        self._source_index[article.source].add(article.id)
        self._category_index[article.category].add(article.id)
        
        # Limit stored articles
        if len(self._latest_articles) > 50000:
            # Remove oldest 10000
            sorted_ids = sorted(
                self._latest_articles.keys(),
                key=lambda k: self._latest_articles[k].published_at
            )
            for old_id in sorted_ids[:10000]:
                old_article = self._latest_articles.pop(old_id, None)
                if old_article:
                    for symbol in old_article.symbols:
                        self._symbol_index[symbol.upper()].discard(old_id)
                    self._source_index[old_article.source].discard(old_id)
                    self._category_index[old_article.category].discard(old_id)
        
        self._stats["articles_published"] += 1
        
        # Determine subscribers
        subscribers = set()
        
        # Subscribers for specific symbols
        for symbol in article.symbols:
            subscribers |= self._subscriptions.get(f"news:symbol:{symbol.upper()}", set())
            subscribers |= self._subscriptions.get(f"news:symbol:{symbol.upper()}:{article.category.value}", set())
        
        # Subscribers for source
        subscribers |= self._subscriptions.get(f"news:source:{article.source.value}", set())
        
        # Subscribers for category
        subscribers |= self._subscriptions.get(f"news:category:{article.category.value}", set())
        
        # Subscribers for all news
        subscribers |= self._subscriptions.get("news:all", set())
        
        if subscribers:
            message = WSMessage(
                type=MessageType.NEWS_ARTICLE,
                payload=article.to_dict()
            )
            sent = await self.ws_server.send_to_clients(list(subscribers), message)
            self._stats["broadcasts_sent"] += sent
        
        # Call update callbacks
        for callback in self._update_callbacks:
            try:
                await callback(article)
            except Exception as e:
                logger.error(f"News update callback error: {e}")
    
    async def publish_batch(self, articles: List[NewsArticle]) -> None:
        """Publish multiple articles."""
        for article in articles:
            await self.publish_article(article)
    
    def get_latest_articles(
        self,
        symbol: Optional[str] = None,
        source: Optional[NewsSource] = None,
        category: Optional[NewsCategory] = None,
        limit: int = 50,
        since: Optional[datetime] = None
    ) -> List[NewsArticle]:
        """Get latest articles with optional filters."""
        articles = list(self._latest_articles.values())
        
        if symbol:
            article_ids = self._symbol_index.get(symbol.upper(), set())
            articles = [a for a in articles if a.id in article_ids]
        
        if source:
            article_ids = self._source_index.get(source, set())
            articles = [a for a in articles if a.id in article_ids]
        
        if category:
            article_ids = self._category_index.get(category, set())
            articles = [a for a in articles if a.id in article_ids]
        
        if since:
            articles = [a for a in articles if a.published_at >= since]
        
        articles.sort(key=lambda a: a.published_at, reverse=True)
        return articles[:limit]
    
    def get_article(self, article_id: str) -> Optional[NewsArticle]:
        """Get article by ID."""
        return self._latest_articles.get(article_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get streaming statistics."""
        return {
            **self._stats,
            "stored_articles": len(self._latest_articles),
            "indexed_symbols": len(self._symbol_index),
            "active_subscriptions": len(self._subscriptions)
        }


# Global news stream instance
_news_stream: Optional[NewsStream] = None


def get_news_stream() -> NewsStream:
    """Get or create the global news stream."""
    global _news_stream
    if _news_stream is None:
        _news_stream = NewsStream()
    return _news_stream