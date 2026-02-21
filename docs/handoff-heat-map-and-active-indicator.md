# Handoff: Heat Map & Active Session Indicator Not Rendering

## What We Built

Two dashboard features in this session:

### LAT-178: Active Session Indicator
- Pulsing green dot + "Active" badge on tasks that are `in_progress` with a non-null `assigned_to`
- `has_active_session` boolean added to `/api/tasks` compact response, detail, and full endpoints
- CSS: `.active-dot` with `@keyframes activePulse`, `.active-badge`
- Shows in board cards, list view, floating panel, and full detail view

### LAT-179: Heat Map (Last Status Change Time)
- `last_status_changed_at` field added to task snapshots in `src/lattice/core/tasks.py`
  - Set from `task_created` event `ts` on init
  - Updated from `status_changed` event `ts` on transitions
  - Included in `compact_snapshot()`
- Dashboard JS: `getHeatClass(ts)` returns `heat-hot` (< 1min), `heat-warm` (< 10min), `heat-cooling` (< 1hr), or empty string
- Dashboard JS: `formatHeatAge(ts)` shows human-readable age ("3m", "2h", "5d") next to the short ID on board cards, colored to match heat tier
- CSS: `.card.heat-hot` red border-left, `.card.heat-warm` orange, `.card.heat-cooling` yellow
- Carbon theme overrides added: `[data-theme="carbon"] .card.heat-hot/warm/cooling`
- Heat map ON by default (`isHeatMapEnabled` returns `true` when config is undefined)
- Info popup on eye icon in settings explaining each color tier
- Toggle persists via `POST /api/config/dashboard` with `heat_map_enabled` key
- Server validates `heat_map_enabled` as boolean

### LAT-177: Test Suite Speedup (completed, working)
- `serve_forever(poll_interval=0.05)` in all 4 test locations. 60s -> 20s.

## Current State: What's Broken

After restarting the dashboard (`lattice dashboard`) and hard-refreshing the browser, **neither feature is visually rendering**. The data pipeline works end-to-end:

1. **Snapshots on disk** have `last_status_changed_at` (verified)
2. **API responses** include `last_status_changed_at` and `has_active_session` (verified via `curl` and browser JS)
3. **The served HTML** contains the JS functions and CSS rules (verified via `curl | grep`)
4. **The global tool was reinstalled** with `uv tool install . --force` (verified)

Yet nothing appears visually on the cards.

## Hypotheses (Not Yet Investigated)

### 1. CSS Specificity / Cascade
The Carbon theme applies `border-color:#2A2A2A` on `.card` via `[data-theme="carbon"] .card`. The heat rules use `[data-theme="carbon"] .card.heat-hot{border-left:3px solid #ef4444}`. These should have higher specificity (0-3-0 vs 0-2-0), but:
- Check if `border` shorthand on the base `.card` rule is resetting `border-left` after the heat rule applies
- Check cascade order: the base `.card` rule is at line 194, heat rules at ~207, Carbon overrides at ~569. If anything resets borders after the heat class, it would hide the effect.
- **Test:** In browser DevTools, manually add `class="heat-hot"` to a card and see if the red border appears. If not, it's a CSS problem. If yes, it's a JS problem.

### 2. JS Not Applying Classes
The `renderBoardCard` function builds HTML with the heat class. But:
- Is `renderBoardCard` actually being called? Or is some other render path used?
- Is there a second board render that overwrites the first?
- The `formatHeatAge` helper was added in the same function. If the age text isn't showing either, the function is either not being called or the data isn't reaching it.
- **Test:** `document.querySelectorAll('.card').forEach(c => console.log(c.className))` to see if any card has a heat class.

### 3. The Active Indicator Has Correct But Invisible Output
`has_active_session` is `false` for all visible tasks because:
- It requires `status == "in_progress"` AND `assigned_to` is non-null
- The only `in_progress` task visible is LAT-175 in "Check My Work" (review status), not in_progress
- LAT-180 was moved to `in_planning` without an assignee
- **Test:** `lattice status LAT-180 in_progress --actor agent:claude-cli && lattice assign LAT-180 agent:claude-cli --actor agent:claude-cli` then refresh

### 4. Global Tool Still Serving Stale Code
Even after `uv tool install . --force`, the running `lattice dashboard` process was started before the reinstall. The process loaded old Python into memory. Static files are re-read from disk on each request, but `STATIC_DIR` is resolved at import time.
- **Test:** Kill the dashboard process, restart it, then check `curl -s http://127.0.0.1:<port>/ | wc -c` matches `wc -c < src/lattice/dashboard/static/index.html`

### 5. Stale .pyc or Installed Package Not Matching Source
The `uv tool install` copies files to `~/.local/share/uv/tools/lattice-tracker/`. The copy might not include the latest `index.html`.
- **Test:** `diff <(curl -s http://127.0.0.1:<port>/) src/lattice/dashboard/static/index.html`
- **Test:** `grep "formatHeatAge" ~/.local/share/uv/tools/lattice-tracker/lib/python3.12/site-packages/lattice/dashboard/static/index.html`

## Files Changed

| File | Changes |
|------|---------|
| `src/lattice/core/tasks.py` | `last_status_changed_at` in PROTECTED_FIELDS, _init_snapshot, _mut_status_changed, compact_snapshot |
| `src/lattice/dashboard/server.py` | `has_active_session` in task list/detail/full endpoints; `heat_map_enabled` validation + persistence; `Cache-Control: no-cache` on static files |
| `src/lattice/dashboard/static/index.html` | Heat CSS (base + Carbon), active session CSS, `getHeatClass`, `formatHeatAge`, `isHeatMapEnabled` (default true), `renderBoardCard` updated, info popup, settings toggle |
| `tests/test_dashboard/conftest.py` | `poll_interval=0.05` |
| `tests/test_dashboard/test_git_api.py` | `poll_interval=0.05` |
| `tests/test_dashboard/test_graph_api.py` | `poll_interval=0.05` |
| `tests/test_dashboard/test_server.py` | `poll_interval=0.05` |
| `tests/test_core/test_tasks.py` | `last_status_changed_at` in expected compact fields |
| `CLAUDE.md` | Global tool vs dev install failure mode documentation |

## Recommended First Steps for Next Session

1. Run `uv run lattice dashboard` (dev install, not global) and verify changes are visible
2. If still not visible, open DevTools and inspect a card element to check applied classes and computed styles
3. If classes are missing, add `console.log` in `renderBoardCard` to trace execution
4. If classes are present but invisible, the CSS cascade is the problem; use DevTools to see what overrides `border-left`

## Commits

All on `main`, pushed:
- `d47b2a1` fix: reduce test suite time from 60s to 20s (LAT-177)
- `cc47877` feat: add active session indicator (LAT-178)
- `253f032` fix: adjust heat indicator thresholds (LAT-179)
- `682e65f` fix: heat map defaults on, Carbon theme support, info popup (LAT-179)
- `6cda0b0` fix: add Cache-Control no-cache header for static files (LAT-179)
- `35535f4` docs: add global tool vs dev install failure mode to CLAUDE.md
