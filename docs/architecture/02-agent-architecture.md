# Agent Architecture
## Agentic Financial Intelligence Platform

---

## Overview

The platform implements a **modular agent architecture** where each agent is a self-contained, independently deployable unit that implements the `BaseWorkerAgent` interface. The system currently has **14 specialized agents** orchestrated by a central `ManagerAgent` and the new **Phase 8 AI Copilot** for natural language interaction.

---

## Base Agent Interface

### `BaseWorkerAgent` (Abstract Base Class)

All agents inherit from `BaseWorkerAgent` which defines the standard contract:

```python
class BaseWorkerAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.llm = OpenRouterClient()
        self.settings = get_settings()
    
    @abstractmethod
    async def run(self, company: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent logic for given company and context."""
        pass
    
    def _create_task(self, task_type: str, company: str, query: str, context: Dict) -> Task:
        """Create standardized task object."""
        return Task(
            task_id=str(uuid.uuid4())[:8],
            task_type=task_type,
            company=company,
            query=query,
            context=context
        )
    
    async def _call_llm(self, prompt: str, system_prompt: str = "") -> Dict[str, Any]:
        """Call LLM with structured output parsing."""
        return await self.llm.agenerate_json(prompt, system_prompt)
```

**Key Features:**
- **Standardized I/O**: All agents accept `(company, context)` and return `Dict[str, Any]`
- **Error Handling**: Structured exceptions with `AgentError`, `ValidationError`, `TimeoutError`
- **Cost Tracking**: Automatic token usage and cost calculation per execution
- **Async-First**: All I/O operations use `async/await` for concurrency
- **Configurable**: Settings injected via `get_settings()` for environment-specific config

---

## Agent Registry

The `ManagerAgent` maintains a registry of all available agents:

```python
class ManagerAgent:
    def __init__(self):
        self.agents: Dict[str, BaseWorkerAgent] = {}
        self._register_default_agents()
    
    def _register_default_agents(self):
        self.agents["financial_document"] = FinancialDocumentAgent()
        self.agents["sentiment"] = SentimentAnalysisAgent()
        self.agents["risk"] = RiskAssessmentAgent()
        self.agents["competitive"] = CompetitiveIntelligenceAgent()
        self.agents["news"] = NewsAgent()
        self.agents["market_data"] = MarketDataAgent()
        self.agents["investment_summary"] = InvestmentSummaryAgent()
        self.agents["knowledge_graph"] = KnowledgeGraphAgent()
        self.agents["portfolio"] = PortfolioAgent()
        self.agents["patterns"] = PatternDetectionAgent()
        self.agents["alerts"] = AlertsAgent()
        self.agents["analytics"] = AnalyticsAgent()
        self.agents["historical"] = HistoricalIntelligenceAgent()
        self.agents["cross_agent_memory"] = CrossAgentMemoryAgent()
        # Phase 8: Research Planner (meta-agent)
        self.agents["research_planner"] = ResearchPlannerAgent()
```

**Dynamic Registration**: Agents can be registered/removed at runtime for extensibility.

---

## Agent Specifications

### 1. Financial Document Agent
**Purpose**: RAG-powered analysis of SEC filings, earnings transcripts, analyst reports

| Attribute | Details |
|-----------|---------|
| **Input** | Company name/ticker, question set, optional fiscal year/quarter |
| **Processing** | SEC filings (10-K, 10-Q, 8-K), earnings transcripts, analyst reports |
| **RAG Pipeline** | BGE-M3 embeddings + BGE-Reranker-v2-M3 + ChromaDB |
| **Output** | Structured financial metrics, ratio analysis, findings with citations |
| **Dependencies** | `data/filings/cache.py`, `data/financial_documents/parser.py`, `rag/vector_store/chroma_store.py` |
| **Avg Latency** | ~60s for 100-page document |

### 2. Sentiment Analysis Agent
**Purpose**: Multi-source sentiment scoring from news, social media, analyst opinions

| Attribute | Details |
|-----------|---------|
| **Input** | Company name, optional context from other agents |
| **Sources** | News articles, social media, analyst opinions |
| **Processing** | Source credibility weighting (Tier 1-3), 7-point sentiment scale |
| **Output** | Sentiment distribution, key drivers, divergence flag, confidence level |
| **Dependencies** | `data/news/aggregator.py`, `data/news/intelligence.py` |
| **Avg Latency** | ~30s |

### 3. Risk Assessment Agent
**Purpose**: Multi-category risk analysis (market, credit, operational, liquidity)

| Attribute | Details |
|-----------|---------|
| **Input** | Company name, optional context from other agents |
| **Categories** | Market, Credit, Operational, Liquidity risk |
| **Processing** | VaR/CVaR (95%/99%), stress testing, concentration analysis |
| **Output** | Risk category scores, risk factors, mitigation suggestions |
| **Dependencies** | `data/portfolio/portfolio.py` (risk metrics), `data/analytics/analytics.py` |
| **Avg Latency** | ~45s |

### 4. Competitive Intelligence Agent
**Purpose**: Peer comparison and competitive positioning analysis

| Attribute | Details |
|-----------|---------|
| **Input** | Company name, optional context from other agents |
| **Processing** | Peer identification, benchmarking, advantage/disadvantage analysis |
| **Output** | Peer comparison tables, competitive positioning, market position |
| **Dependencies** | `data/portfolio/portfolio.py` (peer data), `data/financial_documents/parser.py` |
| **Avg Latency** | ~45s |

### 5. News Intelligence Agent
**Purpose**: Financial news aggregation, sentiment, event detection, entity extraction

| Attribute | Details |
|-----------|---------|
| **Input** | Company name, timeframe, optional topics |
| **Providers** | 6 (Yahoo, Finnhub, Alpha Vantage, NewsAPI, RSS, Google News) |
| **Processing** | Fallback chain, deduplication (4 strategies), sentiment, events, entities |
| **Output** | Sentiment trends, key events, impact analysis, entity mentions |
| **Dependencies** | `data/news/aggregator.py`, `data/news/intelligence.py`, `data/news/summarizer.py` |
| **Avg Latency** | ~30s |

### 6. Market Data Agent
**Purpose**: Real-time market data, technical indicators, fundamentals

| Attribute | Details |
|-----------|---------|
| **Input** | Company ticker, timeframe, data types |
| **Providers** | Yahoo Finance, Alpha Vantage, Finnhub (composite with fallback) |
| **Indicators** | RSI(14), SMA(20/50/200), MACD, Bollinger Bands |
| **Output** | Technical analysis, fundamental valuation, market trends |
| **Dependencies** | `data/market_data/adapter.py`, `data/market_data/real_providers.py` |
| **Avg Latency** | ~15s |

### 7. Investment Summary Agent
**Purpose**: Multi-agent synthesis and investment thesis formulation

| Attribute | Details |
|-----------|---------|
| **Input** | Context from all other agents |
| **Processing** | Multi-agent synthesis, thesis formulation, risk-adjusted analysis |
| **Output** | Investment recommendation, price target, catalyst timeline |
| **Dependencies** | All other agents (synthesis) |
| **Avg Latency** | ~30s |

### 8. Knowledge Graph Agent (Phase 5)
**Purpose**: Entity relationships, graph traversal, centrality analysis, community detection

| Attribute | Details |
|-----------|---------|
| **Input** | Company names, tickers, extracted entities |
| **Graph** | 14 node types, 28 relationship types, PostgreSQL adjacency list |
| **Operations** | BFS/DFS, shortest path, centrality (degree, betweenness, PageRank), Louvain communities |
| **Output** | Entity relationships, network centrality, communities, graph queries |
| **Dependencies** | `data/knowledge_graph/graph.py`, `data/knowledge_graph/persistence.py` |
| **Avg Latency** | ~30s |

### 9. Portfolio Intelligence Agent (Phase 5)
**Purpose**: Position management, order execution, risk metrics, rebalancing

| Attribute | Details |
|-----------|---------|
| **Input** | Portfolio ID, positions, market data |
| **Operations** | Position mgmt, order execution (market/limit/stop), VaR/CVaR, Monte Carlo |
| **Strategies** | Equal weight, risk parity, max Sharpe, min variance, target allocation |
| **Output** | Portfolio metrics, risk analysis, rebalancing recommendations |
| **Dependencies** | `data/portfolio/portfolio.py`, `data/analytics/analytics.py` |
| **Avg Latency** | ~30s |

### 10. Pattern Detection Agent (Phase 5)
**Purpose**: 10 pattern types with backtesting

| Attribute | Details |
|-----------|---------|
| **Patterns** | Trend, Seasonal, S/R, Reversal, Breakout, Volume Spike, Cycle, Regime Change, Anomaly, Correlation |
| **Methods** | Linear regression, FFT, K-means, HMM, Z-score |
| **Output** | Detected patterns, signals, backtest results |
| **Dependencies** | `data/patterns/patterns.py`, `data/analytics/analytics.py` |
| **Avg Latency** | ~30s |

### 11. Alert Engine Agent (Phase 5)
**Purpose**: 30+ alert types, 5 channels, deduplication, cooldown

| Attribute | Details |
|-----------|---------|
| **Alert Types** | Price, Volume, MA Cross, RSI, Bollinger, MACD, Pattern, Earnings, Sentiment, Portfolio, News |
| **Channels** | Email (SMTP), Slack, Discord, Webhook, Console |
| **Features** | Deduplication (hash), cooldown (60min default), rate limiting (10/hr), retry (3x) |
| **Dependencies** | `data/alerts/alerts.py`, `data/alerts/channels.py` |
| **Avg Latency** | ~15s |

### 12. Analytics Engine Agent (Phase 5)
**Purpose**: Advanced analytics - factor models, Monte Carlo, attribution, scenarios

| Attribute | Details |
|-----------|---------|
| **Models** | Fama-French 3/5-factor, Monte Carlo (10K paths), Brinson attribution |
| **Scenarios** | Custom shocks (rate, equity, credit, FX, volatility) |
| **Correlation** | Rolling, EWMA, regime-aware |
| **Dependencies** | `data/analytics/analytics.py` |
| **Avg Latency** | ~60s |

### 13. Historical Intelligence Agent (Phase 5)
**Purpose**: Time-series storage, trend analysis, company evolution, peer comparison

| Attribute | Details |
|-----------|---------|
| **Storage** | Reports, news, filings, sentiment, risks, market data |
| **Trends** | Linear, polynomial, Mann-Kendall, Sen's slope |
| **Evolution** | Revenue/margin/leverage trajectories, lifecycle stage |
| **Dependencies** | `data/intelligence/historical.py` |
| **Avg Latency** | ~45s |

### 14. Cross-Agent Memory Agent (Phase 5)
**Purpose**: 9 memory types, 5 scopes, supersession, linking, TTL

| Attribute | Details |
|-----------|---------|
| **Memory Types** | Fact, Insight, Risk, Opportunity, Pattern, Alert, Portfolio, Entity, Relationship |
| **Scopes** | Global, Company, Sector, Portfolio, User |
| **Features** | Supersession, bidirectional linking, access logging, TTL expiration |
| **Dependencies** | `data/memory/cross_agent_memory.py`, `memory/enhanced.py` |
| **Avg Latency** | ~10s |

### 15. Research Planner Agent (Phase 7/8)
**Purpose**: LLM-driven dynamic task planning based on query complexity

| Attribute | Details |
|-----------|---------|
| **Complexity Levels** | SIMPLE, MODERATE, COMPLEX, COMPREHENSIVE |
| **Agent Types** | 14 available agent types |
| **Output** | ExecutionPlan with steps, dependencies, parallel groups, duration estimates |
| **Dependencies** | `agents/research_planner/agent.py`, `llm/orchestration.py` |
| **Avg Latency** | ~5s (planning only) |

---

## Agent Communication Protocol

### Standardized Interfaces

All agents communicate through standardized interfaces:

```python
# Input Context (passed to all agents)
{
    "company": "NVDA",
    "query": "Analyze competitive position",
    "context": {
        "financial_metrics": {...},
        "sentiment": {...},
        "risk_factors": [...],
        "news_events": [...],
        "market_data": {...},
        "peer_comparison": {...},
        "patterns": [...],
        "risk_assessment": {...}
    }
}

# Standard Output
{
    "agent_type": "risk_assessment",
    "status": "completed",
    "data": {...},
    "confidence": 0.87,
    "citations": [...],
    "metadata": {
        "execution_time_ms": 45000,
        "tokens_used": 1250,
        "cost_usd": 0.03
    }
}
```

### Context Propagation

The `WorkflowOrchestrator` manages context propagation between agents:

```python
class WorkflowOrchestrator:
    async def execute_plan(self, plan: ExecutionPlan) -> PlanExecution:
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(plan.steps)
        
        # Execute in topological waves
        for wave in self._topological_sort(dependency_graph):
            # Execute parallel tasks in wave
            tasks = [self._execute_step(step) for step in wave]
            results = await asyncio.gather(*tasks)
            
            # Propagate results to dependent steps
            for step, result in zip(wave, results):
                self._propagate_context(step, result, dependency_graph)
```

### Cross-Agent Memory Access

Agents can store and retrieve shared knowledge:

```python
# Store finding
await memory_store.store_agent_output(
    company="NVDA",
    agent_type="risk_assessment",
    output={"risk_score": 0.72, "key_risks": ["market", "concentration"]},
    session_id=session_id
)

# Retrieve relevant context
memories = await memory_store.retrieve_memories(
    company="NVDA",
    memory_types=[MemoryType.RISK, MemoryType.INSIGHT],
    limit=10
)
```

---

## Agent Lifecycle Management

### Registration
```python
manager = ManagerAgent()
manager.register_agent("custom_agent", CustomAgent())
```

### Health Monitoring
```python
async def check_agent_health(agent_name: str) -> AgentHealth:
    agent = manager.agents.get(agent_name)
    if not agent:
        return AgentHealth(healthy=False, reason="Not registered")
    
    try:
        # Quick health check
        start = time.time()
        result = await agent.run("TEST", {"query": "health_check"})
        latency = (time.time() - start) * 1000
        
        return AgentHealth(
            healthy=True,
            latency_ms=latency,
            last_check=datetime.now()
        )
    except Exception as e:
        return AgentHealth(healthy=False, reason=str(e))
```

### Graceful Degradation
```python
async def execute_with_fallback(agent_name: str, company: str, context: Dict) -> Dict:
    primary = manager.agents.get(agent_name)
    fallback = manager.agents.get(f"{agent_name}_fallback")
    
    try:
        return await primary.run(company, context)
    except Exception as e:
        logger.warning(f"Primary agent {agent_name} failed: {e}")
        if fallback:
            return await fallback.run(company, context)
        raise
```

---

## Agent Configuration

Each agent can be configured via environment variables:

```yaml
# .env.example
# Financial Document Agent
FINANCIAL_DOC_MAX_PAGES=100
FINANCIAL_DOC_CHUNK_SIZE=1000
FINANCIAL_DOC_CHUNK_OVERLAP=200

# Sentiment Agent
SENTIMENT_TIMEFRAME_DAYS=30
SENTIMENT_SOURCE_WEIGHTS='{"tier1": 1.0, "tier2": 0.8, "tier3": 0.5}'

# Risk Agent
RISK_VAR_CONFIDENCE=0.95
RISK_STRESS_SCENARIOS=10000

# News Agent
NEWS_TIMEFRAME_DAYS=7
NEWS_DEDUP_THRESHOLD=0.85
NEWS_MAX_ARTICLES=100

# Market Data
MARKET_DATA_CACHE_TTL=300
MARKET_DATA_PROVIDERS="yahoo,alphavantage,finnhub"
```

---

## Extending with Custom Agents

```python
from agents.base_worker_agent import BaseWorkerAgent
from agents.manager_agent.schemas import Task, TaskResult

class CustomAnalystAgent(BaseWorkerAgent):
    def __init__(self):
        super().__init__("custom_analyst")
    
    async def run(self, company: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # Custom logic here
        return {
            "custom_analysis": "results",
            "confidence": 0.85
        }

# Register at runtime
manager = ManagerAgent()
manager.register_agent("custom_analyst", CustomAnalystAgent())
```

---

## Performance Characteristics

| Agent | Avg Latency | Max Latency | Throughput | Memory |
|-------|-------------|-------------|------------|--------|
| Financial Document | 60s | 180s | 10/min | 150MB |
| Sentiment | 30s | 60s | 20/min | 80MB |
| Risk | 45s | 90s | 13/min | 120MB |
| Competitive | 45s | 90s | 13/min | 100MB |
| News | 30s | 60s | 20/min | 100MB |
| Market Data | 15s | 30s | 40/min | 80MB |
| Investment Summary | 30s | 60s | 20/min | 100MB |
| Knowledge Graph | 30s | 60s | 20/min | 150MB |
| Portfolio | 30s | 60s | 20/min | 120MB |
| Patterns | 30s | 60s | 20/min | 100MB |
| Alerts | 15s | 30s | 40/min | 50MB |
| Analytics | 60s | 120s | 10/min | 200MB |
| Historical | 45s | 90s | 13/min | 100MB |
| Cross-Agent Memory | 10s | 30s | 60/min | 50MB |
| Research Planner | 5s | 15s | 120/min | 30MB |

---

## Error Handling & Resilience

### Retry Logic
```python
async def _call_with_retry(self, func, *args, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except TransientError as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Circuit Breaker Integration
```python
from middleware.circuit_breaker import CircuitBreaker

@circuit_breaker(failure_threshold=5, timeout=60)
async def call_external_api(self, endpoint: str, payload: Dict) -> Dict:
    return await self.http_client.post(endpoint, json=payload)
```

---

*Document Version: 1.0*  
*Last Updated: 2026-07-18*  
*Platform: Agentic Financial Intelligence Platform v1.7.0-phase8*