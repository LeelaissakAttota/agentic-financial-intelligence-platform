"""
Knowledge Graph Integration - Cross-agent knowledge sharing via graph.

Enables agents to query and contribute to a shared knowledge graph
for entity relationships, facts, and context.
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import logging

from data.knowledge_graph.graph import KnowledgeGraph
from config.settings import get_settings

logger = logging.getLogger(__name__)


class KnowledgeSource(str, Enum):
    """Source of knowledge in the graph."""
    AGENT_FINDING = "agent_finding"
    SEC_FILING = "sec_filing"
    NEWS_ARTICLE = "news_article"
    EARNINGS_CALL = "earnings_call"
    ANALYST_REPORT = "analyst_report"
    MARKET_DATA = "market_data"
    USER_INPUT = "user_input"
    INFERRED = "inferred"


class RelationshipType(str, Enum):
    """Types of relationships in the knowledge graph."""
    # Company relationships
    COMPETES_WITH = "competes_with"
    PARTNERS_WITH = "partners_with"
    SUPPLIES_TO = "supplies_to"
    CUSTOMER_OF = "customer_of"
    SUBSIDIARY_OF = "subsidiary_of"
    ACQUIRED = "acquired"
    MERGED_WITH = "merged_with"
    INVESTS_IN = "invests_in"
    # Person relationships
    CEO_OF = "ceo_of"
    CFO_OF = "cfo_of"
    EXECUTIVE_OF = "executive_of"
    BOARD_MEMBER_OF = "board_member_of"
    FOUNDED = "founded"
    # Product relationships
    PRODUCES = "produces"
    USES_TECHNOLOGY = "uses_technology"
    LICENSES_FROM = "licenses_from"
    # Financial relationships
    HOLDS_POSITION = "holds_position"
    LENDS_TO = "lends_to"
    BORROWS_FROM = "borrows_from"
    # Market relationships
    CORRELATED_WITH = "correlated_with"
    SECTOR_PEER = "sector_peer"
    INDEX_MEMBER = "index_member"
    # Event relationships
    ANNOUNCED = "announced"
    TRIGGERED = "triggered"
    CAUSED = "caused"
    IMPACTED = "impacted"


@dataclass
class KnowledgeNode:
    """Node in the knowledge graph."""
    node_id: str
    entity_type: str  # company, person, product, metric, event, concept
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    source: KnowledgeSource = KnowledgeSource.INFERRED
    confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class KnowledgeEdge:
    """Edge (relationship) in the knowledge graph."""
    edge_id: str
    source_id: str
    target_id: str
    relationship: RelationshipType
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    confidence: float = 1.0
    source: KnowledgeSource = KnowledgeSource.INFERRED
    created_at: datetime = field(default_factory=datetime.now)
    created_by: Optional[str] = None
    evidence: List[str] = field(default_factory=list)  # Evidence IDs


@dataclass
class KnowledgeQuery:
    """Query for knowledge graph."""
    query_id: str
    query_type: str  # neighbors, path, centrality, community, subgraph
    parameters: Dict[str, Any]
    requester: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class KnowledgeResult:
    """Result of a knowledge graph query."""
    query_id: str
    nodes: List[KnowledgeNode] = field(default_factory=list)
    edges: List[KnowledgeEdge] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    paths: List[List[str]] = field(default_factory=list)
    communities: List[List[str]] = field(default_factory=list)
    execution_time_ms: float = 0.0


class KnowledgeGraphClient:
    """
    Client for interacting with the shared knowledge graph.

    Provides high-level operations for agents to:
    - Add findings as nodes/edges
    - Query relationships
    - Get entity context
    - Find paths between entities
    - Detect communities
    """

    def __init__(self):
        self.settings = get_settings()
        self.kg = KnowledgeGraph()
        self.pending_writes: List[Tuple[KnowledgeNode | KnowledgeEdge, KnowledgeSource]] = []

    async def add_finding(
        self,
        agent_name: str,
        finding_type: str,
        content: Dict[str, Any],
        confidence: float = 0.8,
        tags: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add agent finding as nodes/edges to knowledge graph.

        Returns list of created node/edge IDs.
        """
        created_ids = []

        # Extract entities and relationships from finding
        entities = self._extract_entities(content, finding_type)
        relationships = self._extract_relationships(content, finding_type)

        # Create nodes
        for entity in entities:
            node = KnowledgeNode(
                node_id=str(uuid.uuid4())[:8],
                entity_type=entity["type"],
                name=entity["name"],
                properties=entity.get("properties", {}),
                source=KnowledgeSource.AGENT_FINDING,
                confidence=confidence,
                created_by=agent_name,
                tags=tags or []
            )
            await self.kg.add_node(node)
            created_ids.append(node.node_id)
            self._update_entity_index(entity["name"], node.node_id)

        # Create edges
        for rel in relationships:
            source_id = self._resolve_entity_id(rel["source"])
            target_id = self._resolve_entity_id(rel["target"])

            if source_id and target_id:
                edge = KnowledgeEdge(
                    edge_id=str(uuid.uuid4())[:8],
                    source_id=source_id,
                    target_id=target_id,
                    relationship=RelationshipType(rel["type"]),
                    properties=rel.get("properties", {}),
                    confidence=confidence * rel.get("confidence", 1.0),
                    source=KnowledgeSource.AGENT_FINDING,
                    created_by=agent_name,
                    evidence=[f"finding_{finding_type}"]
                )
                await self.kg.add_edge(edge)
                created_ids.append(edge.edge_id)

        logger.info(f"Added finding from {agent_name}: {len(created_ids)} graph elements")
        return created_ids

    def _extract_entities(self, content: Dict[str, Any], finding_type: str) -> List[Dict[str, Any]]:
        """Extract entities from finding content."""
        entities = []

        # Common entity fields
        if "company" in content:
            entities.append({
                "type": "company",
                "name": content["company"],
                "properties": {"ticker": content.get("ticker")}
            })

        if "ticker" in content:
            entities.append({
                "type": "company",
                "name": content["ticker"],
                "properties": {"is_ticker": True}
            })

        # Finding-type specific entities
        if finding_type == "financial_analysis":
            for metric in ["revenue", "profit", "eps", "pe_ratio", "margin"]:
                if metric in content:
                    entities.append({
                        "type": "metric",
                        "name": metric,
                        "properties": {"value": content[metric], "company": content.get("company")}
                    })

        elif finding_type == "risk_assessment":
            for risk in content.get("risk_factors", []):
                entities.append({
                    "type": "risk",
                    "name": risk.get("name", "Unknown Risk"),
                    "properties": risk
                })

        elif finding_type == "pattern_detection":
            for pattern in content.get("patterns", []):
                entities.append({
                    "type": "pattern",
                    "name": pattern.get("type", "Unknown Pattern"),
                    "properties": pattern
                })

        elif finding_type == "news_analysis":
            for entity in content.get("entities", []):
                entities.append({
                    "type": entity.get("type", "entity"),
                    "name": entity.get("name", "Unknown"),
                    "properties": entity
                })

        # Deduplicate
        seen = set()
        unique = []
        for e in entities:
            key = (e["type"], e["name"])
            if key not in seen:
                seen.add(key)
                unique.append(e)

        return unique

    def _extract_relationships(self, content: Dict[str, Any], finding_type: str) -> List[Dict[str, Any]]:
        """Extract relationships from finding content."""
        relationships = []

        company = content.get("company")
        if not company:
            return relationships

        if finding_type == "financial_analysis":
            for metric in ["revenue", "profit", "eps", "pe_ratio", "margin"]:
                if metric in content:
                    relationships.append({
                        "source": company,
                        "target": metric,
                        "type": "HAS_METRIC",
                        "properties": {"value": content[metric]}
                    })

        elif finding_type == "competitive_analysis":
            peers = content.get("peers", [])
            for peer in peers:
                relationships.append({
                    "source": company,
                    "target": peer.get("name", ""),
                    "type": "COMPETES_WITH",
                    "properties": {"comparison": peer}
                })

        elif finding_type == "risk_assessment":
            for risk in content.get("risk_factors", []):
                relationships.append({
                    "source": company,
                    "target": risk.get("name", "Unknown Risk"),
                    "type": "HAS_RISK",
                    "properties": {"severity": risk.get("severity", "medium")}
                })

        elif finding_type == "news_analysis":
            for entity in content.get("entities", []):
                relationships.append({
                    "source": company,
                    "target": entity.get("name", ""),
                    "type": "MENTIONED_IN",
                    "properties": {"context": entity.get("context", "")}
                })

        return relationships

    def _resolve_entity_id(self, name: str) -> Optional[str]:
        """Resolve entity name to node ID."""
        # Check index
        if name in self._entity_index:
            return self._entity_index[name]

        # Query graph
        nodes = self.kg.find_nodes(name=name)
        if nodes:
            node_id = nodes[0].node_id
            self._entity_index[name] = node_id
            return node_id

        return None

    def _update_entity_index(self, name: str, node_id: str):
        """Update entity name to ID index."""
        self._entity_index[name] = node_id

    _entity_index: Dict[str, str] = {}

    async def get_entity_context(self, entity_name: str, depth: int = 2) -> Dict[str, Any]:
        """Get full context for an entity (neighbors, paths, metrics)."""
        node_id = self._resolve_entity_id(entity_name)
        if not node_id:
            return {"error": f"Entity not found: {entity_name}"}

        # Get neighbors
        neighbors = await self.kg.get_neighbors(node_id, depth)

        # Get shortest paths to key entities
        key_entities = ["CEO", "CFO", "competitor", "partner", "subsidiary"]
        paths = []
        for key in key_entities:
            target_id = self._resolve_entity_id(key)
            if target_id and target_id != node_id:
                path = await self.kg.get_shortest_path(node_id, target_id)
                if path:
                    paths.append(path)

        # Get centrality metrics
        centrality = await self.kg.get_centrality(node_id)

        return {
            "entity": entity_name,
            "node_id": node_id,
            "neighbors": neighbors,
            "paths_to_key_entities": paths,
            "centrality": centrality,
            "depth": depth
        }

    async def find_relationship_path(
        self,
        source: str,
        target: str,
        max_depth: int = 4
    ) -> Optional[List[str]]:
        """Find shortest path between two entities."""
        source_id = self._resolve_entity_id(source)
        target_id = self._resolve_entity_id(target)

        if not source_id or not target_id:
            return None

        return await self.kg.get_shortest_path(source_id, target_id, max_depth)

    async def detect_communities(self, entity_type: Optional[str] = None) -> List[List[str]]:
        """Detect communities in the graph."""
        return await self.kg.detect_communities(entity_type)

    async def get_central_entities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most central entities by PageRank/degree."""
        return await self.kg.get_central_entities(limit)

    async def query_subgraph(
        self,
        center: str,
        radius: int = 2,
        edge_types: Optional[List[RelationshipType]] = None
    ) -> Dict[str, Any]:
        """Get subgraph around center entity."""
        node_id = self._resolve_entity_id(center)
        if not node_id:
            return {"error": f"Entity not found: {center}"}

        return await self.kg.get_subgraph(node_id, radius, edge_types)

    async def find_similar_entities(
        self,
        entity: str,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Find entities similar to given entity."""
        node_id = self._resolve_entity_id(entity)
        if not node_id:
            return []

        # Use graph embeddings or structural similarity
        # Simplified: find by shared neighbors
        neighbors = await self.kg.get_neighbors(node_id, 1)
        similar = []

        for neighbor in neighbors:
            n_neighbors = await self.kg.get_neighbors(neighbor["node_id"], 1)
            overlap = len(set(n["node_id"] for n in n_neighbors) &
                         set(n["node_id"] for n in neighbors))
            similarity = overlap / max(len(n_neighbors), 1)

            if similarity >= similarity_threshold:
                similar.append({
                    "entity": neighbor["name"],
                    "similarity": similarity,
                    "shared_neighbors": overlap
                })

        similar.sort(key=lambda x: x["similarity"], reverse=True)
        return similar[:10]


class KnowledgeAggregator:
    """Aggregates knowledge from multiple agents into coherent view."""

    def __init__(self, kg_client: KnowledgeGraphClient):
        self.kg = kg_client

    async def aggregate_company_view(self, company: str) -> Dict[str, Any]:
        """Build comprehensive company view from all agent findings."""
        # Get entity context
        context = await self.kg.get_entity_context(company, depth=2)

        # Get communities
        communities = await self.kg.detect_communities("company")

        # Find similar companies
        similar = await self.kg.find_similar_entities(company)

        # Get central entities in network
        central = await self.kg.get_central_entities(10)

        return {
            "company": company,
            "graph_context": context,
            "peer_community": self._find_company_community(company, communities),
            "similar_companies": similar,
            "network_centrality": central,
            "timestamp": datetime.now().isoformat()
        }

    def _find_company_community(self, company: str, communities: List[List[str]]) -> Optional[List[str]]:
        """Find which community a company belongs to."""
        for community in communities:
            if company in community:
                return community
        return None

    async def build_investment_thesis_context(
        self,
        company: str,
        thesis: str
    ) -> Dict[str, Any]:
        """Build context for investment thesis from graph knowledge."""
        # Get direct relationships
        context = await self.kg.get_entity_context(company)

        # Find supporting/contradicting evidence
        # Query for risk factors, competitive advantages, catalysts
        evidence = {
            "supporting": [],
            "contradicting": [],
            "neutral": []
        }

        # In production, would query graph for specific evidence types
        return {
            "company": company,
            "thesis": thesis,
            "graph_evidence": evidence,
            "network_context": context
        }


# Global instances
_kg_client: Optional[KnowledgeGraphClient] = None
_kg_aggregator: Optional[KnowledgeAggregator] = None


def get_knowledge_graph_client() -> KnowledgeGraphClient:
    """Get global knowledge graph client."""
    global _kg_client
    if _kg_client is None:
        _kg_client = KnowledgeGraphClient()
    return _kg_client


def get_knowledge_aggregator() -> KnowledgeAggregator:
    """Get global knowledge aggregator."""
    global _kg_aggregator
    if _kg_aggregator is None:
        _kg_aggregator = KnowledgeAggregator(get_knowledge_graph_client())
    return _kg_aggregator