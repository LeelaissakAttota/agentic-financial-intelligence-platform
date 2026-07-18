"""
Analytics Module - Phase 5: Advanced Analytics & Reporting

Provides advanced analytics, reporting, and quantitative analysis capabilities.
"""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

import asyncpg
import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


class AnalyticsBackend(ABC):
    """Abstract analytics storage backend."""
    
    @abstractmethod
    async def save_report(self, report: "AnalyticsReport") -> None:
        pass
    
    @abstractmethod
    async def get_report(self, report_id: str) -> Optional["AnalyticsReport"]:
        pass
    
    @abstractmethod
    async def find_reports(
        self,
        portfolio_id: str = None,
        report_type: str = None,
        start_date: date = None,
        end_date: date = None,
        limit: int = 100
    ) -> list["AnalyticsReport"]:
        pass
    
    @abstractmethod
    async def save_analysis(self, analysis: "QuantAnalysis") -> None:
        pass
    
    @abstractmethod
    async def get_analysis(self, analysis_id: str) -> Optional["QuantAnalysis"]:
        pass
    
    @abstractmethod
    async def save_factor_analysis(self, analysis: "FactorAnalysis") -> None:
        pass
    
    @abstractmethod
    async def get_factor_analysis(self, analysis_id: str) -> Optional["FactorAnalysis"]:
        pass


@dataclass
class AnalyticsReport:
    """A generated analytics report."""
    id: str = field(default_factory=lambda: str(uuid4()))
    portfolio_id: str = ""
    report_type: str = ""
    title: str = ""
    description: str = ""
    period_start: date = field(default_factory=date.today)
    period_end: date = field(default_factory=date.today)
    generated_at: datetime = field(default_factory=datetime.utcnow)
    generated_by: str = ""
    content: dict = field(default_factory=dict)
    charts: list[dict] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    format: str = "json"  # json, pdf, html
    status: str = "completed"
    metadata: dict = field(default_factory=dict)


@dataclass
class QuantAnalysis:
    """A quantitative analysis result."""
    id: str = field(default_factory=lambda: str(uuid4()))
    portfolio_id: str = ""
    analysis_type: str = ""
    title: str = ""
    description: str = ""
    period_start: date = field(default_factory=date.today)
    period_end: date = field(default_factory=date.today)
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    results: dict = field(default_factory=dict)
    charts: list[dict] = field(default_factory=list)
    methodology: str = ""
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    confidence: str = "medium"
    metadata: dict = field(default_factory=dict)


@dataclass
class FactorAnalysis:
    """Factor-based analysis results."""
    id: str = field(default_factory=lambda: str(uuid4()))
    portfolio_id: str = ""
    model_name: str = ""  # e.g., "Fama-French 3-factor", "Fama-French 5-factor", "Custom"
    factors: list[str] = field(default_factory=list)
    period_start: date = field(default_factory=date.today)
    period_end: date = field(default_factory=date.today)
    factor_loadings: dict[str, float] = field(default_factory=dict)
    factor_returns: dict[str, float] = field(default_factory=dict)
    alpha: float = 0.0
    alpha_t_stat: float = 0.0
    r_squared: float = 0.0
    adjusted_r_squared: float = 0.0
    residual_volatility: float = 0.0
    information_ratio: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)


@dataclass
class RiskMetrics:
    """Comprehensive risk metrics for a portfolio."""
    portfolio_id: str = ""
    period_start: date = field(default_factory=date.today)
    period_end: date = field(default_factory=date.today)
    
    # Value at Risk
    var_95: float = 0.0
    var_99: float = 0.0
    cvar_95: float = 0.0
    cvar_99: float = 0.0
    
    # Volatility
    daily_volatility: float = 0.0
    annualized_volatility: float = 0.0
    downside_volatility: float = 0.0
    
    # Returns
    total_return: float = 0.0
    annualized_return: float = 0.0
    excess_return: float = 0.0
    
    # Risk-adjusted
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    information_ratio: float = 0.0
    
    # Tail risk
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    avg_drawdown: float = 0.0
    avg_drawdown_duration: float = 0.0
    
    # Higher moments
    skewness: float = 0.0
    kurtosis: float = 0.0
    tail_ratio: float = 0.0
    
    # Stress testing
    stress_scenarios: dict[str, float] = field(default_factory=dict)
    
    # Correlation
    correlation_to_market: float = 0.0
    correlation_to_sector: float = 0.0
    
    # Factor exposures
    factor_exposures: dict[str, float] = field(default_factory=dict)
    
    # Liquidity
    avg_daily_volume: float = 0.0
    liquidity_score: float = 0.0
    
    # Concentration
    herfindahl_index: float = 0.0
    max_position_weight: float = 0.0
    top_10_concentration: float = 0.0
    
    metadata: dict = field(default_factory=dict)


class AnalyticsEngine:
    """Core analytics engine for quantitative analysis."""
    
    def __init__(self, portfolio_manager=None, market_data_provider=None):
        self.portfolio_manager = portfolio_manager
        self.market_data = market_data_provider
        self._cache: dict[str, Any] = {}
    
    # ==================== Risk Metrics ====================
    
    async def calculate_risk_metrics(
        self,
        portfolio_id: str,
        period_start: date = None,
        period_end: date = None,
        benchmark_symbol: str = "SPY"
    ) -> RiskMetrics:
        """Calculate comprehensive risk metrics for a portfolio."""
        
        if not self.portfolio_manager:
            raise ValueError("Portfolio manager not configured")
        
        portfolio = await self.portfolio_manager.get_portfolio(portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        
        # Get historical snapshots
        end_date = period_end or date.today()
        start_date = period_start or (end_date - timedelta(days=252))
        
        snapshots = await self.portfolio_manager.backend.get_snapshots(
            portfolio_id, start_date, end_date
        )
        
        if len(snapshots) < 2:
            logger.warning(f"Insufficient data for risk metrics: {len(snapshots)} snapshots")
            return RiskMetrics(portfolio_id=portfolio_id)
        
        # Build returns series
        returns = self._calculate_returns(snapshots)
        
        # Get benchmark data
        benchmark_returns = await self._get_benchmark_returns(
            benchmark_symbol, start_date, end_date
        )
        
        # Calculate metrics
        metrics = RiskMetrics(
            portfolio_id=portfolio_id,
            period_start=start_date,
            period_end=end_date
        )
        
        # VaR/CVaR
        metrics.var_95 = self._calculate_var(returns, 0.95)
        metrics.var_99 = self._calculate_var(returns, 0.99)
        metrics.cvar_95 = self._calculate_cvar(returns, 0.95)
        metrics.cvar_99 = self._calculate_cvar(returns, 0.99)
        
        # Volatility
        metrics.daily_volatility = float(np.std(returns))
        metrics.annualized_volatility = metrics.daily_volatility * np.sqrt(252)
        
        # Downside volatility
        negative_returns = [r for r in returns if r < 0]
        metrics.downside_volatility = float(np.std(negative_returns)) * np.sqrt(252) if negative_returns else 0
        
        # Returns
        metrics.total_return = float((snapshots[-1].total_value - snapshots[0].total_value) / snapshots[0].total_value)
        metrics.annualized_return = (1 + metrics.total_return) ** (252 / len(returns)) - 1
        
        # Benchmark comparison
        if benchmark_returns and len(benchmark_returns) == len(returns):
            metrics.excess_return = metrics.annualized_return - self._annualize_return(benchmark_returns)
            metrics.correlation_to_market = float(np.corrcoef(returns, benchmark_returns)[0, 1])
            metrics.information_ratio = self._calculate_information_ratio(returns, benchmark_returns)
        
        # Risk-adjusted metrics
        risk_free_rate = 0.02  # Assume 2% risk-free
        excess_returns = np.array(returns) - risk_free_rate / 252
        metrics.sharpe_ratio = float(np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)) if np.std(excess_returns) > 0 else 0
        metrics.sortino_ratio = float(np.mean(excess_returns) / np.std([r for r in excess_returns if r < 0]) * np.sqrt(252)) if negative_returns else 0
        
        # Drawdown analysis
        dd_metrics = self._calculate_drawdowns(snapshots)
        metrics.max_drawdown = dd_metrics["max_drawdown"]
        metrics.max_drawdown_duration = dd_metrics["max_duration"]
        metrics.avg_drawdown = dd_metrics["avg_drawdown"]
        metrics.avg_drawdown_duration = dd_metrics["avg_duration"]
        
        # Tail risk
        metrics.skewness = float(stats.skew(returns))
        metrics.kurtosis = float(stats.kurtosis(returns))
        metrics.tail_ratio = self._calculate_tail_ratio(returns)
        
        # Calmar ratio
        metrics.calmar_ratio = metrics.annualized_return / abs(metrics.max_drawdown) if metrics.max_drawdown != 0 else 0
        
        # Beta and alpha
        if benchmark_returns and len(benchmark_returns) == len(returns):
            beta, alpha = self._calculate_beta_alpha(returns, benchmark_returns)
            metrics.factor_exposures["market_beta"] = beta
            metrics.factor_exposures["alpha"] = alpha
        
        # Concentration metrics
        if portfolio.positions:
            weights = [float(p.market_value / portfolio.total_value) for p in portfolio.positions.values()]
            metrics.herfindahl_index = sum(w**2 for w in weights)
            metrics.max_position_weight = max(weights)
            metrics.top_10_concentration = sum(sorted(weights, reverse=True)[:10])
        
        return metrics
    
    def _calculate_returns(self, snapshots: list) -> list[float]:
        """Calculate returns from portfolio snapshots."""
        returns = []
        for i in range(1, len(snapshots)):
            prev_val = float(snapshots[i-1].total_value)
            curr_val = float(snapshots[i].total_value)
            if prev_val > 0:
                returns.append((curr_val - prev_val) / prev_val)
        return returns
    
    def _calculate_var(self, returns: list[float], confidence: float) -> float:
        """Calculate Value at Risk."""
        returns_arr = np.array(returns)
        return float(np.percentile(returns_arr, (1 - confidence) * 100))
    
    def _calculate_cvar(self, returns: list[float], confidence: float) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall)."""
        var = self._calculate_var(returns, confidence)
        returns_arr = np.array(returns)
        tail_returns = returns_arr[returns_arr <= var]
        return float(np.mean(tail_returns)) if len(tail_returns) > 0 else var
    
    def _calculate_drawdowns(self, snapshots: list) -> dict:
        """Calculate drawdown metrics."""
        values = [float(s.total_value) for s in snapshots]
        peak = values[0]
        drawdowns = []
        durations = []
        current_duration = 0
        
        for val in values:
            if val > peak:
                peak = val
                current_duration = 0
            else:
                dd = (peak - val) / peak
                drawdowns.append(dd)
                current_duration += 1
                durations.append(current_duration)
        
        return {
            "max_drawdown": max(drawdowns) if drawdowns else 0,
            "max_duration": max(durations) if durations else 0,
            "avg_drawdown": np.mean(drawdowns) if drawdowns else 0,
            "avg_duration": np.mean(durations) if durations else 0
        }
    
    def _calculate_tail_ratio(self, returns: list[float]) -> float:
        """Calculate tail ratio (95th percentile / 5th percentile)."""
        returns_arr = np.array(returns)
        p95 = np.percentile(returns_arr, 95)
        p5 = np.percentile(returns_arr, 5)
        return abs(p95 / p5) if p5 != 0 else 0
    
    def _calculate_information_ratio(self, returns: list, benchmark_returns: list) -> float:
        """Calculate Information Ratio."""
        returns_arr = np.array(returns)
        bench_arr = np.array(benchmark_returns)
        excess = returns_arr - bench_arr
        tracking_error = np.std(excess)
        return float(np.mean(excess) / tracking_error * np.sqrt(252)) if tracking_error > 0 else 0
    
    def _calculate_beta_alpha(self, returns: list, benchmark_returns: list) -> tuple[float, float]:
        """Calculate beta and alpha using linear regression."""
        returns_arr = np.array(returns)
        bench_arr = np.array(benchmark_returns)
        
        # Excess returns over risk-free (simplified)
        slope, intercept, r_value, p_value, std_err = stats.linregress(bench_arr, returns_arr)
        beta = float(slope)
        alpha = float(intercept) * 252  # Annualized
        return beta, alpha
    
    def _annualize_return(self, returns: list) -> float:
        """Annualize returns."""
        if not returns:
            return 0
        cumulative = np.prod([1 + r for r in returns]) - 1
        return (1 + cumulative) ** (252 / len(returns)) - 1
    
    async def _get_benchmark_returns(self, symbol: str, start: date, end: date) -> list[float]:
        """Get benchmark returns from market data provider."""
        if not self.market_data:
            return []
        
        # This would use the market data provider
        # For now, return empty
        return []
    
    # ==================== Factor Analysis ====================
    
    async def run_factor_analysis(
        self,
        portfolio_id: str,
        model: str = "fama_french_5",
        period_start: date = None,
        period_end: date = None
    ) -> FactorAnalysis:
        """Run factor analysis on portfolio returns."""
        
        if not self.portfolio_manager:
            raise ValueError("Portfolio manager not configured")
        
        portfolio = await self.portfolio_manager.get_portfolio(portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        
        end_date = period_end or date.today()
        start_date = period_start or (end_date - timedelta(days=252))
        
        snapshots = await self.portfolio_manager.backend.get_snapshots(
            portfolio_id, start_date, end_date
        )
        
        if len(snapshots) < 30:
            raise ValueError("Insufficient data for factor analysis")
        
        returns = self._calculate_returns(snapshots)
        
        # Get factor data (would need factor data provider)
        # For now, use placeholder
        factors = self._get_factor_data(model, start_date, end_date)
        
        # Run regression
        if model == "fama_french_3":
            factor_names = ["MKT-RF", "SMB", "HML"]
        elif model == "fama_french_5":
            factor_names = ["MKT-RF", "SMB", "HML", "RMW", "CMA"]
        elif model == "fama_french_5_momentum":
            factor_names = ["MKT-RF", "SMB", "HML", "RMW", "CMA", "MOM"]
        else:
            factor_names = ["MKT-RF"]
        
        # Run OLS regression
        X = np.column_stack([factors[f] for f in factor_names if f in factors])
        y = np.array(returns)
        
        if X.shape[0] != len(y):
            # Align lengths
            min_len = min(X.shape[0], len(y))
            X = X[:min_len]
            y = y[:min_len]
        
        # Add constant for alpha
        X = np.column_stack([np.ones(X.shape[0]), X])
        
        # OLS
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        alpha = beta[0] * 252  # Annualized
        factor_loadings = beta[1:]
        
        # Predicted values
        y_pred = X @ beta
        residuals = y - y_pred
        
        # Statistics
        rss = np.sum(residuals**2)
        tss = np.sum((y - np.mean(y))**2)
        r_squared = 1 - rss / tss if tss > 0 else 0
        adj_r_squared = 1 - (1 - r_squared) * (len(y) - 1) / (len(y) - X.shape[1])
        
        residual_vol = np.std(residuals) * np.sqrt(252)
        
        # Factor returns (annualized)
        factor_returns = {}
        for i, name in enumerate(factor_names):
            if i < len(factors[name]):
                factor_returns[name] = float(np.mean(factors[name]) * 252)
        
        # T-stat for alpha
        alpha_se = np.std(residuals) / np.sqrt(len(residuals))
        alpha_t_stat = alpha / alpha_se if alpha_se > 0 else 0
        
        # Information ratio
        excess_returns = np.array(returns) - np.mean(factors.get("MKT-RF", [0]))
        info_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252) if np.std(excess_returns) > 0 else 0
        
        return FactorAnalysis(
            portfolio_id=portfolio_id,
            model_name=model,
            factors=factor_names,
            period_start=start_date,
            period_end=end_date,
            factor_loadings=dict(zip(factor_names, [float(b) for b in factor_loadings])),
            factor_returns=factor_returns,
            alpha=alpha,
            alpha_t_stat=alpha_t_stat,
            r_squared=r_squared,
            adjusted_r_squared=adj_r_squared,
            residual_volatility=residual_vol,
            information_ratio=info_ratio,
            metadata={
                "sample_size": len(returns),
                "model": model
            }
        )
    
    def _get_factor_data(self, model: str, start: date, end: date) -> dict[str, list]:
        """Get factor data for analysis (placeholder)."""
        # In production, this would fetch from factor data provider
        # Ken French data library, etc.
        n_days = (end - start).days
        return {
            "MKT-RF": np.random.normal(0.0005, 0.01, n_days).tolist(),
            "SMB": np.random.normal(0.0001, 0.005, n_days).tolist(),
            "HML": np.random.normal(0.0001, 0.005, n_days).tolist(),
            "RMW": np.random.normal(0.0001, 0.005, n_days).tolist(),
            "CMA": np.random.normal(0.0001, 0.005, n_days).tolist(),
            "MOM": np.random.normal(0.0002, 0.008, n_days).tolist()
        }
    
    # ==================== Performance Attribution ====================
    
    async def attribution_analysis(
        self,
        portfolio_id: str,
        benchmark_id: str = "SPY",
        period_start: date = None,
        period_end: date = None
    ) -> dict:
        """Perform Brinson-Hood-Beebower attribution analysis."""
        
        if not self.portfolio_manager:
            raise ValueError("Portfolio manager not configured")
        
        portfolio = await self.portfolio_manager.get_portfolio(portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        
        end_date = period_end or date.today()
        start_date = period_start or (end_date - timedelta(days=90))
        
        # Get portfolio snapshots
        snapshots = await self.portfolio_manager.backend.get_snapshots(
            portfolio_id, start_date, period_end
        )
        
        if len(snapshots) < 2:
            raise ValueError("Insufficient data for attribution")
        
        # Get benchmark data
        benchmark_returns = await self._get_benchmark_returns(benchmark_id, start_date, end_date)
        
        # Simplified attribution (would need sector/industry data for full Brinson)
        returns = self._calculate_returns(snapshots)
        
        # Simple attribution: allocation + selection + interaction
        # This is simplified - full implementation needs sector weights and returns
        total_return = np.prod([1 + r for r in returns]) - 1
        benchmark_return = np.prod([1 + r for r in benchmark_returns]) - 1 if benchmark_returns else 0
        
        return {
            "portfolio_return": float(total_return),
            "benchmark_return": float(benchmark_return),
            "excess_return": float(total_return - benchmark_return),
            "allocation_effect": 0.0,  # Would need sector data
            "selection_effect": 0.0,   # Would need sector data
            "interaction_effect": 0.0, # Would need sector data
            "total_return": float(total_return),
            "period_start": start_date,
            "period_end": end_date
        }
    
    # ==================== Monte Carlo Simulation ====================
    
    async def monte_carlo_simulation(
        self,
        portfolio_id: str,
        num_simulations: int = 200,
        time_horizon_days: int = 252,
        initial_value: float = None
    ) -> dict:
        """Run Monte Carlo simulation for portfolio projections."""
        
        if not self.portfolio_manager:
            raise ValueError("Portfolio manager not configured")
        
        portfolio = await self.portfolio_manager.get_portfolio(portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        
        # Get historical returns
        snapshots = await self.portfolio_manager.backend.get_snapshots(
            portfolio_id, date.today() - timedelta(days=252), date.today()
        )
        
        if len(snapshots) < 30:
            raise ValueError("Insufficient historical data")
        
        returns = self._calculate_returns(snapshots)
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        # Get initial value
        start_value = initial_value or float(portfolio.total_value)
        
        # Run simulations
        np.random.seed(42)
        simulations = []
        
        for _ in range(num_simulations):
            # Generate random returns
            sim_returns = np.random.normal(mean_return, std_return, time_horizon_days)
            
            # Calculate path
            path = [start_value]
            for r in sim_returns:
                path.append(path[-1] * (1 + r))
            
            simulations.append({
                "final_value": path[-1],
                "total_return": (path[-1] - start_value) / start_value,
                "max_drawdown": self._calculate_path_drawdown(path),
                "path": path[::max(1, time_horizon_days // 100)]  # Sample for storage
            })
        
        # Aggregate results
        final_values = [s["final_value"] for s in simulations]
        returns = [s["total_return"] for s in simulations]
        drawdowns = [s["max_drawdown"] for s in simulations]
        
        return {
            "portfolio_id": portfolio_id,
            "num_simulations": num_simulations,
            "time_horizon_days": time_horizon_days,
            "initial_value": start_value,
            "mean_final_value": float(np.mean(final_values)),
            "median_final_value": float(np.median(final_values)),
            "percentile_5": float(np.percentile(final_values, 5)),
            "percentile_25": float(np.percentile(final_values, 25)),
            "percentile_75": float(np.percentile(final_values, 75)),
            "percentile_95": float(np.percentile(final_values, 95)),
            "prob_profit": float(sum(1 for r in returns if r > 0) / len(returns)),
            "mean_return": float(np.mean(returns)),
            "median_return": float(np.median(returns)),
            "var_95": float(np.percentile(returns, 5)),
            "cvar_95": float(np.mean([r for r in returns if r <= np.percentile(returns, 5)])),
            "max_drawdown_mean": float(np.mean(drawdowns)),
            "max_drawdown_95": float(np.percentile(drawdowns, 95)),
            "sample_paths": [s["path"] for s in simulations[:10]]  # Store 10 sample paths
        }
    
    def _calculate_path_drawdown(self, path: list[float]) -> float:
        peak = path[0]
        max_dd = 0
        for val in path:
            if val > peak:
                peak = val
            dd = (peak - val) / peak
            max_dd = max(max_dd, dd)
        return max_dd
    
    # ==================== Correlation Analysis ====================
    
    async def correlation_analysis(
        self,
        symbols: list[str],
        period_start: date = None,
        period_end: date = None,
        method: str = "pearson"
    ) -> dict:
        """Analyze correlations between assets."""
        
        if not self.market_data:
            raise ValueError("Market data provider not configured")
        
        end_date = period_end or date.today()
        start_date = period_start or (end_date - timedelta(days=252))
        
        # Fetch price data for all symbols
        price_data = {}
        for symbol in symbols:
            data = await self.market_data.get_historical_prices(symbol, start_date, end_date)
            if data:
                price_data[symbol] = pd.Series(data['close'], index=pd.to_datetime(data['date']))
        
        if len(price_data) < 2:
            raise ValueError("Need at least 2 symbols with data")
        
        # Align dates
        df = pd.DataFrame(price_data).dropna()
        returns = df.pct_change().dropna()
        
        # Calculate correlation matrix
        if method == "pearson":
            corr_matrix = returns.corr(method='pearson')
        elif method == "spearman":
            corr_matrix = returns.corr(method='spearman')
        elif method == "kendall":
            corr_matrix = returns.corr(method='kendall')
        else:
            raise ValueError(f"Unknown correlation method: {method}")
        
        # Find highly correlated pairs
        high_corr_pairs = []
        for i in range(len(symbols)):
            for j in range(i+1, len(symbols)):
                corr = corr_matrix.iloc[i, j]
                if abs(corr) > 0.7:
                    high_corr_pairs.append({
                        "symbol1": symbols[i],
                        "symbol2": symbols[j],
                        "correlation": float(corr)
                    })
        
        # Find uncorrelated pairs (diversification candidates)
        low_corr_pairs = []
        for i in range(len(symbols)):
            for j in range(i+1, len(symbols)):
                corr = corr_matrix.iloc[i, j]
                if abs(corr) < 0.3:
                    low_corr_pairs.append({
                        "symbol1": symbols[i],
                        "symbol2": symbols[j],
                        "correlation": float(corr)
                    })
        
        # Eigenvalues for PCA
        eigenvals, eigenvecs = np.linalg.eigh(corr_matrix.values)
        explained_variance = eigenvals / np.sum(eigenvals)
        
        return {
            "correlation_matrix": corr_matrix.to_dict(),
            "symbols": symbols,
            "method": method,
            "period_start": start_date,
            "period_end": end_date,
            "high_correlation_pairs": high_corr_pairs,
            "low_correlation_pairs": low_corr_pairs,
            "explained_variance": explained_variance.tolist(),
            "num_effective_factors": sum(explained_variance > 0.1),
            "condition_number": float(np.max(eigenvals) / np.min(eigenvals)) if np.min(eigenvals) > 0 else float('inf')
        }
    
    # ==================== Scenario Analysis ====================
    
    async def scenario_analysis(
        self,
        portfolio_id: str,
        scenarios: list[dict] = None
    ) -> dict:
        """Run scenario analysis on portfolio."""
        
        if not self.portfolio_manager:
            raise ValueError("Portfolio manager not configured")
        
        portfolio = await self.portfolio_manager.get_portfolio(portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        
        # Default scenarios
        if scenarios is None:
            scenarios = [
                {"name": "Market Crash", "market_shock": -0.30, "vol_multiplier": 2.0},
                {"name": "Bear Market", "market_shock": -0.20, "vol_multiplier": 1.5},
                {"name": "Correction", "market_shock": -0.10, "vol_multiplier": 1.2},
                {"name": "Bull Market", "market_shock": 0.20, "vol_multiplier": 0.8},
                {"name": "Volatility Spike", "market_shock": -0.05, "vol_multiplier": 3.0},
                {"name": "Interest Rate Hike", "rate_shock": 0.02, "duration_shock": -0.10},
                {"name": "Inflation Shock", "inflation_shock": 0.02, "real_rate_shock": 0.01},
                {"name": "Credit Crisis", "spread_widening": 0.02, "equity_shock": -0.15},
                {"name": "Currency Crisis", "fx_shock": -0.15, "local_equity_shock": -0.20},
                {"name": "Commodity Shock", "oil_shock": 0.50, "energy_weight": 0.05}
            ]
        
        # Get current portfolio value and positions
        current_value = float(portfolio.total_value)
        positions = portfolio.positions
        
        results = []
        
        for scenario in scenarios:
            scenario_value = current_value
            position_impacts = {}
            
            # Apply scenario to each position
            for symbol, position in positions.items():
                pos_value = float(position.market_value)
                impact = self._apply_scenario_to_position(
                    symbol, pos_value, scenario
                )
                scenario_value += impact
                position_impacts[symbol] = {
                    "original_value": pos_value,
                    "impact": impact,
                    "new_value": pos_value + impact
                }
            
            total_change = scenario_value - current_value
            pct_change = total_change / current_value if current_value else 0
            
            results.append({
                "scenario": scenario["name"],
                "portfolio_value": scenario_value,
                "change": total_change,
                "pct_change": pct_change,
                "position_impacts": position_impacts,
                "max_position_loss": min((v["impact"] for v in position_impacts.values()), default=0),
                "max_position_gain": max((v["impact"] for v in position_impacts.values()), default=0)
            })
        
        return {
            "portfolio_id": portfolio_id,
            "current_value": current_value,
            "base_date": date.today().isoformat(),
            "scenarios": results,
            "worst_case": min(results, key=lambda x: x["pct_change"])["pct_change"],
            "best_case": max(results, key=lambda x: x["pct_change"])["pct_change"],
            "expected_change": float(np.mean([s["pct_change"] for s in results]))
        }
    
    def _apply_scenario_to_position(self, symbol: str, value: float, scenario: dict) -> float:
        """Apply scenario shock to a single position."""
        # Simplified - would use factor models in production
        shock = scenario.get("market_shock", 0)
        vol_mult = scenario.get("vol_multiplier", 1.0)
        
        # Simple beta-adjusted shock (would use factor model in production)
        beta = 1.0  # Placeholder
        impact = value * shock * beta
        
        # Add volatility impact
        if vol_mult != 1.0:
            impact *= vol_mult
        
        return impact
    
    # ==================== Report Generation ====================
    
    async def generate_report(
        self,
        portfolio_id: str,
        report_type: str = "comprehensive",
        period_start: date = None,
        period_end: date = None
    ) -> AnalyticsReport:
        """Generate analytics report for portfolio."""
        
        if not self.portfolio_manager:
            raise ValueError("Portfolio manager not configured")
        
        portfolio = await self.portfolio_manager.get_portfolio(portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        
        end_date = period_end or date.today()
        start_date = period_start or (period_end - timedelta(days=90))
        
        report = AnalyticsReport(
            portfolio_id=portfolio_id,
            report_type=report_type,
            title=f"{report_type.title()} Report - {portfolio.name}",
            description=f"{report_type} analysis for {portfolio.name}",
            period_start=start_date,
            period_end=end_date,
            generated_by="analytics_engine"
        )
        
        if report_type == "comprehensive":
            # Risk metrics
            risk_metrics = await self.calculate_risk_metrics(portfolio_id, start_date, end_date)
            report.metrics["risk"] = risk_metrics.__dict__
            
            # Performance
            snapshots = await self.portfolio_manager.backend.get_snapshots(
                portfolio_id, start_date, end_date
            )
            returns = self._calculate_returns(snapshots)
            
            report.metrics["performance"] = {
                "total_return": float(np.prod([1+r for r in returns]) - 1),
                "annualized_return": self._annualize_return(returns),
                "volatility": float(np.std(returns) * np.sqrt(252)),
                "sharpe": float(np.mean(returns) / np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0,
                "max_drawdown": self._calculate_drawdowns(snapshots)["max_drawdown"],
                "win_rate": sum(1 for r in returns if r > 0) / len(returns) if returns else 0
            }
            
            # Risk metrics
            risk = await self.calculate_risk_metrics(portfolio_id, start_date, end_date)
            report.metrics["risk"] = risk.__dict__
            
            # Attribution
            try:
                attr = await self.attribution_analysis(portfolio_id)
                report.metrics["attribution"] = attr
            except:
                pass
            
            # Monte Carlo
            try:
                mc = await self.monte_carlo_simulation(portfolio_id, num_simulations=100)
                report.metrics["monte_carlo"] = mc
            except:
                pass
            
            # Correlation
            if len(portfolio.positions) > 1:
                symbols = list(portfolio.positions.keys())
                corr = await self.correlation_analysis(symbols, start_date, end_date)
                report.metrics["correlation"] = corr
            
            # Scenarios
            try:
                scenarios = await self.scenario_analysis(portfolio_id)
                report.metrics["scenarios"] = scenarios
            except:
                pass
        
        report.content = {
            "summary": f"Analysis of {portfolio.name} from {start_date} to {end_date}",
            "key_findings": self._extract_key_findings(report.metrics),
            "recommendations": self._generate_recommendations(report.metrics)
        }
        
        return report
    
    def _extract_key_findings(self, metrics: dict) -> list[str]:
        findings = []
        
        if "risk" in metrics:
            risk = metrics["risk"]
            if risk.get("var_95", 0) < -0.05:
                findings.append(f"High 95% VaR: {risk['var_95']:.2%}")
            if risk.get("max_drawdown", 0) > 0.2:
                findings.append(f"Significant max drawdown: {risk['max_drawdown']:.2%}")
            if risk.get("sharpe_ratio", 0) < 0.5:
                findings.append(f"Low Sharpe ratio: {risk['sharpe_ratio']:.2f}")
        
        if "performance" in metrics:
            perf = metrics["performance"]
            if perf.get("total_return", 0) < 0:
                findings.append(f"Negative total return: {perf['total_return']:.2%}")
            elif perf.get("total_return", 0) > 0.1:
                findings.append(f"Strong positive return: {perf['total_return']:.2%}")
        
        return findings
    
    def _generate_recommendations(self, metrics: dict) -> list[str]:
        recommendations = []
        
        if "risk" in metrics:
            risk = metrics["risk"]
            if risk.get("concentration", 0) > 0.3:
                recommendations.append("Consider diversifying - portfolio is highly concentrated")
            if risk.get("herfindahl_index", 0) > 0.25:
                recommendations.append("High Herfindahl index suggests concentration risk")
            if risk.get("max_position_weight", 0) > 0.2:
                recommendations.append("Largest position exceeds 20% - consider reducing")
        
        if "correlation" in metrics:
            corr = metrics["correlation"]
            if corr.get("high_correlation_pairs"):
                recommendations.append("Several highly correlated positions - consider diversification")
        
        return recommendations


# Factory
async def create_analytics_engine(
    portfolio_manager=None,
    market_data_provider=None,
    backend_type: str = "postgres",
    **kwargs
) -> AnalyticsEngine:
    """Factory function to create AnalyticsEngine."""
    engine = AnalyticsEngine(
        portfolio_manager=portfolio_manager,
        market_data_provider=market_data_provider
    )
    return engine


# Export
__all__ = [
    "AnalyticsBackend",
    "AnalyticsReport",
    "QuantAnalysis",
    "FactorAnalysis",
    "RiskMetrics",
    "AnalyticsEngine",
    "create_analytics_engine",
]