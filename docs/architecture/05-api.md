# API Architecture
## Agentic Financial Intelligence Platform

---

## Overview

The platform exposes a comprehensive REST API built with **FastAPI** providing access to all research capabilities, autonomous workflows, and the AI Copilot. The API follows OpenAPI 3.0 specification with automatic documentation generation.

---

## API Structure

### Base Configuration
```python
# api/main.py
app = FastAPI(
    title="Agentic Financial Intelligence Platform",
    description="Autonomous financial research with AI Copilot",
    version="1.7.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Middleware stack (order matters)
app.add_middleware(CORSMiddleware, allow_origins=["*"])
app.add_middleware(RateLimitMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(CompressionMiddleware)

# Router inclusion
app.include_router(research_router, prefix="/api/v1/research", tags=["Research"])
app.include_router(watchlist_router, prefix="/api/v1/watchlists", tags=["Watchlists"])
app.include_router(approval_router, prefix="/api/v1/approval", tags=["Approvals"])
app.include_router(report_router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(copilot_router, prefix="/api/v1/copilot", tags=["Copilot"])
```

### Middleware Stack (Request Flow)
```
Request
   │
   ▼
┌─────────────────────────────────────────────────────────────┐
│  CORSMiddleware        │  Origin validation, preflight      │
├─────────────────────────────────────────────────────────────┤
│  RateLimitMiddleware   │  Token bucket + sliding window     │
├─────────────────────────────────────────────────────────────┤
│  LoggingMiddleware     │  Correlation IDs, structured logs  │
├─────────────────────────────────────────────────────────────┤
│  SecurityMiddleware    │  JWT validation, API keys, RBAC    │
├─────────────────────────────────────────────────────────────┤
│  CompressionMiddleware │  Gzip/Brotli compression           │
├─────────────────────────────────────────────────────────────┤
│  Route Handler         │  Business logic                     │
└─────────────────────────────────────────────────────────────┘
   │
   ▼
Response
```

---

## Research API (Phase 7)

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/research/start` | Start autonomous research |
| GET | `/api/v1/research/{research_id}` | Get research status & results |
| GET | `/api/v1/research/history` | List research history |
| GET | `/api/v1/research/status` | System capacity & active executions |

### Request/Response Models

#### Start Research
```python
# Request
class ResearchStartRequest(BaseModel):
    company: str
    query: str
    context: Optional[Dict] = None
    auto_approve: bool = False
    mode: ResearchMode = ResearchMode.AUTO_EXECUTE

# Response
class ResearchStartResponse(BaseModel):
    research_id: str
    status: ResearchStatus
    estimated_duration_seconds: int
    plan_preview: Optional[ExecutionPlan]
```

#### Research Status
```python
class ResearchStatusResponse(BaseModel):
    research_id: str
    status: ResearchStatus  # pending, running, completed, failed, approved
    company: str
    query: str
    progress: float
    current_step: Optional[str]
    steps: List[ExecutionStep]
    results: Optional[ResearchResults]
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
```

### Example Usage
```bash
# Start research
curl -X POST http://localhost:8000/api/v1/research/start \
  -H "Content-Type: application/json" \
  -d '{"company": "NVDA", "query": "Analyze competitive position in AI chips"}'

# Check status
curl http://localhost:8000/api/v1/research/{research_id}
```

---

## Watchlist API (Phase 7)

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/watchlists` | Create watchlist |
| GET | `/api/v1/watchlists` | List watchlists |
| GET | `/api/v1/watchlists/{watchlist_id}` | Get watchlist details |
| DELETE | `/api/v1/watchlists/{watchlist_id}` | Delete watchlist |
| POST | `/api/v1/watchlists/{watchlist_id}/companies` | Add company |
| DELETE | `/api/v1/watchlists/{watchlist_id}/companies/{symbol}` | Remove company |
| POST | `/api/v1/watchlists/{watchlist_id}/alerts` | Create alert rule |

### Watchlist Types
```python
class WatchlistType(str, Enum):
    PERSONAL = "personal"
    PORTFOLIO = "portfolio"
    SECTOR = "sector"
    THEMATIC = "thematic"
    COMPETITOR = "competitor"
```

### Alert Conditions
```python
class AlertConditionType(str, Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    VOLUME_SPIKE = "volume_spike"
    RSI_OVERBOUGHT = "rsi_overbought"
    RSI_OVERSOLD = "rsi_oversold"
    SENTIMENT_POSITIVE = "sentiment_positive"
    SENTIMENT_NEGATIVE = "sentiment_negative"
    AGENT_SIGNAL = "agent_signal"
    PATTERN_DETECTED = "pattern_detected"
    EARNINGS_DATE = "earnings_date"
```

---

## Approval API (Phase 7)

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/approval/{approval_id}` | Get approval request |
| POST | `/api/v1/approval/{approval_id}/action` | Process approval action |
| GET | `/api/v1/approval` | List approval requests |

### Approval Actions
```python
class ApprovalAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"
    ESCALATE = "escalate"
    DELEGATE = "delegate"
    COMMENT = "comment"
```

### Example
```bash
# Process approval
curl -X POST http://localhost:8000/api/v1/approval/{approval_id}/action \
  -H "Content-Type: application/json" \
  -d '{"action": "approve", "comment": "Looks good", "user": "analyst1"}'
```

---

## Report API (Phase 7)

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/reports/generate` | Generate report |
| GET | `/api/v1/reports` | List generated reports |
| GET | `/api/v1/reports/{report_id}` | Get report |
| GET | `/api/v1/reports/{report_id}/download` | Download report |

### Report Types
```python
class ReportType(str, Enum):
    EXECUTIVE_SUMMARY = "executive_summary"
    ANALYST_REPORT = "analyst_report"
    INVESTMENT_THESIS = "investment_thesis"
    COMPANY_SNAPSHOT = "company_snapshot"
    INDUSTRY_ANALYSIS = "industry_analysis"
    DAILY_BRIEFING = "daily_briefing"
    WEEKLY_BRIEFING = "weekly_briefing"
    MONTHLY_BRIEFING = "monthly_briefing"
```

### Formats
```python
class ReportFormat(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
```

---

## Copilot API (Phase 8)

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/copilot/chat` | Natural language chat (streaming) |
| POST | `/api/v1/copilot/sessions` | Create session |
| GET | `/api/v1/copilot/sessions` | List sessions |
| GET | `/api/v1/copilot/sessions/{session_id}` | Get session |
| DELETE | `/api/v1/copilot/sessions/{session_id}` | Delete session |
| POST | `/api/v1/copilot/sessions/{session_id}/plan` | Create execution plan |
| POST | `/api/v1/copilot/sessions/{session_id}/execute` | Execute plan |
| GET | `/api/v1/copilot/tools` | List available tools |
| POST | `/api/v1/copilot/tools/execute` | Execute tool |
| POST | `/api/v1/copilot/reports/generate` | Generate report via copilot |
| POST | `/api/v1/copilot/watchlists` | Create watchlist |
| GET | `/api/v1/copilot/watchlists` | List watchlists |
| GET | `/api/v1/copilot/approval/{approval_id}` | Get approval |
| POST | `/api/v1/copilot/approval/{approval_id}/action` | Process approval |
| GET | `/api/v1/copilot/sessions/{session_id}/history` | Session history |
| GET | `/api/v1/copilot/sessions/{session_id}/status` | Session status |
| GET | `/api/v1/copilot/health` | Copilot health check |

### Chat Streaming (Server-Sent Events)
```python
# Request
{
    "message": "Analyze NVDA's competitive moat",
    "session_id": "optional-existing-session",
    "mode": "auto_execute"
}

# Response (SSE)
data: {"type": "thinking", "content": "Analyzing competitive position..."}
data: {"type": "tool_call", "tool": "competitive_intelligence", "status": "running"}
data: {"type": "tool_result", "tool": "competitive_intelligence", "result": {...}}
data: {"type": "answer", "content": "NVIDIA's competitive moat..."}
data: {"type": "citations", "citations": [...]}
data: {"type": "done", "session_id": "abc123"}
```

### Plan & Execute
```bash
# Create plan
curl -X POST http://localhost:8000/api/v1/copilot/sessions/{session_id}/plan \
  -H "Content-Type: application/json" \
  -d '{"goal": "Full competitive analysis of NVDA", "mode": "plan_only"}'

# Execute plan
curl -X POST http://localhost:8000/api/v1/copilot/sessions/{session_id}/execute \
  -H "Content-Type: application/json" \
  -d '{"plan_id": "plan_abc123"}'
```

---

## System Endpoints

### Health Checks
| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Basic liveness |
| `GET /health/live` | Kubernetes liveness probe |
| `GET /health/ready` | Kubernetes readiness probe |
| `GET /health/detailed` | Full component health |
| `GET /metrics` | Prometheus metrics |

### Detailed Health Response
```json
{
  "status": "healthy",
  "version": "1.7.0",
  "timestamp": "2026-07-18T10:30:00Z",
  "components": {
    "database": {"status": "healthy", "latency_ms": 12},
    "vector_store": {"status": "healthy", "collections": 5},
    "redis": {"status": "healthy", "latency_ms": 3},
    "llm_provider": {"status": "healthy", "models_available": 9},
    "agents": {"status": "healthy", "active": 14},
    "disk": {"status": "healthy", "free_gb": 45.2},
    "memory": {"status": "healthy", "used_mb": 210}
  }
}
```

### Metrics (Prometheus)
```
# HTTP metrics
http_requests_total{method="POST", endpoint="/api/v1/copilot/chat", status="200"}
http_request_duration_seconds_bucket{endpoint="/api/v1/copilot/chat", le="2.0"}

# LLM metrics
llm_tokens_total{model="claude-3.5-sonnet", type="input"}
llm_tokens_total{model="claude-3.5-sonnet", type="output"}
llm_cost_usd_total{model="claude-3.5-sonnet"}

# Agent metrics
agent_executions_total{agent="risk_assessment", status="success"}
agent_duration_seconds{agent="financial_document"}

# Business metrics
research_sessions_total{status="completed"}
copilot_sessions_active
```

---

## Authentication & Authorization

### JWT Bearer Token
```bash
# Header
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...

# Token payload
{
  "sub": "user123",
  "roles": ["analyst"],
  "permissions": ["research:read", "research:write", "watchlist:*"],
  "exp": 1705564800
}
```

### API Key
```bash
# Header
X-API-Key: fk_live_abc123def456...

# Or query param (less secure)
?api_key=fk_live_abc123def456
```

### RBAC Permissions
| Role | Permissions |
|------|-------------|
| `admin` | `*`, `admin:*` |
| `analyst` | `research:*`, `watchlist:*`, `report:*`, `approval:*`, `copilot:*` |
| `viewer` | `research:read`, `watchlist:read`, `report:read` |
| `api_only` | `research:read`, `copilot:chat` |

---

## Rate Limiting

### Default Limits
| Tier | Requests/Minute | Burst |
|------|-----------------|-------|
| Anonymous | 10 | 20 |
| API Key | 60 | 120 |
| JWT (viewer) | 60 | 120 |
| JWT (analyst) | 300 | 600 |
| JWT (admin) | 1000 | 2000 |

### Headers
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1705564800
Retry-After: 30  # On 429
```

---

## Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input parameters",
    "details": [
      {
        "field": "company",
        "message": "Company ticker required"
      }
    ],
    "request_id": "req_abc123"
  }
}
```

### HTTP Status Codes
| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (async) |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 429 | Rate Limited |
| 500 | Internal Error |
| 503 | Service Unavailable |

---

## Versioning

### URL Versioning
```
/api/v1/...
/api/v2/...  (future)
```

### Deprecation Policy
- 6 months notice for breaking changes
- Deprecation headers on endpoints
- Migration guides in changelog

---

## OpenAPI Documentation

### Auto-Generated
- **Swagger UI**: `GET /docs`
- **ReDoc**: `GET /redoc`
- **OpenAPI JSON**: `GET /openapi.json`

### Custom Extensions
```python
# x-code-samples for each endpoint
# x-rate-limit for rate limit info
# x-auth for authentication requirements
# x-deprecated for deprecated endpoints
```

---

## Testing the API

### With curl
```bash
# Health check
curl http://localhost:8000/health

# Start research
curl -X POST http://localhost:8000/api/v1/research/start \
  -H "Content-Type: application/json" \
  -d '{"company": "NVDA", "query": "Analyze AI chip market position"}'

# Chat with copilot
curl -X POST http://localhost:8000/api/v1/copilot/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is NVDA's competitive advantage?"}'
```

### With Python SDK (conceptual)
```python
from financial_research import FinancialResearchClient

client = FinancialResearchClient(
    base_url="http://localhost:8000",
    api_key="fk_live_..."
)

# Start research
research = await client.research.start(
    company="NVDA",
    query="Analyze competitive position"
)

# Chat with copilot
response = await client.copilot.chat(
    message="What's NVDA's moat?",
    session_id=research.session_id
)
```

---

*Document Version: 1.0*  
*Last Updated: 2026-07-18*  
*Platform: Agentic Financial Intelligence Platform v1.7.0-phase8*