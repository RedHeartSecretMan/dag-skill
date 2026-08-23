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
A Ticket whose integrated Final Artifact Identity, verification, Formal Review, Finding Dispositions, and tracker evidence agree and are persisted.
_Avoid_: worker-complete Ticket

**Authoritative Integration Baseline**:
The Target Project state that receives reviewed candidates and supplies the integrated bytes used for Ticket acceptance and downstream work.
_Avoid_: candidate workspace

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
The terminal outcome where effective Tickets remain unfinished, running Agent count is zero, and the Runnable Frontier is empty with evidenced causes.
_Avoid_: waiting

**Whole-DAG Acceptance Gate**:
The final verification of Approved Spec coverage, baseline integration, dependency consumption, current artifact evidence, project gates, and tracker consistency.
_Avoid_: final test

**Formal Rework**:
The single Coordinator-authorized return of a Ticket for implementation after accepting an in-scope blocking review or integration finding.
_Avoid_: Operational Retry

**DAG Revision**:
An evidence-backed replacement or restructuring of part of an Approved DAG that preserves acyclicity and provenance.
_Avoid_: retry, back edge

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

**Operational Retry**:
The single corrected redispatch available when an Agent, tool, profile, report, or integration failure prevents valid evidence for one Ticket attempt.
_Avoid_: Formal Rework

**Required Skill Bundle**:
The pinned, complete set of `implement`, `code-review`, `tdd`, and `codebase-design` Skills validated before Ticket work.
_Avoid_: optional helpers

**Authoring Skill**:
The Target Project capability that creates or revises Spec and Ticket content for an approved DAG Revision.
_Avoid_: DAG-native implementation

**Execution Agent**:
A fresh Agent assigned to implement exactly one Ticket and return a complete Implementation Handoff.
_Avoid_: Coordinator

**Implementation-Side Review**:
The independent Standards and Spec evidence produced within an applicable `implement` attempt before handoff.
_Avoid_: self-approval

**Implementation Handoff**:
The evidence boundary where an Execution Agent returns its candidate, verification, review artifacts, profiles, deviations, and blockers to the Coordinator.
_Avoid_: Ticket acceptance

**Review Sufficiency Gate**:
The Coordinator's check that independent review evidence is complete, current for the Final Artifact Identity, and adequate for adjudication and risk.
_Avoid_: automatic duplicate review

**Formal Review**:
The independent Standards and Spec evidence adopted by the Coordinator from a sufficient Implementation-Side Review or a fresh review dispatch.
_Avoid_: worker summary

**Review Fixed Point**:
The immutable pre-implementation baseline that bounds one Ticket's review surface.
_Avoid_: branch name

**Final Artifact Identity**:
The immutable commit or verifiable content snapshot covered by both review axes and checked on the Authoritative Integration Baseline.
_Avoid_: latest files

**Finding Disposition**:
The Coordinator's evidence-backed classification of a review finding as blocking, graph-changing, advisory, false positive, or unresolved.
_Avoid_: aggregate verdict

**DAG-Native Fallback**:
The disclosed direct dispatch of DAG roles for a validated Skill whose contract is inapplicable to the live host or Target Project, with equivalent gates.
_Avoid_: missing-bundle recovery

**Standards / Spec Reviewers**:
Independent Agents that evaluate the Final Artifact Identity against Target Project standards or the Approved Spec and Ticket acceptance criteria.
_Avoid_: implementer

**Normative Authority**:
A live governing source that defines authorized scope, intended semantics, acceptance, or delivery behavior for an Approved DAG.
_Avoid_: Agent report

**State Evidence**:
A live tracker, repository, test, or Formal Review artifact that substantiates Target Project state.
_Avoid_: chat state

**Recovery Evidence**:
State Evidence sufficient to reconstruct a Ticket's identities, ownership, profiles, checkpoints, budgets, review, integration, blockers, acceptance, and lineage across start, resume, or handoff.
_Avoid_: Coordinator memory
