"""
Rate Limiting Middleware

Implements token bucket rate limiting with Redis backend
and in-memory fallback for single-instance deployments.
"""
import time
import asyncio
from typing import Optional, Dict, Any, Tuple, Union, List, Callable
from dataclasses import dataclass, field
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp

from config.settings import get_settings
from config.logging import get_logger


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int
    tokens: float
    refill_rate: float  # tokens per second
    last_refill: float = field(default_factory=time.time)

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if successful."""
        now = time.time()
        # Refill tokens
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def get_retry_after(self, tokens: int = 1) -> float:
        """Get seconds until enough tokens are available."""
        if self.tokens >= tokens:
            return 0
        return (tokens - self.tokens) / self.refill_rate


class InMemoryRateLimiter:
    """In-memory rate limiter using token buckets."""

    def __init__(self, default_limit: int = 100, default_window: int = 60):
        self.default_limit = default_limit
        self.default_window = default_window
        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()

    def _get_bucket_key(self, identifier: str, endpoint: str = "") -> str:
        """Generate bucket key."""
        return f"{identifier}:{endpoint}"

    async def check_rate_limit(
        self,
        identifier: str,
        endpoint: str = "",
        limit: Optional[int] = None,
        window: Optional[int] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit for identifier.

        Returns:
            (allowed, headers_dict)
        """
        limit = limit or self.default_limit
        window = window or self.default_window
        refill_rate = limit / window
        key = self._get_bucket_key(identifier, endpoint)

        async with self._lock:
            if key not in self._buckets:
                self._buckets[key] = TokenBucket(
                    capacity=limit,
                    tokens=limit,
                    refill_rate=refill_rate
                )

            bucket = self._buckets[key]
            allowed = bucket.consume(1)

            headers = {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(max(0, int(bucket.tokens))),
                "X-RateLimit-Reset": str(int(time.time() + bucket.get_retry_after()))
            }

            return allowed, headers

    async def reset(self, identifier: str, endpoint: str = "") -> None:
        """Reset rate limit for identifier."""
        key = self._get_bucket_key(identifier, endpoint)
        async with self._lock:
            self._buckets.pop(key, None)

    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        return {
            "active_buckets": len(self._buckets),
            "default_limit": self.default_limit,
            "default_window": self.default_window
        }


class RedisRateLimiter:
    """Redis-backed distributed rate limiter."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_limit: int = 100,
        default_window: int = 60,
        key_prefix: str = "ratelimit:"
    ):
        self.default_limit = default_limit
        self.default_window = default_window
        self.key_prefix = key_prefix
        self._client = None
        self._host = host
        self._port = port
        self._db = db
        self._password = password

    async def _get_client(self):
        """Get or create Redis client."""
        if self._client is None:
            import redis.asyncio as redis
            self._client = redis.Redis(
                host=self._host,
                port=self._port,
                db=self._db,
                password=self._password,
                decode_responses=True
            )
        return self._client

    async def check_rate_limit(
        self,
        identifier: str,
        endpoint: str = "",
        limit: Optional[int] = None,
        window: Optional[int] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit using Redis sliding window."""
        limit = limit or self.default_limit
        window = window or self.default_window
        key = f"{self.key_prefix}{identifier}:{endpoint}"
        now = time.time()
        window_start = now - window

        client = await self._get_client()

        # Use sorted set for sliding window
        pipe = client.pipeline()

        # Remove expired entries
        pipe.zremrangebyscore(key, 0, window_start)

        # Count current requests
        pipe.zcard(key)

        # Add current request
        pipe.zadd(key, {str(now): now})

        # Set expiry
        pipe.expire(key, window + 1)

        results = await pipe.execute()
        current_count = results[1]

        allowed = current_count < limit

        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(max(0, limit - current_count - 1)),
            "X-RateLimit-Reset": str(int(now + window))
        }

        if not allowed:
            # Remove the request we just added
            await client.zrem(key, str(now))

        return allowed, headers

    async def reset(self, identifier: str, endpoint: str = "") -> None:
        """Reset rate limit for identifier."""
        key = f"{self.key_prefix}{identifier}:{endpoint}"
        client = await self._get_client()
        await client.delete(key)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with multiple strategies."""

    def __init__(
        self,
        app: ASGIApp,
        limiter: Optional[Union[InMemoryRateLimiter, RedisRateLimiter]] = None,
        identifier_header: str = "X-Forwarded-For",
        fallback_identifier: str = "default",
        exclude_paths: Optional[list] = None,
        custom_limits: Optional[Dict[str, Dict[str, int]]] = None
    ):
        super().__init__(app)

        settings = get_settings()

        # Create limiter if not provided
        if limiter is None:
            if settings.rate_limit_enabled and settings.redis_host:
                try:
                    limiter = RedisRateLimiter(
                        host=settings.redis_host,
                        port=settings.redis_port,
                        db=settings.redis_db,
                        password=settings.redis_password,
                        default_limit=settings.rate_limit_requests,
                        default_window=settings.rate_limit_window
                    )
                except Exception:
                    limiter = InMemoryRateLimiter(
                        default_limit=settings.rate_limit_requests,
                        default_window=settings.rate_limit_window
                    )
            else:
                limiter = InMemoryRateLimiter(
                    default_limit=settings.rate_limit_requests,
                    default_window=settings.rate_limit_window
                )

        self.limiter = limiter
        self.identifier_header = identifier_header
        self.fallback_identifier = fallback_identifier
        self.exclude_paths = exclude_paths or [
            "/health",
            "/health/detailed",
            "/metrics",
            "/favicon.ico",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
        self.custom_limits = custom_limits or {}
        self.logger = get_logger("ratelimit")

    def _get_identifier(self, request: Request) -> str:
        """Extract identifier from request."""
        # Try header first
        identifier = request.headers.get(self.identifier_header)
        if identifier:
            # Take first IP if comma-separated
            return identifier.split(",")[0].strip()

        # Try client host
        if request.client:
            return request.client.host

        return self.fallback_identifier

    def _get_custom_limit(self, path: str) -> Optional[Dict[str, int]]:
        """Get custom limit for path."""
        for pattern, limits in self.custom_limits.items():
            if path.startswith(pattern):
                return limits
        return None

    def _should_limit(self, path: str) -> bool:
        """Check if path should be rate limited."""
        return not any(path.startswith(excluded) for excluded in self.exclude_paths)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self._should_limit(request.url.path):
            return await call_next(request)

        identifier = self._get_identifier(request)
        custom_limit = self._get_custom_limit(request.url.path)

        try:
            allowed, headers = await self.limiter.check_rate_limit(
                identifier=identifier,
                endpoint=request.url.path,
                limit=custom_limit.get("limit") if custom_limit else None,
                window=custom_limit.get("window") if custom_limit else None
            )

            if not allowed:
                self.logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "identifier": identifier,
                        "path": request.url.path,
                        "method": request.method
                    }
                )

                return JSONResponse(
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Limit: {headers.get('X-RateLimit-Limit')} per window"
                    },
                    status_code=429,
                    headers=headers
                )

            # Add rate limit headers to successful response
            response = await call_next(request)
            for key, value in headers.items():
                response.headers[key] = value
            return response

        except Exception as e:
            self.logger.error(f"Rate limiter error: {e}")
            # Fail open - allow request through if limiter fails
            return await call_next(request)


# ==================== Decorator for Function-Level Rate Limiting ====================
def rate_limit(
    limit: int = 10,
    window: int = 60,
    key_func: Optional[Callable] = None,
    limiter: Optional[Union[InMemoryRateLimiter, RedisRateLimiter]] = None
):
    """Decorator to rate limit a function."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get or create limiter
            nonlocal limiter
            if limiter is None:
                settings = get_settings()
                limiter = InMemoryRateLimiter(
                    default_limit=limit,
                    default_window=window
                )

            # Generate key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = f"{func.__module__}.{func.__qualname__}"

            allowed, _ = await limiter.check_rate_limit(key, limit=limit, window=window)

            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded for {func.__name__}"
                )

            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(async_wrapper(*args, **kwargs))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ==================== Adaptive Rate Limiter ====================
class AdaptiveRateLimiter:
    """Rate limiter that adapts based on system load."""

    def __init__(
        self,
        base_limiter: Union[InMemoryRateLimiter, RedisRateLimiter],
        min_limit: int = 10,
        max_limit: int = 1000,
        adjustment_factor: float = 0.1
    ):
        self.base_limiter = base_limiter
        self.min_limit = min_limit
        self.max_limit = max_limit
        self.adjustment_factor = adjustment_factor
        self._current_limit = None

    async def check_rate_limit(
        self,
        identifier: str,
        endpoint: str = "",
        limit: Optional[int] = None,
        window: Optional[int] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit with adaptive adjustment."""
        import psutil

        # Get system load
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent

        # Adjust limit based on load
        if self._current_limit is None:
            self._current_limit = limit or self.max_limit

        # Reduce limit under high load
        if cpu_percent > 80 or memory_percent > 85:
            self._current_limit = max(
                self.min_limit,
                int(self._current_limit * (1 - self.adjustment_factor))
            )
        elif cpu_percent < 50 and memory_percent < 70:
            self._current_limit = min(
                self.max_limit,
                int(self._current_limit * (1 + self.adjustment_factor))
            )

        effective_limit = limit or self._current_limit

        return await self.base_limiter.check_rate_limit(
            identifier, endpoint, effective_limit, window
        )

    def get_current_limit(self) -> int:
        return self._current_limit or self.max_limit