# Future Features

Candidates for post-v0 implementation, drawn from the Lattice vs Linear audit (2026-02-15).

## Cycles / Time-Boxing

Time-boxed iteration boundaries for agent work. Linear's model: auto-scheduled sprints with duration, cooldown periods, auto-rollover of incomplete work, velocity tracking, and capacity estimation. Lattice equivalent would be lighter — likely a config-defined cycle entity with start/end dates, task association, and rollover semantics. Agents benefit from iteration boundaries for scoping work and measuring throughput.

## Project-Level Grouping

A first-class entity above epics for grouping related work toward a deliverable. Properties: name, lead, members, start/target dates, milestones, progress tracking. Currently Lattice uses `epic` task type + relationships, but this doesn't give you aggregate progress, status updates, or a dedicated view. A project entity would sit between tasks and any future roadmapping layer.

## Analytics / Metrics Aggregation

Lattice already stores per-event metrics (tokens_in, tokens_out, cost_usd, latency_ms, tool_calls, retries, cache_hits) as passthrough data. The gap is aggregation and visualization. Candidates:
- Cost roll-ups per task, per agent, per time period
- Velocity tracking (tasks completed per cycle/week)
- Agent efficiency metrics (tokens per task, retry rates)
- Dashboard charts (burn-up, cumulative flow, scatter)
- CLI summary commands (`lattice stats`, `lattice costs`)

This is high-value because the data is already being captured — it just needs a read path.

## Spatial / Dimensional Task Visualization

The task graph (blocking relationships, dependencies, status) maps naturally to spatial visualization. Nodes are tasks; edges are relationships. Structure becomes visible — root blockers are obvious, orphan clusters stand out, connected components reveal work streams.

**v1 (implemented):** 2D force-directed graph in the dashboard ("Cube" view tab). Status maps to X-axis position (left=backlog, right=done), force-directed Y for separation. Node color from lane/status colors, size from priority. Directed edges colored by relationship type. Hover tooltips, click-to-select with side panel, double-click to navigate to detail.

- **Library:** `force-graph` 2D (~80KB, canvas-based)
- **Layout:** Status-constrained X via `d3.forceX`, NOT dagMode (which uses topology, not status)
- **Endpoint:** `GET /api/graph` with ETag support for efficient polling
- **Fallback:** Graceful CDN failure message, canvas support check, mobile viewport notice

**v1.5 (planned):** 3D toggle within the Cube view. Lazy-loads `3d-force-graph` (~600KB) only when user activates 3D mode. Same status-constrained layout extended to XZ plane with force-directed Y for depth.

**v2 (future):** Implement as a Display within the Panel/Display system. User-configurable dimension mapping — choose which task properties (status, priority, assignee, type, age) map to which visual channels (position, color, size, shape). This is the path toward n-dimensional projections where structure in high-dimensional task data becomes visible.

The key architectural constraint: the data model doesn't need to change. The graph is already captured in `relationships_out`. This is purely a read-path / visualization question, which means it can evolve independently of the core event-sourced engine.
