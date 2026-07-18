"""
Phase 5 - Alerts Tests
"""
import pytest
from datetime import datetime, date, timedelta
from data.alerts import (
    AlertEngine, AlertType, AlertSeverity, AlertStatus, AlertChannel,
    AlertCondition, AlertRule, Alert, PostgresAlertBackend, create_alert_engine,
    AlertEvaluator, DEFAULT_ALERT_TEMPLATES
)


class TestAlertDataclasses:
    """Test alert dataclasses."""
    
    def test_create_alert_condition(self):
        condition = AlertCondition(
            type=AlertType.PRICE_ABOVE,
            symbol="AAPL",
            parameters={"threshold": 150.0}
        )
        assert condition.type == AlertType.PRICE_ABOVE
        assert condition.symbol == "AAPL"
        assert condition.parameters["threshold"] == 150.0
    
    def test_create_alert_rule(self):
        rule = AlertRule(
            name="AAPL Breakout",
            user_id="user123",
            portfolio_id="pf123",
            conditions=[
                AlertCondition(
                    type=AlertType.PRICE_ABOVE,
                    symbol="AAPL",
                    parameters={"threshold": 200.0}
                ),
                AlertCondition(
                    type=AlertType.VOLUME_SPIKE,
                    symbol="AAPL",
                    parameters={"threshold": 3.0}
                )
            ],
            logic="AND",
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.IN_APP, AlertChannel.EMAIL],
            cooldown_minutes=60
        )
        assert rule.name == "AAPL Breakout"
        assert rule.logic == "AND"
        assert len(rule.conditions) == 2
        assert rule.cooldown_minutes == 60
    
    def test_create_alert(self):
        alert = Alert(
            rule_id="rule123",
            user_id="user123",
            portfolio_id="pf123",
            type=AlertType.PRICE_ABOVE,
            severity=AlertSeverity.CRITICAL,
            title="AAPL Above $200",
            message="AAPL price $205 exceeded $200 threshold",
            symbol="AAPL",
            trigger_value=205.0,
            threshold_value=200.0,
            channels=[AlertChannel.IN_APP, AlertChannel.SLACK]
        )
        assert alert.rule_id == "rule123"
        assert alert.type == AlertType.PRICE_ABOVE
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.status == AlertStatus.ACTIVE
        assert alert.trigger_value == 205.0
        assert alert.threshold_value == 200.0
    
    def test_alert_acknowledge(self):
        alert = Alert(
            rule_id="rule123",
            user_id="user123",
            type=AlertType.PRICE_BELOW,
            severity=AlertSeverity.WARNING
        )
        alert.acknowledge("user456")
        
        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.acknowledged_by == "user456"
        assert alert.acknowledged_at is not None
    
    def test_alert_resolve(self):
        alert = Alert(
            rule_id="rule123",
            user_id="user123",
            type=AlertType.PRICE_BELOW
        )
        alert.resolve("user456")
        
        assert alert.status == AlertStatus.RESOLVED
        assert alert.resolved_by == "user456"
        assert alert.resolved_at is not None
    
    def test_alert_expire(self):
        alert = Alert(
            rule_id="rule123",
            user_id="user123",
            type=AlertType.PRICE_BELOW
        )
        alert.expire()
        
        assert alert.status == AlertStatus.EXPIRED
        assert alert.expires_at is not None


class TestAlertEnums:
    """Test alert enums."""
    
    def test_alert_types(self):
        # Price alerts
        assert AlertType.PRICE_ABOVE.value == "price_above"
        assert AlertType.PRICE_BELOW.value == "price_below"
        assert AlertType.PRICE_CHANGE_PCT.value == "price_change_pct"
        
        # Technical alerts
        assert AlertType.MOVING_AVERAGE_CROSS.value == "moving_average_cross"
        assert AlertType.RSI_OVERBOUGHT.value == "rsi_overbought"
        assert AlertType.MACD_CROSS.value == "macd_cross"
        
        # Portfolio alerts
        assert AlertType.PORTFOLIO_VALUE_CHANGE.value == "portfolio_value_change"
        assert AlertType.VAR_BREACH.value == "var_breach"
        
        # News alerts
        assert AlertType.NEWS_SENTIMENT_SHIFT.value == "news_sentiment_shift"
        assert AlertType.EARNINGS_ANNOUNCEMENT.value == "earnings_announcement"
    
    def test_alert_severity(self):
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.CRITICAL.value == "critical"
    
    def test_alert_status(self):
        assert AlertStatus.ACTIVE.value == "active"
        assert AlertStatus.TRIGGERED.value == "triggered"
        assert AlertStatus.ACKNOWLEDGED.value == "acknowledged"
        assert AlertStatus.RESOLVED.value == "resolved"
        assert AlertStatus.EXPIRED.value == "expired"
    
    def test_alert_channel(self):
        assert AlertChannel.IN_APP.value == "in_app"
        assert AlertChannel.EMAIL.value == "email"
        assert AlertChannel.SLACK.value == "slack"
        assert AlertChannel.WEBHOOK.value == "webhook"


class TestAlertEvaluator:
    """Test AlertEvaluator."""
    
    @pytest.fixture
    def evaluator(self):
        return AlertEvaluator(market_data_provider=None)
    
    @pytest.mark.asyncio
    async def test_check_price_above(self, evaluator):
        condition = AlertCondition(
            type=AlertType.PRICE_ABOVE,
            symbol="AAPL",
            parameters={"threshold": 150.0}
        )
        
        market_data = {
            "AAPL": {"price": 155.0, "last": 155.0}
        }
        
        triggered, data = await evaluator.evaluate_condition(condition, market_data)
        
        assert triggered is True
        assert data["current_price"] == 155.0
        assert data["threshold"] == 150.0
    
    @pytest.mark.asyncio
    async def test_check_price_below(self, evaluator):
        condition = AlertCondition(
            type=AlertType.PRICE_BELOW,
            symbol="AAPL",
            parameters={"threshold": 150.0}
        )
        
        market_data = {
            "AAPL": {"price": 145.0, "last": 145.0}
        }
        
        triggered, data = await evaluator.evaluate_condition(condition, market_data)
        
        assert triggered is True
        assert data["current_price"] == 145.0
        assert data["threshold"] == 150.0
    
    @pytest.mark.asyncio
    async def test_check_price_below_not_triggered(self, evaluator):
        condition = AlertCondition(
            type=AlertType.PRICE_BELOW,
            symbol="AAPL",
            parameters={"threshold": 150.0}
        )
        
        market_data = {
            "AAPL": {"price": 155.0, "last": 155.0}
        }
        
        triggered, data = await evaluator.evaluate_condition(condition, market_data)
        
        assert triggered is False
    
    @pytest.mark.asyncio
    async def test_check_price_change_pct(self, evaluator):
        condition = AlertCondition(
            type=AlertType.PRICE_CHANGE_PCT,
            symbol="AAPL",
            parameters={"threshold_pct": 5.0, "period": "1d"}
        )
        
        market_data = {
            "AAPL": {"change_pct_1d": 7.5, "change_pct": 7.5}
        }
        
        triggered, data = await evaluator.evaluate_condition(condition, market_data)
        
        assert triggered is True
        assert data["change_pct"] == 7.5
        assert data["threshold"] == 5.0
    
    @pytest.mark.asyncio
    async def test_check_volume_spike(self, evaluator):
        condition = AlertCondition(
            type=AlertType.VOLUME_SPIKE,
            symbol="AAPL",
            parameters={"threshold": 3.0, "period": 20}
        )
        
        market_data = {
            "AAPL": {"volume": 15000000, "avg_volume_20": 3000000}
        }
        
        triggered, data = await evaluator.evaluate_condition(condition, market_data)
        
        assert triggered is True
        assert data["ratio"] == 5.0
        assert data["threshold"] == 3.0
    
    @pytest.mark.asyncio
    async def test_check_ma_cross_golden(self, evaluator):
        condition = AlertCondition(
            type=AlertType.MOVING_AVERAGE_CROSS,
            symbol="AAPL",
            parameters={
                "short_window": 50,
                "long_window": 200,
                "direction": "golden_cross"
            }
        )
        
        market_data = {
            "AAPL": {
                "sma_50": 155.0,
                "sma_200": 150.0,
                "prev_sma_50": 148.0,
                "prev_sma_200": 150.0
            }
        }
        
        triggered, data = await evaluator.evaluate_condition(condition, market_data)
        
        assert triggered is True
        assert data["cross_type"] == "golden_cross"
    
    @pytest.mark.asyncio
    async def test_check_ma_cross_death(self, evaluator):
        condition = AlertCondition(
            type=AlertType.MOVING_AVERAGE_CROSS,
            symbol="AAPL",
            parameters={
                "short_window": 50,
                "long_window": 200,
                "direction": "death_cross"
            }
        )
        
        market_data = {
            "AAPL": {
                "sma_50": 145.0,
                "sma_200": 150.0,
                "prev_sma_50": 152.0,
                "prev_sma_200": 150.0
            }
        }
        
        triggered, data = await evaluator.evaluate_condition(condition, market_data)
        
        assert triggered is True
        assert data["cross_type"] == "death_cross"
    
    @pytest.mark.asyncio
    async def test_check_rsi_overbought(self, evaluator):
        condition = AlertCondition(
            type=AlertType.RSI_OVERBOUGHT,
            symbol="AAPL",
            parameters={"threshold": 70}
        )
        
        market_data = {
            "AAPL": {"rsi": 75}
        }
        
        triggered, data = await evaluator.evaluate_condition(condition, market_data)
        
        assert triggered is True
        assert data["rsi"] == 75
        assert data["threshold"] == 70
    
    @pytest.mark.asyncio
    async def test_check_rsi_oversold(self, evaluator):
        condition = AlertCondition(
            type=AlertType.RSI_OVERSOLD,
            symbol="AAPL",
            parameters={"threshold": 30}
        )
        
        market_data = {
            "AAPL": {"rsi": 25}
        }
        
        triggered, data = await evaluator.evaluate_condition(condition, market_data)
        
        assert triggered is True
        assert data["rsi"] == 25
        assert data["threshold"] == 30
    
    @pytest.mark.asyncio
    async def test_check_bollinger_break(self, evaluator):
        condition = AlertCondition(
            type=AlertType.BOLLINGER_BAND_BREAK,
            symbol="AAPL",
            parameters={"direction": "upper"}
        )
        
        market_data = {
            "AAPL": {"price": 165.0, "bb_upper": 160.0, "bb_lower": 140.0}
        }
        
        triggered, data = await evaluator.evaluate_condition(condition, market_data)
        
        assert triggered is True
        assert data["price"] == 165.0
        assert data["upper_band"] == 160.0
        assert data["direction"] == "upper"
    
    @pytest.mark.asyncio
    async def test_check_macd_cross(self, evaluator):
        condition = AlertCondition(
            type=AlertType.MACD_CROSS,
            symbol="AAPL",
            parameters={"direction": "bullish"}
        )
        
        market_data = {
            "AAPL": {
                "macd": 2.5,
                "macd_signal": 2.0,
                "prev_macd": 1.8,
                "prev_macd_signal": 2.0
            }
        }
        
        triggered, data = await evaluator.evaluate_condition(condition, market_data)
        
        assert triggered is True
        assert data["cross_type"] == "bullish"
    
    @pytest.mark.asyncio
    async def test_check_earnings(self, evaluator):
        condition = AlertCondition(
            type=AlertType.EARNINGS_ANNOUNCEMENT,
            symbol="AAPL",
            parameters={"surprise_threshold": 5.0}
        )
        
        market_data = {
            "AAPL": {
                "earnings": {
                    "has_earnings": True,
                    "surprise_pct": 8.0
                }
            }
        }
        
        triggered, data = await evaluator.evaluate_condition(condition, market_data)
        
        assert triggered is True
        assert data["surprise_pct"] == 8.0
        assert data["surprise_threshold"] == 5.0


class TestAlertEngine:
    """Test AlertEngine."""
    
    @pytest.fixture
    def mock_backend(self):
        from unittest.mock import AsyncMock
        backend = AsyncMock()
        backend.get_rules = AsyncMock(return_value=[])
        backend.save_alert = AsyncMock()
        backend.get_alert = AsyncMock()
        backend.update_alert = AsyncMock()
        return backend
    
    @pytest.fixture
    def mock_evaluator(self):
        from unittest.mock import AsyncMock
        evaluator = AsyncMock()
        evaluator.evaluate_condition = AsyncMock(return_value=(False, {}))
        return evaluator
    
    @pytest.fixture
    def engine(self, mock_backend, mock_evaluator):
        return AlertEngine(backend=mock_backend, evaluator=mock_evaluator)
    
    @pytest.mark.asyncio
    async def test_add_rule(self, engine, mock_backend):
        rule = AlertRule(
            name="Test Rule",
            user_id="user123",
            conditions=[
                AlertCondition(
                    type=AlertType.PRICE_ABOVE,
                    symbol="AAPL",
                    parameters={"threshold": 150.0}
                )
            ],
            severity=AlertSeverity.INFO
        )
        
        rule_id = await engine.add_rule(rule)
        
        assert rule_id is not None
        assert rule_id in engine._rules_cache
        mock_backend.save_rule.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_evaluate_rules_no_trigger(self, engine, mock_evaluator):
        # Rule with condition that won't trigger
        rule = AlertRule(
            id="rule1",
            name="Test",
            user_id="user123",
            conditions=[
                AlertCondition(
                    type=AlertType.PRICE_ABOVE,
                    symbol="AAPL",
                    parameters={"threshold": 200.0}
                )
            ],
            enabled=True
        )
        engine._rules_cache["rule1"] = rule
        mock_evaluator.evaluate_condition.return_value = (False, {})
        
        market_data = {"AAPL": {"price": 150.0}}
        alerts = await engine.evaluate_rules(market_data)
        
        assert len(alerts) == 0
        mock_evaluator.evaluate_condition.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_evaluate_rules_with_trigger(self, engine, mock_evaluator, mock_backend):
        rule = AlertRule(
            id="rule1",
            name="Test",
            user_id="user123",
            portfolio_id="pf123",
            conditions=[
                AlertCondition(
                    type=AlertType.PRICE_ABOVE,
                    symbol="AAPL",
                    parameters={"threshold": 150.0}
                )
            ],
            logic="AND",
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.IN_APP],
            enabled=True
        )
        engine._rules_cache["rule1"] = rule
        
        # Mock evaluator to return triggered
        mock_evaluator.evaluate_condition.return_value = (True, {
            "current_price": 155.0,
            "threshold": 150.0
        })
        
        market_data = {"AAPL": {"price": 155.0}}
        alerts = await engine.evaluate_rules(market_data)
        
        assert len(alerts) == 1
        assert alerts[0].type == AlertType.PRICE_ABOVE
        assert alerts[0].symbol == "AAPL"
        assert alerts[0].severity == AlertSeverity.WARNING
        assert alerts[0].status == AlertStatus.ACTIVE
        mock_backend.save_alert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cooldown_respected(self, engine, mock_evaluator, mock_backend):
        rule = AlertRule(
            id="rule1",
            name="Test",
            user_id="user123",
            conditions=[
                AlertCondition(
                    type=AlertType.PRICE_ABOVE,
                    symbol="AAPL",
                    parameters={"threshold": 150.0}
                )
            ],
            logic="AND",
            cooldown_minutes=60,
            enabled=True
        )
        engine._rules_cache["rule1"] = rule
        
        # First evaluation - triggers
        mock_evaluator.evaluate_condition.return_value = (True, {"current_price": 155.0})
        alerts1 = await engine.evaluate_rules({"AAPL": {"price": 155.0}})
        assert len(alerts1) == 1
        
        # Second evaluation - should be in cooldown
        mock_evaluator.evaluate_condition.return_value = (True, {"current_price": 156.0})
        alerts2 = await engine.evaluate_rules({"AAPL": {"price": 156.0}})
        assert len(alerts2) == 0  # Cooldown active
    
    @pytest.mark.asyncio
    async def test_rate_limit_respected(self, engine, mock_evaluator, mock_backend):
        rule = AlertRule(
            id="rule1",
            name="Test",
            user_id="user123",
            conditions=[
                AlertCondition(
                    type=AlertType.PRICE_ABOVE,
                    symbol="AAPL",
                    parameters={"threshold": 150.0}
                )
            ],
            logic="AND",
            max_triggers_per_hour=2,
            cooldown_minutes=0,  # Disable cooldown for this test
            enabled=True
        )
        engine._rules_cache["rule1"] = rule
        
        mock_evaluator.evaluate_condition.return_value = (True, {"current_price": 155.0})
        
        # First two triggers
        alerts1 = await engine.evaluate_rules({"AAPL": {"price": 155.0}})
        alerts2 = await engine.evaluate_rules({"AAPL": {"price": 156.0}})
        
        # Third should be rate limited
        alerts3 = await engine.evaluate_rules({"AAPL": {"price": 157.0}})
        
        assert len(alerts1) == 1
        assert len(alerts2) == 1
        assert len(alerts3) == 0  # Rate limited


class TestDefaultAlertTemplates:
    """Test DEFAULT_ALERT_TEMPLATES."""
    
    def test_templates_exist(self):
        expected = [
            "price_above", "price_below", "ma_golden_cross", "ma_death_cross",
            "rsi_overbought", "rsi_oversold", "volume_spike", "bollinger_break",
            "macd_bullish", "macd_bearish", "earnings_alert"
        ]
        
        for template in expected:
            assert template in DEFAULT_ALERT_TEMPLATES
    
    def test_template_structure(self):
        template = DEFAULT_ALERT_TEMPLATES["ma_golden_cross"]
        
        assert "name" in template
        assert "type" in template
        assert "severity" in template
        assert "parameters" in template
        assert "message_template" in template
        assert template["type"] == AlertType.MOVING_AVERAGE_CROSS
        assert template["parameters"]["direction"] == "golden_cross"


class TestAlertBackend:
    """Test PostgresAlertBackend (requires database)."""
    
    @pytest.mark.skip(reason="Requires PostgreSQL database")
    @pytest.mark.asyncio
    async def test_backend_crud(self):
        backend = PostgresAlertBackend(dsn="postgresql://localhost/test", pool_size=5)
        await backend.connect()
        
        rule = AlertRule(
            name="Test Rule",
            user_id="user123",
            conditions=[
                AlertCondition(
                    type=AlertType.PRICE_ABOVE,
                    symbol="AAPL",
                    parameters={"threshold": 150.0}
                )
            ],
            severity=AlertSeverity.INFO
        )
        
        await backend.save_rule(rule)
        
        retrieved = await backend.get_rule(rule.id)
        assert retrieved is not None
        assert retrieved.name == "Test Rule"
        
        # Update
        rule.name = "Updated Rule"
        await backend.update_rule(rule)
        
        retrieved = await backend.get_rule(rule.id)
        assert retrieved.name == "Updated Rule"
        
        # Delete
        deleted = await backend.delete_rule(rule.id)
        assert deleted is True
        
        retrieved = await backend.get_rule(rule.id)
        assert retrieved is None
        
        await backend.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])