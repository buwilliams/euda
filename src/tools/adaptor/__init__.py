"""Evolution tools for system analysis and identity evolution."""

from .evolution import (
    EVOLUTION_TOOLS, EVOLUTION_HANDLERS,
    EVOLUTION_DIR,
    list_agents, get_agent_identity, get_core_identity,
    analyze_agent_code, analyze_tools_module, list_tools_modules,
    get_last_introspection, save_capabilities, get_system_overview
)

from .health import (
    HEALTH_TOOLS, HEALTH_HANDLERS,
    assess_data_completeness, assess_configuration, assess_agent_activity,
    get_progress_metrics, identify_gaps, run_health_assessment
)

# Backwards compatibility aliases
INTROSPECTION_TOOLS = EVOLUTION_TOOLS
INTROSPECTION_HANDLERS = EVOLUTION_HANDLERS
INTROSPECTION_DIR = EVOLUTION_DIR

__all__ = [
    'EVOLUTION_TOOLS', 'EVOLUTION_HANDLERS', 'EVOLUTION_DIR',
    'HEALTH_TOOLS', 'HEALTH_HANDLERS',
    'INTROSPECTION_TOOLS', 'INTROSPECTION_HANDLERS', 'INTROSPECTION_DIR',
    'list_agents', 'get_agent_identity', 'get_core_identity',
    'analyze_agent_code', 'analyze_tools_module', 'list_tools_modules',
    'get_last_introspection', 'save_capabilities', 'get_system_overview',
    'assess_data_completeness', 'assess_configuration', 'assess_agent_activity',
    'get_progress_metrics', 'identify_gaps', 'run_health_assessment',
]
