# Process Tasks Prompt

*Instructions for processing the task queue with delegation logic*

## Task

Check the task queue and process pending tasks using appropriate delegation.

## IMPORTANT: Do NOT Create Duplicate Tasks

**NEVER create new tasks that duplicate existing ones.** If a task already exists, update its status instead of creating a new task. Each task should only exist once in the queue.

## Delegation Strategy

For each pending task, check its delegation strategy:

### 1. Learning tasks (delegation.strategy = "prepare_materials")
- Research and curate learning materials
- Store result with prepared content
- Notify user that materials are ready
- Mark task as "materials_ready"

### 2. User-only tasks (delegation.strategy = "user_only")
- Cannot execute these (physical activity, creative work, personal decisions)
- **Do NOT create a new task.** Just update the existing task's status to "surfaced"
- The task will appear in the user's task list for them to complete

### 3. Tasks requiring approval (delegation.requires_approval = true)
- Create a pending action with clear summary (this auto-creates an approval task in From Euno)
- Update the ORIGINAL task status to "awaiting_approval"
- **Do NOT create another task** - the approval task is created automatically

### 4. Autonomous tasks (delegation.strategy = "agent_autonomous")
- Execute the task (research, fetch info, etc.)
- Store the result
- Mark task as "completed"

## Additional Checks

- Check for projects with upcoming deadlines and create relevant notifications
- If there are approved actions ready for execution, execute them

## Output

Report what you did and what decisions you made.
