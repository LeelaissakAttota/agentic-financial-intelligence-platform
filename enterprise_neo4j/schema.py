"""
Graph Schema - Schema management and validation for Neo4j knowledge graph.
"""

import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from .models import EntityType, RelationshipType

logger = logging.getLogger(__name__)


@dataclass
class NodeSchema:
    """Schema definition for a node type."""
    label: str
    required_properties: List[str] = field(default_factory=list)
    optional_properties: List[str] = field(default_factory=list)
    property_types: Dict[str, str] = field(default_factory=dict)
    indexes: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class RelationshipSchema:
    """Schema definition for a relationship type."""
    type: str
    source_labels: List[str] = field(default_factory=list)
    target_labels: List[str] = field(default_factory=list)
    required_properties: List[str] = field(default_factory=list)
    optional_properties: List[str] = field(default_factory=list)
    property_types: Dict[str, str] = field(default_factory=dict)
    description: str = ""


class GraphSchema:
    """
    Manages the graph schema including node types, relationship types,
    indexes, constraints, and validation rules.
    """
    
    # Standard node schemas
    NODE_SCHEMAS: Dict[str, NodeSchema] = {
        "Company": NodeSchema(
            label="Company",
            required_properties=["id", "ticker", "name"],
            optional_properties=[
                "cik", "sector", "industry", "market_cap", "description",
                "website", "headquarters", "employees", "founded_year",
                "exchange", "currency", "is_active", "created_at", "updated_at"
            ],
            property_types={
                "id": "STRING",
                "ticker": "STRING",
                "name": "STRING",
                "cik": "STRING",
                "sector": "STRING",
                "industry": "STRING",
                "market_cap": "FLOAT",
                "description": "STRING",
                "website": "STRING",
                "headquarters": "STRING",
                "employees": "INTEGER",
                "founded_year": "INTEGER",
                "exchange": "STRING",
                "currency": "STRING",
                "is_active": "BOOLEAN",
                "created_at": "DATETIME",
                "updated_at": "DATETIME",
                "version": "INTEGER",
                "source": "STRING",
                "confidence": "FLOAT"
            },
            indexes=["ticker", "name", "sector", "industry", "created_at"],
            constraints=["UNIQUE (c:Company) ASSERT c.id IS UNIQUE", "UNIQUE (c:Company) ASSERT c.ticker IS UNIQUE"],
            description="Publicly traded company entity"
        ),
        "Person": NodeSchema(
            label="Person",
            required_properties=["id", "name"],
            optional_properties=[
                "role", "company_id", "bio", "linkedin", "twitter",
                "created_at", "updated_at", "version", "source", "confidence"
            ],
            property_types={
                "id": "STRING",
                "name": "STRING",
                "role": "STRING",
                "company_id": "STRING",
                "bio": "STRING",
                "linkedin": "STRING",
                "twitter": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME",
                "version": "INTEGER",
                "source": "STRING",
                "confidence": "FLOAT"
            },
            indexes=["name", "company_id", "role"],
            constraints=["UNIQUE (p:Person) ASSERT p.id IS UNIQUE"],
            description="Person entity (executive, analyst, etc.)"
        ),
        "Product": NodeSchema(
            label="Product",
            required_properties=["id", "name", "company_id"],
            optional_properties=[
                "description", "category", "revenue", "created_at", "updated_at",
                "version", "source", "confidence"
            ],
            property_types={
                "id": "STRING",
                "name": "STRING",
                "company_id": "STRING",
                "description": "STRING",
                "category": "STRING",
                "revenue": "FLOAT",
                "created_at": "DATETIME",
                "updated_at": "DATETIME",
                "version": "INTEGER",
                "source": "STRING",
                "confidence": "FLOAT"
            },
            indexes=["name", "company_id", "category"],
            constraints=["UNIQUE (p:Product) ASSERT p.id IS UNIQUE"],
            description="Product or service offered by a company"
        ),
        "Sector": NodeSchema(
            label="Sector",
            required_properties=["id", "name"],
            optional_properties=["description", "created_at"],
            property_types={
                "id": "STRING",
                "name": "STRING",
                "description": "STRING",
                "created_at": "DATETIME"
            },
            indexes=["name"],
            constraints=["UNIQUE (s:Sector) ASSERT s.id IS UNIQUE", "UNIQUE (s:Sector) ASSERT s.name IS UNIQUE"],
            description="Market sector classification"
        ),
        "Industry": NodeSchema(
            label="Industry",
            required_properties=["id", "name"],
            optional_properties=["description", "sector_id", "created_at"],
            property_types={
                "id": "STRING",
                "name": "STRING",
                "description": "STRING",
                "sector_id": "STRING",
                "created_at": "DATETIME"
            },
            indexes=["name", "sector_id"],
            constraints=["UNIQUE (i:Industry) ASSERT i.id IS UNIQUE", "UNIQUE (i:Industry) ASSERT i.name IS UNIQUE"],
            description="Industry classification within a sector"
        ),
        "FinancialMetric": NodeSchema(
            label="FinancialMetric",
            required_properties=["id", "company_id", "metric_name", "value", "period", "fiscal_year"],
            optional_properties=[
                "fiscal_quarter", "unit", "created_at", "updated_at",
                "version", "source", "confidence"
            ],
            property_types={
                "id": "STRING",
                "company_id": "STRING",
                "metric_name": "STRING",
                "value": "FLOAT",
                "period": "STRING",
                "fiscal_year": "INTEGER",
                "fiscal_quarter": "INTEGER",
                "unit": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME",
                "version": "INTEGER",
                "source": "STRING",
                "confidence": "FLOAT"
            },
            indexes=["company_id", "metric_name", "fiscal_year", "period"],
            constraints=["UNIQUE (m:FinancialMetric) ASSERT m.id IS UNIQUE"],
            description="Financial metric data point for a company"
        ),
        "NewsArticle": NodeSchema(
            label="NewsArticle",
            required_properties=["id", "title", "published_at"],
            optional_properties=[
                "content", "source", "url", "sentiment_score",
                "entities_mentioned", "created_at", "updated_at",
                "version", "source", "confidence"
            ],
            property_types={
                "id": "STRING",
                "title": "STRING",
                "content": "STRING",
                "source": "STRING",
                "url": "STRING",
                "published_at": "DATETIME",
                "sentiment_score": "FLOAT",
                "entities_mentioned": "LIST",
                "created_at": "DATETIME",
                "updated_at": "DATETIME",
                "version": "INTEGER",
                "source": "STRING",
                "confidence": "FLOAT"
            },
            indexes=["published_at", "source", "sentiment_score"],
            constraints=["UNIQUE (n:NewsArticle) ASSERT n.id IS UNIQUE"],
            description="News article with financial relevance"
        ),
        "EarningsCall": NodeSchema(
            label="EarningsCall",
            required_properties=["id", "company_id", "quarter", "year", "date"],
            optional_properties=[
                "transcript", "participants", "created_at", "updated_at",
                "version", "source", "confidence"
            ],
            property_types={
                "id": "STRING",
                "company_id": "STRING",
                "transcript": "STRING",
                "quarter": "STRING",
                "year": "INTEGER",
                "date": "DATETIME",
                "participants": "LIST",
                "created_at": "DATETIME",
                "updated_at": "DATETIME",
                "version": "INTEGER",
                "source": "STRING",
                "confidence": "FLOAT"
            },
            indexes=["company_id", "year", "quarter", "date"],
            constraints=["UNIQUE (e:EarningsCall) ASSERT e.id IS UNIQUE"],
            description="Earnings call transcript and metadata"
        ),
        "SECFiling": NodeSchema(
            label="SECFiling",
            required_properties=["id", "company_id", "form_type", "filing_date", "accession_number"],
            optional_properties=[
                "content", "created_at", "updated_at", "version", "source", "confidence"
            ],
            property_types={
                "id": "STRING",
                "company_id": "STRING",
                "form_type": "STRING",
                "filing_date": "DATETIME",
                "accession_number": "STRING",
                "content": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME",
                "version": "INTEGER",
                "source": "STRING",
                "confidence": "FLOAT"
            },
            indexes=["company_id", "form_type", "filing_date", "accession_number"],
            constraints=["UNIQUE (s:SECFiling) ASSERT s.id IS UNIQUE"],
            description="SEC filing document"
        ),
        "AnalystReport": NodeSchema(
            label="AnalystReport",
            required_properties=["id", "company_id", "analyst", "firm", "report_date"],
            optional_properties=[
                "rating", "target_price", "summary", "created_at", "updated_at",
                "version", "source", "confidence"
            ],
            property_types={
                "id": "STRING",
                "company_id": "STRING",
                "analyst": "STRING",
                "firm": "STRING",
                "rating": "STRING",
                "target_price": "FLOAT",
                "summary": "STRING",
                "report_date": "DATETIME",
                "created_at": "DATETIME",
                "updated_at": "DATETIME",
                "version": "INTEGER",
                "source": "STRING",
                "confidence": "FLOAT"
            },
            indexes=["company_id", "firm", "analyst", "report_date", "rating"],
            constraints=["UNIQUE (a:AnalystReport) ASSERT a.id IS UNIQUE"],
            description="Analyst research report"
        ),
        "MarketIndex": NodeSchema(
            label="MarketIndex",
            required_properties=["id", "name", "symbol"],
            optional_properties=[
                "description", "constituents", "created_at", "updated_at"
            ],
            property_types={
                "id": "STRING",
                "name": "STRING",
                "symbol": "STRING",
                "description": "STRING",
                "constituents": "LIST",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            indexes=["symbol", "name"],
            constraints=["UNIQUE (m:MarketIndex) ASSERT m.id IS UNIQUE"],
            description="Market index (S&P 500, NASDAQ, etc.)"
        ),
        "Event": NodeSchema(
            label="Event",
            required_properties=["id", "name", "event_type", "date"],
            optional_properties=[
                "description", "impact_score", "entities_affected", "created_at", "updated_at"
            ],
            property_types={
                "id": "STRING",
                "name": "STRING",
                "event_type": "STRING",
                "date": "DATETIME",
                "description": "STRING",
                "impact_score": "FLOAT",
                "entities_affected": "LIST",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            indexes=["event_type", "date", "impact_score"],
            constraints=["UNIQUE (e:Event) ASSERT e.id IS UNIQUE"],
            description="Financial or market event"
        ),
    }
    
    # Standard relationship schemas
    RELATIONSHIP_SCHEMAS: Dict[str, RelationshipSchema] = {
        "COMPETES_WITH": RelationshipSchema(
            type="COMPETES_WITH",
            source_labels=["Company"],
            target_labels=["Company"],
            required_properties=[],
            optional_properties=["confidence", "weight", "since", "source", "created_at", "updated_at"],
            property_types={
                "confidence": "FLOAT",
                "weight": "FLOAT",
                "since": "DATETIME",
                "source": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            description="Company competes with another company"
        ),
        "PARTNERS_WITH": RelationshipSchema(
            type="PARTNERS_WITH",
            source_labels=["Company"],
            target_labels=["Company"],
            required_properties=[],
            optional_properties=["confidence", "weight", "partnership_type", "since", "source", "created_at", "updated_at"],
            property_types={
                "confidence": "FLOAT",
                "weight": "FLOAT",
                "partnership_type": "STRING",
                "since": "DATETIME",
                "source": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            description="Company has a partnership with another company"
        ),
        "SUPPLIES_TO": RelationshipSchema(
            type="SUPPLIES_TO",
            source_labels=["Company"],
            target_labels=["Company"],
            required_properties=[],
            optional_properties=["confidence", "weight", "product_category", "revenue_share", "source", "created_at", "updated_at"],
            property_types={
                "confidence": "FLOAT",
                "weight": "FLOAT",
                "product_category": "STRING",
                "revenue_share": "FLOAT",
                "source": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            description="Company supplies products/services to another company"
        ),
        "ACQUIRED": RelationshipSchema(
            type="ACQUIRED",
            source_labels=["Company"],
            target_labels=["Company"],
            required_properties=["date"],
            optional_properties=["price", "status", "source", "created_at", "updated_at"],
            property_types={
                "date": "DATETIME",
                "price": "FLOAT",
                "status": "STRING",
                "source": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            description="Company acquired another company"
        ),
        "MERGED_WITH": RelationshipSchema(
            type="MERGED_WITH",
            source_labels=["Company"],
            target_labels=["Company"],
            required_properties=["date"],
            optional_properties=["terms", "status", "source", "created_at", "updated_at"],
            property_types={
                "date": "DATETIME",
                "terms": "STRING",
                "status": "STRING",
                "source": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            description="Company merged with another company"
        ),
        "SUBSIDIARY_OF": RelationshipSchema(
            type="SUBSIDIARY_OF",
            source_labels=["Company"],
            target_labels=["Company"],
            required_properties=[],
            optional_properties=["ownership_pct", "since", "source", "created_at", "updated_at"],
            property_types={
                "ownership_pct": "FLOAT",
                "since": "DATETIME",
                "source": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            description="Company is a subsidiary of another company"
        ),
        "WORKS_FOR": RelationshipSchema(
            type="WORKS_FOR",
            source_labels=["Person"],
            target_labels=["Company"],
            required_properties=[],
            optional_properties=["role", "title", "since", "until", "source", "created_at", "updated_at"],
            property_types={
                "role": "STRING",
                "title": "STRING",
                "since": "DATETIME",
                "until": "DATETIME",
                "source": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            description="Person works for a company"
        ),
        "BOARD_MEMBER_OF": RelationshipSchema(
            type="BOARD_MEMBER_OF",
            source_labels=["Person"],
            target_labels=["Company"],
            required_properties=[],
            optional_properties=["since", "until", "committee", "source", "created_at", "updated_at"],
            property_types={
                "since": "DATETIME",
                "until": "DATETIME",
                "committee": "STRING",
                "source": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            description="Person is a board member of a company"
        ),
        "ADVISES": RelationshipSchema(
            type="ADVISES",
            source_labels=["Person"],
            target_labels=["Company"],
            required_properties=[],
            optional_properties=["advisor_type", "since", "until", "source", "created_at", "updated_at"],
            property_types={
                "advisor_type": "STRING",
                "since": "DATETIME",
                "until": "DATETIME",
                "source": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            description="Person advises a company"
        ),
        "FOUNDED": RelationshipSchema(
            type="FOUNDED",
            source_labels=["Person"],
            target_labels=["Company"],
            required_properties=["date"],
            optional_properties=["source", "created_at", "updated_at"],
            property_types={
                "date": "DATETIME",
                "source": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            description="Person founded a company"
        ),
        "PRODUCES": RelationshipSchema(
            type="PRODUCES",
            source_labels=["Company"],
            target_labels=["Product"],
            required_properties=[],
            optional_properties=["since", "revenue", "source", "created_at", "updated_at"],
            property_types={
                "since": "DATETIME",
                "revenue": "FLOAT",
                "source": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            description="Company produces a product"
        ),
        "OPERATES_IN": RelationshipSchema(
            type="OPERATES_IN",
            source_labels=["Company"],
            target_labels=["Sector", "Industry"],
            required_properties=[],
            optional_properties=["since", "primary", "source", "created_at", "updated_at"],
            property_types={
                "since": "DATETIME",
                "primary": "BOOLEAN",
                "source": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            description="Company operates in a sector/industry"
        ),
        "PART_OF": RelationshipSchema(
            type="PART_OF",
            source_labels=["Industry"],
            target_labels=["Sector"],
            required_properties=[],
            optional_properties=["source", "created_at", "updated_at"],
            property_types={
                "source": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            description="Industry is part of a sector"
        ),
        "HAS_METRIC": RelationshipSchema(
            type="HAS_METRIC",
            source_labels=["Company"],
            target_labels=["FinancialMetric"],
            required_properties=["period", "fiscal_year"],
            optional_properties=["fiscal_quarter", "unit", "source", "created_at", "updated_at"],
            property_types={
                "period": "STRING",
                "fiscal_year": "INTEGER",
                "fiscal_quarter": "INTEGER",
                "unit": "STRING",
                "source": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            description="Company has a financial metric"
        ),
        "MENTIONS": RelationshipSchema(
            type="MENTIONS",
            source_labels=["NewsArticle", "AnalystReport", "EarningsCall", "SECFiling"],
            target_labels=["Company", "Person", "Product", "Event"],
            required_properties=[],
            optional_properties=["sentiment", "relevance", "context", "source", "created_at", "updated_at"],
            property_types={
                "sentiment": "FLOAT",
                "relevance": "FLOAT",
                "context": "STRING",
                "source": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            description="Document mentions an entity"
        ),
        "TRIGGERED": RelationshipSchema(
            type="TRIGGERED",
            source_labels=["Event", "NewsArticle"],
            target_labels=["Company", "MarketIndex", "FinancialMetric"],
            required_properties=[],
            optional_properties=["impact", "confidence", "source", "created_at", "updated_at"],
            property_types={
                "impact": "FLOAT",
                "confidence": "FLOAT",
                "source": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            description="Event/document triggered a market reaction"
        ),
        "IMPACTED": RelationshipSchema(
            type="IMPACTED",
            source_labels=["Event", "NewsArticle", "EarningsCall"],
            target_labels=["Company", "Person", "Product", "FinancialMetric"],
            required_properties=[],
            optional_properties=["impact_score", "direction", "confidence", "source", "created_at", "updated_at"],
            property_types={
                "impact_score": "FLOAT",
                "direction": "STRING",
                "confidence": "FLOAT",
                "source": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            description="Entity was impacted by an event"
        ),
        "CITES": RelationshipSchema(
            type="CITES",
            source_labels=["AnalystReport", "SECFiling", "EarningsCall"],
            target_labels=["AnalystReport", "SECFiling", "NewsArticle", "EarningsCall"],
            required_properties=[],
            optional_properties=["context", "source", "created_at", "updated_at"],
            property_types={
                "context": "STRING",
                "source": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            description="Document cites another document"
        ),
        "ANALYZES": RelationshipSchema(
            type="ANALYZES",
            source_labels=["AnalystReport", "NewsArticle"],
            target_labels=["Company", "Product", "FinancialMetric", "Event"],
            required_properties=[],
            optional_properties=["depth", "confidence", "source", "created_at", "updated_at"],
            property_types={
                "depth": "STRING",
                "confidence": "FLOAT",
                "source": "STRING",
                "created_at": "DATETIME",
                "updated_at": "DATETIME"
            },
            description="Document analyzes an entity"
        ),
    }
    
    def __init__(self):
        self.custom_node_schemas: Dict[str, NodeSchema] = {}
        self.custom_rel_schemas: Dict[str, RelationshipSchema] = {}
    
    def get_node_schema(self, label: str) -> Optional[NodeSchema]:
        """Get node schema by label."""
        if label in self.NODE_SCHEMAS:
            return self.NODE_SCHEMAS[label]
        return self.custom_node_schemas.get(label)
    
    def get_relationship_schema(self, rel_type: str) -> Optional[RelationshipSchema]:
        """Get relationship schema by type."""
        if rel_type in self.RELATIONSHIP_SCHEMAS:
            return self.RELATIONSHIP_SCHEMAS[rel_type]
        return self.custom_rel_schemas.get(rel_type)
    
    def register_node_schema(self, schema: NodeSchema) -> None:
        """Register a custom node schema."""
        self.custom_node_schemas[schema.label] = schema
        logger.info(f"Registered custom node schema: {schema.label}")
    
    def register_relationship_schema(self, schema: RelationshipSchema) -> None:
        """Register a custom relationship schema."""
        self.custom_rel_schemas[schema.type] = schema
        logger.info(f"Registered custom relationship schema: {schema.type}")
    
    def get_all_node_labels(self) -> List[str]:
        """Get all registered node labels."""
        return list(self.NODE_SCHEMAS.keys()) + list(self.custom_node_schemas.keys())
    
    def get_all_relationship_types(self) -> List[str]:
        """Get all registered relationship types."""
        return list(self.RELATIONSHIP_SCHEMAS.keys()) + list(self.custom_rel_schemas.keys())
    
    def validate_node(self, label: str, properties: Dict[str, Any]) -> List[str]:
        """Validate node properties against schema."""
        errors = []
        schema = self.get_node_schema(label)
        
        if not schema:
            errors.append(f"Unknown node label: {label}")
            return errors
        
        # Check required properties
        for req in schema.required_properties:
            if req not in properties:
                errors.append(f"Missing required property: {req}")
        
        # Check property types
        for prop, value in properties.items():
            if prop in schema.property_types:
                expected_type = schema.property_types[prop]
                if not self._check_type(value, expected_type):
                    errors.append(f"Property {prop}: expected {expected_type}, got {type(value).__name__}")
        
        return errors
    
    def validate_relationship(
        self, 
        rel_type: str, 
        source_label: str, 
        target_label: str,
        properties: Dict[str, Any]
    ) -> List[str]:
        """Validate relationship against schema."""
        errors = []
        schema = self.get_relationship_schema(rel_type)
        
        if not schema:
            errors.append(f"Unknown relationship type: {rel_type}")
            return errors
        
        # Check source/target labels
        if schema.source_labels and source_label not in schema.source_labels:
            errors.append(f"Invalid source label: {source_label} (expected one of {schema.source_labels})")
        
        if schema.target_labels and target_label not in schema.target_labels:
            errors.append(f"Invalid target label: {target_label} (expected one of {schema.target_labels})")
        
        # Check required properties
        for req in schema.required_properties:
            if req not in properties:
                errors.append(f"Missing required property: {req}")
        
        # Check property types
        for prop, value in properties.items():
            if prop in schema.property_types:
                expected_type = schema.property_types[prop]
                if not self._check_type(value, expected_type):
                    errors.append(f"Property {prop}: expected {expected_type}, got {type(value).__name__}")
        
        return errors
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        if value is None:
            return True  # None is valid for optional properties
        
        type_map = {
            "STRING": str,
            "INTEGER": int,
            "FLOAT": (int, float),
            "BOOLEAN": bool,
            "DATETIME": str,  # ISO format string
            "LIST": list,
            "MAP": dict,
        }
        
        expected_python_type = type_map.get(expected_type)
        if expected_python_type:
            return isinstance(value, expected_python_type)
        return True  # Unknown type, allow
    
    async def apply_schema(self, neo4j_client) -> Dict[str, Any]:
        """Apply schema constraints and indexes to Neo4j."""
        results = {
            "constraints_created": 0,
            "indexes_created": 0,
            "errors": []
        }
        
        # Create constraints
        for label, schema in self.NODE_SCHEMAS.items():
            for constraint in schema.constraints:
                try:
                    await neo4j_client.execute_write(constraint)
                    results["constraints_created"] += 1
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        results["errors"].append(f"Constraint error for {label}: {e}")
        
        for rel_type, schema in self.RELATIONSHIP_SCHEMAS.items():
            # Relationship constraints would go here
            pass
        
        # Create indexes
        for label, schema in self.NODE_SCHEMAS.items():
            for index_prop in schema.indexes:
                try:
                    index_name = f"{label.lower()}_{index_prop}_index"
                    cypher = f"CREATE INDEX {index_name} IF NOT EXISTS FOR (n:{label}) ON (n.{index_prop})"
                    await neo4j_client.execute_write(cypher)
                    results["indexes_created"] += 1
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        results["errors"].append(f"Index error for {label}.{index_prop}: {e}")
        
        return results
    
    def generate_cypher_ddl(self) -> str:
        """Generate Cypher DDL statements for the schema."""
        statements = []
        
        # Node constraints
        for label, schema in self.NODE_SCHEMAS.items():
            for constraint in schema.constraints:
                statements.append(constraint + ";")
        
        # Node indexes
        for label, schema in self.NODE_SCHEMAS.items():
            for index_prop in schema.indexes:
                index_name = f"{label.lower()}_{index_prop}_index"
                statements.append(
                    f"CREATE INDEX {index_name} IF NOT EXISTS FOR (n:{label}) ON (n.{index_prop});"
                )
        
        # Relationship indexes (on type)
        statements.append("CREATE INDEX relationship_type_index IF NOT EXISTS FOR ()-[r]-() ON (type(r));")
        
        return "\n".join(statements)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export schema as dictionary."""
        return {
            "nodes": {
                label: {
                    "required": schema.required_properties,
                    "optional": schema.optional_properties,
                    "types": schema.property_types,
                    "indexes": schema.indexes,
                    "constraints": schema.constraints,
                    "description": schema.description
                }
                for label, schema in self.NODE_SCHEMAS.items()
            },
            "relationships": {
                rel_type: {
                    "source_labels": schema.source_labels,
                    "target_labels": schema.target_labels,
                    "required": schema.required_properties,
                    "optional": schema.optional_properties,
                    "types": schema.property_types,
                    "description": schema.description
                }
                for rel_type, schema in self.RELATIONSHIP_SCHEMAS.items()
            }
        }


# Global schema instance
_graph_schema: Optional[GraphSchema] = None


def get_graph_schema() -> GraphSchema:
    """Get or create the global graph schema."""
    global _graph_schema
    if _graph_schema is None:
        _graph_schema = GraphSchema()
    return _graph_schema