# Architecture Update
## Phase 9: Autonomous Financial Intelligence Platform v2.0

**Date**: 2026-07-18  
**Version**: v2.0.0-development

---

## Overview

This document describes the architectural changes introduced in Phase 9 to evolve the platform from a multi-agent research system into a comprehensive **Autonomous Financial Intelligence Platform v2.0** with enterprise-grade capabilities across distributed intelligence, real-time processing, and autonomous decision-making.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AUTONOMOUS FINANCIAL INTELLIGENCE PLATFORM v2.0       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │   PRESENTATION  │  │   ORCHESTRATION │  │   INTELLIGENCE  │             │
│  │     LAYER       │  │     LAYER       │  │     LAYER       │             │
│  │                 │  │                 │  │                 │             │
│  │ • Dashboard v2  │  │ • Workflow Viz  │  │ • Autonomous    │             │
│  │ • Graph Explorer│  │ • Research Ws   │  │   Research      │             │
│  │ • Realtime Feed │  │ • Scheduler     │  │ • Portfolio     │             │
│  │ • Workspace     │  │ • Event Bus     │  │   Intelligence  │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
│           │                    │                    │                       │
├───────────┼────────────────────┼────────────────────┼───────────────────────┤
│           ▼                    ▼                    ▼                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      CORE SERVICES LAYER                              │  │
│  │                                                                       │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │  │
│  │  │   Event     │ │  Knowledge  │ │  Semantic   │ │ Predictive  │    │  │
│  │  │   System    │ │   Graph     │ │ Intelligence│ │ Intelligence│    │  │
│  │  │             │ │             │ │             │ │             │    │  │
│  │  │ • Queue     │ │ • Neo4j     │ │ • Embeddings│ │ • Forecast  │    │  │
│  │  │ • Worker    │ │ • Sync      │ │ • Vector    │ │ • Early     │    │  │
│  │  │ • Scheduler │ │ • Algorithms│ │ • Memory    │ │   Warning   │    │  │
│  │  │ • Persistence│ • Schema    │ │ • Sharing   │ │ • Events    │    │  │
│  │  │ • Retry     │ │ • Communities│ • Evidence  │ │ • Risk      │    │  │
│  │  │ • Scheduler │ │ • Paths     │ │ • Ranking   │ │ • Regime    │    │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
├────────────────────────────────────┼───────────────────────────────────────┤
│                                    ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        DATA LAYER                                      │  │
│  │                                                                       │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │  │
│  │  │ PostgreSQL  │ │   Neo4j     │ │  ChromaDB   │ │   Redis     │    │  │
│  │  │  (Primary)  │ │  (Graph)    │ │  (Vectors)  │ │  (Cache/    │    │  │
│  │  │             │ │             │ │             │ │   Streams)  │    │  │
│  │  │ • Relational│ │ • Nodes: 14 │ │ • 8 models  │ │             │    │  │
│  │  │ • ACID      │ │ • Edges: 28 │ │ • 6 backends│ │ • Pub/Sub   │    │  │
│  │  │ • Migrations│ │ • Algorithms│ │ • HNSW      │ │ • Rate Limit│    │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## New Module Architectures

### 1. Enterprise Neo4j Knowledge Graph (`enterprise_neo4j/`)

**Purpose**: Persistent, queryable knowledge graph with bidirectional PostgreSQL sync

**Components**:
```
enterprise_neo4j/
├── client.py          # Async Neo4j driver, connection pooling, health checks
├── models.py          # 14 Node types, 28 Edge types, Paths, Communities
├── repository.py      # High-level CRUD, Path finding, Centrality, Similarity
├── schema.py          # Constraints, Indexes, Validation, DDL generation
└── sync.py            # Bidirectional PG ↔ Neo4j sync (incremental/full)
```

**Data Model**:
- **14 Node Types**: Company, Person, Product, Sector, Industry, MarketIndex, FinancialMetric, Event, NewsArticle, EarningsCall, SECFiling, AnalystReport, RegulatoryBody, Geography
- **28 Edge Types**: COMPETES_WITH, PARTNERS_WITH, SUPPLIES_TO, ACQUIRED, MERGED_WITH, SUBSIDIARY_OF, WORKS_FOR, BOARD_MEMBER_OF, ADVISES, FOUNDED, PRODUCES, COMPETES_WITH_PRODUCT, OPERATES_IN, PART_OF, HAS_METRIC, REPORTED_IN, MENTIONED_IN, CITES, REFERENCES, ANALYZES, TRIGGERED, IMPACTED, RELATED_TO

**Sync Architecture**:
```
PostgreSQL (Source of Truth)          Neo4j (Graph Layer)
┌─────────────────────┐               ┌──────────────────────┐
│ Tables              │   Sync Mgr    │ Nodes & Relationships │
│ • companies         │◄─────────────►│ Company nodes         │
│ • people            │   Incremental │ Person nodes          │
│ • news_articles     │   or Full     │ NewsArticle nodes     │
│ • financial_metrics │               │ Metric nodes          │
│ • relationships     │   Conflict    │ Edges with properties │
└─────────────────────┘   Resolution  └──────────────────────┘
```

**Graph Algorithms**:
- PageRank centrality
- Louvain community detection
- Shortest path (Dijkstra)
- Betweenness centrality
- Jaccard/Cosine similarity

---

### 2. Real-Time Intelligence Layer (`realtime_intelligence/`)

**Purpose**: WebSocket-based real-time data streaming with pub/sub

**Components**:
```
realtime_intelligence/
├── server.py          # WebSocket server with subscriptions, heartbeats
├── market_stream.py   # Quotes, trades, depth with fan-out
├── news_stream.py     # News with dedup, sentiment, entities
├── event_bus.py       # Pub/Sub with priorities, scheduled events
├── pubsub.py          # Topic-based pub/sub with filters
└── processor.py       # Background processor with retries, DLQ
```

**WebSocket Protocol**:
```json
// Client → Server
{"type": "subscribe", "topics": ["market:quote:AAPL", "news:tech"], "filters": {"min_confidence": 0.7}}

// Server → Client
{"type": "market:quote", "topic": "market:quote:AAPL", "data": {"price": 150.25, "change": 0.02}, "timestamp": "2026-07-18T14:30:00Z"}
```

**Market Data Types**:
- Quotes (price, bid/ask, volume, change)
- Trades (price, size, side, conditions)
- Depth (bids/asks with sizes)
- OHLCV candles

**News Processing**:
- Deduplication (title + source + time window)
- Sentiment scoring (-1 to 1)
- Entity extraction (companies, people, products)
- Category classification (earnings, M&A, regulatory, etc.)

---

### 3. Cross-Agent Semantic Intelligence (`semantic_intelligence/`)

**Purpose**: Vector-based semantic search, memory, and cross-agent knowledge sharing

**Components**:
```
semantic_intelligence/
├── embeddings.py          # 8 models (BGE-M3, E5, OpenAI, MiniLM, MPNet)
├── vector_store.py        # 6 backends (ChromaDB, FAISS, Pinecone, Weaviate, Qdrant, Memory)
├── memory_retrieval.py    # 5 scopes, importance, TTL, access tracking
├── knowledge_sharing.py   # Cross-agent sharing, synthesis, validation
├── evidence_lookup.py     # Semantic retrieval, ranking, bundles
└── context_ranker.py      # 5 strategies, agent-specific preferences
```

**Embedding Models**:
| Model | Dimensions | Use Case |
|-------|------------|----------|
| BGE-M3 | 1024 | General purpose, multilingual |
| E5-Large | 1024 | Retrieval, asymmetric |
| OpenAI Ada-002 | 1536 | General, OpenAI ecosystem |
| E5-Base | 768 | Fast retrieval |
| MiniLM-L6 | 384 | Fast, resource-constrained |
| MiniLM-L12 | 384 | Balanced speed/quality |
| MPNet | 768 | Semantic similarity |
| OpenAI 3-Large | 3072 | High-quality retrieval |

**Vector Backends**:
| Backend | Type | Best For |
|---------|------|----------|
| ChromaDB | Embedded/Server | Development, small-medium |
| FAISS | In-memory | High performance, static |
| Pinecone | Managed cloud | Production, scale |
| Weaviate | Hybrid | Graph + Vector |
| Qdrant | Rust-based | High performance, filtering |
| In-Memory | Python | Testing, tiny datasets |

**Memory Scopes**:
1. **Global** - System-wide facts, never pruned
2. **User** - Per-user preferences, patterns
3. **Session** - Active research context, TTL 24h
4. **Company** - Entity-specific knowledge
5. **Agent** - Agent-learned patterns

---

### 4. Autonomous Research Engine (`autonomous_research/`)

**Purpose**: End-to-end autonomous research with thesis generation, debate, and synthesis

**Components**:
```
autonomous_research/
├── thesis_generator.py    # 6 thesis types, evidence chains
├── evidence_ranker.py     # 6 objectives, thematic bundles
├── agent_debate.py        # 5 roles, 4 phases, consensus
├── confidence_scorer.py   # 8 dimensions, CI, recommendation
├── contradiction_detector.py # 6 types, severity, resolution
└── research_synthesizer.py # 6 report types, templates
```

**Thesis Types**:
| Type | Description | Typical Horizon |
|------|-------------|-----------------|
| Long | Bullish, growth/compounding | 12-18 months |
| Short | Bearish, structural issues | 6-12 months |
| Value | Margin of safety, catalysts | 12-24 months |
| Growth | TAM expansion, moats | 18-36 months |
| Turnaround | Restructuring, new mgmt | 12-18 months |
| Event-Driven | Catalyst-specific | 1-6 months |

**Debate Framework**:
- **Roles**: Proposer, Skeptic, Validator, Mediator, Moderator
- **Phases**: Opening → Rebuttal → Evidence Review → Synthesis → Voting
- **Consensus**: 2/3 majority with evidence backing

**Confidence Dimensions**:
1. Evidence Quality (0-1)
2. Evidence Quantity (0-1)
3. Source Credibility (0-1)
4. Methodology Rigor (0-1)
5. Consensus Level (0-1)
6. Recency (0-1)
7. Completeness (0-1)
8. Consistency (0-1)

---

### 5. Advanced Portfolio Intelligence (`advanced_portfolio/`)

**Purpose**: Institutional-grade portfolio analytics with Monte Carlo, copulas, stress testing

**Components**:
```
advanced_portfolio/
├── monte_carlo.py      # 6 distributions, antithetic, control variates
├── copula.py           # 6 families: Gaussian, t, Clayton, Gumbel, Frank, Joe
├── stress_test.py      # 9 scenarios: GFC, COVID, CCAR, Basel, Stagflation, etc.
├── scenario.py         # 4 methods: MC, Historical, Factor, Regime-Switching
└── risk_decomposition.py # Factor model, marginal/component VaR, diversification
```

**Distributions**:
| Distribution | Parameters | Use Case |
|--------------|------------|----------|
| Normal | μ, σ | Baseline |
| Student-t | μ, σ, ν | Fat tails |
| Skewed-t | μ, σ, ν, λ | Asymmetric tails |
| Historical | Empirical | Non-parametric |
| GARCH | ω, α, β | Volatility clustering |
| Mixture | π, μ₁, μ₂, σ₁, σ₂ | Regime-switching |

**Copula Families**:
| Copula | Tail Dependence | Use Case |
|--------|----------------|----------|
| Gaussian | None | Baseline |
| Student-t | Symmetric | Financial crises |
| Clayton | Lower | Crash dependence |
| Gumbel | Upper | Boom dependence |
| Frank | None | General |
| Joe | Upper | Extreme upper |

**Stress Scenarios**:
1. GFC 2008 - Equity -50%, Credit +500bps, Vol +60pts
2. COVID 2020 - Equity -35%, Rates -150bps, Vol +45pts
3. CCAR 2023 Severe - Equity -55%, GDP -4%, Unemployment 10%
4. Basel IRRBB - Parallel ±200bp, Steepener/Flattener
5. 1970s Stagflation - Inflation 10%, Rates +400bp, Real returns negative
6. Tech Bubble 2000s - Tech -78%, P/E compression 50%
7. Modern Tech Bubble - FAANG -40%, P/E compression 50%
7. Geopolitical Crisis - Oil 2x, Equity -25%, Spreads +300bp

---

### 6. Predictive Intelligence (`predictive_intelligence/`)

**Purpose**: Forecasting, early warning, event prediction, risk prediction, regime detection

**Components**:
```
predictive_intelligence/
├── forecast_engine.py     # 10 models, ensemble, CV, backtesting
├── early_warning.py       # 10 signals, cooldowns, severity
├── event_prediction.py    # 14 categories, signal detection
├── risk_prediction.py     # 10 risks, portfolio analysis
└── regime_detection.py    # 7 regimes, 3 methods ensemble
```

**Forecast Models**:
| Model | Type | Horizon | Strengths |
|-------|------|---------|-----------|
| ARIMA | Statistical | Short | Interpretable |
| SARIMA | Statistical | Short-Med | Seasonality |
| Prophet | ML | Med-Long | Holidays, trends |
| LSTM | Deep Learning | Med-Long | Non-linear |
| Transformer | Deep Learning | Long | Attention |
| GRU | Deep Learning | Med | Efficient |
| XGBoost | ML | Short-Med | Features |
| LightGBM | ML | Short-Med | Fast, accurate |
| Random Forest | ML | Short | Robust |
| Ensemble | Hybrid | All | Best overall |

**Early Warning Signals**:
1. Market Crash (>10% DD)
2. Volatility Spike (>1.5x)
3. Regime Change (>60% prob)
4. Correlation Breakdown (>0.3 drop)
5. Momentum Reversal (>50% change)
6. Liquidity Crisis (>1.5x spread)
7. Credit Deterioration (>50bps widening)
8. Valuation Extreme (>2σ)
9. Sentiment Shift (>30%)
10. Flow Imbalance

**Regime Types**:
1. **Bull** - Trend up, low vol, positive momentum
2. **Bear** - Trend down, high vol, negative momentum
3. **Sideways** - Range-bound, low vol, flat momentum
4. **High Volatility** - High vol, high correlation, no trend
5. **Crisis** - Extreme vol, correlation →1, negative sentiment
6. **Recovery** - Vol declining, momentum up, breadth improving
7. **Transition** - Conflicting signals, rising vol

---

### 7. Enterprise Dashboard v2 (`dashboard_v2/`)

**Purpose**: Real-time, interactive dashboard with live monitoring and exploration

**Components**:
```
dashboard_v2/
├── components.py      # 8 types: MetricCard, Chart, Table, AlertPanel, AgentStatus, WorkflowViz, GraphExplorer, RealtimeFeed
├── layout.py          # 12-col responsive grid, drag/drop, auto-arrange
├── realtime.py        # WebSocket engine, subscriptions, priorities
├── workspace.py       # 5 modes, 8 panels, queries, notes
├── graph_explorer.py  # 14 nodes, 28 edges, 5 layouts, communities
├── workspace.py       # Research workspace
├── graph_explorer.py  # Graph explorer
└── workflow_viz.py    # Live DAG, progress, timeline
```

**Layout System**:
- 12-column responsive grid
- 5 breakpoints (xs, sm, md, lg, xl)
- Drag/drop with collision detection
- Auto-arrange (pack, grid)
- Persistent layouts (localStorage/DB)

**Component Types**:
| Component | Types | Features |
|-----------|-------|----------|
| MetricCard | KPI, delta, trend | Real-time, sparklines |
| Chart | Line, bar, candle, heatmap | Multi-series, zoom |
| Table | Sortable, paginated | Filters, export |
| AlertPanel | Severity, filters | Real-time, acknowledgment |
| AgentStatus | Pool, individual | Logs, metrics |
| WorkflowViz | DAG, progress | Real-time, drill-down |
| GraphExplorer | 5 layouts | Paths, communities, centrality |
| RealtimeFeed | Priority, filters | WebSocket, history |

---

### 8. Production Event System (`production_events/`)

**Purpose**: Enterprise-grade event processing with reliability guarantees

**Components**:
```
production_events/
├── queue.py         # Priority heap, scheduled, DLQ, metrics
├── worker.py        # Multi-topic, concurrency, health
├── scheduler.py     # 6 types: interval, cron, daily, weekly, monthly, one-time
├── persistence.py   # Partitioning, retention, replay
├── retry.py         # Exponential backoff, circuit breaker, DLQ
└── event_bus.py     # Topics, partitioning, ordering, replay
```

**Queue Features**:
- Priority heap (Critical > High > Normal > Low > Background)
- Scheduled/delayed execution
- Dead letter queue with replay
- Metrics: throughput, latency, depth, age

**Scheduler Types**:
| Type | Expression | Example |
|------|------------|---------|
| Interval | "30s", "5m", "1h", "1d" | Every 5 minutes |
| Cron | "0 9 * * *" | Daily 9:30 AM |
| Daily | "09:30" | Every day 9:30 |
| Weekly | "mon 09:00" | Mondays 9:00 AM |
| Monthly | "1 09:00" | 1st of month 9:00 AM |
| One-Time | "2024-12-31 23:59" | Year-end |

**Retry Policy**:
- Exponential backoff: 5s, 10s, 20s, 40s... (max 5min)
- Circuit breaker: 3-state (closed/open/half-open)
- DLQ with manual/automatic replay

---

## Data Flow Patterns

### 1. Research Request Flow
```
User Query → Workspace → Query Builder → Autonomous Research
    → Thesis Generator → Evidence Ranker → Agent Debate
    → Confidence Scorer → Contradiction Detector → Synthesizer
    → Report → Dashboard → User
```

### 2. Real-Time Data Flow
```
External APIs → Market/News Stream → Event Bus → WebSocket
    → Dashboard Components → User Browser
```

### 3. Knowledge Graph Sync
```
PostgreSQL (Source) → Sync Manager → Neo4j (Graph)
    → Graph Algorithms → Communities/Centrality
    → Semantic Intelligence → Embeddings/Vector Store
    → Context Ranker → Research Workspace
```

### 4. Portfolio Risk Flow
```
Portfolio → Factor Exposures → Monte Carlo → Stress Tests
    → Risk Decomposition → VaR/CVaR → Attribution
    → Dashboard → Risk Alerts
```

### 5. Predictive Intelligence Flow
```
Market Data → Forecast Engine → Predictions
    → Early Warning → Alerts
    → Event Prediction → Signals
    → Risk Prediction → Portfolio Alerts
    → Regime Detection → Strategy Adjustment
```

---

## Deployment Architecture

### Kubernetes Resources
```yaml
# Core Services
Deployment: api-gateway (3 replicas, HPA)
Deployment: research-engine (5 replicas, HPA)
Deployment: realtime-gateway (3 replicas, HPA)
Deployment: dashboard (2 replicas)
StatefulSet: postgres-primary (1), postgres-replica (2)
StatefulSet: neo4j (3, causal clustering)
StatefulSet: chromadb (3)
StatefulSet: redis (3, sentinel)
Deployment: workers (10, KEDA scaling)
Deployment: scheduler (1, leader election)
```

### Scaling Policies
| Component | Metric | Scale Trigger |
|-----------|--------|---------------|
| API Gateway | CPU > 70% | +1 replica |
| Research Engine | Queue depth > 100 | +2 replicas |
| Workers | Queue latency > 5s | +2 replicas |
| Dashboard | Connections > 5000 | +1 replica |

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                           │
├─────────────────────────────────────────────────────────────┤
│  Network:    VPC, Private Subnets, Security Groups, WAF    │
│  Transport:  TLS 1.3, mTLS (service mesh), Certificate Mgmt │
│  Identity:   JWT RS256 + JWKS, API Keys (bcrypt), OIDC     │
│  Access:     RBAC (Admin/Analyst/Viewer), ABAC (attributes) │
│  Data:       Encryption at rest (AES-256), in transit (TLS) │
│  App:        Input validation (Pydantic), Rate limiting,   │
│              Circuit breakers, Prompt injection detection   │
│  Audit:      Immutable logs, Correlation IDs, GDPR-ready    │
└─────────────────────────────────────────────────────────────┘
```

---

## Monitoring & Observability

```
┌─────────────────────────────────────────────────────────────┐
│                    OBSERVABILITY STACK                       │
├─────────────────────────────────────────────────────────────┤
│  Metrics:     Prometheus + Grafana (custom dashboards)      │
│  Logs:        ELK Stack / Loki + Promtail                   │
│  Traces:      Jaeger / Tempo (distributed tracing)          │
│  Alerts:      Alertmanager + PagerDuty / Slack / Email      │
│  Health:      /health/live, /health/ready, /health/detailed │
│  Business:    Custom metrics (research quality, accuracy)   │
└─────────────────────────────────────────────────────────────┘
```

---

## Migration from Phase 8

### Backward Compatibility
- All Phase 1-8 APIs unchanged
- Existing agents work without modification
- Database schema additive only (7 new tables)
- Configuration additive only

### New Capabilities
| Phase 8 | Phase 9 Enhancement |
|---------|---------------------|
| 7 Agents | 14 Specialized Agents + Orchestration |
| Static Reports | Autonomous Research + Live Workflows |
| Basic Cache | Multi-backend Vector Store + Graph |
| Batch Processing | Real-time Streaming + Event Bus |
| Basic Portfolio | Advanced MC + Copulas + Stress |
| Basic Risk | Predictive Risk + Regime Detection |
| Static Dashboard | Live Dashboard + Graph Explorer |
| Basic Queue | Production Event System |

---

*Architecture Update: 2026-07-18*  
*Platform: Autonomous Financial Intelligence Platform v2.0*