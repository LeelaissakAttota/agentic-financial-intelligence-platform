"""
Event Processor - Background event processing with retries, dead letter queue, and monitoring.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import traceback

from .event_bus import get_event_bus, Event, EventTypes

logger = logging.getLogger(__name__)


class ProcessingStatus(str, Enum):
    """Event processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    RETRYING = "retrying"


@dataclass
class ProcessingResult:
    """Result of event processing."""
    event_id: str
    status: ProcessingStatus
    result: Any = None
    error: Optional[str] = None
    attempts: int = 1
    processed_at: datetime = field(default_factory=datetime.utcnow)
    duration_ms: float = 0.0


@dataclass
class EventProcessorConfig:
    """Configuration for event processor."""
    max_concurrent: int = 10
    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    retry_backoff_multiplier: float = 2.0
    max_retry_delay_seconds: float = 300.0
    timeout_seconds: float = 60.0
    dead_letter_enabled: bool = True
    dead_letter_max_size: int = 10000
    batch_size: int = 1
    enable_metrics: bool = True


@dataclass
class ProcessorMetrics:
    """Metrics for event processor."""
    events_processed: int = 0
    events_succeeded: int = 0
    events_failed: int = 0
    events_retried: int = 0
    events_dead_lettered: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    last_processed_at: Optional[datetime] = None
    errors_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))


class EventProcessor:
    """
    Background event processor with retry logic, dead letter queue,
    and comprehensive monitoring.
    """
    
    def __init__(self, config: Optional[EventProcessorConfig] = None):
        self.config = config or EventProcessorConfig()
        self.event_bus = get_event_bus()
        self._running = False
        self._processor_tasks: List[asyncio.Task] = []
        self._handlers: Dict[str, Callable] = {}
        self._dead_letter_queue: List[Event] = []
        self._processing_status: Dict[str, ProcessingStatus] = {}
        self._metrics = ProcessorMetrics()
        self._retry_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
    
    def register_handler(
        self,
        event_type: str,
        handler: Callable,
        filter_fn: Optional[Callable[[Event], bool]] = None
    ) -> None:
        """Register a handler for an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((handler, filter_fn))
        logger.info(f"Registered handler for event type: {event_type}")
    
    async def start(self) -> None:
        """Start the event processor."""
        await self.event_bus.start()
        self._running = True
        
        # Start processor workers
        for i in range(self.config.max_concurrent):
            task = asyncio.create_task(self._worker(f"worker-{i}"))
            self._processor_tasks.append(task)
        
        # Start retry processor
        retry_task = asyncio.create_task(self._retry_processor())
        self._processor_tasks.append(retry_task)
        
        # Subscribe to all registered event types
        for event_type in self._handlers:
            self.event_bus.subscribe(
                self._handle_event,
                event_types=[event_type]
            )
        
        logger.info(f"Event processor started with {self.config.max_concurrent} workers")
    
    async def stop(self) -> None:
        """Stop the event processor."""
        self._running = False
        
        # Cancel all tasks
        for task in self._processor_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._processor_tasks:
            await asyncio.gather(*self._processor_tasks, return_exceptions=True)
        
        self._processor_tasks.clear()
        await self.event_bus.stop()
        logger.info("Event processor stopped")
    
    async def _worker(self, worker_id: str) -> None:
        """Background worker to process events from the queue."""
        logger.info(f"Worker {worker_id} started")
        
        while self._running:
            try:
                # Events are pushed via event bus subscription
                # This worker just monitors and processes retries
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def _handle_event(self, event: Event) -> None:
        """Handle incoming event from event bus."""
        if not self._running:
            return
        
        handlers = self._handlers.get(event.event_type, [])
        if not handlers:
            return
        
        for handler, filter_fn in handlers:
            # Check filter
            if filter_fn and not filter_fn(event):
                continue
            
            # Process with retry logic
            await self._process_with_retry(event, handler)
    
    async def _process_with_retry(self, event: Event, handler: Callable) -> None:
        """Process event with retry logic."""
        attempt = 1
        delay = self.config.retry_delay_seconds
        last_error = None
        
        while attempt <= self.config.max_retries + 1:
            start_time = datetime.utcnow()
            self._processing_status[event.event_id] = ProcessingStatus.PROCESSING
            
            try:
                # Execute handler with timeout
                if asyncio.iscoroutinefunction(handler):
                    result = await asyncio.wait_for(
                        handler(event),
                        timeout=self.config.timeout_seconds
                    )
                else:
                    result = handler(event)
                
                # Success
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                self._processing_status[event.event_id] = ProcessingStatus.COMPLETED
                self._metrics.events_processed += 1
                self._metrics.events_succeeded += 1
                self._metrics.total_duration_ms += duration_ms
                self._metrics.avg_duration_ms = self._metrics.total_duration_ms / self._metrics.events_processed
                self._metrics.last_processed_at = datetime.utcnow()
                
                logger.debug(f"Event {event.event_id} processed successfully in {duration_ms:.2f}ms")
                return
                
            except asyncio.TimeoutError:
                last_error = f"Timeout after {self.config.timeout_seconds}s"
                logger.warning(f"Event {event.event_id} timed out (attempt {attempt})")
                
            except Exception as e:
                last_error = str(e)
                error_type = type(e).__name__
                self._metrics.errors_by_type[error_type] += 1
                logger.warning(f"Event {event.event_id} failed (attempt {attempt}): {e}")
            
            # Check if we should retry
            if attempt <= self.config.max_retries:
                self._metrics.events_retried += 1
                self._processing_status[event.event_id] = ProcessingStatus.RETRYING
                
                # Add to retry queue with delay
                retry_time = datetime.utcnow() + timedelta(seconds=delay)
                await self._retry_queue.put((retry_time.timestamp(), event, handler, attempt + 1))
                
                delay = min(delay * self.config.retry_backoff_multiplier, self.config.max_retry_delay_seconds)
                attempt += 1
            else:
                # Max retries exceeded
                break
        
        # All retries failed
        await self._handle_failure(event, last_error)
    
    async def _handle_failure(self, event: Event, error: Optional[str]) -> None:
        """Handle permanent failure after all retries."""
        self._processing_status[event.event_id] = ProcessingStatus.FAILED
        self._metrics.events_failed += 1
        
        logger.error(f"Event {event.event_id} failed permanently: {error}")
        
        # Add to dead letter queue if enabled
        if self.config.dead_letter_enabled:
            await self._add_to_dead_letter(event, error)
    
    async def _add_to_dead_letter(self, event: Event, error: Optional[str]) -> None:
        """Add failed event to dead letter queue."""
        if len(self._dead_letter_queue) >= self.config.dead_letter_max_size:
            # Remove oldest
            self._dead_letter_queue.pop(0)
        
        dlq_entry = {
            "event": event,
            "error": error,
            "failed_at": datetime.utcnow(),
            "attempts": self.config.max_retries + 1
        }
        
        self._dead_letter_queue.append(dlq_entry)
        self._metrics.events_dead_lettered += 1
        self._processing_status[event.event_id] = ProcessingStatus.DEAD_LETTER
        
        logger.warning(f"Event {event.event_id} added to dead letter queue")
    
    async def _retry_processor(self) -> None:
        """Process retry queue."""
        logger.info("Retry processor started")
        
        while self._running:
            try:
                # Get next retry with timeout
                retry_item = await asyncio.wait_for(
                    self._retry_queue.get(),
                    timeout=1.0
                )
                
                retry_time, event, handler, attempt = retry_item
                
                # Check if it's time to retry
                now = datetime.utcnow().timestamp()
                if retry_time > now:
                    # Put back with remaining delay
                    await asyncio.sleep(retry_time - now)
                
                # Retry processing
                await self._process_with_retry(event, handler)
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Retry processor error: {e}")
                await asyncio.sleep(1)
        
        logger.info("Retry processor stopped")
    
    def get_dead_letter_queue(self) -> List[Dict[str, Any]]:
        """Get dead letter queue entries."""
        return [
            {
                "event_id": entry["event"].event_id,
                "event_type": entry["event"].event_type,
                "source": entry["event"].source,
                "payload": entry["event"].payload,
                "error": entry["error"],
                "failed_at": entry["failed_at"].isoformat(),
                "attempts": entry["attempts"]
            }
            for entry in self._dead_letter_queue
        ]
    
    def replay_dead_letter(self, index: int) -> bool:
        """Replay a dead letter event."""
        if 0 <= index < len(self._dead_letter_queue):
            entry = self._dead_letter_queue.pop(index)
            event = entry["event"]
            
            # Find handler
            handlers = self._handlers.get(event.event_type, [])
            if handlers:
                handler = handlers[0][0]  # Use first handler
                asyncio.create_task(self._process_with_retry(event, handler))
                return True
        return False
    
    def clear_dead_letter_queue(self) -> int:
        """Clear dead letter queue."""
        count = len(self._dead_letter_queue)
        self._dead_letter_queue.clear()
        return count
    
    def get_processing_status(self, event_id: str) -> Optional[ProcessingStatus]:
        """Get processing status for an event."""
        return self._processing_status.get(event_id)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get processor metrics."""
        return {
            "events_processed": self._metrics.events_processed,
            "events_succeeded": self._metrics.events_succeeded,
            "events_failed": self._metrics.events_failed,
            "events_retried": self._metrics.events_retried,
            "events_dead_lettered": self._metrics.events_dead_lettered,
            "avg_duration_ms": self._metrics.avg_duration_ms,
            "last_processed_at": self._metrics.last_processed_at.isoformat() if self._metrics.last_processed_at else None,
            "errors_by_type": dict(self._metrics.errors_by_type),
            "dead_letter_queue_size": len(self._dead_letter_queue),
            "registered_handlers": len(self._handlers),
            "is_running": self._running
        }
    
    def get_handler_stats(self) -> Dict[str, int]:
        """Get handler registration stats."""
        return {event_type: len(handlers) for event_type, handlers in self._handlers.items()}


# Global event processor instance
_event_processor: Optional[EventProcessor] = None


def get_event_processor(config: Optional[EventProcessorConfig] = None) -> EventProcessor:
    """Get or create the global event processor."""
    global _event_processor
    if _event_processor is None:
        _event_processor = EventProcessor(config)
    return _event_processor


async def close_event_processor() -> None:
    """Close the global event processor."""
    global _event_processor
    if _event_processor:
        await _event_processor.stop()
        _event_processor = None