"""
Graph Repository - High-level data access layer for Neo4j operations.
"""

import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime

from .client import get_neo4j_client
from .models import (
    GraphEntity, GraphRelationship, GraphPath, GraphCommunity,
    EntityType, RelationshipType, GraphQueryResult
)

logger = logging.getLogger(__name__)


@dataclass
class QueryOptions:
    """Options for graph queries."""
    limit: int = 100
    offset: int = 0
    include_properties: bool = True
    include_relationships: bool = True
    min_confidence: float = 0.0
    max_depth: int = 3
    relationship_types: Optional[List[RelationshipType]] = None
    entity_types: Optional[List[EntityType]] = None


class GraphRepository:
    """
    High-level repository for graph operations.
    Provides type-safe methods for common graph queries.
    """
    
    def __init__(self):
        self.neo4j = get_neo4j_client()
    
    # Entity operations
    
    async def get_entity(self, entity_id: str) -> Optional[GraphEntity]:
        """Get a single entity by ID."""
        cypher = "MATCH (n {id: $id}) RETURN n"
        results = await self.neo4j.execute_query(cypher, {"id": entity_id})
        if results:
            return GraphEntity.from_record(results[0])
        return None
    
    async def get_entities(
        self,
        entity_type: Optional[EntityType] = None,
        filters: Optional[Dict[str, Any]] = None,
        options: Optional[QueryOptions] = None
    ) -> List[GraphEntity]:
        """Get entities with optional filtering."""
        options = options or QueryOptions()
        where_clauses = []
        params = {"limit": options.limit, "offset": options.offset}
        
        if entity_type:
            where_clauses.append(f"n:{entity_type.value}")
        
        if filters:
            for key, value in filters.items():
                where_clauses.append(f"n.{key} = ${key}")
                params[key] = value
        
        where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        cypher = f"""
        MATCH (n)
        {where_clause}
        RETURN n
        SKIP $offset LIMIT $limit
        """
        
        results = await self.neo4j.execute_query(cypher, params)
        return [GraphEntity.from_record(r) for r in results]
    
    async def create_entity(self, entity: GraphEntity) -> GraphEntity:
        """Create a new entity."""
        cypher = f"""
        CREATE (n:{entity.type.value} $properties)
        SET n.id = $id, n.type = $type, n.created_at = datetime($created_at), n.updated_at = datetime($updated_at)
        RETURN n
        """
        params = entity.to_cypher_params()
        results = await self.neo4j.execute_write(cypher, params)
        if results:
            return GraphEntity.from_record(results[0])
        return entity
    
    async def update_entity(self, entity: GraphEntity) -> GraphEntity:
        """Update an existing entity."""
        entity.updated_at = datetime.utcnow()
        entity.version += 1
        
        cypher = """
        MATCH (n {id: $id})
        SET n += $properties,
            n.updated_at = datetime($updated_at),
            n.version = $version
        RETURN n
        """
        params = entity.to_cypher_params()
        results = await self.neo4j.execute_write(cypher, params)
        if results:
            return GraphEntity.from_record(results[0])
        return entity
    
    async def upsert_entity(self, entity: GraphEntity) -> GraphEntity:
        """Create or update an entity."""
        cypher = f"""
        MERGE (n:{entity.type.value} {{id: $id}})
        SET n += $properties,
            n.type = $type,
            n.updated_at = datetime($updated_at),
            n.version = coalesce(n.version, 0) + 1
        RETURN n
        """
        params = entity.to_cypher_params()
        results = await self.neo4j.execute_write(cypher, params)
        if results:
            return GraphEntity.from_record(results[0])
        return entity
    
    async def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity and its relationships."""
        cypher = """
        MATCH (n {id: $id})
        DETACH DELETE n
        RETURN count(n) as deleted
        """
        results = await self.neo4j.execute_write(cypher, {"id": entity_id})
        return results[0].get("deleted", 0) > 0 if results else False
    
    # Relationship operations
    
    async def get_relationships(
        self,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        rel_type: Optional[RelationshipType] = None,
        options: Optional[QueryOptions] = None
    ) -> List[GraphRelationship]:
        """Get relationships with optional filters."""
        options = options or QueryOptions()
        where_clauses = []
        params = {"limit": options.limit, "offset": options.offset}
        
        if source_id:
            where_clauses.append("source.id = $source_id")
            params["source_id"] = source_id
        
        if target_id:
            where_clauses.append("target.id = $target_id")
            params["target_id"] = target_id
        
        if rel_type:
            where_clauses.append(f"type(r) = $rel_type")
            params["rel_type"] = rel_type.value
        
        where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        cypher = f"""
        MATCH (source)-[r]->(target)
        {where_clause}
        RETURN r, source, target
        SKIP $offset LIMIT $limit
        """
        
        results = await self.neo4j.execute_query(cypher, params)
        relationships = []
        for record in results:
            rel_data = dict(record.get("r", {}))
            rel_data["source_id"] = record.get("source", {}).get("id")
            rel_data["target_id"] = record.get("target", {}).get("id")
            rel = GraphRelationship(
                id=rel_data.get("id", ""),
                type=RelationshipType(rel_data.get("type", "RELATED_TO")),
                source_id=rel_data.get("source_id", ""),
                target_id=rel_data.get("target_id", ""),
                properties=rel_data,
            )
            relationships.append(rel)
        
        return relationships
    
    async def create_relationship(self, relationship: GraphRelationship) -> GraphRelationship:
        """Create a new relationship."""
        cypher = f"""
        MATCH (source {{id: $source_id}}), (target {{id: $target_id}})
        CREATE (source)-[r:{relationship.type.value} $properties]->(target)
        SET r.id = $id, r.created_at = datetime($created_at), r.updated_at = datetime($updated_at)
        RETURN r
        """
        params = relationship.to_cypher_params()
        results = await self.neo4j.execute_write(cypher, params)
        return relationship
    
    async def upsert_relationship(self, relationship: GraphRelationship) -> GraphRelationship:
        """Create or update a relationship."""
        relationship.updated_at = datetime.utcnow()
        relationship.version += 1
        
        cypher = f"""
        MATCH (source {{id: $source_id}}), (target {{id: $target_id}})
        MERGE (source)-[r:{relationship.type.value}]->(target)
        SET r += $properties,
            r.updated_at = datetime($updated_at),
            r.version = coalesce(r.version, 0) + 1
        RETURN r
        """
        params = relationship.to_cypher_params()
        results = await self.neo4j.execute_write(cypher, params)
        return relationship
    
    async def delete_relationship(
        self, 
        source_id: str, 
        target_id: str, 
        rel_type: Optional[RelationshipType] = None
    ) -> bool:
        """Delete a relationship."""
        type_clause = f":{rel_type.value}" if rel_type else ""
        cypher = f"""
        MATCH (source {{id: $source_id}})-[r{type_clause}]->(target {{id: $target_id}})
        DELETE r
        RETURN count(r) as deleted
        """
        results = await self.neo4j.execute_write(cypher, {
            "source_id": source_id,
            "target_id": target_id
        })
        return results[0].get("deleted", 0) > 0 if results else False
    
    # Path and traversal operations
    
    async def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
        relationship_types: Optional[List[RelationshipType]] = None
    ) -> Optional[GraphPath]:
        """Find shortest path between two entities."""
        rel_filter = ""
        if relationship_types:
            types_str = "|".join([rt.value for rt in relationship_types])
            rel_filter = f":{types_str}"
        
        cypher = f"""
        MATCH (source {{id: $source_id}}), (target {{id: $target_id}})
        MATCH path = shortestPath((source)-[{rel_filter}*1..{max_depth}]-(target))
        RETURN path
        """
        
        results = await self.neo4j.execute_query(cypher, {
            "source_id": source_id,
            "target_id": target_id
        })
        
        if not results:
            return None
        
        path_data = results[0].get("path")
        if not path_data:
            return None
        
        # Parse path nodes and relationships
        nodes = []
        relationships = []
        
        for node in path_data.nodes:
            nodes.append(GraphEntity.from_record({"n": node}))
        
        for rel in path_data.relationships:
            rel_data = dict(rel)
            rel_data["source_id"] = rel.start_node.get("id")
            rel_data["target_id"] = rel.end_node.get("id")
            relationships.append(GraphRelationship(
                id=rel_data.get("id", ""),
                type=RelationshipType(rel_data.get("type", "RELATED_TO")),
                source_id=rel_data.get("source_id", ""),
                target_id=rel_data.get("target_id", ""),
                properties=rel_data,
            ))
        
        return GraphPath(nodes=nodes, relationships=relationships)
    
    async def find_all_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 4,
        max_paths: int = 10,
        relationship_types: Optional[List[RelationshipType]] = None
    ) -> List[GraphPath]:
        """Find all paths between two entities up to max_depth."""
        rel_filter = ""
        if relationship_types:
            types_str = "|".join([rt.value for rt in relationship_types])
            rel_filter = f":{types_str}"
        
        cypher = f"""
        MATCH (source {{id: $source_id}}), (target {{id: $target_id}})
        MATCH path = (source)-[{rel_filter}*1..{max_depth}]-(target)
        RETURN path
        LIMIT $max_paths
        """
        
        results = await self.neo4j.execute_query(cypher, {
            "source_id": source_id,
            "target_id": target_id,
            "max_paths": max_paths
        })
        
        paths = []
        for record in results:
            path_data = record.get("path")
            if not path_data:
                continue
            
            nodes = []
            relationships = []
            
            for node in path_data.nodes:
                nodes.append(GraphEntity.from_record({"n": node}))
            
            for rel in path_data.relationships:
                rel_data = dict(rel)
                rel_data["source_id"] = rel.start_node.get("id")
                rel_data["target_id"] = rel.end_node.get("id")
                relationships.append(GraphRelationship(
                    id=rel_data.get("id", ""),
                    type=RelationshipType(rel_data.get("type", "RELATED_TO")),
                    source_id=rel_data.get("source_id", ""),
                    target_id=rel_data.get("target_id", ""),
                    properties=rel_data,
                ))
            
            paths.append(GraphPath(nodes=nodes, relationships=relationships))
        
        return paths
    
    async def get_neighbors(
        self,
        entity_id: str,
        depth: int = 1,
        relationship_types: Optional[List[RelationshipType]] = None,
        direction: str = "both"
    ) -> GraphQueryResult:
        """Get neighboring entities up to specified depth."""
        rel_filter = ""
        if relationship_types:
            types_str = "|".join([rt.value for rt in relationship_types])
            rel_filter = f":{types_str}"
        
        dir_pattern = {
            "outgoing": "->",
            "incoming": "<-",
            "both": "-"
        }.get(direction, "-")
        
        cypher = f"""
        MATCH (center {{id: $entity_id}})
        MATCH path = (center)-[{rel_filter}*1..{depth}]{dir_pattern}(neighbor)
        RETURN DISTINCT neighbor, 
               relationships(path) as rels,
               nodes(path) as path_nodes
        """
        
        results = await self.neo4j.execute_query(cypher, {"entity_id": entity_id})
        
        entities = []
        relationships = []
        seen_entity_ids = set()
        seen_rel_ids = set()
        
        for record in results:
            neighbor = record.get("neighbor")
            if neighbor and neighbor.get("id") not in seen_entity_ids:
                entities.append(GraphEntity.from_record({"n": neighbor}))
                seen_entity_ids.add(neighbor.get("id"))
            
            for rel in record.get("rels", []):
                rel_data = dict(rel)
                rel_data["source_id"] = rel.start_node.get("id")
                rel_data["target_id"] = rel.end_node.get("id")
                rel_id = rel_data.get("id", "")
                if rel_id not in seen_rel_ids:
                    relationships.append(GraphRelationship(
                        id=rel_id,
                        type=RelationshipType(rel_data.get("type", "RELATED_TO")),
                        source_id=rel_data.get("source_id", ""),
                        target_id=rel_data.get("target_id", ""),
                        properties=rel_data,
                    ))
                    seen_rel_ids.add(rel_id)
        
        return GraphQueryResult(
            entities=entities,
            relationships=relationships
        )
    
    # Company-specific queries
    
    async def get_company_competitors(
        self, 
        company_id: str, 
        limit: int = 20
    ) -> List[GraphEntity]:
        """Get competitors for a company."""
        cypher = """
        MATCH (c:Company {id: $company_id})-[:COMPETES_WITH]-(competitor:Company)
        RETURN competitor
        LIMIT $limit
        """
        results = await self.neo4j.execute_query(cypher, {
            "company_id": company_id,
            "limit": limit
        })
        return [GraphEntity.from_record({"n": r.get("competitor")}) for r in results]
    
    async def get_company_suppliers(
        self, 
        company_id: str, 
        limit: int = 20
    ) -> List[GraphEntity]:
        """Get suppliers for a company."""
        cypher = """
        MATCH (supplier:Company)-[:SUPPLIES_TO]->(c:Company {id: $company_id})
        RETURN supplier
        LIMIT $limit
        """
        results = await self.neo4j.execute_query(cypher, {
            "company_id": company_id,
            "limit": limit
        })
        return [GraphEntity.from_record({"n": r.get("supplier")}) for r in results]
    
    async def get_company_customers(
        self, 
        company_id: str, 
        limit: int = 20
    ) -> List[GraphEntity]:
        """Get customers for a company."""
        cypher = """
        MATCH (c:Company {id: $company_id})-[:SUPPLIES_TO]->(customer:Company)
        RETURN customer
        LIMIT $limit
        """
        results = await self.neo4j.execute_query(cypher, {
            "company_id": company_id,
            "limit": limit
        })
        return [GraphEntity.from_record({"n": r.get("customer")}) for r in results]
    
    async def get_company_executives(
        self, 
        company_id: str, 
        limit: int = 50
    ) -> List[GraphEntity]:
        """Get executives/people working for a company."""
        cypher = """
        MATCH (p:Person)-[:WORKS_FOR]->(c:Company {id: $company_id})
        RETURN p
        LIMIT $limit
        """
        results = await self.neo4j.execute_query(cypher, {
            "company_id": company_id,
            "limit": limit
        })
        return [GraphEntity.from_record({"n": r.get("p")}) for r in results]
    
    async def get_company_products(
        self, 
        company_id: str, 
        limit: int = 50
    ) -> List[GraphEntity]:
        """Get products produced by a company."""
        cypher = """
        MATCH (c:Company {id: $company_id})-[:PRODUCES]->(p:Product)
        RETURN p
        LIMIT $limit
        """
        results = await self.neo4j.execute_query(cypher, {
            "company_id": company_id,
            "limit": limit
        })
        return [GraphEntity.from_record({"n": r.get("p")}) for r in results]
    
    async def get_company_financial_metrics(
        self, 
        company_id: str, 
        metric_names: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[GraphEntity]:
        """Get financial metrics for a company."""
        cypher = """
        MATCH (c:Company {id: $company_id})-[:HAS_METRIC]->(m:FinancialMetric)
        """
        params = {"company_id": company_id, "limit": limit}
        
        if metric_names:
            cypher += " WHERE m.metric_name IN $metric_names"
            params["metric_names"] = metric_names
        
        cypher += " RETURN m ORDER BY m.fiscal_year DESC, m.fiscal_quarter DESC LIMIT $limit"
        
        results = await self.neo4j.execute_query(cypher, params)
        return [GraphEntity.from_record({"n": r.get("m")}) for r in results]
    
    async def get_company_news(
        self, 
        company_id: str, 
        days: int = 30,
        limit: int = 50
    ) -> List[GraphEntity]:
        """Get recent news mentioning a company."""
        cypher = """
        MATCH (n:NewsArticle)-[:MENTIONS]->(c:Company {id: $company_id})
        WHERE n.published_at >= datetime() - duration({days: $days})
        RETURN n
        ORDER BY n.published_at DESC
        LIMIT $limit
        """
        results = await self.neo4j.execute_query(cypher, {
            "company_id": company_id,
            "days": days,
            "limit": limit
        })
        return [GraphEntity.from_record({"n": r.get("n")}) for r in results]
    
    # Sector/Industry queries
    
    async def get_sector_companies(
        self, 
        sector: str, 
        limit: int = 100
    ) -> List[GraphEntity]:
        """Get all companies in a sector."""
        cypher = """
        MATCH (c:Company)-[:OPERATES_IN]->(s:Sector {name: $sector})
        RETURN c
        LIMIT $limit
        """
        results = await self.neo4j.execute_query(cypher, {
            "sector": sector,
            "limit": limit
        })
        return [GraphEntity.from_record({"n": r.get("c")}) for r in results]
    
    async def get_industry_companies(
        self, 
        industry: str, 
        limit: int = 100
    ) -> List[GraphEntity]:
        """Get all companies in an industry."""
        cypher = """
        MATCH (c:Company)-[:OPERATES_IN]->(i:Industry {name: $industry})
        RETURN c
        LIMIT $limit
        """
        results = await self.neo4j.execute_query(cypher, {
            "industry": industry,
            "limit": limit
        })
        return [GraphEntity.from_record({"n": r.get("c")}) for r in results]
    
    # Search operations
    
    async def search_entities(
        self,
        query: str,
        entity_types: Optional[List[EntityType]] = None,
        limit: int = 20
    ) -> List[GraphEntity]:
        """Full-text search across entities."""
        type_filter = ""
        if entity_types:
            labels = ":".join([et.value for et in entity_types])
            type_filter = f"({labels})"
        
        cypher = f"""
        CALL db.index.fulltext.queryNodes('entity_search', $query)
        YIELD node, score
        WHERE node:type IN $types OR $types IS NULL
        RETURN node, score
        ORDER BY score DESC
        LIMIT $limit
        """
        
        types = [et.value for et in entity_types] if entity_types else None
        results = await self.neo4j.execute_query(cypher, {
            "query": query,
            "types": types,
            "limit": limit
        })
        
        entities = []
        for record in results:
            node = record.get("node")
            if node:
                entities.append(GraphEntity.from_record({"n": node}))
        
        return entities
    
    # Aggregation queries
    
    async def get_sector_distribution(self) -> Dict[str, int]:
        """Get count of companies per sector."""
        cypher = """
        MATCH (c:Company)-[:OPERATES_IN]->(s:Sector)
        RETURN s.name as sector, count(c) as count
        ORDER BY count DESC
        """
        results = await self.neo4j.execute_query(cypher)
        return {r["sector"]: r["count"] for r in results}
    
    async def get_relationship_type_distribution(self) -> Dict[str, int]:
        """Get count of relationships by type."""
        cypher = """
        MATCH ()-[r]->()
        RETURN type(r) as type, count(r) as count
        ORDER BY count DESC
        """
        results = await self.neo4j.execute_query(cypher)
        return {r["type"]: r["count"] for r in results}
    
    async def get_entity_count_by_type(self) -> Dict[str, int]:
        """Get count of entities by type."""
        cypher = """
        MATCH (n)
        WHERE n.type IS NOT NULL
        RETURN n.type as type, count(n) as count
        ORDER BY count DESC
        """
        results = await self.neo4j.execute_query(cypher)
        return {r["type"]: r["count"] for r in results}
    
    # Health and stats
    
    async def get_graph_stats(self) -> Dict[str, Any]:
        """Get overall graph statistics."""
        cypher = """
        CALL db.stats.retrieve('GRAPH COUNTS')
        YIELD label, count
        RETURN label, count
        """
        results = await self.neo4j.execute_query(cypher)
        node_counts = {r["label"]: r["count"] for r in results}
        
        cypher = """
        CALL db.stats.retrieve('RELATIONSHIP COUNTS')
        YIELD type, count
        RETURN type, count
        """
        results = await self.neo4j.execute_query(cypher)
        rel_counts = {r["type"]: r["count"] for r in results}
        
        return {
            "nodes": node_counts,
            "relationships": rel_counts,
            "total_nodes": sum(node_counts.values()),
            "total_relationships": sum(rel_counts.values()),
        }


# Global repository instance
_graph_repository: Optional[GraphRepository] = None


def get_graph_repository() -> GraphRepository:
    """Get or create the global graph repository."""
    global _graph_repository
    if _graph_repository is None:
        _graph_repository = GraphRepository()
    return _graph_repository