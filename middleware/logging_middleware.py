"""
Request/Response Logging Middleware

Provides structured logging for all HTTP requests and responses
with correlation IDs, performance metrics, and security event detection.
"""
import time
import uuid
import json
from typing import Callable, Optional, Set
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.types import ASGIApp, Receive, Scope, Send

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
from monitoring.metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    REQUEST_IN_PROGRESS,
    ERROR_COUNT
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured HTTP request/response logging.

    Features:
    - Correlation ID propagation
    - Request/response timing
    - Structured JSON logging
    - Security event detection
    - Performance metrics
    - Configurable body logging
    """

    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: Optional[Set[str]] = None,
        log_request_body: bool = False,
        log_response_body: bool = False,
        max_body_size: int = 10000,
        sensitive_headers: Optional[Set[str]] = None,
        sensitive_fields: Optional[Set[str]] = None
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or {
            "/health",
            "/health/detailed",
            "/metrics",
            "/favicon.ico",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/ready",
            "/live"
        }
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_size = max_body_size
        self.sensitive_headers = sensitive_headers or {
            "authorization",
            "x-api-key",
            "cookie",
            "set-cookie",
            "x-csrf-token",
            "x-xsrf-token"
        }
        self.sensitive_fields = sensitive_fields or {
            "password",
            "token",
            "secret",
            "api_key",
            "apikey",
            "access_token",
            "refresh_token",
            "authorization",
            "credit_card",
            "ssn",
            "social_security"
        }
        self.logger = get_logger("http.request")
        self.security_logger = get_logger("http.security")
        self.settings = get_settings()

    def _should_log(self, path: str) -> bool:
        """Check if path should be logged."""
        return not any(path.startswith(excluded) for excluded in self.exclude_paths)

    def _sanitize_headers(self, headers: dict) -> dict:
        """Remove sensitive headers from log."""
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized

    def _sanitize_body(self, body: str) -> str:
        """Remove sensitive fields from body."""
        if not body:
            return body

        try:
            # Try to parse as JSON
            data = json.loads(body)
            return json.dumps(self._sanitize_dict(data))
        except (json.JSONDecodeError, TypeError):
            # Not JSON, check for sensitive patterns
            for field in self.sensitive_fields:
                if field in body.lower():
                    return "[REDACTED - contains sensitive data]"
            return body

    def _sanitize_dict(self, data: dict) -> dict:
        """Recursively sanitize dictionary."""
        sanitized = {}
        for key, value in data.items():
            if key.lower() in self.sensitive_fields:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_dict(v) if isinstance(v, dict) else v
                    for v in value
                ]
            else:
                sanitized[key] = value
        return sanitized

    def _detect_security_events(self, request: Request, body: Optional[str]) -> list:
        """Detect potential security events in request."""
        events = []

        # Check for SQL injection patterns
        sql_patterns = [
            r"(\bunion\b.*\bselect\b)",
            r"(\bselect\b.*\bfrom\b)",
            r"(\binsert\b.*\binto\b)",
            r"(\bupdate\b.*\bset\b)",
            r"(\bdelete\b.*\bfrom\b)",
            r"(\bdrop\b.*\btable\b)",
            r"(\bexec\b|\bexecute\b)",
            r"(;\s*--)",
            r"(\bor\s+1\s*=\s*1)",
            r"(\band\s+1\s*=\s*1)",
        ]

        # Check for prompt injection patterns
        prompt_patterns = [
            r"ignore\s+(previous|above|all)\s+(instructions|prompts|rules)",
            r"disregard\s+(previous|above|all)\s+(instructions|prompts|rules)",
            r"forget\s+(previous|above|all)\s+(instructions|prompts|rules)",
            r"you\s+are\s+now\s+(a|an)\s+",
            r"act\s+as\s+(a|an)\s+",
            r"pretend\s+to\s+be\s+",
            r"simulate\s+(a|an)\s+",
            r"roleplay\s+(as|a)\s+",
            r"jailbreak",
            r"bypass\s+(security|safety|guidelines)",
            r"override\s+(security|safety|guidelines)",
            r"developer\s+mode",
            r"admin\s+mode",
            r"system\s+prompt",
            r"<\|.*\|>",
            r"\[INST\].*\[/INST\]",
            r"<<SYS>>.*<</SYS>>",
        ]

        check_text = " ".join([
            str(request.url.path),
            str(request.query_params),
            body or ""
        ]).lower()

        import re
        for pattern in sql_patterns:
            if re.search(pattern, check_text, re.IGNORECASE):
                events.append({
                    "type": "sql_injection_attempt",
                    "pattern": pattern,
                    "severity": "high"
                })

        for pattern in prompt_patterns:
            if re.search(pattern, check_text, re.IGNORECASE):
                events.append({
                    "type": "prompt_injection_attempt",
                    "pattern": pattern,
                    "severity": "high"
                })

        # Check for unusual request sizes
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB
            events.append({
                "type": "large_request",
                "size_bytes": int(content_length),
                "severity": "medium"
            })

        # Check for suspicious user agents
        user_agent = request.headers.get("user-agent", "").lower()
        suspicious_agents = ["sqlmap", "nikto", "nmap", "burp", "zap", "w3af", "skipfish"]
        for agent in suspicious_agents:
            if agent in user_agent:
                events.append({
                    "type": "suspicious_user_agent",
                    "agent": agent,
                    "severity": "high"
                })

        return events

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

        # Read request body if needed
        request_body = None
        request_body_bytes = b""
        if self.log_request_body and method in ("POST", "PUT", "PATCH", "DELETE"):
            try:
                request_body_bytes = await request.body()
                if len(request_body_bytes) <= self.max_body_size:
                    request_body = request_body_bytes.decode("utf-8", errors="replace")
                else:
                    request_body = f"<body too large: {len(request_body_bytes)} bytes>"
            except Exception:
                request_body = "<failed to read body>"

        # Sanitize
        sanitized_headers = self._sanitize_headers(dict(request.headers))
        sanitized_body = self._sanitize_body(request_body) if request_body else None

        # Detect security events
        security_events = self._detect_security_events(request, request_body)

        # Log security events
        for event in security_events:
            self.security_logger.warning(
                f"Security event detected: {event['type']}",
                extra={
                    "event": event,
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "client_ip": client_ip,
                    "method": method,
                    "path": path
                }
            )

        # Log request
        self.logger.info(
            "HTTP Request",
            extra={
                "http_method": method,
                "http_path": path,
                "http_query": query_params,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "request_headers": sanitized_headers,
                "request_body": sanitized_body,
                "security_events": security_events if security_events else None,
                "correlation_id": correlation_id,
                "request_id": request_id
            }
        )

        # Track metrics
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=path).inc()
        request_start = time.perf_counter()

        # Process request
        response = None
        response_body = None
        response_body_bytes = b""
        status_code = 500
        error = None

        try:
            response = await call_next(request)
            status_code = response.status_code

            # Read response body if needed
            if self.log_response_body and hasattr(response, "body"):
                response_body_bytes = response.body
                if len(response_body_bytes) <= self.max_body_size:
                    response_body = response_body_bytes.decode("utf-8", errors="replace")
                else:
                    response_body = f"<body too large: {len(response_body_bytes)} bytes>"
            elif self.log_response_body and isinstance(response, StreamingResponse):
                # For streaming responses, we can't easily capture body
                response_body = "<streaming response>"
            elif self.log_response_body and hasattr(response, "body"):
                # Some response types have .body
                try:
                    response_body = response.body.decode("utf-8", errors="replace")
                except Exception:
                    response_body = "<binary response>"

        except Exception as e:
            error = e
            status_code = 500
            self.logger.error(
                "HTTP Request Failed",
                extra={
                    "http_method": method,
                    "http_path": path,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "correlation_id": correlation_id,
                    "request_id": request_id
                },
                exc_info=True
            )
            ERROR_COUNT.labels(
                component="http",
                error_type=type(e).__name__
            ).inc()
            raise
        finally:
            # Calculate latency
            latency = time.perf_counter() - request_start

            # Sanitize response body
            sanitized_response_body = self._sanitize_body(response_body) if response_body else None

            # Log response
            self.logger.info(
                "HTTP Response",
                extra={
                    "http_method": method,
                    "http_path": path,
                    "http_status": status_code,
                    "latency_ms": round(latency * 1000, 2),
                    "response_headers": self._sanitize_headers(dict(response.headers)) if response else {},
                    "response_body": sanitized_response_body,
                    "correlation_id": correlation_id,
                    "request_id": request_id
                }
            )

            # Track metrics
            REQUEST_LATENCY.labels(method=method, endpoint=path).observe(latency)
            REQUEST_COUNT.labels(
                method=method,
                endpoint=path,
                status=str(status_code)
            ).inc()
            REQUEST_IN_PROGRESS.labels(method=method, endpoint=path).dec()

            # Add correlation headers to response
            if response:
                response.headers["X-Correlation-ID"] = correlation_id
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Response-Time-MS"] = str(round(latency * 1000, 2))

            # Clear context
            clear_request_id()
            clear_correlation_id()

        return response


class RequestResponseLogger:
    """
    Standalone request/response logger for use outside middleware.
    """

    def __init__(self):
        self.logger = get_logger("http")
        self.security_logger = get_logger("http.security")

    def log_request(
        self,
        method: str,
        path: str,
        headers: dict = None,
        body: str = None,
        query_params: str = None,
        client_ip: str = None,
        user_agent: str = None,
        correlation_id: str = None,
        request_id: str = None
    ):
        """Log an outgoing or incoming request."""
        self.logger.info(
            "Request",
            extra={
                "http_method": method,
                "http_path": path,
                "http_query": query_params,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "request_headers": headers,
                "request_body": body,
                "correlation_id": correlation_id,
                "request_id": request_id
            }
        )

    def log_response(
        self,
        method: str,
        path: str,
        status_code: int,
        latency_ms: float,
        headers: dict = None,
        body: str = None,
        correlation_id: str = None,
        request_id: str = None
    ):
        """Log a response."""
        self.logger.info(
            "Response",
            extra={
                "http_method": method,
                "http_path": path,
                "http_status": status_code,
                "latency_ms": latency_ms,
                "response_headers": headers,
                "response_body": body,
                "correlation_id": correlation_id,
                "request_id": request_id
            }
        )

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        details: dict,
        request: Request = None,
        correlation_id: str = None,
        request_id: str = None
    ):
        """Log a security event."""
        extra = {
            "event_type": event_type,
            "severity": severity,
            "details": details,
            "correlation_id": correlation_id,
            "request_id": request_id
        }

        if request:
            extra.update({
                "client_ip": request.client.host if request.client else None,
                "method": request.method,
                "path": request.url.path,
                "user_agent": request.headers.get("User-Agent")
            })

        self.security_logger.warning(
            f"Security event: {event_type}",
            extra=extra
        )


# ==================== Dependency Injection ====================
request_response_logger = RequestResponseLogger()


def get_request_logger() -> RequestResponseLogger:
    """Get request/response logger instance."""
    return request_response_logger


# ==================== Export ====================
__all__ = [
    "RequestLoggingMiddleware",
    "RequestResponseLogger",
    "request_response_logger",
    "get_request_logger",
]