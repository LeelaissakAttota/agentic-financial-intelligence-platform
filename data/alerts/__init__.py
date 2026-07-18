"""
Alerts Module - Phase 5: Knowledge Persistence & Advanced Analytics

Real-time alerting system for portfolio events, price movements, news, and pattern triggers.
"""

from data.alerts.alerts import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    AlertChannel,
    AlertCondition,
    AlertRule,
    Alert,
    AlertBackend,
    PostgresAlertBackend,
    AlertEvaluator,
    AlertEngine,
    create_alert_engine,
    DEFAULT_ALERT_TEMPLATES,
)

from data.portfolio.portfolio import (
    AlertManager,
)

__all__ = [
    "AlertSeverity",
    "AlertStatus",
    "AlertType",
    "AlertChannel",
    "AlertCondition",
    "AlertRule",
    "Alert",
    "AlertBackend",
    "PostgresAlertBackend",
    "AlertEvaluator",
    "AlertEngine",
    "create_alert_engine",
    "DEFAULT_ALERT_TEMPLATES",
    "AlertManager",
]