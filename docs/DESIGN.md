# DAG Skill Design

This document records the stable design and rationale of a project-independent, host-neutral Agent Skill for advancing an approved Spec-and-Ticket dependency DAG. [`SKILL.md`](../skill/dag/SKILL.md) remains the normative step-by-step runtime contract, while the Target Project's live contracts and evidence remain authoritative.

## Artifact and scope

The copyable artifact is [`skill/dag/`](../skill/dag/):

- [`SKILL.md`](../skill/dag/SKILL.md) is the sole normative DAG runtime source;
- [`agents/openai.yaml`](../skill/dag/agents/openai.yaml) provides optional interface metadata;
- [`scripts/install_dependencies.py`](../skill/dag/scripts/install_dependencies.py) performs separately authorized setup of the pinned supporting Skills.

The project [`README.md`](../README.md) is the human-facing entry point. [`CONTEXT.md`](../CONTEXT.md) preserves shared language. Runtime state lives in the Target Project's tracker or repository evidence, giving each run one recovery authority.

The Skill consumes an Approved DAG whose Spec, Tickets, and dependency semantics already exist. Spec and Ticket content follows the Target Project's Spec/Ticket Authoring Process. Local Markdown, GitHub Issues, and other carriers are represented through the Target Project's Tracker Contract.

## Invocation and host contract

The frontmatter exposes `name: dag` and a focused trigger for requests to execute, advance, continue, or resume an approved multi-Ticket DAG.

A run resolves four inputs before acting: Target Project, Approved Spec, in-scope Tickets and dependency carrier, and DAG Run Authorization. Ambiguity keeps the Runnable Frontier empty until one precise clarification resolves it.

A supported Agent Host can:

- dispatch fresh role-isolated Agent contexts;
- establish write-capable Execution Agent and read-only Review Agent boundaries;
- expose liveness and terminal states;
- access the Target Project's tracker, repository, and verification tools;
- activate the model-invoked supporting Skills through its native mechanism.

Tickets may be scheduled serially. Nested concurrency declared by a validated supporting Skill remains an entry capability. Host-specific paths, invocation syntax, policy fields, and APIs remain setup details.

## Dependency and execution model

The Runtime Skill Bundle contains complete `code-review`, `tdd`, and `codebase-design` directories pinned to `mattpocock/skills` revision `5b15a47f2d7150f545fbcacbfe381787fc0230dc`. The same pinned support package includes the user-invoked `setup-matt-pocock-skills` helper for Target Projects that need its shared configuration. The Python 3.12+ installer places all four directories under an explicit host Skills root. Fixed tree digests enable offline validation of current local content; missing content is fetched with config-isolated bounded Git, conflict preflight, exclusive path creation, and final whole-bundle verification.

Before Ticket work, the Coordinator Agent verifies every runtime member's resolved identity, referenced resources, immutable content identity, activation path, and live contract. The Execution Agent must be able to execute `tdd` at the Ticket's public test seams and obtain fresh independent Standards and Spec reports for a non-empty committed Ticket diff through `code-review`, directly or through a Coordinator Agent relay that returns the reports for pre-handoff closure. The host must also support direct dispatch of fresh read-only Review Agents for a zero-delivery current-state review; the pinned diff-based `code-review` remains assigned to non-empty Ticket deltas. The Target Project's live review prerequisites determine whether its setup helper is needed. Dependency installation and user-invoked setup use separate authorization. Ticket scheduling begins after the runtime path and project prerequisites pass the entry gate.

## Authority and evidence

DAG Run Authorization covers locally auditable coordination:

- local Ticket claims, tracker evidence, and transitions;
- Agent dispatch;
- a run-scoped DAG Integration Branch and the Coordinator Agent's isolated worktree;
- one ticket-scoped branch and worktree per active Ticket;
- implementation, verification, and safe local commits;
- project-governed candidate alignment with the pre-alignment identity retained as Recovery Evidence;
- semantics-preserving local Ticket repairs and DAG Revisions through the Target Project's governed process;
- local integration, acceptance evidence, and successor unlocking.

One run-scoped Remote Checkpoint Authorization covers fast-forward publication of the selected DAG Integration Branch after each DAG Milestone and exact remote-ref readback. Separate authorization continues to govern remote tracker writes, other publication, deployment, external writes, state-changing remote CI, destructive Git, product-semantic or acceptance changes, and gate weakening.

Normative Authority consists of current user scope, applicable project instructions, the Approved Spec, approved Tickets, and the Tracker Contract. State Evidence consists of live tracker, Git, code, tests, and formal-review artifacts. Chat and Agent reports point to evidence for the Coordinator Agent to verify.

An approval boundary is effective only when it traces to Normative Authority. Agent-authored State Evidence may preserve or cite that boundary, but cannot narrow or expire existing DAG Run Authorization. Revision and recovery counts therefore remain audit facts rather than permission gates.

## Git integration topology

A Git-backed run creates or resumes one DAG Integration Branch from the Approved Baseline and assigns the Coordinator Agent an isolated worktree. Its tip advances only to locally verified DAG Milestones. The user's existing checkout remains outside DAG writes.

Each active Ticket receives one branch and isolated worktree from the current accepted DAG Milestone. When a required Remote Checkpoint is pending, a graph-independent Ticket may start from the last checkpointed accepted tip if its contract does not consume the pending milestone. Graph-independent Ticket Workspaces may run concurrently.

```text
Approved Baseline
`-- DAG Integration Branch and Coordinator Agent worktree
    |-- Ticket A branch and worktree
    |-- Ticket B branch and worktree
    `-- Ticket C branch and worktree
```

Worker review and any post-handoff Review Sufficiency work bind to immutable Ticket candidates and may proceed concurrently across graph-independent Tickets. After the Coordinator Agent adjudicates the handed-off candidate, the serialized integration lane covers alignment, review and adjudication of any alignment delta, promotion, and Remote Checkpoint. Every alignment-delta finding receives a supported disposition before promotion; a blocker routes to Formal Rework, DAG Revision, or its authority condition after preserving the candidate and releasing the lane. The current DAG tip becomes the Review Fixed Point and the aligned candidate tip becomes the Final Artifact Identity. An alignment is byte-preserving only when it replays the reviewed Ticket delta unchanged onto already accepted bytes without conflict resolution or a changed review surface.

Promotion is fast-forward-only and advances the DAG Integration Branch without unreviewed delivery changes. The accepted tip becomes a DAG Milestone. A configured writable remote adds an authorized Remote Checkpoint: publish the selected DAG branch with an ordinary fast-forward push, reread the remote ref, and require exact identity before accepting that milestone and unlocking dependent Tickets. Repository-backed acceptance evidence is included in that milestone whenever the Tracker Contract permits. When the Accepted transition must follow remote readback and creates another DAG-branch commit, that Evidence-only finalization commit receives one final checkpoint without repeating delivery gates or review; matching refs are its terminal evidence. A pending checkpoint holds the integration lane while graph-independent execution can continue from the last checkpointed accepted tip.

## Entry baseline recovery

The entry gate establishes a trustworthy starting state without conflating host variance with product failure. The Coordinator Agent classifies every failed entry check:

| Classification | Coordinator Agent action |
| --- | --- |
| Host environment variance | Prove the host-global cause, establish a project-governed run environment, and rerun the unchanged semantic gate |
| Target baseline defect | Append the smallest semantics-preserving prerequisite repair Ticket through the Target Project's process |
| Graph contract defect | Repair the affected Ticket, seam, or dependency through DAG Revision |
| Authority or semantic boundary | Record affected nodes and closing condition, continue independent work, and obtain user authorization |
| Unresolved cause | Keep affected nodes unclaimed while gathering evidence and advancing independent branches |

A normalized run environment may remove host-global configuration, permission, cache, or tool-placement variance while preserving dependencies, acceptance, and every gate. An entry failure remains actionable by the Coordinator Agent while an authorized correction, repair, revision, or independent Runnable branch exists.

## Graph and recovery model

Each executable node is one Ticket with:

- authoritative identity and one delivery objective;
- scope and dependency inputs;
- observable downstream outputs;
- acceptance and verification requirements, including one or more pre-agreed public test seams;
- current state, ownership, and blockers.

Before claim, the Coordinator Agent derives a Ticket Execution Contract from the approved Ticket and its accepted direct inputs. The minimum contract names the owned acceptance obligation, consumed accepted inputs or an evidenced empty set, delivered output, every acceptance requirement's public probe and observable result, scope boundary, and gates. Equivalence classes, state transitions, and forbidden outcomes are included when live authority defines them or acceptance execution needs them; an inapplicable optional field records `N/A` with its source or rationale. This is an executable projection of approved meaning rather than a new source of product semantics. A missing or contradictory required field holds the Ticket before claim and routes through the Target Project's Spec/Ticket Authoring Process, DAG Revision, or the required authority decision.

Each dependency edge is `prerequisite -> dependent` and represents consumption of an accepted predecessor output. Ordering preferences, shared files, ownership, phases, and external blockers remain scheduling facts.

The Whole-Graph Validity Gate requires unique and complete nodes, defensible edges, acyclicity, hard-dependency coverage, and acceptance state aligned with live evidence. Superseded Tickets remain as provenance while replacement nodes form the effective graph.

Recovery Evidence stays in the Target Project's tracker or repository and captures:

- bundle, Ticket, Ticket Attempt identity, ownership, single implementation-continuation state and closing condition, and Formal Rework state;
- Coordinator Agent, Execution Agent, and Review Agent profiles, checkpoints, liveness, and milestones;
- Invocation Corrections, Operational Recovery causes and corrections, blockers, and closing conditions;
- Ticket Base, Ticket Workspace, Review Fixed Point, Final Artifact Identity, findings, and dispositions;
- DAG Integration Branch and milestone reachability, gate commands and outcomes;
- selected remote branch, last verified Remote Checkpoint, and any pending checkpoint cause;
- DAG Revisions, violated obligations, causal mechanisms, owning seams, prior effective shapes, gate outcomes, Structural Progress, acceptance evidence, and Ticket Lineage.

A compact Run Receipt indexes the current DAG Milestone, last recorded and pending remote checkpoints, Runnable Frontier, active Ticket identities and workspaces, implementation-continuation state, Agent checkpoints, pending gates or reviews, graph identity, and live closing conditions. It points to authoritative Recovery Evidence instead of copying raw reports or long lineage. A repository-backed receipt records the preceding verified checkpoint and the closing condition for its own publication; matching refs complete that condition and serve as the receipt's terminal checkpoint evidence. Milestone transitions update the receipt; unchanged monitoring does not.

A cross-task handoff completes when the receiving Coordinator Agent rereads the live project, reconstructs this evidence, and recomputes the frontier.

Matching local and remote DAG refs prove a completed Remote Checkpoint. A known local-ahead milestone resumes at checkpoint publication before acceptance, dependent successor unlock, or another promotion. Graph-independent work may start or continue from the last checkpointed accepted tip. An unknown remote-only commit or divergence resumes through cause-scoped recovery with both refs preserved as evidence.

## Roles, profiles, and scheduling

DAG coordination has exactly three Agent role types. One Coordinator Agent owns the run; graph-independent Tickets may use multiple Execution Agent instances, and independent review axes or targeted scopes may use multiple Review Agent instances. Ticket Worker Protocol and Worker Self-Check are Execution Agent workflows, while Standards and Spec are Review Agent axes.

| Role | Responsibility | Selection |
| --- | --- | --- |
| Coordinator Agent | Live reconciliation, entry recovery, graph validation, scheduling, adjudication, integration, revision, and final acceptance | Strong useful graph-wide reasoning and context capacity |
| Execution Agent | One Ticket through causal TDD or baseline-satisfaction proof, final gates, complete pre-handoff review coverage, and bounded repair to an Implementation Handoff or Blocked Handoff | Repository, coding, tool, context, complexity, and risk fit |
| Review Agent | Independent Standards, Spec, or targeted review of one fixed artifact | Fresh context matched to review scope and risk |

Exact user or Target Project model, Agent, and reasoning-effort requirements are hard constraints. Otherwise the Coordinator Agent chooses from live capability and risk. Runtime records contain exposed metadata and mark other fields unknown. A proposed substitution for an exact requirement requires user authorization.

Scheduling follows three rules:

1. prioritize handed-off candidates without idling graph-independent implementation capacity;
2. select the largest safe frontier subset whose Agent demand fits current capacity;
3. use tracker priority, downstream-unlock or critical-path value, then stable Ticket identity as tie-breakers.

Parallel implementation combines graph independence with one Ticket Workspace per write-capable Execution Agent. Read-only review of different fixed candidates may run concurrently. Candidate alignment, promotion, and Remote Checkpoint use one serialized integration lane; review or gates join that lane only when alignment creates a relevant delta.

Every directly dispatched Agent receives a bounded progress checkpoint. An evidence-bearing milestone that reduces or clarifies remaining work, an evidenced blocker, or a terminal result demonstrates progress. An invocation that never reached its target receives correction at the same checkpoint. The same cause repeating after a corrected recovery without progress becomes an Operational Blocker.

Continuous Scheduling repeats dispatch, bounded waiting, evidence reconciliation, Ticket advancement, persistence, and frontier recomputation until Complete or Stalled. An empty frontier remains active while observable Agents run or the Coordinator Agent has an authorized recovery or graph transition.

## Ticket delivery rationale

A Ticket Attempt is the stable recovery identity for one implementation-to-integration cycle. It keeps Coordinator-directed continuation, independent review, repair, alignment, and operational recovery attached to the same evidence lineage. Only a post-handoff Formal Rework opens the second Attempt.

Each initial or Formal Rework Execution Agent dispatch is finite. It uses TDD to observe applicable causal RED caused by missing target behavior and GREEN caused by implementing that behavior, runs final gates, freezes a Review Candidate, and obtains one complete read-only review. An initially GREEN probe is refined to expose missing behavior, routed as a contract blocker, or—when the complete contract appears to exist on the Ticket Base—checked through final gates and direct current-state Standards and Spec review by fresh read-only Review Agents. This zero-delivery path uses the fixed current artifact and contract surface; the diff-based `code-review` covers non-empty Ticket deltas. A bounded missing obligation returns to causal TDD, while complete satisfaction yields a zero-delta Handoff. With no credible in-scope blocker the Agent returns an Implementation Handoff. With repairable blockers it performs one TDD repair phase, reruns affected final gates, freezes the Final Candidate, and ends at one read-only Targeted Closure Review: PASS returns an Implementation Handoff and FAIL returns a Blocked Handoff. Graph-changing, external, or unresolved blockers also return a Blocked Handoff. Either terminal result returns control to the Coordinator Agent.

The Coordinator Agent verifies either Handoff against live commits and evidence. An in-scope repairable Blocked Handoff may receive one Coordinator-directed continuation within the same Attempt only after a new evidence-bearing milestone and a concrete closing condition; its consumption, source candidate, and closing condition are persisted before redispatch. The fresh Execution Agent resumes the same Ticket Workspace from the latest trusted candidate, uses TDD, reruns applicable gates, and reuses still-current review for unchanged scope. A bounded repair receives Targeted Closure Review, while incomplete coverage receives complete Worker review; either review is terminal for the continuation. If it does not clear the handoff gate, the Coordinator Agent persists the unresolved acceptance, failed repair shape, latest candidate, and recovery condition, then routes the Ticket to recovery, a structurally valid DAG Revision, blocker suspension, rejection, or deferral. For an Implementation Handoff, the Review Sufficiency Gate preserves independence without routinely repeating equivalent work: adopt complete current Worker evidence, add Targeted Formal Review when one bounded request can close the remaining uncertainty, or request complete fresh review when coverage cannot be established.

## Change impact and evidence reuse

Delivery-affecting Changes include product, test, dependency, generated-delivery, required-gate, and acceptance-bearing documentation changes. They invalidate the affected tests, gates, and review surface. Evidence-only Changes record tracker state, identities, gate results, review summaries, dispositions, or remote readback without changing accepted delivery behavior. After the Coordinator Agent verifies that classification, they require tracker, format, secret, diff, graph, and other directly applicable evidence checks rather than recursive delivery gates or full review.

Review and gate evidence bind to a fixed delivery candidate, relevant inputs, gate definitions, execution context, and verified scope. An Evidence-only descendant or byte-preserving alignment retains that evidence when the Coordinator Agent proves these bindings and the reviewed delivery surface remain current. Any Delivery-affecting or review-relevant delta reruns affected final gates and reapplies Review Sufficiency before promotion. This separates durable coordination receipts from delivery validity without adding a scheduler database or a second tracker.

## Recovery and revision rationale

Operational handling follows the evidenced cause so infrastructure failure does not consume implementation rework. An invocation correction resumes an action that never started; a corrected operational failure receives one cause-scoped rerun; repetition without a new milestone becomes an Operational Blocker. Verified terminal or superseded writers and isolated write boundaries protect every redispatch.

One Formal Rework after the Implementation Handoff gate bounds repeated post-handoff implementation cycles. The second Ticket Attempt therefore has one clear owner and one clear stopping point.

DAG Revision is bounded by Structural Progress rather than a lineage-level count. A fixed count can stop a genuinely new structural remedy, while a renamed retry can consume another identity without changing the failed work. A newly discovered public test seam updates the Ticket contract, while diff size informs review scoping; DAG Revision follows when the evidence reveals distinct acceptance ownership, a missing prerequisite, an owning-seam defect, or an invalid dependency. The Revision Progress Gate records the violated acceptance obligation, observable seam, causal mechanism, owning seam, affected dependency or output, and prior effective shapes. A candidate proceeds only when its structural difference addresses that evidence and preserves approved semantics, gates, acyclicity, and lineage.

The Coordinator Agent selects the smallest complete revision shape. One cohesive invariant, cause, and owning seam remain one replacement Ticket. Multiple results form a replacement subgraph only when every parent obligation has exactly one owning child and every child has a distinct acceptance responsibility, a public seam, and Independent Acceptance after its hard predecessors are accepted. A child without a mapped parent obligation owns a newly evidenced prerequisite output consumed by a named successor; its consumer may retain the complete mapped parent obligation. Combined behavior receives a convergence Ticket only when that combination adds a separate public contract. These constraints make acceptance ownership, rather than file layout or process phase, determine graph structure.

An Equivalent Revision matches a failed ancestor's effective objective, acceptance ownership, hard dependencies, and owning seam, so it cannot establish Structural Progress. Comparing every ancestor prevents alternating between previously failed shapes. Once an unresolved obligation is independently atomic and no consumed prerequisite, owning-seam change, dependency correction, or supported disposition remains, the lineage records a blocker and lets the terminal gate decide. This stops scheduler-generated retry and split loops while allowing genuinely new evidence to support a new structural response.

Late findings invalidate the affected acceptance lineage and preserve contradicted candidates as evidence. Independent branches continue, while the affected subgraph resumes through remaining Formal Rework or a semantics-preserving replacement lineage.

## Terminal-outcome rationale

Continuous Scheduling ends only when live evidence proves one of two symmetric outcomes: every effective Ticket and the Whole-DAG Acceptance Gate establish Complete, or unfinished work has no running Agent, Runnable node, authorized recovery, or DAG Revision that passes the Revision Progress Gate and therefore establishes Stalled. The exact terminal evidence is defined in [`SKILL.md`](../skill/dag/SKILL.md) and summarized for users in [`README.md`](../README.md).

## Deliverable acceptance

The project is ready when the copyable artifact validates as an Agent Skill, the runtime contract and project guide agree, the three-Skill Runtime Bundle and conditional project setup contract are explicit, the four-directory support package verifies against its pinned identities, and realistic incident replays preserve host neutrality, minimum-complete claim-time execution contracts, causal TDD and baseline-satisfaction routing, persisted continuation bounds, finite Execution Agent dispatch, read-only review, evidence reuse, scoped checkpoint blocking, alignment-delta adjudication, Coordinator Agent authority, isolated Ticket work, serialized promotion, cause-scoped recovery, bounded Formal Rework, progress-based DAG Revision, and whole-DAG acceptance.
