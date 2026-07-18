"""Performance tracking and profiling utilities."""

import time
import functools
import asyncio
import psutil
import threading
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict
import statistics


@dataclass
class PerformanceSnapshot:
    """A single performance measurement."""
    operation: str
    start_time: float
    end_time: float
    duration_ms: float
    memory_delta_mb: float
    cpu_percent: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        return self.duration_ms / 1000.0


@dataclass
class PerformanceStats:
    """Aggregated performance statistics."""
    operation: str
    count: int
    total_ms: float
    min_ms: float
    max_ms: float
    mean_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    std_dev_ms: float
    total_memory_mb: float
    avg_cpu_percent: float


class PerformanceTracker:
    """Tracks performance metrics for operations."""

    def __init__(self):
        self._measurements: List[PerformanceSnapshot] = []
        self._lock = threading.Lock()
        self._process = psutil.Process()

    def record(
        self,
        operation: str,
        start_time: float,
        end_time: float,
        memory_delta_mb: float = 0.0,
        cpu_percent: float = 0.0,
        **metadata
    ) -> PerformanceSnapshot:
        """Record a performance measurement."""
        snapshot = PerformanceSnapshot(
            operation=operation,
            start_time=start_time,
            end_time=end_time,
            duration_ms=(end_time - start_time) * 1000,
            memory_delta_mb=memory_delta_mb,
            cpu_percent=cpu_percent,
            metadata=metadata
        )

        with self._lock:
            self._measurements.append(snapshot)

        return snapshot

    def get_stats(self, operation: Optional[str] = None) -> List[PerformanceStats]:
        """Get aggregated statistics."""
        with self._lock:
            measurements = list(self._measurements)

        if operation:
            measurements = [m for m in measurements if m.operation == operation]

        # Group by operation
        grouped: Dict[str, List[PerformanceSnapshot]] = defaultdict(list)
        for m in measurements:
            grouped[m.operation].append(m)

        stats = []
        for op, measurements in grouped.items():
            durations = [m.duration_ms for m in measurements]
            memory = [m.memory_delta_mb for m in measurements]
            cpu = [m.cpu_percent for m in measurements]

            stats.append(PerformanceStats(
                operation=op,
                count=len(measurements),
                total_ms=sum(durations),
                min_ms=min(durations),
                max_ms=max(durations),
                mean_ms=statistics.mean(durations),
                median_ms=statistics.median(durations),
                p95_ms=self._percentile(durations, 95),
                p99_ms=self._percentile(durations, 99),
                std_dev_ms=statistics.stdev(durations) if len(durations) > 1 else 0.0,
                total_memory_mb=sum(memory),
                avg_cpu_percent=statistics.mean(cpu) if cpu else 0.0
            ))

        return stats

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def clear(self) -> None:
        """Clear all measurements."""
        with self._lock:
            self._measurements.clear()

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        stats = self.get_stats()
        return {
            "operations": len(stats),
            "total_measurements": sum(s.count for s in stats),
            "total_time_ms": sum(s.total_ms for s in stats),
            "by_operation": {
                s.operation: {
                    "count": s.count,
                    "mean_ms": round(s.mean_ms, 2),
                    "p95_ms": round(s.p95_ms, 2),
                    "p99_ms": round(s.p99_ms, 2),
                    "max_ms": round(s.max_ms, 2),
                    "total_ms": round(s.total_ms, 2)
                }
                for s in stats
            }
        }


class AsyncPerformanceTracker(PerformanceTracker):
    """Async-compatible performance tracker."""

    async def measure_async(
        self,
        operation: str,
        coro: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Measure async operation performance."""
        # Get baseline memory
        mem_before = self._process.memory_info().rss / 1024 / 1024
        cpu_before = self._process.cpu_percent(interval=0)

        start = time.perf_counter()
        try:
            result = await coro(*args, **kwargs)
            return result
        finally:
            end = time.perf_counter()
            mem_after = self._process.memory_info().rss / 1024 / 1024
            cpu_after = self._process.cpu_percent(interval=0)

            self.record(
                operation=operation,
                start_time=start,
                end_time=end,
                memory_delta_mb=mem_after - mem_before,
                cpu_percent=cpu_after
            )

    def measure_sync(
        self,
        operation: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Measure sync operation performance."""
        mem_before = self._process.memory_info().rss / 1024 / 1024
        cpu_before = self._process.cpu_percent(interval=0)

        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end = time.perf_counter()
            mem_after = self._process.memory_info().rss / 1024 / 1024
            cpu_after = self._process.cpu_percent(interval=0)

            self.record(
                operation=operation,
                start_time=start,
                end_time=end,
                memory_delta_mb=mem_after - mem_before,
                cpu_percent=cpu_after
            )


# Global trackers
performance_tracker = PerformanceTracker()
async_performance_tracker = AsyncPerformanceTracker()


# ==================== Decorators ====================
def track_performance(operation: Optional[str] = None):
    """Decorator to track function performance."""
    def decorator(func: Callable) -> Callable:
        op_name = operation or f"{func.__module__}.{func.__qualname__}"

        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await async_performance_tracker.measure_async(op_name, func, *args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return async_performance_tracker.measure_sync(op_name, func, *args, **kwargs)
            return sync_wrapper

    return decorator


@contextmanager
def measure(operation: str, **metadata):
    """Context manager to measure a code block."""
    tracker = async_performance_tracker
    mem_before = tracker._process.memory_info().rss / 1024 / 1024
    cpu_before = tracker._process.cpu_percent(interval=0)
    start = time.perf_counter()

    try:
        yield
    finally:
        end = time.perf_counter()
        mem_after = tracker._process.memory_info().rss / 1024 / 1024
        cpu_after = tracker._process.cpu_percent(interval=0)

        tracker.record(
            operation=operation,
            start_time=start,
            end_time=end,
            memory_delta_mb=mem_after - mem_before,
            cpu_percent=cpu_after,
            **metadata
        )


# ==================== Profiling ====================
class Profiler:
    """Context manager for detailed profiling."""

    def __init__(self, name: str):
        self.name = name
        self.start_time = 0
        self.end_time = 0
        self.snapshots: List[Dict[str, Any]] = []

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()

    def snapshot(self, label: str, **data):
        """Take a snapshot during profiling."""
        self.snapshots.append({
            "label": label,
            "elapsed_ms": (time.perf_counter() - self.start_time) * 1000,
            "memory_mb": psutil.Process().memory_info().rss / 1024 / 1024,
            **data
        })

    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000


def profile_block(name: str) -> Profiler:
    """Create a profiler context."""
    return Profiler(name)


# ==================== Memory Tracking ====================
class MemoryTracker:
    """Tracks memory usage over time."""

    def __init__(self):
        self._process = psutil.Process()
        self._snapshots: List[Dict[str, Any]] = []

    def snapshot(self, label: str = "") -> Dict[str, Any]:
        """Take a memory snapshot."""
        mem = self._process.memory_info()
        snap = {
            "label": label,
            "timestamp": time.time(),
            "rss_mb": mem.rss / 1024 / 1024,
            "vms_mb": mem.vms / 1024 / 1024,
            "percent": self._process.memory_percent()
        }
        self._snapshots.append(snap)
        return snap

    def get_growth(self) -> float:
        """Get memory growth since first snapshot in MB."""
        if len(self._snapshots) < 2:
            return 0.0
        return self._snapshots[-1]["rss_mb"] - self._snapshots[0]["rss_mb"]

    def get_peak(self) -> float:
        """Get peak memory usage in MB."""
        return max(s["rss_mb"] for s in self._snapshots) if self._snapshots else 0.0

    def clear(self) -> None:
        self._snapshots.clear()


# ==================== Resource Monitoring ====================
class ResourceMonitor:
    """Monitors system resources continuously."""

    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self._process = psutil.Process()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._snapshots: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start monitoring."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor, daemon=True)
        self._thread.start()

    def stop(self) -> List[Dict[str, Any]]:
        """Stop monitoring and return snapshots."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        with self._lock:
            return list(self._snapshots)

    def _monitor(self) -> None:
        while self._running:
            mem = self._process.memory_info()
            cpu = self._process.cpu_percent(interval=0)
            snap = {
                "timestamp": time.time(),
                "rss_mb": mem.rss / 1024 / 1024,
                "vms_mb": mem.vms / 1024 / 1024,
                "cpu_percent": cpu,
                "threads": self._process.num_threads(),
                "fds": self._process.num_fds() if hasattr(self._process, 'num_fds') else 0
            }
            with self._lock:
                self._snapshots.append(snap)
            time.sleep(self.interval)

    def get_stats(self) -> Dict[str, Any]:
        """Get resource usage statistics."""
        with self._lock:
            snapshots = list(self._snapshots)

        if not snapshots:
            return {}

        return {
            "duration_seconds": snapshots[-1]["timestamp"] - snapshots[0]["timestamp"],
            "memory": {
                "min_mb": min(s["rss_mb"] for s in snapshots),
                "max_mb": max(s["rss_mb"] for s in snapshots),
                "avg_mb": statistics.mean(s["rss_mb"] for s in snapshots),
                "growth_mb": snapshots[-1]["rss_mb"] - snapshots[0]["rss_mb"]
            },
            "cpu": {
                "min_percent": min(s["cpu_percent"] for s in snapshots),
                "max_percent": max(s["cpu_percent"] for s in snapshots),
                "avg_percent": statistics.mean(s["cpu_percent"] for s in snapshots)
            },
            "threads": {
                "min": min(s["threads"] for s in snapshots),
                "max": max(s["threads"] for s in snapshots)
            }
        }


# ==================== Reporting ====================
def generate_performance_report() -> Dict[str, Any]:
    """Generate a comprehensive performance report."""
    return {
        "timestamp": time.time(),
        "performance": performance_tracker.get_summary(),
        "async_performance": async_performance_tracker.get_summary(),
        "system": {
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024,
            "memory_available_gb": psutil.virtual_memory().available / 1024 / 1024 / 1024,
            "process": {
                "pid": psutil.Process().pid,
                "memory_mb": psutil.Process().memory_info().rss / 1024 / 1024,
                "cpu_percent": psutil.Process().cpu_percent(interval=0.1),
                "threads": psutil.Process().num_threads()
            }
        }
    }


def print_performance_report() -> None:
    """Print performance report to stdout."""
    import json
    report = generate_performance_report()
    print(json.dumps(report, indent=2, default=str))