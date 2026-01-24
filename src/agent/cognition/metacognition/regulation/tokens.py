"""
Token Awareness - Unified token tracking and budget enforcement.

Replaces the fragmented velocity.py and resources.py with a unified system that:
- Tracks tokens PRE-call using tokenizer (not just post-call from API)
- Enforces per-agent budgets with frequency-based thresholds
- Introduces proper agent states: enabled, disabled, paused
- Pauses agents automatically when thresholds are exceeded

This is the core metacognition component for token/resource awareness.
"""

import json
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Set

from ....logger import get_logger
from .....web.events import emit_ui_event
from .incidents import (
    get_incident_tracker,
    IncidentType,
    IncidentSeverity
)


DATA_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "data"
CONFIG_PATH = DATA_DIR / "system" / "config.json"
AGENTS_DIR = DATA_DIR / "agents"
USAGE_DIR = DATA_DIR / "system" / "token_usage"


class AgentState(Enum):
    """Agent operational states."""
    ENABLED = "enabled"    # Normal operation
    DISABLED = "disabled"  # User explicitly disabled
    PAUSED = "paused"      # Threshold breach - awaiting manual intervention


@dataclass
class TokenBudget:
    """Token budget configuration for an agent."""
    frequency: str  # "monthly", "weekly", "daily", "hourly"
    input_ratio: float  # Fraction of budget for input tokens (e.g., 0.8)
    output_ratio: float  # Fraction of budget for output tokens (e.g., 0.2)


class AgentPausedError(Exception):
    """Raised when an agent is paused due to threshold breach."""

    def __init__(self, agent_id: str, reason: str):
        self.agent_id = agent_id
        self.reason = reason
        super().__init__(f"Agent {agent_id} is paused: {reason}")


class TokenAwareness:
    """Unified token tracking and budget enforcement.

    Provides:
    - Pre-call token estimation using tokenizer
    - Per-agent budgets with configurable frequency
    - Automatic pausing when thresholds exceeded
    - Incident tracking for all breaches

    Thread-safe implementation for multi-agent environments.
    """

    # Default budget split (input vs output)
    DEFAULT_INPUT_RATIO = 0.8
    DEFAULT_OUTPUT_RATIO = 0.2

    # Default frequency for agents
    DEFAULT_FREQUENCY = "daily"

    def __init__(self):
        self._lock = threading.RLock()
        self._logger = get_logger("system/logs/token-awareness")

        # Per-agent usage tracking (current period)
        # Structure: {agent_id: {input: int, output: int, period_start: datetime}}
        self._agent_usage: Dict[str, dict] = {}

        # Paused agents and reasons
        self._paused_agents: Set[str] = set()
        self._pause_reasons: Dict[str, str] = {}
        self._pause_timestamps: Dict[str, str] = {}

        # Cached config
        self._config_cache: dict = None
        self._config_mtime: float = 0

        # Load persisted usage data
        self._load_usage_data()

    def _load_config(self) -> dict:
        """Load system config with caching."""
        try:
            current_mtime = CONFIG_PATH.stat().st_mtime
            if self._config_cache is not None and current_mtime == self._config_mtime:
                return self._config_cache

            with open(CONFIG_PATH) as f:
                self._config_cache = json.load(f)
            self._config_mtime = current_mtime
            return self._config_cache
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def _get_token_awareness_config(self) -> dict:
        """Get token awareness configuration."""
        config = self._load_config()
        return config.get("metacognition", {}).get("token_awareness", {})

    def _get_global_budget_tokens(self) -> int:
        """Get global monthly token budget from config.

        Converts the dollar budget to tokens using average pricing.
        Default: 10M tokens if no budget configured.
        """
        config = self._load_config()
        llm_config = config.get("llm", {})
        budget = llm_config.get("budget", {})
        budget_dollars = budget.get("limit", 10.0)

        # Get average pricing from default or first provider
        pricing = llm_config.get("default_pricing", {})
        if not pricing:
            providers = llm_config.get("providers", {})
            if providers:
                first_provider = next(iter(providers.values()), {})
                pricing = first_provider.get("pricing", {})

        # Average input/output rate (per million tokens)
        input_rate = pricing.get("input", 3.0)
        output_rate = pricing.get("output", 15.0)

        # Assume 80/20 split for cost estimation
        avg_rate = (input_rate * 0.8 + output_rate * 0.2)

        # Convert dollars to tokens (in millions, then to actual tokens)
        if avg_rate > 0:
            tokens_in_millions = budget_dollars / avg_rate
            return int(tokens_in_millions * 1_000_000)

        # Default fallback
        return 10_000_000  # 10M tokens

    def _get_agent_budget_config(self, agent_id: str) -> TokenBudget:
        """Get token budget configuration for an agent."""
        config_path = AGENTS_DIR / agent_id / "config.json"

        try:
            with open(config_path) as f:
                agent_config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            agent_config = {}

        token_budget = agent_config.get("token_budget", {})

        return TokenBudget(
            frequency=token_budget.get("frequency", self.DEFAULT_FREQUENCY),
            input_ratio=token_budget.get("input_ratio", self.DEFAULT_INPUT_RATIO),
            output_ratio=token_budget.get("output_ratio", self.DEFAULT_OUTPUT_RATIO)
        )

    def _get_agent_state_from_config(self, agent_id: str) -> AgentState:
        """Get agent state from config file."""
        config_path = AGENTS_DIR / agent_id / "config.json"

        try:
            with open(config_path) as f:
                agent_config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return AgentState.ENABLED

        # Read state field only, default to ENABLED if missing
        state_str = agent_config.get("state", "enabled")
        try:
            return AgentState(state_str)
        except ValueError:
            return AgentState.ENABLED

    def _save_agent_state(self, agent_id: str, state: AgentState,
                          reason: Optional[str] = None):
        """Save agent state to config file."""
        config_path = AGENTS_DIR / agent_id / "config.json"

        try:
            with open(config_path) as f:
                agent_config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            agent_config = {"id": agent_id}

        # Update state field only (no dual-write to enabled)
        agent_config["state"] = state.value

        # Remove legacy enabled field if present
        agent_config.pop("enabled", None)

        if state == AgentState.PAUSED:
            agent_config["pause_reason"] = reason
            agent_config["pause_timestamp"] = datetime.now().isoformat()
        else:
            # Remove pause fields when not paused
            agent_config.pop("pause_reason", None)
            agent_config.pop("pause_timestamp", None)

        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w") as f:
            json.dump(agent_config, f, indent=2)
            f.write("\n")

    def _calculate_period_budget(self, enabled_agent_count: int,
                                 frequency: str) -> tuple:
        """Calculate token budget for a period.

        Each agent gets an equal share of the global monthly budget,
        then divided by the frequency period.

        Args:
            enabled_agent_count: Number of enabled agents
            frequency: Budget frequency ("monthly", "weekly", "daily", "hourly")

        Returns:
            Tuple of (total_budget_tokens, period_name)
        """
        global_budget = self._get_global_budget_tokens()

        # Each agent gets equal share
        per_agent_monthly = global_budget // max(1, enabled_agent_count)

        # Divide by frequency
        if frequency == "monthly":
            return per_agent_monthly, "month"
        elif frequency == "weekly":
            return per_agent_monthly // 4, "week"
        elif frequency == "daily":
            return per_agent_monthly // 31, "day"
        elif frequency == "hourly":
            daily = per_agent_monthly // 31
            return daily // 24, "hour"
        else:
            # Default to daily
            return per_agent_monthly // 31, "day"

    def _get_period_key(self, frequency: str) -> str:
        """Get the current period key for usage tracking."""
        now = datetime.now()

        if frequency == "monthly":
            return now.strftime("%Y-%m")
        elif frequency == "weekly":
            # ISO week number
            return f"{now.year}-W{now.isocalendar()[1]:02d}"
        elif frequency == "daily":
            return now.strftime("%Y-%m-%d")
        elif frequency == "hourly":
            return now.strftime("%Y-%m-%d-%H")
        else:
            return now.strftime("%Y-%m-%d")

    def _get_agent_usage(self, agent_id: str, frequency: str) -> dict:
        """Get current period usage for an agent."""
        period_key = self._get_period_key(frequency)

        if agent_id not in self._agent_usage:
            self._agent_usage[agent_id] = {}

        agent_data = self._agent_usage[agent_id]

        # Check if we're in a new period
        if agent_data.get("period_key") != period_key:
            agent_data = {
                "period_key": period_key,
                "input": 0,
                "output": 0
            }
            self._agent_usage[agent_id] = agent_data

        return agent_data

    def _load_usage_data(self):
        """Load persisted usage data from disk."""
        usage_file = USAGE_DIR / "current.json"
        if usage_file.exists():
            try:
                with open(usage_file) as f:
                    data = json.load(f)
                    self._agent_usage = data.get("agent_usage", {})
                    self._paused_agents = set(data.get("paused_agents", []))
                    self._pause_reasons = data.get("pause_reasons", {})
                    self._pause_timestamps = data.get("pause_timestamps", {})
            except (json.JSONDecodeError, IOError):
                pass

    def _save_usage_data(self):
        """Persist usage data to disk."""
        USAGE_DIR.mkdir(parents=True, exist_ok=True)
        usage_file = USAGE_DIR / "current.json"

        data = {
            "agent_usage": self._agent_usage,
            "paused_agents": list(self._paused_agents),
            "pause_reasons": self._pause_reasons,
            "pause_timestamps": self._pause_timestamps,
            "last_updated": datetime.now().isoformat()
        }

        with open(usage_file, "w") as f:
            json.dump(data, f, indent=2)

    def _get_pricing(self, provider: str) -> dict:
        """Get pricing for a provider from config."""
        config = self._load_config()
        llm_config = config.get("llm", {})
        providers = llm_config.get("providers", {})

        # Get pricing from provider config
        if provider in providers:
            pricing = providers[provider].get("pricing")
            if pricing:
                return pricing

        # Fall back to default pricing
        return llm_config.get("default_pricing", {
            "input": 3.00,
            "cached_input": 0.30,
            "output": 15.00,
        })

    def _calculate_cost(self, provider: str, input_tokens: int, output_tokens: int,
                        cached_input_tokens: int = 0) -> float:
        """Calculate cost for a single API call.

        Note: input_tokens is the TOTAL prompt tokens (includes cached).
        cached_input_tokens is the subset that was cached.
        We charge non-cached at full price, cached at discounted price.
        """
        pricing = self._get_pricing(provider)
        # Subtract cached from total to get non-cached input tokens
        non_cached_input = max(0, input_tokens - cached_input_tokens)
        input_cost = (non_cached_input / 1_000_000) * pricing.get("input", 3.0)
        cached_cost = (cached_input_tokens / 1_000_000) * pricing.get("cached_input", 0.3)
        output_cost = (output_tokens / 1_000_000) * pricing.get("output", 15.0)
        return input_cost + cached_cost + output_cost

    def _log_cost_entry(self, entry: dict):
        """Log a cost entry to the monthly cost file.

        Storage location: data/system/token_usage/yyyy-mm.jsonl
        """
        now = datetime.now()
        cost_file = USAGE_DIR / f"{now.strftime('%Y-%m')}.jsonl"
        USAGE_DIR.mkdir(parents=True, exist_ok=True)

        with open(cost_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_cost_summary(self, days: int = 30) -> dict:
        """Get cost summary for the specified number of days.

        Args:
            days: Number of days to look back (default 30)

        Returns:
            Dict with total cost, calls, and per-agent breakdown
        """
        from datetime import timedelta

        now = datetime.now()
        start_date = now - timedelta(days=days - 1)

        entries = []
        # Load all relevant monthly files
        current = start_date.replace(day=1)
        while current <= now:
            cost_file = USAGE_DIR / f"{current.strftime('%Y-%m')}.jsonl"
            if cost_file.exists():
                with open(cost_file) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                entry = json.loads(line)
                                # Filter by date
                                entry_date = datetime.fromisoformat(entry.get("timestamp", "")[:10])
                                if entry_date >= start_date.replace(hour=0, minute=0, second=0):
                                    entries.append(entry)
                            except (json.JSONDecodeError, ValueError):
                                pass
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

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
                }
            agents[agent_id]["cost"] += entry.get("cost", 0)
            agents[agent_id]["calls"] += 1
            agents[agent_id]["input_tokens"] += entry.get("input_tokens", 0)
            agents[agent_id]["output_tokens"] += entry.get("output_tokens", 0)

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

    def acquire(self, agent_id: str, estimated_input_tokens: int,
                enabled_agent_count: int = 1) -> bool:
        """Acquire permission for an LLM call (pre-call check).

        This should be called BEFORE making an LLM API call with
        token estimates from the tokenizer.

        Args:
            agent_id: ID of the calling agent
            estimated_input_tokens: Estimated input tokens for this call
            enabled_agent_count: Number of enabled agents for budget splitting

        Returns:
            True if call can proceed

        Raises:
            AgentPausedError: If agent is paused or threshold exceeded
        """
        ta_config = self._get_token_awareness_config()
        if not ta_config.get("enabled", True):
            return True

        with self._lock:
            # Check if agent is already paused
            if agent_id in self._paused_agents:
                raise AgentPausedError(
                    agent_id,
                    self._pause_reasons.get(agent_id, "threshold exceeded")
                )

            # Check agent state from config
            state = self._get_agent_state_from_config(agent_id)
            if state == AgentState.DISABLED:
                raise AgentPausedError(agent_id, "agent is disabled")
            if state == AgentState.PAUSED:
                self._paused_agents.add(agent_id)
                raise AgentPausedError(agent_id, "agent is paused")

            # Get budget configuration
            budget_config = self._get_agent_budget_config(agent_id)
            total_budget, period_name = self._calculate_period_budget(
                enabled_agent_count, budget_config.frequency
            )

            # Calculate separate input/output budgets
            input_budget = int(total_budget * budget_config.input_ratio)

            # Get current usage
            usage = self._get_agent_usage(agent_id, budget_config.frequency)

            # Check if adding these tokens would exceed threshold
            thresholds = ta_config.get("thresholds", {})
            warning_percent = thresholds.get("warning_percent", 80)
            pause_percent = thresholds.get("pause_percent", 100)

            projected_input = usage["input"] + estimated_input_tokens
            input_percent = (projected_input / input_budget * 100) if input_budget > 0 else 0

            # Check for pause threshold
            if input_percent >= pause_percent:
                self._pause_agent(
                    agent_id,
                    f"input token threshold exceeded ({input_percent:.0f}%)",
                    IncidentType.INPUT_THRESHOLD_EXCEEDED,
                    {
                        "usage": usage["input"],
                        "projected": projected_input,
                        "limit": input_budget,
                        "percent": input_percent
                    }
                )
                raise AgentPausedError(
                    agent_id,
                    f"input token threshold exceeded ({input_percent:.0f}%)"
                )

            # Check for warning threshold
            if input_percent >= warning_percent:
                self._record_warning(
                    agent_id,
                    f"approaching input token limit ({input_percent:.0f}%)",
                    IncidentType.INPUT_THRESHOLD_WARNING,
                    {
                        "usage": usage["input"],
                        "limit": input_budget,
                        "percent": input_percent
                    }
                )

            return True

    def record(self, agent_id: str, input_tokens: int, output_tokens: int,
               provider: str = "openai", model: str = "unknown",
               enabled_agent_count: int = 1, job_id: Optional[str] = None,
               cached_input_tokens: int = 0, stop_reason: str = None,
               duration_ms: int = None, timestamp: str = None):
        """Record actual token usage after an API call.

        This should be called AFTER a successful LLM API call with
        the actual token counts from the API response.

        Args:
            agent_id: ID of the calling agent
            input_tokens: Actual input tokens used
            output_tokens: Actual output tokens used
            provider: LLM provider name
            model: Model name
            enabled_agent_count: Number of enabled agents
            job_id: Optional job ID for per-job tracking
            cached_input_tokens: Cached input tokens (subset of input_tokens)
            stop_reason: Reason the model stopped
            duration_ms: Duration of the API call
            timestamp: ISO timestamp for correlation
        """
        ta_config = self._get_token_awareness_config()
        if not ta_config.get("enabled", True):
            return

        # Calculate cost
        cost = self._calculate_cost(provider, input_tokens, output_tokens, cached_input_tokens)

        # Log to monthly cost file
        call_timestamp = timestamp or datetime.now().isoformat()
        self._log_cost_entry({
            "timestamp": call_timestamp,
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
        })

        # Emit SSE event for UI updates (monitoring view)
        emit_ui_event("monitoring:llm_call", {
            "agent_id": agent_id,
            "timestamp": call_timestamp,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": round(cost, 6),
            "duration_ms": duration_ms,
        })

        with self._lock:
            # Get budget configuration
            budget_config = self._get_agent_budget_config(agent_id)
            total_budget, period_name = self._calculate_period_budget(
                enabled_agent_count, budget_config.frequency
            )

            # Calculate output budget
            output_budget = int(total_budget * budget_config.output_ratio)

            # Get and update usage
            usage = self._get_agent_usage(agent_id, budget_config.frequency)
            usage["input"] += input_tokens
            usage["output"] += output_tokens

            # Persist usage
            self._save_usage_data()

            # Log the usage
            self._logger.info({
                "event": "token_usage_recorded",
                "agent_id": agent_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "provider": provider,
                "model": model,
                "cost": round(cost, 6),
                "cumulative_input": usage["input"],
                "cumulative_output": usage["output"]
            })

            # Check output threshold
            thresholds = ta_config.get("thresholds", {})
            warning_percent = thresholds.get("warning_percent", 80)
            pause_percent = thresholds.get("pause_percent", 100)

            output_percent = (usage["output"] / output_budget * 100) if output_budget > 0 else 0

            # Check for pause threshold on output
            if output_percent >= pause_percent:
                self._pause_agent(
                    agent_id,
                    f"output token threshold exceeded ({output_percent:.0f}%)",
                    IncidentType.OUTPUT_THRESHOLD_EXCEEDED,
                    {
                        "usage": usage["output"],
                        "limit": output_budget,
                        "percent": output_percent
                    }
                )
            elif output_percent >= warning_percent:
                self._record_warning(
                    agent_id,
                    f"approaching output token limit ({output_percent:.0f}%)",
                    IncidentType.OUTPUT_THRESHOLD_WARNING,
                    {
                        "usage": usage["output"],
                        "limit": output_budget,
                        "percent": output_percent
                    }
                )

    def _pause_agent(self, agent_id: str, reason: str,
                     incident_type: IncidentType, details: dict):
        """Pause an agent due to threshold breach."""
        self._paused_agents.add(agent_id)
        self._pause_reasons[agent_id] = reason
        self._pause_timestamps[agent_id] = datetime.now().isoformat()

        # Save state to config
        self._save_agent_state(agent_id, AgentState.PAUSED, reason)
        self._save_usage_data()

        # Record incident
        get_incident_tracker().record(
            agent_id=agent_id,
            incident_type=incident_type,
            reason=reason,
            severity=IncidentSeverity.CRITICAL,
            details=details
        )

        # Log event
        self._logger.info({
            "event": "agent_paused",
            "agent_id": agent_id,
            "reason": reason,
            **details
        })

        # Emit SSE event
        emit_ui_event("agent:paused", {
            "agent_id": agent_id,
            "reason": reason,
            "timestamp": self._pause_timestamps[agent_id]
        })

        print(f"[TOKEN-AWARENESS] Agent '{agent_id}' paused: {reason}")

    def _record_warning(self, agent_id: str, reason: str,
                        incident_type: IncidentType, details: dict):
        """Record a warning incident (no pause)."""
        get_incident_tracker().record(
            agent_id=agent_id,
            incident_type=incident_type,
            reason=reason,
            severity=IncidentSeverity.WARNING,
            details=details
        )

        self._logger.info({
            "event": "token_warning",
            "agent_id": agent_id,
            "reason": reason,
            **details
        })

    def get_agent_state(self, agent_id: str) -> AgentState:
        """Get the current state of an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            AgentState enum value
        """
        with self._lock:
            # Check in-memory pause state first
            if agent_id in self._paused_agents:
                return AgentState.PAUSED

            # Then check config
            return self._get_agent_state_from_config(agent_id)

    def set_agent_state(self, agent_id: str, state: AgentState,
                        reason: Optional[str] = None):
        """Set an agent's state.

        Args:
            agent_id: ID of the agent
            state: New state to set
            reason: Optional reason (used for PAUSED state)
        """
        with self._lock:
            # Update in-memory state
            if state == AgentState.PAUSED:
                self._paused_agents.add(agent_id)
                self._pause_reasons[agent_id] = reason or "manually paused"
                self._pause_timestamps[agent_id] = datetime.now().isoformat()
            else:
                self._paused_agents.discard(agent_id)
                self._pause_reasons.pop(agent_id, None)
                self._pause_timestamps.pop(agent_id, None)

            # Persist to config
            self._save_agent_state(agent_id, state, reason)
            self._save_usage_data()

            # Log event
            self._logger.info({
                "event": "agent_state_changed",
                "agent_id": agent_id,
                "state": state.value,
                "reason": reason
            })

            # Emit SSE event
            if state == AgentState.ENABLED:
                emit_ui_event("agent:resumed", {"agent_id": agent_id})
            elif state == AgentState.PAUSED:
                emit_ui_event("agent:paused", {
                    "agent_id": agent_id,
                    "reason": reason
                })

    def enable_agent(self, agent_id: str):
        """Enable an agent (resume from paused or disabled state)."""
        self.set_agent_state(agent_id, AgentState.ENABLED)
        print(f"[TOKEN-AWARENESS] Agent '{agent_id}' enabled")

    def disable_agent(self, agent_id: str):
        """Disable an agent."""
        self.set_agent_state(agent_id, AgentState.DISABLED)
        print(f"[TOKEN-AWARENESS] Agent '{agent_id}' disabled")

    def get_agent_usage(self, agent_id: str) -> dict:
        """Get usage statistics for an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            Dict with input, output token counts and budget info
        """
        with self._lock:
            budget_config = self._get_agent_budget_config(agent_id)
            usage = self._get_agent_usage(agent_id, budget_config.frequency)

            # Calculate budgets (assume 1 agent for now, will be updated)
            total_budget, period_name = self._calculate_period_budget(1, budget_config.frequency)
            input_budget = int(total_budget * budget_config.input_ratio)
            output_budget = int(total_budget * budget_config.output_ratio)

            return {
                "agent_id": agent_id,
                "state": self.get_agent_state(agent_id).value,
                "frequency": budget_config.frequency,
                "period": usage.get("period_key"),
                "input_tokens": usage.get("input", 0),
                "output_tokens": usage.get("output", 0),
                "input_budget": input_budget,
                "output_budget": output_budget,
                "input_percent": round(usage.get("input", 0) / input_budget * 100, 1) if input_budget > 0 else 0,
                "output_percent": round(usage.get("output", 0) / output_budget * 100, 1) if output_budget > 0 else 0,
            }

    def get_all_agent_usage(self) -> dict:
        """Get usage statistics for all tracked agents.

        Returns:
            Dict mapping agent_id to usage stats
        """
        with self._lock:
            result = {}
            for agent_id in self._agent_usage:
                result[agent_id] = self.get_agent_usage(agent_id)
            return result

    def get_pause_info(self, agent_id: str) -> dict:
        """Get pause information for an agent.

        Returns:
            Dict with is_paused, reason, timestamp
        """
        with self._lock:
            if agent_id in self._paused_agents:
                return {
                    "is_paused": True,
                    "reason": self._pause_reasons.get(agent_id, "unknown"),
                    "timestamp": self._pause_timestamps.get(agent_id)
                }
            return {"is_paused": False}

    def invalidate_config(self):
        """Invalidate cached configuration."""
        with self._lock:
            self._config_cache = None
            self._config_mtime = 0


# Singleton instance
_token_awareness: Optional[TokenAwareness] = None
_token_awareness_lock = threading.Lock()


def get_token_awareness() -> TokenAwareness:
    """Get the global TokenAwareness instance."""
    global _token_awareness
    with _token_awareness_lock:
        if _token_awareness is None:
            _token_awareness = TokenAwareness()
        return _token_awareness


def get_calls_by_job(job_id: str, days: int = 30) -> list:
    """Get all API calls for a specific job.

    Args:
        job_id: The job ID to filter by
        days: Number of days to look back

    Returns:
        List of API call entries for this job
    """
    ta = get_token_awareness()
    cutoff = datetime.now() - timedelta(days=days)
    results = []

    # Read from current month's log file
    log_path = ta._cost_log_path
    if log_path.exists():
        try:
            with open(log_path, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("job_id") == job_id:
                            entry_time = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
                            if entry_time.replace(tzinfo=None) >= cutoff:
                                results.append(entry)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        except Exception:
            pass

    return results


def get_job_call_count(job_id: str, days: int = 30) -> dict:
    """Get call count and cost summary for a job.

    Args:
        job_id: The job ID to summarize
        days: Number of days to look back

    Returns:
        Dict with call_count and total_cost
    """
    calls = get_calls_by_job(job_id, days)
    total_cost = sum(c.get("cost", 0) for c in calls)
    total_input = sum(c.get("input_tokens", 0) for c in calls)
    total_output = sum(c.get("output_tokens", 0) for c in calls)

    return {
        "job_id": job_id,
        "call_count": len(calls),
        "total_cost": round(total_cost, 6),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output
    }


def get_costs_by_agent(days: int = 30) -> dict:
    """Get cost breakdown by agent for the specified period.

    Args:
        days: Number of days to look back

    Returns:
        Dict mapping agent_id to cost summary
    """
    ta = get_token_awareness()
    cutoff = datetime.now() - timedelta(days=days)
    by_agent = {}

    log_path = ta._cost_log_path
    if log_path.exists():
        try:
            with open(log_path, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        entry_time = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
                        if entry_time.replace(tzinfo=None) >= cutoff:
                            agent_id = entry.get("agent", "unknown")
                            if agent_id not in by_agent:
                                by_agent[agent_id] = {"calls": 0, "cost": 0, "input_tokens": 0, "output_tokens": 0}
                            by_agent[agent_id]["calls"] += 1
                            by_agent[agent_id]["cost"] += entry.get("cost", 0)
                            by_agent[agent_id]["input_tokens"] += entry.get("input_tokens", 0)
                            by_agent[agent_id]["output_tokens"] += entry.get("output_tokens", 0)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        except Exception:
            pass

    return by_agent


def get_resource_tracker():
    """Get resource tracking data (for backward compatibility).

    Returns:
        Dict with resource utilization metrics
    """
    # This is a stub for backward compatibility after removing resources.py
    # Returns basic resource info derived from token tracking
    ta = get_token_awareness()
    return {
        "tracked_agents": list(ta._agent_usage.keys()),
        "paused_agents": list(ta._paused_agents),
    }


def get_cost_summary(days: int = 30) -> dict:
    """Get cost summary for the specified number of days.

    This is a convenience wrapper around TokenAwareness.get_cost_summary().

    Args:
        days: Number of days to look back (default 30)

    Returns:
        Dict with total cost, calls, and per-agent breakdown
    """
    return get_token_awareness().get_cost_summary(days)
