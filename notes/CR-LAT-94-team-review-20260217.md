# Team Three Code Review — LAT-94

## Metadata
- **Task:** LAT-94 — Dashboard: floating detail panel on task click
- **Commit:** 93643cc
- **Branch:** main
- **Date:** 2026-02-17
- **Review Type:** Team Three (6-agent parallel review)

### Reviewers
| Agent | Model | Type |
|-------|-------|------|
| Claude | Claude Opus 4.6 (claude-opus-4-6) | Standard + Critical |
| Codex | GPT-5 Codex (gpt-5-codex) | Standard + Critical |
| Gemini | Gemini 3 Pro Preview | Standard + Critical |

---

## Executive Summary

**Verdict: NOT READY FOR PRODUCTION**

All six reviewers converge on one critical finding: the auto-refresh panel update logic is fundamentally broken. Beyond that, there is strong consensus on a race condition in the stale-ID guard pattern. The card sizing changes (`large` variant) are structurally sound with minor nits.

The diff is small (27 insertions, 7 deletions in a single file) but introduces logic bugs that contradict the feature's stated behavior.

---

## Consensus Findings

### BLOCKER: Auto-refresh closes the detail panel instead of updating it

**Agreement: 5/6 reviewers** (Claude Standard, Claude Critical, Codex Standard, Codex Critical, Gemini Critical — Gemini Standard did not flag this, focusing instead on the race condition)

**The bug:** The `startAutoRefresh` function calls `await route(location.hash.slice(1))` before checking whether to refresh the detail panel. Inside `route()`, there is an unconditional call to `closeDetailPanel()` whenever `_detailPanelTaskId` is truthy. This sets `_detailPanelTaskId = null`. By the time execution reaches the panel refresh guard (`if (_detailPanelTaskId && tasksChanged)`), the variable is always null. The entire panel refresh block (lines 6677-6689) is dead code.

**Net effect:** The panel closes itself every 5 seconds whenever any task data changes. This is the opposite of "auto-refresh silently updates panel content."

**Recommended fix (consensus):** Modify `route()` to accept a flag (e.g., `{ keepPanel: true }`) or restructure auto-refresh to preserve panel state during same-view re-renders. The cleanest approach (per Claude Critical) is to refactor `route()` so panel-close logic only fires on actual hash changes, not re-renders of the same view.

### BLOCKER: Cross-task race condition in panel refresh

**Agreement: 6/6 reviewers** (unanimous)

**The bug:** After the `await Promise.all(...)` that fetches task + events data, the code re-checks `_detailPanelTaskId` with a truthiness check (`if (_detailPanelTaskId)`), not an identity check. If the user switches from Task A to Task B while the fetch is in-flight, the code renders Task A's data into Task B's panel. Worse, `_renderPanelContent` wires action handlers using the passed task ID, so mutations could be directed at the wrong task.

**Note:** This is currently moot because the dead-code blocker prevents this path from executing. But it must be fixed alongside Blocker #1.

**Recommended fix (unanimous):**
```javascript
var panelId = _detailPanelTaskId;
var dpResults = await Promise.all([...]);
if (_detailPanelTaskId === panelId) _renderPanelContent(panelId, dpResults[0], dpResults[1]);
```

---

## Important Findings

### 1. Focus guard misses `<select>` elements

**Raised by:** Claude Critical

The focus detection at line 6680 checks `input:focus, textarea:focus` but the panel contains `<select>` dropdowns for status, priority, and type. A user interacting with a dropdown would not be detected as "editing," and the panel would be re-rendered mid-selection.

**Fix:** Change selector to `input:focus, textarea:focus, select:focus`.

### 2. Full innerHTML replacement destroys scroll position and draft text

**Raised by:** Claude Critical, Gemini Critical (as DOM thrashing)

Every call to `_renderPanelContent` replaces the entire panel body via `innerHTML`. This destroys:
- Scroll position within the panel
- Partially typed comment text (if the textarea has lost focus)
- Text selections (noted by Gemini Critical)

The focus guard only protects *active* focus. A user who types a comment, scrolls down, then returns would lose their draft.

### 3. Small card width silently increased from 120 to 130

**Raised by:** Claude Standard

The old code used `cardW = 120 / globalScale`. The new code uses `baseW = large ? 200 : 130`. The non-large path widened from 120 to 130 — an undocumented ~8% increase affecting all cards.

### 4. `large` variant not wired at call site

**Raised by:** Codex Standard

`webDrawCard` now branches on `opts.large`, but the only call site in `drawWebNode` passes `large: isLargeCard` — **UPDATE:** On re-examination of the full diff, the call site at line 4261 *does* pass `large: isLargeCard`. Codex's finding appears to reference older line numbers and may be based on incomplete diff context. **Status: Likely false positive** — needs verification against the actual committed code.

### 5. No single-flight guard for auto-refresh loop

**Raised by:** Codex Critical, Claude Critical

`setInterval` with an `async` callback does not wait for completion. If a refresh cycle takes longer than 5s (server latency, network issues), the next interval fires while the previous is suspended. Both cycles interleave at `await` points, potentially causing stale data overwrites. The new panel API calls increase the time per cycle, widening the race window.

### 6. Silent catch swallows all errors

**Raised by:** Claude Standard, Claude Critical

`catch(ex) { /* panel data fetch failed, ignore */ }` silently swallows everything including programming errors (TypeError, ReferenceError). At minimum, `console.debug` would aid debugging.

---

## Potential / Nits

| Finding | Raised by | Notes |
|---------|-----------|-------|
| Function comment missing `large` option | Claude Standard, Claude Critical | Documentation debt |
| Ternary proliferation in card sizing | Claude Critical | Readability — config object would be cleaner |
| Magic numbers in card rendering | Claude Critical, Gemini Standard, Gemini Critical | Stripe width, padding, font sizes hardcoded inline |
| Large-card stripe cornerR > stripeW | Codex Critical | `cornerR = 5/gs` but `stripeW = 4/gs` — potentially malformed rounded rect |
| globalScale = 0 division guard | Gemini Critical | Unlikely but undefined behavior with Infinity fonts |
| Unnecessary panel refresh when other tasks change | Claude Standard, Gemini Critical | Panel refetches even when the specific panel task didn't change |

---

## Required Actions Before Merge

1. **Fix route/panel collision** — Prevent `route()` from closing the detail panel during auto-refresh when the view hasn't changed
2. **Add identity guard on panel task ID** — Capture ID before `await`, compare after, skip render on mismatch
3. **Add `select:focus` to focus guard** — Both in auto-refresh and post-action refresh paths

## Recommended Follow-ups (Non-Blocking)

4. Add single-flight protection to auto-refresh loop
5. Replace silent catch with `console.debug`
6. Preserve scroll position / draft text during panel refresh (incremental DOM updates vs innerHTML replacement)
7. Clamp large-card stripe cornerRadius to not exceed stripe width

---

## Individual Reviews

The full individual reviews are preserved at:
- `notes/.tmp/CR-LAT-94-Standard-Claude.md`
- `notes/.tmp/CR-LAT-94-Critical-Claude.md`
- `notes/.tmp/CR-LAT-94-Standard-Codex.md`
- `notes/.tmp/CR-LAT-94-Critical-Codex.md`
- `notes/.tmp/CR-LAT-94-Standard-Gemini.md`
- `notes/.tmp/CR-LAT-94-Critical-Gemini.md`
