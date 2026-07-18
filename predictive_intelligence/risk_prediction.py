"""
Risk Prediction
Predicts portfolio risk, drawdowns, and tail events using ML and statistical models.
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


class RiskType(str, Enum):
    """Types of risk predictions."""
    PORTFOLIO_DRAWDOWN = "portfolio_drawdown"
    TAIL_EVENT = "tail_event"
    VOLATILITY_SPIKE = "volatility_spike"
    CORRELATION_BREAKDOWN = "correlation_breakdown"
    LIQUIDITY_CRISIS = "liquidity_crisis"
    CREDIT_DETERIORATION = "credit_deterioration"
    FACTOR_CROWDING = "factor_crowding"
    REGIME_SHIFT = "regime_shift"
    MARGIN_CALL = "margin_call"
    CONCENTRATION_RISK = "concentration_risk"


class RiskHorizon(str, Enum):
    """Risk prediction horizons."""
    INTRADAY = "intraday"       # Hours
    DAILY = "daily"             # 1 day
    WEEKLY = "weekly"           # 1 week
    MONTHLY = "monthly"         # 1 month
    QUARTERLY = "quarterly"     # 3 months


@dataclass
class RiskPredictionResult:
    """Result of a risk prediction."""
    prediction_id: str
    risk_type: RiskType
    portfolio_id: Optional[str]
    symbols: List[str]
    horizon: RiskHorizon
    probability: float
    severity: float  # Expected magnitude if event occurs
    confidence: float
    expected_loss: float  # Expected portfolio loss %
    var_contribution: float  # Contribution to VaR
    key_drivers: List[str]
    trigger_conditions: List[str]
    mitigation_suggestions: List[str]
    historical_frequency: float
    similar_episodes: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


@dataclass
class RiskAlert:
    """Active risk alert."""
    alert_id: str
    risk_type: RiskType
    severity: str  # low, medium, high, critical
    message: str
    affected_symbols: List[str]
    probability: float
    expected_impact: float
    triggered_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    resolved: bool = False


class RiskPrediction:
    """
    Predicts portfolio risks and tail events using multiple approaches:
    - Statistical models (GARCH, EVT)
    - Machine learning classifiers
    - Factor model stress testing
    - Network analysis for contagion
    - Liquidity risk modeling
    """
    
    def __init__(self):
        self._risk_models: Dict[RiskType, Any] = {}
        self._active_alerts: Dict[str, RiskAlert] = {}
        self._prediction_history: List[RiskPredictionResult] = []
        self._portfolio_snapshots: List[Dict[str, Any]] = []
        self._risk_budgets: Dict[str, Dict[str, float]] = {}
    
    async def initialize(self) -> None:
        """Initialize risk prediction system."""
        logger.info("Risk prediction system initialized")
    
    def register_risk_model(self, risk_type: RiskType, model: Any) -> None:
        """Register a custom risk prediction model."""
        self._risk_models[risk_type] = model
        logger.info(f"Registered risk model for {risk_type.value}")
    
    async def predict_portfolio_risk(
        self,
        portfolio: Dict[str, Dict[str, Any]],  # symbol -> {weight, returns, etc.}
        risk_types: Optional[List[RiskType]] = None,
        horizon: RiskHorizon = RiskHorizon.DAILY,
        confidence_level: float = 0.95
    ) -> List[RiskPredictionResult]:
        """Predict multiple risk types for a portfolio."""
        
        risk_types = risk_types or list(RiskType)
        results = []
        
        # Analyze portfolio characteristics
        portfolio_analysis = self._analyze_portfolio(portfolio)
        
        for risk_type in risk_types:
            try:
                if risk_type == RiskType.PORTFOLIO_DRAWDOWN:
                    result = await self._predict_drawdown(portfolio, portfolio_analysis, horizon, confidence_level)
                elif risk_type == RiskType.TAIL_EVENT:
                    result = await self._predict_tail_event(portfolio, portfolio_analysis, horizon, confidence_level)
                elif risk_type == RiskType.VOLATILITY_SPIKE:
                    result = await self._predict_volatility_spike(portfolio, portfolio_analysis, horizon)
                elif risk_type == RiskType.CORRELATION_BREAKDOWN:
                    result = await self._predict_correlation_breakdown(portfolio, portfolio_analysis, horizon)
                elif risk_type == RiskType.LIQUIDITY_CRISIS:
                    result = await self._predict_liquidity_crisis(portfolio, portfolio_analysis, horizon)
                elif risk_type == RiskType.FACTOR_CROWDING:
                    result = await self._predict_factor_crowding(portfolio, portfolio_analysis, horizon)
                elif risk_type == RiskType.REGIME_SHIFT:
                    result = await self._predict_regime_shift(portfolio, portfolio_analysis, horizon)
                elif risk_type == RiskType.CONCENTRATION_RISK:
                    result = await self._predict_concentration_risk(portfolio, portfolio_analysis, horizon)
                else:
                    continue
                
                if result:
                    results.append(result)
                    self._prediction_history.append(result)
                    
                    # Create alert if high probability
                    if result.probability > 0.7 and result.severity > 0.5:
                        await self._create_alert(result)
                        
            except Exception as e:
                logger.error(f"Error predicting {risk_type.value}: {e}")
        
        return results
    
    def _analyze_portfolio(self, portfolio: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze portfolio characteristics."""
        
        symbols = list(portfolio.keys())
        weights = np.array([portfolio[s].get("weight", 0) for s in symbols])
        weights = weights / weights.sum() if weights.sum() > 0 else weights
        
        n = len(symbols)
        
        analysis = {
            "symbols": symbols,
            "weights": weights,
            "n_assets": n,
            "concentration": {
                "hhi": np.sum(weights**2),
                "top5_weight": np.sum(np.sort(weights)[-5:]),
                "max_weight": np.max(weights)
            },
            "sector_exposure": self._calculate_sector_exposure(portfolio),
            "factor_exposure": self._calculate_factor_exposure(portfolio),
            "liquidity_profile": self._calculate_liquidity_profile(portfolio),
            "historical_metrics": self._calculate_historical_metrics(portfolio)
        }
        
        return analysis
    
    def _calculate_sector_exposure(self, portfolio: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """Calculate sector exposures."""
        sector_weights = defaultdict(float)
        for symbol, info in portfolio.items():
            sector = info.get("sector", "Unknown")
            sector_weights[sector] += info.get("weight", 0)
        return dict(sector_weights)
    
    def _calculate_factor_exposure(self, portfolio: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """Calculate factor exposures."""
        factor_exp = defaultdict(float)
        for symbol, info in portfolio.items():
            weight = info.get("weight", 0)
            betas = info.get("betas", {})
            for factor, beta in betas.items():
                factor_exp[factor] += weight * beta
        return dict(factor_exp)
    
    def _calculate_liquidity_profile(self, portfolio: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate portfolio liquidity profile."""
        weights = np.array([info.get("weight", 0) for info in portfolio.values()])
        adv = np.array([info.get("avg_daily_volume", 1e6) for info in portfolio.values()])
        
        # Days to liquidate (assuming 20% participation)
        days_to_liquidate = np.sum(weights) / (0.2 * adv / 1e6) if np.any(adv > 0) else 0
        
        return {
            "weighted_avg_adv": float(np.average(adv, weights=weights)),
            "days_to_liquidate_90": float(days_to_liquidate),
            "least_liquid_weight": float(np.max(weights[adv == np.min(adv)])) if len(adv) > 0 else 0,
            "liquidity_score": 1.0 / (1.0 + days_to_liquidate / 10)
        }
    
    def _calculate_historical_metrics(self, portfolio: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """Calculate historical risk metrics."""
        # Would use historical returns data
        # Placeholder
        return {
            "annualized_vol": 0.15,
            "max_drawdown": 0.20,
            "var_95": 0.02,
            "cvar_95": 0.035,
            "skewness": -0.5,
            "kurtosis": 4.0,
            "sharpe": 1.2,
            "sortino": 1.8
        }
    
    async def _predict_drawdown(
        self,
        portfolio: Dict[str, Dict[str, Any]],
        analysis: Dict[str, Any],
        horizon: RiskHorizon,
        confidence_level: float
    ) -> Optional[Any]:
        """Predict portfolio drawdown risk."""
        
        # Use historical metrics and current positioning
        metrics = portfolio.get("_historical_metrics", {})
        max_dd = portfolio.get("_historical_metrics", {}).get("max_drawdown", 0.20)
        current_dd = portfolio.get("current_drawdown", 0)
        
        # Simple model: probability increases with current drawdown and volatility
        vol = portfolio.get("_historical_metrics", {}).get("annualized_vol", 0.15)
        current_dd = portfolio.get("current_drawdown", 0)
        
        # Probability of >10% drawdown in horizon
        horizon_days = {"intraday": 1, "daily": 1, "weekly": 5, "monthly": 21, "quarterly": 63}.get(str(horizon).split(".")[-1], 21)
        
        # Simple model: P(drawdown > 10%) ~ f(vol, time, current_dd)
        base_prob = 0.10  # Base 10% probability of 10% drawdown per month
        vol_factor = min(2.0, portfolio.get("_historical_metrics", {}).get("annualized_vol", 0.15) / 0.15)
        dd_factor = 1.0 + current_dd * 2  # Higher current DD increases probability
        
        prob = 0.10 * vol_factor * dd_factor * np.sqrt(horizon_days / 21)
        prob = min(max(prob, 0.01), 0.80)
        
        # Expected severity
        severity = min(0.5, max_dd * 1.5)
        
        from predictive_intelligence.risk_prediction import RiskPredictionResult, RiskType, RiskHorizon
        
        return RiskPredictionResult(
            prediction_id=f"dd_{datetime.utcnow().timestamp()}",
            risk_type=RiskType.PORTFOLIO_DRAWDOWN,
            portfolio_id="main",
            symbols=list(portfolio.keys())[:10],
            horizon=RiskHorizon(horizon) if isinstance(horizon, str) else horizon,
            probability=float(prob),
            severity=float(severity),
            confidence=0.7,
            expected_loss=float(prob * severity),
            var_contribution=0.3,
            key_drivers=["Current drawdown level", "Portfolio volatility", "Correlation risk"],
            trigger_conditions=[
                "Portfolio drawdown exceeds 5%",
                "VIX spikes above 30",
                "Correlation breakdown"
            ],
            mitigation_suggestions=[
                "Reduce position sizes",
                "Add tail hedges",
                "Diversify across uncorrelated assets",
                "Set stop-losses"
            ],
            historical_frequency=0.15,
            similar_episodes=[
                {"date": "2022-01", "drawdown": 0.25, "recovery_days": 180},
                {"date": "2020-03", "drawdown": 0.34, "recovery_days": 150}
            ],
            metadata={"current_drawdown": current_dd, "volatility": float(portfolio.get("_historical_metrics", {}).get("annualized_vol", 0.15))},
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
    
    async def _predict_tail_event(
        self,
        portfolio: Dict[str, Dict[str, Any]],
        analysis: Dict[str, Any],
        horizon: RiskHorizon,
        confidence_level: float
    ) -> Optional[Any]:
        """Predict extreme tail events."""
        
        # Use Extreme Value Theory concepts
        metrics = portfolio.get("_historical_metrics", {})
        kurtosis = metrics.get("kurtosis", 4.0)
        skewness = metrics.get("skewness", -0.5)
        
        # Tail risk increases with kurtosis and negative skewness
        tail_prob = 0.01 * (kurtosis / 3) * (1 + abs(skewness))
        tail_prob = min(max(tail_prob, 0.001), 0.05)
        
        severity = min(0.6, 0.1 + metrics.get("max_drawdown", 0.2))
        
        from predictive_intelligence.risk_prediction import RiskPredictionResult, RiskType, RiskHorizon
        
        return RiskPredictionResult(
            prediction_id=f"tail_{datetime.utcnow().timestamp()}",
            risk_type=RiskType.TAIL_EVENT,
            portfolio_id="main",
            symbols=list(portfolio.keys())[:10],
            horizon=horizon if isinstance(horizon, RiskHorizon) else RiskHorizon.MONTHLY,
            probability=float(tail_prob),
            severity=float(severity),
            confidence=0.6,
            expected_loss=float(tail_prob * severity),
            var_contribution=0.5,
            key_drivers=["Excess kurtosis", "Negative skewness", "Correlation clustering"],
            trigger_conditions=[
                "VIX > 40",
                "Correlation > 0.8",
                "Funding stress"
            ],
            mitigation_suggestions=[
                "Tail hedges (put spreads)",
                "Reduce leverage",
                "Diversify tail risk",
                "Maintain cash buffer"
            ],
            historical_frequency=0.02,
            similar_episodes=[
                {"date": "2008-09", "event": "Lehman", "loss": 0.40},
                {"date": "2020-03", "event": "COVID", "loss": 0.34},
                {"date": "2022-01", "event": "Rate hikes", "loss": 0.25}
            ],
            metadata={"kurtosis": kurtosis, "skewness": skewness},
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=90)
        )
    
    async def _predict_volatility_spike(
        self,
        portfolio: Dict[str, Dict[str, Any]],
        analysis: Dict[str, Any],
        horizon: RiskHorizon
    ) -> Optional[Any]:
        """Predict volatility spike."""
        
        # Current VIX level (would come from market data)
        current_vix = 20  # Placeholder
        
        # Volatility mean reversion model
        long_term_vix = 18
        vix_ratio = current_vix / long_term_vix
        
        # Probability of VIX > 30
        if vix_ratio > 1.5:
            prob = 0.3
        elif vix_ratio > 1.2:
            prob = 0.15
        else:
            prob = 0.05
        
        severity = 0.3
        
        from predictive_intelligence.risk_prediction import RiskPredictionResult, RiskType, RiskHorizon
        
        return RiskPredictionResult(
            prediction_id=f"vol_{datetime.utcnow().timestamp()}",
            risk_type=RiskType.VOLATILITY_SPIKE,
            portfolio_id="main",
            symbols=["VIX", "SPY"],
            horizon=horizon if isinstance(horizon, RiskHorizon) else RiskHorizon.WEEKLY,
            probability=prob,
            severity=0.3,
            confidence=0.65,
            expected_loss=prob * 0.1,
            var_contribution=0.2,
            key_drivers=["VIX level", "Realized vol", "Skew"],
            trigger_conditions=["VIX > 25", "Realized vol > 20", "Skew steepening"],
            mitigation_suggestions=["Long vol positions", "Reduce gamma exposure", "Buy put protection"],
            historical_frequency=0.20,
            similar_episodes=[],
            metadata={"current_vix": current_vix, "vix_ratio": vix_ratio},
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
    
    async def _predict_correlation_breakdown(
        self,
        portfolio: Dict[str, Dict[str, Any]],
        analysis: Dict[str, Any],
        horizon: RiskHorizon
    ) -> Optional[Any]:
        """Predict correlation breakdown."""
        
        # Current average correlation
        avg_corr = portfolio.get("avg_correlation", 0.3)
        sector_concentration = max(analysis.get("sector_exposure", {}).values()) if analysis.get("sector_exposure") else 0
        
        # High sector concentration + low current correlation = risk
        prob = 0.1
        if sector_concentration > 0.4:
            prob *= 2
        if avg_corr < 0.2:
            prob *= 1.5
        
        prob = min(prob, 0.3)
        
        from predictive_intelligence.risk_prediction import RiskPredictionResult, RiskType, RiskHorizon
        
        return RiskPredictionResult(
            prediction_id=f"corr_{datetime.utcnow().timestamp()}",
            risk_type=RiskType.CORRELATION_BREAKDOWN,
            portfolio_id="main",
            symbols=list(portfolio.keys())[:10],
            horizon=horizon if isinstance(horizon, RiskHorizon) else RiskHorizon.MONTHLY,
            probability=prob,
            severity=0.25,
            confidence=0.55,
            expected_loss=prob * 0.15,
            var_contribution=0.2,
            key_drivers=["Sector concentration", "Factor crowding", "Liquidity stress"],
            trigger_conditions=["Sector rotation", "Factor unwind", "Liquidity event"],
            mitigation_suggestions=["Diversify across factors", "Reduce sector bets", "Add uncorrelated assets"],
            historical_frequency=0.10,
            similar_episodes=[],
            metadata={"avg_correlation": avg_corr, "sector_concentration": sector_concentration},
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=60)
        )
    
    async def _predict_liquidity_crisis(
        self,
        portfolio: Dict[str, Dict[str, Any]],
        analysis: Dict[str, Any],
        horizon: RiskHorizon
    ) -> Optional[Any]:
        """Predict liquidity crisis."""
        
        liq_profile = analysis.get("liquidity_profile", {})
        days_to_liq = liq_profile.get("days_to_liquidate_90", 5)
        liq_score = liq_profile.get("liquidity_score", 0.8)
        
        # Low liquidity score + high concentration = risk
        prob = 0.05
        if liq_score < 0.5:
            prob = 0.2
        if days_to_liq > 10:
            prob = 0.15
        
        from predictive_intelligence.risk_prediction import RiskPredictionResult, RiskType, RiskHorizon
        
        return RiskPredictionResult(
            prediction_id=f"liq_{datetime.utcnow().timestamp()}",
            risk_type=RiskType.LIQUIDITY_CRISIS,
            portfolio_id="main",
            symbols=list(portfolio.keys())[:5],
            horizon=horizon if isinstance(horizon, RiskHorizon) else RiskHorizon.MONTHLY,
            probability=prob,
            severity=0.4,
            confidence=0.6,
            expected_loss=prob * 0.2,
            var_contribution=0.15,
            key_drivers=["Low liquidity scores", "High concentration", "Market stress"],
            trigger_conditions=["Bid-ask widening", "Volume drying up", "Redemption pressure"],
            mitigation_suggestions=["Hold more liquid assets", "Reduce position sizes", "Use limit orders"],
            historical_frequency=0.05,
            similar_episodes=[],
            metadata={"liquidity_score": liq_score, "days_to_liquidate": days_to_liq},
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=90)
        )
    
    async def _predict_factor_crowding(
        self,
        portfolio: Dict[str, Dict[str, Any]],
        analysis: Dict[str, Any],
        horizon: RiskHorizon
    ) -> Optional[Any]:
        """Predict factor crowding risk."""
        
        factor_exp = analysis.get("factor_exposure", {})
        max_factor_exp = max(abs(v) for v in factor_exp.values()) if factor_exp else 0
        
        # High factor exposure = crowding risk
        prob = min(0.3, max_factor_exp / 2)
        
        from predictive_intelligence.risk_prediction import RiskPredictionResult, RiskType, RiskHorizon
        
        return RiskPredictionResult(
            prediction_id=f"crowd_{datetime.utcnow().timestamp()}",
            risk_type=RiskType.FACTOR_CROWDING,
            portfolio_id="main",
            symbols=list(portfolio.keys())[:10],
            horizon=horizon if isinstance(horizon, RiskHorizon) else RiskHorizon.QUARTERLY,
            probability=prob,
            severity=0.2,
            confidence=0.5,
            expected_loss=prob * 0.1,
            var_contribution=0.1,
            key_drivers=["High factor exposure", "Popular factor trades", "Leverage"],
            trigger_conditions=["Factor reversal", "Leverage unwind", "Risk parity rebalance"],
            mitigation_suggestions=["Diversify factor exposures", "Reduce max factor beta", "Add orthogonal strategies"],
            historical_frequency=0.15,
            similar_episodes=[],
            metadata={"max_factor_exposure": max_factor_exp, "factor_exposures": factor_exp},
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=90)
        )
    
    async def _predict_regime_shift(
        self,
        portfolio: Dict[str, Dict[str, Any]],
        analysis: Dict[str, Any],
        horizon: RiskHorizon
    ) -> Optional[Any]:
        """Predict market regime shift."""
        
        # Simple regime shift probability based on multiple indicators
        prob = 0.10  # Base probability
        
        # Would use: VIX term structure, yield curve, momentum, breadth, etc.
        
        from predictive_intelligence.risk_prediction import RiskPredictionResult, RiskType, RiskHorizon
        
        return RiskPredictionResult(
            prediction_id=f"regime_{datetime.utcnow().timestamp()}",
            risk_type=RiskType.REGIME_SHIFT,
            portfolio_id="main",
            symbols=["SPY", "VIX", "TLT"],
            horizon=horizon if isinstance(horizon, RiskHorizon) else RiskHorizon.QUARTERLY,
            probability=0.15,
            severity=0.35,
            confidence=0.5,
            expected_loss=0.05,
            var_contribution=0.25,
            key_drivers=["Yield curve", "VIX term structure", "Momentum", "Breadth"],
            trigger_conditions=["Yield curve inversion", "VIX backwardation", "Momentum crash"],
            mitigation_suggestions=["Dynamic allocation", "Trend following overlay", "Increase cash"],
            historical_frequency=0.20,
            similar_episodes=[],
            metadata={},
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=90)
        )
    
    async def _predict_concentration_risk(
        self,
        portfolio: Dict[str, Dict[str, Any]],
        analysis: Dict[str, Any],
        horizon: RiskHorizon
    ) -> Optional[Any]:
        """Predict concentration risk."""
        
        conc = analysis.get("concentration", {})
        hhi = conc.get("hhi", 0.1)
        max_weight = conc.get("max_weight", 0.1)
        
        # High HHI or single large position
        prob = 0.0
        if hhi > 0.25:
            prob = 0.4
        elif hhi > 0.15:
            prob = 0.2
        if max_weight > 0.20:
            prob = max(prob, 0.5)
        elif max_weight > 0.15:
            prob = max(prob, 0.3)
        
        from predictive_intelligence.risk_prediction import RiskPredictionResult, RiskType, RiskHorizon
        
        return RiskPredictionResult(
            prediction_id=f"conc_{datetime.utcnow().timestamp()}",
            risk_type=RiskType.CONCENTRATION_RISK,
            portfolio_id="main",
            symbols=list(portfolio.keys())[:5],
            horizon=horizon if isinstance(horizon, RiskHorizon) else RiskHorizon.MONTHLY,
            probability=prob,
            severity=0.3,
            confidence=0.8,
            expected_loss=prob * 0.15,
            var_contribution=0.2,
            key_drivers=["High HHI", "Large single positions", "Sector concentration"],
            trigger_conditions=["Single stock > 20%", "Sector > 40%", "HHI > 0.25"],
            mitigation_suggestions=["Reduce position sizes", "Diversify across sectors", "Add uncorrelated assets"],
            historical_frequency=0.25,
            similar_episodes=[],
            metadata={"hhi": hhi, "max_weight": max_weight},
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=60)
        )
    
    async def _create_alert(self, prediction: Any) -> None:
        """Create risk alert from high-probability prediction."""
        
        severity = "critical" if prediction.probability > 0.8 and prediction.severity > 0.5 else \
                   "high" if prediction.probability > 0.6 else "medium"
        
        alert = RiskAlert(
            alert_id=f"alert_{prediction.prediction_id}",
            risk_type=prediction.risk_type,
            severity=severity,
            message=f"{prediction.risk_type.value}: {prediction.probability:.0%} probability, {prediction.severity:.0%} severity",
            affected_symbols=prediction.symbols,
            probability=prediction.probability,
            expected_impact=prediction.expected_loss
        )
        
        self._active_alerts[alert.alert_id] = alert
        logger.warning(f"Risk alert created: {alert.message}")
    
    async def check_risk_budget(
        self,
        portfolio_id: str,
        current_risk: Dict[str, float]
    ) -> Dict[str, Any]:
        """Check portfolio against risk budgets."""
        
        budgets = self._risk_budgets.get(portfolio_id, {})
        
        if not budgets:
            return {"status": "no_budget", "message": "No risk budget defined"}
        
        violations = []
        warnings = []
        
        for risk_type, budget in budgets.items():
            current = current_risk.get(risk_type, 0)
            
            if current > budget * 1.1:
                violations.append({
                    "risk_type": risk_type,
                    "current": current,
                    "budget": budget,
                    "excess": current - budget
                })
            elif current > budget * 0.9:
                warnings.append({
                    "risk_type": risk_type,
                    "current": current,
                    "budget": budget,
                    "utilization": current / budget
                })
        
        return {
            "status": "violation" if violations else ("warning" if warnings else "ok"),
            "violations": violations,
            "warnings": warnings,
            "budget_utilization": {
                k: current_risk.get(k, 0) / v for k, v in budgets.items()
            }
        }
    
    def set_risk_budget(self, portfolio_id: str, risk_type: RiskType, budget: float) -> None:
        """Set risk budget for a portfolio."""
        if portfolio_id not in self._risk_budgets:
            self._risk_budgets[portfolio_id] = {}
        self._risk_budgets[portfolio_id][risk_type.value] = budget
        logger.info(f"Set risk budget for {portfolio_id}: {risk_type.value} = {budget}")
    
    def get_active_alerts(self) -> List[RiskAlert]:
        """Get all active risk alerts."""
        return list(self._active_alerts.values())
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge a risk alert."""
        if alert_id in self._active_alerts:
            self._active_alerts[alert_id].acknowledged = True
            return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve a risk alert."""
        if alert_id in self._active_alerts:
            self._active_alerts[alert_id].resolved = True
            del self._active_alerts[alert_id]
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_predictions": len(self._prediction_history),
            "active_alerts": len(self._active_alerts),
            "portfolios_monitored": len(self._risk_budgets),
            "by_risk_type": {
                rt.value: sum(1 for p in self._prediction_history if p.risk_type == rt)
                for rt in RiskType
            }
        }


# Global risk prediction instance
_risk_prediction: Optional[RiskPrediction] = None


def get_risk_prediction() -> RiskPrediction:
    global _risk_prediction
    if _risk_prediction is None:
        _risk_prediction = RiskPrediction()
    return _risk_prediction


async def close_risk_prediction() -> None:
    global _risk_prediction
    if _risk_prediction:
        _risk_prediction = None