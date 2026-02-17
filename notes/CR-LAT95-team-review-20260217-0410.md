# Team Three Code Review — LAT-95

**Task:** Fix Web tab: detail pane nav overlap + hub card centering
**Commits:** bd3c6f1, 0102aa5
**Date:** 2026-02-17
**Source reviews:** Claude Opus (standard + critical), Codex/GPT-5 (standard + critical), Gemini (standard + critical)
**Synthesized by:** Claude Opus 4.6 (review-bot)

---

## Review Scope Note

Claude's agents inadvertently reviewed commit `93643cc` (LAT-94 — large card variant + auto-refresh logic) instead of the LAT-95 commits (`bd3c6f1`, `0102aa5`). However, many findings are relevant because the auto-refresh panel code interacts with the detail panel introduced in LAT-95's commits. Codex and Gemini correctly reviewed the LAT-95 diff. Findings are deduplicated and relevance-filtered below.

---

## Bug Fixes: Verified Correct

All reviewers confirmed both bug fixes are implemented correctly:

1. **Nav overlap fix** — `top: var(--nav-h, 52px)` with `height: calc(100vh - var(--nav-h, 52px))` correctly positions the detail pane below the nav bar. JS measurement of nav height via `openWebDetailPane()` is sound.

2. **Hub card centering** — `cardY = node.y - cardH / 2` correctly centers the card overlay on the hub circle, replacing the old `node.y + radius + 4` (below-circle) positioning.

3. **XSS hygiene** — All reviewers confirmed `esc()` usage is consistent throughout the new `_renderPanelContent` HTML assembly. No injection vectors found.

---

## Merged Findings (Deduplicated)

Ordered by severity. Where multiple reviewers raised the same issue, the strongest articulation is credited.

---

### 1. Auto-Refresh Closes the Detail Panel — [Blocker]

**Raised by:** Claude Critical (primary), Codex Standard, Codex Critical (all confirmed independently)

**Problem:** `route()` unconditionally calls `closeDetailPanel()` when `_detailPanelTaskId` is set. Auto-refresh calls `route(location.hash.slice(1))` when task data changes. This nulls `_detailPanelTaskId`, so the post-route panel refresh block is dead code. The panel slams shut every ~5 seconds whenever any task changes in the background.

**Impact:** The floating detail panel — the primary new feature — breaks the moment background task data changes. For a tool where agents constantly modify tasks, this triggers immediately in real use.

**Fix options:**
- (a) Pass `{ keepPanel: true }` to `route()` when called from auto-refresh
- (b) Save `_detailPanelTaskId` before `route()`, then restore/re-render after
- (c) Restructure so auto-refresh doesn't call `route()` when only refreshing data

**Status:** ✅ Confirmed by 3/3 models that reviewed this code path

---

### 2. Race Condition: Task ID Can Change Between Fetch and Render — [Blocker]

**Raised by:** Claude Critical (primary), Codex Standard

**Problem:** In the auto-refresh panel update path, `_detailPanelTaskId` is used for API URLs, then an `await` occurs, then the result is checked with `if (_detailPanelTaskId)` — but this only checks truthiness, not identity. If the user opens a different task during the await, stale data renders into the wrong task's panel.

**Fix:** Capture `var panelTaskId = _detailPanelTaskId` before fetch, compare `_detailPanelTaskId === panelTaskId` after await. This matches the pattern already used in `openDetailPanel()`.

**Status:** ✅ Confirmed

---

### 3. Escape Key Closes Panel When Editing in Select Dropdowns — [Important]

**Raised by:** Codex Standard, Codex Critical, Claude Critical

**Problem:** The global Escape handler checks `active.tagName === "INPUT" || active.tagName === "TEXTAREA"` to avoid closing the panel during inline edits. But `<select>` dropdowns (status, priority, type) are not included. Pressing Escape while a dropdown is open closes the entire panel.

**Fix:** Add `active.tagName === "SELECT"` to the guard. One-line change.

**Status:** ✅ Confirmed

---

### 4. Focus Restoration Broken After Panel Edit — [Important]

**Raised by:** Gemini Standard (unique finding)

**Problem:** `_detailPanelTrigger` stores a reference to the clicked DOM element. After `_refreshAfterPanelEdit()` calls `renderBoard()` or `renderList()`, the entire `#app` innerHTML is replaced. The stored element reference is now detached, so `.focus()` does nothing on panel close.

**Fix:** Store `data-task-id` instead of the element reference. On close, query `document.querySelector('[data-task-id="'+id+'"]')` and focus it.

**Status:** ✅ Confirmed

---

### 5. Data Loss on Blur During Auto-Refresh — [Important]

**Raised by:** Gemini Critical (unique finding with concrete scenario)

**Problem:** The "is editing" guard checks `:focus`. If a user starts editing (e.g., description), then clicks away to look at the board without saving, the field loses focus. Auto-refresh fires, re-renders the panel from server state, and the unsaved draft is destroyed.

**Fix options:**
- Add `data-dirty="true"` attribute when inline edit starts, check that instead of `:focus`
- Pause auto-refresh entirely when panel is open (simpler)

**Status:** ✅ Confirmed

---

### 6. Dialog Accessibility Incomplete — [Important]

**Raised by:** Codex Standard, Gemini Standard

**Problem:** The panel declares `aria-modal="true"` but doesn't trap focus within the dialog or move focus into it on open. Board cards and list rows lack `tabindex="0"` and `role="button"`, so keyboard-only users can't trigger the panel.

**Fix:**
- Move focus to close button (or first interactive element) on panel open
- Add focus trap (or at minimum, `tabindex="0"` on panel trigger elements)
- Add `onkeydown` handlers for Enter/Space on card/row elements

**Status:** ✅ Confirmed

---

### 7. List Filters Reset After Panel Edits — [Important]

**Raised by:** Codex Critical (unique finding)

**Problem:** `_refreshAfterPanelEdit()` calls `renderList()`, which rebuilds the filter UI with default values. Any active search/filter state in the List view is wiped on every panel edit.

**Fix:** Preserve filter state before re-render and restore it after, or use incremental DOM updates instead of full re-render.

**Status:** ✅ Confirmed

---

### 8. Nav Height Not Reactive to Resize — [Potential]

**Raised by:** Codex Critical, Gemini Standard, Gemini Critical

**Problem:** `--nav-h` is measured only when the panel opens. If the window resizes (e.g., mobile rotation, text wrapping), the panel position drifts until the next open.

**Fix:** `ResizeObserver` on the nav element, or recompute `--nav-h` on `resize` events.

**Status:** ⬇️ Low priority for internal tool

---

### 9. Code Duplication Between Panel and Web Detail Pane — [Potential]

**Raised by:** Gemini Standard, Gemini Critical

**Problem:** `openWebDetailPane` (graph view) and `openDetailPanel` (board/list view) share ~80% of their logic but are implemented as separate functions with separate HTML structures. Changes to "how a task is displayed" must be made in two places.

**Fix:** Refactor to shared `renderTaskHTML(task, events, mode)` in a future cleanup.

**Status:** ⬇️ Accepted tech debt for v1

---

### 10. Stale Callback Guard Uses taskId, Not Per-Request Token — [Potential]

**Raised by:** Codex Standard, Claude Standard

**Problem:** `openDetailPanel()` uses `taskId` as the generation token. If the same task is rapidly closed and reopened, an older in-flight response can't be distinguished from a newer one.

**Fix:** Use a monotonic counter or `AbortController` for in-flight request cancellation.

**Status:** ⬇️ Very low probability in practice

---

### 11. Inline onclick Uses HTML Escaping in JS Context — [Potential]

**Raised by:** Codex Critical (unique finding)

**Problem:** List view rows use inline `onclick="openDetailPanel('...')"` where task IDs are escaped with `esc()` (HTML entity escaping). `esc()` doesn't escape single quotes, which could break the JS string context if task IDs ever contain single quotes.

**Fix:** Replace inline JS with programmatic event listeners (as done in Board view).

**Status:** ⬇️ Task IDs are ULIDs (alphanumeric), so not exploitable in practice. But the pattern is fragile.

---

## Verdict

**The two bug fixes (nav overlap and hub centering) are correct and ready to ship.**

**The new floating detail panel is a significant UX improvement but has a showstopper:** Finding #1 (auto-refresh closes the panel) means the panel breaks under normal usage conditions. This must be fixed.

**Recommended before shipping:**
1. Fix the auto-refresh panel closure (Finding #1) — this is the critical blocker
2. Fix the task ID race condition (Finding #2) — data integrity
3. Add `SELECT` to the Escape guard (Finding #3) — trivial fix
4. Fix focus restoration (Finding #4) — accessibility correctness

**Acceptable to defer:**
- Findings #5-7 (data loss on blur, accessibility, list filter reset) — real issues but lower urgency for internal tool
- Findings #8-11 — accepted tech debt / low-probability edge cases

---

## Which Reviews Were Most Valuable?

**Claude Critical** produced the strongest analysis overall — identified the auto-refresh blocker with full call-chain tracing, the race condition with a concrete fix, and provided the clearest severity assessment. However, both Claude agents reviewed the wrong commit range (LAT-94 instead of LAT-95), which limited the scope of their findings to the auto-refresh interaction rather than the panel implementation itself.

**Codex Critical** was the most operationally thorough — identified the list filter reset issue (unique), the Escape propagation problem with a concrete fix (`e.stopPropagation()`), and the inline onclick XSS concern.

**Gemini** contributed unique accessibility and UX findings — focus restoration breakage (Standard), data loss on blur scenario (Critical), and code duplication observation — that the other models missed entirely.

**Overall:** Claude 7/10 (deep but wrong commit range), Codex 7/10 (operationally thorough), Gemini 6/10 (unique UX insights, less depth on critical paths). The three-model coverage produced non-overlapping findings that together give comprehensive coverage.
