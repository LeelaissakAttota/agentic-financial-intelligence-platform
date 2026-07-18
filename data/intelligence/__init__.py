"""
Historical Intelligence Module - Phase 5: Knowledge Persistence & Advanced Analytics

Provides historical data storage, trend analysis, company evolution tracking, and peer comparison.
"""

from data.intelligence.historical import (
    IntelligenceBackend,
    PostgresIntelligenceBackend,
    HistoricalReport,
    HistoricalNews,
    HistoricalFiling,
    HistoricalSentiment,
    HistoricalIntelligence,
    PostgresIntelligenceBackend,
    create_historical_intelligence,
)

__all__ = [
    "IntelligenceBackend",
    "PostgresIntelligenceBackend",
    "HistoricalReport",
    "HistoricalNews",
    "HistoricalFiling",
    "HistoricalSentiment",
    "HistoricalIntelligence",
    "PostgresIntelligenceBackend",
    "create_historical_intelligence",
]