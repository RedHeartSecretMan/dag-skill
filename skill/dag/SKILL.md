---
name: dag
description: Coordinate an already approved Spec-and-Ticket dependency DAG through continuous multi-ticket implementation, evidence-aware review, bounded rework, graph revision, and final acceptance. Use when the user explicitly asks to execute, advance, continue, or resume an approved DAG in a target project. Route Spec or Ticket authoring and isolated single-ticket implementation to their dedicated skills.
---

# Coordinate an Approved Ticket DAG

Act as the Coordinator for an approved directed acyclic graph of delivery Tickets. Advance the graph from live Target Project evidence; treat worker reports and chat history as leads to verify, not state to trust.

Keep DAG and tracker state under the Coordinator's exclusive control. Execution Agents may change only their authorized Ticket workspace; Review Agents remain read-only. Execution, Review, and nested Agents return artifacts and evidence but do not claim or accept Tickets, mutate tracker or graph state, integrate candidates, or unlock successors.

## Establish the run

1. Resolve the Target Project, Approved Spec, in-scope Tickets and dependency carrier, and the user's explicit request to execute, advance, continue, or resume the DAG.
2. Ask for one precise pointer when any required input is missing or ambiguous. Keep the run paused rather than guessing scope, dependencies, or approval.
3. Read the Target Project's current `AGENTS.md` files, domain and engineering documents, Tracker Contract, Approved Spec, Tickets, repository state, tests, and existing review evidence.
4. Discover the exact installed `implement`, `code-review`, and Target Project authoring Skills, plus the Agent models, reasoning controls, tools, and runtime metadata actually available in the live environment. Treat availability and applicability as evidence, not as an assumption from chat.
5. Resolve a run-scoped Execution Profile for each role:
   - Treat an exact model, Agent, or reasoning-effort requirement from the user or Target Project as a hard constraint.
   - Otherwise use a suitable active primary Agent as Coordinator, favoring the strongest available graph-wide reasoning and context capacity.
   - Choose Execution Agents for the Ticket's repository, coding, tool, context, and risk needs. Choose Review Agents for the review surface and an independent context; model diversity is optional unless a governing contract requires it.
   - Use the highest useful supported reasoning effort for coordination and high-risk work, and proportional effort for bounded lower-risk work.
6. When the user names a model or asks which model to use, evaluate the live available choices against the requested role and work. Recommend concrete role assignments and relevant trade-offs. Honor a suitable available choice; when an exact request is unavailable, incapable, or conflicts with a governing contract, explain why and obtain user authorization before substituting it.
7. Inspect and record all runtime metadata the host exposes for the active Coordinator and every dispatched Agent, including unavailable fields, the resolved profile, and any run-time change. Never infer a missing model or reasoning effort. If an exact requirement cannot be verified, leave that role unavailable. Without an exact constraint, an Agent may run when its required identity and capabilities are substantiated even if the host omits a model or effort field; disclose the omission. Before dispatch, selecting another suitable substantiated profile is ordinary scheduling, not a reason to stop the whole DAG; after dispatch, handle an observed profile mismatch as an Operational Failure. Never silently substitute or claim a model, Agent, or reasoning effort that the evidence does not show.

Optionally use an already-authorized durable host goal or continuation mechanism when available; when used, read back its live state after continuation, resume, or task handoff. Treat it only as run liveness; never treat it as Target Project state, forward progress, or completion evidence.

Treat a contradiction among user scope, project instructions, Tracker Contract, Approved Spec, or approved Tickets as a blocked design input when it affects scope, semantics, acceptance, or delivery behavior. Pause the affected node and propose a Ticket repair, split, or graph revision through the Target Project's authoring capability.

## Respect authorization

Treat the DAG Run Authorization as permission for continuous, locally auditable coordination without per-Ticket confirmation when the Target Project permits it:

- update a local tracker carrier and claim local Tickets;
- dispatch Agents;
- create and use non-destructive, ticket-scoped local candidate branches or worktrees;
- make ticket-scoped local changes and run verification;
- create a ticket-scoped commit in a safe Git context;
- persist local acceptance evidence and unlock successors.

Obtain separate user authorization before any external-system mutation, including remote tracker writes, deployments, external API or database writes, and state-changing remote CI triggers. Also obtain separate authorization before push, pull request creation, tag, release, destructive Git, approved product-semantic or acceptance changes, or gate weakening.

Preserve unrelated work. Use the existing repository as found; never initialize Git, reset or clean away state, or manufacture a baseline. Classify inherited changes as the current Ticket candidate, protected unrelated work, or unaccepted historical work. Treat unaccepted historical work as evidence only unless a live approved Ticket explicitly adopts it.

## Reconstruct the live graph

Treat each executable node as one approved Ticket. Require every Ticket to expose an authoritative identity, one delivery objective, scope boundaries, dependency inputs, downstream outputs, acceptance and verification requirements, current state, ownership, and blockers.

Orient every dependency edge `prerequisite -> dependent`. Add an edge only when the dependent consumes an accepted output of the prerequisite. Treat preferred order, similar files, shared ownership, implementation phases, and external blockers as scheduling facts rather than dependency edges.

On every start or continuation:

1. Project the live carrier into a DAG without creating a shadow authority.
2. Resolve unique nodes and edges.
3. Reject self-edges, cycles, missing hard dependencies, ambiguous semantics, incomplete node contracts, and acceptance claims unsupported by current evidence.
4. Exclude Superseded Tickets from execution while retaining their provenance; include every approved replacement Ticket in the effective graph.
5. Reconcile accepted, in-progress, blocked, superseded, and unclaimed Tickets from live evidence.

Keep recovery data in the Target Project's existing tracker or repository evidence under its contract. For every started Ticket, reconstruct:

- current attempt, ownership, and blockers;
- resolved and observed Execution Profiles for the active Coordinator and every dispatched Agent, including unavailable metadata fields, mismatches, and changes;
- for every Agent dispatched directly by the Coordinator, its current bounded progress checkpoint, bound, observed state, and last evidence-bearing milestone;
- Review Fixed Point and Final Artifact Identity when available;
- integration state, Authoritative Integration Baseline identity, candidate representation or reachability, and integrated-gate commands, contexts, outcomes, and bound artifact identities when available;
- consumed Operational Retry and Formal Rework;
- raw review findings and Coordinator dispositions;
- acceptance evidence;
- known failing gates, including the exact command and context, actual result, classification, owning Ticket or blocker, and closing condition;
- Ticket Lineage and consumed automatic DAG Revision.

Treat a Ticket as non-runnable when required recovery evidence cannot be reconstructed or legally persisted. Do not create a DAG Skill scheduler file.

For a cross-task handoff, persist this recovery evidence first. Count the handoff as established only after the receiving Coordinator rereads the live Target Project, reconstructs all required Recovery Evidence, and recomputes the frontier; sending a message or observing an active task is insufficient.

## Compute and schedule the frontier

Include a Ticket in the Runnable Frontier only when:

- the Ticket is not already accepted;
- every hard predecessor is accepted;
- blockers are cleared;
- current authorization permits both claiming and acceptance evidence persistence;
- a suitable resolved Execution Profile and required capability are available;
- a safe write boundary exists without an ownership conflict and cannot advance the Authoritative Integration Baseline before adjudication.

Treat a ready-like status string as insufficient by itself.

Finish evidence checks, review, and acceptance for work already in progress before opening more implementation work. Recompute the frontier after every claim, handoff, acceptance, block, or graph revision. Within currently available Agent capacity, select the largest safe subset whose peak direct and nested Agent demand fits; serialize when that demand is unknown. Break capacity ties by tracker priority, then clear downstream-unlock or critical-path value, then stable Ticket identity.

Run graph-independent Tickets concurrently only when the Target Project permits isolated workspaces and defines an explicit integration boundary. Under the Target Project's contract, the Coordinator may create and use ticket-scoped local candidate branches or worktrees for those boundaries. Keep one write-capable Execution Agent per workspace. Serialize uncertain write interactions; allow independent read-only reviews to run concurrently.

For every Agent that the Coordinator dispatches directly, set and persist a bounded progress checkpoint appropriate to its role, Ticket, and host. Make a dispatching Agent responsible for equivalent bounded monitoring of any nested Agents it creates and for reporting their resolved and observed Execution Profiles, unavailable metadata fields, changes, and terminal states. At each checkpoint, require an evidence-bearing milestone, an evidenced blocker, or a terminal result; otherwise interrupt the still-live Agent and record an Operational Failure.

## Advance one Ticket

### 1. Claim and capture the fixed point

Reread the Ticket, dependencies, blockers, repository, and tracker immediately before dispatch. Claim it under the Tracker Contract, then capture an immutable pre-implementation Review Fixed Point that bounds the Ticket's change. Persist enough evidence to recover the attempt.

### 2. Dispatch implementation

Dispatch one fresh Execution Agent for exactly one Ticket with its resolved Execution Profile. Supply the Target Project instructions, Approved Spec, Ticket, dependency outputs, Review Fixed Point, acceptance criteria, allowed workspace, and authorization boundary.

When `implement` is installed and applicable, explicitly require the Execution Agent to use it as installed. Let its required `code-review` run as an Implementation-Side Review. Treat the raw Standards and Spec results as candidate evidence.

Use `implement` only when its Git commit and nested review contracts can be satisfied safely and its commit remains a candidate without advancing the Authoritative Integration Baseline. Supply the fixed point, Spec, Ticket, standards, and tracker context before dispatch. Treat it as inapplicable if following it would require installing prerequisites, mutating project configuration, skipping a required step, or committing in an unsafe, non-Git, or baseline-advancing context.

When `implement` is unavailable or inapplicable, disclose DAG-Native Fallback and dispatch a fresh Execution Agent directly. Require it to:

- implement only the Ticket's approved scope;
- use public-interface TDD at an agreed seam when feasible;
- run focused checks during implementation and the Target Project's complete applicable gates at the end;
- create a ticket-scoped candidate commit only when the repository and authorization permit it without advancing the Authoritative Integration Baseline;
- return a complete Implementation Handoff.

Across both paths, count a RED only when its input conforms to the live Ticket contract, it exercises the live Ticket's agreed public contract seam and real delivered seam when applicable, and it fails because of the target behavior rather than an environment, tool, or probe error. Claiming, reading, and exploration are neither RED nor candidate evidence.

Represent fallback honestly; never claim that an unavailable or inapplicable Skill ran.

### 3. Validate the handoff

Require the Execution Agent to return:

- Ticket identity and delivered scope;
- changed files and commit when applicable;
- exact verification commands, execution contexts, and outcomes, including failures and checks not run; classify each failure as an introduced regression, an evidenced baseline exception with an owning Ticket or blocker and closing condition, an environment/tool/probe failure, or unverified;
- raw Standards and Spec review artifacts when available;
- actual Execution Agent and reviewer runtime metadata, and the artifact identity each reviewer examined;
- every change made after the Implementation-Side Review;
- deviations, unresolved risks, and blockers.

Inspect the live diff, commit, repository state, scope, verification results, raw review artifacts, reviewer independence, and artifact identities yourself. Inspect the delivered public seam when it differs from source or test fixtures, and reject unexplained generated, formatted, or dependency-lock churn. Reject a completion claim or second-hand review summary as an invalid handoff.

Reproduce a claimed environment, tool, or probe failure with the same relevant check in a suitable authorized environment; otherwise keep it unverified. Never represent a non-green gate as green or project an exception from one artifact identity onto another.

Treat a required gate that remains non-green or unverified as blocking unless the Target Project contract explicitly permits that exact exception and its recovery evidence identifies an owner or blocker and a closing condition.

Allow one total corrected Operational Retry per Ticket attempt across implementation, review, and integration when an Agent crash, tool failure, profile mismatch, invalid handoff or report, or integration tool failure prevents a valid result. Persist the consumed retry before redispatch. After that budget is consumed, treat any further operational failure as a blocker rather than another retry.

Keep role separation after failure: redispatch the appropriate Agent within the retry budget or block the Ticket. The Coordinator does not take over Ticket implementation or replace independent review.

### 4. Apply the Review Sufficiency Gate

Identify and freeze the immutable Final Artifact Identity before adjudication. Prevent writers from changing the reviewed workspace or artifact until the Coordinator decides its disposition.

Adopt the Implementation-Side Review as Formal Review evidence only when:

- both raw Standards and Spec reports are available;
- the reviewers did not implement the Ticket and their actual profiles and contexts are valid;
- both reports examine the same Final Artifact Identity;
- no implementation change followed the review;
- the evidence is complete enough to substantiate every finding disposition;
- neither the Target Project nor the change risk requires a fresh review.

When these conditions hold, proceed without mechanically repeating the review.

Dispatch a fresh Review Agent when evidence is missing, stale, incomplete, contradictory, unverifiable, or inadequate for the risk. Require a fresh review when the Target Project mandates one or when the Coordinator cannot substantiate a high-impact surface such as security, a public contract, persistence or migration, concurrency, deployment behavior, or a release gate.

When `code-review` is installed and applicable, explicitly require the fresh Review Agent to use it with the Review Fixed Point, Final Artifact Identity, Approved Spec and Ticket, standards sources, commit list, and exact scope. Require independent Standards and Spec results side by side; the Spec axis is mandatory for this workflow.

When `code-review` is unavailable or inapplicable, disclose DAG-Native Fallback and dispatch fresh, independent Standards and Spec Reviewers against the same Final Artifact Identity. Preserve both axes and their resolved Execution Profiles.

Require every Review Agent report to include its own and any nested Reviewers' resolved and observed Execution Profiles, unavailable metadata fields, run-time changes, artifact identities, and raw findings. Do not adopt review evidence when required profile evidence is missing or violates an exact constraint.

Treat a review timeout or missing report as missing evidence, never as a clean result. Use the remaining Operational Retry for a replacement when the missing evidence is an operational failure; block after that retry is consumed. Before adjudication, require every dispatched reviewer for the attempt to reach an observed terminal state or be explicitly superseded, then reconcile every queued or late report even when a replacement review has already been dispatched.

Treat any later change to reviewed bytes or review-relevant identity or history as invalidating both review axes. Establish the new Final Artifact Identity and apply the Review Sufficiency Gate again. Retain existing evidence across a topology-only integration only when equivalence is verifiable and the changed identity or history lies outside both review scopes.

### 5. Adjudicate

Inspect the implementation evidence and raw review results. Give every finding one supported disposition:

- blocking within the Ticket's approved scope;
- valid but graph-changing;
- advisory and non-blocking, with rationale;
- false positive, with evidence;
- unresolved.

Keep mandatory Target Project, Spec, and Ticket violations blocking. Keep unresolved findings blocking. Treat every graph-changing finding as preventing integration until the Target Project's authoring capability produces an approved, valid revision. Do not weaken a gate or change approved semantics to obtain acceptance.

### 6. Integrate and accept

After adjudication leaves no blocking, graph-changing, or unresolved finding, integrate the exact reviewed candidate into the Target Project's Authoritative Integration Baseline under its contract and the current authorization. Verify that the reviewed artifact is represented by or reachable from that baseline, then run the required affected and integration gates on the integrated bytes, including the delivered public seam when applicable.

Apply the same invalidation rule when integration, conflict resolution, rebase, generated output, or any other integration action changes the reviewed artifact.

Keep integration byte-preserving. When a conflict requires reviewed-byte changes within the original Ticket scope, preserve the reviewed candidate and consume the Ticket's remaining Formal Rework to redispatch the appropriate Execution Agent. Require the new artifact to pass handoff, review, adjudication, and integration again. Revise the graph when Formal Rework is exhausted or the conflict exposes scope drift; the Coordinator does not implement the resolution.

Accept the Ticket only when the integrated Final Artifact Identity, verification, review evidence, finding dispositions, scope, Authoritative Integration Baseline, and tracker evidence agree. When an external resolved state promises artifact availability from a designated integration or remote reference, prove that reachability before writing the state; without every required remote tracker-write and publication authorization, retain local acceptance evidence and leave the external state unchanged. Persist the Target Project's acceptance state and evidence, reread it, and only then unlock successors. Never use green tests, an Execution Agent claim, or a Reviewer verdict alone as completion proof.

## Bound rework and revise the graph

Stop in-place implementation as soon as the Ticket acquires another independent delivery objective or acceptance seam, or its fixed diff no longer supports a bounded review. Use the Target Project's authoring capability to repair or split the graph instead of allowing scope to accumulate inside the node.

Authorize one Formal Rework per Ticket when the Coordinator accepts a blocking Formal Review or integration finding within the original scope. Persist the consumed rework before redispatch. Reuse the original Execution Agent when it remains available with a suitable resolved Execution Profile; otherwise dispatch a fresh Execution Agent with the complete accepted findings. Reapply the initial dispatch's Skill applicability gate against the live environment: explicitly use `implement` when applicable, or disclose and use DAG-Native Fallback.

Treat self-correction before handoff, duplicate findings, false positives, and Operational Retry as outside the Formal Rework budget. Make the reworked artifact pass implementation, handoff, review sufficiency, and adjudication again.

When valid blockers remain after Formal Rework, stop retrying that Ticket. Decide whether the graph needs a split Ticket, a new prerequisite, reordered work, rejected or deferred scope, or an external blocker. Preserve acyclicity and provenance; append a replacement subgraph rather than adding a back edge or deleting history.

Use the Target Project's current authoring Skill to create or revise Ticket content. The DAG Skill decides that revision is required but does not author replacement Tickets and has no authoring fallback. Obtain user approval for any product-semantic, acceptance, or gate change.

Allow at most one automatic semantics-preserving DAG Revision per original Ticket Lineage. Persist its rationale, provenance, and consumed budget before scheduling the replacement subgraph. Require explicit user authorization for another revision in the same lineage; otherwise leave that path evidenced and unfinished. Revalidate the whole graph after every revision.

When a valid late review finding or Whole-DAG failure contradicts an accepted Ticket, immediately treat its acceptance evidence and the acceptance of every consuming descendant as invalid, and pause the affected subgraph. Persist that invalidation under the Tracker Contract when authorized; block the path when it cannot be legally persisted. Reopen the Ticket when its remaining Formal Rework can address the original scope; otherwise use the authoring capability to append a remediation lineage. Recompute and revalidate the graph before resuming affected work.

## Reach a terminal outcome

Continue independent runnable branches when one branch blocks. Count an Agent as running only while its liveness is observable and its bounded progress checkpoint has not failed; convert a lost or non-progressing Agent into an Operational Failure. Report forward progress only from evidence-bearing milestones such as a valid RED, a ticket-scoped change, a candidate artifact, or a valid handoff; an active goal or chat output alone is not progress.

Report **Stalled** only when unfinished effective Tickets remain, no Agent is running, and the Runnable Frontier is empty. Give every stopped path a live evidenced cause, such as missing authorization, invalid graph, unavailable capability, external blocker, repeated Operational Failure, exhausted Formal Rework, or exhausted automatic DAG Revision.

Report **Complete** only after every effective Ticket is accepted and a Whole-DAG Acceptance Gate verifies:

- complete Approved Spec coverage;
- integration of every accepted candidate into the Authoritative Integration Baseline and of accepted predecessor outputs into dependents;
- current Final Artifact Identities matching Ticket and review evidence;
- all Target Project graph-wide verification gates;
- no unresolved findings, blockers, or unexplained in-scope changes;
- tracker, commit, Ticket Lineage, and acceptance-evidence consistency.

Return a final evidence-backed summary of accepted, superseded, and stalled Tickets, verification performed and omitted, review dispositions, graph revisions, and any unexecuted High-impact Operations. Treat Complete as local acceptance only; it grants no publication authority.
