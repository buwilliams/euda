import json
import sys
import uuid
from typing import Any, Dict, List, Optional

import shared_router

from src.config import load_config
from src.tools import TOOLS, dispatch_tool, tools_for_openai


def run_agent(
    agent: Dict[str, Any],
    provider_override: Optional[str] = None,
    model_override: Optional[str] = None,
) -> None:
    # --- Load configs ---
    agents_config, _ = load_config()
    runner_cfg = agents_config.get("runner", {})
    max_tokens = runner_cfg.get("max_tokens", 4096)
    max_tool_rounds = runner_cfg.get("max_tool_rounds", 20)
    command_timeout = runner_cfg.get("command_timeout", 30)

    try:
        llm_result = shared_router.run_core("llm", ["config", "cat-full"])
    except Exception as exc:
        print(f"Error: could not load LLM config: {exc}", file=sys.stderr)
        sys.exit(1)
    llm_config = json.loads(llm_result.stdout)

    provider = provider_override or llm_config.get("provider", "anthropic")
    model = model_override or llm_config.get("model", "")
    api_key = llm_config.get("api_keys", {}).get(provider, "")
    provider_cfg = llm_config.get("providers", {}).get(provider, {})

    if not api_key:
        print(f"Error: no API key configured for provider '{provider}'.", file=sys.stderr)
        sys.exit(1)
    if not model:
        print("Error: no model configured.", file=sys.stderr)
        sys.exit(1)

    # --- Load identity as system prompt ---
    identity_name = agent.get("identity", "")
    if not identity_name:
        print("Error: agent has no identity linked.", file=sys.stderr)
        sys.exit(1)

    try:
        id_result = shared_router.run_core("identity", ["id", "read", identity_name])
        system_prompt = id_result.stdout.strip()
    except Exception as exc:
        print(f"Error: could not load identity '{identity_name}': {exc}", file=sys.stderr)
        sys.exit(1)

    if not system_prompt:
        print(f"Error: identity '{identity_name}' is empty.", file=sys.stderr)
        sys.exit(1)

    # --- Session setup ---
    session_id = str(uuid.uuid4())
    messages: List[Dict[str, Any]] = []
    agent_name = agent["name"]
    turn_number = 0

    print(f"Agent: {agent_name} | Provider: {provider} | Model: {model}")
    print("Type 'exit' or 'quit' to end the session.\n")

    # --- Conversation loop ---
    try:
        while True:
            try:
                user_input = input("> ")
            except EOFError:
                print()
                break

            stripped = user_input.strip()
            if stripped.lower() in ("exit", "quit"):
                break
            if not stripped:
                continue

            messages.append({"role": "user", "content": stripped})
            turn_number += 1
            tool_calls_log: List[Dict[str, Any]] = []
            tool_round = 0

            # --- Inner tool loop ---
            while True:
                try:
                    assistant_msg = _call_llm(
                        provider=provider,
                        model=model,
                        api_key=api_key,
                        provider_cfg=provider_cfg,
                        system=system_prompt,
                        messages=messages,
                        max_tokens=max_tokens,
                    )
                except Exception as exc:
                    print(f"\n[LLM error: {exc}]\n")
                    if messages and messages[-1]["role"] == "user":
                        messages.pop()
                    break

                messages.append(assistant_msg)

                # Extract text and tool_use blocks
                text_parts, tool_uses = _parse_assistant(assistant_msg)

                if text_parts:
                    print(f"\n{text_parts}\n")

                if not tool_uses:
                    break

                tool_round += 1
                if tool_round > max_tool_rounds:
                    print(f"\n[Reached max tool rounds ({max_tool_rounds}). Stopping.]\n")
                    break

                tool_results = []
                for tu in tool_uses:
                    tool_name = tu["name"]
                    tool_input = tu["input"]
                    tool_id = tu["id"]
                    print(f"[calling {tool_name}...]")
                    result_text = dispatch_tool(tool_name, tool_input, timeout=command_timeout)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result_text,
                    })
                    tool_calls_log.append({
                        "name": tool_name,
                        "input": tool_input,
                        "output": result_text,
                    })

                messages.append({"role": "user", "content": tool_results})

            # --- Log turn to memory ---
            _log_turn(
                session_id=session_id,
                agent_name=agent_name,
                turn=turn_number,
                user_text=stripped,
                assistant_msg=messages[-1] if messages else {},
                tool_calls=tool_calls_log,
            )

    except KeyboardInterrupt:
        print("\n")

    print("Session ended.")


def _call_llm(
    provider: str,
    model: str,
    api_key: str,
    provider_cfg: Dict[str, Any],
    system: str,
    messages: List[Dict[str, Any]],
    max_tokens: int,
) -> Dict[str, Any]:
    if provider == "anthropic":
        return _call_anthropic(api_key, provider_cfg, model, system, messages, max_tokens)
    else:
        return _call_openai(api_key, provider_cfg, model, system, messages, max_tokens, provider)


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

def _call_anthropic(
    api_key: str,
    provider_cfg: Dict[str, Any],
    model: str,
    system: str,
    messages: List[Dict[str, Any]],
    max_tokens: int,
) -> Dict[str, Any]:
    import anthropic

    client = anthropic.Anthropic(
        api_key=api_key,
        base_url=provider_cfg.get("base_url"),
    )

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
        tools=TOOLS,
    )

    # Convert response to internal format
    content: List[Dict[str, Any]] = []
    for block in response.content:
        if block.type == "text":
            content.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            content.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })

    return {"role": "assistant", "content": content}


# ---------------------------------------------------------------------------
# OpenAI-compatible (OpenAI, xAI)
# ---------------------------------------------------------------------------

def _call_openai(
    api_key: str,
    provider_cfg: Dict[str, Any],
    model: str,
    system: str,
    messages: List[Dict[str, Any]],
    max_tokens: int,
    provider: str,
) -> Dict[str, Any]:
    import openai

    base_url = provider_cfg.get("base_url")
    client = openai.OpenAI(api_key=api_key, base_url=base_url)

    oai_messages = _to_openai_messages(system, messages)

    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=oai_messages,
        tools=tools_for_openai(),
    )

    return _from_openai_response(response)


def _to_openai_messages(
    system: str, messages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    oai: List[Dict[str, Any]] = [{"role": "system", "content": system}]

    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        if role == "assistant":
            oai.append(_assistant_to_openai(msg))
        elif role == "user" and isinstance(content, list):
            # Tool results
            for block in content:
                if block.get("type") == "tool_result":
                    oai.append({
                        "role": "tool",
                        "tool_call_id": block["tool_use_id"],
                        "content": block.get("content", ""),
                    })
        else:
            oai.append({"role": "user", "content": content})

    return oai


def _assistant_to_openai(msg: Dict[str, Any]) -> Dict[str, Any]:
    content = msg["content"]
    if isinstance(content, str):
        return {"role": "assistant", "content": content}

    text_parts = []
    tool_calls = []
    for block in content:
        if block.get("type") == "text":
            text_parts.append(block["text"])
        elif block.get("type") == "tool_use":
            tool_calls.append({
                "id": block["id"],
                "type": "function",
                "function": {
                    "name": block["name"],
                    "arguments": json.dumps(block["input"]),
                },
            })

    result: Dict[str, Any] = {"role": "assistant"}
    result["content"] = "\n".join(text_parts) if text_parts else None
    if tool_calls:
        result["tool_calls"] = tool_calls
    return result


def _from_openai_response(response: Any) -> Dict[str, Any]:
    choice = response.choices[0]
    message = choice.message
    content: List[Dict[str, Any]] = []

    if message.content:
        content.append({"type": "text", "text": message.content})

    if message.tool_calls:
        for tc in message.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            content.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.function.name,
                "input": args,
            })

    return {"role": "assistant", "content": content}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_assistant(msg: Dict[str, Any]) -> tuple:
    content = msg.get("content", [])
    if isinstance(content, str):
        return content, []

    text_parts = []
    tool_uses = []
    for block in content:
        if block.get("type") == "text" and block.get("text", "").strip():
            text_parts.append(block["text"])
        elif block.get("type") == "tool_use":
            tool_uses.append(block)

    return "\n".join(text_parts), tool_uses


def _log_turn(
    session_id: str,
    agent_name: str,
    turn: int,
    user_text: str,
    assistant_msg: Dict[str, Any],
    tool_calls: List[Dict[str, Any]],
) -> None:
    # Extract assistant text for logging
    assistant_text = ""
    content = assistant_msg.get("content", [])
    if isinstance(content, str):
        assistant_text = content
    elif isinstance(content, list):
        parts = [b.get("text", "") for b in content if b.get("type") == "text"]
        assistant_text = "\n".join(parts)

    entry = {
        "session_id": session_id,
        "agent": agent_name,
        "turn": turn,
        "user": user_text,
        "assistant": assistant_text,
        "tool_calls": tool_calls,
    }

    try:
        shared_router.run_core(
            "memory",
            ["write", json.dumps(entry), "--term", "short", "--type", "agent", "--id", agent_name],
            timeout=10.0,
        )
    except Exception:
        pass
