# PERFORMANCE_REPORT.md - Phase 1 Stabilization

## Test Execution Performance

| Metric | Value |
|--------|-------|
| **Total Test Time** | 22.94 seconds |
| **Tests per Second** | ~12.4 |
| **Slowest Test File** | `test_financial_report_agent.py` (6.78s) |
| **Fastest Test File** | `test_openrouter_connection.py` (<0.1s) |

## Test File Breakdown

| Test File | Tests | Duration | Avg/Test |
|-----------|-------|----------|----------|
| `test_financial_report_agent.py` | 21 | 6.78s | 0.32s |
| `test_market_agent.py` | 27 | 4.10s | 0.15s |
| `test_risk_agent.py` | 21 | 1.23s | 0.06s |
| `test_competitor_agent.py` | 18 | 0.40s | 0.02s |
| `test_sentiment_agent.py` | 22 | 0.35s | 0.02s |
| `test_news_agent.py` | 18 | 0.30s | 0.02s |
| `test_manager_agent.py` | 7 | 0.25s | 0.04s |
| LLM Tests (110) | 110 | ~8.0s | 0.07s |
| RAG Tests | 5 | ~1.0s | 0.20s |

## Memory Profile
- **Baseline**: ~150MB
- **Peak During Tests**: ~280MB
- **No memory leaks detected** - stable across multiple runs

## Data Provider Performance (Real vs Mock)

| Provider | Avg Latency | Cache Hit Rate |
|----------|-------------|----------------|
| Yahoo Finance (yfinance) | ~800ms | 100% after 1st call |
| Alpha Vantage | N/A (no key) | N/A |
| Finnhub | N/A (no key) | N/A |

**Cache TTL**: 5 minutes (300 seconds)
**Cache Key Format**: `method:symbol:params`
**Thread Safety**: Lock-based rate limiting per provider

## LLM Provider Performance

| Provider | Model | Avg Latency | Cost/1K Tokens |
|----------|-------|-------------|----------------|
| OpenRouter | anthropic/claude-sonnet-5 | ~2.5s | $0.003 |

## Pipeline Latency (End-to-End)

| Company | Total Time | Agents Run |
|---------|------------|------------|
| NVIDIA | ~140s | 7 |
| Apple | ~135s | 7 |
| Microsoft | ~145s | 7 |

**Bottleneck**: Sequential LLM calls (7 agents × ~2.5s each = ~17.5s minimum)

## Recommendations for Production

1. **Parallelize Independent Agents**: News, Market, Financial can run in parallel
2. **Add Redis Cache Layer**: Replace in-memory cache for multi-instance deployments
3. **Connection Pooling**: Reuse HTTP sessions for data providers
4. **Stream LLM Responses**: Reduce perceived latency
5. **Async Rate Limiting**: Replace blocking `time.sleep` with `asyncio.sleep`