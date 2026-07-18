"""
Background Worker
Managed background worker pool for processing queued events.
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, List, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

from .queue import EventQueue, get_event_queue, QueuedEvent, QueuePriority, QueueStats

logger = logging.getLogger(__name__)


class WorkerStatus(str, Enum):
    """Worker status."""
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class WorkerStats:
    """Worker statistics."""
    worker_id: str
    status: WorkerStatus
    topics: List[str]
    events_processed: int = 0
    events_failed: int = 0
    avg_processing_time_ms: float = 0.0
    current_event_id: Optional[str] = None
    started_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    uptime_seconds: float = 0.0


class BackgroundWorker:
    """
    Background worker for processing events from queues.
    Features:
    - Multi-topic subscription
    - Concurrent processing with semaphore
    - Graceful shutdown
    - Health monitoring
    - Automatic retry with backoff
    - Metrics collection
    """
    
    def __init__(
        self,
        worker_id: Optional[str] = None,
        topics: Optional[List[str]] = None,
        max_concurrent: int = 10,
        poll_interval: float = 1.0,
        batch_size: int = 10
    ):
        self.worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        self.topics = topics or []
        self.max_concurrent = max_concurrent
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        
        # Queues for each topic
        self._queues: Dict[str, EventQueue] = {}
        
        # Workers
        self._worker_tasks: Dict[str, asyncio.Task] = {}
        self._status = WorkerStatus.STOPPED
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        
        # Stats
        self._stats = WorkerStats(
            worker_id=self.worker_id,
            status=WorkerStatus.STOPPED,
            topics=self.topics
        )
        
        # Processing
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._processing: Dict[str, QueuedEvent] = {}
        self._processing_times: List[float] = []
        
        # Handlers
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._global_handlers: List[Callable] = []
        
        # Health
        self._health_check_interval = 30.0
        self._last_health_check: Optional[datetime] = None
    
    def add_topic(self, topic: str, queue: Optional[EventQueue] = None) -> None:
        """Add a topic to subscribe to."""
        if topic not in self.topics:
            self.topics.append(topic)
            self._stats.topics = self.topics
        
        if queue:
            self._queues[topic] = queue
        elif topic not in self._queues:
            self._queues[topic] = get_event_queue(topic)
    
    def remove_topic(self, topic: str) -> None:
        """Remove a topic subscription."""
        if topic in self.topics:
            self.topics.remove(topic)
            self._stats.topics = self.topics
    
    def register_handler(self, topic: str, handler: Callable) -> None:
        """Register a handler for a specific topic."""
        self._event_handlers[topic].append(handler)
    
    def register_global_handler(self, handler: Callable) -> None:
        """Register a handler for all topics."""
        self._global_handlers.append(handler)
    
    @property
    def status(self) -> WorkerStatus:
        return self._status
    
    @property
    def is_running(self) -> bool:
        return self._status == WorkerStatus.RUNNING
    
    async def start(self) -> None:
        """Start the worker."""
        
        if self._status == WorkerStatus.RUNNING:
            return
        
        # Ensure queues exist
        for topic in self.topics:
            if topic not in self._queues:
                self._queues[topic] = get_event_queue(topic)
        
        self._status = WorkerStatus.STARTING
        self._stats.status = WorkerStatus.STARTING
        self._stats.started_at = datetime.utcnow()
        
        # Start worker tasks for each topic
        for topic in self.topics:
            task = asyncio.create_task(self._run_topic_worker(topic))
            self._worker_tasks[topic] = task
        
        # Start health check
        health_task = asyncio.create_task(self._health_check_loop())
        self._worker_tasks["health"] = health_task
        
        self._status = WorkerStatus.RUNNING
        self._stats.status = WorkerStatus.RUNNING
        
        logger.info(f"Worker {self.worker_id} started with topics: {self.topics}")
    
    async def stop(self, graceful: bool = True, timeout: float = 30.0) -> None:
        """Stop the worker."""
        
        if self._status == WorkerStatus.STOPPED:
            return
        
        self._status = WorkerStatus.STOPPING
        self._stats.status = WorkerStatus.STOPPING
        
        if graceful:
            # Wait for current processing to complete
            start = datetime.utcnow()
            while self._processing and (datetime.utcnow() - start).total_seconds() < timeout:
                await asyncio.sleep(0.1)
        
        # Cancel all tasks
        for task in self._worker_tasks.values():
            task.cancel()
        
        # Wait for cancellation
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks.values(), return_exceptions=True)
        
        self._worker_tasks.clear()
        self._status = WorkerStatus.STOPPED
        self._stats.status = WorkerStatus.STOPPED
        
        logger.info(f"Worker {self.worker_id} stopped")
    
    async def pause(self) -> None:
        """Pause event processing."""
        self._status = WorkerStatus.PAUSED
        self._stats.status = WorkerStatus.PAUSED
        self._pause_event.clear()
        logger.info(f"Worker {self.worker_id} paused")
    
    async def resume(self) -> None:
        """Resume event processing."""
        self._status = WorkerStatus.RUNNING
        self._stats.status = WorkerStatus.RUNNING
        self._pause_event.set()
        logger.info(f"Worker {self.worker_id} resumed")
    
    async def _run_topic_worker(self, topic: str) -> None:
        """Main worker loop for a topic."""
        
        queue = self._queues.get(topic)
        if not queue:
            logger.error(f"No queue found for topic: {topic}")
            return
        
        logger.info(f"Worker {self.worker_id} started processing topic: {topic}")
        
        while self._status != WorkerStatus.STOPPED:
            try:
                # Wait if paused
                await self._pause_event.wait()
                
                if self._status == WorkerStatus.STOPPED:
                    break
                
                # Dequeue events
                events = await queue.dequeue(self.batch_size)
                
                if not events:
                    await asyncio.sleep(self.poll_interval)
                    continue
                
                # Process events concurrently
                tasks = []
                for event in events:
                    task = asyncio.create_task(self._process_event(topic, event, queue))
                    tasks.append(task)
                
                # Wait for completion
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error on topic {topic}: {e}")
                await asyncio.sleep(1.0)
        
        logger.info(f"Worker {self.worker_id} stopped processing topic: {topic}")
    
    async def _process_event(self, topic: str, event: QueuedEvent, queue: EventQueue) -> None:
        """Process a single event."""
        
        start_time = datetime.utcnow()
        self._processing[event.event_id] = event
        self._stats.current_event_id = event.event_id
        self._stats.last_activity = datetime.utcnow()
        
        try:
            # Get handlers for this topic
            handlers = self._event_handlers.get(topic, []) + self._global_handlers
            
            if not handlers:
                logger.warning(f"No handlers for topic: {topic}")
                await queue.acknowledge(event.event_id, success=False)
                return
            
            # Execute handlers
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Handler error for {event.event_id}: {e}")
                    raise
            
            # Acknowledge success
            await queue.acknowledge(event.event_id, success=True)
            
            # Update stats
            self._stats.events_processed += 1
            self._stats.last_activity = datetime.utcnow()
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._processing_times.append(processing_time)
            if len(self._processing_times) > 1000:
                self._processing_times = self._processing_times[-1000:]
            
        except Exception as e:
            logger.error(f"Event processing failed for {event.event_id}: {e}")
            await queue.acknowledge(event.event_id, success=False)
            self._stats.events_failed += 1
            
        finally:
            self._processing.pop(event.event_id, None)
            self._stats.current_event_id = None
    
    async def _health_check_loop(self) -> None:
        """Periodic health check."""
        
        while self._status != WorkerStatus.STOPPED:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                if self._status == WorkerStatus.STOPPED:
                    break
                
                # Update uptime
                if self._stats.started_at:
                    self._stats.uptime_seconds = (datetime.utcnow() - self._stats.started_at).total_seconds()
                
                # Calculate avg processing time
                if self._processing_times:
                    self._stats.avg_processing_time_ms = np.mean(self._processing_times)
                
                self._last_health_check = datetime.utcnow()
                
                # Check for stuck processing
                if self._stats.current_event_id and self._stats.last_activity:
                    if (datetime.utcnow() - self._stats.last_activity).total_seconds() > 300:
                        logger.warning(f"Worker {self.worker_id} may be stuck on event {self._stats.current_event_id}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    def get_stats(self) -> WorkerStats:
        """Get worker statistics."""
        
        # Update uptime
        if self._stats.started_at:
            self._stats.uptime_seconds = (datetime.utcnow() - self._stats.started_at).total_seconds()
        
        if self._processing_times:
            self._stats.avg_processing_time_ms = np.mean(self._processing_times)
        
        return self._stats
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed worker statistics."""
        
        stats = self.get_stats()
        
        return {
            "worker_id": stats.worker_id,
            "status": stats.status.value,
            "topics": stats.topics,
            "events_processed": stats.events_processed,
            "events_failed": stats.events_failed,
            "success_rate": stats.events_processed / max(stats.events_processed + stats.events_failed, 1),
            "avg_processing_time_ms": stats.avg_processing_time_ms,
            "currently_processing": len(self._processing),
            "max_concurrent": self.max_concurrent,
            "uptime_seconds": stats.uptime_seconds,
            "started_at": stats.started_at.isoformat() if stats.started_at else None,
            "last_activity": stats.last_activity.isoformat() if stats.last_activity else None,
            "processing_events": [
                {
                    "event_id": e.event_id,
                    "topic": e.topic,
                    "attempts": e.attempts,
                    "started_at": (datetime.utcnow() - timedelta(milliseconds=np.mean(self._processing_times) if self._processing_times else 0)).isoformat()
                }
                for e in list(self._processing.values())[:10]
            ]
        }
    
    def register_callback(self, callback: Callable) -> None:
        """Register a status change callback."""
        pass  # Would store for notifications


# Global worker registry
_workers: Dict[str, BackgroundWorker] = {}


def get_background_worker(
    worker_id: Optional[str] = None,
    topics: Optional[List[str]] = None,
    max_concurrent: int = 10,
    poll_interval: float = 1.0,
    batch_size: int = 10
) -> BackgroundWorker:
    """Get or create a background worker."""
    global _workers
    
    if worker_id is None:
        worker_id = f"worker_{uuid.uuid4().hex[:8]}"
    
    if worker_id not in _workers:
        _workers[worker_id] = BackgroundWorker(
            worker_id=worker_id,
            topics=topics,
            max_concurrent=max_concurrent,
            poll_interval=poll_interval,
            batch_size=batch_size
        )
    
    return _workers[worker_id]


async def close_background_worker(worker_id: str) -> None:
    """Close and remove a worker."""
    global _workers
    
    if worker_id in _workers:
        worker = _workers[worker_id]
        await worker.stop()
        del _workers[worker_id]


async def close_all_workers() -> None:
    """Close all workers."""
    global _workers
    
    for worker_id, worker in _workers.items():
        await worker.stop()
    
    _workers.clear()