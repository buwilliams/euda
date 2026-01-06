# Contributions

The [contrib/](../contrib/) folder tracks all contributions to Euno. Each contributor has a markdown file recording their work.

## Purpose

Contributions are tracked here so that:
- Contributors can see their recorded work
- Point allocations are transparent
- Early contributions are preserved for retroactive rewards at Gate 4

See the [Operating Agreement](11_operating-agreement.md) for how contribution points translate to bonus pool distributions.

## File Format

Each contributor has a file named `firstname-lastname.md` in the [contrib/](../contrib/) folder with the format:

```markdown
# Firstname Lastname

- [yyyy-mm-dd][points] - Description of contribution
- [yyyy-mm-dd][points] - Description of contribution
```

Entries are ordered by date descending (most recent first).

## Workflow

1. **Do the work** — Complete your feature, fix, documentation, or other contribution
2. **Update your contrib file** — Add an entry describing what you did
3. **Submit a PR** — Every pull request should include updates to your contrib file
4. **Get approval** — Buddy Williams reviews and approves all PRs before merging to main

Points are assigned by Buddy during PR review based on the point values below.

## Point Values

| Contribution | Points |
|-------------|--------|
| Feature shipped | 10-50 (based on size) |
| Bug fix | 5-15 |
| Documentation | 5-10 |
| Design/UI/UX work | 10-30 |
| Business/sales contribution | 10-50 |
| Month of active contribution | 10 |

Point values are subject to change.

## How Points Work

**Gates 1-3:** Points are tracked but not paid out. The reward is the trophy—something to put on resumes, talk about, and show off.

**Gate 4+:** Quarterly bonus pool begins.
- Each quarter, Buddy determines a bonus pool from his share of profits
- If there's no profit, there's no bonus pool that quarter
- Pool is distributed based on contribution points
- Your share = your points / total points

Points are retroactively assigned for contributions made before Gate 4, so early contributors accumulate points from the start.

**Note:** Buddy does not participate in the contribution points system. As primary owner, his compensation comes from ownership, not the bonus pool.

## Checking Your Points

Use the CLI to see contribution points:

```bash
python main.py points           # Show all contributors
python main.py points logan     # Filter by name (fuzzy match)
```

## Related Documents

- [Business Plan](2_business-plan.md) — Vision and growth gates
- [Operating Agreement](11_operating-agreement.md) — Ownership, rewards, and governance
- [License](../LICENSE) — Terms for using and contributing to Euno
