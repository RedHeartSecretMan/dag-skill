---
name: dag-skill
description: Coordinate an already approved Spec-and-Ticket dependency DAG through continuous multi-ticket implementation, evidence-aware review, bounded rework, graph revision, and final acceptance. Use when the user explicitly asks to execute, advance, continue, or resume an approved DAG in a target project. Route Spec or Ticket authoring and isolated single-ticket implementation to their dedicated skills.
---

# Coordinate an Approved Ticket DAG

Act as the Coordinator for an approved directed acyclic graph of delivery Tickets. Advance the graph from live Target Project evidence; treat worker reports and chat history as leads to verify, not state to trust.

## Establish the run

1. Resolve the Target Project, Approved Spec, in-scope Tickets and dependency carrier, and the user's explicit request to execute, advance, continue, or resume the DAG.
2. Ask for one precise pointer when any required input is missing or ambiguous. Keep the run paused rather than guessing scope, dependencies, or approval.
3. Read the Target Project's current `AGENTS.md` files, domain and engineering documents, Tracker Contract, Approved Spec, Tickets, repository state, tests, and existing review evidence.
4. Discover the exact installed `implement`, `code-review`, and Target Project authoring Skills from the live environment. Treat current availability and applicability as evidence, not as an assumption from chat.
5. Use these required profiles and verify actual visible runtime metadata:
   - Coordinator: `gpt-5.6-sol`, `max`;
   - Execution Agent: `gpt-5.6-sol`, `high`;
   - Review Agent, Standards Reviewer, and Spec Reviewer: `gpt-5.6-sol`, `high`.
6. Report a mismatched or unverifiable profile and pause the affected work until the correct profile is available or the user explicitly authorizes a substitute. Never silently substitute a model or reasoning effort.

Treat a contradiction among user scope, project instructions, Tracker Contract, Approved Spec, or approved Tickets as a blocked design input when it affects scope, semantics, acceptance, or delivery behavior. Pause the affected node and propose a Ticket repair, split, or graph revision through the Target Project's authoring capability.

## Respect authorization

Treat the DAG Run Authorization as permission for continuous, locally auditable coordination without per-Ticket confirmation when the Target Project permits it:

- update a local tracker carrier and claim local Tickets;
- dispatch Agents;
- make ticket-scoped local changes and run verification;
- create a ticket-scoped commit in a safe Git context;
- persist local acceptance evidence and unlock successors.

Obtain separate user authorization before any external-system mutation, including remote tracker writes, deployments, external API or database writes, and state-changing remote CI triggers. Also obtain separate authorization before push, pull request creation, tag, release, destructive Git, approved product-semantic or acceptance changes, or gate weakening.

Preserve unrelated work. Use the existing repository as found; never initialize Git, reset or clean away state, or manufacture a baseline.

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
- Review Fixed Point and Final Artifact Identity when available;
- consumed Operational Retry and Formal Rework;
- raw review findings and Coordinator dispositions;
- acceptance evidence;
- Ticket Lineage and consumed automatic DAG Revision.

Treat a Ticket as non-runnable when required recovery evidence cannot be reconstructed or legally persisted. Do not create a DAG Skill scheduler file.

## Compute and schedule the frontier

Include a Ticket in the Runnable Frontier only when:

- every hard predecessor is accepted;
- blockers are cleared;
- current authorization permits both claiming and acceptance evidence persistence;
- the required Agent profile and capability are available;
- a safe write boundary exists without an ownership conflict.

Treat a ready-like status string as insufficient by itself.

Finish evidence checks, review, and acceptance for work already in progress before opening more implementation work. Recompute the frontier after every claim, handoff, acceptance, block, or graph revision. Select work by tracker priority, then clear downstream-unlock or critical-path value, then stable Ticket identity.

Run graph-independent Tickets concurrently only when the Target Project supplies isolated workspaces and an explicit integration boundary. Keep one write-capable Execution Agent per workspace. Serialize uncertain write interactions; allow independent read-only reviews to run concurrently.

## Advance one Ticket

### 1. Claim and capture the fixed point

Reread the Ticket, dependencies, blockers, repository, and tracker immediately before dispatch. Claim it under the Tracker Contract, then capture an immutable pre-implementation Review Fixed Point that bounds the Ticket's change. Persist enough evidence to recover the attempt.

### 2. Dispatch implementation

Dispatch one fresh Execution Agent for exactly one Ticket with the required profile. Supply the Target Project instructions, Approved Spec, Ticket, dependency outputs, Review Fixed Point, acceptance criteria, allowed workspace, and authorization boundary.

When `implement` is installed and applicable, explicitly require the Execution Agent to use it as installed. Let its required `code-review` run as an Implementation-Side Review. Treat the raw Standards and Spec results as candidate evidence; neither the Execution Agent nor its nested reviewers may accept the Ticket, mutate DAG state, or unlock successors.

Use `implement` only when its Git commit and nested review contracts can be satisfied safely. Supply the fixed point, Spec, Ticket, standards, and tracker context before dispatch. Treat it as inapplicable if following it would require installing prerequisites, mutating project configuration, skipping a required step, or committing in an unsafe or non-Git context.

When `implement` is unavailable or inapplicable, disclose DAG-Native Fallback and dispatch a fresh Execution Agent directly. Require it to:

- implement only the Ticket's approved scope;
- use public-interface TDD at an agreed seam when feasible;
- run focused checks during implementation and the Target Project's complete applicable gates at the end;
- create a ticket-scoped commit only when the repository and authorization permit it;
- return a complete Implementation Handoff.

Represent fallback honestly; never claim that an unavailable or inapplicable Skill ran.

### 3. Validate the handoff

Require the Execution Agent to return:

- Ticket identity and delivered scope;
- changed files and commit when applicable;
- exact verification commands and outcomes, including failures and checks not run;
- raw Standards and Spec review artifacts when available;
- actual reviewer runtime metadata and the artifact identity each reviewer examined;
- every change made after the Implementation-Side Review;
- deviations, unresolved risks, and blockers.

Inspect the live diff, commit, repository state, scope, verification results, raw review artifacts, reviewer independence, and artifact identities yourself. Reject a completion claim or second-hand review summary as an invalid handoff.

Allow one total corrected Operational Retry per Ticket attempt when an Agent crash, tool failure, profile mismatch, or invalid handoff prevents a valid result. Persist the consumed retry before redispatch. After that budget is consumed, treat any further operational failure as a blocker rather than another retry.

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

When `code-review` is unavailable or inapplicable, disclose DAG-Native Fallback and dispatch fresh, independent Standards and Spec Reviewers against the same Final Artifact Identity. Preserve both axes and the required profiles.

Treat any later implementation change, amend, or rebase as invalidating both review axes. Establish the new Final Artifact Identity and apply the Review Sufficiency Gate again.

### 5. Adjudicate

Inspect the implementation evidence and raw review results. Give every finding one supported disposition:

- blocking within the Ticket's approved scope;
- valid but graph-changing;
- advisory and non-blocking, with rationale;
- false positive, with evidence;
- unresolved.

Keep mandatory Target Project, Spec, and Ticket violations blocking. Keep unresolved findings blocking. Do not weaken a gate or change approved semantics to obtain acceptance.

Accept the Ticket only when the Final Artifact Identity, verification, review evidence, finding dispositions, scope, and tracker evidence agree. Persist the Target Project's acceptance state and evidence, reread it, and only then unlock successors. Never use green tests, an Execution Agent claim, or a Reviewer verdict alone as completion proof.

## Bound rework and revise the graph

Authorize one Formal Rework per Ticket when the Coordinator accepts a blocking Formal Review finding within the original scope. Persist the consumed rework before redispatch. Reuse the original Execution Agent when it remains available with the required profile; otherwise dispatch a fresh `implement` Agent with the complete accepted findings.

Treat self-correction before handoff, duplicate findings, false positives, and Operational Retry as outside the Formal Rework budget. Make the reworked artifact pass implementation, handoff, review sufficiency, and adjudication again.

When valid blockers remain after Formal Rework, stop retrying that Ticket. Decide whether the graph needs a split Ticket, a new prerequisite, reordered work, rejected or deferred scope, or an external blocker. Preserve acyclicity and provenance; append a replacement subgraph rather than adding a back edge or deleting history.

Use the Target Project's current authoring Skill to create or revise Ticket content. The DAG Skill decides that revision is required but does not author replacement Tickets and has no authoring fallback. Obtain user approval for any product-semantic, acceptance, or gate change.

Allow at most one automatic semantics-preserving DAG Revision per original Ticket Lineage. Persist its rationale, provenance, and consumed budget before scheduling the replacement subgraph. Require explicit user authorization for another revision in the same lineage; otherwise leave that path evidenced and unfinished. Revalidate the whole graph after every revision.

## Reach a terminal outcome

Continue independent runnable branches when one branch blocks. Count an Agent as running only while its liveness is observable; convert a lost Agent into an Operational Failure.

Report **Stalled** only when unfinished effective Tickets remain, no Agent is running, and the Runnable Frontier is empty. Give every stopped path a live evidenced cause, such as missing authorization, invalid graph, unavailable capability, external blocker, repeated Operational Failure, exhausted Formal Rework, or exhausted automatic DAG Revision.

Report **Complete** only after every effective Ticket is accepted and a Whole-DAG Acceptance Gate verifies:

- complete Approved Spec coverage;
- integration of accepted predecessor outputs into dependents;
- current Final Artifact Identities matching Ticket and review evidence;
- all Target Project graph-wide verification gates;
- no unresolved findings, blockers, or unexplained in-scope changes;
- tracker, commit, Ticket Lineage, and acceptance-evidence consistency.

Return a final evidence-backed summary of accepted, superseded, and stalled Tickets, verification performed and omitted, review dispositions, graph revisions, and any unexecuted High-impact Operations. Treat Complete as local acceptance only; it grants no publication authority.
