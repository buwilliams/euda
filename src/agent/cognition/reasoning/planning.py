"""
Strategic Planning - Think before acting for complex operations.

Provides a planning phase for complex operations like consolidation
where thinking through the approach first leads to better outcomes.
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ...agent import Agent


PLANNING_SYSTEM_PROMPT = """You are planning your approach to a task. Think through:
1. What is the goal?
2. What information do you need?
3. What tools will be most useful?
4. What's the best sequence of steps?

Be concise but thorough. Your plan will guide your execution."""

PLANNING_USER_PROMPT = """## Task
{task_description}

## Available Tools
{available_tools}

## Instructions
Create a brief plan for approaching this task. Consider:
- What key information do you need to gather first?
- What tools will you use and in what order?
- What are the main steps to complete this task?

Keep your plan focused and actionable (3-5 key steps max)."""


class Planner:
    """Strategic planning capability for agents.

    Adds a planning phase before complex operations where thinking
    through the approach leads to better outcomes.
    """

    def __init__(self, agent: "Agent"):
        """Initialize planner for an agent.

        Args:
            agent: The agent this planner belongs to
        """
        self.agent = agent

    def should_plan(self, topic: dict) -> bool:
        """Check if this topic type requires planning.

        Args:
            topic: The topic dict to check

        Returns:
            True if planning should be done for this topic
        """
        # Delegate to metacognition config
        return self.agent.metacognition.should_plan(topic)

    def create_plan(self, topic: dict) -> Optional[str]:
        """Generate a plan for the topic.

        Args:
            topic: The topic to plan for

        Returns:
            Plan string, or None if planning fails
        """
        from ....llms import get_client

        # Build task description from topic
        task_description = self._format_task_description(topic)

        # Get available tools
        available_tools = self._format_available_tools()

        # Build planning prompt
        user_prompt = PLANNING_USER_PROMPT.format(
            task_description=task_description,
            available_tools=available_tools
        )

        self.agent._log("planning_start", {"topic_id": topic.get("id")})

        try:
            client = get_client()
            response = client.create(
                max_tokens=500,
                system=PLANNING_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
                agent_id=f"{self.agent.id}/planning",
                topic_id=topic.get("id")
            )

            # Extract text response
            plan = ""
            for block in response.content:
                if hasattr(block, "text"):
                    plan += block.text

            self.agent._log("planning_complete", {
                "topic_id": topic.get("id"),
                "plan_length": len(plan)
            })

            return plan.strip()

        except Exception as e:
            self.agent._log("planning_error", {
                "topic_id": topic.get("id"),
                "error": str(e)
            })
            return None

    def inject_plan(self, prompt: str, plan: str) -> str:
        """Inject plan into the working prompt.

        Args:
            prompt: The original prompt
            plan: The generated plan

        Returns:
            Modified prompt with plan context
        """
        plan_section = f"""
## Your Approach (planned)

{plan}

---

"""
        # Insert plan at the beginning of the prompt
        return plan_section + prompt

    def _format_task_description(self, topic: dict) -> str:
        """Format topic details for planning prompt."""
        parts = []

        name = topic.get("name", "Untitled")
        parts.append(f"**Task:** {name}")

        description = topic.get("description")
        if description:
            parts.append(f"**Details:** {description}")

        tags = topic.get("tags", [])
        if tags:
            parts.append(f"**Tags:** {', '.join(tags)}")

        return "\n".join(parts)

    def _format_available_tools(self) -> str:
        """Format list of available tools for planning prompt."""
        tools = self.agent._get_tools()
        if not tools:
            return "(no tools available)"

        # _get_tools() returns list of tool definitions with name/description
        lines = []
        for tool in tools[:15]:  # Limit to avoid overwhelming
            name = tool.get("name", "unknown")
            desc = tool.get("description", "")
            # Truncate long descriptions
            if len(desc) > 100:
                desc = desc[:100] + "..."
            lines.append(f"- **{name}**: {desc}")

        if len(tools) > 15:
            lines.append(f"- ... and {len(tools) - 15} more tools")

        return "\n".join(lines)
