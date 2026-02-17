# CI Integration Patterns

Lattice is a CLI tool that reads and writes plain files. This makes CI integration straightforward: install Lattice in your pipeline, call the CLI, done. No API tokens, no webhooks, no external service to configure.

This guide covers two directions of integration:

1. **CI → Lattice** — CI pipelines update Lattice state (status changes, comments, metadata)
2. **Lattice → CI** — Lattice state informs CI behavior (conditional steps, gating)

## Prerequisites

Your CI environment needs:

- Python 3.12+
- The `lattice-tracker` package
- Access to the `.lattice/` directory (checked out with the repo, or initialized in CI)

### Installing Lattice in CI

```yaml
# GitHub Actions
- name: Install Lattice
  run: pip install lattice-tracker

# Or with uv (faster)
- name: Install Lattice
  run: uv pip install lattice-tracker --system
```

### The `.lattice/` directory in CI

Lattice stores state in `.lattice/` at the project root. If your project gitignores this directory (the default recommendation), CI pipelines won't have task state to read or write. You have two options:

1. **Commit `.lattice/` to the repo.** Remove it from `.gitignore`. Task state becomes versioned alongside code. Simple, but creates noise in diffs. Best for small projects where task state is lightweight.

2. **Initialize a fresh instance in CI.** Run `lattice init` in the pipeline. Useful when CI only needs to *write* events (e.g., posting comments) and a separate system aggregates them. Less common.

For most projects, option 1 is the practical choice. The event log files (JSONL) are append-only and merge cleanly.

## CI → Lattice: Updating task state from pipelines

The most common pattern: CI results flow back into Lattice as comments, status changes, or metadata.

### Actor convention for CI

Use a consistent actor format so CI-authored events are distinguishable:

```
agent:ci:github-actions
agent:ci:gitlab-ci
agent:ci:jenkins
agent:ci:buildkite
```

The `agent:ci:` prefix signals "this was an automated system, not a human or AI agent."

### Pattern 1: Comment test results on a task

Extract the task ID from the branch name or commit message, then post CI results as a comment.

```yaml
# .github/workflows/lattice-update.yml
name: Update Lattice on PR

on:
  pull_request:
    branches: [main]

jobs:
  update-lattice:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Lattice
        run: pip install lattice-tracker

      - name: Run tests
        id: tests
        run: |
          pytest -q 2>&1 | tee test-output.txt
          echo "exit_code=${PIPESTATUS[0]}" >> "$GITHUB_OUTPUT"
        continue-on-error: true

      - name: Extract task ID from branch
        id: task
        run: |
          # Branch naming convention: feat/LAT-42-description
          BRANCH="${{ github.head_ref }}"
          TASK_ID=$(echo "$BRANCH" | grep -oP 'LAT-\d+' | head -1)
          echo "id=$TASK_ID" >> "$GITHUB_OUTPUT"

      - name: Comment results on task
        if: steps.task.outputs.id != ''
        run: |
          RESULT=$([ "${{ steps.tests.outputs.exit_code }}" = "0" ] && echo "PASSED" || echo "FAILED")
          lattice comment "${{ steps.task.outputs.id }}" \
            "CI $RESULT on PR #${{ github.event.pull_request.number }} (commit ${{ github.sha | cut -c1-7 }})" \
            --actor agent:ci:github-actions
```

### Pattern 2: Move task to review when PR is opened

```yaml
- name: Move to review on PR open
  if: github.event.action == 'opened' && steps.task.outputs.id != ''
  run: |
    lattice status "${{ steps.task.outputs.id }}" review \
      --actor agent:ci:github-actions \
      --reason "PR #${{ github.event.pull_request.number }} opened"
```

### Pattern 3: Move task to done when PR merges

```yaml
name: Lattice on merge

on:
  pull_request:
    branches: [main]
    types: [closed]

jobs:
  close-task:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install Lattice
        run: pip install lattice-tracker

      - name: Extract task ID from branch
        id: task
        run: |
          BRANCH="${{ github.head_ref }}"
          TASK_ID=$(echo "$BRANCH" | grep -oP 'LAT-\d+' | head -1)
          echo "id=$TASK_ID" >> "$GITHUB_OUTPUT"

      - name: Mark task done
        if: steps.task.outputs.id != ''
        run: |
          lattice status "${{ steps.task.outputs.id }}" done \
            --actor agent:ci:github-actions \
            --reason "PR #${{ github.event.pull_request.number }} merged"
```

### Pattern 4: Attach build artifacts to a task

```yaml
- name: Attach coverage report
  if: steps.task.outputs.id != ''
  run: |
    lattice attach "${{ steps.task.outputs.id }}" coverage.xml \
      --actor agent:ci:github-actions \
      --title "Coverage report"
```

## Lattice → CI: Using task state to drive pipelines

The reverse direction: CI reads Lattice state to make decisions.

### Pattern 5: Gate deployment on task status

Only deploy when the associated task has reached `done`:

```yaml
- name: Check task status before deploy
  run: |
    STATUS=$(lattice show "$TASK_ID" --json | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['status'])")
    if [ "$STATUS" != "done" ]; then
      echo "::error::Task $TASK_ID is '$STATUS', not 'done'. Aborting deploy."
      exit 1
    fi
```

### Pattern 6: Skip CI for tasks still in planning

```yaml
- name: Check if task is implementation-ready
  id: check
  run: |
    STATUS=$(lattice show "$TASK_ID" --json | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['status'])")
    if [ "$STATUS" = "backlog" ] || [ "$STATUS" = "in_planning" ]; then
      echo "skip=true" >> "$GITHUB_OUTPUT"
    fi

- name: Run expensive tests
  if: steps.check.outputs.skip != 'true'
  run: pytest --slow
```

### Pattern 7: Generate a task summary for release notes

```yaml
- name: Generate release notes from done tasks
  run: |
    lattice list --status done --json | python3 -c "
    import sys, json
    data = json.load(sys.stdin)
    for task in data.get('data', []):
        print(f\"- {task['short_id']}: {task['title']}\")
    " > release-notes.txt
```

## Extracting task IDs

CI pipelines need to know which Lattice task a given branch or PR relates to. Common conventions:

### From branch names

Convention: `<type>/LAT-<number>-<description>`

```bash
# Examples: feat/LAT-42-add-auth, fix/LAT-99-null-check
TASK_ID=$(echo "$BRANCH" | grep -oP 'LAT-\d+' | head -1)
```

### From commit messages

Convention: include `LAT-<number>` anywhere in the commit message.

```bash
TASK_ID=$(git log -1 --format='%s' | grep -oP 'LAT-\d+' | head -1)
```

### From PR title or body

```bash
# GitHub Actions
TASK_ID=$(echo "${{ github.event.pull_request.title }}" | grep -oP 'LAT-\d+' | head -1)
```

### Fallback: no task ID found

When no task ID is extracted, CI should skip Lattice operations gracefully rather than failing:

```yaml
- name: Update Lattice
  if: steps.task.outputs.id != ''
  run: lattice comment "${{ steps.task.outputs.id }}" "..." --actor agent:ci:github-actions
```

## Handling workflow transition errors

Lattice enforces workflow transitions. A CI pipeline that tries to move a task from `backlog` directly to `done` will get an error. Two approaches:

### Strict: let it fail

If your pipeline assumes tasks follow the workflow, a transition error is a signal that something is wrong. Let it fail and investigate.

### Lenient: force with reason

If CI needs to set status regardless of current state, use `--force`:

```bash
lattice status "$TASK_ID" done \
  --force --reason "Auto-closed by CI on PR merge" \
  --actor agent:ci:github-actions
```

Use `--force` sparingly. Every forced transition is recorded in the event log with its reason, so abuse is visible.

## Generic CI (non-GitHub Actions)

The patterns above use GitHub Actions syntax, but the Lattice commands are the same everywhere. Adapt the YAML to your CI system:

### GitLab CI

```yaml
update-lattice:
  stage: post-test
  image: python:3.12-slim
  script:
    - pip install lattice-tracker
    - TASK_ID=$(echo "$CI_MERGE_REQUEST_SOURCE_BRANCH_NAME" | grep -oP 'LAT-\d+' | head -1)
    - |
      if [ -n "$TASK_ID" ]; then
        lattice comment "$TASK_ID" "Pipeline $CI_PIPELINE_STATUS for MR !$CI_MERGE_REQUEST_IID" \
          --actor agent:ci:gitlab-ci
      fi
  rules:
    - if: $CI_MERGE_REQUEST_IID
```

### Shell script (any CI)

```bash
#!/usr/bin/env bash
# lattice-ci-update.sh — generic CI integration
set -euo pipefail

TASK_ID=$(echo "${BRANCH_NAME:-}" | grep -oP 'LAT-\d+' | head -1 || true)
CI_ACTOR="agent:ci:${CI_SYSTEM:-unknown}"

if [ -z "$TASK_ID" ]; then
  echo "No Lattice task ID found in branch name. Skipping."
  exit 0
fi

case "${CI_EVENT:-}" in
  test_pass)
    lattice comment "$TASK_ID" "Tests passed ($BUILD_URL)" --actor "$CI_ACTOR"
    ;;
  test_fail)
    lattice comment "$TASK_ID" "Tests FAILED ($BUILD_URL)" --actor "$CI_ACTOR"
    ;;
  pr_merged)
    lattice status "$TASK_ID" done --actor "$CI_ACTOR" --reason "PR merged"
    ;;
esac
```

## Committing Lattice state from CI

If CI writes Lattice state (comments, status changes) and `.lattice/` is committed to the repo, the pipeline needs to commit those changes back:

```yaml
- name: Commit Lattice updates
  run: |
    git config user.name "lattice-ci"
    git config user.email "ci@example.com"
    git add .lattice/
    git diff --staged --quiet || git commit -m "chore: update Lattice state from CI"
    git push
```

This creates a potential loop (CI commit triggers CI). Prevent it with:

```yaml
on:
  push:
    branches: [main]
    paths-ignore:
      - '.lattice/**'
```

Or use `[skip ci]` in the commit message.

## JSON mode for structured output

All Lattice commands support `--json` for machine-readable output. CI scripts should prefer this over parsing human-readable text:

```bash
# Get task status programmatically
lattice show LAT-42 --json | python3 -c "
import sys, json
task = json.load(sys.stdin)['data']
print(f\"Status: {task['status']}\")
print(f\"Assigned: {task.get('assigned_to', 'unassigned')}\")
"

# List tasks as structured data
lattice list --status in_progress --json | python3 -c "
import sys, json
tasks = json.load(sys.stdin)['data']
print(f'{len(tasks)} tasks in progress')
"
```

## Summary

| Direction | What | How |
|-----------|------|-----|
| CI → Lattice | Post test results | `lattice comment <ID> "..." --actor agent:ci:*` |
| CI → Lattice | Move status on PR events | `lattice status <ID> <status> --actor agent:ci:*` |
| CI → Lattice | Attach artifacts | `lattice attach <ID> <file> --actor agent:ci:*` |
| Lattice → CI | Gate on task status | `lattice show <ID> --json` + conditional logic |
| Lattice → CI | Generate release notes | `lattice list --status done --json` |
| Either | Extract task ID | Parse `LAT-\d+` from branch name, commit, or PR title |
| Either | Actor convention | `agent:ci:<system-name>` |
