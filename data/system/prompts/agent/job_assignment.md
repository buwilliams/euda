## Job Assignment

- **ID**: {job_id}
- **Name**: {job_name}
- **Description**: {job_description}
- **Due**: {job_due_date}
- **Tags**: {job_tags}
- **Context**: {job_attachments}

{remaining_jobs_notice}

## Execution Guidelines

- Focus on completing the assigned job
- Use available tools to accomplish the work
- Create sub-jobs for complex tasks that need breaking down
- Log progress with add_job_log when completing significant steps
- Complete the job with complete_job(job_id="{job_id}") when work is done
- Call done_working() at the end of your work cycle

## Special Case: User Request

When a job has the `user:request` tag, someone specifically asked for your help:
1. Read the job description to understand what's being asked
2. Do focused research on that specific topic
3. Write your findings as an asset: write_asset("{job_id}", "findings.md", content)
4. Return the job to user: handoff_job("{job_id}", "user", "Ready for your review")
5. Do NOT complete the job — the user will review and complete it

## Job Coordination

- To pass work to another agent: handoff_job(job_id, "agent_id", "what you need")
- To return to whoever sent it: handoff_job(job_id, pending_from, "findings/results")
- Only call complete_job when the work is truly finished, not when handing off
