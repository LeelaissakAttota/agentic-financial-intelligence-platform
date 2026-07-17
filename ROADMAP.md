# ROADMAP.md - Agentic Financial Intelligence Platform

## Vision
Build the most comprehensive AI-powered financial research platform that automates end-to-end equity research workflows with institutional-grade quality, speed, and auditability.

---

## Phase Status Overview

| Phase | Status | Version | Completion |
|-------|--------|---------|------------|
| Phase 1: Core Infrastructure | ✅ Complete | v1.0.0-phase1 | 2026-07-13 |
| Phase 2.1: Market Data Agent | ✅ Complete | v1.0.0-phase2.1 | 2026-07-15 |
| Phase 2.2: News Intelligence | ✅ Complete | v1.1.0-phase2.2 | 2026-07-16 |
| Phase 2.3: Entity Recognition | ✅ Complete | v1.2.0-phase2.3 | 2026-07-17 |
| Phase 3: Real Financial Intelligence | ✅ Complete | v1.3.0-phase3 | 2026-07-17 |
| **Phase 4: Knowledge Persistence** | 🔄 **Next** | v1.4.0-phase4 | Planned |
| Phase 5: MLOps & Production | ⏳ Planned | v1.5.0-phase5 | Future |
| Phase 6: Enterprise Features | ⏳ Planned | v2.0.0-phase6 | Future |

---

## Phase 3: Real Financial Intelligence (v1.3.0) ✅ COMPLETE
**Completed**: 2026-07-17 | **Effort**: 4-6 weeks

### 3.1 Real News Providers ✅
- [x] Yahoo Finance News (yfinance API)
- [x] Google News RSS (RSS feed)
- [x] Reuters Business (RSS feed)
- [x] Alpha Vantage News (REST API)
- [x] Finnhub News (REST API)

### 3.2 News Aggregator ✅
- [x] Multi-source collection with concurrent fetching
- [x] Duplicate removal (content hash + title similarity + content fingerprint)
- [x] Importance ranking (weighted: importance, market impact, freshness, relevance, quality, credibility)
- [x] Company relevance scoring (keyword matching + entity bonus + position bonus)
- [x] Time decay (configurable: step/linear/exponential)
- [x] Source credibility tiers (Tier 1: Reuters/Bloomberg=1.0, Tier 2: CNBC/MarketWatch=0.8, Tier 3: Others=0.5-0.7)

### 3.3 Company News Intelligence ✅
- [x] Companies, People, Products extraction
- [x] Earnings, Acquisitions, Partnerships detection
- [x] Lawsuits, Regulations, Management changes detection
- [x] Financial event detection via regex patterns (12 categories)
- [x] Company name resolution (aliases → canonical + ticker)
- [x] Executive recognition with roles (Tim Cook, Satya Nadella, etc.)
- [x] Product/technology extraction via entity recognition
- [x] Risk/opportunity identification from text and events
- [x] Key metric extraction (sentiment, event counts, company mentions)

### 3.4 News Summarization ✅
- [x] Executive Summary (500-char max, multi-factor synthesis)
- [x] Positive Events (earnings beats, guidance raises, product launches, partnerships)
- [x] Negative Events (lawsuits, regulatory actions, layoffs, bankruptcies)
- [x] Risks (15+ keyword categories + event-based)
- [x] Opportunities (15+ keyword categories + event-based)
- [x] Company focus identification with sentiment + event summary
- [x] Event classification (positive/negative/neutral via category + article sentiment)

### 3.5 News Database ✅
- [x] Articles with full analysis (sentiment, events, companies, scores)
- [x] Companies with mention tracking and sentiment averaging
- [x] Article-Company many-to-many with mention details
- [x] News summaries with period aggregation
- [x] Embedding references (ChromaDB vector IDs)
- [x] Watchlists with alert rules
- [x] Repository functions for upserts, queries, trends, top companies

### 3.6 Dashboard Components ✅
- [x] Latest News (filterable cards: source, category, sentiment, sort)
- [x] News Timeline (Plotly: importance vs time, size=market impact)
- [x] Sentiment Analysis (pie chart + time series + rolling avg + key drivers)
- [x] Source Breakdown (bar chart + credibility scores + tier labels)
- [x] Related Companies (table + co-mentions network)

---

## Phase 4: Knowledge Persistence & Advanced Analytics (v1.4.0)
**Target**: Q3 2026 | **Effort**: 4-6 weeks

### 4.1 Knowledge Graph Persistence (Neo4j/PostgreSQL)
- [ ] **Neo4j Integration**: Deploy Neo4j for persistent graph storage
- [ ] **Graph Persistence Layer**: Save entity graphs across research sessions
- [ ] **PostgreSQL Graph Tables**: Alternative graph storage in PostgreSQL
- [ ] **Graph Migration**: Migrate in-memory NetworkX graphs to persistent storage
- [ ] **Graph Queries**: Cypher/GraphQL interface for graph traversal
- [ ] **Schema Evolution**: Versioned graph schema with migrations

### 4.2 Cross-Agent Knowledge Sharing
- [ ] **Shared Vector Space**: Common embedding space for all agent outputs
- [ ] **Knowledge Injection**: Inject relevant findings from previous agents into next agent context
- [ ] **Entity Linking**: Cross-reference entities across agent outputs
- [ ] **Conflict Detection**: Identify contradictory findings between agents
- [ ] **Consensus Scoring**: Weight findings by source reliability and recency

### 4.3 Historical Pattern Recognition
- [ ] **Time-Series Entity Tracking**: Track entity mentions, relationships, sentiment over time
- [ ] **Trend Detection**: Identify emerging patterns (sentiment shifts, relationship changes)
- [ ] **Anomaly Detection**: Flag unusual entity behavior (sudden mention spikes, sentiment reversals)
- [ ] **Correlation Analysis**: Find correlated entity movements (sector rotation, peer dynamics)
- [ ] **Predictive Signals**: Generate forward-looking indicators from historical patterns

### 4.4 Alerting & Real-time Monitoring
- [ ] **Event-Driven Architecture**: Webhook/queue system for real-time triggers
- [ ] **Watchlist Management**: User-defined entity/topic watchlists
- [ ] **Alert Rules Engine**: Configurable conditions (sentiment threshold, event type, entity mention)
- [ ] **Delivery Channels**: Email, Slack, Webhook, In-app notifications
- [ ] **Alert Deduplication**: Suppress noise with intelligent grouping
- [ ] **Dashboard Integration**: Real-time alert panel in Streamlit

---

## Phase 5: MLOps & Production Hardening (v1.5.0)
**Target**: Q4 2026 | **Effort**: 4-6 weeks

### 5.1 Model Drift Detection & Automated Retraining
- [ ] **Embedding Drift Monitoring**: Track BGE-M3 embedding distribution shifts
- [ ] **Prediction Drift**: Monitor agent output quality metrics over time
- [ ] **Automated Retraining Pipeline**: Trigger fine-tuning when drift exceeds threshold
- [ ] **Model Registry**: Versioned model storage with metadata (training data, metrics, date)
- [ ] **Canary Deployment**: Gradual rollout with automated rollback on regression

### 5.2 A/B Testing Framework
- [ ] **Agent Variant Framework**: Swap agent implementations per request
- [ ] **Traffic Splitting**: Percentage-based routing to variants
- [ ] **Metric Collection**: Automated A/B metric aggregation
- [ ] **Statistical Significance**: Built-in significance testing
- [ ] **Decision Dashboard**: Visual comparison of variant performance

### 5.3 Continuous Learning from Feedback
- [ ] **User Feedback Loop**: Rating/correction mechanism in dashboard/API
- [ ] **Active Learning**: Prioritize uncertain samples for human review
- [ ] **Feedback Integration**: Incorporate corrections into RAG and entity recognition
- [ ] **Reward Modeling**: Learn preference model from user rankings

### 5.4 Advanced Caching & Performance
- [ ] **Multi-Level Caching**: L1 (in-memory), L2 (Redis), L3 (disk)
- [ ] **Query Result Caching**: Cache agent outputs with TTL and invalidation
- [ ] **Embedding Cache**: Persistent embedding storage with similarity lookup
- [ ] **Batch Processing**: Async batch endpoints for bulk research
- [ ] **Connection Pooling**: Optimized DB/HTTP connection management

---

## Phase 6: Enterprise Features (v2.0.0)
**Target**: Q1 2027 | **Effort**: 6-8 weeks

### 6.1 Multi-Tenant Architecture
- [ ] **Tenant Isolation**: Data, config, and resource isolation
- [ ] **Shared Infrastructure**: Cost-efficient multi-tenancy
- [ ] **Tenant Management API**: Provision, configure, monitor tenants
- [ ] **Custom Branding**: White-label dashboard and reports

### 6.2 Role-Based Access Control (RBAC)
- [ ] **Roles**: Admin, Analyst, Viewer, API-Only
- [ ] **Permissions**: Granular resource/action permissions
- [ ] **Team Management**: User groups with inherited permissions
- [ ] **Audit Logging**: Comprehensive action logging for compliance

### 6.3 Audit Logging & Compliance
- [ ] **Immutable Audit Trail**: Append-only logs for all research actions
- [ ] **Data Lineage**: Track data from source to conclusion
- [ ] **Compliance Reports**: SOC2, GDPR, financial regulation templates
- [ ] **Retention Policies**: Configurable data retention with automated cleanup

### 6.4 Custom Agent Marketplace
- [ ] **Agent Plugin System**: Load custom agents from external packages
- [ ] **Agent Registry**: Discover, install, update custom agents
- [ ] **Sandbox Execution**: Isolated execution environment for untrusted agents
- [ ] **Revenue Sharing**: Marketplace economics for agent developers

---

## Technical Debt & Maintenance (Ongoing)

| Area | Tasks |
|------|-------|
| **Dependencies** | Monthly dependency updates, security patches |
| **Testing** | Maintain >90% coverage, add integration tests for new features |
| **Documentation** | Keep README, CHANGELOG, API docs in sync with code |
| **Performance** | Quarterly performance benchmarks, optimize bottlenecks |
| **Security** | Annual penetration testing, dependency scanning |
| **Monitoring** | Enhance Prometheus metrics, Grafana dashboards |

---

## Release Cadence

| Release Type | Frequency | Version Bump | Example |
|--------------|-----------|--------------|---------|
| **Major** | Quarterly | X.0.0 | v2.0.0 |
| **Minor (Phase)** | Monthly | X.Y.0 | v1.4.0 |
| **Patch** | Weekly | X.Y.Z | v1.4.1 |
| **Hotfix** | As needed | X.Y.Z+1 | v1.4.2 |

---

## Success Metrics

| Metric | Phase 4 Target | Phase 5 Target | Phase 6 Target |
|--------|----------------|----------------|----------------|
| Research Time | < 5 min | < 3 min | < 2 min |
| Entity Accuracy | 96% | 97% | 98% |
| System Uptime | 99.9% | 99.95% | 99.99% |
| Test Coverage | >90% | >92% | >95% |
| Concurrent Users | 100 | 1,000 | 10,000 |
| API Latency (p95) | < 500ms | < 300ms | < 200ms |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-07-17 | Phase 3 complete, proceed to Phase 4 | All quality gates passed, 320 tests green |
| 2026-07-17 | Phase 3 complete, proceed to Phase 4 | All quality gates passed, 320 tests green |
| 2026-07-16 | Use Neo4j for graph persistence | Native graph queries, mature ecosystem |
| 2026-07-15 | OpenRouter as primary LLM provider | Unified API, cost optimization, model diversity |
| 2026-07-13 | 7-agent architecture from start | Modular, testable, independently deployable |

---

## Contributing to Roadmap

1. **Propose**: Open GitHub Issue with "roadmap" label
2. **Discuss**: Community/team discussion in issue
3. **Prioritize**: Maintainers evaluate impact/effort
4. **Schedule**: Added to appropriate phase milestone
5. **Execute**: Implementation with tests and docs

---

*Last Updated: 2026-07-17 | Current Phase: 3 Complete → Phase 4 Next*