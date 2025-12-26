"""Self tools - epistemic axioms at the foundation, values derived from them.

Hierarchy:
1. Epistemic (foundational) - axioms, mental models, reasoning tools
2. Values (derived) - what you care about, emergent from epistemic core
3. Behaviors (reveals) - how you act, shows which axioms are operative
4. Context (supporting) - biographical facts and relationships
"""

from .epistemic import (
    EPISTEMIC_TOOLS, EPISTEMIC_HANDLERS,
    get_axioms, write_axioms,
    get_mental_models, write_mental_models,
    get_epistemic_tools, write_epistemic_tools,
    get_all_epistemic, note_epistemic_shift, get_epistemic_shifts,
    EPISTEMIC_DIR
)
from .values import (
    VALUES_TOOLS, VALUES_HANDLERS,
    get_current_values, get_phase_values, get_lifetime_values, get_all_values,
    write_current_values, write_phase_values, write_lifetime_values,
    get_all_summaries, note_value_tension, get_value_tensions,
    SELF_DIR, VALUES_DIR
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
    get_profile, generate_profile, get_self_summary
)
from .summary import (
    SUMMARY_TOOLS, SUMMARY_HANDLERS,
    get_year_logs, get_manifest, get_summary, write_summary,
    check_summary_needed, list_years
)

# Combined tools for convenience - epistemic first (foundational)
ALL_SELF_TOOLS = EPISTEMIC_TOOLS + VALUES_TOOLS + BEHAVIOR_TOOLS + CONTEXT_TOOLS + PROFILE_TOOLS
ALL_SELF_HANDLERS = {
    **EPISTEMIC_HANDLERS,
    **VALUES_HANDLERS,
    **BEHAVIOR_HANDLERS,
    **CONTEXT_HANDLERS,
    **PROFILE_HANDLERS
}

# Backwards compatibility aliases
ALL_IDENTITY_TOOLS = ALL_SELF_TOOLS
ALL_IDENTITY_HANDLERS = ALL_SELF_HANDLERS
IDENTITY_DIR = SELF_DIR
get_identity_summary = get_self_summary

__all__ = [
    # Self paths
    'SELF_DIR', 'VALUES_DIR', 'EPISTEMIC_DIR',
    # Combined
    'ALL_SELF_TOOLS', 'ALL_SELF_HANDLERS',
    # Backwards compatibility
    'ALL_IDENTITY_TOOLS', 'ALL_IDENTITY_HANDLERS', 'IDENTITY_DIR', 'get_identity_summary',
    # Epistemic tools (foundational)
    'EPISTEMIC_TOOLS', 'EPISTEMIC_HANDLERS',
    'get_axioms', 'write_axioms',
    'get_mental_models', 'write_mental_models',
    'get_epistemic_tools', 'write_epistemic_tools',
    'get_all_epistemic', 'note_epistemic_shift', 'get_epistemic_shifts',
    # Values tools (derived from epistemic core)
    'VALUES_TOOLS', 'VALUES_HANDLERS',
    'get_current_values', 'get_phase_values', 'get_lifetime_values', 'get_all_values',
    'write_current_values', 'write_phase_values', 'write_lifetime_values',
    'get_all_summaries', 'note_value_tension', 'get_value_tensions',
    # Behavior tools (reveals operative axioms)
    'BEHAVIOR_TOOLS', 'BEHAVIOR_HANDLERS',
    'get_behaviors', 'write_behaviors', 'note_behavior_pattern',
    # Context tools (supporting)
    'CONTEXT_TOOLS', 'CONTEXT_HANDLERS',
    'get_biographical', 'update_biographical',
    'get_relationships', 'get_relationship', 'add_relationship', 'update_relationship',
    # Profile tools (consolidated)
    'PROFILE_TOOLS', 'PROFILE_HANDLERS',
    'get_profile', 'generate_profile', 'get_self_summary',
    # Summary tools
    'SUMMARY_TOOLS', 'SUMMARY_HANDLERS',
    'get_year_logs', 'get_manifest', 'get_summary', 'write_summary',
    'check_summary_needed', 'list_years',
]
