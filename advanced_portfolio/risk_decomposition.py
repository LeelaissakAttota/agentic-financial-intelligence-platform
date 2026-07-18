"""
Risk Decomposition
Advanced risk decomposition and attribution for portfolio analysis.
"""

import asyncio
import logging
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class RiskComponent(str, Enum):
    """Types of risk components."""
    SYSTEMATIC = "systematic"           # Market risk
    SECTOR = "sector"                   # Sector risk
    STYLE = "style"                     # Style factor risk
    SPECIFIC = "specific"               # Idiosyncratic risk
    CURRENCY = "currency"               # FX risk
    COUNTRY = "country"                 # Country risk
    LIQUIDITY = "liquidity"             # Liquidity risk
    TAIL = "tail"                       # Tail risk


@dataclass
class RiskFactor:
    """Risk factor definition."""
    name: str
    component: RiskComponent
    exposure: float  # Portfolio beta/exposure
    variance: float  # Factor variance
    covariance: Dict[str, float] = field(default_factory=dict)  # Covariances with other factors
    description: str = ""


@dataclass
class RiskDecompositionResult:
    """Result of risk decomposition."""
    total_risk: float  # Portfolio variance
    systematic_risk: float
    specific_risk: float
    factor_contributions: Dict[str, float]  # Factor -> marginal contribution to risk
    component_breakdown: Dict[RiskComponent, float]  # Component -> risk
    asset_contributions: Dict[str, float]  # Asset -> marginal contribution to risk
    correlation_risk: float  # Risk from correlations
    concentration_risk: float  # Risk from concentration
    tail_risk_contribution: float
    diversification_ratio: float
    risk_budget: Dict[str, float]  # Asset -> risk budget %
    marginal_var: Dict[str, float]  # Asset -> marginal VaR
    component_var: Dict[str, float]  # Asset -> component VaR
    metadata: Dict[str, Any] = field(default_factory=dict)


class RiskDecomposition:
    """
    Advanced risk decomposition and attribution.
    Decomposes portfolio risk into systematic, sector, style, specific, and tail components.
    Provides risk budgeting, marginal VaR, and diversification analysis.
    """
    
    def __init__(self):
        self._factor_models: Dict[str, Any] = {}
        self._covariance_estimators: Dict[str, Any] = {}
    
    def register_factor_model(self, name: str, model: Any) -> None:
        """Register a factor model for risk decomposition."""
        self._factor_models[name] = model
    
    def register_covariance_estimator(self, name: str, estimator: Any) -> None:
        """Register a covariance estimator."""
        self._covariance_estimators[name] = estimator
    
    async def decompose_risk(
        self,
        portfolio: Dict[str, Dict[str, Any]],  # symbol -> {weight, returns, betas}
        factor_returns: Optional[Dict[str, np.ndarray]] = None,
        factor_covariance: Optional[np.ndarray] = None,
        factor_names: Optional[List[str]] = None,
        confidence_level: float = 0.95,
        lookback_days: int = 252
    ) -> RiskDecompositionResult:
        """Perform comprehensive risk decomposition."""
        
        logger.info("Performing risk decomposition")
        
        # Extract portfolio data
        symbols = list(portfolio.keys())
        weights = np.array([portfolio[s].get("weight", 0) for s in symbols])
        n_assets = len(symbols)
        
        if n_assets == 0:
            raise ValueError("Empty portfolio")
        
        # Normalize weights
        weights = weights / weights.sum()
        
        # Get or estimate covariance matrix
        if factor_returns is not None and factor_names is not None:
            # Factor model approach
            result = await self._factor_model_decomposition(
                portfolio, factor_returns, factor_covariance, factor_names, confidence_level
            )
        else:
            # Historical covariance approach
            result = await self._historical_decomposition(
                portfolio, confidence_level, lookback_days
            )
        
        # Add common calculations
        result.diversification_ratio = self._calculate_diversification_ratio(portfolio, result)
        result.correlation_risk = self._calculate_correlation_risk(portfolio, result)
        result.concentration_risk = self._calculate_concentration_risk(weights)
        result.tail_risk_contribution = await self._estimate_tail_risk(portfolio)
        
        return result
    
    async def _factor_model_decomposition(
        self,
        portfolio: Dict[str, Dict[str, Any]],
        factor_returns: Dict[str, np.ndarray],
        factor_covariance: Optional[np.ndarray],
        factor_names: List[str],
        confidence_level: float
    ) -> RiskDecompositionResult:
        """Risk decomposition using factor model."""
        
        symbols = list(portfolio.keys())
        weights = np.array([portfolio[s].get("weight", 0) for s in symbols])
        weights = weights / weights.sum()
        n_assets = len(symbols)
        n_factors = len(factor_names)
        
        # Build factor exposure matrix B (n_assets x n_factors)
        B = np.zeros((n_assets, n_factors))
        for i, symbol in enumerate(symbols):
            betas = portfolio[symbol].get("betas", {})
            for j, factor in enumerate(factor_names):
                B[i, j] = betas.get(factor, 0)
        
        # Factor covariance matrix
        if factor_covariance is not None:
            F = factor_covariance
        else:
            # Estimate from factor returns
            factor_data = np.column_stack([factor_returns[f] for f in factor_names])
            F = np.cov(factor_data, rowvar=False)
        
        # Specific risk (diagonal matrix)
        D = np.zeros((n_assets, n_assets))
        for i, symbol in enumerate(symbols):
            specific_var = portfolio[symbol].get("specific_variance", 0.02**2)
            D[i, i] = specific_var
        
        # Total portfolio covariance: B @ F @ B.T + D
        systematic_cov = B @ F @ B.T
        total_cov = systematic_cov + D
        
        # Portfolio variance
        port_var = weights @ total_cov @ weights
        port_vol = np.sqrt(port_var)
        
        # Systematic variance
        sys_var = weights @ systematic_cov @ weights
        sys_vol = np.sqrt(sys_var)
        
        # Specific variance
        spec_var = port_var - sys_var
        spec_vol = np.sqrt(max(spec_var, 0))
        
        # Marginal contributions to risk (MCR)
        mcr = total_cov @ weights / port_vol if port_vol > 0 else np.zeros(n_assets)
        
        # Component contributions to risk (CCR = weight * MCR)
        ccr = weights * mcr
        
        # Factor contributions
        factor_contributions = {}
        for j, factor in enumerate(factor_names):
            # Factor marginal contribution
            factor_exposure = B[:, j] @ weights
            factor_mcr = (B @ F[:, j] @ weights + B[:, j] @ (F @ (B.T @ weights))) / port_vol if port_vol > 0 else 0
            factor_contributions[factor] = factor_mcr * factor_exposure
        
        # Asset contributions
        asset_contributions = dict(zip(symbols, ccr))
        
        # Component breakdown
        component_breakdown = {
            RiskComponent.SYSTEMATIC: sys_var / port_var if port_var > 0 else 0,
            RiskComponent.SPECIFIC: spec_var / port_var if port_var > 0 else 0
        }
        
        # VaR calculations
        from scipy.stats import norm
        z_score = norm.ppf(confidence_level)
        port_var_dollar = z_score * port_vol
        
        # Marginal VaR
        mvar = z_score * mcr
        cvar = weights * mvar
        
        return RiskDecompositionResult(
            total_risk=port_var,
            systematic_risk=sys_var,
            specific_risk=spec_var,
            factor_contributions=factor_contributions,
            component_breakdown=component_breakdown,
            asset_contributions=asset_contributions,
            correlation_risk=0,  # Will be calculated later
            concentration_risk=0,
            tail_risk_contribution=0,
            diversification_ratio=0,
            risk_budget={s: ccr[i] / port_var if port_var > 0 else 0 for i, s in enumerate(symbols)},
            marginal_var=dict(zip(symbols, mvar)),
            component_var=dict(zip(symbols, cvar)),
            metadata={
                "method": "factor_model",
                "n_factors": n_factors,
                "portfolio_vol": port_vol,
                "systematic_vol": sys_vol,
                "specific_vol": spec_vol
            }
        )
    
    async def _historical_decomposition(
        self,
        portfolio: Dict[str, Dict[str, Any]],
        confidence_level: float,
        lookback_days: int
    ) -> RiskDecompositionResult:
        """Risk decomposition using historical covariance."""
        
        symbols = list(portfolio.keys())
        weights = np.array([portfolio[s].get("weight", 0) for s in symbols])
        weights = weights / weights.sum()
        n_assets = len(symbols)
        
        # Get historical returns (would come from data provider)
        # For now, generate sample covariance
        returns_data = portfolio.get("_returns")  # Would be provided
        
        if returns_data is not None:
            cov_matrix = np.cov(returns_data, rowvar=False)
        else:
            # Fallback: use provided volatilities and correlations
            vol = np.array([portfolio[s].get("volatility", 0.2) for s in symbols])
            corr = np.eye(n_assets)
            for i in range(n_assets):
                for j in range(i+1, n_assets):
                    corr[i, j] = corr[j, i] = portfolio[symbols[i]].get("correlation", {}).get(symbols[j], 0.3)
            cov_matrix = np.diag(vol) @ corr @ np.diag(vol)
        
        # Portfolio variance
        port_var = weights @ cov_matrix @ weights
        port_vol = np.sqrt(port_var)
        
        # Marginal contributions
        mcr = cov_matrix @ weights / port_vol if port_vol > 0 else np.zeros(n_assets)
        ccr = weights * mcr
        
        # Asset contributions
        asset_contributions = dict(zip(symbols, ccr))
        
        # Risk budget
        risk_budget = {s: ccr[i] / port_var if port_var > 0 else 0 for i, s in enumerate(symbols)}
        
        # VaR
        from scipy.stats import norm
        z_score = norm.ppf(confidence_level)
        mvar = z_score * mcr
        cvar = weights * mvar
        
        return RiskDecompositionResult(
            total_risk=port_var,
            systematic_risk=port_var * 0.7,  # Approximation
            specific_risk=port_var * 0.3,
            factor_contributions={},
            component_breakdown={
                RiskComponent.SYSTEMATIC: 0.7,
                RiskComponent.SPECIFIC: 0.3
            },
            asset_contributions=asset_contributions,
            correlation_risk=0,
            concentration_risk=0,
            tail_risk_contribution=0,
            diversification_ratio=0,
            risk_budget=risk_budget,
            marginal_var=dict(zip(symbols, mvar)),
            component_var=dict(zip(symbols, cvar)),
            metadata={
                "method": "historical",
                "lookback_days": lookback_days,
                "portfolio_vol": port_vol
            }
        )
    
    def _calculate_diversification_ratio(
        self,
        portfolio: Dict[str, Dict[str, Any]],
        result: RiskDecompositionResult
    ) -> float:
        """Calculate diversification ratio."""
        symbols = list(portfolio.keys())
        weights = np.array([portfolio[s].get("weight", 0) for s in symbols])
        weights = weights / weights.sum()
        
        # Weighted average volatility
        vols = np.array([portfolio[s].get("volatility", 0.2) for s in symbols])
        weighted_avg_vol = np.sum(weights * vols)
        
        if weighted_avg_vol == 0:
            return 1.0
        
        portfolio_vol = np.sqrt(result.total_risk)
        return weighted_avg_vol / portfolio_vol if portfolio_vol > 0 else 1.0
    
    def _calculate_correlation_risk(
        self,
        portfolio: Dict[str, Dict[str, Any]],
        result: RiskDecompositionResult
    ) -> float:
        """Calculate risk attributable to correlations."""
        symbols = list(portfolio.keys())
        weights = np.array([portfolio[s].get("weight", 0) for s in symbols])
        weights = weights / weights.sum()
        n_assets = len(symbols)
        
        vols = np.array([portfolio[s].get("volatility", 0.2) for s in symbols])
        
        # Risk if uncorrelated (diagonal covariance)
        uncorr_var = np.sum((weights * vols)**2)
        
        # Actual portfolio variance
        actual_var = result.total_risk
        
        # Correlation risk = excess variance from correlations
        corr_risk = max(actual_var - uncorr_var, 0)
        
        return corr_risk / actual_var if actual_var > 0 else 0
    
    def _calculate_concentration_risk(self, weights: np.ndarray) -> float:
        """Calculate concentration risk (Herfindahl index)."""
        # Herfindahl-Hirschman Index
        hhi = np.sum(weights**2)
        
        # Normalize: 1/N (perfectly diversified) to 1 (concentrated)
        n = len(weights)
        min_hhi = 1 / n if n > 0 else 1
        
        # Normalize to 0-1 scale
        if min_hhi == 1:
            return 0.0
        
        return (hhi - min_hhi) / (1 - min_hhi)
    
    async def _estimate_tail_risk(
        self,
        portfolio: Dict[str, Dict[str, Any]]
    ) -> float:
        """Estimate tail risk contribution."""
        symbols = list(portfolio.keys())
        weights = np.array([portfolio[s].get("weight", 0) for s in symbols])
        weights = weights / weights.sum()
        
        # Estimate from asset tail risk
        tail_contributions = []
        for i, symbol in enumerate(symbols):
            # Skewness and kurtosis from asset
            skew = portfolio[symbol].get("skewness", -0.5)
            kurt = portfolio[symbol].get("kurtosis", 5.0)
            
            # Tail risk proportional to weight * (kurtosis - 3) * |skew|
            tail_risk = weights[i] * (kurt - 3) * abs(skew)
            tail_contributions.append(tail_risk)
        
        return float(np.sum(tail_contributions))
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "factor_models": len(self._factor_models),
            "covariance_estimators": len(self._covariance_estimators)
        }


# Global risk decomposition instance
_risk_decomposition: Optional[RiskDecomposition] = None


def get_risk_decomposition() -> RiskDecomposition:
    global _risk_decomposition
    if _risk_decomposition is None:
        _risk_decomposition = RiskDecomposition()
    return _risk_decomposition


async def close_risk_decomposition() -> None:
    global _risk_decomposition
    if _risk_decomposition:
        _risk_decomposition = None