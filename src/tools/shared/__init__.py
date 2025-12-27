"""Shared tools for cross-agent functionality."""

from .log import (
    LOG_TOOLS, LOG_HANDLERS,
    write_log_entry, read_log_entry, search_log, get_recent_entries
)
from .identity import (
    IDENTITY_TOOLS, IDENTITY_HANDLERS,
    read_own_identity, read_core_identity, propose_identity_evolution,
    get_pending_evolutions, approve_evolution, reject_evolution
)
from .notifications import create_euno_task
from .agent_log import (
    AGENT_LOG_TOOLS, AGENT_LOG_HANDLERS,
    log_activity, log_tool_call, log_work_check, log_work_start,
    log_work_complete, log_signal_sent, log_error, get_agent_log,
    get_all_agent_logs, get_recent_agent_activity
)
from .profile_signals import (
    PROFILE_SIGNAL_TOOLS, PROFILE_SIGNAL_HANDLERS,
    SYNTHESIS_SIGNAL_TOOLS, SYNTHESIS_SIGNAL_HANDLERS,
    emit_profile_observation, get_pending_observations, consume_observations,
    count_pending_observations
)

__all__ = [
    # Log tools
    'LOG_TOOLS', 'LOG_HANDLERS',
    'write_log_entry', 'read_log_entry', 'search_log', 'get_recent_entries',
    # Identity tools
    'IDENTITY_TOOLS', 'IDENTITY_HANDLERS',
    'read_own_identity', 'read_core_identity', 'propose_identity_evolution',
    'get_pending_evolutions', 'approve_evolution', 'reject_evolution',
    # Euno task creation (for agent-to-user communication)
    'create_euno_task',
    # Agent logging
    'AGENT_LOG_TOOLS', 'AGENT_LOG_HANDLERS',
    'log_activity', 'log_tool_call', 'log_work_check', 'log_work_start',
    'log_work_complete', 'log_signal_sent', 'log_error', 'get_agent_log',
    'get_all_agent_logs', 'get_recent_agent_activity',
    # Profile signals (for contributing to profile updates)
    'PROFILE_SIGNAL_TOOLS', 'PROFILE_SIGNAL_HANDLERS',
    'SYNTHESIS_SIGNAL_TOOLS', 'SYNTHESIS_SIGNAL_HANDLERS',
    'emit_profile_observation', 'get_pending_observations', 'consume_observations',
    'count_pending_observations',
]
