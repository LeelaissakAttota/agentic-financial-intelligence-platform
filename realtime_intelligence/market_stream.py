"""
Market Data Stream - Real-time market data streaming and distribution.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import json

from .server import get_websocket_server, MessageType, WSMessage

logger = logging.getLogger(__name__)


class MarketDataType(str, Enum):
    """Types of market data."""
    QUOTE = "quote"
    TRADE = "trade"
    DEPTH = "depth"
    SUMMARY = "summary"
    OHLCV = "ohlcv"
    OPTION_CHAIN = "option_chain"
    FUNDAMENTAL = "fundamental"


@dataclass
class MarketQuote:
    """Real-time market quote."""
    symbol: str
    price: float
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    volume: int
    change: float
    change_percent: float
    high: float
    low: float
    open: float
    previous_close: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    exchange: str = ""
    currency: str = "USD"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "bid": self.bid,
            "ask": self.ask,
            "bid_size": self.bid_size,
            "ask_size": self.ask_size,
            "volume": self.volume,
            "change": self.change,
            "change_percent": self.change_percent,
            "high": self.high,
            "low": self.low,
            "open": self.open,
            "previous_close": self.previous_close,
            "timestamp": self.timestamp.isoformat(),
            "exchange": self.exchange,
            "currency": self.currency
        }


@dataclass
class MarketTrade:
    """Individual trade execution."""
    symbol: str
    price: float
    size: int
    side: str  # "buy" or "sell"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    exchange: str = ""
    trade_id: str = ""
    conditions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "size": self.size,
            "side": self.side,
            "timestamp": self.timestamp.isoformat(),
            "exchange": self.exchange,
            "trade_id": self.trade_id,
            "conditions": self.conditions
        }


@dataclass
class MarketDepth:
    """Order book depth."""
    symbol: str
    bids: List[Dict[str, Any]]  # [{"price": float, "size": int, "orders": int}, ...]
    asks: List[Dict[str, Any]]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    exchange: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "bids": self.bids,
            "asks": self.asks,
            "timestamp": self.timestamp.isoformat(),
            "exchange": self.exchange
        }


class MarketDataStream:
    """
    Real-time market data streaming service.
    Ingests market data from providers and distributes via WebSocket.
    """
    
    def __init__(self):
        self.ws_server = get_websocket_server()
        self._running = False
        self._subscriptions: Dict[str, Set[str]] = defaultdict(set)  # symbol -> client_ids
        self._symbol_subscribers: Dict[str, Set[str]] = defaultdict(set)
        self._data_providers: Dict[str, Callable] = {}
        self._latest_quotes: Dict[str, MarketQuote] = {}
        self._latest_trades: Dict[str, List[MarketTrade]] = defaultdict(list)
        self._latest_depth: Dict[str, MarketDepth] = {}
        self._update_callbacks: List[Callable] = []
        self._stats = {
            "quotes_received": 0,
            "trades_received": 0,
            "depth_updates": 0,
            "broadcasts_sent": 0,
            "errors": 0
        }
        
        # Register WebSocket handlers
        self.ws_server.register_handler(MessageType.SUBSCRIBE, self._handle_subscribe)
        self.ws_server.register_handler(MessageType.UNSUBSCRIBE, self._handle_unsubscribe)
    
    async def start(self) -> None:
        """Start the market data stream."""
        self._running = True
        await self.ws_server.start_heartbeat()
        logger.info("Market data stream started")
    
    async def stop(self) -> None:
        """Stop the market data stream."""
        self._running = False
        logger.info("Market data stream stopped")
    
    def register_provider(self, name: str, provider: Callable) -> None:
        """Register a market data provider."""
        self._data_providers[name] = provider
        logger.info(f"Registered market data provider: {name}")
    
    def register_update_callback(self, callback: Callable) -> None:
        """Register a callback for data updates."""
        self._update_callbacks.append(callback)
    
    async def _handle_subscribe(self, client, message: WSMessage) -> None:
        """Handle market data subscription."""
        topics = message.payload.get("topics", [])
        if isinstance(topics, str):
            topics = [topics]
        
        for topic in topics:
            # Parse topic format: "market:quote:AAPL" or "market:trade:AAPL"
            if topic.startswith("market:"):
                parts = topic.split(":")
                if len(parts) >= 3:
                    data_type = parts[1]
                    symbol = parts[2].upper()
                    
                    if data_type in ["quote", "trade", "depth", "all"]:
                        self._symbol_subscribers[f"{symbol}:{data_type}"].add(client.client_id)
                        client.subscriptions.add(topic)
                        
                        # Send latest data if available
                        await self._send_latest_data(client, symbol, data_type)
    
    async def _handle_unsubscribe(self, client, message: WSMessage) -> None:
        """Handle market data unsubscription."""
        topics = message.payload.get("topics", [])
        if isinstance(topics, str):
            topics = [topics]
        
        for topic in topics:
            if topic.startswith("market:"):
                parts = topic.split(":")
                if len(parts) >= 3:
                    data_type = parts[1]
                    symbol = parts[2].upper()
                    self._symbol_subscribers[f"{symbol}:{data_type}"].discard(client.client_id)
                    client.subscriptions.discard(topic)
    
    async def _send_latest_data(self, client, symbol: str, data_type: str) -> None:
        """Send latest cached data to newly subscribed client."""
        if data_type in ["quote", "all"] and symbol in self._latest_quotes:
            quote = self._latest_quotes[symbol]
            await client.send(WSMessage(
                type=MessageType.MARKET_QUOTE,
                payload=quote.to_dict()
            ))
        
        if data_type in ["trade", "all"] and symbol in self._latest_trades:
            for trade in self._latest_trades[symbol][-10:]:  # Last 10 trades
                await client.send(WSMessage(
                    type=MessageType.MARKET_TRADE,
                    payload=trade.to_dict()
                ))
        
        if data_type in ["depth", "all"] and symbol in self._latest_depth:
            depth = self._latest_depth[symbol]
            await client.send(WSMessage(
                type=MessageType.MARKET_DEPTH,
                payload=depth.to_dict()
            ))
    
    async def publish_quote(self, quote: MarketQuote) -> None:
        """Publish a market quote to subscribers."""
        self._latest_quotes[quote.symbol] = quote
        self._stats["quotes_received"] += 1
        
        # Broadcast to subscribers
        subscribers = self._symbol_subscribers.get(f"{quote.symbol}:quote", set()) | \
                     self._symbol_subscribers.get(f"{quote.symbol}:all", set())
        
        if subscribers:
            message = WSMessage(
                type=MessageType.MARKET_QUOTE,
                payload=quote.to_dict()
            )
            sent = await self.ws_server.send_to_clients(list(subscribers), message)
            self._stats["broadcasts_sent"] += sent
        
        # Call update callbacks
        for callback in self._update_callbacks:
            try:
                await callback("quote", quote)
            except Exception as e:
                logger.error(f"Update callback error: {e}")
    
    async def publish_trade(self, trade: MarketTrade) -> None:
        """Publish a trade to subscribers."""
        self._latest_trades[trade.symbol].append(trade)
        # Keep only last 100 trades
        if len(self._latest_trades[trade.symbol]) > 100:
            self._latest_trades[trade.symbol] = self._latest_trades[trade.symbol][-100:]
        
        self._stats["trades_received"] += 1
        
        subscribers = self._symbol_subscribers.get(f"{trade.symbol}:trade", set()) | \
                     self._symbol_subscribers.get(f"{trade.symbol}:all", set())
        
        if subscribers:
            message = WSMessage(
                type=MessageType.MARKET_TRADE,
                payload=trade.to_dict()
            )
            sent = await self.ws_server.send_to_clients(list(subscribers), message)
            self._stats["broadcasts_sent"] += sent
        
        for callback in self._update_callbacks:
            try:
                await callback("trade", trade)
            except Exception as e:
                logger.error(f"Update callback error: {e}")
    
    async def publish_depth(self, depth: MarketDepth) -> None:
        """Publish order book depth to subscribers."""
        self._latest_depth[depth.symbol] = depth
        self._stats["depth_updates"] += 1
        
        subscribers = self._symbol_subscribers.get(f"{depth.symbol}:depth", set()) | \
                     self._symbol_subscribers.get(f"{depth.symbol}:all", set())
        
        if subscribers:
            message = WSMessage(
                type=MessageType.MARKET_DEPTH,
                payload=depth.to_dict()
            )
            sent = await self.ws_server.send_to_clients(list(subscribers), message)
            self._stats["broadcasts_sent"] += sent
        
        for callback in self._update_callbacks:
            try:
                await callback("depth", depth)
            except Exception as e:
                logger.error(f"Update callback error: {e}")
    
    def get_latest_quote(self, symbol: str) -> Optional[MarketQuote]:
        """Get latest quote for a symbol."""
        return self._latest_quotes.get(symbol.upper())
    
    def get_latest_trades(self, symbol: str, limit: int = 50) -> List[MarketTrade]:
        """Get latest trades for a symbol."""
        trades = self._latest_trades.get(symbol.upper(), [])
        return trades[-limit:]
    
    def get_latest_depth(self, symbol: str) -> Optional[MarketDepth]:
        """Get latest depth for a symbol."""
        return self._latest_depth.get(symbol.upper())
    
    def get_subscribed_symbols(self) -> List[str]:
        """Get list of symbols with active subscriptions."""
        symbols = set()
        for key in self._symbol_subscribers:
            if self._symbol_subscribers[key]:
                symbols.add(key.split(":")[0])
        return sorted(symbols)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get streaming statistics."""
        return {
            **self._stats,
            "active_symbols": len(self._latest_quotes),
            "subscribed_symbols": len(self.get_subscribed_symbols()),
            "total_subscribers": sum(len(s) for s in self._symbol_subscribers.values())
        }


# Global market stream instance
_market_stream: Optional[MarketDataStream] = None


def get_market_stream() -> MarketDataStream:
    """Get or create the global market data stream."""
    global _market_stream
    if _market_stream is None:
        _market_stream = MarketDataStream()
    return _market_stream