# Contribution Points

The points system tracks and rewards contributions to Euno. Each contributor has a markdown file in [contrib/](../contrib/) recording their work.

## Purpose

- Contributors can see their recorded work
- Point allocations are transparent
- Early contributions are preserved for retroactive rewards at Gate 4

See the [Operating Agreement](6_operating-agreement.md) for how contribution points translate to bonus pool distributions.

## File Format

Each contributor has a file named `firstname-lastname.md` in [contrib/](../contrib/):

```markdown
# Firstname Lastname

- [yyyy-mm-dd][points] - Description of contribution
- [yyyy-mm-dd][points] - Description of contribution
```

Entries are ordered by date descending (most recent first).

## Point Values

| Contribution | Points |
|-------------|--------|
| Feature shipped | 10-50 (based on size) |
| Bug fix | 5-15 |
| Documentation | 5-10 |
| Design/UI/UX work | 10-30 |
| Business/sales contribution | 10-50 |
| Month of active contribution | 10 |

Point values are subject to change. Points are assigned by repository administrators during PR review.

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

```bash
python main.py points           # Show all contributors
python main.py points logan     # Filter by name (fuzzy match)
```

## Related Documents

- [Contributing Guide](4_contribute.md) — How to contribute
- [Business Plan](2_business-plan.md) — Vision and growth gates
- [Operating Agreement](6_operating-agreement.md) — Ownership, rewards, and governance
