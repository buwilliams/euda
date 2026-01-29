"""Agent management commands for the core plugin."""

from typing import Optional
import typer

app = typer.Typer(no_args_is_help=True)


def _get_agents_module():
    """Lazy import of agents module."""
    from src.core.agents.agents import (
        list_agents, get_agent, create_agent,
        enable_agent, disable_agent, delete_agent,
        list_available_tools, pause_agent, resume_agent,
        get_agent_status, get_agent_triggers, trigger_agent,
        get_agent_token_usage, reset_agent_token_usage,
        get_agent_config
    )
    return {
        "list_agents": list_agents,
        "get_agent": get_agent,
        "create_agent": create_agent,
        "enable_agent": enable_agent,
        "disable_agent": disable_agent,
        "delete_agent": delete_agent,
        "list_available_tools": list_available_tools,
        "pause_agent": pause_agent,
        "resume_agent": resume_agent,
        "get_agent_status": get_agent_status,
        "get_agent_triggers": get_agent_triggers,
        "trigger_agent": trigger_agent,
        "get_agent_token_usage": get_agent_token_usage,
        "reset_agent_token_usage": reset_agent_token_usage,
        "get_agent_config": get_agent_config,
    }


@app.command("list")
def list_cmd():
    """List all configured agents."""
    m = _get_agents_module()
    agents = m["list_agents"]()

    if not agents:
        print("No agents configured.")
        return

    for agent in agents:
        agent_id = agent.get("id", "?")
        name = agent.get("name", agent_id)
        state = agent.get("state", "enabled")
        print(f"  {agent_id}: {name} [{state}]")


@app.command("show")
def show_cmd(agent_name: str = typer.Argument(..., help="Agent name")):
    """Show detailed information about an agent."""
    m = _get_agents_module()
    agent = m["get_agent"](agent_name)

    if not agent:
        print(f"Agent not found: {agent_name}")
        raise typer.Exit(1)

    config = agent.get("config", {})
    print(f"ID: {config.get('id', agent_name)}")
    print(f"Name: {config.get('name', agent_name)}")
    print(f"State: {config.get('state', 'enabled')}")
    print(f"Order: {config.get('order', '-')}")

    tools = config.get("tools", [])
    print(f"Tools: {len(tools)} configured")

    triggers = config.get("triggers", [])
    print(f"Triggers: {len(triggers)} configured")

    identity = agent.get("identity", "")
    if identity:
        # Show first paragraph of identity
        first_para = identity.split("\n\n")[0] if identity else ""
        print(f"\nIdentity excerpt:\n{first_para[:200]}...")


@app.command("create")
def create_cmd(
    agent_name: str = typer.Argument(..., help="Unique identifier (lowercase, no spaces)"),
    name: str = typer.Argument(..., help="Display name"),
    purpose: str = typer.Argument(..., help="Description of what the agent does"),
    tools: Optional[str] = typer.Option(None, "--tools", "-t", help="Comma-separated tool names"),
):
    """Create a new agent."""
    m = _get_agents_module()

    tool_list = [t.strip() for t in tools.split(",")] if tools else None

    result = m["create_agent"](
        agent_id=agent_name,
        name=name,
        purpose=purpose,
        tools=tool_list
    )

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Created agent: {agent_name}")
    print(f"Name: {name}")
    print(f"Started: {result.get('started', False)}")


@app.command("enable")
def enable_cmd(agent_name: str = typer.Argument(..., help="Agent name")):
    """Enable an agent so it can process topics."""
    m = _get_agents_module()
    result = m["enable_agent"](agent_name)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Enabled agent: {agent_name}")


@app.command("disable")
def disable_cmd(agent_name: str = typer.Argument(..., help="Agent name")):
    """Disable an agent so it stops processing topics."""
    m = _get_agents_module()
    result = m["disable_agent"](agent_name)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Disabled agent: {agent_name}")


@app.command("pause")
def pause_cmd(
    agent_name: str = typer.Argument(..., help="Agent name"),
    reason: Optional[str] = typer.Option(None, "--reason", "-r", help="Reason for pausing"),
):
    """Pause an agent temporarily.

    Unlike disable, a paused agent is still counted in budget calculations
    and can be auto-resumed when budget resets.
    """
    m = _get_agents_module()
    result = m["pause_agent"](agent_name, reason)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Paused agent: {agent_name}")
    if reason:
        print(f"Reason: {reason}")


@app.command("resume")
def resume_cmd(agent_name: str = typer.Argument(..., help="Agent name")):
    """Resume a paused agent."""
    m = _get_agents_module()
    result = m["resume_agent"](agent_name)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Resumed agent: {agent_name}")


@app.command("status")
def status_cmd(agent_name: str = typer.Argument(..., help="Agent name")):
    """Show detailed status for an agent including pause info and usage."""
    m = _get_agents_module()
    result = m["get_agent_status"](agent_name)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Agent: {result['name']} ({result['agent_id']})")
    print(f"State: {result['state']}")

    # Pause info
    pause_info = result.get("pause_info", {})
    if pause_info.get("is_paused"):
        print(f"Paused: Yes")
        print(f"  Reason: {pause_info.get('reason', 'unknown')}")
        print(f"  Since: {pause_info.get('timestamp', 'unknown')}")

    # Usage
    usage = result.get("usage", {})
    print(f"\nToken Usage ({usage.get('frequency', 'daily')}):")
    print(f"  Input: {usage.get('input_tokens', 0):,} ({usage.get('input_percent', 0):.1f}%)")
    print(f"  Output: {usage.get('output_tokens', 0):,} ({usage.get('output_percent', 0):.1f}%)")

    # Budget reset
    reset_info = result.get("budget_reset", {})
    print(f"  Resets in: {reset_info.get('time_until', 'unknown')}")


@app.command("triggers")
def triggers_cmd(agent_name: str = typer.Argument(..., help="Agent name")):
    """List triggers configured for an agent."""
    m = _get_agents_module()
    result = m["get_agent_triggers"](agent_name)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    triggers = result.get("triggers", [])
    if not triggers:
        print(f"No triggers configured for {agent_name}")
        return

    print(f"Triggers for {agent_name} ({result['count']}):\n")

    for t in triggers:
        event = t.get("event", "?")
        topic = t.get("topic_name", "?")
        action = t.get("action", "llm")

        print(f"  Event: {event}")
        print(f"    Topic: {topic}")
        print(f"    Action: {action}")
        if t.get("tool"):
            print(f"    Tool: {t['tool']}")
        if t.get("topic_description"):
            print(f"    Description: {t['topic_description'][:60]}...")

        # Show state for interval triggers
        if event.startswith("interval:"):
            last_ran = t.get("last_ran", "never")
            next_run = t.get("next_run", "pending")
            print(f"    Last ran: {last_ran}")
            print(f"    Next run: {next_run}")

        print()


@app.command("trigger")
def trigger_cmd(
    agent_name: str = typer.Argument(..., help="Agent name"),
    topic_name: str = typer.Argument(..., help="Topic name to create (e.g., euno:consolidate)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Topic description"),
):
    """Manually fire a trigger for an agent by creating a topic."""
    m = _get_agents_module()
    result = m["trigger_agent"](agent_name, topic_name, description)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Triggered: {topic_name}")
    print(f"Topic ID: {result['topic_id']}")


@app.command("usage")
def usage_cmd(agent_name: str = typer.Argument(..., help="Agent name")):
    """Show token usage statistics for an agent."""
    m = _get_agents_module()
    result = m["get_agent_token_usage"](agent_name)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Token Usage for {agent_name}")
    print(f"Period: {result.get('period', 'unknown')} ({result.get('frequency', 'daily')})")
    print()
    print(f"Input Tokens:  {result.get('input_tokens', 0):>10,} / {result.get('input_budget', 0):,} ({result.get('input_percent', 0):.1f}%)")
    print(f"Output Tokens: {result.get('output_tokens', 0):>10,} / {result.get('output_budget', 0):,} ({result.get('output_percent', 0):.1f}%)")
    print()
    print(f"Budget resets: {result.get('reset_time', 'unknown')}")
    print(f"Time until reset: {result.get('time_until_reset', 'unknown')}")


@app.command("reset-usage")
def reset_usage_cmd(agent_name: str = typer.Argument(..., help="Agent name")):
    """Reset token usage for an agent to zero.

    This also auto-resumes the agent if it was paused due to budget limits.
    """
    m = _get_agents_module()
    result = m["reset_agent_token_usage"](agent_name)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Reset token usage for: {agent_name}")


@app.command("config")
def config_cmd(agent_name: str = typer.Argument(..., help="Agent name")):
    """Show full configuration for an agent."""
    import json

    m = _get_agents_module()
    config = m["get_agent_config"](agent_name)

    if config is None:
        print(f"Agent not found: {agent_name}")
        raise typer.Exit(1)

    print(json.dumps(config, indent=2))


@app.command("delete")
def delete_cmd(agent_name: str = typer.Argument(..., help="Agent name")):
    """Permanently delete an agent."""
    m = _get_agents_module()
    result = m["delete_agent"](agent_name)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Deleted agent: {agent_name}")
    print("Note: Restart Euno to fully remove the agent")


@app.command("tools")
def tools_cmd():
    """List all available tools that can be assigned to agents."""
    m = _get_agents_module()
    tools = m["list_available_tools"]()

    print("Available tools (meta-tools for skill access):")
    for tool in tools:
        print(f"  {tool.get('name')}: {tool.get('description', '')[:60]}...")
