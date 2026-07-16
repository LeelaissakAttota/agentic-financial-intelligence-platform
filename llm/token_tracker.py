"""
Token Tracking data structures for auditing and cost calculation.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class LLMUsage:
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float = 0.0
    timestamp: datetime = datetime.utcnow()
    provider: str = "openrouter"

    def to_dict(self):
        return {
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost": self.cost,
            "timestamp": self.timestamp.isoformat(),
            "provider": self.provider
        }
