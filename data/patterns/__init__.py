"""
Patterns Module - Phase 5: Knowledge Persistence & Advanced Analytics

Provides pattern detection, storage, and analysis for financial time series data.
"""

from data.patterns.patterns import (
    PatternType,
    PatternConfidence,
    Pattern,
    PatternMatch,
    PatternBackend,
    PostgresPatternBackend,
    PatternDetector,
    PatternAnalytics,
    create_pattern_detector,
)

__all__ = [
    "PatternType",
    "PatternConfidence",
    "Pattern",
    "PatternMatch",
    "PatternBackend",
    "PostgresPatternBackend",
    "PatternDetector",
    "PatternAnalytics",
    "create_pattern_detector",
]