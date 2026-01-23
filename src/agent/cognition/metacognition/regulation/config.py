"""
Metacognition Configuration - Handles loading and merging of metacognition settings.

System-wide defaults are in data/system/config.json under "metacognition".
Individual agents can override specific settings in their config.json.
"""

import json
from pathlib import Path
from typing import Optional


DATA_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "data"
CONFIG_PATH = DATA_DIR / "system" / "config.json"
AGENTS_DIR = DATA_DIR / "agents"

# Default metacognition settings (fallback if config is missing)
# Note: velocity (rate limiting) and resources (budget) are now in llm.* config
DEFAULT_CONFIG = {
    "progress": {
        "max_tool_calls_per_iteration": 50,
        "max_repeated_tool_calls": 3,
        "max_no_progress_iterations": 5
    },
    "planning": {
        "enabled_for": ["exploration", "consolidation"]
    },
    "efficiency": {
        "defer_consolidation_in_work_cycles": True
    },
    "consolidation": {
        "append_max_tokens": 500,
        "append_batch_max_tokens": 1000,
        "consolidate_max_tokens": 2000,
        "upload_analysis_max_tokens": 1000
    }
}


class MetacognitionConfig:
    """Configuration handler for metacognition settings.

    Merges system-wide defaults with optional per-agent overrides.
    """

    def __init__(self, agent_id: Optional[str] = None):
        """Initialize metacognition config.

        Args:
            agent_id: Optional agent ID for per-agent overrides
        """
        self.agent_id = agent_id
        self._config_cache: Optional[dict] = None
        self._config_mtime: float = 0

    def _load_system_config(self) -> dict:
        """Load system-wide metacognition config with caching."""
        try:
            current_mtime = CONFIG_PATH.stat().st_mtime
            if self._config_cache is not None and current_mtime == self._config_mtime:
                return self._config_cache

            with open(CONFIG_PATH) as f:
                config = json.load(f)

            self._config_cache = config.get("metacognition", {})
            self._config_mtime = current_mtime
            return self._config_cache
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def _load_agent_overrides(self) -> dict:
        """Load agent-specific metacognition overrides."""
        if not self.agent_id:
            return {}

        config_path = AGENTS_DIR / self.agent_id / "config.json"
        if not config_path.exists():
            return {}

        try:
            with open(config_path) as f:
                config = json.load(f)
            return config.get("metacognition", {})
        except (json.JSONDecodeError, OSError):
            return {}

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge two dicts, with override taking precedence."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get_full_config(self) -> dict:
        """Get fully merged metacognition config.

        Priority: agent overrides > system config > defaults
        """
        # Start with defaults
        config = DEFAULT_CONFIG.copy()

        # Merge system config
        system = self._load_system_config()
        config = self._deep_merge(config, system)

        # Merge agent overrides
        agent = self._load_agent_overrides()
        config = self._deep_merge(config, agent)

        return config

    def get_progress_config(self) -> dict:
        """Get progress awareness configuration."""
        full = self.get_full_config()
        return full.get("progress", DEFAULT_CONFIG["progress"])

    def get_planning_config(self) -> dict:
        """Get planning configuration."""
        full = self.get_full_config()
        return full.get("planning", DEFAULT_CONFIG["planning"])

    def get_efficiency_config(self) -> dict:
        """Get efficiency optimization configuration."""
        full = self.get_full_config()
        return full.get("efficiency", DEFAULT_CONFIG["efficiency"])

    def get_consolidation_config(self) -> dict:
        """Get consolidation (memory processing) configuration."""
        full = self.get_full_config()
        return full.get("consolidation", DEFAULT_CONFIG["consolidation"])

    def invalidate(self):
        """Invalidate cached config. Call when settings change."""
        self._config_cache = None
        self._config_mtime = 0


# Global config instance for system-wide access
_global_config: Optional[MetacognitionConfig] = None


def get_global_config() -> MetacognitionConfig:
    """Get the global metacognition config instance."""
    global _global_config
    if _global_config is None:
        _global_config = MetacognitionConfig()
    return _global_config
