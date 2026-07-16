# Agent Architecture Specification

## Overview
This document specifies the architecture for the AI Financial Research Analyst Agent system. It defines agent responsibilities, communication protocols, data contracts, and optimization strategies for a multi-agent system that generates structured investment research reports.

## System Architecture

```
User Query → [Manager Agent] 
              │
              ├──→ [News Agent] ────┐
              ├──→ [Market Data Agent]──┐
              ├──→ [Financial Report Agent]──┐
              ├──→ [Sentiment Agent] ◄───────┘
              ├──→ [Competitor Analysis Agent]─┐
              ├──→ [Risk Agent] ◄──────────────┘
              │
              └→ [Investment Summary Agent] → Final Report
```

### Core Principles
1. **Separation of Concerns**: Each agent handles one distinct domain
2. **Schema-First Communication**: All inter-agent data exchange uses strictly defined JSON schemas
3. **Model Routing**: Tasks directed to appropriate LLMs based on complexity
4. **Fault Tolerance**: System gracefully handles partial failures
5. **Token Efficiency**: Optimized prompting and response formatting

## Agent Responsibilities

### 1. Manager Agent (Orchestrator)
**Role**: Central coordinator that decomposes user requests, manages worker agents, and synthesizes results.

**Responsibilities**:
- Parse user input to extract company identifier (name/ticker)
- Determine optimal execution order (parallel vs sequential)
- Dispatch tasks to worker agents via standardized interfaces
- Validate worker outputs against JSON schemas
- Handle timeouts, retries, and partial failures
- Aggregate results for Investment Summary Agent
- Persist execution metadata to database

**Interfaces**:
- Input: User query string (e.g., `"Analyze NVIDIA"`)
- Output: Structured data package for Investment Summary Agent
- Internal: Async task dispatch with timeout management

### 2. News Agent
**Role**: Collects and analyzes recent news sentiment.

**Responsibilities**:
- Query news APIs for last 7 days of company coverage
- Deduplicate and rank articles by relevance/recency
- Generate concise summaries (1-2 sentences) for each article
- Classify sentiment impact: Positive/Negative/Neutral
- Return top N articles with metadata

**Input**: Company identifier
**Output**: 
```json
{
  "articles": [
    {
      "title": "string",
      "source": "string",
      "date": "ISO 8601 timestamp",
      "summary": "string",
      "relevance_score": 0.0-1.0,
      "impact": "positive|negative|neutral",
      "url": "string (optional)"
    }
  ],
  "total_analyzed": integer
}
```

### 3. Market Data Agent
**Role**: Retrieves and interprets current market metrics.

**Responsibilities**:
- Fetch real-time/near-real-time market data:
  - Current price, volume, market cap
  - 52-week high/low, day's change
  - Key ratios: P/E, P/B, EPS, dividend yield
- Ensure numerical data comes strictly from API (no LLM hallucination)
- Generate brief factual interpretation from verified data

**Input**: Company identifier
**Output**:
```json
{
  "price": {
    "current": number,
    "change_24h": number,
    "change_24h_percent": number,
    "52_week_high": number,
    "52_week_low": number
  },
  "volume": {
    "current": integer,
    "average_30d": integer
  },
  "valuation": {
    "market_cap": number,
    "pe_ratio": number|null,
    "pb_ratio": number|null,
    "eps_ttm": number
  },
  "interpretation": "string (brief, fact-based summary)"
}
```

### 4. Financial Report Agent (RAG-Based)
**Role**: Extracts insights from company's financial reports using retrieval-augmented generation.

**Responsibilities**:
- Load and process relevant 10-K/annual report documents
- Retrieve top-K relevant chunks for each financial question
- Generate grounded answers with explicit citations
- Cover: revenue growth, profit margins, debt levels, cash flow, segment performance

**Input**: Company identifier (to locate correct filing)
**Output**:
```json
{
  "financial_metrics": [
    {
      "metric": "revenue_growth_yoy",
      "value": number,
      "period": "string (e.g., 'FY2023')",
      "citation_ids": ["chunk_123", "chunk_456"],
      "confidence": 0.0-1.0
    },
    {
      "metric": "profit_margin_net",
      "value": number,
      "period": "string",
      "citation_ids": ["chunk_789"],
      "confidence": 0.0-1.0
    }
    // ... additional metrics
  ]
}
```

### 5. Sentiment Agent
**Role**: Aggregates sentiment signals from news and other sources.

**Responsibilities**:
- Consume News Agent output (primary input)
- Calculate composite sentiment score (-1.0 to +1.0)
- Identify top 3 sentiment-driving factors
- Provide confidence assessment and explanation

**Input**: News Agent output
**Output**:
```json
{
  "sentiment_score": number (-1.0 to +1.0),
  "sentiment_label": "negative|neutral|positive",
  "confidence": 0.0-1.0,
  "drivers": [
    {
      "factor": "string (e.g., 'earnings_beat', 'regulatory_concern')",
      "impact": "positive|negative",
      "explanation": "string",
      "weight": number (0.0-1.0)
    }
  ]
}
```

### 6. Competitor Analysis Agent
**Role**: Analyzes competitive landscape and positioning.

**Responsibilities**:
- Identify 2-4 primary competitors (same sector, similar market cap)
- Collect Market Agent-style metrics for each competitor
- Generate side-by-side comparison table
- Provide narrative analysis of competitive advantages/threats

**Input**: Company identifier
**Output**:
```json
{
  "target_company": "string",
  "competitors": [
    {
      "name": "string",
      "metrics": { /* Same structure as Market Agent output */ },
      "positioning_summary": "string"
    }
  ],
  "comparison_table": [
    {
      "company": "string",
      "current_price": number,
      "market_cap": number,
      "pe_ratio": number|null,
      "revenue_growth": number
      // ... other comparable metrics
    }
  ],
  "strategic_assessment": "string"
}
```

### 7. Risk Agent
**Role**: Synthesizes risk factors from all available intelligence.

**Responsibilities**:
- Consume outputs from News, Market, Financial Report, and Competitor agents
- Categorize risks: Market, Regulatory, Competitive, Operational, Financial, etc.
- Assess severity and likelihood for each risk
- Provide evidence-based justification

**Input**: Combined outputs from 4 upstream agents
**Output**:
```json
{
  "risks": [
    {
      "category": "string (e.g., 'Market', 'Regulatory')",
      "description": "string",
      "severity": "low|medium|high",
      "likelihood": "low|medium|high",
      "justification": "string",
      "source_agents": ["string"]  // Which agents contributed to this risk
    }
  ],
  "overall_risk_score": number (0.0-1.0)
}
```

### 8. Investment Summary Agent
**Role**: Produces final synthesized investment recommendation.

**Responsibilities**:
- Consume complete analysis package from Manager Agent
- Generate investment thesis with supporting evidence
- Identify key catalysts (positive drivers) and risks (negative factors)
- Provide clear, actionable summary with appropriate disclaimers

**Input**: Aggregated results from all prior agents
**Output**:
```json
{
  "recommendation": "buy|hold|sell",
  "confidence": 0.0-1.0,
  "investment_thesis": "string",
  "key_catalysts": ["string"],
  "key_risks": ["string"],
  "time_horizon": "short|medium|long",
  "suggested_allocation": "string (optional, e.g., '1-5% of portfolio')",
  "disclaimer": "string (standard investment advice disclaimer)"
}
```

## Communication Protocol

### Message Format
All inter-agent communication uses JSON objects adhering to the schemas defined above. Messages are passed as dictionaries between agent methods.

### Interaction Flow
1. **Manager → Worker**:
   - Manager invokes `worker.run(company_id: str, context: dict)`
   - Context contains outputs from prerequisite workers (None for independent agents)
   - Worker returns `(result_dict, usage_metadata)` where:
     - `result_dict`: Validated per agent's schema
     - `usage_metadata`: Token usage and cost tracking

2. **Worker → Manager**:
   - Returns structured result + usage stats
   - On error: Returns error object with `error: true` and diagnostic message

3. **Manager Internal Coordination**:
   - Uses asyncio for concurrent execution where dependencies allow
   - Implements per-agent timeout wrappers (default 30s)
   - Validates outputs before proceeding to dependent agents
   - Maintains execution history for debugging

### Error Handling Pattern
```python
async def safe_agent_call(agent, company_id, context):
    try:
        result, usage = await asyncio.wait_for(
            agent.run(company_id, context),
            timeout=agent.timeout
        )
        
        if not result.get("success", True):  # Assuming success flag in response
            logger.warning(f"{agent.name} returned error: {result.get('error')}")
            return {"error": True, "message": result.get("error")}, usage
            
        return result, usage
        
    except asyncio.TimeoutError:
        logger.error(f"{agent.name} timed out after {agent.timeout}s")
        return {"error": True, "message": "timeout"}, get_empty_usage()
        
    except Exception as e:
        logger.error(f"{agent.name} failed: {str(e)}")
        return {"error": True, "message": str(e)}, get_empty_usage()
```

## Data Contracts

### Base Response Envelope
All agents wrap their responses in this structure:
```json
{
  "success": boolean,
  "data": object | null,
  "error": {
    "message": string,
    "code": string
  } | null,
  "metadata": {
    "agent": string,
    "timestamp": "ISO 8601 string",
    "model_used": string,
    "token_usage": {
      "prompt_tokens": integer,
      "completion_tokens": integer,
      "total_tokens": integer,
      "estimated_cost_usd": float
    }
  }
}
```

### Validation Rules
- **Presence**: Required fields must exist
- **Type**: Fields must match specified JSON types
- **Constraints**: 
  - Scores/probabilities: 0.0-1.0 range
  - Enumerated values: Must match allowed strings
  - Dates: Valid ISO 8601 format
  - Arrays: Must contain valid objects per schema

## Model Selection Strategy

### Decision Framework
| Task Complexity | Model Choice | Rationale |
|----------------|--------------|-----------|
| **High** (Reasoning, synthesis, judgment) | `PRIMARY_MODEL` (anthropic/claude-3.5-sonnet) | Complex analysis requiring contextual understanding |
| **Medium** (Analysis, classification, summarization) | `PRIMARY_MODEL` | Requires nuanced language understanding |
| **Low** (Data extraction, formatting, simple transformation) | `FAST_MODEL` (anthropic/claude-3-haiku) | Primarily structured data handling |

### Agent-Specific Assignments
| Agent | Complexity | Model | Justification |
|-------|------------|-------|---------------|
| Manager Agent | High (orchestration) | PRIMARY | Complex workflow optimization decisions |
| News Agent | Medium (impact classification) | PRIMARY | Requires understanding of linguistic nuance |
| Market Data Agent | Low (data retrieval/formatting) | FAST | Minimal language generation needed |
| Financial Report Agent | High (RAG synthesis) | PRIMARY | Complex reasoning over retrieved text |
| Sentiment Agent | Medium (opinion aggregation) | PRIMARY | Requires semantic understanding of sentiment |
| Competitor Agent | Medium (comparative analysis) | PRIMARY | Involves reasoning across multiple data points |
| Risk Agent | High (multi-factor synthesis) | PRIMARY | Integrates diverse inputs into coherent assessment |
| Investment Summary Agent | High (final recommendation) | PRIMARY | High-stakes synthesis requiring balanced judgment |

### Fallback Protocol
1. Primary model failure → Retry with exponential backoff (max 3 attempts)
2. Persistent failures → Attempt with FAST model (for applicable agents)
3. Critical agent failure (Financial Report, Investment Summary) → Alert for manual intervention
4. All fallback attempts logged for cost/performance analysis

## Token Optimization Strategy

### Input Optimization Techniques
- **Context Minimization**: Pass only essential data to each agent
  - Example: Market Agent receives only company ID, not full news feed
  - Example: Sentiment Agent receives only news articles (not raw prices)
- **Prompt Engineering**:
  - System prompts are highly specific and task-focused
  - Zero-shot preferred in production (few-shot only for development/debugging)
  - Dynamic prompt length adjustment based on available context window

### Output Optimization Techniques
- **Schema Enforcement**: Strict Pydantic validation prevents verbose responses
- **Token Budgets**:
  - MAX_TOKENS configured per agent based on expected output complexity
  - Output truncation with warning if approaching limits (rare with proper prompting)
- **Response Compression**:
  - Numerical values transmitted as raw numbers (not strings)
  - Homogeneous data stored in arrays rather than objects
  - Timestamps in standardized ISO format
  - Repeated structural elements minimized through schema design

### Agent-Specific Token Budgets
| Agent | Max Input Tokens | Max Output Tokens | Rationale |
|-------|------------------|-------------------|-----------|
| Manager Agent | 2,000 | 1,000 | Planning phase needs context but output is structured |
| News Agent | 3,000 | 800 | Must process multiple articles for summarization |
| Market Data Agent | 500 | 300 | Minimal text processing requirements |
| Financial Report Agent | 4,000 | 1,000 | RAG context + synthesis requirements |
| Sentiment Agent | 2,000 | 400 | Scoring + explanation generation |
| Competitor Agent | 2,500 | 600 | Multiple data points requiring synthesis |
| Risk Agent | 3,000 | 800 | Integrating four distinct information sources |
| Investment Summary Agent | 3,500 | 800 | Final synthesis of all analytical inputs |

### Monitoring Framework
- Per-call token usage logged to structured JSON logs
- Daily aggregation of actual vs. budgeted token consumption
- Monthly review of prompt effectiveness and output quality
- Dynamic adjustment of model selection thresholds based on complexity scoring

## Error Handling & Resilience Strategy

### Error Classification
1. **Transient Errors** (Network, rate limits, temporary unavailability):
   - Automatic retry with exponential backoff (base 1s, max 10s)
   - Full jitter to prevent thundering herd problems
   - Maximum 3 retry attempts per operation

2. **Validation Errors** (Schema violations, missing required fields):
   - Trigger prompt refinement attempt (max 2 rephrasing)
   - If persistent, escalate as agent failure
   - Detailed logging of validation failure reasons

3. **Agent-Specific Failures**:
   - Individual agent timeouts (configurable, default 30s)
   - Failed agents return error status with diagnostic information
   - Pipeline continues with available data (degraded mode operation)
   - Missing data clearly flagged in final report

4. **Systemic Failures**:
   - Circuit breaker pattern for persistent downstream service issues
   - Fallback to cached/stub data in development/test environments
   - Production degradation: Report generation continues with data quality warnings

### Data Integrity Safeguards
- **Pre-flight Validation**: 
  - Input sanitization before agent invocation
  - Company ID validation against known ticker/exchange databases
  
- **Post-flight Validation**:
  - Mandatory schema validation using Pydantic models
  - Range checks (e.g., P/E ratio > 0, probabilities in [0,1])
  - Temporal validity (no future dates in financial data)
  - Cross-field consistency (e.g., market cap ≈ price × shares outstanding)

- **Degraded Operation Modes**:
  - **Level 1 (Partial Data)**: Missing non-critical sections marked as `data_unavailable: true`
  - **Level 2 (Critical Path)**: If Financial Report or Market Data fails completely, trigger manual review workflow
  - **Level 3 (Systemic)**: Queue job for manual intervention with detailed diagnostics

### Logging & Observability
- Structured JSON logging for all agent interactions
- Correlation IDs to trace request flow through agent chain
- Timing metrics for each stage of processing
- Resource utilization (token counts, API call frequencies)
- Error categorization for trend analysis and preventive maintenance

## Implementation Dependencies

### Core Libraries
- **pydantic**: Data validation and settings management
- **tenacity**: Retry logic with exponential backoff
- **structlog**: Structured logging for observability
- **asyncio**: Concurrent agent execution
- **openai**: Official client for OpenRouter API compatibility

### Orchestration Framework
- **LangGraph** (planned): State graph workflow management
  - Enables conditional routing based on intermediate results
  - Provides checkpointing for long-running analyses
  - Supports human-in-the-loop intervention points

### Data Persistence
- **PostgreSQL**: Execution metadata, run history, cached results
- **ChromaDB**: Vector storage for RAG operations (Financial Report Agent)
- **Redis** (planned): Short-term caching for frequently accessed data

### Testing Strategy
- **Unit Tests**: 
  - Mock LLM responses using predefined fixtures
  - Validate schema compliance and error handling
  - Test edge cases and boundary conditions
  
- **Integration Tests**:
  - Real LLM calls (marked `@pytest.mark.integration`)
  - Use VCR.py or similar to record/replay HTTP interactions
  - Validate end-to-end data flow correctness
  
- **Performance Tests**:
  - Load testing with concurrent analysis requests
  - Latency measurement per agent stage
  - Resource utilization profiling

### Future Extension Points
1. **Dynamic Agent Spawning**: Create specialized agents based on query complexity analysis
2. **Reinforcement Learning Loop**: Optimize workflow selection based on historical outcome quality
3. **Real-time Progress Reporting**: WebSocket interface for UI updates during long analyses
4. **A/B Testing Framework**: Systematic prompt and model variation testing
5. **Cost-Aware Routing**: Dynamic model selection based on real-time cost/quality tradeoffs

---
*This specification establishes the immutable contract between all system components. Implementation must strictly adhere to these interfaces, data formats, and behavioral guidelines.*