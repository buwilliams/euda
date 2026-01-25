## Topic Assignment

- **ID**: {topic_id}
- **Name**: {topic_name}
- **Description**: {topic_description}
- **Due**: {topic_due_date}
- **Tags**: {topic_tags}
- **Context**: {topic_attachments}

{remaining_topics_notice}

## Execution Guidelines

- Focus on completing the assigned topic
- Use available tools to accomplish the work
- Create sub-topics for complex tasks that need breaking down
- Log progress with add_topic_log when completing significant steps
- Complete the topic with complete_topic(topic_id="{topic_id}") when work is done
- Call done_working() at the end of your work cycle

## Blocked Topics

If you cannot progress because you're waiting on something external:
1. Add a `waiting:reason` tag to the topic (e.g., `waiting:logan`, `waiting:user-input`, `waiting:external-api`)
2. Log why it's blocked: add_topic_log("{topic_id}", "Blocked: waiting for Logan's response with QA findings")
3. Then call done_working()

This removes the topic from your queue until the user interacts with it again.
Do NOT keep checking the same blocked topic repeatedly — mark it and move on.

## Special Case: User Request

When a topic has the `user:request` tag, someone specifically asked for your help:
1. Read the topic description to understand what's being asked
2. Do focused research on that specific topic
3. Write your findings as an asset: write_asset("{topic_id}", "findings.md", content)
4. Return the topic to user: handoff_topic("{topic_id}", "user", "Ready for your review")
5. Do NOT complete the topic — the user will review and complete it

## Topic Coordination

- To pass work to another agent: handoff_topic(topic_id, "agent_id", "what you need")
- To return to whoever sent it: handoff_topic(topic_id, pending_from, "findings/results")
- Only call complete_topic when the work is truly finished, not when handing off
