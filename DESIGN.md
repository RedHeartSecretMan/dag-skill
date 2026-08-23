# DAG Skill Design

This document records the stable design of a project-independent, host-neutral Agent Skill for advancing an approved Spec-and-Ticket dependency DAG. The Target Project's live contracts and evidence remain authoritative.

## Artifact and scope

The copyable artifact is `skill/dag/`:

- `SKILL.md` is the sole normative DAG runtime source;
- `agents/openai.yaml` provides optional interface metadata;
- `scripts/install_dependencies.py` performs separately authorized setup of the Required Skill Bundle.

The Chinese `README.md` is the human-facing guide. `CONTEXT.md` and this document preserve shared language and design evidence. Runtime coordination state lives in the Target Project's existing tracker or repository evidence, giving the project one recovery authority; the artifact itself consists of instructions, interface metadata, and dependency setup.

The Skill consumes an Approved DAG whose Spec, Tickets, and dependency semantics are already approved. Target Project authoring capabilities create or revise Spec and Ticket content; isolated single-Ticket work goes directly to its implementation capability. Local Markdown, GitHub Issues, and other carriers are represented through the Target Project's Tracker Contract.

This standalone repository is the implementation home. Historical bidevs, A-share research, vLLM E2E Report, and other repositories contribute engineering experience.

## Invocation and host contract

The open Agent Skills frontmatter exposes `name: dag` and a focused description for requests to execute, advance, continue, or resume an approved multi-Ticket DAG. Host and setup requirements stay in the runtime entry steps so clients using the common frontmatter subset can load the same artifact.

A run resolves four inputs before acting: Target Project, Approved Spec, in-scope Tickets and dependency carrier, and DAG Run Authorization. Ambiguity keeps the Runnable Frontier empty until one precise clarification resolves it.

A supported Agent Host can:

- activate named Skills;
- dispatch fresh role-isolated Agent contexts;
- establish write-capable Execution and read-only Review boundaries;
- expose liveness and terminal states;
- access the Target Project's tracker, repository, and verification tools.

Parallelism is optional; serial scheduling preserves the same contract. Fresh context, role independence, and observable terminal state are capability gates. Host-specific paths, invocation syntax, policy fields, and APIs remain setup details.

## Required Skill Bundle

The execution profile uses complete directories named `implement`, `code-review`, `tdd`, and `codebase-design`, pinned to `mattpocock/skills` revision `5b15a47f2d7150f545fbcacbfe381787fc0230dc`. The Python 3.12+ setup helper reads each directory from the upstream `skills/engineering/` grouping and installs it directly under the explicit host Skills root. Its config-isolated and bounded Git context, empty hook and template paths, conflict preflight, exclusive target reservation, content verification, and inspection-safe failure preservation keep setup scoped and recoverable.

Before Ticket work, the Coordinator verifies every member's unique resolved identity or location, referenced resources, immutable content identity, activation, and live contract. A valid bundle opens the Ticket frontier. A pending bundle keeps Ticket budgets untouched and reports the exact setup action.

Dependency installation uses separate user authorization and an explicit Skills root. After setup, the Coordinator rereads the complete host catalog and validates all four members again. DAG-Native Fallback applies to a validated, present Skill whose contract is inapplicable to the current host or Target Project; the bundle itself remains the common prerequisite.

## Authority and evidence

DAG Run Authorization covers locally auditable coordination:

- local Ticket claims and tracker updates;
- Agent dispatch;
- ticket-scoped candidate branches or worktrees;
- implementation, verification, and safe local commits;
- local acceptance evidence and successor unlocking.

Separate authorization covers remote tracker writes, publication, deployment, external writes, state-changing remote CI, destructive Git, product-semantic or acceptance changes, and gate weakening.

Normative Authority consists of current user scope, applicable project instructions, the Approved Spec, approved Tickets, and the Tracker Contract. State Evidence consists of live tracker, Git, code, tests, and formal-review artifacts. Chat and Agent reports point to evidence for the Coordinator to verify.

The Coordinator owns DAG and tracker transitions, integration, finding dispositions, rework and revision decisions, Ticket acceptance, and final acceptance. Execution and Review Agents own their scoped work and return evidence.

## Graph model

Each executable node is one Ticket with:

- authoritative identity and one delivery objective;
- scope and dependency inputs;
- observable downstream outputs;
- acceptance and verification requirements, including any applicable pre-agreed public test seam;
- current state, ownership, and blockers.

Each dependency edge is `prerequisite -> dependent` and represents consumption of an accepted predecessor output. Ordering preferences, shared files, ownership, implementation phases, and external blockers remain scheduling facts.

The Whole-Graph Validity Gate requires unique and complete nodes, defensible edges, acyclicity, hard-dependency coverage, and acceptance state aligned with live evidence. Superseded Tickets remain as provenance while their approved replacements form the effective graph.

A missing applicable pre-agreed public test seam holds the node before claim with all Ticket budgets unchanged. The Target Project's authoring capability proposes the Ticket repair, and acceptance or product-semantic changes retain explicit user authorization.

The Runnable Frontier contains Tickets with open acceptance state, accepted hard predecessors, cleared blockers, current claim and persistence authority, a verified Execution Profile, and a safe write boundary.

Recovery Evidence stays in the Target Project's tracker or repository and captures:

- bundle, Ticket, Ticket Attempt identity, ownership, and budget state;
- Coordinator and Agent profiles, checkpoints, liveness, and milestones;
- Review Fixed Point, Final Artifact Identity, review findings, and dispositions;
- integration baseline and reachability, gate commands and outcomes;
- acceptance evidence, blocker closing conditions, and Ticket Lineage.

A cross-task handoff completes when the receiving Coordinator rereads the live project, reconstructs this evidence, and recomputes the frontier.

Continuation reconciles each prior dispatch and trusted milestone. A completed milestone resumes at the next stage. An unobservable dispatch first receives a quiescent or isolated write boundary and a terminal or superseded identity, then consumes the current Ticket Attempt's Operational Retry immediately before corrected action. Exhausted retry routes to the Coordinator's graph decision. Uncertain write liveness keeps the current Attempt, ownership, and budgets in place and blocks redispatch.

## Roles, profiles, and scheduling

| Role | Responsibility | Selection |
| --- | --- | --- |
| Coordinator | Live reconciliation, graph validation, scheduling, adjudication, integration, revision, and final acceptance | Strong useful graph-wide reasoning and context capacity |
| Execution Agent | One Ticket through Implementation Handoff | Repository, coding, tool, context, complexity, and risk fit |
| Review Agent | Fresh formal review when existing evidence needs reinforcement | Independent context matched to review scope and risk |
| Standards / Spec Reviewer | DAG-native review axes when `code-review` is inapplicable | Independent context with the corresponding capability |

Exact user or Target Project model, Agent, and reasoning-effort requirements are hard constraints. Otherwise the Coordinator chooses from live capability and risk. Runtime records contain the metadata the host exposes and mark other fields unknown. A proposed substitution for an exact requirement requires user authorization; a post-dispatch mismatch becomes an Operational Failure.

Scheduling follows three rules:

1. finish review, integration, and acceptance already in progress before opening more implementation work;
2. select the largest safe frontier subset whose direct and nested Agent demand fits current capacity;
3. use tracker priority, downstream-unlock or critical-path value, then stable Ticket identity as tie-breakers.

Parallel implementation combines graph independence with Target Project-permitted workspace isolation and an explicit integration boundary. Each workspace has one write-capable Execution Agent. Independent read-only reviews may run concurrently.

Every directly dispatched Agent receives a bounded progress checkpoint. New evidence-bearing milestones that reduce or clarify remaining work, evidenced blockers, and terminal results demonstrate progress; repeated or non-advancing milestones produce an Operational Failure. A write-capable redispatch follows verified terminal or superseded state plus a quiescent or isolated boundary for the prior writer, then consumes an available Operational Retry immediately before corrected action. Exhausted retry enters the Coordinator's graph decision.

Continuous Scheduling repeats dispatch, bounded waiting, evidence reconciliation, Ticket advancement, persistence, and frontier recomputation until Complete or Stalled. An empty frontier remains active while observable Agents are running.

## Per-Ticket flow

### 1. Fixed point and implementation

Immediately before claim, the Coordinator rereads the Ticket, dependencies, blockers, repository, tracker, and bundle identities. The claim opens the first Ticket Attempt, records an immutable Review Fixed Point, and dispatches one fresh Execution Agent in a candidate workspace that preserves the Authoritative Integration Baseline. Formal Rework is the only transition that opens a second Attempt; continuation, follow-up, review, integration, and Operational Retry retain the current Attempt identity and budget. An evidenced external blocker suspends a started Attempt with its fixed point, ownership, milestones, and budgets intact; clearing its closing condition resumes the same Attempt after live reconciliation. A live or uncertain prior write boundary also holds that identity and budget until its safety condition closes.

An applicable `implement` dispatch receives the fixed point, Spec, Ticket, standards, tracker context, scope, authorization, and any applicable pre-agreed public test seam. Its nested `tdd`, conditional `codebase-design`, and `code-review` uses resolve from the same bundle. The nested Standards and Spec review forms Implementation-Side Review evidence.

When that nested-review or candidate-commit contract is inapplicable to the live host or project, the Coordinator discloses DAG-Native Fallback and dispatches a fresh Execution Agent under the Target Project's contracts. This path explicitly uses `tdd` at the agreed public seam when feasible and `codebase-design` when the seam shape requires design. Both paths run applicable gates and return the same Implementation Handoff.

### 2. Implementation Handoff

A valid handoff carries Ticket identity and scope, changed files and candidate commit, exact gate commands and outcomes, classified failures, review artifacts and reviewed identity, post-review changes, Agent profiles, risks, and blockers.

The Coordinator checks the live candidate, public delivery seam, verification, reviewer independence, artifact identity, and generated or lockfile changes. The handoff becomes reviewable after implementation gates are green or covered by the exact Target Project-permitted exception with an owner and closing condition.

Before Formal Review, evidence-only failures consume the current Attempt's Operational Retry, a Coordinator-accepted in-scope implementation defect uses the remaining Formal Rework, an external blocker suspends with a closing condition, and a graph-changing issue enters DAG Revision. An in-scope defect with exhausted Formal Rework also enters DAG Revision. When conditions coexist, a live-confirmed substantive defect takes the Formal Rework route; evidence completion uses Operational Retry only while the candidate bytes stay fixed. Each Ticket Attempt has one Operational Retry shared across implementation, review, and integration. Formal Rework opens the second Attempt with one fresh Operational Retry; continuation and role follow-up preserve the current budget. Implementation and review retries redispatch their roles, while the Coordinator owns the single corrected integration retry. Exhausting that retry requires a persisted graph decision: split, add a prerequisite, reorder, reject, defer, or suspend on an evidenced external blocker.

### 3. Formal Review evidence

The Coordinator freezes the Final Artifact Identity and adopts Implementation-Side Review evidence when both raw axes are present, reviewers are independent, profiles and contexts are valid, both axes cover the final identity, the evidence supports finding dispositions, and project contract and risk permit reuse.

Evidence requiring reinforcement triggers a fresh Review Agent against the same fixed point and final identity. The applicable `code-review` Skill returns Standards and Spec results side by side; DAG-Native Fallback dispatches fresh independent Standards and Spec Reviewers with equivalent scope. Review reports include profiles, artifact identities, and raw findings. Timeouts remain missing evidence, and all dispatched reviewers reach terminal or superseded state before adjudication.

Any review-relevant byte, identity, or history change establishes a new Final Artifact Identity and reapplies the Review Sufficiency Gate. Verified topology-only equivalence may retain evidence outside both review scopes.

### 4. Adjudication, integration, and acceptance

The Coordinator assigns every finding one supported disposition: blocking, graph-changing, advisory, false positive, or unresolved. Integration opens when mandatory requirements are satisfied and all findings have supported non-blocking dispositions.

The exact reviewed candidate then enters the Authoritative Integration Baseline. The Coordinator proves artifact representation or reachability and runs affected, integration, and delivered-public-seam gates on the integrated bytes. A byte-changing integration conflict consumes available Formal Rework, opens the second Ticket Attempt from the current baseline with a new Review Fixed Point, and repeats the complete flow; exhausted rework or scope drift enters DAG Revision.

Ticket acceptance requires agreement among integrated identity, verification, Formal Review, dispositions, scope, baseline, and tracker evidence. Persisted and reread acceptance unlocks successors. An external resolved state additionally requires the promised reference to contain the artifact and the applicable remote-write authorization.

## Bounded failure and graph revision

Each Ticket has one Formal Rework for a Coordinator-accepted in-scope blocking handoff, review, or integration finding. It opens the second Ticket Attempt from the current baseline with a new Review Fixed Point and one Operational Retry; the reworked artifact repeats the complete Ticket flow. Self-correction before handoff, duplicate findings, false positives, and Operational Retry remain outside this budget.

A new independent objective, acceptance seam, or diff beyond bounded review moves directly to DAG Revision. Blocking findings after Formal Rework lead the Coordinator to split the Ticket, add a prerequisite, reorder work, reject or defer scope, or record an external blocker.

The Target Project's authoring capability creates revised Ticket content. The Coordinator appends an approved replacement subgraph, retains displaced Tickets as Superseded, and revalidates the whole graph. One semantics-preserving revision proceeds automatically per original Ticket Lineage after its rationale and budget are recorded; later revisions in that lineage use explicit user authorization.

A valid late finding or Whole-DAG failure freezes dispatch, integration, and acceptance for the consuming subgraph. Active affected Agents reach a verified terminal or superseded state with quiescent write boundaries, their candidates remain unaccepted evidence, and authorized acceptance invalidation covers the contradicted Ticket plus every accepted consuming descendant. The affected subgraph resumes through remaining Formal Rework or an authoring-produced remediation lineage.

## Terminal outcomes

Independent runnable branches continue while another branch is blocked.

**Stalled** means effective Tickets remain unfinished, running Agent count is zero, and the Runnable Frontier is empty; every stopped path has a live evidenced cause.

**Complete** means every effective Ticket is accepted and the Whole-DAG Acceptance Gate confirms Approved Spec coverage, baseline integration, dependency consumption, current artifact identities, graph-wide gates, resolved findings and blockers, and tracker/commit/lineage consistency.

Complete represents local acceptance. Publication uses separate authorization.

## Deliverable acceptance

The project is ready when the copyable artifact validates as an Agent Skill, the English runtime and Chinese guide agree, the pinned bundle and setup contract are explicit, and the workflow preserves host neutrality, Coordinator authority, independent review, bounded failure, same-final-bytes evidence, integration-before-acceptance, and whole-DAG acceptance.
