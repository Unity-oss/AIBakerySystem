"""
Token tracking utility for Tastyz Bakery AI System.

Provides lightweight token estimation and cost tracking.
Stores usage in-memory per session and can be exported.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# Rough token estimation: ~4 chars per token for English text
CHARS_PER_TOKEN = 4

# Cost per 1K tokens (USD)
MODEL_COSTS = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "text-embedding-3-small": {"input": 0.00002, "output": 0.0},
}


def estimate_tokens(text: str) -> int:
    """Estimate token count from text length."""
    if not text:
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate estimated cost in USD."""
    costs = MODEL_COSTS.get(model, MODEL_COSTS["gpt-4o-mini"])
    input_cost = (input_tokens / 1000) * costs["input"]
    output_cost = (output_tokens / 1000) * costs["output"]
    return round(input_cost + output_cost, 6)


@dataclass
class UsageRecord:
    """Single LLM usage record."""
    timestamp: str
    agent: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


@dataclass
class TokenTracker:
    """Track token usage across the session."""
    records: list = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0

    def record(self, agent: str, model: str, input_text: str, output_text: str) -> UsageRecord:
        """Record a single LLM interaction."""
        input_tokens = estimate_tokens(input_text)
        output_tokens = estimate_tokens(output_text)
        cost = estimate_cost(model, input_tokens, output_tokens)

        record = UsageRecord(
            timestamp=datetime.now().isoformat(),
            agent=agent,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )

        self.records.append(record)
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost

        logger.info(
            "Token usage | agent=%s model=%s in=%d out=%d cost=$%.6f",
            agent, model, input_tokens, output_tokens, cost,
        )
        return record

    def get_summary(self) -> dict:
        """Return usage summary."""
        return {
            "total_requests": len(self.records),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_cost_usd": round(self.total_cost, 6),
        }


# Global session tracker (reset per server restart)
_tracker = TokenTracker()


def get_tracker() -> TokenTracker:
    """Get the global token tracker instance."""
    return _tracker


def track_usage(agent: str, model: str, input_text: str, output_text: str) -> UsageRecord:
    """Convenience function to record usage on the global tracker."""
    return _tracker.record(agent, model, input_text, output_text)
