# Architecture Summary
## Financial Research Agent v2.0.0

**Version**: v2.0.0  
**Status**: Stable Release - Maintenance Mode  
**Date**: 2026-07-18

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        FINANCIAL RESEARCH AGENT v2.0.0                               │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                           PRESENTATION LAYER                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │   │
│  │  │   REST API  │  │  WebSocket  │  │  Streamlit  │  │   CLI / SDK     │   │   │
│  │  │  (FastAPI)  │  │  Streaming  │  │  Dashboard  │  │                 │   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                                │
├────────────────────────────────────┼───────────────────────────────────────────────┤
│                                    ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                        APPLICATION LAYER (Phase 1-8)                         │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │   │
│  │  │                     AI COPILOT ORCHESTRATION                         │   │   │
│  │  │  Chat │ Session │ Intent │ Context │ Planning │ Execution │ Tools │   │   │
│  │  └─────────────────────────────────────────────────────────────────────┘   │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │   │
│  │  │                    14 SPECIALIZED AGENTS                             │   │   │
│  │  │ Financial│Sentiment│Risk│Competitive│News│Market│Investment│KG    │   │   │
│  │  │ Portfolio│Patterns│Alerts│Analytics│Historical│Memory│Planner     │   │   │
│  │  └─────────────────────────────────────────────────────────────────────┘   │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │   │
│  │  │                  SUPPORTING INFRASTRUCTURE                           │   │   │
│  │  │  Tool Registry (15) │ Collaboration │ Decision Engine │ Explainability│   │   │
│  │  │  Enhanced Memory (5 scopes) │ Workflow Orchestrator │ Approvals    │   │   │
│  │  └─────────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                                │
├────────────────────────────────────┼───────────────────────────────────────────────┤
│                                    ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                     INTELLIGENCE LAYER (Phase 9 - NEW)                       │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │   │
│  │  │ Enterprise  │ │ Real-Time   │ │ Semantic    │ │ Autonomous          │   │   │
│  │  │ Neo4j KG    │ │ Intelligence│ │ Intelligence│ │ Research Engine     │   │   │
│  │  │             │ │             │ │             │ │                     │   │   │
│  │  │ • 14 nodes  │ │ • WebSocket │ │ • 8 embeds  │ │ • Thesis gen        │   │   │
│  │  │ • 28 edges  │ │ • Market WS │ │ • 6 backends│ │ • Agent debate      │   │   │
│  │  │ • Algorithms│ │ • News WS   │ │ • Memory    │ │ • Confidence        │   │   │
│  │  │ • PG↔Neo4j  │ │ • Event Bus │ │ • Sharing   │ │ • Contradiction     │   │   │
│  │  │ • Sync      │ │ • Pub/Sub   │ │ • Evidence  │ │ • Synthesis         │   │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────┘   │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │   │
│  │  │ Advanced    │ │ Predictive  │ │ Dashboard   │ │ Production          │   │   │
│  │  │ Portfolio   │ │ Intelligence│ │ v2          │ │ Event System        │   │   │
│  │  │             │ │             │ │             │ │                     │   │   │
│  │  │ • MC (6)    │ │ • Forecast  │ │ • 8 comps   │ │ • Priority queue    │   │   │
│  │  │ • Copulas(6)│ │ • Early warn│ │ • 12-col    │ │ • Workers           │   │   │
│  │  │ • Stress(9) │ │ • Events(14)│ │ • WS engine │ │ • Scheduler(6)      │   │   │
│  │  │ • Scenarios │ │ • Risk pred │ │ • Workspace │ │ • Persistence       │   │   │
│  │  │ • Decomp    │ │ • Regimes(7)│ │ • Graph Exp │ │ • Retry+CB          │   │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                                │
├────────────────────────────────────┼───────────────────────────────────────────────┤
│                                    ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                            DATA LAYER                                        │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │   │
│  │  │ PostgreSQL  │ │ Neo4j       │ │ ChromaDB    │ │ Redis               │   │   │
│  │  │ (Primary)   │ │ (Graph)     │ │ (Vectors)   │ │ (Cache/Streams)     │   │   │
│  │  │             │ │             │ │             │ │                     │   │   │
│  │  │ • 31 tables │ │ • 14 nodes  │ │ • 8 collections│ • Pub/Sub          │   │   │
│  │  │ • ACID      │ │ • 28 edges  │ │ • HNSW idx  │ • Rate limiting     │   │   │
│  │  │ • Replicas  │ │ • Algorithms│ │ • Multi-model│ • Sessions          │   │   │
│  │  │ • Migrations│ │ • Causal Cl │ │ • 384-3072d │ • Circuit breaker   │   │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Major Modules

### Phase 1-8 (Core Platform)

| Module | Responsibility | Key Components |
|--------|----------------|----------------|
| **Agents (14)** | Domain-specific analysis | Financial Doc, Sentiment, Risk, Competitive, News, Market, Investment, KG, Portfolio, Patterns, Alerts, Analytics, Historical, Cross-Agent Memory |
| **AI Copilot** | Natural language orchestration | Chat, Session, Intent, Context, Planning, Execution |
| **Tool Registry** | 15 tools across 14 categories | Auto-selection, OpenAI schemas, tracking |
| **Collaboration** | Agent coordination | Coordinator, Delegation, Consensus, KG Client |
| **Decision Engine** | 6-step reasoning | Evidence, Hypothesis, Alternatives, Risk, Synthesis |
| **Explainability** | Evidence-based explanations | 10 evidence types, 7 explanation types |
| **Enhanced Memory** | Cross-agent memory | 5 scopes, 5 importance, decision history |
| **Workflows** | Research orchestration | Planner, Orchestrator, Memory, Watchlists, Reports, Approvals, Notifications |

### Phase 9 (Intelligence Layer)

| Module | Responsibility | Key Components |
|--------|----------------|----------------|
| **Enterprise Neo4j KG** | Persistent knowledge graph | Client, Models (14/28), Repository, Schema, Sync |
| **Real-Time Intelligence** | Live data streaming | WebSocket Server, Market Stream, News Stream, Event Bus, Pub/Sub, Processor |
| **Semantic Intelligence** | Vector search & memory | Embeddings (8), Vector Store (6), Memory Retrieval, Knowledge Sharing, Evidence Lookup, Context Ranker |
| **Autonomous Research** | AI-driven research | Thesis Generator, Evidence Ranker, Agent Debate, Confidence Scorer, Contradiction Detector, Research Synthesizer |
| **Advanced Portfolio** | Institutional analytics | Monte Carlo (6), Copulas (6), Stress (9), Scenarios (4), Risk Decomposition |
| **Predictive Intelligence** | Forecasting & warning | Forecast Engine (10), Early Warning (10), Event Prediction (14), Risk Prediction (10), Regime Detection (7) |
| **Dashboard v2** | Real-time UI | Components (8), Layout (12-col), WebSocket, Workspace, Graph Explorer, Workflow Viz |
| **Production Events** | Reliable event processing | Priority Queue, Workers, Scheduler (6), Persistence, Retry+CB, Event Bus |

---

## Agents (14 Specialized)

| Agent | Domain | Key Capabilities |
|-------|--------|------------------|
| Financial Report Agent | SEC filings, earnings, presentations | 16 form types, section-aware chunking, RAG |
| Market Data Agent | Quotes, technicals, fundamentals | Real-time, RSI/MACD/BB, financial metrics |
| News Agent | Multi-source aggregation | 6 providers, 7-layer NLP, 28 entities |
| Sentiment Agent | Multi-source sentiment | News + social, divergence detection |
| Risk Agent | Multi-category risk | 10 risk types, VaR/CVaR, Monte Carlo |
| Competitive Agent | Peer analysis | Comparison matrix, positioning |
| Investment Summary Agent | Thesis synthesis | Consensus, confidence, alternatives |
| Knowledge Graph Agent | Graph queries | Traversal, paths, centrality, communities |
| Portfolio Agent | Position/order management | 5 rebalancing, risk metrics, MC |
| Patterns Agent | Technical patterns | 10 types, backtesting, performance |
| Alerts Agent | Monitoring engine | 30+ types, 5 channels, dedup |
| Analytics Agent | Factor models, attribution | Fama-French 3/5, Brinson, MC |
| Historical Intelligence | Time-series trends | Evolution, peer comparison, benchmarks |
| Cross-Agent Memory Agent | Shared knowledge | 9 types, 5 scopes, supersession |
| Research Planner Agent | Autonomous planning | 4 complexity levels, 14 agents, topological sort |

---

## Database Schema

### PostgreSQL (31 Tables)

| Category | Tables |
|----------|--------|
| Core Entities | companies, people, products, sectors, industries |
| Financial Data | financial_metrics, financial_statements, filings |
| News & Intelligence | news_articles, news_summaries, company_intelligence, events |
| Research | research_sessions, research_steps, research_results, agent_outputs |
| Portfolio | portfolios, positions, orders, transactions, snapshots |
| Knowledge Graph | graph_nodes, graph_edges, graph_communities |
| Patterns | patterns, pattern_performance, pattern_backtests |
| Alerts | alert_rules, alerts, alert_channels, alert_history |
| Analytics | factor_exposures, monte_carlo_results, stress_test_results |
| Copilot | copilot_sessions, conversations, conversation_messages, decision_history, tool_executions, workflow_executions |
| Approvals | approval_requests, approval_actions, approval_chains |
| Memory | cross_agent_memories, memory_links, memory_access_log |
| Watchlists | watchlists, watchlist_companies, watchlist_alerts |

### ChromaDB (8 Collections)

| Collection | Purpose | Dimensions |
|------------|---------|------------|
| financial_documents | SEC filings, reports | 1024 |
| news_articles | News embeddings | 1024 |
| earnings_calls | Transcript embeddings | 1024 |
| research_memory | Cross-agent memory | 1024 |
| company_knowledge | Entity embeddings | 1024 |
| pattern_embeddings | Pattern signatures | 384 |
| thesis_embeddings | Research theses | 1024 |
| evidence_embeddings | Evidence chunks | 1024 |

### Neo4j (Graph)

| Element | Count | Details |
|---------|-------|---------|
| Node Types | 14 | Company, Person, Product, Sector, Industry, MarketIndex, FinancialMetric, Event, NewsArticle, EarningsCall, SECFiling, AnalystReport, RegulatoryBody, Geography |
| Relationship Types | 28 | COMPETES_WITH, PARTNERS_WITH, SUPPLIES_TO, ACQUIRED, MERGED_WITH, SUBSIDIARY_OF, WORKS_FOR, BOARD_MEMBER_OF, ADVISES, FOUNDED, PRODUCES, COMPETES_WITH_PRODUCT, OPERATES_IN, PART_OF, HAS_METRIC, REPORTED_IN, MENTIONED_IN, CITES, REFERENCES, ANALYZES, TRIGGERED, IMPACTED, RELATED_TO |

---

## Dashboard (v2)

### Components (8 Types)

| Component | Variants | Features |
|-----------|----------|----------|
| MetricCard | KPI, Delta, Trend | Real-time, sparklines, thresholds |
| Chart | Line, Bar, Candle, Heatmap | Multi-series, zoom, export |
| Table | Sortable, Paginated | Filters, virtual scroll, export |
| AlertPanel | Severity, Filters | Real-time, acknowledgment |
| AgentStatus | Pool, Individual | Logs, metrics, health |
| WorkflowViz | DAG, Progress | Real-time, drill-down |
| GraphExplorer | 5 Layouts | Paths, communities, centrality |
| RealtimeFeed | Priority, Filters | WebSocket, history, search |

### Layout System

- 12-column responsive grid
- 5 breakpoints (xs, sm, md, lg, xl)
- Drag/drop with collision detection
- Auto-arrange (pack, grid, flow)
- Persistent layouts (localStorage/DB)

---

## Workflow & Research Pipeline

### Autonomous Research Flow

```
User Query
    │
    ▼
Intent Classification ─────► Company Extraction
    │
    ▼
Complexity Analysis (SIMPLE/MODERATE/COMPLEX/COMPREHENSIVE)
    │
    ▼
Dynamic Agent Selection (from 14 types)
    │
    ▼
Dependency Graph Construction
    │
    ▼
Topological Sort → Parallel Waves
    │
    ├── Wave 1: Data Collection (News, Market, Filings)
    ├── Wave 2: Analysis 1 (Sentiment, Risk, Patterns)
    ├── Wave 3: Analysis 2 (Competitive, Analytics, KG)
    └── Wave 4: Synthesis (Investment Summary)
    │
    ▼
Agent Debate (Proposer, Skeptic, Validator, Mediator, Moderator)
    │
    ▼
Confidence Scoring (8 dimensions + CI)
    │
    ▼
Contradiction Detection (6 types)
    │
    ▼
Research Synthesis (6 report types)
    │
    ▼
Report Generation (Markdown/HTML/JSON)
```

---

## Data Flow Patterns

### 1. Research Request Flow
```
User Query → Copilot → Planner → Orchestrator → 14 Agents → Memory → Debate → Synthesis → Report
```

### 2. Real-Time Data Flow
```
External APIs → Market/News Stream → Event Bus → WebSocket → Dashboard → User
```

### 3. Knowledge Graph Sync
```
PostgreSQL (Source) → Sync Manager → Neo4j (Graph) → Algorithms → Semantic Intelligence → Context Ranker
```

### 4. Portfolio Risk Flow
```
Portfolio → Factor Exposures → Monte Carlo → Stress Tests → Risk Decomposition → Dashboard
```

### 5. Predictive Intelligence Flow
```
Market Data → Forecast Engine → Predictions
    ├── Early Warning → Alerts
    ├── Event Prediction → Signals
    ├── Risk Prediction → Portfolio Alerts
    └── Regime Detection → Strategy Adjustment
```

---

## Integration Points

| Layer | Interfaces |
|-------|------------|
| REST API | 84 endpoints (v1 frozen) |
| WebSocket | 8 channels (v1 frozen) |
| Graph Query | Cypher + Algorithms (v1 frozen) |
| Memory API | Read/Write/Query (v1 frozen) |
| Database | PostgreSQL (additive only), Neo4j, ChromaDB, Redis |

---

**Architecture Status**: ✅ **FROZEN** - No further changes permitted without architecture review board approval

**Document Version**: 1.0  
**Date**: 2026-07-18