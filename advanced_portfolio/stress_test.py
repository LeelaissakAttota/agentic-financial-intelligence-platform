"""
Stress Test Engine
Comprehensive portfolio stress testing with historical, hypothetical, and regulatory scenarios.
"""

import asyncio
import logging
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

from .monte_carlo import MultiAssetMonteCarlo, get_monte_carlo, SimulationConfig, AssetConfig, SimulationResult

logger = logging.getLogger(__name__)


class StressType(str, Enum):
    """Types of stress tests."""
    HISTORICAL = "historical"           # Historical crisis scenarios
    HYPOTHETICAL = "hypothetical"       # Custom hypothetical scenarios
    REGULATORY = "regulatory"           # Regulatory requirements (CCAR, Basel, etc.)
    REVERSE = "reverse"                 # Reverse stress testing
    SENSITIVITY = "sensitivity"         # Single factor sensitivity
    SCENARIO_ANALYSIS = "scenario"      # Multi-factor scenario analysis


@dataclass
class StressFactor:
    """Individual stress factor."""
    name: str
    factor_type: str  # "equity", "rates", "credit", "fx", "commodity", "volatility"
    shock: float  # Magnitude of shock (e.g., -0.20 for 20% drop)
    duration_days: int = 1
    correlation_impact: Optional[Dict[str, float]] = None  # Impact on correlations
    description: str = ""


@dataclass
class StressScenario:
    """Complete stress scenario."""
    name: str
    stress_type: StressType
    factors: List[StressFactor]
    description: str = ""
    probability: Optional[float] = None
    historical_date: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StressResult:
    """Result of a stress test."""
    scenario_name: str
    portfolio_loss: float  # Total portfolio loss
    asset_losses: Dict[str, float]  # Per-asset losses
    var_breach: bool  # Whether VaR was breached
    max_drawdown: float
    recovery_time_days: Optional[int] = None
    tail_risk_metrics: Dict[str, float] = field(default_factory=dict)
    factor_contributions: Dict[str, float] = field(default_factory=dict)
    passed: bool = True  # Whether portfolio meets requirements
    metadata: Dict[str, Any] = field(default_factory=dict)


class StressTestEngine:
    """
    Comprehensive stress testing engine supporting:
    - Historical scenarios (2008, 2020, etc.)
    - Hypothetical scenarios
    - Regulatory scenarios (CCAR, Basel III, etc.)
    - Reverse stress testing
    - Sensitivity analysis
    - Multi-factor scenario analysis
    """
    
    def __init__(self):
        self.monte_carlo = get_monte_carlo()
        self._scenarios: Dict[str, StressScenario] = {}
        self._results: Dict[str, StressResult] = {}
        self._load_standard_scenarios()
    
    def _load_standard_scenarios(self) -> None:
        """Load standard regulatory and historical scenarios."""
        
        # 2008 Financial Crisis
        self.add_scenario(StressScenario(
            name="GFC_2008",
            stress_type=StressType.HISTORICAL,
            factors=[
                StressFactor("Equity_Crash", "equity", -0.50, 252, description="S&P 500 -50%"),
                StressFactor("Credit_Spread_Widening", "credit", 0.05, 252, description="Spreads +500bps"),
                StressFactor("Rate_Cut", "rates", -0.03, 252, description="Fed cuts 300bps"),
                StressFactor("Vol_Spike", "volatility", 0.60, 60, description="VIX +60 points"),
            ],
            description="Global Financial Crisis 2008-2009",
            historical_date=datetime(2008, 9, 15),
            probability=0.01
        ))
        
        # COVID-19 Crash 2020
        self.add_scenario(StressScenario(
            name="COVID_2020",
            stress_type=StressType.HISTORICAL,
            factors=[
                StressFactor("Equity_Crash", "equity", -0.35, 30, description="S&P 500 -35% in month"),
                StressFactor("Rate_Cut", "rates", -0.015, 30, description="Emergency rate cuts"),
                StressFactor("Vol_Spike", "volatility", 0.45, 30, description="VIX spike to 80"),
                StressFactor("Credit_Spread", "credit", 0.02, 60, description="Investment grade spreads +200bps"),
            ],
            description="COVID-19 Market Crash March 2020",
            historical_date=datetime(2020, 3, 23),
            probability=0.02
        ))
        
        # Dot-com Bubble
        self.add_scenario(StressScenario(
            name="DOTCOM_2000",
            stress_type=StressType.HISTORICAL,
            factors=[
                StressFactor("Tech_Crash", "equity", -0.50, 500, description="NASDAQ -78% peak to trough"),
                StressFactor("Rate_Hike", "rates", 0.015, 200, description="Fed tightening cycle"),
                StressFactor("Valuation_Compression", "equity", -0.30, 252, description="P/E multiple compression"),
            ],
            description="Dot-com Bubble Burst 2000-2002",
            historical_date=datetime(2000, 3, 10),
            probability=0.015
        ))
        
        # 1987 Black Monday
        self.add_scenario(StressScenario(
            name="BLACK_MONDAY_1987",
            stress_type=StressType.HISTORICAL,
            factors=[
                StressFactor("Single_Day_Crash", "equity", -0.22, 1, description="DJIA -22.6% in one day"),
                StressFactor("Vol_Spike", "volatility", 1.0, 10, description="Implied vol explosion"),
                StressFactor("Liquidity_Crisis", "credit", 0.03, 30, description="Market maker failure"),
            ],
            description="Black Monday 1987",
            historical_date=datetime(1987, 10, 19),
            probability=0.005
        ))
        
        # CCAR Severely Adverse (2023-style)
        self.add_scenario(StressScenario(
            name="CCAR_SEVERELY_ADVERSE_2023",
            stress_type=StressType.REGULATORY,
            factors=[
                StressFactor("Unemployment", "macro", 0.10, 252, description="Unemployment 10%"),
                StressFactor("GDP_Decline", "macro", -0.04, 252, description="Real GDP -4%"),
                StressFactor("Equity_Decline", "equity", -0.55, 252, description="S&P 500 -55%"),
                StressFactor("Rate_Rise", "rates", 0.025, 252, description="Long-term rates +250bps"),
                StressFactor("Spread_Widening", "credit", 0.04, 252, description="BBB spreads +400bps"),
                StressFactor("HPI_Decline", "real_estate", -0.25, 252, description="Home prices -25%"),
                StressFactor("FX_Shock", "fx", 0.20, 252, description="USD +20% trade-weighted"),
            ],
            description="Federal Reserve CCAR 2023 Severely Adverse Scenario",
            probability=0.01
        ))
        
        # Basel III Interest Rate Shock
        self.add_scenario(StressScenario(
            name="BASEL_IR_SHOCK",
            stress_type=StressType.REGULATORY,
            factors=[
                StressFactor("Parallel_Up_200bp", "rates", 0.02, 1, description="Parallel +200bps"),
                StressFactor("Parallel_Down_200bp", "rates", -0.02, 1, description="Parallel -200bps"),
                StressFactor("Steepener", "rates", 0.01, 1, description="Curve steepening +100bps"),
                StressFactor("Flattener", "rates", -0.01, 1, description="Curve flattening -100bps"),
                StressFactor("Short_Rate_Up", "rates", 0.03, 1, description="Short rates +300bps"),
                StressFactor("Long_Rate_Down", "rates", -0.01, 1, description="Long rates -100bps"),
            ],
            description="Basel III Interest Rate Risk in the Banking Book (IRRBB)",
            probability=0.05
        ))
        
        # Stagflation Scenario
        self.add_scenario(StressScenario(
            name="STAGFLATION_1970S",
            stress_type=StressType.HYPOTHETICAL,
            factors=[
                StressFactor("High_Inflation", "macro", 0.10, 252, description="CPI +10%"),
                StressFactor("Rate_Hikes", "rates", 0.04, 252, description="Fed funds +400bps"),
                StressFactor("Equity_Decline", "equity", -0.30, 252, description="Real returns negative"),
                StressFactor("Commodity_Spike", "commodity", 0.50, 120, description="Oil/commodities +50%"),
                StressFactor("FX_Debasement", "fx", -0.15, 252, description="Currency -15%"),
            ],
            description="1970s-style Stagflation",
            probability=0.02
        ))
        
        # Tech Bubble Burst (Modern)
        self.add_scenario(StressScenario(
            name="TECH_BUBBLE_2020S",
            stress_type=StressType.HYPOTHETICAL,
            factors=[
                StressFactor("Mega_Cap_Crash", "equity", -0.40, 120, description="FAANG/Magnificent 7 -40%"),
                StressFactor("Valuation_Reset", "equity", -0.50, 252, description="P/E compression 50%"),
                StressFactor("Rate_Normalization", "rates", 0.02, 252, description="Rates normalize from zero"),
                StressFactor("Regulatory_Crackdown", "macro", -0.10, 252, description="Antitrust/regulation impact"),
            ],
            description="Modern Tech Valuation Bubble Burst",
            probability=0.03
        ))
        
        # Geopolitical Crisis
        self.add_scenario(StressScenario(
            name="GEOPOLITICAL_CRISIS",
            stress_type=StressType.HYPOTHETICAL,
            factors=[
                StressFactor("Oil_Shock", "commodity", 1.0, 30, description="Oil price doubles"),
                StressFactor("Equity_Selloff", "equity", -0.25, 60, description="Risk-off -25%"),
                StressFactor("Flight_to_Quality", "credit", 0.03, 30, description="Spreads +300bps"),
                StressFactor("Safe_Haven_Flows", "fx", 0.10, 30, description="USD/CHF/JPY +10%"),
                StressFactor("Supply_Chain", "macro", -0.05, 180, description="Global trade disruption -5%"),
            ],
            description="Major Geopolitical Conflict (e.g., Taiwan Strait)",
            probability=0.01
        ))
    
    def add_scenario(self, scenario: StressScenario) -> None:
        """Add a stress scenario."""
        self._scenarios[scenario.name] = scenario
    
    def get_scenario(self, name: str) -> Optional[StressScenario]:
        """Get a scenario by name."""
        return self._scenarios.get(name)
    
    def list_scenarios(self, stress_type: Optional[StressType] = None) -> List[StressScenario]:
        """List all scenarios, optionally filtered by type."""
        scenarios = list(self._scenarios.values())
        if stress_type:
            scenarios = [s for s in scenarios if s.stress_type == stress_type]
        return scenarios
    
    async def run_stress_test(
        self,
        scenario_name: str,
        portfolio_assets: List[AssetConfig],
        base_config: Optional[SimulationConfig] = None
    ) -> StressResult:
        """Run a single stress test scenario."""
        scenario = self._scenarios.get(scenario_name)
        if not scenario:
            raise ValueError(f"Scenario {scenario_name} not found")
        
        logger.info(f"Running stress test: {scenario_name}")
        
        # Apply scenario shocks to portfolio
        shocked_assets = self._apply_shocks(portfolio_assets, scenario.factors)
        
        # Run Monte Carlo with shocked parameters
        config = base_config or SimulationConfig()
        self.monte_carlo = get_monte_carlo(config)
        
        for asset in shocked_assets:
            self.monte_carlo.add_asset(asset)
        
        result = await self.monte_carlo.run_simulation(config)
        
        # Calculate stress metrics
        portfolio_loss = 1 - result.final_values.mean()
        asset_losses = {}
        for symbol, paths in result.asset_paths.items():
            asset_losses[symbol] = 1 - paths[:, -1].mean()
        
        # Factor contribution analysis
        factor_contributions = self._analyze_factor_contributions(scenario.factors, asset_losses)
        
        # Check if VaR breached (99% VaR)
        var_99 = result.var.get(0.99, 0)
        var_breach = portfolio_loss > abs(var_99)
        
        # Recovery time estimate (simplified)
        recovery_time = self._estimate_recovery_time(portfolio_loss, scenario)
        
        stress_result = StressResult(
            scenario_name=scenario.name,
            portfolio_loss=portfolio_loss,
            asset_losses=asset_losses,
            var_breach=var_breach,
            max_drawdown=float(np.mean(result.max_drawdown_paths)),
            recovery_time_days=recovery_time,
            tail_risk_metrics={
                "var_95": result.var.get(0.95, 0),
                "var_99": result.var.get(0.99, 0),
                "cvar_95": result.cvar.get(0.95, 0),
                "cvar_99": result.cvar.get(0.99, 0),
                "prob_loss": result.probability_of_loss,
                "skewness": result.skewness,
                "kurtosis": result.kurtosis
            },
            factor_contributions=factor_contributions,
            passed=not var_breach,
            metadata={
                "scenario_type": scenario.stress_type.value,
                "num_factors": len(scenario.factors),
                "historical_date": scenario.historical_date.isoformat() if scenario.historical_date else None
            }
        )
        
        self._results[scenario_name] = stress_result
        logger.info(f"Stress test completed: {scenario_name}, Portfolio loss: {portfolio_loss:.2%}")
        
        return stress_result
    
    def _apply_shocks(
        self,
        assets: List[AssetConfig],
        factors: List[StressFactor]
    ) -> List[AssetConfig]:
        """Apply stress factor shocks to asset parameters."""
        shocked = []
        
        for asset in assets:
            new_asset = AssetConfig(
                symbol=asset.symbol,
                weight=asset.weight,
                expected_return=asset.expected_return,
                volatility=asset.volatility,
                skew=asset.skew,
                kurtosis=asset.kurtosis,
                distribution=asset.distribution,
                regime_params=asset.regime_params
            )
            
            for factor in factors:
                if factor.factor_type == "equity":
                    # Equity shock affects expected return and volatility
                    new_asset.expected_return += factor.shock
                    new_asset.volatility *= (1 + abs(factor.shock) * 0.5)
                    new_asset.skew -= 0.5 * abs(factor.shock)
                    new_asset.kurtosis += 2 * abs(factor.shock)
                
                elif factor.factor_type == "rates":
                    # Rate shock affects fixed income primarily
                    # For equities, discount rate increase lowers valuations
                    new_asset.expected_return -= factor.shock * 0.5
                
                elif factor.factor_type == "credit":
                    # Credit spread widening
                    new_asset.expected_return -= factor.shock * 0.3
                    new_asset.volatility *= (1 + factor.shock)
                
                elif factor.factor_type == "volatility":
                    new_asset.volatility *= (1 + factor.shock)
                    new_asset.kurtosis += factor.shock * 3
                
                elif factor.factor_type == "fx":
                    # FX impact on foreign assets
                    if not asset.symbol.endswith(".US"):
                        new_asset.expected_return += factor.shock * 0.5
                
                elif factor.factor_type == "commodity":
                    # Commodity shock - affects commodity producers
                    if "COM" in asset.symbol or "OIL" in asset.symbol or "GOLD" in asset.symbol:
                        new_asset.expected_return += factor.shock * 0.7
                
                elif factor.factor_type == "macro":
                    # Macro shock (GDP, inflation, unemployment)
                    new_asset.expected_return += factor.shock * 0.3
                    new_asset.volatility *= (1 + abs(factor.shock) * 0.2)
            
            shocked.append(new_asset)
        
        return shocked
    
    def _analyze_factor_contributions(
        self,
        factors: List[StressFactor],
        asset_losses: Dict[str, float]
    ) -> Dict[str, float]:
        """Analyze contribution of each stress factor to total loss."""
        # Simplified: allocate loss proportionally to factor shocks
        total_shock = sum(abs(f.shock) for f in factors)
        if total_shock == 0:
            return {f.name: 0.0 for f in factors}
        
        portfolio_loss = sum(asset_losses.values()) / len(asset_losses) if asset_losses else 0
        
        contributions = {}
        for factor in factors:
            contributions[factor.name] = portfolio_loss * (abs(factor.shock) / total_shock)
        
        return contributions
    
    def _estimate_recovery_time(
        self,
        portfolio_loss: float,
        scenario: StressScenario
    ) -> Optional[int]:
        """Estimate recovery time in days."""
        if portfolio_loss <= 0:
            return 0
        
        # Historical recovery patterns
        recovery_map = {
            "GFC_2008": 1000,      # ~4 years
            "COVID_2020": 150,     # ~5 months
            "DOTCOM_2000": 1500,   # ~6 years
            "BLACK_MONDAY_1987": 600,
            "CCAR_SEVERELY_ADVERSE_2023": 800,
            "BASEL_IR_SHOCK": 200,
            "STAGFLATION_1970S": 1200,
            "TECH_BUBBLE_2020S": 600,
            "GEOPOLITICAL_CRISIS": 300
        }
        
        return recovery_map.get(scenario.name, int(portfolio_loss * 1000))
    
    async def run_all_scenarios(
        self,
        portfolio_assets: List[AssetConfig],
        scenario_names: Optional[List[str]] = None,
        base_config: Optional[SimulationConfig] = None
    ) -> Dict[str, StressResult]:
        """Run multiple stress scenarios."""
        names = scenario_names or list(self._scenarios.keys())
        results = {}
        
        for name in names:
            try:
                results[name] = await self.run_stress_test(name, portfolio_assets, base_config)
            except Exception as e:
                logger.error(f"Failed to run scenario {name}: {e}")
                results[name] = StressResult(
                    scenario_name=name,
                    portfolio_loss=0,
                    asset_losses={},
                    var_breach=False,
                    max_drawdown=0,
                    passed=False,
                    metadata={"error": str(e)}
                )
        
        return results
    
    async def run_reverse_stress_test(
        self,
        portfolio_assets: List[AssetConfig],
        target_loss: float,
        max_iterations: int = 20
    ) -> StressResult:
        """Reverse stress test: find scenario that causes target loss."""
        logger.info(f"Running reverse stress test for target loss: {target_loss:.2%}")
        
        # Binary search on scenario severity
        low_shock = 0.1
        high_shock = 1.0
        best_scenario = None
        
        for iteration in range(max_iterations):
            mid_shock = (low_shock + high_shock) / 2
            
            # Create test scenario
            test_factors = [
                StressFactor("Equity_Crash", "equity", -mid_shock, 252),
                StressFactor("Vol_Spike", "volatility", mid_shock * 2, 60),
                StressFactor("Credit_Spread", "credit", mid_shock * 0.5, 120),
            ]
            
            test_scenario = StressScenario(
                name=f"Reverse_Test_{mid_shock:.2f}",
                stress_type=StressType.REVERSE,
                factors=test_factors
            )
            
            self._scenarios[test_scenario.name] = test_scenario
            result = await self.run_stress_test(test_scenario.name, portfolio_assets)
            
            if result.portfolio_loss >= target_loss:
                high_shock = mid_shock
                best_scenario = result
            else:
                low_shock = mid_shock
            
            if abs(result.portfolio_loss - target_loss) / target_loss < 0.05:
                break
        
        return best_scenario or StressResult(
            scenario_name="Reverse_Stress_Failed",
            portfolio_loss=0,
            asset_losses={},
            var_breach=False,
            max_drawdown=0,
            passed=False
        )
    
    async def run_sensitivity_analysis(
        self,
        portfolio_assets: List[AssetConfig],
        factor_name: str,
        shock_range: Tuple[float, float],
        steps: int = 10
    ) -> List[StressResult]:
        """Run sensitivity analysis on a single factor."""
        min_shock, max_shock = shock_range
        shocks = np.linspace(min_shock, max_shock, steps)
        results = []
        
        for shock in shocks:
            factors = [StressFactor(factor_name, factor_name, shock, 252)]
            scenario = StressScenario(
                name=f"Sensitivity_{factor_name}_{shock:.2f}",
                stress_type=StressType.SENSITIVITY,
                factors=factors
            )
            self._scenarios[scenario.name] = scenario
            result = await self.run_stress_test(scenario.name, portfolio_assets)
            results.append(result)
        
        return results
    
    def get_results_summary(self) -> Dict[str, Any]:
        """Get summary of all stress test results."""
        if not self._results:
            return {"message": "No stress tests run yet"}
        
        return {
            "scenarios_run": len(self._results),
            "worst_case": max(self._results.values(), key=lambda r: r.portfolio_loss).scenario_name,
            "best_case": min(self._results.values(), key=lambda r: r.portfolio_loss).scenario_name,
            "avg_loss": np.mean([r.portfolio_loss for r in self._results.values()]),
            "var_breaches": sum(1 for r in self._results.values() if r.var_breach),
            "passed": sum(1 for r in self._results.values() if r.passed),
            "failed": sum(1 for r in self._results.values() if not r.passed),
            "by_type": {
                st.value: sum(1 for r in self._results.values() 
                             if self._scenarios.get(r.scenario_name, None) 
                             and self._scenarios[r.scenario_name].stress_type == st)
                for st in StressType
            }
        }
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "available_scenarios": len(self._scenarios),
            "scenarios_by_type": {
                st.value: len([s for s in self._scenarios.values() if s.stress_type == st])
                for st in StressType
            },
            "results_count": len(self._results)
        }


# Global stress test engine instance
_stress_test_engine: Optional[StressTestEngine] = None


def get_stress_test_engine() -> StressTestEngine:
    global _stress_test_engine
    if _stress_test_engine is None:
        _stress_test_engine = StressTestEngine()
    return _stress_test_engine


async def close_stress_test_engine() -> None:
    global _stress_test_engine
    if _stress_test_engine:
        _stress_test_engine = None