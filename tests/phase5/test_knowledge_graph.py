"""
Phase 5 - Knowledge Graph Tests
"""
import pytest
from datetime import date, datetime
from data.knowledge_graph import (
    KnowledgeGraph, NodeType, RelationshipType, GraphNode, GraphEdge,
    PostgresGraphBackend, create_knowledge_graph
)


class TestGraphNode:
    """Test GraphNode dataclass."""
    
    def test_create_company_node(self):
        node = GraphNode(
            node_type=NodeType.COMPANY,
            name="Apple Inc.",
            label="AAPL",
            properties={"sector": "Technology", "market_cap": 3000000000000},
            confidence=0.95,
            source="entity_recognition"
        )
        assert node.node_type == NodeType.COMPANY
        assert node.name == "Apple Inc."
        assert node.properties["sector"] == "Technology"
        assert node.confidence == 0.95
        assert node.is_active is True
        assert node.version == 1
    
    def test_create_person_node(self):
        node = GraphNode(
            node_type=NodeType.PERSON,
            name="Tim Cook",
            label="CEO",
            properties={"title": "CEO", "since": 2011}
        )
        assert node.node_type == NodeType.PERSON
        assert node.name == "Tim Cook"
    
    def test_node_to_dict(self):
        node = GraphNode(
            node_type=NodeType.COMPANY,
            name="Microsoft",
            label="MSFT"
        )
        d = node.to_dict()
        assert d["node_type"] == "company"
        assert d["name"] == "Microsoft"
        assert d["label"] == "MSFT"


class TestGraphEdge:
    """Test GraphEdge dataclass."""
    
    def test_create_edge(self):
        edge = GraphEdge(
            source_id="node1",
            target_id="node2",
            relationship_type=RelationshipType.CEO_OF,
            properties={"since": 2011},
            confidence=0.99,
            weight=1.0,
            evidence=["filing_10k_2023"]
        )
        assert edge.source_id == "node1"
        assert edge.target_id == "node2"
        assert edge.relationship_type == RelationshipType.CEO_OF
        assert edge.confidence == 0.99
        assert edge.evidence == ["filing_10k_2023"]
    
    def test_edge_to_dict(self):
        edge = GraphEdge(
            source_id="n1",
            target_id="n2",
            relationship_type=RelationshipType.COMPETES_WITH
        )
        d = edge.to_dict()
        assert d["relationship_type"] == "COMPETES_WITH"
        assert d["source_id"] == "n1"
        assert d["target_id"] == "n2"


class TestNodeType:
    """Test NodeType enum."""
    
    def test_all_node_types(self):
        expected = ["company", "person", "product", "industry", "sector", 
                    "country", "event", "filing", "metric", "news", 
                    "pattern", "portfolio", "alert"]
        actual = [nt.value for nt in NodeType]
        assert set(actual) == set(expected)


class TestRelationshipType:
    """Test RelationshipType enum."""
    
    def test_company_relationships(self):
        company_rels = [rt for rt in RelationshipType if rt.value in 
                       ["HAS_TICKER", "CEO_OF", "COMPETES_WITH", "PARTNERS_WITH",
                        "SUBSIDIARY_OF", "ACQUIRED", "INVESTS_IN", "OWNS"]]
        assert len(company_rels) >= 8
    
    def test_filing_relationships(self):
        filing_rels = [rt for rt in RelationshipType if rt.value in 
                      ["FILED", "REPORTED_IN", "CONTAINS", "MENTIONS", "REFERENCES"]]
        assert len(filing_rels) >= 5


class TestKnowledgeGraphIntegration:
    """Integration tests for KnowledgeGraph (requires database)."""
    
    @pytest.mark.asyncio
    async def test_create_knowledge_graph(self):
        import os
        db_name = os.getenv("POSTGRES_DB", "financial_research_agent")
        db_user = os.getenv("POSTGRES_USER", "postgres")
        db_pass = os.getenv("POSTGRES_PASSWORD", "postgres")
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        
        dsn = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        kg = await create_knowledge_graph(
            dsn=dsn,
            pool_size=5
        )
        assert kg is not None
        await kg.close()
    
    @pytest.mark.asyncio
    async def test_add_company_with_ceo(self):
        import os
        db_name = os.getenv("POSTGRES_DB", "financial_research_agent")
        db_user = os.getenv("POSTGRES_USER", "postgres")
        db_pass = os.getenv("POSTGRES_PASSWORD", "postgres")
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        
        dsn = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        kg = await create_knowledge_graph(
            dsn=dsn,
            pool_size=5
        )
        
        # Add company
        company = await kg.add_node(
            node_type=NodeType.COMPANY,
            name="Apple Inc.",
            label="AAPL",
            properties={"sector": "Technology", "exchange": "NASDAQ"}
        )
        
        # Add CEO
        ceo = await kg.add_node(
            node_type=NodeType.PERSON,
            name="Tim Cook",
            label="CEO",
            properties={"title": "CEO"}
        )
        
        # Create relationship
        edge = await kg.add_edge(
            source_id=ceo.id,
            target_id=company.id,
            relationship_type=RelationshipType.CEO_OF,
            confidence=0.99
        )
        
        assert company.id is not None
        assert ceo.id is not None
        assert edge.relationship_type == RelationshipType.CEO_OF
        
        await kg.close()


class TestPostgresGraphBackend:
    """Test PostgresGraphBackend methods."""
    
    @pytest.mark.asyncio
    async def test_node_crud(self):
        import os
        db_name = os.getenv("POSTGRES_DB", "financial_research_agent")
        db_user = os.getenv("POSTGRES_USER", "postgres")
        db_pass = os.getenv("POSTGRES_PASSWORD", "postgres")
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        
        dsn = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        backend = PostgresGraphBackend(dsn=dsn, pool_size=5)
        await backend.connect()
        
        node = GraphNode(
            node_type=NodeType.COMPANY,
            name="Test Corp",
            label="TEST"
        )
        await backend.create_node(node)
        
        retrieved = await backend.get_node(node.id)
        assert retrieved is not None
        assert retrieved.name == "Test Corp"
        
        node.name = "Updated Corp"
        await backend.update_node(node)
        
        retrieved = await backend.get_node(node.id)
        assert retrieved.name == "Updated Corp"
        
        await backend.delete_node(node.id)
        retrieved = await backend.get_node(node.id)
        assert retrieved is None
        
        await backend.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])