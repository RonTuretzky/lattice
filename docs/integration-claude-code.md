# Using Lattice with Claude Code

Lattice integrates with Claude Code through a block injected into your project's `CLAUDE.md` file. This block is what makes agents treat task tracking as a first-class obligation rather than an afterthought. Without it, agents can use Lattice if prompted; with it, they create tasks and update statuses as their default behavior.

## How the integration works

Claude Code loads `CLAUDE.md` at the start of every session. The Lattice integration block teaches agents four things:

1. **Work intake** -- create a task before doing any work. Before planning, before implementing, before touching a file.
2. **Status tracking** -- update status at every real transition. Statuses are events, not labels.
3. **Actor attribution** -- every operation requires an `--actor` identifying who made the decision.
4. **Breadcrumbs** -- use `lattice comment` and `.lattice/notes/<task_id>.md` to leave context for the next agent.

## Adding the integration block

### For new projects

`lattice init` creates the `.lattice/` directory and offers to add the integration block to `CLAUDE.md` automatically:

```bash
lattice init --path /your/project --actor human:yourname
```

If you skipped the CLAUDE.md step during init, run `setup-claude` afterward.

### For existing projects

```bash
lattice setup-claude --path /your/project
```

This appends the Lattice block to the end of your existing `CLAUDE.md`. If the file does not exist, it creates one.

### Updating an existing block

When the template is updated (new instructions, better wording, additional guidance), refresh your project's block:

```bash
lattice setup-claude --path /your/project --force
```

The `--force` flag removes the existing Lattice block and replaces it with the latest version from the template. Without `--force`, the command exits if it detects an existing block.

## What the block teaches agents

The integration block (sourced from `src/lattice/templates/claude_md_block.py`) includes these sections:

### The First Act

Instructs agents to create a Lattice task as their first action when any work arrives -- a feature request, a bug, a pivot in conversation. The task must exist before work begins.

```
lattice create "<title>" --actor agent:<your-id>
```

### Status Is a Signal

Teaches agents the workflow: `backlog -> in_planning -> planned -> in_progress -> review -> done`. Every transition is an immutable, attributed event. Agents learn to update status at every real transition point.

```
lattice status <task> <status> --actor agent:<your-id>
```

### Actor Attribution

Explains the attribution model. The actor is the mind that made the decision, not the tool that executed it:

| Situation | Actor |
|-----------|-------|
| Agent decides autonomously | `agent:<id>` |
| Human types the command | `human:<id>` |
| Human shaped the decision, agent executed | `human:<id>` |

### Leave Breadcrumbs

Agents are instructed to leave records for future agents via comments and notes files:

```
lattice comment <task> "<text>" --actor agent:<id>
```

## Best practices

### Keep the Lattice block near the top of CLAUDE.md

Instruction position affects agent compliance. The Lattice block should appear early in the file -- ideally as the first or second major section. Instructions at the bottom of long files lose influence as conversational momentum takes over.

### Do not hand-write the block

The canonical template lives in `src/lattice/templates/claude_md_block.py`. This is the single source of truth. Do not copy-paste from another project's CLAUDE.md or write your own version. Use `lattice setup-claude` to keep all projects on the same template.

### Verify after setup

After running `setup-claude`, confirm the block exists:

```bash
grep "## Lattice" CLAUDE.md
```

If you see `## Lattice` in the output, the integration is in place.

### Combine with the `/lattice` skill

The CLAUDE.md block teaches agents the core workflow. For deeper CLI knowledge (all commands, flags, error codes, advanced workflows), agents can load the `/lattice` skill, which provides the full command reference. The two are complementary:

- **CLAUDE.md block** -- always loaded, covers the essentials (create, status, attribution)
- **`/lattice` skill** -- loaded on demand, covers every command and flag in detail

## Troubleshooting

### Agent ignores Lattice and starts coding immediately

The CLAUDE.md block is missing or positioned too far down the file. Run:

```bash
lattice setup-claude --path . --force
```

Then move the `## Lattice` section higher in CLAUDE.md if other sections precede it.

### "Already has Lattice integration" but the block is outdated

The command detects the block by looking for the `## Lattice` marker. Use `--force` to replace it:

```bash
lattice setup-claude --path . --force
```

### Agent uses wrong status names

Historical documentation used statuses like `in_implementation` and `in_review`. The real statuses are: `backlog`, `in_planning`, `planned`, `in_progress`, `review`, `done`, `blocked`, `cancelled`. If an agent uses wrong names, update the CLAUDE.md block with `--force` to get the latest template.
