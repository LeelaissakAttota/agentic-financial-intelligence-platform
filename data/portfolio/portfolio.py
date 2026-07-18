"""
Portfolio Management Module - Phase 5

Manages portfolio construction, optimization, tracking, and analytics.
"""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

import asyncpg
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PositionSide(str, Enum):
    LONG = "long"
    SHORT = "short"


class RebalanceStrategy(str, Enum):
    EQUAL_WEIGHT = "equal_weight"
    MARKET_CAP = "market_cap"
    RISK_PARITY = "risk_parity"
    MINIMUM_VARIANCE = "minimum_variance"
    MAX_SHARPE = "max_sharpe"
    CUSTOM = "custom"


@dataclass
class Order:
    """A trade order."""
    id: str = field(default_factory=lambda: str(uuid4()))
    portfolio_id: str = ""
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: Decimal = Decimal("0")
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = Decimal("0")
    avg_fill_price: Optional[Decimal] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    commission: Decimal = Decimal("0")
    metadata: dict = field(default_factory=dict)


@dataclass
class Position:
    """A portfolio position."""
    id: str = field(default_factory=lambda: str(uuid4()))
    portfolio_id: str = ""
    symbol: str = ""
    side: PositionSide = PositionSide.LONG
    quantity: Decimal = Decimal("0")
    avg_cost: Decimal = Decimal("0")
    market_value: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    cost_basis: Decimal = Decimal("0")
    first_acquired: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)


@dataclass
class Portfolio:
    """A portfolio with positions and cash."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    owner_id: str = ""
    cash: Decimal = Decimal("0")
    base_currency: str = "USD"
    positions: dict[str, Position] = field(default_factory=dict)
    total_value: Decimal = field(init=False)
    total_cost: Decimal = Decimal("0")
    total_pnl: Decimal = Decimal("0")
    daily_pnl: Decimal = Decimal("0")
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        self.total_value = self.cash
        self.recalculate_totals()
    
    def add_position(self, position: Position) -> None:
        self.positions[position.symbol] = position
    
    def remove_position(self, symbol: str) -> Optional[Position]:
        return self.positions.pop(symbol, None)
    
    def get_position(self, symbol: str) -> Optional[Position]:
        return self.positions.get(symbol)
    
    def recalculate_totals(self) -> None:
        """Recalculate portfolio totals from positions."""
        self.total_value = self.cash
        self.total_cost = Decimal("0")
        self.total_pnl = Decimal("0")
        
        for position in self.positions.values():
            self.total_value += position.market_value
            self.total_cost += position.cost_basis
            self.total_pnl += position.unrealized_pnl + position.realized_pnl
        
        self.updated_at = datetime.utcnow()


@dataclass
class Transaction:
    """A completed transaction."""
    id: str = field(default_factory=lambda: str(uuid4()))
    portfolio_id: str = ""
    order_id: str = ""
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    quantity: Decimal = Decimal("0")
    price: Decimal = Decimal("0")
    commission: Decimal = Decimal("0")
    fees: Decimal = Decimal("0")
    executed_at: datetime = field(default_factory=datetime.utcnow)
    settlement_date: Optional[date] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class PortfolioSnapshot:
    """A snapshot of portfolio state at a point in time."""
    id: str = field(default_factory=lambda: str(uuid4()))
    portfolio_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    total_value: Decimal = Decimal("0")
    cash: Decimal = Decimal("0")
    positions: dict = field(default_factory=dict)  # symbol -> {quantity, value, pnl}
    daily_pnl: Decimal = Decimal("0")
    total_pnl: Decimal = Decimal("0")


class PortfolioBackend(ABC):
    """Abstract portfolio storage backend."""
    
    @abstractmethod
    async def save_portfolio(self, portfolio: Portfolio) -> None:
        pass
    
    @abstractmethod
    async def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        pass
    
    @abstractmethod
    async def delete_portfolio(self, portfolio_id: str) -> bool:
        pass
    
    @abstractmethod
    async def list_portfolios(self, owner_id: str = None) -> list[Portfolio]:
        pass
    
    @abstractmethod
    async def save_order(self, order: Order) -> None:
        pass
    
    @abstractmethod
    async def get_order(self, order_id: str) -> Optional[Order]:
        pass
    
    @abstractmethod
    async def update_order(self, order: Order) -> None:
        pass
    
    @abstractmethod
    async def get_orders(self, portfolio_id: str, status: OrderStatus = None) -> list[Order]:
        pass
    
    @abstractmethod
    async def save_transaction(self, transaction: Transaction) -> None:
        pass
    
    @abstractmethod
    async def get_transactions(
        self, 
        portfolio_id: str, 
        start_date: date = None, 
        end_date: date = None
    ) -> list[Transaction]:
        pass
    
    @abstractmethod
    async def save_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        pass
    
    @abstractmethod
    async def get_snapshots(
        self, 
        portfolio_id: str, 
        start_date: date = None, 
        end_date: date = None
    ) -> list[PortfolioSnapshot]:
        pass


class PostgresPortfolioBackend(PortfolioBackend):
    """PostgreSQL backend for portfolio storage."""
    
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
                CREATE TABLE IF NOT EXISTS portfolios (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    cash NUMERIC(20, 8) NOT NULL DEFAULT 0,
                    base_currency TEXT NOT NULL DEFAULT 'USD',
                    total_value NUMERIC(20, 8) NOT NULL DEFAULT 0,
                    total_cost NUMERIC(20, 8) NOT NULL DEFAULT 0,
                    total_pnl NUMERIC(20, 8) NOT NULL DEFAULT 0,
                    daily_pnl NUMERIC(20, 8) NOT NULL DEFAULT 0,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_portfolios_owner ON portfolios(owner_id);
                
                CREATE TABLE IF NOT EXISTS positions (
                    id TEXT PRIMARY KEY,
                    portfolio_id TEXT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity NUMERIC(20, 8) NOT NULL DEFAULT 0,
                    avg_cost NUMERIC(20, 8) NOT NULL DEFAULT 0,
                    market_value NUMERIC(20, 8) NOT NULL DEFAULT 0,
                    unrealized_pnl NUMERIC(20, 8) NOT NULL DEFAULT 0,
                    realized_pnl NUMERIC(20, 8) NOT NULL DEFAULT 0,
                    cost_basis NUMERIC(20, 8) NOT NULL DEFAULT 0,
                    first_acquired TIMESTAMPTZ,
                    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}',
                    UNIQUE(portfolio_id, symbol)
                );
                
                CREATE INDEX IF NOT EXISTS idx_positions_portfolio ON positions(portfolio_id);
                
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    portfolio_id TEXT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    order_type TEXT NOT NULL,
                    quantity NUMERIC(20, 8) NOT NULL DEFAULT 0,
                    limit_price NUMERIC(20, 8),
                    stop_price NUMERIC(20, 8),
                    status TEXT NOT NULL DEFAULT 'pending',
                    filled_quantity NUMERIC(20, 8) NOT NULL DEFAULT 0,
                    avg_fill_price NUMERIC(20, 8),
                    commission NUMERIC(20, 8) NOT NULL DEFAULT 0,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    submitted_at TIMESTAMPTZ,
                    filled_at TIMESTAMPTZ,
                    cancelled_at TIMESTAMPTZ
                );
                
                CREATE INDEX IF NOT EXISTS idx_orders_portfolio ON orders(portfolio_id);
                CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
                CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
                
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    portfolio_id TEXT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
                    order_id TEXT REFERENCES orders(id),
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity NUMERIC(20, 8) NOT NULL,
                    price NUMERIC(20, 8) NOT NULL,
                    commission NUMERIC(20, 8) NOT NULL DEFAULT 0,
                    fees NUMERIC(20, 8) NOT NULL DEFAULT 0,
                    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    settlement_date DATE,
                    metadata JSONB DEFAULT '{}'
                );
                
                CREATE INDEX IF NOT EXISTS idx_transactions_portfolio ON transactions(portfolio_id);
                CREATE INDEX IF NOT EXISTS idx_transactions_executed ON transactions(executed_at);
                CREATE INDEX IF NOT EXISTS idx_transactions_symbol ON transactions(symbol);
                
                CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                    id TEXT PRIMARY KEY,
                    portfolio_id TEXT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    total_value NUMERIC(20, 8) NOT NULL,
                    cash NUMERIC(20, 8) NOT NULL,
                    positions JSONB NOT NULL DEFAULT '{}',
                    daily_pnl NUMERIC(20, 8) NOT NULL DEFAULT 0,
                    total_pnl NUMERIC(20, 8) NOT NULL DEFAULT 0
                );
                
                CREATE INDEX IF NOT EXISTS idx_snapshots_portfolio ON portfolio_snapshots(portfolio_id);
                CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON portfolio_snapshots(timestamp);
                
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    portfolio_id TEXT REFERENCES portfolios(id) ON DELETE CASCADE,
                    symbol TEXT,
                    alert_type TEXT NOT NULL,
                    condition JSONB NOT NULL,
                    message TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'info',
                    triggered BOOLEAN NOT NULL DEFAULT FALSE,
                    triggered_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                );
                
                CREATE INDEX IF NOT EXISTS idx_alerts_portfolio ON alerts(portfolio_id);
                CREATE INDEX IF NOT EXISTS idx_alerts_triggered ON alerts(triggered);
            """)
    
    async def save_portfolio(self, portfolio: Portfolio) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO portfolios (id, name, owner_id, cash, base_currency, total_value, total_cost, total_pnl, daily_pnl, metadata, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    cash = EXCLUDED.cash,
                    base_currency = EXCLUDED.base_currency,
                    total_value = EXCLUDED.total_value,
                    total_cost = EXCLUDED.total_cost,
                    total_pnl = EXCLUDED.total_pnl,
                    daily_pnl = EXCLUDED.daily_pnl,
                    metadata = EXCLUDED.metadata,
                    updated_at = EXCLUDED.updated_at
            """, portfolio.id, portfolio.name, portfolio.owner_id, portfolio.cash,
               portfolio.base_currency, portfolio.total_value, portfolio.total_cost,
               portfolio.total_pnl, portfolio.daily_pnl, json.dumps(portfolio.metadata),
               portfolio.created_at, portfolio.updated_at)
            
            # Save positions
            for position in portfolio.positions.values():
                await conn.execute("""
                    INSERT INTO positions (id, portfolio_id, symbol, side, quantity, avg_cost, market_value, 
                                          unrealized_pnl, realized_pnl, cost_basis, first_acquired, last_updated, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    ON CONFLICT (portfolio_id, symbol) DO UPDATE SET
                        side = EXCLUDED.side,
                        quantity = EXCLUDED.quantity,
                        avg_cost = EXCLUDED.avg_cost,
                        market_value = EXCLUDED.market_value,
                        unrealized_pnl = EXCLUDED.unrealized_pnl,
                        realized_pnl = EXCLUDED.realized_pnl,
                        cost_basis = EXCLUDED.cost_basis,
                        first_acquired = COALESCE(positions.first_acquired, EXCLUDED.first_acquired),
                        last_updated = EXCLUDED.last_updated,
                        metadata = EXCLUDED.metadata
                """, position.id, position.portfolio_id, position.symbol, position.side.value,
                   position.quantity, position.avg_cost, position.market_value,
                   position.unrealized_pnl, position.realized_pnl, position.cost_basis,
                   position.first_acquired, position.last_updated, json.dumps(position.metadata))
    
    async def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM portfolios WHERE id = $1", portfolio_id
            )
            if not row:
                return None
            
            portfolio = Portfolio(
                id=row["id"],
                name=row["name"],
                owner_id=row["owner_id"],
                cash=row["cash"],
                base_currency=row["base_currency"],
                total_value=row["total_value"],
                total_cost=row["total_cost"],
                total_pnl=row["total_pnl"],
                daily_pnl=row["daily_pnl"],
                metadata=row["metadata"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            
            # Load positions
            positions_rows = await conn.fetch(
                "SELECT * FROM positions WHERE portfolio_id = $1", portfolio_id
            )
            for row in rows:
                position = Position(
                    id=row["id"],
                    portfolio_id=row["portfolio_id"],
                    symbol=row["symbol"],
                    side=PositionSide(row["side"]),
                    quantity=row["quantity"],
                    avg_cost=row["avg_cost"],
                    market_value=row["market_value"],
                    unrealized_pnl=row["unrealized_pnl"],
                    realized_pnl=row["realized_pnl"],
                    cost_basis=row["cost_basis"],
                    first_acquired=row["first_acquired"],
                    last_updated=row["last_updated"],
                    metadata=row["metadata"]
                )
                portfolio.add_position(position)
            
            return portfolio
    
    async def delete_portfolio(self, portfolio_id: str) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM portfolios WHERE id = $1", portfolio_id)
            return result != "DELETE 0"
    
    async def list_portfolios(self, owner_id: str = None) -> list[Portfolio]:
        async with self.pool.acquire() as conn:
            if owner_id:
                rows = await conn.fetch(
                    "SELECT id FROM portfolios WHERE owner_id = $1 ORDER BY created_at DESC", owner_id
                )
            else:
                rows = await conn.fetch(
                    "SELECT id FROM portfolios ORDER BY created_at DESC"
                )
            
            portfolios = []
            for row in rows:
                portfolio = await self.get_portfolio(row["id"])
                if portfolio:
                    portfolios.append(portfolio)
            return portfolios
    
    async def save_order(self, order: Order) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO orders (id, portfolio_id, symbol, side, order_type, quantity, limit_price, stop_price,
                                   status, filled_quantity, avg_fill_price, commission, metadata, created_at, submitted_at, filled_at, cancelled_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    filled_quantity = EXCLUDED.filled_quantity,
                    avg_fill_price = EXCLUDED.avg_fill_price,
                    commission = EXCLUDED.commission,
                    submitted_at = EXCLUDED.submitted_at,
                    filled_at = EXCLUDED.filled_at,
                    cancelled_at = EXCLUDED.cancelled_at
            """, order.id, order.portfolio_id, order.symbol, order.side.value,
               order.order_type.value, order.quantity, order.limit_price, order.stop_price,
               order.status.value, order.filled_quantity, order.avg_fill_price,
               order.commission, json.dumps(order.metadata), order.created_at,
               order.submitted_at, order.filled_at, order.cancelled_at)
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
            if not row:
                return None
            return Order(
                id=row["id"],
                portfolio_id=row["portfolio_id"],
                symbol=row["symbol"],
                side=OrderSide(row["side"]),
                order_type=OrderType(row["order_type"]),
                quantity=row["quantity"],
                limit_price=row["limit_price"],
                stop_price=row["stop_price"],
                status=OrderStatus(row["status"]),
                filled_quantity=row["filled_quantity"],
                avg_fill_price=row["avg_fill_price"],
                commission=row["commission"],
                metadata=row["metadata"],
                created_at=row["created_at"],
                submitted_at=row["submitted_at"],
                filled_at=row["filled_at"],
                cancelled_at=row["cancelled_at"]
            )
    
    async def update_order(self, order: Order) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE orders SET
                    status = $2,
                    filled_quantity = $3,
                    avg_fill_price = $4,
                    commission = $5,
                    submitted_at = $6,
                    filled_at = $7,
                    cancelled_at = $8,
                    metadata = $9
                WHERE id = $1
            """, order.id, order.status.value, order.filled_quantity, order.avg_fill_price,
               order.commission, order.submitted_at, order.filled_at, order.cancelled_at,
               json.dumps(order.metadata))
    
    async def get_orders(self, portfolio_id: str, status: OrderStatus = None) -> list[Order]:
        async with self.pool.acquire() as conn:
            if status:
                rows = await conn.fetch(
                    "SELECT * FROM orders WHERE portfolio_id = $1 AND status = $2 ORDER BY created_at DESC",
                    portfolio_id, status.value
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM orders WHERE portfolio_id = $1 ORDER BY created_at DESC",
                    portfolio_id
                )
            
            return [
                Order(
                    id=row["id"],
                    portfolio_id=row["portfolio_id"],
                    symbol=row["symbol"],
                    side=OrderSide(row["side"]),
                    order_type=OrderType(row["order_type"]),
                    quantity=row["quantity"],
                    limit_price=row["limit_price"],
                    stop_price=row["stop_price"],
                    status=OrderStatus(row["status"]),
                    filled_quantity=row["filled_quantity"],
                    avg_fill_price=row["avg_fill_price"],
                    commission=row["commission"],
                    metadata=row["metadata"],
                    created_at=row["created_at"],
                    submitted_at=row["submitted_at"],
                    filled_at=row["filled_at"],
                    cancelled_at=row["cancelled_at"]
                )
                for row in rows
            ]
    
    async def save_transaction(self, transaction: Transaction) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO transactions (id, portfolio_id, order_id, symbol, side, quantity, price, commission, fees, executed_at, settlement_date, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """, transaction.id, transaction.portfolio_id, transaction.order_id, transaction.symbol,
               transaction.side.value, transaction.quantity, transaction.price,
               transaction.commission, transaction.fees, transaction.executed_at,
               transaction.settlement_date, json.dumps(transaction.metadata))
    
    async def get_transactions(
        self, 
        portfolio_id: str, 
        start_date: date = None, 
        end_date: date = None
    ) -> list[Transaction]:
        async with self.pool.acquire() as conn:
            conditions = ["portfolio_id = $1"]
            params = [portfolio_id]
            param_idx = 2
            
            if start_date:
                params.append(start_date)
                conditions.append(f"executed_at >= ${len(params)}")
            if end_date:
                params.append(end_date)
                conditions.append(f"executed_at <= ${len(params)}")
            
            query = f"""
                SELECT * FROM transactions 
                WHERE {' AND '.join(conditions)}
                ORDER BY executed_at DESC
            """
            rows = await conn.fetch(query, *params)
            
            return [
                Transaction(
                    id=row["id"],
                    portfolio_id=row["portfolio_id"],
                    order_id=row["order_id"],
                    symbol=row["symbol"],
                    side=OrderSide(row["side"]),
                    quantity=row["quantity"],
                    price=row["price"],
                    commission=row["commission"],
                    fees=row["fees"],
                    executed_at=row["executed_at"],
                    settlement_date=row["settlement_date"],
                    metadata=row["metadata"]
                )
                for row in rows
            ]
    
    async def save_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO portfolio_snapshots (id, portfolio_id, timestamp, total_value, cash, positions, daily_pnl, total_pnl)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, snapshot.id, snapshot.portfolio_id, snapshot.timestamp, snapshot.total_value,
               snapshot.cash, json.dumps(snapshot.positions), snapshot.daily_pnl, snapshot.total_pnl)
    
    async def get_snapshots(
        self, 
        portfolio_id: str, 
        start_date: date = None, 
        end_date: date = None
    ) -> list[PortfolioSnapshot]:
        async with self.pool.acquire() as conn:
            conditions = ["portfolio_id = $1"]
            params = [portfolio_id]
            param_idx = 2
            
            if start_date:
                params.append(start_date)
                conditions.append(f"timestamp >= ${len(params)}")
            if end_date:
                params.append(end_date)
                conditions.append(f"timestamp <= ${len(params)}")
            
            query = f"""
                SELECT * FROM portfolio_snapshots 
                WHERE {' AND '.join(conditions)}
                ORDER BY timestamp DESC
            """
            rows = await conn.fetch(query, *params)
            
            return [
                PortfolioSnapshot(
                    id=row["id"],
                    portfolio_id=row["portfolio_id"],
                    timestamp=row["timestamp"],
                    total_value=row["total_value"],
                    cash=row["cash"],
                    positions=row["positions"],
                    daily_pnl=row["daily_pnl"],
                    total_pnl=row["total_pnl"]
                )
                for row in rows
            ]


class PortfolioManager:
    """
    High-level portfolio management service.
    Handles portfolio operations, order management, position tracking, and analytics.
    """
    
    def __init__(
        self,
        backend: PortfolioBackend,
        market_data_provider=None,
        risk_engine=None
    ):
        self.backend = backend
        self.market_data = market_data_provider
        self.risk_engine = risk_engine
    
    async def initialize(self) -> None:
        await self.backend.connect()
    
    async def close(self) -> None:
        await self.backend.disconnect()
    
    # Portfolio CRUD
    async def create_portfolio(
        self,
        name: str,
        owner_id: str,
        initial_cash: Decimal = Decimal("0"),
        base_currency: str = "USD"
    ) -> Portfolio:
        portfolio = Portfolio(
            name=name,
            owner_id=owner_id,
            cash=initial_cash,
            base_currency=base_currency
        )
        await self.backend.save_portfolio(portfolio)
        return portfolio
    
    async def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        return await self.backend.get_portfolio(portfolio_id)
    
    async def delete_portfolio(self, portfolio_id: str) -> bool:
        return await self.backend.delete_portfolio(portfolio_id)
    
    async def list_portfolios(self, owner_id: str = None) -> list[Portfolio]:
        return await self.backend.list_portfolios(owner_id)
    
    # Position management
    async def update_position(
        self,
        portfolio_id: str,
        symbol: str,
        quantity_change: Decimal,
        price: Decimal,
        side: OrderSide,
        commission: Decimal = Decimal("0")
    ) -> Position:
        """Update a position after a trade."""
        portfolio = await self.get_portfolio(portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        
        position = portfolio.get_position(symbol)
        
        if position is None:
            # New position
            if side == OrderSide.SELL:
                # Short position
                position = Position(
                    portfolio_id=portfolio_id,
                    symbol=symbol,
                    side=PositionSide.SHORT,
                    quantity=abs(quantity_change),
                    avg_cost=price,
                    cost_basis=abs(quantity_change) * price + commission,
                    market_value=abs(quantity_change) * price,
                    unrealized_pnl=Decimal("0")
                )
            else:
                # Long position
                position = Position(
                    portfolio_id=portfolio_id,
                    symbol=symbol,
                    side=PositionSide.LONG,
                    quantity=quantity_change,
                    avg_cost=(quantity_change * price + commission) / quantity_change if quantity_change > 0 else price,
                    cost_basis=quantity_change * price + commission,
                    market_value=quantity_change * price,
                    unrealized_pnl=Decimal("0"),
                    first_acquired=datetime.utcnow()
                )
        else:
            # Update existing position
            if side == OrderSide.BUY:
                if position.side == PositionSide.LONG:
                    # Add to long position
                    new_quantity = position.quantity + quantity_change
                    new_cost = position.cost_basis + quantity_change * price + commission
                    position.quantity = new_quantity
                    position.cost_basis = new_cost
                    position.avg_cost = new_cost / new_quantity if new_quantity > 0 else Decimal("0")
                    position.quantity = new_quantity
                elif position.side == PositionSide.SHORT:
                    # Cover short position
                    if quantity_change >= position.quantity:
                        # Fully cover and go long
                        remaining = quantity_change - position.quantity
                        realized_pnl = position.quantity * (position.avg_cost - price) - commission
                        position.side = PositionSide.LONG
                        position.quantity = remaining
                        position.avg_cost = price
                        position.cost_basis = remaining * price + commission
                        position.realized_pnl += realized_pnl
                    else:
                        # Partially cover
                        realized_pnl = quantity_change * (position.avg_cost - price) - commission
                        position.quantity -= quantity_change
                        position.realized_pnl += realized_pnl
            else:  # SELL
                if position.side == PositionSide.LONG:
                    # Reduce long position
                    if quantity_change >= position.quantity:
                        # Fully close
                        realized_pnl = position.quantity * (price - position.avg_cost) - commission
                        position.realized_pnl += realized_pnl
                        position.quantity = Decimal("0")
                        position.cost_basis = Decimal("0")
                        position.avg_cost = Decimal("0")
                    else:
                        # Partially close
                        realized_pnl = quantity_change * (price - position.avg_cost) - commission
                        position.quantity -= quantity_change
                        position.cost_basis -= quantity_change * position.avg_cost
                        position.realized_pnl += realized_pnl
                elif position.side == PositionSide.SHORT:
                    # Add to short position
                    new_quantity = position.quantity + quantity_change
                    new_cost = position.cost_basis + quantity_change * price + commission
                    position.quantity = new_quantity
                    position.cost_basis = new_cost
                    position.avg_cost = new_cost / new_quantity if new_quantity > 0 else Decimal("0")
        
        # Update market value
        if position.quantity > 0:
            if position.side == PositionSide.LONG:
                position.market_value = position.quantity * price
                position.unrealized_pnl = position.quantity * (price - position.avg_cost)
            else:  # SHORT
                position.market_value = position.quantity * price
                position.unrealized_pnl = position.quantity * (position.avg_cost - price)
        else:
            position.market_value = Decimal("0")
            position.unrealized_pnl = Decimal("0")
            # Remove if fully closed
            portfolio.remove_position(symbol)
        
        position.last_updated = datetime.utcnow()
        portfolio.add_position(position)
        portfolio.recalculate_totals()
        
        await self.backend.save_portfolio(portfolio)
        return position
    
    # Order management
    async def place_order(
        self,
        portfolio_id: str,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None
    ) -> Order:
        order = Order(
            portfolio_id=portfolio_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price
        )
        await self.backend.save_order(order)
        return order
    
    async def submit_order(self, order_id: str) -> Order:
        order = await self.backend.get_order(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        order.status = OrderStatus.SUBMITTED
        order.submitted_at = datetime.utcnow()
        await self.backend.update_order(order)
        return order
    
    async def cancel_order(self, order_id: str) -> Order:
        order = await self.backend.get_order(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.status not in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
            raise ValueError(f"Cannot cancel order in status {order.status}")
        
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.utcnow()
        await self.backend.update_order(order)
        return order
    
    async def fill_order(
        self,
        order_id: str,
        fill_price: Decimal,
        fill_quantity: Decimal,
        commission: Decimal = Decimal("0")
    ) -> tuple[Order, Transaction]:
        order = await self.backend.get_order(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.status not in [OrderStatus.SUBMITTED, OrderStatus.PARTIAL_FILL]:
            raise ValueError(f"Cannot fill order in status {order.status}")
        
        # Update order
        order.filled_quantity += fill_quantity
        order.avg_fill_price = (
            (order.avg_fill_price or Decimal("0")) * (order.filled_quantity - fill_quantity) +
            fill_price * fill_quantity
        ) / order.filled_quantity
        order.commission += commission
        
        if order.filled_quantity >= order.quantity:
            order.status = OrderStatus.FILLED
            order.filled_at = datetime.utcnow()
        else:
            order.status = OrderStatus.PARTIAL_FILL
        
        await self.backend.update_order(order)
        
        # Create transaction
        transaction = Transaction(
            portfolio_id=order.portfolio_id,
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=fill_quantity,
            price=fill_price,
            commission=commission,
            fees=Decimal("0"),
            executed_at=datetime.utcnow()
        )
        
        await self.backend.save_transaction(transaction)
        
        # Update position
        await self.update_position(
            order.portfolio_id,
            order.symbol,
            fill_quantity if order.side == OrderSide.BUY else -fill_quantity,
            fill_price,
            order.side,
            commission
        )
        
        return order, transaction
    
    async def get_orders(self, portfolio_id: str, status: OrderStatus = None) -> list[Order]:
        return await self.backend.get_orders(portfolio_id, status)
    
    # Analytics
    async def get_portfolio_performance(
        self,
        portfolio_id: str,
        start_date: date,
        end_date: date
    ) -> dict:
        """Get portfolio performance metrics for a period."""
        snapshots = await self.backend.get_snapshots(portfolio_id, start_date, end_date)
        
        if not snapshots:
            return {}
        
        # Calculate returns
        first = snapshots[-1]  # oldest
        last = snapshots[0]    # newest
        
        total_return = (last.total_value - first.total_value) / first.total_value if first.total_value > 0 else Decimal("0")
        
        # Calculate daily returns
        daily_returns = []
        for i in range(len(snapshots) - 1):
            curr = snapshots[i]
            prev = snapshots[i + 1]
            if prev.total_value > 0:
                daily_ret = (curr.total_value - prev.total_value) / prev.total_value
                daily_returns.append(daily_ret)
        
        daily_returns = np.array([float(r) for r in daily_returns])
        
        return {
            "total_return": float(total_return),
            "annualized_return": float(total_return * 252 / len(snapshots)) if len(snapshots) > 1 else 0,
            "volatility": float(np.std(daily_returns) * np.sqrt(252)) if len(daily_returns) > 1 else 0,
            "sharpe_ratio": float(np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)) if len(daily_returns) > 1 and np.std(daily_returns) > 0 else 0,
            "max_drawdown": float(self._calculate_max_drawdown(snapshots)),
            "start_value": float(first.total_value),
            "end_value": float(last.total_value),
            "period_days": (end_date - start_date).days
        }
    
    def _calculate_max_drawdown(self, snapshots: list[PortfolioSnapshot]) -> Decimal:
        peak = Decimal("0")
        max_dd = Decimal("0")
        
        for snap in snapshots:
            if snap.total_value > peak:
                peak = snap.total_value
            if peak > 0:
                dd = (peak - snap.total_value) / peak
                if dd > max_dd:
                    max_dd = dd
        
        return max_dd
    
    async def take_snapshot(self, portfolio_id: str) -> PortfolioSnapshot:
        """Take a snapshot of current portfolio state."""
        portfolio = await self.get_portfolio(portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        
        positions = {}
        for symbol, pos in portfolio.positions.items():
            positions[symbol] = {
                "quantity": float(pos.quantity),
                "value": float(pos.market_value),
                "pnl": float(pos.unrealized_pnl + pos.realized_pnl)
            }
        
        snapshot = PortfolioSnapshot(
            portfolio_id=portfolio_id,
            total_value=portfolio.total_value,
            cash=portfolio.cash,
            positions=positions,
            daily_pnl=portfolio.daily_pnl,
            total_pnl=portfolio.total_pnl
        )
        
        await self.backend.save_snapshot(snapshot)
        return snapshot
    
    async def get_snapshots(
        self,
        portfolio_id: str,
        start_date: date = None,
        end_date: date = None
    ) -> list[PortfolioSnapshot]:
        return await self.backend.get_snapshots(portfolio_id, start_date, end_date)
    
    # Rebalancing
    async def rebalance(
        self,
        portfolio_id: str,
        target_weights: dict[str, Decimal],
        strategy: RebalanceStrategy = RebalanceStrategy.EQUAL_WEIGHT,
        tolerance: Decimal = Decimal("0.01")
    ) -> list[Order]:
        """Rebalance portfolio to target weights."""
        portfolio = await self.get_portfolio(portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        
        # Calculate target allocations
        total_value = portfolio.total_value
        target_allocations = {
            symbol: total_value * weight for symbol, weight in target_weights.items()
        }
        
        # Calculate current allocations
        current_allocations = {
            symbol: pos.market_value for symbol, pos in portfolio.positions.items()
        }
        
        # Determine trades needed
        orders = []
        for symbol, target_value in target_allocations.items():
            current_value = current_allocations.get(symbol, Decimal("0"))
            diff = target_value - current_value
            
            if abs(diff) > total_value * tolerance:
                # Need to trade
                if diff > 0:
                    # Buy
                    # Would need current price to calculate quantity
                    pass
                else:
                    # Sell
                    pass
        
        return orders
    
    async def calculate_risk_metrics(self, portfolio_id: str) -> dict:
        """Calculate portfolio risk metrics."""
        portfolio = await self.get_portfolio(portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        
        # Get snapshots for risk calculations
        end_date = date.today()
        start_date = end_date - timedelta(days=252)  # 1 year
        snapshots = await self.backend.get_snapshots(portfolio_id, start_date, end_date)
        
        if len(snapshots) < 2:
            return {}
        
        # Calculate returns
        values = [float(s.total_value) for s in snapshots]
        returns = np.diff(values) / values[:-1]
        
        # Risk-free rate assumption
        risk_free_rate = 0.02  # 2% annual
        
        # Calculate max drawdown
        peak = values[0]
        max_dd = 0
        for val in values:
            if val > peak:
                peak = val
            dd = (peak - val) / peak
            if dd > max_dd:
                max_dd = dd

        return {
            "var_95": float(np.percentile(returns, 5)),
            "var_99": float(np.percentile(returns, 1)),
            "cvar_95": float(np.mean(returns[returns <= np.percentile(returns, 5)])) if np.any(returns <= np.percentile(returns, 5)) else 0,
            "volatility": float(np.std(returns) * np.sqrt(252)),
            "skewness": float(pd.Series(returns).skew()),
            "kurtosis": float(pd.Series(returns).kurtosis()),
            "beta": 1.0,  # Would need market data
            "correlation_sp500": 0.0,  # Would need market data
            "sharpe_ratio": float((np.mean(returns) * 252 - risk_free_rate) / (np.std(returns) * np.sqrt(252))) if np.std(returns) > 0 else 0,
            "max_drawdown": float(max_dd)
        }
    
    async def get_exposure_analysis(self, portfolio_id: str) -> dict:
        """Analyze portfolio exposures by sector, industry, geography, etc."""
        portfolio = await self.get_portfolio(portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        
        # This would need sector/industry data for each symbol
        # For now, return basic allocation
        total = float(portfolio.total_value)
        allocations = {}
        
        for symbol, pos in portfolio.positions.items():
            allocations[symbol] = {
                "value": float(pos.market_value),
                "weight": float(pos.market_value / portfolio.total_value) if total > 0 else 0,
                "pnl": float(pos.unrealized_pnl + pos.realized_pnl)
            }
        
        return {
            "allocations": allocations,
            "total_positions": len(portfolio.positions),
            "largest_position": max(allocations.items(), key=lambda x: x[1]["weight"]) if allocations else None,
            "concentration": sum(w["weight"]**2 for w in allocations.values())
        }
    
    async def close(self) -> None:
        await self.backend.disconnect()


class AlertManager:
    """Manages portfolio alerts."""
    
    def __init__(self, backend: PortfolioBackend):
        self.backend = backend
        self.pool = backend.pool
    
    async def create_alert(
        self,
        portfolio_id: str,
        alert_type: str,
        condition: dict,
        message: str,
        severity: str = "info",
        symbol: str = None
    ) -> str:
        alert_id = str(uuid4())
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO alerts (id, portfolio_id, symbol, alert_type, condition, message, severity, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, alert_id, portfolio_id, symbol, alert_type, json.dumps(condition), message, severity, datetime.utcnow())
        return alert_id
    
    async def check_alerts(self, portfolio_id: str = None) -> list[dict]:
        """Check and trigger alerts."""
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM alerts WHERE triggered = FALSE"
            params = []
            if portfolio_id:
                query += " AND portfolio_id = $1"
                params.append(portfolio_id)
            
            rows = await conn.fetch(query, *params)
            
            triggered = []
            for row in rows:
                condition = row["condition"]
                # Evaluate condition (simplified)
                triggered_alert = await self._evaluate_condition(row)
                if triggered_alert:
                    triggered.append(triggered_alert)
                    # Mark as triggered
                    await conn.execute(
                        "UPDATE alerts SET triggered = TRUE, triggered_at = $1 WHERE id = $2",
                        datetime.utcnow(), row["id"]
                    )
            
            return triggered
    
    async def _evaluate_condition(self, alert_row) -> Optional[dict]:
        """Evaluate alert condition."""
        # Simplified - would need actual market data
        return None
    
    async def get_active_alerts(self, portfolio_id: str = None) -> list[dict]:
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM alerts WHERE triggered = FALSE"
            params = []
            if portfolio_id:
                query += " AND portfolio_id = $1"
                params.append(portfolio_id)
            query += " ORDER BY created_at DESC"
            
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]


# Factory
async def create_portfolio_manager(
    backend_type: str = "postgres",
    **kwargs
) -> PortfolioManager:
    """Factory function to create PortfolioManager with specified backend."""
    if backend_type == "postgres":
        backend = PostgresPortfolioBackend(
            dsn=kwargs.get("dsn", "postgresql://localhost/financial_portfolio"),
            pool_size=kwargs.get("pool_size", 10)
        )
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")
    
    manager = PortfolioManager(
        backend=backend,
        market_data_provider=kwargs.get("market_data_provider"),
        risk_engine=kwargs.get("risk_engine")
    )
    
    await manager.initialize()
    return manager


# Export
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
    "create_portfolio_manager",
]