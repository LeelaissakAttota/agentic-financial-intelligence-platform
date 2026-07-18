"""
Phase 5 - Portfolio Management Tests
"""
import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from data.portfolio import (
    PortfolioManager, Portfolio, Position, Order, Transaction, PortfolioSnapshot,
    OrderSide, OrderType, OrderStatus, PositionSide, RebalanceStrategy,
    PostgresPortfolioBackend, create_portfolio_manager
)
from data.alerts import (
    AlertManager, AlertEvaluator,
    AlertRule, AlertCondition, AlertType, AlertSeverity, AlertChannel
)


class TestPortfolioDataclasses:
    """Test portfolio dataclasses."""

    def test_create_portfolio(self):
        portfolio = Portfolio(
            name="Test Portfolio",
            owner_id="user123",
            cash=Decimal("100000"),
            base_currency="USD"
        )
        assert portfolio.name == "Test Portfolio"
        assert portfolio.owner_id == "user123"
        assert portfolio.cash == Decimal("100000")
        assert portfolio.total_value == Decimal("100000")

    def test_create_position(self):
        position = Position(
            portfolio_id="pf123",
            symbol="AAPL",
            side=PositionSide.LONG,
            quantity=Decimal("100"),
            avg_cost=Decimal("150.00"),
            cost_basis=Decimal("15000"),
            market_value=Decimal("17500"),
            unrealized_pnl=Decimal("2500")
        )
        assert position.symbol == "AAPL"
        assert position.quantity == Decimal("100")
        assert position.unrealized_pnl == Decimal("2500")

    def test_create_order(self):
        order = Order(
            portfolio_id="pf123",
            symbol="MSFT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("50"),
            limit_price=Decimal("300.00")
        )
        assert order.symbol == "MSFT"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.LIMIT
        assert order.limit_price == Decimal("300.00")
        assert order.status == OrderStatus.PENDING

    def test_create_transaction(self):
        txn = Transaction(
            portfolio_id="pf123",
            order_id="ord123",
            symbol="GOOGL",
            side=OrderSide.BUY,
            quantity=Decimal("10"),
            price=Decimal("2500.00"),
            commission=Decimal("1.00")
        )
        assert txn.symbol == "GOOGL"
        assert txn.quantity == Decimal("10")
        assert txn.price == Decimal("2500.00")

    def test_create_snapshot(self):
        snapshot = PortfolioSnapshot(
            portfolio_id="pf123",
            total_value=Decimal("105000"),
            cash=Decimal("50000"),
            positions={"AAPL": {"quantity": 100, "value": 17500, "pnl": 2500}},
            daily_pnl=Decimal("500"),
            total_pnl=Decimal("5000")
        )
        assert snapshot.total_value == Decimal("105000")
        assert "AAPL" in snapshot.positions


class TestEnums:
    """Test enum values."""

    def test_order_side(self):
        assert OrderSide.BUY.value == "buy"
        assert OrderSide.SELL.value == "sell"

    def test_order_type(self):
        assert OrderType.MARKET.value == "market"
        assert OrderType.LIMIT.value == "limit"
        assert OrderType.STOP.value == "stop"
        assert OrderType.STOP_LIMIT.value == "stop_limit"

    def test_order_status(self):
        assert OrderStatus.PENDING.value == "pending"
        assert OrderStatus.FILLED.value == "filled"
        assert OrderStatus.CANCELLED.value == "cancelled"

    def test_position_side(self):
        assert PositionSide.LONG.value == "long"
        assert PositionSide.SHORT.value == "short"

    def test_rebalance_strategy(self):
        assert RebalanceStrategy.EQUAL_WEIGHT.value == "equal_weight"
        assert RebalanceStrategy.RISK_PARITY.value == "risk_parity"
        assert RebalanceStrategy.MAX_SHARPE.value == "max_sharpe"


class TestPortfolioManager:
    """Test PortfolioManager methods (mocked backend)."""

    @pytest.fixture
    def mock_backend(self):
        """Create a mock backend."""
        from unittest.mock import AsyncMock, MagicMock
        backend = AsyncMock()
        backend.connect = AsyncMock()
        backend.disconnect = AsyncMock()
        backend.save_portfolio = AsyncMock()
        backend.get_portfolio = AsyncMock()
        backend.delete_portfolio = AsyncMock(return_value=True)
        backend.list_portfolios = AsyncMock(return_value=[])
        backend.save_order = AsyncMock()
        backend.get_order = AsyncMock()
        backend.update_order = AsyncMock()
        backend.get_orders = AsyncMock(return_value=[])
        backend.save_transaction = AsyncMock()
        backend.get_transactions = AsyncMock(return_value=[])
        backend.save_snapshot = AsyncMock()
        backend.get_snapshots = AsyncMock(return_value=[])
        return backend

    @pytest.fixture
    def portfolio_manager(self, mock_backend):
        return PortfolioManager(backend=mock_backend)

    @pytest.mark.asyncio
    async def test_create_portfolio(self, portfolio_manager, mock_backend):
        portfolio = await portfolio_manager.create_portfolio(
            name="Test Portfolio",
            owner_id="user123",
            initial_cash=Decimal("50000")
        )

        assert portfolio.name == "Test Portfolio"
        assert portfolio.owner_id == "user123"
        assert portfolio.cash == Decimal("50000")
        mock_backend.save_portfolio.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_portfolio(self, portfolio_manager, mock_backend):
        # Setup mock return
        mock_portfolio = Portfolio(
            id="pf123",
            name="Test",
            owner_id="user123",
            cash=Decimal("10000")
        )
        mock_backend.get_portfolio.return_value = mock_portfolio

        portfolio = await portfolio_manager.get_portfolio("pf123")

        assert portfolio is not None
        assert portfolio.id == "pf123"
        assert portfolio.name == "Test"
        mock_backend.get_portfolio.assert_called_once_with("pf123")

    @pytest.mark.asyncio
    async def test_update_position_buy(self, portfolio_manager, mock_backend):
        # Setup mock portfolio with no existing position
        mock_portfolio = Portfolio(
            id="pf123",
            name="Test",
            owner_id="user123",
            cash=Decimal("10000")
        )
        mock_backend.get_portfolio.return_value = mock_portfolio

        # Update position - buy
        position = await portfolio_manager.update_position(
            portfolio_id="pf123",
            symbol="AAPL",
            quantity_change=Decimal("100"),
            price=Decimal("150.00"),
            side=OrderSide.BUY,
            commission=Decimal("1.00")
        )

        assert position.symbol == "AAPL"
        assert position.quantity == Decimal("100")
        assert position.side == PositionSide.LONG
        assert position.avg_cost == Decimal("150.01")
        mock_backend.save_portfolio.assert_called()

    @pytest.mark.asyncio
    async def test_update_position_sell_partial(self, portfolio_manager, mock_backend):
        # Setup mock portfolio with existing long position
        existing_position = Position(
            id="pos1",
            portfolio_id="pf123",
            symbol="AAPL",
            side=PositionSide.LONG,
            quantity=Decimal("100"),
            avg_cost=Decimal("150.00"),
            cost_basis=Decimal("15000"),
            market_value=Decimal("17500"),
            unrealized_pnl=Decimal("2500"),
            realized_pnl=Decimal("0"),
        )
        mock_portfolio = Portfolio(
            id="pf123",
            name="Test",
            owner_id="user123",
            cash=Decimal("10000")
        )
        mock_portfolio.add_position(existing_position)
        mock_backend.get_portfolio.return_value = mock_portfolio

        # Sell 50 shares
        position = await portfolio_manager.update_position(
            portfolio_id="pf123",
            symbol="AAPL",
            quantity_change=Decimal("50"),
            price=Decimal("180.00"),
            side=OrderSide.SELL,
            commission=Decimal("1.00")
        )

        assert position.quantity == Decimal("50")  # Remaining
        assert position.realized_pnl > Decimal("0")  # Profit realized
        mock_backend.save_portfolio.assert_called()

    @pytest.mark.asyncio
    async def test_place_order(self, portfolio_manager, mock_backend):
        order = await portfolio_manager.place_order(
            portfolio_id="pf123",
            symbol="MSFT",
            side=OrderSide.BUY,
            quantity=Decimal("50"),
            order_type=OrderType.LIMIT,
            limit_price=Decimal("300.00")
        )

        assert order.symbol == "MSFT"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.LIMIT
        assert order.limit_price == Decimal("300.00")
        mock_backend.save_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_fill_order(self, portfolio_manager, mock_backend):
        # Setup mock order
        mock_order = Order(
            id="ord123",
            portfolio_id="pf123",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100"),
            status=OrderStatus.SUBMITTED
        )
        mock_backend.get_order.return_value = mock_order

        # Mock portfolio for position update
        mock_portfolio = Portfolio(
            id="pf123",
            name="Test",
            owner_id="user123",
            cash=Decimal("10000")
        )
        mock_backend.get_portfolio.return_value = mock_portfolio

        filled_order, transaction = await portfolio_manager.fill_order(
            order_id="ord123",
            fill_price=Decimal("155.00"),
            fill_quantity=Decimal("100"),
            commission=Decimal("1.00")
        )

        assert filled_order.status == OrderStatus.FILLED
        assert filled_order.filled_quantity == Decimal("100")
        assert filled_order.avg_fill_price == Decimal("155.00")
        assert transaction.price == Decimal("155.00")
        assert transaction.quantity == Decimal("100")
        mock_backend.update_order.assert_called()
        mock_backend.save_transaction.assert_called()

    @pytest.mark.asyncio
    async def test_cancel_order(self, portfolio_manager, mock_backend):
        mock_order = Order(
            id="ord123",
            portfolio_id="pf123",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            status=OrderStatus.SUBMITTED
        )
        mock_backend.get_order.return_value = mock_order

        cancelled = await portfolio_manager.cancel_order("ord123")

        assert cancelled.status == OrderStatus.CANCELLED
        assert cancelled.cancelled_at is not None
        mock_backend.update_order.assert_called()

    @pytest.mark.asyncio
    async def test_take_snapshot(self, portfolio_manager, mock_backend):
        mock_portfolio = Portfolio(
            id="pf123",
            name="Test",
            owner_id="user123",
            cash=Decimal("10000")
        )
        mock_backend.get_portfolio.return_value = mock_portfolio

        snapshot = await portfolio_manager.take_snapshot("pf123")

        assert snapshot.portfolio_id == "pf123"
        assert snapshot.total_value == Decimal("10000")
        assert snapshot.cash == Decimal("10000")
        mock_backend.save_snapshot.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_exposure_analysis(self, portfolio_manager, mock_backend):
        mock_portfolio = Portfolio(
            id="pf123",
            name="Test",
            owner_id="user123",
            cash=Decimal("10000")
        )
        mock_backend.get_portfolio.return_value = mock_portfolio

        exposure = await portfolio_manager.get_exposure_analysis("pf123")

        assert exposure["total_positions"] == 0
        assert "allocations" in exposure
        assert "concentration" in exposure

    @pytest.mark.asyncio
    async def test_calculate_risk_metrics(self, portfolio_manager, mock_backend):
        # Need snapshots for risk metrics
        from data.portfolio import PortfolioSnapshot
        mock_snapshots = [
            PortfolioSnapshot(
                portfolio_id="pf123",
                timestamp=datetime.now(),
                total_value=Decimal("10000"),
                cash=Decimal("10000"),
                positions={},
                daily_pnl=Decimal("0"),
                total_pnl=Decimal("0")
            )
            for _ in range(10)
        ]
        # Vary values slightly
        for i, s in enumerate(mock_snapshots):
            s.total_value = Decimal(str(10000 + i * 100 - 500))
            s.total_pnl = Decimal(str(i * 100 - 500))

        mock_backend.get_snapshots.return_value = mock_snapshots

        metrics = await portfolio_manager.calculate_risk_metrics("pf123")

        assert "var_95" in metrics
        assert "var_99" in metrics
        assert "volatility" in metrics
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics


class TestPortfolioBackend:
    """Test PostgresPortfolioBackend (requires database)."""

    @pytest.mark.asyncio
    async def test_backend_crud(self):
        import os
        db_name = os.getenv("POSTGRES_DB", "financial_research_agent")
        db_user = os.getenv("POSTGRES_USER", "postgres")
        db_pass = os.getenv("POSTGRES_PASSWORD", "postgres")
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        
        dsn = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        backend = PostgresPortfolioBackend(dsn=dsn, pool_size=5)
        await backend.connect()

        # Create portfolio
        portfolio = Portfolio(
            name="Test Portfolio",
            owner_id="user123",
            cash=Decimal("10000")
        )
        await backend.save_portfolio(portfolio)

        # Retrieve
        retrieved = await backend.get_portfolio(portfolio.id)
        assert retrieved is not None
        assert retrieved.name == "Test Portfolio"

        # List
        portfolios = await backend.list_portfolios(owner_id="user123")
        assert len(portfolios) >= 1

        # Delete
        deleted = await backend.delete_portfolio(portfolio.id)
        assert deleted is True

        await backend.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])