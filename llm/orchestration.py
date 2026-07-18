"""
LLM Orchestration - Automatic model routing based on task requirements.

Routes requests to optimal models based on:
- Cost optimization (cheapest adequate model)
- Latency optimization (fastest adequate model)  
- Quality optimization (best model for complex reasoning)
- Capability matching (vision, code, reasoning, etc.)
"""
import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Set
import logging

from llm.openrouter_client import OpenRouterClient
from config.settings import get_settings

logger = logging.getLogger(__name__)


class OptimizationGoal(str, Enum):
    """Optimization goals for model selection."""
    COST = "cost"
    LATENCY = "latency"
    QUALITY = "quality"
    BALANCED = "balanced"


class ModelCapability(str, Enum):
    """Model capabilities."""
    REASONING = "reasoning"
    CODING = "coding"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    EXTRACTION = "extraction"
    CHAT = "chat"
    VISION = "vision"


@dataclass
class ModelProfile:
    """Profile of a model with its characteristics."""
    name: str
    provider: str
    capabilities: List[ModelCapability]
    max_tokens: int
    context_window: int
    cost_per_1k_input: float  # USD
    cost_per_1k_output: float  # USD
    avg_latency_ms: int
    quality_score: float  # 0-1
    supports_json: bool = True
    supports_streaming: bool = True
    supports_tools: bool = True


@dataclass
class RoutingDecision:
    """Result of routing decision."""
    model: str
    provider: str
    reason: str
    estimated_cost: float
    estimated_latency_ms: int
    confidence: float
    fallback_models: List[str] = field(default_factory=list)


class ModelRegistry:
    """Registry of available models with their profiles."""

    def __init__(self):
        self.models: Dict[str, ModelProfile] = {}
        self._initialize_models()

    def _initialize_models(self):
        """Initialize model profiles."""
        # OpenRouter models with typical characteristics
        models = [
            # High-quality reasoning models
            ModelProfile(
                name="anthropic/claude-3.5-sonnet",
                provider="Anthropic",
                capabilities=[ModelCapability.REASONING, ModelCapability.ANALYSIS, ModelCapability.CODING, ModelCapability.CREATIVE],
                max_tokens=8192,
                context_window=200000,
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015,
                avg_latency_ms=2000,
                quality_score=0.95,
                supports_tools=True
            ),
            ModelProfile(
                name="anthropic/claude-3-opus",
                provider="Anthropic",
                capabilities=[ModelCapability.REASONING, ModelCapability.ANALYSIS, ModelCapability.CODING],
                max_tokens=4096,
                context_window=200000,
                cost_per_1k_input=0.015,
                cost_per_1k_output=0.075,
                avg_latency_ms=3000,
                quality_score=0.98,
                supports_tools=True
            ),
            ModelProfile(
                name="openai/gpt-4o",
                provider="OpenAI",
                capabilities=[ModelCapability.REASONING, ModelCapability.ANALYSIS, ModelCapability.CODING, ModelCapability.VISION],
                max_tokens=4096,
                context_window=128000,
                cost_per_1k_input=0.005,
                cost_per_1k_output=0.015,
                avg_latency_ms=1500,
                quality_score=0.93,
                supports_tools=True
            ),
            ModelProfile(
                name="openai/gpt-4-turbo",
                provider="OpenAI",
                capabilities=[ModelCapability.REASONING, ModelCapability.ANALYSIS, ModelCapability.CODING],
                max_tokens=4096,
                context_window=128000,
                cost_per_1k_input=0.01,
                cost_per_1k_output=0.03,
                avg_latency_ms=2000,
                quality_score=0.92,
                supports_tools=True
            ),
            # Balanced models
            ModelProfile(
                name="google/gemini-pro-1.5",
                provider="Google",
                capabilities=[ModelCapability.REASONING, ModelCapability.ANALYSIS, ModelCapability.CODING, ModelCapability.VISION],
                max_tokens=8192,
                context_window=1000000,
                cost_per_1k_input=0.00125,
                cost_per_1k_output=0.005,
                avg_latency_ms=1800,
                quality_score=0.88,
                supports_tools=True
            ),
            # Fast/cheap models
            ModelProfile(
                name="anthropic/claude-3-haiku",
                provider="Anthropic",
                capabilities=[ModelCapability.SUMMARIZATION, ModelCapability.EXTRACTION, ModelCapability.CHAT],
                max_tokens=4096,
                context_window=200000,
                cost_per_1k_input=0.00025,
                cost_per_1k_output=0.00125,
                avg_latency_ms=500,
                quality_score=0.75,
                supports_tools=True
            ),
            ModelProfile(
                name="openai/gpt-4o-mini",
                provider="OpenAI",
                capabilities=[ModelCapability.SUMMARIZATION, ModelCapability.EXTRACTION, ModelCapability.CHAT, ModelCapability.CODING],
                max_tokens=16384,
                context_window=128000,
                cost_per_1k_input=0.00015,
                cost_per_1k_output=0.0006,
                avg_latency_ms=800,
                quality_score=0.82,
                supports_tools=True
            ),
            ModelProfile(
                name="deepseek/deepseek-chat",
                provider="DeepSeek",
                capabilities=[ModelCapability.CODING, ModelCapability.REASONING, ModelCapability.CHAT],
                max_tokens=4096,
                context_window=32000,
                cost_per_1k_input=0.00014,
                cost_per_1k_output=0.00028,
                avg_latency_ms=1000,
                quality_score=0.80,
                supports_tools=True
            ),
            ModelProfile(
                name="mistral/mistral-7b-instruct",
                provider="Mistral",
                capabilities=[ModelCapability.CHAT, ModelCapability.EXTRACTION],
                max_tokens=8192,
                context_window=32000,
                cost_per_1k_input=0.00007,
                cost_per_1k_output=0.00007,
                avg_latency_ms=400,
                quality_score=0.70,
                supports_tools=False
            ),
        ]

        for model in models:
            self.models[model.name] = model

    def get_model(self, name: str) -> Optional[ModelProfile]:
        """Get model profile by name."""
        return self.models.get(name)

    def get_models_by_capability(self, capability: ModelCapability) -> List[ModelProfile]:
        """Get all models supporting a capability."""
        return [m for m in self.models.values() if capability in m.capabilities]

    def get_all_models(self) -> List[ModelProfile]:
        """Get all model profiles."""
        return list(self.models.values())


class LLMRouter:
    """
    Intelligent LLM router that selects optimal model based on task requirements
    and optimization goals.
    """

    def __init__(self):
        self.registry = ModelRegistry()
        self.client = OpenRouterClient()
        self.settings = get_settings()

        # Routing history for learning
        self.routing_history: List[Dict[str, Any]] = []

        # Default optimization goal
        self.default_goal = OptimizationGoal.BALANCED

        # Task-to-capability mapping
        self.task_capability_map = {
            "financial_analysis": [ModelCapability.ANALYSIS, ModelCapability.REASONING],
            "investment_thesis": [ModelCapability.REASONING, ModelCapability.ANALYSIS, ModelCapability.CREATIVE],
            "risk_assessment": [ModelCapability.REASONING, ModelCapability.ANALYSIS],
            "sentiment_analysis": [ModelCapability.ANALYSIS, ModelCapability.EXTRACTION],
            "news_summarization": [ModelCapability.SUMMARIZATION, ModelCapability.EXTRACTION],
            "code_generation": [ModelCapability.CODING, ModelCapability.REASONING],
            "data_extraction": [ModelCapability.EXTRACTION],
            "entity_resolution": [ModelCapability.EXTRACTION, ModelCapability.ANALYSIS],
            "pattern_detection": [ModelCapability.ANALYSIS, ModelCapability.REASONING],
            "report_generation": [ModelCapability.CREATIVE, ModelCapability.SUMMARIZATION],
            "chat": [ModelCapability.CHAT],
            "planning": [ModelCapability.REASONING, ModelCapability.ANALYSIS],
            "tool_use": [ModelCapability.REASONING],
        }

        # Complexity thresholds
        self.complexity_thresholds = {
            "simple": 0.3,
            "moderate": 0.6,
            "complex": 0.8,
            "expert": 0.95
        }

    def route(
        self,
        task_type: str,
        complexity: str = "moderate",
        required_capabilities: Optional[List[ModelCapability]] = None,
        max_cost: Optional[float] = None,
        max_latency_ms: Optional[int] = None,
        goal: OptimizationGoal = None,
        prefer_model: Optional[str] = None,
        require_tools: bool = True,
        require_json: bool = True,
        context_length: int = 4000
    ) -> RoutingDecision:
        """
        Route to optimal model based on task requirements.

        Args:
            task_type: Type of task (e.g., "financial_analysis", "investment_thesis")
            complexity: simple, moderate, complex, expert
            required_capabilities: Specific capabilities needed
            max_cost: Maximum acceptable cost per 1k tokens
            max_latency_ms: Maximum acceptable latency
            goal: Optimization goal (cost, latency, quality, balanced)
            prefer_model: Preferred model if available
            require_tools: Whether tool calling is needed
            require_json: Whether JSON mode is needed
            context_length: Required context window

        Returns:
            RoutingDecision with selected model and metadata
        """
        goal = goal or self.default_goal
        complexity_score = self.complexity_thresholds.get(complexity, 0.6)

        # Get required capabilities from task type
        task_caps = self.task_capability_map.get(task_type, [ModelCapability.ANALYSIS])
        all_required = set(task_caps)
        if required_capabilities:
            all_required.update(required_capabilities)

        # Filter candidate models
        candidates = self._filter_candidates(
            all_required,
            max_cost,
            max_latency_ms,
            require_tools,
            require_json,
            context_length,
            complexity_score
        )

        if not candidates:
            # Fallback to any model
            candidates = self.registry.get_all_models()
            if not candidates:
                raise ValueError("No models available")

        # Score and rank candidates
        scored = self._score_candidates(candidates, goal, complexity_score, prefer_model)

        if not scored:
            raise ValueError("No suitable models found")

        # Select best
        best = scored[0]

        # Build fallback chain
        fallbacks = [c["model"].name for c in scored[1:4]]

        # Build decision
        decision = RoutingDecision(
            model=best["model"].name,
            provider=best["model"].provider,
            reason=self._build_reason(best, goal, complexity, all_required),
            estimated_cost=self._estimate_cost(best["model"]),
            estimated_latency_ms=best["model"].avg_latency_ms,
            confidence=best["score"],
            fallback_models=fallbacks
        )

        # Log routing decision
        self._log_routing(task_type, complexity, decision)

        return decision

    def _filter_candidates(
        self,
        required_capabilities: Set[ModelCapability],
        max_cost: Optional[float],
        max_latency_ms: Optional[int],
        require_tools: bool,
        require_json: bool,
        context_length: int,
        complexity_score: float
    ) -> List[ModelProfile]:
        """Filter models meeting basic requirements."""
        candidates = []

        for model in self.registry.get_all_models():
            # Check capabilities
            if not all(cap in model.capabilities for cap in required_capabilities):
                continue

            # Check quality threshold for complexity
            if model.quality_score < complexity_score:
                continue

            # Check tool support
            if require_tools and not model.supports_tools:
                continue

            # Check JSON support
            if require_json and not model.supports_json:
                continue

            # Check context window
            if context_length > model.context_window:
                continue

            # Check cost constraint
            if max_cost and model.cost_per_1k_input > max_cost:
                continue

            # Check latency constraint
            if max_latency_ms and model.avg_latency_ms > max_latency_ms:
                continue

            candidates.append(model)

        return candidates

    def _score_candidates(
        self,
        candidates: List[ModelProfile],
        goal: OptimizationGoal,
        complexity_score: float,
        prefer_model: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Score and rank candidate models."""
        scored = []

        for model in candidates:
            score = 0.0

            # Base quality score
            score += model.quality_score * 0.4

            # Goal-specific scoring
            if goal == OptimizationGoal.COST:
                # Lower cost is better
                max_cost = max(m.cost_per_1k_input for m in candidates)
                cost_score = 1 - (model.cost_per_1k_input / max_cost if max_cost > 0 else 0)
                score += cost_score * 0.5

            elif goal == OptimizationGoal.LATENCY:
                # Lower latency is better
                max_lat = max(m.avg_latency_ms for m in candidates)
                lat_score = 1 - (model.avg_latency_ms / max_lat if max_lat > 0 else 0)
                score += lat_score * 0.5

            elif goal == OptimizationGoal.QUALITY:
                # Higher quality is better
                score += model.quality_score * 0.5

            else:  # BALANCED
                # Balance cost, latency, quality
                max_cost = max(m.cost_per_1k_input for m in candidates)
                max_lat = max(m.avg_latency_ms for m in candidates)
                cost_score = 1 - (model.cost_per_1k_input / max_cost if max_cost > 0 else 0)
                lat_score = 1 - (model.avg_latency_ms / max_lat if max_lat > 0 else 0)
                score += (cost_score + lat_score + model.quality_score) / 3 * 0.5

            # Prefer model bonus
            if prefer_model and model.name == prefer_model:
                score += 0.2

            # Capability bonus
            score += len(model.capabilities) * 0.02

            scored.append({
                "model": model,
                "score": score,
                "cost_per_1k": model.cost_per_1k_input,
                "latency_ms": model.avg_latency_ms,
                "quality": model.quality_score
            })

        # Sort by score descending
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def _build_reason(
        self,
        best: Dict[str, Any],
        goal: OptimizationGoal,
        complexity: str,
        capabilities: Set[ModelCapability]
    ) -> str:
        """Build human-readable reason for routing decision."""
        model = best["model"]
        parts = [
            f"Selected {model.name} ({model.provider}) for {complexity} {capabilities}",
            f"Optimization goal: {goal.value}"
        ]

        if goal == OptimizationGoal.COST:
            parts.append(f"Lowest cost: ${model.cost_per_1k_input:.4f}/1k input")
        elif goal == OptimizationGoal.LATENCY:
            parts.append(f"Lowest latency: {model.avg_latency_ms}ms avg")
        elif goal == OptimizationGoal.QUALITY:
            parts.append(f"Highest quality: {model.quality_score:.0%}")
        else:
            parts.append(f"Balanced: cost=${model.cost_per_1k_input:.4f}/1k, latency={model.avg_latency_ms}ms, quality={model.quality_score:.0%}")

        return "; ".join(parts)

    def _estimate_cost(self, model: ModelProfile) -> float:
        """Estimate cost for typical usage."""
        # Assume 2k input, 1k output tokens
        input_cost = (2000 / 1000) * model.cost_per_1k_input
        output_cost = (1000 / 1000) * model.cost_per_1k_output
        return input_cost + output_cost

    def _log_routing(self, task_type: str, complexity: str, decision: RoutingDecision):
        """Log routing decision for analysis."""
        self.routing_history.append({
            "timestamp": datetime.now().isoformat(),
            "task_type": task_type,
            "complexity": complexity,
            "selected_model": decision.model,
            "provider": decision.provider,
            "goal": "balanced",  # Would track actual goal
            "estimated_cost": decision.estimated_cost,
            "estimated_latency_ms": decision.estimated_latency_ms,
            "confidence": decision.confidence
        })

        # Keep last 1000 entries
        if len(self.routing_history) > 1000:
            self.routing_history = self.routing_history[-1000:]


class ModelManager:
    """Manages model lifecycle, health, and fallbacks."""

    def __init__(self, router: LLMRouter):
        self.router = router
        self.health_status: Dict[str, Dict[str, Any]] = {}
        self.fallback_chains: Dict[str, List[str]] = {}

    async def check_health(self, model_name: str) -> Dict[str, Any]:
        """Check model health via test request."""
        model = self.router.registry.get_model(model_name)
        if not model:
            return {"healthy": False, "reason": "Model not found"}

        try:
            # Quick health check
            start = time.time()
            client = OpenRouterClient()
            await client.agenerate("Test", model=model_name)
            latency = (time.time() - start) * 1000

            self.health_status[model_name] = {
                "healthy": True,
                "latency_ms": latency,
                "last_check": datetime.now().isoformat(),
                "error_rate": 0.0
            }
        except Exception as e:
            self.health_status[model_name] = {
                "healthy": False,
                "reason": str(e),
                "last_check": datetime.now().isoformat()
            }

        return self.health_status.get(model_name, {})

    async def get_fallback_chain(self, primary_model: str) -> List[str]:
        """Get fallback chain for a model."""
        if primary_model in self.fallback_chains:
            return self.fallback_chains[primary_model]

        # Build fallback chain: same provider -> similar quality -> cheapest
        primary = self.router.registry.get_model(primary_model)
        if not primary:
            return []

        fallbacks = []

        # Same provider, lower quality
        same_provider = [
            m for m in self.router.registry.get_all_models()
            if m.provider == primary.provider and m.quality_score < primary.quality_score
        ]
        same_provider.sort(key=lambda m: m.quality_score, reverse=True)
        fallbacks.extend([m.name for m in same_provider[:2]])

        # Different provider, similar quality
        similar_quality = [
            m for m in self.router.registry.get_all_models()
            if m.provider != primary.provider and abs(m.quality_score - primary.quality_score) < 0.1
        ]
        similar_quality.sort(key=lambda m: m.cost_per_1k_input)
        fallbacks.extend([m.name for m in similar_quality[:2]])

        # Cheapest capable model
        capable = [m for m in self.router.registry.get_all_models() if m.quality_score >= 0.7]
        capable.sort(key=lambda m: m.cost_per_1k_input)
        if capable:
            fallbacks.append(capable[0].name)

        self.fallback_chains[primary_model] = fallbacks[:5]
        return self.fallback_chains[primary_model]

    async def execute_with_fallback(
        self,
        task_type: str,
        complexity: str,
        prompt: str,
        **kwargs
    ) -> Any:
        """Execute with automatic fallback on failure."""
        decision = self.router.route(task_type, complexity, **kwargs)
        models_to_try = [decision.model] + decision.fallback_models

        last_error = None
        for model_name in models_to_try:
            try:
                # Check health first
                health = await self.check_health(model_name)
                if not health.get("healthy", True):
                    logger.warning(f"Model {model_name} unhealthy: {health.get('reason')}")
                    continue

                # Execute
                client = OpenRouterClient()
                result = await client.agenerate(prompt, model=model_name)
                return result

            except Exception as e:
                last_error = e
                logger.warning(f"Model {model_name} failed: {e}")
                continue

        raise Exception(f"All models failed. Last error: {last_error}")


class AdaptiveRouter(LLMRouter):
    """Router that learns from execution history."""

    def __init__(self):
        super().__init__()
        self.performance_history: Dict[str, List[Dict]] = {}

    def record_execution(
        self,
        model: str,
        task_type: str,
        latency_ms: float,
        cost: float,
        success: bool,
        quality_rating: Optional[float] = None
    ):
        """Record execution for learning."""
        if model not in self.performance_history:
            self.performance_history[model] = []

        self.performance_history[model].append({
            "timestamp": datetime.now().isoformat(),
            "task_type": task_type,
            "latency_ms": latency_ms,
            "cost": cost,
            "success": success,
            "quality": quality_rating
        })

        if len(self.performance_history[model]) > 1000:
            self.performance_history[model] = self.performance_history[model][-1000:]

    def get_model_stats(self, model: str) -> Dict[str, Any]:
        """Get performance statistics for a model."""
        if model not in self.performance_history:
            return {"executions": 0}

        executions = self.performance_history[model]
        successful = [e for e in executions if e["success"]]

        return {
            "executions": len(executions),
            "success_rate": len(successful) / len(executions) if executions else 0,
            "avg_latency_ms": sum(e["latency_ms"] for e in successful) / len(successful) if successful else 0,
            "avg_cost": sum(e["cost"] for e in successful) / len(successful) if successful else 0,
            "avg_quality": sum(e.get("quality", 0) for e in successful) / len(successful) if successful else 0
        }

    def _score_candidates(
        self,
        candidates: List[ModelProfile],
        task_type: str,
        complexity: str,
        goal: OptimizationGoal
    ) -> List[tuple]:
        """Enhanced scoring with historical performance."""
        scored = super()._score_candidates(candidates, task_type, complexity, goal)

        adjusted = []
        for model, score in scored:
            stats = self.get_model_stats(model.name)
            if stats["executions"] > 10:
                # Boost score based on success rate
                score *= (0.8 + 0.2 * stats["success_rate"])
                # Adjust for actual latency/cost
                if stats["avg_latency_ms"] > 0:
                    actual_latency_factor = model.avg_latency_ms / max(stats["avg_latency_ms"], 1)
                    score *= min(1.2, max(0.8, actual_latency_factor))
            adjusted.append((model, score))

        adjusted.sort(key=lambda x: x[1], reverse=True)
        return adjusted


# Global instances
_router: Optional[LLMRouter] = None
_model_manager: Optional[ModelManager] = None
_adaptive_router: Optional[AdaptiveRouter] = None


def get_llm_router() -> LLMRouter:
    """Get global LLM router."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


def get_model_manager() -> ModelManager:
    """Get global model manager."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager(get_llm_router())
    return _model_manager


def get_adaptive_router() -> AdaptiveRouter:
    """Get global adaptive router."""
    global _adaptive_router
    if _adaptive_router is None:
        _adaptive_router = AdaptiveRouter()
    return _adaptive_router