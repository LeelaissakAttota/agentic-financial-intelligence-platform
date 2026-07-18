# Copilot Architecture - AI Financial Research Copilot

## System Overview

The Phase 8 implementation transforms the Financial Research Platform into an **AI Financial Copilot** - an intelligent assistant that understands natural language, plans multi-step research workflows, selects tools automatically, coordinates multiple agents, and delivers explainable financial intelligence.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE LAYER                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │  Chat API   │  │ REST API    │  │  Streamlit  │  │   WebSocket │       │
│  │  (Streaming)│  │  (20+ eps)  │  │ Dashboard   │  │  (Future)   │       │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘       │
└─────────┼────────────────┼────────────────┼────────────────┼───────────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      COPILOT ORCHESTRATION LAYER                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    COPILOT AGENT (copilot/agent.py)                  │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐  │   │
│  │  │ Conversation │ │   Session    │ │   Context    │ │  Response  │  │   │
│  │  │   Manager    │ │   Manager    │ │   Builder    │ │  Synthesizer│  │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│         ┌──────────────────────────┼──────────────────────────┐           │
│         ▼                          ▼                          ▼           │
│  ┌───────────────┐         ┌───────────────┐         ┌───────────────┐  │
│  │ TASK PLANNER  │         │  TOOL SELECTOR│         │ DECISION ENGINE│  │
│  │ (planning/)   │         │   (tools/)    │         │  (decision/)   │  │
│  │               │         │               │         │                │  │
│  │ • Decomposition│        │ • 15 Tools    │         │ • 6-Step Reason│  │
│  │ • Dependencies│        │ • Confidence  │         │ • Hypotheses   │  │
│  │ • Parallelism │        │ • Validation  │         │ • Alternatives │  │
│  │ • Cost/Token  │        │ • Categories  │         │ • Risk Analysis│  │
│  └───────────────┘         └───────────────┘         └───────────────┘  │
│                                    │                                        │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          ▼                          ▼                          ▼
┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
│ COLLABORATION LAYER   │  │   MEMORY LAYER        │  │ EXPLAINABILITY        │
│ (collaboration/)      │  │ (memory/enhanced.py)  │  │ (explainability/)     │
│                       │  │                       │  │                       │
│ • Coordinator         │  │ • Long-Term (5 scopes)│  │ • Evidence Collector│
│ • Delegation Manager  │  │ • Conversation Memory │  │ • Explanation Gen   │
│ • Consensus Builder   │  │ • User Preferences    │  │ • 7 Explanation Types│
│ • Knowledge Graph     │  │ • Decision History    │  │ • Bear/Base/Bull    │
│ • Knowledge Aggregator│  │ • Tool Analytics      │  │ • Risk/Assumptions  │
│ • 5 Consensus Methods │  │ • Auto Pruning        │  │ • User-Facing Only  │
└───────────────────────┘  └───────────────────────┘  └───────────────────────┘
          │                          │                          │
          ▼                          ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LLM ORCHESTRATION LAYER (llm/orchestration.py)           │
├─────────────────────────────────────────────────────────────────────────────┤
│  • 9 Models (Claude, GPT, Gemini, DeepSeek, Mistral)                       │
│  • 8 Capabilities (reasoning, coding, vision, analysis, etc.)              │
│  • 4 Optimization Goals (Cost, Latency, Quality, Balanced)                 │
│  • Automatic Routing + Health Checks + Fallback Chains                     │
│  • Adaptive Learning from Execution History                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TOOL EXECUTION LAYER (tools/registry.py)                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  15 Tools across 14 Categories:                                             │
│  ┌────────────┐ ┌──────────┐ ┌────────┐ ┌───────────┐ ┌────────────────┐  │
│  │ Financial  │ │Sentiment │ │ Risk   │ │Competitive│ │ News           │  │
│  │ Documents  │ │ Analysis │ │Assessment│ │ Intel    │ │ Intelligence  │  │
│  └────────────┘ └──────────┘ └────────┘ └───────────┘ └────────────────┘  │
│  ┌────────────┐ ┌──────────┐ ┌────────┐ ┌───────────┐ ┌────────────────┐  │
│  │ Market     │ │Investment│ │Knowledge│ │ Portfolio │ │ Patterns     │  │
│  │ Data       │ │ Summary  │ │ Graph   │ │ Management│ │ Detection    │  │
│  └────────────┘ └──────────┘ └────────┘ └───────────┘ └────────────────┘  │
│  ┌────────────┐ ┌──────────┐ ┌────────┐ ┌───────────┐                    │
│  │ Alerts     │ │Analytics │ │Historical│ │ Memory    │                    │
│  │ Engine     │ │ Engine   │ │ Intelligence│ │ Access   │                    │
│  └────────────┘ └──────────┘ └───────────┘ └───────────┘                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 7 AGENT LAYER (14 Agents)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Financial Doc │ Sentiment │ Risk │ Competitive │ News │ Market Data      │
│ Investment Sum │ Knowledge │ Portfolio │ Patterns │ Alerts │ Analytics     │
│ Historical     │ Cross-Agent Memory │ Research Planner                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DATA & INFRASTRUCTURE LAYER                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  PostgreSQL (20+ tables) │ ChromaDB (Vector) │ Redis (Cache)              │
│  SEC EDGAR │ 6 News Providers │ Market Data APIs │ Financial APIs         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. User Request → Copilot Chat
```
User Message
    │
    ▼
Conversation Manager (session, history, context)
    │
    ▼
Intent Classification (LLM)
    │
    ▼
┌─────────────────────────────────────┐
│ Intent: research_request            │
│ Company: NVIDIA                     │
│ Question: "competitive position"    │
└─────────────────────────────────────┘
    │
    ▼
Task Planner → Execution Plan
    │
    ▼
Tool Selector → Tool Sequence
    │
    ▼
Decision Engine → Reasoning Chain
    │
    ▼
Tool Executor → Agent Results
    │
    ▼
Collaboration → Consensus/Conflict Resolution
    │
    ▼
Explainability → User-Facing Explanation
    │
    ▼
Response Synthesis → User
```

### 2. Research Execution Flow
```
Execution Plan (from Research Planner)
    │
    ▼
Workflow Orchestrator (Phase 7)
    │
    ├── Wave 1 (Parallel): Financial Docs + News + Market Data
    ├── Wave 2 (Parallel): Sentiment + Patterns
    ├── Wave 3 (Sequential): Risk + Competitive
    └── Wave 4: Investment Summary (depends on all)
         │
         ▼
    Research Memory Store (persist all results)
         │
         ▼
    Watchlist Evaluation → Alerts → Notifications
         │
         ▼
    Report Generation (8 types, 3 formats)
         │
         ▼
    Approval Workflow (if needed)
         │
         ▼
    Delivery (API response, Dashboard, Webhook)
```

---

## Key Components Detail

### Copilot Agent (`copilot/agent.py`)
**Purpose**: Main orchestration point for conversational financial research.

**Key Methods**:
- `create_session()` - Initialize conversation with context
- `process_message()` - Handle user input, determine intent, execute
- `execute_plan()` - Run research plan via workflow orchestrator
- `create_watchlist()` - Proactive monitoring setup
- `generate_report()` - Professional report generation

**Intent Types**:
- `research_request` - Full autonomous research
- `plan_request` - Create plan only
- `tool_request` - Single tool execution
- `report_request` - Generate report
- `watchlist_request` - Monitoring setup
- `memory_request` - Knowledge query
- `status_request` - Progress check
- `conversational` - General chat

### Task Planner (`planning/agent.py`)
**Purpose**: Decompose high-level goals into executable task plans.

**Planning Process**:
1. **Complexity Analysis** (LLM): simple/moderate/complex/expert
2. **Agent Selection** (LLM): Choose from 14 agent types
3. **Dependency Resolution**: Topological sort
4. **Parallel Group Identification**: Data collection, analysis_1, analysis_2
5. **Duration/Cost Estimation**: Per-step and total

**Output**: `ExecutionPlan` with steps, dependencies, parallel groups, estimates

### Tool Selector (`tools/registry.py`)
**Purpose**: Unified interface for all 15 financial research tools.

**Tool Categories** (14):
1. Financial Documents - SEC filings, earnings, reports
2. Sentiment - Multi-source sentiment analysis
3. Risk - VaR, stress testing, multi-category
4. Competitive - Peer comparison, positioning
5. News - 6 providers, events, entities
6. Market Data - Real-time, technicals, fundamentals
7. Investment Summary - Synthesis, thesis
8. Knowledge Graph - Relationships, centrality
9. Portfolio - Positions, risk, rebalancing
10. Patterns - 10 pattern types
11. Alerts - 30+ types, 5 channels
12. Analytics - Fama-French, Monte Carlo
13. Historical - Trends, evolution, peers
13. Memory - Cross-agent knowledge

**Selection**: LLM-based confidence scoring with category filtering

### Decision Engine (`decision/engine.py`)
**Purpose**: Multi-step reasoning with evidence aggregation.

**Reasoning Steps** (6 types):
1. **Evidence Gathering** - Execute planned tools, collect data
2. **Hypothesis Formation** - Generate testable hypotheses
3. **Evidence Evaluation** - Score hypotheses against evidence
4. **Alternative Consideration** - Bear/Base/Bull scenarios
5. **Risk Analysis** - Identify risk factors, likelihood, impact
6. **Synthesis** - Integrate findings into conclusion

**Internal vs External**:
- **Internal** (never exposed): Raw reasoning chain, tool calls, intermediate hypotheses
- **External** (user-facing): Evidence summary, alternatives, risk factors, assumptions, explanation

### Collaboration Coordinator (`collaboration/coordinator.py`)
**Purpose**: Enable agents to share findings and coordinate.

**Features**:
- **Message Routing**: 10 coordination signals (start, complete, need input, share finding, conflict, consensus)
- **Finding Sharing**: Agents publish findings with confidence, tags, validation
- **Conflict Detection**: Sentiment opposition, recommendation contradictions
- **Consensus Building**: 5 methods (majority, weighted, unanimous, threshold, borda)

### LLM Orchestration (`llm/orchestration.py`)
**Purpose**: Intelligent model routing.

**Models** (9):
| Model | Provider | Best For | Cost/1k | Latency |
|-------|----------|----------|---------|---------|
| Claude 3.5 Sonnet | Anthropic | Reasoning, Analysis | $0.018 | 2000ms |
| Claude 3 Opus | Anthropic | Expert Reasoning | $0.09 | 3000ms |
| GPT-4o | OpenAI | Reasoning, Vision | $0.02 | 1500ms |
| GPT-4 Turbo | OpenAI | Reasoning | $0.04 | 2000ms |
| Gemini Pro 1.5 | Google | Long Context | $0.00625 | 1800ms |
| Haiku | Anthropic | Fast/Cheap | $0.0015 | 500ms |
| GPT-4o-mini | OpenAI | Balanced | $0.00075 | 800ms |
| DeepSeek Chat | DeepSeek | Coding | $0.00042 | 1000ms |
| Mistral 7B | Mistral | Ultra Cheap | $0.00014 | 400ms |

**Routing Logic**:
1. Filter by required capabilities
2. Filter by cost/latency/context constraints
3. Score by optimization goal (cost/latency/quality/balanced)
4. Return primary + 3 fallbacks

### Explainability Engine (`explainability/engine.py`)
**Purpose**: Generate user-facing explanations without exposing internal reasoning.

**Evidence Types** (10): Documents, News, Market Data, Analyst Reports, Metrics, Indicators, Relationships, Patterns, Models, Expert Opinion

**Explanation Types** (7): Recommendation, Risk, Sentiment, Pattern, Consensus, Conflict, Trend

**Output Structure**:
- Summary (2-3 sentences)
- Detailed Explanation with citations
- Alternative Scenarios (Bear/Base/Bull with probabilities)
- Risk Factors (severity, likelihood, mitigation)
- Assumptions (confidence, sensitivity, impact if wrong)
- Evidence with citations

**Critical Rule**: Internal reasoning chain NEVER exposed to users.

### Enhanced Memory (`memory/enhanced.py`)
**Memory Types**:
| Type | Scope | Use Case |
|------|-------|----------|
| Long-Term | Global/User/Session/Company/Agent | Facts, preferences, patterns |
| Conversation | Session | Full history, summarization |
| User Preferences | User | Learned from interactions |
| Decision History | User/Session | Outcome tracking |
| Tool Analytics | User | Usage, cost, success rates |

**Pruning Strategy**:
- By importance (Critical → High → Medium → Low → Ephemeral)
- By TTL (configurable, default 365 days)
- By access frequency (< 2 accesses + old = prune)

### AI Dashboard (`dashboard/copilot.py`)
**Tabs**:
1. **Chat** - Streaming conversation interface
2. **Workflow** - Execution plan visualization with progress
3. **Decisions** - Confidence gauge, factor breakdown, alternatives
4. **Evidence** - Source documents with excerpts, risk assessment
5. **Tools** - Available tools with inline parameter forms

**Sidebar**: Session management, agent status cards, token/cost tracker

---

## API Layer

### Copilot Endpoints (`api/copilot_endpoints.py`)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/copilot/sessions` | POST | Create session |
| `/copilot/sessions/{id}` | GET | Get session |
| `/copilot/sessions/{id}/chat` | POST | Send message |
| `/copilot/sessions/{id}/plan` | POST | Create plan |
| `/copilot/sessions/{id}/execute` | POST | Execute plan |
| `/copilot/tools` | GET | List tools |
| `/copilot/tools/execute` | POST | Execute tool |
| `/copilot/reports/generate` | POST | Generate report |
| `/copilot/watchlists` | POST/GET | Watchlist CRUD |
| `/copilot/approval/{id}/action` | POST | Process approval |
| `/copilot/sessions/{id}/history` | GET | Conversation history |
| `/copilot/sessions/{id}/status` | GET | Session status |

---

## Database Schema (Phase 8 Additions)

```sql
-- Copilot Sessions
CREATE TABLE copilot_sessions (
    session_id UUID PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    company VARCHAR(128),
    mode VARCHAR(32) DEFAULT 'auto_execute',
    status VARCHAR(32) DEFAULT 'active',
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    completed_at TIMESTAMP,
    context JSONB,
    total_tokens INT DEFAULT 0,
    total_cost_usd FLOAT DEFAULT 0.0
);

-- Conversations
CREATE TABLE conversations (
    conversation_id UUID PRIMARY KEY,
    session_id UUID REFERENCES copilot_sessions,
    user_id VARCHAR(64),
    title VARCHAR(512),
    status VARCHAR(32) DEFAULT 'active',
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    summary TEXT,
    token_count INT DEFAULT 0
);

-- Conversation Messages
CREATE TABLE conversation_messages (
    message_id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations,
    role VARCHAR(32),
    content TEXT,
    metadata JSONB,
    tool_calls JSONB,
    tool_call_id UUID,
    timestamp TIMESTAMP
);

-- Decision History
CREATE TABLE decision_history (
    decision_id UUID PRIMARY KEY,
    user_id VARCHAR(64),
    session_id UUID,
    question TEXT,
    decision_type VARCHAR(64),
    conclusion TEXT,
    confidence FLOAT,
    outcome TEXT,
    outcome_accuracy FLOAT,
    feedback TEXT,
    created_at TIMESTAMP
);

-- Tool Executions
CREATE TABLE tool_executions (
    execution_id UUID PRIMARY KEY,
    session_id UUID REFERENCES copilot_sessions,
    tool_name VARCHAR(64),
    category VARCHAR(32),
    parameters JSONB,
    result JSONB,
    status VARCHAR(32),
    error TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds FLOAT,
    tokens_used INT,
    cost_usd FLOAT
);

-- Workflow Executions
CREATE TABLE workflow_executions (
    execution_id UUID PRIMARY KEY,
    session_id UUID REFERENCES copilot_sessions,
    plan_id UUID,
    company VARCHAR(128),
    goal TEXT,
    complexity VARCHAR(32),
    tasks JSONB,
    status VARCHAR(32),
    current_step VARCHAR(64),
    completed_steps INT,
    total_steps INT,
    step_results JSONB,
    error TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    total_duration_seconds FLOAT,
    total_cost_usd FLOAT,
    total_tokens INT
);
```

---

## Security Considerations

1. **No Internal Reasoning Exposure**: Explainability engine filters all outputs
2. **Input Validation**: All API inputs validated via Pydantic
3. **SQL Injection Prevention**: Parameterized queries, ORM usage
4. **Prompt Injection Detection**: Middleware layer (Phase 6)
5. **Rate Limiting**: Token bucket + sliding window (Phase 6)
6. **Circuit Breakers**: Prevent cascade failures (Phase 6)
7. **Secrets Management**: Environment variables only
8. **Audit Trail**: Full decision history with outcomes

---

## Performance Targets

| Metric | Target |
|--------|--------|
| Chat Response (p95) | < 3 seconds |
| Plan Generation | < 5 seconds |
| Tool Execution (avg) | < 30 seconds |
| Full Research (complex) | < 3 minutes |
| Memory Query | < 100ms |
| Dashboard Load | < 2 seconds |
| Concurrent Sessions | 100+ |

---

## Deployment Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Load Balancer │────▶│  API Instances  │────▶│  PostgreSQL     │
│   (nginx)       │     │  (FastAPI)      │     │  (Primary)      │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ ChromaDB │ │  Redis   │ │  Worker  │
              │ (Vector) │ │ (Cache)  │ │ (Async)  │
              └──────────┘ └──────────┘ └──────────┘
```

---

## Configuration

### Required Environment Variables (Phase 8)
```bash
# Already required from Phases 1-7
OPENROUTER_API_KEY=<key>
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=financial_research
CHROMADB_HOST=localhost
CHROMADB_PORT=8000
REDIS_HOST=localhost
REDIS_PORT=6379

# Phase 8 Optional
LLM_ROUTING_GOAL=balanced          # cost, latency, quality, balanced
MEMORY_PRUNING_ENABLED=true
MEMORY_MAX_AGE_DAYS=365
DECISION_TIMEOUT_SECONDS=60
MAX_REASONING_STEPS=10
```

---

## Testing Strategy

### Unit Tests (Per Module)
- Copilot: Conversation flow, intent classification, session management
- Planner: Plan creation, dependency resolution, parallel grouping
- Tools: Registry lookup, executor dispatch, parameter validation
- Collaboration: Message routing, finding sharing, conflict detection
- Decision: Reasoning steps, hypothesis evaluation, synthesis
- Memory: Storage, retrieval, pruning, preference learning
- LLM Router: Model selection, fallback chains, health checks
- Explainability: Evidence extraction, explanation generation

### Integration Tests
- Full chat → plan → execute → explain flow
- Multi-agent consensus on conflicting findings
- Memory persistence across sessions
- Tool execution with fallback
- WebSocket streaming (future)

### Performance Tests
- Concurrent session handling
- Tool execution latency under load
- Memory pruning at scale
- LLM routing decision latency

---

## Monitoring & Observability

### Metrics (Prometheus)
- `copilot_sessions_active` - Active sessions
- `copilot_chat_requests_total` - Chat requests
- `copilot_plan_generation_duration_seconds` - Plan latency
- `copilot_tool_execution_duration_seconds` - Tool latency
- `copilot_decision_reasoning_steps` - Reasoning depth
- `copilot_memory_size_bytes` - Memory usage
- `copilot_llm_routing_decisions_total` - Routing distribution
- `copilot_explanation_generation_duration_seconds` - Explainability latency

### Health Checks
- `/copilot/health` - Overall status
- `/copilot/health/models` - Model availability
- `/copilot/health/memory` - Memory system status
- `/copilot/health/tools` - Tool executor status

---

## Future Extensibility

### Phase 9+ Hooks
1. **Custom Agent Plugin System** - `tools/registry.py` designed for dynamic loading
2. **Multi-Tenant Architecture** - Memory scopes support tenant isolation
3. **Advanced Reasoning** - Reasoning engine supports plugin step types
4. **Custom Explanation Templates** - Prompt system supports user templates
5. **WebSocket Real-Time** - Dashboard designed for streaming updates
6. **Vector Search** - Memory search ready for pgvector integration
7. **Custom Models** - Router supports dynamic model registration

---

## Summary

The Phase 8 Copilot Architecture delivers a **production-ready AI Financial Research Assistant** with:

- **Natural Language Interface** - Chat-based research requests
- **Autonomous Planning** - LLM-driven task decomposition
- **Intelligent Tool Selection** - 15 tools, confidence-based routing
- **Multi-Agent Coordination** - Consensus, conflict resolution, knowledge sharing
- **Explainable Decisions** - Evidence, alternatives, risks, assumptions
- **Persistent Memory** - Long-term, conversational, preference learning
- **Multi-Model LLM Orchestration** - 9 models, automatic routing
- **Real-Time Dashboard** - Streaming chat, workflow viz, evidence panel
- **Full API** - 20+ endpoints for programmatic access
- **Complete Observability** - Metrics, health, audit trails

All built with **async-first design**, **type safety**, **zero breaking changes**, and **Phase 1-7 compatibility**.