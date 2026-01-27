"""Agent management commands for the core plugin."""

from typing import Optional
import typer

app = typer.Typer(no_args_is_help=True)


def _get_agents_module():
    """Lazy import of agents module."""
    from src.core.agents.agents import (
        list_agents, get_agent, create_agent,
        enable_agent, disable_agent, delete_agent,
        list_available_tools
    )
    return {
        "list_agents": list_agents,
        "get_agent": get_agent,
        "create_agent": create_agent,
        "enable_agent": enable_agent,
        "disable_agent": disable_agent,
        "delete_agent": delete_agent,
        "list_available_tools": list_available_tools,
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
def show_cmd(agent_id: str = typer.Argument(..., help="Agent ID")):
    """Show detailed information about an agent."""
    m = _get_agents_module()
    agent = m["get_agent"](agent_id)

    if not agent:
        print(f"Agent not found: {agent_id}")
        raise typer.Exit(1)

    config = agent.get("config", {})
    print(f"ID: {config.get('id', agent_id)}")
    print(f"Name: {config.get('name', agent_id)}")
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
    agent_id: str = typer.Argument(..., help="Unique identifier (lowercase, no spaces)"),
    name: str = typer.Argument(..., help="Display name"),
    purpose: str = typer.Argument(..., help="Description of what the agent does"),
    tools: Optional[str] = typer.Option(None, "--tools", "-t", help="Comma-separated tool names"),
):
    """Create a new agent."""
    m = _get_agents_module()

    tool_list = [t.strip() for t in tools.split(",")] if tools else None

    result = m["create_agent"](
        agent_id=agent_id,
        name=name,
        purpose=purpose,
        tools=tool_list
    )

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Created agent: {agent_id}")
    print(f"Name: {name}")
    print(f"Started: {result.get('started', False)}")


@app.command("enable")
def enable_cmd(agent_id: str = typer.Argument(..., help="Agent ID")):
    """Enable an agent so it can process topics."""
    m = _get_agents_module()
    result = m["enable_agent"](agent_id)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Enabled agent: {agent_id}")


@app.command("disable")
def disable_cmd(agent_id: str = typer.Argument(..., help="Agent ID")):
    """Disable an agent so it stops processing topics."""
    m = _get_agents_module()
    result = m["disable_agent"](agent_id)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Disabled agent: {agent_id}")


@app.command("delete")
def delete_cmd(agent_id: str = typer.Argument(..., help="Agent ID")):
    """Permanently delete an agent."""
    m = _get_agents_module()
    result = m["delete_agent"](agent_id)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Deleted agent: {agent_id}")
    print("Note: Restart Euno to fully remove the agent")


@app.command("tools")
def tools_cmd():
    """List all available tools that can be assigned to agents."""
    m = _get_agents_module()
    tools = m["list_available_tools"]()

    print("Available tools:")
    for tool in tools:
        print(f"  {tool.get('name')}: {tool.get('description', '')[:60]}...")
