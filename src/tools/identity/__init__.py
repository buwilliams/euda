"""Identity tools - values at the core, with supporting context.

Hierarchy:
1. Values (core) - who you ARE
2. Behaviors (derived) - how you actually act
3. Context (supporting) - biographical facts and relationships
"""

from .values import (
    VALUES_TOOLS, VALUES_HANDLERS,
    get_current_values, get_phase_values, get_lifetime_values, get_all_values,
    write_current_values, write_phase_values, write_lifetime_values,
    get_all_summaries, note_value_tension, get_value_tensions,
    IDENTITY_DIR, VALUES_DIR
)
from .behaviors import (
    BEHAVIOR_TOOLS, BEHAVIOR_HANDLERS,
    get_behaviors, write_behaviors, note_behavior_pattern
)
from .context import (
    CONTEXT_TOOLS, CONTEXT_HANDLERS,
    get_biographical, update_biographical,
    get_relationships, get_relationship, add_relationship, update_relationship
)
from .profile import (
    PROFILE_TOOLS, PROFILE_HANDLERS,
    get_profile, generate_profile, get_identity_summary
)
from .summary import (
    SUMMARY_TOOLS, SUMMARY_HANDLERS,
    get_year_logs, get_manifest, get_summary, write_summary,
    check_summary_needed, list_years
)

# Combined tools for convenience
ALL_IDENTITY_TOOLS = VALUES_TOOLS + BEHAVIOR_TOOLS + CONTEXT_TOOLS + PROFILE_TOOLS
ALL_IDENTITY_HANDLERS = {
    **VALUES_HANDLERS,
    **BEHAVIOR_HANDLERS,
    **CONTEXT_HANDLERS,
    **PROFILE_HANDLERS
}

__all__ = [
    # Identity paths
    'IDENTITY_DIR', 'VALUES_DIR',
    # Combined
    'ALL_IDENTITY_TOOLS', 'ALL_IDENTITY_HANDLERS',
    # Values tools (core identity)
    'VALUES_TOOLS', 'VALUES_HANDLERS',
    'get_current_values', 'get_phase_values', 'get_lifetime_values', 'get_all_values',
    'write_current_values', 'write_phase_values', 'write_lifetime_values',
    'get_all_summaries', 'note_value_tension', 'get_value_tensions',
    # Behavior tools (derived)
    'BEHAVIOR_TOOLS', 'BEHAVIOR_HANDLERS',
    'get_behaviors', 'write_behaviors', 'note_behavior_pattern',
    # Context tools (supporting)
    'CONTEXT_TOOLS', 'CONTEXT_HANDLERS',
    'get_biographical', 'update_biographical',
    'get_relationships', 'get_relationship', 'add_relationship', 'update_relationship',
    # Profile tools (consolidated)
    'PROFILE_TOOLS', 'PROFILE_HANDLERS',
    'get_profile', 'generate_profile', 'get_identity_summary',
    # Summary tools
    'SUMMARY_TOOLS', 'SUMMARY_HANDLERS',
    'get_year_logs', 'get_manifest', 'get_summary', 'write_summary',
    'check_summary_needed', 'list_years',
]
