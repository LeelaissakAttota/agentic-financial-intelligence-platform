"""
Regime Detection
Market regime detection and classification using multiple methods.
"""

import asyncio
import logging
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class MarketRegime(str, Enum):
    """Market regime types."""
    BULL = "bull"                 # Strong uptrend, low vol
    BEAR = "bear"                 # Downtrend, high vol
    SIDEWAYS = "sideways"         # Range-bound, low vol
    HIGH_VOLATILITY = "high_volatility"  # High vol, no clear trend
    CRISIS = "crisis"             # Extreme stress
    RECOVERY = "recovery"         # Post-crisis bounce
    TRANSITION = "transition"     # Regime change in progress


class RegimeFeature(str, Enum):
    """Features used for regime detection."""
    TREND = "trend"                    # Price trend
    VOLATILITY = "volatility"          # Volatility level
    MOMENTUM = "momentum"              # Momentum strength
    BREADTH = "breadth"                # Market breadth
    VOLUME = "volume"                  # Volume patterns
    CORRELATION = "correlation"        # Cross-asset correlation
    VIX_TERM = "vix_term_structure"    # VIX futures term structure
    YIELD_CURVE = "yield_curve"        # Yield curve shape
    CREDIT_SPREADS = "credit_spreads"  # Credit spreads
    SENTIMENT = "sentiment"            # Market sentiment
    FLOW = "flow"                      # Fund flows


@dataclass
class RegimeProbability:
    """Probability distribution over regimes."""
    regime: MarketRegime
    probability: float
    confidence: float
    supporting_features: Dict[RegimeFeature, float]


@dataclass
class RegimeState:
    """Current regime state with metadata."""
    current_regime: MarketRegime
    regime_probabilities: Dict[MarketRegime, float]
    regime_duration_days: int
    features: Dict[RegimeFeature, float]
    feature_scores: Dict[RegimeFeature, float]
    transition_risk: float
    last_change_date: Optional[datetime]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegimeTransition:
    """Detected regime transition."""
    from_regime: MarketRegime
    to_regime: MarketRegime
    transition_date: datetime
    confidence: float
    duration_days: int
    trigger_features: List[RegimeFeature]


class RegimeDetection:
    """
    Multi-method market regime detection.
    Combines statistical models, ML classifiers, and rule-based systems.
    """
    
    def __init__(self):
        self._regime_models: Dict[str, Any] = {}
        self._current_state: Optional[RegimeState] = None
        self._regime_history: List[RegimeState] = []
        self._transitions: List[RegimeTransition] = []
        self._feature_buffer: Dict[RegimeFeature, List[Tuple[datetime, float]]] = defaultdict(list)
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize regime detection."""
        logger.info("Regime detection initialized")
        await self._load_historical_regimes()
    
    async def _load_historical_regimes(self) -> None:
        """Load historical regime data for training."""
        # In production, would load from database
        logger.info("Historical regime data loaded")
    
    def register_model(self, name: str, model: Any) -> None:
        """Register a custom regime detection model."""
        self._regime_models[name] = model
        logger.info(f"Registered regime model: {name}")
    
    async def update_features(
        self,
        features: Dict[RegimeFeature, float],
        timestamp: Optional[datetime] = None
    ) -> None:
        """Update feature buffer with new values."""
        ts = timestamp or datetime.utcnow()
        
        for feature, value in features.items():
            self._feature_buffer[feature].append((timestamp, value))
            
            # Keep last 500 values
            if len(self._feature_buffer[feature]) > 500:
                self._feature_buffer[feature] = self._feature_buffer[feature][-500:]
    
    async def detect_regime(
        self,
        market_data: Dict[str, Any],
        features: Optional[Dict[RegimeFeature, float]] = None
    ) -> RegimeState:
        """Detect current market regime."""
        
        # Extract features from market data
        if features is None:
            features = await self._extract_features(market_data)
        
        # Update feature buffer
        await self.update_features(features)
        
        # Run multiple detection methods
        methods_results = await asyncio.gather(
            self._statistical_detection(features),
            self._rule_based_detection(features),
            self._ml_classification(features),
            return_exceptions=True
        )
        
        # Combine results
        combined_probs = self._combine_results(methods_results)
        
        # Determine current regime
        current_regime = max(combined_probs, key=combined_probs.get)
        max_prob = combined_probs.get(current_regime, 0)
        
        # Calculate feature scores
        feature_scores = self._calculate_feature_scores(features)
        
        # Calculate transition risk
        transition_risk = self._calculate_transition_risk(combined_probs)
        
        # Determine regime duration
        duration = self._calculate_regime_duration(current_regime)
        
        # Last change date
        last_change = self._get_last_regime_change(current_regime)
        
        state = RegimeState(
            current_regime=current_regime,
            regime_probabilities=combined_probs,
            regime_duration_days=self._calculate_duration_days(current_regime),
            features={k: v for k, v in features.items()},
            feature_scores=feature_scores,
            transition_risk=transition_risk,
            last_change_date=last_change,
            metadata={
                "method": "ensemble",
                "max_probability": max_prob,
                "entropy": -sum(p * np.log(p + 1e-10) for p in combined_probs.values())
            }
        )
        
        # Check for regime change
        if self._current_state and self._current_state.current_regime != current_regime:
            await self._record_transition(self._current_state.current_regime, current_regime, combined_probs)
        
        self._current_state = state
        self._regime_history.append(state)
        
        # Keep last 1000 states
        if len(self._regime_history) > 1000:
            self._regime_history = self._regime_history[-1000:]
        
        return state
    
    async def _extract_features(self, market_data: Dict[str, Any]) -> Dict[RegimeFeature, float]:
        """Extract regime features from market data."""
        
        features = {}
        
        # Trend features
        if "price" in market_data and "sma_50" in market_data and "sma_200" in market_data:
            price = market_data["price"]
            sma50 = market_data["sma_50"]
            sma200 = market_data["sma_200"]
            features[RegimeFeature.TREND] = (sma50 - sma200) / sma200
        
        # Volatility
        if "vix" in market_data:
            features[RegimeFeature.VOLATILITY] = market_data["vix"] / 20.0  # Normalized
        elif "realized_vol" in market_data:
            features[RegimeFeature.VOLATILITY] = market_data["realized_vol"] / 0.15
        
        # Momentum
        if "momentum_1m" in market_data:
            features[RegimeFeature.MOMENTUM] = market_data["momentum_1m"]
        elif "returns_1m" in market_data:
            features[RegimeFeature.MOMENTUM] = market_data["returns_1m"]
        
        # Breadth
        if "advance_decline" in market_data:
            features[RegimeFeature.BREADTH] = market_data["advance_decline"]
        elif "percent_above_sma50" in market_data:
            features[RegimeFeature.BREADTH] = market_data["percent_above_sma50"] - 0.5
        
        # Volume
        if "volume_ratio" in market_data:
            features[RegimeFeature.VOLUME] = market_data["volume_ratio"] - 1.0
        
        # Correlation
        if "avg_correlation" in market_data:
            features[RegimeFeature.CORRELATION] = market_data["avg_correlation"]
        
        # VIX term structure
        if "vix" in market_data and "vix_3m" in market_data:
            features[RegimeFeature.VIX_TERM] = market_data["vix_3m"] / market_data["vix"]
        
        # Yield curve
        if "yield_10y" in market_data and "yield_2y" in market_data:
            features[RegimeFeature.YIELD_CURVE] = market_data["yield_10y"] - market_data["yield_2y"]
        
        # Credit spreads
        if "hy_spread" in market_data:
            features[RegimeFeature.CREDIT_SPREADS] = market_data["hy_spread"] / 500  # Normalized
        
        # Sentiment
        if "sentiment" in market_data:
            features[RegimeFeature.SENTIMENT] = market_data["sentiment"]
        elif "put_call_ratio" in market_data:
            features[RegimeFeature.SENTIMENT] = 1.0 - market_data["put_call_ratio"]
        
        # Flows
        if "etf_flows" in market_data:
            features[RegimeFeature.FLOW] = market_data["etf_flows"] / 1e9  # Billions
        
        return features
    
    async def _statistical_detection(self, features: Dict[RegimeFeature, float]) -> Dict[MarketRegime, float]:
        """Statistical regime detection using thresholds."""
        
        probs = {regime: 0.1 for regime in MarketRegime}
        
        trend = features.get(RegimeFeature.TREND, 0)
        vol = features.get(RegimeFeature.VOLATILITY, 1.0)
        momentum = features.get(RegimeFeature.MOMENTUM, 0)
        breadth = features.get(RegimeFeature.BREADTH, 0)
        correlation = features.get(RegimeFeature.CORRELATION, 0.3)
        yield_curve = features.get(RegimeFeature.YIELD_CURVE, 0)
        credit = features.get(RegimeFeature.CREDIT_SPREADS, 0)
        sentiment = features.get(RegimeFeature.SENTIMENT, 0)
        
        # Bull: positive trend, low vol, positive momentum, good breadth
        if features.get(RegimeFeature.TREND, 0) > 0.02 and features.get(RegimeFeature.VOLATILITY, 1) < 1.2:
            probs[MarketRegime.BULL] += 0.4
        if features.get(RegimeFeature.MOMENTUM, 0) > 0.05:
            probs[MarketRegime.BULL] += 0.2
        if features.get(RegimeFeature.BREADTH, 0) > 0.1:
            probs[MarketRegime.BULL] += 0.2
        
        # Bear: negative trend, high vol, negative momentum
        if features.get(RegimeFeature.TREND, 0) < -0.05:
            probs[MarketRegime.BEAR] += 0.4
        if features.get(RegimeFeature.VOLATILITY, 1) > 1.5:
            probs[MarketRegime.BEAR] += 0.3
        if features.get(RegimeFeature.MOMENTUM, 0) < -0.05:
            probs[MarketRegime.BEAR] += 0.2
        
        # High volatility regime
        if features.get(RegimeFeature.VOLATILITY, 1) > 2.0:
            probs[MarketRegime.HIGH_VOLATILITY] += 0.5
        if features.get(RegimeFeature.CORRELATION, 0.3) > 0.7:
            probs[MarketRegime.HIGH_VOLATILITY] += 0.3
        
        # Crisis: extreme vol, high correlation, negative sentiment
        if features.get(RegimeFeature.VOLATILITY, 1) > 3.0:
            probs[MarketRegime.CRISIS] += 0.5
        if features.get(RegimeFeature.CORRELATION, 0.3) > 0.8:
            probs[MarketRegime.CRISIS] += 0.3
        if features.get(RegimeFeature.SENTIMENT, 0) < -0.5:
            probs[MarketRegime.CRISIS] += 0.2
        
        # Recovery: improving from crisis
        if features.get(RegimeFeature.VOLATILITY, 1) < 1.5 and features.get(RegimeFeature.MOMENTUM, 0) > 0.03:
            if features.get(RegimeFeature.BREADTH, 0) > 0:
                probs[MarketRegime.RECOVERY] += 0.4
        
        # Sideways: low trend, low vol
        if abs(features.get(RegimeFeature.TREND, 0)) < 0.01 and features.get(RegimeFeature.VOLATILITY, 1) < 1.2:
            probs[MarketRegime.SIDEWAYS] += 0.3
        
        # Transition: conflicting signals
        bull_score = (features.get(RegimeFeature.TREND, 0) > 0) + (features.get(RegimeFeature.MOMENTUM, 0) > 0)
        bear_score = (features.get(RegimeFeature.TREND, 0) < 0) + (features.get(RegimeFeature.MOMENTUM, 0) < 0)
        if abs(bull_score - bear_score) <= 1 and features.get(RegimeFeature.VOLATILITY, 1) > 1.0:
            probs[MarketRegime.TRANSITION] += 0.3
        
        # Normalize
        total = sum(probs.values())
        if total > 0:
            for k in probs:
                probs[k] /= total
        
        return probs
    
    async def _rule_based_detection(self, features: Dict[RegimeFeature, float]) -> Dict[MarketRegime, float]:
        """Rule-based regime detection."""
        
        probs = {regime: 0.0 for regime in MarketRegime}
        
        # Define rules for each regime
        rules = {
            MarketRegime.BULL: [
                (lambda f: f.get(RegimeFeature.TREND, 0) > 0.03, 0.3),
                (lambda f: f.get(RegimeFeature.VOLATILITY, 1) < 0.8, 0.2),
                (lambda f: f.get(RegimeFeature.MOMENTUM, 0) > 0.05, 0.2),
                (lambda f: f.get(RegimeFeature.BREADTH, 0) > 0.15, 0.2),
                (lambda f: f.get(RegimeFeature.SENTIMENT, 0) > 0.2, 0.1),
            ],
            MarketRegime.BEAR: [
                (lambda f: f.get(RegimeFeature.TREND, 0) < -0.05, 0.3),
                (lambda f: f.get(RegimeFeature.VOLATILITY, 1) > 1.5, 0.2),
                (lambda f: f.get(RegimeFeature.MOMENTUM, 0) < -0.05, 0.2),
                (lambda f: f.get(RegimeFeature.CREDIT_SPREADS, 0) > 1.0, 0.2),
                (lambda f: f.get(RegimeFeature.SENTIMENT, 0) < -0.3, 0.1),
            ],
            MarketRegime.HIGH_VOLATILITY: [
                (lambda f: f.get(RegimeFeature.VOLATILITY, 1) > 2.0, 0.4),
                (lambda f: f.get(RegimeFeature.CORRELATION, 0.3) > 0.7, 0.3),
                (lambda f: abs(f.get(RegimeFeature.TREND, 0)) < 0.02, 0.2),
            ],
            MarketRegime.CRISIS: [
                (lambda f: f.get(RegimeFeature.VOLATILITY, 1) > 3.0, 0.5),
                (lambda f: f.get(RegimeFeature.CORRELATION, 0.3) > 0.8, 0.3),
                (lambda f: f.get(RegimeFeature.SENTIMENT, 0) < -0.6, 0.2),
            ],
            MarketRegime.RECOVERY: [
                (lambda f: f.get(RegimeFeature.VOLATILITY, 1) < 1.2, 0.2),
                (lambda f: f.get(RegimeFeature.MOMENTUM, 0) > 0.03, 0.3),
                (lambda f: f.get(RegimeFeature.BREADTH, 0) > 0, 0.2),
                (lambda f: f.get(RegimeFeature.YIELD_CURVE, 0) > 0, 0.2),
            ],
            MarketRegime.SIDEWAYS: [
                (lambda f: abs(f.get(RegimeFeature.TREND, 0)) < 0.01, 0.3),
                (lambda f: f.get(RegimeFeature.VOLATILITY, 1) < 1.1, 0.2),
                (lambda f: abs(f.get(RegimeFeature.MOMENTUM, 0)) < 0.01, 0.2),
            ],
            MarketRegime.TRANSITION: [
                (lambda f: f.get(RegimeFeature.VOLATILITY, 1) > 1.2, 0.2),
                (lambda f: f.get(RegimeFeature.CORRELATION, 0.3) > 0.5, 0.2),
                (lambda f: abs(f.get(RegimeFeature.MOMENTUM, 0)) < 0.02, 0.2),
            ],
        }
        
        for regime, rule_list in rules.items():
            for rule, weight in rule_list:
                try:
                    if rule(self._feature_buffer):
                        probs[regime] += weight
                except:
                    pass
        
        # Normalize
        total = sum(probs.values())
        if total > 0:
            for k in probs:
                probs[k] /= total
        
        return probs
    
    async def _ml_classification(self, features: Dict[RegimeFeature, float]) -> Dict[MarketRegime, float]:
        """ML-based regime classification (placeholder)."""
        
        # In production, would use trained ML model
        # For now, return uniform with slight bias from features
        probs = {regime: 1.0 / len(MarketRegime) for regime in MarketRegime}
        
        # Simple bias
        trend = features.get(RegimeFeature.TREND, 0)
        if trend > 0.02:
            probs[MarketRegime.BULL] += 0.1
        elif trend < -0.02:
            probs[MarketRegime.BEAR] += 0.1
        
        vol = features.get(RegimeFeature.VOLATILITY, 1)
        if vol > 2.0:
            probs[MarketRegime.HIGH_VOLATILITY] += 0.15
            probs[MarketRegime.CRISIS] += 0.05
        
        total = sum(probs.values())
        if total > 0:
            for k in probs:
                probs[k] /= total
        
        return probs
    
    def _combine_results(
        self,
        results: List[Dict[MarketRegime, float]]
    ) -> Dict[MarketRegime, float]:
        """Combine results from multiple detection methods."""
        
        combined = {regime: 0.0 for regime in MarketRegime}
        
        weights = [0.3, 0.4, 0.3]  # statistical, rule-based, ML
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                continue
            for regime, prob in result.items():
                combined[regime] += prob * weights[i]
        
        # Normalize
        total = sum(combined.values())
        if total > 0:
            for k in combined:
                combined[k] /= total
        
        return combined
    
    def _calculate_feature_scores(self, features: Dict[RegimeFeature, float]) -> Dict[RegimeFeature, float]:
        """Calculate normalized feature scores."""
        
        # Normalization parameters (would be learned)
        norms = {
            RegimeFeature.TREND: (0, 0.05),
            RegimeFeature.VOLATILITY: (1.0, 2.0),
            RegimeFeature.MOMENTUM: (0, 0.1),
            RegimeFeature.BREADTH: (-0.5, 0.5),
            RegimeFeature.VOLUME: (-0.5, 0.5),
            RegimeFeature.CORRELATION: (0.3, 0.8),
            RegimeFeature.VIX_TERM: (0.8, 1.2),
            RegimeFeature.YIELD_CURVE: (-0.02, 0.02),
            RegimeFeature.CREDIT_SPREADS: (0, 1.0),
            RegimeFeature.SENTIMENT: (-1, 1),
            RegimeFeature.FLOW: (-5, 5),
        }
        
        scores = {}
        for feature, value in features.items():
            if feature in norms:
                mean, std = norms[feature]
                scores[feature] = (value - mean) / (std + 1e-6)
            else:
                scores[feature] = 0.0
        
        return scores
    
    def _calculate_transition_risk(self, probs: Dict[MarketRegime, float]) -> float:
        """Calculate risk of regime transition."""
        
        # High entropy = uncertain regime = higher transition risk
        entropy = -sum(p * np.log(p + 1e-10) for p in probs.values() if p > 0)
        max_entropy = np.log(len(MarketRegime))
        
        # Also consider if second-highest probability is close to highest
        sorted_probs = sorted(probs.values(), reverse=True)
        gap = sorted_probs[0] - sorted_probs[1] if len(sorted_probs) > 1 else 1.0
        
        transition_risk = (entropy / max_entropy) * 0.7 + (1 - gap) * 0.3
        return float(min(max(transition_risk, 0), 1))
    
    def _calculate_regime_duration(self, regime: MarketRegime) -> int:
        """Calculate how long we've been in current regime."""
        
        if not self._regime_history:
            return 0
        
        duration = 0
        for state in reversed(self._regime_history):
            if state.current_regime == regime:
                duration += 1
            else:
                break
        
        return duration
    
    def _get_last_regime_change(self, current_regime: MarketRegime) -> Optional[datetime]:
        """Get date of last regime change."""
        
        for state in reversed(self._regime_history):
            if state.current_regime != current_regime:
                # Next state after this one was the change
                idx = self._regime_history.index(state)
                if idx + 1 < len(self._regime_history):
                    return self._regime_history[idx + 1].metadata.get("timestamp", datetime.utcnow())
        
        return None
    
    def _calculate_duration_days(self, regime: MarketRegime) -> int:
        """Calculate days in current regime."""
        
        if not self._regime_history:
            return 0
        
        # Find last state with different regime
        for i in range(len(self._regime_history) - 1, -1, -1):
            if self._regime_history[i].current_regime != regime:
                return len(self._regime_history) - i - 1
        
        return len(self._regime_history)
    
    async def _record_transition(
        self,
        from_regime: MarketRegime,
        to_regime: MarketRegime,
        probs: Dict[MarketRegime, float]
    ) -> None:
        """Record a regime transition."""
        
        confidence = probs.get(to_regime, 0)
        duration = self._calculate_duration_days(from_regime)
        
        # Identify trigger features
        triggers = []
        if self._current_state:
            for feature, score in self._current_state.feature_scores.items():
                if abs(score) > 2.0:
                    triggers.append(feature)
        
        transition = RegimeTransition(
            from_regime=from_regime,
            to_regime=to_regime,
            transition_date=datetime.utcnow(),
            confidence=confidence,
            duration_days=duration,
            trigger_features=triggers
        )
        
        self._transitions.append(transition)
        
        logger.info(f"Regime transition: {from_regime.value} -> {to_regime.value} (confidence: {confidence:.2f})")
    
    def get_current_state(self) -> Optional[RegimeState]:
        """Get current regime state."""
        return self._current_state
    
    def get_regime_history(self, days: int = 30) -> List[RegimeState]:
        """Get regime history for specified days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        return [s for s in self._regime_history if s.metadata.get("timestamp", datetime.utcnow()) >= cutoff]
    
    def get_transitions(self, days: int = 90) -> List[RegimeTransition]:
        """Get recent regime transitions."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        return [t for t in self._transitions if t.transition_date >= cutoff]
    
    def get_regime_statistics(self) -> Dict[str, Any]:
        """Get regime statistics."""
        
        if not self._regime_history:
            return {}
        
        # Regime frequency
        freq = defaultdict(int)
        for state in self._regime_history:
            freq[state.current_regime.value] += 1
        
        total = len(self._regime_history)
        regime_freq = {k: v/total for k, v in freq.items()}
        
        # Average duration
        avg_duration = defaultdict(list)
        current_regime = None
        current_duration = 0
        
        for state in self._regime_history:
            if state.current_regime != current_regime:
                if current_regime:
                    avg_duration[current_regime.value].append(current_duration)
                current_regime = state.current_regime
                current_duration = 1
            else:
                current_duration += 1
        
        if current_regime:
            avg_duration[current_regime.value].append(current_duration)
        
        avg_dur = {k: np.mean(v) for k, v in avg_duration.items() if v}
        
        # Transition matrix
        transitions = defaultdict(lambda: defaultdict(int))
        for i in range(1, len(self._regime_history)):
            from_r = self._regime_history[i-1].current_regime.value
            to_r = self._regime_history[i].current_regime.value
            if from_r != to_r:
                transitions[from_r][to_r] += 1
        
        return {
            "regime_frequency": regime_freq,
            "average_duration_days": avg_dur,
            "transition_matrix": {k: dict(v) for k, v in transitions.items()},
            "total_transitions": len(self._transitions),
            "current_regime": self._current_state.current_regime.value if self._current_state else None,
            "current_duration": self._calculate_regime_duration(self._current_state.current_regime) if self._current_state else 0,
            "transition_risk": self._current_state.transition_risk if self._current_state else 0
        }
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "current_regime": self._current_state.current_regime.value if self._current_state else None,
            "regime_probabilities": {k.value: v for k, v in self._current_state.regime_probabilities.items()} if self._current_state else {},
            "transition_risk": self._current_state.transition_risk if self._current_state else 0,
            "regime_duration": self._current_state.regime_duration_days if self._current_state else 0,
            "history_length": len(self._regime_history),
            "transitions_count": len(self._transitions)
        }


# Global regime detection instance
_regime_detection: Optional[RegimeDetection] = None


def get_regime_detection() -> RegimeDetection:
    global _regime_detection
    if _regime_detection is None:
        _regime_detection = RegimeDetection()
    return _regime_detection


async def close_regime_detection() -> None:
    global _regime_detection
    if _regime_detection:
        _regime_detection = None