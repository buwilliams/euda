"""
Cost Tracker - Tracks API usage and enforces budget limits.

Provides global cost tracking across all LLM calls with configurable
budget limits. When budget is exceeded, raises BudgetExceeded to
trigger graceful shutdown.

Also maintains a unified API call log at data/system/api_calls.jsonl
"""

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


DATA_DIR = Path(__file__).parent.parent / "data"
CONFIG_PATH = DATA_DIR / "system" / "config.json"
API_LOG_PATH = DATA_DIR / "system" / "api_calls.jsonl"


def _load_budget_from_config() -> Optional[float]:
    """Load budget limit from system config."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                config = json.load(f)
            budget = config.get("cost", {}).get("budget_limit")
            if budget is not None and budget > 0:
                return float(budget)
        except (json.JSONDecodeError, IOError):
            pass
    return None

# Pricing per million tokens (as of user-provided rates)
PRICING = {
    "gpt-5.2": {
        "input": 1.75,          # $1.75 per 1M input tokens
        "cached_input": 0.175,  # $0.175 per 1M cached input tokens
        "output": 14.00,        # $14.00 per 1M output tokens
    },
    # Fallback for unknown models - use GPT-5.2 rates
    "default": {
        "input": 1.75,
        "cached_input": 0.175,
        "output": 14.00,
    }
}


class BudgetExceeded(Exception):
    """Raised when the cost budget has been exceeded."""

    def __init__(self, budget: float, spent: float):
        self.budget = budget
        self.spent = spent
        super().__init__(f"Budget exceeded: ${spent:.4f} spent of ${budget:.2f} limit")


@dataclass
class CostTracker:
    """Tracks cumulative API costs and enforces budget limits."""

    budget: Optional[float] = None  # None means no limit
    total_input_tokens: int = 0
    total_cached_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    call_count: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _start_time: datetime = field(default_factory=datetime.now)

    def set_budget(self, dollars: float):
        """Set the budget limit in dollars."""
        with self._lock:
            self.budget = dollars
            print(f"[CostTracker] Budget set: ${dollars:.2f}")

    def get_pricing(self, model: str) -> dict:
        """Get pricing for a model."""
        # Normalize model name
        model_lower = model.lower()
        for known_model in PRICING:
            if known_model in model_lower:
                return PRICING[known_model]
        return PRICING["default"]

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int,
                       cached_input_tokens: int = 0) -> float:
        """Calculate cost for a single API call."""
        pricing = self.get_pricing(model)

        # Calculate cost (pricing is per million tokens)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        cached_cost = (cached_input_tokens / 1_000_000) * pricing["cached_input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + cached_cost + output_cost

    def check_budget(self):
        """Check if budget is exceeded. Raises BudgetExceeded if so."""
        with self._lock:
            if self.budget is not None and self.total_cost >= self.budget:
                raise BudgetExceeded(self.budget, self.total_cost)

    def _log_api_call(self, entry: dict):
        """Append an API call entry to the unified log file."""
        API_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(API_LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def record_usage(self, model: str, input_tokens: int, output_tokens: int,
                     cached_input_tokens: int = 0, agent_id: str = None,
                     stop_reason: str = None, duration_ms: int = None):
        """Record token usage and update cumulative cost.

        Args:
            model: The model name
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
            cached_input_tokens: Number of cached input tokens (if applicable)
            agent_id: ID of the agent making the call (optional)
            stop_reason: Why the LLM stopped (end_turn, tool_use, etc.)
            duration_ms: How long the API call took in milliseconds
        """
        cost = self.calculate_cost(model, input_tokens, output_tokens, cached_input_tokens)

        with self._lock:
            self.total_input_tokens += input_tokens
            self.total_cached_input_tokens += cached_input_tokens
            self.total_output_tokens += output_tokens
            self.total_cost += cost
            self.call_count += 1
            call_number = self.call_count

            # Log the API call
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "call_number": call_number,
                "agent": agent_id,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cached_input_tokens": cached_input_tokens,
                "cost": round(cost, 6),
                "cumulative_cost": round(self.total_cost, 6),
                "stop_reason": stop_reason,
                "duration_ms": duration_ms,
            }
            self._log_api_call(log_entry)

            # Check budget after recording
            if self.budget is not None:
                remaining = self.budget - self.total_cost
                if remaining <= 0:
                    raise BudgetExceeded(self.budget, self.total_cost)

                # Warn at 80% and 95% thresholds
                percent_used = (self.total_cost / self.budget) * 100
                if percent_used >= 95 and self.call_count > 1:
                    print(f"[CostTracker] WARNING: 95% of budget used (${self.total_cost:.4f} / ${self.budget:.2f})")
                elif percent_used >= 80 and percent_used < 95 and self.call_count > 1:
                    # Only warn once when crossing 80%
                    prev_cost = self.total_cost - cost
                    prev_percent = (prev_cost / self.budget) * 100
                    if prev_percent < 80:
                        print(f"[CostTracker] WARNING: 80% of budget used (${self.total_cost:.4f} / ${self.budget:.2f})")

    def get_stats(self) -> dict:
        """Get current usage statistics."""
        with self._lock:
            elapsed = (datetime.now() - self._start_time).total_seconds()
            return {
                "budget": self.budget,
                "total_cost": self.total_cost,
                "remaining": (self.budget - self.total_cost) if self.budget else None,
                "total_input_tokens": self.total_input_tokens,
                "total_cached_input_tokens": self.total_cached_input_tokens,
                "total_output_tokens": self.total_output_tokens,
                "call_count": self.call_count,
                "elapsed_seconds": elapsed,
                "cost_per_minute": (self.total_cost / elapsed * 60) if elapsed > 0 else 0,
            }

    def format_stats(self) -> str:
        """Format stats as a human-readable string."""
        stats = self.get_stats()
        lines = [
            "=" * 50,
            "Cost Tracker Summary",
            "=" * 50,
            f"Total Cost:    ${stats['total_cost']:.4f}",
        ]

        if stats['budget']:
            lines.append(f"Budget:        ${stats['budget']:.2f}")
            lines.append(f"Remaining:     ${stats['remaining']:.4f}")
            percent = (stats['total_cost'] / stats['budget']) * 100
            lines.append(f"Used:          {percent:.1f}%")

        lines.extend([
            f"API Calls:     {stats['call_count']}",
            f"Input Tokens:  {stats['total_input_tokens']:,}",
            f"Output Tokens: {stats['total_output_tokens']:,}",
            f"Runtime:       {stats['elapsed_seconds']:.0f}s",
            f"Cost/min:      ${stats['cost_per_minute']:.4f}",
            "=" * 50,
        ])

        return "\n".join(lines)


# Global singleton instance
_tracker: Optional[CostTracker] = None
_tracker_lock = threading.Lock()


def get_tracker() -> CostTracker:
    """Get the global cost tracker instance."""
    global _tracker
    with _tracker_lock:
        if _tracker is None:
            _tracker = CostTracker()
            # Load budget from config on first initialization
            budget = _load_budget_from_config()
            if budget is not None:
                _tracker.set_budget(budget)
        return _tracker


def set_budget(dollars: float):
    """Set the global budget limit."""
    get_tracker().set_budget(dollars)


def record_usage(model: str, input_tokens: int, output_tokens: int,
                 cached_input_tokens: int = 0, agent_id: str = None,
                 stop_reason: str = None, duration_ms: int = None):
    """Record usage to the global tracker."""
    get_tracker().record_usage(
        model, input_tokens, output_tokens, cached_input_tokens,
        agent_id, stop_reason, duration_ms
    )


def check_budget():
    """Check if global budget exceeded."""
    get_tracker().check_budget()


def get_stats() -> dict:
    """Get global usage stats."""
    return get_tracker().get_stats()


def print_summary():
    """Print usage summary to console."""
    print(get_tracker().format_stats())
