"""
Graph Models - Core data models for Neo4j graph entities.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import uuid


class EntityType(str, Enum):
    """Types of entities in the financial knowledge graph."""
    COMPANY = "Company"
    PERSON = "Person"
    PRODUCT = "Product"
    SECTOR = "Sector"
    INDUSTRY = "Industry"
    MARKET_INDEX = "MarketIndex"
    FINANCIAL_METRIC = "FinancialMetric"
    EVENT = "Event"
    NEWS_ARTICLE = "NewsArticle"
    EARNINGS_CALL = "EarningsCall"
    SEC_FILING = "SECFiling"
    ANALYST_REPORT = "AnalystReport"
    REGULATORY_BODY = "RegulatoryBody"
    GEOGRAPHY = "Geography"


class RelationshipType(str, Enum):
    """Types of relationships in the financial knowledge graph."""
    # Company relationships
    COMPETES_WITH = "COMPETES_WITH"
    PARTNERS_WITH = "PARTNERS_WITH"
    SUPPLIES_TO = "SUPPLIES_TO"
    ACQUIRED = "ACQUIRED"
    MERGED_WITH = "MERGED_WITH"
    SUBSIDIARY_OF = "SUBSIDIARY_OF"
    
    # Person relationships
    WORKS_FOR = "WORKS_FOR"
    BOARD_MEMBER_OF = "BOARD_MEMBER_OF"
    ADVISES = "ADVISES"
    FOUNDED = "FOUNDED"
    
    # Product relationships
    PRODUCES = "PRODUCES"
    COMPETES_WITH_PRODUCT = "COMPETES_WITH_PRODUCT"
    
    # Sector/Industry relationships
    OPERATES_IN = "OPERATES_IN"
    PART_OF = "PART_OF"
    
    # Financial relationships
    HAS_METRIC = "HAS_METRIC"
    REPORTED_IN = "REPORTED_IN"
    MENTIONED_IN = "MENTIONED_IN"
    
    # Event relationships
    TRIGGERED = "TRIGGERED"
    IMPACTED = "IMPACTED"
    RELATED_TO = "RELATED_TO"
    
    # Document relationships
    CITES = "CITES"
    REFERENCES = "REFERENCES"
    ANALYZES = "ANALYZES"


@dataclass
class GraphEntity:
    """Represents a node in the knowledge graph."""
    id: str
    type: EntityType
    properties: Dict[str, Any] = field(default_factory=dict)
    labels: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: int = 1
    source: str = "system"
    confidence: float = 1.0
    
    def __post_init__(self):
        if not self.labels:
            self.labels = [self.type.value]
        if "id" not in self.properties:
            self.properties["id"] = self.id
        if "type" not in self.properties:
            self.properties["type"] = self.type.value
    
    @classmethod
    def create(
        cls,
        type: EntityType,
        properties: Dict[str, Any],
        source: str = "system",
        confidence: float = 1.0
    ) -> "GraphEntity":
        """Factory method to create a new entity."""
        entity_id = properties.get("id") or str(uuid.uuid4())
        return cls(
            id=entity_id,
            type=type,
            properties=properties,
            source=source,
            confidence=confidence
        )
    
    def to_cypher_params(self) -> Dict[str, Any]:
        """Convert to parameters for Cypher query."""
        return {
            "id": self.id,
            "type": self.type.value,
            "properties": self.properties,
            "labels": self.labels,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "source": self.source,
            "confidence": self.confidence
        }
    
    @classmethod
    def from_record(cls, record: Dict[str, Any]) -> "GraphEntity":
        """Create entity from Neo4j record."""
        node = record.get("n") or record.get("node")
        if node:
            return cls(
                id=node.get("id", ""),
                type=EntityType(node.get("type", "Company")),
                properties=dict(node),
                labels=list(node.labels) if hasattr(node, "labels") else [],
                created_at=node.get("created_at"),
                updated_at=node.get("updated_at"),
                version=node.get("version", 1),
                source=node.get("source", "system"),
                confidence=node.get("confidence", 1.0)
            )
        return cls(id="", type=EntityType.COMPANY)


@dataclass
class GraphRelationship:
    """Represents an edge in the knowledge graph."""
    id: str
    type: RelationshipType
    source_id: str
    target_id: str
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: int = 1
    source: str = "system"
    confidence: float = 1.0
    weight: float = 1.0
    
    def __post_init__(self):
        if "id" not in self.properties:
            self.properties["id"] = self.id
        if "type" not in self.properties:
            self.properties["type"] = self.type.value
        if "source_id" not in self.properties:
            self.properties["source_id"] = self.source_id
        if "target_id" not in self.properties:
            self.properties["target_id"] = self.target_id
    
    @classmethod
    def create(
        cls,
        type: RelationshipType,
        source_id: str,
        target_id: str,
        properties: Dict[str, Any] = None,
        source: str = "system",
        confidence: float = 1.0,
        weight: float = 1.0
    ) -> "GraphRelationship":
        """Factory method to create a new relationship."""
        rel_id = properties.get("id") if properties else str(uuid.uuid4())
        return cls(
            id=rel_id,
            type=type,
            source_id=source_id,
            target_id=target_id,
            properties=properties or {},
            source=source,
            confidence=confidence,
            weight=weight
        )
    
    def to_cypher_params(self) -> Dict[str, Any]:
        """Convert to parameters for Cypher query."""
        return {
            "id": self.id,
            "type": self.type.value,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "source": self.source,
            "confidence": self.confidence,
            "weight": self.weight
        }


@dataclass
class GraphPath:
    """Represents a path in the knowledge graph."""
    nodes: List[GraphEntity]
    relationships: List[GraphRelationship]
    length: int
    cost: float = 0.0
    
    def __post_init__(self):
        self.length = len(self.relationships)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_cypher_params() for n in self.nodes],
            "relationships": [r.to_cypher_params() for r in self.relationships],
            "length": self.length,
            "cost": self.cost
        }


@dataclass
class GraphCommunity:
    """Represents a community/cluster in the graph."""
    id: str
    name: str
    entities: List[GraphEntity]
    relationships: List[GraphRelationship]
    centrality_scores: Dict[str, float] = field(default_factory=dict)
    modularity: float = 0.0
    size: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        self.size = len(self.entities)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "size": self.size,
            "modularity": self.modularity,
            "centrality_scores": self.centrality_scores,
            "entities": [e.id for e in self.entities],
            "created_at": self.created_at.isoformat()
        }


@dataclass
class GraphQueryResult:
    """Result of a graph query operation."""
    entities: List[GraphEntity] = field(default_factory=list)
    relationships: List[GraphRelationship] = field(default_factory=list)
    paths: List[GraphPath] = field(default_factory=list)
    communities: List[GraphCommunity] = field(default_factory=list)
    aggregations: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0