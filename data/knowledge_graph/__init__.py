"""
Knowledge Graph Module - Phase 5: Knowledge Persistence & Advanced Analytics

Provides graph persistence for financial entities and relationships using PostgreSQL.
Enables cross-agent knowledge sharing through graph structure.
"""

from data.knowledge_graph.graph import (
    NodeType,
    RelationshipType,
    GraphNode,
    GraphEdge,
    GraphBackend,
    PostgresGraphBackend,
    KnowledgeGraph,
    create_knowledge_graph,
)

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