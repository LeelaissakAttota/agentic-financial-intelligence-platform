"""
Circuit Breaker Middleware

Implements circuit breaker pattern for external service calls
and internal components to prevent cascade failures.
"""
import asyncio
import time
from enum import Enum
from typing import Callable, Optional, Dict, Any, TypeVar, Generic
from dataclasses import dataclass, field
from functools import wraps
from contextlib import asynccontextmanager

from config.logging import get_logger


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5          # Failures before opening
    success_threshold: int = 3          # Successes in half-open before closing
    timeout: float = 30.0               # Seconds before trying half-open
    half_open_max_calls: int = 3        # Max calls in half-open state
    excluded_exceptions: tuple = ()     # Exceptions that don't count as failures


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    total_calls: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changed_at: float = field(default_factory=time.time)

    def record_success(self):
        self.success_count += 1
        self.total_calls += 1
        self.last_success_time = time.time()

    def record_failure(self):
        self.failure_count += 1
        self.total_calls += 1
        self.last_failure_time = time.time()


class CircuitBreaker:
    """
    Circuit breaker implementation for fault tolerance.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failure threshold exceeded, requests blocked
    - HALF_OPEN: Testing recovery, limited requests allowed
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()
        self._half_open_calls = 0
        self.logger = get_logger(f"circuit_breaker.{name}")

    @property
    def state(self) -> CircuitState:
        """Get current state, checking for auto-transition."""
        if self.stats.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.stats.last_failure_time and \
               time.time() - self.stats.last_failure_time >= self.config.timeout:
                return CircuitState.HALF_OPEN
        return self.stats.state

    async def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to new state."""
        old_state = self.stats.state
        self.stats.state = new_state
        self.stats.state_changed_at = time.time()

        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self.stats.success_count = 0

        self.logger.info(
            f"Circuit breaker '{self.name}' state changed: {old_state.value} -> {new_state.value}",
            extra={
                "circuit_name": self.name,
                "old_state": old_state.value,
                "new_state": new_state.value,
                "failure_count": self.stats.failure_count,
                "success_count": self.stats.success_count
            }
        )

    def is_available(self) -> bool:
        """Check if requests are allowed."""
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.config.half_open_max_calls
        return False

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Any exception from the wrapped function
        """
        # Check availability
        if not self.is_available():
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is {self.state.value}"
            )

        # Handle half-open call limit
        if self.state == CircuitState.HALF_OPEN:
            async with self._lock:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' half-open call limit reached"
                    )
                self._half_open_calls += 1

        try:
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Record success
            async with self._lock:
                self._on_success()

            return result

        except Exception as e:
            # Check if exception should be ignored
            if isinstance(e, self.config.excluded_exceptions):
                raise

            # Record failure
            async with self._lock:
                self._on_failure()

            raise

    def _on_success(self) -> None:
        """Handle successful call."""
        self.stats.record_success()

        if self.state == CircuitState.HALF_OPEN:
            if self.stats.success_count >= self.config.success_threshold:
                asyncio.create_task(self._transition_to(CircuitState.CLOSED))

        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.stats.failure_count = 0

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.stats.record_failure()

        if self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open goes back to open
            asyncio.create_task(self._transition_to(CircuitState.OPEN))

        elif self.state == CircuitState.CLOSED:
            if self.stats.failure_count >= self.config.failure_threshold:
                asyncio.create_task(self._transition_to(CircuitState.OPEN))

    def reset(self) -> None:
        """Manually reset circuit breaker."""
        self.stats = CircuitBreakerStats()
        self._half_open_calls = 0
        self.logger.info(f"Circuit breaker '{self.name}' manually reset")

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "total_calls": self.stats.total_calls,
            "failure_rate": (
                self.stats.failure_count / self.stats.total_calls
                if self.stats.total_calls > 0 else 0
            ),
            "last_failure_time": self.stats.last_failure_time,
            "last_success_time": self.stats.last_success_time,
            "state_duration": time.time() - self.stats.state_changed_at,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout,
                "half_open_max_calls": self.config.half_open_max_calls
            }
        }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}

    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)

    def remove(self, name: str) -> bool:
        """Remove circuit breaker."""
        if name in self._breakers:
            del self._breakers[name]
            return True
        return False

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get stats for all circuit breakers."""
        return {
            name: breaker.get_stats()
            for name, breaker in self._breakers.items()
        }

    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()


# Global registry
circuit_breaker_registry = CircuitBreakerRegistry()


# ==================== Decorator ====================
def circuit_breaker(
    name: Optional[str] = None,
    config: Optional[CircuitBreakerConfig] = None,
    registry: Optional[CircuitBreakerRegistry] = None
):
    """
    Decorator to add circuit breaker protection to a function.

    Usage:
        @circuit_breaker("external_api", failure_threshold=3)
        async def call_external_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        breaker_name = name or f"{func.__module__}.{func.__qualname__}"
        reg = registry or circuit_breaker_registry
        breaker = reg.get_or_create(breaker_name, config)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(breaker.call(func, *args, **kwargs))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ==================== Context Manager ====================
@asynccontextmanager
async def circuit_breaker_context(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
    registry: Optional[CircuitBreakerRegistry] = None
):
    """
    Context manager for circuit breaker.

    Usage:
        async with circuit_breaker_context("db_query") as breaker:
            result = await db.execute(query)
    """
    reg = registry or circuit_breaker_registry
    breaker = reg.get_or_create(name, config)

    if not breaker.is_available():
        raise CircuitBreakerOpenError(f"Circuit breaker '{name}' is {breaker.state.value}")

    try:
        yield breaker
    except Exception as e:
        # Failure is recorded by the breaker.call method
        # but we need to record it manually since we're not using .call()
        if not isinstance(e, breaker.config.excluded_exceptions):
            async with breaker._lock:
                breaker._on_failure()
        raise


# ==================== HTTP Client Integration ====================
class CircuitBreakerHTTPClient:
    """HTTP client with circuit breaker for each host."""

    def __init__(self, registry: Optional[CircuitBreakerRegistry] = None):
        self.registry = registry or circuit_breaker_registry
        self._client = None

    async def _get_client(self):
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _get_host(self, url: str) -> str:
        from urllib.parse import urlparse
        return urlparse(url).netloc

    async def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> Any:
        """Make HTTP request with circuit breaker."""
        host = self._get_host(url)
        breaker_name = f"http_{host}"
        breaker = self.registry.get_or_create(
            breaker_name,
            CircuitBreakerConfig(
                failure_threshold=5,
                timeout=30.0,
                excluded_exceptions=(asyncio.TimeoutError,)
            )
        )

        client = await self._get_client()

        async def _make_request():
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

        return await breaker.call(_make_request)

    async def get(self, url: str, **kwargs) -> Any:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> Any:
        return await self.request("POST", url, **kwargs)

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


# ==================== Database Integration ====================
class CircuitBreakerDB:
    """Database connection with circuit breaker."""

    def __init__(
        self,
        pool: Any,
        registry: Optional[CircuitBreakerRegistry] = None,
        name: str = "database"
    ):
        self.pool = pool
        self.registry = registry or circuit_breaker_registry
        self.breaker = self.registry.get_or_create(
            name,
            CircuitBreakerConfig(
                failure_threshold=3,
                timeout=15.0,
                excluded_exceptions=(asyncio.TimeoutError,)
            )
        )

    async def execute(self, query: str, *args) -> Any:
        """Execute query with circuit breaker."""
        async def _execute():
            async with self.pool.acquire() as conn:
                return await conn.execute(query, *args)

        return await self.breaker.call(_execute)

    async def fetch(self, query: str, *args) -> Any:
        """Fetch with circuit breaker."""
        async def _fetch():
            async with self.pool.acquire() as conn:
                return await conn.fetch(query, *args)

        return await self.breaker.call(_fetch)

    async def fetchrow(self, query: str, *args) -> Any:
        """Fetch row with circuit breaker."""
        async def _fetchrow():
            async with self.pool.acquire() as conn:
                return await conn.fetchrow(query, *args)

        return await self.breaker.call(_fetchrow)

    async def fetchval(self, query: str, *args) -> Any:
        """Fetch value with circuit breaker."""
        async def _fetchval():
            async with self.pool.acquire() as conn:
                return await conn.fetchval(query, *args)

        return await self.breaker.call(_fetchval)


# ==================== Export ====================
__all__ = [
    "CircuitState",
    "CircuitBreakerConfig",
    "CircuitBreakerStats",
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "CircuitBreakerRegistry",
    "circuit_breaker_registry",
    "circuit_breaker",
    "circuit_breaker_context",
    "CircuitBreakerHTTPClient",
    "CircuitBreakerDB",
]