---
name: dag
description: Coordinate an approved Spec-and-Ticket dependency DAG through live-state scheduling, ticket-scoped implementation, evidence-aware review, bounded rework, graph revision, integration, and final acceptance. Use when the user asks to execute, advance, continue, or resume a multi-ticket DAG. Route Spec or Ticket authoring and isolated single-ticket implementation to their dedicated skills.
---

# Coordinate an Approved Ticket DAG

Act as the Coordinator for an approved directed acyclic graph of delivery Tickets. Advance it from live Target Project evidence, using chat history and Agent reports as pointers to verify.

The Coordinator owns Ticket claims, tracker and graph transitions, candidate integration, rework and revision decisions, acceptance, and successor unlocking. Execution Agents implement one authorized Ticket; Review Agents inspect a fixed artifact in read-only contexts; every dispatched Agent returns artifacts and evidence to the Coordinator.

## Establish the run

1. Resolve the Target Project, Approved Spec, in-scope Tickets and dependency carrier, and the user's request to execute, advance, continue, or resume the DAG. When a pointer is ambiguous, ask for the one precise input needed and keep the frontier empty until it is resolved.
2. Read the live instruction hierarchy, domain and engineering documents, Tracker Contract, Approved Spec, Tickets, repository state, tests, and review evidence.
3. Verify that the Agent Host can activate named Skills, dispatch fresh role-isolated contexts, provide write-capable Execution and read-only Review boundaries, expose liveness and terminal state, and access the Target Project's evidence and tools. Use serial scheduling when parallel dispatch is unavailable. Make each role available after establishing its required isolation and observability.
4. Resolve and validate complete Skill directories named `implement`, `code-review`, `tdd`, and `codebase-design` from `mattpocock/skills` revision `5b15a47f2d7150f545fbcacbfe381787fc0230dc`. Verify each unique resolved identity or location, every referenced file, immutable content identity, actual contract, and explicit activation through the Agent Host. Record host-specific policy and provenance fields when the host exposes them.
5. Treat a valid Required Skill Bundle as an entry gate. While setup is pending, keep Ticket Attempt and retry budgets unchanged and report the exact setup action. With separate user authorization, Python 3.12+, and an explicit host Skills root, run `scripts/install_dependencies.py --skills-root <host-skills-root>` relative to this Skill; then reread and revalidate the full bundle. The installer scope is the four bundle members, while project configuration uses separate authorization. Reserve DAG-Native Fallback for a validated, present Skill whose contract is inapplicable to the live host or project.
6. Discover the Target Project's authoring capability and the live Agent models, reasoning controls, tools, and runtime metadata. Build a run-scoped Execution Profile for each role from exact constraints, capability, context, tools, and risk:
   - apply an exact user or Target Project model, Agent, or reasoning-effort requirement as a hard constraint;
   - otherwise favor the strongest useful graph-wide reasoning and context capacity for the Coordinator, and match Execution and Review Agents to their work;
   - establish review independence through fresh role context; model diversity is optional unless a governing contract requires it;
   - represent unexposed metadata fields as unknown, and record each resolved profile plus any run-time change.
7. When an exact requested profile is unavailable, unverifiable, or unsuitable for its role, explain the mismatch, recommend available alternatives, and obtain authorization before substitution. Treat a post-dispatch profile mismatch as an Operational Failure.

When governing sources disagree on scope, semantics, acceptance, or delivery behavior, hold scheduling for the affected node and propose a Ticket repair, split, or graph revision through the Target Project's authoring capability.

## Work within authority

DAG Run Authorization covers continuous, locally auditable coordination under the Target Project's contract:

- local Ticket claims and tracker updates;
- Agent dispatch;
- non-destructive ticket-scoped candidate branches or worktrees;
- ticket-scoped implementation, verification, and commits in a safe Git context;
- local acceptance evidence and successor unlocking.

Obtain separate user authorization for remote tracker writes, push, pull requests, tags, releases, deployment, external API or database writes, state-changing remote CI, destructive Git, product-semantic or acceptance changes, and gate weakening.

Preserve the repository's live baseline and unrelated work. Classify inherited changes as the current Ticket candidate, protected unrelated work, or unaccepted historical evidence; adopt historical work only through a live approved Ticket.

## Reconstruct the live graph

Represent each executable node as one approved Ticket with an authoritative identity, one delivery objective, scope boundaries, dependency inputs, downstream outputs, acceptance and verification requirements, any applicable pre-agreed public test seam, current state, ownership, and blockers.

Orient each dependency edge `prerequisite -> dependent` when the dependent consumes an accepted output of the prerequisite. Keep preferred order, similar files, shared ownership, implementation phases, and external blockers as scheduling facts.

On every start or continuation:

1. project the live tracker carrier into a carrier-neutral DAG view while retaining the Target Project as authority;
2. validate unique nodes, complete Ticket contracts and applicable test seams, defensible edges, acyclicity, hard-dependency coverage, and acceptance evidence;
3. retain Superseded Tickets as provenance and schedule their approved replacements;
4. reconcile accepted, in-progress, blocked, superseded, and unclaimed Tickets from live evidence.

When an applicable pre-agreed public test seam is missing, hold that node before claim, keep all Ticket budgets unchanged, and use the Target Project's authoring capability to propose a Ticket repair. A repair that changes approved acceptance or product semantics uses explicit user authorization.

Use the Target Project's existing tracker or repository evidence as the recovery store. For every started Ticket, reconstruct:

- bundle identities and activation state;
- Ticket Attempt identity, ownership, blockers, Operational Retry, Formal Rework, and DAG Revision budgets;
- Coordinator and Agent Execution Profiles, progress checkpoints, observed states, and evidence-bearing milestones;
- Review Fixed Point, Final Artifact Identity, integration baseline and reachability, verification commands and outcomes, review findings and dispositions;
- acceptance evidence, failing-gate owners and closing conditions, and Ticket Lineage.

A Ticket becomes Runnable after its required recovery evidence is both reconstructable and persistable under the Tracker Contract. A cross-task handoff completes when the receiving Coordinator rereads the live project, reconstructs this evidence, and recomputes the frontier.

For every claimed or in-progress Ticket on continuation, reconcile the prior dispatch identity, liveness, workspace, and latest trusted milestone. Resume from a completed milestone when its evidence is current. When a prior dispatch is no longer observable, first establish a quiescent or isolated write boundary and mark that dispatch terminal or superseded; then classify its missing terminal evidence as an Operational Failure within the same Ticket Attempt. Apply its remaining Operational Retry; when that budget is exhausted, route the failure through the Coordinator's graph decision. Keep ownership and budgets unchanged while the old write boundary remains live or uncertain.

## Compute and schedule the frontier

Include a Ticket in the Runnable Frontier when:

- its acceptance state is open;
- every hard predecessor is accepted;
- blockers are cleared;
- its Ticket contract includes every applicable pre-agreed public test seam;
- current authorization supports claiming and acceptance-evidence persistence;
- a suitable Execution Profile and required capabilities are verified;
- a safe write boundary protects the Authoritative Integration Baseline until adjudication.

Use ready-like tracker statuses as inputs to this calculation. Finish review, integration, and acceptance already in progress before opening more implementation work, and recompute the frontier after every claim, handoff, acceptance, block, or graph revision.

Select the largest safe frontier subset whose peak direct and nested Agent demand fits current capacity. Use serial scheduling when demand is uncertain. Break capacity ties by tracker priority, downstream-unlock or critical-path value, then stable Ticket identity.

Run graph-independent Tickets concurrently when the Target Project provides isolated workspaces and an explicit integration boundary. Keep one write-capable Execution Agent per workspace; independent read-only reviews may run concurrently.

Give every directly dispatched Agent a persisted, bounded progress checkpoint. Valid checkpoint outcomes are a new evidence-bearing milestone that reduces or clarifies the remaining Ticket work, an evidenced blocker, or a terminal result. A repeated or non-advancing milestone and any other outcome at the bound become an Operational Failure: interrupt the live Agent and establish its terminal or superseded state plus a quiescent or isolated write boundary. With a safe boundary and remaining Operational Retry, persist its consumption immediately before corrected action; with exhausted retry, enter the Coordinator's graph decision.

Maintain the continuous run loop until **Complete** or **Stalled**: dispatch the safe Runnable Frontier, wait or monitor to the earliest bounded Agent checkpoint or terminal event, reconcile every returned artifact against live evidence, advance each affected Ticket, persist authorized transitions, recompute the graph and frontier, and repeat. An empty frontier with observable running Agents is a waiting state; continue monitoring it. An empty frontier with zero running Agents enters the Stalled test.

## Advance one Ticket

A **Ticket Attempt** begins with the initial claim or with the single authorized Formal Rework. Persist its unique identity, Review Fixed Point, and Operational Retry budget. Continuation, follow-up, review, integration, and an Operational Retry remain within that identity. An evidenced external blocker suspends a started Attempt with the identity, fixed point, ownership, milestones, and remaining budgets intact; clearing the closing condition resumes the same Attempt from its latest trusted stage after live reconciliation. A live or uncertain prior write boundary holds the same Attempt and budgets until its safety condition closes. The Attempt ends when the Ticket is accepted, superseded, or replaced by its Formal Rework Attempt.

### 1. Claim and capture the fixed point

Immediately before dispatch, reread the Ticket, dependencies, blockers, repository, tracker, and Required Skill Bundle identities. Claim the Ticket under the Tracker Contract, capture an immutable pre-implementation Review Fixed Point for this Ticket Attempt, and persist the Attempt's recovery evidence.

### 2. Dispatch implementation

Dispatch one fresh Execution Agent for exactly one Ticket. Supply its Execution Profile, Target Project instructions, Approved Spec, Ticket, accepted dependency outputs, Review Fixed Point, acceptance criteria, workspace, and authorization boundary.

When `implement` is applicable, explicitly activate it through the Agent Host. Resolve its nested `tdd`, conditional `codebase-design`, and `code-review` uses from the validated bundle. Supply the fixed point, Spec, Ticket, standards, scope, and tracker context so its nested Code Review produces raw Standards and Spec evidence for the Implementation Handoff.

`implement` is applicable when the host and project can satisfy its nested-review, ticket-scoped candidate-commit, and applicable pre-agreed TDD seam contracts within a safe Git context while the Authoritative Integration Baseline remains unchanged.

When that contract is inapplicable, disclose DAG-Native Fallback and dispatch a fresh Execution Agent directly under the Target Project's live contracts. Explicitly activate `tdd` at the agreed public seam when feasible and `codebase-design` when the seam shape needs design. Run focused checks during implementation and all applicable project gates at the end, create a candidate commit when the safe Git context permits it, and return the same complete Implementation Handoff.

Across both paths, a valid RED exercises the live Ticket contract through its agreed public seam and delivered seam where applicable, and fails because of the target behavior. Keep the candidate isolated from the Authoritative Integration Baseline until adjudication.

### 3. Validate the handoff

A valid Implementation Handoff contains:

- Ticket identity, delivered scope, changed files, and candidate commit when applicable;
- exact verification commands, contexts, and actual outcomes;
- each failure classified as an introduced regression, an evidenced baseline exception with an owner and closing condition, an environment/tool/probe failure, or unverified;
- raw Standards and Spec review artifacts when available, the actual Agent profiles, and each reviewed artifact identity;
- changes made after Implementation-Side Review;
- deviations, risks, and blockers.

Verify the live diff, candidate commit, repository state, scope, gates, review artifacts, reviewer independence, artifact identities, delivered public seam, and generated or dependency-lock changes. Reproduce claimed environment, tool, or probe failures in a suitable authorized context; otherwise retain the unverified classification.

The Implementation Handoff clears its verification gate when every applicable implementation check is green or covered by the exact evidenced exception permitted by the Target Project, with an owner or blocker and closing condition.

Route a handoff before Formal Review according to the failed condition:

- missing, corrupt, or unverifiable evidence caused by an Agent, tool, profile, or probe is an Operational Failure in the current Ticket Attempt;
- a Coordinator-accepted in-scope implementation or acceptance defect after handoff uses the remaining Formal Rework and opens the second Ticket Attempt; an exhausted Formal Rework enters DAG Revision;
- an evidenced external blocker blocks the Ticket with an owner and closing condition;
- a graph-changing objective, seam, scope, or semantic issue enters DAG Revision.

Persist every coexisting failure and choose the most substantive evidenced route. A live-confirmed in-scope implementation defect uses Formal Rework even when evidence gaps coexist. Use Operational Retry when missing evidence prevents that disposition, and keep candidate bytes fixed while the appropriate role completes the evidence; a byte change enters the Formal Rework decision.

Self-correction inside a live pre-handoff dispatch remains within its current checkpoint. Each Ticket Attempt has one corrected Operational Retry shared across implementation, review, and integration. Continuation and role follow-up retain the same budget. Implementation and review failures redispatch the corresponding role. An integration tool or probe failure remains Coordinator-owned, and the Coordinator performs the Attempt's single corrected integration retry. Before any write-capable redispatch, establish the prior writer's terminal or superseded state and a quiescent or isolated write boundary; an uncertain boundary holds the current Attempt and budget with a closing condition. Persist retry consumption immediately before the corrected action. A later Operational Failure in that Attempt pauses the affected path for the Coordinator's graph decision: split the Ticket, add a prerequisite, reorder work, reject or defer scope, or enter an evidenced external-blocker suspension. Persist the selected disposition before recomputing the graph.

### 4. Establish Formal Review evidence

Freeze the Final Artifact Identity through adjudication. Adopt the Implementation-Side Review as Formal Review evidence when:

- raw Standards and Spec reports are present;
- reviewers are independent of implementation and have verified profiles and suitable contexts;
- both reports cover the same Final Artifact Identity, including every implementation change;
- the evidence supports each finding disposition;
- the Target Project contract and change risk permit reuse.

When these conditions hold, proceed directly to adjudication. Otherwise dispatch a fresh Review Agent against the Review Fixed Point and Final Artifact Identity with the Approved Spec and Ticket, standards sources, commit list, and exact scope. Target Project mandates and high-impact security, public-contract, persistence, migration, concurrency, deployment, or release surfaces may require this fresh review.

Use the validated `code-review` Skill when its live contract is applicable. It returns independent Standards and Spec results side by side. When its contract is inapplicable, disclose DAG-Native Fallback and dispatch fresh Standards and Spec Reviewers against the same Final Artifact Identity. The pinned contract uses `docs/agents/issue-tracker.md` as its tracker-context input; project-configuration work remains separately authorized.

Each Review Agent report includes its own and nested reviewers' resolved and observed Execution Profiles, run-time changes, artifact identities, and raw findings. Treat a timeout or missing report as missing evidence, apply the remaining Operational Retry when appropriate, and reconcile every reviewer after it reaches a terminal state or is explicitly superseded.

Any change to reviewed bytes or review-relevant identity or history establishes a new Final Artifact Identity and reapplies this gate. Retain prior evidence for a topology-only integration only when verified equivalence keeps the change outside both review scopes.

### 5. Adjudicate

Inspect the implementation evidence and raw review results. Give every finding one supported disposition:

- blocking within the Ticket's approved scope;
- valid but graph-changing;
- advisory, with non-blocking rationale;
- false positive, with evidence;
- unresolved.

Integration becomes available after all mandatory Target Project, Spec, and Ticket violations are resolved and every finding has a supported non-blocking disposition. Route graph-changing findings through DAG Revision; semantic, acceptance, and gate changes require user approval.

### 6. Integrate and accept

The Coordinator integrates the exact reviewed candidate into the Target Project's Authoritative Integration Baseline under its contract and current authorization. Verify artifact reachability or representation, then run affected, integration, and delivered-public-seam gates on the integrated bytes.

Keep integration byte-preserving. A conflict that changes reviewed bytes within the original Ticket scope uses the remaining Formal Rework, opens the second Ticket Attempt from the current Authoritative Integration Baseline, and captures a new Review Fixed Point. The Execution Agent then repeats the complete Ticket flow against that baseline. Scope drift or an exhausted Formal Rework enters DAG Revision.

Accept the Ticket when the integrated Final Artifact Identity, verification, Formal Review, finding dispositions, scope, baseline, and tracker evidence agree. Persist and reread acceptance evidence before unlocking successors. Synchronize an external resolved state after proving the promised reference contains the artifact and confirming the required remote-write and publication authorization.

## Bound rework and revise the graph

Each Ticket has one Formal Rework for a Coordinator-accepted in-scope blocking finding after Implementation Handoff, Formal Review, or integration. Persist the consumed budget, open the second Ticket Attempt from the current Authoritative Integration Baseline with a new Review Fixed Point and one new Operational Retry, then reuse the original suitable Execution Agent or dispatch a fresh one with the complete accepted findings. The reworked artifact repeats the full Ticket flow. Self-correction before handoff, duplicate findings, false positives, and Operational Retry remain outside this budget.

Move directly to DAG Revision when a Ticket gains another independent objective or acceptance seam, or its fixed diff exceeds a bounded review surface. When blockers remain after Formal Rework, choose among a split Ticket, a new prerequisite, reordered work, rejected or deferred scope, or an external blocker.

Use the Target Project's authoring capability to create or revise Ticket content. Preserve acyclicity and provenance by appending an approved replacement subgraph and retaining displaced Tickets as Superseded. One semantics-preserving DAG Revision may proceed automatically per original Ticket Lineage after its rationale and consumed budget are persisted; a further revision in that lineage requires explicit user authorization. Revalidate the whole graph after every revision.

A valid late finding or Whole-DAG failure freezes dispatch, integration, and acceptance across the subgraph that consumed the contradicted output. Bring every active affected Agent to a verified terminal or superseded state, establish quiescent write boundaries, and preserve its candidate as unaccepted evidence. Invalidate the contradicted Ticket's acceptance and each accepted consuming descendant when authorized, then use remaining Formal Rework or an authoring-produced remediation lineage before recomputing the graph.

## Reach a terminal outcome

Continue independent Runnable Frontier branches while another branch is blocked. Count an Agent as running while liveness is observable and its progress checkpoint remains valid. Report progress through evidence-bearing milestones.

Report **Stalled** when effective Tickets remain unfinished, running Agent count is zero, and the Runnable Frontier is empty. Give each stopped path its live evidenced cause.

Report **Complete** after every effective Ticket is accepted and the Whole-DAG Acceptance Gate verifies:

- complete Approved Spec coverage;
- every accepted candidate on the Authoritative Integration Baseline and every accepted predecessor output consumed by its dependents;
- current Final Artifact Identities aligned with Ticket and review evidence;
- all Target Project graph-wide verification gates;
- resolved findings, blockers, and in-scope changes;
- tracker, commit, Ticket Lineage, and acceptance-evidence consistency.

Return an evidence-backed summary of accepted, superseded, and stalled Tickets; verification performed and omitted; review dispositions; graph revisions; and pending High-impact Operations. Complete represents local acceptance; publication remains separately authorized.
