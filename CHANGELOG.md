# CHANGELOG.md - Agentic Financial Intelligence Platform

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0-phase1] - 2026-07-16

### Added
- **Real-time Market Data Pipeline** - Multi-provider market data integration
  - Yahoo Finance provider (yfinance) with thread-pool executor for async compatibility
  - Alpha Vantage provider with rate limiting (5/min, 500/day)
  - Finnhub provider with 60 calls/min rate limit
  - Composite provider with automatic fallback chain and 5-minute TTL caching
  
- **Market Data Adapter** - Converts real provider data to CompleteMarketData format
  - Technical indicator calculations: RSI (14), SMA (20/50/200), MACD, Bollinger Bands
  - Fundamentals normalization across providers
  - Company info and historical price data adaptation

- **MarketAgent Real Data Integration** - Replaces mock data with live market data
  - Validates symbol from context (ticker or company name)
  - Fetches real-time quotes, fundamentals, historical prices, company info
  - LLM-powered analysis with fallback to rule-based analysis

- **ManagerAgent Ticker Passing** - Properly passes ticker symbol to MarketAgent via context

- **News Intelligence System** (Foundation)
  - 6 news providers: Yahoo Finance, Finnhub, Alpha Vantage, NewsAPI, RSS, Google News RSS
  - Article deduplication, sentiment scoring, entity extraction, event detection
  - News cache with 10-minute TTL
  - Company name/ticker extraction from articles

- **Async LLM Interface** - All agents now use `agenerate_json()` for async structured output
  - BaseLLMClient with async-first design and sync wrappers
  - OpenRouterClient with full async support
  - Retry logic with exponential backoff for both sync and async

- **NumPy 2.0 Compatibility** - Upgraded chromadb to 1.5.9, added sentence-transformers

### Fixed
- MarketAgent fallback analysis TypeError with None/float values
- MarketAgent NoneType format errors in narrative generation
- MarketAgent analyst_rating type mismatch (float vs string from Yahoo Finance)
- All agent test mocks updated to implement `agenerate_json()` async method
- FinancialReportAgent test signature mismatch (context dict vs ticker kwarg)
- RiskAgent, CompetitorAgent, SentimentAgent test assertions using correct mock flags

### Changed
- Updated MarketAgent to use real data adapter instead of mock provider
- Updated ManagerAgent to pass ticker symbol via context to MarketAgent
- Updated requirements.txt with yfinance, aiohttp, feedparser, beautifulsoup4
- Upgraded chromadb from 0.5.5 to 1.5.9 for NumPy 2.0 compatibility

## [0.1.0] - 2026-07-13

### Added
- Initial project structure with 7-agent architecture
- Mock market data provider for development
- Basic RAG pipeline with ChromaDB
- FastAPI REST API with background task processing
- Streamlit dashboard
- PostgreSQL persistence
- Docker Compose deployment
- OpenRouter LLM integration with cost tracking