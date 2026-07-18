"""
Pub/Sub Manager - High-level publish-subscribe patterns.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import json

from .event_bus import get_event_bus, EventTypes

logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    """Represents a topic subscription."""
    subscriber_id: str
    topic: str
    filters: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    message_count: int = 0
    last_message_at: Optional[datetime] = None


class PubSubManager:
    """
    High-level pub/sub manager built on EventBus.
    Provides topic-based subscriptions with filtering.
    """
    
    def __init__(self):
        self.event_bus = get_event_bus()
        self._subscriptions: Dict[str, Dict[str, Subscription]] = defaultdict(dict)  # topic -> subscriber_id -> Subscription
        self._subscriber_topics: Dict[str, Set[str]] = defaultdict(set)  # subscriber_id -> topics
        self._topic_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._running = False
    
    async def start(self) -> None:
        """Start the pub/sub manager."""
        await self.event_bus.start()
        self._running = True
        logger.info("Pub/Sub manager started")
    
    async def stop(self) -> None:
        """Stop the pub/sub manager."""
        self._running = False
        await self.event_bus.stop()
        logger.info("Pub/Sub manager stopped")
    
    async def subscribe(
        self,
        subscriber_id: str,
        topic: str,
        handler: Callable,
        filters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Subscribe to a topic with optional filters."""
        if subscriber_id in self._subscriptions[topic]:
            logger.warning(f"Subscriber {subscriber_id} already subscribed to {topic}")
            return False
        
        subscription = Subscription(
            subscriber_id=subscriber_id,
            topic=topic,
            filters=filters or {}
        )
        
        self._subscriptions[topic][subscriber_id] = subscription
        self._subscriber_topics[subscriber_id].add(topic)
        self._topic_handlers[topic].append(handler)
        
        # Subscribe to event bus
        event_type = self._topic_to_event_type(topic)
        self.event_bus.subscribe(
            lambda event: self._dispatch_to_handler(subscriber_id, handler, event),
            event_types=[event_type]
        )
        
        logger.info(f"Subscriber {subscriber_id} subscribed to {topic}")
        return True
    
    def _topic_to_event_type(self, topic: str) -> str:
        """Convert topic to event type."""
        if topic.startswith("market."):
            return topic
        elif topic.startswith("news."):
            return topic
        elif topic.startswith("research."):
            return topic
        return f"custom.{topic}"
    
    async def unsubscribe(self, subscriber_id: str, topic: str) -> bool:
        """Unsubscribe from a topic."""
        if topic in self._subscriptions and subscriber_id in self._subscriptions[topic]:
            del self._subscriptions[topic][subscriber_id]
            self._subscriber_topics[subscriber_id].discard(topic)
            
            if not self._subscriptions[topic]:
                del self._subscriptions[topic]
            
            logger.info(f"Subscriber {subscriber_id} unsubscribed from {topic}")
            return True
        return False
    
    async def publish(
        self,
        topic: str,
        message: Any,
        source: str = "system",
        priority: int = 50,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Publish a message to a topic."""
        event_type = self._topic_to_event_type(topic)
        
        result = await self.event_bus.publish(
            event_type=event_type,
            payload=message,
            source=source,
            priority=priority,
            metadata=metadata or {}
        )
        
        if result:
            # Update subscription stats
            for sub in self._subscriptions.get(topic, {}).values():
                sub.message_count += 1
                sub.last_message_at = datetime.utcnow()
        
        return 1 if result else 0
    
    async def _dispatch_to_handler(self, subscriber_id: str, handler: Callable, event) -> None:
        """Dispatch event to handler with filter checking."""
        subscription = self._subscriptions.get(event.event_type, {}).get(subscriber_id)
        if not subscription:
            return
        
        # Check filters
        if subscription.filters:
            for key, expected in subscription.filters.items():
                if key not in event.payload or event.payload[key] != expected:
                    return
        
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event.payload, event)
            else:
                handler(event.payload, event)
        except Exception as e:
            logger.error(f"Handler error for {subscriber_id}: {e}")
    
    def get_subscriber_info(self, subscriber_id: str) -> Optional[Dict[str, Any]]:
        """Get subscriber information."""
        topics = self._subscriber_topics.get(subscriber_id, set())
        if not topics:
            return None
        
        return {
            "subscriber_id": subscriber_id,
            "topics": list(topics),
            "subscriptions": {
                topic: {
                    "message_count": self._subscriptions[topic][subscriber_id].message_count,
                    "last_message_at": self._subscriptions[topic][subscriber_id].last_message_at.isoformat() if self._subscriptions[topic][subscriber_id].last_message_at else None,
                    "filters": self._subscriptions[topic][subscriber_id].filters
                }
                for topic in topics if subscriber_id in self._subscriptions[topic]
            }
        }
    
    def get_topic_info(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get topic information."""
        subs = self._subscriptions.get(topic)
        if not subs:
            return None
        
        return {
            "topic": topic,
            "subscriber_count": len(subs),
            "subscribers": [
                {
                    "subscriber_id": sub_id,
                    "message_count": sub.message_count,
                    "last_message_at": sub.last_message_at.isoformat() if sub.last_message_at else None,
                    "filters": sub.filters
                }
                for sub_id, sub in subs.items()
            ]
        }
    
    def get_all_topics(self) -> List[str]:
        """Get all active topics."""
        return list(self._subscriptions.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pub/sub statistics."""
        total_subs = sum(len(subs) for subs in self._subscriptions.values())
        return {
            "active_topics": len(self._subscriptions),
            "total_subscriptions": total_subs,
            "unique_subscribers": len(self._subscriber_topics),
            "topic_details": {
                topic: len(subs) for topic, subs in self._subscriptions.items()
            }
        }


# Global pub/sub manager
_pubsub_manager: Optional[PubSubManager] = None


def get_pubsub_manager() -> PubSubManager:
    """Get or create the global pub/sub manager."""
    global _pubsub_manager
    if _pubsub_manager is None:
        _pubsub_manager = PubSubManager()
    return _pubsub_manager


async def close_pubsub_manager() -> None:
    """Close the global pub/sub manager."""
    global _pubsub_manager
    if _pubsub_manager:
        await _pubsub_manager.stop()
        _pubsub_manager = None