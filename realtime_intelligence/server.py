"""
WebSocket Server - Real-time bidirectional communication for the platform.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Set, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Types of WebSocket messages."""
    # System
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    ACK = "ack"
    
    # Subscriptions
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    SUBSCRIPTION_CONFIRMED = "subscription_confirmed"
    
    # Market data
    MARKET_QUOTE = "market_quote"
    MARKET_TRADE = "market_trade"
    MARKET_DEPTH = "market_depth"
    MARKET_SUMMARY = "market_summary"
    
    # News
    NEWS_ARTICLE = "news_article"
    NEWS_ALERT = "news_alert"
    NEWS_SUMMARY = "news_summary"
    
    # Research
    RESEARCH_STARTED = "research_started"
    RESEARCH_PROGRESS = "research_progress"
    RESEARCH_COMPLETED = "research_completed"
    RESEARCH_FAILED = "research_failed"
    
    # Agent updates
    AGENT_STATUS = "agent_status"
    AGENT_OUTPUT = "agent_output"
    
    # Portfolio
    PORTFOLIO_UPDATE = "portfolio_update"
    ALERT_TRIGGERED = "alert_triggered"
    
    # Knowledge graph
    GRAPH_UPDATE = "graph_update"
    ENTITY_UPDATED = "entity_updated"
    RELATIONSHIP_ADDED = "relationship_added"


@dataclass
class WSMessage:
    """WebSocket message structure."""
    type: MessageType
    payload: Dict[str, Any] = field(default_factory=dict)
    request_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    
    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value,
            "payload": self.payload,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id
        }, default=str)
    
    @classmethod
    def from_json(cls, data: str) -> "WSMessage":
        obj = json.loads(data)
        return cls(
            type=MessageType(obj["type"]),
            payload=obj.get("payload", {}),
            request_id=obj.get("request_id"),
            timestamp=datetime.fromisoformat(obj["timestamp"]) if obj.get("timestamp") else datetime.utcnow(),
            correlation_id=obj.get("correlation_id")
        )


@dataclass
class ClientConnection:
    """Represents a connected WebSocket client."""
    client_id: str
    websocket: WebSocket
    connected_at: datetime = field(default_factory=datetime.utcnow)
    subscriptions: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    message_count: int = 0
    
    async def send(self, message: WSMessage) -> bool:
        """Send message to client."""
        try:
            if self.websocket.client_state == WebSocketState.CONNECTED:
                await self.websocket.send_text(message.to_json())
                self.message_count += 1
                return True
        except Exception as e:
            logger.error(f"Failed to send to client {self.client_id}: {e}")
        return False
    
    async def send_json(self, data: Dict[str, Any]) -> bool:
        """Send raw JSON to client."""
        try:
            if self.websocket.client_state == WebSocketState.CONNECTED:
                await self.websocket.send_json(data)
                self.message_count += 1
                return True
        except Exception as e:
            logger.error(f"Failed to send JSON to client {self.client_id}: {e}")
        return False


class WebSocketServer:
    """
    WebSocket server for real-time communication.
    Manages client connections, subscriptions, and message routing.
    """
    
    def __init__(
        self,
        heartbeat_interval: int = 30,
        max_message_size: int = 1024 * 1024,  # 1MB
        max_connections: int = 10000
    ):
        self.heartbeat_interval = heartbeat_interval
        self.max_message_size = max_message_size
        self.max_connections = max_connections
        
        self._clients: Dict[str, ClientConnection] = {}
        self._subscriptions: Dict[str, Set[str]] = {}  # topic -> client_ids
        self._message_handlers: Dict[MessageType, List[Callable]] = {}
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0
        }
    
    def register_handler(self, message_type: MessageType, handler: Callable) -> None:
        """Register a message handler for a specific message type."""
        if message_type not in self._message_handlers:
            self._message_handlers[message_type] = []
        self._message_handlers[message_type].append(handler)
    
    async def handle_connection(self, websocket: WebSocket) -> None:
        """Handle a new WebSocket connection."""
        client_id = str(uuid.uuid4())
        
        try:
            await websocket.accept()
        except Exception as e:
            logger.error(f"Failed to accept connection: {e}")
            return
        
        if len(self._clients) >= self.max_connections:
            await websocket.close(code=1013, reason="Server at capacity")
            return
        
        client = ClientConnection(client_id=client_id, websocket=websocket)
        self._clients[client_id] = client
        self._stats["total_connections"] += 1
        self._stats["active_connections"] = len(self._clients)
        
        logger.info(f"Client connected: {client_id} (total: {len(self._clients)})")
        
        # Send welcome message
        await client.send(WSMessage(
            type=MessageType.CONNECT,
            payload={"client_id": client_id, "server_time": datetime.utcnow().isoformat()}
        ))
        
        try:
            while True:
                # Receive message with timeout
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=self.heartbeat_interval * 2
                    )
                except asyncio.TimeoutError:
                    # Check heartbeat
                    if (datetime.utcnow() - client.last_heartbeat).seconds > self.heartbeat_interval * 3:
                        logger.warning(f"Client {client_id} heartbeat timeout")
                        break
                    continue
                
                if len(data) > self.max_message_size:
                    await client.send(WSMessage(
                        type=MessageType.ERROR,
                        payload={"error": "Message too large"}
                    ))
                    continue
                
                client.last_heartbeat = datetime.utcnow()
                self._stats["messages_received"] += 1
                
                try:
                    message = WSMessage.from_json(data)
                    await self._process_message(client, message)
                except json.JSONDecodeError:
                    await client.send(WSMessage(
                        type=MessageType.ERROR,
                        payload={"error": "Invalid JSON"}
                    ))
                except Exception as e:
                    logger.error(f"Error processing message from {client_id}: {e}")
                    await client.send(WSMessage(
                        type=MessageType.ERROR,
                        payload={"error": str(e)}
                    ))
        
        except WebSocketDisconnect:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Connection error for {client_id}: {e}")
            self._stats["errors"] += 1
        finally:
            await self._cleanup_client(client_id)
    
    async def _process_message(self, client: ClientConnection, message: WSMessage) -> None:
        """Process incoming message."""
        # Handle built-in message types
        if message.type == MessageType.HEARTBEAT:
            await client.send(WSMessage(
                type=MessageType.HEARTBEAT,
                payload={"server_time": datetime.utcnow().isoformat()},
                request_id=message.request_id
            ))
            return
        
        elif message.type == MessageType.SUBSCRIBE:
            await self._handle_subscribe(client, message)
            return
        
        elif message.type == MessageType.UNSUBSCRIBE:
            await self._handle_unsubscribe(client, message)
            return
        
        # Call registered handlers
        handlers = self._message_handlers.get(message.type, [])
        for handler in handlers:
            try:
                await handler(client, message)
            except Exception as e:
                logger.error(f"Handler error for {message.type}: {e}")
    
    async def _handle_subscribe(self, client: ClientConnection, message: WSMessage) -> None:
        """Handle subscription request."""
        topics = message.payload.get("topics", [])
        if isinstance(topics, str):
            topics = [topics]
        
        subscribed = []
        for topic in topics:
            if topic not in self._subscriptions:
                self._subscriptions[topic] = set()
            self._subscriptions[topic].add(client.client_id)
            client.subscriptions.add(topic)
            subscribed.append(topic)
        
        await client.send(WSMessage(
            type=MessageType.SUBSCRIPTION_CONFIRMED,
            payload={"topics": subscribed},
            request_id=message.request_id
        ))
        
        logger.debug(f"Client {client.client_id} subscribed to: {subscribed}")
    
    async def _handle_unsubscribe(self, client: ClientConnection, message: WSMessage) -> None:
        """Handle unsubscription request."""
        topics = message.payload.get("topics", [])
        if isinstance(topics, str):
            topics = [topics]
        
        unsubscribed = []
        for topic in topics:
            if topic in self._subscriptions:
                self._subscriptions[topic].discard(client.client_id)
                if not self._subscriptions[topic]:
                    del self._subscriptions[topic]
            client.subscriptions.discard(topic)
            unsubscribed.append(topic)
        
        await client.send(WSMessage(
            type=MessageType.SUBSCRIPTION_CONFIRMED,
            payload={"topics": unsubscribed, "action": "unsubscribed"},
            request_id=message.request_id
        ))
    
    async def _cleanup_client(self, client_id: str) -> None:
        """Clean up client resources."""
        client = self._clients.pop(client_id, None)
        if client:
            # Remove from subscriptions
            for topic in client.subscriptions:
                if topic in self._subscriptions:
                    self._subscriptions[topic].discard(client_id)
                    if not self._subscriptions[topic]:
                        del self._subscriptions[topic]
            
            self._stats["active_connections"] = len(self._clients)
            logger.info(f"Client cleaned up: {client_id} (remaining: {len(self._clients)})")
    
    async def broadcast(self, message: WSMessage, topic: Optional[str] = None) -> int:
        """Broadcast message to all clients or subscribers of a topic."""
        sent = 0
        
        if topic:
            client_ids = self._subscriptions.get(topic, set())
        else:
            client_ids = set(self._clients.keys())
        
        for client_id in client_ids:
            client = self._clients.get(client_id)
            if client and await client.send(message):
                sent += 1
        
        self._stats["messages_sent"] += sent
        return sent
    
    async def send_to_client(self, client_id: str, message: WSMessage) -> bool:
        """Send message to specific client."""
        client = self._clients.get(client_id)
        if client:
            result = await client.send(message)
            if result:
                self._stats["messages_sent"] += 1
            return result
        return False
    
    async def send_to_clients(self, client_ids: List[str], message: WSMessage) -> int:
        """Send message to multiple clients."""
        sent = 0
        for client_id in client_ids:
            if await self.send_to_client(client_id, message):
                sent += 1
        return sent
    
    def get_client_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a client."""
        client = self._clients.get(client_id)
        if not client:
            return None
        return {
            "client_id": client.client_id,
            "connected_at": client.connected_at.isoformat(),
            "subscriptions": list(client.subscriptions),
            "metadata": client.metadata,
            "message_count": client.message_count,
            "last_heartbeat": client.last_heartbeat.isoformat()
        }
    
    def get_all_clients(self) -> List[Dict[str, Any]]:
        """Get info for all connected clients."""
        return [self.get_client_info(cid) for cid in self._clients.keys()]
    
    def get_subscription_info(self) -> Dict[str, int]:
        """Get subscription statistics."""
        return {topic: len(clients) for topic, clients in self._subscriptions.items()}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        return {
            **self._stats,
            "subscriptions": len(self._subscriptions),
            "uptime_seconds": (datetime.utcnow() - min(
                (c.connected_at for c in self._clients.values()), 
                default=datetime.utcnow()
            )).total_seconds() if self._clients else 0
        }
    
    async def start_heartbeat(self) -> None:
        """Start heartbeat task."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            return
        
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("WebSocket heartbeat started")
    
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to all clients."""
        while self._running:
            await asyncio.sleep(self.heartbeat_interval)
            
            if not self._running:
                break
            
            heartbeat = WSMessage(
                type=MessageType.HEARTBEAT,
                payload={"server_time": datetime.utcnow().isoformat()}
            )
            
            # Send to all clients
            for client in list(self._clients.values()):
                if not await client.send(heartbeat):
                    # Client failed, will be cleaned up on next message
                    pass
    
    async def stop(self) -> None:
        """Stop the server and close all connections."""
        self._running = False
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Close all client connections
        for client in list(self._clients.values()):
            try:
                await client.websocket.close(code=1001, reason="Server shutting down")
            except Exception:
                pass
        
        self._clients.clear()
        self._subscriptions.clear()
        logger.info("WebSocket server stopped")


# Global server instance
_websocket_server: Optional[WebSocketServer] = None


def get_websocket_server(
    heartbeat_interval: int = 30,
    max_message_size: int = 1024 * 1024,
    max_connections: int = 10000
) -> WebSocketServer:
    """Get or create the global WebSocket server."""
    global _websocket_server
    if _websocket_server is None:
        _websocket_server = WebSocketServer(
            heartbeat_interval=heartbeat_interval,
            max_message_size=max_message_size,
            max_connections=max_connections
        )
    return _websocket_server


async def close_websocket_server() -> None:
    """Close the global WebSocket server."""
    global _websocket_server
    if _websocket_server:
        await _websocket_server.stop()
        _websocket_server = None