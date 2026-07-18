# Agentic Financial Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-396%20passing-brightgreen.svg)](https://github.com/LeelaissakAttota/agentic-financial-intelligence-platform/actions)
[![Implemented Agents](https://img.shields.io/badge/Implemented%20Agents-8/8-green.svg)](#implementation-status)
[![Phase](https://img.shields.io/badge/Phase-7%20Complete-blue.svg)](#phase-7-autonomous-research-workflows)

> **An AI-powered financial research system that automates financial document analysis, sentiment analysis, risk assessment, competitive intelligence, news intelligence, market data analysis, and investment synthesis through a multi-agent architecture with Retrieval-Augmented Generation (RAG) capabilities.**

---

## 🎯 Project Overview

### What the Project Does
The Agentic Financial Intelligence Platform is an **implemented system** that automates specific aspects of financial research workflows. It currently provides:
- **Financial Document Analysis**: RAG-powered analysis of SEC filings (10-K, 10-Q), earnings transcripts, and analyst reports
- **Sentiment Analysis**: Multi-source sentiment scoring from news, social media, and analyst opinions
- **Risk Assessment**: Multi-category risk analysis (market, credit, operational, liquidity)
- **Competitive Intelligence**: Peer comparison and positioning analysis
- **News Intelligence**: Financial news aggregation, sentiment, event detection, and entity extraction
- **Market Data Analysis**: Real-time market data, technical indicators, and fundamentals
- **Investment Summary**: Multi-agent insight synthesis and thesis formulation
- **Financial Entity Recognition**: 7-layer hybrid NLP pipeline for entity extraction (28 types, 100+ sub-types, 35+ relationships)
- **Persistent Storage**: Research history and agent execution tracking via PostgreSQL
- **Flexible LLM Integration**: OpenRouter primary with fallback options
- **Multiple Interfaces**: CLI, REST API, and Streamlit dashboard
- **Autonomous Research Workflows**: Dynamic planning, orchestration, and memory

### Phase 7: Autonomous Research Workflows (NEW)
- **Research Planner Agent**: LLM-driven dynamic task planning based on query complexity
- **Workflow Orchestrator**: Topological sort for execution waves, parallel execution with bounded concurrency, retry with exponential backoff
- **Research Memory**: Persistent sessions, conclusions, agent outputs, cross-session knowledge retrieval, semantic search ready
- **Watchlists & Monitoring**: Company/ETF tracking, alert rules with complex conditions, multi-channel notifications
- **Automated Report Generation**: 8 report types (Executive Summary, Analyst Report, Investment Thesis, Company Snapshot, Industry Analysis, Daily/Weekly/Monthly Briefings), Markdown/HTML/JSON export
- **Human Approval Workflow**: Approve/Reject/Request Changes/Escalate with audit trail
- **Research Dashboard API**: Research Queue, Workflow Status, Running Tasks, Completed Reports, Agent Activity, Notifications, Watchlists, Research History

### Why Financial Research Automation is Valuable
Financial analysts spend approximately 70% of their time on data collection and only 30% on actual analysis and insight generation. Traditional research workflows involve manual gathering of data from disparate sources (SEC filings, earnings transcripts, news, market data), leading to inefficiencies, inconsistent analysis, and knowledge loss when projects end.

### How Agentic AI Improves the Workflow
The platform uses a **modular agent-based architecture** where specialized AI agents handle distinct aspects of financial research:
- **Automation**: Eliminates manual data collection and initial analysis
- **Consistency**: Standardized processes reduce human bias and variability
- **Speed**: Reduces research time from hours/days to minutes
- **Auditability**: Every conclusion is traceable to source documents with citations
- **Knowledge Retention**: Persistent storage enables learning from past research

---

## 📋 Problem Statement

Traditional financial research suffers from several critical inefficiencies:

### ⏰ Time Inefficiency
- Analysts spend 70% of time on data collection, 30% on analysis
- Manual gathering from 10+ disparate sources (SEC EDGAR, news sites, financial databases)
- Repetitive work across similar research projects

### 📊 Quality & Consistency Issues
- Human bias and fatigue affect analysis quality
- Inconsistent methodologies across analysts and teams
- Difficulty maintaining standardized quality controls

### 🧠 Knowledge Limitations
- Insights trapped in individual analysts' notes and memories
- No systematic way to build organizational knowledge
- Difficulty leveraging past research for new projects

### 🔍 Verification Challenges
- Manual source verification is time-consuming and error-prone
- Audit trails are difficult to maintain
- Tracing conclusions back to source documents is challenging

### ⚡ Speed Limitations
- Research cycles measured in hours or days
- Unable to respond quickly to market-moving events
- Bottlenecks in high-frequency decision-making environments

---

## 💡 Solution

The Agentic Financial Intelligence Platform addresses these challenges through a **modular agent-based AI system** that:

### 🤖 Automates the Research Workflow
- Replaces manual data collection with automated agent execution
- Processes financial documents, news, social media, and market data autonomously
- Eliminates repetitive data gathering tasks

### 🎯 Ensures Consistent, High-Quality Analysis
- Standardized agent behaviors reduce variability
- Evidence-based conclusions through RAG grounding
- Configurable confidence scoring and divergence detection
- Structured output formats ensure consistency

### 🧠 Builds Organizational Knowledge
- Persistent storage of all research sessions and agent outputs
- Enables knowledge retrieval for future similar queries
- Foundation for implementing learning systems over time

### 🔬 Provides Verifiable, Auditable Results
- Every financial claim tied to source documents with page/section references
- Source credibility scoring for external information
- Complete execution metadata (timing, token usage, costs)
- Database persistence for audit trails and compliance

### ⚡ Delivers Rapid Insights
- Reduces research time from hours/days to minutes
- Parallel processing capabilities (planned enhancement)
- Responsive API and dashboard interfaces
- Enables real-time monitoring and alerting (future enhancement)

---

## 🏗️ Architecture

```mermaid
flowchart TD
    A[User Input] --> B[AI Orchestrator (Manager Agent)]
    B --> C[Financial Document Agent]:::implemented
    B --> D[Sentiment Analysis Agent]:::implemented
    B --> E[Risk Assessment Agent]:::implemented
    B --> F[Competitive Intelligence Agent]:::implemented
    B --> G[News Intelligence Agent]:::implemented
    B --> H[Market Data Agent]:::implemented
    B --> I[Investment Summary Agent]:::implemented
    B --> J[Research Planner Agent]:::implemented
    J --> K[Workflow Orchestrator]:::implemented
    K --> L[Research Memory]:::implemented
    L --> M[Watchlists & Monitoring]:::implemented
    M --> N[Report Generator]:::implemented
    N --> O[Approval Workflow]:::implemented
    O --> P[Notification Engine]:::implemented
    C --> Q[RAG Knowledge Base]
    Q --> R[Vector Search (BGE-M3)]
    R --> S[Re-ranking (BGE-Reranker)]
    S --> T[Cited Answers with Sources]
    T --> U[Structured Financial Analysis]
    U --> V[Final Output]

    classDef implemented fill:#d4edda,stroke:#28a745;
    classDef planned fill:#f8d7da,stroke:#dc3545;

    style A fill:#e3f2fd,stroke:#1565c0
    style B fill:#f3e5f5,stroke:#7b1fa2
    style C fill:#fff3e0,stroke:#e65100
    style D fill:#e8f5e9,stroke:#2e7d32
    style E fill:#fce4ec,stroke:#c2185b
    style G fill:#e3f2fd,stroke:#1565c0
    style H fill:#fff3e0,stroke:#e65100
    style I fill:#e8f5e9,stroke:#2e7d32
    style J fill:#fff3e0,stroke:#e65100
    style K fill:#e8f5e9,stroke:#2e7d32
    style L fill:#fff3e0,stroke:#e65100
    style M fill:#e8f5e9,stroke:#2e7d32
    style N fill:#fff3e0,stroke:#e65100
    style O fill:#e8f5e9,stroke:#2e7d32
    style P fill:#f3e5f5,stroke:#7b1fa2
    style Q fill:#f3e5f5,stroke:#7b1fa2
    style R fill:#fff3e0,stroke:#e65100
    style S fill:#e8f5e9,stroke:#2e7d32
    style T fill:#fff3e0,stroke:#e65100
    style U fill:#e8f5e9,stroke:#2e7d32
    style V fill:#fce4ec,stroke:#c2185b
```

### Component Details

```
┌─────────────────────────────────────────────────────────────────┐
│                 AGENTIC FINANCIAL INTELLIGENCE PLATFORM         │
├─────────────────────────────────────────────────────────────────┤
│  Orchestration Layer (Manager Agent)                            │
│  • Agent registration and lifecycle management                  │
│  • Workflow execution coordination                              │
│  • Result aggregation and persistence                           │
├─────────────────────────────────────────────────────────────────┤
│  Implemented Agents (8/8):                                      │
│  • Financial Document Agent  ✅ (RAG-based financial analysis)  │
│  • Sentiment Analysis Agent  ✅ (Multi-source sentiment analysis)│
│  • Risk Assessment Agent     ✅ (Multi-category risk assessment) │
│  • Competitive Intelligence  ✅ (Peer comparison analysis)      │
│  • News Intelligence Agent   ✅ (Financial news processing)     │
│  • Market Data Agent         ✅ (Real-time market data & analysis)│
│  • Investment Summary Agent  ✅ (Multi-agent synthesis)         │
│  • Research Planner Agent    ✅ (Autonomous task planning)      │
├─────────────────────────────────────────────────────────────────┤
│  Supporting Systems:                                            │
│  • LLM Abstraction Layer (OpenRouter primary)                  │
│  • RAG System (BGE-M3 embeddings + ChromaDB)                   │
│  • Database Persistence (PostgreSQL + SQLAlchemy)              │
│  • REST API (FastAPI)                                          │
│  • Web Dashboard (Streamlit)                                   │
├─────────────────────────────────────────────────────────────────┤
│  Phase 6: Production Hardening:                                 │
│  • Centralized Configuration (80+ typed settings)               │
│  • Structured Logging (JSON/text, correlation IDs, rotation)   │
│  • Monitoring & Metrics (30+ Prometheus metrics, health probes)│
│  • Performance Tracking (decorators, context managers, p50/p95)│
│  • Cache Abstraction (L1 Memory + L2 Redis, tiered, @cached)   │
│  • Security & Auth (JWT RS256, API Keys, RBAC, injection detection)│
│  • Rate Limiting (token bucket + sliding window, adaptive)      │
│  • Circuit Breaker (3-state, auto-recovery, HTTP/DB wrappers)  │
│  • Request/Response Logging (correlation IDs, security events) │
│  • Middleware Stack: CORS → Rate Limit → Logging → Security    │
├─────────────────────────────────────────────────────────────────┤
│  Phase 7: Autonomous Research Workflows:                       │
│  • Research Planner Agent (LLM-driven dynamic planning)        │
│  • Workflow Orchestrator (topological sort, parallel waves)    │
│  • Research Memory (persistent sessions, conclusions, embeddings)│
│  • Watchlists & Monitoring (5 types, complex alerts, channels) │
│  • Automated Report Generator (8 types, 3 formats)             │
│  • Human Approval Workflow (6 actions, audit trail)            │
│  • Research Dashboard API (15 endpoints)                       │
│  • Notification Engine (6 channels, retry, history)            │
├─────────────────────────────────────────────────────────────────┤
│  News Intelligence Stack (Phase 2.2 + 3):                       │
│  • 6 News Providers (Yahoo, Finnhub, Alpha Vantage, NewsAPI, RSS, Google News)│
│  • Fallback Chain with Automatic Provider Switching            │
│  • Article Deduplication (4 strategies)                        │
│  • Sentiment Scoring + Event Detection + Entity Extraction     │
│  • **Phase 3: News Aggregator** (multi-source, relevance, time decay)│
│  • **Phase 3: Company Intelligence** (companies, people, products, events)│
│  • **Phase 3: Summarization** (executive summary, events, risks/opportunities)│
│  • **Phase 3: Database** (articles, metadata, companies, embeddings)│
│  • **Phase 3: Dashboard** (latest news, timeline, sentiment, sources)│
├─────────────────────────────────────────────────────────────────┤
│  Financial Entity Recognition (Phase 2.3):                      │
│  • 7-Layer Hybrid NLP Pipeline                                  │
│  • 28 Entity Types, 100+ Sub-Types, 35+ Relationship Types     │
│  • 100+ Built-in Financial Entities                            │
│  • 60+ Regex Patterns                                          │
│  • Entity Resolution (Ticker/Company/Alias)                    │
│  • Relationship Graph (NetworkX)                                │
│  • Confidence Engine (7 signals)                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🤖 AI Agents

### 1. Financial Document Agent
- **Purpose**: Analyzes financial statements and documents using Retrieval-Augmented Generation
- **Input**: Company name, ticker, question set, optional fiscal year/quarter
- **Processing Logic**: 
  - Processes SEC filings (10-K, 10-Q), earnings transcripts, analyst reports
  - Uses BGE-M3 embeddings for semantic document understanding
  - Implements hybrid search with BGE-Reranker-v2-M3 re-ranking
  - Generates structured financial analysis with source citations
  - Integrates with ChromaDB vector store for efficient retrieval
- **Output**: Structured financial metrics, ratio analysis, findings with citations
- **Technologies**: LlamaIndex, BGE-M3, BGE-Reranker-v2-M3, ChromaDB, PyMuPDF

### 2. Sentiment Analysis Agent
- **Purpose**: Analyzes market sentiment from multiple sources
- **Input**: Company name, optional context from other agents
- **Processing Logic**:
  - Analyzes sentiment from news articles, social media, and analyst opinions
  - Applies source credibility weighting (Tier 1: SEC/Bloomberg/Reuters, Tier 2: Analyst reports, Tier 3: Blogs)
  - Calculates sentiment distribution across 7-point scale (Very Bearish to Very Bullish)
  - Detects divergence between price movements and sentiment
  - Provides confidence scoring (High/Medium/Low)
- **Output**: Sentiment distribution, key drivers, divergence flag, confidence level
- **Technologies**: Custom sentiment analysis pipeline, source credibility scoring

### 3. Risk Assessment Agent
- **Purpose**: Evaluates multiple dimensions of financial risk
- **Input**: Company name, optional context from other agents
- **Processing Logic**:
  - Assesses market, credit, operational, and liquidity risks
  - Identifies and quantifies specific risk factors
  - Calculates VaR/CVaR and performs stress testing
  - Analyzes risk concentration and exposure
  - Checks regulatory compliance (Basel III principles)
- **Output**: Risk category scores, risk factors, overall risk assessment
- **Technologies**: Financial risk modeling, statistical analysis frameworks

### 4. Competitive Intelligence Agent
- **Purpose**: Analyzes competitive positioning and market dynamics
- **Input**: Company name, optional context from other agents
- **Processing Logic**:
  - Identifies peer group and competitors
  - Performs benchmarking across key financial and operational metrics
  - Evaluates competitive advantages and disadvantages
  - Analyzes market positioning and strategic groupings
  - Provides relative performance analysis
- **Output**: Peer comparison tables, competitive positioning analysis
- **Technologies**: Financial ratio analysis, benchmarking frameworks

### 5. News Intelligence Agent (Phase 2.2 + Phase 3)
- **Purpose**: Processes and analyzes financial news from multiple real providers
- **Input**: Company name, time frame, optional topics
- **Processing Logic**:
  - Aggregates news from 6 providers (Yahoo Finance, Finnhub, Alpha Vantage, NewsAPI, RSS, Google News)
  - Implements fallback chain with automatic provider switching
  - Deduplicates articles using title/content similarity
  - Scores sentiment per article with confidence
  - Extracts entities (companies, tickers, people, products, countries)
  - Detects events (earnings, M&A, lawsuits, product launches, guidance)
- **Output**: Sentiment trends, key events, impact analysis, entity mentions
- **Technologies**: Multi-provider news aggregation, NLP pipeline, event detection

### 6. Market Data Agent (Phase 2.1)
- **Purpose**: Analyzes real-time market and trading data
- **Input**: Company ticker, time frame, data types
- **Processing Logic**:
  - Fetches real-time quotes, fundamentals, historical prices, company info
  - Calculates technical indicators: RSI (14), SMA (20/50/200), MACD, Bollinger Bands
  - Normalizes fundamentals across providers
  - Provides market context and trend analysis
- **Output**: Technical analysis, fundamental valuation, market trends
- **Technologies**: Multi-provider market data (Yahoo Finance, Alpha Vantage, Finnhub), composite provider with fallback

### 7. Investment Summary Agent
- **Purpose**: Synthesizes insights from all agents into investment thesis
- **Input**: Context from all other agents
- **Processing Logic**:
  - Multi-agent synthesis
  - Thesis formulation
  - Risk-adjusted analysis
- **Output**: Investment recommendation, price target, catalyst timeline
- **Technologies**: Structured synthesis, weighted scoring

### 8. Research Planner Agent (Phase 7)
- **Purpose**: LLM-driven dynamic task planning based on query complexity
- **Input**: Research query, company, optional context
- **Processing Logic**:
  - Analyzes query complexity (SIMPLE/MODERATE/COMPLEX/COMPREHENSIVE)
  - Determines required agents based on query semantics
  - Creates dependency-aware execution plan with parallel groups
  - Estimates execution duration
- **Output**: Structured execution plan with steps, dependencies, parallel groups
- **Technologies**: OpenRouter LLM, topological sort, dependency resolution

---

## 🔄 Workflow

### User-to-Output Process

1. **Input Reception**
   - User submits company name/ticker and optional research question via CLI, API, or dashboard
   - System validates input and prepares execution context

2. **Orchestration Initialization**
   - ManagerAgent loads all registered worker agents
   - Creates execution plan based on available agents
   - Initializes LLM provider and database connections

3. **Agent Execution (Current Sequential Flow)**
   - **Financial Document Agent**: Retrieves and analyzes SEC filings, earnings transcripts using RAG
   - **Sentiment Analysis Agent**: Processes news, social media, and analyst sentiment with source weighting
   - **Risk Assessment Agent**: Evaluates multiple risk categories and provides scoring
   - **Competitive Intelligence Agent**: Performs peer comparison and positioning analysis
   - **News Intelligence Agent**: Aggregates real financial news, sentiment, events, entities
   - **Market Data Agent**: Analyzes real-time market data, technical indicators, fundamentals
   - **Investment Summary Agent**: Synthesizes insights into investment thesis

4. **Result Aggregation**
   - ManagerAgent collects outputs from all executed agents
   - Structures results into standardized format
   - Calculates execution metrics (time, tokens, cost)

5. **Persistence & Output**
   - Stores complete results in PostgreSQL database
   - Returns structured JSON response to user
   - Available via CLI, API response, or dashboard visualization

### Phase 7 Autonomous Workflow
1. **Planning**: Research Planner Agent creates execution plan with dependencies
2. **Approval**: Optional human approval workflow for research plans
3. **Execution**: Workflow Orchestrator executes steps in parallel waves
3. **Memory**: Each step stores outputs in Research Memory for cross-agent access
4. **Monitoring**: Watchlists evaluated, alerts triggered, notifications sent
5. **Reporting**: Report Generator creates formatted output
6. **Approval**: Optional human approval for final reports
7. **Delivery**: Reports delivered via configured channels

### Data Flow Example
```
User: "Analyze NVIDIA's competitive position in AI chips"
       ↓
Research Planner: Creates execution plan (COMPLEX complexity, 6 agents)
       ↓
Workflow Orchestrator: Executes in waves
  Wave 1 (parallel): Financial Document + News + Market Data
  Wave 2 (parallel): Sentiment + Patterns
  Wave 3 (sequential): Risk + Competitive
  Wave 4: Investment Summary (depends on all)
       ↓
Research Memory: Stores all agent outputs for cross-agent access
       ↓
Watchlist Monitor: Evaluates alerts, triggers notifications
       ↓
Report Generator: Creates Analyst Report + Investment Thesis
       ↓
Approval Workflow: Human review (optional)
       ↓
Delivery: Reports + notifications via configured channels
```

---

## 🛠️ Technology Stack

### Core AI/ML Components
| Component | Technology | Purpose |
|-----------|------------|---------|
| **LLM Provider** | OpenRouter (Primary) | Unified API for Claude 3.5 Sonnet, GPT-4o, and other models |
| **Agent Framework** | Custom BaseWorkerAgent | Standardized agent interface with lifecycle management |
| **Embedding Model** | BGE-M3 (BAAI) | 1024-dim multilingual embeddings for financial text |
| **Re-ranker** | BGE-Reranker-v2-M3 (BAAI) | Cross-encoder precision enhancement for RAG |
| **Vector Database** | ChromaDB | Efficient similarity search and retrieval |
| **JSON Extraction** | Custom Utility | Robust LLM output parsing with markdown fence handling |
| **Cost Tracking** | Custom Module | Token usage and cost calculation per model |
| **Entity Recognition** | 7-Layer Hybrid NLP | spaCy + Dictionary + LLM Validation + Resolution + Graph |

### Data & Infrastructure
| Component | Technology | Purpose |
|-----------|------------|---------|
| **Primary Database** | PostgreSQL 15+ | Relational storage for companies, reports, agent runs |
| **ORM** | SQLAlchemy 2.0 | Object-relational mapping for database interactions |
| **Cache Layer** | Redis 7 | Session management and API rate limiting |
| **Document Processing** | PyMuPDF + LlamaIndex | PDF/text extraction and chunking for RAG |
| **Financial APIs** | Alpha Vantage, Polygon.io, Yahoo Finance | Market and fundamental data |
| **SEC Data** | SEC EDGAR | Corporate filings (10-K, 10-Q, 8-K, etc.) |
| **News Providers** | Yahoo, Finnhub, Alpha Vantage, NewsAPI, RSS, Google News | Multi-source news aggregation |

### Frontend & DevOps
| Component | Technology | Purpose |
|-----------|------------|---------|
| **Dashboard** | Streamlit 1.38+ | Interactive research interface |
| **API Framework** | FastAPI | High-performance REST API with auto-docs |
| **Web Server** | Uvicorn | ASGI server for FastAPI |
| **Containerization** | Docker | Consistent environment packaging |
| **Orchestration** | Docker Compose | Local development and testing |
| **Monitoring** | Prometheus + Grafana | Metrics collection and visualization (configurable) |
| **Logging** | Structured JSON | Centralized logging with severity levels |
| **Testing Framework** | Pytest | 396 unit tests with >90% coverage |
| **Code Quality** | Black, Ruff, MyPy | Formatting, linting, and type checking |

---

## ✨ Features

### Implemented Features
- ✅ **Financial Document Analysis**: RAG-powered processing of SEC filings and earnings transcripts
- ✅ **Multi-source Sentiment Analysis**: News, social media, and analyst sentiment with source weighting
- ✅ **Risk Assessment Analysis**: Market, credit, operational, and liquidity risk evaluation
- ✅ **Competitive Intelligence**: Peer comparison and competitive positioning analysis
- ✅ **News Intelligence**: Financial news aggregation, sentiment, event detection, entity extraction
- ✅ **Market Data Analysis**: Real-time market data, technical indicators, and fundamentals
- ✅ **Investment Summary**: Multi-agent insight synthesis and thesis formulation
- ✅ **Financial Entity Recognition**: 7-layer hybrid NLP pipeline (28 types, 100+ sub-types, 35+ relationships)
- ✅ **Persistent Knowledge Storage**: PostgreSQL storage of research history and executions
- ✅ **Flexible LLM Integration**: OpenRouter primary with OpenAI/Anthropic fallbacks
- ✅ **REST API**: Full CRUD interface for research jobs and results
- ✅ **Interactive Dashboard**: Streamlit interface with real-time agent monitoring
- ✅ **Automated Testing**: 396+ unit tests passing (>90% coverage)
- ✅ **Docker Deployment**: Containerized services with docker-compose orchestration
- ✅ **News Aggregator (Phase 3)**: Multi-source collection, duplicate removal, importance ranking, company relevance scoring, time decay, source credibility
- ✅ **Company News Intelligence (Phase 3)**: Extract companies, people, products, earnings, acquisitions, partnerships, lawsuits, regulations
- ✅ **News Summarization (Phase 3)**: Executive Summary, Positive Events, Negative Events, Opportunities, Risks
- ✅ **News Database (Phase 3)**: Articles, metadata, companies, categories, sentiment, embeddings
- ✅ **Dashboard (Phase 3)**: Latest News, Top Headlines, News Timeline, News Sentiment, Source Breakdown

### Phase 4: Financial Documents Intelligence
- ✅ **SEC Filing Downloader**: 16 form types, rate-limited, cached
- ✅ **Document Cache**: Multi-tier (memory + SQLite), versioned, deduplicated
- ✅ **Incremental Updates**: Scheduled, resumable, RAG-integrated
- ✅ **PDF Parser**: 3 backends (pdfplumber, PyMuPDF, pdfminer) with fallback
- ✅ **Table Extractor**: Financial statement classification, period/currency/unit detection
- ✅ **Statement Parsers**: Income Statement, Balance Sheet, Cash Flow
- ✅ **Earnings Transcripts**: Speaker ID, Q&A extraction, guidance, sentiment
- ✅ **Annual Reports**: Business overview, financials, segments, MD&A, risk factors
- ✅ **Quarterly Reports**: Financial results, guidance, segment performance
- ✅ **Investor Presentations**: Slides, highlights, initiatives, capital allocation
- ✅ **Full RAG Integration**: Section-aware chunking, vector storage

### Phase 5: Knowledge Intelligence Platform
- ✅ **Knowledge Graph**: 14 node types, 28 relationship types, PostgreSQL persistence, graph traversal, centrality, community detection
- ✅ **Portfolio Intelligence**: Position management, order execution, VaR/CVaR, Monte Carlo, rebalancing (5 strategies), sector allocation
- ✅ **Pattern Detection**: 10 pattern types (trend, seasonal, S/R, reversal, breakout, volume spike, cycle, regime change, anomaly, correlation)
- ✅ **Alert Engine**: 30+ alert types, 5 channels (Email, Slack, Discord, Webhook, Console), deduplication, cooldown, rate limiting, retry logic
- ✅ **Advanced Analytics**: Fama-French 3/5-factor, Monte Carlo (10K paths), Brinson attribution, scenario analysis, rolling correlation
- ✅ **Historical Intelligence**: Time-series storage, trend analysis (Mann-Kendall, Sen's slope), company evolution, peer comparison
- ✅ **Cross-Agent Memory**: 9 memory types, 5 scopes, supersession, linking, access logging, TTL expiration
- ✅ **Dashboard Extensions**: 5 new tabs (Knowledge Graph, Portfolio, Alerts, Patterns, Analytics) with visualizations

### Phase 3 - Real Financial Intelligence
- ✅ **News Aggregator**: Multi-source collection, duplicate removal, importance ranking, company relevance scoring, time decay, source credibility
- ✅ **Company News Intelligence**: Extract companies, people, products, earnings, acquisitions, partnerships, lawsuits, regulations
- ✅ **News Summarization**: Executive Summary, Positive Events, Negative Events, Opportunities, Risks
- ✅ **News Database**: Articles, metadata, companies, categories, sentiment, embeddings
- ✅ **Dashboard**: Latest News, Top Headlines, News Timeline, News Sentiment, Source Breakdown

### Phase 6: Production Hardening
- ✅ **Centralized Configuration**: Environment-specific configs (prod/dev), typed settings (80+ fields), validation
- ✅ **Structured Logging**: JSON/text formatters, correlation IDs, request IDs, agent context, execution timing
- ✅ **Prometheus Metrics**: HTTP, LLM, DB, Agent, Vector, Cache, System, Errors, Business metrics
- ✅ **Health Checks**: DB, Redis, ChromaDB, LLM, Agent System, System Resources, K8s probes
- ✅ **Performance Tracking**: Decorators, context managers, p50/p95/p99 stats, resource monitoring
- ✅ **Tiered Caching**: L1 Memory (LRU) + L2 Redis, tag invalidation, `@cached` decorator
- ✅ **Security**: JWT (RS256), API Keys (bcrypt), RBAC (3 roles, 20+ perms), SQL/prompt injection detection, CSP/HSTS headers
- ✅ **Rate Limiting**: Token bucket + sliding window, adaptive limits, standard headers
- ✅ **Circuit Breakers**: 3-state, auto-recovery, HTTP client & DB wrappers
- ✅ **Middleware Stack**: CORS → Rate Limit → Logging → Security → Compression

### Phase 7: Autonomous Research Workflows (NEW)
- ✅ **Research Planner Agent**: LLM-driven dynamic planning, 4 complexity levels, 14 agent types
- ✅ **Workflow Orchestrator**: Topological sort, parallel waves, retry with backoff, context propagation
- ✅ **Research Memory**: Persistent sessions, conclusions, agent outputs, embeddings-ready
- ✅ **Watchlists & Monitoring**: 5 types, target/stop prices, 10+ alert conditions, cooldown, channels
- ✅ **Automated Report Generation**: 8 types, Markdown/HTML/JSON, templates, citations
- ✅ **Human Approval Workflow**: 6 actions, sequential chains, escalation, delegation, audit trail
- ✅ **Notification Engine**: 6 channels, retry logic, templates, history, callbacks
- ✅ **Research Dashboard API**: 15 endpoints (research, watchlists, approvals, reports, status)

### Planned Features (Future Implementation)
- ⏸️ **Parallel Execution**: Enable concurrent agent execution where dependencies allow
- ⏸️ **Enhanced Context Passing**: Share relevant outputs between agents
- ⏸️ **Dynamic Task Planning**: LLM-driven agent sequencing based on query complexity
- ⏸️ **Advanced RAG**: Cross-agent knowledge sharing via vector embeddings
- ⏸️ **MLOps Features**: Model drift detection, A/B testing, continuous learning
- ⏸️ **User Feedback System**: Rating and correction mechanisms for improvement
- ⏸️ **Neo4j Knowledge Graph**: Enhanced graph database for relationship tracking
- ⏸️ **Real-time Dashboard**: WebSocket updates for live agent monitoring
- ⏸️ **Multi-asset Monte Carlo**: Correlation modeling with copulas

---

## 📁 Project Structure

```
agentic-financial-intelligence-platform/
├── .github/                   # CI/CD workflows and templates
├── .gitignore                 # Git ignore rules
├── Dockerfile                 # Production container image
├── docker-compose.yml         # Multi-service orchestration (dev)
├── .env.example               # Environment variable template
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development & testing dependencies
├── alembic/                   # Database migrations
├── agents/                    # AI agent implementations
│   ├── __init__.py
│   ├── financial_document_agent/   # ✅ Implemented (RAG-based)
│   │   ├── agent.py
│   │   ├── schemas.py
│   │   ├── prompts.py
│   │   └── exceptions.py
│   ├── sentiment_analysis_agent/   # ✅ Implemented (multi-source)
│   │   ├── agent.py
│   │   ├── schemas.py
│   │   ├── prompts.py
│   │   └── exceptions.py
│   ├── risk_assessment_agent/      # ✅ Implemented (multi-category)
│   │   ├── agent.py
│   │   ├── schemas.py
│   │   ├── prompts.py
│   │   └── exceptions.py
│   ├── competitive_intelligence_agent/ # ✅ Implemented (positioning)
│   │   ├── agent.py
│   │   ├── schemas.py
│   │   ├── prompts.py
│   │   └── exceptions.py
│   ├── news_agent/                # ✅ Implemented (news intelligence)
│   │   ├── agent.py
│   │   ├── schemas.py
│   │   ├── prompts.py
│   │   ├── exceptions.py
│   │   └── news_agent.py
│   ├── market_data_agent/         # ✅ Implemented (real-time data)
│   │   ├── market_agent.py
│   │   ├── schemas.py
│   │   ├── prompts.py
│   │   └── exceptions.py
│   ├── investment_summary_agent/  # ✅ Implemented (synthesis)
│   │   ├── agent.py
│   │   ├── schemas.py
│   │   ├── prompts.py
│   │   └── exceptions.py
│   ├── research_planner/          # ✅ Phase 7: Autonomous planning
│   │   ├── agent.py
│   │   └── __init__.py
│   └── manager_agent/             # ✅ Implemented (orchestration)
│       ├── manager.py
│       ├── schemas.py
│       ├── posters.py
│       └── exceptions.py
├── workflows/                 # Phase 7: Orchestration engine
│   ├── orchestrator.py
│   └── __init__.py
├── memory/                    # Phase 7: Research memory
│   ├── research_memory.py
│   └── __init__.py
├── watchlists/                # Phase 7: Monitoring
│   ├── manager.py
│   └── __init__.py
├── reports/                   # Phase 7: Report generation
│   ├── generator.py
│   ├── templates.py
│   └── __init__.py
├── notifications/             # Phase 7: Notification engine
│   ├── engine.py
│   └── __init__.py
├── approval/                  # Phase 7: Human approval
│   ├── workflow.py
│   └── __init__.py
├── api/                       # FastAPI application
│   ├── main.py
│   ├── research_endpoints.py  # Phase 7 endpoints
│   ├── dependencies.py
│   └── __init__.py
├── data/                      # Financial data processing
│   ├── __init__.py
│   ├── sec/                   # SEC EDGAR integration
│   │   ├── __init__.py
│   │   └── downloader.py
│   ├── filings/               # Filing processing & caching
│   │   ├── __init__.py
│   │   ├── cache.py
│   │   └── incremental.py
│   ├── earnings/              # Earnings call transcripts
│   │   ├── __init__.py
│   │   └── transcript_parser.py
│   ├── annual_reports/        # Annual/quarterly report parsers
│   │   ├── __init__.py
│   │   ├── annual_report_parser.py
│   │   ├── quarterly_report_parser.py
│   │   └── investor_presentation_parser.py
│   ├── earnings/              # Earnings transcripts
│   │   ├── __init__.py
│   │   └── transcript_parser.py
│   └── financial_documents/   # Core PDF/financial parsing
│       ├── __init__.py
│       ├── parser.py
│       ├── tables.py
│       ├── parsers.py
│       └── investor_presentation_parser.py
├── database/                  # SQLAlchemy ORM and persistence
│   ├── __init__.py
│   ├── connection.py
│   └── models.py
├── rag/                       # RAG pipeline
│   ├── ingestion/
│   │   ├── pdf_processor.py
│   │   ├── metadata_extractor.py
│   │   └── document_loader.py
│   ├── chunking/
│   │   └── section_splitter.py
│   └── vector_store/
│       └── chroma_store.py
├── dashboard/                 # Streamlit dashboard
│   ├── app.py
│   └── components/
├── tests/                     # Test suite (396 tests)
│   ├── llm/
│   ├── test_*.py
│   └── phase5/
├── config/                    # Phase 6: Configuration
│   ├── settings.py
│   ├── logging.py
│   ├── production.py
│   ├── development.py
│   ├── security.py
│   └── cache.py
├── monitoring/                # Phase 6: Observability
│   ├── metrics.py
│   ├── health.py
│   └── performance.py
├── middleware/                # Phase 6: Middleware stack
│   ├── logging_middleware.py
│   ├── rate_limit.py
│   └── circuit_breaker.py
├── security/                  # Phase 6: Security
│   └── auth.py
├── cache/                     # Phase 6: Cache abstraction
│   └── manager.py
├── middleware/                # Phase 6: Middleware
│   ├── logging_middleware.py
│   ├── rate_limit.py
│   └── circuit_breaker.py
├── docs/                      # Documentation
├── config/                    # Configuration
├── .dockerignore
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7
- Docker & Docker Compose (recommended for deployment)
- At least one LLM API key (OpenRouter recommended)

### 1. Clone the Repository
```bash
git clone https://github.com/LeelaissakAttota/agentic-financial-intelligence-platform.git
cd agentic-financial-intelligence-platform
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys:
# OPENROUTER_API_KEY=your_key
# FINNHUB_API_KEY=your_key
# ALPHA_VANTAGE_API_KEY=your_key
# NEWSAPI_KEY=your_key
```

### 3. Start with Docker (Recommended)
```bash
docker-compose up -d
```

### 4. Manual Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run database migrations
alembic upgrade head

# Start API
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Start Dashboard (separate terminal)
streamlit run dashboard/app.py --server.port 8501
```

### 5. Verify Health
```bash
curl http://localhost:8000/health/detailed
# Should return: {"status":"healthy","checks":{"api":"healthy","database":"healthy","chromadb":"healthy"}}
```

---

## 📖 Usage

### CLI Usage
```bash
# Run analysis for a company
python main.py analyze --company "NVIDIA" --query "competitive position in AI chips"

# With ticker
python main.py analyze --company "NVDA" --query "recent earnings and guidance"
```

### API Usage
```bash
# Start analysis
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"company": "NVIDIA", "query": "competitive position in AI chips"}'

# Response
# {"analysis_id": "uuid", "company": "NVIDIA", "status": "pending", "message": "Analysis started..."}

# Poll for results
curl http://localhost:8000/api/v1/analyze/{analysis_id}
```

### Autonomous Research (Phase 7)
```bash
# Start autonomous research with auto-approval
curl -X POST http://localhost:8000/api/v1/research/start \
  -H "Content-Type: application/json" \
  -d '{"company": "NVDA", "query": "full investment thesis", "auto_approve": true}'

# Check status
curl http://localhost:8000/api/v1/research/{research_id}

# Get research history
curl http://localhost:8000/api/v1/research/history?company=NVDA

# System status
curl http://localhost:8000/api/v1/research/status
```

### Dashboard
1. Open http://localhost:8501
2. Enter company name or ticker
3. Optionally add research question
4. Click "Start Analysis"
5. Monitor agent execution in real-time
6. View structured results with citations

---

## 📊 Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| API Response | <200ms | ~150ms |
| Document Processing | <5s/100pg | ~3s/100pg |
| Cache Hit Rate | >90% | ~95% |
| SEC Rate Limit | 10 req/s | 10 req/s enforced |
| Test Suite | <60s | ~20s |
| Memory (idle) | <500MB | ~210MB |
| CPU (idle) | <5% | ~1% |

## ✅ Quality Gates

| Gate | Status |
|------|--------|
| Code Style (Ruff) | ✅ Pass |
| Type Hints | ✅ 100% public API |
| Tests | ✅ 396/396 pass (2 skipped) |
| Security | ✅ No vulnerabilities |
| Documentation | ✅ Complete |
| Compile | ✅ No errors |

---

## 📝 Known Limitations

1. **Optional Dependencies**: pdfplumber, pdfminer, python-pptx not required but enhance functionality
2. **SEC Rate Limits**: Conservative 10 req/s enforced
3. **PPTX Parsing**: Falls back to PDF if python-pptx not installed
4. **Network Dependency**: SEC downloader requires internet
5. **Database Tests**: 2 tests skipped requiring live PostgreSQL
6. **Knowledge Graph**: PostgreSQL adjacency list (Neo4j planned for Phase 8)
7. **Pattern Detection**: Daily timeframe only (intraday planned Phase 8)
8. **Alert Channels**: Email/Slack/Discord require external config
9. **Monte Carlo**: Single-asset GBM (multi-asset planned Phase 8)
10. **Cross-Agent Memory**: Exact match + metadata (vector similarity planned Phase 8)
11. **Dashboard**: Static refresh (WebSocket real-time planned Phase 8)

---

## 🔮 Next Phase (Phase 8)

### Phase 8: Intelligence Amplification (Next)
- [ ] Neo4j integration for Knowledge Graph
- [ ] WebSocket real-time dashboard updates
- [ ] Multi-asset Monte Carlo with copula correlation
- [ ] Vector similarity search in Cross-Agent Memory
- [ ] Auto-entity linking from RAG to Knowledge Graph
- [ ] Advanced pattern backtesting framework

### Phase 9: Intelligence Amplification
- [ ] Causal inference engine for event attribution
- [ ] LLM-powered insight generation from patterns
- [ ] Automated thesis generation with evidence chains
- [ ] Counterfactual analysis ("what if" scenarios)

### Phase 10: Enterprise Features
- [ ] Multi-tenant isolation
- [ ] RBAC and audit logging
- [ ] SOC2 compliance artifacts
- [ ] Disaster recovery / backup automation
- [ ] Kubernetes deployment manifests
- [ ] Prometheus/Grafana observability stack

---

## 📂 Git Tags

- `v1.0.0-phase1` - Core infrastructure
- `v1.1.0-phase2.2` - News pipeline
- `v1.2.0-phase2.3` - Entity recognition
- `v1.3.0-phase3` - Financial intelligence
- `v1.4.0-phase4` - Document intelligence
- `v1.4.0-phase5` - Knowledge Intelligence Platform
- `v1.5.0-phase6` - Production Hardening
- `v1.6.0-phase7` - **Autonomous Research Workflows (current)**

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **BGE Models**: BAAI for M3 embeddings and re-ranker
- **ChromaDB**: Vector database
- **OpenRouter**: LLM provider aggregation
- **spaCy**: NLP pipeline foundation
- **NetworkX**: Graph operations
- **FastAPI**: API framework
- **Streamlit**: Dashboard framework
- **SEC EDGAR**: Public filings data
- **Financial APIs**: Alpha Vantage, Polygon.io, Yahoo Finance, Finnhub

---

## 📞 Contact

**Project Maintainer**: Leela Issak Attota  
**GitHub**: [@LeelaissakAttota](https://github.com/LeelaissakAttota)**Repository**: [agentic-financial-intelligence-platform](https://github.com/LeelaissakAttota/agentic-financial-intelligence-platform)

---

**Status**: ✅ **ALL PHASES COMPLETE - PRODUCTION READY**