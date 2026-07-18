"""
Monitoring & Metrics Module

Provides Prometheus metrics collection for:
- Request latency
- LLM latency
- Database latency
- Agent execution time
- Token usage
- Memory/CPU usage
- Error counts
"""
import time
import functools
from typing import Callable, Any, Optional
from contextlib import contextmanager
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST

# Create custom registry
registry = CollectorRegistry()

# ==================== Request Metrics ====================
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=registry
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=registry
)

REQUEST_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "endpoint"],
    registry=registry
)

# ==================== LLM Metrics ====================
LLM_REQUEST_COUNT = Counter(
    "llm_requests_total",
    "Total LLM requests",
    ["model", "provider", "status"],
    registry=registry
)

LLM_LATENCY = Histogram(
    "llm_request_duration_seconds",
    "LLM request latency in seconds",
    ["model", "provider"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
    registry=registry
)

LLM_TOKEN_USAGE = Counter(
    "llm_tokens_total",
    "Total LLM tokens used",
    ["model", "provider", "type"],  # type: prompt, completion, total
    registry=registry
)

LLM_COST = Counter(
    "llm_cost_usd_total",
    "Total LLM cost in USD",
    ["model", "provider"],
    registry=registry
)

# ==================== Database Metrics ====================
DB_QUERY_COUNT = Counter(
    "db_queries_total",
    "Total database queries",
    ["operation", "table", "status"],
    registry=registry
)

DB_QUERY_LATENCY = Histogram(
    "db_query_duration_seconds",
    "Database query latency in seconds",
    ["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
    registry=registry
)

DB_POOL_SIZE = Gauge(
    "db_pool_size",
    "Database connection pool size",
    ["state"],  # active, idle
    registry=registry
)

DB_POOL_CHECKOUTS = Counter(
    "db_pool_checkouts_total",
    "Total pool checkouts",
    ["status"],  # success, failed
    registry=registry
)

# ==================== Agent Metrics ====================
AGENT_EXECUTION_COUNT = Counter(
    "agent_executions_total",
    "Total agent executions",
    ["agent", "status"],
    registry=registry
)

AGENT_EXECUTION_LATENCY = Histogram(
    "agent_execution_duration_seconds",
    "Agent execution latency in seconds",
    ["agent"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
    registry=registry
)

AGENT_CONTEXT_SIZE = Histogram(
    "agent_context_size_bytes",
    "Agent context size in bytes",
    ["agent"],
    buckets=(100, 1000, 10000, 50000, 100000, 500000, 1000000),
    registry=registry
)

# ==================== Vector Search Metrics ====================
VECTOR_SEARCH_COUNT = Counter(
    "vector_searches_total",
    "Total vector searches",
    ["collection", "status"],
    registry=registry
)

VECTOR_SEARCH_LATENCY = Histogram(
    "vector_search_duration_seconds",
    "Vector search latency in seconds",
    ["collection"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=registry
)

VECTOR_SEARCH_RESULTS = Histogram(
    "vector_search_results_count",
    "Number of results returned by vector search",
    ["collection"],
    buckets=(1, 5, 10, 25, 50, 100, 200),
    registry=registry
)

# ==================== Cache Metrics ====================
CACHE_HIT_COUNT = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_type"],  # memory, redis
    registry=registry
)

CACHE_MISS_COUNT = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache_type"],
    registry=registry
)

CACHE_LATENCY = Histogram(
    "cache_operation_duration_seconds",
    "Cache operation latency in seconds",
    ["cache_type", "operation"],  # get, set, delete
    buckets=(0.0001, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1),
    registry=registry
)

# ==================== System Metrics ====================
MEMORY_USAGE = Gauge(
    "process_memory_bytes",
    "Process memory usage in bytes",
    ["type"],  # rss, vms
    registry=registry
)

CPU_USAGE = Gauge(
    "process_cpu_percent",
    "Process CPU usage percentage",
    registry=registry
)

# ==================== Error Metrics ====================
ERROR_COUNT = Counter(
    "errors_total",
    "Total errors",
    ["component", "error_type"],
    registry=registry
)

# ==================== Business Metrics ====================
ANALYSIS_REQUESTS = Counter(
    "analysis_requests_total",
    "Total analysis requests",
    ["company", "status"],
    registry=registry
)

REPORT_GENERATED = Counter(
    "reports_generated_total",
    "Total reports generated",
    ["report_type", "format"],
    registry=registry
)

KNOWLEDGE_GRAPH_OPERATIONS = Counter(
    "knowledge_graph_operations_total",
    "Knowledge graph operations",
    ["operation", "status"],
    registry=registry
)

PATTERN_DETECTIONS = Counter(
    "pattern_detections_total",
    "Pattern detections",
    ["pattern_type", "status"],
    registry=registry
)

PORTFOLIO_OPERATIONS = Counter(
    "portfolio_operations_total",
    "Portfolio operations",
    ["operation", "status"],
    registry=registry
)

ALERT_TRIGGERED = Counter(
    "alerts_triggered_total",
    "Alerts triggered",
    ["alert_type", "severity", "channel"],
    registry=registry
)


# ==================== Decorator Helpers ====================
def track_latency(histogram: Histogram, labels: Optional[dict] = None) -> Callable:
    """Decorator to track function latency."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = time.perf_counter() - start
                if labels:
                    histogram.labels(**labels).observe(elapsed)
                else:
                    histogram.observe(elapsed)
        return wrapper
    return decorator


def count_calls(counter: Counter, labels: Optional[dict] = None, on_error: bool = False) -> Callable:
    """Decorator to count function calls."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                result = func(*args, **kwargs)
                if not on_error:
                    if labels:
                        counter.labels(**labels).inc()
                    else:
                        counter.inc()
                return result
            except Exception as e:
                if on_error:
                    if labels:
                        counter.labels(**labels).inc()
                    else:
                        counter.inc()
                raise
        return wrapper
    return decorator


@contextmanager
def track_request(method: str, endpoint: str):
    """Context manager to track HTTP request metrics."""
    REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
    start = time.perf_counter()
    status = "500"
    try:
        yield
        status = "200"
    except Exception:
        status = "500"
        raise
    finally:
        elapsed = time.perf_counter() - start
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(elapsed)
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()


@contextmanager
def track_llm(model: str, provider: str):
    """Context manager to track LLM request metrics."""
    start = time.perf_counter()
    status = "success"
    try:
        yield
    except Exception:
        status = "error"
        LLM_REQUEST_COUNT.labels(model=model, provider=provider, status="error").inc()
        raise
    finally:
        elapsed = time.perf_counter() - start
        LLM_LATENCY.labels(model=model, provider=provider).observe(elapsed)
        LLM_REQUEST_COUNT.labels(model=model, provider=provider, status=status).inc()


@contextmanager
def track_db_query(operation: str, table: str):
    """Context manager to track database query metrics."""
    start = time.perf_counter()
    status = "success"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        elapsed = time.perf_counter() - start
        DB_QUERY_LATENCY.labels(operation=operation, table=table).observe(elapsed)
        DB_QUERY_COUNT.labels(operation=operation, table=table, status=status).inc()


@contextmanager
def track_agent(agent_name: str):
    """Context manager to track agent execution metrics."""
    start = time.perf_counter()
    status = "success"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        elapsed = time.perf_counter() - start
        AGENT_EXECUTION_LATENCY.labels(agent=agent_name).observe(elapsed)
        AGENT_EXECUTION_COUNT.labels(agent=agent_name, status=status).inc()


@contextmanager
def track_vector_search(collection: str):
    """Context manager to track vector search metrics."""
    start = time.perf_counter()
    status = "success"
    result_count = 0
    try:
        yield lambda count: setattr(track_vector_search, "_count", count)
        result_count = getattr(track_vector_search, "_count", 0)
    except Exception:
        status = "error"
        raise
    finally:
        elapsed = time.perf_counter() - start
        VECTOR_SEARCH_LATENCY.labels(collection=collection).observe(elapsed)
        VECTOR_SEARCH_COUNT.labels(collection=collection, status=status).inc()
        if result_count > 0:
            VECTOR_SEARCH_RESULTS.labels(collection=collection).observe(result_count)


def record_cache_hit(cache_type: str):
    """Record a cache hit."""
    CACHE_HIT_COUNT.labels(cache_type=cache_type).inc()


def record_cache_miss(cache_type: str):
    """Record a cache miss."""
    CACHE_MISS_COUNT.labels(cache_type=cache_type).inc()


def record_error(component: str, error_type: str):
    """Record an error."""
    ERROR_COUNT.labels(component=component, error_type=error_type).inc()


def update_system_metrics():
    """Update system metrics (memory, CPU)."""
    import psutil
    process = psutil.Process()

    mem = process.memory_info()
    MEMORY_USAGE.labels(type="rss").set(mem.rss)
    MEMORY_USAGE.labels(type="vms").set(mem.vms)

    CPU_USAGE.set(process.cpu_percent(interval=0.1))


# ==================== Metrics Endpoint ====================
def get_metrics() -> bytes:
    """Generate Prometheus metrics output."""
    update_system_metrics()
    return generate_latest(registry)


def get_content_type() -> str:
    """Get Prometheus content type."""
    return CONTENT_TYPE_LATEST


# ==================== Health Checks ====================
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class HealthCheck:
    """Health check result."""
    name: str
    status: str  # healthy, degraded, unhealthy
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: float = 0

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()


class HealthChecker:
    """Aggregates health checks from multiple components."""

    def __init__(self):
        self.checks: List[HealthCheck] = []
        self._check_functions: Dict[str, Callable] = {}

    def register_check(self, name: str, check_fn: Callable) -> None:
        """Register a health check function."""
        self._check_functions[name] = check_fn

    async def run_checks(self) -> Dict[str, Any]:
        """Run all registered health checks."""
        self.checks = []

        for name, check_fn in self._check_functions.items():
            try:
                if hasattr(check_fn, "__call__"):
                    import asyncio
                    if asyncio.iscoroutinefunction(check_fn):
                        result = await check_fn()
                    else:
                        result = check_fn()
                else:
                    result = check_fn()

                if isinstance(result, HealthCheck):
                    self.checks.append(result)
                elif isinstance(result, dict):
                    self.checks.append(HealthCheck(
                        name=name,
                        status=result.get("status", "healthy"),
                        message=result.get("message", "OK"),
                        details=result.get("details")
                    ))
                else:
                    self.checks.append(HealthCheck(
                        name=name,
                        status="healthy",
                        message=str(result)
                    ))

            except Exception as e:
                self.checks.append(HealthCheck(
                    name=name,
                    status="unhealthy",
                    message=f"Check failed: {str(e)}",
                    details={"error": str(e)}
                ))

        # Determine overall status
        statuses = [c.status for c in self.checks]
        if "unhealthy" in statuses:
            overall = "unhealthy"
        elif "degraded" in statuses:
            overall = "degraded"
        else:
            overall = "healthy"

        return {
            "status": overall,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status,
                    "message": c.message,
                    "details": c.details,
                    "timestamp": c.timestamp
                }
                for c in self.checks
            ],
            "timestamp": time.time()
        }


# Global health checker
health_checker = HealthChecker()


def register_health_check(name: str, check_fn: Callable) -> None:
    """Register a health check."""
    health_checker.register_check(name, check_fn)


async def get_health_status() -> Dict[str, Any]:
    """Get overall health status."""
    return await health_checker.run_checks()