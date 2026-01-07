"""
Cost Tracker - Tracks API costs and enforces budget limits.

Provides centralized cost tracking for all LLM API calls. Costs are recorded
by agents after each LLM call and persisted to daily log files.
"""

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


DATA_DIR = Path(__file__).parent.parent / "data"
CONFIG_PATH = DATA_DIR / "system" / "config.json"
COSTS_DIR = DATA_DIR / "user" / "costs"

# Default pricing (fallback if config doesn't have pricing)
DEFAULT_PRICING = {
    "input": 3.00,
    "cached_input": 0.30,
    "output": 15.00,
}

# Cached pricing from config
_pricing_cache: dict = None


def _load_pricing() -> dict:
    """Load pricing from config.json."""
    global _pricing_cache
    if _pricing_cache is not None:
        return _pricing_cache

    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                config = json.load(f)
            _pricing_cache = config.get("cost", {}).get("pricing", {})
            if _pricing_cache:
                return _pricing_cache
        except (json.JSONDecodeError, IOError):
            pass

    # Return empty dict if no pricing in config (will use DEFAULT_PRICING)
    _pricing_cache = {}
    return _pricing_cache


class BudgetExceeded(Exception):
    """Raised when the cost budget has been exceeded."""

    def __init__(self, budget: float, spent: float):
        self.budget = budget
        self.spent = spent
        super().__init__(f"Budget exceeded: ${spent:.4f} spent of ${budget:.2f} limit")


class CostTracker:
    """Tracks cumulative API costs and enforces budget limits."""

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

        # Load budget from config
        budget = self._load_budget_from_config()
        if budget is not None:
            self.set_budget(budget)

    @staticmethod
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

    @staticmethod
    def _get_cost_file_path(date: datetime = None) -> Path:
        """Get path to cost log file for a given date."""
        COSTS_DIR.mkdir(parents=True, exist_ok=True)
        date = date or datetime.now()
        return COSTS_DIR / f"{date.strftime('%Y-%m-%d')}.jsonl"

    def _append_cost_entry(self, entry: dict):
        """Append a cost entry to today's cost log."""
        path = self._get_cost_file_path()
        with open(path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    @staticmethod
    def _load_costs_for_date(date: datetime) -> list:
        """Load all cost entries for a specific date."""
        path = CostTracker._get_cost_file_path(date)
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
            entries.extend(CostTracker._load_costs_for_date(current))
            current += timedelta(days=1)
        return entries

    def set_budget(self, dollars: float):
        """Set the budget limit in dollars."""
        with self._lock:
            self.budget = dollars
            self._warned_thresholds.clear()
            print(f"[CostTracker] Budget set: ${dollars:.2f}")

    def get_pricing(self, model: str) -> dict:
        """Get pricing for a model from config."""
        pricing = _load_pricing()
        model_lower = model.lower()

        # Model pattern -> config key mapping
        # Maps patterns found in model names to their config pricing keys
        model_to_config = {
            "gpt": "chatgpt",  # gpt-5.2 -> chatgpt pricing
        }

        # Check model patterns and map to config keys
        for pattern, config_key in model_to_config.items():
            if pattern in model_lower and config_key in pricing:
                return pricing[config_key]

        # Try direct match (claude, grok, etc.)
        for known_model in pricing:
            if known_model in model_lower:
                return pricing[known_model]

        # Fall back to "default" in config, or DEFAULT_PRICING
        return pricing.get("default", DEFAULT_PRICING)

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int,
                       cached_input_tokens: int = 0) -> float:
        """Calculate cost for a single API call.

        Note: input_tokens is the TOTAL prompt tokens (includes cached).
        cached_input_tokens is the subset that was cached.
        We charge non-cached at full price, cached at discounted price.
        """
        pricing = self.get_pricing(model)
        # Subtract cached from total to get non-cached input tokens
        non_cached_input = max(0, input_tokens - cached_input_tokens)
        input_cost = (non_cached_input / 1_000_000) * pricing["input"]
        cached_cost = (cached_input_tokens / 1_000_000) * pricing["cached_input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + cached_cost + output_cost

    def check_budget(self):
        """Check if budget is exceeded. Raises BudgetExceeded if so."""
        with self._lock:
            if self.budget is not None and self.total_cost >= self.budget:
                raise BudgetExceeded(self.budget, self.total_cost)

    def record_usage(self, model: str, input_tokens: int, output_tokens: int,
                     cached_input_tokens: int = 0, agent_id: str = None,
                     stop_reason: str = None, duration_ms: int = None):
        """Record token usage and update cumulative cost."""
        cost = self.calculate_cost(model, input_tokens, output_tokens, cached_input_tokens)

        # Prepare log entry before acquiring lock
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_id,
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

            # Check budget thresholds
            should_warn_80 = False
            should_warn_95 = False
            should_raise = False

            if self.budget is not None:
                if self.total_cost >= self.budget:
                    should_raise = True
                else:
                    percent_used = (self.total_cost / self.budget) * 100
                    if percent_used >= 95 and 95 not in self._warned_thresholds:
                        self._warned_thresholds.add(95)
                        should_warn_95 = True
                    elif percent_used >= 80 and 80 not in self._warned_thresholds:
                        self._warned_thresholds.add(80)
                        should_warn_80 = True

            budget = self.budget
            total_cost = self.total_cost

        # File I/O and warnings outside lock
        self._append_cost_entry(log_entry)

        if should_warn_95:
            print(f"[CostTracker] WARNING: 95% of budget used (${total_cost:.4f} / ${budget:.2f})")
        elif should_warn_80:
            print(f"[CostTracker] WARNING: 80% of budget used (${total_cost:.4f} / ${budget:.2f})")

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
_tracker: CostTracker = None
_tracker_lock = threading.Lock()


def get_tracker() -> CostTracker:
    """Get the global cost tracker instance."""
    global _tracker
    with _tracker_lock:
        if _tracker is None:
            _tracker = CostTracker()
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


def get_cost_summary() -> dict:
    """Get cost summary for session, today, 7 days, and this month."""
    return get_tracker().get_summary()


def get_costs_by_agent(days: int = 30) -> dict:
    """Get cost breakdown by agent for the specified number of days."""
    return get_tracker().get_costs_by_agent(days)


def print_cost_summary():
    """Print usage summary to console."""
    print(get_tracker().format_stats())
