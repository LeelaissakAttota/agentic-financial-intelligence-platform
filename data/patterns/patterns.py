"""
Pattern Detection Module - Phase 5

Detects historical patterns, recurring events, and emerging trends in financial data.
"""

import asyncio
import json
import logging
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4
from enum import Enum

import asyncpg
from scipy import signal
from scipy.stats import linregress
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class PatternType(str, Enum):
    """Types of patterns that can be detected."""
    SEASONAL = "seasonal"
    TREND = "trend"
    CYCLE = "cycle"
    REVERSAL = "reversal"
    BREAKOUT = "breakout"
    SUPPORT_RESISTANCE = "support_resistance"
    VOLUME_SPIKE = "volume_spike"
    CORRELATION = "correlation"
    REGIME_CHANGE = "regime_change"
    ANOMALY = "anomaly"


class PatternConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class Pattern:
    """A detected pattern in financial data."""
    id: str = field(default_factory=lambda: str(uuid4()))
    pattern_type: PatternType = PatternType.TREND
    symbol: str = ""
    timeframe: str = "daily"
    start_date: date = field(default_factory=date.today)
    end_date: date = field(default_factory=date.today)
    confidence: PatternConfidence = PatternConfidence.MEDIUM
    confidence_score: float = 0.5
    description: str = ""
    parameters: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    detected_at: datetime = field(default_factory=datetime.utcnow)
    occurrences: int = 1
    last_occurrence: date = field(default_factory=date.today)
    is_active: bool = True


@dataclass
class PatternMatch:
    """A match of a known pattern in current data."""
    pattern: Pattern
    match_start: date
    match_end: date
    similarity_score: float
    current_data: pd.DataFrame
    prediction: dict = field(default_factory=dict)
    confidence: PatternConfidence = PatternConfidence.MEDIUM


class PatternBackend(ABC):
    """Abstract pattern storage backend."""
    
    @abstractmethod
    async def save_pattern(self, pattern: Pattern) -> None:
        pass
    
    @abstractmethod
    async def get_pattern(self, pattern_id: str) -> Optional[Pattern]:
        pass
    
    @abstractmethod
    async def find_patterns(
        self,
        symbol: str = None,
        pattern_type: PatternType = None,
        timeframe: str = None,
        min_confidence: PatternConfidence = PatternConfidence.LOW,
        limit: int = 100
    ) -> list[Pattern]:
        pass
    
    @abstractmethod
    async def update_pattern(self, pattern: Pattern) -> None:
        pass
    
    @abstractmethod
    async def delete_pattern(self, pattern_id: str) -> bool:
        pass
    
    @abstractmethod
    async def get_pattern_stats(self) -> dict:
        pass


class PostgresPatternBackend(PatternBackend):
    """PostgreSQL backend for pattern storage."""
    
    def __init__(self, dsn: str, pool_size: int = 10):
        self.dsn = dsn
        self.pool_size = pool_size
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(
            self.dsn,
            min_size=2,
            max_size=self.pool_size,
        )
        await self._init_schema()
    
    async def disconnect(self) -> None:
        if self.pool:
            await self.pool.close()
    
    async def _init_schema(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id TEXT PRIMARY KEY,
                    pattern_type TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL DEFAULT 'daily',
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    confidence TEXT NOT NULL DEFAULT 'medium',
                    confidence_score REAL NOT NULL DEFAULT 0.5,
                    description TEXT DEFAULT '',
                    parameters JSONB DEFAULT '{}',
                    metadata JSONB DEFAULT '{}',
                    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    occurrences INTEGER NOT NULL DEFAULT 1,
                    last_occurrence DATE NOT NULL DEFAULT CURRENT_DATE,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_patterns_symbol ON patterns(symbol);
                CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type);
                CREATE INDEX IF NOT EXISTS idx_patterns_timeframe ON patterns(timeframe);
                CREATE INDEX IF NOT EXISTS idx_patterns_confidence ON patterns(confidence);
                CREATE INDEX IF NOT EXISTS idx_patterns_dates ON patterns(start_date, end_date);
                CREATE INDEX IF NOT EXISTS idx_patterns_active ON patterns(is_active);
                
                CREATE TABLE IF NOT EXISTS pattern_matches (
                    id TEXT PRIMARY KEY,
                    pattern_id TEXT NOT NULL REFERENCES patterns(id) ON DELETE CASCADE,
                    match_start DATE NOT NULL,
                    match_end DATE NOT NULL,
                    similarity_score REAL NOT NULL,
                    prediction JSONB DEFAULT '{}',
                    confidence TEXT NOT NULL DEFAULT 'medium',
                    matched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                );
                
                CREATE INDEX IF NOT EXISTS idx_matches_pattern ON pattern_matches(pattern_id);
                CREATE INDEX IF NOT EXISTS idx_matches_dates ON pattern_matches(match_start, match_end);
            """)
    
    async def save_pattern(self, pattern: Pattern) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO patterns (id, pattern_type, symbol, timeframe, start_date, end_date,
                                     confidence, confidence_score, description, parameters, metadata,
                                     detected_at, occurrences, last_occurrence, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                ON CONFLICT (id) DO UPDATE SET
                    pattern_type = EXCLUDED.pattern_type,
                    symbol = EXCLUDED.symbol,
                    timeframe = EXCLUDED.timeframe,
                    start_date = EXCLUDED.start_date,
                    end_date = EXCLUDED.end_date,
                    confidence = EXCLUDED.confidence,
                    confidence_score = EXCLUDED.confidence_score,
                    description = EXCLUDED.description,
                    parameters = EXCLUDED.parameters,
                    metadata = EXCLUDED.metadata,
                    occurrences = EXCLUDED.occurrences,
                    last_occurrence = EXCLUDED.last_occurrence,
                    is_active = EXCLUDED.is_active,
                    updated_at = NOW()
            """, pattern.id, pattern.pattern_type.value, pattern.symbol, pattern.timeframe,
               pattern.start_date, pattern.end_date, pattern.confidence.value,
               pattern.confidence_score, pattern.description, json.dumps(pattern.parameters),
               json.dumps(pattern.metadata), pattern.detected_at, pattern.occurrences,
               pattern.last_occurrence, pattern.is_active)
    
    async def get_pattern(self, pattern_id: str) -> Optional[Pattern]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM patterns WHERE id = $1", pattern_id)
            if not row:
                return None
            return self._row_to_pattern(row)
    
    async def find_patterns(
        self,
        symbol: str = None,
        pattern_type: PatternType = None,
        timeframe: str = None,
        min_confidence: PatternConfidence = PatternConfidence.LOW,
        limit: int = 100
    ) -> list[Pattern]:
        conditions = ["is_active = TRUE"]
        params = []
        
        if symbol:
            params.append(symbol)
            conditions.append(f"symbol = ${len(params)}")
        if pattern_type:
            params.append(pattern_type.value)
            conditions.append(f"pattern_type = ${len(params)}")
        if timeframe:
            params.append(timeframe)
            conditions.append(f"timeframe = ${len(params)}")
        
        confidence_order = {"low": 1, "medium": 2, "high": 3, "very_high": 4}
        min_score = confidence_order.get(min_confidence.value, 1)
        params.append(min_score)
        conditions.append(f"confidence_score >= ${len(params)}")
        
        params.append(limit)
        query = f"""
            SELECT * FROM patterns 
            WHERE {' AND '.join(conditions)}
            ORDER BY confidence_score DESC, detected_at DESC
            LIMIT ${len(params)}
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_pattern(row) for row in rows]
    
    async def update_pattern(self, pattern: Pattern) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE patterns SET
                    pattern_type = $2, symbol = $3, timeframe = $3, start_date = $4,
                    end_date = $5, confidence = $6, confidence_score = $6, description = $7,
                    parameters = $8, metadata = $9, occurrences = $10, last_occurrence = $11,
                    is_active = $11, updated_at = NOW()
                WHERE id = $1
            """, pattern.id, pattern.pattern_type.value, pattern.symbol, pattern.timeframe,
               pattern.start_date, pattern.end_date, pattern.confidence.value,
               pattern.confidence_score, pattern.description, json.dumps(pattern.parameters),
               json.dumps(pattern.metadata), pattern.occurrences, pattern.last_occurrence, pattern.is_active)
    
    async def delete_pattern(self, pattern_id: str) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM patterns WHERE id = $1", pattern_id)
            return result != "DELETE 0"
    
    async def get_pattern_stats(self) -> dict:
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_patterns,
                    COUNT(*) FILTER (WHERE is_active) as active_patterns,
                    COUNT(DISTINCT symbol) as symbols_covered,
                    COUNT(DISTINCT pattern_type) as types_covered,
                    AVG(confidence_score) as avg_confidence,
                    COUNT(DISTINCT timeframe) as timeframes_covered
                FROM patterns
            """)
            return dict(stats) if stats else {}
    
    def _row_to_pattern(self, row) -> Pattern:
        return Pattern(
            id=row["id"],
            pattern_type=PatternType(row["pattern_type"]),
            symbol=row["symbol"],
            timeframe=row["timeframe"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            confidence=PatternConfidence(row["confidence"]),
            confidence_score=row["confidence_score"],
            description=row["description"],
            parameters=row["parameters"],
            metadata=row["metadata"],
            detected_at=row["detected_at"],
            occurrences=row["occurrences"],
            last_occurrence=row["last_occurrence"],
            is_active=row["is_active"]
        )


class PatternDetector:
    """
    Main pattern detection engine.
    Detects patterns in time series financial data.
    """
    
    def __init__(self, backend: Optional[PatternBackend] = None):
        self.backend = backend
        self._pattern_templates: dict[PatternType, list] = defaultdict(list)
    
    async def initialize(self) -> None:
        """Load pattern templates from storage."""
        if self.backend:
            patterns = await self.backend.find_patterns(limit=10000)
            for pattern in patterns:
                self._pattern_templates[pattern.pattern_type].append(pattern)
    
    async def detect_patterns(
        self,
        symbol: str,
        data: pd.DataFrame,
        timeframe: str = "daily",
        pattern_types: list[PatternType] = None
    ) -> list[Pattern]:
        """
        Detect patterns in price/volume data.
        
        Args:
            symbol: Stock symbol
            data: DataFrame with OHLCV columns
            timeframe: Data timeframe
            pattern_types: Specific types to detect (None = all)
        
        Returns:
            List of detected patterns
        """
        if pattern_types is None:
            pattern_types = list(PatternType)
        
        detected = []
        
        # Ensure data has required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in data.columns:
                logger.warning(f"Missing required column: {col}")
                return []
        
        # Run detectors for each pattern type
        for ptype in pattern_types:
            try:
                if ptype == PatternType.TREND:
                    detected.extend(await self._detect_trends(symbol, data, timeframe))
                elif ptype == PatternType.SEASONAL:
                    detected.extend(await self._detect_seasonal(symbol, data, timeframe))
                elif ptype == PatternType.SUPPORT_RESISTANCE:
                    detected.extend(await self._detect_support_resistance(symbol, data, timeframe))
                elif ptype == PatternType.REVERSAL:
                    detected.extend(await self._detect_reversals(symbol, data, timeframe))
                elif ptype == PatternType.BREAKOUT:
                    detected.extend(await self._detect_breakouts(symbol, data, timeframe))
                elif ptype == PatternType.VOLUME_SPIKE:
                    detected.extend(await self._detect_volume_spikes(symbol, data, timeframe))
                elif ptype == PatternType.CYCLE:
                    detected.extend(await self._detect_cycles(symbol, data, timeframe))
                elif ptype == PatternType.CORRELATION:
                    detected.extend(await self._detect_correlations(symbol, data, timeframe))
                elif ptype == PatternType.REGIME_CHANGE:
                    detected.extend(await self._detect_regime_changes(symbol, data, timeframe))
                elif ptype == PatternType.ANOMALY:
                    detected.extend(await self._detect_anomalies(symbol, data, timeframe))
            except Exception as e:
                logger.error(f"Error detecting {ptype}: {e}")
        
        # Save detected patterns
        if self.backend:
            for pattern in detected:
                await self.backend.save_pattern(pattern)
        
        return detected
    
    async def _detect_trends(self, symbol: str, data: pd.DataFrame, timeframe: str) -> list[Pattern]:
        """Detect trend patterns using moving averages and linear regression."""
        patterns = []
        close = data['close']
        
        # Calculate multiple moving averages
        sma_20 = close.rolling(20).mean()
        sma_50 = close.rolling(50).mean()
        sma_200 = close.rolling(200).mean()
        
        # Linear regression over different windows
        for window in [20, 50, 100]:
            if len(close) >= window:
                recent = close.iloc[-window:]
                x = np.arange(len(recent))
                slope, intercept, r_value, p_value, std_err = linregress(x, recent.values)
                
                # Determine trend strength
                trend_strength = abs(r_value)
                if trend_strength > 0.7:
                    trend_type = "strong_uptrend" if slope > 0 else "strong_downtrend"
                elif trend_strength > 0.4:
                    trend_type = "uptrend" if slope > 0 else "downtrend"
                else:
                    trend_type = "sideways"
                
                # Moving average alignment
                ma_alignment = self._check_ma_alignment(close.iloc[-1], sma_20.iloc[-1], sma_50.iloc[-1], sma_200.iloc[-1])
                
                if trend_type != "sideways" or ma_alignment:
                    confidence_score = (trend_strength + (1 if ma_alignment else 0)) / 2
                    
                    pattern = Pattern(
                        pattern_type=PatternType.TREND,
                        symbol=symbol,
                        timeframe=timeframe,
                        start_date=data.index[-window].date() if hasattr(data.index[-1], 'date') else data.index[-window],
                        end_date=data.index[-1].date() if hasattr(data.index[-1], 'date') else data.index[-1],
                        confidence=self._score_to_confidence(confidence_score),
                        confidence_score=confidence_score,
                        description=f"{trend_type.replace('_', ' ').title()} over {window} periods (R²={r_value**2:.3f})",
                        parameters={
                            "window": window,
                            "slope": float(slope),
                            "r_squared": float(r_value**2),
                            "trend_type": trend_type,
                            "ma_alignment": ma_alignment
                        }
                    )
                    patterns.append(pattern)
        
        # Golden/Death cross detection
        if len(sma_50) > 0 and len(sma_200) > 0:
            # Check for golden cross (50 SMA crosses above 200 SMA)
            prev_diff = sma_50.iloc[-2] - sma_200.iloc[-2] if len(sma_50) > 1 else 0
            curr_diff = sma_50.iloc[-1] - sma_200.iloc[-1]
            
            if prev_diff <= 0 and curr_diff > 0:
                patterns.append(Pattern(
                    pattern_type=PatternType.TREND,
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=data.index[-2].date() if hasattr(data.index[-2], 'date') else data.index[-2],
                    end_date=data.index[-1].date() if hasattr(data.index[-1], 'date') else data.index[-1],
                    confidence=PatternConfidence.HIGH,
                    confidence_score=0.85,
                    description="Golden Cross - 50 SMA crossed above 200 SMA (bullish signal)",
                    parameters={
                        "cross_type": "golden_cross",
                        "sma_50": float(sma_50.iloc[-1]),
                        "sma_200": float(sma_200.iloc[-1])
                    }
                ))
            
            # Death cross (50 SMA crosses below 200 SMA)
            elif prev_diff >= 0 and curr_diff < 0:
                patterns.append(Pattern(
                    pattern_type=PatternType.TREND,
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=data.index[-2].date() if hasattr(data.index[-2], 'date') else data.index[-2],
                    end_date=data.index[-1].date() if hasattr(data.index[-1], 'date') else data.index[-1],
                    confidence=PatternConfidence.HIGH,
                    confidence_score=0.85,
                    description="Death Cross - 50 SMA crossed below 200 SMA (bearish signal)",
                    parameters={
                        "cross_type": "death_cross",
                        "sma_50": float(sma_50.iloc[-1]),
                        "sma_200": float(sma_200.iloc[-1])
                    }
                ))
        
        return patterns
    
    def _check_ma_alignment(self, price: float, sma_20: float, sma_50: float, sma_200: float) -> bool:
        """Check if moving averages are aligned with price."""
        if pd.isna(sma_20) or pd.isna(sma_50) or pd.isna(sma_200):
            return False
        # Bullish alignment: price > SMA20 > SMA50 > SMA200
        # Bearish alignment: price < SMA20 < SMA50 < SMA200
        bullish = price > sma_20 > sma_50 > sma_200
        bearish = price < sma_20 < sma_50 < sma_200
        return bullish or bearish
    
    def _score_to_confidence(self, score: float) -> PatternConfidence:
        if score >= 0.85:
            return PatternConfidence.VERY_HIGH
        elif score >= 0.7:
            return PatternConfidence.HIGH
        elif score >= 0.5:
            return PatternConfidence.MEDIUM
        elif score >= 0.3:
            return PatternConfidence.LOW
        return PatternConfidence.LOW
    
    async def _detect_seasonal(self, symbol: str, data: pd.DataFrame, timeframe: str) -> list[Pattern]:
        """Detect seasonal patterns using frequency analysis."""
        patterns = []
        close = data['close']
        
        if len(close) < 252:  # Need at least a year of daily data
            return patterns
        
        # Resample to monthly and analyze
        monthly = close.resample('M').last()
        if len(monthly) < 24:
            return patterns
        
        # FFT for seasonal detection
        values = monthly.values
        n = len(values)
        
        # Detrend
        detrended = values - np.linspace(values[0], values[-1], n)
        
        # FFT
        fft = np.fft.fft(detrended)
        freqs = np.fft.fftfreq(n)
        power = np.abs(fft)**2
        
        # Find dominant frequencies (excluding DC and Nyquist)
        positive_freqs = freqs[:n//2]
        positive_power = power[:n//2]
        
        # Find peaks in power spectrum
        peaks, properties = signal.find_peaks(positive_power, height=np.max(positive_power)*0.1)
        
        for peak in peaks:
            freq = positive_freqs[peak]
            if freq > 0:
                period_months = 1 / freq
                # Look for annual (12), semi-annual (6), quarterly (3) cycles
                if abs(period_months - 12) < 1.5:
                    period_name = "annual"
                elif abs(period_months - 6) < 1:
                    period_name = "semi-annual"
                elif abs(period_months - 3) < 0.5:
                    period_name = "quarterly"
                else:
                    continue
                
                strength = positive_power[peak] / np.sum(positive_power)
                
                if strength > 0.1:  # Significant seasonal component
                    pattern = Pattern(
                        pattern_type=PatternType.SEASONAL,
                        symbol=symbol,
                        timeframe=timeframe,
                        start_date=data.index[0].date() if hasattr(data.index[0], 'date') else data.index[0],
                        end_date=data.index[-1].date() if hasattr(data.index[-1], 'date') else data.index[-1],
                        confidence=self._score_to_confidence(strength),
                        confidence_score=float(strength),
                        description=f"{period_name.title()} seasonal pattern detected (period: {period_months:.1f} months)",
                        parameters={
                            "period_months": float(period_months),
                            "seasonal_type": period_name,
                            "strength": float(strength),
                            "period_name": period_name
                        }
                    )
                    patterns.append(pattern)
        
        return patterns
    
    async def _detect_support_resistance(self, symbol: str, data: pd.DataFrame, timeframe: str) -> list[Pattern]:
        """Detect support and resistance levels using price clustering."""
        patterns = []
        close = data['close']
        high = data['high']
        low = data['low']
        
        # Use price clustering to find support/resistance levels
        # Combine high and low prices for level detection
        prices = pd.concat([high, low]).dropna()
        
        # Use KDE or histogram to find price clusters
        # Simple approach: find local extrema
        window = 20
        
        # Find local highs and lows
        highs_idx = signal.argrelextrema(high.values, np.greater, order=window)[0]
        lows_idx = signal.argrelextrema(low.values, np.less, order=window)[0]
        
        if len(highs_idx) < 3 or len(lows_idx) < 3:
            return patterns
        
        # Cluster price levels
        high_levels = high.iloc[highs_idx].values
        low_levels = low.iloc[lows_idx].values
        
        # Cluster using DBSCAN
        all_levels = np.concatenate([high_levels, low_levels]).reshape(-1, 1)
        if len(all_levels) < 5:
            return patterns
        
        clustering = DBSCAN(eps=0.02, min_samples=2).fit(all_levels)  # 2% price tolerance
        labels = clustering.labels_
        
        # Find clusters with multiple touches
        unique_labels = set(labels)
        for label in unique_labels:
            if label == -1:  # Noise
                continue
            cluster_points = all_levels[labels == label]
            if len(cluster_points) >= 3:  # At least 3 touches
                level_price = np.mean(cluster_points)
                touch_count = len(cluster_points)
                
                # Determine if support or resistance
                current_price = data['close'].iloc[-1]
                is_resistance = level_price > current_price
                
                # Calculate strength
                strength = min(touch_count / 10, 1.0)  # Max 10 touches
                
                pattern = Pattern(
                    pattern_type=PatternType.SUPPORT_RESISTANCE,
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=data.index[min(highs_idx[0], lows_idx[0])].date() if hasattr(data.index[0], 'date') else data.index[0],
                    end_date=data.index[-1].date() if hasattr(data.index[-1], 'date') else data.index[-1],
                    confidence=self._score_to_confidence(strength * 0.8),
                    confidence_score=strength,
                    description=f"{'Resistance' if is_resistance else 'Support'} level at ${level_price:.2f} with {touch_count} touches",
                    parameters={
                        "level_price": float(level_price),
                        "touch_count": int(touch_count),
                        "is_resistance": is_resistance,
                        "type": "resistance" if is_resistance else "support"
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _detect_reversals(self, symbol: str, data: pd.DataFrame, timeframe: str) -> list[Pattern]:
        """Detect reversal patterns (double top/bottom, head and shoulders, etc.)."""
        patterns = []
        close = data['close']
        high = data['high']
        low = data['low']
        
        if len(close) < 50:
            return patterns
        
        # Find peaks and troughs
        peaks_idx = signal.argrelextrema(high.values, np.greater, order=10)[0]
        troughs_idx = signal.argrelextrema(low.values, np.less, order=10)[0]
        
        if len(peaks_idx) < 2 or len(troughs_idx) < 2:
            return patterns
        
        # Double top detection
        if len(peaks_idx) >= 2:
            for i in range(len(peaks_idx) - 1):
                peak1_idx, peak2_idx = peaks_idx[i], peaks_idx[i + 1]
                peak1_price = high.iloc[peak1_idx]
                peak2_price = high.iloc[peak2_idx]
                
                # Check if peaks are similar height (within 3%)
                if abs(peak1_price - peak2_price) / peak1_price < 0.03:
                    # Check for trough between them
                    between_troughs = troughs_idx[(troughs_idx > peak1_idx) & (troughs_idx < peak2_idx)]
                    if len(between_troughs) > 0:
                        trough_idx = between_troughs[np.argmin(low.iloc[between_troughs])]
                        trough_price = low.iloc[trough_idx]
                        
                        # Neckline
                        decline = (peak1_price - trough_price) / peak1_price
                        
                        if decline > 0.05:  # At least 5% decline
                            pattern = Pattern(
                                pattern_type=PatternType.REVERSAL,
                                symbol=symbol,
                                timeframe=timeframe,
                                start_date=data.index[peak1_idx].date() if hasattr(data.index[peak1_idx], 'date') else data.index[peak1_idx],
                                end_date=data.index[peak2_idx].date() if hasattr(data.index[peak2_idx], 'date') else data.index[peak2_idx],
                                confidence=PatternConfidence.HIGH,
                                confidence_score=0.8,
                                description=f"Double Top pattern at ${peak1_price:.2f} (neckline: ${trough_price:.2f})",
                                parameters={
                                    "pattern": "double_top",
                                    "peak_price": float(peak1_price),
                                    "neckline": float(trough_price),
                                    "decline_pct": float(decline * 100),
                                    "target_price": float(trough_price - (peak1_price - trough_price))
                                }
                            )
                            patterns.append(pattern)
        
        # Double bottom detection
        if len(troughs_idx) >= 2:
            for i in range(len(troughs_idx) - 1):
                trough1_idx, trough2_idx = troughs_idx[i], troughs_idx[i + 1]
                trough1_price = low.iloc[trough1_idx]
                trough2_price = low.iloc[trough2_idx]
                
                if abs(trough1_price - trough2_price) / trough1_price < 0.03:
                    between_peaks = peaks_idx[(peaks_idx > trough1_idx) & (peaks_idx < trough2_idx)]
                    if len(between_peaks) > 0:
                        peak_idx = between_peaks[np.argmax(high.iloc[between_peaks])]
                        peak_price = high.iloc[peak_idx]
                        
                        advance = (peak_price - trough1_price) / trough1_price
                        
                        if advance > 0.05:
                            pattern = Pattern(
                                pattern_type=PatternType.REVERSAL,
                                symbol=symbol,
                                timeframe=timeframe,
                                start_date=data.index[trough1_idx].date() if hasattr(data.index[trough1_idx], 'date') else data.index[trough1_idx],
                                end_date=data.index[trough2_idx].date() if hasattr(data.index[trough2_idx], 'date') else data.index[trough2_idx],
                                confidence=PatternConfidence.HIGH,
                                confidence_score=0.8,
                                description=f"Double Bottom pattern at ${trough1_price:.2f} (neckline: ${peak_price:.2f})",
                                parameters={
                                    "pattern": "double_bottom",
                                    "trough_price": float(trough1_price),
                                    "neckline": float(peak_price),
                                    "advance_pct": float(advance * 100),
                                    "target_price": float(peak_price + (peak_price - trough1_price))
                                }
                            )
                            patterns.append(pattern)
        
        return patterns
    
    async def _detect_breakouts(self, symbol: str, data: pd.DataFrame, timeframe: str) -> list[Pattern]:
        """Detect breakout patterns."""
        patterns = []
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # Donchian channel breakout (20-period)
        window = 20
        upper_band = high.rolling(window).max()
        lower_band = low.rolling(window).min()
        
        # Breakout above upper band
        breakout_up = (close > upper_band.shift(1)) & (close.shift(1) <= upper_band.shift(2))
        # Breakdown below lower band
        breakout_down = (close < lower_band.shift(1)) & (close.shift(1) >= lower_band.shift(2))
        
        # Volume confirmation
        avg_volume = volume.rolling(20).mean()
        volume_surge = volume > avg_volume * 1.5
        
        # Bullish breakouts
        bullish_breakouts = breakout_up & volume_surge
        for idx in data[bullish_breakouts].index:
            pattern = Pattern(
                pattern_type=PatternType.BREAKOUT,
                symbol=symbol,
                timeframe=timeframe,
                start_date=idx.date() if hasattr(idx, 'date') else idx,
                end_date=idx.date() if hasattr(idx, 'date') else idx,
                confidence=PatternConfidence.HIGH,
                confidence_score=0.75,
                description=f"Bullish breakout above {window}-period high at ${close.loc[idx]:.2f}",
                parameters={
                    "direction": "bullish",
                    "breakout_price": float(close.loc[idx]),
                    "resistance_level": float(upper_band.loc[idx]),
                    "volume_ratio": float(volume.loc[idx] / avg_volume.loc[idx]) if avg_volume.loc[idx] > 0 else 1.0
                }
            )
            patterns.append(pattern)
        
        # Bearish breakdowns
        bearish_breakouts = breakout_down & volume_surge
        for idx in data[bearish_breakouts].index:
            pattern = Pattern(
                pattern_type=PatternType.BREAKOUT,
                symbol=symbol,
                timeframe=timeframe,
                start_date=idx.date() if hasattr(idx, 'date') else idx,
                end_date=idx.date() if hasattr(idx, 'date') else idx,
                confidence=PatternConfidence.HIGH,
                confidence_score=0.75,
                description=f"Bearish breakdown below {window}-period low at ${close.loc[idx]:.2f}",
                parameters={
                    "direction": "bearish",
                    "breakout_price": float(close.loc[idx]),
                    "support_level": float(lower_band.loc[idx]),
                    "volume_ratio": float(volume.loc[idx] / avg_volume.loc[idx]) if avg_volume.loc[idx] > 0 else 1.0
                }
            )
            patterns.append(pattern)
        
        return patterns
    
    async def _detect_volume_spikes(self, symbol: str, data: pd.DataFrame, timeframe: str) -> list[Pattern]:
        """Detect unusual volume spikes."""
        patterns = []
        volume = data['volume']
        close = data['close']
        
        if len(volume) < 30:
            return patterns
        
        # Calculate volume statistics
        avg_volume = volume.rolling(30).mean()
        std_volume = volume.rolling(30).std()
        
        # Z-score for volume
        z_score = (volume - avg_volume) / std_volume.replace(0, np.nan)
        
        # Extreme volume spikes (z-score > 3)
        extreme_spikes = z_score > 3
        
        for idx in data[extreme_spikes].index:
            price_change = (close.loc[idx] - close.shift(1).loc[idx]) / close.shift(1).loc[idx] if close.shift(1).loc[idx] != 0 else 0
            volume_ratio = volume.loc[idx] / avg_volume.loc[idx] if avg_volume.loc[idx] > 0 else 0
            
            pattern = Pattern(
                pattern_type=PatternType.VOLUME_SPIKE,
                symbol=symbol,
                timeframe=timeframe,
                start_date=idx.date() if hasattr(idx, 'date') else idx,
                end_date=idx.date() if hasattr(idx, 'date') else idx,
                confidence=PatternConfidence.MEDIUM,
                confidence_score=min(z_score.loc[idx] / 5, 1.0),
                description=f"Extreme volume spike: {volume_ratio:.1f}x average volume",
                parameters={
                    "volume_ratio": float(volume_ratio),
                    "z_score": float(z_score.loc[idx]),
                    "price_change_pct": float(price_change * 100),
                    "volume": int(volume.loc[idx]),
                    "avg_volume": int(avg_volume.loc[idx])
                }
            )
            patterns.append(pattern)
        
        return patterns
    
    async def _detect_cycles(self, symbol: str, data: pd.DataFrame, timeframe: str) -> list[Pattern]:
        """Detect cyclical patterns using autocorrelation."""
        patterns = []
        close = data['close']
        
        if len(close) < 100:
            return patterns
        
        # Calculate autocorrelation
        max_lag = min(100, len(close) // 4)
        autocorr = [close.autocorr(lag=i) for i in range(1, max_lag + 1)]
        
        # Find significant autocorrelation peaks
        autocorr = np.array(autocorr)
        peaks, _ = signal.find_peaks(autocorr, height=0.3, distance=5)
        
        for peak in peaks:
            period = peak + 1  # lag = peak + 1
            correlation = autocorr[peak]
            
            if correlation > 0.4 and period > 5:
                pattern = Pattern(
                    pattern_type=PatternType.CYCLE,
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=data.index[0].date() if hasattr(data.index[0], 'date') else data.index[0],
                    end_date=data.index[-1].date() if hasattr(data.index[-1], 'date') else data.index[-1],
                    confidence=self._score_to_confidence(correlation),
                    confidence_score=correlation,
                    description=f"Cyclical pattern with {period}-period cycle (autocorr: {correlation:.3f})",
                    parameters={
                        "period": int(period),
                        "autocorrelation": float(correlation),
                        "cycle_type": "price_cycle"
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _detect_correlations(self, symbol: str, data: pd.DataFrame, timeframe: str) -> list[Pattern]:
        """Detect correlation patterns with market/sector."""
        # This would require external data (market/sector indices)
        # Placeholder for now
        return []
    
    async def _detect_regime_changes(self, symbol: str, data: pd.DataFrame, timeframe: str) -> list[Pattern]:
        """Detect market regime changes using volatility/returns regime detection."""
        patterns = []
        close = data['close']
        
        if len(close) < 60:
            return patterns
        
        # Calculate rolling volatility
        returns = close.pct_change().dropna()
        rolling_vol = returns.rolling(20).std() * np.sqrt(252)  # Annualized
        rolling_mean = returns.rolling(60).mean() * 252  # Annualized
        
        # Detect regime changes using HMM or simple threshold
        # Simple approach: detect when volatility shifts significantly
        vol_mean = rolling_vol.rolling(60).mean()
        vol_std = rolling_vol.rolling(60).std()
        
        vol_zscore = (rolling_vol - vol_mean) / vol_std.replace(0, np.nan)
        
        # Regime changes when z-score crosses thresholds
        high_vol = vol_zscore > 2
        low_vol = vol_zscore < -2
        
        regime_changes = high_vol | low_vol
        regime_changes = regime_changes & ~regime_changes.shift(1, fill_value=False)
        
        for idx in data[regime_changes].index:
            regime_type = "high_volatility" if high_vol.loc[idx] else "low_volatility"
            vol_level = rolling_vol.loc[idx]
            
            pattern = Pattern(
                pattern_type=PatternType.REGIME_CHANGE,
                symbol=symbol,
                timeframe=timeframe,
                start_date=idx.date() if hasattr(idx, 'date') else idx,
                end_date=idx.date() if hasattr(idx, 'date') else idx,
                confidence=PatternConfidence.MEDIUM,
                confidence_score=0.6,
                description=f"Market regime change: {regime_type} (vol: {vol_level:.1%})",
                parameters={
                    "regime_type": regime_type,
                    "volatility": float(vol_level),
                    "z_score": float(vol_zscore.loc[idx])
                }
            )
            patterns.append(pattern)
        
        return patterns
    
    async def _detect_anomalies(self, symbol: str, data: pd.DataFrame, timeframe: str) -> list[Pattern]:
        """Detect anomalous price/volume behavior."""
        patterns = []
        close = data['close']
        volume = data['volume']
        
        # Price anomalies - extreme daily moves
        returns = close.pct_change().dropna()
        ret_mean = returns.rolling(60).mean()
        ret_std = returns.rolling(60).std()
        
        z_score = (returns - ret_mean) / ret_std.replace(0, np.nan)
        
        # Extreme moves (> 3 sigma)
        extreme_moves = abs(z_score) > 3
        
        # Align with original data index
        extreme_moves = extreme_moves.reindex(data.index, fill_value=False)
        
        for idx in data[extreme_moves].index:
            move_pct = returns.loc[idx] * 100
            direction = "up" if returns.loc[idx] > 0 else "down"
            
            pattern = Pattern(
                pattern_type=PatternType.ANOMALY,
                symbol=symbol,
                timeframe=timeframe,
                start_date=idx.date() if hasattr(idx, 'date') else idx,
                end_date=idx.date() if hasattr(idx, 'date') else idx,
                confidence=PatternConfidence.HIGH,
                confidence_score=min(abs(z_score.loc[idx]) / 5, 1.0),
                description=f"Anomalous {direction} move: {move_pct:.1f}% ({z_score.loc[idx]:.1f}σ)",
                parameters={
                    "direction": direction,
                    "move_pct": float(move_pct),
                    "z_score": float(z_score.loc[idx]),
                    "return": float(returns.loc[idx])
                }
            )
            patterns.append(pattern)
        
        return patterns
    
    async def find_similar_patterns(
        self,
        symbol: str,
        current_data: pd.DataFrame,
        timeframe: str = "daily",
        min_similarity: float = 0.7
    ) -> list[PatternMatch]:
        """Find historical patterns similar to current price action."""
        if not self.backend:
            return []
        
        # Get stored patterns for this symbol
        patterns = await self.backend.find_patterns(symbol=symbol, limit=1000)
        
        matches = []
        for pattern in patterns:
            if pattern.occurrences < 2:
                continue
            
            # Compare current data with pattern
            similarity = await self._calculate_similarity(pattern, current_data, timeframe)
            
            if similarity >= min_similarity:
                matches.append(PatternMatch(
                    pattern=pattern,
                    match_start=date.today(),
                    match_end=date.today(),
                    similarity_score=similarity,
                    current_data=current_data,
                    confidence=self._score_to_confidence(similarity)
                ))
        
        # Sort by similarity
        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        return matches[:10]
    
    async def _calculate_similarity(
        self,
        pattern: Pattern,
        current_data: pd.DataFrame,
        timeframe: str
    ) -> float:
        """Calculate similarity between pattern and current data."""
        # Simplified similarity based on pattern type
        if pattern.pattern_type == PatternType.TREND:
            # Compare trend direction and strength
            return 0.5  # Placeholder
        elif pattern.pattern_type == PatternType.SEASONAL:
            # Compare seasonal timing
            return 0.5  # Placeholder
        return 0.3  # Default low similarity
    
    async def get_emerging_patterns(
        self,
        symbols: list[str],
        timeframe: str = "daily",
        min_occurrences: int = 2,
        days_back: int = 30
    ) -> list[Pattern]:
        """Find patterns that are emerging across multiple symbols."""
        if not self.backend:
            return []
        
        all_patterns = []
        for symbol in symbols:
            patterns = await self.backend.find_patterns(
                symbol=symbol,
                timeframe=timeframe,
                limit=100
            )
            for p in patterns:
                if p.last_occurrence >= date.today() - timedelta(days=days_back):
                    all_patterns.append(p)
        
        # Group by pattern type and parameters
        pattern_groups = defaultdict(list)
        for p in all_patterns:
            key = (p.pattern_type, p.timeframe, json.dumps(p.parameters, sort_keys=True))
            pattern_groups[key].append(p)
        
        # Find patterns occurring in multiple symbols
        emerging = []
        for group in pattern_groups.values():
            if len(group) >= min_occurrences:
                # Average confidence
                avg_conf = np.mean([p.confidence_score for p in group])
                emerging.append(Pattern(
                    pattern_type=group[0].pattern_type,
                    symbol="MULTI",
                    timeframe=group[0].timeframe,
                    start_date=min(p.start_date for p in group),
                    end_date=max(p.end_date for p in group),
                    confidence=self._score_to_confidence(avg_conf),
                    confidence_score=avg_conf,
                    description=f"Emerging {group[0].pattern_type.value} pattern across {len(group)} symbols",
                    parameters=group[0].parameters
                ))
        
        return emerging


class PatternAnalytics:
    """Analytics and reporting for detected patterns."""
    
    def __init__(self, backend: PatternBackend):
        self.backend = backend
    
    async def get_pattern_performance(
        self,
        pattern_type: PatternType = None,
        symbol: str = None,
        days_back: int = 90
    ) -> dict:
        """Analyze historical performance of detected patterns."""
        if not self.backend:
            return {}
        
        patterns = await self.backend.find_patterns(
            pattern_type=pattern_type,
            symbol=symbol,
            limit=1000
        )
        
        cutoff = date.today() - timedelta(days=days_back)
        recent = [p for p in patterns if p.detected_at.date() >= cutoff]
        
        if not recent:
            return {"total_patterns": 0, "by_type": {}}
        
        # Group by type
        by_type = defaultdict(list)
        for p in recent:
            by_type[p.pattern_type].append(p)
        
        results = {}
        for ptype, patterns in by_type.items():
            results[ptype.value] = {
                "count": len(patterns),
                "avg_confidence": np.mean([p.confidence_score for p in patterns]),
                "avg_occurrences": np.mean([p.occurrences for p in patterns]),
                "symbols": len(set(p.symbol for p in patterns)),
                "timeframes": list(set(p.timeframe for p in patterns))
            }
        
        return {
            "total_patterns": len(recent),
            "by_type": results,
            "period_days": days_back,
            "accuracy": np.mean([p.confidence_score for p in recent]) if recent else 0.0,
            "confidence": np.mean([p.confidence_score for p in recent]) if recent else 0.0
        }
    
    async def get_pattern_success_rate(
        self,
        pattern_type: PatternType,
        symbol: str = None,
        lookback_days: int = 180
    ) -> dict:
        """Calculate historical success rate of a pattern type."""
        # This would require tracking pattern outcomes
        # Placeholder for now
        return {
            "pattern_type": pattern_type.value,
            "total_occurrences": 0,
            "successful": 0,
            "success_rate": 0.0,
            "avg_return": 0.0,
            "avg_holding_period": 0
        }
    
    async def get_pattern_correlation(
        self,
        pattern_type: PatternType,
        metric: str = "price"
    ) -> dict:
        """Analyze correlation between pattern occurrences and market metrics."""
        # Placeholder for correlation analysis
        return {
            "pattern_type": pattern_type.value,
            "metric": metric,
            "correlation": 0.0,
            "p_value": 1.0
        }


# Factory
async def create_pattern_detector(
    backend_type: str = "postgres",
    **kwargs
) -> PatternDetector:
    """Factory function to create PatternDetector with specified backend."""
    if backend_type == "postgres":
        backend = PostgresPatternBackend(
            dsn=kwargs.get("dsn", "postgresql://localhost/financial_patterns"),
            pool_size=kwargs.get("pool_size", 10)
        )
        await backend.connect()
    else:
        backend = None
    
    detector = PatternDetector(backend)
    await detector.initialize()
    return detector


# Export
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