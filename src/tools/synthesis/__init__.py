"""Synthesis tools - profile generation and identity management.

The profile is generated from temporal profiles (yearly snapshots) and
stored in synthesis/state/profile/. The profile is synced to
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
from ..shared.profile_signals import (
    SYNTHESIS_SIGNAL_TOOLS, SYNTHESIS_SIGNAL_HANDLERS,
    get_pending_observations, consume_observations
)

# Combined tools for convenience
ALL_SYNTHESIS_TOOLS = (
    TEMPORAL_TOOLS + PROFILE_TOOLS + PRIVATE_PROFILE_TOOLS +
    SUMMARY_TOOLS + SYNTHESIS_SIGNAL_TOOLS
)
ALL_SYNTHESIS_HANDLERS = {
    **TEMPORAL_HANDLERS,
    **PROFILE_HANDLERS,
    **PRIVATE_PROFILE_HANDLERS,
    **SUMMARY_HANDLERS,
    **SYNTHESIS_SIGNAL_HANDLERS,
}

__all__ = [
    # Paths
    'PROFILE_DIR',
    # Combined
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
    # Signal consumption tools
    'SYNTHESIS_SIGNAL_TOOLS', 'SYNTHESIS_SIGNAL_HANDLERS',
    'get_pending_observations', 'consume_observations',
]
