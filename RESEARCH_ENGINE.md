# Research Engine - Autonomous Financial Research System

## Overview

The Research Engine is the core autonomous system that transforms high-level research goals into comprehensive financial analyses. It combines intelligent planning, multi-agent orchestration, persistent memory, and automated reporting.

## Core Components

### 1. Research Planner Agent

**File**: `agents/research_planner/agent.py`

**Purpose**: LLM-driven dynamic task planning based on query complexity.

**Key Features**:
- **Complexity Classification**: 4 levels (SIMPLE, MODERATE, COMPLEX, COMPREHENSIVE)
- **Agent Selection**: 14 agent types with capability matching
- **Dependency Resolution**: Automatic topological ordering
- **Parallel Grouping**: Identifies independent steps for concurrent execution
- **Duration Estimation**: Per-step time estimates

**Usage**:
```python
from agents.research_planner.agent import create_research_plan, ExecutionPlan

plan = await create_research_plan(
    query="Full investment thesis for NVIDIA including competitive analysis",
    company="NVDA"
)
# Returns ExecutionPlan with steps, dependencies, parallel groups
```

### 2. Workflow Orchestrator

**File**: `workflows/orchestrator.py`

**Purpose**: Execute research plans with proper dependency management.

**Key Features**:
- **Topological Sort**: Resolves dependencies into execution waves
- **Parallel Execution**: Configurable concurrency (default 4)
- **Retry Logic**: Exponential backoff (1m, 5m, 15m)
- **Context Propagation**: Shared context between steps
- **Memory Integration**: Automatic storage of agent outputs
- **Progress Callbacks**: Real-time execution tracking

**Usage**:
```python
from workflows.orchestrator import execute_research_plan
from agents.research_planner.agent import create_research_plan

plan = await create_research_plan(query, company)
execution = await execute_research_plan(plan, progress_callback=callback)

# Check results
for step_id, result in execution.step_results.items():
    if result.status == StepStatus.COMPLETED:
        print(f"{step_id}: {result.result}")
```

### 3. Research Memory

**File**: `memory/research_memory.py`

**Purpose**: Persistent storage and retrieval of research knowledge.

**Memory Types** (7):
| Type | Purpose |
|------|---------|
| SESSION | Complete research sessions |
| CONCLUSION | Key findings with evidence |
| SOURCE | Document/source references |
| AGENT_OUTPUT | Raw agent results |
| FOLLOW_UP | Questions for future research |
| REPORT | Generated reports |
| INSIGHT | Synthesized insights |

**Key Operations**:
```python
from memory.research_memory import get_memory_store

store = get_memory_store()

# Store session
session = await store.create_session("NVDA", "Analyze competitive position")
await store.store_session(session)

# Store conclusion
await store.store_conclusion(
    company="NVDA",
    conclusion="Strong moat in AI chips",
    supporting_evidence=["Market share 80%", "CUDA lock-in"],
    confidence=0.9,
    session_id=session.session_id,
    agent_type="competitive"
)

# Get context for new research
context = await store.get_relevant_context("NVDA", "risk analysis")
```

### 4. Task Orchestration

**Coordination Layer**: The orchestrator automatically dispatches tasks to all available agents:

| Agent | Trigger | Input Context |
|-------|---------|---------------|
| Market Data | Price/technical queries | Company, timeframe |
| News | Events, sentiment | Company, topics, timeframe |
| Financial Document | SEC filings, earnings | Company, year/quarter |
| Knowledge Graph | Entity relationships | Company, entities |
| Analytics | Factor models, Monte Carlo | Portfolio, symbols |
| Portfolio | Positions, risk | Holdings, benchmarks |
| Patterns | Technical patterns | Symbol, timeframe |
| Memory | Cross-agent knowledge | Company, query |

**Context Passing**: Each step receives:
- Original query and company
- Results from dependency steps (in `dependency_results`)
- Shared context from previous waves
- Custom metadata from planner

### 5. Automated Report Generation

**File**: `reports/generator.py`

**Report Types**:
- **Executive Summary** (1-2 pages): Key findings, recommendation
- **Analyst Report** (10-20 pages): Full fundamental analysis
- **Investment Thesis** (5-10 pages): Rationale, drivers, risks
- **Company Snapshot** (1-2 pages): Quick reference
- **Industry Analysis** (5-15 pages): Sector dynamics
- **Daily Briefing** (2-3 pages): Markets, movers, news
- **Weekly Briefing** (3-5 pages): Week review, outlook
- **Monthly Intelligence** (10-20 pages): Strategic themes

**Output Formats**:
- Markdown (primary, version control friendly)
- HTML (styled, web-ready)
- JSON (structured, API-friendly)

**Template System**: Jinja2 with inheritance, customizable per report type.

### 6. Watchlist Monitoring

**File**: `watchlists/manager.py`

**Features**:
- Multiple watchlist types (personal, portfolio, sector, thematic)
- Company tracking with target prices, stop losses
- Alert rules with complex conditions
- Cooldown and rate limiting
- Multi-channel notifications

**Alert Conditions**:
```python
conditions = {
    "price_above": 500.0,
    "price_change_pct": 5.0,
    "volume_spike": 3.0,
    "rsi_above": 70,
    "rsi_below": 30,
    "news_sentiment": 0.5,
    "news_count": 10,
    "agent_signal": {"agent": "risk", "signal": "high"}
}
```

### 7. Notification Engine

**File**: `notifications/engine.py`

**Channels**:
- Email (SMTP with TLS)
- Slack (webhook with blocks)
- Discord (webhook with embeds)
- Webhook (generic with headers)
- Console (development)
- In-App (database)

**Reliability**:
- Retry with exponential backoff
- Configurable max retries
- Delivery status tracking
- History persistence

### 8. Human Approval Workflow

**File**: `approval/workflow.py`

**Actions**: APPROVE, REJECT, REQUEST_CHANGES, ESCALATE, DELEGATE, COMMENT

**Features**:
- Sequential approval chains
- Escalation with auto-approver addition
- Delegation support
- Expiration handling
- Full audit trail
- Integration with notification engine

## API Reference

### Start Research
```bash
POST /api/v1/research/start
{
  "company": "NVDA",
  "query": "Full investment thesis including risk assessment",
  "auto_approve": false,
  "custom_context": {}
}
```

**Response**:
```json
{
  "research_id": "abc12345",
  "status": "pending_approval",
  "message": "Research plan created, awaiting human approval",
  "plan": {
    "plan_id": "plan_001",
    "complexity": "comprehensive",
    "steps": [...]
  }
}
```

### Get Research Status
```bash
GET /api/v1/research/{research_id}
```

**Response**:
```json
{
  "research_id": "abc12345",
  "company": "NVDA",
  "query": "Full investment thesis...",
  "status": "completed",
  "results": {
    "step_0_market_data": {"status": "completed", "data": {...}},
    "step_1_news": {"status": "completed", "data": {...}}
  },
  "conclusions": [...]
}
```

### Create Watchlist
```bash
POST /api/v1/watchlists
{
  "name": "AI Semiconductors",
  "description": "Track AI chip companies",
  "type": "thematic",
  "owner_id": "analyst_001",
  "companies": ["NVDA", "AMD", "INTC"]
}
```

### Create Alert Rule
```bash
POST /api/v1/watchlists/{watchlist_id}/alerts
{
  "name": "NVDA Price Alert",
  "description": "Alert on significant price moves",
  "conditions": {"price_change_pct": 5.0},
  "severity": "warning",
  "channels": ["email", "slack"],
  "cooldown_minutes": 60
}
```

### Process Approval
```bash
POST /api/v1/approval/{request_id}/action
{
  "action": "approve",
  "user_id": "senior_analyst",
  "user_name": "Jane Doe",
  "comment": "Plan looks comprehensive"
}
```

### Generate Report
```bash
POST /api/v1/reports/generate
{
  "report_type": "analyst_report",
  "company": "NVDA",
  "session_id": "abc12345",
  "format": "markdown",
  "custom_data": {}
}
```

## Integration Guide

### Adding a New Agent

1. Implement `BaseWorkerAgent` interface
2. Register in `workflows/orchestrator.py`:
```python
agent_map = {
    AgentType.YOUR_AGENT: "agents.your_agent.agent.YourAgent",
}
```
3. Add capability description in `agents/research_planner/agent.py`
4. Create templates in `reports/templates/`

### Custom Report Type

1. Add to `ReportType` enum
2. Create builder method `_build_your_report_sections()`
3. Create template in `reports/templates/your_report.md`
4. Add formatting helpers

### Custom Alert Condition

1. Extend `_evaluate_conditions()` in `watchlists/manager.py`
2. Add condition type to `AlertRuleData` conditions schema
3. Document in API reference

## Configuration

### Environment Variables
```bash
# SMTP for email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@company.com
SMTP_PASSWORD=app-password
SMTP_USE_TLS=true
FROM_EMAIL=research@company.com

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Webhook
WEBHOOK_URL=https://your-endpoint.com/webhook
WEBHOOK_HEADERS={"Authorization": "Bearer token"}
```

### Settings (config/settings.py)
Added to `AppSettings`:
- `smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`, `smtp_use_tls`
- `from_email`
- `slack_webhook_url`
- `discord_webhook_url`
- `webhook_url`, `webhook_headers`
- `rate_limit_requests`, `rate_limit_window`

## Database Schema

Run Alembic migration for new tables:
```bash
alembic revision --autogenerate -m "Add Phase 7 tables"
alembic upgrade head
```

Tables:
- `research_sessions`
- `research_memory`
- `watchlists`
- `watchlist_items`
- `alert_rules`
- `approval_requests`
- `notifications`

## Monitoring

### Key Metrics
- Research execution duration (per step, total)
- Agent success/failure rates
- Approval request turnaround time
- Notification delivery success rate
- Alert trigger frequency
- Report generation latency

### Health Checks
- `/health/live` - Liveness probe
- `/health/ready` - Readiness probe
- `/health/detailed` - Full dependency check

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Plan execution stuck | Circular dependency | Check planner dependency logic |
| Agent timeout | Complex analysis | Increase timeout in orchestrator |
| Memory not found | Session ID mismatch | Verify session_id in requests |
| Alert not firing | Cooldown active | Check last_triggered, cooldown_minutes |
| Email not sending | SMTP config | Verify SMTP credentials, TLS |
| Approval expired | Short expiry | Increase expires_in_hours |

### Debug Mode
Set `LOG_LEVEL=DEBUG` for detailed execution logs.

## Performance Optimization

1. **Connection Pooling**: PostgreSQL pool (default 10 connections)
2. **Async I/O**: All external calls use aiohttp/aiohttp
3. **Caching**: ResearchMemory caches recent sessions
4. **Parallel Execution**: Configurable wave parallelism
5. **Batch Operations**: Notifications batched per channel

## Future Enhancements

- [ ] WebSocket for real-time dashboard
- [ ] pgvector for semantic memory search
- [ ] Neo4j for Knowledge Graph persistence
- [ ] Custom agent plugin system
- [ ] Multi-tenant isolation
- [ ] Advanced scheduling (cron triggers)
- [ ] Collaborative research sessions
- [ ] PDF export with WeasyPrint