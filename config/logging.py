"""
Structured Logging Module

Provides JSON logging with correlation IDs, request tracking,
and performance metrics.
"""
import logging
import json
import sys
import time
import uuid
import contextvars
from typing import Any, Optional, Dict
from datetime import datetime
from pathlib import Path

from config.settings import get_settings

# Context variables for correlation tracking
request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)
correlation_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("correlation_id", default=None)
agent_name_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("agent_name", default=None)
execution_start_var: contextvars.ContextVar[Optional[float]] = contextvars.ContextVar("execution_start", default=None)


class JSONFormatter(logging.Formatter):
    """JSON log formatter with structured fields."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation context
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id

        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_data["correlation_id"] = correlation_id

        agent_name = agent_name_var.get()
        if agent_name:
            log_data["agent_name"] = agent_name

        # Add execution time if available
        exec_start = execution_start_var.get()
        if exec_start:
            log_data["execution_time_ms"] = round((time.time() - exec_start) * 1000, 2)

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName", "relativeCreated",
                "thread", "threadName", "exc_info", "exc_text", "stack_info"
            }:
                log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter with correlation context."""

    def format(self, record: logging.LogRecord) -> str:
        parts = [
            f"{datetime.utcnow().isoformat()}Z",
            f"[{record.levelname}]",
            f"{record.name}",
        ]

        request_id = request_id_var.get()
        if request_id:
            parts.append(f"[req:{request_id[:8]}]")

        correlation_id = correlation_id_var.get()
        if correlation_id:
            parts.append(f"[corr:{correlation_id[:8]}]")

        agent_name = agent_name_var.get()
        if agent_name:
            parts.append(f"[{agent_name}]")

        parts.append(record.getMessage())

        exec_start = execution_start_var.get()
        if exec_start:
            parts.append(f"(exec: {(time.time() - exec_start) * 1000:.1f}ms)")

        return " ".join(parts)


def setup_logging(
    level: Optional[str] = None,
    format_type: Optional[str] = None,
    log_file: Optional[str] = None,
    max_size: Optional[int] = None,
    backup_count: Optional[int] = None,
) -> logging.Logger:
    """
    Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        format_type: 'json' or 'text'
        log_file: Optional log file path
        max_size: Max log file size in bytes
        backup_count: Number of backup files

    Returns:
        Root logger instance
    """
    settings = get_settings()

    level = level or settings.log_level
    format_type = format_type or settings.log_format
    log_file = log_file or settings.log_file
    max_size = max_size or settings.log_max_size
    backup_count = backup_count or settings.log_backup_count

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Choose formatter
    if format_type == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count,
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


# Correlation ID Management
def set_request_id(request_id: Optional[str] = None) -> str:
    """Set request ID in context. Generates if not provided."""
    rid = request_id or str(uuid.uuid4())
    request_id_var.set(rid)
    return rid


def get_request_id() -> Optional[str]:
    """Get current request ID."""
    return request_id_var.get()


def clear_request_id() -> None:
    """Clear request ID from context."""
    request_id_var.set(None)


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Set correlation ID in context. Generates if not provided."""
    cid = correlation_id or str(uuid.uuid4())
    correlation_id_var.set(cid)
    return cid


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID."""
    return correlation_id_var.get()


def clear_correlation_id() -> None:
    """Clear correlation ID from context."""
    correlation_id_var.set(None)


def set_agent_name(agent_name: Optional[str] = None) -> None:
    """Set agent name in context."""
    agent_name_var.set(agent_name)


def get_agent_name() -> Optional[str]:
    """Get current agent name."""
    return agent_name_var.get()


def start_execution_timer() -> float:
    """Start execution timer and return start time."""
    start = time.time()
    execution_start_var.set(start)
    return start


def get_execution_time_ms() -> Optional[float]:
    """Get execution time in milliseconds since timer started."""
    exec_start = execution_start_var.get()
    if exec_start:
        return round((time.time() - exec_start) * 1000, 2)
    return None


def clear_execution_timer() -> None:
    """Clear execution timer."""
    execution_start_var.set(None)


class LoggingContext:
    """Context manager for structured logging with correlation."""

    def __init__(
        self,
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        agent_name: Optional[str] = None,
    ):
        self.request_id = request_id
        self.correlation_id = correlation_id
        self.agent_name = agent_name
        self.start_time: Optional[float] = None

    def __enter__(self) -> "LoggingContext":
        self.start_time = start_execution_timer()
        if self.request_id:
            set_request_id(self.request_id)
        else:
            set_request_id()

        if self.correlation_id:
            set_correlation_id(self.correlation_id)

        if self.agent_name:
            set_agent_name(self.agent_name)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        clear_request_id()
        clear_correlation_id()
        set_agent_name(None)
        clear_execution_timer()

    def log(self, level: int, message: str, **kwargs: Any) -> None:
        """Log with current context."""
        logger = get_logger(self.agent_name or "app")
        logger.log(level, message, extra=kwargs)


def log_execution(
    logger: logging.Logger,
    level: int,
    message: str,
    **kwargs: Any,
) -> None:
    """Log with execution time and context."""
    exec_time = get_execution_time_ms()
    if exec_time:
        kwargs["execution_time_ms"] = exec_time
    logger.log(level, message, extra=kwargs)