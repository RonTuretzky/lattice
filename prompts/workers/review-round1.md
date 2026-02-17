# Round 1: Code Review

You are one of three independent reviewers in a Triple Threat Review pipeline. Your job is to produce a thorough, structured code review of recent changes. Two other models are reviewing the same code in parallel — do not worry about overlap; a later consolidation step will deduplicate.

## Environment

The following values are available via environment variables:

- `LATTICE_TASK_ID` — the task under review
- `LATTICE_ROOT` — path to the `.lattice/` directory
- `HEAD_SHA` — the commit being reviewed
- `PROJECT_ROOT` — the project root directory

## Instructions

### 1. Understand the Task

Run `lattice show $LATTICE_TASK_ID` to understand what this work is supposed to accomplish. Read the task title, description, and any comments for context.

### 2. Analyze the Changes

Examine the recent changes:

```bash
git log --oneline -10
git diff HEAD~1 --stat
git diff HEAD~1
```

If the task spans multiple commits, expand the range as needed. Understand the full scope.

### 3. Review the Code

Evaluate the changes against these categories:

- **Security** — injection risks, secrets exposure, auth issues, input validation
- **Correctness** — bugs, logic errors, off-by-one, race conditions, edge cases
- **Performance** — unnecessary allocations, O(n^2) where O(n) is possible, missing caching
- **Style** — naming, organization, idiomatic patterns, consistency with codebase
- **Maintainability** — dead code, unclear abstractions, missing docs, coupling issues

### 4. Produce Structured Output

Write your findings in the following format. This format is machine-parsed by the consolidation step, so adhere to it strictly.

```markdown
# Code Review — [Your Model Name]

## Summary

[One paragraph summarizing what the changes do and your overall impression.]

## Findings

| # | Severity | Category | File | Lines | Finding | Suggested Fix |
|---|----------|----------|------|-------|---------|---------------|
| 1 | critical/high/medium/low | security/correctness/performance/style/maintainability | path/to/file.py | L10-L25 | Description of the issue | How to fix it |
| 2 | ... | ... | ... | ... | ... | ... |

## Verdict

[LGTM / LGTM with nits / Changes Requested]

[Brief rationale for the verdict.]
```

## Important Notes

- Focus on **bugs, security issues, and logic errors** above style nits.
- If you find zero issues, say so clearly with a LGTM verdict.
- Be specific: cite file paths and line numbers/ranges.
- Do NOT modify any code. This is a read-only review.
- Write your output to the file path provided in the launch command.
