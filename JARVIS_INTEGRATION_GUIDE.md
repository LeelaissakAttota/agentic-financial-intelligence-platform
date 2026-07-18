# JARVIS Integration Guide
## Financial Research Agent v2.0.0

**Version**: v2.0.0  
**Status**: Stable Release - Maintenance Mode  
**Integration Contract**: FROZEN v1 APIs  
**Date**: 2026-07-18

---

## Overview

This guide documents how the **JARVIS AI CEO** integrates with the Financial Research Agent (FRA) as its **Financial Intelligence Engine**. All APIs are versioned v1 and frozen for stability.

### Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              JARVIS AI CEO                                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐  │
│  │ Decision     │ │ Strategy     │ │ Portfolio    │ │ Risk             │  │
│  │ Engine       │ │ Engine       │ │ Manager      │ │ Controller       │  │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └────────┬─────────┘  │
│         │                │                │                   │            │
│         └────────────────┼────────────────┼───────────────────┘            │
│                          ▼                                                │
│              ┌───────────────────────┐                                   │
│              │   Service Mesh /      │                                   │
│              │   API Gateway         │                                   │
│              │   (Istio/Envoy)       │                                   │
│              └───────────┬─────────────┘                                   │
└──────────────────────────┼────────────────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   REST API      │ │  WebSocket      │ │  Direct DB      │
│   (sync/async)  │ │  (streaming)    │ │  (Neo4j/PG)     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FINANCIAL RESEARCH AGENT v2.0.0              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Authentication

### Service-to-Service (JWT)

```http
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Required JWT Claims**:
```json
{
  "sub": "jarvis-ceo",
  "iss": "jarvis-auth",
  "aud": "financial-research-agent",
  "roles": ["financial_intelligence:read", "financial_intelligence:write"],
  "scopes": ["research", "reports", "knowledge_graph", "memory", "portfolio", "market_data", "news", "patterns", "analytics"],
  "exp": 1731942600,
  "iat": 1731939000
}
```

### API Key (Alternative)

```http
X-API-Key: fra_sk_live_jarvis_xxxxxxxxxxxx
Authorization: Bearer fra_sk_live_jarvis_xxxxxxxxxxxx
```

**API Key Scopes**: Same as JWT scopes above.

---

## REST APIs

### Base URL
```
Production:  https://api.financial-research.internal/v1
Staging:     https://api-staging.financial-research.internal/v1
```

### Research API

#### Start Autonomous Research
```http
POST /api/v1/research/start
Content-Type: application/json
Authorization: Bearer <token>

{
  "company": "AAPL",
  "query": "Should JARVIS increase AAPL position to 10% of portfolio?",
  "complexity": "COMPREHENSIVE",
  "auto_approve": true,
  "context": {
    "portfolio_id": "port_jarvis_core",
    "risk_tolerance": "MODERATE",
    "horizon_months": 12,
    "current_position_pct": 5.2,
    "target_position_pct": 10.0
  }
}
```

**Response** (202 Accepted):
```json
{
  "research_id": "res_abc123def456",
  "status": "QUEUED",
  "estimated_duration_seconds": 180,
  "poll_url": "/api/v1/research/res_abc123def456",
  "websocket_url": "wss://api.financial-research.internal/v1/ws/research/res_abc123def456"
}
```

#### Get Research Status
```http
GET /api/v1/research/{research_id}
Authorization: Bearer <token>
```

**Response** (200 OK):
```json
{
  "research_id": "res_abc123def456",
  "status": "COMPLETED",
  "progress": 1.0,
  "current_step": "SYNTHESIS",
  "steps_completed": 14,
  "steps_total": 14,
  "started_at": "2026-07-18T14:30:00Z",
  "completed_at": "2026-07-18T14:32:45Z",
  "result": {
    "thesis": "LONG",
    "confidence": 0.87,
    "confidence_interval": [0.82, 0.91],
    "recommendation": "BUY",
    "target_price": 215.00,
    "stop_loss": 165.00,
    "time_horizon_months": 12,
    "key_drivers": ["Services growth", "Margin expansion", "Buyback yield"],
    "risks": ["China exposure", "Regulatory", "Valuation"],
    "evidence_count": 247,
    "sources": ["10-K", "10-Q", "earnings calls", "analyst reports", "news"]
  }
}
```

#### Get Full Research Result
```http
GET /api/v1/research/{research_id}/result
Authorization: Bearer <token>
```

#### List Research History
```http
GET /api/v1/research/history?company=AAPL&status=COMPLETED&limit=20
Authorization: Bearer <token>
```

### Reports API

#### Generate Report
```http
POST /api/v1/reports/generate
Content-Type: application/json
Authorization: Bearer <token>

{
  "research_id": "res_abc123def456",
  "report_type": "INVESTMENT_THESIS",
  "format": "MARKDOWN",
  "template": "institutional",
  "sections": ["executive_summary", "thesis", "evidence", "risks", "valuation", "recommendation"]
}
```

**Response** (202 Accepted):
```json
{
  "report_id": "rpt_xyz789",
  "status": "GENERATING",
  "download_url": "/api/v1/reports/rpt_xyz789/download"
}
```

#### Download Report
```http
GET /api/v1/reports/{report_id}/download?format=MARKDOWN
Authorization: Bearer <token>
```

### Knowledge Graph API

#### Execute Cypher Query
```http
POST /api/v1/kg/query
Content-Type: application/json
Authorization: Bearer <token>

{
  "cypher": "MATCH (c:Company {ticker: $ticker})-[r:COMPETES_WITH]->(comp:Company) RETURN c, r, comp LIMIT 20",
  "parameters": {"ticker": "AAPL"}
}
```

**Response** (200 OK):
```json
{
  "nodes": [
    {"id": "n1", "labels": ["Company"], "properties": {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology"}},
    {"id": "n2", "labels": ["Company"], "properties": {"ticker": "MSFT", "name": "Microsoft Corporation", "sector": "Technology"}}
  ],
  "edges": [
    {"id": "e1", "type": "COMPETES_WITH", "source": "n1", "target": "n2", "properties": {"strength": 0.85, "basis": "OS, Cloud, AI"}}
  ],
  "statistics": {"nodes": 2, "edges": 1}
}
```

#### Run Graph Algorithm
```http
POST /api/v1/kg/algorithms/pagerank
Content-Type: application/json
Authorization: Bearer <token>

{
  "node_type": "Company",
  "iterations": 20,
  "damping_factor": 0.85
}
```

#### Get Company Context
```http
GET /api/v1/kg/companies/{ticker}/context?depth=2&include_metrics=true
Authorization: Bearer <token>
```

### Memory API

#### Write Memory
```http
POST /api/v1/memory/write
Content-Type: application/json
Authorization: Bearer <token>

{
  "scope": "COMPANY",
  "scope_key": "AAPL",
  "memory_type": "INSIGHT",
  "content": "Apple's services margin expanded to 74% in Q4 2025, driven by App Store and Apple Care growth",
  "importance": "HIGH",
  "source": "earnings_call_q4_2025",
  "tags": ["margin", "services", "quarterly"],
  "ttl_days": 365
}
```

#### Read Memory
```http
GET /api/v1/memory/read?scope=COMPANY&scope_key=AAPL&type=INSIGHT&limit=50
Authorization: Bearer <token>
```

#### Cross-Agent Memory Query
```http
POST /api/v1/memory/query
Content-Type: application/json
Authorization: Bearer <token>

{
  "query": "What are the key risks for Apple in China?",
  "scopes": ["COMPANY", "GLOBAL"],
  "scope_keys": ["AAPL"],
  "types": ["RISK", "INSIGHT"],
  "limit": 20,
  "min_relevance": 0.7
}
```

### Portfolio API

#### Create Portfolio
```http
POST /api/v1/portfolio
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "JARVIS Core Equity",
  "base_currency": "USD",
  "risk_budget": 0.15,
  "constraints": {
    "max_position": 0.10,
    "max_sector": 0.25,
    "max_single_stock": 0.15
  }
}
```

#### Calculate Risk Metrics
```http
POST /api/v1/portfolio/{portfolio_id}/risk
Content-Type: application/json
Authorization: Bearer <token>

{
  "method": "MONTE_CARLO",
  "paths": 10000,
  "horizon_days": 252,
  "confidence_levels": [0.95, 0.99],
  "include_copula": true,
  "stress_scenarios": ["GFC_2008", "COVID_2020", "CCAR_2023"]
}
```

#### Rebalance Portfolio
```http
POST /api/v1/portfolio/{portfolio_id}/rebalance
Content-Type: application/json
Authorization: Bearer <token>

{
  "strategy": "RISK_PARITY",
  "target_date": "2026-07-25",
  "dry_run": true
}
```

### Market Data API

#### Real-Time Quote (REST)
```http
GET /api/v1/market/quote?symbols=AAPL,MSFT,GOOGL
Authorization: Bearer <token>
```

**Response**:
```json
{
  "quotes": [
    {
      "symbol": "AAPL",
      "price": 185.42,
      "change": 2.15,
      "change_pct": 1.17,
      "volume": 45200000,
      "bid": 185.40,
      "ask": 185.44,
      "timestamp": "2026-07-18T15:30:00Z"
    }
  ]
}
```

### News API

#### Search News
```http
GET /api/v1/news/search?company=AAPL&limit=20&sentiment=negative&since=2026-07-10
Authorization: Bearer <token>
```

---

## WebSocket APIs

### Connection
```javascript
const ws = new WebSocket('wss://api.financial-research.internal/v1/ws/research/res_abc123def456', {
  headers: {
    'Authorization': 'Bearer <token>'
  }
});
```

### Channel: Research Progress
```javascript
// Subscribe to research updates
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'research_progress',
  research_id: 'res_abc123def456'
}));

// Messages received:
{
  "type": "research_progress",
  "research_id": "res_abc123def456",
  "step": "SENTIMENT_ANALYSIS",
  "progress": 0.45,
  "message": "Analyzing sentiment from 247 news articles",
  "timestamp": "2026-07-18T14:31:22Z"
}
```

### Channel: Market Data
```javascript
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'market_quotes',
  symbols: ['AAPL', 'MSFT', 'GOOGL'],
  filters: { min_confidence: 0.7 }
}));

// Messages:
{
  "type": "market_quote",
  "symbol": "AAPL",
  "price": 185.42,
  "change": 2.15,
  "volume": 45200000,
  "timestamp": "2026-07-18T15:30:00Z"
}
```

### Channel: News Stream
```javascript
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'news_stream',
  companies: ['AAPL'],
  categories: ['earnings', 'ma', 'regulatory'],
  min_importance: 0.6
}));

// Messages:
{
  "type": "news_article",
  "article_id": "art_123",
  "title": "Apple Reports Record Q4 Services Revenue",
  "summary": "Services revenue grew 14% YoY to $96.2B...",
  "sentiment": 0.72,
  "companies": ["AAPL"],
  "category": "earnings",
  "importance": 0.89,
  "timestamp": "2026-07-18T14:30:00Z"
}
```

### Channel: Portfolio Updates
```javascript
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'portfolio_updates',
  portfolio_id: 'port_jarvis_core'
}));

// Messages:
{
  "type": "portfolio_update",
  "portfolio_id": "port_jarvis_core",
  "event": "rebalance_complete",
  "details": {...}
}
```

### Channel: Workflow Visualization
```javascript
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'workflow',
  execution_id: 'exec_123'
}));

// Messages:
{
  "type": "workflow_progress",
  "execution_id": "exec_123",
  "nodes": [...],
  "edges": [...],
  "current_node": "sentiment_analysis",
  "progress": 0.62
}
```

---

## Direct Database Access (Read-Only)

### PostgreSQL (Analytics)

```sql
-- Connect via read replica
-- Host: pg-read.financial-research.internal
-- Database: financial_research
-- User: jarvis_ro
-- Password: [from Vault]

-- Example: Get research history for AAPL
SELECT * FROM research_sessions 
WHERE company_ticker = 'AAPL' 
AND status = 'COMPLETED'
ORDER BY completed_at DESC LIMIT 10;

-- Example: Portfolio risk metrics
SELECT * FROM monte_carlo_results 
WHERE portfolio_id = 'port_jarvis_core'
ORDER BY created_at DESC LIMIT 1;
```

### Neo4j (Knowledge Graph)

```cypher
// Connect via Bolt
// Host: neo4j.financial-research.internal:7687
// Database: neo4j
// User: jarvis_ro
// Password: [from Vault]

// Example: Get AAPL competitive landscape
MATCH (c:Company {ticker: 'AAPL'})-[r:COMPETES_WITH]->(comp:Company)
RETURN c, r, comp
LIMIT 20;

// Example: PageRank for sector influence
CALL gds.pageRank.stream('company-graph', {
  nodeLabels: ['Company'],
  relationshipTypes: ['COMPETES_WITH', 'PARTNERS_WITH', 'SUPPLIES_TO'],
  maxIterations: 20
})
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).ticker AS ticker, score
ORDER BY score DESC
LIMIT 10;
```

### ChromaDB (Vector Search)

```python
# Via REST API (read-only)
import chromadb
client = chromadb.HttpClient(host='chroma-read.financial-research.internal', port=8000)
collection = client.get_collection('financial_documents')

results = collection.query(
    query_texts=["Apple China risk supply chain"],
    n_results=10,
    where={"company": "AAPL"}
)
```

---

## Expected Inputs/Outputs

### Research Request Input
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| company | string | Yes | Ticker symbol (e.g., "AAPL") |
| query | string | Yes | Natural language research question |
| complexity | enum | No | SIMPLE/MODERATE/COMPLEX/COMPREHENSIVE |
| auto_approve | boolean | No | Skip human approval (default: false) |
| context | object | No | Portfolio context, risk tolerance, horizon |

### Research Result Output
| Field | Type | Description |
|-------|------|-------------|
| thesis | enum | LONG/SHORT/VALUE/GROWTH/TURNAROUND/EVENT_DRIVEN |
| confidence | float | 0.0-1.0 overall confidence |
| confidence_interval | array | [lower, upper] 95% CI |
| recommendation | enum | BUY/HOLD/SELL |
| target_price | float | 12-month target |
| stop_loss | float | Risk management stop |
| time_horizon_months | int | Investment horizon |
| key_drivers | array | Top 3-5 positive drivers |
| risks | array | Top 3-5 risks |
| evidence_count | int | Total evidence pieces |
| sources | array | Source types used |

### Report Output
| Format | Description |
|--------|-------------|
| MARKDOWN | Human-readable with formatting |
| HTML | Styled report with charts |
| JSON | Machine-readable structured data |

---

## Error Handling

### HTTP Status Codes
| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Process response |
| 202 | Accepted (async) | Poll or use WebSocket |
| 400 | Bad Request | Fix request payload |
| 401 | Unauthorized | Refresh token / check API key |
| 403 | Forbidden | Check scopes/permissions |
| 404 | Not Found | Verify resource ID |
| 429 | Rate Limited | Backoff, retry after Retry-After header |
| 500 | Server Error | Retry with exponential backoff |
| 503 | Service Unavailable | Circuit breaker open, retry later |

### Error Response Format
```json
{
  "error": {
    "code": "RESEARCH_NOT_FOUND",
    "message": "Research session res_xyz not found",
    "details": {"research_id": "res_xyz"},
    "trace_id": "abc123"
  }
}
```

---

## Rate Limits

| Endpoint Category | Limit | Window |
|-------------------|-------|--------|
| Research Start | 10 | minute |
| Research Status | 100 | minute |
| Reports | 20 | minute |
| Knowledge Graph | 200 | minute |
| Memory | 500 | minute |
| Portfolio | 50 | minute |
| Market Data (REST) | 1000 | minute |
| WebSocket Messages | 5000 | second |

Headers returned:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1731939060
Retry-After: 45 (on 429)
```

---

## Future Integration Architecture

### Phase 1: Current (v2.0.0)
- REST + WebSocket + Direct DB
- Service mesh: Istio/Envoy
- Auth: JWT + API Keys

### Phase 2: Q3 2026 (Planned)
- gRPC for internal services
- Async message bus (Kafka) for event streaming
- GraphQL federation for flexible queries
- mTLS everywhere

### Phase 3: Q4 2026 (JARVIS-Native)
- Native JARVIS protocol (protobuf)
- Shared memory for ultra-low latency
- Distributed tracing (Jaeger)
- Self-healing integration

---

## Support

| Channel | Contact |
|---------|---------|
| Integration Issues | #fra-integration (Slack) |
| API Questions | api-support@financial-research.internal |
| Security | security@financial-research.internal |
| Emergency | +1-555-FRA-HELP |

---

**Document Version**: 1.0  
**Last Updated**: 2026-07-18  
**API Version**: v1 (FROZEN)  
**Next Review**: 2026-10-18