"""
Token Estimation Utilities

Uses tiktoken's cl100k_base encoding for all token counting.
"""

import json
from typing import Optional

import tiktoken

_encoding = None


def _get_encoding():
    """Get the cached tiktoken encoding."""
    global _encoding
    if _encoding is None:
        _encoding = tiktoken.get_encoding("cl100k_base")
    return _encoding


def count_tokens(text: str) -> int:
    """Count tokens in a string."""
    if not text:
        return 0
    return len(_get_encoding().encode(text))


def estimate_request_tokens(system: str, messages: list, tools: Optional[list] = None) -> int:
    """Estimate input tokens for an LLM request."""
    tokens = 10  # Base overhead

    tokens += count_tokens(system)

    for message in messages:
        tokens += 4  # Per-message overhead
        content = message.get("content", "")

        if isinstance(content, str):
            tokens += count_tokens(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if "text" in block:
                        tokens += count_tokens(block["text"])
                    elif "content" in block:
                        result_content = block["content"]
                        if isinstance(result_content, str):
                            tokens += count_tokens(result_content)
                        else:
                            tokens += count_tokens(json.dumps(result_content))
                    elif "input" in block:
                        tokens += count_tokens(json.dumps(block.get("input", {})))
                elif hasattr(block, "text"):
                    tokens += count_tokens(block.text)
                elif hasattr(block, "input"):
                    tokens += count_tokens(json.dumps(block.input))

    if tools:
        for tool in tools:
            tokens += 50  # Per-tool overhead
            tokens += count_tokens(tool.get("name", ""))
            tokens += count_tokens(tool.get("description", ""))
            input_schema = tool.get("input_schema", {})
            if input_schema:
                tokens += count_tokens(json.dumps(input_schema))

    return tokens
