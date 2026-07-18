"""
Historical Intelligence Module - Phase 5

Stores and analyzes historical financial data for trend analysis, similarity search, and company evolution tracking.
"""

import asyncio
import logging
import json
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

import asyncpg
import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial.distance import cosine
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class IntelligenceBackend(ABC):
    """Abstract backend for historical intelligence storage."""
    
    @abstractmethod
    async def connect(self) -> None:
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        pass
    
    @abstractmethod
    async def store_report(self, report: "HistoricalReport") -> None:
        pass
    
    @abstractmethod
    async def get_report(self, report_id: str) -> Optional["HistoricalReport"]:
        pass
    
    @abstractmethod
    async def find_reports(
        self,
        company_id: str = None,
        report_type: str = None,
        start_date: date = None,
        end_date: date = None,
        limit: int = 100
    ) -> list["HistoricalReport"]:
        pass
    
    @abstractmethod
    async def store_news(self, news: "HistoricalNews") -> None:
        pass
    
    @abstractmethod
    async def get_news(
        self,
        company_id: str = None,
        start_date: date = None,
        end_date: date = None,
        limit: int = 100
    ) -> list["HistoricalNews"]:
        pass
    
    @abstractmethod
    async def store_filing(self, filing: "HistoricalFiling") -> None:
        pass
    
    @abstractmethod
    async def get_filings(
        self,
        company_id: str = None,
        filing_type: str = None,
        start_date: date = None,
        end_date: date = None,
        limit: int = 100
    ) -> list["HistoricalFiling"]:
        pass
    
    @abstractmethod
    async def store_sentiment(self, sentiment: "HistoricalSentiment") -> None:
        pass
    
    @abstractmethod
    async def get_sentiment_history(
        self,
        company_id: str = None,
        start_date: date = None,
        end_date: date = None,
        limit: int = 100
    ) -> list["HistoricalSentiment"]:
        pass


class PostgresIntelligenceBackend(IntelligenceBackend):
    """PostgreSQL backend for historical intelligence storage."""
    
    def __init__(self, dsn: str, pool_size: int = 10):
        self.dsn = dsn
        self.pool_size = pool_size
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(
            self.dsn,
            min_size=2,
            max_size=self.pool_size,
        )
        await self._init_schema()
    
    async def disconnect(self) -> None:
        if self.pool:
            await self.pool.close()
    
    async def _init_schema(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS historical_reports (
                    id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    company_name TEXT,
                    report_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    period_start DATE,
                    period_end DATE,
                    fiscal_year INTEGER,
                    fiscal_quarter INTEGER,
                    source_url TEXT,
                    source_document_id TEXT,
                    extracted_data JSONB NOT NULL DEFAULT '{}',
                    key_metrics JSONB NOT NULL DEFAULT '{}',
                    narrative TEXT,
                    risk_factors TEXT[],
                    guidance TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                );
                
                CREATE INDEX IF NOT EXISTS idx_historical_reports_company ON historical_reports(company_id);
                CREATE INDEX IF NOT EXISTS idx_historical_reports_type ON historical_reports(report_type);
                CREATE INDEX IF NOT EXISTS idx_historical_reports_dates ON historical_reports(period_start, period_end);
                CREATE INDEX IF NOT EXISTS idx_historical_reports_fiscal ON historical_reports(fiscal_year, fiscal_quarter);
                
                CREATE TABLE IF NOT EXISTS historical_news (
                    id TEXT PRIMARY KEY,
                    company_id TEXT,
                    company_name TEXT,
                    title TEXT NOT NULL,
                    content TEXT,
                    url TEXT,
                    source TEXT,
                    author TEXT,
                    published_at TIMESTAMPTZ NOT NULL,
                    sentiment REAL,
                    sentiment_label TEXT,
                    entities JSONB DEFAULT '[]',
                    topics JSONB DEFAULT '[]',
                    categories JSONB DEFAULT '[]',
                    relevance_score REAL,
                    language TEXT DEFAULT 'en',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                );
                
                CREATE INDEX IF NOT EXISTS idx_historical_news_company ON historical_news(company_id);
                CREATE INDEX IF NOT EXISTS idx_historical_news_published ON historical_news(published_at);
                CREATE INDEX IF NOT EXISTS idx_historical_news_sentiment ON historical_news(sentiment);
                
                CREATE TABLE IF NOT EXISTS historical_filings (
                    id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    company_name TEXT,
                    filing_type TEXT NOT NULL,
                    accession_number TEXT,
                    filing_date DATE NOT NULL,
                    period_end DATE,
                    fiscal_year INTEGER,
                    fiscal_quarter INTEGER,
                    document_url TEXT,
                    document_text TEXT,
                    extracted_sections JSONB DEFAULT '{}',
                    key_metrics JSONB DEFAULT '{}',
                    risk_factors TEXT[],
                    management_discussion TEXT,
                    exhibits JSONB DEFAULT '[]',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                );
                
                CREATE INDEX IF NOT EXISTS idx_historical_filings_company ON historical_filings(company_id);
                CREATE INDEX IF NOT EXISTS idx_historical_filings_type ON historical_filings(filing_type);
                CREATE INDEX IF NOT EXISTS idx_historical_filings_date ON historical_filings(filing_date);
                CREATE INDEX IF NOT EXISTS idx_historical_filings_fiscal ON historical_filings(fiscal_year, fiscal_quarter);
                
                CREATE TABLE IF NOT EXISTS historical_sentiment (
                    id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    company_name TEXT,
                    source TEXT NOT NULL,
                    source_type TEXT,
                    sentiment_score REAL NOT NULL,
                    sentiment_label TEXT,
                    confidence REAL,
                    entity_mentions JSONB DEFAULT '[]',
                    key_topics JSONB DEFAULT '[]',
                    referenced_date DATE,
                    published_at TIMESTAMPTZ NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                );
                
                CREATE INDEX IF NOT EXISTS idx_historical_sentiment_company ON historical_sentiment(company_id);
                CREATE INDEX IF NOT EXISTS idx_historical_sentiment_published ON historical_sentiment(published_at);
                CREATE INDEX IF NOT EXISTS idx_historical_sentiment_score ON historical_sentiment(sentiment_score);
            """)
    
    async def store_report(self, report: "HistoricalReport") -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO historical_reports (id, company_id, company_name, report_type, title,
                                               period_start, period_end, fiscal_year, fiscal_quarter,
                                               source_url, source_document_id, extracted_data, key_metrics,
                                               narrative, risk_factors, guidance, created_at, updated_at, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $9, $10, $10, $11, $12, $12, $13, $13, NOW(), NOW(), $14)
                ON CONFLICT (id) DO UPDATE SET
                    company_name = EXCLUDED.company_name,
                    report_type = EXCLUDED.report_type,
                    title = EXCLUDED.title,
                    period_start = EXCLUDED.period_start,
                    period_end = EXCLUDED.period_end,
                    fiscal_year = EXCLUDED.fiscal_year,
                    fiscal_quarter = EXCLUDED.fiscal_quarter,
                    source_url = EXCLUDED.source_url,
                    source_document_id = EXCLUDED.source_document_id,
                    extracted_data = EXCLUDED.extracted_data,
                    key_metrics = EXCLUDED.key_metrics,
                    narrative = EXCLUDED.narrative,
                    risk_factors = EXCLUDED.risk_factors,
                    guidance = EXCLUDED.guidance,
                    updated_at = NOW()
            """, report.id, report.company_id, report.company_name, report.report_type, report.title,
               report.period_start, report.period_end, report.fiscal_year, report.fiscal_quarter,
               report.source_url, report.source_document_id, json.dumps(report.extracted_data),
               json.dumps(report.key_metrics), report.narrative, report.risk_factors, report.guidance,
               json.dumps(report.metadata))
    
    async def get_report(self, report_id: str) -> Optional["HistoricalReport"]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM historical_reports WHERE id = $1", report_id)
            if not row:
                return None
            return self._row_to_report(row)
    
    async def find_reports(
        self,
        company_id: str = None,
        report_type: str = None,
        start_date: date = None,
        end_date: date = None,
        limit: int = 100
    ) -> list["HistoricalReport"]:
        conditions = []
        params = []
        
        if company_id:
            params.append(company_id)
            conditions.append(f"company_id = ${len(params)}")
        if report_type:
            params.append(report_type)
            conditions.append(f"report_type = ${len(params)}")
        if start_date:
            params.append(start_date)
            conditions.append(f"period_end >= ${len(params)}")
        if end_date:
            params.append(end_date)
            conditions.append(f"period_start <= ${len(params)}")
        
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.append(limit)
        
        query = f"""
            SELECT * FROM historical_reports 
            {where}
            ORDER BY period_end DESC NULLS LAST, created_at DESC
            LIMIT ${len(params)}
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_report(row) for row in rows]
    
    async def store_news(self, news: "HistoricalNews") -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO historical_news (id, company_id, company_name, title, content, url, source, author,
                                            published_at, sentiment, sentiment_label, entities, topics, categories,
                                            relevance_score, language, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    sentiment = EXCLUDED.sentiment,
                    sentiment_label = EXCLUDED.sentiment_label,
                    entities = EXCLUDED.entities,
                    topics = EXCLUDED.topics,
                    categories = EXCLUDED.categories,
                    relevance_score = EXCLUDED.relevance_score
            """, news.id, news.company_id, news.company_name, news.title, news.content, news.url,
               news.source, news.author, news.published_at, news.sentiment, news.sentiment_label,
               json.dumps(news.entities), json.dumps(news.topics), json.dumps(news.categories),
               news.relevance_score, news.language, json.dumps(news.metadata))
    
    async def get_news(
        self,
        company_id: str = None,
        start_date: date = None,
        end_date: date = None,
        limit: int = 100
    ) -> list["HistoricalNews"]:
        conditions = []
        params = []
        
        if company_id:
            params.append(company_id)
            conditions.append(f"company_id = ${len(params)}")
        if start_date:
            params.append(start_date)
            conditions.append(f"published_at >= ${len(params)}")
        if end_date:
            params.append(end_date)
            conditions.append(f"published_at <= ${len(params)}")
        
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.append(limit)
        
        query = f"""
            SELECT * FROM historical_news 
            {where}
            ORDER BY published_at DESC
            LIMIT ${len(params)}
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_news(row) for row in rows]
    
    async def store_filing(self, filing: "HistoricalFiling") -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO historical_filings (id, company_id, company_name, filing_type, accession_number,
                                               filing_date, period_end, fiscal_year, fiscal_quarter,
                                               document_url, document_text, extracted_sections, key_metrics,
                                               risk_factors, management_discussion, exhibits, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                ON CONFLICT (id) DO UPDATE SET
                    company_name = EXCLUDED.company_name,
                    filing_type = EXCLUDED.filing_type,
                    accession_number = EXCLUDED.accession_number,
                    filing_date = EXCLUDED.filing_date,
                    period_end = EXCLUDED.period_end,
                    fiscal_year = EXCLUDED.fiscal_year,
                    fiscal_quarter = EXCLUDED.fiscal_quarter,
                    document_url = EXCLUDED.document_url,
                    document_text = EXCLUDED.document_text,
                    extracted_sections = EXCLUDED.extracted_sections,
                    key_metrics = EXCLUDED.key_metrics,
                    risk_factors = EXCLUDED.risk_factors,
                    management_discussion = EXCLUDED.management_discussion,
                    exhibits = EXCLUDED.exhibits
            """, filing.id, filing.company_id, filing.company_name, filing.filing_type, filing.accession_number,
               filing.filing_date, filing.period_end, filing.fiscal_year, filing.fiscal_quarter,
               filing.document_url, filing.document_text, json.dumps(filing.extracted_sections),
               json.dumps(filing.key_metrics), filing.risk_factors, filing.management_discussion,
               json.dumps(filing.exhibits), json.dumps(filing.metadata))
    
    async def get_filings(
        self,
        company_id: str = None,
        filing_type: str = None,
        start_date: date = None,
        end_date: date = None,
        limit: int = 100
    ) -> list["HistoricalFiling"]:
        conditions = []
        params = []
        
        if company_id:
            params.append(company_id)
            conditions.append(f"company_id = ${len(params)}")
        if filing_type:
            params.append(filing_type)
            conditions.append(f"filing_type = ${len(params)}")
        if start_date:
            params.append(start_date)
            conditions.append(f"filing_date >= ${len(params)}")
        if end_date:
            params.append(end_date)
            conditions.append(f"filing_date <= ${len(params)}")
        
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.append(limit)
        
        query = f"""
            SELECT * FROM historical_filings 
            WHERE {' AND '.join(conditions) if conditions else '1=1'}
            ORDER BY filing_date DESC
            LIMIT ${len(params)}
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_filing(row) for row in rows]
    
    async def store_sentiment(self, sentiment: "HistoricalSentiment") -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO historical_sentiment (id, company_id, company_name, source, source_type,
                                                 sentiment_score, sentiment_label, confidence,
                                                 entity_mentions, key_topics, referenced_date, published_at, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ON CONFLICT (id) DO UPDATE SET
                    sentiment_score = EXCLUDED.sentiment_score,
                    sentiment_label = EXCLUDED.sentiment_label,
                    confidence = EXCLUDED.confidence,
                    entity_mentions = EXCLUDED.entity_mentions,
                    key_topics = EXCLUDED.key_topics
            """, sentiment.id, sentiment.company_id, sentiment.company_name, sentiment.source,
               sentiment.source_type, sentiment.sentiment_score, sentiment.sentiment_label,
               sentiment.confidence, json.dumps(sentiment.entity_mentions),
               json.dumps(sentiment.key_topics), sentiment.referenced_date, sentiment.published_at,
               json.dumps(sentiment.metadata))
    
    async def get_sentiment_history(
        self,
        company_id: str = None,
        start_date: date = None,
        end_date: date = None,
        limit: int = 100
    ) -> list["HistoricalSentiment"]:
        conditions = []
        params = []
        
        if company_id:
            params.append(company_id)
            conditions.append(f"company_id = ${len(params)}")
        if start_date:
            params.append(start_date)
            conditions.append(f"published_at >= ${len(params)}")
        if end_date:
            params.append(end_date)
            conditions.append(f"published_at <= ${len(params)}")
        
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.append(limit)
        
        query = f"""
            SELECT * FROM historical_sentiment 
            {where if conditions else ''}
            ORDER BY published_at DESC
            LIMIT ${len(params)}
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_sentiment(row) for row in rows]
    
    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(
            self.dsn,
            min_size=2,
            max_size=self.pool_size,
        )
        await self._init_schema()
    
    async def disconnect(self) -> None:
        if self.pool:
            await self.pool.close()
    
    def _row_to_report(self, row) -> "HistoricalReport":
        return HistoricalReport(
            id=row["id"],
            company_id=row["company_id"],
            company_name=row["company_name"],
            report_type=row["report_type"],
            title=row["title"],
            period_start=row["period_start"],
            period_end=row["period_end"],
            fiscal_year=row["fiscal_year"],
            fiscal_quarter=row["fiscal_quarter"],
            source_url=row["source_url"],
            source_document_id=row["source_document_id"],
            extracted_data=row["extracted_data"],
            key_metrics=row["key_metrics"],
            narrative=row["narrative"],
            risk_factors=row["risk_factors"],
            guidance=row["guidance"],
            metadata=row["metadata"]
        )
    
    def _row_to_news(self, row) -> "HistoricalNews":
        return HistoricalNews(
            id=row["id"],
            company_id=row["company_id"],
            company_name=row["company_name"],
            title=row["title"],
            content=row["content"],
            url=row["url"],
            source=row["source"],
            author=row["author"],
            published_at=row["published_at"],
            sentiment=row["sentiment"],
            sentiment_label=row["sentiment_label"],
            entities=row["entities"],
            topics=row["topics"],
            categories=row["categories"],
            relevance_score=row["relevance_score"],
            language=row["language"],
            metadata=row["metadata"]
        )
    
    def _row_to_filing(self, row) -> "HistoricalFiling":
        return HistoricalFiling(
            id=row["id"],
            company_id=row["company_id"],
            company_name=row["company_name"],
            filing_type=row["filing_type"],
            accession_number=row["accession_number"],
            filing_date=row["filing_date"],
            period_end=row["period_end"],
            fiscal_year=row["fiscal_year"],
            fiscal_quarter=row["fiscal_quarter"],
            document_url=row["document_url"],
            document_text=row["document_text"],
            extracted_sections=row["extracted_sections"],
            key_metrics=row["key_metrics"],
            risk_factors=row["risk_factors"],
            management_discussion=row["management_discussion"],
            exhibits=row["exhibits"],
            metadata=row["metadata"]
        )
    
    def _row_to_sentiment(self, row) -> "HistoricalSentiment":
        return HistoricalSentiment(
            id=row["id"],
            company_id=row["company_id"],
            company_name=row["company_name"],
            source=row["source"],
            source_type=row["source_type"],
            sentiment_score=row["sentiment_score"],
            sentiment_label=row["sentiment_label"],
            confidence=row["confidence"],
            entity_mentions=row["entity_mentions"],
            key_topics=row["key_topics"],
            referenced_date=row["referenced_date"],
            published_at=row["published_at"],
            metadata=row["metadata"]
        )


# Data classes
@dataclass
class HistoricalReport:
    """A historical financial report (10-K, 10-Q, annual report, etc.)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    company_id: str = ""
    company_name: str = ""
    report_type: str = ""  # 10-K, 10-Q, 8-K, annual_report, etc.
    title: str = ""
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    source_url: Optional[str] = None
    source_document_id: Optional[str] = None
    extracted_data: dict = field(default_factory=dict)
    key_metrics: dict = field(default_factory=dict)
    narrative: str = ""
    risk_factors: list[str] = field(default_factory=list)
    guidance: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class HistoricalNews:
    """A historical news article."""
    id: str = field(default_factory=lambda: str(uuid4()))
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    title: str = ""
    content: str = ""
    url: Optional[str] = None
    source: str = ""
    author: Optional[str] = None
    published_at: datetime = field(default_factory=datetime.utcnow)
    sentiment: Optional[float] = None
    sentiment_label: Optional[str] = None
    entities: list = field(default_factory=list)
    topics: list = field(default_factory=list)
    categories: list = field(default_factory=list)
    relevance_score: Optional[float] = None
    language: str = "en"
    metadata: dict = field(default_factory=dict)


@dataclass
class HistoricalFiling:
    """A historical SEC filing."""
    id: str = field(default_factory=lambda: str(uuid4()))
    company_id: str = ""
    company_name: str = ""
    filing_type: str = ""  # 10-K, 10-Q, 8-K, etc.
    accession_number: Optional[str] = None
    filing_date: date = field(default_factory=date.today)
    period_end: Optional[date] = None
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    document_url: Optional[str] = None
    document_text: str = ""
    extracted_sections: dict = field(default_factory=dict)
    key_metrics: dict = field(default_factory=dict)
    risk_factors: list = field(default_factory=list)
    management_discussion: str = ""
    exhibits: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class HistoricalSentiment:
    """Historical sentiment data point."""
    id: str = field(default_factory=lambda: str(uuid4()))
    company_id: str = ""
    company_name: str = ""
    source: str = ""
    source_type: str = ""
    sentiment_score: float = 0.0
    sentiment_label: str = ""
    confidence: float = 0.0
    entity_mentions: list = field(default_factory=list)
    key_topics: list = field(default_factory=list)
    referenced_date: Optional[date] = None
    published_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)


class HistoricalIntelligence:
    """
    High-level historical intelligence engine.
    Manages storage and retrieval of historical financial data.
    """
    
    def __init__(self, backend: IntelligenceBackend):
        self.backend = backend
    
    async def initialize(self) -> None:
        await self.backend.connect()
    
    async def close(self) -> None:
        await self.backend.disconnect()
    
    # Report management
    async def store_report(self, report: HistoricalReport) -> str:
        await self.backend.store_report(report)
        return report.id
    
    async def get_report(self, report_id: str) -> Optional[HistoricalReport]:
        return await self.backend.get_report(report_id)
    
    async def get_company_reports(
        self,
        company_id: str,
        report_type: Optional[str] = None,
        start_date: date = None,
        end_date: date = None,
        limit: int = 50
    ) -> list[HistoricalReport]:
        return await self.backend.find_reports(
            company_id=company_id,
            report_type=report_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
    
    async def get_company_filings(
        self,
        company_id: str,
        filing_type: Optional[str] = None,
        start_date: date = None,
        end_date: date = None,
        limit: int = 50
    ) -> list[HistoricalFiling]:
        return await self.backend.get_filings(
            company_id=company_id,
            filing_type=filing_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
    
    async def store_filing(self, filing: HistoricalFiling) -> str:
        await self.backend.store_filing(filing)
        return filing.id
    
    async def get_company_news(
        self,
        company_id: str,
        start_date: date = None,
        end_date: date = None,
        limit: int = 100
    ) -> list[HistoricalNews]:
        return await self.backend.get_news(
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
    
    async def store_news(self, news: HistoricalNews) -> str:
        await self.backend.store_news(news)
        return news.id
    
    async def store_sentiment(self, sentiment: HistoricalSentiment) -> str:
        await self.backend.store_sentiment(sentiment)
        return sentiment.id
    
    async def get_sentiment_history(
        self,
        company_id: str = None,
        start_date: date = None,
        end_date: date = None,
        limit: int = 100
    ) -> list[HistoricalSentiment]:
        return await self.backend.get_sentiment_history(
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
    
    # Company evolution tracking
    async def get_company_evolution(
        self,
        company_id: str,
        start_date: date = None,
        end_date: date = None
    ) -> dict:
        """Get comprehensive evolution timeline for a company."""
        
        filings = await self.get_company_filings(company_id)
        news = await self.get_company_news(company_id)
        
        timeline = []
        
        for filing in filings:
            timeline.append({
                "date": filing.filing_date,
                "type": "filing",
                "subtype": filing.filing_type,
                "title": f"{filing.filing_type} filed",
                "source": filing.document_url or "",
                "metadata": {
                    "fiscal_year": filing.fiscal_year,
                    "fiscal_quarter": filing.fiscal_quarter,
                    "accession_number": filing.accession_number
                }
            })
        
        for article in news:
            timeline.append({
                "date": article.published_at.date() if article.published_at else None,
                "type": "news",
                "subtype": "news",
                "title": article.title,
                "source": article.url or article.source,
                "metadata": {
                    "sentiment": article.sentiment,
                    "source": article.source
                }
            })
        
        # Sort by date
        timeline.sort(key=lambda x: x["date"] if x["date"] else date.min)
        
        # Extract key milestones
        milestones = []
        for item in timeline:
            if item["type"] == "filing" and item["subtype"] in ["10-K", "10-Q"]:
                milestones.append({
                    "date": item["date"],
                    "event": f"{item['subtype']} filed for FY{item['metadata'].get('fiscal_year', 'N/A')} Q{item['metadata'].get('fiscal_quarter', 'N/A')}",
                    "type": "filing"
                })
            elif item["type"] == "news" and item.get("metadata", {}).get("sentiment", 0) < -0.5:
                milestones.append({
                    "date": item["date"],
                    "event": f"Negative news: {item['title'][:100]}",
                    "type": "risk"
                })
        
        return {
            "company_id": company_id,
            "timeline": timeline,
            "milestones": milestones,
            "total_filings": len([t for t in timeline if t["type"] == "filing"]),
            "total_news": len([t for t in timeline if t["type"] == "news"]),
            "date_range": {
                "start": min((t["date"] for t in timeline if t["date"]), default=None),
                "end": max((t["date"] for t in timeline if t["date"]), default=None)
            }
        }
    
    # Trend analysis
    async def analyze_metric_trends(
        self,
        company_id: str,
        metric_name: str,
        years: int = 5
    ) -> dict:
        """Analyze trends for a specific metric over time."""
        
        reports = await self.get_company_reports(
            company_id=company_id,
            start_date=date.today() - timedelta(days=365*5),
            limit=50
        )
        
        values = []
        dates = []
        
        for report in reports:
            if metric_name in report.key_metrics:
                value = report.key_metrics[metric_name]
                if isinstance(value, (int, float)):
                    values.append(float(value))
                    dates.append(report.period_end or date.today())
        
        if len(values) < 2:
            return {"error": "Insufficient data points"}
        
        # Sort by date
        sorted_pairs = sorted(zip(dates, values))
        dates = [d for d, _ in sorted_pairs]
        values = [v for _, v in sorted_pairs]
        
        # Calculate trend
        x = np.arange(len(values))
        y = np.array(values)
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        # Calculate growth rates
        growth_rates = []
        for i in range(1, len(values)):
            if values[i-1] != 0:
                growth = (values[i] - values[i-1]) / values[i-1]
                growth_rates.append(growth)
        
        return {
            "metric": metric_name,
            "company_id": company_id,
            "data_points": len(values),
            "date_range": {"start": dates[0], "end": dates[-1]},
            "values": list(zip(dates, values)),
            "trend": {
                "slope": float(slope),
                "r_squared": float(r_value**2),
                "p_value": float(p_value),
                "direction": "increasing" if slope > 0 else "decreasing",
                "significant": p_value < 0.05
            },
            "growth_rates": {
                "mean": float(np.mean(growth_rates)) if growth_rates else 0,
                "median": float(np.median(growth_rates)) if growth_rates else 0,
                "std": float(np.std(growth_rates)) if growth_rates else 0,
                "cagr": float((values[-1]/values[0])**(1/(len(values)-1)) - 1) if len(values) > 1 and values[0] > 0 else 0
            },
            "current_value": values[-1],
            "current_vs_avg": float((values[-1] - np.mean(values)) / np.mean(values)) if np.mean(values) != 0 else 0
        }
    
    # Peer comparison
    async def compare_companies(
        self,
        company_ids: list[str],
        metrics: list[str],
        years: int = 5
    ) -> dict:
        """Compare multiple companies on specified metrics."""
        
        comparison = {
            "companies": company_ids,
            "metrics": metrics,
            "period_years": years,
            "comparison": {}
        }
        
        for metric in metrics:
            metric_data = {}
            for cid in company_ids:
                trend = await self.analyze_metric_trends(cid, metric, years)
                if "error" not in trend:
                    metric_data[cid] = trend
            
            comparison["comparison"][metric] = metric_data
        
        # Add relative rankings
        for metric in metrics:
            companies_with_data = {cid: data for cid, data in comparison["comparison"][metric].items() 
                                  if "current_value" in data}
            if companies_with_data:
                sorted_companies = sorted(
                    companies_with_data.items(),
                    key=lambda x: x[1]["current_value"],
                    reverse=True
                )
                comparison["comparison"][metric]["ranking"] = [
                    {"company": cid, "value": data["current_value"], "rank": i+1}
                    for i, (cid, data) in enumerate(sorted_companies)
                ]
        
        return comparison
    
    # Company similarity
    async def find_similar_companies(
        self,
        company_id: str,
        metrics: list[str] = None,
        top_k: int = 10
    ) -> list[dict]:
        """Find companies similar to the given company based on metrics."""
        if metrics is None:
            metrics = ["revenue", "net_income", "total_assets", "employees"]
        
        # Get target company profile
        target_profile = {}
        for metric in metrics:
            trend = await self.analyze_metric_trends(company_id, metric, 3)
            if "error" not in trend:
                target_profile[metric] = trend.get("current_value", 0)
        
        # Compare with other companies (would need a list of companies to compare)
        # This is a placeholder - would need a company registry
        similar = []
        return similar


# Factory
async def create_historical_intelligence(
    backend_type: str = "postgres",
    **kwargs
) -> HistoricalIntelligence:
    """Factory function to create HistoricalIntelligence with specified backend."""
    if backend_type == "postgres":
        backend = PostgresIntelligenceBackend(
            dsn=kwargs.get("dsn", "postgresql://localhost/financial_intelligence"),
            pool_size=kwargs.get("pool_size", 10)
        )
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")
    
    hi = HistoricalIntelligence(backend)
    await hi.initialize()
    return hi


# Export
__all__ = [
    "IntelligenceBackend",
    "PostgresIntelligenceBackend",
    "HistoricalReport",
    "HistoricalNews",
    "HistoricalFiling",
    "HistoricalSentiment",
    "HistoricalIntelligence",
    "PostgresIntelligenceBackend",
    "create_historical_intelligence",
]