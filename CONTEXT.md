# DAG Coordination

This context defines the shared language for advancing an approved Ticket dependency graph from a Target Project's live evidence.

## Language

**Target Project**:
The Git-backed project whose live instructions, any Specs, Tickets, tracker, repository, and acceptance rules govern one DAG run.
_Avoid_: DAG Skill repository, chat snapshot

**Approved DAG**:
A user-approved acyclic graph of delivery Tickets governed by the Target Project.
_Avoid_: draft plan, generated backlog

**Ticket**:
One acceptance-scoped unit of delivery in an Approved DAG.
_Avoid_: prompt, retry, implementation phase

**Acceptance Obligation**:
The externally observable result and evidence that one Ticket is responsible for satisfying.
_Avoid_: implementation task, file ownership

**Hard Dependency**:
A directed relationship in which a dependent Ticket consumes an Accepted output of its prerequisite.
_Avoid_: preferred order, shared-file relationship

**Accepted Ticket**:
A Ticket whose Acceptance Obligation is satisfied by verified evidence and every checkpoint required by the selected Integration Publication Mode.
_Avoid_: implementation complete, candidate ready, locally committed

**Superseded Ticket**:
A Ticket removed from the effective DAG by an approved rule or decision, with its Acceptance Obligation proved already satisfied or assigned to an effective Ticket.
_Avoid_: abandoned Ticket, hidden rejection

**Runnable Frontier**:
The open Tickets whose Hard Dependencies and blockers are clear and that can start within current authority and isolated write boundaries.
_Avoid_: ready label, all unclaimed Tickets

**Coordinator Agent**:
The single Agent responsible for graph state, scheduling, assignment, acceptance decisions, and successor unlocking.
_Avoid_: implementer, duplicate reviewer

**Execution Agent**:
The Agent responsible for one Ticket through implementation, verification, review finding closure, and one stable Execution Outcome.
_Avoid_: Ticket scheduler, acceptance authority

**Ticket Base**:
The Accepted Git commit against which one Promotion Candidate is built and evaluated; it stays fixed for that candidate.
_Avoid_: moving branch name, latest review summary

**DAG Integration Branch**:
The run-scoped local Git branch that serializes reviewed candidates into the Accepted delivery baseline from which Tickets start and successors unlock.
_Avoid_: Ticket branch, default branch, scheduler database

**DAG Milestone**:
The exact commit and tree established as the new Accepted DAG Integration Branch tip after one non-empty Promotion Candidate clears the serialized acceptance lane.
_Avoid_: Ticket-branch candidate, intermediate commit, zero-diff acceptance

**Integration Publication Mode**:
The run-level choice made when the DAG Integration Branch is created or resumed: Local-only, or Remote-mirrored to one selected remote integration branch synchronized before each new milestone is Accepted.
_Avoid_: incidental remote configuration, per-Ticket push choice

**Promotion Candidate**:
A fixed Git commit and tree whose delivery bytes, required gates, and Candidate Review Record agree.
_Avoid_: working tree, latest files

**Two-axis Review**:
Independent Standards evidence plus either independent Spec evidence or a confirmed no-Spec record for one fixed Promotion Candidate.
_Avoid_: scheduling role, self-review

**Candidate Review Record**:
Evidence that binds one Ticket Base, one Promotion Candidate identity, the evaluated range, and the complete Two-axis Review result.
_Avoid_: unbound review text, reviewer identity

**Execution Outcome**:
One of three reports from an Execution Agent: Ready for Acceptance, Needs Coordinator Decision, or Externally Blocked.
_Avoid_: tracker status, Ticket acceptance

**DAG Revision**:
An evidence-backed graph change required by a missing prerequisite, invalid dependency, an Acceptance Obligation assigned to the wrong Ticket, or independently acceptable replacement results.
_Avoid_: review repair, renamed retry

**Terminal Outcome**:
Either Complete, where every effective Ticket is Accepted and superseded obligations are accounted for, or Stalled, where unfinished work has no authorized path that can currently advance it.
_Avoid_: waiting, unsynchronized Remote-mirrored run
