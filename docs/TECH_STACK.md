# PHASE 3 — Technology Stack (Testing Phase)

| Layer | Choice | Why (for THIS testing phase specifically) |
|---|---|---|
| **Language** | Python 3.12 | Matches your existing JARVIS OS / trading system stack, so utility code (settings loader, logging, DB models) can be shared/copy-pasted later. |
| **AI Model** | Claude API — `claude-sonnet-4-6` for synthesis agents (Manager, Risk, Investment Summary), `claude-haiku-4-5` for lighter/high-volume tasks (News summarization, Market narrative) | Sonnet gives the best reasoning quality for multi-source synthesis; Haiku keeps per-article news summarization cheap and fast during repeated test runs. Mirrors the two-tier pattern already used in your trading system's Claude AI Coordinator. |
| **LLM Framework** | Anthropic Python SDK directly, wrapped in `llm/claude_client.py` | For a testing phase, a thin direct wrapper is easier to debug than a heavy abstraction layer — you can see exact prompts/tokens/costs per call. |
| **Agent Framework** | LangGraph | You're already using LangGraph in the Deep Research Agent and Job Apply Agent — reusing it here keeps the orchestration mental model (nodes = agents, edges = handoffs, state = shared JSON bundle) consistent across your whole portfolio. |
| **Orchestration pattern support** | LangChain (selectively) | Only for its document loaders / text splitters in the RAG pipeline — not used as the primary agent framework (LangGraph owns that role) to avoid framework overlap/confusion. |
| **RAG Framework** | LangChain `RecursiveCharacterTextSplitter` + custom `rag/retriever.py` | Minimal, inspectable pipeline — enough to validate retrieval quality without pulling in a heavier RAG framework this early. |
| **Vector Database** | ChromaDB (local, persistent) | Zero external service to stand up during testing; matches the ChromaDB usage already in your JARVIS OS memory layer and Research Agent v2.0 Second Brain — one more consistent building block across projects. FAISS considered but ChromaDB's built-in persistence + metadata filtering wins for this use case. |
| **Relational Database** | PostgreSQL | Matches your production stack (JARVIS OS's 5-database strategy already uses PostgreSQL); SQLite is acceptable as a same-schema drop-in for CI-only test runs to avoid needing Postgres running in every environment. |
| **API Framework** | FastAPI | Async-native (works cleanly with LangGraph's async nodes), auto-generates OpenAPI docs useful for testing endpoints manually, and is what your other agent projects (Deep Research Agent scaffold) already use. |
| **Dashboard** | Streamlit | Fastest way to get a clickable "Analyze NVIDIA" debug console without building a full Next.js frontend — appropriate for a testing phase; your Next.js dashboard pattern from other projects can replace this in production. |
| **Testing Framework** | Pytest + `pytest-asyncio` + `pytest-mock` | Standard for async Python; supports the unit/integration test-marker split described in Phase 1. |
| **Deployment Tools** | Docker + `docker-compose` (Postgres + ChromaDB + app service) | Keeps the testing environment reproducible and portable to your Contabo VPS later without changes — same containers can be promoted to production. |
| **Observability (test phase)** | Structured JSON logging (`config/logging_config.py`) + per-run DB record in `AgentRun` table | Lets you diff outputs across NVIDIA/Tesla/Apple test runs and across days without external tooling. |

### Explicitly deferred to production phase
- Authentication / multi-user access
- Rate limiting / API gateway
- Cloud vector DB / managed Postgres
- CI/CD pipeline
- Live brokerage/trading system integration (planned hook point only: the
  `InvestmentReport` JSON schema is designed so the Multi-Market Trading
  System can later consume `investment_summary.thesis` + `risk_analysis.overall_risk_level`
  as a signal input, without needing this project's internals.)
