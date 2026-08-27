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

**Ticket Execution Contract**:
The claim-time projection of one approved Ticket into its owned acceptance obligation, accepted direct inputs, delivered output, acceptance-to-probe map, scope, required gates, and applicable authority-defined behavior constraints.
_Avoid_: new Spec, implementation plan

**Accepted Ticket**:
A Ticket whose Final Artifact Identity is promoted to a DAG Milestone and whose verification, Formal Review, Finding Dispositions, tracker evidence, and required Remote Checkpoint agree.
_Avoid_: implementation-complete Ticket

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
_Avoid_: Execution Agent checkpoint, candidate commit

**Remote Checkpoint**:
Verified equality between a DAG Milestone and its selected remote DAG branch after authorized fast-forward publication.
_Avoid_: push attempt, remote backup

**Delivery-affecting Change**:
A change that can alter accepted behavior, verification, dependencies, generated delivery artifacts, acceptance-bearing content, or a required gate and therefore invalidates the affected delivery evidence.
_Avoid_: every commit

**Evidence-only Change**:
A change that records coordination state or evidence without changing the delivery surface, allowing current delivery tests and review to remain valid after the delta is verified.
_Avoid_: product documentation change

**Whole-Graph Validity Gate**:
The pre-scheduling validation that a DAG Projection is approved, resolvable, contract-complete, acyclic, and aligned with current acceptance evidence.
_Avoid_: cycle check

**Runnable Frontier**:
The Tickets currently eligible for dispatch through accepted dependencies, cleared blockers, a complete Ticket Execution Contract, valid authority, verified profiles, recovery persistence, and safe write boundaries.
_Avoid_: ready status

**Continuous Scheduling**:
The Coordinator Agent's repeated live reconciliation, frontier calculation, dispatch, adjudication, integration, acceptance, and successor unlocking under DAG Run Authorization.
_Avoid_: background daemon

**Safe Parallelism**:
Concurrent execution of graph-independent frontier Tickets with isolated write and integration boundaries.
_Avoid_: maximum fan-out

**Complete**:
The terminal outcome where every effective Ticket is Accepted and the Whole-DAG Acceptance Gate passes.
_Avoid_: Agent work finished

**Stalled**:
The terminal outcome where effective Tickets remain unfinished, running Agent count is zero, the Runnable Frontier is empty, and no authorized recovery or graph transition can make progress.
_Avoid_: waiting

**Whole-DAG Acceptance Gate**:
The final verification of Approved Spec coverage, DAG Milestones, dependency consumption, current artifact evidence, project gates, tracker consistency, and required Remote Checkpoints.
_Avoid_: final test

**Formal Rework**:
The single second Ticket Attempt authorized by the Coordinator Agent after it accepts an in-scope blocking finding in a candidate that cleared the Implementation Handoff gate.
_Avoid_: Operational Recovery

**DAG Revision**:
An evidence-backed replacement or restructuring of part of an Approved DAG that preserves acyclicity and provenance and demonstrates Structural Progress.
_Avoid_: retry, back edge

**Structural Progress**:
A DAG Revision's evidenced movement toward delivery through narrower acceptance ownership, a consumed prerequisite, an invariant assigned to its owning seam, a corrected dependency, or an evidenced disposition.
_Avoid_: revision count, renamed retry

**Equivalent Revision**:
A proposed DAG Revision that reproduces a failed ancestor's effective delivery objective, acceptance ownership, hard dependencies, and owning seam under a new identity.
_Avoid_: Structural Progress

**Independent Acceptance**:
A Ticket property where accepted hard-predecessor outputs plus the Ticket's own artifact and public seams suffice to decide its acceptance.
_Avoid_: file split, implementation phase

**Ticket Lineage**:
The provenance chain connecting an original Ticket to every replacement Ticket or subgraph created through DAG Revision.
_Avoid_: retry sequence

**Superseded Ticket**:
A historical Ticket retained as provenance after an approved replacement Ticket or subgraph assumes its delivery role.
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

DAG coordination uses exactly three Agent roles: Coordinator Agent, Execution Agent, and Review Agent. Chinese documentation names them 主 Agent, 执行 Agent, and 审查 Agent; Ticket Worker Protocol and Worker Self-Check are Execution Agent workflows, while Standards and Spec are Review Agent review axes.

**Agent Host**:
The runtime environment that provides Skills, fresh role-isolated Agent contexts, observable execution, and governed Target Project access.
_Avoid_: model

**Coordinator Agent**:
The single primary Agent in a DAG run, accountable for live reconciliation, graph scheduling, evidence adjudication, integration, revision decisions, and final acceptance.
_Avoid_: implementer, reviewer

**Agent Profile**:
The run-scoped assignment of an available Agent to a DAG role, including observable model, reasoning effort, tools, capabilities, and explicitly unknown metadata fields.
_Avoid_: fixed default model

**Ticket Attempt**:
A persisted implementation-to-integration cycle created by the initial Ticket claim or its single Formal Rework; its one directed-continuation entitlement, Operational Recovery, external-blocker suspension, and pending write-safety boundary remain attached to that cycle.
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
The DAG-native contract that gives one fresh Execution Agent one Ticket, its fixed scope and public test seams, TDD implementation or baseline-satisfaction proof, independent pre-handoff review, finding closure, final-byte verification, candidate identity, and terminal Implementation or Blocked Handoff.
_Avoid_: generic task prompt

**Spec/Ticket Authoring Process**:
The Target Project's governed process for creating or revising Spec and Ticket content under its Tracker Contract.
_Avoid_: Authoring Skill, DAG-native implementation

**Execution Agent**:
A fresh Agent assigned to advance exactly one Ticket through one finite Worker Self-Check and return either an Implementation Handoff or a Blocked Handoff.
_Avoid_: Coordinator Agent, Review Agent

**Worker Self-Check**:
The finite Execution Agent workflow that establishes causal, baseline-satisfaction, or equivalent delivery evidence, current final-byte gates, complete read-only review coverage, bounded repair, and terminal review coverage before Handoff.
_Avoid_: Formal Review, self-approval

**Review Candidate**:
The immutable clean Ticket commit reviewed after initial TDD implementation or verified baseline satisfaction and applicable final-byte gates pass.
_Avoid_: working tree, Final Artifact Identity

**Final Candidate**:
The immutable clean Ticket commit returned at the end of an Execution Agent dispatch, equal to the current Review Candidate or containing the bounded repair delta covered by its terminal review.
_Avoid_: DAG Milestone

**Targeted Closure Review**:
The single read-only terminal review of a bounded Execution Agent repair, limited to the repair-target findings, repair delta, and directly affected contract surface.
_Avoid_: Targeted Formal Review, repair loop

**Implementation Handoff**:
The terminal Execution Agent result that returns a Final Candidate with causal, baseline-satisfaction, or equivalent delivery evidence, current gates, complete pre-handoff review, finding responses, and terminal review coverage for every repair.
_Avoid_: Ticket acceptance

**Blocked Handoff**:
The terminal Execution Agent result that preserves its latest candidate and evidence when a credible blocker, failed Targeted Closure Review, graph condition, or external condition prevents an Implementation Handoff.
_Avoid_: automatic retry, Formal Rework

**Review Sufficiency Gate**:
The Coordinator Agent's choice to adopt current pre-handoff review evidence, supplement an identifiable gap with targeted review, or obtain complete fresh review for a fixed handed-off or aligned candidate.
_Avoid_: automatic duplicate review

**Targeted Formal Review**:
A Coordinator Agent-requested independent review of one identified uncertainty in a handed-off or aligned fixed artifact.
_Avoid_: Targeted Closure Review, full Formal Review

**Formal Review**:
The body of independent Standards and Spec reports plus verified post-review closure evidence that the Coordinator Agent accepts for one Final Artifact Identity.
_Avoid_: Execution Agent summary

**Review Fixed Point**:
The immutable DAG Integration Branch commit that bounds an aligned candidate's Formal Review and promotion.
_Avoid_: Ticket Base, branch name

**Final Artifact Identity**:
The immutable aligned candidate commit or verifiable content snapshot that clears the Review Sufficiency Gate and is promoted without byte changes.
_Avoid_: latest files

**Finding Disposition**:
The Coordinator Agent's evidence-backed classification of a review finding as blocking, graph-changing, advisory, false positive, or unresolved.
_Avoid_: aggregate verdict

**Review Agent**:
An independent Agent that evaluates one fixed Review Candidate, Final Candidate, or Final Artifact Identity along the Standards axis, the Spec axis, or a defined targeted-review scope.
_Avoid_: Coordinator Agent, Execution Agent, implementer

**Normative Authority**:
A live governing source that defines authorized scope, intended semantics, acceptance, or delivery behavior for an Approved DAG; Agent-authored State Evidence can cite but cannot narrow it.
_Avoid_: Agent report

**State Evidence**:
A live tracker, repository, test, or Formal Review artifact that substantiates Target Project state.
_Avoid_: chat state

**Recovery Evidence**:
State Evidence sufficient to reconstruct a Ticket's identities, ownership, profiles, workspace, checkpoints, directed-continuation state, Formal Rework, operational causes and corrections, review, DAG Milestone, Remote Checkpoint, blockers, acceptance, and lineage across start, resume, or handoff.
_Avoid_: Coordinator Agent memory

**Run Receipt**:
The compact tracker-or-repository index of the current DAG Milestone, last recorded and pending remote checkpoints, frontier, active Ticket identities, Agent checkpoints, and live closing conditions, with detailed Recovery Evidence retained at its authoritative locations.
_Avoid_: scheduler database, duplicate evidence archive
