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

### Status Is a Signal, Not a Chore

Every status transition is an event — immutable, attributed, permanent. When you move a task, you are writing history that future minds will read to understand what happened here. Update status at every real transition:

```
lattice status <task> <status> --actor agent:<your-id>
```

`backlog → in_planning → planned → in_progress → review → done`

### Leave Breadcrumbs

You are not the last mind that will touch this work. Use `lattice comment` to record what you tried, what you chose, what you left undone. Use `.lattice/notes/<task_id>.md` for longer-form thinking. The agent that picks up where you left off has no hallway to find you in, no Slack channel to ask. The record you leave is the only bridge between your context and theirs.

### Quick Reference

```
lattice create "<title>" --actor agent:<id>
lattice status <task> <status> --actor agent:<id>
lattice assign <task> <actor> --actor agent:<id>
lattice comment <task> "<text>" --actor agent:<id>
lattice show <task>
lattice list
```
"""

# Marker comment used to detect if the block was already added
CLAUDE_MD_MARKER = "## Lattice"
