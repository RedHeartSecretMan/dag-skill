# DAG Coordination

This context defines the language for coordinating an approved directed acyclic execution graph in a target project without replacing that project's own delivery contracts.

## Language

**DAG Skill**:
The project-independent Graph Engineering pattern for continuously scheduling an Approved DAG through execution, review, and final acceptance.
_Avoid_: project-specific orchestrator, tracker-specific workflow

**Target Project**:
The project whose approved delivery work is being coordinated and whose live rules and evidence govern that work.
_Avoid_: source project, template project

**DAG**:
A finite directed acyclic graph whose Ticket nodes and dependency edges form the execution plan followed by coordinated agents.
_Avoid_: workflow loop, flat queue, checklist

**Graph Engineering**:
The discipline of expressing coordinated agent work as an explicit DAG so execution order and safe parallelism follow graph topology rather than an implicit loop.
_Avoid_: loop engineering, sequential checklist, agent swarm

**Approved DAG**:
A user-approved DAG grounded in an approved Spec and its already-decomposed Tickets; it is execution input, not a draft design.
_Avoid_: plan, backlog, draft DAG

**DAG Projection**:
The carrier-neutral live reconstruction of an Approved DAG used for validation and scheduling without becoming a separate authority or inventing dependency semantics.
_Avoid_: shadow tracker, inferred plan, persisted scheduler state

**Ticket**:
An executable, acceptance-scoped unit of delivery work within an Approved DAG.
_Avoid_: task, step, prompt

**Accepted Ticket**:
A Ticket whose Final Artifact Identity, verification, Finding Dispositions, and tracker evidence have been validated and persisted by the Coordinator.
_Avoid_: implemented ticket, reviewed ticket, worker-complete ticket

**Node Contract**:
The minimum live semantics required to schedule a Ticket without guessing: identity, scope, dependency inputs, observable outputs, acceptance, state, ownership, and blockers.
_Avoid_: tracker schema, prompt template, node metadata file

**Edge Contract**:
The requirement that a directed edge run from a prerequisite Ticket to a dependent Ticket that consumes the prerequisite's accepted output.
_Avoid_: preferred order, shared ownership, external blocker

**Whole-Graph Validity Gate**:
The fail-closed check that a live DAG Projection is acyclic, resolvable, approved, contract-complete, and consistent with current acceptance evidence before scheduling proceeds.
_Avoid_: lint pass, tracker status check, cycle check alone

**Runnable Frontier**:
The set of unaccepted Tickets whose hard dependencies are accepted, blockers are cleared, and required claim and acceptance persistence, verified Agent profiles, and safe write boundaries are currently available under live authorization.
_Avoid_: ready status, graph-ready set, pending queue

**Continuous Scheduling**:
The Coordinator's repeated live reconciliation, frontier calculation, dispatch, adjudication, and successor unlocking under a DAG Run Authorization until the graph completes or genuinely stalls.
_Avoid_: background daemon, per-Ticket confirmation, chat-driven progress

**Safe Parallelism**:
Concurrent execution limited to frontier Tickets that are both graph-independent and sufficiently isolated from shared write or runtime conflicts.
_Avoid_: maximum fan-out, dependency-only concurrency, speculative parallelism

**Single-Writer Boundary**:
The rule that only one Execution Agent may write in a workspace at a time unless the Target Project provides explicitly authorized isolation and integration boundaries.
_Avoid_: shared-worktree parallelism, concurrent commits, inferred isolation

**Finish-First Scheduling**:
The capacity rule that completes formal review and acceptance of work already in progress before opening additional implementation work.
_Avoid_: maximum work in progress, implementation-first scheduling

**Complete**:
The terminal outcome reached only when every effective Ticket is accepted and the Whole-DAG Acceptance Gate passes against live evidence.
_Avoid_: all workers done, all tests green, tracker complete

**Stalled**:
The terminal outcome reached when unfinished Tickets remain but no Agent is running and no Runnable Frontier exists, with every stopped path explained by live evidence.
_Avoid_: waiting, agent capacity limit, partial completion

**Whole-DAG Acceptance Gate**:
The Coordinator's final graph-wide verification of Spec coverage, integrated dependency outputs, current Ticket evidence, project gates, and tracker consistency.
_Avoid_: last Ticket acceptance, full test alone, completion summary

**Ticket Gate**:
An evidence-backed condition that a Ticket must satisfy before it can advance within its execution and acceptance lifecycle.
_Avoid_: checklist item, status label

**Formal Rework**:
The single Coordinator-authorized return of a Ticket to its Execution Agent after valid formal-review findings are accepted within the Ticket's original scope.
_Avoid_: retry, self-correction, new implementation attempt

**Rework Budget**:
The limit of one Formal Rework for a Ticket before further failure requires DAG-level adjudication rather than another implementation attempt.
_Avoid_: retry count, unlimited repair loop

**DAG Revision**:
An evidence-backed replacement or restructuring of part of an Approved DAG that preserves acyclicity and the provenance of displaced Tickets.
_Avoid_: retry, back edge, silent mutation

**Ticket Lineage**:
The provenance chain connecting an original Ticket to every Ticket or replacement subgraph created from it by DAG Revision.
_Avoid_: new independent Ticket, deleted history, retry sequence

**Superseded Ticket**:
A non-executable Ticket retained as historical evidence after a DAG Revision replaces its delivery role with another acyclic subgraph.
_Avoid_: deleted ticket, completed ticket, blocked ticket

**Tracker Contract**:
The Target Project's authoritative rules for Ticket representation, claiming, status transitions, evidence, and completion, independent of the storage carrier.
_Avoid_: tracker format, Markdown workflow, GitHub workflow

**DAG Run Authorization**:
An explicit user request to execute, advance, continue, or resume an Approved DAG through its locally auditable operations, without granting authority for High-impact Operations.
_Avoid_: blanket authorization, unrestricted execution

**High-impact Operation**:
An operation requiring separate user authorization because it mutates an external system, performs destructive Git work, changes approved product semantics, or weakens a gate.
_Avoid_: routine DAG operation, local step

## Roles and Evidence

**Coordinator**:
The primary agent accountable for live-state reconciliation, DAG scheduling, evidence adjudication, replanning decisions, and final acceptance.
_Avoid_: worker, reviewer, agent manager

**Execution Profile**:
The required model and reasoning-effort pair for a DAG role, verified from actual runtime metadata rather than inferred from a request.
_Avoid_: preferred model, requested configuration, silent fallback

**DAG State Ownership**:
The Coordinator's exclusive authority to claim Tickets, change tracker state, record acceptance evidence, and unlock successors.
_Avoid_: worker completion, reviewer transition, shared ownership

**Operational Retry**:
The single corrected redispatch allowed after an Agent or tool failure prevents a valid handoff, separate from a Ticket's Rework Budget.
_Avoid_: Formal Rework, automatic retry loop, repeated dispatch

**Implement Skill**:
The currently installed Matt Skill exposed through the exact name `implement` and used for both initial Ticket implementation and Formal Rework, including its implementation-side Code Review before the Implementation Handoff.
_Avoid_: Target Implementation Skill, copied implementation rules, fuzzy Skill discovery

**Authoring Skill**:
The Target Project's current capability for creating or revising Spec and Ticket content when the Coordinator determines that a DAG Revision is required.
_Avoid_: DAG Skill authoring, DAG-Native Fallback, silent Ticket rewrite

**Execution Agent**:
An agent assigned through the Implement Skill to implement exactly one Ticket against fresh Target Project context and return its implementation and raw review evidence.
_Avoid_: Coordinator, reviewer, general worker

**Implementation-Side Review**:
The independent Standards and Spec review invoked by the Implement Skill within one implementation attempt before handoff; it is candidate evidence and cannot accept the Ticket.
_Avoid_: implementer self-approval, automatic acceptance, Coordinator review decision

**Implementation Handoff**:
The boundary where an Execution Agent returns its implementation, verification, commit when applicable, raw Implementation-Side Review artifacts, deviations, and blockers to the Coordinator.
_Avoid_: Ticket acceptance, review result, worker completion claim

**Code Review Skill**:
The currently installed Matt Skill exposed through the exact name `code-review` and used for independent two-axis review either inside the Implement Skill or through a fresh Coordinator dispatch.
_Avoid_: implementer opinion, Coordinator acceptance, aggregate pass/fail

**Review Sufficiency Gate**:
The Coordinator's determination that raw independent review evidence is complete, current for the Final Artifact Identity, and reliable enough for formal adjudication; otherwise a fresh review is required.
_Avoid_: automatic second review, worker review verdict, clean-review requirement

**Formal Review**:
The Coordinator-adopted independent Standards and Spec evidence against the Final Artifact Identity, obtained either from a sufficient Implementation-Side Review or from a fresh Coordinator-dispatched review.
_Avoid_: worker summary, test run, implementation handoff

**Review Fixed Point**:
The immutable pre-implementation baseline that bounds the change attributable to one Ticket for Formal Review.
_Avoid_: current branch name, approximate start, mutable reference

**Final Artifact Identity**:
The immutable commit or verifiable content snapshot examined by both review axes and by the Coordinator before Ticket acceptance.
_Avoid_: latest files, worker-reported version, stale review target

**Finding Disposition**:
The Coordinator's evidence-backed classification of every formal-review finding as blocking, graph-changing, advisory, false positive, or unresolved.
_Avoid_: aggregate pass/fail, reviewer verdict, silent dismissal

**DAG-Native Fallback**:
The explicitly disclosed direct dispatch of DAG roles when the Implement Skill or Code Review Skill is unavailable or inapplicable, while preserving the same gates.
_Avoid_: silent downgrade, alternate workflow, skipped Skill

**Standards Reviewer**:
An agent independent of a Ticket's implementation who evaluates conformance with the Target Project's governing engineering standards.
_Avoid_: linter, implementer, general reviewer

**Spec Reviewer**:
An agent independent of a Ticket's implementation who evaluates conformance with the approved Spec and Ticket acceptance criteria.
_Avoid_: product designer, implementer, general reviewer

**Normative Authority**:
A live governing source that defines authorized scope, intended semantics, or required delivery behavior for an Approved DAG.
_Avoid_: status evidence, agent report

**State Evidence**:
A live tracker, repository, test, or formal-review artifact that substantiates what has actually happened in the Target Project.
_Avoid_: chat state, plan text, agent claim

**Recovery Evidence**:
State Evidence sufficient to reconstruct a Ticket's Review Fixed Point, Final Artifact Identity, consumed Operational Retry, Formal Rework and DAG Revision budgets, findings, acceptance, and Ticket Lineage after start or resume.
_Avoid_: chat memory, Coordinator recollection, separate scheduler state
