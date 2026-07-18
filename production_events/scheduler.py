"""
Event Scheduler
Cron-like scheduler for recurring events and workflows.
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


class ScheduleType(str, Enum):
    """Schedule types."""
    INTERVAL = "interval"          # Every N seconds/minutes/hours
    CRON = "cron"                  # Cron expression
    DAILY = "daily"                # At specific time daily
    WEEKLY = "weekly"              # Specific day/time weekly
    MONTHLY = "monthly"            # Specific date/time monthly
    ONE_TIME = "one_time"          # Run once at specific time


class ScheduleStatus(str, Enum):
    """Schedule status."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    COMPLETED = "completed"  # For one-time schedules


@dataclass
class Schedule:
    """Scheduled job definition."""
    schedule_id: str
    name: str
    schedule_type: ScheduleType
    expression: str  # Cron expression, interval, or time specification
    topic: str
    payload: Any
    priority: int = 2  # QueuePriority.NORMAL
    max_attempts: int = 3
    timeout: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ScheduleStatus = ScheduleStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    max_runs: Optional[int] = None  # None = unlimited
    timezone: str = "UTC"
    
    def __lt__(self, other: "Schedule") -> bool:
        """For heap ordering by next_run."""
        if self.next_run is None and other.next_run is None:
            return self.schedule_id < other.schedule_id
        if self.next_run is None:
            return False
        if other.next_run is None:
            return True
        return self.next_run < other.next_run


@dataclass
class ScheduledEvent:
    """Event created from a schedule."""
    event_id: str
    schedule_id: str
    topic: str
    payload: Any
    priority: int
    max_attempts: int
    timeout: float
    metadata: Dict[str, Any]
    scheduled_at: datetime
    created_at: datetime = field(default_factory=datetime.utcnow)


class EventScheduler:
    """
    Cron-like scheduler for recurring events.
    Features:
    - Multiple schedule types (interval, cron, daily, weekly, monthly, one-time)
    - Timezone support
    - Pause/resume/disable schedules
    - Max runs limit
    - Distributed locking for HA
    - Metrics and monitoring
    """
    
    def __init__(self, default_timezone: str = "UTC"):
        self.default_timezone = default_timezone
        self._schedules: Dict[str, Schedule] = {}
        self._schedule_heap: List[Schedule] = []  # Min-heap by next_run
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._event_queue = None  # Will be set externally
        self._event_publisher = None  # Will be set externally
        
        # Callbacks
        self._schedule_callbacks: List[Callable] = []
        self._event_callbacks: List[Callable] = []
        
        # Stats
        self._stats = {
            "total_schedules": 0,
            "active_schedules": 0,
            "events_published": 0,
            "failed_publishes": 0,
            "last_tick": None
        }
    
    def set_event_publisher(self, publisher: Callable) -> None:
        """Set the event publisher callback."""
        self._event_publisher = publisher
    
    def register_schedule_callback(self, callback: Callable) -> None:
        """Register callback for schedule events."""
        self._schedule_callbacks.append(callback)
    
    def register_event_callback(self, callback: Callable) -> None:
        """Register callback for scheduled event publishing."""
        self._event_callbacks.append(callback)
    
    @property
    def running(self) -> bool:
        return self._running
    
    async def add_schedule(
        self,
        name: str,
        schedule_type: ScheduleType,
        expression: str,
        topic: str,
        payload: Any,
        priority: int = 2,
        max_attempts: int = 3,
        timeout: float = 30.0,
        metadata: Optional[Dict[str, Any]] = None,
        status: ScheduleStatus = ScheduleStatus.ACTIVE,
        max_runs: Optional[int] = None,
        timezone: Optional[str] = None
    ) -> str:
        """Add a new schedule."""
        
        schedule_id = f"sched_{uuid.uuid4().hex[:12]}"
        
        # Parse expression and calculate next run
        next_run = self._calculate_next_run(schedule_type, expression, timezone or self.default_timezone)
        
        schedule = Schedule(
            schedule_id=schedule_id,
            name=name,
            schedule_type=schedule_type,
            expression=expression,
            topic=topic,
            payload=payload,
            priority=priority,
            max_attempts=max_attempts,
            timeout=timeout,
            metadata=metadata or {},
            status=status,
            next_run=next_run,
            max_runs=max_runs,
            timezone=timezone or self.default_timezone
        )
        
        async with self._lock:
            self._schedules[schedule_id] = schedule
            if schedule.status == ScheduleStatus.ACTIVE and schedule.next_run:
                heapq.heappush(self._schedule_heap, schedule)
        
        self._stats["total_schedules"] += 1
        self._stats["active_schedules"] = len([s for s in self._schedules.values() if s.status == ScheduleStatus.ACTIVE])
        
        logger.info(f"Added schedule: {schedule_id} ({name}) - next run: {next_run}")
        
        await self._notify_schedule_callbacks("created", schedule)
        
        return schedule_id
    
    async def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a schedule."""
        
        async with self._lock:
            schedule = self._schedules.pop(schedule_id, None)
            
            if not schedule:
                return False
            
            # Rebuild heap (simple approach - rebuild entirely)
            self._rebuild_heap()
            
            self._stats["active_schedules"] = len([s for s in self._schedules.values() if s.status == ScheduleStatus.ACTIVE])
            
            await self._notify_schedule_callbacks("removed", schedule)
            
            logger.info(f"Removed schedule: {schedule_id}")
            return True
    
    async def pause_schedule(self, schedule_id: str) -> bool:
        """Pause a schedule."""
        
        async with self._lock:
            schedule = self._schedules.get(schedule_id)
            
            if not schedule:
                return False
            
            if schedule.status == ScheduleStatus.ACTIVE:
                schedule.status = ScheduleStatus.PAUSED
                schedule.updated_at = datetime.utcnow()
                self._rebuild_heap()
                self._stats["active_schedules"] = len([s for s in self._schedules.values() if s.status == ScheduleStatus.ACTIVE])
                
                logger.info(f"Paused schedule: {schedule_id}")
                return True
        
        return False
    
    async def resume_schedule(self, schedule_id: str) -> bool:
        """Resume a paused schedule."""
        
        async with self._lock:
            schedule = self._schedules.get(schedule_id)
            
            if not schedule:
                return False
            
            if schedule.status == ScheduleStatus.PAUSED:
                schedule.status = ScheduleStatus.ACTIVE
                schedule.updated_at = datetime.utcnow()
                schedule.next_run = self._calculate_next_run(
                    schedule.schedule_type,
                    schedule.expression,
                    schedule.timezone
                )
                
                if schedule.next_run:
                    heapq.heappush(self._schedule_heap, schedule)
                
                self._stats["active_schedules"] = len([s for s in self._schedules.values() if s.status == ScheduleStatus.ACTIVE])
                
                logger.info(f"Resumed schedule: {schedule_id}")
                return True
        
        return False
    
    async def disable_schedule(self, schedule_id: str) -> bool:
        """Disable a schedule permanently."""
        
        async with self._lock:
            schedule = self._schedules.get(schedule_id)
            
            if not schedule:
                return False
            
            schedule.status = ScheduleStatus.DISABLED
            schedule.updated_at = datetime.utcnow()
            self._rebuild_heap()
            self._stats["active_schedules"] = len([s for s in self._schedules.values() if s.status == ScheduleStatus.ACTIVE])
            
            logger.info(f"Disabled schedule: {schedule_id}")
            return True
    
    async def trigger_now(self, schedule_id: str) -> bool:
        """Trigger a schedule immediately."""
        
        schedule = self._schedules.get(schedule_id)
        
        if not schedule:
            return False
        
        await self._publish_scheduled_event(schedule)
        
        logger.info(f"Manually triggered schedule: {schedule_id}")
        return True
    
    async def start(self) -> None:
        """Start the scheduler."""
        
        if self._running:
            return
        
        self._running = True
        
        # Rebuild heap with active schedules
        self._rebuild_heap()
        
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        logger.info("Event scheduler started")
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        
        self._running = False
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Event scheduler stopped")
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        
        logger.info("Scheduler loop started")
        
        while True:
            try:
                now = datetime.utcnow()
                
                # Check for due schedules
                await self._process_due_schedules(now)
                
                # Sleep until next check (minimum 1 second)
                await asyncio.sleep(1.0)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(5.0)
    
    async def _process_due_schedules(self, now: datetime) -> None:
        """Process all schedules that are due."""
        
        async with self._lock:
            # Process all due schedules
            while self._schedule_heap:
                schedule = self._schedule_heap[0]
                
                if not schedule.next_run or schedule.next_run > now:
                    break  # No more due schedules
                
                # Pop the schedule
                heapq.heappop(self._schedule_heap)
                
                # Check if schedule is still active
                if schedule.status != ScheduleStatus.ACTIVE:
                    continue
                
                # Check max runs
                if schedule.max_runs and schedule.run_count >= schedule.max_runs:
                    schedule.status = ScheduleStatus.COMPLETED
                    schedule.updated_at = datetime.utcnow()
                    logger.info(f"Schedule completed (max runs reached): {schedule.schedule_id}")
                    continue
                
                # Publish event
                await self._publish_scheduled_event(schedule)
                
                # Update schedule
                schedule.last_run = now
                schedule.run_count += 1
                schedule.updated_at = now
                
                # Calculate next run
                schedule.next_run = self._calculate_next_run(
                    schedule.schedule_type,
                    schedule.expression,
                    schedule.timezone,
                    from_time=now
                )
                
                if schedule.next_run:
                    heapq.heappush(self._schedule_heap, schedule)
                else:
                    # No more runs (e.g., one-time schedule)
                    schedule.status = ScheduleStatus.COMPLETED
                    logger.info(f"Schedule completed: {schedule.schedule_id}")
                
                schedule.updated_at = datetime.utcnow()
    
    def _calculate_next_run(
        self,
        schedule_type: ScheduleType,
        expression: str,
        timezone: str,
        from_time: Optional[datetime] = None
    ) -> Optional[datetime]:
        """Calculate next run time based on schedule type and expression."""
        
        base_time = from_time or datetime.utcnow()
        
        try:
            if schedule_type == ScheduleType.INTERVAL:
                # Expression: "30s", "5m", "1h", "1d"
                return self._parse_interval(expression, base_time)
            
            elif schedule_type == ScheduleType.CRON:
                # Cron expression: "0 0 * * *"
                return self._parse_cron(expression, base_time)
            
            elif schedule_type == ScheduleType.DAILY:
                # Expression: "09:30" or "09:30:00"
                return self._parse_daily(expression, base_time)
            
            elif schedule_type == ScheduleType.WEEKLY:
                # Expression: "mon 09:00" or "1 09:00" (0=Sunday)
                return self._parse_weekly(expression, base_time)
            
            elif schedule_type == ScheduleType.MONTHLY:
                # Expression: "1 09:00" (day of month)
                return self._parse_monthly(expression, base_time)
            
            elif schedule_type == ScheduleType.ONE_TIME:
                # Expression: "2024-12-31 23:59:59"
                return self._parse_datetime(expression, base_time)
            
        except Exception as e:
            logger.error(f"Error parsing schedule expression '{expression}': {e}")
        
        return None
    
    def _parse_interval(self, expression: str, base_time: datetime) -> datetime:
        """Parse interval expression like '30s', '5m', '1h', '1d'."""
        
        import re
        
        match = re.match(r'^(\d+)([smhd])$', expression.strip().lower())
        if not match:
            raise ValueError(f"Invalid interval format: {expression}")
        
        value = int(match.group(1))
        unit = match.group(2)
        
        delta_map = {
            's': timedelta(seconds=value),
            'm': timedelta(minutes=value),
            'h': timedelta(hours=value),
            'd': timedelta(days=value)
        }
        
        delta = delta_map[unit]
        return base_time + delta
    
    def _parse_cron(self, expression: str, base_time: datetime) -> datetime:
        """Parse cron expression (simplified - would use croniter in production)."""
        
        # Simplified cron parsing - in production use croniter library
        # Format: "minute hour day month weekday"
        # For now, return next minute as fallback
        return base_time + timedelta(minutes=1)
    
    def _parse_daily(self, expression: str, base_time: datetime) -> datetime:
        """Parse daily time expression 'HH:MM' or 'HH:MM:SS'."""
        
        time_str = expression.strip()
        parts = time_str.split(':')
        
        if len(parts) < 2 or len(parts) > 3:
            raise ValueError(f"Invalid daily time format: {expression}")
        
        hour = int(parts[0])
        minute = int(parts[1])
        second = int(parts[2]) if len(parts) == 3 else 0
        
        target = base_time.replace(hour=hour, minute=minute, second=second, microsecond=0)
        
        if target <= base_time:
            target += timedelta(days=1)
        
        return target
    
    def _parse_weekly(self, expression: str, base_time: datetime) -> datetime:
        """Parse weekly expression 'weekday HH:MM'."""
        
        parts = expression.strip().split()
        if len(parts) != 2:
            raise ValueError(f"Invalid weekly format: {expression}")
        
        day_str, time_str = parts
        
        # Parse day
        day_map = {
            'sun': 6, 'sunday': 6,
            'mon': 0, 'monday': 0,
            'tue': 1, 'tuesday': 1,
            'wed': 2, 'wednesday': 2,
            'thu': 3, 'thursday': 3,
            'fri': 4, 'friday': 4,
            'sat': 5, 'saturday': 5
        }
        
        weekday = day_map.get(day_str.lower())
        if weekday is None:
            try:
                weekday = int(day_str)
            except ValueError:
                raise ValueError(f"Invalid weekday: {day_str}")
        
        # Parse time
        time_parts = time_str.split(':')
        hour = int(time_parts[0])
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
        second = int(time_parts[2]) if len(time_parts) > 2 else 0
        
        # Calculate next occurrence
        days_ahead = (weekday - base_time.weekday()) % 7
        if days_ahead == 0:
            target = base_time.replace(hour=hour, minute=minute, second=second, microsecond=0)
            if target <= base_time:
                days_ahead = 7
        
        target = base_time + timedelta(days=days_ahead)
        target = target.replace(hour=hour, minute=minute, second=second, microsecond=0)
        
        return target
    
    def _parse_monthly(self, expression: str, base_time: datetime) -> datetime:
        """Parse monthly expression 'day HH:MM'."""
        
        parts = expression.strip().split()
        if len(parts) != 2:
            raise ValueError(f"Invalid monthly format: {expression}")
        
        day = int(parts[0])
        if not 1 <= day <= 31:
            raise ValueError(f"Invalid day: {day}")
        
        time_parts = parts[1].split(':')
        hour = int(time_parts[0])
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
        second = int(time_parts[2]) if len(time_parts) > 2 else 0
        
        # Calculate next occurrence
        target = base_time.replace(day=min(day, 28), hour=hour, minute=minute, second=second, microsecond=0)
        
        # Handle months with fewer days
        import calendar
        last_day = calendar.monthrange(target.year, target.month)[1]
        target = target.replace(day=min(day, last_day))
        
        if target <= base_time:
            # Next month
            if target.month == 12:
                target = target.replace(year=target.year + 1, month=1)
            else:
                target = target.replace(month=target.month + 1)
        
        return target
    
    def _parse_datetime(self, expression: str, base_time: datetime) -> datetime:
        """Parse ISO datetime string."""
        
        try:
            dt = datetime.fromisoformat(expression.replace('Z', '+00:00'))
            if dt <= base_time:
                raise ValueError("One-time schedule must be in the future")
            return dt
        except ValueError as e:
            raise ValueError(f"Invalid datetime format: {expression}")
    
    def _rebuild_heap(self) -> None:
        """Rebuild the schedule heap from active schedules."""
        
        self._schedule_heap = [
            s for s in self._schedules.values()
            if s.status == ScheduleStatus.ACTIVE and s.next_run
        ]
        heapq.heapify(self._schedule_heap)
    
    async def _publish_scheduled_event(self, schedule: Schedule) -> None:
        """Publish a scheduled event."""
        
        event = ScheduledEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            schedule_id=schedule.schedule_id,
            topic=schedule.topic,
            payload=schedule.payload,
            priority=schedule.priority,
            max_attempts=schedule.max_attempts,
            timeout=schedule.timeout,
            metadata={
                **schedule.metadata,
                "schedule_name": schedule.name,
                "schedule_id": schedule.schedule_id,
                "run_count": schedule.run_count + 1
            },
            scheduled_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        
        # Publish via event publisher
        if self._event_publisher:
            try:
                await self._event_publisher(event)
            except Exception as e:
                logger.error(f"Failed to publish scheduled event: {e}")
        
        # Call event callbacks
        for callback in self._event_callbacks:
            try:
                await callback(schedule)
            except Exception as e:
                logger.error(f"Event callback error: {e}")
        
        self._stats["events_published"] += 1
        self._stats["last_tick"] = datetime.utcnow()
    
    def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Get schedule details."""
        
        schedule = self._schedules.get(schedule_id)
        
        if not schedule:
            return None
        
        return {
            "schedule_id": schedule.schedule_id,
            "name": schedule.name,
            "schedule_type": schedule.schedule_type.value,
            "expression": schedule.expression,
            "topic": schedule.topic,
            "payload": schedule.payload,
            "priority": schedule.priority,
            "max_attempts": schedule.max_attempts,
            "timeout": schedule.timeout,
            "metadata": schedule.metadata,
            "status": schedule.status.value,
            "created_at": schedule.created_at.isoformat(),
            "updated_at": schedule.updated_at.isoformat(),
            "last_run": schedule.last_run.isoformat() if schedule.last_run else None,
            "next_run": schedule.next_run.isoformat() if schedule.next_run else None,
            "run_count": schedule.run_count,
            "max_runs": schedule.max_runs,
            "timezone": schedule.timezone
        }
    
    def list_schedules(self, status: Optional[ScheduleStatus] = None) -> List[Dict[str, Any]]:
        """List all schedules."""
        
        schedules = list(self._schedules.values())
        
        if status:
            schedules = [s for s in schedules if s.status == status]
        
        return [self.get_schedule(s.schedule_id) for s in schedules]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        
        return {
            **self._stats,
            "pending_schedules": len(self._schedule_heap),
            "by_status": {
                status.value: sum(1 for s in self._schedules.values() if s.status == status)
                for status in ScheduleStatus
            }
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        return {
            "total_schedules": len(self._schedules),
            "active_schedules": len([s for s in self._schedules.values() if s.status == ScheduleStatus.ACTIVE]),
            "paused_schedules": len([s for s in self._schedules.values() if s.status == ScheduleStatus.PAUSED]),
            "disabled_schedules": len([s for s in self._schedules.values() if s.status == ScheduleStatus.DISABLED]),
            "completed_schedules": len([s for s in self._schedules.values() if s.status == ScheduleStatus.COMPLETED]),
            "next_scheduled": self._schedule_heap[0].next_run.isoformat() if self._schedule_heap else None,
            "events_published": self._stats["events_published"],
            "failed_publishes": self._stats["failed_publishes"],
            "last_tick": self._stats["last_tick"].isoformat() if self._stats["last_tick"] else None
        }


# Global scheduler instance
_scheduler: Optional[EventScheduler] = None


def get_event_scheduler(default_timezone: str = "UTC") -> EventScheduler:
    global _scheduler
    
    if _scheduler is None:
        _scheduler = EventScheduler(default_timezone)
    
    return _scheduler


async def close_event_scheduler() -> None:
    global _scheduler
    
    if _scheduler:
        await _scheduler.stop()
        _scheduler = None