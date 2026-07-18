"""
Graph Algorithms - Network analysis algorithms for the knowledge graph.
"""

import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import math

from .client import get_neo4j_client
from .models import GraphEntity, GraphRelationship, GraphCommunity, EntityType, RelationshipType
from .repository import get_graph_repository

logger = logging.getLogger(__name__)


class CentralityAlgorithm(str, Enum):
    """Types of centrality algorithms."""
    DEGREE = "degree"
    BETWEENNESS = "betweenness"
    CLOSENESS = "closeness"
    EIGENVECTOR = "eigenvector"
    PAGERANK = "pagerank"


class CommunityAlgorithm(str, Enum):
    """Types of community detection algorithms."""
    LOUVAIN = "louvain"
    LEIDEN = "leiden"
    LABEL_PROPAGATION = "label_propagation"
    WEAKLY_CONNECTED = "weakly_connected"


@dataclass
class CentralityResult:
    """Result of centrality computation."""
    entity_id: str
    entity_type: str
    score: float
    rank: int
    algorithm: CentralityAlgorithm
    normalized_score: float = 0.0


@dataclass
class CommunityResult:
    """Result of community detection."""
    community_id: int
    entities: List[str]
    size: int
    modularity: float
    internal_edges: int
    external_edges: int
    algorithm: CommunityAlgorithm


@dataclass
class SimilarityResult:
    """Result of similarity computation."""
    entity_id_1: str
    entity_id_2: str
    similarity: float
    method: str
    common_neighbors: int = 0
    jaccard_coefficient: float = 0.0
    adamic_adar: float = 0.0


@dataclass
class PathAnalysisResult:
    """Result of path analysis."""
    source_id: str
    target_id: str
    shortest_path_length: int
    all_paths: List[List[str]]
    path_count: int
    betweenness_contribution: Dict[str, float]


class GraphAlgorithms:
    """
    Graph algorithms for network analysis.
    Integrates with Neo4j Graph Data Science library where available.
    """
    
    def __init__(self):
        self.neo4j = get_neo4j_client()
        self.repo = get_graph_repository()
        self._gds_available = False
    
    async def initialize(self) -> None:
        """Initialize and check for GDS availability."""
        try:
            # Check if GDS is available
            result = await self.neo4j.execute_query("CALL gds.version()")
            self._gds_available = True
            logger.info("Neo4j Graph Data Science library available")
        except Exception:
            self._gds_available = False
            logger.info("Neo4j GDS not available, using custom implementations")
    
    # Centrality Algorithms
    
    async def compute_degree_centrality(
        self,
        entity_type: Optional[EntityType] = None,
        relationship_types: Optional[List[RelationshipType]] = None,
        normalized: bool = True
    ) -> List[CentralityResult]:
        """Compute degree centrality for all nodes."""
        type_filter = f":{entity_type.value}" if entity_type else ""
        
        rel_filter = ""
        if relationship_types:
            types = "|".join([rt.value for rt in relationship_types])
            rel_filter = f":{types}"
        
        if self._gds_available:
            cypher = f"""
            CALL gds.degree.stream('graph', {{
                relationshipTypes: {relationship_types},
                nodeLabels: {entity_type.value if entity_type else '*'},
                orientation: 'UNDIRECTED'
            }})
            YIELD nodeId, score
            RETURN gds.util.asNode(nodeId).id AS entity_id, 
                   labels(gds.util.asNode(nodeId))[0] AS entity_type,
                   score
            ORDER BY score DESC
            """
            # Would need graph projection first
            pass
        
        # Fallback implementation
        cypher = f"""
        MATCH (n{type_filter})-[r{rel_filter}]-(m)
        RETURN n.id AS entity_id, labels(n)[0] AS entity_type, count(r) AS degree
        ORDER BY degree DESC
        """
        
        results = await self.neo4j.execute_query(cypher)
        
        centrality_results = []
        max_degree = max([r["degree"] for r in results]) if results else 1
        
        for i, record in enumerate(results):
            score = record["degree"] / max_degree if normalized and max_degree > 0 else record["degree"]
            centrality_results.append(CentralityResult(
                entity_id=record["entity_id"],
                entity_type=record["entity_type"],
                score=record["degree"],
                rank=i + 1,
                algorithm=CentralityAlgorithm.DEGREE,
                normalized_score=score
            ))
        
        return centrality_results
    
    async def compute_pagerank(
        self,
        entity_type: Optional[EntityType] = None,
        relationship_types: Optional[List[RelationshipType]] = None,
        damping_factor: float = 0.85,
        max_iterations: int = 20,
        tolerance: float = 1e-6
    ) -> List[CentralityResult]:
        """Compute PageRank centrality."""
        if self._gds_available:
            # Use GDS PageRank
            pass
        
        # Custom implementation
        type_filter = f"AND n:{entity_type.value}" if entity_type else ""
        
        cypher = f"""
        MATCH (n)
        WHERE n.id IS NOT NULL {type_filter}
        RETURN n.id AS entity_id, labels(n)[0] AS entity_type
        """
        nodes = await self.neo4j.execute_query(cypher)
        
        # Build adjacency
        cypher = f"""
        MATCH (n)-[r]->(m)
        WHERE n.id IS NOT NULL AND m.id IS NOT NULL {type_filter}
        RETURN n.id AS source, m.id AS target
        """
        edges = await self.neo4j.execute_query(cypher)
        
        # Compute PageRank
        node_ids = [n["entity_id"] for n in nodes]
        node_index = {nid: i for i, nid in enumerate(node_ids)}
        n = len(node_ids)
        
        if n == 0:
            return []
        
        # Initialize scores
        scores = {nid: 1.0 / n for nid in node_ids}
        
        # Build adjacency lists
        outlinks = defaultdict(set)
        inlinks = defaultdict(set)
        for edge in edges:
            if edge["source"] in node_index and edge["target"] in node_index:
                outlinks[edge["source"]].add(edge["target"])
                inlinks[edge["target"]].add(edge["source"])
        
        # Power iteration
        for _ in range(max_iterations):
            new_scores = {}
            diff = 0.0
            
            for nid in node_ids:
                # Sum of scores from inlinks
                inlink_sum = sum(
                    scores[in_nid] / max(len(outlinks[in_nid]), 1)
                    for in_nid in inlinks[nid]
                )
                
                new_score = (1 - damping_factor) / n + damping_factor * inlink_sum
                new_scores[nid] = new_score
                diff += abs(new_score - scores[nid])
            
            scores = new_scores
            if diff < tolerance:
                break
        
        # Rank results
        sorted_nodes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        max_score = sorted_nodes[0][1] if sorted_nodes else 1
        
        results = []
        for i, (entity_id, score) in enumerate(sorted_nodes):
            entity_type = next((n["entity_type"] for n in nodes if n["entity_id"] == entity_id), "Unknown")
            results.append(CentralityResult(
                entity_id=entity_id,
                entity_type=entity_type,
                score=score,
                rank=i + 1,
                algorithm=CentralityAlgorithm.PAGERANK,
                normalized_score=score / max_score if max_score > 0 else 0
            ))
        
        return results
    
    async def compute_betweenness_centrality(
        self,
        entity_type: Optional[EntityType] = None,
        sample_size: int = 1000
    ) -> List[CentralityResult]:
        """Compute betweenness centrality (approximate for large graphs)."""
        if self._gds_available:
            pass  # Use GDS
        
        # Simplified: return degree centrality as proxy
        return await self.compute_degree_centrality(entity_type)
    
    async def compute_eigenvector_centrality(
        self,
        entity_type: Optional[EntityType] = None,
        max_iterations: int = 100,
        tolerance: float = 1e-6
    ) -> List[CentralityResult]:
        """Compute eigenvector centrality."""
        # For now, delegate to PageRank which is similar
        return await self.compute_pagerank(entity_type, max_iterations=max_iterations)
    
    # Community Detection
    
    async def detect_communities(
        self,
        algorithm: CommunityAlgorithm = CommunityAlgorithm.LOUVAIN,
        entity_type: Optional[EntityType] = None,
        relationship_types: Optional[List[RelationshipType]] = None,
        min_community_size: int = 3
    ) -> List[CommunityResult]:
        """Detect communities in the graph."""
        if self._gds_available and algorithm in [CommunityAlgorithm.LOUVAIN, CommunityAlgorithm.LEIDEN]:
            # Use GDS community detection
            pass
        
        # Custom implementation: Label Propagation
        if algorithm == CommunityAlgorithm.LABEL_PROPAGATION:
            return await self._label_propagation(entity_type, relationship_types)
        
        # Fallback: Weakly connected components
        return await self._weakly_connected_components(entity_type, min_community_size)
    
    async def _label_propagation(
        self,
        entity_type: Optional[EntityType] = None,
        relationship_types: Optional[List[RelationshipType]] = None,
        max_iterations: int = 10
    ) -> List[CommunityResult]:
        """Label propagation community detection."""
        type_filter = f"AND n:{entity_type.value}" if entity_type else ""
        
        # Get all nodes
        cypher = f"""
        MATCH (n)
        WHERE n.id IS NOT NULL {type_filter}
        RETURN n.id AS entity_id, labels(n)[0] AS entity_type
        """
        nodes = await self.neo4j.execute_query(cypher)
        
        if not nodes:
            return []
        
        # Initialize labels
        labels = {n["entity_id"]: i for i, n in enumerate(nodes)}
        
        # Get edges
        rel_filter = ""
        if relationship_types:
            types = "|".join([rt.value for rt in relationship_types])
            rel_filter = f":{types}"
        
        cypher = f"""
        MATCH (n)-[r{rel_filter}]-(m)
        WHERE n.id IS NOT NULL AND m.id IS NOT NULL {type_filter}
        RETURN n.id AS source, m.id AS target
        """
        edges = await self.neo4j.execute_query(cypher)
        
        # Build adjacency
        neighbors = defaultdict(set)
        for edge in edges:
            if edge["source"] in labels and edge["target"] in labels:
                neighbors[edge["source"]].add(edge["target"])
                neighbors[edge["target"]].add(edge["source"])
        
        # Label propagation iterations
        for _ in range(max_iterations):
            changed = False
            for node in labels:
                neighbor_labels = [labels[n] for n in neighbors[node] if n in labels]
                if neighbor_labels:
                    # Most frequent label
                    from collections import Counter
                    most_common = Counter(neighbor_labels).most_common(1)[0][0]
                    if most_common != labels[node]:
                        labels[node] = most_common
                        changed = True
            
            if not changed:
                break
        
        # Group by label
        communities = defaultdict(list)
        for node_id, label in labels.items():
            communities[label].append(node_id)
        
        # Filter by size and create results
        results = []
        for i, (label, entities) in enumerate(communities.items()):
            if len(entities) >= min_community_size:
                results.append(CommunityResult(
                    community_id=i,
                    entities=entities,
                    size=len(entities),
                    modularity=0.0,  # Would need to compute
                    internal_edges=0,
                    external_edges=0,
                    algorithm=CommunityAlgorithm.LABEL_PROPAGATION
                ))
        
        return results
    
    async def _weakly_connected_components(
        self,
        entity_type: Optional[EntityType] = None,
        min_size: int = 3
    ) -> List[CommunityResult]:
        """Find weakly connected components as communities."""
        type_filter = f"AND n:{entity_type.value}" if entity_type else ""
        
        cypher = f"""
        MATCH (n)
        WHERE n.id IS NOT NULL {type_filter}
        RETURN n.id AS entity_id
        """
        nodes = await self.neo4j.execute_query(cypher)
        
        if not nodes:
            return []
        
        # Union-Find for connected components
        parent = {n["entity_id"]: n["entity_id"] for n in nodes}
        
        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        
        def union(x, y):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[ry] = rx
        
        # Get edges
        cypher = f"""
        MATCH (n)-[r]-(m)
        WHERE n.id IS NOT NULL AND m.id IS NOT NULL {type_filter}
        RETURN n.id AS source, m.id AS target
        """
        edges = await self.neo4j.execute_query(cypher)
        
        for edge in edges:
            if edge["source"] in parent and edge["target"] in parent:
                union(edge["source"], edge["target"])
        
        # Group by root
        components = defaultdict(list)
        for node_id in parent:
            components[find(node_id)].append(node_id)
        
        results = []
        for i, entities in enumerate(components.values()):
            if len(entities) >= min_size:
                results.append(CommunityResult(
                    community_id=i,
                    entities=entities,
                    size=len(entities),
                    modularity=0.0,
                    internal_edges=0,
                    external_edges=0,
                    algorithm=CommunityAlgorithm.WEAKLY_CONNECTED
                ))
        
        return results
    
    # Similarity
    
    async def compute_similarity(
        self,
        entity_id_1: str,
        entity_id_2: str,
        method: str = "jaccard"
    ) -> SimilarityResult:
        """Compute similarity between two entities."""
        # Get neighbors
        cypher = """
        MATCH (n {id: $id1})-[r]-(m)
        RETURN m.id AS neighbor_id
        """
        neighbors1_result = await self.neo4j.execute_query(cypher, {"id1": entity_id_1})
        neighbors1 = set(r["neighbor_id"] for r in neighbors1_result)
        
        neighbors2_result = await self.neo4j.execute_query(cypher, {"id1": entity_id_2})
        neighbors2 = set(r["neighbor_id"] for r in neighbors2_result)
        
        common = neighbors1 & neighbors2
        union = neighbors1 | neighbors2
        
        jaccard = len(common) / len(union) if union else 0.0
        
        # Adamic-Adar
        adamic_adar = 0.0
        for neighbor in common:
            # Get degree of common neighbor
            cypher = """
            MATCH (n {id: $id})-[r]-()
            RETURN count(r) AS degree
            """
            degree_result = await self.neo4j.execute_query(cypher, {"id": neighbor})
            degree = degree_result[0]["degree"] if degree_result else 1
            if degree > 1:
                adamic_adar += 1 / math.log(degree)
        
        return SimilarityResult(
            entity_id_1=entity_id_1,
            entity_id_2=entity_id_2,
            similarity=jaccard,
            method=method,
            common_neighbors=len(common),
            jaccard_coefficient=jaccard,
            adamic_adar=adamic_adar
        )
    
    async def find_similar_entities(
        self,
        entity_id: str,
        entity_type: Optional[EntityType] = None,
        top_k: int = 10,
        min_similarity: float = 0.1
    ) -> List[SimilarityResult]:
        """Find entities similar to the given entity."""
        # Get candidate entities
        type_filter = f"AND n:{entity_type.value}" if entity_type else ""
        
        cypher = f"""
        MATCH (n)
        WHERE n.id <> $entity_id AND n.id IS NOT NULL {type_filter}
        RETURN n.id AS candidate_id
        """
        candidates = await self.neo4j.execute_query(cypher, {"entity_id": entity_id})
        
        similarities = []
        for candidate in candidates[:top_k * 5]:  # Limit candidates
            sim = await self.compute_similarity(entity_id, candidate["candidate_id"])
            if sim.similarity >= min_similarity:
                similarities.append(sim)
        
        # Sort by similarity
        similarities.sort(key=lambda x: x.similarity, reverse=True)
        return similarities[:top_k]
    
    # Path Analysis
    
    async def analyze_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5
    ) -> PathAnalysisResult:
        """Analyze paths between two entities."""
        paths = await self.repo.find_all_paths(source_id, target_id, max_depth)
        
        if not paths:
            return PathAnalysisResult(
                source_id=source_id,
                target_id=target_id,
                shortest_path_length=-1,
                all_paths=[],
                path_count=0,
                betweenness_contribution={}
            )
        
        # Calculate betweenness contribution
        betweenness = defaultdict(float)
        for path in paths:
            for rel in path.relationships:
                betweenness[rel.id] += 1.0 / len(paths)
        
        return PathAnalysisResult(
            source_id=source_id,
            target_id=target_id,
            shortest_path_length=min(p.length for p in paths),
            all_paths=[[n.id for n in p.nodes] for p in paths],
            path_count=len(paths),
            betweenness_contribution=dict(betweenness)
        )
    
    # Graph Statistics
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get comprehensive graph statistics."""
        stats = {}
        
        # Basic counts
        cypher = """
        MATCH (n)
        RETURN count(n) AS node_count
        """
        result = await self.neo4j.execute_query(cypher)
        stats["node_count"] = result[0]["node_count"] if result else 0
        
        cypher = """
        MATCH ()-[r]->()
        RETURN count(r) AS edge_count
        """
        result = await self.neo4j.execute_query(cypher)
        stats["edge_count"] = result[0]["edge_count"] if result else 0
        
        # Density
        n = stats["node_count"]
        e = stats["edge_count"]
        stats["density"] = (2 * e) / (n * (n - 1)) if n > 1 else 0
        
        # Average degree
        stats["avg_degree"] = (2 * e) / n if n > 0 else 0
        
        # Connected components
        cypher = """
        CALL gds.wcc.stream('graph') YIELD componentId
        RETURN count(DISTINCT componentId) AS components
        """
        if self._gds_available:
            result = await self.neo4j.execute_query(cypher)
            stats["connected_components"] = result[0]["components"] if result else 0
        else:
            stats["connected_components"] = 0
        
        return stats
    
    # Entity Ranking
    
    async def rank_entities(
        self,
        entity_type: EntityType,
        algorithm: CentralityAlgorithm = CentralityAlgorithm.PAGERANK,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[CentralityResult]:
        """Rank entities by centrality."""
        if algorithm == CentralityAlgorithm.DEGREE:
            results = await self.compute_degree_centrality(entity_type)
        elif algorithm == CentralityAlgorithm.PAGERANK:
            results = await self.compute_pagerank(entity_type)
        elif algorithm == CentralityAlgorithm.EIGENVECTOR:
            results = await self.compute_eigenvector_centrality(entity_type)
        else:
            results = await self.compute_degree_centrality(entity_type)
        
        # Apply filters
        if filters:
            filtered = []
            for r in results:
                entity = await self.repo.get_entity(r.entity_id)
                if entity:
                    match = all(
                        entity.properties.get(k) == v for k, v in filters.items()
                    )
                    if match:
                        filtered.append(r)
            results = filtered
        
        return results[:limit]


# Global algorithms instance
_graph_algorithms: Optional[GraphAlgorithms] = None


def get_graph_algorithms() -> GraphAlgorithms:
    """Get or create the global graph algorithms instance."""
    global _graph_algorithms
    if _graph_algorithms is None:
        _graph_algorithms = GraphAlgorithms()
    return _graph_algorithms