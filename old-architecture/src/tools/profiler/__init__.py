"""Profiler tools - profile generation and behavioral pattern extraction.

The profile is generated from temporal profiles (yearly snapshots) and
stored in profiler/state/profile/. The profile is synced to
shared/state/profile/ for other agents to access.
"""

from .profile import (
    PROFILE_TOOLS, PROFILE_HANDLERS,
    get_profile, get_synthesis_summary,
    PROFILE_DIR
)
from .summary import (
    SUMMARY_TOOLS, SUMMARY_HANDLERS,
    get_year_logs, get_manifest, get_summary, write_summary,
    check_summary_needed, list_years
)
from .temporal import (
    TEMPORAL_TOOLS, TEMPORAL_HANDLERS,
    get_temporal_profile, write_temporal_profile, list_temporal_profiles,
    get_evolution, write_evolution,
    get_influence_timeline, add_influence_to_timeline,
    generate_current_profile, generate_public_profile, get_public_profile
)
from .private_profile import (
    PRIVATE_PROFILE_TOOLS, PRIVATE_PROFILE_HANDLERS,
    get_private_profile, write_private_profile, get_profile_section,
    get_handlers_for_agent
)
from .project_patterns import (
    PROJECT_PATTERN_TOOLS, PROJECT_PATTERN_HANDLERS,
    get_project_task_patterns, get_values_actualization_analysis,
    get_abandonment_patterns
)
from ..shared.profile_signals import (
    PROFILER_SIGNAL_TOOLS, PROFILER_SIGNAL_HANDLERS,
    get_pending_observations, consume_observations
)

# Combined tools for convenience
ALL_PROFILER_TOOLS = (
    TEMPORAL_TOOLS + PROFILE_TOOLS + PRIVATE_PROFILE_TOOLS +
    SUMMARY_TOOLS + PROFILER_SIGNAL_TOOLS + PROJECT_PATTERN_TOOLS
)
ALL_PROFILER_HANDLERS = {
    **TEMPORAL_HANDLERS,
    **PROFILE_HANDLERS,
    **PRIVATE_PROFILE_HANDLERS,
    **SUMMARY_HANDLERS,
    **PROFILER_SIGNAL_HANDLERS,
    **PROJECT_PATTERN_HANDLERS,
}

# Backwards compatibility aliases
ALL_SYNTHESIS_TOOLS = ALL_PROFILER_TOOLS
ALL_SYNTHESIS_HANDLERS = ALL_PROFILER_HANDLERS
SYNTHESIS_SIGNAL_TOOLS = PROFILER_SIGNAL_TOOLS
SYNTHESIS_SIGNAL_HANDLERS = PROFILER_SIGNAL_HANDLERS

__all__ = [
    # Paths
    'PROFILE_DIR',
    # Combined (new names)
    'ALL_PROFILER_TOOLS', 'ALL_PROFILER_HANDLERS',
    # Combined (backwards compatibility)
    'ALL_SYNTHESIS_TOOLS', 'ALL_SYNTHESIS_HANDLERS',
    # Profile tools
    'PROFILE_TOOLS', 'PROFILE_HANDLERS',
    'get_profile', 'get_synthesis_summary',
    # Summary tools
    'SUMMARY_TOOLS', 'SUMMARY_HANDLERS',
    'get_year_logs', 'get_manifest', 'get_summary', 'write_summary',
    'check_summary_needed', 'list_years',
    # Temporal tools
    'TEMPORAL_TOOLS', 'TEMPORAL_HANDLERS',
    'get_temporal_profile', 'write_temporal_profile', 'list_temporal_profiles',
    'get_evolution', 'write_evolution',
    'get_influence_timeline', 'add_influence_to_timeline',
    'generate_current_profile', 'generate_public_profile', 'get_public_profile',
    # Private profile tools
    'PRIVATE_PROFILE_TOOLS', 'PRIVATE_PROFILE_HANDLERS',
    'get_private_profile', 'write_private_profile', 'get_profile_section',
    'get_handlers_for_agent',
    # Project pattern tools
    'PROJECT_PATTERN_TOOLS', 'PROJECT_PATTERN_HANDLERS',
    'get_project_task_patterns', 'get_values_actualization_analysis',
    'get_abandonment_patterns',
    # Signal consumption tools
    'PROFILER_SIGNAL_TOOLS', 'PROFILER_SIGNAL_HANDLERS',
    'SYNTHESIS_SIGNAL_TOOLS', 'SYNTHESIS_SIGNAL_HANDLERS',  # backwards compat
    'get_pending_observations', 'consume_observations',
]
