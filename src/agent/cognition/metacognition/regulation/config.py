"""
Metacognition Configuration - Hardcoded defaults for metacognition behavior.

These settings are implementation details, not user-configurable.
Budget/cost control is handled by llm.json and token awareness.
"""

from typing import Optional


class MetacognitionConfig:
    """Configuration for metacognition behavior.

    Planning is always enabled. Consolidation is deferred during work cycles.
    Budget control is handled separately by token awareness.
    """

    def __init__(self, agent_id: Optional[str] = None):
        self.agent_id = agent_id

    def is_planning_enabled(self, job_tags: list = None) -> bool:
        """Planning is always enabled."""
        return True

    def should_defer_consolidation(self) -> bool:
        """Consolidation append is deferred until end of work cycle."""
        return True

    def invalidate(self):
        """No-op for compatibility."""
        pass


# Global config instance for system-wide access
_global_config: Optional[MetacognitionConfig] = None


def get_global_config() -> MetacognitionConfig:
    """Get the global metacognition config instance."""
    global _global_config
    if _global_config is None:
        _global_config = MetacognitionConfig()
    return _global_config
