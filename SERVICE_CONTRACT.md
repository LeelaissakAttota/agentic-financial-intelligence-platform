# Service Contract
## Financial Research Agent v2.0.0

**Version**: v2.0.0  
**Status**: Stable Release - Maintenance Mode  
**Contract Version**: 1.0  
**Effective**: 2026-07-18  
**Next Review**: 2027-01-18

---

## Purpose

This document defines the service contract between the Financial Research Agent (FRA) and its consumers, specifically the JARVIS AI CEO ecosystem. It establishes responsibilities, boundaries, interfaces, and guarantees.

---

## Service Identity

| Attribute | Value |
|-----------|-------|
| Service Name | financial-research-agent |
| Version | v2.0.0 |
| Environment | Production |
| Ownership | AI Architecture Team |
| SLA Tier | Platinum |

---

## Responsibilities

### FRA Responsibilities (Provider)

| Responsibility | Description | SLA |
|----------------|-------------|-----|
| Research Execution | Autonomous multi-agent research with AI debate | 99.9% availability |
| Report Generation | 8 report types, 3 formats | <5 min for standard |
| Knowledge Graph | Graph queries, algorithms, sync | <200ms p95 |
| Real-Time Intelligence | Market data, news streaming | <50ms latency |
| Portfolio Analytics | Risk metrics, Monte Carlo, stress | <10s for 10K paths |
| Memory Management | Cross-agent memory, 5 scopes | <100ms p95 |
| API Availability | REST + WebSocket endpoints | 99.95% uptime |
| Data Integrity | ACID transactions, audit logs | Zero data loss |
| Security | AuthZ/AuthN, rate limiting, encryption | Zero critical vulns |

### Consumer Responsibilities (JARVIS)

| Responsibility | Description |
|----------------|-------------|
| Authentication | Provide valid JWT/API key with required scopes |
| Rate Limiting | Respect X-RateLimit headers, implement backoff |
| Error Handling | Implement retry with exponential backoff |
| Circuit Breaker | Respect 503 responses, don't hammer |
| Data Validation | Validate requests before sending |
| Monitoring | Report anomalies via #fra-integration |
| Version Pinning | Pin to v1 API, test before upgrades |

---

## Service Boundaries

### In Scope (FRA Owns)

| Domain | Components |
|--------|------------|
| Research Orchestration | Planner, orchestrator, agents, memory, debate, synthesis |
| Document Intelligence | SEC filings, earnings, presentations, RAG pipeline |
| News Intelligence | 6 providers, NLP pipeline, event detection, summarization |
| Market Data | Quotes, technicals, fundamentals, real-time streaming |
| Risk Analytics | VaR, CVaR, Monte Carlo, stress, factor models |
| Portfolio Management | Positions, orders, rebalancing, risk metrics |
| Knowledge Graph | Neo4j graph, algorithms, PG sync, Cypher API |
| Pattern Detection | 10 pattern types, backtesting, performance |
| Alert Engine | 30+ types, 5 channels, dedup, cooldown |
| Copilot | Natural language chat, planning, execution |
| Memory | Cross-agent, 9 types, 5 scopes, supersession |
| Reports | 8 types, 3 formats, Jinja2 templates |

### Out of Scope (Consumer Owns)

| Domain | Owned By |
|--------|----------|
| Trade Execution | Multi-Market Trading Agent |
| Portfolio Construction | JARVIS Portfolio Manager |
| Risk Limits | JARVIS Risk Controller |
| Strategy Decisions | JARVIS Strategy Engine |
| Regulatory Reporting | Compliance Agent |
| Customer Data | CRM/CDP |
| Order Management | OMS/EMS |
| Accounting | General Ledger |

---

## Interface Contracts

### REST API v1 (Frozen)

| Endpoint | Method | Contract |
|----------|--------|----------|
| `/api/v1/research/start` | POST | StartResearchRequest → ResearchResponse |
| `/api/v1/research/{id}` | GET | ResearchStatusResponse |
| `/api/v1/research/{id}/result` | GET | ResearchResultResponse |
| `/api/v1/research/history` | GET | ResearchHistoryResponse |
| `/api/v1/reports/generate` | POST | GenerateReportRequest → ReportResponse |
| `/api/v1/reports/{id}/download` | GET | File download |
| `/api/v1/kg/query` | POST | CypherQueryRequest → GraphResponse |
| `/api/v1/kg/algorithms/{name}` | POST | AlgorithmRequest → AlgorithmResponse |
| `/api/v1/kg/companies/{ticker}/context` | GET | CompanyContextResponse |
| `/api/v1/memory/write` | POST | WriteMemoryRequest → WriteMemoryResponse |
| `/api/v1/memory/read` | GET | ReadMemoryResponse |
| `/api/v1/memory/query` | POST | MemoryQueryRequest → MemoryQueryResponse |
| `/api/v1/portfolio` | POST | CreatePortfolioRequest → PortfolioResponse |
| `/api/v1/portfolio/{id}/risk` | POST | RiskRequest → RiskResponse |
| `/api/v1/portfolio/{id}/rebalance` | POST | RebalanceRequest → RebalanceResponse |
| `/api/v1/market/quote` | GET | QuoteResponse |
| `/api/v1/market/technical` | GET | TechnicalResponse |
| `/api/v1/news/search` | GET | NewsSearchResponse |

### WebSocket v1 (Frozen)

| Channel | Protocol | Auth | Message Format |
|---------|----------|------|----------------|
| `research/{id}` | WSS | JWT/API Key | ResearchProgressEvent |
| `market/quotes` | WSS | JWT/API Key | MarketQuoteEvent |
| `market/trades` | WSS | JWT/API Key | MarketTradeEvent |
| `market/depth` | WSS | JWT/API Key | MarketDepthEvent |
| `news/stream` | WSS | JWT/API Key | NewsArticleEvent |
| `portfolio/{id}` | WSS | JWT/API Key | PortfolioEvent |
| `workflow/{id}` | WSS | JWT/API Key | WorkflowEvent |

### Direct Database Access (Read-Only)

| Database | Access | Purpose |
|----------|--------|---------|
| PostgreSQL (read replica) | Read-only | Analytics, reporting, history |
| Neo4j (read) | Read-only | Graph traversal, algorithms |
| ChromaDB (read) | Read-only | Vector similarity search |

---

## Data Contracts

### Research Request Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["company", "query"],
  "properties": {
    "company": {"type": "string", "pattern": "^[A-Z]{1,5}$"},
    "query": {"type": "string", "minLength": 10, "maxLength": 2000},
    "complexity": {"type": "string", "enum": ["SIMPLE", "MODERATE", "COMPLEX", "COMPREHENSIVE"], "default": "COMPREHENSIVE"},
    "auto_approve": {"type": "boolean", "default": false},
    "context": {
      "type": "object",
      "properties": {
        "portfolio_id": {"type": "string"},
        "risk_tolerance": {"type": "string", "enum": ["CONSERVATIVE", "MODERATE", "AGGRESSIVE"]},
        "horizon_months": {"type": "integer", "minimum": 1, "maximum": 60},
        "current_position_pct": {"type": "number", "minimum": 0, "maximum": 100},
        "target_position_pct": {"type": "number", "minimum": 0, "maximum": 100}
      }
    }
  }
}
```

### Research Result Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["research_id", "company", "thesis", "evidence"],
  "properties": {
    "research_id": {"type": "string"},
    "company": {"type": "string"},
    "thesis": {
      "type": "object",
      "required": ["type", "confidence", "recommendation", "target_price"],
      "properties": {
        "type": {"type": "string", "enum": ["LONG", "SHORT", "VALUE", "GROWTH", "TURNAROUND", "EVENT_DRIVEN"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "confidence_interval": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2},
        "recommendation": {"type": "string", "enum": ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]},
        "target_price": {"type": "number", "minimum": 0},
        "stop_loss": {"type": "number", "minimum": 0},
        "time_horizon_months": {"type": "integer", "minimum": 1, "maximum": 60}
      }
    },
    "evidence": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "type", "source", "content", "relevance", "credibility"],
        "properties": {
          "id": {"type": "string"},
          "type": {"type": "string"},
          "source": {"type": "string"},
          "content": {"type": "string"},
          "relevance": {"type": "number", "minimum": 0, "maximum": 1},
          "credibility": {"type": "number", "minimum": 0, "maximum": 1},
          "timestamp": {"type": "string", "format": "date-time"}
        }
      }
    }
  }
}
```

---

## Quality Guarantees

### Availability

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Uptime | 99.95% | Monthly |
| WebSocket Uptime | 99.9% | Monthly |
| Database Uptime | 99.99% | Monthly |
| Scheduled Maintenance | <4 hrs/month | Planned windows |

### Latency (p95)

| Operation | Target |
|-----------|--------|
| Health Check | <50ms |
| Research Status | <200ms |
| Graph Query | <200ms |
| Memory Query | <300ms |
| Market Quote | <100ms |
| Report Generation | <300s |

### Throughput

| Endpoint | Sustained RPS | Burst RPS |
|----------|---------------|-----------|
| REST API | 500 | 1000 |
| WebSocket | 10,000 msg/s | 20,000 msg/s |
| Graph Queries | 200 | 500 |

### Data Quality

| Metric | Guarantee |
|--------|-----------|
| Data Freshness | Market data <1s, News <5min |
| Accuracy | Calculations verified against reference |
| Completeness | 100% for requested data |
| Consistency | ACID for writes, eventual for reads |

---

## Security Contract

### Authentication
- JWT RS256 with JWKS (primary)
- API Key bcrypt + scopes (alternative)
- Token rotation: 15min access, 7d refresh

### Authorization
- RBAC: Admin/Analyst/Viewer/API_Only
- Scopes: 10 granular permissions
- Resource-level permissions for portfolio data

### Encryption
- TLS 1.3 for all external traffic
- AES-256 at rest (DB, vectors, cache)
- mTLS for service mesh (staging)

### Rate Limits
- Per-client token bucket
- Per-endpoint sliding window
- Standard headers (X-RateLimit-*)

---

## Error Handling Contract

### HTTP Status Codes
| Code | Meaning | Retryable |
|------|---------|-----------|
| 200 | Success | N/A |
| 202 | Accepted (async) | N/A |
| 400 | Bad Request | No |
| 401 | Unauthorized | Yes (re-auth) |
| 403 | Forbidden | No |
| 404 | Not Found | No |
| 429 | Rate Limited | Yes (backoff) |
| 500 | Server Error | Yes (exp backoff) |
| 503 | Unavailable | Yes (circuit breaker) |

### Error Response
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {},
    "trace_id": "uuid"
  }
}
```

---

## Versioning & Lifecycle

### API Versioning
- **Current**: v1 (FROZEN)
- **Format**: URL path `/v1/`
- **Deprecation**: 12 months notice
- **Sunset**: 18 months after deprecation

### Release Schedule
| Release Type | Frequency | Notice |
|--------------|-----------|--------|
| Patch (bug/security) | As needed | 0 days |
| Minor (additive) | Quarterly | 30 days |
| Major (breaking) | Annual | 365 days |

### Deprecation Policy
1. Announce via GitHub releases + #fra-integration
2. Maintain old version for 12 months
3. Provide migration guide
4. Monitor usage, communicate with consumers

---

## Monitoring & Observability

### Metrics Exposed
| Metric | Type | Labels |
|--------|------|--------|
| `fra_api_requests_total` | Counter | method, endpoint, status |
| `fra_api_latency_seconds` | Histogram | method, endpoint |
| `fra_research_active` | Gauge | - |
| `fra_research_duration_seconds` | Histogram | complexity |
| `fra_websocket_connections` | Gauge | channel |
| `fra_kg_query_duration_seconds` | Histogram | algorithm |

### Health Endpoints
| Endpoint | Checks |
|----------|--------|
| `/health/live` | Process alive |
| `/health/ready` | DB, Redis, ChromaDB, Neo4j |
| `/health/detailed` | All dependencies + metrics |

---

## Disaster Recovery

### RPO/RTO
| Tier | RPO | RTO |
|------|-----|-----|
| PostgreSQL | <1 min | <15 min |
| Neo4j | <5 min | <30 min |
| ChromaDB | <5 min | <30 min |
| Redis | <1 min | <5 min |

### Backup Schedule
| Data | Frequency | Retention |
|------|-----------|-----------|
| PostgreSQL | Continuous (WAL) + Daily | 30 days |
| Neo4j | Daily | 14 days |
| ChromaDB | Daily | 7 days |
| Config/Secrets | On change | 90 days |

---

## Support & Escalation

### Channels
| Channel | Purpose | Response Time |
|---------|---------|---------------|
| `#fra-integration` | General questions | 4 hours |
| `fra-support@internal` | Technical issues | 2 hours |
| PagerDuty `FRA-CRITICAL` | Production outages | 15 minutes |
| GitHub Issues | Bug reports | 24 hours |

### Escalation Path
1. #fra-integration (Slack)
2. fra-support@internal (Email)
3. PagerDuty on-call (Critical)
4. Architecture Review Board (Breaking changes)

---

## Compliance

| Standard | Status |
|----------|--------|
| GDPR | Compliant |
| CCPA | Compliant |
| SOC 2 Type II | Phase 10 |
| ISO 27001 | Phase 10 |

---

## Financial Terms

| Aspect | Terms |
|--------|-------|
| Pricing | Internal service (no chargeback) |
| Quotas | Defined per consumer |
| Overages | Alert + auto-throttle |
| Support | Included in platform budget |

---

## Signatures

| Role | Organization | Signature | Date |
|------|--------------|-----------|------|
| Service Owner | AI Architecture | | 2026-07-18 |
| Consumer Lead | JARVIS AI CEO | | 2026-07-18 |
| Security | Security Architecture | | 2026-07-18 |
| Platform | Platform Engineering | | 2026-07-18 |

---

**Contract Status**: ✅ **ACTIVE - FROZEN v1**  
**Next Review**: 2027-01-18  
**Document Version**: 1.0