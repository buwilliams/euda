"""
Tool Batcher - Automatically batches multiple tool calls for efficiency.

This module intercepts tool execution and batches multiple calls of the same
type into single batch operations, transparent to the LLM.
"""

from typing import List, Dict, Any


# Mapping of individual tools to their batch equivalents
BATCHABLE_TOOLS = {
    "create_job": {
        "batch_fn": "create_jobs_batch",
        "input_key": "jobs",
        "result_key": "created",
    },
    "update_job": {
        "batch_fn": "update_jobs_batch",
        "input_key": "updates",
        "result_key": "updated",
    },
    "complete_job": {
        "batch_fn": "complete_jobs_batch",
        "input_key": "job_ids",
        "result_key": "completed",
        "extract_id": "job_id",
    },
    "add_job_log": {
        "batch_fn": "add_job_logs_batch",
        "input_key": "logs",
        "result_key": "logged",
    },
}


def execute_tools_batched(tool_calls: List[dict], execute_fn, agent_id: str = None) -> List[dict]:
    """Execute tool calls, automatically batching where possible.

    Args:
        tool_calls: List of tool call blocks with 'name', 'id', 'input'
        execute_fn: Function to execute a single tool: (name, inputs) -> result
        agent_id: Agent ID for batch operations that need it

    Returns:
        List of tool results in the same order as input calls
    """
    from .tools.data.jobs import (
        create_jobs_batch, update_jobs_batch,
        complete_jobs_batch, add_job_logs_batch
    )

    batch_fns = {
        "create_jobs_batch": create_jobs_batch,
        "update_jobs_batch": update_jobs_batch,
        "complete_jobs_batch": complete_jobs_batch,
        "add_job_logs_batch": add_job_logs_batch,
    }

    # Group batchable calls by tool name, preserve order info
    grouped: Dict[str, List[tuple]] = {}  # tool_name -> [(index, block), ...]
    non_batchable: List[tuple] = []  # [(index, block), ...]

    for i, block in enumerate(tool_calls):
        if block.name in BATCHABLE_TOOLS:
            if block.name not in grouped:
                grouped[block.name] = []
            grouped[block.name].append((i, block))
        else:
            non_batchable.append((i, block))

    # Prepare results array (same length as input)
    results = [None] * len(tool_calls)

    # Execute batched operations
    for tool_name, indexed_blocks in grouped.items():
        config = BATCHABLE_TOOLS[tool_name]

        if len(indexed_blocks) == 1:
            # Single call - execute normally
            idx, block = indexed_blocks[0]
            result = execute_fn(block.name, block.input)
            results[idx] = _format_result(block.id, result)
        else:
            # Multiple calls - batch them
            batch_fn_name = config["batch_fn"]
            batch_fn = batch_fns[batch_fn_name]

            # Build batch input
            if "extract_id" in config:
                # For complete_job: extract just the IDs
                batch_input = {
                    config["input_key"]: [block.input.get(config["extract_id"]) for _, block in indexed_blocks],
                    "agent": agent_id or "agent"
                }
            elif tool_name == "create_job":
                batch_input = {
                    config["input_key"]: [block.input for _, block in indexed_blocks],
                    "created_by": agent_id or "agent"
                }
            else:
                batch_input = {
                    config["input_key"]: [block.input for _, block in indexed_blocks]
                }

            # Execute batch
            try:
                batch_result = batch_fn(**batch_input)
            except Exception as e:
                batch_result = {"error": str(e)}

            # Map results back to individual calls
            result_list = batch_result.get(config["result_key"], []) if isinstance(batch_result, dict) else []

            for i, (idx, block) in enumerate(indexed_blocks):
                if i < len(result_list):
                    individual_result = result_list[i]
                elif isinstance(batch_result, dict) and "error" in batch_result:
                    individual_result = {"error": batch_result["error"]}
                else:
                    individual_result = batch_result

                results[idx] = _format_result(block.id, individual_result)

    # Execute non-batchable operations
    for idx, block in non_batchable:
        result = execute_fn(block.name, block.input)
        results[idx] = _format_result(block.id, result)

    return results


def _format_result(tool_use_id: str, result: Any) -> dict:
    """Format a tool result for the LLM."""
    import json
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": json.dumps(result) if isinstance(result, (dict, list)) else str(result)
    }
