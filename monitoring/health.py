"""
Enhanced Health Checks Module

Provides comprehensive health checking for all system components.
"""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import asyncpg
import psutil
import redis.asyncio as redis

from config.settings import get_settings
from monitoring.metrics import health_checker, HealthCheck


@dataclass
class ComponentHealth:
    """Health status for a component."""
    name: str
    status: str  # healthy, degraded, unhealthy
    latency_ms: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class HealthCheckRegistry:
    """Registry for health checks."""

    def __init__(self):
        self._checks: Dict[str, Callable] = {}
        self._results: Dict[str, ComponentHealth] = {}

    def register(self, name: str, check_fn: Callable):
        """Register a health check function."""
        self._checks[name] = check_fn

    async def run_all(self) -> Dict[str, ComponentHealth]:
        """Run all registered health checks."""
        self._results = {}

        # Run checks concurrently
        tasks = {
            name: self._run_check(name, check_fn)
            for name, check_fn in self._checks.items()
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for (name, _), result in zip(tasks.items(), results):
            if isinstance(result, Exception):
                self._results[name] = ComponentHealth(
                    name=name,
                    status="unhealthy",
                    latency_ms=0,
                    message=f"Check failed: {str(result)}",
                    details={"error": str(result)}
                )
            else:
                self._results[name] = result

        return self._results

    async def _run_check(self, name: str, check_fn: Callable) -> ComponentHealth:
        """Run a single health check with timing."""
        start = time.perf_counter()
        try:
            if asyncio.iscoroutinefunction(check_fn):
                result = await check_fn()
            else:
                result = check_fn()

            latency_ms = (time.perf_counter() - start) * 1000

            if isinstance(result, ComponentHealth):
                result.latency_ms = latency_ms
                return result
            elif isinstance(result, dict):
                return ComponentHealth(
                    name=name,
                    status=result.get("status", "healthy"),
                    latency_ms=latency_ms,
                    message=result.get("message", "OK"),
                    details=result.get("details", {})
                )
            else:
                return ComponentHealth(
                    name=name,
                    status="healthy",
                    latency_ms=latency_ms,
                    message=str(result)
                )

        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            return ComponentHealth(
                name=name,
                status="unhealthy",
                latency_ms=latency_ms,
                message=f"Check failed: {str(e)}",
                details={"error": str(e), "type": type(e).__name__}
            )

    def get_overall_status(self) -> str:
        """Get overall system status."""
        if not self._results:
            return "unknown"

        statuses = [r.status for r in self._results.values()]

        if "unhealthy" in statuses:
            return "unhealthy"
        elif "degraded" in statuses:
            return "degraded"
        return "healthy"

    async def get_summary(self) -> Dict[str, Any]:
        """Get health summary."""
        results = await self.run_all()
        return {
            "status": self.get_overall_status(),
            "timestamp": time.time(),
            "components": {
                name: {
                    "status": health.status,
                    "latency_ms": round(health.latency_ms, 2),
                    "message": health.message,
                    "details": health.details
                }
                for name, health in results.items()
            }
        }


# ==================== Default Health Checks ====================
async def check_database() -> ComponentHealth:
    """Check PostgreSQL database connectivity."""
    settings = get_settings()

    try:
        conn = await asyncpg.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_db,
            timeout=5
        )

        # Test query
        result = await conn.fetchval("SELECT 1")
        await conn.close()

        if result == 1:
            return ComponentHealth(
                name="database",
                status="healthy",
                latency_ms=0,  # Will be set by runner
                message="Database connection successful",
                details={
                    "host": settings.postgres_host,
                    "port": settings.postgres_port,
                    "database": settings.postgres_db
                }
            )
        else:
            return ComponentHealth(
                name="database",
                status="degraded",
                latency_ms=0,
                message="Unexpected query result",
                details={"result": result}
            )

    except asyncpg.PostgresError as e:
        return ComponentHealth(
            name="database",
            status="unhealthy",
            latency_ms=0,
            message=f"Database error: {str(e)}",
            details={"error": str(e), "type": type(e).__name__}
        )
    except Exception as e:
        return ComponentHealth(
            name="database",
            status="unhealthy",
            latency_ms=0,
            message=f"Connection failed: {str(e)}",
            details={"error": str(e), "type": type(e).__name__}
        )


async def check_redis() -> ComponentHealth:
    """Check Redis connectivity."""
    settings = get_settings()

    try:
        client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            socket_timeout=5,
            socket_connect_timeout=5
        )

        result = await client.ping()
        await client.close()

        if result:
            return ComponentHealth(
                name="redis",
                status="healthy",
                latency_ms=0,
                message="Redis connection successful",
                details={
                    "host": settings.redis_host,
                    "port": settings.redis_port,
                    "db": settings.redis_db
                }
            )
        else:
            return ComponentHealth(
                name="redis",
                status="degraded",
                latency_ms=0,
                message="Redis ping returned false",
                details={}
            )

    except redis.RedisError as e:
        return ComponentHealth(
            name="redis",
            status="unhealthy",
            latency_ms=0,
            message=f"Redis error: {str(e)}",
            details={"error": str(e), "type": type(e).__name__}
        )
    except Exception as e:
        return ComponentHealth(
            name="redis",
            status="unhealthy",
            latency_ms=0,
            message=f"Connection failed: {str(e)}",
            details={"error": str(e), "type": type(e).__name__}
        )


async def check_chromadb() -> ComponentHealth:
    """Check ChromaDB connectivity."""
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        settings = get_settings()

        client = chromadb.HttpClient(
            host=settings.chromadb_host,
            port=settings.chromadb_port,
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        # Test connection
        collections = client.list_collections()
        await client.close()

        return ComponentHealth(
            name="chromadb",
            status="healthy",
            latency_ms=0,
            message="ChromaDB connection successful",
            details={
                "host": settings.chromadb_host,
                "port": settings.chromadb_port,
                "collections": len(collections)
            }
        )

    except Exception as e:
        return ComponentHealth(
            name="chromadb",
            status="unhealthy",
            latency_ms=0,
            message=f"ChromaDB connection failed: {str(e)}",
            details={"error": str(e), "type": type(e).__name__}
        )


def check_system_resources() -> ComponentHealth:
    """Check system resource usage."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Determine status based on thresholds
        status = "healthy"
        messages = []

        if cpu_percent > 90:
            status = "degraded"
            messages.append(f"High CPU: {cpu_percent:.1f}%")
        elif cpu_percent > 95:
            status = "unhealthy"
            messages.append(f"Critical CPU: {cpu_percent:.1f}%")

        if memory.percent > 90:
            status = "degraded" if status == "healthy" else status
            messages.append(f"High memory: {memory.percent:.1f}%")
        elif memory.percent > 95:
            status = "unhealthy"
            messages.append(f"Critical memory: {memory.percent:.1f}%")

        if disk.percent > 90:
            status = "degraded" if status == "healthy" else status
            messages.append(f"High disk: {disk.percent:.1f}%")
        elif disk.percent > 95:
            status = "unhealthy"
            messages.append(f"Critical disk: {disk.percent:.1f}%")

        message = "System resources OK" if not messages else "; ".join(messages)

        return ComponentHealth(
            name="system",
            status=status,
            latency_ms=0,
            message=message,
            details={
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory.percent, 1),
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": round(disk.percent, 1),
                "disk_free_gb": round(disk.free / (1024**3), 2)
            }
        )

    except Exception as e:
        return ComponentHealth(
            name="system",
            status="unhealthy",
            latency_ms=0,
            message=f"System check failed: {str(e)}",
            details={"error": str(e)}
        )


def check_llm_providers() -> ComponentHealth:
    """Check LLM provider configuration."""
    settings = get_settings()

    providers = {
        "openrouter": bool(settings.openrouter_api_key),
        "anthropic": bool(getattr(settings, 'anthropic_api_key', None)),
        "openai": bool(getattr(settings, 'openai_api_key', None)),
    }

    configured = [k for k, v in providers.items() if v]

    if not configured:
        return ComponentHealth(
            name="llm_providers",
            status="unhealthy",
            latency_ms=0,
            message="No LLM providers configured",
            details={"providers": providers}
        )
    elif len(configured) == 1:
        return ComponentHealth(
            name="llm_providers",
            status="degraded",
            latency_ms=0,
            message=f"Single LLM provider: {configured[0]}",
            details={"providers": providers, "configured": configured}
        )
    else:
        return ComponentHealth(
            name="llm_providers",
            status="healthy",
            latency_ms=0,
            message=f"Multiple LLM providers: {', '.join(configured)}",
            details={"providers": providers, "configured": configured}
        )


async def check_agent_system() -> ComponentHealth:
    """Check agent system health."""
    try:
        from agents.manager_agent import get_manager_agent
        manager = get_manager_agent()

        # Check registered agents
        agents = manager.registry.get_all_agents()
        agent_count = len(agents)

        return ComponentHealth(
            name="agent_system",
            status="healthy",
            latency_ms=0,
            message=f"Agent system operational with {agent_count} agents",
            details={
                "registered_agents": list(agents.keys()),
                "agent_count": agent_count
            }
        )

    except Exception as e:
        return ComponentHealth(
            name="agent_system",
            status="unhealthy",
            latency_ms=0,
            message=f"Agent system check failed: {str(e)}",
            details={"error": str(e), "type": type(e).__name__}
        )


# ==================== Registry Instance ====================
health_registry = HealthCheckRegistry()

# Register default checks
health_registry.register("database", check_database)
health_registry.register("redis", check_redis)
health_registry.register("chromadb", check_chromadb)
health_registry.register("system", check_system_resources)
health_registry.register("llm_providers", check_llm_providers)
health_registry.register("agent_system", check_agent_system)


# ==================== Integration with Metrics HealthChecker ====================
# Register with metrics health_checker for backward compatibility
health_checker.register_check("database", check_database)
health_checker.register_check("redis", check_redis)
health_checker.register_check("chromadb", check_chromadb)
health_checker.register_check("system", check_system_resources)
health_checker.register_check("llm_providers", check_llm_providers)
health_checker.register_check("agent_system", check_agent_system)


# ==================== API Endpoints Helper ====================
async def get_detailed_health() -> Dict[str, Any]:
    """Get detailed health status for all components."""
    results = await health_registry.run_all()

    return {
        "status": health_registry.get_overall_status(),
        "timestamp": time.time(),
        "components": {
            name: {
                "status": health.status,
                "latency_ms": round(health.latency_ms, 2),
                "message": health.message,
                "details": health.details
            }
            for name, health in results.items()
        }
    }


async def get_health_summary() -> Dict[str, Any]:
    """Get quick health summary."""
    results = await health_registry.run_all()

    healthy = sum(1 for h in results.values() if h.status == "healthy")
    degraded = sum(1 for h in results.values() if h.status == "degraded")
    unhealthy = sum(1 for h in results.values() if h.status == "unhealthy")

    return {
        "status": health_registry.get_overall_status(),
        "timestamp": time.time(),
        "counts": {
            "healthy": healthy,
            "degraded": degraded,
            "unhealthy": unhealthy,
            "total": len(results)
        },
        "issues": [
            {"component": name, "message": health.message}
            for name, health in results.items()
            if health.status != "healthy"
        ]
    }


# ==================== Readiness/Liveness Probes ====================
async def readiness_probe() -> Dict[str, Any]:
    """Kubernetes readiness probe - checks if service can handle requests."""
    # Critical components for readiness
    critical = ["database", "redis"]
    results = await health_registry.run_all()

    ready = all(
        results.get(c, ComponentHealth("", "unhealthy", 0, "")).status != "unhealthy"
        for c in critical
    )

    return {
        "ready": ready,
        "timestamp": time.time(),
        "critical_components": {
            c: results.get(c, ComponentHealth(c, "unknown", 0, "not checked")).status
            for c in critical
        }
    }


async def liveness_probe() -> Dict[str, Any]:
    """Kubernetes liveness probe - checks if service is alive."""
    # Just check basic system health
    system_health = check_system_resources()

    alive = system_health.status != "unhealthy"

    return {
        "alive": alive,
        "timestamp": time.time(),
        "system_status": system_health.status
    }