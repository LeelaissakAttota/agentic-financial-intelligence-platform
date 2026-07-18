"""
Portfolio Management Module - Phase 5

Manages portfolio construction, optimization, tracking, and analytics.
"""

from data.portfolio.portfolio import (
    OrderSide,
    OrderType,
    OrderStatus,
    PositionSide,
    RebalanceStrategy,
    Order,
    Position,
    Portfolio,
    Transaction,
    PortfolioSnapshot,
    PortfolioBackend,
    PostgresPortfolioBackend,
    PortfolioManager,
    AlertManager,
    create_portfolio_manager,
)

from data.alerts.alerts import (
    AlertEvaluator,
    AlertRule,
    AlertCondition,
    Alert,
    AlertType,
    AlertSeverity,
    AlertStatus,
    AlertChannel,
    DEFAULT_ALERT_TEMPLATES,
)

__all__ = [
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "PositionSide",
    "RebalanceStrategy",
    "Order",
    "Position",
    "Portfolio",
    "Transaction",
    "PortfolioSnapshot",
    "PortfolioBackend",
    "PostgresPortfolioBackend",
    "PortfolioManager",
    "AlertManager",
    "AlertEvaluator",
    "AlertRule",
    "AlertCondition",
    "Alert",
    "AlertType",
    "AlertSeverity",
    "AlertStatus",
    "AlertChannel",
    "DEFAULT_ALERT_TEMPLATES",
    "create_portfolio_manager",
]