"""
Early Warning System
Detects early warning signals for market events, regime changes, and risk factors.
"""

import asyncio
import logging
import numpy as np
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class SignalType(str, Enum):
    """Types of early warning signals."""
    MARKET_CRASH = "market_crash"
    REGIME_CHANGE = "regime_change"
    VOLATILITY_SPIKE = "volatility_spike"
    LIQUIDITY_CRISIS = "liquidity_crisis"
    CREDIT_DETERIORATION = "credit_deterioration"
    MOMENTUM_REVERSAL = "momentum_reversal"
    CORRELATION_BREAKDOWN = "correlation_breakdown"
    VALUATION_EXTREME = "valuation_extreme"
    SENTIMENT_SHIFT = "sentiment_shift"
    FLOW_IMBALANCE = "flow_imbalance"
    TECHNICAL_BREAKOUT = "technical_breakout"
    MACRO_SURPRISE = "macro_surprise"


class SignalSeverity(str, Enum):
    """Signal severity levels."""
    INFO = "info"
    WATCH = "watch"
    WARNING = "warning"
    ALERT = "alert"
    CRITICAL = "critical"


@dataclass
class WarningSignal:
    """Early warning signal."""
    id: str
    signal_type: SignalType
    severity: SignalSeverity
    symbol: Optional[str]  # None for market-wide
    description: str
    value: float
    threshold: float
    confidence: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class SignalRule:
    """Rule for detecting warning signals."""
    signal_type: SignalType
    condition: Callable  # Function that returns (triggered, value, confidence)
    severity_thresholds: Dict[SignalSeverity, float]
    cooldown_hours: int = 24
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class EarlyWarningSystem:
    """
    Early warning system for detecting market risks and regime changes.
    Monitors multiple indicators and generates actionable alerts.
    """
    
    def __init__(self):
        self._rules: Dict[SignalType, SignalRule] = {}
        self._active_signals: Dict[str, WarningSignal] = {}
        self._signal_history: List[WarningSignal] = []
        self._last_triggered: Dict[SignalType, datetime] = {}
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._register_default_rules()
    
    def _register_default_rules(self) -> None:
        """Register default early warning rules."""
        
        # Market crash detection
        self.register_rule(SignalRule(
            signal_type=SignalType.MARKET_CRASH,
            condition=self._check_market_crash,
            severity_thresholds={
                SignalSeverity.WATCH: 0.10,    # 10% drawdown
                SignalSeverity.WARNING: 0.15,  # 15% drawdown
                SignalSeverity.ALERT: 0.20,    # 20% drawdown
                SignalSeverity.CRITICAL: 0.30  # 30% drawdown
            },
            cooldown_hours=48
        ))
        
        # Volatility spike
        self.register_rule(SignalRule(
            signal_type=SignalType.VOLATILITY_SPIKE,
            condition=self._check_volatility_spike,
            severity_thresholds={
                SignalSeverity.WATCH: 1.5,     # 1.5x normal vol
                SignalSeverity.WARNING: 2.0,   # 2x normal vol
                SignalSeverity.ALERT: 3.0,     # 3x normal vol
                SignalSeverity.CRITICAL: 5.0   # 5x normal vol
            },
            cooldown_hours=24
        ))
        
        # Regime change
        self.register_rule(SignalRule(
            signal_type=SignalType.REGIME_CHANGE,
            condition=self._check_regime_change,
            severity_thresholds={
                SignalSeverity.WATCH: 0.6,     # 60% regime probability
                SignalSeverity.WARNING: 0.75,
                SignalSeverity.ALERT: 0.85,
                SignalSeverity.CRITICAL: 0.95
            },
            cooldown_hours=72
        ))
        
        # Correlation breakdown
        self.register_rule(SignalRule(
            signal_type=SignalType.CORRELATION_BREAKDOWN,
            condition=self._check_correlation_breakdown,
            severity_thresholds={
                SignalSeverity.WATCH: 0.3,     # Correlation drop > 0.3
                SignalSeverity.WARNING: 0.5,
                SignalSeverity.ALERT: 0.7,
                SignalSeverity.CRITICAL: 0.9
            },
            cooldown_hours=48
        ))
        
        # Momentum reversal
        self.register_rule(SignalRule(
            signal_type=SignalType.MOMENTUM_REVERSAL,
            condition=self._check_momentum_reversal,
            severity_thresholds={
                SignalSeverity.WATCH: 0.5,     # 50% momentum change
                SignalSeverity.WARNING: 0.7,
                SignalSeverity.ALERT: 0.85,
                SignalSeverity.CRITICAL: 0.95
            },
            cooldown_hours=24
        ))
        
        # Liquidity crisis
        self.register_rule(SignalRule(
            signal_type=SignalType.LIQUIDITY_CRISIS,
            condition=self._check_liquidity_crisis,
            severity_thresholds={
                SignalSeverity.WATCH: 1.5,     # Spread 1.5x normal
                SignalSeverity.WARNING: 2.0,
                SignalSeverity.ALERT: 3.0,
                SignalSeverity.CRITICAL: 5.0
            },
            cooldown_hours=48
        ))
        
        # Credit deterioration
        self.register_rule(SignalRule(
            signal_type=SignalType.CREDIT_DETERIORATION,
            condition=self._check_credit_deterioration,
            severity_thresholds={
                SignalSeverity.WATCH: 0.5,     # Spread +50bps
                SignalSeverity.WARNING: 1.0,   # Spread +100bps
                SignalSeverity.ALERT: 2.0,     # Spread +200bps
                SignalSeverity.CRITICAL: 3.0   # Spread +300bps
            },
            cooldown_hours=72
        ))
        
        # Valuation extreme
        self.register_rule(SignalRule(
            signal_type=SignalType.VALUATION_EXTREME,
            condition=self._check_valuation_extreme,
            severity_thresholds={
                SignalSeverity.WATCH: 2.0,     # 2 std dev from mean
                SignalSeverity.WARNING: 2.5,
                SignalSeverity.ALERT: 3.0,
                SignalSeverity.CRITICAL: 3.5
            },
            cooldown_hours=168  # Weekly
        ))
        
        # Sentiment shift
        self.register_rule(SignalRule(
            signal_type=SignalType.SENTIMENT_SHIFT,
            condition=self._check_sentiment_shift,
            severity_thresholds={
                SignalSeverity.WATCH: 0.3,     # 30% sentiment change
                SignalSeverity.WARNING: 0.5,
                SignalSeverity.ALERT: 0.7,
                SignalSeverity.CRITICAL: 0.9
            },
            cooldown_hours=24
        ))
    
    def register_rule(self, rule: SignalRule) -> None:
        """Register a warning signal rule."""
        self._rules[rule.signal_type] = rule
        logger.info(f"Registered early warning rule: {rule.signal_type.value}")
    
    async def start_monitoring(self, interval_seconds: int = 300) -> None:
        """Start continuous monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval_seconds))
        logger.info("Early warning system monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Early warning system monitoring stopped")
    
    async def _monitor_loop(self, interval_seconds: int) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                await self.check_all_signals()
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            await asyncio.sleep(interval_seconds)
    
    async def check_all_signals(self, market_data: Optional[Dict[str, Any]] = None) -> List[WarningSignal]:
        """Check all registered signal rules."""
        triggered = []
        
        for signal_type, rule in self._rules.items():
            if not rule.enabled:
                continue
            
            # Check cooldown
            last = self._last_triggered.get(signal_type)
            if last and (datetime.utcnow() - last).total_seconds() < rule.cooldown_hours * 3600:
                continue
            
            try:
                triggered_flag, value, confidence = rule.condition(market_data)
                
                if triggered_flag:
                    # Determine severity
                    severity = self._determine_severity(value, rule.severity_thresholds)
                    
                    if severity:
                        signal = WarningSignal(
                            id=f"{signal_type.value}_{datetime.utcnow().timestamp()}",
                            signal_type=signal_type,
                            severity=severity,
                            symbol=None,
                            description=self._generate_description(signal_type, value),
                            value=value,
                            threshold=rule.severity_thresholds[severity],
                            confidence=confidence
                        )
                        
                        self._active_signals[signal.id] = signal
                        self._signal_history.append(signal)
                        self._last_triggered[signal_type] = datetime.utcnow()
                        triggered.append(signal)
                        
                        logger.warning(f"Early warning triggered: {signal_type.value} ({severity.value})")
            
            except Exception as e:
                logger.error(f"Error checking signal {signal_type}: {e}")
        
        return triggered
    
    def _determine_severity(self, value: float, thresholds: Dict[SignalSeverity, float]) -> Optional[SignalSeverity]:
        """Determine severity based on value and thresholds."""
        for severity in [SignalSeverity.CRITICAL, SignalSeverity.ALERT, SignalSeverity.WARNING, SignalSeverity.WATCH]:
            if severity in thresholds and value >= thresholds[severity]:
                return severity
        return None
    
    def _generate_description(self, signal_type: SignalType, value: float) -> str:
        """Generate human-readable description."""
        descriptions = {
            SignalType.MARKET_CRASH: f"Market drawdown of {value:.1%} detected",
            SignalType.VOLATILITY_SPIKE: f"Volatility spike to {value:.1f}x normal levels",
            SignalType.REGIME_CHANGE: f"Regime change probability: {value:.0%}",
            SignalType.CORRELATION_BREAKDOWN: f"Correlation breakdown detected: {value:.2f}",
            SignalType.MOMENTUM_REVERSAL: f"Momentum reversal signal strength: {value:.2f}",
            SignalType.LIQUIDITY_CRISIS: f"Liquidity stress indicator: {value:.1f}x normal",
            SignalType.CREDIT_DETERIORATION: f"Credit spread widening: {value:.1f}%",
            SignalType.VALUATION_EXTREME: f"Valuation at {value:.1f} standard deviations from mean",
            SignalType.SENTIMENT_SHIFT: f"Sentiment shift magnitude: {value:.0%}",
        }
        return descriptions.get(signal_type, f"{signal_type.value}: {value}")
    
    # Condition check methods
    
    async def _check_market_crash(self, market_data: Optional[Dict[str, Any]]) -> Tuple[bool, float, float]:
        """Check for market crash conditions."""
        if not market_data or "market_returns" not in market_data:
            return False, 0.0, 0.0
        
        returns = market_data["market_returns"]
        if len(returns) < 20:
            return False, 0.0, 0.0
        
        # Calculate drawdown from peak
        cumulative = np.cumprod(1 + returns)
        peak = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - peak) / peak
        current_dd = drawdown[-1]
        
        # Check if drawdown exceeds threshold
        triggered = current_dd < -0.10  # 10% drawdown
        confidence = min(1.0, abs(current_dd) / 0.30)  # Max confidence at 30% DD
        
        return triggered, abs(current_dd), confidence
    
    async def _check_volatility_spike(self, market_data: Optional[Dict[str, Any]]) -> Tuple[bool, float, float]:
        """Check for volatility spike."""
        if not market_data or "market_returns" not in market_data:
            return False, 0.0, 0.0
        
        returns = market_data["market_returns"]
        if len(returns) < 30:
            return False, 0.0, 0.0
        
        # Current volatility vs historical
        current_vol = np.std(returns[-10:]) * np.sqrt(252)  # 10-day annualized
        historical_vol = np.std(returns[-252:-10]) * np.sqrt(252)  # Year before recent
        
        if historical_vol == 0:
            return False, 0.0, 0.0
        
        vol_ratio = current_vol / historical_vol
        triggered = vol_ratio > 1.5
        confidence = min(1.0, vol_ratio / 5.0)
        
        return triggered, vol_ratio, confidence
    
    async def _check_regime_change(self, market_data: Optional[Dict[str, Any]]) -> Tuple[bool, float, float]:
        """Check for regime change probability."""
        if not market_data or "regime_probability" not in market_data:
            return False, 0.0, 0.0
        
        prob = market_data["regime_probability"]
        triggered = prob > 0.6
        confidence = prob
        
        return triggered, prob, confidence
    
    async def _check_correlation_breakdown(self, market_data: Optional[Dict[str, Any]]) -> Tuple[bool, float, float]:
        """Check for correlation breakdown."""
        if not market_data or "correlation_matrix" not in market_data:
            return False, 0.0, 0.0
        
        current_corr = market_data["correlation_matrix"]
        historical_corr = market_data.get("historical_correlation", current_corr)
        
        if current_corr.shape != historical_corr.shape:
            return False, 0.0, 0.0
        
        # Average absolute correlation change
        diff = np.abs(current_corr - historical_corr)
        avg_change = np.mean(diff[np.triu_indices_from(diff, k=1)])
        
        triggered = avg_change > 0.3
        confidence = min(1.0, avg_change / 1.0)
        
        return triggered, avg_change, confidence
    
    async def _check_momentum_reversal(self, market_data: Optional[Dict[str, Any]]) -> Tuple[bool, float, float]:
        """Check for momentum reversal."""
        if not market_data or "momentum" not in market_data:
            return False, 0.0, 0.0
        
        momentum = market_data["momentum"]
        prev_momentum = market_data.get("previous_momentum", momentum)
        
        change = abs(momentum - prev_momentum) / (abs(prev_momentum) + 1e-6)
        triggered = change > 0.5
        confidence = min(1.0, change)
        
        return triggered, change, confidence
    
    async def _check_liquidity_crisis(self, market_data: Optional[Dict[str, Any]]) -> Tuple[bool, float, float]:
        """Check for liquidity crisis."""
        if not market_data or "bid_ask_spread" not in market_data:
            return False, 0.0, 0.0
        
        current_spread = market_data["bid_ask_spread"]
        normal_spread = market_data.get("normal_spread", current_spread)
        
        if normal_spread == 0:
            return False, 0.0, 0.0
        
        spread_ratio = current_spread / normal_spread
        triggered = spread_ratio > 1.5
        confidence = min(1.0, spread_ratio / 5.0)
        
        return triggered, spread_ratio, confidence
    
    async def _check_credit_deterioration(self, market_data: Optional[Dict[str, Any]]) -> Tuple[bool, float, float]:
        """Check for credit deterioration."""
        if not market_data or "credit_spreads" not in market_data:
            return False, 0.0, 0.0
        
        current_spreads = market_data["credit_spreads"]
        historical_spreads = market_data.get("historical_spreads", current_spreads)
        
        widening = current_spreads - historical_spreads
        max_widening = np.max(widening) if len(widening) > 0 else 0
        
        # Convert to percentage (bps)
        max_widening_pct = max_widening * 100
        
        triggered = max_widening_pct > 50  # 50 bps
        confidence = min(1.0, max_widening_pct / 300)
        
        return triggered, max_widening_pct, confidence
    
    async def _check_valuation_extreme(self, market_data: Optional[Dict[str, Any]]) -> Tuple[bool, float, float]:
        """Check for valuation extremes."""
        if not market_data or "valuation_zscore" not in market_data:
            return False, 0.0, 0.0
        
        zscore = market_data["valuation_zscore"]
        triggered = abs(zscore) > 2.0
        confidence = min(1.0, abs(zscore) / 4.0)
        
        return triggered, abs(zscore), confidence
    
    async def _check_sentiment_shift(self, market_data: Optional[Dict[str, Any]]) -> Tuple[bool, float, float]:
        """Check for sentiment shift."""
        if not market_data or "sentiment" not in market_data:
            return False, 0.0, 0.0
        
        current = market_data["sentiment"]
        previous = market_data.get("previous_sentiment", current)
        
        shift = abs(current - previous)
        triggered = shift > 0.3
        confidence = min(1.0, shift)
        
        return triggered, shift, confidence
    
    def get_active_signals(self, severity: Optional[SignalSeverity] = None) -> List[WarningSignal]:
        """Get currently active signals."""
        signals = list(self._active_signals.values())
        
        if severity:
            signals = [s for s in signals if s.severity == severity]
        
        return sorted(signals, key=lambda s: s.timestamp, reverse=True)
    
    def get_signal_history(
        self,
        signal_type: Optional[SignalType] = None,
        days: int = 30
    ) -> List[WarningSignal]:
        """Get signal history."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        history = [
            s for s in self._signal_history
            if s.timestamp >= cutoff
        ]
        
        if signal_type:
            history = [s for s in history if s.signal_type == signal_type]
        
        return sorted(history, key=lambda s: s.timestamp, reverse=True)
    
    def acknowledge_signal(self, signal_id: str) -> bool:
        """Acknowledge a signal."""
        if signal_id in self._active_signals:
            self._active_signals[signal_id].acknowledged = True
            return True
        return False
    
    def resolve_signal(self, signal_id: str) -> bool:
        """Resolve a signal."""
        if signal_id in self._active_signals:
            signal = self._active_signals[signal_id]
            signal.resolved = True
            signal.resolution_time = datetime.utcnow()
            del self._active_signals[signal_id]
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_signals": len(self._active_signals),
            "by_severity": {
                sev.value: len([s for s in self._active_signals.values() if s.severity == sev])
                for sev in SignalSeverity
            },
            "by_type": {
                st.value: len([s for s in self._active_signals.values() if s.signal_type == st])
                for st in SignalType
            },
            "total_history": len(self._signal_history),
            "monitoring": self._monitoring,
            "rules_registered": len(self._rules)
        }


# Global early warning system instance
_early_warning_system: Optional[EarlyWarningSystem] = None


def get_early_warning_system() -> EarlyWarningSystem:
    global _early_warning_system
    if _early_warning_system is None:
        _early_warning_system = EarlyWarningSystem()
    return _early_warning_system


async def close_early_warning_system() -> None:
    global _early_warning_system
    if _early_warning_system:
        await _early_warning_system.stop_monitoring()
        _early_warning_system = None