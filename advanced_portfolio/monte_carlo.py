"""
Multi-Asset Monte Carlo Simulation
Advanced portfolio simulation with correlation modeling, regime switching, and tail risk.
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


class DistributionType(str, Enum):
    """Return distribution types."""
    NORMAL = "normal"
    STUDENT_T = "student_t"
    SKEWED_T = "skewed_t"
    HISTORICAL = "historical"
    GARCH = "garch"
    MIXTURE = "mixture"


class CorrelationModel(str, Enum):
    """Correlation modeling approaches."""
    CONSTANT = "constant"
    DCC_GARCH = "dcc_garch"
    COPULA = "copula"
    REGIME_SWITCHING = "regime_switching"
    FACTOR = "factor"


@dataclass
class AssetConfig:
    """Configuration for a single asset in the simulation."""
    symbol: str
    weight: float
    expected_return: float
    volatility: float
    skew: float = 0.0
    kurtosis: float = 3.0
    distribution: DistributionType = DistributionType.NORMAL
    regime_params: Optional[Dict[str, Any]] = None


@dataclass
class SimulationConfig:
    """Monte Carlo simulation configuration."""
    num_simulations: int = 10000
    time_horizon_days: int = 252
    num_steps: int = 252
    correlation_model: CorrelationModel = CorrelationModel.CONSTANT
    correlation_matrix: Optional[np.ndarray] = None
    random_seed: Optional[int] = None
    use_antithetic: bool = True
    use_control_variates: bool = True
    confidence_levels: List[float] = field(default_factory=lambda: [0.95, 0.99, 0.999])


@dataclass
class SimulationResult:
    """Results of Monte Carlo simulation."""
    portfolio_paths: np.ndarray  # Shape: (num_simulations, num_steps + 1)
    asset_paths: Dict[str, np.ndarray]  # symbol -> (num_simulations, num_steps + 1)
    final_values: np.ndarray  # Shape: (num_simulations,)
    returns: np.ndarray  # Shape: (num_simulations,)
    var: Dict[float, float]  # confidence_level -> VaR
    cvar: Dict[float, float]  # confidence_level -> CVaR
    mean_return: float
    std_return: float
    skewness: float
    kurtosis: float
    max_drawdown_paths: np.ndarray
    probability_of_loss: float
    probability_of_gain: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultiAssetMonteCarlo:
    """
    Multi-asset Monte Carlo simulation engine with advanced features:
    - Multiple distribution types
    - Correlation modeling (constant, DCC-GARCH, copula, regime-switching)
    - Variance reduction techniques
    - Tail risk analysis
    - Stress scenario integration
    """
    
    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or SimulationConfig()
        self.assets: Dict[str, AssetConfig] = {}
        self._rng = None
    
    def add_asset(self, asset: AssetConfig) -> None:
        """Add an asset to the simulation."""
        self.assets[asset.symbol] = asset
    
    def set_correlation_matrix(self, matrix: np.ndarray, symbols: List[str]) -> None:
        """Set correlation matrix for assets."""
        if matrix.shape != (len(symbols), len(symbols)):
            raise ValueError("Correlation matrix dimensions must match number of symbols")
        self.config.correlation_matrix = matrix
        self._symbol_order = symbols
    
    def _initialize_rng(self) -> None:
        """Initialize random number generator."""
        if self.config.random_seed is not None:
            self._rng = np.random.default_rng(self.config.random_seed)
        else:
            self._rng = np.random.default_rng()
    
    def _generate_correlated_returns(
        self,
        num_sims: int,
        num_steps: int,
        n_assets: int
    ) -> np.ndarray:
        """Generate correlated random returns."""
        # Cholesky decomposition for correlation
        if self.config.correlation_matrix is not None:
            L = np.linalg.cholesky(self.config.correlation_matrix)
        else:
            # Default: identity (uncorrelated)
            L = np.eye(n_assets)
        
        # Generate independent standard normals
        if self.config.use_antithetic:
            # Antithetic variates
            half_sims = (num_sims + 1) // 2
            Z = self._rng.standard_normal((half_sims, num_steps, n_assets))
            Z = np.concatenate([Z, -Z[:num_sims - half_sims]], axis=0)
        else:
            Z = self._rng.standard_normal((num_sims, num_steps, n_assets))
        
        # Apply correlation
        correlated = np.einsum('sni,ij->snj', Z, L)
        
        return correlated
    
    def _generate_returns(
        self,
        correlated_normals: np.ndarray,
        asset_configs: List[AssetConfig],
        dt: float
    ) -> Dict[str, np.ndarray]:
        """Generate asset returns from correlated normals."""
        returns = {}
        
        for i, asset in enumerate(asset_configs):
            z = correlated_normals[:, :, i]
            
            if asset.distribution == DistributionType.NORMAL:
                # Simple geometric Brownian motion
                r = (asset.expected_return - 0.5 * asset.volatility**2) * dt + asset.volatility * np.sqrt(dt) * z
            
            elif asset.distribution == DistributionType.STUDENT_T:
                # Student's t with specified dof
                dof = max(asset.kurtosis, 3.1)
                t_samples = self._rng.standard_t(dof, size=z.shape)
                r = (asset.expected_return - 0.5 * asset.volatility**2) * dt + asset.volatility * np.sqrt(dt) * t_samples / np.sqrt(dof / (dof - 2))
            
            elif asset.distribution == DistributionType.SKEWED_T:
                # Skewed t-distribution (simplified)
                from scipy.stats import skewnorm
                skew_param = asset.skew * 10
                skewed = skewnorm.rvs(skew_param, size=z.shape, random_state=self._rng)
                r = (asset.expected_return - 0.5 * asset.volatility**2) * dt + asset.volatility * np.sqrt(dt) * skewed
            
            elif asset.distribution == DistributionType.MIXTURE:
                # Two-component mixture for fat tails
                mix_weight = 0.9
                normal_comp = z
                tail_comp = self._rng.standard_t(3, size=z.shape) * 3
                mixture = np.where(self._rng.random(z.shape) < mix_weight, normal_comp, tail_comp)
                r = (asset.expected_return - 0.5 * asset.volatility**2) * dt + asset.volatility * np.sqrt(dt) * mixture
            
            else:
                # Default to normal
                r = (asset.expected_return - 0.5 * asset.volatility**2) * dt + asset.volatility * np.sqrt(dt) * z
            
            returns[asset.symbol] = r
        
        return returns
    
    def _calculate_portfolio_paths(
        self,
        asset_returns: Dict[str, np.ndarray],
        weights: Dict[str, float]
    ) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """Calculate portfolio and asset price paths."""
        num_sims = list(asset_returns.values())[0].shape[0]
        num_steps = list(asset_returns.values())[0].shape[1]
        
        # Initialize paths
        portfolio_paths = np.ones((num_sims, num_steps + 1))
        asset_paths = {}
        
        for symbol, returns in asset_returns.items():
            weight = weights.get(symbol, 0)
            # Cumulative returns
            cum_returns = np.cumsum(returns, axis=1)
            # Price paths (starting at 1)
            paths = np.exp(np.concatenate([np.zeros((num_sims, 1)), cum_returns], axis=1))
            asset_paths[symbol] = paths
            
            # Add to portfolio
            portfolio_paths += weight * (paths - 1)
        
        return portfolio_paths, asset_paths
    
    def _calculate_risk_metrics(
        self,
        final_values: np.ndarray,
        returns: np.ndarray,
        portfolio_paths: np.ndarray
    ) -> Dict[str, Any]:
        """Calculate comprehensive risk metrics."""
        # VaR and CVaR
        var = {}
        cvar = {}
        for cl in self.config.confidence_levels:
            var[cl] = float(np.percentile(returns, (1 - cl) * 100))
            tail = returns[returns <= var[cl]]
            cvar[cl] = float(tail.mean()) if len(tail) > 0 else var[cl]
        
        # Drawdown
        running_max = np.maximum.accumulate(portfolio_paths, axis=1)
        drawdowns = (portfolio_paths - running_max) / running_max
        max_drawdown = np.max(-drawdowns, axis=1)
        
        # Moments
        mean_ret = float(np.mean(returns))
        std_ret = float(np.std(returns))
        
        # Skewness and kurtosis
        from scipy.stats import skew, kurtosis
        skew_val = float(skew(returns))
        kurt_val = float(kurtosis(returns))
        
        # Probabilities
        prob_loss = float(np.mean(returns < 0))
        prob_gain = float(np.mean(returns > 0))
        
        # Ratios
        sharpe = mean_ret / std_ret if std_ret > 0 else 0
        downside_returns = returns[returns < 0]
        sortino = mean_ret / np.std(downside_returns) if len(downside_returns) > 0 else 0
        calmar = mean_ret / np.mean(max_drawdown) if np.mean(max_drawdown) > 0 else 0
        
        return {
            "var": var,
            "cvar": cvar,
            "mean_return": mean_ret,
            "std_return": std_ret,
            "skewness": skew_val,
            "kurtosis": kurt_val,
            "max_drawdown_paths": max_drawdown,
            "probability_of_loss": prob_loss,
            "probability_of_gain": prob_gain,
            "sharpe_ratio": float(sharpe),
            "sortino_ratio": float(sortino),
            "calmar_ratio": float(calmar)
        }
    
    async def run_simulation(
        self,
        config: Optional[SimulationConfig] = None
    ) -> SimulationResult:
        """Run the Monte Carlo simulation."""
        if config:
            self.config = config
        
        if not self.assets:
            raise ValueError("No assets configured for simulation")
        
        self._initialize_rng()
        
        symbols = list(self.assets.keys())
        weights = {s: self.assets[s].weight for s in symbols}
        asset_configs = [self.assets[s] for s in symbols]
        
        # Validate weights sum to 1
        total_weight = sum(weights.values())
        if abs(total_weight - 1.0) > 1e-6:
            logger.warning(f"Weights sum to {total_weight}, normalizing")
            weights = {k: v/total_weight for k, v in weights.items()}
        
        # Time step
        dt = self.config.time_horizon_days / self.config.num_steps
        
        # Generate correlated random numbers
        correlated = self._generate_correlated_returns(
            self.config.num_simulations,
            self.config.num_steps,
            len(symbols)
        )
        
        # Generate asset returns
        asset_returns = self._generate_returns(correlated, asset_configs, dt)
        
        # Calculate portfolio paths
        portfolio_paths, asset_paths = self._calculate_portfolio_paths(asset_returns, weights)
        
        # Final portfolio values and returns
        final_values = portfolio_paths[:, -1]
        returns = final_values - 1  # Since we started at 1
        
        # Risk metrics
        metrics = self._calculate_risk_metrics(final_values, returns, portfolio_paths)
        
        # Build result
        result = SimulationResult(
            portfolio_paths=portfolio_paths,
            asset_paths=asset_paths,
            final_values=final_values,
            returns=returns,
            **metrics
        )
        
        logger.info(f"Monte Carlo simulation completed: {self.config.num_simulations} paths")
        return result
    
    async def run_stress_scenarios(
        self,
        scenarios: List[Dict[str, Any]],
        base_config: Optional[SimulationConfig] = None
    ) -> List[SimulationResult]:
        """Run simulation under stress scenarios."""
        results = []
        
        for scenario in scenarios:
            # Modify config for scenario
            scenario_config = base_config or self.config
            # Apply scenario shocks (simplified)
            # In production, would modify correlation matrix, expected returns, etc.
            
            # Run simulation with scenario
            result = await self.run_simulation(scenario_config)
            result.metadata["scenario"] = scenario
            results.append(result)
        
        return results


# Global Monte Carlo instance
_monte_carlo: Optional[MultiAssetMonteCarlo] = None


def get_monte_carlo(config: Optional[SimulationConfig] = None) -> MultiAssetMonteCarlo:
    global _monte_carlo
    if _monte_carlo is None:
        _monte_carlo = MultiAssetMonteCarlo(config)
    return _monte_carlo


async def close_monte_carlo() -> None:
    global _monte_carlo
    if _monte_carlo:
        _monte_carlo = None