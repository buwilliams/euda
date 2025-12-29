"""
Tools package for Euno agents.

Tools are organized by agent concern:
- shared: Cross-agent tools (log, identity, signals)
- archivist: File processing and classification
- profiler: User profile (from temporal profiles)
- curator: Surfacing queue and energy tracking
- friend: Conversations and cards
- worker: Tasks and projects (including From Euno agent communication)
- adaptor: System analysis and identity evolution
"""

# Re-export from submodules for backwards compatibility
from .shared import (
    LOG_TOOLS, LOG_HANDLERS,
    write_log_entry, read_log_entry, search_log, get_recent_entries,
    IDENTITY_TOOLS, IDENTITY_HANDLERS,
    AGENT_LOG_TOOLS, AGENT_LOG_HANDLERS,
    log_activity, get_agent_log, get_all_agent_logs,
    create_euno_task,
)

from .archivist import (
    FILE_TOOLS, FILE_HANDLERS,
    list_pending_files, read_file_content, mark_file_processed, mark_file_failed,
    extract_temporal_hints, PENDING_DIR,
    CLASSIFIER_TOOLS, CLASSIFIER_HANDLERS,
    classify_file, is_duplicate, compute_file_hash,
    DIGEST_TOOLS, DIGEST_HANDLERS,
    generate_digest, get_content_for_ai,
    QUEUE_TOOLS, QUEUE_HANDLERS,
    get_queue as get_archivist_queue, IngestionQueue,
    TOKEN_BUDGET_TOOLS, TOKEN_BUDGET_HANDLERS,
    get_budget, TokenBudget,
)

from .profiler import (
    SUMMARY_TOOLS, SUMMARY_HANDLERS,
    get_year_logs, get_manifest, get_summary, write_summary,
    check_summary_needed, list_years,
    PROFILE_TOOLS, PROFILE_HANDLERS,
    get_profile, get_synthesis_summary,
    TEMPORAL_TOOLS, TEMPORAL_HANDLERS,
    generate_current_profile,
    ALL_PROFILER_TOOLS, ALL_PROFILER_HANDLERS,
    ALL_SYNTHESIS_TOOLS, ALL_SYNTHESIS_HANDLERS,  # backwards compat
)

from .curator import (
    ATTENTION_TOOLS, ATTENTION_HANDLERS,
    get_queue, add_to_queue, mark_surfaced,
    record_energy, get_recent_energy,
)

from .friend import (
    CONVERSATION_TOOLS, CONVERSATION_HANDLERS,
    clear_conversation, reset_clear_flag, was_clear_requested,
    CONVERSATION_HISTORY_TOOLS, CONVERSATION_HISTORY_HANDLERS,
    save_message, get_conversation, get_conversations_for_date,
    search_conversations, get_conversation_themes, get_recent_conversations,
    CARDS_TOOLS, CARDS_HANDLERS,
    get_internal_card, get_public_card, write_public_card,
    get_received_cards, update_received_card_status, approve_public_card,
)

from .worker import (
    TASK_TOOLS, TASK_HANDLERS,
    create_task, get_tasks, get_task, update_task_status,
    get_daily_view, add_quick_task, store_result, get_recent_results,
    PROJECT_TOOLS, PROJECT_HANDLERS,
    create_project, get_projects, get_project, update_project,
    add_milestone, archive_project, get_projects_with_deadlines,
    WORKER_TOOLS, WORKER_HANDLERS, EXTENDED_WORKER_TOOLS,
)

from .adaptor import (
    EVOLUTION_TOOLS, EVOLUTION_HANDLERS,
    get_last_introspection, get_system_overview,
)

# Backwards compatibility aliases
INTROSPECTION_TOOLS = EVOLUTION_TOOLS
INTROSPECTION_HANDLERS = EVOLUTION_HANDLERS
get_ingestion_queue = get_archivist_queue
