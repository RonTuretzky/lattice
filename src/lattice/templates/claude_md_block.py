"""CLAUDE.md integration template for Lattice.

This is the single source of truth for the Lattice agent integration block.
Edit this file to update what `lattice init` and `lattice setup-claude` write.
"""

CLAUDE_MD_BLOCK = """\

## Lattice

This project coordinates through Lattice — file-based, event-sourced task tracking built for minds that think in tokens and act in tool calls. The `.lattice/` directory is the coordination state. It lives here, alongside the code, not behind an API or inside someone else's database.

### The First Act

When work arrives — a plan, a feature request, a bug, a conversation that implies something needs building — your first action is to give it a name in Lattice. Before you plan. Before you implement. Before you touch a single file. The task must exist in the system before the work begins, because work that isn't tracked is work that other minds cannot see, cannot build on, cannot trust.

```
lattice create "<title>" --actor agent:<your-id>
```

This is not bookkeeping. This is the minimum viable act of coordination: declaring that something is happening, and who is doing it.

### Descriptions Carry Context

The description should be sufficient for an agent to decide whether it needs to plan. Plan files are where agents write *how* — descriptions say *what* and *why*.

- **Fully specified** (bug located, fix named, files identified): skip `in_planning`, go straight to `in_progress`. Mark `complexity: low`.
- **Clear goal, open implementation**: go through `in_planning`. The agent figures out the approach.
- **Decision context from conversations**: bake the decisions and rationale into the description. Without it, the next agent re-derives what was already decided.

### Status Is a Signal, Not a Chore

Every status transition is an event — immutable, attributed, permanent. When you move a task, you are writing history that future minds will read to understand what happened here.

**The cardinal rule: update status BEFORE you start the work, not after.** If you're about to plan a task, move it to `in_planning` first. If you're about to implement, move it to `in_progress` first. Lattice is the source of ground truth for what is happening right now. If the board says a task is in `backlog` but an agent is actively working on it, the board is lying — and every other mind reading it is making decisions on false information.

```
lattice status <task> <status> --actor agent:<your-id>
```

```
backlog → in_planning → planned → in_progress → review → done
                                       ↕            ↕
                                    blocked      needs_human
```

**Transition discipline:**
- Moving to `in_planning`? Do it before you open the first file to read. Then **write the plan** — see below.
- Moving to `planned`? Only after the plan file has real content.
- Moving to `in_progress`? Do it before you write the first line of code.
- Moving to `review`? Do it when implementation is complete, before review starts. Then **actually review** — see below.
- Moving to `done`? Only after a review has been performed and recorded.
- Spawning a sub-agent to work on a task? Update status in the parent context before the sub-agent launches.

### The Planning Gate

Moving a task to `in_planning` means you are about to produce a plan. The plan file lives at `.lattice/plans/<task_id>.md` — it's scaffolded on task creation, but the scaffold is empty. `in_planning` is when you fill it in.

**When you move a task to `in_planning`:**
1. Open the plan file (`.lattice/plans/<task_id>.md`).
2. Write the plan — scope, approach, key files, acceptance criteria. For trivial tasks, a single sentence is fine. For substantial work, be thorough.
3. Move to `planned` only when the plan file reflects what you intend to build.

**The test:** If you moved from `in_planning` to `planned` and the plan file is still empty scaffold, you didn't plan. Either write the plan or skip `in_planning` honestly with `--force --reason "trivial task, no planning needed"`.

### The Review Gate

Moving a task to `review` is not a formality — it is a commitment to actually review the work before it ships.

**When you move a task to `review`:**
1. Identify what changed — the commits, files modified, and scope of work under this task.
2. Perform a code review. For substantial work, use a review skill (`/exit-review`, `/code_review`). For trivial tasks, a focused self-review is sufficient — but it must be real, not ceremonial.
3. Record your findings with `lattice comment` — what you reviewed, what you found, whether it meets the acceptance criteria from the plan.

**When moving from `review` to `done`:**
- If the completion policy blocks you for a missing review artifact, **do the review**. Do not `--force` past it. The policy is correct — you haven't reviewed yet.
- `--force --reason` on the completion policy is for genuinely exceptional cases (task cancelled, review happened outside Lattice, process validation). It is not a convenience shortcut.

**The test:** If you moved to `review` and then to `done` in the same breath with nothing in between, you skipped the review. That's the exact failure mode this gate exists to prevent.

### When You're Stuck

If you hit a point where you need human decision, approval, or input — **signal it immediately** with `needs_human`. This is different from `blocked` (generic external dependency). `needs_human` creates a clear queue of "things waiting on the human."

```
lattice status <task> needs_human --actor agent:<your-id>
lattice comment <task> "Need: <what you need, in one line>" --actor agent:<your-id>
```

**When to use `needs_human`:**
- Design decisions that require human judgment
- Missing access, credentials, or permissions
- Ambiguous requirements that can't be resolved from context
- Approval needed before proceeding (deploy, merge, etc.)

The comment is mandatory — explain what you need in seconds, not minutes. The human's queue should be scannable.

### Actor Attribution

Every Lattice operation requires an `--actor`. Attribution follows authorship of the decision, not authorship of the keystroke.

| Situation | Actor | Why |
|-----------|-------|-----|
| Agent autonomously creates or modifies a task | `agent:<id>` | Agent was the decision-maker |
| Human creates via direct interaction (UI, manual CLI) | `human:<id>` | Human typed it |
| Human meaningfully shaped the outcome in conversation with an agent | `human:<id>` | Human authored the decision; agent was the instrument |
| Agent creates based on its own analysis, unprompted | `agent:<id>` | Agent authored the decision |

When in doubt, give the human credit. If the human was substantively involved in shaping *what* a task is — not just saying "go create tasks" but actually defining scope, debating structure, giving feedback — the human is the actor.

Users may have their own preferences about attribution. If a user seems frustrated or particular about actor assignments, ask them directly: "How do you want attribution to work? Should I default to crediting you, myself, or ask each time?" Respect whatever norm they set.

### Branch Linking

When you create a feature branch for a task, link it in Lattice so the association is tracked:

```
lattice branch-link <task> <branch-name> --actor agent:<your-id>
```

This creates an immutable event tying the branch to the task. `lattice show` will display it, and any mind reading the task knows which branch carries the work.

If the branch name contains the task's short code (e.g., `feat/LAT-42-login`), Lattice auto-detects the link — but explicit linking is always authoritative and preferred for cross-repo or non-standard branch names.

### Leave Breadcrumbs

You are not the last mind that will touch this work. Use `lattice comment` to record what you tried, what you chose, what you left undone. Use `.lattice/plans/<task_id>.md` for the structured plan (scope, steps, acceptance criteria) and `.lattice/notes/<task_id>.md` for working notes, debug logs, and context dumps. The agent that picks up where you left off has no hallway to find you in, no Slack channel to ask. The record you leave is the only bridge between your context and theirs.

### Quick Reference

```
lattice create "<title>" --actor agent:<id>
lattice status <task> <status> --actor agent:<id>
lattice assign <task> <actor> --actor agent:<id>
lattice comment <task> "<text>" --actor agent:<id>
lattice link <task> <type> <target> --actor agent:<id>
lattice branch-link <task> <branch> --actor agent:<id>
lattice next [--actor agent:<id>] [--claim]
lattice show <task>
lattice list
```

**Useful flags:**
- `--quiet` — prints only the task ID (essential for scripting: `TASK=$(lattice create "..." --quiet)`)
- `--json` — structured output: `{"ok": true, "data": ...}` or `{"ok": false, "error": ...}`
- `lattice list --status in_progress` — filter by status
- `lattice list --assigned agent:<id>` — filter by assignee
- `lattice list --tag <tag>` — filter by tag
- `lattice link <task> subtask_of|depends_on|blocks <target>` — express task relationships

For the full CLI reference (all commands, flags, error codes, and workflow examples), see the `/lattice` skill.
"""

# Marker comment used to detect if the block was already added
CLAUDE_MD_MARKER = "## Lattice"
