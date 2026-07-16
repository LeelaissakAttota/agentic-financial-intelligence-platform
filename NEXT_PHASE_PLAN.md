# NEXT_PHASE_PLAN.md - Phase 2: Real News Intelligence Agent

## Phase 2: Real News Intelligence Agent

### Objective
Build an enterprise-grade News Intelligence System that collects REAL financial news from multiple providers with automatic fallback.

---

## Providers (Priority Order)

| Priority | Provider | Type | Credentials Needed | Rate Limits |
|----------|----------|------|-------------------|-------------|
| 1 | Yahoo Finance News | RSS/API | None | ~100/min |
| 2 | Finnhub News | REST API | FINNHUB_API_KEY | 60/min |
| 3 | Alpha Vantage News | REST API | ALPHA_VANTAGE_API_KEY | 5/min, 500/day |
| 4 | NewsAPI.org | REST API | NEWSAPI_KEY | 100/day (free) |
| 5 | RSS Feeds | RSS | None | Unlimited |
| 6 | Google News RSS | RSS | None | Unlimited |

---

## Implementation Plan

### Week 1: Core Infrastructure
- [ ] Create `data/news/` package structure
  - [ ] `schemas.py` - Pydantic models for NewsArticle, NewsSummary, etc.
  - [ ] `providers.py` - Base class + 6 provider implementations
  - [ ] `cache.py` - 10-minute TTL cache
  - [ ] `adapter.py` - Bridge to NewsAgent interface
- [ ] Create `data/news/__init__.py` with exports
- [ ] Add dependencies: `feedparser`, `beautifulsoup4`, `aiohttp`

### Week 2: Provider Implementation
- [ ] YahooFinanceNewsProvider (RSS + yfinance news)
- [ ] FinnhubNewsProvider (REST API)
- [ ] AlphaVantageNewsProvider (REST API)
- [ ] NewsAPIProvider (REST API)
- [ ] RSSProvider (generic + MarketWatch, CNBC, Bloomberg feeds)
- [ ] GoogleNewsRSSProvider (RSS)
- [ ] CompositeNewsProvider with fallback chain

### Week 3: News Processing Pipeline
- [ ] Article deduplication (title + content similarity)
- [ ] Relevance ranking (recency + source credibility + keyword match)
- [ ] Sentiment scoring per article (Positive/Negative/Neutral + confidence)
- [ ] Entity extraction (companies, tickers, CEOs, products, countries)
- [ ] Event detection (earnings, M&A, lawsuits, product launches, guidance)
- [ ] Importance scoring (market impact + freshness + confidence)

### Week 4: NewsAgent Integration
- [ ] Create `agents/news_agent/agent.py` with real provider adapter
- [ ] Update NewsAgent to use real providers
- [ ] Update `agents/news_agent/schemas.py` for output format
- [ ] Register in `api/main.py`
- [ ] Add mock provider support for tests

### Week 5: Testing & Integration
- [ ] Unit tests for all providers
- [ ] Integration tests with real APIs
- [ ] Deduplication tests
- [ ] Sentiment accuracy tests
- [ ] Fallback chain tests
- [ ] End-to-end pipeline test

---

## Data Structures

### NewsArticle
```python
class NewsArticle(BaseModel):
    title: str
    summary: str
    url: str
    source: NewsSource
    published_at: datetime
    sentiment: SentimentLabel
    confidence: float
    companies: List[str]
    categories: List[NewsCategory]
```

### NewsSummary (Output)
```python
class NewsSummary(BaseModel):
    articles: List[NewsArticle]
    key_events: List[str]
    bullish_signals: List[str]
    bearish_signals: List[str]
    top_risks: List[str]
    opportunities: List[str]
    overall_sentiment: str
    sentiment_distribution: Dict[str, float]
```

### Event Detection Types
- EARNINGS
- GUIDANCE
- MERGERS_ACQUISITIONS
- PRODUCT_LAUNCH
- LAWSUIT
- SEC_INVESTIGATION
- MANAGEMENT_CHANGE
- DIVIDEND
- STOCK_SPLIT
- PARTNERSHIP

---

## Test Companies
- Apple (AAPL)
- Microsoft (MSFT)
- NVIDIA (NVDA)
- Tesla (TSLA)
- Amazon (AMZN)
- Meta (META)
- Netflix (NFLX)
- AMD (AMD)
- Intel (INTC)
- Google (GOOGL)

---

## Files to Create/Modify

### New Files
```
data/news/
├── __init__.py
├── schemas.py
├── providers.py
├── cache.py
└── adapter.py

agents/news_agent/
├── agent.py (updated)
├── schemas.py (updated)
└── prompts.py (updated)
```

### Modified Files
- `requirements.txt` - add feedparser, beautifulsoup4
- `api/main.py` - register NewsAgent
- `tests/test_news_agent.py` - update mocks

---

## Dependencies

```txt
feedparser==6.0.12
beautifulsoup4==4.15.0
```

---

## Acceptance Criteria
- [ ] All 6 providers implemented with fallback
- [ ] Real news fetched for all 10 test companies
- [ ] No mock data in production path
- [ ] Deduplication works (same story from multiple sources)
- [ ] Sentiment scoring works (positive/negative/neutral)
- [ ] Entity extraction finds tickers and company names
- [ ] Event detection identifies earnings, M&A, etc.
- [ ] Fallback chain works when primary fails
- [ ] 10-minute cache TTL respected
- [ ] All tests pass (target: 300+ tests)
- [ ] Docker build successful
- [ ] API returns structured NewsSummary

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Rate limiting | High | Medium | Implement exponential backoff, cache aggressively |
| API changes | Medium | High | Version detection, graceful degradation |
| Sentiment accuracy | Medium | Medium | Use ensemble (VADER + LLM), confidence thresholds |
| Duplicate detection | Medium | Medium | Fuzzy matching on title + first 200 chars |
| No API keys | Medium | Low | Priority 1-3 need keys; 4-6 work without |

---

## Timeline Estimate

| Week | Deliverable |
|------|-------------|
| 1 | Core infrastructure + provider base classes |
| 2 | All 6 providers + composite fallback |
| 3 | Processing pipeline (dedup, sentiment, entities, events) |
| 4 | NewsAgent integration + API registration |
| 5 | Testing + Docker + documentation |

**Total: ~5 weeks**

---

## Success Metrics
- [ ] 300+ tests passing
- [ ] <500ms average news fetch time
- [ ] 95%+ sentiment accuracy on labeled data
- [ ] 90%+ entity extraction F1
- [ ] 100% fallback coverage
- [ ] Zero mock data in production