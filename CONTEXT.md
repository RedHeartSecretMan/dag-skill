# DAG Coordination

This context defines the shared language for coordinating an approved directed acyclic execution graph while preserving the Target Project's delivery contracts.

## Graph and delivery

**Target Project**:
The project whose approved delivery work, live rules, tracker, repository, and evidence govern a DAG run.
_Avoid_: template project

**DAG**:
A finite directed acyclic graph whose Ticket nodes and dependency edges form an execution plan.
_Avoid_: queue, checklist

**Graph Engineering**:
The discipline of making graph topology determine coordinated execution order and Safe Parallelism.
_Avoid_: agent swarm

**Approved DAG**:
A user-approved execution input grounded in an Approved Spec and its decomposed Tickets.
_Avoid_: draft plan

**DAG Projection**:
The carrier-neutral live view of an Approved DAG used for validation and scheduling while the Target Project remains authoritative.
_Avoid_: shadow tracker

**Ticket**:
One executable, acceptance-scoped unit of delivery in an Approved DAG.
_Avoid_: prompt, step

**Accepted Ticket**:
A Ticket whose Final Artifact Identity is promoted to a DAG Milestone and whose verification, Formal Review, Finding Dispositions, tracker evidence, and required Remote Checkpoint agree.
_Avoid_: worker-complete Ticket

**DAG Integration Branch**:
The run-scoped Git branch that advances only to locally verified DAG Milestones and supplies accepted baselines for downstream Tickets.
_Avoid_: candidate branch, main branch

**Ticket Base**:
The accepted DAG Integration Branch tip, including the Approved Baseline, from which one Ticket Attempt's isolated work begins.
_Avoid_: Review Fixed Point

**Ticket Workspace**:
The ticket-scoped branch and isolated worktree assigned to one write-capable Execution Agent.
_Avoid_: DAG Integration Branch, shared checkout

**DAG Milestone**:
The locally verified DAG Integration Branch tip produced by one Ticket or governed DAG Revision.
_Avoid_: worker checkpoint, candidate commit

**Remote Checkpoint**:
Verified equality between a DAG Milestone and its selected remote DAG branch after authorized fast-forward publication.
_Avoid_: push attempt, remote backup

**Whole-Graph Validity Gate**:
The pre-scheduling validation that a DAG Projection is approved, resolvable, contract-complete, acyclic, and aligned with current acceptance evidence.
_Avoid_: cycle check

**Runnable Frontier**:
The Tickets currently eligible for dispatch through accepted dependencies, cleared blockers, valid authority, verified profiles, recovery persistence, and safe write boundaries.
_Avoid_: ready status

**Continuous Scheduling**:
The Coordinator's repeated live reconciliation, frontier calculation, dispatch, adjudication, integration, acceptance, and successor unlocking under DAG Run Authorization.
_Avoid_: background daemon

**Safe Parallelism**:
Concurrent execution of graph-independent frontier Tickets with isolated write and integration boundaries.
_Avoid_: maximum fan-out

**Complete**:
The terminal outcome where every effective Ticket is Accepted and the Whole-DAG Acceptance Gate passes.
_Avoid_: workers done

**Stalled**:
The terminal outcome where effective Tickets remain unfinished, running Agent count is zero, the Runnable Frontier is empty, and no authorized recovery or graph transition can make progress.
_Avoid_: waiting

**Whole-DAG Acceptance Gate**:
The final verification of Approved Spec coverage, DAG Milestones, dependency consumption, current artifact evidence, project gates, tracker consistency, and required Remote Checkpoints.
_Avoid_: final test

**Formal Rework**:
The single Coordinator-authorized second Ticket Attempt after accepting an in-scope blocking finding in a candidate that cleared the Implementation Handoff gate.
_Avoid_: Operational Recovery

**DAG Revision**:
An evidence-backed replacement or restructuring of part of an Approved DAG that preserves acyclicity and provenance and demonstrates Structural Progress.
_Avoid_: retry, back edge

**Structural Progress**:
A DAG Revision's demonstrated reduction or clarification of remaining work through a smaller objective, a missing prerequisite, a corrected dependency, or an evidenced disposition.
_Avoid_: revision count, renamed retry

**Ticket Lineage**:
The provenance chain connecting an original Ticket to every replacement Ticket or subgraph created through DAG Revision.
_Avoid_: retry sequence

**Superseded Ticket**:
A historical Ticket retained as provenance after an approved replacement subgraph assumes its delivery role.
_Avoid_: deleted Ticket

**Tracker Contract**:
The Target Project's authoritative rules for Ticket representation, claiming, transitions, evidence, and acceptance across any carrier.
_Avoid_: tracker format

**DAG Run Authorization**:
The user's authorization to execute, advance, continue, or resume an Approved DAG through its locally auditable operations; High-impact Operations use separate authorization.
_Avoid_: blanket authorization

**Remote Checkpoint Authorization**:
The user's run-scoped authorization to publish each DAG Milestone to one selected remote DAG branch and verify the resulting remote ref.
_Avoid_: blanket push authorization

**High-impact Operation**:
An operation with separate authorization because it mutates an external system, performs destructive Git work, changes approved product semantics, or weakens a gate.
_Avoid_: local DAG operation

## Roles and evidence

**Agent Host**:
The runtime environment that provides Skills, fresh role-isolated Agent contexts, observable execution, and governed Target Project access.
_Avoid_: model

**Coordinator**:
The primary Agent accountable for live reconciliation, graph scheduling, evidence adjudication, integration, revision decisions, and final acceptance.
_Avoid_: implementer, reviewer

**Execution Profile**:
The run-scoped assignment of an available Agent to a DAG role, including observable model, reasoning effort, tools, capabilities, and explicitly unknown metadata fields.
_Avoid_: fixed default model

**Ticket Attempt**:
A persisted implementation-to-integration cycle created by the initial Ticket claim or its single Formal Rework; continuation, Operational Recovery, external-blocker suspension, and a pending write-safety boundary preserve the same cycle.
_Avoid_: Agent dispatch

**Operational Recovery**:
A cause-scoped correction and rerun after an Agent, tool, profile, report, or integration failure prevents valid evidence. It remains within the current Ticket Attempt; the same cause repeating after correction becomes an Operational Blocker.
_Avoid_: Formal Rework

**Invocation Correction**:
A corrected command, path, patch, or dispatch request after the attempted action did not start or reach its intended boundary.
_Avoid_: Operational Recovery, Formal Rework

**Operational Blocker**:
An evidenced operational cause that repeats after its correction without an advancing milestone, or whose closing condition requires unavailable authority or capability.
_Avoid_: implementation defect

**Runtime Skill Bundle**:
The pinned, complete set of model-invoked `code-review`, `tdd`, and `codebase-design` Skills required during DAG execution.
_Avoid_: optional helpers

**Ticket Worker Protocol**:
The DAG-native contract that gives one fresh Execution Agent one Ticket, its fixed scope and public test seam, TDD implementation, independent pre-handoff review, finding closure, final-byte verification, candidate identity, and Implementation Handoff.
_Avoid_: generic task prompt

**Spec/Ticket Authoring Process**:
The Target Project's governed process for creating or revising Spec and Ticket content under its Tracker Contract.
_Avoid_: Authoring Skill, DAG-native implementation

**Execution Agent**:
A fresh Agent assigned to advance exactly one Ticket through Worker Self-Check and return either an Implementation Handoff or an evidenced blocked result at a bounded checkpoint.
_Avoid_: Coordinator

**Worker Self-Check**:
The Execution Agent-owned, checkpoint-bounded pre-handoff loop that uses TDD, independent Standards and Spec review, finding repair, and final-byte verification to close one Ticket candidate before handoff.
_Avoid_: Formal Review, self-approval

**Implementation Handoff**:
The evidence boundary where an Execution Agent returns its committed review and final candidates, raw Worker review reports, finding responses, repair closure, verification, profiles, deviations, and blockers to the Coordinator.
_Avoid_: Ticket acceptance

**Review Sufficiency Gate**:
The Coordinator's choice to adopt current Worker review evidence, supplement an identifiable gap with targeted review, or obtain complete fresh review for the Final Artifact Identity.
_Avoid_: automatic duplicate review

**Formal Review**:
The Coordinator-approved body of independent Standards and Spec reports plus any verified post-review closure evidence for one Final Artifact Identity.
_Avoid_: worker summary

**Review Fixed Point**:
The immutable DAG Integration Branch commit that bounds an aligned candidate's Formal Review and promotion.
_Avoid_: Ticket Base, branch name

**Final Artifact Identity**:
The immutable aligned candidate commit or verifiable content snapshot that clears the Review Sufficiency Gate and is promoted without byte changes.
_Avoid_: latest files

**Finding Disposition**:
The Coordinator's evidence-backed classification of a review finding as blocking, graph-changing, advisory, false positive, or unresolved.
_Avoid_: aggregate verdict

**Standards / Spec Reviewers**:
Independent Agents that evaluate one fixed Review Candidate or Final Artifact Identity against Target Project standards or the Approved Spec and Ticket acceptance criteria.
_Avoid_: implementer

**Normative Authority**:
A live governing source that defines authorized scope, intended semantics, acceptance, or delivery behavior for an Approved DAG.
_Avoid_: Agent report

**State Evidence**:
A live tracker, repository, test, or Formal Review artifact that substantiates Target Project state.
_Avoid_: chat state

**Recovery Evidence**:
State Evidence sufficient to reconstruct a Ticket's identities, ownership, profiles, workspace, checkpoints, Formal Rework, operational causes and corrections, review, DAG Milestone, Remote Checkpoint, blockers, acceptance, and lineage across start, resume, or handoff.
_Avoid_: Coordinator memory
