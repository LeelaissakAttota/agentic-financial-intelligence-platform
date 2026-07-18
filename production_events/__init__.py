"""
Production Event System Module
Background workers, queue architecture, scheduler, event persistence, and retry system.
"""

from .queue import EventQueue, get_event_queue
from .worker import BackgroundWorker, get_background_worker
from .scheduler import EventScheduler, get_event_scheduler
from .persistence import EventPersistence, get_event_persistence
from .retry import RetryManager, get_retry_manager
from .event_bus import ProductionEventBus, get_production_event_bus

__all__ = [
    "EventQueue",
    "get_event_queue",
    "BackgroundWorker",
    "get_background_worker",
    "EventScheduler",
    "get_event_scheduler",
    "EventPersistence",
    "get_event_persistence",
    "RetryManager",
    "get_retry_manager",
    "ProductionEventBus",
    "get_production_event_bus",
]

__version__ = "1.0.0-phase9"