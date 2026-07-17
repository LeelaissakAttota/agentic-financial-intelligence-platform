# Agentic Financial Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-319%20passing-brightgreen.svg)](https://github.com/LeelaissakAttota/agentic-financial-intelligence-platform/actions)
[![Implemented Agents](https://img.shields.io/badge/Implemented%20Agents-7/7-green.svg)](#implementation-status)
[![Phase](https://img.shields.io/badge/Phase-2.3%20Complete-blue.svg)](#phase-23-financial-entity-recognition)

> **An AI-powered financial research system that automates financial document analysis, sentiment analysis, risk assessment, competitive intelligence, news intelligence, market data analysis, and investment synthesis through a multi-agent architecture with Retrieval-Augmented Generation (RAG) capabilities.**

---

## 🎯 Project Overview

### What the Project Does
The Agentic Financial Intelligence Platform is an implemented system that automates specific aspects of financial research workflows. It currently provides:
- **Financial Document Analysis**: RAG-powered analysis of SEC filings (10-K, 10-Q), earnings transcripts, and analyst reports
- **Sentiment Analysis**: Multi-source sentiment scoring from news, social media, and analyst opinions
- **Risk Assessment**: Multi-category risk analysis (market, credit, operational, liquidity)
- **Competitive Intelligence**: Peer comparison and positioning analysis
- **News Intelligence**: Financial news aggregation, sentiment, event detection, and entity extraction
- **Market Data Analysis**: Real-time market data, technical indicators, and fundamentals
- **Investment Summary**: Multi-agent insight synthesis and thesis formulation
- **Persistent Storage**: Research history and agent execution tracking via PostgreSQL
- **Financial Entity Recognition**: 7-layer hybrid NLP pipeline for entity extraction (28 types, 100+ sub-types, 35+ relationships)
- **Flexible LLM Integration**: OpenRouter primary with fallback options
- **Multiple Interfaces**: CLI, REST API, and Streamlit dashboard

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
    C --> J[RAG Knowledge Base]
    J --> K[Vector Search (BGE-M3)]
    K --> L[Re-ranking (BGE-Reranker)]
    L --> M[Cited Answers with Sources]
    M --> N[Structured Financial Analysis]
    N --> O[Final Output]
    
    B -.-> P[Financial Entity Recognition Engine]:::new
    P --> Q[7-Layer Hybrid NLP Pipeline]
    Q --> R[Rule-based → Dictionary → Local NER → LLM Validation → Resolution → Relationships → Confidence]
    
    classDef implemented fill:#d4edda,stroke:#28a745;
    classDef new fill:#e3f2fd,stroke:#1565c0;
    classDef planned fill:#f8d7da,stroke:#dc3545;
    
    style A fill:#e3f2fd,stroke:#1565c0
    style B fill:#f3e5f5,stroke:#7b1fa2
    style C fill:#fff3e0,stroke:#e65100
    style D fill:#e8f5e9,stroke:#2e7d32
    style E fill:#fce4ec,stroke:#c2185b
    style G fill:#e3f2fd,stroke:#1565c0
    style H fill:#fff3e0,stroke:#e65100
    style I fill:#e8f5e9,stroke:#2e7d32
    style J fill:#f3e5f5,stroke:#7b1fa2
    style K fill:#fff3e0,stroke:#e65100
    style L fill:#e8f5e9,stroke:#2e7d32
    style M fill:#fff3e0,stroke:#e65100
    style N fill:#e8f5e9,stroke:#2e7d32
    style O fill:#fce4ec,stroke:#c2185b
    style P fill:#e3f2fd,stroke:#1565c0
    style Q fill:#e3f2fd,stroke:#1565c0
    style R fill:#e3f2fd,stroke:#1565c0
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
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Implemented Agents (7/7):                                      │
│  • Financial Document Agent  ✅ (RAG-based financial analysis)  │
│  • Sentiment Analysis Agent  ✅ (Multi-source sentiment)        │
│  • Risk Assessment Agent     ✅ (Multi-category risk)           │
│  • Competitive Intelligence  ✅ (Peer comparison)               │
│  • News Intelligence Agent   ✅ (Financial news processing)     │
│  • Market Data Agent         ✅ (Real-time market data)         │
│  • Investment Summary Agent  ✅ (Multi-agent synthesis)         │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Financial Entity Recognition Engine (Phase 2.3)                │
│  • 7-Layer Hybrid NLP Pipeline                                  │
│  • 28 Entity Types, 100+ Sub-Types, 35+ Relationship Types      │
│  • 100+ Built-in Financial Entities                             │
│  • 60+ Regex Patterns                                           │
│  • spaCy Local NER + Dictionary Lookup + LLM Validation         │
│  • Entity Resolution (Ticker/Company/Alias)                     │
│  • Relationship Graph + Confidence Scoring                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Supporting Systems:                                            │
│  • LLM Abstraction Layer (OpenRouter primary)                  │
│  • RAG System (BGE-M3 embeddings + ChromaDB)                   │
│  • Database Persistence (PostgreSQL + SQLAlchemy)              │
│  • REST API (FastAPI)                                          │
│  • Web Dashboard (Streamlit)                                   │
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

### 5. News Intelligence Agent (Phase 2.2)
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
   - **Financial Document Agent**: Retrieves and analyzes SEC filings, earnings reports using RAG
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

### Data Flow Example
```
User: "Analyze NVIDIA's competitive position in AI chips"
      ↓
ManagerAgent: Creates execution plan
      ↓
Financial Document Agent: 
   - Retrieves NVIDIA 10-K, 10-Q, earnings transcripts
   - Answers financial questions via RAG
   - Returns: Revenue growth, margins, ratios with citations
      ↓
Sentiment Analysis Agent:
   - Analyzes recent news, social media, analyst reports
   - Applies source weighting and divergence detection
   - Returns: Sentiment distribution, key drivers, confidence
      ↓
Risk Assessment Agent:
   - Evaluates market, credit, operational, liquidity risks
   - Provides VaR/CVaR, stress test results
   - Returns: Risk scores, factors, mitigation suggestions
      ↓
Competitive Intelligence Agent:
   - Identifies peers (AMD, Intel, etc.)
   - Benchmarks financial and operational metrics
   - Returns: Competitive positioning, advantages/disadvantages
      ↓
News Intelligence Agent:
   - Aggregates from 6 providers (Yahoo, Finnhub, Alpha Vantage, NewsAPI, RSS, Google News)
   - Deduplicates, sentiment scores, entity extracts, event detects
   - Returns: Key events, sentiment trends, entity mentions
      ↓
Market Data Agent:
   - Fetches real-time quotes, fundamentals, historical prices
   - Calculates RSI, SMA, MACD, Bollinger Bands
   - Returns: Technical analysis, valuation, market trends
      ↓
Investment Summary Agent:
   - Synthesizes all agent outputs
   - Formulates investment thesis
   - Returns: Recommendation, price target, catalyst timeline
      ↓
ManagerAgent: Aggregates results, stores in database
      ↓
User Receives: Structured JSON with all agent outputs and metadata
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
| **Testing Framework** | Pytest | 319 unit tests with >90% coverage |
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
- ✅ **Automated Testing**: 319 unit tests passing (>90% coverage)
- ✅ **Docker Deployment**: Containerized services with docker-compose orchestration

### Phase 2.3 - Financial Entity Recognition
- ✅ **7-Layer Hybrid NLP Pipeline**: Rule-based → Dictionary → Local NER → LLM Validation → Entity Resolution → Relationship Building → Confidence Scoring
- ✅ **28 Entity Types**: COMPANY, TICKER, PERSON, MONEY, PERCENTAGE, DATE, INDEX, CURRENCY, COMMODITY, CRYPTOCURRENCY, SECTOR, REGULATOR, EXCHANGE, FINANCIAL_INSTRUMENT, ECONOMIC_INDICATOR, CENTRAL_BANK, GOVERNMENT_ENTITY, LEGAL_ENTITY, EVENT, LOCATION, ORGANIZATION, PRODUCT, TECHNOLOGY, METRIC, COUNTRY, CITY, INDUSTRY, FUND
- ✅ **100+ Sub-Types**: PUBLIC_COMPANY, PRIVATE_COMPANY, SUBSIDIARY, HEDGE_FUND, US_EQUITY, ETF, CEO, CFO, REVENUE, EBITDA, EPS, EARNINGS_DATE, FINANCIAL_QUARTER, EARNINGS_RELEASE, MERGER_ACQUISITION, IPO, etc.
- ✅ **35+ Relationship Types**: HAS_CEO, HAS_TICKER, LISTED_ON, HEADQUARTERED_IN, COMPETES_WITH, ACQUIRED, SUBSIDIARY_OF, WORKS_AT, FOUNDED, TRADES_ON, COMPONENT_OF, DENOMINATED_IN, etc.
- ✅ **100+ Built-in Entities**: Apple, Microsoft, NVIDIA, Tesla, Amazon, Google, Meta, Berkshire Hathaway, JPMorgan, Goldman Sachs, Tim Cook, Satya Nadella, Jensen Huang, Elon Musk, Warren Buffett, Jamie Dimon, NASDAQ, NYSE, LSE, S&P 500, NASDAQ 100, VIX, BTC, ETH, GOLD, SILVER, CRUDE OIL, etc.
- ✅ **60+ Regex Patterns**: Tickers, money amounts, percentages, dates, financial metrics, events
- ✅ **Entity Resolution**: Ticker→Company, Company→Canonical, Alias→Canonical
- ✅ **Relationship Graph**: NetworkX-based queryable entity relationship graph
- ✅ **Confidence Engine**: 7-signal weighted scoring (method, dictionary, LLM, context, cross-ref, position, duplicates)

### Planned Features (Future Implementation)
- ⏸️ **Parallel Execution**: Enable concurrent agent execution where dependencies allow
- ⏸️ **Enhanced Context Passing**: Share relevant outputs between agents
- ⏸️ **Dynamic Task Planning**: LLM-driven agent sequencing based on query complexity
- ⏸️ **Advanced RAG**: Cross-agent knowledge sharing via vector embeddings
- ⏸️ **Knowledge Graph**: Neo4j-based relationship tracking for insights
- ⏸️ **MLOps Features**: Model drift detection, A/B testing, continuous learning
- ⏸️ **User Feedback System**: Rating and correction mechanisms for improvement

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
│   └── versions/
├── api/                       # FastAPI application
│   ├── main.py                # API endpoints and middleware
│   └── dependencies.py        # Dependency injection
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
│   └── manager_agent/            # ✅ Implemented (orchestration)
│       ├── manager.py            # Core orchestration logic
│       ├── schemas.py            # Task types and data models
│       ├── posters.py
│       └── exceptions.py
├── database/                  # SQLAlchemy ORM and persistence
│   ├── __init__.py             # CRUD operations and persistence logic
│   ├── connection.py           # Engine and session management
│   └── models.py               # Company, Report, AgentRun tables
├── dashboard/                 # Streamlit web interface
│   └── app.py                 # Main dashboard application
├── data/                      # Data storage directories
│   ├── reports/               # Generated research reports (JSON/MD)
│   └── processed/             # ChromaDB and embedding caches
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md        # Detailed system architecture
│   ├── AGENTS.md              # Agent specifications
│   ├── WORKFLOW.md            # Detailed workflow explanation
│   ├── INSTALLATION.md        # Installation guide
│   └── PROJECT_OVERVIEW.md    # Project overview and motivation
├── llm/                       # LLM abstraction layer
│   ├── __init__.py
│   ├── base_client.py         # Shared retry, JSON extraction, cost tracking
│   ├── openrouter_client.py   # Primary LLM provider (used in prod)
│   ├── claude_client.py       # Anthropic Claude integration
│   ├── model_registry.py      # Dynamic model resolution system
│   ├── pricing.py             # Token cost calculation
│   ├── json_utils.py          # Robust LLM response parsing
│   ├── token_tracker.py       # Usage tracking
│   ├── llm_provider.py        # Abstract base class
│   ├── exceptions.py          # Custom exception hierarchy
│   ├── router.py              # Legacy router (deprecated)
│   └── model_router.py        # Legacy router (deprecated)
├── rag/                       # Retrieval-Augmented Generation system
│   ├── __init__.py
│   ├── embeddings/            # BGE-M3 embedding generation
│   ├── chunking/              # Section-aware document splitting
│   └── ingest/                # Document processing pipeline
├── data/news/                 # News intelligence pipeline (Phase 2.2)
│   ├── __init__.py
│   ├── schemas.py             # NewsArticle, NewsSummary, NewsCategory, etc.
│   ├── providers.py           # 6 providers + composite with fallback
│   ├── cache.py               # 10-minute TTL cache
│   └── adapter.py             # Bridge to NewsAgent
├── data/news/entity_recognition/  # Financial Entity Recognition (Phase 2.3)
│   ├── __init__.py
│   ├── schemas.py             # EntityType, EntitySubType, RelationshipType, Entity, etc.
│   ├── dictionary.py          # FinancialDictionary + 100+ built-in entities
│   ├── rule_based_extractor.py # 60+ regex patterns
│   ├── local_ner.py           # spaCy NER with financial hints
│   ├── llm_validator.py       # LLM validation for low-confidence entities
│   ├── ticker_resolver.py     # Ticker → canonical company resolution
│   ├── company_resolver.py    # Company name → canonical resolution
│   ├── alias_resolver.py      # Alias → canonical resolution
│   ├── relationship_builder.py # 35+ relationship types
│   ├── confidence_engine.py   # 7-signal confidence scoring
│   ├── entity_graph.py        # NetworkX relationship graph
│   └── entity_extractor.py    # 7-layer pipeline orchestrator
├── tests/                     # Comprehensive test suite
│   ├── __init__.py
│   ├── llm/                   # LLM layer tests
│   ├── agents/                # Agent implementation tests
│   ├── database/              # Database integration tests
│   └── api/                   # API endpoint tests
├── main.py                    # Command-line interface entry point
├── README.md                  # This file
└── LICENSE                    # MIT License
```

---

## 🚀 Installation Guide

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (recommended for deployment)
- API key for at least one LLM provider (OpenRouter recommended)

### Quick Start (Docker Recommended)
```bash
# 1. Clone the repository
git clone https://github.com/LeelaissakAttota/agentic-financial-intelligence-platform.git
cd agentic-financial-intelligence-platform

# 2. Configure environment (copy template and add your keys)
cp .env.example .env
# Edit .env with your API keys:
# OPENROUTER_API_KEY=your_key_here
# FINNHUB_API_KEY=your_key_here
# ALPHA_VANTAGE_API_KEY=your_key_here
# NEWSAPI_KEY=your_key_here

# 3. Start all services
docker-compose up -d

# 4. Verify health
curl http://localhost:8000/health/detailed
# Should return: {"status":"healthy","checks":{"api":"healthy","database":"healthy","chromadb":"healthy"}}

# 5. Access interfaces
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Dashboard: http://localhost:8501
```

### Manual Development Setup
```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. Start PostgreSQL and Redis (or use docker-compose for just these)
docker-compose up -d postgres redis chromadb

# 4. Run database migrations
alembic upgrade head

# 5. Start API server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 6. Start dashboard (separate terminal)
streamlit run dashboard/app.py
```

### Environment Variables
```env
# Required
OPENROUTER_API_KEY=your_openrouter_key

# Optional - Market Data
FINNHUB_API_KEY=your_finnhub_key
ALPHA_VANTAGE_API_KEY=your_alphavantage_key

# Optional - News
NEWSAPI_KEY=your_newsapi_key

# Database (auto-configured in Docker)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/financial_research
REDIS_URL=redis://localhost:6379/0
CHROMADB_HOST=localhost
CHROMADB_PORT=8000
```

---

## 📖 Usage

### CLI Usage
```bash
# Run analysis for a company
python main.py analyze --company "NVIDIA" --query "competitive position in AI chips"

# Or with ticker
python main.py analyze --ticker "NVDA" --query "recent earnings and guidance"

# View help
python main.py --help
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

# Health check
curl http://localhost:8000/health/detailed
```

### Dashboard Usage
1. Open http://localhost:8501
2. Enter company name or ticker
3. Optionally add research question
4. Click "Start Analysis"
5. Monitor agent execution in real-time
6. View structured results with citations

---

## 📊 Implementation Status

| Phase | Component | Status | Tests |
|-------|-----------|--------|-------|
| **Phase 1** | Core Infrastructure | ✅ Complete | 247 tests |
| | LLM Abstraction Layer | ✅ Complete | |
| | Model Registry & Pricing | ✅ Complete | |
| | RAG Foundation (BGE-M3 + ChromaDB) | ✅ Complete | |
| | PostgreSQL + SQLAlchemy | ✅ Complete | |
| | FastAPI + Streamlit | ✅ Complete | |
| | Docker Compose | ✅ Complete | |
| **Phase 2.1** | Market Data Agent | ✅ Complete | 23 tests |
| | Multi-provider (Yahoo, Alpha Vantage, Finnhub) | ✅ Complete | |
| | Technical Indicators (RSI, SMA, MACD, BB) | ✅ Complete | |
| | Composite Provider with Fallback | ✅ Complete | |
| **Phase 2.2** | News Intelligence Agent | ✅ Complete | 35 tests |
| | 6 News Providers | ✅ Complete | |
| | Fallback Chain | ✅ Complete | |
| | Deduplication | ✅ Complete | |
| | Sentiment + Event Detection + Entity Extraction | ✅ Complete | |
| **Phase 2.3** | Financial Entity Recognition | ✅ Complete | Covered by 319 total |
| | 7-Layer Hybrid NLP Pipeline | ✅ Complete | |
| | 28 Entity Types, 100+ Sub-Types | ✅ Complete | |
| | 35+ Relationship Types | ✅ Complete | |
| | 100+ Built-in Entities | ✅ Complete | |
| | 60+ Regex Patterns | ✅ Complete | |
| | Entity Resolution (Ticker/Company/Alias) | ✅ Complete | |
| | Relationship Graph (NetworkX) | ✅ Complete | |
| | Confidence Engine (7 signals) | ✅ Complete | |

**Total Tests: 319 passing** | **Coverage: >90%** | **All Agents: 7/7 Implemented**

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Detailed system architecture |
| [AGENTS.md](docs/AGENTS.md) | Agent specifications and interfaces |
| [WORKFLOW.md](docs/WORKFLOW.md) | Detailed workflow explanation |
| [INSTALLATION.md](docs/INSTALLATION.md) | Installation guide |
| [PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) | Project overview and motivation |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [ROADMAP.md](ROADMAP.md) | Future development roadmap |
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | Current project status |

---

## 🗺️ Roadmap

See [ROADMAP.md](ROADMAP.md) for detailed future plans.

### Phase 3: Knowledge Persistence & Advanced Analytics (Planned)
- **3.1**: Knowledge Graph Persistence (Neo4j/PostgreSQL)
- **3.2**: Cross-Agent Knowledge Sharing via Vector Embeddings
- **3.3**: Historical Pattern Recognition & Trend Analysis
- **3.4**: Alerting & Real-time Monitoring System

### Phase 4: MLOps & Production Hardening (Planned)
- **4.1**: Model Drift Detection & Automated Retraining
- **4.2**: A/B Testing Framework for Agent Variants
- **4.3**: Continuous Learning from User Feedback
- **4.4**: Advanced Caching & Performance Optimization

### Phase 5: Enterprise Features (Planned)
- **5.1**: Multi-tenant Architecture
- **5.2**: Role-Based Access Control
- **5.3**: Audit Logging & Compliance Reporting
- **5.4**: Custom Agent Marketplace

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest tests/ --ignore=tests/test_claude_connection.py --ignore=tests/test_openrouter_connection.py`)
5. Ensure code quality (`black . && ruff . && mypy .`)
6. Commit with conventional commits (`feat:`, `fix:`, `docs:`, etc.)
7. Push to your fork
8. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **BAAI** for BGE-M3 and BGE-Reranker models
- **BAAI** for financial embedding models
- **Hugging Face** for transformer infrastructure
- **ChromaDB** for vector database
- **FastAPI** for API framework
- **Streamlit** for dashboard
- **SQLAlchemy** for ORM
- **OpenRouter** for unified LLM API
- **NetworkX** for graph operations
- **spaCy** for NLP pipeline

---

## 📞 Contact

**Project Maintainer**: Leelaissak Attota  
**GitHub**: [@LeelaissakAttota](https://github.com/LeelaissakAttota)  
**Repository**: [agentic-financial-intelligence-platform](https://github.com/LeelaissakAttota/agentic-financial-intelligence-platform)

---

*Last Updated: 2026-07-17 | Version: v1.2.0-phase2.3*