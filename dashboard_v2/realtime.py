"""
Real-time Dashboard Engine
WebSocket-based real-time updates for the Enterprise Dashboard v2.
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class UpdateType(str, Enum):
    """Types of real-time updates."""
    METRIC = "metric"
    CHART = "chart"
    ALERT = "alert"
    AGENT_STATUS = "agent_status"
    WORKFLOW_PROGRESS = "workflow_progress"
    NEWS = "news"
    MARKET_DATA = "market_data"
    PORTFOLIO = "portfolio"
    SYSTEM = "system"


@dataclass
class RealtimeUpdate:
    """Real-time data update."""
    update_id: str
    update_type: UpdateType
    component_id: str
    data: Any
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: int = 0  # 0=low, 1=normal, 2=high, 3=critical
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Subscription:
    """Client subscription to data streams."""
    subscription_id: str
    client_id: str
    component_ids: Set[str]
    update_types: Set[UpdateType]
    filters: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)


class RealtimeDashboard:
    """
    Real-time dashboard engine with WebSocket support.
    Manages subscriptions, broadcasts updates, and handles client connections.
    """
    
    def __init__(self):
        self._subscriptions: Dict[str, Subscription] = {}
        self._client_subscriptions: Dict[str, Set[str]] = defaultdict(set)  # client_id -> subscription_ids
        self._component_subscribers: Dict[str, Set[str]] = defaultdict(set)  # component_id -> subscription_ids
        self._update_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._broadcast_task: Optional[asyncio.Task] = None
        self._update_handlers: Dict[UpdateType, List[Callable]] = defaultdict(list)
        self._stats = {
            "total_updates": 0,
            "active_subscriptions": 0,
            "connected_clients": 0,
            "updates_per_second": 0.0
        }
        self._update_times: List[datetime] = []
    
    def register_update_handler(self, update_type: UpdateType, handler: Callable) -> None:
        """Register a handler for specific update types."""
        self._update_handlers[update_type].append(handler)
    
    async def start(self) -> None:
        """Start the real-time engine."""
        self._running = True
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info("Real-time dashboard engine started")
    
    async def stop(self) -> None:
        """Stop the real-time engine."""
        self._running = False
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        logger.info("Real-time dashboard engine stopped")
    
    async def subscribe(
        self,
        client_id: str,
        component_ids: List[str],
        update_types: Optional[List[UpdateType]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new subscription for a client."""
        
        subscription_id = f"sub_{client_id}_{datetime.utcnow().timestamp()}"
        
        subscription = Subscription(
            subscription_id=subscription_id,
            client_id=client_id,
            component_ids=set(component_ids),
            update_types=set(update_types) if update_types else set(UpdateType),
            filters=filters or {}
        )
        
        self._subscriptions[subscription_id] = subscription
        self._client_subscriptions[client_id].add(subscription_id)
        
        for comp_id in component_ids:
            self._component_subscribers[comp_id].add(subscription_id)
        
        self._stats["active_subscriptions"] = len(self._subscriptions)
        self._stats["connected_clients"] = len(self._client_subscriptions)
        
        logger.info(f"Client {client_id} subscribed to {len(component_ids)} components")
        return subscription_id
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription."""
        if subscription_id not in self._subscriptions:
            return False
        
        subscription = self._subscriptions[subscription_id]
        
        # Remove from client subscriptions
        self._client_subscriptions[subscription.client_id].discard(subscription_id)
        if not self._client_subscriptions[subscription.client_id]:
            del self._client_subscriptions[subscription.client_id]
        
        # Remove from component subscribers
        for comp_id in subscription.component_ids:
            self._component_subscribers[comp_id].discard(subscription_id)
            if not self._component_subscribers[comp_id]:
                del self._component_subscribers[comp_id]
        
        del self._subscriptions[subscription_id]
        
        self._stats["active_subscriptions"] = len(self._subscriptions)
        self._stats["connected_clients"] = len(self._client_subscriptions)
        
        return True
    
    async def unsubscribe_client(self, client_id: str) -> int:
        """Unsubscribe all subscriptions for a client."""
        subscription_ids = list(self._client_subscriptions.get(client_id, set()))
        count = 0
        
        for sub_id in subscription_ids:
            if await self.unsubscribe(sub_id):
                count += 1
        
        return count
    
    async def publish_update(self, update: RealtimeUpdate) -> int:
        """Publish an update to all relevant subscribers."""
        
        # Find matching subscriptions
        matching_subs = set()
        
        # Subscriptions for this component
        matching_subs.update(self._component_subscribers.get(update.component_id, set()))
        
        # Also check for wildcard subscriptions (empty component_ids)
        for sub_id, sub in self._subscriptions.items():
            if not sub.component_ids or update.component_id in sub.component_ids:
                if update.update_type in sub.update_types:
                    matching_subs.add(sub_id)
        
        # Filter by filters
        filtered_subs = set()
        for sub_id in matching_subs:
            sub = self._subscriptions.get(sub_id)
            if not sub:
                continue
            
            # Apply filters
            match = True
            for key, value in update.metadata.items():
                if key in sub.filters and sub.filters[key] != value:
                    match = False
                    break
            
            if match:
                filtered_subs.add(sub_id)
        
        # Deliver updates
        delivered = 0
        for sub_id in filtered_subs:
            sub = self._subscriptions.get(sub_id)
            if not sub:
                continue
            
            # Call registered handlers
            for handler in self._update_handlers.get(update.update_type, []):
                try:
                    await handler(update, sub)
                    delivered += 1
                except Exception as e:
                    logger.error(f"Handler error for {update.update_type}: {e}")
        
        # Update stats
        self._stats["total_updates"] += 1
        self._update_times.append(datetime.utcnow())
        
        # Calculate updates per second (last 60 seconds)
        cutoff = datetime.utcnow() - timedelta(seconds=60)
        recent = [t for t in self._update_times if t > cutoff]
        self._stats["updates_per_second"] = len(recent) / 60.0
        
        return delivered
    
    async def _broadcast_loop(self) -> None:
        """Background loop for processing queued updates."""
        while self._running:
            try:
                # Process queued updates with timeout
                update = await asyncio.wait_for(
                    self._update_queue.get(),
                    timeout=1.0
                )
                await self.publish_update(update)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Broadcast loop error: {e}")
                await asyncio.sleep(0.1)
    
    def queue_update(
        self,
        update_type: UpdateType,
        component_id: str,
        data: Any,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Queue an update for broadcast."""
        
        update = RealtimeUpdate(
            update_id=f"upd_{datetime.utcnow().timestamp()}",
            update_type=update_type,
            component_id=component_id,
            data=data,
            priority=priority,
            metadata=metadata or {}
        )
        
        try:
            self._update_queue.put_nowait(update)
        except asyncio.QueueFull:
            logger.warning("Update queue full, dropping update")
    
    def broadcast_to_component(
        self,
        component_id: str,
        data: Any,
        update_type: UpdateType = UpdateType.CHART,
        priority: int = 0
    ) -> None:
        """Convenience method to broadcast to a component."""
        self.queue_update(update_type, component_id, data, priority)
    
    def broadcast_alert(
        self,
        alert_data: Any,
        priority: int = 2
    ) -> None:
        """Broadcast an alert."""
        self.queue_update(UpdateType.ALERT, "alert_panel", alert_data, priority)
    
    def broadcast_agent_status(
        self,
        agent_data: Any
    ) -> None:
        """Broadcast agent status update."""
        self.queue_update(UpdateType.AGENT_STATUS, "agent_status", agent_data, 1)
    
    def broadcast_workflow_progress(
        self,
        workflow_data: Any
    ) -> None:
        """Broadcast workflow progress."""
        self.queue_update(UpdateType.WORKFLOW_PROGRESS, "workflow_viz", workflow_data, 1)
    
    def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get subscription by ID."""
        return self._subscriptions.get(subscription_id)
    
    def get_client_subscriptions(self, client_id: str) -> List[Subscription]:
        """Get all subscriptions for a client."""
        return [
            self._subscriptions[sid]
            for sid in self._client_subscriptions.get(client_id, set())
            if sid in self._subscriptions
        ]
    
    def get_component_subscribers(self, component_id: str) -> List[Subscription]:
        """Get all subscriptions for a component."""
        return [
            self._subscriptions[sid]
            for sid in self._component_subscribers.get(component_id, set())
            if sid in self._subscriptions
        ]
    
    def update_stats(self) -> None:
        """Update real-time statistics."""
        self._stats["active_subscriptions"] = len(self._subscriptions)
        self._stats["connected_clients"] = len(self._client_subscriptions)
        
        # Calculate updates per second
        cutoff = datetime.utcnow() - timedelta(seconds=60)
        recent = [t for t in self._update_times if t > cutoff]
        self._stats["updates_per_second"] = len(recent) / 60.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get real-time engine statistics."""
        self.update_stats()
        return {
            **self._stats,
            "queue_size": self._update_queue.qsize(),
            "registered_handlers": {
                ut.value: len(handlers) for ut, handlers in self._update_handlers.items()
            }
        }
    
    def get_subscription_info(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed subscription information."""
        sub = self._subscriptions.get(subscription_id)
        if not sub:
            return None
        
        return {
            "subscription_id": sub.subscription_id,
            "client_id": sub.client_id,
            "component_ids": list(sub.component_ids),
            "update_types": [ut.value for ut in sub.update_types],
            "filters": sub.filters,
            "created_at": sub.created_at.isoformat(),
            "last_activity": sub.last_activity.isoformat(),
            "age_seconds": (datetime.utcnow() - sub.created_at).total_seconds()
        }


# Global realtime dashboard instance
_realtime_dashboard: Optional[RealtimeDashboard] = None


def get_realtime_dashboard() -> RealtimeDashboard:
    global _realtime_dashboard
    if _realtime_dashboard is None:
        _realtime_dashboard = RealtimeDashboard()
    return _realtime_dashboard


async def close_realtime_dashboard() -> None:
    global _realtime_dashboard
    if _realtime_dashboard:
        await _realtime_dashboard.stop()
        _realtime_dashboard = None