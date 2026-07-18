"""
Request/Response Logging Middleware

Provides structured logging for all HTTP requests and responses
with correlation IDs and performance metrics.
"""
import time
import uuid
from typing import Callable, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.types import ASGIApp

from config.logging import (
    get_logger,
    set_request_id,
    get_request_id,
    set_correlation_id,
    get_correlation_id,
    start_execution_timer,
    clear_request_id,
    clear_correlation_id,
    LoggingContext
)
from config.settings import get_settings


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response logging."""

    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: Optional[list] = None,
        log_request_body: bool = False,
        log_response_body: bool = False,
        max_body_size: int = 10000
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/health/detailed",
            "/metrics",
            "/favicon.ico",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_size = max_body_size
        self.logger = get_logger("http")

    def _should_log(self, path: str) -> bool:
        """Check if path should be logged."""
        return not any(path.startswith(excluded) for excluded in self.exclude_paths)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self._should_log(request.url.path):
            return await call_next(request)

        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request_id = str(uuid.uuid4())

        # Set context
        set_request_id(request_id)
        set_correlation_id(correlation_id)
        start_execution_timer()

        # Extract request info
        method = request.method
        path = request.url.path
        query_params = str(request.query_params) if request.query_params else ""
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")

        # Log request
        request_start = time.perf_counter()
        request_body = None

        if self.log_request_body and method in ("POST", "PUT", "PATCH"):
            try:
                body = await request.body()
                if len(body) <= self.max_body_size:
                    request_body = body.decode("utf-8", errors="replace")
                else:
                    request_body = f"<body too large: {len(body)} bytes>"
            except Exception:
                request_body = "<failed to read body>"

        self.logger.info(
            "HTTP Request",
            extra={
                "http_method": method,
                "http_path": path,
                "http_query": query_params,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "request_body": request_body,
                "correlation_id": correlation_id,
                "request_id": request_id
            }
        )

        # Process request
        response = None
        status_code = 500
        response_body = None
        error = None

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            error = e
            status_code = 500
            raise
        finally:
            request_duration = (time.perf_counter() - request_start) * 1000

            # Log response
            if response and self.log_response_body:
                try:
                    if isinstance(response, StreamingResponse):
                        response_body = "<streaming response>"
                    else:
                        body = b""
                        async for chunk in response.body_iterator:
                            body += chunk
                        if len(body) <= self.max_body_size:
                            response_body = body.decode("utf-8", errors="replace")
                        else:
                            response_body = f"<body too large: {len(body)} bytes>"
                except Exception:
                    response_body = "<failed to read response body>"

            # Determine log level
            log_level = "info"
            if status_code >= 500:
                log_level = "error"
            elif status_code >= 400:
                log_level = "warning"

            extra = {
                "http_method": method,
                "http_path": path,
                "http_status": status_code,
                "duration_ms": round(request_duration, 2),
                "client_ip": client_ip,
                "correlation_id": correlation_id,
                "request_id": request_id
            }

            if error:
                extra["error"] = str(error)
                extra["error_type"] = type(error).__name__

            if response_body:
                extra["response_body"] = response_body

            getattr(self.logger, log_level)(
                "HTTP Response",
                extra=extra
            )

            # Clear context
            clear_request_id()
            clear_correlation_id()

        # Add correlation ID to response headers
        if response:
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{request_duration:.2f}ms"

        return response


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware to propagate correlation IDs across service boundaries."""

    def __init__(self, app: ASGIApp, header_name: str = "X-Correlation-ID"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get or generate correlation ID
        correlation_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        set_correlation_id(correlation_id)

        # Add to request state for downstream use
        request.state.correlation_id = correlation_id

        response = await call_next(request)

        # Add to response headers
        response.headers[self.header_name] = correlation_id

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size."""

    def __init__(self, app: ASGIApp, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("Content-Length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_size:
                    return Response(
                        content=f"Request body too large. Maximum size: {self.max_size} bytes",
                        status_code=413,
                        headers={"Content-Type": "text/plain"}
                    )
            except ValueError:
                pass

        return await call_next(request)


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce request timeout."""

    def __init__(self, app: ASGIApp, timeout: float = 30.0):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            return Response(
                content=f"Request timeout after {self.timeout} seconds",
                status_code=504,
                headers={"Content-Type": "text/plain"}
            )


import asyncio
from starlette.responses import Response


class CompressionMiddleware(BaseHTTPMiddleware):
    """Middleware for response compression (gzip)."""

    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 500,
        compression_level: int = 6
    ):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compression_level = compression_level

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        import gzip

        response = await call_next(request)

        # Check if client accepts gzip
        accept_encoding = request.headers.get("Accept-Encoding", "")
        if "gzip" not in accept_encoding.lower():
            return response

        # Check content type
        content_type = response.headers.get("Content-Type", "")
        if not self._should_compress(content_type):
            return response

        # Check content length
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) < self.minimum_size:
            return response

        # Compress body
        if isinstance(response, StreamingResponse):
            # For streaming, we'd need to wrap the iterator
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        if len(body) < self.minimum_size:
            return response

        compressed = gzip.compress(body, compresslevel=self.compression_level)

        # Update headers
        response.headers["Content-Encoding"] = "gzip"
        response.headers["Content-Length"] = str(len(compressed))
        response.headers["Vary"] = "Accept-Encoding"

        # Return new response with compressed body
        return Response(
            content=compressed,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )

    def _should_compress(self, content_type: str) -> bool:
        compressible_types = [
            "text/",
            "application/json",
            "application/xml",
            "application/javascript",
            "application/x-javascript",
            "application/x-yaml",
        ]
        return any(content_type.startswith(t) for t in compressible_types)


def create_middleware_stack(app: ASGIApp, settings=None) -> ASGIApp:
    """Create the full middleware stack in correct order.

    Order (outer to inner):
    1. Security headers (outermost)
    2. Request size limit
    3. Timeout
    3. Correlation ID
    4. Request logging
    5. Rate limiting
    6. Compression (innermost)

    Returns the wrapped app.
    """
    if settings is None:
        settings = get_settings()

    # Order matters - outer wraps inner
    app = SecurityHeadersMiddleware(app)
    app = RequestSizeLimitMiddleware(app, max_size=settings.max_request_size if hasattr(settings, 'max_request_size') else 10_000_000)
    app = TimeoutMiddleware(app, timeout=settings.request_timeout if hasattr(settings, 'request_timeout') else 30.0)
    app = CorrelationIDMiddleware(app)
    app = RequestLoggingMiddleware(
        app,
        log_request_body=settings.log_request_body if hasattr(settings, 'log_request_body') else False,
        log_response_body=settings.log_response_body if hasattr(settings, 'log_response_body') else False,
        max_body_size=settings.max_log_body_size if hasattr(settings, 'max_log_body_size') else 10000
    )
    app = CompressionMiddleware(app)

    return app


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # HSTS (only in production with HTTPS)
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response