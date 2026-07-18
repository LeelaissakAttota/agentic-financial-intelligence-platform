"""
Event Queue
High-performance async queue with priority support, persistence, and monitoring.
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, List, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import heapq

logger = logging.getLogger(__name__)


class QueuePriority(int, Enum):
    """Queue priority levels (lower = higher priority)."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class QueueStatus(str, Enum):
    """Queue status."""
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    DRAINING = "draining"


@dataclass
class QueuedEvent:
    """Event in the queue."""
    event_id: str
    topic: str
    payload: Any
    priority: QueuePriority = QueuePriority.NORMAL
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None
    attempts: int = 0
    max_attempts: int = 3
    timeout: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    
    def __lt__(self, other: "QueuedEvent") -> bool:
        """For heap ordering: priority first, then scheduled time, then creation time."""
        if self.priority != other.priority:
            return self.priority < other.priority
        if self.scheduled_at != other.scheduled_at:
            return (self.scheduled_at or datetime.max) < (other.scheduled_at or datetime.max)
        return self.created_at < other.created_at


@dataclass
class QueueStats:
    """Queue statistics."""
    topic: str
    pending: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0
    dead_letter: int = 0
    avg_processing_time_ms: float = 0.0
    throughput_per_sec: float = 0.0
    oldest_pending_age_sec: float = 0.0


class EventQueue:
    """
    High-performance async event queue with priority support.
    Features:
    - Priority-based ordering (heap-based)
    - Scheduled/delayed execution
    - Dead letter queue
    - Metrics and monitoring
    - Backpressure handling
    """
    
    def __init__(
        self,
        topic: str,
        max_size: int = 100000,
        max_processing: int = 100,
        dead_letter_max: int = 10000
    ):
        self.topic = topic
        self.max_size = max_size
        self.max_processing = max_processing
        self.dead_letter_max = dead_letter_max
        
        # Priority queue (heap)
        self._queue: List[QueuedEvent] = []
        self._processing: Dict[str, QueuedEvent] = {}
        self._dead_letter: List[QueuedEvent] = []
        
        # Metrics
        self._completed_count = 0
        self._failed_count = 0
        self._processing_times: List[float] = []
        self._enqueue_times: List[datetime] = []
        
        # State
        self._status = QueueStatus.RUNNING
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        
        # Callbacks
        self._event_handlers: List[Callable] = []
        self._dead_letter_handlers: List[Callable] = []
        
        # Concurrency control
        self._semaphore = asyncio.Semaphore(max_processing)
        self._lock = asyncio.Lock()
    
    def register_handler(self, handler: Callable) -> None:
        """Register an event handler."""
        self._event_handlers.append(handler)
    
    def register_dead_letter_handler(self, handler: Callable) -> None:
        """Register a dead letter handler."""
        self._dead_letter_handlers.append(handler)
    
    @property
    def status(self) -> QueueStatus:
        return self._status
    
    @property
    def pending_count(self) -> int:
        return len(self._queue)
    
    @property
    def processing_count(self) -> int:
        return len(self._processing)
    
    async def enqueue(
        self,
        payload: Any,
        topic: Optional[str] = None,
        priority: QueuePriority = QueuePriority.NORMAL,
        scheduled_at: Optional[datetime] = None,
        max_attempts: int = 3,
        timeout: float = 30.0,
        metadata: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        event_id: Optional[str] = None
    ) -> str:
        """Add an event to the queue."""
        
        if self._status == QueueStatus.STOPPED:
            raise RuntimeError("Queue is stopped")
        
        async with self._lock:
            if len(self._queue) >= self.max_size:
                raise RuntimeError(f"Queue full (max: {self.max_size})")
            
            event = QueuedEvent(
                event_id=event_id or str(uuid.uuid4()),
                topic=topic or self.topic,
                payload=payload,
                priority=priority,
                scheduled_at=scheduled_at,
                max_attempts=max_attempts,
                timeout=timeout,
                metadata=metadata or {},
                headers=headers or {}
            )
            
            heapq.heappush(self._queue, event)
            self._enqueue_times.append(datetime.utcnow())
            
            logger.debug(f"Enqueued event {event.event_id} to {event.topic} (priority: {priority.name})")
            
            return event.event_id
    
    async def enqueue_batch(
        self,
        events: List[Dict[str, Any]]
    ) -> List[str]:
        """Enqueue multiple events efficiently."""
        
        if self._status == QueueStatus.STOPPED:
            raise RuntimeError("Queue is stopped")
        
        event_ids = []
        async with self._lock:
            for event_data in events:
                if len(self._queue) >= self.max_size:
                    logger.warning("Queue full, stopping batch enqueue")
                    break
                
                event = QueuedEvent(
                    event_id=event_data.get("event_id", str(uuid.uuid4())),
                    topic=event_data.get("topic", self.topic),
                    payload=event_data.get("payload"),
                    priority=QueuePriority(event_data.get("priority", QueuePriority.NORMAL)),
                    scheduled_at=event_data.get("scheduled_at"),
                    max_attempts=event_data.get("max_attempts", 3),
                    timeout=event_data.get("timeout", 30.0),
                    metadata=event_data.get("metadata", {}),
                    headers=event_data.get("headers", {})
                )
                
                heapq.heappush(self._queue, event)
                event_ids.append(event.event_id)
                self._enqueue_times.append(datetime.utcnow())
        
        return event_ids
    
    async def dequeue(self, count: int = 1) -> List[QueuedEvent]:
        """Dequeue events for processing."""
        
        events = []
        async with self._lock:
            now = datetime.utcnow()
            
            while self._queue and len(events) < count:
                # Check if next event is ready (scheduled)
                next_event = self._queue[0]
                
                if next_event.scheduled_at and next_event.scheduled_at > now:
                    break  # Next event not ready yet
                
                event = heapq.heappop(self._queue)
                event.attempts += 1
                self._processing[event.event_id] = event
                events.append(event)
        
        return events
    
    async def acknowledge(self, event_id: str, success: bool = True) -> bool:
        """Acknowledge event processing completion."""
        
        async with self._lock:
            event = self._processing.pop(event_id, None)
            if not event:
                return False
            
            if success:
                self._completed_count += 1
                # Record processing time
                processing_time = (datetime.utcnow() - event.created_at).total_seconds() * 1000
                self._processing_times.append(processing_time)
                if len(self._processing_times) > 1000:
                    self._processing_times = self._processing_times[-1000:]
            else:
                await self._handle_failure(event)
            
            return True
    
    async def _handle_failure(self, event: QueuedEvent) -> None:
        """Handle event processing failure."""
        
        if event.attempts >= event.max_attempts:
            # Move to dead letter queue
            await self._move_to_dead_letter(event)
        else:
            # Re-queue with exponential backoff
            delay = min(2 ** event.attempts * 5, 300)  # Max 5 minutes
            event.scheduled_at = datetime.utcnow() + timedelta(seconds=delay)
            heapq.heappush(self._queue, event)
            self._failed_count += 1
            
            logger.warning(f"Event {event.event_id} failed (attempt {event.attempts}/{event.max_attempts}), re-queued in {delay}s")
    
    async def _move_to_dead_letter(self, event: QueuedEvent) -> None:
        """Move event to dead letter queue."""
        
        if len(self._dead_letter) >= self.dead_letter_max:
            # Remove oldest
            self._dead_letter.pop(0)
        
        self._dead_letter.append(event)
        self._failed_count += 1
        
        logger.error(f"Event {event.event_id} moved to dead letter queue after {event.attempts} attempts")
        
        # Call dead letter handlers
        for handler in self._dead_letter_handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Dead letter handler error: {e}")
    
    async def requeue_dead_letter(self, event_id: str) -> bool:
        """Re-queue an event from dead letter queue."""
        
        async with self._lock:
            for i, event in enumerate(self._dead_letter):
                if event.event_id == event_id:
                    event.attempts = 0
                    event.scheduled_at = None
                    self._dead_letter.pop(i)
                    heapq.heappush(self._queue, event)
                    logger.info(f"Re-queued dead letter event {event_id}")
                    return True
        
        return False
    
    async def pause(self) -> None:
        """Pause queue processing."""
        self._status = QueueStatus.PAUSED
        self._pause_event.clear()
        logger.info(f"Queue {self.topic} paused")
    
    async def resume(self) -> None:
        """Resume queue processing."""
        self._status = QueueStatus.RUNNING
        self._pause_event.set()
        logger.info(f"Queue {self.topic} resumed")
    
    async def stop(self) -> None:
        """Stop the queue."""
        self._status = QueueStatus.STOPPED
        self._pause_event.set()
        logger.info(f"Queue {self.topic} stopped")
    
    async def drain(self) -> None:
        """Drain queue - process all pending events then stop."""
        self._status = QueueStatus.DRAINING
        logger.info(f"Queue {self.topic} draining")
    
    async def wait_until_empty(self, timeout: float = 60.0) -> bool:
        """Wait until queue is empty."""
        start = datetime.utcnow()
        
        while self._queue or self._processing:
            if (datetime.utcnow() - start).total_seconds() > timeout:
                return False
            await asyncio.sleep(0.1)
        
        return True
    
    def get_stats(self) -> QueueStats:
        """Get queue statistics."""
        
        now = datetime.utcnow()
        oldest_pending = 0.0
        if self._queue:
            oldest = self._queue[0]
            oldest_pending = (now - oldest.created_at).total_seconds()
        
        avg_time = np.mean(self._processing_times) if self._processing_times else 0.0
        
        # Throughput (last 60 seconds)
        recent = [t for t in self._enqueue_times if (now - t).total_seconds() < 60]
        throughput = len(recent) / 60.0
        
        return QueueStats(
            topic=self.topic,
            pending=len(self._queue),
            processing=len(self._processing),
            completed=self._completed_count,
            failed=self._failed_count,
            dead_letter=len(self._dead_letter),
            avg_processing_time_ms=avg_time,
            throughput_per_sec=throughput,
            oldest_pending_age_sec=oldest_pending
        )
    
    async def peek(self, count: int = 10) -> List[Dict[str, Any]]:
        """Peek at next events without dequeuing."""
        
        async with self._lock:
            events = []
            for event in heapq.nsmallest(count, self._queue):
                events.append({
                    "event_id": event.event_id,
                    "topic": event.topic,
                    "priority": event.priority.name,
                    "scheduled_at": event.scheduled_at.isoformat() if event.scheduled_at else None,
                    "created_at": event.created_at.isoformat(),
                    "attempts": event.attempts,
                    "payload_preview": str(event.payload)[:200]
                })
            return events
    
    async def clear_dead_letter(self) -> int:
        """Clear dead letter queue."""
        
        async with self._lock:
            count = len(self._dead_letter)
            self._dead_letter.clear()
            return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics as dict."""
        stats = self.get_stats()
        return {
            "topic": stats.topic,
            "pending": stats.pending,
            "processing": stats.processing,
            "completed": stats.completed,
            "failed": stats.failed,
            "dead_letter": stats.dead_letter,
            "avg_processing_time_ms": stats.avg_processing_time_ms,
            "throughput_per_sec": stats.throughput_per_sec,
            "oldest_pending_age_sec": stats.oldest_pending_age_sec,
            "status": self._status.value,
            "max_size": self.max_size,
            "max_processing": self.max_processing
        }


# Global queue registry
_queues: Dict[str, EventQueue] = {}


def get_event_queue(
    topic: str,
    max_size: int = 100000,
    max_processing: int = 100,
    dead_letter_max: int = 10000
) -> EventQueue:
    """Get or create an event queue for a topic."""
    global _queues
    
    if topic not in _queues:
        _queues[topic] = EventQueue(
            topic=topic,
            max_size=max_size,
            max_processing=max_processing,
            dead_letter_max=dead_letter_max
        )
    
    return _queues[topic]


async def close_event_queue(topic: str) -> None:
    """Close and remove a queue."""
    global _queues
    
    if topic in _queues:
        queue = _queues[topic]
        await queue.stop()
        del _queues[topic]


async def close_all_queues() -> None:
    """Close all queues."""
    global _queues
    
    for topic, queue in _queues.items():
        await queue.stop()
    
    _queues.clear()