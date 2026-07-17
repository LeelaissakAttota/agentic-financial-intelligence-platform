"""
News Database Models - SQLAlchemy models for news article storage
"""

from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from enum import Enum as PyEnum

from sqlalchemy import (
    String, DateTime, ForeignKey, Text, Integer, Float, Boolean, 
    Enum as SQLEnum, Index, JSON, ARRAY, LargeBinary
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from data.news.schemas import NewsSource, NewsCategory, SentimentLabel


class Base(DeclarativeBase):
    pass


class NewsArticleModel(Base):
    """SQLAlchemy model for news articles."""
    __tablename__ = "news_articles"
    
    # Primary key
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    
    # Core content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    
    # Source info
    source: Mapped[NewsSource] = mapped_column(
        SQLEnum(NewsSource), nullable=False, index=True
    )
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    
    # Analysis
    category: Mapped[Optional[NewsCategory]] = mapped_column(
        SQLEnum(NewsCategory), nullable=True, index=True
    )
    
    # Sentiment (stored as JSON for flexibility)
    sentiment_label: Mapped[Optional[SentimentLabel]] = mapped_column(
        SQLEnum(SentimentLabel), nullable=True, index=True
    )
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentiment_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentiment_positive: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentiment_negative: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentiment_neutral: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentiment_key_phrases: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Events (stored as JSON)
    events: Mapped[List[dict]] = mapped_column(JSON, default=list)
    
    # Company mentions (stored as JSON)
    companies: Mapped[List[dict]] = mapped_column(JSON, default=list)
    
    # People mentions (stored as JSON)
    people: Mapped[List[dict]] = mapped_column(JSON, default=list)
    
    # Tickers mentioned
    tickers: Mapped[List[str]] = mapped_column(ARRAY(String(20)), default=list)
    
    # Scoring
    importance_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    market_impact_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    freshness_score: Mapped[float] = mapped_column(Float, default=0.0)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    credibility_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    composite_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    
    # Deduplication
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    duplicate_of: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Metadata (flexible JSON)
    article_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Embedding reference (link to vector store)
    embedding_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company_links: Mapped[List["ArticleCompanyLink"]] = relationship(
        "ArticleCompanyLink", back_populates="article", cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index('ix_news_articles_published_source', 'published_at', 'source'),
        Index('ix_news_articles_company_relevance', 'relevance_score', 'importance_score'),
        Index('ix_news_articles_sentiment_date', 'sentiment_label', 'published_at'),
        Index('ix_news_articles_composite_score', 'composite_score'),
    )


class CompanyModel(Base):
    """SQLAlchemy model for companies mentioned in news."""
    __tablename__ = "news_companies"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    cik: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    lei: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    isin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Classification
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    exchange: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    market_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # News tracking
    mention_count: Mapped[int] = mapped_column(Integer, default=0, index=True)
    first_mention: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_mention: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    avg_sentiment: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Metadata
    company_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    article_links: Mapped[List["ArticleCompanyLink"]] = relationship(
        "ArticleCompanyLink", back_populates="company"
    )
    
    __table_args__ = (
        Index('ix_news_companies_ticker_sector', 'ticker', 'sector'),
        Index('ix_news_companies_mention_count', 'mention_count'),
    )


class ArticleCompanyLink(Base):
    """Many-to-many link between articles and companies with mention details."""
    __tablename__ = "article_company_links"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    article_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("news_articles.id"), nullable=False, index=True
    )
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("news_companies.id"), nullable=False, index=True
    )
    
    # Mention details
    mention_count: Mapped[int] = mapped_column(Integer, default=1)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    sentiment: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # -1 to 1
    
    # Context
    context_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    article: Mapped["NewsArticleModel"] = relationship(
        "NewsArticleModel", back_populates="company_links"
    )
    company: Mapped["CompanyModel"] = relationship(
        "CompanyModel", back_populates="article_links"
    )
    
    __table_args__ = (
        Index('ix_article_company_links_article_company', 'article_id', 'company_id', unique=True),
        Index('ix_article_company_links_primary', 'is_primary'),
    )


class NewsSummaryModel(Base):
    """SQLAlchemy model for news summary aggregations."""
    __tablename__ = "news_summaries"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    lookback_hours: Mapped[int] = mapped_column(Integer, default=24)
    
    total_articles: Mapped[int] = mapped_column(Integer, default=0)
    
    # Sentiment
    overall_sentiment: Mapped[SentimentLabel] = mapped_column(
        SQLEnum(SentimentLabel), nullable=False
    )
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_distribution: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Categories
    category_counts: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Top events (JSON)
    top_events: Mapped[List[dict]] = mapped_column(JSON, default=list)
    
    # Related companies
    related_companies: Mapped[List[dict]] = mapped_column(JSON, default=list)
    
    # Top articles (references)
    top_article_ids: Mapped[List[str]] = mapped_column(ARRAY(String(36)), default=list)
    
    # Source diversity
    source_counts: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Metrics
    avg_importance: Mapped[float] = mapped_column(Float, default=0.0)
    avg_market_impact: Mapped[float] = mapped_column(Float, default=0.0)
    avg_relevance: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Source breakdown
    source_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Category breakdown
    category_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Time period
    time_period: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Confidence
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_news_summaries_company_period', 'company_name', 'period_start', 'period_end'),
        Index('ix_news_summaries_ticker_period', 'ticker', 'period_start'),
    )


class NewsEmbeddingModel(Base):
    """SQLAlchemy model for article embeddings."""
    __tablename__ = "news_embeddings"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    article_id: Mapped[str] = mapped_column(String(36), ForeignKey("news_articles.id"), nullable=False, index=True)
    
    # Embedding metadata
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Vector reference (stored in ChromaDB, this is just the ID)
    vector_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Metadata
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # Hash of text that was embedded
    text_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_news_embeddings_article_model', 'article_id', 'model_name'),
    )


class NewsWatchlistModel(Base):
    """SQLAlchemy model for user news watchlists."""
    __tablename__ = "news_watchlists"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    
    # Company/ticker tracking
    companies: Mapped[List[dict]] = mapped_column(JSON, default=list)  # [{"name": "", "ticker": ""}]
    
    # Alert settings
    alert_on_earnings: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_on_ma: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_on_lawsuit: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_on_regulatory: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_on_management_change: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_on_analyst_rating: Mapped[bool] = mapped_column(Boolean, default=True)
    min_importance_score: Mapped[float] = mapped_column(Float, default=0.5)
    min_sentiment_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Notification channels
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    webhook_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Timing
    check_interval_hours: Mapped[int] = mapped_column(Integer, default=6)
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_news_watchlists_user_active', 'user_id', 'is_active'),
    )


# Repository functions
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc


async def upsert_article(session: AsyncSession, article_data: dict) -> NewsArticleModel:
    """Upsert article by content_hash."""
    content_hash = article_data.get('content_hash')
    
    # Check existing
    stmt = select(NewsArticleModel).where(NewsArticleModel.content_hash == content_hash)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        # Update existing
        for key, value in article_data.items():
            if key != 'id' and hasattr(existing, key):
                setattr(existing, key, value)
        existing.updated_at = datetime.utcnow()
        return existing
    else:
        # Create new
        article = NewsArticleModel(**article_data)
        session.add(article)
        return article


async def upsert_company(session: AsyncSession, company_data: dict) -> CompanyModel:
    """Upsert company by ticker or name."""
    ticker = company_data.get('ticker')
    name = company_data.get('name')
    
    if ticker:
        stmt = select(CompanyModel).where(CompanyModel.ticker == ticker)
    else:
        stmt = select(CompanyModel).where(CompanyModel.name == name)
        
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        for key, value in company_data.items():
            if key != 'id' and hasattr(existing, key):
                setattr(existing, key, value)
        existing.updated_at = datetime.utcnow()
        return existing
    else:
        company = CompanyModel(**company_data)
        session.add(company)
        return company


async def link_article_company(
    session: AsyncSession, 
    article_id: str, 
    company_id: str, 
    mention_count: int = 1,
    is_primary: bool = False,
    sentiment: Optional[float] = None,
    context_snippet: Optional[str] = None
) -> ArticleCompanyLink:
    """Link article and company."""
    stmt = select(ArticleCompanyLink).where(
        and_(
            ArticleCompanyLink.article_id == article_id,
            ArticleCompanyLink.company_id == company_id
        )
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.mention_count += mention_count
        if is_primary:
            existing.is_primary = True
        if sentiment is not None:
            existing.sentiment = sentiment
        if context_snippet:
            existing.context_snippet = context_snippet
        return existing
    else:
        link = ArticleCompanyLink(
            article_id=article_id,
            company_id=company_id,
            mention_count=mention_count,
            is_primary=is_primary,
            sentiment=sentiment,
            context_snippet=context_snippet
        )
        session.add(link)
        return link


async def get_articles_for_company(
    session: AsyncSession,
    company_name: str,
    ticker: Optional[str] = None,
    lookback_hours: int = 24,
    limit: int = 50
) -> List[NewsArticleModel]:
    """Get recent articles mentioning a company."""
    cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
    
    # Find company
    if ticker:
        stmt = select(CompanyModel).where(CompanyModel.ticker == ticker)
    else:
        stmt = select(CompanyModel).where(CompanyModel.name == company_name)
    
    result = await session.execute(stmt)
    company = result.scalar_one_or_none()
    
    if not company:
        return []
        
    # Get linked articles
    stmt = (
        select(NewsArticleModel)
        .join(ArticleCompanyLink)
        .where(
            and_(
                ArticleCompanyLink.company_id == company.id,
                NewsArticleModel.published_at >= cutoff,
                NewsArticleModel.is_duplicate == False
            )
        )
        .order_by(desc(NewsArticleModel.published_at))
        .limit(limit)
    )
    
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_recent_articles(
    session: AsyncSession,
    lookback_hours: int = 24,
    min_importance: float = 0.0,
    min_relevance: float = 0.0,
    sources: Optional[List[NewsSource]] = None,
    categories: Optional[List[NewsCategory]] = None,
    limit: int = 100
) -> List[NewsArticleModel]:
    """Get recent articles with filters."""
    cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
    
    stmt = select(NewsArticleModel).where(
        and_(
            NewsArticleModel.published_at >= cutoff,
            NewsArticleModel.is_duplicate == False,
            NewsArticleModel.importance_score >= min_importance,
            NewsArticleModel.relevance_score >= min_relevance
        )
    )
    
    if sources:
        stmt = stmt.where(NewsArticleModel.source.in_(sources))
    if categories:
        stmt = stmt.where(NewsArticleModel.category.in_(categories))
        
    stmt = stmt.order_by(desc(NewsArticleModel.composite_score)).limit(limit)
    
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_sentiment_trend(
    session: AsyncSession,
    company_name: str,
    ticker: Optional[str] = None,
    days: int = 30
) -> List[dict]:
    """Get sentiment trend for a company over time."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    if ticker:
        stmt = select(CompanyModel).where(CompanyModel.ticker == ticker)
    else:
        stmt = select(CompanyModel).where(CompanyModel.name == company_name)
        
    result = await session.execute(stmt)
    company = result.scalar_one_or_none()
    
    if not company:
        return []
        
    # Get daily sentiment from articles
    stmt = (
        select(
            func.date(NewsArticleModel.published_at).label('date'),
            func.avg(NewsArticleModel.sentiment_score).label('avg_sentiment'),
            func.count(NewsArticleModel.id).label('article_count'),
            func.avg(NewsArticleModel.importance_score).label('avg_importance')
        )
        .join(ArticleCompanyLink)
        .where(
            and_(
                ArticleCompanyLink.company_id == company.id,
                NewsArticleModel.published_at >= cutoff,
                NewsArticleModel.is_duplicate == False,
                NewsArticleModel.sentiment_score.isnot(None)
            )
        )
        .group_by(func.date(NewsArticleModel.published_at))
        .order_by(func.date(NewsArticleModel.published_at))
    )
    
    result = await session.execute(stmt)
    return [
        {
            "date": row.date.isoformat(),
            "avg_sentiment": float(row.avg_sentiment) if row.avg_sentiment else 0.0,
            "article_count": row.article_count,
            "avg_importance": float(row.avg_importance) if row.avg_importance else 0.0
        }
        for row in result.all()
    ]


async def get_top_companies_by_mentions(
    session: AsyncSession,
    lookback_hours: int = 24,
    limit: int = 20
) -> List[dict]:
    """Get top mentioned companies in recent news."""
    cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
    
    stmt = (
        select(
            CompanyModel.name,
            CompanyModel.ticker,
            func.count(ArticleCompanyLink.article_id).label('mention_count'),
            func.sum(ArticleCompanyLink.mention_count).label('total_mentions'),
            func.avg(NewsArticleModel.sentiment_score).label('avg_sentiment'),
            func.avg(NewsArticleModel.importance_score).label('avg_importance')
        )
        .join(ArticleCompanyLink, CompanyModel.id == ArticleCompanyLink.company_id)
        .join(NewsArticleModel, ArticleCompanyLink.article_id == NewsArticleModel.id)
        .where(
            and_(
                NewsArticleModel.published_at >= cutoff,
                NewsArticleModel.is_duplicate == False
            )
        )
        .group_by(CompanyModel.id, CompanyModel.name, CompanyModel.ticker)
        .order_by(desc('mention_count'))
        .limit(limit)
    )
    
    result = await session.execute(stmt)
    return [
        {
            "name": row.name,
            "ticker": row.ticker,
            "mention_count": row.mention_count,
            "total_mentions": row.total_mentions,
            "avg_sentiment": float(row.avg_sentiment) if row.avg_sentiment else 0.0,
            "avg_importance": float(row.avg_importance) if row.avg_importance else 0.0
        }
        for row in result.all()
    ]


async def create_news_summary(session: AsyncSession, summary_data: dict) -> NewsSummaryModel:
    """Create news summary record."""
    summary = NewsSummaryModel(**summary_data)
    session.add(summary)
    return summary


async def get_latest_summary(
    session: AsyncSession,
    company_name: str,
    ticker: Optional[str] = None,
    lookback_hours: int = 24
) -> Optional[NewsSummaryModel]:
    """Get latest news summary for a company."""
    if ticker:
        stmt = select(NewsSummaryModel).where(
            and_(
                NewsSummaryModel.ticker == ticker,
                NewsSummaryModel.lookback_hours == lookback_hours
            )
        )
    else:
        stmt = select(NewsSummaryModel).where(
            and_(
                NewsSummaryModel.company_name == company_name,
                NewsSummaryModel.lookback_hours == lookback_hours
            )
        )
        
    stmt = stmt.order_by(desc(NewsSummaryModel.generated_at)).limit(1)
    
    result = await session.execute(stmt)
    return result.scalar_one_or_none()