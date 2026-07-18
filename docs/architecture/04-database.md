# Database Architecture
## Agentic Financial Intelligence Platform

---

## Overview

The platform uses PostgreSQL 15+ as the primary relational database with SQLAlchemy 2.0 ORM for type-safe database operations. ChromaDB serves as the vector store for RAG operations.

---

## PostgreSQL Schema

### Core Tables

#### Companies
```sql
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    ticker VARCHAR(20),
    cik VARCHAR(10),
    sector VARCHAR(100),
    industry VARCHAR(100),
    market_cap BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_companies_ticker ON companies(ticker);
CREATE INDEX idx_companies_cik ON companies(cik);
```

#### Reports
```sql
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    json_payload JSONB,
    generated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_reports_company ON reports(company_id);
CREATE INDEX idx_reports_generated ON reports(generated_at DESC);
```

#### Agent Runs
```sql
CREATE TABLE agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID REFERENCES reports(id) ON DELETE SET NULL,
    agent_name VARCHAR(100) NOT NULL,
    input_payload JSONB,
    output_payload JSONB,
    tokens_used INTEGER,
    cost_usd DECIMAL(10,6),
    status VARCHAR(20) DEFAULT 'pending',
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_agent_runs_report ON agent_runs(report_id);
CREATE INDEX idx_agent_runs_agent ON agent_runs(agent_name);
CREATE INDEX idx_agent_runs_status ON agent_runs(status);
CREATE INDEX idx_agent_runs_timestamp ON agent_runs(timestamp DESC);
```

---

## Phase 5: Knowledge Intelligence Tables

### Knowledge Graph
```sql
CREATE TABLE kg_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    properties JSONB DEFAULT '{}',
    embedding VECTOR(1024),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE kg_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES kg_nodes(id) ON DELETE CASCADE,
    target_id UUID REFERENCES kg_nodes(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,
    properties JSONB DEFAULT '{}',
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_kg_nodes_type ON kg_nodes(node_type);
CREATE INDEX idx_kg_nodes_name ON kg_nodes(name);
CREATE INDEX idx_kg_edges_source ON kg_edges(source_id);
CREATE INDEX idx_kg_edges_target ON kg_edges(target_id);
CREATE INDEX idx_kg_edges_type ON kg_edges(relationship_type);
```

### Portfolio Intelligence
```sql
CREATE TABLE portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    owner_id VARCHAR(100) NOT NULL,
    base_currency VARCHAR(3) DEFAULT 'USD',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    quantity DECIMAL(20,8) NOT NULL,
    avg_cost DECIMAL(20,8),
    market_value DECIMAL(20,2),
    currency VARCHAR(3) DEFAULT 'USD',
    opened_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(4) NOT NULL,  -- BUY, SELL
    quantity DECIMAL(20,8) NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    commission DECIMAL(10,2) DEFAULT 0,
    executed_at TIMESTAMP DEFAULT NOW()
);
```

### Patterns
```sql
CREATE TABLE patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_type VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(20) NOT NULL,
    detected_at TIMESTAMP NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    confidence FLOAT NOT NULL,
    metadata JSONB DEFAULT '{}',
    backtest_results JSONB
);

CREATE INDEX idx_patterns_symbol ON patterns(symbol);
CREATE INDEX idx_patterns_type ON patterns(pattern_type);
CREATE INDEX idx_patterns_detected ON patterns(detected_at DESC);
```

### Alerts
```sql
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    watchlist_id UUID REFERENCES watchlists(id) ON DELETE CASCADE,
    rule_id UUID REFERENCES alert_rules(id) ON DELETE CASCADE,
    symbol VARCHAR(20),
    triggered_at TIMESTAMP DEFAULT NOW(),
    severity VARCHAR(20) DEFAULT 'warning',
    message TEXT,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP,
    acknowledged_by VARCHAR(100)
);

CREATE TABLE alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    watchlist_id UUID REFERENCES watchlists(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    condition_type VARCHAR(50) NOT NULL,
    parameters JSONB NOT NULL,
    severity VARCHAR(20) DEFAULT 'warning',
    channels JSONB DEFAULT '[]',
    cooldown_minutes INTEGER DEFAULT 60,
    max_triggers_per_hour INTEGER DEFAULT 10,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Analytics
```sql
CREATE TABLE analytics_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_type VARCHAR(50) NOT NULL,
    parameters JSONB NOT NULL,
    results JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE factor_exposures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES analytics_runs(id) ON DELETE CASCADE,
    factor_name VARCHAR(50) NOT NULL,
    exposure FLOAT NOT NULL,
    t_stat FLOAT,
    p_value FLOAT
);

CREATE TABLE monte_carlo_paths (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES analytics_runs(id) ON DELETE CASCADE,
    path_index INTEGER NOT NULL,
    final_value DECIMAL(20,2) NOT NULL,
    max_drawdown FLOAT
);
```

### Historical Intelligence
```sql
CREATE TABLE historical_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    data_type VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    value JSONB NOT NULL,
    source VARCHAR(100)
);

CREATE INDEX idx_historical_company_type ON historical_data(company_id, data_type);
CREATE INDEX idx_historical_timestamp ON historical_data(timestamp DESC);
```

### Cross-Agent Memory
```sql
CREATE TABLE agent_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_type VARCHAR(50) NOT NULL,
    scope VARCHAR(50) NOT NULL,
    scope_key VARCHAR(255) NOT NULL,
    content JSONB NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    source_agent VARCHAR(100),
    supersedes_id UUID REFERENCES agent_memory(id),
    linked_memories UUID[],
    tags TEXT[],
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_memory_type_scope ON agent_memory(memory_type, scope);
CREATE INDEX idx_memory_scope_key ON agent_memory(scope, scope_key);
CREATE INDEX idx_memory_expires ON agent_memory(expires_at);
CREATE INDEX idx_memory_tags ON agent_memory USING GIN(tags);
```

---

## Phase 7: Autonomous Research Tables

### Research Sessions
```sql
CREATE TABLE research_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company VARCHAR(255) NOT NULL,
    query TEXT NOT NULL,
    plan_id VARCHAR(50),
    status VARCHAR(32) DEFAULT 'pending',
    steps JSONB DEFAULT '[]',
    results JSONB DEFAULT '{}',
    conclusions TEXT[],
    reports UUID[],
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_seconds FLOAT DEFAULT 0,
    error TEXT
);

CREATE INDEX idx_research_company ON research_sessions(company);
CREATE INDEX idx_research_status ON research_sessions(status);
CREATE INDEX idx_research_started ON research_sessions(started_at DESC);
```

---

## Phase 8: AI Copilot Tables

### Copilot Sessions
```sql
CREATE TABLE copilot_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(64) NOT NULL,
    company VARCHAR(128),
    mode VARCHAR(32) DEFAULT 'auto_execute',
    status VARCHAR(32) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    context JSONB DEFAULT '{}',
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd FLOAT DEFAULT 0.0
);

CREATE INDEX idx_copilot_user ON copilot_sessions(user_id);
CREATE INDEX idx_copilot_company ON copilot_sessions(company);
CREATE INDEX idx_copilot_status ON copilot_sessions(status);
```

### Conversations
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES copilot_sessions(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL,
    title VARCHAR(512),
    status VARCHAR(32) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    summary TEXT,
    token_count INTEGER DEFAULT 0
);

CREATE INDEX idx_conversation_session ON conversations(session_id);
CREATE INDEX idx_conversation_user ON conversations(user_id);
```

### Conversation Messages
```sql
CREATE TABLE conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL,  -- user, assistant, tool, system
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    tool_calls JSONB,
    tool_call_id VARCHAR(64),
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_msg_conversation ON conversation_messages(conversation_id);
CREATE INDEX idx_msg_timestamp ON conversation_messages(timestamp);
```

### Decision History
```sql
CREATE TABLE decision_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES copilot_sessions(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id),
    question TEXT NOT NULL,
    decision_type VARCHAR(64) NOT NULL,
    conclusion TEXT NOT NULL,
    confidence FLOAT DEFAULT 0.0,
    reasoning TEXT,
    explanation TEXT NOT NULL,
    evidence JSONB,
    alternatives JSONB,
    risk_factors JSONB,
    assumptions JSONB,
    model_used VARCHAR(64),
    tokens_used INTEGER DEFAULT 0,
    cost_usd FLOAT DEFAULT 0.0,
    latency_ms FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_decision_session ON decision_history(session_id);
CREATE INDEX idx_decision_conversation ON decision_history(conversation_id);
```

### Tool Executions
```sql
CREATE TABLE tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES copilot_sessions(id) ON DELETE CASCADE,
    tool_name VARCHAR(64) NOT NULL,
    category VARCHAR(32) NOT NULL,
    parameters JSONB NOT NULL,
    result JSONB,
    status VARCHAR(32) DEFAULT 'pending',
    error TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_seconds FLOAT DEFAULT 0.0,
    tokens_used INTEGER DEFAULT 0,
    cost_usd FLOAT DEFAULT 0.0
);

CREATE INDEX idx_tool_session ON tool_executions(session_id);
CREATE INDEX idx_tool_name ON tool_executions(tool_name);
```

### Workflow Executions
```sql
CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES copilot_sessions(id) ON DELETE CASCADE,
    plan_id UUID,
    company VARCHAR(128) NOT NULL,
    goal TEXT NOT NULL,
    complexity VARCHAR(32) NOT NULL,
    tasks JSONB NOT NULL,
    status VARCHAR(32) DEFAULT 'pending',
    current_step VARCHAR(64),
    completed_steps INTEGER DEFAULT 0,
    total_steps INTEGER DEFAULT 0,
    step_results JSONB,
    error TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    total_duration_seconds FLOAT DEFAULT 0.0,
    total_cost_usd FLOAT DEFAULT 0.0,
    total_tokens INTEGER DEFAULT 0
);

CREATE INDEX idx_workflow_session ON workflow_executions(session_id);
CREATE INDEX idx_workflow_company ON workflow_executions(company);
CREATE INDEX idx_workflow_status ON workflow_executions(status);
```

---

## Phase 8: Enhanced Memory Tables

### Long-Term Memory
```sql
CREATE TABLE long_term_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope VARCHAR(32) NOT NULL,
    scope_key VARCHAR(255) NOT NULL,
    content JSONB NOT NULL,
    memory_type VARCHAR(32) NOT NULL,
    importance VARCHAR(16) DEFAULT 'medium',
    confidence FLOAT DEFAULT 1.0,
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    tags TEXT[],
    source VARCHAR(32) DEFAULT 'system',
    supersedes_id UUID REFERENCES long_term_memory(id),
    linked_memories UUID[]
);

CREATE INDEX idx_ltm_scope_key ON long_term_memory(scope, scope_key);
CREATE INDEX idx_ltm_importance ON long_term_memory(importance);
CREATE INDEX idx_ltm_expires ON long_term_memory(expires_at);
CREATE INDEX idx_ltm_tags ON long_term_memory USING GIN(tags);
```

### Conversation Memory
```sql
CREATE TABLE conversation_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(64) NOT NULL,
    session_id UUID,
    messages JSONB DEFAULT '[]',
    topics TEXT[],
    entities_mentioned TEXT[],
    decisions_made UUID[],
    tools_used TEXT[],
    agents_consulted TEXT[],
    summary TEXT,
    sentiment FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    message_count INTEGER DEFAULT 0
);

CREATE INDEX idx_conv_user ON conversation_memory(user_id);
CREATE INDEX idx_conv_session ON conversation_memory(session_id);
```

### User Preferences
```sql
CREATE TABLE user_preferences (
    user_id VARCHAR(64) PRIMARY KEY,
    preferences JSONB DEFAULT '{}',
    interaction_patterns JSONB DEFAULT '{}',
    preferred_companies TEXT[],
    preferred_report_types TEXT[],
    preferred_agents TEXT[],
    notification_preferences JSONB DEFAULT '{}',
    ui_preferences JSONB DEFAULT '{}',
    confidence FLOAT DEFAULT 0.5,
    last_updated TIMESTAMP DEFAULT NOW(),
    interaction_count INTEGER DEFAULT 0
);
```

### Decision History
```sql
CREATE TABLE decision_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(64) NOT NULL,
    session_id UUID,
    decision_id UUID NOT NULL,
    question TEXT NOT NULL,
    decision_type VARCHAR(64) NOT NULL,
    conclusion TEXT NOT NULL,
    confidence FLOAT,
    outcome TEXT,
    outcome_accuracy FLOAT,
    feedback TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dh_user ON decision_history(user_id);
CREATE INDEX idx_dh_session ON decision_history(session_id);
```

### Tool Usage Analytics
```sql
CREATE TABLE tool_usage_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(64) NOT NULL,
    session_id UUID,
    tool_name VARCHAR(64) NOT NULL,
    category VARCHAR(32) NOT NULL,
    parameters JSONB,
    result_summary JSONB,
    success BOOLEAN,
    duration_ms FLOAT,
    tokens_used INTEGER,
    cost_usd FLOAT,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tool_user ON tool_usage_analytics(user_id);
CREATE INDEX idx_tool_name ON tool_usage_analytics(tool_name);
CREATE INDEX idx_tool_timestamp ON tool_usage_analytics(timestamp);
```

---

## Indexes Summary

### Critical Indexes
```sql
-- Company lookups
CREATE INDEX idx_companies_ticker ON companies(ticker);
CREATE INDEX idx_companies_cik ON companies(cik);

-- Report queries
CREATE INDEX idx_reports_company ON reports(company_id);
CREATE INDEX idx_reports_generated ON reports(generated_at DESC);

-- Agent runs
CREATE INDEX idx_agent_runs_report ON agent_runs(report_id);
CREATE INDEX idx_agent_runs_agent ON agent_runs(agent_name);
CREATE INDEX idx_agent_runs_status ON agent_runs(status);
CREATE INDEX idx_agent_runs_timestamp ON agent_runs(timestamp DESC);

-- Knowledge Graph
CREATE INDEX idx_kg_nodes_type ON kg_nodes(node_type);
CREATE INDEX idx_kg_nodes_name ON kg_nodes(name);
CREATE INDEX idx_kg_edges_source ON kg_edges(source_id);
CREATE INDEX idx_kg_edges_target ON kg_edges(target_id);
CREATE INDEX idx_kg_edges_type ON kg_edges(relationship_type);

-- Portfolio
CREATE INDEX idx_positions_portfolio ON positions(portfolio_id);
CREATE INDEX idx_positions_symbol ON positions(symbol);

-- Patterns
CREATE INDEX idx_patterns_symbol ON patterns(symbol);
CREATE INDEX idx_patterns_type ON patterns(pattern_type);
CREATE INDEX idx_patterns_detected ON patterns(detected_at DESC);

-- Alerts
CREATE INDEX idx_alerts_watchlist ON alerts(watchlist_id);
CREATE INDEX idx_alerts_symbol ON alerts(symbol);
CREATE INDEX idx_alerts_triggered ON alerts(triggered_at DESC);

-- Research Sessions
CREATE INDEX idx_research_company ON research_sessions(company);
CREATE INDEX idx_research_status ON research_sessions(status);
CREATE INDEX idx_research_started ON research_sessions(started_at DESC);

-- Copilot Sessions
CREATE INDEX idx_copilot_user ON copilot_sessions(user_id);
CREATE INDEX idx_copilot_company ON copilot_sessions(company);
CREATE INDEX idx_copilot_status ON copilot_sessions(status);

-- Conversations
CREATE INDEX idx_conv_session ON conversations(session_id);
CREATE INDEX idx_conv_user ON conversations(user_id);

-- Messages
CREATE INDEX idx_msg_conversation ON conversation_messages(conversation_id);
CREATE INDEX idx_msg_timestamp ON conversation_messages(timestamp);

-- Decisions
CREATE INDEX idx_decision_session ON decision_history(session_id);
CREATE INDEX idx_decision_conv ON decision_history(conversation_id);

-- Tool Executions
CREATE INDEX idx_tool_session ON tool_executions(session_id);
CREATE INDEX idx_tool_name ON tool_executions(tool_name);

# Workflows
CREATE INDEX idx_wf_session ON workflow_executions(session_id);
CREATE INDEX idx_wf_company ON workflow_executions(company);
CREATE INDEX idx_wf_status ON workflow_executions(status);
```

---

## Connection Management

### Connection Pool (SQLAlchemy 2.0)
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

def get_engine():
    settings = get_settings()
    url = (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )
    return create_async_engine(
        url,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.debug
    )

def get_session_factory(engine):
    return sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

# Context manager for sessions
@asynccontextmanager
async def get_session():
    session_factory = get_session_factory(get_engine())
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

---

## Migration Management (Alembic)

### Configuration (`alembic.ini`)
```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = postgresql+asyncpg://user:pass@localhost:5432/financial_research

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 100
```

### Migration Commands
```bash
# Create new migration
alembic revision --autogenerate -m "Phase 8: Add copilot tables"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Show history
alembic history
```

---

## ChromaDB Vector Store

### Collections
| Collection | Purpose | Dimensions |
|------------|---------|------------|
| `financial_docs` | SEC filings, earnings, reports | 1024 (BGE-M3) |
| `news_articles` | News articles, embeddings | 1024 |
| `earnings_transcripts` | Earnings call transcripts | 1024 |
| `analyst_reports` | Analyst reports | 1024 |
| `market_data` | Market data embeddings | 1024 |

### ChromaDB Config
```python
CHROMA_CONFIG = {
    "persist_directory": "./chroma_db",
    "anonymized_telemetry": False,
    "settings": {
        "chroma_db_impl": "duckdb+parquet",
        "persist_directory": "./chroma_db"
    }
}
```

---

## Redis Cache

### Usage
| Purpose | TTL | Pattern |
|---------|-----|---------|
| Session storage | 24h | `session:{session_id}` |
| Rate limiting | 1m-1h | `ratelimit:{key}` |
| Tool cache | 5m-1h | `tool:{tool}:{hash}` |
| LLM response cache | 1h | `llm:{model}:{hash}` |
| Market data | 5m | `market:{ticker}:quote` |

### Redis Config
```python
REDIS_CONFIG = {
    "host": "localhost",
    "port": 6379,
    "db": 0,
    "max_connections": 50,
    "decode_responses": True
}
```

---

## Backup & Recovery

### PostgreSQL
```bash
# Backup
pg_dump -h localhost -U postgres financial_research > backup_$(date +%Y%m%d).sql

# Restore
psql -h localhost -U postgres financial_research < backup_20260718.sql
```

### ChromaDB
```bash
# Backup (copy persist directory)
cp -r ./chroma_db ./backups/chroma_db_$(date +%Y%m%d)

# Restore
rm -rf ./chroma_db && cp -r ./backups/chroma_db_20260718 ./chroma_db
```

### Redis
```bash
# Backup
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb ./backups/redis_$(date +%Y%m%d).rdb

# Restore
redis-cli SHUTDOWN NOSAVE
cp ./backups/redis_20260718.rdb /var/lib/redis/dump.rdb
redis-server
```

---

## Performance Tuning

### PostgreSQL Settings
```postgresql
# postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB
maintenance_work_mem = 64MB
random_page_cost = 1.1
effective_io_concurrency = 200
max_worker_processes = 8
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
```

### Index Maintenance
```sql
-- Reindex periodically
REINDEX DATABASE financial_research;

-- Check index usage
SELECT * FROM pg_stat_user_indexes 
WHERE idx_scan = 0 AND schemaname = 'public';

-- Table bloat check
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

*Document Version: 1.0*  
*Last Updated: 2026-07-18*  
*Platform: Agentic Financial Intelligence Platform v1.7.0-phase8*