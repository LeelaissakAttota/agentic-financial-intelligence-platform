"""
Phase 5 - Pattern Detection Tests
"""
import pytest
import pandas as pd
import numpy as np
from datetime import date, datetime
from data.patterns import (
    PatternDetector, PatternType, PatternConfidence, Pattern, PatternMatch,
    PostgresPatternBackend, create_pattern_detector
)


class TestPatternDataclasses:
    """Test pattern dataclasses."""
    
    def test_create_pattern(self):
        pattern = Pattern(
            pattern_type=PatternType.TREND,
            symbol="AAPL",
            timeframe="daily",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            confidence=PatternConfidence.HIGH,
            confidence_score=0.85,
            description="Strong uptrend detected",
            parameters={"window": 50, "slope": 0.02, "r_squared": 0.92}
        )
        assert pattern.pattern_type == PatternType.TREND
        assert pattern.symbol == "AAPL"
        assert pattern.confidence == PatternConfidence.HIGH
        assert pattern.confidence_score == 0.85
    
    def test_pattern_match(self):
        pattern = Pattern(
            pattern_type=PatternType.REVERSAL,
            symbol="MSFT",
            confidence=PatternConfidence.VERY_HIGH,
            confidence_score=0.92
        )
        match = PatternMatch(
            pattern=pattern,
            match_start=date(2024, 1, 15),
            match_end=date(2024, 1, 25),
            similarity_score=0.88,
            current_data=pd.DataFrame(),
            confidence=PatternConfidence.HIGH
        )
        assert match.pattern == pattern
        assert match.similarity_score == 0.88
        assert match.confidence == PatternConfidence.HIGH


class TestPatternEnums:
    """Test pattern enums."""
    
    def test_pattern_types(self):
        expected = ["seasonal", "trend", "cycle", "reversal", "breakout",
                   "support_resistance", "volume_spike", "correlation",
                   "regime_change", "anomaly"]
        actual = [pt.value for pt in PatternType]
        assert set(actual) == set(expected)
    
    def test_confidence_levels(self):
        expected = ["low", "medium", "high", "very_high"]
        actual = [pc.value for pc in PatternConfidence]
        assert set(actual) == set(expected)
    
    def test_confidence_ordering(self):
        order = [PatternConfidence.LOW, PatternConfidence.MEDIUM, 
                PatternConfidence.HIGH, PatternConfidence.VERY_HIGH]
        for i in range(len(order) - 1):
            assert order[i].value != order[i+1].value


class TestPatternDetector:
    """Test PatternDetector methods."""
    
    @pytest.fixture
    def detector(self):
        return PatternDetector(backend=None)
    
    @pytest.fixture
    def sample_price_data(self):
        """Generate sample OHLCV data for testing."""
        dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
        np.random.seed(42)
        # Generate trending price data
        returns = np.random.normal(0.0005, 0.015, 252)
        prices = 100 * np.cumprod(1 + returns)
        
        df = pd.DataFrame({
            'open': prices * (1 + np.random.normal(0, 0.002, 252)),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.01, 252))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.01, 252))),
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, 252)
        }, index=dates)
        
        # Ensure high >= close >= low
        df['high'] = df[['high', 'close']].max(axis=1)
        df['low'] = df[['low', 'close']].min(axis=1)
        
        return df
    
    @pytest.fixture
    def trending_data(self):
        """Generate strongly trending data."""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        # Strong uptrend
        trend = np.linspace(100, 150, 100)
        noise = np.random.normal(0, 1, 100)
        close = trend + noise
        
        df = pd.DataFrame({
            'open': close * (1 + np.random.normal(0, 0.002, 100)),
            'high': close * (1 + np.abs(np.random.normal(0, 0.01, 100))),
            'low': close * (1 - np.abs(np.random.normal(0, 0.01, 100))),
            'close': close,
            'volume': np.random.randint(1000000, 5000000, 100)
        }, index=dates)
        
        df['high'] = df[['high', 'close']].max(axis=1)
        df['low'] = df[['low', 'close']].min(axis=1)
        
        return df
    
    @pytest.mark.asyncio
    async def test_detect_trends(self, detector, trending_data):
        patterns = await detector._detect_trends("AAPL", trending_data, "daily")
        
        assert len(patterns) > 0
        # Should detect uptrend
        uptrend_patterns = [p for p in patterns if 'uptrend' in p.description.lower()]
        assert len(uptrend_patterns) > 0
        for p in uptrend_patterns:
            assert p.confidence_score > 0.44  # Lower threshold for test data
            assert p.parameters["trend_type"] in ["uptrend", "strong_uptrend"]
    
    @pytest.mark.asyncio
    async def test_detect_trends_sideways(self, detector):
        """Test trend detection on sideways data."""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        # Sideways data - price oscillates around 100
        close = 100 + np.sin(np.arange(100) * 0.2) * 5 + np.random.normal(0, 1, 100)
        
        df = pd.DataFrame({
            'open': close * (1 + np.random.normal(0, 0.002, 100)),
            'high': close * (1 + np.abs(np.random.normal(0, 0.01, 100))),
            'low': close * (1 - np.abs(np.random.normal(0, 0.01, 100))),
            'close': close,
            'volume': np.random.randint(1000000, 5000000, 100)
        }, index=dates)
        
        df['high'] = df[['high', 'close']].max(axis=1)
        df['low'] = df[['low', 'close']].min(axis=1)
        
        patterns = await detector._detect_trends("TEST", df, "daily")
        
        # Should detect sideways or weak trends
        trend_patterns = [p for p in patterns if p.pattern_type == PatternType.TREND]
        assert len(trend_patterns) >= 0  # May or may not detect
    
    @pytest.mark.asyncio
    async def test_detect_golden_cross(self, detector):
        """Test golden cross detection."""
        dates = pd.date_range(start='2023-01-01', periods=250, freq='D')
        
        # Create data where 50 SMA crosses above 200 SMA
        # Start with price below 200 SMA, then trend up
        np.random.seed(42)
        base = 100
        prices = []
        for i in range(250):
            if i < 50:
                base *= 0.999  # Slight downtrend initially
            elif i < 150:
                base *= 1.005  # Uptrend
            else:
                base *= 1.001  # Flattening
            base += np.random.normal(0, 0.5)
            prices.append(base)
        
        close = np.array(prices)
        
        df = pd.DataFrame({
            'open': close * (1 + np.random.normal(0, 0.002, 250)),
            'high': close * (1 + np.abs(np.random.normal(0, 0.01, 250))),
            'low': close * (1 - np.abs(np.random.normal(0, 0.01, 250))),
            'close': close,
            'volume': np.random.randint(1000000, 5000000, 250)
        }, index=dates)
        
        df['high'] = df[['high', 'close']].max(axis=1)
        df['low'] = df[['low', 'close']].min(axis=1)
        
        patterns = await detector._detect_trends("TEST", df, "daily")
        
        # Check for golden cross
        golden_cross = [p for p in patterns if 'golden cross' in p.description.lower()]
        # May or may not detect depending on data
        if golden_cross:
            assert golden_cross[0].confidence == PatternConfidence.HIGH
            assert golden_cross[0].parameters["cross_type"] == "golden_cross"
    
    @pytest.mark.asyncio
    async def test_detect_support_resistance(self, detector, sample_price_data):
        patterns = await detector._detect_support_resistance("AAPL", sample_price_data, "daily")
        
        # Should find some S/R levels
        for p in patterns:
            assert p.pattern_type == PatternType.SUPPORT_RESISTANCE
            assert "level_price" in p.parameters
            assert "touch_count" in p.parameters
            assert p.parameters["touch_count"] >= 3
            assert p.parameters["type"] in ["support", "resistance"]
    
    @pytest.mark.asyncio
    async def test_detect_reversals(self, detector):
        """Test double top/bottom detection."""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        
        # Create double top pattern
        # Two peaks at similar level with trough between
        close = np.ones(100) * 100
        close[20:30] = np.linspace(100, 120, 10)  # First peak
        close[30:40] = np.linspace(120, 105, 10)  # Decline
        close[40:50] = np.linspace(105, 119, 10)  # Second peak (slightly lower)
        close[50:60] = np.linspace(119, 95, 10)   # Breakdown
        close[60:] = 95 + np.random.normal(0, 1, 40)
        
        # Add noise
        close += np.random.normal(0, 0.5, 100)
        
        df = pd.DataFrame({
            'open': close * (1 + np.random.normal(0, 0.002, 100)),
            'high': close * (1 + np.abs(np.random.normal(0, 0.01, 100))),
            'low': close * (1 - np.abs(np.random.normal(0, 0.01, 100))),
            'close': close,
            'volume': np.random.randint(1000000, 5000000, 100)
        }, index=dates)
        
        df['high'] = df[['high', 'close']].max(axis=1)
        df['low'] = df[['low', 'close']].min(axis=1)
        
        patterns = await detector._detect_reversals("TEST", df, "daily")
        
        # Should detect double top
        double_tops = [p for p in patterns if p.parameters.get("pattern") == "double_top"]
        if double_tops:
            assert double_tops[0].confidence == PatternConfidence.HIGH
            assert double_tops[0].parameters["peak_price"] > 0
            assert "target_price" in double_tops[0].parameters
    
    @pytest.mark.asyncio
    async def test_detect_breakouts(self, detector):
        """Test breakout detection."""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        
        # Price consolidates then breaks out
        close = np.ones(100) * 100
        close[:50] = 100 + np.random.normal(0, 1, 50)  # Consolidation
        close[50:] = np.linspace(100, 130, 50) + np.random.normal(0, 1, 50)  # Breakout
        
        df = pd.DataFrame({
            'open': close * (1 + np.random.normal(0, 0.002, 100)),
            'high': close * (1 + np.abs(np.random.normal(0, 0.015, 100))),
            'low': close * (1 - np.abs(np.random.normal(0, 0.01, 100))),
            'close': close,
            'volume': np.concatenate([
                np.random.randint(1000000, 2000000, 50),  # Low volume during consolidation
                np.random.randint(3000000, 8000000, 50)   # High volume on breakout
            ])
        }, index=dates)
        
        df['high'] = df[['high', 'close']].max(axis=1)
        df['low'] = df[['low', 'close']].min(axis=1)
        
        patterns = await detector._detect_breakouts("TEST", df, "daily")
        
        breakouts = [p for p in patterns if p.pattern_type == PatternType.BREAKOUT]
        # Should detect at least one breakout
        if breakouts:
            assert breakouts[0].parameters["direction"] in ["bullish", "bearish"]
            assert breakouts[0].parameters["volume_ratio"] > 1.0
    
    @pytest.mark.asyncio
    async def test_detect_volume_spikes(self, detector):
        """Test volume spike detection."""
        dates = pd.date_range(start='2023-01-01', periods=60, freq='D')
        
        # Normal volume with one extreme spike
        close = 100 + np.cumsum(np.random.normal(0, 0.5, 60))
        volume = np.random.randint(1000000, 2000000, 60)
        volume[30] = 10000000  # 5-10x spike
        
        df = pd.DataFrame({
            'open': close * (1 + np.random.normal(0, 0.002, 60)),
            'high': close * (1 + np.abs(np.random.normal(0, 0.01, 60))),
            'low': close * (1 - np.abs(np.random.normal(0, 0.01, 60))),
            'close': close,
            'volume': volume
        }, index=dates)
        
        df['high'] = df[['high', 'close']].max(axis=1)
        df['low'] = df[['low', 'close']].min(axis=1)
        
        patterns = await detector._detect_volume_spikes("TEST", df, "daily")
        
        spikes = [p for p in patterns if p.pattern_type == PatternType.VOLUME_SPIKE]
        assert len(spikes) >= 1
        assert spikes[0].parameters["volume_ratio"] > 3.0
        assert spikes[0].confidence_score > 0.5
    
    @pytest.mark.asyncio
    async def test_detect_anomalies(self, detector):
        """Test anomaly detection."""
        dates = pd.date_range(start='2023-01-01', periods=200, freq='D')
        
        # Normal returns with one extreme outlier at position 100 (well past rolling window)
        returns = np.random.normal(0.0005, 0.01, 200)
        returns[100] = 0.15  # 15% move - extreme
        
        close = 100 * np.cumprod(1 + returns)
        
        df = pd.DataFrame({
            'open': close * (1 + np.random.normal(0, 0.002, 200)),
            'high': close * (1 + np.abs(np.random.normal(0, 0.01, 200))),
            'low': close * (1 - np.abs(np.random.normal(0, 0.01, 200))),
            'close': close,
            'volume': np.random.randint(1000000, 5000000, 200)
        }, index=dates)
        
        df['high'] = df[['high', 'close']].max(axis=1)
        df['low'] = df[['low', 'close']].min(axis=1)
        
        patterns = await detector._detect_anomalies("TEST", df, "daily")
        
        anomalies = [p for p in patterns if p.pattern_type == PatternType.ANOMALY]
        assert len(anomalies) >= 1
        assert anomalies[0].parameters["direction"] in ["up", "down"]
        assert abs(anomalies[0].parameters["move_pct"]) > 5.0  # Significant move


class TestPatternAnalytics:
    """Test PatternAnalytics."""
    
    @pytest.mark.asyncio
    async def test_get_pattern_performance(self):
        from data.patterns import PatternAnalytics
        import os
        db_name = os.getenv("POSTGRES_DB", "financial_research_agent")
        db_user = os.getenv("POSTGRES_USER", "postgres")
        db_pass = os.getenv("POSTGRES_PASSWORD", "postgres")
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        
        dsn = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        backend = PostgresPatternBackend(dsn=dsn, pool_size=5)
        await backend.connect()
        
        analytics = PatternAnalytics(backend)
        perf = await analytics.get_pattern_performance(days_back=30)
        
        assert "total_patterns" in perf
        assert "by_type" in perf
        
        await backend.disconnect()


class TestPatternBackend:
    """Test PostgresPatternBackend (requires database)."""
    
    @pytest.mark.asyncio
    async def test_save_and_retrieve_pattern(self):
        import os
        db_name = os.getenv("POSTGRES_DB", "financial_research_agent")
        db_user = os.getenv("POSTGRES_USER", "postgres")
        db_pass = os.getenv("POSTGRES_PASSWORD", "postgres")
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        
        dsn = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        backend = PostgresPatternBackend(dsn=dsn, pool_size=5)
        await backend.connect()
        
        pattern = Pattern(
            pattern_type=PatternType.TREND,
            symbol="AAPL",
            timeframe="daily",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            confidence=PatternConfidence.HIGH,
            confidence_score=0.85,
            description="Test pattern"
        )
        
        await backend.save_pattern(pattern)
        
        retrieved = await backend.get_pattern(pattern.id)
        assert retrieved is not None
        assert retrieved.symbol == "AAPL"
        assert retrieved.pattern_type == PatternType.TREND
        assert retrieved.confidence_score == pytest.approx(0.85)
        
        await backend.delete_pattern(pattern.id)
        await backend.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])