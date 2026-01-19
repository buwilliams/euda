"""
Resource Awareness - Tracks API costs and enforces budget limits.

Provides centralized cost tracking for all LLM API calls. Costs are recorded
by agents after each LLM call and persisted to daily log files.

This module was migrated from src/cost_tracker.py as part of the
metacognition consolidation.
"""

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from ..logger import get_logger
from ..events import emit_ui_event
from .config import get_global_config


DATA_DIR = Path(__file__).parent.parent.parent / "data"
CONFIG_PATH = DATA_DIR / "system" / "config.json"
COSTS_DIR = DATA_DIR / "agents" / "user" / "costs"

# Cost logger instance
_cost_logger = None

# Default pricing (fallback if config doesn't have pricing)
DEFAULT_PRICING = {
    "input": 3.00,
    "cached_input": 0.30,
    "output": 15.00,
}

# Cached config from file (for pricing lookups)
_llm_config_cache: dict = None


def _load_llm_config() -> dict:
    """Load and cache LLM config.json for pricing."""
    global _llm_config_cache
    if _llm_config_cache is not None:
        return _llm_config_cache

    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                _llm_config_cache = json.load(f)
                return _llm_config_cache
        except (json.JSONDecodeError, IOError):
            pass

    _llm_config_cache = {}
    return _llm_config_cache


def _get_provider_pricing(provider: str) -> dict:
    """Get pricing for a provider from config."""
    config = _load_llm_config()
    llm = config.get("llm", {})
    providers = llm.get("providers", {})

    # Get pricing from provider config
    if provider in providers:
        pricing = providers[provider].get("pricing")
        if pricing:
            return pricing

    # Fall back to default_pricing in llm config, or DEFAULT_PRICING
    return llm.get("default_pricing", DEFAULT_PRICING)


class BudgetExceeded(Exception):
    """Raised when the cost budget has been exceeded."""

    def __init__(self, budget: float, spent: float):
        self.budget = budget
        self.spent = spent
        super().__init__(f"Budget exceeded: ${spent:.4f} spent of ${budget:.2f} limit")


class ResourceTracker:
    """Tracks cumulative API costs and enforces budget limits.

    This is the metacognition component for resource awareness.
    """

    def __init__(self):
        self.budget: Optional[float] = None
        self.total_input_tokens: int = 0
        self.total_cached_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_cost: float = 0.0
        self.call_count: int = 0
        self._lock = threading.Lock()
        self._start_time = datetime.now()
        self._warned_thresholds: set = set()

        # Config - uses metacognition config
        self._config = get_global_config()

        # Load budget from config
        budget = self._load_budget_from_config()
        if budget is not None:
            self.set_budget(budget)

    def _load_budget_from_config(self) -> Optional[float]:
        """Load budget limit from system config."""
        # First try metacognition config
        resources_config = self._config.get_resources_config()
        budget = resources_config.get("budget_limit")
        if budget is not None and budget > 0:
            return float(budget)

        # Fall back to legacy llm.budget_limit
        config = _load_llm_config()
        budget = config.get("llm", {}).get("budget_limit")
        if budget is not None and budget > 0:
            return float(budget)

        return None

    def _get_budget_period(self) -> str:
        """Get the budget period from config (daily, weekly, monthly, or session)."""
        resources_config = self._config.get_resources_config()
        return resources_config.get("budget_period", "daily")

    def _get_period_spent(self) -> float:
        """Get total spent in the current budget period."""
        period = self._get_budget_period()
        now = datetime.now()

        if period == "session":
            # Session tracking uses in-memory total
            return self.total_cost

        elif period == "daily":
            # Load today's costs from file
            entries = self._load_costs_for_date(now)
            return sum(e.get("cost", 0) for e in entries)

        elif period == "weekly":
            # Load last 7 days
            start = now - timedelta(days=6)
            entries = self._load_costs_for_range(start, now)
            return sum(e.get("cost", 0) for e in entries)

        elif period == "monthly":
            # Load from start of month
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            entries = self._load_costs_for_range(start, now)
            return sum(e.get("cost", 0) for e in entries)

        else:
            # Unknown period, default to session
            return self.total_cost

    @staticmethod
    def _get_cost_logger():
        """Get the cost logger instance."""
        global _cost_logger
        if _cost_logger is None:
            _cost_logger = get_logger("agents/user/costs")
        return _cost_logger

    def _append_cost_entry(self, entry: dict):
        """Append a cost entry to today's cost log."""
        self._get_cost_logger().write_raw(entry)

    @staticmethod
    def _load_costs_for_date(date: datetime) -> list:
        """Load all cost entries for a specific date."""
        path = COSTS_DIR / f"{date.strftime('%Y-%m-%d')}.jsonl"
        if not path.exists():
            return []
        entries = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries

    @staticmethod
    def _load_costs_for_range(start_date: datetime, end_date: datetime) -> list:
        """Load all cost entries for a date range (inclusive)."""
        entries = []
        current = start_date
        while current <= end_date:
            entries.extend(ResourceTracker._load_costs_for_date(current))
            current += timedelta(days=1)
        return entries

    def set_budget(self, dollars: float):
        """Set the budget limit in dollars."""
        with self._lock:
            self.budget = dollars
            self._warned_thresholds.clear()
            print(f"[METACOGNITION] Budget set: ${dollars:.2f}")

    def get_pricing(self, provider: str) -> dict:
        """Get pricing for a provider from config."""
        return _get_provider_pricing(provider)

    def calculate_cost(self, provider: str, input_tokens: int, output_tokens: int,
                       cached_input_tokens: int = 0) -> float:
        """Calculate cost for a single API call.

        Note: input_tokens is the TOTAL prompt tokens (includes cached).
        cached_input_tokens is the subset that was cached.
        We charge non-cached at full price, cached at discounted price.
        """
        pricing = self.get_pricing(provider)
        # Subtract cached from total to get non-cached input tokens
        non_cached_input = max(0, input_tokens - cached_input_tokens)
        input_cost = (non_cached_input / 1_000_000) * pricing["input"]
        cached_cost = (cached_input_tokens / 1_000_000) * pricing["cached_input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + cached_cost + output_cost

    def check_budget(self):
        """Check if budget is exceeded for the configured period. Raises BudgetExceeded if so."""
        with self._lock:
            if self.budget is not None:
                period_spent = self._get_period_spent()
                if period_spent >= self.budget:
                    raise BudgetExceeded(self.budget, period_spent)

    def record_usage(self, provider: str, model: str, input_tokens: int, output_tokens: int,
                     cached_input_tokens: int = 0, agent_id: str = None, job_id: str = None,
                     stop_reason: str = None, duration_ms: int = None, timestamp: str = None):
        """Record token usage and update cumulative cost.

        Args:
            provider: LLM provider name
            model: Model name
            input_tokens: Total input tokens
            output_tokens: Output tokens
            cached_input_tokens: Cached input tokens (subset of input_tokens)
            agent_id: ID of calling agent (for cost attribution)
            job_id: ID of job being worked on (for per-job tracking)
            stop_reason: Reason the model stopped
            duration_ms: Duration of the API call
            timestamp: ISO timestamp for correlation with prompt logs
        """
        cost = self.calculate_cost(provider, input_tokens, output_tokens, cached_input_tokens)

        # Prepare log entry before acquiring lock
        log_entry = {
            "timestamp": timestamp or datetime.now().isoformat(),
            "agent": agent_id,
            "job_id": job_id,
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_input_tokens": cached_input_tokens,
            "cost": round(cost, 6),
            "stop_reason": stop_reason,
            "duration_ms": duration_ms,
        }

        # Update in-memory state under lock
        with self._lock:
            self.total_input_tokens += input_tokens
            self.total_cached_input_tokens += cached_input_tokens
            self.total_output_tokens += output_tokens
            self.total_cost += cost
            self.call_count += 1

        # Write log entry first (so period calculation includes it)
        self._append_cost_entry(log_entry)

        # Emit SSE event for UI updates (monitoring view)
        emit_ui_event("monitoring:llm_call", {
            "agent_id": agent_id,
            "timestamp": log_entry["timestamp"],
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": log_entry["cost"],
            "duration_ms": duration_ms,
        })

        # Check budget thresholds using period-based spending
        should_warn_80 = False
        should_warn_95 = False
        should_raise = False
        period = self._get_budget_period()

        if self.budget is not None:
            period_spent = self._get_period_spent()

            if period_spent >= self.budget:
                should_raise = True
            else:
                percent_used = (period_spent / self.budget) * 100
                # Use period-specific warning keys to reset warnings at period boundaries
                warn_key_80 = f"{period}:80"
                warn_key_95 = f"{period}:95"

                with self._lock:
                    if percent_used >= 95 and warn_key_95 not in self._warned_thresholds:
                        self._warned_thresholds.add(warn_key_95)
                        should_warn_95 = True
                    elif percent_used >= 80 and warn_key_80 not in self._warned_thresholds:
                        self._warned_thresholds.add(warn_key_80)
                        should_warn_80 = True

            budget = self.budget
            total_cost = period_spent
        else:
            budget = None
            total_cost = 0

        if should_warn_95:
            print(f"[METACOGNITION] WARNING: 95% of {period} budget used (${total_cost:.4f} / ${budget:.2f})")
        elif should_warn_80:
            print(f"[METACOGNITION] WARNING: 80% of {period} budget used (${total_cost:.4f} / ${budget:.2f})")

        if should_raise:
            raise BudgetExceeded(budget, total_cost)

    def get_stats(self) -> dict:
        """Get current session statistics."""
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

    def get_summary(self) -> dict:
        """Get cost summary for session, today, 7 days, and this month."""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        seven_days_ago = today_start - timedelta(days=6)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Load costs for different periods
        today_costs = self._load_costs_for_date(now)
        week_costs = self._load_costs_for_range(seven_days_ago, now)
        month_costs = self._load_costs_for_range(month_start, now)

        # Get session stats
        stats = self.get_stats()

        def sum_costs(entries):
            return sum(e.get("cost", 0) for e in entries)

        def count_calls(entries):
            return len(entries)

        return {
            "session": {
                "cost": round(stats["total_cost"], 4),
                "calls": stats["call_count"],
            },
            "today": {
                "cost": round(sum_costs(today_costs), 4),
                "calls": count_calls(today_costs),
            },
            "seven_days": {
                "cost": round(sum_costs(week_costs), 4),
                "calls": count_calls(week_costs),
            },
            "month": {
                "cost": round(sum_costs(month_costs), 4),
                "calls": count_calls(month_costs),
            },
            "budget": self.budget,
        }

    def get_costs_by_agent(self, days: int = 30) -> dict:
        """Get cost breakdown by agent for the specified number of days.

        Args:
            days: Number of days to look back (default 30)

        Returns:
            Dict with agent IDs as keys, each containing:
            - cost: Total cost for that agent
            - calls: Number of API calls
            - input_tokens: Total input tokens
            - output_tokens: Total output tokens
            - cached_input_tokens: Total cached input tokens
        """
        now = datetime.now()
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)

        # Load all costs for the date range
        entries = self._load_costs_for_range(start_date, now)

        # Aggregate by agent
        agents = {}
        for entry in entries:
            agent_id = entry.get("agent") or "unknown"
            if agent_id not in agents:
                agents[agent_id] = {
                    "cost": 0.0,
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cached_input_tokens": 0,
                }
            agents[agent_id]["cost"] += entry.get("cost", 0)
            agents[agent_id]["calls"] += 1
            agents[agent_id]["input_tokens"] += entry.get("input_tokens", 0)
            agents[agent_id]["output_tokens"] += entry.get("output_tokens", 0)
            agents[agent_id]["cached_input_tokens"] += entry.get("cached_input_tokens", 0)

        # Round costs
        for agent_id in agents:
            agents[agent_id]["cost"] = round(agents[agent_id]["cost"], 4)

        # Sort by cost descending
        sorted_agents = dict(sorted(agents.items(), key=lambda x: x[1]["cost"], reverse=True))

        return {
            "period_days": days,
            "agents": sorted_agents,
            "total_cost": round(sum(a["cost"] for a in agents.values()), 4),
            "total_calls": sum(a["calls"] for a in agents.values()),
        }

    def get_calls_by_job(self, job_id: str, days: int = 7) -> list:
        """Get all API calls for a specific job.

        Args:
            job_id: ID of the job to query
            days: Number of days to look back (default 7)

        Returns:
            List of API call entries for this job, newest first
        """
        now = datetime.now()
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)

        # Load all costs for the date range
        entries = self._load_costs_for_range(start_date, now)

        # Filter by job_id
        job_entries = [e for e in entries if e.get("job_id") == job_id]

        # Sort by timestamp descending (newest first)
        job_entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return job_entries

    def get_job_call_count(self, job_id: str, days: int = 7) -> dict:
        """Get count and cost summary for a specific job.

        Args:
            job_id: ID of the job to query
            days: Number of days to look back (default 7)

        Returns:
            Dict with call count, total cost, and token counts
        """
        entries = self.get_calls_by_job(job_id, days)

        return {
            "job_id": job_id,
            "calls": len(entries),
            "cost": round(sum(e.get("cost", 0) for e in entries), 4),
            "input_tokens": sum(e.get("input_tokens", 0) for e in entries),
            "output_tokens": sum(e.get("output_tokens", 0) for e in entries),
            "cached_input_tokens": sum(e.get("cached_input_tokens", 0) for e in entries),
        }

    def format_stats(self) -> str:
        """Format stats as a human-readable string."""
        stats = self.get_stats()
        lines = [
            "=" * 50,
            "Resource Tracker Summary",
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

    def invalidate_config(self):
        """Invalidate cached config. Call when settings change."""
        global _llm_config_cache
        _llm_config_cache = None
        self._config.invalidate()


# Global singleton instance
_tracker: ResourceTracker = None
_tracker_lock = threading.Lock()


def get_resource_tracker() -> ResourceTracker:
    """Get the global resource tracker instance."""
    global _tracker
    with _tracker_lock:
        if _tracker is None:
            _tracker = ResourceTracker()
        return _tracker


def set_budget(dollars: float):
    """Set the global budget limit."""
    get_resource_tracker().set_budget(dollars)


def record_usage(provider: str, model: str, input_tokens: int, output_tokens: int,
                 cached_input_tokens: int = 0, agent_id: str = None, job_id: str = None,
                 stop_reason: str = None, duration_ms: int = None, timestamp: str = None):
    """Record usage to the global tracker."""
    get_resource_tracker().record_usage(
        provider, model, input_tokens, output_tokens, cached_input_tokens,
        agent_id, job_id, stop_reason, duration_ms, timestamp
    )


def get_calls_by_job(job_id: str, days: int = 7) -> list:
    """Get all API calls for a specific job."""
    return get_resource_tracker().get_calls_by_job(job_id, days)


def get_job_call_count(job_id: str, days: int = 7) -> dict:
    """Get count and cost summary for a specific job."""
    return get_resource_tracker().get_job_call_count(job_id, days)


def check_budget():
    """Check if global budget exceeded."""
    get_resource_tracker().check_budget()


def get_stats() -> dict:
    """Get global usage stats."""
    return get_resource_tracker().get_stats()


def get_cost_summary() -> dict:
    """Get cost summary for session, today, 7 days, and this month."""
    return get_resource_tracker().get_summary()


def get_costs_by_agent(days: int = 30) -> dict:
    """Get cost breakdown by agent for the specified number of days."""
    return get_resource_tracker().get_costs_by_agent(days)


def print_resource_summary():
    """Print usage summary to console."""
    print(get_resource_tracker().format_stats())
