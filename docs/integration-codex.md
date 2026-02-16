# Using Lattice with Codex CLI

Codex CLI (OpenAI's terminal agent) can work with Lattice through shared command prompts and direct CLI invocation. Since Codex reads files and runs shell commands, the same `.lattice/` directory that works for Claude Code works for Codex -- no special integration needed.

## Shared commands via hardlinks

Claude Code and Codex CLI both support slash commands loaded from markdown files:

| Tool | Command directory |
|------|-------------------|
| Claude Code | `~/.claude/commands/*.md` |
| Codex CLI | `~/.codex/prompts/*.md` |

Since both use the same file format, you can hardlink them so a single file serves both tools. Edit one, both update.

### The sync script

The sync script creates hardlinks from Claude commands to Codex prompts:

```bash
~/.claude/scripts/sync-commands-to-codex.sh
```

Run it after adding or modifying any command file:

```bash
# After creating a new command
~/.claude/scripts/sync-commands-to-codex.sh
# Output: Synced 1 of 12 commands:
#   -> lattice.md
```

The script is idempotent -- it skips files that are already hardlinked (same inode) and only creates links for new or changed files.

### What gets synced

The `/lattice` command (`~/.claude/commands/lattice.md`) provides the full Lattice CLI reference -- all commands, flags, workflows, error codes, and best practices. After syncing, Codex agents can access this same reference.

## Codex workflow with Lattice

Codex operates by reading files and running shell commands. Lattice's CLI-first design means Codex can interact with it the same way a human would.

### Reading task state

Codex can read Lattice state through the CLI or by reading files directly:

```bash
# List tasks via CLI
lattice list --json

# Read a specific task snapshot directly
cat .lattice/tasks/task_01HQEXAMPLE.json

# Read task notes
cat .lattice/notes/task_01HQEXAMPLE.md

# Check what's in progress
lattice list --status in_progress --json
```

### Updating status

```bash
# Move a task to in_progress
lattice status LAT-15 in_progress --actor agent:codex

# Leave a comment about what you're doing
lattice comment LAT-15 "Starting implementation of the auth refactor" --actor agent:codex
```

### Creating tasks

```bash
# Create and capture the ID
TASK_ID=$(lattice create "Refactor auth module" --actor agent:codex --quiet)

# Assign to self
lattice assign $TASK_ID agent:codex --actor agent:codex
```

### A typical Codex session with Lattice

```bash
# 1. Check assigned work
lattice list --assigned agent:codex --json

# 2. Pick a task and start it
lattice status LAT-22 in_progress --actor agent:codex

# 3. Read the task details and notes
lattice show LAT-22
cat .lattice/notes/task_01HQEXAMPLE.md

# 4. Do the work (Codex edits files, runs tests, etc.)
# ...

# 5. Leave breadcrumbs
lattice comment LAT-22 "Refactored auth module. Added retry logic for token refresh. All tests passing." --actor agent:codex

# 6. Move to review
lattice status LAT-22 review --actor agent:codex
```

## Prompting Codex to use Lattice

Since Codex does not load `CLAUDE.md` the way Claude Code does, you need to include Lattice instructions in your Codex prompts. Two approaches:

### Approach 1: Reference the task in the prompt

```bash
codex exec --full-auto "Read .lattice/tasks/ to find task LAT-22. Read its notes file. Implement the task, then update its status to review. Use --actor agent:codex for all lattice commands."
```

### Approach 2: Write a prompt file

```bash
cat <<'EOF' > /tmp/codex-task.md
# Task: LAT-22

Read the task details:
```
lattice show LAT-22
```

Read the notes file for implementation plan:
```
cat .lattice/notes/task_01HQEXAMPLE.md
```

Implement the changes described in the task. When done:

1. Run all tests to verify
2. Comment on the task with what you changed: `lattice comment LAT-22 "..." --actor agent:codex`
3. Move to review: `lattice status LAT-22 review --actor agent:codex`
EOF

codex exec --full-auto --skip-git-repo-check "Read /tmp/codex-task.md and follow the instructions."
```

### Approach 3: Use the synced `/lattice` prompt

After syncing commands, Codex can load the full Lattice reference:

```bash
codex exec --full-auto "Read ~/.codex/prompts/lattice.md for the Lattice CLI reference. Then check lattice list for tasks assigned to agent:codex and work through them."
```

## Actor conventions for Codex

Use `agent:codex` as the actor identity when Codex operates autonomously:

```bash
lattice status LAT-15 in_progress --actor agent:codex
lattice comment LAT-15 "Starting work" --actor agent:codex
```

If Codex is acting on behalf of a human who directed the work, use the human's actor:

```bash
lattice create "Task the human described" --actor human:atin
```

The attribution rules are the same as for Claude Code -- the actor is the mind that made the decision, not the tool that typed the command.

## Limitations

- **No CLAUDE.md auto-loading.** Codex does not read CLAUDE.md by default, so the work intake obligation must be included in prompts explicitly.
- **No MCP support.** Codex does not support MCP, so it must use the CLI for all Lattice operations.
- **Stdin limitations.** Codex ignores stdin, so you cannot pipe content to it. Use file references instead (write prompt to a file, tell Codex to read it).
