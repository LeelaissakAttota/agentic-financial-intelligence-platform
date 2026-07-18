"""
Event Bus - Centralized event distribution system.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Set, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict
import json

logger = logging.getLogger(__name__)

T = TypeVar('T')


class EventPriority(int, Enum):
    """Event priority levels."""
    LOW = 0
    NORMAL = 50
    HIGH = 100
    CRITICAL = 200


@dataclass
class Event(Generic[T]):
    """Base event structure."""
    event_type: str
    payload: T
    source: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    priority: EventPriority = EventPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: f"evt_{datetime.utcnow().timestamp()}")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "priority": self.priority.value,
            "metadata": self.metadata
        }


class EventHandler:
    """Event handler wrapper with filtering."""
    
    def __init__(
        self,
        handler: Callable,
        event_types: Optional[List[str]] = None,
        sources: Optional[List[str]] = None,
        min_priority: EventPriority = EventPriority.LOW
    ):
        self.handler = handler
        self.event_types = event_types or []
        self.sources = sources or []
        self.min_priority = min_priority
    
    def matches(self, event: Event) -> bool:
        """Check if this handler should process the event."""
        if self.event_types and event.event_type not in self.event_types:
            return False
        if self.sources and event.source not in self.sources:
            return False
        if event.priority < self.min_priority:
            return False
        return True
    
    async def handle(self, event: Event) -> Any:
        """Handle the event."""
        if asyncio.iscoroutinefunction(self.handler):
            return await self.handler(event)
        return self.handler(event)


class EventBus:
    """
    Centralized event bus for decoupled communication.
    Supports synchronous and asynchronous handlers with filtering.
    """
    
    def __init__(self, max_queue_size: int = 10000):
        self.max_queue_size = max_queue_size
        self._handlers: List[EventHandler] = []
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None
        self._stats = {
            "events_published": 0,
            "events_processed": 0,
            "events_failed": 0,
            "events_dropped": 0,
            "handlers_registered": 0
        }
        self._type_subscriptions: Dict[str, Set[int]] = defaultdict(set)
        self._source_subscriptions: Dict[str, Set[int]] = defaultdict(set)
    
    async def start(self) -> None:
        """Start the event processor."""
        self._running = True
        self._processor_task = asyncio.create_task(self._process_events())
        logger.info("Event bus started")
    
    async def stop(self) -> None:
        """Stop the event processor."""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        logger.info("Event bus stopped")
    
    def subscribe(
        self,
        handler: Callable,
        event_types: Optional[List[str]] = None,
        sources: Optional[List[str]] = None,
        min_priority: EventPriority = EventPriority.LOW
    ) -> int:
        """Subscribe a handler to events. Returns handler ID for unsubscription."""
        handler_obj = EventHandler(handler, event_types, sources, min_priority)
        handler_id = len(self._handlers)
        self._handlers.append(handler_obj)
        self._stats["handlers_registered"] += 1
        
        # Index for fast lookup
        if event_types:
            for et in event_types:
                self._type_subscriptions[et].add(handler_id)
        if sources:
            for src in sources:
                self._source_subscriptions[src].add(handler_id)
        
        logger.debug(f"Registered handler {handler_id} for types={event_types}, sources={sources}")
        return handler_id
    
    def unsubscribe(self, handler_id: int) -> bool:
        """Unsubscribe a handler by ID."""
        if 0 <= handler_id < len(self._handlers):
            handler = self._handlers[handler_id]
            # Remove from indexes
            if handler.event_types:
                for et in handler.event_types:
                    self._type_subscriptions[et].discard(handler_id)
            if handler.sources:
                for src in handler.sources:
                    self._source_subscriptions[src].discard(handler_id)
            
            self._handlers[handler_id] = None  # Mark as removed
            return True
        return False
    
    async def publish(
        self,
        event_type: str,
        payload: Any,
        source: str,
        correlation_id: Optional[str] = None,
        priority: EventPriority = EventPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Publish an event to the bus."""
        event = Event(
            event_type=event_type,
            payload=payload,
            source=source,
            correlation_id=correlation_id,
            priority=priority,
            metadata=metadata or {}
        )
        
        try:
            self._event_queue.put_nowait(event)
            self._stats["events_published"] += 1
            return True
        except asyncio.QueueFull:
            self._stats["events_dropped"] += 1
            logger.warning(f"Event queue full, dropping event: {event_type}")
            return False
    
    async def publish_sync(
        self,
        event_type: str,
        payload: Any,
        source: str,
        correlation_id: Optional[str] = None,
        priority: EventPriority = EventPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """Publish event and wait for all handlers to complete."""
        event = Event(
            event_type=event_type,
            payload=payload,
            source=source,
            correlation_id=correlation_id,
            priority=priority,
            metadata=metadata or {}
        )
        
        results = []
        matched_handlers = self._get_matching_handlers(event)
        
        for handler in matched_handlers:
            try:
                result = await handler.handle(event)
                results.append(result)
            except Exception as e:
                logger.error(f"Handler error in sync publish: {e}")
                self._stats["events_failed"] += 1
        
        self._stats["events_processed"] += len(results)
        return results
    
    def _get_matching_handlers(self, event: Event) -> List[EventHandler]:
        """Get handlers that match the event."""
        # Use indexed subscriptions for fast filtering
        candidate_ids = set()
        
        if event.event_type in self._type_subscriptions:
            candidate_ids |= self._type_subscriptions[event.event_type]
        else:
            # No type filter, include all
            candidate_ids = set(range(len(self._handlers)))
        
        if event.source in self._source_subscriptions:
            source_ids = self._source_subscriptions[event.source]
            candidate_ids &= source_ids if candidate_ids else source_ids
        
        # Filter by actual handler matching
        matched = []
        for handler_id in candidate_ids:
            if handler_id < len(self._handlers) and self._handlers[handler_id]:
                handler = self._handlers[handler_id]
                if handler.matches(event):
                    matched.append(handler)
        
        return matched
    
    async def _process_events(self) -> None:
        """Background event processing loop."""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                
                matched_handlers = self._get_matching_handlers(event)
                
                if not matched_handlers:
                    continue
                
                # Execute handlers
                tasks = []
                for handler in matched_handlers:
                    tasks.append(self._execute_handler(handler, event))
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                self._stats["events_processed"] += 1
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event processing error: {e}")
                self._stats["events_failed"] += 1
    
    async def _execute_handler(self, handler: EventHandler, event: Event) -> None:
        """Execute a single handler with error handling."""
        try:
            await handler.handle(event)
        except Exception as e:
            logger.error(f"Handler execution failed: {e}")
            self._stats["events_failed"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            **self._stats,
            "queue_size": self._event_queue.qsize(),
            "active_handlers": len([h for h in self._handlers if h is not None]),
            "is_running": self._running
        }
    
    def clear_stats(self) -> None:
        """Reset statistics."""
        for key in self._stats:
            self._stats[key] = 0


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


# Predefined event types for the platform
class EventTypes:
    """Standard event types used across the platform."""
    
    # Market data
    MARKET_QUOTE = "market.quote"
    MARKET_TRADE = "market.trade"
    MARKET_DEPTH = "market.depth"
    MARKET_ALERT = "market.alert"
    
    # News
    NEWS_ARTICLE = "news.article"
    NEWS_ALERT = "news.alert"
    NEWS_SUMMARY = "news.summary"
    
    # Research
    RESEARCH_STARTED = "research.started"
    RESEARCH_PROGRESS = "research.progress"
    RESEARCH_COMPLETED = "research.completed"
    RESEARCH_FAILED = "research.failed"
    
    # Agent
    AGENT_STARTED = "agent.started"
    AGENT_PROGRESS = "agent.progress"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    AGENT_OUTPUT = "agent.output"
    
    # Portfolio
    PORTFOLIO_UPDATE = "portfolio.update"
    POSITION_CHANGED = "portfolio.position_changed"
    ALERT_TRIGGERED = "alert.triggered"
    
    # Knowledge graph
    ENTITY_CREATED = "graph.entity_created"
    ENTITY_UPDATED = "graph.entity_updated"
    RELATIONSHIP_CREATED = "graph.relationship_created"
    GRAPH_SYNC_COMPLETED = "graph.sync_completed"
    
    # System
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    ERROR = "system.error"
    METRIC = "system.metric"