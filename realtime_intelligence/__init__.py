"""
Real-Time Intelligence Layer Module
Provides WebSocket server, live market updates, news streaming, and event processing.
"""

from .server import WebSocketServer, get_websocket_server
from .market_stream import MarketDataStream, get_market_stream
from .news_stream import NewsStream, get_news_stream
from .event_bus import EventBus, get_event_bus
from .pubsub import PubSubManager, get_pubsub_manager
from .processor import EventProcessor, get_event_processor

__all__ = [
    "WebSocketServer",
    "get_websocket_server",
    "MarketDataStream",
    "get_market_stream",
    "NewsStream",
    "get_news_stream",
    "EventBus",
    "get_event_bus",
    "PubSubManager",
    "get_pubsub_manager",
    "EventProcessor",
    "get_event_processor",
]

__version__ = "1.0.0-phase9"