# Agentic Financial Intelligence Platform

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Build](https://img.shields.io/badge/Build-Passing-brightgreen.svg)
![Tests](https://img.shields.io/badge/Tests-396%20Passed-success.svg)
![Coverage](https://img.shields.io/badge/Coverage-92%25-yellow.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)

A production-grade, multi-agent AI system that automates end-to-end equity research workflows with institutional-grade quality, speed, and auditability.

---

## 🎯 Overview

The Agentic Financial Intelligence Platform transforms financial research from a manual, hours-long process into an automated, minutes-long workflow using **14 specialized AI agents** orchestrated by an **AI Copilot** with natural language interaction.

### Key Capabilities

| Capability | Description |
|------------|-------------|
| **AI Financial Copilot** | Natural language chat with multi-turn conversations, streaming responses, and autonomous planning |
| **Autonomous Research** | Dynamic LLM-driven planning with 4 complexity levels, 14 agent types, and parallel execution |
| **Document Intelligence** | RAG-powered analysis of SEC filings (16 form types), earnings transcripts, and analyst reports |
| **News Intelligence** | 6 news providers, 7-layer NLP pipeline (28 entity types, 35+ relationships), real-time aggregation |
| **Market Data** | Real-time quotes, technical indicators (RSI, MACD, Bollinger), fundamentals |
| **Risk Analytics** | VaR/CVaR, Monte Carlo (10K paths), stress testing, multi-category risk |
| **Portfolio Management** | Positions, orders, 5 rebalancing strategies, risk metrics |
| **Knowledge Graph** | 14 node types, 28 relationships, graph algorithms (PageRank, Louvain, centrality) |
| **Pattern Detection** | 10 pattern types with backtesting |
| **Advanced Analytics** | Fama-French 3/5-factor, Monte Carlo, Brinson attribution, scenario analysis |
| **Alert Engine** | 30+ alert types, 5 notification channels, deduplication, cooldown |
| **Report Generation** | 8 report types, 3 formats (Markdown/HTML/JSON), Jinja2 templates |
| **Human Approval** | 6 action types, sequential chains, escalation, delegation, full audit trail |
| **Cross-Agent Memory** | 9 memory types, 5 scopes, supersession, pgvector-ready |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SYSTEM ARCHITECTURE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  User Interfaces:  CLI │ REST API (FastAPI) │ Streamlit Dashboard           │
├─────────────────────────────────────────────────────────────────────────────┤
│  Phase 9: Enterprise Knowledge Graph (Neo4j) & Semantic Intelligence       │
├─────────────────────────────────────────────────────────────────────────────┤
│  Phase 8: AI Copilot Orchestration (Natural Language → Plan → Execute)     │
├─────────────────────────────────────────────────────────────────────────────┤
│  Phase 7: Workflow Orchestration (Topological Sort → Parallel Waves)       │
├─────────────────────────────────────────────────────────────────────────────┤
│  14 Specialized Agents (Financial Doc, Sentiment, Risk, Competitive,       │
│   News, Market Data, Investment Summary, Knowledge Graph, Portfolio,       │
│   Patterns, Alerts, Analytics, Historical, Cross-Agent Memory)             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Supporting Infrastructure: LLM Orchestration (9 models), Tool Registry    │
│  (15 tools), Collaboration Layer (consensus), Decision Engine (6-step),    │
│  Explainability (evidence/alternatives/risks), Enhanced Memory (5 scopes)  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Data Layer: PostgreSQL (27+ tables) │ ChromaDB (Vector) │ Redis (Cache)  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Docker Desktop 4.30+
- Python 3.11+ (for local development)
- OpenRouter API key (for LLM access)

### Using Docker (Recommended)
```bash
# 1. Clone repository
git clone https://github.com/LeelaissakAttota/agentic-financial-intelligence-platform.git
cd agentic-financial-intelligence-platform

# 2. Configure environment
cp .env.example .env
# Edit .env with your OPENROUTER_API_KEY

# 3. Start all services
docker-compose up -d --build

# 4. Verify health
curl http://localhost:8000/health/detailed
# Open http://localhost:8501 for Streamlit dashboard

# 5. Run tests
docker-compose exec api pytest tests/ -q
```

### Local Development
```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Start infrastructure
docker-compose up -d postgres chromadb redis

# 5. Run database migrations
alembic upgrade head

# 6. Start API server
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 7. Start dashboard (separate terminal)
streamlit run dashboard/app.py --server.port 8501
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Architecture Overview](docs/architecture/01-system-overview.md) | Complete system architecture |
| [Agent Architecture](docs/architecture/02-agent-architecture.md) | 14-agent system design |
| [RAG Pipeline](docs/architecture/03-rag-pipeline.md) | Document ingestion & retrieval |
| [Database Schema](docs/architecture/04-database.md) | 27+ tables, indexes, relationships |
| [API Reference](docs/architecture/05-api.md) | 40+ endpoints with examples |
| [Dashboard Guide](docs/architecture/06-dashboard.md) | Streamlit & Copilot dashboards |
| [Security Architecture](docs/architecture/07-security.md) | Auth, RBAC, injection prevention |
| [Deployment Guide](docs/architecture/08-deployment.md) | Docker, Kubernetes, CI/CD |
| [Workflows](docs/architecture/09-workflows.md) | Autonomous research orchestration |
| [Memory System](docs/architecture/10-memory.md) | Three-generation memory architecture |

### Diagrams
All diagrams are in Mermaid format (`.mmd`) in `docs/diagrams/`:
- [Overall Architecture](docs/diagrams/overall-architecture.mmd)
- [Agent Architecture](docs/diagrams/agent-architecture.mmd)
- [Workflow](docs/diagrams/workflow.mmd)
- [Knowledge Graph](docs/diagrams/knowledge-graph.mmd)
- [Database](docs/diagrams/database.mmd)
- [RAG Pipeline](docs/diagrams/rag-pipeline.mmd)
- [API Flow](docs/diagrams/api-flow.mmd)
- [Dashboard](docs/diagrams/dashboard.mmd)
- [Deployment](docs/diagrams/deployment.mmd)

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -q

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test suites
pytest tests/test_database.py -v
pytest tests/phase7/ -v
pytest tests/phase8/ -v

# Run linting
ruff check .
black --check .
mypy .
```

**Current Status**: 396 tests passing, 2 skipped (API credential tests), 0 failures

---

## 🔧 Configuration

### Environment Variables (`.env`)
```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=financial_research
POSTGRES_PASSWORD=your_password
POSTGRES_DB=financial_research

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# LLM Provider (OpenRouter)
OPENROUTER_API_KEY=«redacted:sk-...»

# JWT Keys (generate with: openssl genrsa -out private.pem 2048)
JWT_PRIVATE_KEY_PATH=./keys/private.pem
JWT_PUBLIC_KEY_PATH=./keys/public.pem

# Optional: Notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@yourdomain.com
SMTP_PASSWORD=app_password
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

---

## 🔒 Security

- **Authentication**: JWT RS256 + API Keys (bcrypt)
- **Authorization**: RBAC (Admin/Analyst/Viewer/API_Only)
- **Rate Limiting**: Token bucket + Redis sliding window
- **Circuit Breakers**: 3-state with auto-recovery
- **Injection Prevention**: SQL injection detection, Prompt injection detection
- **Security Headers**: CSP, HSTS, X-Frame, Referrer-Policy
- **Audit Logging**: Structured JSON with correlation IDs

---

## 📊 Monitoring

- **Health Endpoints**: `/health`, `/health/live`, `/health/ready`, `/health/detailed`
- **Metrics**: Prometheus at `/metrics` (30+ metrics)
- **Key Metrics**: API latency, agent execution, LLM tokens/cost, cache hit rate, DB connections

---

## 🐳 Docker Services

| Service | Port | Description |
|---------|------|-------------|
| API | 8000 | FastAPI REST API |
| Streamlit | 8501 | Research Dashboard |
| PostgreSQL | 5432 | Primary Database |
| ChromaDB | 8001 | Vector Store |
| Redis | 6379 | Cache & Sessions |
| Neo4j | 7474/7687 | Knowledge Graph (optional) |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests and linting (`make test lint`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

---

## 🙋 Support

- **Issues**: [GitHub Issues](https://github.com/LeelaissakAttota/agentic-financial-intelligence-platform/issues)
- **Discussions**: [GitHub Discussions](https://github.com/LeelaissakAttota/agentic-financial-intelligence-platform/discussions)
- **Security**: See [SECURITY.md](SECURITY.md) for vulnerability reporting

---

## 🏷️ Version History

| Version | Date | Description |
|---------|------|-------------|
| **v2.0.0-phase9** | 2026-07-18 | **Autonomous Financial Intelligence Platform v2.0** - Neo4j Knowledge Graph, Real-Time Intelligence, Semantic Intelligence, Autonomous Research, Advanced Portfolio, Predictive Intelligence, Enterprise Dashboard v2, Production Event System |
| v1.7.0-phase8 | 2026-07-18 | AI Copilot & Autonomous Decision Intelligence |
| v1.6.0-phase7 | 2026-07-18 | Autonomous Research Workflows |
| v1.5.0-phase6 | 2026-07-18 | Production Hardening |
| v1.4.0-phase5 | 2026-07-18 | Knowledge Intelligence Platform |
| v1.4.0-phase4 | 2026-07-17 | Financial Documents Intelligence |
| v1.3.0-phase3 | 2026-07-17 | Real Financial Intelligence |
| v1.2.0-phase2.3 | 2026-07-17 | Entity Recognition |
| v1.1.0-phase2.2 | 2026-07-16 | News Intelligence |
| v1.0.0-phase1 | 2026-07-13 | Core Infrastructure |

---

*Built with ❤️ for institutional-grade financial research automation*