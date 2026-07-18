"""
Enterprise Neo4j Knowledge Graph Module
Provides persistent graph storage, Cypher query interface, and graph algorithms
for the Agentic Financial Intelligence Platform.
"""

from .client import Neo4jClient, get_neo4j_client
from .models import GraphEntity, GraphRelationship, GraphPath, GraphCommunity
from .repository import GraphRepository, get_graph_repository
from .algorithms import GraphAlgorithms, get_graph_algorithms
from .schema import GraphSchema, get_graph_schema
from .sync import GraphSyncManager, get_graph_sync_manager

__all__ = [
    "Neo4jClient",
    "get_neo4j_client",
    "GraphEntity",
    "GraphRelationship", 
    "GraphPath",
    "GraphCommunity",
    "GraphRepository",
    "get_graph_repository",
    "GraphAlgorithms",
    "get_graph_algorithms",
    "GraphSchema",
    "get_graph_schema",
    "GraphSyncManager",
    "get_graph_sync_manager",
]

__version__ = "1.0.0-phase9"