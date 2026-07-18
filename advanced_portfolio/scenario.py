"""
Scenario Simulator
Advanced scenario simulation for portfolio analysis with regime switching and factor models.
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


class FactorType(str, Enum):
    """Types of risk factors."""
    MACRO = "macro"               # GDP, inflation, unemployment
    RATES = "rates"               # Interest rates, yield curve
    EQUITY = "equity"             # Equity market factors
    CREDIT = "credit"             # Credit spreads, defaults
    FX = "fx"                     # Foreign exchange
    COMMODITY = "commodity"       # Commodities
    VOLATILITY = "volatility"     # Volatility surfaces
    LIQUIDITY = "liquidity"       # Funding liquidity
    SENTIMENT = "sentiment"       # Market sentiment
    TECHNICAL = "technical"       # Technical indicators


class ScenarioMethod(str, Enum):
    """Scenario generation methods."""
    MONTE_CARLO = "monte_carlo"           # Full Monte Carlo
    HISTORICAL = "historical"              # Historical simulation
    PARAMETRIC = "parametric"             # Parametric (e.g., PCA)
    FACTOR_MODEL = "factor_model"         # Factor model based
    REGIME_SWITCHING = "regime_switching" # Regime-switching model
    MACHINE_LEARNING = "ml"               # ML-based scenario generation


@dataclass
class FactorShock:
    """Shock to a risk factor."""
    factor_name: str
    factor_type: FactorType
    shock_magnitude: float  # Standard deviations or absolute change
    duration: int = 1  # Days
    decay: float = 0.0  # Exponential decay rate
    correlation_impact: Dict[str, float] = field(default_factory=dict)
    description: str = ""


@dataclass
class ScenarioPath:
    """Single scenario path through time."""
    scenario_id: str
    timestamps: List[datetime]
    factor_values: Dict[str, np.ndarray]  # factor -> values over time
    portfolio_values: np.ndarray  # Portfolio value over time
    asset_values: Dict[str, np.ndarray]  # symbol -> values over time
    weights: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScenarioResult:
    """Result of scenario simulation."""
    scenario_name: str
    method: ScenarioMethod
    paths: List[ScenarioPath]
    summary_stats: Dict[str, Any]
    generated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ScenarioSimulator:
    """
    Advanced scenario simulator for portfolio analysis.
    Supports multiple generation methods including regime-switching and factor models.
    """
    
    def __init__(self):
        self._factor_models: Dict[str, Any] = {}
        self._regime_models: Dict[str, Any] = {}
        self._historical_data: Dict[str, np.ndarray] = {}
        self._scenario_cache: Dict[str, ScenarioResult] = {}
    
    def load_historical_factors(
        self,
        factor_names: List[str],
        data: Dict[str, np.ndarray],
        timestamps: Optional[List[datetime]] = None
    ) -> None:
        """Load historical factor data for simulation."""
        for name in factor_names:
            if name in data:
                self._historical_data[name] = data[name]
        
        if timestamps:
            self._factor_timestamps = timestamps
    
    def register_factor_model(
        self,
        factor_name: str,
        model: Callable
    ) -> None:
        """Register a custom factor model."""
        self._factor_models[factor_name] = model
    
    def register_regime_model(
        self,
        name: str,
        model: Callable
    ) -> None:
        """Register a regime-switching model."""
        self._regime_models[name] = model
    
    async def simulate_scenarios(
        self,
        scenario_name: str,
        factor_shocks: List[FactorShock],
        portfolio_assets: Dict[str, Dict[str, Any]],  # symbol -> {weight, beta, etc.}
        num_paths: int = 1000,
        time_horizon: int = 252,
        method: ScenarioMethod = ScenarioMethod.MONTE_CARLO,
        base_factors: Optional[Dict[str, float]] = None
    ) -> ScenarioResult:
        """Simulate scenarios with specified factor shocks."""
        
        logger.info(f"Simulating scenario: {scenario_name} with {num_paths} paths")
        
        if method == ScenarioMethod.MONTE_CARLO:
            result = await self._monte_carlo_scenarios(
                scenario_name, factor_shocks, portfolio_assets, num_paths, time_horizon, base_factors
            )
        elif method == ScenarioMethod.HISTORICAL:
            result = await self._historical_scenarios(
                scenario_name, factor_shocks, portfolio_assets, num_paths, time_horizon
            )
        elif method == ScenarioMethod.FACTOR_MODEL:
            result = await self._factor_model_scenarios(
                scenario_name, factor_shocks, portfolio_assets, num_paths, time_horizon
            )
        elif method == ScenarioMethod.REGIME_SWITCHING:
            result = await self._regime_switching_scenarios(
                scenario_name, factor_shocks, portfolio_assets, num_paths, time_horizon
            )
        else:
            raise NotImplementedError(f"Method {method} not implemented")
        
        self._scenario_cache[scenario_name] = result
        return result
    
    async def _monte_carlo_scenarios(
        self,
        scenario_name: str,
        factor_shocks: List[FactorShock],
        portfolio_assets: Dict[str, Dict[str, Any]],
        num_paths: int,
        time_horizon: int,
        base_factors: Optional[Dict[str, float]]
    ) -> ScenarioResult:
        """Monte Carlo scenario generation."""
        
        paths = []
        factor_names = [fs.factor_name for fs in factor_shocks]
        n_factors = len(factor_names)
        
        # Build correlation matrix for factors
        corr_matrix = self._build_factor_correlation(factor_shocks)
        
        # Cholesky decomposition
        L = np.linalg.cholesky(corr_matrix)
        
        timestamps = [datetime.utcnow() + timedelta(days=i) for i in range(time_horizon + 1)]
        
        for path_idx in range(num_paths):
            # Generate correlated random walks for factors
            factor_paths = {}
            dt = 1.0  # Daily steps
            
            for f_idx, shock in enumerate(factor_shocks):
                # Generate random walk with drift
                n_steps = time_horizon
                increments = np.random.randn(n_steps) * np.sqrt(dt)
                
                # Apply shock
                if shock.shock_magnitude != 0:
                    shock_step = int(shock.duration * time_horizon / max(sum(fs.duration for fs in factor_shocks), 1))
                    shock_step = max(1, min(shock_step, n_steps))
                    increments[:shock_step] += shock.shock_magnitude / shock_step
                
                # Random walk
                path = np.cumsum(increments)
                if base_factors and shock.factor_name in base_factors:
                    path += base_factors[shock.factor_name]
                
                factor_paths[shock.factor_name] = path
            
            # Calculate portfolio path
            portfolio_path = self._calculate_portfolio_path(
                factor_paths, portfolio_assets, factor_shocks, time_horizon
            )
            
            # Calculate individual asset paths
            asset_paths = {}
            for symbol, asset_info in portfolio_assets.items():
                asset_paths[symbol] = self._calculate_asset_path(
                    symbol, asset_info, factor_paths, factor_shocks, time_horizon
                )
            
            sp = ScenarioPath(
                scenario_id=f"{scenario_name}_{path_idx}",
                timestamps=[datetime.utcnow() + timedelta(days=i) for i in range(time_horizon + 1)],
                factor_values=factor_paths,
                portfolio_values=portfolio_path,
                asset_values=asset_paths,
                weights={s: a.get('weight', 0) for s, a in portfolio_assets.items()}
            )
            paths.append(sp)
        
        # Summary statistics
        final_values = np.array([p.portfolio_values[-1] for p in paths])
        returns = final_values - 1.0  # Starting at 1
        
        summary = {
            "mean_return": float(np.mean(returns)),
            "std_return": float(np.std(returns)),
            "var_95": float(np.percentile(returns, 5)),
            "var_99": float(np.percentile(returns, 1)),
            "max_drawdown_mean": float(np.mean([self._max_drawdown(p.portfolio_values) for p in paths])),
            "prob_loss": float(np.mean(returns < 0)),
            "paths_generated": num_paths
        }
        
        return ScenarioResult(
            scenario_name=scenario_name,
            method=ScenarioMethod.MONTE_CARLO,
            paths=paths,
            summary_stats=summary
        )
    
    async def _historical_scenarios(
        self,
        scenario_name: str,
        factor_shocks: List[FactorShock],
        portfolio_assets: Dict[str, Dict[str, Any]],
        num_paths: int,
        time_horizon: int
    ) -> ScenarioResult:
        """Historical simulation using past market data."""
        
        if not self._historical_data:
            raise ValueError("No historical data loaded for historical simulation")
        
        # Use historical windows
        available_history = min(len(list(self._historical_data.values())[0]), time_horizon)
        window_size = available_history
        
        paths = []
        timestamps = [datetime.utcnow() + timedelta(days=i) for i in range(window_size + 1)]
        
        for path_idx in range(min(num_paths, len(list(self._historical_data.values())[0]) - window_size)):
            # Random starting point in history
            start_idx = np.random.randint(0, len(list(self._historical_data.values())[0]) - window_size)
            
            factor_paths = {}
            for shock in factor_shocks:
                if shock.factor_name in self._historical_data:
                    hist_data = self._historical_data[shock.factor_name]
                    path = hist_data[start_idx:start_idx + window_size]
                    factor_paths[shock.factor_name] = path
            
            portfolio_path = self._calculate_portfolio_path(
                factor_paths, portfolio_assets, factor_shocks, window_size
            )
            
            asset_paths = {}
            for symbol, asset_info in portfolio_assets.items():
                asset_paths[symbol] = self._calculate_asset_path(
                    symbol, asset_info, factor_paths, factor_shocks, window_size
                )
            
            sp = ScenarioPath(
                scenario_id=f"{scenario_name}_hist_{path_idx}",
                timestamps=timestamps,
                factor_values=factor_paths,
                portfolio_values=portfolio_path,
                asset_values=asset_paths
            )
            paths.append(sp)
        
        final_values = np.array([p.portfolio_values[-1] for p in paths])
        returns = final_values - 1.0
        
        summary = {
            "mean_return": float(np.mean(returns)),
            "std_return": float(np.std(returns)),
            "var_95": float(np.percentile(returns, 5)),
            "var_99": float(np.percentile(returns, 1)),
            "paths_generated": len(paths)
        }
        
        return ScenarioResult(
            scenario_name=scenario_name,
            method=ScenarioMethod.HISTORICAL,
            paths=paths,
            summary_stats=summary
        )
    
    async def _factor_model_scenarios(
        self,
        scenario_name: str,
        factor_shocks: List[FactorShock],
        portfolio_assets: Dict[str, Dict[str, Any]],
        num_paths: int,
        time_horizon: int
    ) -> ScenarioResult:
        """Factor model based scenario generation."""
        
        # Define risk factors
        risk_factors = {
            "market": {"beta": 1.0, "vol": 0.16},
            "size": {"beta": 0.0, "vol": 0.10},
            "value": {"beta": 0.0, "vol": 0.12},
            "momentum": {"beta": 0.0, "vol": 0.15},
            "quality": {"beta": 0.0, "vol": 0.10},
            "rates": {"beta": 0.0, "vol": 0.08},
            "credit": {"beta": 0.0, "vol": 0.10},
            "fx": {"beta": 0.0, "vol": 0.10},
        }
        
        # Apply custom betas from portfolio assets
        for symbol, info in portfolio_assets.items():
            if "betas" in info:
                for factor, beta in info["betas"].items():
                    if factor in risk_factors:
                        risk_factors[factor]["asset_betas"] = risk_factors[factor].get("asset_betas", {})
                        risk_factors[factor]["asset_betas"][symbol] = beta
        
        # Generate factor returns
        paths = []
        timestamps = [datetime.utcnow() + timedelta(days=i) for i in range(time_horizon + 1)]
        
        for path_idx in range(num_paths):
            factor_returns = {}
            
            for factor_name, factor_info in risk_factors.items():
                vol = factor_info["vol"]
                daily_vol = vol / np.sqrt(252)
                returns = np.random.randn(time_horizon) * daily_vol
                factor_returns[factor_name] = returns
            
            # Apply shocks
            for shock in factor_shocks:
                if shock.factor_name in factor_returns:
                    n_shock = min(shock.duration, time_horizon)
                    factor_returns[shock.factor_name][:n_shock] += shock.shock_magnitude / max(n_shock, 1)
            
            # Calculate portfolio and asset paths using factor model
            portfolio_path = self._factor_model_portfolio_path(
                factor_returns, portfolio_assets, risk_factors
            )
            
            asset_paths = {}
            for symbol, asset_info in portfolio_assets.items():
                asset_paths[symbol] = self._factor_model_asset_path(
                    symbol, asset_info, factor_returns, risk_factors
                )
            
            sp = ScenarioPath(
                scenario_id=f"{scenario_name}_fm_{path_idx}",
                timestamps=[datetime.utcnow() + timedelta(days=i) for i in range(time_horizon + 1)],
                factor_values=factor_returns,
                portfolio_values=portfolio_path,
                asset_values=asset_paths
            )
            paths.append(sp)
        
        final_values = np.array([p.portfolio_values[-1] for p in paths])
        returns = final_values - 1.0
        
        summary = {
            "mean_return": float(np.mean(returns)),
            "std_return": float(np.std(returns)),
            "var_95": float(np.percentile(returns, 5)),
            "var_99": float(np.percentile(returns, 1)),
            "paths_generated": num_paths
        }
        
        return ScenarioResult(
            scenario_name=scenario_name,
            method=ScenarioMethod.FACTOR_MODEL,
            paths=paths,
            summary_stats=summary
        )
    
    async def _regime_switching_scenarios(
        self,
        scenario_name: str,
        factor_shocks: List[FactorShock],
        portfolio_assets: Dict[str, Dict[str, Any]],
        num_paths: int,
        time_horizon: int
    ) -> ScenarioResult:
        """Regime-switching scenario generation (e.g., Markov-switching)."""
        
        # Define regimes
        regimes = {
            "bull": {
                "prob": 0.6,
                "market_mean": 0.10 / 252,
                "market_vol": 0.12 / np.sqrt(252),
                "correlation": 0.3,
                "transition": {"bull": 0.95, "bear": 0.03, "crisis": 0.02}
            },
            "bear": {
                "prob": 0.3,
                "market_mean": -0.15 / 252,
                "market_vol": 0.25 / np.sqrt(252),
                "correlation": 0.6,
                "transition": {"bull": 0.10, "bear": 0.85, "crisis": 0.05}
            },
            "crisis": {
                "prob": 0.1,
                "market_mean": -0.30 / 252,
                "market_vol": 0.45 / np.sqrt(252),
                "correlation": 0.9,
                "transition": {"bull": 0.05, "bear": 0.20, "crisis": 0.75}
            }
        }
        
        paths = []
        timestamps = [datetime.utcnow() + timedelta(days=i) for i in range(time_horizon + 1)]
        
        for path_idx in range(num_paths):
            # Simulate regime path
            current_regime = np.random.choice(
                list(regimes.keys()),
                p=[r["prob"] for r in regimes.values()]
            )
            
            regime_path = [current_regime]
            for _ in range(time_horizon - 1):
                trans = regimes[current_regime]["transition"]
                current_regime = np.random.choice(
                    list(trans.keys()),
                    p=list(trans.values())
                )
                regime_path.append(current_regime)
            
            # Generate returns conditional on regime
            factor_returns = {"market": np.zeros(time_horizon)}
            
            for t, regime_name in enumerate(regime_path):
                regime = regimes[regime_name]
                daily_ret = np.random.normal(regime["market_mean"], regime["market_vol"])
                factor_returns["market"][t] = daily_ret
            
            # Apply shocks
            for shock in factor_shocks:
                if shock.factor_name in factor_returns:
                    n_shock = min(shock.duration, time_horizon)
                    factor_returns[shock.factor_name][:n_shock] += shock.shock_magnitude / max(n_shock, 1)
            
            portfolio_path = self._factor_model_portfolio_path(
                factor_returns, portfolio_assets, {"market": {"beta": 1.0}}
            )
            
            asset_paths = {}
            for symbol, asset_info in portfolio_assets.items():
                beta = asset_info.get("betas", {}).get("market", 1.0)
                asset_paths[symbol] = np.cumprod(1 + beta * factor_returns["market"])
                asset_paths[symbol] = np.concatenate([[1.0], asset_paths[symbol]])
            
            sp = ScenarioPath(
                scenario_id=f"{scenario_name}_rs_{path_idx}",
                timestamps=[datetime.utcnow() + timedelta(days=i) for i in range(time_horizon + 1)],
                factor_values=factor_returns,
                portfolio_values=portfolio_path,
                asset_values=asset_paths,
                metadata={"regime_path": regime_path}
            )
            paths.append(sp)
        
        final_values = np.array([p.portfolio_values[-1] for p in paths])
        returns = final_values - 1.0
        
        summary = {
            "mean_return": float(np.mean(returns)),
            "std_return": float(np.std(returns)),
            "var_95": float(np.percentile(returns, 5)),
            "var_99": float(np.percentile(returns, 1)),
            "regime_distribution": self._calculate_regime_distribution(paths),
            "paths_generated": num_paths
        }
        
        return ScenarioResult(
            scenario_name=scenario_name,
            method=ScenarioMethod.REGIME_SWITCHING,
            paths=paths,
            summary_stats=summary
        )
    
    def _build_factor_correlation(self, factor_shocks: List[FactorShock]) -> np.ndarray:
        """Build correlation matrix for factors."""
        n = len(factor_shocks)
        corr = np.eye(n)
        
        for i, fs1 in enumerate(factor_shocks):
            for j, fs2 in enumerate(factor_shocks):
                if i != j:
                    # Use explicit correlation impact if specified
                    if fs2.factor_name in fs1.correlation_impact:
                        corr[i, j] = fs1.correlation_impact[fs2.factor_name]
                    elif fs1.factor_name in fs2.correlation_impact:
                        corr[i, j] = fs2.correlation_impact[fs1.factor_name]
                    else:
                        # Default correlations by factor type
                        corr[i, j] = self._default_correlation(fs1.factor_type, fs2.factor_type)
        
        # Ensure positive definite
        eigenvals = np.linalg.eigvals(corr)
        if np.min(eigenvals) < 1e-8:
            corr = corr + np.eye(n) * 1e-6
        
        return corr
    
    def _default_correlation(self, type1: FactorType, type2: FactorType) -> float:
        """Default correlation between factor types."""
        correlation_matrix = {
            (FactorType.MACRO, FactorType.RATES): 0.4,
            (FactorType.MACRO, FactorType.EQUITY): 0.3,
            (FactorType.MACRO, FactorType.CREDIT): 0.3,
            (FactorType.RATES, FactorType.EQUITY): -0.2,
            (FactorType.RATES, FactorType.CREDIT): 0.5,
            (FactorType.EQUITY, FactorType.CREDIT): 0.4,
            (FactorType.FX, FactorType.COMMODITY): 0.3,
            (FactorType.VOLATILITY, FactorType.EQUITY): -0.7,
        }
        
        key = (type1, type2) if (type1, type2) in correlation_matrix else (type2, type1)
        return correlation_matrix.get(key, 0.0)
    
    def _calculate_portfolio_path(
        self,
        factor_paths: Dict[str, np.ndarray],
        portfolio_assets: Dict[str, Dict[str, Any]],
        factor_shocks: List[FactorShock],
        time_horizon: int
    ) -> np.ndarray:
        """Calculate portfolio value path."""
        n_steps = time_horizon
        portfolio_path = np.ones(n_steps + 1)
        
        for symbol, asset_info in portfolio_assets.items():
            weight = asset_info.get("weight", 0)
            if weight == 0:
                continue
            
            # Calculate asset returns from factor exposures
            asset_returns = np.zeros(n_steps)
            
            for shock in factor_shocks:
                beta = asset_info.get("betas", {}).get(shock.factor_name, 0)
                if beta != 0 and shock.factor_name in factor_paths:
                    asset_returns += beta * factor_paths[shock.factor_name]
            
            # Add idiosyncratic risk
            idio_vol = asset_info.get("idio_vol", 0.02) / np.sqrt(252)
            asset_returns += np.random.randn(n_steps) * idio_vol
            
            # Asset price path
            asset_path = np.cumprod(1 + asset_returns)
            asset_path = np.concatenate([[1.0], asset_path])
            
            portfolio_path += weight * (asset_path - 1)
        
        return portfolio_path
    
    def _calculate_asset_path(
        self,
        symbol: str,
        asset_info: Dict[str, Any],
        factor_paths: Dict[str, np.ndarray],
        factor_shocks: List[FactorShock],
        time_horizon: int
    ) -> np.ndarray:
        """Calculate individual asset path."""
        n_steps = time_horizon
        asset_returns = np.zeros(n_steps)
        
        for shock in factor_shocks:
            beta = asset_info.get("betas", {}).get(shock.factor_name, 0)
            if beta != 0 and shock.factor_name in factor_paths:
                asset_returns += beta * factor_paths[shock.factor_name]
        
        idio_vol = asset_info.get("idio_vol", 0.02) / np.sqrt(252)
        asset_returns += np.random.randn(n_steps) * idio_vol
        
        asset_path = np.cumprod(1 + asset_returns)
        return np.concatenate([[1.0], asset_path])
    
    def _factor_model_portfolio_path(
        self,
        factor_returns: Dict[str, np.ndarray],
        portfolio_assets: Dict[str, Dict[str, Any]],
        risk_factors: Dict[str, Any]
    ) -> np.ndarray:
        """Calculate portfolio path using factor model."""
        n_steps = len(list(factor_returns.values())[0])
        portfolio_path = np.ones(n_steps + 1)
        
        for symbol, asset_info in portfolio_assets.items():
            weight = asset_info.get("weight", 0)
            if weight == 0:
                continue
            
            asset_returns = np.zeros(n_steps)
            betas = asset_info.get("betas", {})
            
            for factor_name, returns in factor_returns.items():
                beta = betas.get(factor_name, risk_factors.get(factor_name, {}).get("asset_betas", {}).get(symbol, 0))
                asset_returns += beta * returns
            
            # Idiosyncratic
            idio_vol = asset_info.get("idio_vol", 0.02) / np.sqrt(252)
            asset_returns += np.random.randn(n_steps) * idio_vol
            
            asset_path = np.cumprod(1 + asset_returns)
            asset_path = np.concatenate([[1.0], asset_path])
            
            portfolio_path += weight * (asset_path - 1)
        
        return portfolio_path
    
    def _factor_model_asset_path(
        self,
        symbol: str,
        asset_info: Dict[str, Any],
        factor_returns: Dict[str, np.ndarray],
        risk_factors: Dict[str, Any]
    ) -> np.ndarray:
        """Calculate asset path using factor model."""
        n_steps = len(list(factor_returns.values())[0])
        betas = asset_info.get("betas", {})
        
        asset_returns = np.zeros(n_steps)
        for factor_name, returns in factor_returns.items():
            beta = betas.get(factor_name, 0)
            asset_returns += beta * returns
        
        idio_vol = asset_info.get("idio_vol", 0.02) / np.sqrt(252)
        asset_returns += np.random.randn(n_steps) * idio_vol
        
        asset_path = np.cumprod(1 + asset_returns)
        return np.concatenate([[1.0], asset_path])
    
    def _max_drawdown(self, values: np.ndarray) -> float:
        """Calculate maximum drawdown."""
        running_max = np.maximum.accumulate(values)
        drawdown = (values - running_max) / running_max
        return float(np.min(drawdown))
    
    def _calculate_regime_distribution(self, paths: List[ScenarioPath]) -> Dict[str, float]:
        """Calculate distribution of regimes across paths."""
        regime_counts = defaultdict(int)
        
        for path in paths:
            if "regime_path" in path.metadata:
                for regime in path.metadata["regime_path"]:
                    regime_counts[regime] += 1
        
        total = sum(regime_counts.values())
        if total == 0:
            return {}
        
        return {k: v / total for k, v in regime_counts.items()}
    
    def get_cached_result(self, scenario_name: str) -> Optional[ScenarioResult]:
        """Get cached scenario result."""
        return self._scenario_cache.get(scenario_name)
    
    def clear_cache(self) -> None:
        """Clear scenario cache."""
        self._scenario_cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "cached_scenarios": len(self._scenario_cache),
            "factor_models": len(self._factor_models),
            "regime_models": len(self._regime_models),
            "historical_factors": len(self._historical_data)
        }


# Global scenario simulator instance
_scenario_simulator: Optional[ScenarioSimulator] = None


def get_scenario_simulator() -> ScenarioSimulator:
    global _scenario_simulator
    if _scenario_simulator is None:
        _scenario_simulator = ScenarioSimulator()
    return _scenario_simulator


async def close_scenario_simulator() -> None:
    global _scenario_simulator
    if _scenario_simulator:
        _scenario_simulator = None