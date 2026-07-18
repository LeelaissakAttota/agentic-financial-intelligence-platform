"""
Knowledge Graph Module - Phase 5: Knowledge Persistence & Advanced Analytics

Provides graph persistence for financial entities and relationships using Neo4j/PostgreSQL.
Enables cross-agent knowledge sharing through graph structure.
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
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

import asyncpg
import networkx as nx

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    """Types of nodes in the knowledge graph."""
    COMPANY = "company"
    PERSON = "person"
    PRODUCT = "product"
    INDUSTRY = "industry"
    SECTOR = "sector"
    COUNTRY = "country"
    EVENT = "event"
    FILING = "filing"
    METRIC = "metric"
    NEWS = "news"
    PATTERN = "pattern"
    PORTFOLIO = "portfolio"
    ALERT = "alert"


class RelationshipType(str, Enum):
    """Types of relationships in the knowledge graph."""
    # Company relationships
    HAS_TICKER = "HAS_TICKER"
    LISTED_ON = "LISTED_ON"
    CEO_OF = "CEO_OF"
    CFO_OF = "CFO_OF"
    EXECUTIVE_OF = "EXECUTIVE_OF"
    BOARD_MEMBER_OF = "BOARD_MEMBER_OF"
    OWNS = "OWNS"
    OWNED_BY = "OWNED_BY"
    SUBSIDIARY_OF = "SUBSIDIARY_OF"
    PARENT_OF = "PARENT_OF"
    ACQUIRED = "ACQUIRED"
    ACQUIRED_BY = "ACQUIRED_BY"
    MERGED_WITH = "MERGED_WITH"
    COMPETES_WITH = "COMPETES_WITH"
    PARTNERS_WITH = "PARTNERS_WITH"
    SUPPLIES = "SUPPLIES"
    SUPPLIED_BY = "SUPPLIED_BY"
    CUSTOMER_OF = "CUSTOMER_OF"
    VENDOR_OF = "VENDOR_OF"
    INVESTS_IN = "INVESTS_IN"
    INVESTED_BY = "INVESTED_BY"
    
    # Industry/Sector
    BELONGS_TO = "BELONGS_TO"
    OPERATES_IN = "OPERATES_IN"
    HEADQUARTERED_IN = "HEADQUARTERED_IN"
    INCORPORATED_IN = "INCORPORATED_IN"
    
    # Filings/Reports
    FILED = "FILED"
    REPORTED_IN = "REPORTED_IN"
    CONTAINS = "CONTAINS"
    MENTIONS = "MENTIONS"
    REFERENCES = "REFERENCES"
    
    # Metrics
    HAS_METRIC = "HAS_METRIC"
    REPORTS = "REPORTS"
    DERIVED_FROM = "DERIVED_FROM"
    
    # Events/News
    TRIGGERED = "TRIGGERED"
    CAUSED_BY = "CAUSED_BY"
    RELATED_TO = "RELATED_TO"
    FOLLOWS = "FOLLOWS"
    PRECEDES = "PRECEDES"
    
    # Patterns/Analytics
    DETECTED_IN = "DETECTED_IN"
    PREDICTS = "PREDICTS"
    CORRELATES_WITH = "CORRELATES_WITH"
    
    # Portfolio
    HOLDS = "HOLDS"
    HELD_BY = "HELD_BY"
    ALERT_FOR = "ALERT_FOR"


@dataclass
class GraphNode:
    """A node in the knowledge graph."""
    id: str = field(default_factory=lambda: str(uuid4()))
    node_type: NodeType = NodeType.COMPANY
    name: str = ""
    label: str = ""
    properties: dict = field(default_factory=dict)
    # Metadata
    confidence: float = 1.0
    source: str = "system"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True
    version: int = 1
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "name": self.name,
            "label": self.label,
            "properties": self.properties,
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_active": self.is_active,
            "version": self.version
        }


@dataclass
class GraphEdge:
    """An edge/relationship in the knowledge graph."""
    id: str = field(default_factory=lambda: str(uuid4()))
    source_id: str = ""
    target_id: str = ""
    relationship_type: RelationshipType = RelationshipType.RELATED_TO
    properties: dict = field(default_factory=dict)
    # Metadata
    confidence: float = 1.0
    weight: float = 1.0
    source: str = "system"
    evidence: list[str] = field(default_factory=list)  # Document IDs supporting this edge
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type.value,
            "properties": self.properties,
            "confidence": self.confidence,
            "weight": self.weight,
            "source": self.source,
            "evidence": self.evidence,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_active": self.is_active,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None
        }


class GraphBackend(ABC):
    """Abstract backend for knowledge graph storage."""
    
    @abstractmethod
    async def connect(self) -> None:
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        pass
    
    # Node operations
    @abstractmethod
    async def create_node(self, node: GraphNode) -> str:
        pass
    
    @abstractmethod
    async def get_node(self, node_id: str) -> Optional[GraphNode]:
        pass
    
    @abstractmethod
    async def update_node(self, node: GraphNode) -> None:
        pass
    
    @abstractmethod
    async def delete_node(self, node_id: str) -> bool:
        pass
    
    @abstractmethod
    async def find_nodes(
        self,
        node_type: NodeType = None,
        name: str = None,
        properties: dict = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[GraphNode]:
        pass
    
    # Edge operations
    @abstractmethod
    async def create_edge(self, edge: GraphEdge) -> str:
        pass
    
    @abstractmethod
    async def get_edge(self, edge_id: str) -> Optional[GraphEdge]:
        pass
    
    @abstractmethod
    async def update_edge(self, edge: GraphEdge) -> None:
        pass
    
    @abstractmethod
    async def delete_edge(self, edge_id: str) -> bool:
        pass
    
    @abstractmethod
    async def find_edges(
        self,
        source_id: str = None,
        target_id: str = None,
        relationship_type: RelationshipType = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[GraphEdge]:
        pass
    
    # Graph operations
    @abstractmethod
    async def get_neighbors(
        self,
        node_id: str,
        relationship_type: RelationshipType = None,
        direction: str = "both"  # incoming, outgoing, both
    ) -> list[tuple[GraphEdge, GraphNode]]:
        pass
    
    @abstractmethod
    async def get_subgraph(
        self,
        node_ids: list[str],
        max_depth: int = 1
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        pass
    
    @abstractmethod
    async def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 6,
        relationship_types: list[RelationshipType] = None
    ) -> list[GraphEdge]:
        pass
    
    @abstractmethod
    async def get_stats(self) -> dict:
        pass


class PostgresGraphBackend(GraphBackend):
    """PostgreSQL backend for knowledge graph storage."""
    
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
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    label TEXT,
                    properties JSONB DEFAULT '{}',
                    confidence REAL NOT NULL DEFAULT 1.0,
                    source TEXT NOT NULL DEFAULT 'system',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    version INTEGER NOT NULL DEFAULT 1
                );
                
                CREATE INDEX IF NOT EXISTS idx_nodes_type ON graph_nodes(node_type);
                CREATE INDEX IF NOT EXISTS idx_nodes_name ON graph_nodes(name);
                CREATE INDEX IF NOT EXISTS idx_nodes_active ON graph_nodes(is_active);
                
                CREATE TABLE IF NOT EXISTS graph_edges (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
                    target_id TEXT NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
                    relationship_type TEXT NOT NULL,
                    properties JSONB DEFAULT '{}',
                    confidence REAL NOT NULL DEFAULT 1.0,
                    weight REAL NOT NULL DEFAULT 1.0,
                    source TEXT NOT NULL DEFAULT 'system',
                    evidence TEXT[] DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    valid_from DATE,
                    valid_until DATE,
                    UNIQUE(source_id, target_id, relationship_type)
                );
                
                CREATE INDEX IF NOT EXISTS idx_edges_source ON graph_edges(source_id);
                CREATE INDEX IF NOT EXISTS idx_edges_target ON graph_edges(target_id);
                CREATE INDEX IF NOT EXISTS idx_edges_type ON graph_edges(relationship_type);
                CREATE INDEX IF NOT EXISTS idx_edges_active ON graph_edges(is_active);
                CREATE INDEX IF NOT EXISTS idx_edges_source_target ON graph_edges(source_id, target_id);
                
                CREATE TABLE IF NOT EXISTS graph_versions (
                    id TEXT PRIMARY KEY,
                    entity_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,  -- 'node' or 'edge'
                    version INTEGER NOT NULL,
                    snapshot JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    created_by TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_versions_entity ON graph_versions(entity_id, entity_type);
            """)
    
    async def create_node(self, node: GraphNode) -> str:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO graph_nodes (id, node_type, name, label, properties, confidence, source, created_at, updated_at, is_active, version)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (id) DO UPDATE SET
                    node_type = EXCLUDED.node_type,
                    name = EXCLUDED.name,
                    label = EXCLUDED.label,
                    properties = EXCLUDED.properties,
                    confidence = EXCLUDED.confidence,
                    source = EXCLUDED.source,
                    updated_at = EXCLUDED.updated_at,
                    is_active = EXCLUDED.is_active,
                    version = EXCLUDED.version
            """, node.id, node.node_type.value, node.name, node.label,
               json.dumps(node.properties), node.confidence, node.source,
               node.created_at, node.updated_at, node.is_active, node.version)
        return node.id
    
    async def get_node(self, node_id: str) -> Optional[GraphNode]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM graph_nodes WHERE id = $1", node_id)
            if not row:
                return None
            return self._row_to_node(row)
    
    async def update_node(self, node: GraphNode) -> None:
        node.updated_at = datetime.utcnow()
        node.version += 1
        await self.create_node(node)
    
    async def delete_node(self, node_id: str) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM graph_nodes WHERE id = $1", node_id)
            return result != "DELETE 0"
    
    async def find_nodes(
        self,
        node_type: NodeType = None,
        name: str = None,
        properties: dict = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[GraphNode]:
        conditions = ["is_active = TRUE"]
        params = []
        
        if node_type:
            params.append(node_type.value)
            conditions.append(f"node_type = ${len(params)}")
        
        if name:
            params.append(f"%{name}%")
            conditions.append(f"name ILIKE ${len(params)}")
        
        if properties:
            for key, value in properties.items():
                params.append(value)
                conditions.append(f"properties->>'{key}' = ${len(params)}")
        
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.extend([limit, offset])
        
        query = f"""
            SELECT * FROM graph_nodes 
            {where}
            ORDER BY created_at DESC
            LIMIT ${len(params)-1} OFFSET ${len(params)}
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_node(row) for row in rows]
    
    async def create_edge(self, edge: GraphEdge) -> str:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO graph_edges (id, source_id, target_id, relationship_type, properties, 
                                        confidence, weight, source, evidence, created_at, updated_at, 
                                        is_active, valid_from, valid_until)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                ON CONFLICT (source_id, target_id, relationship_type) DO UPDATE SET
                    properties = EXCLUDED.properties,
                    confidence = EXCLUDED.confidence,
                    weight = EXCLUDED.weight,
                    source = EXCLUDED.source,
                    evidence = EXCLUDED.evidence,
                    updated_at = EXCLUDED.updated_at,
                    is_active = EXCLUDED.is_active,
                    valid_from = EXCLUDED.valid_from,
                    valid_until = EXCLUDED.valid_until
            """, edge.id, edge.source_id, edge.target_id, edge.relationship_type.value,
               json.dumps(edge.properties), edge.confidence, edge.weight,
               edge.source, edge.evidence, edge.created_at, edge.updated_at,
               edge.is_active, edge.valid_from, edge.valid_until)
        return edge.id
    
    async def get_edge(self, edge_id: str) -> Optional[GraphEdge]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM graph_edges WHERE id = $1", edge_id)
            if not row:
                return None
            return self._row_to_edge(row)
    
    async def update_edge(self, edge: GraphEdge) -> None:
        edge.updated_at = datetime.utcnow()
        await self.create_edge(edge)
    
    async def delete_edge(self, edge_id: str) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM graph_edges WHERE id = $1", edge_id)
            return result != "DELETE 0"
    
    async def find_edges(
        self,
        source_id: str = None,
        target_id: str = None,
        relationship_type: RelationshipType = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[GraphEdge]:
        conditions = ["is_active = TRUE"]
        params = []
        
        if source_id:
            params.append(source_id)
            conditions.append(f"source_id = ${len(params)}")
        if target_id:
            params.append(target_id)
            conditions.append(f"target_id = ${len(params)}")
        if relationship_type:
            params.append(relationship_type.value)
            conditions.append(f"relationship_type = ${len(params)}")
        
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.extend([limit, offset])
        
        query = f"""
            SELECT * FROM graph_edges 
            {where}
            ORDER BY created_at DESC
            LIMIT ${len(params)-1} OFFSET ${len(params)}
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_edge(row) for row in rows]
    
    async def get_neighbors(
        self,
        node_id: str,
        relationship_type: RelationshipType = None,
        direction: str = "both"
    ) -> list[tuple[GraphEdge, GraphNode]]:
        conditions = ["e.is_active = TRUE", "n.is_active = TRUE"]
        params = [node_id]
        
        if direction == "outgoing":
            conditions.append("e.source_id = $1")
        elif direction == "incoming":
            conditions.append("e.target_id = $1")
        else:  # both
            conditions.append("(e.source_id = $1 OR e.target_id = $1)")
        
        if relationship_type:
            params.append(relationship_type.value)
            conditions.append(f"e.relationship_type = ${len(params)}")
        
        where = "WHERE " + " AND ".join(conditions)
        
        query = f"""
            SELECT e.*, n.* 
            FROM graph_edges e
            JOIN graph_nodes n ON (e.source_id = n.id AND e.target_id = $1)
                                 OR (e.target_id = n.id AND e.source_id = $1)
            {where}
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            results = []
            for row in rows:
                edge = self._row_to_edge(row)
                # Get the other node
                other_id = edge.target_id if edge.source_id == node_id else edge.source_id
                other_row = await conn.fetchrow("SELECT * FROM graph_nodes WHERE id = $1", other_id)
                if other_row:
                    node = self._row_to_node(other_row)
                    results.append((edge, node))
            return results
    
    async def get_subgraph(
        self,
        node_ids: list[str],
        max_depth: int = 1
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        if not node_ids:
            return [], []
        
        all_nodes = set(node_ids)
        all_edges = []
        
        # BFS to find connected nodes up to max_depth
        frontier = set(node_ids)
        for depth in range(max_depth):
            if not frontier:
                break
            
            async with self.pool.acquire() as conn:
                # Find edges from frontier
                placeholders = ", ".join([f"${i+1}" for i in range(len(frontier))])
                edge_query = f"""
                    SELECT * FROM graph_edges 
                    WHERE is_active = TRUE
                    AND (source_id IN ({placeholders}) OR target_id IN ({placeholders}))
                """
                edge_rows = await conn.fetch(edge_query, *list(frontier))
                
                new_frontier = set()
                for row in edge_rows:
                    edge = self._row_to_edge(row)
                    all_edges.append(edge)
                    new_frontier.add(edge.source_id)
                    new_frontier.add(edge.target_id)
                
                frontier = new_frontier - all_nodes
                all_nodes.update(frontier)
        
        # Get all nodes
        placeholders = ", ".join([f"${i+1}" for i in range(len(all_nodes))])
        node_query = f"""
            SELECT * FROM graph_nodes 
            WHERE id IN ({placeholders})
            AND is_active = TRUE
        """
        async with self.pool.acquire() as conn:
            node_rows = await conn.fetch(node_query, *list(all_nodes))
            nodes = [self._row_to_node(row) for row in node_rows]
        
        return nodes, all_edges
    
    async def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 6,
        relationship_types: list[RelationshipType] = None
    ) -> list[GraphEdge]:
        # Use networkx for pathfinding on a subgraph
        nodes, edges = await self.get_subgraph([source_id, target_id], max_depth)
        
        if not nodes:
            return []
        
        # Build networkx graph
        G = nx.DiGraph()
        for node in nodes:
            G.add_node(node.id, **node.properties)
        
        for edge in edges:
            if edge.is_active:
                G.add_edge(edge.source_id, edge.target_id, 
                          type=edge.relationship_type.value, 
                          weight=edge.weight,
                          edge_obj=edge)
        
        try:
            path = nx.shortest_path(G, source_id, target_id)
            # Convert to edges
            path_edges = []
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                edge_data = G[u][v]
                if 'edge_obj' in edge_data:
                    path_edges.append(edge_data['edge_obj'])
            return path_edges
        except nx.NetworkXNoPath:
            return []
    
    async def get_stats(self) -> dict:
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    (SELECT COUNT(*) FROM graph_nodes WHERE is_active) as total_nodes,
                    (SELECT COUNT(*) FROM graph_edges WHERE is_active) as total_edges,
                    (SELECT COUNT(DISTINCT node_type) FROM graph_nodes WHERE is_active) as node_types,
                    (SELECT COUNT(DISTINCT relationship_type) FROM graph_edges WHERE is_active) as edge_types,
                    (SELECT COUNT(*) FROM graph_nodes WHERE is_active AND node_type = 'company') as companies,
                    (SELECT COUNT(*) FROM graph_nodes WHERE is_active AND node_type = 'person') as people,
                    (SELECT COUNT(*) FROM graph_nodes WHERE is_active AND node_type = 'product') as products,
                    (SELECT COUNT(*) FROM graph_nodes WHERE is_active AND node_type = 'event') as events
            """)
            return dict(stats) if stats else {}
    
    def _row_to_node(self, row) -> GraphNode:
        return GraphNode(
            id=row["id"],
            node_type=NodeType(row["node_type"]),
            name=row["name"],
            label=row["label"] or "",
            properties=row["properties"],
            confidence=row["confidence"],
            source=row["source"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            is_active=row["is_active"],
            version=row["version"]
        )
    
    def _row_to_edge(self, row) -> GraphEdge:
        return GraphEdge(
            id=row["id"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            relationship_type=RelationshipType(row["relationship_type"]),
            properties=row["properties"],
            confidence=row["confidence"],
            weight=row["weight"],
            source=row["source"],
            evidence=row["evidence"] or [],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            is_active=row["is_active"],
            valid_from=row["valid_from"],
            valid_until=row["valid_until"]
        )


class KnowledgeGraph:
    """
    High-level knowledge graph service.
    Builds and queries financial knowledge graphs from entity recognition and other sources.
    """
    
    def __init__(self, backend: GraphBackend):
        self.backend = backend
        self._nx_cache: Optional[nx.DiGraph] = None
        self._cache_timestamp: Optional[datetime] = None
    
    async def initialize(self) -> None:
        await self.backend.connect()
    
    async def close(self) -> None:
        await self.backend.disconnect()
    
    # Node management
    async def add_node(
        self,
        node_type: NodeType,
        name: str,
        label: str = "",
        properties: dict = None,
        confidence: float = 1.0,
        source: str = "system"
    ) -> GraphNode:
        """Add a new node to the graph."""
        node = GraphNode(
            node_type=node_type,
            name=name,
            label=label or name,
            properties=properties or {},
            confidence=confidence,
            source=source
        )
        await self.backend.create_node(node)
        self._invalidate_cache()
        return node
    
    async def get_node(self, node_id: str) -> Optional[GraphNode]:
        return await self.backend.get_node(node_id)
    
    async def update_node(self, node: GraphNode) -> None:
        await self.backend.update_node(node)
        self._invalidate_cache()
    
    async def find_nodes(
        self,
        node_type: NodeType = None,
        name: str = None,
        limit: int = 100
    ) -> list[GraphNode]:
        return await self.backend.find_nodes(node_type=node_type, name=name, limit=limit)
    
    # Edge management
    async def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType,
        properties: dict = None,
        confidence: float = 1.0,
        weight: float = 1.0,
        source: str = "system",
        evidence: list[str] = None,
        valid_from: date = None,
        valid_until: date = None
    ) -> GraphEdge:
        """Add a relationship between two nodes."""
        edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            properties=properties or {},
            confidence=confidence,
            weight=weight,
            source=source,
            evidence=evidence or [],
            valid_from=valid_from,
            valid_until=valid_until
        )
        await self.backend.create_edge(edge)
        self._invalidate_cache()
        return edge
    
    async def get_edge(self, edge_id: str) -> Optional[GraphEdge]:
        return await self.backend.get_edge(edge_id)
    
    async def find_edges(
        self,
        source_id: str = None,
        target_id: str = None,
        relationship_type: RelationshipType = None,
        limit: int = 100
    ) -> list[GraphEdge]:
        return await self.backend.find_edges(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            limit=limit
        )
    
    # Graph traversal
    async def get_neighbors(
        self,
        node_id: str,
        relationship_type: RelationshipType = None,
        direction: str = "both"
    ) -> list[tuple[GraphEdge, GraphNode]]:
        return await self.backend.get_neighbors(node_id, relationship_type, direction)
    
    async def get_subgraph(
        self,
        node_ids: list[str],
        max_depth: int = 1
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        return await self.backend.get_subgraph(node_ids, max_depth)
    
    async def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 6,
        relationship_types: list[RelationshipType] = None
    ) -> list[GraphEdge]:
        return await self.backend.find_path(source_id, target_id, max_depth, relationship_types)
    
    async def find_all_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 4,
        relationship_types: list[RelationshipType] = None
    ) -> list[list[GraphEdge]]:
        """Find all paths between two nodes up to max_depth."""
        nodes, edges = await self.get_subgraph([source_id, target_id], max_depth)
        
        G = nx.DiGraph()
        for node in nodes:
            G.add_node(node.id)
        for edge in edges:
            if edge.is_active:
                G.add_edge(edge.source_id, edge.target_id, edge_obj=edge)
        
        try:
            paths = list(nx.all_simple_paths(G, source_id, target_id, cutoff=max_depth))
            result = []
            for path in paths:
                path_edges = []
                for i in range(len(path) - 1):
                    edge_data = G[path[i]][path[i + 1]]
                    if 'edge_obj' in edge_data:
                        path_edges.append(edge_data['edge_obj'])
                result.append(path_edges)
            return result
        except nx.NetworkXNoPath:
            return []
    
    # Building from entity recognition
    async def build_from_entities(
        self,
        entities: list[dict],
        relationships: list[dict]
    ) -> dict:
        """Build graph from entity recognition output."""
        created_nodes = {}
        created_edges = []
        
        # Create nodes
        for entity in entities:
            node_type = self._map_entity_type(entity.get("type", ""))
            node = await self.add_node(
                node_type=node_type,
                name=entity.get("name", ""),
                label=entity.get("label", ""),
                properties=entity.get("properties", {}),
                confidence=entity.get("confidence", 1.0),
                source=entity.get("source", "entity_recognition")
            )
            created_nodes[entity.get("id", node.id)] = node
        
        # Create edges
        for rel in relationships:
            source_node = created_nodes.get(rel.get("source_id"))
            target_node = created_nodes.get(rel.get("target_id"))
            
            if source_node and target_node:
                rel_type = self._map_relationship_type(rel.get("type", "RELATED_TO"))
                edge = await self.add_edge(
                    source_id=source_node.id,
                    target_id=target_node.id,
                    relationship_type=rel_type,
                    properties=rel.get("properties", {}),
                    confidence=rel.get("confidence", 1.0),
                    source=rel.get("source", "entity_recognition")
                )
                created_edges.append(edge)
        
        return {
            "nodes_created": len(created_nodes),
            "edges_created": len(created_edges),
            "nodes": created_nodes,
            "edges": created_edges
        }
    
    def _map_entity_type(self, entity_type: str) -> NodeType:
        mapping = {
            "company": NodeType.COMPANY,
            "organization": NodeType.COMPANY,
            "person": NodeType.PERSON,
            "product": NodeType.PRODUCT,
            "industry": NodeType.INDUSTRY,
            "sector": NodeType.SECTOR,
            "country": NodeType.COUNTRY,
            "event": NodeType.EVENT,
            "filing": NodeType.FILING,
            "metric": NodeType.METRIC,
            "news": NodeType.NEWS,
            "pattern": NodeType.PATTERN,
            "portfolio": NodeType.PORTFOLIO
        }
        return mapping.get(entity_type.lower(), NodeType.COMPANY)
    
    def _map_relationship_type(self, rel_type: str) -> RelationshipType:
        mapping = {
            "CEO_OF": RelationshipType.CEO_OF,
            "CFO_OF": RelationshipType.CFO_OF,
            "EXECUTIVE_OF": RelationshipType.EXECUTIVE_OF,
            "COMPETES_WITH": RelationshipType.COMPETES_WITH,
            "PARTNERS_WITH": RelationshipType.PARTNERS_WITH,
            "SUPPLIES": RelationshipType.SUPPLIES,
            "OWNS": RelationshipType.OWNS,
            "SUBSIDIARY_OF": RelationshipType.SUBSIDIARY_OF,
            "ACQUIRED": RelationshipType.ACQUIRED,
            "INVESTS_IN": RelationshipType.INVESTS_IN,
            "BELONGS_TO": RelationshipType.BELONGS_TO,
            "OPERATES_IN": RelationshipType.OPERATES_IN,
            "HAS_TICKER": RelationshipType.HAS_TICKER,
            "LISTED_ON": RelationshipType.LISTED_ON,
            "HAS_METRIC": RelationshipType.HAS_METRIC,
            "REPORTS": RelationshipType.REPORTS,
            "FILED": RelationshipType.FILED,
            "MENTIONS": RelationshipType.MENTIONS
        }
        return mapping.get(rel_type.upper(), RelationshipType.RELATED_TO)
    
    # Analytics
    async def get_centrality(
        self,
        node_ids: list[str] = None,
        centrality_type: str = "pagerank"
    ) -> dict[str, float]:
        """Calculate centrality measures for nodes."""
        if node_ids:
            nodes, edges = await self.get_subgraph(node_ids, max_depth=3)
        else:
            # Get full graph (might be large)
            stats = await self.backend.get_stats()
            total_nodes = stats.get("total_nodes", 0)
            if total_nodes > 10000:
                # Sample for performance
                sample_nodes = await self.find_nodes(limit=5000)
                node_ids = [n.id for n in sample_nodes]
                nodes, edges = await self.get_subgraph(node_ids, max_depth=2)
            else:
                nodes, edges = await self.get_subgraph([], max_depth=1)
        
        G = nx.DiGraph()
        for node in nodes:
            G.add_node(node.id)
        for edge in edges:
            if edge.is_active:
                G.add_edge(edge.source_id, edge.target_id, weight=edge.weight)
        
        if centrality_type == "pagerank":
            centrality = nx.pagerank(G, weight='weight')
        elif centrality_type == "betweenness":
            centrality = nx.betweenness_centrality(G, weight='weight')
        elif centrality_type == "degree":
            centrality = nx.degree_centrality(G)
        elif centrality_type == "eigenvector":
            centrality = nx.eigenvector_centrality(G, weight='weight', max_iter=1000)
        else:
            centrality = nx.pagerank(G)
        
        return centrality
    
    async def get_communities(
        self,
        node_ids: list[str] = None,
        algorithm: str = "louvain"
    ) -> list[list[str]]:
        """Detect communities in the graph."""
        if node_ids:
            nodes, edges = await self.get_subgraph(node_ids, max_depth=2)
        else:
            sample_nodes = await self.find_nodes(limit=2000)
            node_ids = [n.id for n in sample_nodes]
            nodes, edges = await self.get_subgraph(node_ids, max_depth=2)
        
        G = nx.Graph()  # Undirected for community detection
        for node in nodes:
            G.add_node(node.id)
        for edge in edges:
            if edge.is_active:
                G.add_edge(edge.source_id, edge.target_id, weight=edge.weight)
        
        if algorithm == "louvain":
            try:
                import community as community_louvain
                partition = community_louvain.best_partition(G, weight='weight')
                communities = defaultdict(list)
                for node, comm in partition.items():
                    communities[comm].append(node)
                return list(communities.values())
            except ImportError:
                # Fallback to connected components
                pass
        
        # Fallback: connected components
        return [list(c) for c in nx.connected_components(G)]
    
    async def get_influential_nodes(
        self,
        node_type: NodeType = None,
        top_k: int = 20
    ) -> list[dict]:
        """Get most influential nodes by centrality."""
        centrality = await self.get_centrality()
        
        # Filter by node type if specified
        if node_type:
            nodes = await self.find_nodes(node_type=node_type, limit=top_k * 2)
            filtered = {n.id: centrality.get(n.id, 0) for n in nodes}
            centrality = filtered
        
        # Sort and return top-k
        sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for node_id, score in sorted_nodes[:top_k]:
            node = await self.get_node(node_id)
            if node:
                results.append({
                    "node_id": node_id,
                    "name": node.name,
                    "type": node.node_type.value,
                    "centrality_score": score
                })
        
        return results
    
    async def get_stats(self) -> dict:
        return await self.backend.get_stats()
    
    def _invalidate_cache(self) -> None:
        self._nx_cache = None
        self._cache_timestamp = None


# Factory
async def create_knowledge_graph(
    backend_type: str = "postgres",
    **kwargs
) -> KnowledgeGraph:
    """Factory function to create KnowledgeGraph with specified backend."""
    if backend_type == "postgres":
        backend = PostgresGraphBackend(
            dsn=kwargs.get("dsn", "postgresql://localhost/financial_knowledge_graph"),
            pool_size=kwargs.get("pool_size", 10)
        )
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")
    
    kg = KnowledgeGraph(backend)
    await kg.initialize()
    return kg


# Export
__all__ = [
    "NodeType",
    "RelationshipType",
    "GraphNode",
    "GraphEdge",
    "GraphBackend",
    "PostgresGraphBackend",
    "KnowledgeGraph",
    "create_knowledge_graph",
]