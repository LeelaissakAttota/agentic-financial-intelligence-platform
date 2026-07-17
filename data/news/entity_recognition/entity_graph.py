"""
Entity Graph for Financial Entity Recognition

Queryable graph structure for entity relationships.
Supports traversal, filtering, and analysis of financial entity networks.
"""

import logging
from typing import Dict, List, Optional, Set, Any, Tuple, Iterator
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import networkx as nx

from data.news.entity_recognition.schemas import (
    Entity, EntityType, EntitySubType, EntityRelationship, RelationshipType
)
from data.news.entity_recognition.relationship_builder import RelationshipBuilder

logger = logging.getLogger(__name__)


class GraphQueryType(Enum):
    """Types of graph queries."""
    NEIGHBORS = "neighbors"           # Direct connections
    PATH = "path"                     # Path between two entities
    SUBGRAPH = "subgraph"             # Subgraph around entity
    COMMUNITY = "community"           # Community detection
    CENTRALITY = "centrality"         # Centrality measures
    REACHABLE = "reachable"           # All reachable nodes


@dataclass
class GraphNode:
    """Graph node with entity data."""
    entity_id: str
    entity: Entity
    degree: int = 0
    centrality: float = 0.0
    community: Optional[int] = None
    
    def __hash__(self):
        return hash(self.entity_id)
    
    def __eq__(self, other):
        return isinstance(other, GraphNode) and self.entity_id == other.entity_id


@dataclass
class GraphEdge:
    """Graph edge with relationship data."""
    source_id: str
    target_id: str
    relationship: EntityRelationship
    weight: float = 1.0
    
    def __hash__(self):
        return hash((self.source_id, self.target_id, self.relationship.relationship_type))
    
    def __eq__(self, other):
        return (isinstance(other, GraphEdge) and 
                self.source_id == other.source_id and 
                self.target_id == other.target_id and
                self.relationship.relationship_type == other.relationship.relationship_type)


class EntityGraph:
    """
    Queryable entity relationship graph.
    
    Features:
    - NetworkX-based graph for efficient algorithms
    - Entity-type filtered views
    - Relationship-type filtered views
    - Path finding between entities
    - Community detection
    - Centrality analysis
    - Subgraph extraction
    - Serialization to/from JSON
    """
    
    def __init__(self):
        self._graph = nx.MultiDiGraph()
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._entity_index: Dict[str, Entity] = {}
        
    def add_entity(self, entity: Entity) -> None:
        """Add an entity to the graph."""
        if entity.entity_id in self._entity_index:
            return
            
        self._entity_index[entity.entity_id] = entity
        node = GraphNode(entity_id=entity.entity_id, entity=entity)
        self._nodes[entity.entity_id] = node
        self._graph.add_node(entity.entity_id, entity=entity)
        
    def add_entities(self, entities: List[Entity]) -> None:
        """Add multiple entities."""
        for entity in entities:
            self.add_entity(entity)
            
    def add_relationship(self, relationship: EntityRelationship) -> None:
        """Add a relationship between entities."""
        source_id = relationship.source_entity_id
        target_id = relationship.target_entity_id
        
        # Ensure both entities exist
        if source_id not in self._entity_index or target_id not in self._entity_index:
            logger.warning(f"Cannot add relationship: missing entity {source_id} or {target_id}")
            return
            
        edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            weight=relationship.confidence
        )
        
        self._edges.append(edge)
        self._graph.add_edge(
            source_id, target_id, 
            key=relationship.relationship_type.value,
            relationship=relationship,
            weight=relationship.confidence
        )
        
        # Update node degrees
        self._nodes[source_id].degree = self._graph.degree(source_id)
        self._nodes[target_id].degree = self._graph.degree(target_id)
        
    def add_relationships(self, relationships: List[EntityRelationship]) -> None:
        """Add multiple relationships."""
        for rel in relationships:
            self.add_relationship(rel)
            
    def build_from_extraction(
        self, 
        entities: List[Entity], 
        relationships: List[EntityRelationship]
    ) -> None:
        """Build graph from extraction results."""
        self.clear()
        self.add_entities(entities)
        self.add_relationships(relationships)
        self._calculate_centrality()
        logger.info(f"Built graph with {len(self._nodes)} nodes and {len(self._edges)} edges")
        
    def clear(self) -> None:
        """Clear the graph."""
        self._graph.clear()
        self._nodes.clear()
        self._edges.clear()
        self._entity_index.clear()
        
    def _calculate_centrality(self) -> None:
        """Calculate centrality measures for nodes."""
        try:
            # Degree centrality
            degree_cent = nx.degree_centrality(self._graph)
            # Betweenness centrality (sample for large graphs)
            if len(self._graph) < 500:
                betweenness_cent = nx.betweenness_centrality(self._graph)
            else:
                betweenness_cent = nx.betweenness_centrality(self._graph, k=100)
            # PageRank
            pagerank = nx.pagerank(self._graph, max_iter=100)
            
            for node_id, node in self._nodes.items():
                node.centrality = (
                    degree_cent.get(node_id, 0) * 0.3 +
                    betweenness_cent.get(node_id, 0) * 0.3 +
                    pagerank.get(node_id, 0) * 0.4
                )
        except Exception as e:
            logger.warning(f"Centrality calculation failed: {e}")
            
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        return self._entity_index.get(entity_id)
        
    def get_node(self, entity_id: str) -> Optional[GraphNode]:
        """Get graph node by entity ID."""
        return self._nodes.get(entity_id)
        
    def get_neighbors(
        self, 
        entity_id: str, 
        relationship_types: Optional[List[RelationshipType]] = None,
        entity_types: Optional[List[EntityType]] = None,
        direction: str = "both"
    ) -> List[Tuple[Entity, EntityRelationship]]:
        """
        Get neighboring entities.
        
        Args:
            entity_id: Source entity ID
            relationship_types: Filter by relationship types
            entity_types: Filter by target entity types
            direction: "out", "in", or "both"
            
        Returns:
            List of (neighbor_entity, relationship) tuples
        """
        if entity_id not in self._graph:
            return []
            
        neighbors = []
        
        if direction in ["out", "both"]:
            for _, target_id, key, data in self._graph.out_edges(entity_id, keys=True, data=True):
                rel = data.get("relationship")
                if rel and self._matches_filters(rel, relationship_types, entity_types):
                    target_entity = self._entity_index.get(target_id)
                    if target_entity:
                        neighbors.append((target_entity, rel))
                        
        if direction in ["in", "both"]:
            for source_id, _, key, data in self._graph.in_edges(entity_id, keys=True, data=True):
                rel = data.get("relationship")
                if rel and self._matches_filters(rel, relationship_types, entity_types):
                    source_entity = self._entity_index.get(source_id)
                    if source_entity:
                        neighbors.append((source_entity, rel))
                        
        return neighbors
        
    def _matches_filters(
        self, 
        relationship: EntityRelationship,
        relationship_types: Optional[List[RelationshipType]],
        entity_types: Optional[List[EntityType]]
    ) -> bool:
        """Check if relationship matches filters."""
        if relationship_types and relationship.relationship_type not in relationship_types:
            return False
        # Entity type filtering would need target entity lookup
        return True
        
    def find_path(
        self, 
        source_id: str, 
        target_id: str,
        relationship_types: Optional[List[RelationshipType]] = None,
        max_length: int = 5
    ) -> Optional[List[Tuple[Entity, EntityRelationship]]]:
        """Find shortest path between two entities."""
        if source_id not in self._graph or target_id not in self._graph:
            return None
            
        try:
            # Create filtered graph if needed
            if relationship_types:
                filtered_graph = nx.MultiDiGraph()
                for u, v, key, data in self._graph.edges(keys=True, data=True):
                    rel = data.get("relationship")
                    if rel and rel.relationship_type in relationship_types:
                        filtered_graph.add_edge(u, v, key=key, **data)
            else:
                filtered_graph = self._graph
                
            # Find shortest path
            path_nodes = nx.shortest_path(filtered_graph, source_id, target_id)
            
            if len(path_nodes) > max_length + 1:
                return None
                
            # Build path with relationships
            path = []
            for i in range(len(path_nodes) - 1):
                u, v = path_nodes[i], path_nodes[i + 1]
                # Get relationship
                edges = filtered_graph.get_edge_data(u, v)
                if edges:
                    # Take first relationship
                    for key, data in edges.items():
                        rel = data.get("relationship")
                        if rel:
                            target_entity = self._entity_index.get(v)
                            if target_entity:
                                path.append((target_entity, rel))
                            break
                            
            return path
            
        except nx.NetworkXNoPath:
            return None
        except Exception as e:
            logger.warning(f"Path finding failed: {e}")
            return None
            
    def get_subgraph(
        self, 
        entity_id: str, 
        radius: int = 2,
        relationship_types: Optional[List[RelationshipType]] = None,
        entity_types: Optional[List[EntityType]] = None
    ) -> "EntityGraph":
        """Extract subgraph around an entity."""
        if entity_id not in self._graph:
            return EntityGraph()
            
        # Get nodes within radius
        subgraph_nodes = set()
        current_layer = {entity_id}
        
        for _ in range(radius):
            subgraph_nodes.update(current_layer)
            next_layer = set()
            for node in current_layer:
                # Out neighbors
                for _, v, _, data in self._graph.out_edges(node, keys=True, data=True):
                    rel = data.get("relationship")
                    if not relationship_types or (rel and rel.relationship_type in relationship_types):
                        next_layer.add(v)
                # In neighbors
                for u, _, _, data in self._graph.in_edges(node, keys=True, data=True):
                    rel = data.get("relationship")
                    if not relationship_types or (rel and rel.relationship_type in relationship_types):
                        next_layer.add(u)
            current_layer = next_layer - subgraph_nodes
            
        # Filter by entity types
        if entity_types:
            filtered_nodes = set()
            for node_id in subgraph_nodes:
                entity = self._entity_index.get(node_id)
                if entity and entity.entity_type in entity_types:
                    filtered_nodes.add(node_id)
            subgraph_nodes = filtered_nodes
            
        # Build subgraph
        subgraph = EntityGraph()
        for node_id in subgraph_nodes:
            entity = self._entity_index.get(node_id)
            if entity:
                subgraph.add_entity(entity)
                
        for u, v, key, data in self._graph.edges(keys=True, data=True):
            if u in subgraph_nodes and v in subgraph_nodes:
                rel = data.get("relationship")
                if rel and (not relationship_types or rel.relationship_type in relationship_types):
                    subgraph.add_relationship(rel)
                    
        return subgraph
        
    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Get all entities of a specific type."""
        return [e for e in self._entity_index.values() if e.entity_type == entity_type]
        
    def get_relationships_by_type(self, rel_type: RelationshipType) -> List[EntityRelationship]:
        """Get all relationships of a specific type."""
        relationships = []
        for u, v, key, data in self._graph.edges(keys=True, data=True):
            rel = data.get("relationship")
            if rel and rel.relationship_type == rel_type:
                relationships.append(rel)
        return relationships
        
    def get_companies_with_tickers(self) -> List[Tuple[Entity, Entity]]:
        """Get all company-ticker pairs."""
        pairs = []
        for rel in self.get_relationships_by_type(RelationshipType.HAS_TICKER):
            company = self.get_entity(rel.source_entity_id)
            ticker = self.get_entity(rel.target_entity_id)
            if company and ticker:
                pairs.append((company, ticker))
        return pairs
        
    def get_company_executives(self, company_id: str) -> List[Tuple[Entity, EntityRelationship]]:
        """Get executives for a company."""
        exec_relationships = [
            RelationshipType.HAS_CEO, RelationshipType.HAS_CFO,
            RelationshipType.HAS_EXECUTIVE, RelationshipType.HAS_FOUNDER
        ]
        return self.get_neighbors(company_id, relationship_types=exec_relationships)
        
    def get_company_competitors(self, company_id: str) -> List[Entity]:
        """Get competitors of a company."""
        neighbors = self.get_neighbors(company_id, relationship_types=[RelationshipType.COMPETES_WITH])
        return [e for e, _ in neighbors]
        
    def get_company_partners(self, company_id: str) -> List[Entity]:
        """Get partners of a company."""
        neighbors = self.get_neighbors(company_id, relationship_types=[RelationshipType.PARTNERS_WITH])
        return [e for e, _ in neighbors]
        
    def get_market_metrics(self, company_id: str) -> List[Tuple[Entity, EntityRelationship]]:
        """Get financial metrics for a company."""
        return self.get_neighbors(company_id, relationship_types=[RelationshipType.REPORTED])
        
    def get_company_events(self, company_id: str) -> List[Tuple[Entity, EntityRelationship]]:
        """Get events for a company."""
        return self.get_neighbors(company_id, relationship_types=[RelationshipType.INVOLVED_IN])
        
    def get_central_entities(self, top_k: int = 10, entity_type: Optional[EntityType] = None) -> List[Tuple[Entity, float]]:
        """Get most central entities by centrality score."""
        candidates = []
        for node in self._nodes.values():
            if entity_type is None or node.entity.entity_type == entity_type:
                candidates.append((node.entity, node.centrality))
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_k]
        
    def detect_communities(self, min_size: int = 3) -> List[List[Entity]]:
        """Detect communities in the graph."""
        try:
            # Convert to undirected for community detection
            undirected = self._graph.to_undirected()
            communities = nx.community.greedy_modularity_communities(undirected)
            
            result = []
            for community in communities:
                if len(community) >= min_size:
                    entities = [self._entity_index[n] for n in community if n in self._entity_index]
                    if entities:
                        result.append(entities)
                        
            return result
        except Exception as e:
            logger.warning(f"Community detection failed: {e}")
            return []
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "num_nodes": len(self._nodes),
            "num_edges": len(self._edges),
            "entity_types": self._count_by_type(),
            "relationship_types": self._count_by_relationship(),
            "density": nx.density(self._graph) if len(self._graph) > 1 else 0,
            "connected_components": nx.number_weakly_connected_components(self._graph),
            "average_degree": sum(d for _, d in self._graph.degree()) / len(self._graph) if self._graph else 0,
        }
        
    def _count_by_type(self) -> Dict[str, int]:
        """Count entities by type."""
        counts = defaultdict(int)
        for entity in self._entity_index.values():
            counts[entity.entity_type.value] += 1
        return dict(counts)
        
    def _count_by_relationship(self) -> Dict[str, int]:
        """Count relationships by type."""
        counts = defaultdict(int)
        for edge in self._edges:
            counts[edge.relationship.relationship_type.value] += 1
        return dict(counts)
        
    def to_json(self) -> Dict[str, Any]:
        """Serialize graph to JSON."""
        return {
            "nodes": [
                {
                    "entity_id": node.entity_id,
                    "entity": node.entity.to_dict() if hasattr(node.entity, 'to_dict') else str(node.entity),
                    "degree": node.degree,
                    "centrality": node.centrality,
                    "community": node.community,
                }
                for node in self._nodes.values()
            ],
            "edges": [
                {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "relationship_type": edge.relationship.relationship_type.value,
                    "confidence": edge.relationship.confidence,
                    "evidence": edge.relationship.evidence,
                }
                for edge in self._edges
            ],
            "statistics": self.get_statistics(),
        }
        
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "EntityGraph":
        """Deserialize graph from JSON."""
        graph = cls()
        # Note: Full deserialization would require Entity/Relationship reconstruction
        # This is a simplified version
        return graph
        
    def export_gexf(self, path: str) -> None:
        """Export graph to GEXF format for Gephi."""
        nx.write_gexf(self._graph, path)
        
    def export_graphml(self, path: str) -> None:
        """Export graph to GraphML format."""
        nx.write_graphml(self._graph, path)
        
    def __len__(self) -> int:
        return len(self._nodes)
        
    def __contains__(self, entity_id: str) -> bool:
        return entity_id in self._nodes
        
    def __iter__(self) -> Iterator[Entity]:
        return iter(self._entity_index.values())


# Singleton instance
_entity_graph: Optional[EntityGraph] = None


def get_entity_graph() -> EntityGraph:
    """Get or create the default entity graph."""
    global _entity_graph
    if _entity_graph is None:
        _entity_graph = EntityGraph()
    return _entity_graph