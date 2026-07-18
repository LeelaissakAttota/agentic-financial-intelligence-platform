"""
Predictive Intelligence Module
Provides forecast engine, early warning signals, event prediction, risk prediction, and market regime detection.
"""

from .forecast_engine import ForecastEngine, get_forecast_engine
from .early_warning import EarlyWarningSystem, get_early_warning_system
from .event_prediction import EventPrediction, get_event_prediction
from .risk_prediction import RiskPrediction, get_risk_prediction
from .regime_detection import RegimeDetection, get_regime_detection

__all__ = [
    "ForecastEngine",
    "get_forecast_engine",
    "EarlyWarningSystem",
    "get_early_warning_system",
    "EventPrediction",
    "get_event_prediction",
    "RiskPrediction",
    "get_risk_prediction",
    "RegimeDetection",
    "get_regime_detection",
]

__version__ = "1.0.0-phase9"