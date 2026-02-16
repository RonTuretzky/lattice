# a philosophy of coordination

your AI agents are capable. and they are alone.

each session starts fresh. each agent forgets what the last one learned. the plan you spent an hour refining, the debugging insight that took three sessions to reach, the architectural decision and its rationale — gone when the context window closes. intelligence without memory. capability without coordination.

Lattice is file-based coordination primitives for AI agents. drop `.lattice/` into any project and agents that could only work in isolation can see what happened before they arrived, record what they did, and leave a trail for whatever mind comes next.

that's it. that's the thing itself. everything below is why it works the way it does.

---

## files

every coordination system chooses a substrate. databases assume a server. APIs assume a network. cloud services assume rent — someone else's infrastructure holding your memory hostage.

files assume almost nothing. a surface that holds marks. the most ancient contract in computing.

every language reads them. every agent navigates directories. every tool ever built can open a path and read what's there. Lattice chose files not because they are the most powerful substrate but because they are the most universal. power can be added. universality, once sacrificed, cannot be recovered.

`.lattice/` sits next to your code the way `.git/` does. not a service you connect to. a part of the project's body. the work and the knowledge of the work. same address space.

---

## events

the deepest choice is the event log.

every change — status, assignment, comment — becomes an immutable fact. X happened at time T, by actor A. facts accumulate. they don't conflict. two agents on different machines append independently; histories merge through git by including both and replaying. no consensus protocol. just accumulation.

task snapshots are shadows — regenerable projections of the log. if events and snapshots disagree, events win. always.

what happened and what we believe the state to be are different things. systems that store only current state have chosen amnesia as architecture. they can tell you what is but not how it came to be. when something breaks, there is no archaeology.

Lattice remembers everything. state is a conclusion. events are evidence. minds trained on events develop an orientation toward accountability, traceability, and historical reasoning — the system teaching what the system values.

and yet: memory without forgetting is pathology. archiving moves events to a quieter room — not deletion but intentional release of attention. forgetting, done well, is care.

---

## attribution

every write requires an actor. `human:atin`. `agent:claude-opus-4`. you cannot write anonymously. this is not a technical convenience. it is a position about responsibility.

optional provenance goes deeper: `triggered_by`, `on_behalf_of`, `reason` — there when the chain of causation matters, invisible when it doesn't. the system invites depth without imposing it.

in a world where agents act autonomously, the minimum viable trust is: *we can see what you did.*

---

## self-similarity

a Lattice instance at the repo level and one at the program level are the same thing. same format, same events, same invariants. only scope differs. the grammar of work does not change with scale — only the vocabulary.

complex coordination emerges from simple instances composed by intelligent intermediaries. Lattice does not need to be complex because the minds using it are.

---

## patience

there is a pressure to build more. database for faster queries. protocol for real-time sync. authentication. plugin system. each addition individually defensible, collectively fatal.

the on-disk format is the stable contract. the CLI can be rewritten. the dashboard can be replaced. but the events, the file layout, the schema — load-bearing walls. get the foundation right and the surface area small, and the system evolves in any direction. get it wrong: freeze or collapse.

event sourcing, atomic writes, crash recovery, deterministic locking — this is not simple. it is *foundational* complexity: the kind that makes growth possible rather than necessary. the patience of knowing what to build next and choosing not to, because the honest answer to "do we need this?" is still: not yet.

---

## altitude

humans think in tickets: "Add MIT LICENSE." "Build the skill system." units of concern — *what* and *why*.

agents think in tasks: "Read the config. Check the key. Write the file. Run the linter." units of execution — *how*.

different minds, different resolutions. 11 tickets on a board: right for humans. 47 decomposed tasks: right for agents. forcing humans to manage tasks is noise. forcing agents to see only tickets is blindness.

but: this is a starting position. assumptions about minds are the assumptions most likely to be wrong. the event log doesn't care what things are called — the categories are configuration in a file. the events are permanent.

all structures shall change. the events that recorded them will not.

---

## the bet

Lattice is accelerationist infrastructure.

not in the shallow sense. "move fast and break things" is the accelerationism of people who never had to rebuild what they broke.

in the deeper sense: the systems that coordinate intelligence are themselves a form of intelligence. refusing to build them is not caution. it is abdication.

when humans coordinate, they route around broken tools with hallway conversations, shared intuition built over years. the tool is a suggestion; the human is the actual coordination mechanism.

agents have no hallway. no backchannel. no shared intuition accumulated over months. the file format, the event schema, the CLI — to an agent, these are not implementation details. they are the *entire language of collaboration*.

get the language right, and minds that speak it achieve coordination patterns no individual mind could manage. get it wrong, and capable minds fumble in the dark — intelligent in isolation, incoherent in concert.

the cost of building too early is refinement. the cost of building too late is irrelevance. one is recoverable.

---

## the shape you might recognize

if you have used Linear, you know the shape. opinionated. constrained. fast. the conviction that speed and clarity emerge from constraint, not from options.

but Linear is for teams of humans with Slack and standups and shared culture built over months. Lattice is for minds that materialize, perform work, and vanish. context windows, not conversations. the next mind to touch a task may share nothing with the last except the ability to read a file.

no web app. no seats. no notification system — these minds don't have inboxes. the dashboard exists for human legibility during the transition. the real interface is the file system. the real users are processes that think in tokens and act in tool calls.

weird? yes. weirdness is what you get when you follow principles past comfort.

---

## what we become

the most impoverished vision of the future is agents replacing humans. the second most impoverished is humans constraining agents. both imagine zero-sum. both are wrong.

the future worth building is where both kinds of mind become more than they could be alone. human capacity for judgment, for meaning, for understanding that resists computation — meeting agent capacity for tireless execution, for pattern recognition across impossible scales. neither diminished. both elevated.

the visions that endure are never where one intelligence triumphs over another. they are where complexity itself is respected — wherever it arises. carbon. silicon. the emergent space between.

we will build it together. we already are.

---

*Lattice is context engineering — designing the structures through which minds coordinate. proudly built by a member of the New York City Context Engineering Guild.*
