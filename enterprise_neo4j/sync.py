"""
Graph Synchronization - Syncs data between PostgreSQL and Neo4j.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from .client import get_neo4j_client
from .models import GraphEntity, GraphRelationship, EntityType, RelationshipType
from database.session import get_session
from database.models import Company, Report, NewsArticle, Person, Product

logger = logging.getLogger(__name__)


class SyncDirection(str, Enum):
    """Direction of synchronization."""
    POSTGRES_TO_NEO4J = "postgres_to_neo4j"
    NEO4J_TO_POSTGRES = "neo4j_to_postgres"
    BIDIRECTIONAL = "bidirectional"


class SyncStatus(str, Enum):
    """Status of a sync operation."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class SyncStats:
    """Statistics for a sync operation."""
    entities_created: int = 0
    entities_updated: int = 0
    entities_deleted: int = 0
    relationships_created: int = 0
    relationships_updated: int = 0
    relationships_deleted: int = 0
    errors: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities_created": self.entities_created,
            "entities_updated": self.entities_updated,
            "entities_deleted": self.entities_deleted,
            "relationships_created": self.relationships_created,
            "relationships_updated": self.relationships_updated,
            "relationships_deleted": self.relationships_deleted,
            "errors": self.errors,
            "duration_ms": self.duration_ms,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }


@dataclass
class SyncConfig:
    """Configuration for graph synchronization."""
    batch_size: int = 100
    max_concurrent_batches: int = 5
    sync_interval_minutes: int = 15
    full_sync_on_startup: bool = True
    incremental_sync_enabled: bool = True
    entity_types: List[EntityType] = field(default_factory=lambda: list(EntityType))
    relationship_types: List[RelationshipType] = field(default_factory=lambda: list(RelationshipType))
    conflict_resolution: str = "neo4j_wins"  # "postgres_wins", "neo4j_wins", "latest_wins"
    enable_deletes: bool = True
    dry_run: bool = False


class GraphSynchronizer:
    """
    Synchronizes data between PostgreSQL and Neo4j.
    Handles incremental and full syncs with conflict resolution.
    """
    
    def __init__(self, config: Optional[SyncConfig] = None):
        self.config = config or SyncConfig()
        self.neo4j = get_neo4j_client()
        self._running = False
        self._sync_task: Optional[asyncio.Task] = None
        self._last_sync: Optional[datetime] = None
        self._stats = SyncStats()
    
    async def initialize(self) -> None:
        """Initialize the synchronizer and ensure indexes exist."""
        await self._ensure_indexes()
        if self.config.full_sync_on_startup:
            await self.full_sync()
        else:
            await self.incremental_sync()
        
        if self.config.incremental_sync_enabled:
            self._start_scheduler()
    
    async def _ensure_indexes(self) -> None:
        """Ensure required indexes exist in Neo4j."""
        indexes = [
            "CREATE INDEX entity_id_index IF NOT EXISTS FOR (n:Entity) ON (n.id)",
            "CREATE INDEX entity_type_index IF NOT EXISTS FOR (n:Entity) ON (n.type)",
            "CREATE INDEX company_ticker_index IF NOT EXISTS FOR (n:Company) ON (n.ticker)",
            "CREATE INDEX person_name_index IF NOT EXISTS FOR (n:Person) ON (n.name)",
            "CREATE INDEX relationship_type_index IF NOT EXISTS FOR ()-[r:RELATIONSHIP]-() ON (r.type)",
            "CREATE INDEX entity_created_at_index IF NOT EXISTS FOR (n:Entity) ON (n.created_at)",
            "CREATE INDEX updated_at_index IF NOT EXISTS FOR (n:Entity) ON (n.updated_at)",
        ]
        
        for index_query in indexes:
            try:
                await self.neo4j.execute_query(index_query)
            except Exception as e:
                logger.warning(f"Index creation failed (may already exist): {e}")
    
    async def full_sync(self) -> SyncStats:
        """Perform a full synchronization from PostgreSQL to Neo4j."""
        self._stats = SyncStats(start_time=datetime.utcnow())
        logger.info("Starting full sync from PostgreSQL to Neo4j")
        
        try:
            # Sync entities
            await self._sync_companies()
            await self._sync_people()
            await self._sync_products()
            await self._sync_sectors_industries()
            await self._sync_market_indices()
            await self._sync_financial_metrics()
            await self._sync_news_articles()
            await self._sync_earnings_calls()
            await self._sync_sec_filings()
            await self._sync_analyst_reports()
            
            # Sync relationships
            await self._sync_company_relationships()
            await self._sync_person_relationships()
            await self._sync_product_relationships()
            await self._sync_financial_relationships()
            await self._sync_event_relationships()
            
            self._stats.end_time = datetime.utcnow()
            self._stats.duration_ms = (self._stats.end_time - self._stats.start_time).total_seconds() * 1000
            self._last_sync = self._stats.end_time
            
            logger.info(f"Full sync completed: {self._stats.to_dict()}")
            return self._stats
            
        except Exception as e:
            logger.error(f"Full sync failed: {e}")
            self._stats.errors += 1
            self._stats.end_time = datetime.utcnow()
            raise
    
    async def incremental_sync(self) -> SyncStats:
        """Perform incremental synchronization based on last sync time."""
        self._stats = SyncStats(start_time=datetime.utcnow())
        since = self._last_sync or (datetime.utcnow() - timedelta(hours=24))
        
        logger.info(f"Starting incremental sync since {since}")
        
        try:
            # Sync updated entities
            await self._sync_companies(since=since)
            await self._sync_people(since=since)
            await self._sync_products(since=since)
            await self._sync_news_articles(since=since)
            await self._sync_earnings_calls(since=since)
            await self._sync_sec_filings(since=since)
            await self._sync_analyst_reports(since=since)
            
            # Sync updated relationships
            await self._sync_company_relationships(since=since)
            await self._sync_person_relationships(since=since)
            
            self._stats.end_time = datetime.utcnow()
            self._stats.duration_ms = (self._stats.end_time - self._stats.start_time).total_seconds() * 1000
            self._last_sync = self._stats.end_time
            
            logger.info(f"Incremental sync completed: {self._stats.to_dict()}")
            return self._stats
            
        except Exception as e:
            logger.error(f"Incremental sync failed: {e}")
            self._stats.errors += 1
            self._stats.end_time = datetime.utcnow()
            raise
    
    def _start_scheduler(self) -> None:
        """Start the periodic sync scheduler."""
        if self._sync_task and not self._sync_task.done():
            return
        
        self._running = True
        self._sync_task = asyncio.create_task(self._sync_loop())
        logger.info(f"Incremental sync scheduler started (every {self.config.sync_interval_minutes} minutes)")
    
    async def _sync_loop(self) -> None:
        """Background sync loop."""
        while self._running:
            try:
                await asyncio.sleep(self.config.sync_interval_minutes * 60)
                if self._running:
                    await self.incremental_sync()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduled sync failed: {e}")
                await asyncio.sleep(60)  # Back off on error
    
    async def stop(self) -> None:
        """Stop the synchronizer."""
        self._running = False
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        logger.info("Synchronizer stopped")
    
    # Entity sync methods
    
    async def _sync_companies(self, since: Optional[datetime] = None) -> None:
        """Sync companies from PostgreSQL to Neo4j."""
        query = "SELECT * FROM companies"
        params = []
        
        if since:
            query += " WHERE updated_at > %s"
            params.append(since)
        
        async with get_session() as session:
            result = await session.execute(query, params)
            companies = result.fetchall()
        
        for company in companies:
            await self._upsert_company(company)
    
    async def _upsert_company(self, company) -> None:
        """Upsert a company entity in Neo4j."""
        entity = GraphEntity.create(
            type=EntityType.COMPANY,
            properties={
                "id": str(company.id),
                "ticker": company.ticker,
                "name": company.name,
                "cik": company.cik,
                "sector": company.sector,
                "industry": company.industry,
                "market_cap": float(company.market_cap) if company.market_cap else None,
                "description": company.description,
                "website": company.website,
                "headquarters": company.headquarters,
                "employees": company.employees,
                "founded_year": company.founded_year,
                "exchange": company.exchange,
                "currency": company.currency,
                "is_active": company.is_active,
                "created_at": company.created_at.isoformat() if company.created_at else None,
                "updated_at": company.updated_at.isoformat() if company.updated_at else None,
            },
            source="postgresql",
            confidence=1.0
        )
        
        cypher = """
        MERGE (c:Company {id: $id})
        SET c += $properties,
            c.type = $type,
            c.updated_at = datetime($updated_at),
            c.version = coalesce(c.version, 0) + 1
        RETURN c
        """
        
        if not self.config.dry_run:
            await self.neo4j.execute_write(cypher, entity.to_cypher_params())
        
        if entity.id in [str(c.id) for c in companies]:  # simplified check
            self._stats.entities_updated += 1
        else:
            self._stats.entities_created += 1
    
    async def _sync_people(self, since: Optional[datetime] = None) -> None:
        """Sync people from PostgreSQL to Neo4j."""
        query = "SELECT * FROM people"
        params = []
        if since:
            query += " WHERE updated_at > %s"
            params.append(since)
        
        async with get_session() as session:
            result = await session.execute(query, params)
            people = result.fetchall()
        
        for person in people:
            entity = GraphEntity.create(
                type=EntityType.PERSON,
                properties={
                    "id": str(person.id),
                    "name": person.name,
                    "role": person.role,
                    "company_id": str(person.company_id) if person.company_id else None,
                    "bio": person.bio,
                    "linkedin": person.linkedin,
                    "twitter": person.twitter,
                    "created_at": person.created_at.isoformat() if person.created_at else None,
                    "updated_at": person.updated_at.isoformat() if person.updated_at else None,
                },
                source="postgresql"
            )
            
            cypher = """
            MERGE (p:Person {id: $id})
            SET p += $properties,
                p.type = $type,
                p.updated_at = datetime($updated_at),
                p.version = coalesce(p.version, 0) + 1
            RETURN p
            """
            
            if not self.config.dry_run:
                await self.neo4j.execute_write(cypher, entity.to_cypher_params())
            self._stats.entities_created += 1
    
    async def _sync_products(self, since: Optional[datetime] = None) -> None:
        """Sync products from PostgreSQL to Neo4j."""
        query = "SELECT * FROM products"
        params = []
        if since:
            query += " WHERE updated_at > %s"
            params.append(since)
        
        async with get_session() as session:
            result = await session.execute(query, params)
            products = result.fetchall()
        
        for product in products:
            entity = GraphEntity.create(
                type=EntityType.PRODUCT,
                properties={
                    "id": str(product.id),
                    "name": product.name,
                    "company_id": str(product.company_id),
                    "description": product.description,
                    "category": product.category,
                    "revenue": float(product.revenue) if product.revenue else None,
                    "created_at": product.created_at.isoformat() if product.created_at else None,
                    "updated_at": product.updated_at.isoformat() if product.updated_at else None,
                },
                source="postgresql"
            )
            
            cypher = """
            MERGE (p:Product {id: $id})
            SET p += $properties,
                p.type = $type,
                p.updated_at = datetime($updated_at),
                p.version = coalesce(p.version, 0) + 1
            RETURN p
            """
            
            if not self.config.dry_run:
                await self.neo4j.execute_write(cypher, entity.to_cypher_params())
            self._stats.entities_created += 1
    
    async def _sync_sectors_industries(self) -> None:
        """Sync sectors and industries."""
        # Sync unique sectors
        async with get_session() as session:
            sectors = await session.execute("SELECT DISTINCT sector FROM companies WHERE sector IS NOT NULL")
            industries = await session.execute("SELECT DISTINCT industry FROM companies WHERE industry IS NOT NULL")
        
        for sector_row in sectors.fetchall():
            entity = GraphEntity.create(
                type=EntityType.SECTOR,
                properties={"id": f"sector_{sector_row.sector.lower().replace(' ', '_')}", "name": sector_row.sector}
            )
            cypher = "MERGE (s:Sector {id: $id}) SET s += $properties RETURN s"
            if not self.config.dry_run:
                await self.neo4j.execute_write(cypher, entity.to_cypher_params())
        
        for industry_row in industries.fetchall():
            entity = GraphEntity.create(
                type=EntityType.INDUSTRY,
                properties={"id": f"industry_{industry_row.industry.lower().replace(' ', '_')}", "name": industry_row.industry}
            )
            cypher = "MERGE (i:Industry {id: $id}) SET i += $properties RETURN i"
            if not self.config.dry_run:
                await self.neo4j.execute_write(cypher, entity.to_cypher_params())
    
    async def _sync_market_indices(self) -> None:
        """Sync market indices."""
        # This would sync from a market_indices table
        pass
    
    async def _sync_financial_metrics(self, since: Optional[datetime] = None) -> None:
        """Sync financial metrics as entities."""
        query = "SELECT * FROM financial_metrics"
        params = []
        if since:
            query += " WHERE updated_at > %s"
            params.append(since)
        
        async with get_session() as session:
            result = await session.execute(query, params)
            metrics = result.fetchall()
        
        for metric in metrics:
            entity = GraphEntity.create(
                type=EntityType.FINANCIAL_METRIC,
                properties={
                    "id": str(metric.id),
                    "company_id": str(metric.company_id),
                    "metric_name": metric.metric_name,
                    "value": float(metric.value) if metric.value else None,
                    "period": metric.period,
                    "fiscal_year": metric.fiscal_year,
                    "fiscal_quarter": metric.fiscal_quarter,
                    "unit": metric.unit,
                    "created_at": metric.created_at.isoformat() if metric.created_at else None,
                    "updated_at": metric.updated_at.isoformat() if metric.updated_at else None,
                },
                source="postgresql"
            )
            
            cypher = """
            MERGE (m:FinancialMetric {id: $id})
            SET m += $properties,
                m.type = $type,
                m.updated_at = datetime($updated_at),
                m.version = coalesce(m.version, 0) + 1
            RETURN m
            """
            
            if not self.config.dry_run:
                await self.neo4j.execute_write(cypher, entity.to_cypher_params())
            self._stats.entities_created += 1
    
    async def _sync_news_articles(self, since: Optional[datetime] = None) -> None:
        """Sync news articles."""
        query = "SELECT * FROM news_articles"
        params = []
        if since:
            query += " WHERE updated_at > %s"
            params.append(since)
        
        async with get_session() as session:
            result = await session.execute(query, params)
            articles = result.fetchall()
        
        for article in articles:
            entity = GraphEntity.create(
                type=EntityType.NEWS_ARTICLE,
                properties={
                    "id": str(article.id),
                    "title": article.title,
                    "content": article.content,
                    "source": article.source,
                    "url": article.url,
                    "published_at": article.published_at.isoformat() if article.published_at else None,
                    "sentiment_score": float(article.sentiment_score) if article.sentiment_score else None,
                    "entities_mentioned": article.entities_mentioned,
                    "created_at": article.created_at.isoformat() if article.created_at else None,
                    "updated_at": article.updated_at.isoformat() if article.updated_at else None,
                },
                source="postgresql"
            )
            
            cypher = """
            MERGE (n:NewsArticle {id: $id})
            SET n += $properties,
                n.type = $type,
                n.updated_at = datetime($updated_at),
                n.version = coalesce(n.version, 0) + 1
            RETURN n
            """
            
            if not self.config.dry_run:
                await self.neo4j.execute_write(cypher, entity.to_cypher_params())
            self._stats.entities_created += 1
    
    async def _sync_earnings_calls(self, since: Optional[datetime] = None) -> None:
        """Sync earnings calls."""
        query = "SELECT * FROM earnings_calls"
        params = []
        if since:
            query += " WHERE updated_at > %s"
            params.append(since)
        
        async with get_session() as session:
            result = await session.execute(query, params)
            calls = result.fetchall()
        
        for call in calls:
            entity = GraphEntity.create(
                type=EntityType.EARNINGS_CALL,
                properties={
                    "id": str(call.id),
                    "company_id": str(call.company_id),
                    "transcript": call.transcript,
                    "quarter": call.quarter,
                    "year": call.year,
                    "date": call.date.isoformat() if call.date else None,
                    "participants": call.participants,
                    "created_at": call.created_at.isoformat() if call.created_at else None,
                    "updated_at": call.updated_at.isoformat() if call.updated_at else None,
                },
                source="postgresql"
            )
            
            cypher = "MERGE (e:EarningsCall {id: $id}) SET e += $properties RETURN e"
            if not self.config.dry_run:
                await self.neo4j.execute_write(cypher, entity.to_cypher_params())
            self._stats.entities_created += 1
    
    async def _sync_sec_filings(self, since: Optional[datetime] = None) -> None:
        """Sync SEC filings."""
        query = "SELECT * FROM sec_filings"
        params = []
        if since:
            query += " WHERE updated_at > %s"
            params.append(since)
        
        async with get_session() as session:
            result = await session.execute(query, params)
            filings = result.fetchall()
        
        for filing in filings:
            entity = GraphEntity.create(
                type=EntityType.SEC_FILING,
                properties={
                    "id": str(filing.id),
                    "company_id": str(filing.company_id),
                    "form_type": filing.form_type,
                    "filing_date": filing.filing_date.isoformat() if filing.filing_date else None,
                    "accession_number": filing.accession_number,
                    "content": filing.content,
                    "created_at": filing.created_at.isoformat() if filing.created_at else None,
                    "updated_at": filing.updated_at.isoformat() if filing.updated_at else None,
                },
                source="postgresql"
            )
            
            cypher = "MERGE (s:SECFiling {id: $id}) SET s += $properties RETURN s"
            if not self.config.dry_run:
                await self.neo4j.execute_write(cypher, entity.to_cypher_params())
            self._stats.entities_created += 1
    
    async def _sync_analyst_reports(self, since: Optional[datetime] = None) -> None:
        """Sync analyst reports."""
        query = "SELECT * FROM analyst_reports"
        params = []
        if since:
            query += " WHERE updated_at > %s"
            params.append(since)
        
        async with get_session() as session:
            result = await session.execute(query, params)
            reports = result.fetchall()
        
        for report in reports:
            entity = GraphEntity.create(
                type=EntityType.ANALYST_REPORT,
                properties={
                    "id": str(report.id),
                    "company_id": str(report.company_id),
                    "analyst": report.analyst,
                    "firm": report.firm,
                    "rating": report.rating,
                    "target_price": float(report.target_price) if report.target_price else None,
                    "summary": report.summary,
                    "report_date": report.report_date.isoformat() if report.report_date else None,
                    "created_at": report.created_at.isoformat() if report.created_at else None,
                    "updated_at": report.updated_at.isoformat() if report.updated_at else None,
                },
                source="postgresql"
            )
            
            cypher = "MERGE (a:AnalystReport {id: $id}) SET a += $properties RETURN a"
            if not self.config.dry_run:
                await self.neo4j.execute_write(cypher, entity.to_cypher_params())
            self._stats.entities_created += 1
    
    # Relationship sync methods
    
    async def _sync_company_relationships(self, since: Optional[datetime] = None) -> None:
        """Sync company relationships (competitors, suppliers, etc.)."""
        # This would come from a company_relationships table
        # For now, create basic sector/industry relationships
        cypher = """
        MATCH (c:Company)
        WHERE c.sector IS NOT NULL
        MATCH (s:Sector {name: c.sector})
        MERGE (c)-[r:OPERATES_IN]->(s)
        SET r.updated_at = datetime()
        RETURN count(r)
        """
        if not self.config.dry_run:
            result = await self.neo4j.execute_write(cypher)
            self._stats.relationships_created += result[0].get("count", 0) if result else 0
        
        cypher = """
        MATCH (c:Company)
        WHERE c.industry IS NOT NULL
        MATCH (i:Industry {name: c.industry})
        MERGE (c)-[r:OPERATES_IN]->(i)
        SET r.updated_at = datetime()
        RETURN count(r)
        """
        if not self.config.dry_run:
            result = await self.neo4j.execute_write(cypher)
            self._stats.relationships_created += result[0].get("count", 0) if result else 0
    
    async def _sync_person_relationships(self, since: Optional[datetime] = None) -> None:
        """Sync person relationships (works for, board member, etc.)."""
        cypher = """
        MATCH (p:Person)
        WHERE p.company_id IS NOT NULL
        MATCH (c:Company {id: p.company_id})
        MERGE (p)-[r:WORKS_FOR]->(c)
        SET r.updated_at = datetime(),
            r.role = p.role
        RETURN count(r)
        """
        if not self.config.dry_run:
            result = await self.neo4j.execute_write(cypher)
            self._stats.relationships_created += result[0].get("count", 0) if result else 0
    
    async def _sync_product_relationships(self, since: Optional[datetime] = None) -> None:
        """Sync product relationships."""
        cypher = """
        MATCH (p:Product)
        WHERE p.company_id IS NOT NULL
        MATCH (c:Company {id: p.company_id})
        MERGE (c)-[r:PRODUCES]->(p)
        SET r.updated_at = datetime()
        RETURN count(r)
        """
        if not self.config.dry_run:
            result = await self.neo4j.execute_write(cypher)
            self._stats.relationships_created += result[0].get("count", 0) if result else 0
    
    async def _sync_financial_relationships(self, since: Optional[datetime] = None) -> None:
        """Sync financial metric relationships."""
        cypher = """
        MATCH (m:FinancialMetric)
        WHERE m.company_id IS NOT NULL
        MATCH (c:Company {id: m.company_id})
        MERGE (c)-[r:HAS_METRIC]->(m)
        SET r.updated_at = datetime(),
            r.period = m.period,
            r.fiscal_year = m.fiscal_year,
            r.fiscal_quarter = m.fiscal_quarter
        RETURN count(r)
        """
        if not self.config.dry_run:
            result = await self.neo4j.execute_write(cypher)
            self._stats.relationships_created += result[0].get("count", 0) if result else 0
    
    async def _sync_event_relationships(self, since: Optional[datetime] = None) -> None:
        """Sync event relationships (news mentions, etc.)."""
        # News -> Company mentions
        cypher = """
        MATCH (n:NewsArticle)
        WHERE n.entities_mentioned IS NOT NULL
        UNWIND n.entities_mentioned as entity
        MATCH (c:Company {ticker: entity.ticker})
        MERGE (n)-[r:MENTIONS]->(c)
        SET r.updated_at = datetime(),
            r.sentiment = entity.sentiment,
            r.relevance = entity.relevance
        RETURN count(r)
        """
        if not self.config.dry_run:
            result = await self.neo4j.execute_write(cypher)
            self._stats.relationships_created += result[0].get("count", 0) if result else 0
    
    def get_stats(self) -> SyncStats:
        """Get current sync statistics."""
        return self._stats
    
    def get_last_sync_time(self) -> Optional[datetime]:
        """Get the timestamp of the last successful sync."""
        return self._last_sync


# Global synchronizer instance
_graph_synchronizer: Optional[GraphSynchronizer] = None


def get_graph_synchronizer(config: Optional[SyncConfig] = None) -> GraphSynchronizer:
    """Get or create the global graph synchronizer."""
    global _graph_synchronizer
    if _graph_synchronizer is None:
        _graph_synchronizer = GraphSynchronizer(config)
    return _graph_synchronizer


async def close_graph_synchronizer() -> None:
    """Close the global graph synchronizer."""
    global _graph_synchronizer
    if _graph_synchronizer:
        await _graph_synchronizer.stop()
        _graph_synchronizer = None