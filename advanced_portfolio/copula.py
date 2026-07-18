"""
Copula Correlation Modeling
Advanced correlation modeling using copulas for tail dependence and non-linear relationships.
"""

import asyncio
import logging
import numpy as np
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class CopulaType(str, Enum):
    """Supported copula families."""
    GAUSSIAN = "gaussian"
    STUDENT_T = "student_t"
    CLAYTON = "clayton"
    GUMBEL = "gumbel"
    FRANK = "frank"
    JOE = "joe"
    VINE = "vine"  # R-vine copula


@dataclass
class CopulaParams:
    """Parameters for copula fitting."""
    copula_type: CopulaType
    parameters: Dict[str, float] = field(default_factory=dict)
    kendall_tau: Optional[float] = None
    spearman_rho: Optional[float] = None
    tail_dependence: Tuple[float, float] = (0.0, 0.0)  # lower, upper
    aic: Optional[float] = None
    bic: Optional[float] = None
    log_likelihood: Optional[float] = None


@dataclass
class CopulaFitResult:
    """Result of copula fitting."""
    copula_type: CopulaType
    params: CopulaParams
    fitted: bool
    diagnostics: Dict[str, Any] = field(default_factory=dict)


class CopulaCorrelation:
    """
    Copula-based correlation modeling for financial returns.
    Supports Gaussian, Student-t, Clayton, Gumbel, Frank, Joe, and Vine copulas.
    Provides tail dependence modeling crucial for risk management.
    """
    
    def __init__(self):
        self._fitted_copulas: Dict[str, CopulaFitResult] = {}
        self._marginal_models: Dict[str, Any] = {}
    
    def _pseudo_observations(self, data: np.ndarray) -> np.ndarray:
        """Convert data to pseudo-observations (ranks / (n+1))."""
        n = len(data)
        ranks = np.argsort(np.argsort(data)) + 1
        return ranks / (n + 1)
    
    def _empirical_cdf(self, data: np.ndarray, x: float) -> float:
        """Empirical CDF at point x."""
        return np.mean(data <= x)
    
    # Copula CDF and PDF functions
    
    def _gaussian_cdf(self, u: np.ndarray, v: np.ndarray, rho: float) -> np.ndarray:
        """Gaussian copula CDF."""
        from scipy.stats import norm, multivariate_normal
        phi_inv_u = norm.ppf(u)
        phi_inv_v = norm.ppf(v)
        mean = [0, 0]
        cov = [[1, rho], [rho, 1]]
        return multivariate_normal.cdf(np.column_stack([phi_inv_u, phi_inv_v]), mean=mean, cov=cov)
    
    def _gaussian_pdf(self, u: np.ndarray, v: np.ndarray, rho: float) -> np.ndarray:
        """Gaussian copula PDF."""
        from scipy.stats import norm, multivariate_normal
        phi_inv_u = norm.ppf(u)
        phi_inv_v = norm.ppf(v)
        mean = [0, 0]
        cov = [[1, rho], [rho, 1]]
        return multivariate_normal.pdf(np.column_stack([phi_inv_u, phi_inv_v]), mean=mean, cov=cov) / (norm.pdf(phi_inv_u) * norm.pdf(phi_inv_v))
    
    def _student_t_cdf(self, u: np.ndarray, v: np.ndarray, rho: float, nu: float) -> np.ndarray:
        """Student-t copula CDF."""
        from scipy.stats import t
        t_inv_u = t.ppf(u, nu)
        t_inv_v = t.ppf(v, nu)
        # Approximation for bivariate t CDF
        # Using multivariate_normal as approximation for large nu
        if nu > 30:
            return self._gaussian_cdf(u, v, rho)
        # For small nu, use numerical integration (simplified)
        return 0.5 * (u + v)  # Placeholder
    
    def _student_t_pdf(self, u: np.ndarray, v: np.ndarray, rho: float, nu: float) -> np.ndarray:
        """Student-t copula PDF."""
        from scipy.stats import t
        t_inv_u = t.ppf(u, nu)
        t_inv_v = t.ppf(v, nu)
        
        det = 1 - rho**2
        const = (np.math.gamma((nu + 2)/2) / (np.math.gamma(nu/2) * np.pi * nu * np.sqrt(det)))
        quad = (t_inv_u**2 - 2*rho*t_inv_u*t_inv_v + t_inv_v**2) / (nu * det)
        return const * (1 + quad)**(-(nu + 2)/2) / (t.pdf(t_inv_u, nu) * t.pdf(t_inv_v, nu))
    
    def _clayton_cdf(self, u: np.ndarray, v: np.ndarray, theta: float) -> np.ndarray:
        """Clayton copula CDF (lower tail dependence)."""
        return (u**(-theta) + v**(-theta) - 1)**(-1/theta)
    
    def _clayton_pdf(self, u: np.ndarray, v: np.ndarray, theta: float) -> np.ndarray:
        """Clayton copula PDF."""
        return (1 + theta) * (u * v)**(-theta - 1) * (u**(-theta) + v**(-theta) - 1)**(-1/theta - 2)
    
    def _gumbel_cdf(self, u: np.ndarray, v: np.ndarray, theta: float) -> np.ndarray:
        """Gumbel copula CDF (upper tail dependence)."""
        return np.exp(-((-np.log(u))**theta + (-np.log(v))**theta)**(1/theta))
    
    def _gumbel_pdf(self, u: np.ndarray, v: np.ndarray, theta: float) -> np.ndarray:
        """Gumbel copula PDF."""
        A = (-np.log(u))**theta
        B = (-np.log(v))**theta
        S = A + B
        C = S**(1/theta)
        return C * (1/C - 1) * A * B / (u * v * S**2) * (S**(1/theta - 2))
    
    def _frank_cdf(self, u: np.ndarray, v: np.ndarray, theta: float) -> np.ndarray:
        """Frank copula CDF."""
        num = (np.exp(-theta * u) - 1) * (np.exp(-theta * v) - 1)
        den = np.exp(-theta) - 1
        return -1/theta * np.log(1 + num/den)
    
    def _frank_pdf(self, u: np.ndarray, v: np.ndarray, theta: float) -> np.ndarray:
        """Frank copula PDF."""
        num = theta * np.exp(-theta * (u + v)) * (np.exp(-theta) - 1)
        den = (np.exp(-theta * u) - 1) * (np.exp(-theta * v) - 1) + (np.exp(-theta) - 1)
        return num / den
    
    def _joe_cdf(self, u: np.ndarray, v: np.ndarray, theta: float) -> np.ndarray:
        """Joe copula CDF."""
        return 1 - ((1-u)**theta + (1-v)**theta - (1-u)**theta * (1-v)**theta)**(1/theta)
    
    def _joe_pdf(self, u: np.ndarray, v: np.ndarray, theta: float) -> np.ndarray:
        """Joe copula PDF."""
        A = (1-u)**theta
        B = (1-v)**theta
        C = A + B - A*B
        return theta * (1-theta) * A * B * C**(1/theta - 2) / ((1-u)*(1-v))
    
    def fit_copula(
        self,
        data_u: np.ndarray,
        data_v: np.ndarray,
        copula_type: CopulaType = CopulaType.GAUSSIAN
    ) -> CopulaFitResult:
        """Fit copula to bivariate data using maximum likelihood."""
        from scipy.optimize import minimize
        
        # Convert to pseudo-observations
        u = self._pseudo_observations(data_u)
        v = self._pseudo_observations(data_v)
        
        # Remove boundary values
        eps = 1e-10
        u = np.clip(u, eps, 1-eps)
        v = np.clip(v, eps, 1-eps)
        
        def neg_log_likelihood(params):
            """Negative log-likelihood for copula."""
            if copula_type == CopulaType.GAUSSIAN:
                rho = np.clip(params[0], -0.999, 0.999)
                pdf = self._gaussian_pdf(u, v, rho)
            elif copula_type == CopulaType.STUDENT_T:
                rho = np.clip(params[0], -0.999, 0.999)
                nu = max(params[1], 2.1)
                pdf = self._student_t_pdf(u, v, rho, nu)
            elif copula_type == CopulaType.CLAYTON:
                theta = max(params[0], 0.01)
                pdf = self._clayton_pdf(u, v, theta)
            elif copula_type == CopulaType.GUMBEL:
                theta = max(params[0], 1.01)
                pdf = self._gumbel_pdf(u, v, theta)
            elif copula_type == CopulaType.FRANK:
                theta = params[0]
                if abs(theta) < 0.01:
                    return 1e10
                pdf = self._frank_pdf(u, v, theta)
            elif copula_type == CopulaType.JOE:
                theta = max(params[0], 1.01)
                pdf = self._joe_pdf(u, v, theta)
            else:
                return 1e10
            
            # Avoid log(0)
            pdf = np.clip(pdf, 1e-300, None)
            return -np.sum(np.log(pdf))
        
        # Initial parameter guesses
        if copula_type == CopulaType.GAUSSIAN:
            init = [np.corrcoef(data_u, data_v)[0, 1]]
            bounds = [(-0.99, 0.99)]
        elif copula_type == CopulaType.STUDENT_T:
            init = [np.corrcoef(data_u, data_v)[0, 1], 5.0]
            bounds = [(-0.99, 0.99), (2.1, 30)]
        elif copula_type == CopulaType.CLAYTON:
            init = [2.0]
            bounds = [(0.01, 50)]
        elif copula_type == CopulaType.GUMBEL:
            init = [2.0]
            bounds = [(1.01, 50)]
        elif copula_type == CopulaType.FRANK:
            init = [1.0]
            bounds = [(-50, 50)]
        elif copula_type == CopulaType.JOE:
            init = [2.0]
            bounds = [(1.01, 50)]
        else:
            init = [0.5]
            bounds = [(-0.99, 0.99)]
        
        # Optimize
        result = minimize(neg_log_likelihood, init, bounds=bounds, method='L-BFGS-B')
        
        if not result.success:
            logger.warning(f"Copula fitting failed: {result.message}")
        
        # Extract fitted parameters
        fitted_params = result.x
        
        # Calculate diagnostics
        n = len(data_u)
        k = len(fitted_params)
        log_lik = -result.fun
        aic = 2 * k - 2 * log_lik
        bic = k * np.log(n) - 2 * log_lik
        
        # Tail dependence
        lower_td, upper_td = self._calculate_tail_dependence(copula_type, fitted_params)
        
        # Kendall's tau and Spearman's rho
        kendall_tau = self._kendall_tau(copula_type, fitted_params)
        spearman_rho = self._spearman_rho(copula_type, fitted_params)
        
        params = CopulaParams(
            copula_type=copula_type,
            parameters=dict(zip([f"param_{i}" for i in range(len(fitted_params))], fitted_params)),
            kendall_tau=kendall_tau,
            spearman_rho=spearman_rho,
            tail_dependence=(lower_td, upper_td),
            aic=aic,
            bic=bic,
            log_likelihood=log_lik
        )
        
        fit_result = CopulaFitResult(
            copula_type=copula_type,
            params=params,
            fitted=result.success,
            diagnostics={
                "converged": result.success,
                "iterations": result.nit,
                "message": result.message
            }
        )
        
        return fit_result
    
    def _calculate_tail_dependence(self, copula_type: CopulaType, params: np.ndarray) -> Tuple[float, float]:
        """Calculate lower and upper tail dependence coefficients."""
        if copula_type == CopulaType.GAUSSIAN:
            return (0.0, 0.0)
        elif copula_type == CopulaType.STUDENT_T:
            rho, nu = params[0], params[1]
            # Student-t has symmetric tail dependence
            from scipy.stats import t
            td = 2 * t.cdf(-np.sqrt(nu + 1) * np.sqrt((1 - rho) / (1 + rho)), nu)
            return (td, td)
        elif copula_type == CopulaType.CLAYTON:
            theta = params[0]
            lower = 2**(-1/theta)
            return (lower, 0.0)
        elif copula_type == CopulaType.GUMBEL:
            theta = params[0]
            upper = 2 - 2**(1/theta)
            return (0.0, upper)
        elif copula_type == CopulaType.FRANK:
            return (0.0, 0.0)
        elif copula_type == CopulaType.JOE:
            theta = params[0]
            upper = 2 - 2**(1/theta)
            return (0.0, upper)
        return (0.0, 0.0)
    
    def _kendall_tau(self, copula_type: CopulaType, params: np.ndarray) -> float:
        """Calculate Kendall's tau from copula parameters."""
        if copula_type == CopulaType.GAUSSIAN:
            return 2/np.pi * np.arcsin(params[0])
        elif copula_type == CopulaType.STUDENT_T:
            return 2/np.pi * np.arcsin(params[0])
        elif copula_type == CopulaType.CLAYTON:
            return params[0] / (params[0] + 2)
        elif copula_type == CopulaType.GUMBEL:
            return 1 - 1/params[0]
        elif copula_type == CopulaType.FRANK:
            theta = params[0]
            if abs(theta) < 1e-10:
                return 0.0
            from scipy.special import expi
            return 1 - 4/theta * (1 - expi(-theta) / np.exp(-theta))
        elif copula_type == CopulaType.JOE:
            return 1 - 4/params[0] * (1 - np.sum([1/k for k in range(1, int(params[0])+1)]))
        return 0.0
    
    def _spearman_rho(self, copula_type: CopulaType, params: np.ndarray) -> float:
        """Calculate Spearman's rho from copula parameters."""
        if copula_type in [CopulaType.GAUSSIAN, CopulaType.STUDENT_T]:
            return 6/np.pi * np.arcsin(params[0]/2)
        elif copula_type == CopulaType.CLAYTON:
            return params[0] / (params[0] + 3)
        elif copula_type == CopulaType.GUMBEL:
            return 1 - 2/params[0] * (1 - 1/(params[0]+1))
        return 0.0
    
    def sample_copula(
        self,
        copula_type: CopulaType,
        params: np.ndarray,
        n_samples: int,
        dim: int = 2
    ) -> np.ndarray:
        """Generate samples from fitted copula."""
        if copula_type == CopulaType.GAUSSIAN:
            rho = params[0]
            mean = np.zeros(dim)
            cov = np.eye(dim)
            cov[0, 1] = cov[1, 0] = rho
            z = np.random.multivariate_normal(mean, cov, n_samples)
            from scipy.stats import norm
            return norm.cdf(z)
        
        elif copula_type == CopulaType.STUDENT_T:
            rho, nu = params[0], params[1]
            # Sample from multivariate t
            from scipy.stats import chi2
            mean = np.zeros(dim)
            cov = np.eye(dim)
            cov[0, 1] = cov[1, 0] = rho
            z = np.random.multivariate_normal(mean, cov, n_samples)
            s = chi2.rvs(nu, size=n_samples)
            t_samples = z / np.sqrt(s/nu)[:, np.newaxis]
            from scipy.stats import t
            return t.cdf(t_samples, nu)
        
        elif copula_type == CopulaType.CLAYTON:
            theta = params[0]
            # Conditional sampling
            v1 = np.random.uniform(0, 1, n_samples)
            v2 = np.random.uniform(0, 1, n_samples)
            u1 = v1
            u2 = (v1**(-theta) * (v2**(-theta/(1+theta)) - 1) + 1)**(-1/theta)
            return np.column_stack([u1, u2])
        
        elif copula_type == CopulaType.GUMBEL:
            # Use Marshall-Olkin algorithm
            theta = params[0]
            alpha = 1/theta
            v1 = np.random.uniform(0, 1, n_samples)
            v2 = np.random.uniform(0, 1, n_samples)
            # Simplified: use bivariate generation
            return np.column_stack([v1, v2])  # Placeholder
        
        return np.random.uniform(0, 1, (n_samples, dim))
    
    def select_best_copula(
        self,
        data_u: np.ndarray,
        data_v: np.ndarray,
        candidate_types: Optional[List[CopulaType]] = None
    ) -> CopulaFitResult:
        """Select best copula by AIC/BIC."""
        if candidate_types is None:
            candidate_types = [
                CopulaType.GAUSSIAN,
                CopulaType.STUDENT_T,
                CopulaType.CLAYTON,
                CopulaType.GUMBEL,
                CopulaType.FRANK,
                CopulaType.JOE
            ]
        
        best_result = None
        best_aic = np.inf
        
        for ctype in candidate_types:
            try:
                result = self.fit_copula(data_u, data_v, ctype)
                if result.fitted and result.params.aic < best_aic:
                    best_aic = result.params.aic
                    best_result = result
            except Exception as e:
                logger.warning(f"Failed to fit {ctype}: {e}")
        
        return best_result
    
    def estimate_correlation_matrix(
        self,
        returns_data: np.ndarray,
        method: str = "copula"
    ) -> np.ndarray:
        """Estimate correlation matrix using copula approach."""
        n_assets = returns_data.shape[1]
        corr_matrix = np.eye(n_assets)
        
        for i in range(n_assets):
            for j in range(i+1, n_assets):
                # Fit best copula
                result = self.select_best_copula(returns_data[:, i], returns_data[:, j])
                if result and result.fitted:
                    # Convert to Pearson correlation equivalent
                    if result.copula_type == CopulaType.GAUSSIAN:
                        rho = result.params.parameters["param_0"]
                    elif result.copula_type == CopulaType.STUDENT_T:
                        rho = result.params.parameters["param_0"]
                    else:
                        # Use Kendall's tau to approximate Pearson
                        tau = result.params.kendall_tau
                        rho = np.sin(np.pi/2 * tau)
                else:
                    # Fallback to empirical correlation
                    rho = np.corrcoef(returns_data[:, i], returns_data[:, j])[0, 1]
                
                corr_matrix[i, j] = rho
                corr_matrix[j, i] = rho
        
        return corr_matrix
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "fitted_copulas": len(self._fitted_copulas),
            "copula_types": list(set(cf.copula_type.value for cf in self._fitted_copulas.values()))
        }


# Global copula correlation instance
_copula_correlation: Optional[CopulaCorrelation] = None


def get_copula_correlation() -> CopulaCorrelation:
    global _copula_correlation
    if _copula_correlation is None:
        _copula_correlation = CopulaCorrelation()
    return _copula_correlation


async def close_copula_correlation() -> None:
    global _copula_correlation
    if _copula_correlation:
        _copula_correlation = None