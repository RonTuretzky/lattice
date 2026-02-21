#!/usr/bin/env bash
# Lattice Runner: Autonomous orchestrator that spawns fresh agents
# to work through all claimable Lattice tasks until none remain.
#
# Usage: ./scripts/lattice-runner.sh [--dry-run] [--max-parallel N]
#
# Design:
#   - Shell script (no context window to exhaust)
#   - Spawns a fresh "clear claude" agent per task
#   - 3 attempts per task before marking blocked
#   - Logs everything to .lattice/runner.log
#   - Runs until no claimable tasks remain

set -euo pipefail

PROJECT_DIR="/Users/atin/Projects/Stage11/PROJECTS/Lattice"
cd "$PROJECT_DIR"

LOG_FILE=".lattice/runner.log"
ATTEMPT_DIR=".lattice/runner-attempts"
MAX_ATTEMPTS=3
ACTOR="agent:lattice-runner"
DRY_RUN=false
SLEEP_BETWEEN=5  # seconds between task spawns

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

mkdir -p "$ATTEMPT_DIR"

log() {
    local msg="[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"
    echo "$msg" | tee -a "$LOG_FILE"
}

get_attempts() {
    local task_id="$1"
    local file="$ATTEMPT_DIR/$task_id"
    if [[ -f "$file" ]]; then
        cat "$file"
    else
        echo "0"
    fi
}

increment_attempts() {
    local task_id="$1"
    local file="$ATTEMPT_DIR/$task_id"
    local current
    current=$(get_attempts "$task_id")
    echo $((current + 1)) > "$file"
}

get_next_task() {
    # Get the next claimable task (planned or backlog, unassigned)
    local result
    result=$(uv run lattice next --actor "$ACTOR" --json 2>/dev/null) || true
    
    if echo "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('ok') and d.get('data') else 1)" 2>/dev/null; then
        echo "$result"
    else
        echo ""
    fi
}

get_task_status() {
    local short_id="$1"
    uv run lattice show "$short_id" --json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data']['status'])" 2>/dev/null || echo "unknown"
}

count_remaining() {
    # Count tasks in active statuses. lattice list --status takes a single value,
    # so we query each status separately and sum.
    local total=0
    for s in backlog planned in_progress in_planning; do
        local c
        c=$(uv run lattice list --status "$s" --json 2>/dev/null | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('data',[])))" 2>/dev/null) || c=0
        total=$((total + c))
    done
    echo "$total"
}

run_agent_on_task() {
    local task_json="$1"
    local short_id task_id title
    
    short_id=$(echo "$task_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data']['short_id'])")
    task_id=$(echo "$task_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data']['id'])")
    title=$(echo "$task_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data']['title'])")
    
    if $DRY_RUN; then
        log "DRY-RUN: Would spawn agent for $short_id — $title"
        # Track seen tasks so dry-run doesn't loop forever on the same task
        if [[ -f "$ATTEMPT_DIR/dryrun-seen" ]] && grep -q "$task_id" "$ATTEMPT_DIR/dryrun-seen"; then
            log "DRY-RUN: Already seen $short_id, stopping dry-run"
            return 2  # signal to break
        fi
        mkdir -p "$ATTEMPT_DIR"
        echo "$task_id" >> "$ATTEMPT_DIR/dryrun-seen"
        return 0
    fi

    local attempts
    attempts=$(get_attempts "$task_id")

    if [[ "$attempts" -ge "$MAX_ATTEMPTS" ]]; then
        log "SKIP $short_id: max attempts ($MAX_ATTEMPTS) reached, marking blocked"
        uv run lattice status "$short_id" blocked --actor "$ACTOR" --reason "Failed after $MAX_ATTEMPTS attempts" 2>/dev/null || true
        uv run lattice comment "$short_id" "Lattice Runner: Marking blocked after $MAX_ATTEMPTS failed attempts." --actor "$ACTOR" 2>/dev/null || true
        return 1
    fi

    increment_attempts "$task_id"
    local attempt_num
    attempt_num=$(get_attempts "$task_id")

    log "START $short_id (attempt $attempt_num/$MAX_ATTEMPTS): $title"
    
    # Build the agent prompt
    local plan_file=".lattice/plans/${task_id}.md"
    local plan_content=""
    if [[ -f "$plan_file" ]]; then
        plan_content=$(cat "$plan_file")
    fi
    
    # Write the prompt to a temp file to avoid shell escaping issues
    local prompt_file="/tmp/lattice-runner-prompt-${short_id}.md"
    cat > "$prompt_file" << PROMPT
You are an autonomous agent working on the Lattice project at $PROJECT_DIR.

## Your Task

Task: $short_id - $title

## Plan

$plan_content

## Instructions

1. The task has already been claimed for you. Read the plan above carefully.
2. Do the work described in the plan. Make the code changes needed.
3. Git commit your changes with a good commit message.
4. Leave a comment on the task summarizing what you did:
   uv run lattice comment "$short_id" "your summary here" --actor "$ACTOR"
5. Complete the task:
   uv run lattice complete "$short_id" --review "Brief review of what was done" --actor "$ACTOR"

## Important
- Work in $PROJECT_DIR
- Use uv run lattice for all lattice commands  
- If you hit a genuine blocker, run: uv run lattice status "$short_id" blocked --actor "$ACTOR" --reason "description of blocker"
- Do NOT push to remote. Only commit locally.
- Be concise and focused. Do the work and finish.
PROMPT

    # Claim the task first
    log "CLAIM $short_id"
    local claim_result
    claim_result=$(uv run lattice next --claim --actor "$ACTOR" --json 2>/dev/null) || true
    
    if ! echo "$claim_result" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('ok') else 1)" 2>/dev/null; then
        log "CLAIM-FAILED $short_id: could not claim task"
        return 1
    fi
    
    # Spawn the agent
    log "SPAWN agent for $short_id"
    local agent_output
    agent_output=$(CLAUDECODE= claude -p "Read $prompt_file and follow the instructions exactly." --dangerously-skip-permissions 2>&1) || true
    
    # Check result
    local final_status
    final_status=$(get_task_status "$short_id")
    
    if [[ "$final_status" == "done" ]]; then
        log "DONE $short_id: completed successfully"
        rm -f "$prompt_file"
        return 0
    elif [[ "$final_status" == "blocked" ]]; then
        log "BLOCKED $short_id: agent marked as blocked"
        rm -f "$prompt_file"
        return 1
    else
        log "INCOMPLETE $short_id: status=$final_status after agent run (attempt $attempt_num)"
        # Reset to planned so it can be retried
        uv run lattice status "$short_id" planned --actor "$ACTOR" --force --reason "Resetting for retry (attempt $attempt_num failed)" 2>/dev/null || true
        uv run lattice assign "$short_id" none --actor "$ACTOR" 2>/dev/null || true
        rm -f "$prompt_file"
        return 1
    fi
}

# ─── Main Loop ───

log "=========================================="
log "Lattice Runner starting"
log "Project: $PROJECT_DIR"
log "Max attempts per task: $MAX_ATTEMPTS"
log "Dry run: $DRY_RUN"
log "=========================================="

iteration=0
max_iterations=100  # Safety valve

while true; do
    iteration=$((iteration + 1))
    
    if [[ $iteration -gt $max_iterations ]]; then
        log "SAFETY: max iterations ($max_iterations) reached, stopping"
        break
    fi
    
    remaining=$(count_remaining)
    log "--- Iteration $iteration | Remaining tasks: $remaining ---"
    
    if [[ "$remaining" -eq 0 ]]; then
        log "All tasks complete! Runner finished."
        break
    fi
    
    # Get next task
    task_json=$(get_next_task)
    
    if [[ -z "$task_json" ]]; then
        log "No claimable tasks found (remaining=$remaining may be blocked/in_progress by others). Stopping."
        break
    fi
    
    # Run agent on this task
    rc=0
    run_agent_on_task "$task_json" || rc=$?
    if [[ "$rc" -eq 2 ]]; then
        log "Dry-run cycle complete (all claimable tasks seen)."
        break
    fi
    
    # Brief pause between tasks
    sleep "$SLEEP_BETWEEN"
done

log "=========================================="
log "Lattice Runner finished"
log "=========================================="

# Summary
log "Final task statuses:"
uv run lattice list --json 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin).get('data', [])
for t in sorted(data, key=lambda x: x['short_id']):
    print(f\"  {t['short_id']} [{t['status']}] {t['title']}\")
" 2>/dev/null | tee -a "$LOG_FILE"
