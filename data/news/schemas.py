"""
Pydantic Schemas for News Intelligence Agent
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class NewsSource(str, Enum):
    """News source enumeration."""
    YAHOO_FINANCE = "yahoo_finance"
    FINNHUB = "finnhub"
    ALPHA_VANTAGE = "alpha_vantage"
    NEWSAPI = "newsapi"
    GOOGLE_NEWS = "google_news"
    MARKETWATCH = "marketwatch"
    CNBC = "cnbc"
    REUTERS = "reuters"
    BLOOMBERG = "bloomberg"
    FINANCIAL_TIMES = "financial_times"
    WALL_STREET_JOURNAL = "wall_street_journal"
    BARRONS = "barrons"
    SEEKING_ALPHA = "seeking_alpha"
    MOTLEY_FOOL = "motley_fool"
    ZACKS = "zacks"
    TIPRANKS = "tipranks"
    BENZINGA = "benzinga"
    UNKNOWN = "unknown"


class NewsCategory(str, Enum):
    """Financial news category enumeration."""
    GENERAL = "general"
    EARNINGS = "earnings"
    GUIDANCE = "guidance"
    MERGERS_ACQUISITIONS = "mergers_acquisitions"
    PRODUCT_LAUNCH = "product_launch"
    LAYOFFS = "layoffs"
    PARTNERSHIP = "partnership"
    LAWSUIT = "lawsuit"
    REGULATORY = "regulatory"
    SEC_FILING = "sec_filing"
    MANAGEMENT_CHANGE = "management_change"
    DIVIDEND = "dividend"
    STOCK_SPLIT = "stock_split"
    ANALYST_RATING = "analyst_rating"
    SHARE_BUYBACK = "share_buyback"
    IPO = "ipo"
    BANKRUPTCY = "bankruptcy"
    MACROECONOMIC = "macroeconomic"
    SECTOR_NEWS = "sector_news"
    INSIDER_TRADING = "insider_trading"
    SHORT_REPORT = "short_report"
    CRYPTO = "crypto"
    COMMODITIES = "commodities"
    FOREX = "forex"


class SentimentLabel(str, Enum):
    """Sentiment label enumeration."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class CompanyMention(BaseModel):
    """Company mention in article."""
    name: str
    ticker: Optional[str] = None
    mention_count: int = 1
    is_primary: bool = False
    sentiment: Optional[float] = None  # -1 to 1


class PersonMention(BaseModel):
    """Person mention in article."""
    name: str
    role: Optional[str] = None
    company: Optional[str] = None
    mention_count: int = 1


class EventDetection(BaseModel):
    """Detected financial event."""
    event_type: NewsCategory
    confidence: float = Field(ge=0.0, le=1.0)
    details: Dict[str, Any] = Field(default_factory=dict)


class ArticleSentiment(BaseModel):
    """Article-level sentiment analysis."""
    label: SentimentLabel
    score: float = Field(ge=-1.0, le=1.0)  # -1 to 1
    confidence: float = Field(ge=0.0, le=1.0)
    positive_score: float = Field(ge=0.0, le=1.0)
    negative_score: float = Field(ge=0.0, le=1.0)
    neutral_score: float = Field(ge=0.0, le=1.0)
    key_phrases: List[str] = Field(default_factory=list)


class NewsArticle(BaseModel):
    """Complete news article with analysis."""
    # Core content
    title: str
    summary: str
    content: Optional[str] = None
    url: str
    
    # Source info
    source: NewsSource
    source_name: str
    author: Optional[str] = None
    published_at: datetime
    
    # Analysis
    category: Optional[NewsCategory] = None
    sentiment: Optional[ArticleSentiment] = None
    events: List[EventDetection] = Field(default_factory=list)
    companies: List[CompanyMention] = Field(default_factory=list)
    people: List[PersonMention] = Field(default_factory=list)
    tickers: List[str] = Field(default_factory=list)
    
    # Scoring
    importance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    market_impact_score: float = Field(default=0.0, ge=0.0, le=1.0)
    freshness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Metadata
    content_hash: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # For deduplication
    duplicate_of: Optional[str] = None  # content_hash of original
    is_duplicate: bool = False


class NewsSummary(BaseModel):
    """Aggregated news summary for a company."""
    company: str
    ticker: Optional[str] = None
    period_start: datetime
    period_end: datetime
    total_articles: int
    
    # Sentiment summary
    overall_sentiment: SentimentLabel
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    sentiment_distribution: Dict[str, int] = Field(default_factory=dict)
    
    # Category breakdown
    category_counts: Dict[str, int] = Field(default_factory=dict)
    
    # Top events
    top_events: List[EventDetection] = Field(default_factory=list)
    
    # Key companies mentioned
    related_companies: List[CompanyMention] = Field(default_factory=list)
    
    # Top articles
    top_articles: List[NewsArticle] = Field(default_factory=list)
    
    # Source diversity
    source_counts: Dict[str, int] = Field(default_factory=dict)
    
    # Metrics
    avg_importance: float = 0.0
    avg_market_impact: float = 0.0
    avg_relevance: float = 0.0
    
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class NewsAgentInput(BaseModel):
    """Input for News Agent."""
    company: str
    ticker: Optional[str] = None
    lookback_hours: int = Field(default=24, ge=1, le=168)
    max_articles: int = Field(default=50, ge=1, le=200)
    sources: Optional[List[NewsSource]] = None
    min_relevance: float = Field(default=0.3, ge=0.0, le=1.0)
    include_analysis: bool = True


class NewsAgentOutput(BaseModel):
    """Output from News Agent."""
    company: str
    ticker: Optional[str] = None
    articles: List[NewsArticle] = Field(default_factory=list)
    summary: Optional[NewsSummary] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    lookback_hours: int
    total_fetched: int
    sources_used: List[str] = Field(default_factory=list)


class WorkerResponse(BaseModel):
    """Standardized worker response."""
    status: Literal["success", "error"]
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None