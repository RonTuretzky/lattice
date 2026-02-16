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

The task graph (blocking relationships, dependencies, status) maps naturally to spatial visualization. The mental model: a 3D web flowing left-to-right, where position encodes progress and color encodes status — white (to-do) on the left, yellow (in progress) in the middle, purple (review) further right, green/dimmed (done) on the far right. Nodes are tasks; edges are blocking relationships. Structure becomes visible — root blockers are obvious, orphan clusters stand out, the critical path is literally the longest line through the web.

This is v2+ territory, but the architecture should keep the door open:

- **v1 foundation:** The relationship graph already exists in the event log (`blocks`, `blocked_by`, `related_to`, `subtask_of`). Stats computations can derive graph properties (longest chain, most-blocking node, clusters) without any new data model.
- **v2 candidate:** 2D force-directed or DAG layout in the dashboard. Status-as-color, position-as-progress. Interactive — click a node to see the task, hover to see the dependency chain.
- **v3+ aspiration:** Higher-dimensional mappings. Tasks have many properties beyond status and dependencies — priority, type, assignee, tags, age, cost, complexity. Each of these is a potential axis or visual channel. The upgrade path is from 2D graph → 3D spatial web → n-dimensional projections where the user chooses which dimensions to map to which visual channels. This is genuinely novel territory for project management visualization.

The key architectural constraint: the data model doesn't need to change. The graph is already captured. This is purely a read-path / visualization question, which means it can evolve independently of the core event-sourced engine.
