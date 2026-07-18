# System Overview
## Agentic Financial Intelligence Platform

---

## Executive Summary

The Agentic Financial Intelligence Platform is a production-grade, multi-agent AI system that automates end-to-end equity research workflows. It combines 14 specialized AI agents with a sophisticated orchestration layer, RAG pipeline, and autonomous decision-making capabilities.

**Version**: v1.7.0-phase8  
**Status**: Production Ready  
**Architecture**: Modular, async-first, event-driven  

---

## Core Capabilities

| Domain | Implementation | Status |
|--------|---------------|--------|
| **Financial Document Analysis** | RAG-powered SEC filings, earnings transcripts, analyst reports | ✅ Phase 4 |
| **Sentiment Analysis** | Multi-source (news, social, analyst) with credibility weighting | ✅ Phase 2 |
| **Risk Assessment** | VaR/CVaR, stress testing, multi-category risk | ✅ Phase 1 |
| **Competitive Intelligence** | Peer comparison, benchmarking, positioning | ✅ Phase 1 |
| **News Intelligence** | 6 providers, deduplication, events, entities | ✅ Phase 3 |
| **Market Data** | Real-time quotes, technicals, fundamentals | ✅ Phase 2 |
| **Investment Synthesis** | Multi-agent thesis formulation | ✅ Phase 1 |
| **Entity Recognition** | 7-layer NLP, 28 types, 35+ relationships | ✅ Phase 2.3 |
| **Knowledge Graph** | 14 node types, 28 relationships, graph algorithms | ✅ Phase 5 |
| **Portfolio Management** | Positions, VaR, Monte Carlo, 5 rebalance strategies | ✅ Phase 5 |
| **Pattern Detection** | 10 pattern types, backtesting | ✅ Phase 5 |
| **Alert Engine** | 30+ types, 5 channels, deduplication | ✅ Phase 5 |
| **Advanced Analytics** | FF3/5, Monte Carlo, attribution, scenarios | ✅ Phase 5 |
| **Historical Intelligence** | Trends, evolution, peer comparison | ✅ Phase 5 |
| **Cross-Agent Memory** | 9 types, 5 scopes, supersession | ✅ Phase 5 |
| **Production Hardening** | Config, logging, metrics, security, circuit breakers | ✅ Phase 6 |
| **Autonomous Workflows** | Planning, orchestration, memory, reports | ✅ Phase 7 |
| **AI Copilot** | Natural language, planning, tools, decisions | ✅ Phase 8 |

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  CLI          │  REST API (FastAPI)          │  Streamlit Dashboard        │
└───────────────┴──────────────────────────────┴──────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      COPILOT ORCHESTRATION LAYER (Phase 8)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Copilot Agent  │  Task Planner  │  Tool Selector  │  Decision Engine     │
│                 │                │                 │                       │
│  Collaboration  │  Memory        │  Explainability │  LLM Orchestrator    │
└─────────────────┴────────────────┴─────────────────┴───────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    WORKFLOW ORCHESTRATION (Phase 7)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Research Planner  │  Workflow Orchestrator  │  Watchlists & Alerts        │
│                    │  (Topological sort,       │  Reports & Approvals      │
│                    │   parallel waves)         │                           │
└────────────────────┴───────────────────────────┴───────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AGENT LAYER (8 Specialized Agents)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Financial Doc  │  Sentiment  │  Risk  │  Competitive  │  News  │  Market  │
│  Investment Sum │  Planner    │        │             │  KG    │  Portfolio│
│  Patterns       │  Alerts     │  Analytics  │  Historical  │  Memory      │
└─────────────────┴─────────────┴────────┴─────────────┴──────┴──────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SUPPORTING INFRASTRUCTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  LLM Orchestration  │  Tool Registry  │  Collaboration  │  Decision Engine │
│  (9 models, 4 goals) │  (15 tools)     │  (consensus)    │  (6-step)       │
│  Enhanced Memory    │  RAG Pipeline   │  Knowledge Graph│  Explainability  │
│  (5 scopes)         │  (BGE-M3)       │  (14 nodes)     │  (evidence)     │
└─────────────────────┴─────────────────┴─────────────────┴──────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATA & INFRASTRUCTURE LAYER                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  PostgreSQL  │  ChromaDB  │  Redis  │  SEC EDGAR  │  6 News APIs  │ Market │
│  (27 tables) │  (Vector)  │  (Cache)│  (SEC)      │  (Multi)      │ Data   │
└───────────────┴────────────┴─────────┴────────────┴────────────────┴────────┘
```

---

## Technology Stack

### Core AI/ML
| Component | Technology | Purpose |
|-----------|------------|---------|
| LLM Provider | OpenRouter (Primary) | Unified API for Claude, GPT, Gemini, DeepSeek |
| Embeddings | BGE-M3 (BAAI) | 1024-dim multilingual financial text |
| Re-ranker | BGE-Reranker-v2-M3 | Cross-encoder precision for RAG |
| Vector DB | ChromaDB | Efficient similarity search |
| NLP | spaCy + Custom | 7-layer entity recognition |
| Graph | NetworkX + PostgreSQL | Knowledge graph operations |

### Data & Infrastructure
| Component | Technology | Purpose |
|-----------|------------|---------|
| Primary DB | PostgreSQL 15+ | Relational storage, 27 tables |
| Vector Store | ChromaDB | Embeddings, RAG retrieval |
| Cache | Redis 7 | Sessions, rate limiting, cache |
| Document Processing | PyMuPDF + LlamaIndex | PDF/text extraction, chunking |
| Financial APIs | Alpha Vantage, Polygon.io, Yahoo | Market/fundamental data |
| SEC Data | SEC EDGAR | Corporate filings |
| News APIs | Yahoo, Finnhub, Alpha Vantage, NewsAPI, RSS | Multi-source news |

### Frontend & DevOps
| Component | Technology | Purpose |
|-----------|------------|---------|
| Dashboard | Streamlit 1.38+ | Interactive research interface |
| API Framework | FastAPI | High-performance REST API |
| Web Server | Uvicorn | ASGI server for FastAPI |
| Containerization | Docker | Consistent environment packaging |
| Orchestration | Docker Compose | Local development and testing |
| Monitoring | Prometheus + Grafana | Metrics collection and visualization |
| Logging | Structured JSON | Centralized logging with severity |

---

## Design Principles

1. **Async-First**: All I/O operations use async/await for maximum throughput
2. **Type Safety**: 100% type hints on public APIs, mypy validated
3. **Modularity**: Each agent is independently deployable and testable
3. **Observability**: Structured logging, Prometheus metrics, health probes
4. **Security**: JWT RS256, API keys with bcrypt, RBAC, injection detection
4. **Resilience**: Circuit breakers, rate limiting, retry with backoff
4. **Auditability**: Full decision trails, evidence citations, cost tracking
4. **Extensibility**: Plugin architecture for agents, tools, models

---

## Data Flow Summary

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  COPILOT: Intent Classification → Company Extraction        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  TASK PLANNER: Complexity Analysis → Agent Selection        │
│         Dependency Graph → Parallel Wave Planning           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  TOOL SELECTOR: Confidence-based tool routing (15 tools)   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  DECISION ENGINE: 6-Step Reasoning Chain                    │
│  Evidence → Hypotheses → Evaluation → Alternatives → Risk → │
│  Synthesis (Internal reasoning NEVER exposed to users)      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  EXECUTION: Parallel wave execution with retry/backoff      │
│         Memory integration for cross-agent context          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  EXPLAINABILITY: Evidence → Alternatives → Risks →          │
│         Assumptions → User-facing explanation               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  OUTPUT: Chat response / Report / Watchlist / Alert         │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Metrics

| Metric | Target | Current |
|--------|--------|---------|
| API Response (p95) | <200ms | ~150ms |
| Document Processing | <5s/100pg | ~3s/100pg |
| Cache Hit Rate | >90% | ~95% |
| SEC Rate Limit | 10 req/s | 10 req/s enforced |
| Test Suite | <60s | ~23s |
| Memory (idle) | <500MB | ~210MB |
| CPU (idle) | <5% | ~1% |
| Test Coverage | >90% | ~92% |

---

## Security Posture

- **Authentication**: JWT RS256 + API Keys (bcrypt)
- **Authorization**: RBAC (Admin/Analyst/Viewer, 20+ permissions)
- **Input Validation**: Pydantic models, SQL injection detection, prompt injection detection
- **Rate Limiting**: Token bucket + sliding window (adaptive)
- **Circuit Breakers**: 3-state with auto-recovery
- **Security Headers**: CSP, HSTS, X-Frame, Referrer-Policy
- **Audit Trail**: Immutable decision history with outcomes

---

## Deployment Architecture

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    │    (nginx)      │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌───────────┐  ┌───────────┐  ┌───────────┐
        │  API Pod  │  │  API Pod  │  │  API Pod  │
        │  (FastAPI)│  │  (FastAPI)│  │  (FastAPI)│
        └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌───────────┐  ┌───────────┐  ┌───────────┐
        │PostgreSQL │  │  ChromaDB │  │   Redis   │
        │ (Primary) │  │  (Vector) │  │  (Cache)  │
        └───────────┘  └───────────┘  └───────────┘
```

---

*Document Version: 1.0*  
*Last Updated: 2026-07-18*  
*Platform: Agentic Financial Intelligence Platform v1.7.0-phase8*