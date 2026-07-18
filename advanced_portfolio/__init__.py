"""
Advanced Portfolio Intelligence Module
Provides multi-asset Monte Carlo, copula correlation, stress testing,
scenario simulation, and risk decomposition.
"""

from .monte_carlo import MultiAssetMonteCarlo, get_monte_carlo
from .copula import CopulaCorrelation, get_copula_correlation
from .stress_test import StressTestEngine, get_stress_test_engine
from .scenario import ScenarioSimulator, get_scenario_simulator
from .risk_decomposition import RiskDecomposition, get_risk_decomposition

__all__ = [
    "MultiAssetMonteCarlo",
    "get_monte_carlo",
    "CopulaCorrelation",
    "get_copula_correlation",
    "StressTestEngine",
    "get_stress_test_engine",
    "ScenarioSimulator",
    "get_scenario_simulator",
    "RiskDecomposition",
    "get_risk_decomposition",
]

__version__ = "1.0.0-phase9"