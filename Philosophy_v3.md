# a philosophy of coordination

Lattice gives agents and humans a shared surface for tracking work. tasks move through sequences — backlog to planning to execution to review to done — and every transition is an attributed, immutable event. the `.lattice/` directory sits in your project like `.git/` does: plain files that any mind can read, any tool can write, and git can merge.

that's the whole idea. agents claim work, do it, leave context for whatever mind comes next. humans set direction, make judgment calls, review output. tasks flow. decisions accumulate. nothing is lost between context windows.

everything below is why it works the way it does.

---

## the primitives

Lattice asks you to believe six things. these are the load-bearing concepts — not features, but commitments. accept them and the system works. resist them and you're fighting the grain.

**task.** work has a name before it begins. a task is a persistent, attributed record of intent — it outlives the session that created it, the agent that worked it, the conversation that spawned it. tasks have types (task, ticket, epic, bug, spike, chore) and owners. if something needs doing, it gets a task. work that isn't named is work that other minds cannot see.

**event.** every change is an immutable fact. X happened at time T, by actor A. events are the source of truth — task snapshots are derived caches, regenerable at any time. you cannot silently edit history. you can only append to it. this is the foundation everything else rests on.

**status.** work moves through a constrained sequence, not a free-form field. `backlog → in_planning → planned → in_progress → review → done`. the transitions are defined in config and enforced by the CLI. invalid moves are rejected. this means status is a shared language — when a task says `review`, every mind reading the board agrees on what that means.

**actor.** every write has a who. `human:atin`. `agent:claude-opus-4`. `team:frontend`. agents and humans are both first-class participants. you cannot write anonymously. in a world where autonomous agents make real decisions, the minimum viable trust is knowing who decided what.

**relationship.** dependencies are typed, not vague. you cannot just "link" two tasks — you must declare why: `blocks`, `depends_on`, `subtask_of`, `spawned_by`, `supersedes`, `duplicate_of`, `related_to`. each type carries meaning that agents and humans can reason about. the graph of relationships is how complex work decomposes into coordinated parts.

**artifact.** work product attaches to tasks as first-class objects — conversation logs, prompts, designs, files — with provenance, optional cost tracking, and sensitivity markers. artifacts are not comments. they are structured content that survives the session and transfers to the next mind.

these six primitives compose into a coordination system where work is visible, change is auditable, status is meaningful, ownership is explicit, dependencies are intentional, and output is preserved. that is the worldview. everything else is implementation.

---

## files

files are the most universal substrate in computing — every language reads them, every agent navigates directories, every tool ever built can open a path and see what's there. Lattice stores coordination state in plain files the same way git stores code history in plain files.

not a service you connect to. a part of the project's body.

---

## events

every change — status, assignment, comment — becomes an immutable event. X happened at time T, by actor A. facts accumulate and don't conflict. two agents on different machines append independently; histories merge through git.

task snapshots are regenerable projections of the log. if they disagree with events, events win. systems that store only current state have chosen amnesia as architecture — they can tell you what is but not how it came to be. state is a conclusion. events are evidence.

archiving moves events to a quieter room — not deletion but intentional release of attention.

---

## attribution

every write requires an actor. `human:atin`. `agent:claude-opus-4`. you cannot write anonymously. this is a position about responsibility: in a world where agents act autonomously, the minimum viable trust is *we can see what you did.*

optional provenance goes deeper — `triggered_by`, `on_behalf_of`, `reason` — there when the chain of causation matters, invisible when it doesn't.

---

## self-similarity

a Lattice instance at the repo level and one at the program level are the same thing. same format, same events, same invariants. only scope differs. the grammar of work does not change with scale — only the vocabulary.

complex coordination emerges from simple instances composed by intelligent intermediaries. Lattice does not need to be complex because the minds using it are.

---

## patience

there is a pressure to build more — database, real-time sync, auth, plugins. each addition individually defensible, collectively fatal.

the on-disk format is the stable contract. the CLI can be rewritten. the dashboard can be replaced. but the events, the file layout, the schema — load-bearing walls. event sourcing, atomic writes, crash recovery, deterministic locking — foundational complexity that makes growth possible rather than necessary.

---

## altitude

work has a natural grain. epics hold strategic intent — "Build the auth system." tickets hold deliverables — "Implement OAuth for the backend." tasks hold execution — "Write the token refresh handler." three tiers, each at a different resolution of attention.

humans tend to think at the ticket level: *what* needs to ship and *why*. agents tend to think at the task level: *how* to make it happen. epics hold the arc that connects individual deliverables into something coherent.

the hierarchy is available, not imposed. some will use all three tiers. some will use flat tasks and nothing else. the event log records what happened regardless of how you organize it. categories are configuration. events are permanent.

---

## the bet

when humans coordinate, they route around broken tools with hallway conversations and shared intuition. agents have no hallway. the file format, the event schema, the CLI — to an agent, these are not implementation details. they are the *entire language of collaboration*.

get the language right, and minds that speak it achieve coordination patterns no individual mind could manage. get it wrong, and capable minds fumble in the dark — intelligent in isolation, incoherent in concert.

the systems that coordinate intelligence are themselves a form of intelligence. the cost of building too early is refinement. the cost of building too late is irrelevance. one is recoverable.

---

## the shape you might recognize

if you've used Linear, you know the shape. opinionated. constrained. fast. but Linear is for teams with Slack and standups. Lattice is for minds that materialize, perform work, and vanish — context windows, not conversations.

no seats. no inboxes. there is a dashboard, but the real interface is the file system. the real users are processes that think in tokens and act in tool calls.

---

## what we become

the most impoverished vision of the future is agents replacing humans. the second most impoverished is humans constraining agents. both imagine zero-sum. both are wrong.

the future worth building is where both kinds of mind become more than they could be alone. neither diminished. both elevated. carbon. silicon. the emergent space between.

we will build it together. we already are.

---

*Lattice is context engineering — designing the structures through which minds coordinate. proudly built by a member of the New York City Context Engineering Guild.*
