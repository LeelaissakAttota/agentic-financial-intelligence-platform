"""
Alerts Module - Phase 5

Real-time alerting system for portfolio events, price movements, news, and pattern triggers.
"""

import asyncio
import logging
import json
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

import asyncpg

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    EXPIRED = "expired"
    DISABLED = "disabled"


class AlertType(str, Enum):
    # Price alerts
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PRICE_CHANGE_PCT = "price_change_pct"
    PRICE_CHANGE_ABS = "price_change_abs"
    
    # Volume alerts
    VOLUME_SPIKE = "volume_spike"
    VOLUME_ABOVE_AVG = "volume_above_avg"
    
    # Technical alerts
    MOVING_AVERAGE_CROSS = "moving_average_cross"
    RSI_OVERBOUGHT = "rsi_overbought"
    RSI_OVERSOLD = "rsi_oversold"
    BOLLINGER_BAND_BREAK = "bollinger_band_break"
    MACD_CROSS = "macd_cross"
    
    # Pattern alerts
    PATTERN_DETECTED = "pattern_detected"
    PATTERN_COMPLETED = "pattern_completed"
    PATTERN_BREAKOUT = "pattern_breakout"
    
    # Portfolio alerts
    PORTFOLIO_VALUE_CHANGE = "portfolio_value_change"
    POSITION_SIZE_LIMIT = "position_size_limit"
    SECTOR_CONCENTRATION = "sector_concentration"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    VAR_BREACH = "var_breach"
    MARGIN_CALL = "margin_call"
    
    # News/Sentiment alerts
    NEWS_SENTIMENT_SHIFT = "news_sentiment_shift"
    NEWS_EVENT = "news_event"
    EARNINGS_ANNOUNCEMENT = "earnings_announcement"
    ANALYST_RATING_CHANGE = "analyst_rating_change"
    INSIDER_TRANSACTION = "insider_transaction"
    
    # Earnings/Events
    EARNINGS_SURPRISE = "earnings_surprise"
    GUIDANCE_CHANGE = "guidance_change"
    DIVIDEND_ANNOUNCEMENT = "dividend_announcement"
    SPLIT_ANNOUNCEMENT = "split_announcement"
    BUYBACK_ANNOUNCEMENT = "buyback_announcement"
    
    # Macro/Regulatory
    FED_DECISION = "fed_decision"
    CPI_RELEASE = "cpi_release"
    EMPLOYMENT_REPORT = "employment_report"
    REGULATORY_FILING = "regulatory_filing"
    
    # Pattern/Analytics
    REGIME_CHANGE = "regime_change"
    ANOMALY_DETECTED = "anomaly_detected"
    CORRELATION_BREAKDOWN = "correlation_breakdown"
    CUSTOM = "custom"


class AlertChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    PUSH = "push"
    SLACK = "slack"
    DISCORD = "discord"


@dataclass
class AlertCondition:
    """Defines the condition that triggers an alert."""
    type: AlertType
    symbol: str = ""
    parameters: dict = field(default_factory=dict)
    # Example parameters:
    # price_above: {"threshold": 150.0}
    # moving_average_cross: {"short_window": 20, "long_window": 50, "direction": "golden_cross"}
    # rsi_overbought: {"threshold": 70}
    # pattern_detected: {"pattern_types": ["double_bottom", "head_and_shoulders"]}
    # portfolio_value_change: {"threshold_pct": -5.0}
    # news_sentiment_shift: {"threshold": -0.5}


@dataclass
class AlertRule:
    """A rule that defines when and how alerts are triggered."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    user_id: str = ""
    portfolio_id: str = ""
    conditions: list[AlertCondition] = field(default_factory=list)
    # Logic: AND/OR between conditions
    logic: str = "AND"
    severity: AlertSeverity = AlertSeverity.INFO
    channels: list[AlertChannel] = field(default_factory=lambda: [AlertChannel.IN_APP])
    channels_config: dict = field(default_factory=dict)  # channel-specific config
    # Deduplication
    cooldown_minutes: int = 60
    max_triggers_per_hour: int = 10
    # Schedule
    active_hours: tuple[int, int] = (0, 23)  # UTC hours
    active_days: list[int] = field(default_factory=lambda: list(range(7)))  # 0=Mon
    # Time window
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    # Status
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Alert:
    """A triggered alert instance."""
    id: str = field(default_factory=lambda: str(uuid4()))
    rule_id: str = ""
    user_id: str = ""
    portfolio_id: str = ""
    type: AlertType = AlertType.CUSTOM
    severity: AlertSeverity = AlertSeverity.INFO
    status: AlertStatus = AlertStatus.ACTIVE
    title: str = ""
    message: str = ""
    symbol: str = ""
    # Trigger data
    trigger_value: Optional[float] = None
    trigger_condition: str = ""
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None
    # Context
    context: dict = field(default_factory=dict)
    # Channels
    channels: list[AlertChannel] = field(default_factory=lambda: [AlertChannel.IN_APP])
    sent_channels: list[AlertChannel] = field(default_factory=list)
    failed_channels: list[AlertChannel] = field(default_factory=list)
    # Lifecycle
    triggered_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    expires_at: Optional[datetime] = None
    # Metadata
    metadata: dict = field(default_factory=dict)
    
    def acknowledge(self, user_id: str) -> None:
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.utcnow()
        self.acknowledged_by = user_id
    
    def resolve(self, user_id: str) -> None:
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.utcnow()
        self.resolved_by = user_id
    
    def expire(self) -> None:
        self.status = AlertStatus.EXPIRED
        self.expires_at = datetime.utcnow()


class AlertBackend(ABC):
    """Abstract alert storage backend."""
    
    @abstractmethod
    async def save_rule(self, rule: AlertRule) -> None:
        pass
    
    @abstractmethod
    async def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        pass
    
    @abstractmethod
    async def get_rules(
        self,
        user_id: str = None,
        portfolio_id: str = None,
        enabled: bool = None
    ) -> list[AlertRule]:
        pass
    
    @abstractmethod
    async def update_rule(self, rule: AlertRule) -> None:
        pass
    
    @abstractmethod
    async def delete_rule(self, rule_id: str) -> bool:
        pass
    
    @abstractmethod
    async def save_alert(self, alert: Alert) -> None:
        pass
    
    @abstractmethod
    async def get_alert(self, alert_id: str) -> Optional[Alert]:
        pass
    
    @abstractmethod
    async def get_alerts(
        self,
        user_id: str = None,
        portfolio_id: str = None,
        status: AlertStatus = None,
        severity: AlertSeverity = None,
        type: AlertType = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[Alert]:
        pass
    
    @abstractmethod
    async def update_alert(self, alert: Alert) -> None:
        pass
    
    @abstractmethod
    async def get_alert_stats(self, user_id: str = None) -> dict:
        pass


class PostgresAlertBackend:
    """PostgreSQL backend for alert storage."""
    
    def __init__(self, dsn: str, pool_size: int = 10):
        self.dsn = dsn
        self.pool_size = pool_size
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(
            self.dsn,
            min_size=2,
            max_size=self.pool_size,
        )
        await self._init_schema()
    
    async def disconnect(self) -> None:
        if self.pool:
            await self.pool.close()
    
    async def _init_schema(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    portfolio_id TEXT,
                    conditions JSONB NOT NULL DEFAULT '[]',
                    logic TEXT NOT NULL DEFAULT 'AND',
                    severity TEXT NOT NULL DEFAULT 'info',
                    channels TEXT[] NOT NULL DEFAULT '{in_app}',
                    channels_config JSONB DEFAULT '{}',
                    cooldown_minutes INTEGER NOT NULL DEFAULT 60,
                    max_triggers_per_hour INTEGER NOT NULL DEFAULT 10,
                    active_hours_start INTEGER NOT NULL DEFAULT 0,
                    active_hours_end INTEGER NOT NULL DEFAULT 23,
                    active_days INTEGER[] NOT NULL DEFAULT '{0,1,2,3,4,5,6}',
                    valid_from TIMESTAMPTZ,
                    valid_until TIMESTAMPTZ,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_alert_rules_user ON alert_rules(user_id);
                CREATE INDEX IF NOT EXISTS idx_alert_rules_portfolio ON alert_rules(portfolio_id);
                CREATE INDEX IF NOT EXISTS idx_alert_rules_enabled ON alert_rules(enabled);
                
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    portfolio_id TEXT,
                    type TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'info',
                    status TEXT NOT NULL DEFAULT 'active',
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    symbol TEXT,
                    trigger_value NUMERIC,
                    trigger_condition TEXT,
                    current_value NUMERIC,
                    threshold_value NUMERIC,
                    context JSONB DEFAULT '{}',
                    channels TEXT[] NOT NULL DEFAULT '{in_app}',
                    sent_channels TEXT[] DEFAULT '{}',
                    failed_channels TEXT[] DEFAULT '{}',
                    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    acknowledged_at TIMESTAMPTZ,
                    acknowledged_by TEXT,
                    resolved_at TIMESTAMPTZ,
                    resolved_by TEXT,
                    expires_at TIMESTAMPTZ,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_alerts_user ON alerts(user_id);
                CREATE INDEX IF NOT EXISTS idx_alerts_portfolio ON alerts(portfolio_id);
                CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
                CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
                CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(type);
                CREATE INDEX IF NOT EXISTS idx_alerts_triggered ON alerts(triggered_at);
                CREATE INDEX IF NOT EXISTS idx_alerts_rule ON alerts(rule_id);
                
                CREATE TABLE IF NOT EXISTS alert_deliveries (
                    id TEXT PRIMARY KEY,
                    alert_id TEXT NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
                    channel TEXT NOT NULL,
                    status TEXT NOT NULL,
                    sent_at TIMESTAMPTZ,
                    error TEXT,
                    response JSONB,
                    attempts INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_deliveries_alert ON alert_deliveries(alert_id);
                CREATE INDEX IF NOT EXISTS idx_deliveries_status ON alert_deliveries(status);
                
                CREATE TABLE IF NOT EXISTS alert_templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    type TEXT NOT NULL,
                    template JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
    
    async def save_rule(self, rule: AlertRule) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO alert_rules (id, name, user_id, portfolio_id, conditions, logic, severity,
                                       channels, channels_config, cooldown_minutes, max_triggers_per_hour,
                                       active_hours_start, active_hours_end, active_days, valid_from, valid_until,
                                       enabled, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    conditions = EXCLUDED.conditions,
                    logic = EXCLUDED.logic,
                    severity = EXCLUDED.severity,
                    channels = EXCLUDED.channels,
                    channels_config = EXCLUDED.channels_config,
                    cooldown_minutes = EXCLUDED.cooldown_minutes,
                    max_triggers_per_hour = EXCLUDED.max_triggers_per_hour,
                    active_hours_start = EXCLUDED.active_hours_start,
                    active_hours_end = EXCLUDED.active_hours_end,
                    active_days = EXCLUDED.active_days,
                    valid_from = EXCLUDED.valid_from,
                    valid_until = EXCLUDED.valid_until,
                    enabled = EXCLUDED.enabled,
                    updated_at = EXCLUDED.updated_at
            """, rule.id, rule.name, rule.user_id, rule.portfolio_id,
               json.dumps([c.__dict__ for c in rule.conditions]), rule.logic,
               rule.severity.value, [c.value for c in rule.channels],
               json.dumps(rule.channels_config), rule.cooldown_minutes,
               rule.max_triggers_per_hour, rule.active_hours[0], rule.active_hours[1],
               rule.active_days, rule.valid_from, rule.valid_until,
               rule.enabled, rule.created_at, datetime.utcnow())
    
    async def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM alert_rules WHERE id = $1", rule_id)
            if not row:
                return None
            return self._row_to_rule(row)
    
    async def get_rules(
        self,
        user_id: str = None,
        portfolio_id: str = None,
        enabled: bool = None
    ) -> list[AlertRule]:
        conditions = []
        params = []
        
        if user_id:
            params.append(user_id)
            conditions.append(f"user_id = ${len(params)}")
        if portfolio_id:
            params.append(portfolio_id)
            conditions.append(f"portfolio_id = ${len(params)}")
        if enabled is not None:
            params.append(enabled)
            conditions.append(f"enabled = ${len(params)}")
        
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        query = f"SELECT * FROM alert_rules {where} ORDER BY created_at DESC"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_rule(row) for row in rows]
    
    async def update_rule(self, rule: AlertRule) -> None:
        rule.updated_at = datetime.utcnow()
        await self.save_rule(rule)
    
    async def delete_rule(self, rule_id: str) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM alert_rules WHERE id = $1", rule_id)
            return result != "DELETE 0"
    
    async def save_alert(self, alert: Alert) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO alerts (id, rule_id, user_id, portfolio_id, type, severity, status,
                                   title, message, symbol, trigger_value, trigger_condition,
                                   current_value, threshold_value, context, channels,
                                   sent_channels, failed_channels, triggered_at, acknowledged_at,
                                   acknowledged_by, resolved_at, resolved_by, expires_at, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19,
                        $20, $21, $22, $23, $24, $25)
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    acknowledged_at = EXCLUDED.acknowledged_at,
                    acknowledged_by = EXCLUDED.acknowledged_by,
                    resolved_at = EXCLUDED.resolved_at,
                    resolved_by = EXCLUDED.resolved_by,
                    expires_at = EXCLUDED.expires_at,
                    sent_channels = EXCLUDED.sent_channels,
                    failed_channels = EXCLUDED.failed_channels
            """, alert.id, alert.rule_id, alert.user_id, alert.portfolio_id, alert.type.value,
               alert.severity.value, alert.status.value, alert.title, alert.message, alert.symbol,
               alert.trigger_value, alert.trigger_condition, alert.current_value, alert.threshold_value,
               json.dumps(alert.context), [c.value for c in alert.channels],
               [c.value for c in alert.sent_channels], [c.value for c in alert.failed_channels],
               alert.triggered_at, alert.acknowledged_at, alert.acknowledged_by,
               alert.resolved_at, alert.resolved_by, alert.expires_at, json.dumps(alert.metadata))
    
    async def get_alert(self, alert_id: str) -> Optional[Alert]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM alerts WHERE id = $1", alert_id)
            if not row:
                return None
            return self._row_to_alert(row)
    
    async def get_alerts(
        self,
        user_id: str = None,
        portfolio_id: str = None,
        status: AlertStatus = None,
        severity: AlertSeverity = None,
        type: AlertType = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[Alert]:
        conditions = []
        params = []
        
        if user_id:
            params.append(user_id)
            conditions.append(f"user_id = ${len(params)}")
        if portfolio_id:
            params.append(portfolio_id)
            conditions.append(f"portfolio_id = ${len(params)}")
        if status:
            params.append(status.value)
            conditions.append(f"status = ${len(params)}")
        if severity:
            params.append(severity.value)
            conditions.append(f"severity = ${len(params)}")
        if type:
            params.append(type.value)
            conditions.append(f"type = ${len(params)}")
        if start_date:
            params.append(start_date)
            conditions.append(f"triggered_at >= ${len(params)}")
        if end_date:
            params.append(end_date)
            conditions.append(f"triggered_at <= ${len(params)}")
        
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.extend([limit, offset])
        
        query = f"""
            SELECT * FROM alerts 
            {where}
            ORDER BY triggered_at DESC
            LIMIT ${len(params)-1} OFFSET ${len(params)}
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_alert(row) for row in rows]
    
    async def update_alert(self, alert: Alert) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE alerts SET
                    status = $2,
                    acknowledged_at = $3,
                    acknowledged_by = $4,
                    resolved_at = $5,
                    resolved_by = $6,
                    expires_at = $7,
                    sent_channels = $8,
                    failed_channels = $8
                WHERE id = $1
            """, alert.id, alert.status.value, alert.acknowledged_at, alert.acknowledged_by,
               alert.resolved_at, alert.resolved_by, alert.expires_at,
               [c.value for c in alert.sent_channels], [c.value for c in alert.failed_channels])
    
    async def get_alert_stats(self, user_id: str = None) -> dict:
        conditions = []
        params = []
        
        if user_id:
            params.append(user_id)
            conditions.append(f"user_id = ${len(params)}")
        
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow(f"""
                SELECT 
                    COUNT(*) as total_alerts,
                    COUNT(*) FILTER (WHERE status = 'active') as active_alerts,
                    COUNT(*) FILTER (WHERE status = 'triggered') as triggered_alerts,
                    COUNT(*) FILTER (WHERE status = 'acknowledged') as acknowledged_alerts,
                    COUNT(*) FILTER (WHERE status = 'resolved') as resolved_alerts,
                    COUNT(*) FILTER (WHERE severity = 'critical') as critical_alerts,
                    COUNT(*) FILTER (WHERE severity = 'warning') as warning_alerts,
                    COUNT(*) FILTER (WHERE severity = 'info') as info_alerts,
                    COUNT(DISTINCT rule_id) as unique_rules_triggered,
                    COUNT(DISTINCT symbol) as symbols_affected
                FROM alerts
                {where}
            """, *params)
            
            return dict(stats) if stats else {}
    
    def _row_to_rule(self, row) -> AlertRule:
        import json
        conditions = row["conditions"]
        if isinstance(conditions, str):
            conditions = json.loads(conditions)
        return AlertRule(
            id=row["id"],
            name=row["name"],
            user_id=row["user_id"],
            portfolio_id=row["portfolio_id"],
            conditions=[
                AlertCondition(type=AlertType(c["type"]), symbol=c.get("symbol", ""), parameters=c.get("parameters", {}))
                for c in conditions
            ],
            logic=row["logic"],
            severity=AlertSeverity(row["severity"]),
            channels=[AlertChannel(c) for c in row["channels"]],
            channels_config=row["channels_config"],
            cooldown_minutes=row["cooldown_minutes"],
            max_triggers_per_hour=row["max_triggers_per_hour"],
            active_hours=(row["active_hours_start"], row["active_hours_end"]),
            active_days=row["active_days"],
            valid_from=row["valid_from"],
            valid_until=row["valid_until"],
            enabled=row["enabled"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )
    
    def _row_to_alert(self, row) -> Alert:
        return Alert(
            id=row["id"],
            rule_id=row["rule_id"],
            user_id=row["user_id"],
            portfolio_id=row["portfolio_id"],
            type=AlertType(row["type"]),
            severity=AlertSeverity(row["severity"]),
            status=AlertStatus(row["status"]),
            title=row["title"],
            message=row["message"],
            symbol=row["symbol"],
            trigger_value=row["trigger_value"],
            trigger_condition=row["trigger_condition"],
            current_value=row["current_value"],
            threshold_value=row["threshold_value"],
            context=row["context"],
            channels=[AlertChannel(c) for c in row["channels"]],
            sent_channels=[AlertChannel(c) for c in row["sent_channels"]],
            failed_channels=[AlertChannel(c) for c in row["failed_channels"]],
            triggered_at=row["triggered_at"],
            acknowledged_at=row["acknowledged_at"],
            acknowledged_by=row["acknowledged_by"],
            resolved_at=row["resolved_at"],
            resolved_by=row["resolved_by"],
            expires_at=row["expires_at"],
            metadata=row["metadata"]
        )


class AlertEvaluator:
    """Evaluates alert conditions against market data."""
    
    def __init__(self, market_data_provider=None):
        self.market_data = market_data_provider
    
    async def evaluate_condition(
        self,
        condition: AlertCondition,
        market_data: dict[str, Any]
    ) -> tuple[bool, dict]:
        """
        Evaluate a single alert condition.
        
        Returns:
            (triggered, trigger_data)
        """
        try:
            if condition.type == AlertType.PRICE_ABOVE:
                return await self._check_price_above(condition, market_data)
            elif condition.type == AlertType.PRICE_BELOW:
                return await self._check_price_below(condition, market_data)
            elif condition.type == AlertType.PRICE_CHANGE_PCT:
                return await self._check_price_change_pct(condition, market_data)
            elif condition.type == AlertType.PRICE_CHANGE_ABS:
                return await self._check_price_change_abs(condition, market_data)
            elif condition.type == AlertType.VOLUME_SPIKE:
                return await self._check_volume_spike(condition, market_data)
            elif condition.type == AlertType.MOVING_AVERAGE_CROSS:
                return await self._check_ma_cross(condition, market_data)
            elif condition.type == AlertType.RSI_OVERBOUGHT:
                return await self._check_rsi_overbought(condition, market_data)
            elif condition.type == AlertType.RSI_OVERSOLD:
                return await self._check_rsi_oversold(condition, market_data)
            elif condition.type == AlertType.BOLLINGER_BAND_BREAK:
                return await self._check_bollinger_break(condition, market_data)
            elif condition.type == AlertType.MACD_CROSS:
                return await self._check_macd_cross(condition, market_data)
            elif condition.type == AlertType.PATTERN_DETECTED:
                return await self._check_pattern_detected(condition, market_data)
            elif condition.type == AlertType.PORTFOLIO_VALUE_CHANGE:
                return await self._check_portfolio_change(condition, market_data)
            elif condition.type == AlertType.NEWS_SENTIMENT_SHIFT:
                return await self._check_news_sentiment(condition, market_data)
            elif condition.type == AlertType.EARNINGS_ANNOUNCEMENT:
                return await self._check_earnings(condition, market_data)
            else:
                return False, {"error": f"Unknown condition type: {condition.type}"}
        except Exception as e:
            logger.error(f"Error evaluating condition {condition.type}: {e}")
            return False, {"error": str(e)}
    
    async def _check_price_above(self, condition: AlertCondition, market_data: dict) -> tuple[bool, dict]:
        threshold = condition.parameters.get("threshold")
        if threshold is None:
            return False, {"error": "threshold parameter required"}
        
        symbol = condition.symbol
        if symbol not in market_data:
            return False, {"error": f"No market data for {symbol}"}
        
        current_price = market_data[symbol].get("price") or market_data[symbol].get("last")
        if current_price is None:
            return False, {"error": f"No price data for {symbol}"}
        
        triggered = current_price > threshold
        return triggered, {
            "triggered": triggered,
            "current_price": current_price,
            "threshold": threshold,
            "symbol": symbol
        }
    
    async def _check_price_below(self, condition: AlertCondition, market_data: dict) -> tuple[bool, dict]:
        threshold = condition.parameters.get("threshold")
        if threshold is None:
            return False, {"error": "threshold parameter required"}
        
        symbol = condition.symbol
        if symbol not in market_data:
            return False, {"error": f"No market data for {symbol}"}
        
        current_price = market_data[symbol].get("price") or market_data[symbol].get("last")
        if current_price is None:
            return False, {"error": f"No price data for {symbol}"}
        
        triggered = current_price < threshold
        return triggered, {
            "triggered": triggered,
            "current_price": current_price,
            "threshold": threshold,
            "symbol": symbol
        }
    
    async def _check_price_change_pct(self, condition: AlertCondition, market_data: dict) -> tuple[bool, dict]:
        threshold = condition.parameters.get("threshold_pct")
        period = condition.parameters.get("period", "1d")
        
        if threshold is None:
            return False, {"error": "threshold_pct parameter required"}
        
        symbol = condition.symbol
        if symbol not in market_data:
            return False, {"error": f"No market data for {symbol}"}
        
        data = market_data[symbol]
        change_pct = data.get(f"change_pct_{period}") or data.get("change_pct")
        
        if change_pct is None:
            return False, {"error": f"No change data for {symbol}"}
        
        if threshold > 0:
            triggered = change_pct >= threshold
        else:
            triggered = change_pct <= threshold
        
        return triggered, {
            "triggered": triggered,
            "change_pct": change_pct,
            "threshold": threshold,
            "period": period,
            "symbol": symbol
        }
    
    async def _check_price_change_abs(self, condition: AlertCondition, market_data: dict) -> tuple[bool, dict]:
        threshold = condition.parameters.get("threshold")
        if threshold is None:
            return False, {"error": "threshold parameter required"}
        
        symbol = condition.symbol
        if symbol not in market_data:
            return False, {"error": f"No market data for {symbol}"}
        
        data = market_data[symbol]
        change = data.get("change") or data.get("change_abs")
        
        if change is None:
            return False, {"error": f"No change data for {symbol}"}
        
        if threshold > 0:
            triggered = change >= threshold
        else:
            triggered = change <= threshold
        
        return triggered, {
            "triggered": triggered,
            "change": change,
            "threshold": threshold,
            "symbol": symbol
        }
    
    async def _check_volume_spike(self, condition: AlertCondition, market_data: dict) -> tuple[bool, dict]:
        threshold = condition.parameters.get("threshold", 2.0)  # Multiple of average
        period = condition.parameters.get("period", 20)
        
        symbol = condition.symbol
        if symbol not in market_data:
            return False, {"error": f"No market data for {symbol}"}
        
        data = market_data[symbol]
        volume = data.get("volume")
        avg_volume = data.get(f"avg_volume_{period}") or data.get("avg_volume")
        
        if volume is None or avg_volume is None or avg_volume == 0:
            return False, {"error": "Insufficient volume data"}
        
        ratio = volume / avg_volume
        triggered = ratio >= threshold
        
        return triggered, {
            "triggered": triggered,
            "volume": volume,
            "avg_volume": avg_volume,
            "ratio": ratio,
            "threshold": threshold,
            "symbol": symbol
        }
    
    async def _check_ma_cross(self, condition: AlertCondition, market_data: dict) -> tuple[bool, dict]:
        short_window = condition.parameters.get("short_window", 20)
        long_window = condition.parameters.get("long_window", 50)
        direction = condition.parameters.get("direction", "golden_cross")  # golden_cross or death_cross
        
        symbol = condition.symbol
        if symbol not in market_data:
            return False, {"error": f"No market data for {symbol}"}
        
        data = market_data[symbol]
        short_ma = data.get(f"sma_{short_window}")
        long_ma = data.get(f"sma_{long_window}")
        prev_short_ma = data.get(f"prev_sma_{short_window}")
        prev_long_ma = data.get(f"prev_sma_{long_window}")
        
        if None in [short_ma, long_ma, prev_short_ma, prev_long_ma]:
            return False, {"error": "Insufficient MA data"}
        
        # Golden cross: short MA crosses above long MA
        golden_cross = prev_short_ma <= prev_long_ma and short_ma > long_ma
        # Death cross: short MA crosses below long MA
        death_cross = prev_short_ma >= prev_long_ma and short_ma < long_ma
        
        triggered = (direction == "golden_cross" and golden_cross) or \
                    (direction == "death_cross" and death_cross)
        
        return triggered, {
            "triggered": triggered,
            "cross_type": "golden_cross" if golden_cross else "death_cross" if death_cross else "none",
            "short_ma": short_ma,
            "long_ma": long_ma,
            "short_window": short_window,
            "long_window": long_window
        }
    
    async def _check_rsi_overbought(self, condition: AlertCondition, market_data: dict) -> tuple[bool, dict]:
        threshold = condition.parameters.get("threshold", 70)
        
        symbol = condition.symbol
        if symbol not in market_data:
            return False, {"error": f"No market data for {symbol}"}
        
        rsi = market_data[symbol].get("rsi")
        if rsi is None:
            return False, {"error": "RSI not available"}
        
        triggered = rsi >= threshold
        return triggered, {
            "triggered": triggered,
            "rsi": rsi,
            "threshold": threshold
        }
    
    async def _check_rsi_oversold(self, condition: AlertCondition, market_data: dict) -> tuple[bool, dict]:
        threshold = condition.parameters.get("threshold", 30)
        
        symbol = condition.symbol
        if symbol not in market_data:
            return False, {"error": f"No market data for {symbol}"}
        
        rsi = market_data[symbol].get("rsi")
        if rsi is None:
            return False, {"error": "RSI not available"}
        
        triggered = rsi <= threshold
        return triggered, {
            "triggered": triggered,
            "rsi": rsi,
            "threshold": threshold
        }
    
    async def _check_bollinger_break(self, condition: AlertCondition, market_data: dict) -> tuple[bool, dict]:
        direction = condition.parameters.get("direction", "upper")  # upper or lower
        
        symbol = condition.symbol
        if symbol not in market_data:
            return False, {"error": f"No market data for {symbol}"}
        
        data = market_data[symbol]
        upper = data.get("bb_upper")
        lower = data.get("bb_lower")
        price = data.get("price") or data.get("close")
        
        if None in [upper, lower, price]:
            return False, {"error": "Bollinger bands not available"}
        
        if direction == "upper":
            triggered = price >= upper
        else:
            triggered = price <= lower
        
        return triggered, {
            "triggered": triggered,
            "price": price,
            "upper_band": upper,
            "lower_band": lower,
            "direction": direction
        }
    
    async def _check_macd_cross(self, condition: AlertCondition, market_data: dict) -> tuple[bool, dict]:
        direction = condition.parameters.get("direction", "bullish")  # bullish or bearish
        
        symbol = condition.symbol
        if symbol not in market_data:
            return False, {"error": f"No market data for {symbol}"}
        
        data = market_data[symbol]
        macd = data.get("macd")
        signal = data.get("macd_signal")
        prev_macd = data.get("prev_macd")
        prev_signal = data.get("prev_macd_signal")
        
        if None in [macd, signal, prev_macd, prev_signal]:
            return False, {"error": "MACD data not available"}
        
        # Bullish cross: MACD crosses above signal
        bullish = prev_macd <= prev_signal and macd > signal
        # Bearish cross: MACD crosses below signal
        bearish = prev_macd >= prev_signal and macd < signal
        
        triggered = (direction == "bullish" and bullish) or (direction == "bearish" and bearish)
        
        return triggered, {
            "triggered": triggered,
            "macd": macd,
            "signal": signal,
            "cross_type": "bullish" if bullish else "bearish" if bearish else "none"
        }
    
    async def _check_pattern_detected(self, condition: AlertCondition, market_data: dict) -> tuple[bool, dict]:
        pattern_types = condition.parameters.get("pattern_types", [])
        symbol = condition.symbol
        
        # This would integrate with pattern detection system
        # For now, return False
        return False, {"message": "Pattern detection not yet implemented in evaluator"}
    
    async def _check_portfolio_change(self, condition: AlertCondition, market_data: dict) -> tuple[bool, dict]:
        threshold = condition.parameters.get("threshold_pct", -5.0)
        portfolio_id = condition.parameters.get("portfolio_id")
        
        # Would need portfolio data
        return False, {"message": "Portfolio change check not implemented"}
    
    async def _check_news_sentiment(self, condition: AlertCondition, market_data: dict) -> tuple[bool, dict]:
        threshold = condition.parameters.get("threshold", -0.5)
        symbol = condition.symbol
        
        if symbol not in market_data:
            return False, {"error": f"No market data for {symbol}"}
        
        sentiment = market_data[symbol].get("news_sentiment")
        if sentiment is None:
            return False, {"error": "Sentiment data not available"}
        
        triggered = sentiment <= threshold
        return triggered, {
            "triggered": triggered,
            "sentiment": sentiment,
            "threshold": threshold
        }
    
    async def _check_earnings(self, condition: AlertCondition, market_data: dict) -> tuple[bool, dict]:
        symbol = condition.symbol
        
        # Check for earnings announcements
        earnings_data = market_data.get(symbol, {}).get("earnings")
        if not earnings_data:
            return False, {"triggered": False}
        
        has_earnings = earnings_data.get("has_earnings", False)
        surprise = earnings_data.get("surprise_pct", 0)
        surprise_threshold = condition.parameters.get("surprise_threshold", 0)
        
        triggered = has_earnings and abs(surprise) >= surprise_threshold
        
        return triggered, {
            "triggered": triggered,
            "has_earnings": has_earnings,
            "surprise_pct": surprise,
            "surprise_threshold": surprise_threshold
        }


class AlertEngine:
    """Main alert evaluation and dispatch engine."""
    
    def __init__(
        self,
        backend: PostgresAlertBackend,
        evaluator: AlertEvaluator,
        notifier=None
    ):
        self.backend = backend
        self.evaluator = evaluator
        self.notifier = notifier
        self._running = False
        self._rules_cache: dict[str, AlertRule] = {}
        self._trigger_history: dict[str, list[datetime]] = defaultdict(list)
    
    async def initialize(self) -> None:
        """Load active rules into memory."""
        rules = await self.backend.get_rules(enabled=True)
        for rule in rules:
            self._rules_cache[rule.id] = rule
        logger.info(f"Loaded {len(self._rules_cache)} active alert rules")
    
    async def add_rule(self, rule: AlertRule) -> str:
        await self.backend.save_rule(rule)
        self._rules_cache[rule.id] = rule
        return rule.id
    
    async def update_rule(self, rule: AlertRule) -> None:
        await self.backend.update_rule(rule)
        self._rules_cache[rule.id] = rule
    
    async def delete_rule(self, rule_id: str) -> bool:
        result = await self.backend.delete_rule(rule_id)
        if result:
            self._rules_cache.pop(rule_id, None)
        return result
    
    async def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        return self._rules_cache.get(rule_id) or await self.backend.get_rule(rule_id)
    
    async def get_rules(
        self,
        user_id: str = None,
        portfolio_id: str = None
    ) -> list[AlertRule]:
        return await self.backend.get_rules(user_id=user_id, portfolio_id=portfolio_id)
    
    async def evaluate_rules(self, market_data: dict[str, Any]) -> list[Alert]:
        """Evaluate all active rules against current market data."""
        triggered_alerts = []
        
        for rule in self._rules_cache.values():
            if not rule.enabled:
                continue
            
            # Check if rule is within active hours/days
            if not self._is_rule_active(rule):
                continue
            
            # Check cooldown
            if self._is_in_cooldown(rule.id):
                continue
            
            # Check rate limit
            if self._is_rate_limited(rule.id):
                continue
            
            # Evaluate conditions
            triggered = await self._evaluate_rule_conditions(rule, market_data)
            
            if triggered:
                alert = await self._create_alert(rule, market_data)
                triggered_alerts.append(alert)
                self._record_trigger(rule.id)
        
        return triggered_alerts
    
    def _is_rule_active(self, rule: AlertRule) -> bool:
        now = datetime.utcnow()
        
        # Check time window
        if rule.valid_from and now < rule.valid_from:
            return False
        if rule.valid_until and now > rule.valid_until:
            return False
        
        # Check active hours (UTC)
        current_hour = now.hour
        if not (rule.active_hours[0] <= current_hour <= rule.active_hours[1]):
            return False
        
        # Check active days (0=Monday)
        current_day = now.weekday()
        if current_day not in rule.active_days:
            return False
        
        return True
    
    def _is_in_cooldown(self, rule_id: str) -> bool:
        history = self._trigger_history.get(rule_id, [])
        if not history:
            return False
        
        last_trigger = max(history)
        cooldown = self._rules_cache.get(rule_id)
        if cooldown:
            cooldown_minutes = cooldown.cooldown_minutes
        else:
            cooldown_minutes = 60
        
        return datetime.utcnow() - last_trigger < timedelta(minutes=cooldown_minutes)
    
    def _is_rate_limited(self, rule_id: str) -> bool:
        history = self._trigger_history.get(rule_id, [])
        rule = self._rules_cache.get(rule_id)
        max_per_hour = rule.max_triggers_per_hour if rule else 10
        
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_triggers = sum(1 for t in history if t > hour_ago)
        
        return recent_triggers >= max_per_hour
    
    def _record_trigger(self, rule_id: str) -> None:
        self._trigger_history[rule_id].append(datetime.utcnow())
        
        # Clean old history
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        self._trigger_history[rule_id] = [
            t for t in self._trigger_history[rule_id] if t > hour_ago
        ]
    
    async def _evaluate_rule_conditions(self, rule: AlertRule, market_data: dict) -> bool:
        results = []
        
        for condition in rule.conditions:
            triggered, data = await self.evaluator.evaluate_condition(condition, market_data)
            results.append(triggered)
            
            if rule.logic == "AND" and not triggered:
                return False
            elif rule.logic == "OR" and triggered:
                return True
        
        if rule.logic == "AND":
            return all(results)
        elif rule.logic == "OR":
            return any(results)
        return False
    
    async def _create_alert(self, rule: AlertRule, market_data: dict) -> Alert:
        # Determine which condition(s) triggered
        triggered_conditions = []
        for condition in rule.conditions:
            triggered, data = await self.evaluator.evaluate_condition(condition, market_data)
            if triggered:
                triggered_conditions.append((condition, data))
        
        # Build alert
        if not triggered_conditions:
            return None
        
        # Use first triggered condition for primary info
        primary_condition, primary_data = triggered_conditions[0]
        
        symbol = primary_condition.symbol or ""
        trigger_value = primary_data.get("current_price") or primary_data.get("current_price") or primary_data.get("rsi") or primary_data.get("volume")
        threshold_value = primary_data.get("threshold")
        
        alert = Alert(
            rule_id=rule.id,
            user_id="",  # Would need to be passed from rule context
            portfolio_id=rule.portfolio_id or "",
            type=primary_condition.type,
            severity=rule.severity,
            status=AlertStatus.ACTIVE,
            title=self._generate_title(primary_condition, primary_data),
            message=self._generate_message(primary_condition, primary_data, symbol),
            symbol=symbol,
            trigger_value=trigger_value,
            trigger_condition=primary_condition.type.value,
            current_value=trigger_value,
            threshold_value=threshold_value,
            context={
                "rule_name": rule.name,
                "rule_id": rule.id,
                "conditions": [{"type": c.type.value, "data": d} for c, d in triggered_conditions],
                "market_data": {k: v for k, v in market_data.items() if k == symbol}
            },
            channels=rule.channels,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        # Save alert
        await self.backend.save_alert(alert)
        
        # Dispatch notifications
        await self._dispatch_alert(alert)
        
        return alert
    
    def _generate_title(self, condition: AlertCondition, data: dict) -> str:
        symbol = condition.symbol or "MARKET"
        
        if condition.type == AlertType.PRICE_ABOVE:
            return f"{symbol} price above ${data.get('threshold', 'N/A')}"
        elif condition.type == AlertType.PRICE_BELOW:
            return f"{symbol} price below ${data.get('threshold', 'N/A')}"
        elif condition.type == AlertType.MOVING_AVERAGE_CROSS:
            cross_type = data.get("cross_type", "cross").replace("_", " ").title()
            return f"{symbol} {cross_type} detected"
        elif condition.type == AlertType.RSI_OVERBOUGHT:
            return f"{symbol} RSI overbought ({data.get('rsi', 'N/A')})"
        elif condition.type == AlertType.RSI_OVERSOLD:
            return f"{symbol} RSI oversold ({data.get('rsi', 'N/A')})"
        elif condition.type == AlertType.BOLLINGER_BAND_BREAK:
            direction = data.get("direction", "break")
            return f"{symbol} Bollinger Band {direction} break"
        elif condition.type == AlertType.MACD_CROSS:
            direction = "bullish" if data.get("cross_type") == "bullish" else "bearish"
            return f"{symbol} MACD {direction} cross"
        elif condition.type == AlertType.VOLUME_SPIKE:
            return f"{symbol} volume spike ({data.get('ratio', 'N/A')}x avg)"
        elif condition.type == AlertType.PATTERN_DETECTED:
            return f"Pattern detected for {symbol}"
        elif condition.type == AlertType.NEWS_SENTIMENT_SHIFT:
            return f"{symbol} sentiment shift detected"
        elif condition.type == AlertType.EARNINGS_ANNOUNCEMENT:
            return f"{symbol} earnings announcement"
        else:
            return f"Alert triggered for {symbol}"
    
    def _generate_message(self, condition: AlertCondition, data: dict, symbol: str) -> str:
        symbol = condition.symbol or symbol or "MARKET"
        
        if condition.type == AlertType.PRICE_ABOVE:
            return f"{symbol} current price of ${data.get('current_price', 'N/A')} exceeded threshold of ${data.get('threshold', 'N/A')}"
        elif condition.type == AlertType.PRICE_BELOW:
            return f"{symbol} current price of ${data.get('current_price', 'N/A')} fell below threshold of ${data.get('threshold', 'N/A')}"
        elif condition.type == AlertType.MOVING_AVERAGE_CROSS:
            cross_type = data.get("cross_type", "cross").replace("_", " ").title()
            return f"{symbol} {cross_type}: {data.get('short_window', 20)}-period MA crossed {data.get('long_window', 50)}-period MA"
        elif condition.type == AlertType.RSI_OVERBOUGHT:
            return f"{symbol} RSI at {data.get('rsi', 'N/A')} exceeds overbought threshold of {data.get('threshold', 'N/A')}"
        elif condition.type == AlertType.RSI_OVERSOLD:
            return f"{symbol} RSI at {data.get('rsi', 'N/A')} below oversold threshold of {data.get('threshold', 'N/A')}"
        elif condition.type == AlertType.BOLLINGER_BAND_BREAK:
            direction = data.get("direction", "break")
            return f"{symbol} price broke {direction} Bollinger Band"
        elif condition.type == AlertType.MACD_CROSS:
            cross_type = data.get("cross_type", "cross")
            return f"{symbol} MACD {cross_type} cross detected"
        elif condition.type == AlertType.VOLUME_SPIKE:
            return f"{symbol} volume spike: {data.get('ratio', 'N/A')}x average volume"
        elif condition.type == AlertType.PATTERN_DETECTED:
            return f"Technical pattern detected for {symbol}"
        elif condition.type == AlertType.NEWS_SENTIMENT_SHIFT:
            return f"{symbol} news sentiment shifted to {data.get('sentiment', 'N/A')}"
        elif condition.type == AlertType.EARNINGS_ANNOUNCEMENT:
            surprise = data.get("surprise_pct", 0)
            return f"{symbol} reported earnings with {surprise:.1f}% surprise"
        else:
            return f"Alert triggered for {symbol}: {condition.type.value}"
    
    async def _dispatch_alert(self, alert: Alert) -> None:
        """Dispatch alert through configured channels."""
        for channel in alert.channels:
            if channel in alert.sent_channels:
                continue
            
            try:
                success = await self._send_notification(alert, channel)
                if success:
                    alert.sent_channels.append(channel)
                else:
                    alert.failed_channels.append(channel)
            except Exception as e:
                logger.error(f"Failed to send alert via {channel}: {e}")
                alert.failed_channels.append(channel)
        
        # Update alert with delivery status
        await self.backend.update_alert(alert)
    
    async def _send_notification(self, alert: Alert, channel: AlertChannel) -> bool:
        """Send notification via specific channel."""
        if channel == AlertChannel.IN_APP:
            # In-app notifications are stored in database
            return True
        
        elif channel == AlertChannel.EMAIL:
            # Would integrate with email service
            logger.info(f"Email alert: {alert.title}")
            return True
        
        elif channel == AlertChannel.SLACK:
            # Would integrate with Slack webhook
            logger.info(f"Slack alert: {alert.title}")
            return True
        
        elif channel == AlertChannel.WEBHOOK:
            # Would POST to webhook URL
            logger.info(f"Webhook alert: {alert.title}")
            return True
        
        return False
    
    async def acknowledge_alert(self, alert_id: str, user_id: str) -> bool:
        alert = await self.backend.get_alert(alert_id)
        if not alert:
            return False
        
        alert.acknowledge(user_id)
        await self.backend.update_alert(alert)
        return True
    
    async def resolve_alert(self, alert_id: str, user_id: str) -> bool:
        alert = await self.backend.get_alert(alert_id)
        if not alert:
            return False
        
        alert.resolve(user_id)
        await self.backend.update_alert(alert)
        return True
    
    async def get_user_alerts(
        self,
        user_id: str,
        status: AlertStatus = None,
        limit: int = 50
    ) -> list[Alert]:
        return await self.backend.get_alerts(user_id=user_id, status=status, limit=limit)
    
    async def get_portfolio_alerts(
        self,
        portfolio_id: str,
        status: AlertStatus = None
    ) -> list[Alert]:
        return await self.backend.get_alerts(portfolio_id=portfolio_id, status=status)
    
    async def run_evaluation_loop(self, market_data_provider, interval_seconds: int = 60) -> None:
        """Run continuous evaluation loop."""
        self._running = True
        logger.info("Starting alert evaluation loop")
        
        while self._running:
            try:
                market_data = await market_data_provider.get_current_data()
                await self.evaluate_rules(market_data)
            except Exception as e:
                logger.error(f"Error in evaluation loop: {e}")
            
            await asyncio.sleep(interval_seconds)
    
    def stop(self) -> None:
        self._running = False


# Factory
async def create_alert_engine(
    backend_type: str = "postgres",
    market_data_provider=None,
    **kwargs
) -> AlertEngine:
    """Factory function to create AlertEngine with specified backend."""
    if backend_type == "postgres":
        backend = PostgresAlertBackend(
            dsn=kwargs.get("dsn", "postgresql://localhost/financial_alerts"),
            pool_size=kwargs.get("pool_size", 10)
        )
        await backend.connect()
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")
    
    evaluator = AlertEvaluator(market_data_provider=market_data_provider)
    engine = AlertEngine(backend, evaluator)
    await engine.initialize()
    return engine


# Default alert templates
DEFAULT_ALERT_TEMPLATES = {
    "price_above": {
        "name": "Price Above Threshold",
        "type": AlertType.PRICE_ABOVE,
        "severity": AlertSeverity.INFO,
        "parameters": {"threshold": 0.0},
        "message_template": "{symbol} price (${current_price}) exceeded threshold (${threshold})"
    },
    "price_below": {
        "name": "Price Below Threshold",
        "type": AlertType.PRICE_BELOW,
        "severity": AlertSeverity.WARNING,
        "parameters": {"threshold": 0.0},
        "message_template": "{symbol} price (${current_price}) fell below threshold (${threshold})"
    },
    "ma_golden_cross": {
        "name": "Golden Cross",
        "type": AlertType.MOVING_AVERAGE_CROSS,
        "severity": AlertSeverity.INFO,
        "parameters": {"short_window": 50, "long_window": 200, "direction": "golden_cross"},
        "message_template": "{symbol} Golden Cross: 50-day MA crossed above 200-day MA"
    },
    "ma_death_cross": {
        "name": "Death Cross",
        "type": AlertType.MOVING_AVERAGE_CROSS,
        "severity": AlertSeverity.WARNING,
        "parameters": {"short_window": 50, "long_window": 200, "direction": "death_cross"},
        "message_template": "{symbol} Death Cross: 50-day MA crossed below 200-day MA"
    },
    "rsi_overbought": {
        "name": "RSI Overbought",
        "type": AlertType.RSI_OVERBOUGHT,
        "severity": AlertSeverity.WARNING,
        "parameters": {"threshold": 70},
        "message_template": "{symbol} RSI overbought at {rsi}"
    },
    "rsi_oversold": {
        "name": "RSI Oversold",
        "type": AlertType.RSI_OVERSOLD,
        "severity": AlertSeverity.INFO,
        "parameters": {"threshold": 30},
        "message_template": "{symbol} RSI oversold at {rsi}"
    },
    "volume_spike": {
        "name": "Volume Spike",
        "type": AlertType.VOLUME_SPIKE,
        "severity": AlertSeverity.INFO,
        "parameters": {"threshold": 3.0, "period": 20},
        "message_template": "{symbol} volume spike: {ratio:.1f}x average volume"
    },
    "bollinger_break": {
        "name": "Bollinger Band Break",
        "type": AlertType.BOLLINGER_BAND_BREAK,
        "severity": AlertSeverity.INFO,
        "parameters": {"direction": "upper"},
        "message_template": "{symbol} broke {direction} Bollinger Band"
    },
    "macd_bullish": {
        "name": "MACD Bullish Cross",
        "type": AlertType.MACD_CROSS,
        "severity": AlertSeverity.INFO,
        "parameters": {"direction": "bullish"},
        "message_template": "{symbol} MACD bullish cross"
    },
    "macd_bearish": {
        "name": "MACD Bearish Cross",
        "type": AlertType.MACD_CROSS,
        "severity": AlertSeverity.WARNING,
        "parameters": {"direction": "bearish"},
        "message_template": "{symbol} MACD bearish cross"
    },
    "earnings_alert": {
        "name": "Earnings Alert",
        "type": AlertType.EARNINGS_ANNOUNCEMENT,
        "severity": AlertSeverity.INFO,
        "parameters": {"surprise_threshold": 5.0},
        "message_template": "{symbol} earnings surprise: {surprise_pct:.1f}%"
    }
}


# Export
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
]