# Folder Refactor Plan
## Agentic Financial Intelligence Platform

---

## Current Issues

1. **Duplicate folders**: `api/`, `security/`, `logs/` appear twice at root
2. **No standard `src/` layout** - Python packages at root level
3. **Scattered documentation** - 126 markdown files at root
4. **Missing standard folders**: `.github/workflows/`, `docs/architecture/`, `docs/diagrams/`
5. **Missing standard files**: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, `Makefile`
6. **`main.py` at root** - Should be in `src/` or `app/`

---

## Recommended Structure (Enterprise Layout)

```
financial_research_agent/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   ├── cd.yml
│   │   ├── security.yml
│   │   └── release.yml
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   ├── feature_request.md
│   │   └── documentation.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── dependabot.yml
├── docs/
│   ├── architecture/
│   │   ├── 01-system-overview.md
│   │   ├── 02-agent-architecture.md
│   │   ├── 03-rag-pipeline.md
│   │   ├── 04-database.md
│   │   ├── 05-api.md
│   │   ├── 06-dashboard.md
│   │   ├── 07-security.md
│   │   ├── 08-deployment.md
│   │   ├── 09-workflows.md
│   │   └── 10-memory.md
│   ├── diagrams/
│   │   ├── overall-architecture.mmd
│   │   ├── agent-architecture.mmd
│   │   ├── workflow.mmd
│   │   ├── knowledge-graph.mmd
│   │   ├── database.mmd
│   │   ├── deployment.mmd
│   │   ├── rag-pipeline.mmd
│   │   ├── api-flow.mmd
│   │   └── dashboard.mmd
│   ├── api/
│   │   ├── copilot.md
│   │   └── research.md
│   └── guides/
│       ├── getting-started.md
│       ├── development.md
│       ├── deployment.md
│       └── contributing.md
├── src/
│   ├── financial_research_agent/
│   │   ├── __init__.py
│   │   ├── agents/
│   │   │   ├── base.py
│   │   │   ├── financial_document/
│   │   │   ├── sentiment_analysis/
│   │   │   ├── risk_assessment/
│   │   │   ├── competitive_intelligence/
│   │   │   ├── news_intelligence/
│   │   │   ├── market_data/
│   │   │   ├── investment_summary/
│   │   │   ├── research_planner/
│   │   │   └── __init__.py
│   │   ├── api/
│   │   │   ├── main.py
│   │   │   ├── dependencies.py
│   │   │   ├── routes/
│   │   │   │   ├── research.py
│   │   │   │   ├── copilot.py
│   │   │   │   ├── watchlists.py
│   │   │   │   ├── approvals.py
│   │   │   │   └── reports.py
│   │   │   └── __init__.py
│   │   ├── copilot/
│   │   │   ├── agent.py
│   │   │   ├── assistant.py
│   │   │   ├── conversation.py
│   │   │   ├── prompts.py
│   │   │   └── __init__.py
│   │   ├── planning/
│   │   │   ├── agent.py
│   │   │   ├── orchestration.py
│   │   │   └── __init__.py
│   │   ├── tools/
│   │   │   ├── registry.py
│   │   │   ├── executor.py
│   │   │   ├── definitions.py
│   │   │   └── __init__.py
│   │   ├── collaboration/
│   │   │   ├── coordinator.py
│   │   │   ├── delegation.py
│   │   │   ├── consensus.py
│   │   │   ├── knowledge.py
│   │   │   └── __init__.py
│   │   ├── decision/
│   │   │   ├── engine.py
│   │   │   ├── reasoning.py
│   │   │   ├── synthesis.py
│   │   │   └── __init__.py
│   │   ├── explainability/
│   │   │   ├── engine.py
│   │   │   ├── evidence.py
│   │   │   ├── alternatives.py
│   │   │   └── __init__.py
│   │   ├── llm/
│   │   │   ├── orchestration.py
│   │   │   ├── models.py
│   │   │   ├── health.py
│   │   │   ├── adaptive.py
│   │   │   └── __init__.py
│   │   ├── memory/
│   │   │   ├── research_memory.py
│   │   │   ├── enhanced.py
│   │   │   ├── store.py
│   │   │   └── __init__.py
│   │   ├── data/
│   │   │   ├── alerts/
│   │   │   │   ├── engine.py
│   │   │   │   ├── models.py
│   │   │   │   ├── rules.py
│   │   │   │   ├── channels.py
│   │   │   │   └── __init__.py
│   │   │   ├── portfolio/
│   │   │   │   ├── positions.py
│   │   │   │   ├── risk.py
│   │   │   │   ├── rebalancing.py
│   │   │   │   ├── orders.py
│   │   │   │   └── __init__.py
│   │   │   ├── patterns/
│   │   │   │   ├── detectors.py
│   │   │   │   ├── models.py
│   │   │   │   ├── analytics.py
│   │   │   │   ├── backtesting.py
│   │   │   │   └── __init__.py
│   │   │   ├── knowledge_graph/
│   │   │   │   ├── nodes.py
│   │   │   │   │   ├── edges.py
│   │   │   │   │   ├── traversal.py
│   │   │   │   │   ├── algorithms.py
│   │   │   │   │   └── persistence.py
│   │   │   ├── analytics/
│   │   │   │   ├── factor_models.py
│   │   │   │   ├── monte_carlo.py
│   │   │   │   ├── attribution.py
│   │   │   │   ├── scenarios.py
│   │   │   │   └── __init__.py
│   │   │   ├── intelligence/
│   │   │   │   ├── trends.py
│   │   │   │   ├── evolution.py
│   │   │   │   ├── peer_comparison.py
│   │   │   │   └── __init__.py
│   │   │   ├── news/
│   │   │   │   ├── providers/
│   │   │   │   │   ├── base.py
│   │   │   │   │   ├── yahoo.py
│   │   │   │   │   ├── finnhub.py
│   │   │   │   │   ├── alphavantage.py
│   │   │   │   │   ├── newsapi.py
│   │   │   │   │   ├── rss.py
│   │   │   │   │   └── manager.py
│   │   │   │   ├── aggregator.py
│   │   │   │   ├── intelligence.py
│   │   │   │   ├── summarizer.py
│   │   │   │   ├── database.py
│   │   │   │   ├── dashboard.py
│   │   │   │   └── __init__.py
│   │   │   ├── financial_documents/
│   │   │   │   ├── parser.py
│   │   │   │   ├── tables.py
│   │   │   │   ├── statements.py
│   │   │   │   ├── factory.py
│   │   │   │   └── __init__.py
│   │   │   ├── filings/
│   │   │   │   ├── cache.py
│   │   │   │   ├── storage.py
│   │   │   │   ├── incremental.py
│   │   │   │   └── __init__.py
│   │   │   ├── earnings/
│   │   │   │   ├── parser.py
│   │   │   │   ├── speakers.py
│   │   │   │   ├── qa.py
│   │   │   │   └── __init__.py
│   │   │   ├── market_data/
│   │   │   │   ├── adapter.py
│   │   │   │   ├── providers/
│   │   │   │   │   ├── base.py
│   │   │   │   │   ├── yahoo.py
│   │   │   │   │   ├── alphavantage.py
│   │   │   │   │   ├── finnhub.py
│   │   │   │   │   └── manager.py
│   │   │   │   ├── analytics.py
│   │   │   │   └── __init__.py
│   │   │   ├── sec/
│   │   │   │   ├── downloader.py
│   │   │   │   └── __init__.py
│   │   │   ├── filings/
│   │   │   │   ├── cache.py
│   │   │   │   ├── storage.py
│   │   │   │   ├── incremental.py
│   │   │   │   └── __init__.py
│   │   │   └── __init__.py
│   │   ├── database/
│   │   │   ├── models.py
│   │   │   ├── connection.py
│   │   │   ├── migrations/
│   │   │   └── __init__.py
│   │   ├── rag/
│   │   │   ├── ingestion/
│   │   │   │   ├── pdf_processor.py
│   │   │   │   ├── metadata_extractor.py
│   │   │   │   └── document_loader.py
│   │   │   ├── chunking/
│   │   │   │   ├── section_splitter.py
│   │   │   │   └── __init__.py
│   │   │   ├── vector_store/
│   │   │   │   ├── chroma_store.py
│   │   │   │   └── __init__.py
│   │   │   └── __init__.py
│   │   ├── monitoring/
│   │   │   ├── metrics.py
│   │   │   ├── health.py
│   │   │   ├── performance.py
│   │   │   └── __init__.py
│   │   ├── middleware/
│   │   │   ├── logging_middleware.py
│   │   │   ├── rate_limit.py
│   │   │   ├── circuit_breaker.py
│   │   │   └── __init__.py
│   │   ├── security/
│   │   │   ├── auth.py
│   │   │   ├── jwt.py
│   │   │   │   ├── api_keys.py
│   │   │   │   ├── rbac.py
│   │   │   │   └── validation.py
│   │   │   └── __init__.py
│   │   ├── cache/
│   │   │   ├── manager.py
│   │   │   └── __init__.py
│   │   ├── notifications/
│   │   │   ├── engine.py
│   │   │   ├── channels/
│   │   │   │   ├── email.py
│   │   │   │   ├── slack.py
│   │   │   │   ├── discord.py
│   │   │   │   ├── webhook.py
│   │   │   │   ├── console.py
│   │   │   │   └── in_app.py
│   │   │   └── __init__.py
│   │   ├── approval/
│   │   │   ├── workflow.py
│   │   │   ├── models.py
│   │   │   │   ├── audit.py
│   │   │   │   └── __init__.py
│   │   ├── reports/
│   │   │   ├── generator.py
│   │   │   ├── templates.py
│   │   │   │   ├── sections.py
│   │   │   │   ├── templates.py
│   │   │   │   ├── formats.py
│   │   │   │   └── __init__.py
│   │   ├── watchlists/
│   │   │   ├── manager.py
│   │   │   └── __init__.py
│   │   ├── workflows/
│   │   │   ├── orchestrator.py
│   │   │   ├── executor.py
│   │   │   ├── state.py
│   │   │   └── __init__.py
│   │   ├── config/
│   │   │   ├── settings.py
│   │   │   ├── logging.py
│   │   │   ├── production.py
│   │   │   │   ├── development.py
│   │   │   │   ├── security.py
│   │   │   │   ├── cache.py
│   │   │   │   └── __init__.py
│   │   ├── dashboard/
│   │   │   ├── app.py
│   │   │   ├── copilot.py
│   │   │   ├── components/
│   │   │   │   ├── charts.py
│   │   │   │   ├── tables.py
│   │   │   │   ├── forms.py
│   │   │   │   ├── layout.py
│   │   │   │   └── __init__.py
│   │   │   └── __init__.py
│   │   ├── workflows/
│   │   │   ├── orchestrator.py
│   │   │   │   ├── executor.py
│   │   │   │   ├── state.py
│   │   │   │   └── __init__.py
│   │   └── __init__.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── phase5/
│   ├── phase7/
│   ├── phase8/
│   ├── conftest.py
│   └── __init__.py
├── scripts/
│   ├── setup.sh
│   ├── dev.sh
│   ├── test.sh
│   ├── lint.sh
│   ├── build.sh
│   └── deploy.sh
├── .github/
├── docs/
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── requirements-prod.txt
├── README.md
├── CHANGELOG.md
├── ROADMAP.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── SUPPORT.md
├── LICENSE
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
└── alembic/
```

---

## Migration Steps (Safe, Non-Breaking)

### Phase 1: Cleanup (Week 1)
1. **Remove duplicate folders**
   - Remove root `api/` (keep `src/financial_research_agent/api/`)
   - Remove root `security/` (keep `src/financial_research_agent/security/`)
   - Remove root `logs/` (keep `logs/` for application logs)

2. **Remove dead code**
   - Remove `orchestrator/` (functionality in `workflows/orchestrator.py`)
   - Remove `rag/ingestion/` (legacy, replaced by `data/financial_documents/` and `data/filings/`)

3. **Clean up root markdown files**
   - Move 126 markdown files to `docs/` or `docs/guides/`
   - Keep only: `README.md`, `CHANGELOG.md`, `ROADMAP.md`, `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`

### Phase 2: Restructure to src/ layout (Week 2)
1. **Create `src/financial_research_agent/`** package
2. **Move all packages** under `src/financial_research_agent/`
3. **Update all imports** (use IDE refactoring or `sed`)
4. **Update `pyproject.toml`** with `package_dir = {"": "src"}`

### Phase 3: Split Large Files (Week 2-3)
See `LARGE_FILE_REPORT.md` for detailed split plans

### Phase 4: Documentation & CI/CD (Week 3)
1. Create `docs/architecture/` (10 files)
2. Create `docs/diagrams/` (10 Mermaid diagrams)
3. Create `.github/workflows/` (CI/CD pipelines)
4. Add missing GitHub files
5. Create `Makefile` and `DEVELOPER_GUIDE.md`

### Phase 5: Testing & Validation (Week 4)
1. Run full test suite
2. Verify all imports work
3. Run Docker build
3. Verify all 396 tests pass

---

## Risk Assessment

| Change | Risk | Mitigation |
|--------|------|------------|
| Move to `src/` layout | High - breaks all imports | Use IDE refactoring, run tests after each move |
| Split large files | Medium - API changes | Create backward-compatible facade modules |
| Remove duplicate folders | Low | Verify no references first |
| Remove dead code | Low | Verify with `grep -r` first |
| Update imports | Medium | Use IDE bulk refactoring |

---

## Commands for Migration

```bash
# 1. Backup current state
git checkout -b refactor/enterprise-structure

# 2. Remove duplicate folders (verify no references first)
grep -r "from api\." --include="*.py" | grep -v "src/financial_research_agent/api"
grep -r "from security\." --include="*.py" | grep -v "src/financial_research_agent/security"
# If no external references, safe to remove

# 3. Create src layout
mkdir -p src/financial_research_agent
mv agents api collaboration config copilot dashboard data decision explainability llm memory monitoring notifications orchestrator planning rag reports security tools watchlists workflows src/financial_research_agent/

# 4. Update pyproject.toml
# [build-system]
# build-backend = "setuptools.build_meta"
# [tool.setuptools.packages.find]
# where = ["src"]

# 5. Run tests
python -m pytest tests/ -q

# 6. Fix any import errors
# Use IDE refactoring or: find . -name "*.py" -exec sed -i 's/from agents/from financial_research_agent.agents/g' {} \;
```

---

## Validation Checklist

- [ ] All 396 tests pass
- [ ] `python -m compileall src/` passes
- [ ] `python -m pytest tests/ -q` passes (396 passed)
- [ ] `docker compose build --no-cache api` succeeds
- [ ] `docker compose up -d` - all 5 services healthy
- [ ] `curl http://localhost:8000/health/detailed` returns healthy
- [ ] `curl http://localhost:8000/docs` returns OpenAPI docs
- [ ] `python -m pytest tests/phase8/ -q` passes (112 tests)

---

## Timeline Summary

| Week | Focus | Deliverables |
|------|-------|--------------|
| 1 | Cleanup & Safety | No duplicate folders, dead code removed, tests pass |
| 2 | Src Layout + Large Files | `src/` layout, 6 critical files split |
| 3 | Documentation & CI/CD | Architecture docs, diagrams, GitHub Actions |
| 4 | Polish & Release | Makefile, Developer Guide, final testing |

**Total Estimated Effort: ~120 hours (4 weeks)**

---

*Plan generated: 2026-07-18*  
*Architect: Lead Software Architect*