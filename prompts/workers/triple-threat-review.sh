#!/usr/bin/env bash
# Triple Threat Review Pipeline
# Multi-model code review: 3 parallel reviews, consolidate, fix, re-review, auto-done.
#
# Env vars injected by Lattice worker system:
#   LATTICE_TASK_ID          — the task being reviewed
#   LATTICE_STARTED_EVENT_ID — the process_started event ID (for lifecycle)
#   LATTICE_ROOT             — path to .lattice/ directory
#   LATTICE_COMMIT_SHA       — (optional) commit SHA for review scope

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ACTOR="agent:review-pipeline"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/triple-threat-XXXXXX")
HEAD_SHA=$(git -C "$PROJECT_ROOT" rev-parse HEAD)
REPORT_TIMESTAMP=$(date +%Y%m%d-%H%M%S)
TASK_SHORT=$(echo "$LATTICE_TASK_ID" | tail -c 9)
REPORT_FILE="notes/CR-${TASK_SHORT}-triple-${REPORT_TIMESTAMP}.md"
REPORT_PATH="${PROJECT_ROOT}/${REPORT_FILE}"

# ---------------------------------------------------------------------------
# Error trap — signal failure to Lattice on unexpected exit
# ---------------------------------------------------------------------------
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        lattice worker fail "$LATTICE_TASK_ID" "$LATTICE_STARTED_EVENT_ID" \
            --actor "$ACTOR" \
            --error "Triple Threat Review failed with exit code $exit_code" 2>/dev/null || true
    fi
    rm -rf "$WORK_DIR" 2>/dev/null || true
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
log() {
    echo "[triple-threat] $(date +%H:%M:%S) $*"
}

die() {
    echo "[triple-threat] FATAL: $*" >&2
    exit 1
}

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
[ -n "${LATTICE_TASK_ID:-}" ]          || die "LATTICE_TASK_ID not set"
[ -n "${LATTICE_STARTED_EVENT_ID:-}" ] || die "LATTICE_STARTED_EVENT_ID not set"
[ -n "${LATTICE_ROOT:-}" ]             || die "LATTICE_ROOT not set"

log "Starting Triple Threat Review for task $LATTICE_TASK_ID"
log "HEAD SHA: $HEAD_SHA"
log "Working directory: $WORK_DIR"

# ---------------------------------------------------------------------------
# Step 0: Read task context
# ---------------------------------------------------------------------------
log "Step 0 — Reading task context"
TASK_CONTEXT=$(lattice show "$LATTICE_TASK_ID" 2>&1) || die "Failed to read task $LATTICE_TASK_ID"
echo "$TASK_CONTEXT" > "$WORK_DIR/task-context.txt"

# ---------------------------------------------------------------------------
# Step 1: Round 1 — Parallel multi-model review
# ---------------------------------------------------------------------------
log "Step 1 — Launching parallel reviews (Claude + Codex + Gemini)"

REVIEW_CLAUDE="$WORK_DIR/review-claude.md"
REVIEW_CODEX="$WORK_DIR/review-codex.md"
REVIEW_GEMINI="$WORK_DIR/review-gemini.md"

# Export env vars for prompt templates to reference
export LATTICE_TASK_ID LATTICE_ROOT LATTICE_STARTED_EVENT_ID HEAD_SHA PROJECT_ROOT
export REVIEW_CLAUDE REVIEW_CODEX REVIEW_GEMINI

# Claude review
claude -p "Read ${PROJECT_ROOT}/prompts/workers/review-round1.md and follow the instructions for task $LATTICE_TASK_ID. Write your review to $REVIEW_CLAUDE" \
    --dangerously-skip-permissions &
PID_CLAUDE=$!

# Codex review
codex exec --full-auto --skip-git-repo-check \
    "Read ${PROJECT_ROOT}/prompts/workers/review-round1.md and follow the instructions for task $LATTICE_TASK_ID. Write your review to $REVIEW_CODEX" &
PID_CODEX=$!

# Gemini review
gemini -m gemini-3-pro-preview --yolo \
    "Read ${PROJECT_ROOT}/prompts/workers/review-round1.md and follow the instructions for task $LATTICE_TASK_ID. Write your review to $REVIEW_GEMINI" &
PID_GEMINI=$!

log "Waiting for all three reviewers (PIDs: $PID_CLAUDE, $PID_CODEX, $PID_GEMINI)"

FAILURES=0
wait $PID_CLAUDE  || { log "WARNING: Claude review failed (exit $?)"; FAILURES=$((FAILURES+1)); }
wait $PID_CODEX   || { log "WARNING: Codex review failed (exit $?)"; FAILURES=$((FAILURES+1)); }
wait $PID_GEMINI  || { log "WARNING: Gemini review failed (exit $?)"; FAILURES=$((FAILURES+1)); }

if [ $FAILURES -eq 3 ]; then
    die "All three reviewers failed — cannot continue"
fi

# Create placeholder files for any reviewer that failed silently (no output)
for f in "$REVIEW_CLAUDE" "$REVIEW_CODEX" "$REVIEW_GEMINI"; do
    if [ ! -s "$f" ]; then
        echo "*(No review output produced by this reviewer.)*" > "$f"
    fi
done

log "Round 1 complete — $((3 - FAILURES))/3 reviewers succeeded"

# ---------------------------------------------------------------------------
# Step 2: Consolidate findings
# ---------------------------------------------------------------------------
log "Step 2 — Consolidating findings"

CONSOLIDATED="$WORK_DIR/consolidated-findings.md"
export CONSOLIDATED

claude -p "Read ${PROJECT_ROOT}/prompts/workers/review-consolidate.md and follow the instructions. The three review files are: Claude=$REVIEW_CLAUDE Codex=$REVIEW_CODEX Gemini=$REVIEW_GEMINI. Write the consolidated report to $CONSOLIDATED" \
    --dangerously-skip-permissions \
    || die "Consolidation failed"

if [ ! -s "$CONSOLIDATED" ]; then
    die "Consolidation produced no output"
fi

log "Consolidation complete"

# ---------------------------------------------------------------------------
# Step 3: Fix worthy items
# ---------------------------------------------------------------------------
log "Step 3 — Fixing review findings"

FIX_REPORT="$WORK_DIR/fix-report.md"
export FIX_REPORT

claude -p "Read ${PROJECT_ROOT}/prompts/workers/review-fix.md and follow the instructions. The consolidated findings are at $CONSOLIDATED. Write your fix report to $FIX_REPORT" \
    --dangerously-skip-permissions \
    || die "Fix phase failed"

if [ ! -s "$FIX_REPORT" ]; then
    echo "*(Fix agent produced no report. Proceeding to verification.)*" > "$FIX_REPORT"
fi

log "Fix phase complete"

# ---------------------------------------------------------------------------
# Step 4: Round 2 — Verification review
# ---------------------------------------------------------------------------
log "Step 4 — Verification review (Round 2)"

VERIFICATION="$WORK_DIR/verification-report.md"
export VERIFICATION

claude -p "Read ${PROJECT_ROOT}/prompts/workers/review-round2.md and follow the instructions. The consolidated findings are at $CONSOLIDATED. The fix report is at $FIX_REPORT. Write your verification report to $VERIFICATION" \
    --dangerously-skip-permissions \
    || die "Verification review failed"

if [ ! -s "$VERIFICATION" ]; then
    die "Verification review produced no output"
fi

log "Verification complete"

# ---------------------------------------------------------------------------
# Step 5: Decision — assemble final report and close out
# ---------------------------------------------------------------------------
log "Step 5 — Assembling final report and making decision"

# Detect verdict from verification report
VERDICT="REMAINING"
if grep -qi "^.*CLEAN" "$VERIFICATION" 2>/dev/null; then
    VERDICT="CLEAN"
fi

# Assemble the full report
{
    echo "# Triple Threat Review Report"
    echo ""
    echo "**Task:** $LATTICE_TASK_ID"
    echo "**Commit:** $HEAD_SHA"
    echo "**Date:** $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "**Verdict:** $VERDICT"
    echo ""
    echo "---"
    echo ""
    echo "## Round 1: Multi-Model Reviews"
    echo ""
    echo "### Claude Review"
    echo ""
    cat "$REVIEW_CLAUDE"
    echo ""
    echo "### Codex Review"
    echo ""
    cat "$REVIEW_CODEX"
    echo ""
    echo "### Gemini Review"
    echo ""
    cat "$REVIEW_GEMINI"
    echo ""
    echo "---"
    echo ""
    echo "## Consolidated Findings"
    echo ""
    cat "$CONSOLIDATED"
    echo ""
    echo "---"
    echo ""
    echo "## Fix Report"
    echo ""
    cat "$FIX_REPORT"
    echo ""
    echo "---"
    echo ""
    echo "## Verification (Round 2)"
    echo ""
    cat "$VERIFICATION"
} > "$REPORT_PATH"

log "Report written to $REPORT_FILE"

# Attach the report artifact to the task
lattice attach "$LATTICE_TASK_ID" "$REPORT_FILE" \
    --role review \
    --title "TripleThreatReview — $HEAD_SHA" \
    --actor "$ACTOR"

if [ "$VERDICT" = "CLEAN" ]; then
    # All issues resolved — commit any fixes and mark done
    log "Verdict: CLEAN — committing fixes and marking task done"

    # Commit any staged/unstaged changes from the fix phase
    cd "$PROJECT_ROOT"
    if ! git diff --quiet HEAD 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
        git add -A
        git commit -m "fix: apply review findings for $LATTICE_TASK_ID

Automated fixes from Triple Threat Review pipeline.
Reviewed by: Claude, Codex, Gemini
Report: $REPORT_FILE"
    fi

    lattice status "$LATTICE_TASK_ID" done --actor "$ACTOR" \
        --reason "Triple Threat Review passed — all findings resolved"

    lattice worker complete "$LATTICE_TASK_ID" "$LATTICE_STARTED_EVENT_ID" \
        --actor "$ACTOR" \
        --result "Review complete (CLEAN) — see attached report"

    log "Task marked done"
else
    # Issues remain — leave in review, comment with summary
    log "Verdict: REMAINING — leaving task in review status"

    # Extract a brief summary of remaining issues for the comment
    REMAINING_SUMMARY=$(grep -i -A2 "remaining\|unfixed\|open" "$VERIFICATION" | head -20 || echo "See attached report for details.")

    lattice comment "$LATTICE_TASK_ID" \
        "Triple Threat Review complete with outstanding items. Verdict: REMAINING. ${REMAINING_SUMMARY}" \
        --actor "$ACTOR"

    lattice worker complete "$LATTICE_TASK_ID" "$LATTICE_STARTED_EVENT_ID" \
        --actor "$ACTOR" \
        --result "Review complete (REMAINING) — outstanding issues noted in report"

    log "Task left in review with comment"
fi

log "Triple Threat Review pipeline finished (verdict: $VERDICT)"
