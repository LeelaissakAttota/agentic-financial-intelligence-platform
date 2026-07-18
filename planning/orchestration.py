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
from typing import Any, Dict, List, Optional, Callable
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

    def route(
        self,
        task_type: str,
        complexity: str = "moderate",
        required_capabilities: Optional[List[ModelCapability]] = None,
        max_cost: Optional[float] = None,
        max_latency_ms: Optional[int] = None,
        optimization_goal: Optional[OptimizationGoal] = None,
        prefer_provider: Optional[str] = None
    ) -> RoutingDecision:
        """
        Route request to optimal model.

        Args:
            task_type: Type of task (e.g., "financial_analysis", "summarization")
            complexity: "simple", "moderate", "complex"
            required_capabilities: Specific capabilities needed
            max_cost: Maximum cost per 1k tokens (USD)
            max_latency_ms: Maximum acceptable latency
            optimization_goal: What to optimize for
            prefer_provider: Preferred provider

        Returns:
            RoutingDecision with selected model and metadata
        """
        # Determine required capabilities
        if required_capabilities is None:
            required_capabilities = self.task_capability_map.get(task_type, [ModelCapability.CHAT])

        # Filter models by capabilities
        candidates = []
        for model in self.registry.get_all_models():
            if all(cap in model.capabilities for cap in required_capabilities):
                candidates.append(model)

        if not candidates:
            # Fallback to any model with at least one required capability
            for model in self.registry.get_all_models():
                if any(cap in model.capabilities for cap in required_capabilities):
                    candidates.append(model)

        if not candidates:
            # Ultimate fallback
            candidates = self.registry.get_all_models()

        # Apply filters
        if max_cost is not None:
            candidates = [m for m in candidates if m.cost_per_1k_input <= max_cost and m.cost_per_1k_output <= max_cost]
        if max_latency_ms is not None:
            candidates = [m for m in candidates if m.avg_latency_ms <= max_latency_ms]
        if prefer_provider:
            candidates = [m for m in candidates if m.provider.lower() == prefer_provider.lower()]

        if not candidates:
            candidates = self.registry.get_all_models()

        # Score candidates based on optimization goal
        goal = optimization_goal or self.default_goal
        scored = self._score_candidates(candidates, task_type, complexity, goal)

        # Select best
        best = scored[0]

        # Select fallbacks (next best 2-3)
        fallbacks = [s[0].name for s in scored[1:3]]

        decision = RoutingDecision(
            model=best.name,
            provider=best.provider,
            reason=self._generate_reason(best, goal, task_type, complexity),
            estimated_cost=best.cost_per_1k_input + best.cost_per_1k_output,
            estimated_latency_ms=best.avg_latency_ms,
            confidence=0.85,
            fallback_models=fallbacks
        )

        # Record routing decision
        self.routing_history.append({
            "timestamp": datetime.now().isoformat(),
            "task_type": task_type,
            "complexity": complexity,
            "goal": goal.value,
            "selected_model": best.name,
            "candidates_count": len(candidates)
        })

        return decision

    def _score_candidates(
        self,
        candidates: List[ModelProfile],
        task_type: str,
        complexity: str,
        goal: OptimizationGoal
    ) -> List[tuple]:
        """Score and rank candidates."""
        scored = []

        for model in candidates:
            score = 0.0

            if goal == OptimizationGoal.COST:
                # Lower cost = higher score
                cost_score = 1.0 - min(1.0, (model.cost_per_1k_input + model.cost_per_1k_output) / 0.05)
                score = cost_score * 0.7 + model.quality_score * 0.3

            elif goal == OptimizationGoal.LATENCY:
                # Lower latency = higher score
                latency_score = 1.0 - min(1.0, model.avg_latency_ms / 5000)
                score = latency_score * 0.7 + model.quality_score * 0.3

            elif goal == OptimizationGoal.QUALITY:
                # Higher quality = higher score
                score = model.quality_score * 0.8 + (1.0 - min(1.0, (model.cost_per_1k_input + model.cost_per_1k_output) / 0.05)) * 0.2

            else:  # BALANCED
                # Weighted combination
                cost_score = 1.0 - min(1.0, (model.cost_per_1k_input + model.cost_per_1k_output) / 0.05)
                latency_score = 1.0 - min(1.0, model.avg_latency_ms / 5000)
                score = (
                    model.quality_score * 0.4 +
                    cost_score * 0.3 +
                    latency_score * 0.3
                )

            # Complexity adjustment
            if complexity == "complex":
                score *= model.quality_score  # Prefer high quality for complex tasks
            elif complexity == "simple":
                score *= (1.0 + cost_score * 0.5)  # Slight preference for cost on simple tasks

            scored.append((model, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _generate_reason(
        self,
        model: ModelProfile,
        goal: OptimizationGoal,
        task_type: str,
        complexity: str
    ) -> str:
        """Generate human-readable reason for selection."""
        reasons = []

        if goal == OptimizationGoal.COST:
            reasons.append(f"lowest cost (${model.cost_per_1k_input:.4f}/1k input)")
        elif goal == OptimizationGoal.LATENCY:
            reasons.append(f"fastest latency ({model.avg_latency_ms}ms)")
        elif goal == OptimizationGoal.QUALITY:
            reasons.append(f"highest quality score ({model.quality_score:.2f})")
        else:
            reasons.append(f"balanced (quality: {model.quality_score:.2f}, cost: ${model.cost_per_1k_input:.4f}/1k, latency: {model.avg_latency_ms}ms)")

        reasons.append(f"supports {[c.value for c in model.capabilities]}")

        return f"Selected {model.name} for {task_type} ({complexity}): {', '.join(reasons)}"

    async def execute_with_routing(
        self,
        task_type: str,
        prompt: str,
        system_prompt: str = "",
        complexity: str = "moderate",
        **kwargs
    ) -> Dict[str, Any]:
        """Execute LLM request with automatic routing."""
        decision = self.route(task_type, complexity=complexity)

        # Use the routed model
        response = await self.client.agenerate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=decision.model,
            **kwargs
        )

        return {
            "response": response,
            "model_used": decision.model,
            "routing_decision": decision,
            "cost_estimate": decision.estimated_cost
        }


class AdaptiveRouter(LLMRouter):
    """Router that learns from execution history."""

    def __init__(self):
        super().__init__()
        self.performance_history: Dict[str, List[Dict]] = {}  # model -> performance metrics

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

        # Keep only recent history
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

        # Adjust scores based on historical performance
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
_adaptive_router: Optional[AdaptiveRouter] = None


def get_router() -> LLMRouter:
    """Get global router instance."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


def get_adaptive_router() -> AdaptiveRouter:
    """Get global adaptive router instance."""
    global _adaptive_router
    if _adaptive_router is None:
        _adaptive_router = AdaptiveRouter()
    return _adaptive_router