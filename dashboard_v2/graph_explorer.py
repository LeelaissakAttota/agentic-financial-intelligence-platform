"""
Graph Explorer
Interactive knowledge graph explorer for the Enterprise Dashboard v2.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class GraphLayout(str, Enum):
    """Graph layout algorithms."""
    FORCE_DIRECTED = "force_directed"
    HIERARCHICAL = "hierarchical"
    CIRCULAR = "circular"
    GRID = "grid"
    RADIAL = "radial"
    CONCENTRIC = "concentric"


class NodeCategory(str, Enum):
    """Node categories in the knowledge graph."""
    COMPANY = "company"
    PERSON = "person"
    PRODUCT = "product"
    SECTOR = "sector"
    INDUSTRY = "industry"
    MARKET_INDEX = "market_index"
    FINANCIAL_METRIC = "financial_metric"
    EVENT = "event"
    NEWS_ARTICLE = "news_article"
    EARNINGS_CALL = "earnings_call"
    SEC_FILING = "sec_filing"
    ANALYST_REPORT = "analyst_report"
    REGULATORY_BODY = "regulatory_body"
    GEOGRAPHY = "geography"


class EdgeType(str, Enum):
    """Edge types in the knowledge graph."""
    COMPETES_WITH = "competes_with"
    PARTNERS_WITH = "partners_with"
    SUPPLIES_TO = "supplies_to"
    ACQUIRED = "acquired"
    MERGED_WITH = "merged_with"
    SUBSIDIARY_OF = "subsidiary_of"
    WORKS_FOR = "works_for"
    BOARD_MEMBER_OF = "board_member_of"
    ADVISES = "advises"
    FOUNDED = "founded"
    PRODUCES = "produces"
    COMPETES_WITH_PRODUCT = "competes_with_product"
    OPERATES_IN = "operates_in"
    PART_OF = "part_of"
    HAS_METRIC = "has_metric"
    REPORTED_IN = "reported_in"
    MENTIONED_IN = "mentioned_in"
    CITES = "cites"
    REFERENCES = "references"
    ANALYZES = "analyzes"
    TRIGGERED = "triggered"
    IMPACTED = "impacted"
    RELATED_TO = "related_to"


@dataclass
class GraphNode:
    """Node in the knowledge graph."""
    id: str
    category: NodeCategory
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)
    position: Optional[Dict[str, float]] = None  # x, y
    size: float = 1.0
    color: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """Edge in the knowledge graph."""
    id: str
    source: str
    target: str
    type: EdgeType
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphPath:
    """Path in the knowledge graph."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    length: int
    weight: float = 0.0


@dataclass
class GraphCommunity:
    """Community/cluster in the graph."""
    id: str
    name: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    centrality_scores: Dict[str, float] = field(default_factory=dict)
    modularity: float = 0.0
    size: int = 0


@dataclass
class GraphQuery:
    """Query for graph exploration."""
    query_id: str
    query_type: str  # "neighbors", "path", "community", "similarity", "centrality"
    parameters: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "pending"  # pending, running, completed, failed
    results: Optional[Dict[str, Any]] = None


class GraphExplorer:
    """
    Interactive knowledge graph explorer.
    Provides graph visualization, path finding, community detection, and similarity search.
    """
    
    def __init__(self):
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: Dict[str, GraphEdge] = {}
        self._adjacency: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)
        self._node_index: Dict[NodeCategory, Set[str]] = defaultdict(set)
        self._edge_index: Dict[EdgeType, Set[str]] = defaultdict(set)
        self._communities: Dict[str, GraphCommunity] = {}
        self._layout_cache: Dict[str, Dict[str, Dict[str, float]]] = {}
        self._queries: Dict[str, GraphQuery] = {}
        self._layout_algorithm: GraphLayout = GraphLayout.FORCE_DIRECTED
    
    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph."""
        self._nodes[node.id] = node
        self._node_index[node.category].add(node.id)
        
        # Initialize adjacency
        if node.id not in self._adjacency:
            self._adjacency[node.id] = set()
        if node.id not in self._reverse_adjacency:
            self._reverse_adjacency[node.id] = set()
        
        logger.debug(f"Added node: {node.id} ({node.category.value})")
    
    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the graph."""
        self._edges[edge.id] = edge
        self._edge_index[edge.type].add(edge.id)
        
        # Update adjacency
        self._adjacency[edge.source].add(edge.target)
        self._reverse_adjacency[edge.target].add(edge.source)
        
        logger.debug(f"Added edge: {edge.id} ({edge.source} -> {edge.target})")
    
    def add_nodes_batch(self, nodes: List[GraphNode]) -> None:
        """Add multiple nodes at once."""
        for node in nodes:
            self.add_node(node)
    
    def add_edges_batch(self, edges: List[GraphEdge]) -> None:
        """Add multiple edges at once."""
        for edge in edges:
            self.add_edge(edge)
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID."""
        return self._nodes.get(node_id)
    
    def get_edge(self, edge_id: str) -> Optional[GraphEdge]:
        """Get an edge by ID."""
        return self._edges.get(edge_id)
    
    def get_neighbors(
        self,
        node_id: str,
        direction: str = "both",  # "out", "in", "both"
        edge_types: Optional[List[EdgeType]] = None,
        max_depth: int = 1
    ) -> List[GraphNode]:
        """Get neighbors of a node."""
        
        if node_id not in self._nodes:
            return []
        
        if max_depth == 1:
            neighbors = set()
            
            if direction in ["out", "both"]:
                neighbors.update(self._adjacency.get(node_id, set()))
            
            if direction in ["in", "both"]:
                neighbors.update(self._reverse_adjacency.get(node_id, set()))
            
            # Filter by edge type if specified
            if edge_types:
                filtered = set()
                for neighbor_id in neighbors:
                    # Check edge types between node_id and neighbor_id
                    for edge_id in self._get_edge_ids(node_id, neighbor_id):
                        edge = self._edges.get(edge_id)
                        if edge and edge.type in edge_types:
                            filtered.add(neighbor_id)
                            break
                neighbors = filtered
            
            return [self._nodes[nid] for nid in neighbors if nid in self._nodes]
        
        # Multi-hop neighbors (BFS)
        visited = {node_id}
        current_level = {node_id}
        all_neighbors = set()
        
        for _ in range(max_depth):
            next_level = set()
            for nid in current_level:
                neighbors = set()
                if direction in ["out", "both"]:
                    neighbors.update(self._adjacency.get(nid, set()))
                if direction in ["in", "both"]:
                    neighbors.update(self._reverse_adjacency.get(nid, set()))
                
                for neighbor in neighbors:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_level.add(neighbor)
                        all_neighbors.add(neighbor)
            
            current_level = next_level
        
        return [self._nodes[nid] for nid in all_neighbors if nid in self._nodes]
    
    def _get_edge_ids(self, source: str, target: str) -> List[str]:
        """Get edge IDs between two nodes."""
        edge_ids = []
        for edge_id in self._edges:
            edge = self._edges[edge_id]
            if edge.source == source and edge.target == target:
                edge_ids.append(edge_id)
        return edge_ids
    
    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
        edge_types: Optional[List[EdgeType]] = None
    ) -> Optional[GraphPath]:
        """Find shortest path between two nodes."""
        
        if source_id not in self._nodes or target_id not in self._nodes:
            return None
        
        # BFS
        queue = [(source_id, [source_id])]
        visited = {source_id}
        
        while queue:
            current, path = queue.pop(0)
            
            if current == target_id:
                # Build path
                nodes = [self._nodes[nid] for nid in path]
                edges = []
                for i in range(len(path) - 1):
                    edge_ids = self._get_edge_ids(path[i], path[i+1])
                    if edge_ids:
                        edges.append(self._edges[edge_ids[0]])
                
                return GraphPath(
                    nodes=nodes,
                    edges=edges,
                    length=len(path) - 1,
                    weight=len(edges)
                )
            
            if len(path) >= max_depth:
                continue
            
            # Get neighbors
            neighbors = set()
            if direction in ["out", "both"]:
                neighbors.update(self._adjacency.get(current, set()))
            if direction in ["in", "both"]:
                neighbors.update(self._reverse_adjacency.get(current, set()))
            
            for neighbor in neighbors:
                if neighbor not in visited:
                    # Check edge type filter
                    if edge_types:
                        valid = False
                        for edge_id in self._get_edge_ids(current, neighbor):
                            edge = self._edges.get(edge_id)
                            if edge and edge.type in edge_types:
                                valid = True
                                break
                        if not valid:
                            continue
                    
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None
    
    def find_all_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 4,
        max_paths: int = 10,
        edge_types: Optional[List[EdgeType]] = None
    ) -> List[GraphPath]:
        """Find all paths between two nodes up to max_paths."""
        
        paths = []
        
        def dfs(current, path, depth):
            if len(paths) >= max_paths:
                return
            
            if current == target_id:
                # Build path
                nodes = [self._nodes[nid] for nid in path]
                edges = []
                for i in range(len(path) - 1):
                    edge_ids = self._get_edge_ids(path[i], path[i+1])
                    if edge_ids:
                        edges.append(self._edges[edge_ids[0]])
                
                paths.append(GraphPath(
                    nodes=nodes,
                    edges=edges,
                    length=len(path) - 1
                ))
                return
            
            if depth >= max_depth:
                return
            
            # Get neighbors
            neighbors = set()
            neighbors.update(self._adjacency.get(current, set()))
            neighbors.update(self._reverse_adjacency.get(current, set()))
            
            for neighbor in neighbors:
                if neighbor not in path:
                    if edge_types:
                        valid = False
                        for edge_id in self._get_edge_ids(current, neighbor):
                            edge = self._edges.get(edge_id)
                            if edge and edge.type in edge_types:
                                valid = True
                                break
                        if not valid:
                            continue
                    
                    dfs(neighbor, path + [neighbor], depth + 1)
        
        dfs(source_id, [source_id], 0)
        return paths
    
    def detect_communities(
        self,
        algorithm: str = "louvain",
        min_size: int = 3
    ) -> List[GraphCommunity]:
        """Detect communities in the graph."""
        
        # Simplified community detection using connected components
        # In production, would use proper Louvain/Leiden algorithm
        
        visited = set()
        communities = []
        
        for node_id in self._nodes:
            if node_id in visited:
                continue
            
            # BFS to find connected component
            component = set()
            queue = [node_id]
            
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                
                visited.add(current)
                component.add(current)
                
                for neighbor in self._adjacency.get(current, set()):
                    if neighbor not in visited:
                        queue.append(neighbor)
                for neighbor in self._reverse_adjacency.get(current, set()):
                    if neighbor not in visited:
                        queue.append(neighbor)
            
            if len(component) >= min_size:
                # Create community
                community_nodes = [self._nodes[nid] for nid in component]
                community_edges = []
                
                for nid in component:
                    for edge_id in self._get_node_edges(nid):
                        edge = self._edges.get(edge_id)
                        if edge and edge.source in component and edge.target in component:
                            community_edges.append(edge)
                
                community = GraphCommunity(
                    id=f"comm_{len(communities)}",
                    name=f"Community {len(communities) + 1}",
                    nodes=community_nodes,
                    edges=community_edges,
                    size=len(component)
                )
                
                communities.append(community)
        
        self._communities = {c.id: c for c in communities}
        return communities
    
    def _get_node_edges(self, node_id: str) -> List[str]:
        """Get edge IDs for a node."""
        edges = []
        for edge_id, edge in self._edges.items():
            if edge.source == node_id or edge.target == node_id:
                edges.append(edge_id)
        return edges
    
    def find_similar_nodes(
        self,
        node_id: str,
        top_k: int = 10,
        similarity_metric: str = "jaccard"
    ) -> List[Tuple[GraphNode, float]]:
        """Find nodes similar to the given node."""
        
        if node_id not in self._nodes:
            return []
        
        # Get neighbors of the node
        target_neighbors = self._adjacency.get(node_id, set()) | self._reverse_adjacency.get(node_id, set())
        
        similarities = []
        
        for other_id, other_node in self._nodes.items():
            if other_id == node_id:
                continue
            
            other_neighbors = self._adjacency.get(other_id, set()) | self._reverse_adjacency.get(other_id, set())
            
            # Jaccard similarity
            if similarity_metric == "jaccard":
                intersection = len(target_neighbors & other_neighbors)
                union = len(target_neighbors | other_neighbors)
                similarity = intersection / union if union > 0 else 0
            
            elif similarity_metric == "cosine":
                # Cosine similarity of adjacency vectors
                # Simplified
                similarity = 0.5
            
            else:
                similarity = 0
            
            if similarity > 0:
                similarities.append((other_node, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def compute_centrality(
        self,
        centrality_type: str = "degree",
        top_k: int = 20
    ) -> List[Tuple[str, float]]:
        """Compute node centrality measures."""
        
        if centrality_type == "degree":
            scores = {nid: len(self._adjacency.get(nid, set())) + len(self._reverse_adjacency.get(nid, set())) 
                     for nid in self._nodes}
        
        elif centrality_type == "betweenness":
            # Simplified betweenness (would use proper algorithm in production)
            scores = {}
            for nid in self._nodes:
                scores[nid] = np.random.random()  # Placeholder
        
        elif centrality_type == "pagerank":
            # Simplified PageRank
            scores = {nid: 1.0 / len(self._nodes) for nid in self._nodes}
            for _ in range(20):
                new_scores = {}
                for nid in self._nodes:
                    rank = 0.15 / len(self._nodes)
                    for pred in self._reverse_adjacency.get(nid, set()):
                        out_degree = len(self._adjacency.get(pred, set()))
                        if out_degree > 0:
                            rank += 0.85 * scores[pred] / out_degree
                    new_scores[nid] = rank
                scores = new_scores
        
        else:
            scores = {nid: 0.0 for nid in self._nodes}
        
        # Sort and return top k
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:top_k]
    
    def get_subgraph(
        self,
        node_ids: List[str],
        include_edges: bool = True
    ) -> Dict[str, Any]:
        """Extract a subgraph."""
        
        nodes = {nid: self._nodes[nid] for nid in node_ids if nid in self._nodes}
        edges = []
        
        if include_edges:
            for edge_id, edge in self._edges.items():
                if edge.source in node_ids and edge.target in node_ids:
                    edges.append(edge)
        
        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges)
        }
    
    def compute_layout(
        self,
        algorithm: GraphLayout = GraphLayout.FORCE_DIRECTED,
        dimensions: int = 2,
        iterations: int = 100
    ) -> Dict[str, Dict[str, float]]:
        """Compute node positions for visualization."""
        
        # Check cache
        cache_key = f"{algorithm.value}_{dimensions}d_{iterations}"
        if cache_key in self._layout_cache:
            return self._layout_cache[cache_key]
        
        positions = {}
        
        if algorithm == GraphLayout.FORCE_DIRECTED:
            positions = self._force_directed_layout(iterations, dimensions)
        elif algorithm == GraphLayout.CIRCULAR:
            positions = self._circular_layout()
        elif algorithm == GraphLayout.GRID:
            positions = self._grid_layout()
        elif algorithm == GraphLayout.HIERARCHICAL:
            positions = self._hierarchical_layout()
        else:
            positions = self._random_layout()
        
        self._layout_cache[cache_key] = positions
        return positions
    
    def _force_directed_layout(self, iterations: int, dimensions: int) -> Dict[str, Dict[str, float]]:
        """Force-directed layout (Fruchterman-Reingold)."""
        
        nodes = list(self._nodes.keys())
        n = len(nodes)
        
        if n == 0:
            return {}
        
        # Initialize positions randomly
        pos = {}
        for node_id in nodes:
            pos[node_id] = {f"d{i}": np.random.uniform(-1, 1) for i in range(dimensions)}
        
        # Parameters
        k = 1.0 / np.sqrt(n) if n > 0 else 1.0
        temp = 0.1
        
        for iteration in range(iterations):
            # Calculate forces
            disp = {nid: {f"d{i}": 0.0 for i in range(dimensions)} for nid in nodes}
            
            # Repulsive forces
            for i, u in enumerate(nodes):
                for v in nodes[i+1:]:
                    delta = {}
                    dist_sq = 0
                    for d in range(dimensions):
                        diff = pos[u][f"d{d}"] - pos[v][f"d{d}"]
                        delta[f"d{d}"] = diff
                        dist_sq += diff * diff
                    
                    dist = max(np.sqrt(dist_sq), 0.01)
                    force = k * k / dist
                    
                    for d in range(dimensions):
                        disp[u][f"d{d}"] += delta[f"d{d}"] / dist * force
                        disp[v][f"d{d}"] -= delta[f"d{d}"] / dist * force
            
            # Attractive forces (edges)
            for edge_id, edge in self._edges.items():
                u, v = edge.source, edge.target
                if u not in pos or v not in pos:
                    continue
                
                delta = {}
                dist_sq = 0
                for d in range(dimensions):
                    diff = pos[v][f"d{d}"] - pos[u][f"d{d}"]
                    delta[f"d{d}"] = diff
                    dist_sq += diff * diff
                
                dist = max(np.sqrt(dist_sq), 0.01)
                force = dist * dist / k
                
                for d in range(dimensions):
                    disp[u][f"d{d}"] += delta[f"d{d}"] / dist * force
                    disp[v][f"d{d}"] -= delta[f"d{d}"] / dist * force
            
            # Update positions
            for node_id in nodes:
                for d in range(dimensions):
                    displacement = disp[node_id][f"d{d}"]
                    pos[node_id][f"d{d}"] += min(displacement, temp)
            
        
        # Convert to x, y format
        result = {}
        for node_id, coords in pos.items():
            if dimensions == 2:
                result[node_id] = {"x": coords.get("d0", 0), "y": coords.get("d1", 0)}
            elif dimensions == 3:
                result[node_id] = {"x": coords.get("d0", 0), "y": coords.get("d1", 0), "z": coords.get("d2", 0)}
        
        return result
    
    def _circular_layout(self) -> Dict[str, Dict[str, float]]:
        """Circular layout."""
        nodes = list(self._nodes.keys())
        n = len(nodes)
        
        positions = {}
        for i, node_id in enumerate(nodes):
            angle = 2 * np.pi * i / n
            positions[node_id] = {"x": np.cos(angle), "y": np.sin(angle)}
        
        return positions
    
    def _grid_layout(self) -> Dict[str, Dict[str, float]]:
        """Grid layout."""
        nodes = list(self._nodes.keys())
        n = len(nodes)
        
        cols = int(np.ceil(np.sqrt(n)))
        rows = int(np.ceil(n / cols))
        
        positions = {}
        for i, node_id in enumerate(nodes):
            row = i // cols
            col = i % cols
            positions[node_id] = {
                "x": (col - cols / 2) / max(cols, 1),
                "y": (row - rows / 2) / max(rows, 1)
            }
        
        return positions
    
    def _hierarchical_layout(self) -> Dict[str, Dict[str, float]]:
        """Hierarchical layout (simplified)."""
        # Would use topological sort for DAGs
        return self._grid_layout()
    
    def _random_layout(self) -> Dict[str, Dict[str, float]]:
        """Random layout."""
        positions = {}
        for node_id in self._nodes:
            positions[node_id] = {
                "x": np.random.uniform(-1, 1),
                "y": np.random.uniform(-1, 1)
            }
        return positions
    
    def set_layout_algorithm(self, algorithm: GraphLayout) -> None:
        """Set the default layout algorithm."""
        self._layout_algorithm = algorithm
        self._layout_cache.clear()
    
    def export_graph(self, format: str = "json") -> str:
        """Export graph in various formats."""
        
        if format == "json":
            data = {
                "nodes": [self._node_to_dict(n) for n in self._nodes.values()],
                "edges": [self._edge_to_dict(e) for e in self._edges.values()]
            }
            return json.dumps(data, indent=2, default=str)
        
        elif format == "graphml":
            # GraphML export
            lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                     '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
                     '  <graph id="G" edgedefault="directed">']
            
            for node in self._nodes.values():
                lines.append(f'    <node id="{node.id}">')
                for k, v in node.properties.items():
                    lines.append(f'      <data key="{k}">{v}</data>')
                lines.append('    </node>')
            
            for edge in self._edges.values():
                lines.append(f'    <edge id="{edge.id}" source="{edge.source}" target="{edge.target}"/>')
            
            lines.extend(['  </graph>', '</graphml>'])
            return '\n'.join(lines)
        
        return ""
    
    def _node_to_dict(self, node: GraphNode) -> Dict[str, Any]:
        return {
            "id": node.id,
            "category": node.category.value,
            "label": node.label,
            "properties": node.properties,
            "position": node.position,
            "size": node.size,
            "color": node.color,
            "metadata": node.metadata
        }
    
    def _edge_to_dict(self, edge: GraphEdge) -> Dict[str, Any]:
        return {
            "id": edge.id,
            "source": edge.source,
            "target": edge.target,
            "type": edge.type.value,
            "weight": edge.weight,
            "properties": edge.properties,
            "metadata": edge.metadata
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        
        return {
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "categories": {cat.value: len(ids) for cat, ids in self._node_index.items()},
            "edge_types": {et.value: len(ids) for et, ids in self._edge_index.items()},
            "avg_degree": np.mean([len(self._adjacency.get(n, set())) + len(self._reverse_adjacency.get(n, set())) 
                                   for n in self._nodes]) if self._nodes else 0,
            "density": len(self._edges) / (len(self._nodes) * (len(self._nodes) - 1)) if len(self._nodes) > 1 else 0,
            "connected_components": len(self._detect_components()),
            "communities": len(self._communities)
        }
    
    def _detect_components(self) -> List[Set[str]]:
        """Detect connected components."""
        visited = set()
        components = []
        
        for node_id in self._nodes:
            if node_id in visited:
                continue
            
            component = set()
            queue = [node_id]
            
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                
                visited.add(current)
                component.add(current)
                
                for neighbor in self._adjacency.get(current, set()):
                    if neighbor not in visited:
                        queue.append(neighbor)
                for neighbor in self._reverse_adjacency.get(current, set()):
                    if neighbor not in visited:
                        queue.append(neighbor)
            
            components.append(component)
        
        return components
    
    def clear(self) -> None:
        """Clear the graph."""
        self._nodes.clear()
        self._edges.clear()
        self._adjacency.clear()
        self._reverse_adjacency.clear()
        self._node_index.clear()
        self._edge_index.clear()
        self._communities.clear()
        self._layout_cache.clear()
        logger.info("Graph cleared")


# Global graph explorer instance
_graph_explorer: Optional[GraphExplorer] = None


def get_graph_explorer() -> GraphExplorer:
    global _graph_explorer
    if _graph_explorer is None:
        _graph_explorer = GraphExplorer()
    return _graph_explorer


async def close_graph_explorer() -> None:
    global _graph_explorer
    if _graph_explorer:
        _graph_explorer.clear()
        _graph_explorer = None