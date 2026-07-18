# Workflow Architecture - Autonomous Financial Research Platform

## System Overview

The Phase 7 implementation transforms the Financial Research Agent into an autonomous AI research system capable of planning, executing, monitoring, and summarizing financial research with minimal human intervention.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS RESEARCH WORKFLOW SYSTEM                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────────────┐   │
│  │   CLIENT     │───▶│  RESEARCH API    │───▶│  RESEARCH PLANNER AGENT  │   │
│  │  (REST/WS)   │    │  /api/v1/research│    │  • Complexity Analysis   │   │
│  └──────────────┘    └────────┬─────────┘    │  • Agent Selection       │   │
│                               │              │  • Dependency Resolution │   │
│                               ▼              │  • Plan Generation       │   │
│                        ┌──────────────────┐  └───────────┬─────────────┘   │
│                        │ APPROVAL WORKFLOW│              │                 │
│                        │  • Sequential    │              ▼                 │
│                        │  • Escalation    │  ┌──────────────────────────┐   │
│                        │  • Delegation    │  │  WORKFLOW ORCHESTRATOR   │   │
│                        └────────┬─────────┘  │  • Topological Sort      │   │
│                               │             │  • Parallel Wave Exec    │   │
│                               ▼             │  • Retry/Error Handling  │   │
│                        ┌──────────────────┐  │  • Context Propagation   │   │
│                        │  RESEARCH MEMORY │  │  • Progress Tracking     │   │
│                        │  • Sessions      │  └───────────┬─────────────┘   │
│                        │  • Conclusions   │              │                 │
│                        │  • Agent Outputs │              ▼                 │
│                        │  • Sources       │  ┌──────────────────────────┐   │
│                        │  • Embeddings    │  │    AGENT EXECUTION LAYER  │   │
│                        └────────┬─────────┘  │  ┌─────┬─────┬─────┬───┐   │
│                               │             │  │Market│News │Risk │...│   │
│                               ▼             │  └─────┴─────┴─────┴───┘   │
│                        ┌──────────────────┐  └───────────┬─────────────┘   │
│                        │  NOTIFICATIONS   │              │                 │
│                        │  • Email         │              ▼                 │
│                        │  • Slack         │  ┌──────────────────────────┐   │
│                        │  • Discord       │  │   WATCHLISTS & ALERTS    │   │
│                        │  • Webhook       │  │  • Company Tracking      │   │
│                        │  • In-App        │  │  • Alert Rules           │   │
│                        └──────────────────┘  │  • Real-time Monitoring  │   │
│                                              └───────────┬─────────────┘   │
│                                                         │                 │
│                                                         ▼                 │
│                                              ┌──────────────────────────┐   │
│                                              │    REPORT GENERATOR      │   │
│                                              │  • Executive Summary     │   │
│                                              │  • Analyst Report        │   │
│                                              │  • Investment Thesis     │   │
│                                              │  • Company Snapshot      │   │
│                                              │  • Industry Analysis     │   │
│                                              │  • Daily/Weekly/Monthly  │   │
│                                              │  • Markdown/HTML/JSON    │   │
│                                              └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Research Planner Agent (`agents/research_planner/agent.py`)

**Responsibility**: Convert high-level research goals into executable plans.

**Key Classes**:
- `QueryComplexity`: SIMPLE, MODERATE, COMPLEX, COMPREHENSIVE
- `AgentType`: 14 agent types with capability descriptions
- `ExecutionStep`: Single step with dependencies, parallel group, duration
- `ExecutionPlan`: Complete plan with steps, complexity, estimated duration
- `ResearchPlannerAgent`: Main agent class

**Flow**:
```
Query + Company → Complexity Analysis → Agent Selection → Step Creation → 
Dependency Resolution → Parallel Grouping → ExecutionPlan
```

**LLM Integration**: Uses OpenRouter for complexity classification and agent selection.

### 2. Workflow Orchestrator (`workflows/orchestrator.py`)

**Responsibility**: Execute research plans with proper dependency management.

**Key Classes**:
- `StepStatus`: PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
- `StepResult`: Result with timing, error handling
- `PlanExecution`: Full execution tracking
- `WorkflowOrchestrator`: Main orchestrator class

**Execution Algorithm**:
```
1. Topological Sort → Execution Waves (parallel groups)
2. For each wave:
   a. Execute steps in parallel (bounded by max_parallel)
   b. Collect results, update shared context
   c. Store in Research Memory
   d. Check for critical failures
3. Return PlanExecution with all results
```

**Features**:
- Configurable parallelism (default 4)
- Retry with exponential backoff (default 2 retries)
- Timeout per step (default 5 min)
- Progress callbacks
- Shared context propagation
- Memory integration

### 3. Research Memory (`memory/research_memory.py`)

**Responsibility**: Persistent storage and retrieval of research knowledge.

**Data Models**:
- `ResearchSession`: Complete research with all outputs
- `ResearchMemory`: Individual memory entries (14 types)
- `MemoryType`: SESSION, CONCLUSION, SOURCE, AGENT_OUTPUT, FOLLOW_UP, REPORT, INSIGHT

**Storage**: PostgreSQL with JSONB for flexible content
- Full session persistence
- Memory entries with tags, confidence, access tracking
- Company-scoped queries
- Semantic search ready (pgvector)

**Key Operations**:
- `store_session()` / `get_session()`
- `store_memory()` / `retrieve_memories()`
- `store_conclusion()` / `store_agent_output()`
- `get_relevant_context()` for new queries
- `get_recent_sessions()` for history

### 4. Watchlists & Monitoring (`watchlists/manager.py`)

**Responsibility**: Track entities and trigger automated research.

**Data Models**:
- `WatchlistType`: PERSONAL, PORTFOLIO, SECTOR, THEMATIC, COMPETITOR
- `WatchlistItem`: Company, ticker, target price, stop loss, notes
- `AlertRule`: Conditions, severity, channels, cooldown
- `AlertSeverity`: INFO, WARNING, CRITICAL

**Alert Conditions**:
- Price above/below threshold
- Price change percentage
- Volume spike
- RSI above/below
- News sentiment
- Article count
- Custom agent signals

**Evaluation**: Real-time or scheduled, checks cooldown, triggers multi-channel notifications.

### 5. Report Generator (`reports/generator.py`)

**Responsibility**: Generate professional reports from research data.

**Report Types** (8):
- Executive Summary
- Analyst Report
- Investment Thesis
- Company Snapshot
- Industry Analysis
- Daily Briefing
- Weekly Briefing
- Monthly Intelligence

**Output Formats**:
- Markdown (primary)
- HTML (styled)
- JSON (structured)

**Templating**: Jinja2 with base templates, extensible per report type.

**Section Builders**: 20+ formatting methods for different content types.

### 6. Notification Engine (`notifications/engine.py`)

**Responsibility**: Reliable multi-channel notification delivery.

**Channels**:
- Email (SMTP with TLS)
- Slack (webhook with blocks)
- Discord (webhook with embeds)
- Webhook (generic with headers)
- Console (dev)
- In-App (database)

**Reliability**:
- Retry with exponential backoff (1m, 5m, 15m)
- Max 3 retries by default
- Status tracking (pending/sent/failed)
- History persistence
- Callbacks for sent/failed

### 7. Approval Workflow (`approval/workflow.py`)

**Responsibility**: Human-in-the-loop gates for critical decisions.

**Actions**: APPROVE, REJECT, REQUEST_CHANGES, ESCALATE, DELEGATE, COMMENT

**Flow Types**:
- Sequential (default): One approver at a time
- Escalation: Add approver, continue chain
- Delegation: Replace current approver
- Expiration: Auto-expire after timeout

**State Machine**:
```
PENDING → (APPROVE) → PENDING (next) → ... → APPROVED
    ↓ (REJECT) → REJECTED
    ↓ (CHANGES) → CHANGES_REQUESTED
    ↓ (ESCALATE) → ESCALATED → PENDING (new approver)
    ↓ (EXPIRE) → EXPIRED
```

**Audit Trail**: Every action recorded with user, timestamp, comment.

### 8. Research API (`api/research_endpoints.py`)

**Endpoints**:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/research/start` | Start autonomous research |
| GET | `/research/{id}` | Get research status/results |
| GET | `/research/history` | Research history |
| GET | `/research/status` | System status |
| POST | `/watchlists` | Create watchlist |
| GET | `/watchlists` | List watchlists |
| GET | `/watchlists/{id}` | Get watchlist |
| POST | `/watchlists/{id}/companies` | Add company |
| DELETE | `/watchlists/{id}/companies/{company}` | Remove company |
| POST | `/watchlists/{id}/alerts` | Create alert rule |
| GET | `/approval/{id}` | Get approval request |
| POST | `/approval/{id}/action` | Process approval |
| GET | `/approval` | List approval requests |
| POST | `/reports/generate` | Generate report |
| GET | `/reports` | List reports |

## Data Flow

### Autonomous Research Flow
```
1. Client POST /research/start {company, query, auto_approve}
2. ResearchPlannerAgent.create_plan() → ExecutionPlan
3. Store ResearchSession in Memory
4. If auto_approve: Background execute
   Else: Create ApprovalRequest → Notify approvers
5. On approval: Orchestrator.execute_plan()
6. For each step: 
   - Get agent → Run with context → Store result in Memory
   - Update shared context → Progress callback
6. On completion: Update session status
7. Client polls /research/{id} for results
```

### Watchlist Alert Flow
```
1. Scheduled/Real-time trigger
2. WatchlistManager.evaluate_alerts(market_data, news, agent_outputs)
3. For each rule:
   - Check cooldown
   - Evaluate conditions against data
   - If triggered: Create Alert → Notify via channels
4. Update rule stats (trigger_count, last_triggered)
```

### Report Generation Flow
```
1. Client POST /reports/generate {type, company, session_id, format}
2. ReportGenerator.gather_data()
   - Get session from Memory
   - Retrieve relevant Memories (conclusions, insights, agent outputs)
   - Get recent sessions for context
3. Build sections based on report type
4. Render template (Markdown/HTML/JSON)
5. Save to output/reports/
6. Return Report with file_path
```

## Configuration

### Environment Variables (Phase 7)
```bash
# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=app-password
SMTP_USE_TLS=true
FROM_EMAIL=research@yourcompany.com

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Webhook
WEBHOOK_URL=https://your-endpoint.com/webhook
WEBHOOK_HEADERS={"Authorization": "Bearer token"}

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/fra/research.log
```

### Settings Additions (`config/settings.py`)
Added to `AppSettings`:
- `smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`, `smtp_use_tls`
- `from_email`
- `slack_webhook_url`
- `discord_webhook_url`
- `webhook_url`, `webhook_headers`
- `rate_limit_requests`, `rate_limit_window`
- `log_request_body`, `log_response_body`, `max_log_body_size`

## Database Schema Additions

### Tables Required (via Alembic)
```sql
-- Research Sessions
CREATE TABLE research_sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    company VARCHAR(128) NOT NULL,
    query TEXT NOT NULL,
    plan_id VARCHAR(64),
    status VARCHAR(32) DEFAULT 'pending',
    steps JSONB,
    results JSONB,
    conclusions JSONB,
    reports JSONB,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_seconds FLOAT,
    error TEXT,
    metadata JSONB
);

-- Research Memory
CREATE TABLE research_memory (
    memory_id VARCHAR(64) PRIMARY KEY,
    memory_type VARCHAR(32) NOT NULL,
    company VARCHAR(128) NOT NULL,
    content JSONB NOT NULL,
    source_agent VARCHAR(64),
    session_id VARCHAR(64),
    tags JSONB,
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    access_count INT DEFAULT 0,
    last_accessed TIMESTAMP,
    metadata JSONB
);
CREATE INDEX idx_memory_company ON research_memory(company);
CREATE INDEX idx_memory_type ON research_memory(memory_type);
CREATE INDEX idx_memory_session ON research_memory(session_id);

-- Watchlists
CREATE TABLE watchlists (
    watchlist_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    description TEXT,
    type VARCHAR(32) NOT NULL,
    owner_id VARCHAR(64) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

CREATE TABLE watchlist_items (
    item_id SERIAL PRIMARY KEY,
    watchlist_id VARCHAR(64) REFERENCES watchlists(watchlist_id),
    company VARCHAR(128) NOT NULL,
    ticker VARCHAR(32),
    notes TEXT,
    tags JSONB,
    target_price FLOAT,
    stop_loss FLOAT,
    position_size FLOAT,
    metadata JSONB
);

CREATE TABLE alert_rules (
    rule_id VARCHAR(64) PRIMARY KEY,
    watchlist_id VARCHAR(64) REFERENCES watchlists(watchlist_id),
    name VARCHAR(256) NOT NULL,
    description TEXT,
    company VARCHAR(128),
    conditions JSONB NOT NULL,
    severity VARCHAR(32) DEFAULT 'warning',
    channels JSONB,
    cooldown_minutes INT DEFAULT 60,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_triggered TIMESTAMP,
    trigger_count INT DEFAULT 0
);

-- Approval Workflows
CREATE TABLE approval_requests (
    request_id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(256) NOT NULL,
    description TEXT,
    request_type VARCHAR(64) NOT NULL,
    reference_id VARCHAR(64) NOT NULL,
    reference_type VARCHAR(64) NOT NULL,
    requester_id VARCHAR(64) NOT NULL,
    requester_name VARCHAR(128) NOT NULL,
    approvers JSONB NOT NULL,
    current_approver_index INT DEFAULT 0,
    status VARCHAR(32) DEFAULT 'pending',
    actions JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    expires_at TIMESTAMP,
    metadata JSONB
);

-- Notifications
CREATE TABLE notifications (
    notification_id VARCHAR(64) PRIMARY KEY,
    channel VARCHAR(32) NOT NULL,
    recipient VARCHAR(256) NOT NULL,
    subject VARCHAR(512) NOT NULL,
    body TEXT NOT NULL,
    priority VARCHAR(32) DEFAULT 'normal',
    metadata JSONB,
    status VARCHAR(32) DEFAULT 'pending',
    error TEXT,
    retry_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    sent_at TIMESTAMP
);
```

## Security Considerations

1. **Webhook Validation**: HMAC signature verification (not yet implemented)
2. **Rate Limiting**: Per-endpoint limits via middleware
3. **Authentication**: JWT/OAuth integration needed for production
4. **Authorization**: Role-based access to endpoints
5. **Data Encryption**: TLS for all external communications
5. **Audit Logging**: All approval actions and notifications logged

## Scalability Considerations

1. **Orchestrator**: Stateless, can run multiple instances
2. **Memory Store**: PostgreSQL with connection pooling
3. **Notifications**: Async with aiohttp, connection pooling
4. **Watchlists**: Redis caching for real-time evaluation
5. **Reports**: Generated files stored in object storage (S3/GCS)

## Monitoring Points

- Research execution duration per step
- Agent success/failure rates
- Approval request turnaround time
- Notification delivery success rate
- Alert trigger frequency
- Report generation latency
- Memory store query performance

## Future Enhancements (Phase 8+)

1. **WebSocket Support**: Real-time dashboard updates
2. **Neo4j Integration**: Native graph storage for Knowledge Graph
3. **Vector Search**: pgvector for semantic memory retrieval
4. **ML Pipeline**: Model training from research outcomes
5. **Multi-tenancy**: Organization-level isolation
6. **Custom Agents**: Plugin system for user-defined agents
7. **Advanced Scheduling**: Cron-based research triggers
8. **Collaboration**: Shared research sessions, comments