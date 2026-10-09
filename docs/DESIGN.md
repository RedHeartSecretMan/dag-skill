# DAG Skill Design

This document explains the stable design choices behind the DAG Skill. [`SKILL.md`](../skill/dag/SKILL.md) is the Coordinator's normative entrypoint; [`ticket-execution.md`](../skill/dag/references/ticket-execution.md) is the Execution Agent's protocol. The remaining references define [Definition binding](../skill/dag/references/definition-binding.md) and [integration recovery](../skill/dag/references/integration-transitions.md), and [`CONTEXT.md`](../CONTEXT.md) is the shared glossary. The Target Project's live instructions and approved obligations remain authoritative for a run.

## Objective

The scheduler should make graph decisions, not manage a Ticket's internal engineering loop. A Ticket should keep moving while its objective, Accepted inputs, and Acceptance Obligation remain stable, even when it needs several implementation, test, Promotion Candidate, and review rounds.

The smallest architecture that preserves those boundaries is:

```text
thin Coordinator Agent
`-- end-to-end Execution Agent for one Ticket
    |-- tdd and codebase-design when applicable
    `-- code-review
```

This design exposes only graph-relevant outcomes to the Coordinator Agent. Test failures and ordinary review findings stay with the Ticket owner; acceptance and successor unlocking stay with the graph owner.

Context isolation follows the same ownership split. The Coordinator holds the whole-DAG state, while the Execution Agent receives one Ticket contract, an explicit [copyable protocol pointer](../skill/dag/references/ticket-execution.md), and a finalization instruction. Zero-history dispatch, or the smallest relevant history window, keeps unrelated graph state out of implementation context. The protocol supplies the non-obvious execution and handoff rules that workspace pointers alone cannot convey; the contract carries project constraints and existing approvals for the Agent and its downstream Agents.

Optional [shared exploration notes](../skill/dag/SKILL.md#dispatch-the-fixed-ticket-contract) can reduce repeated investigation across Tickets. Dispatch supplies relevant questions, reading conditions, and source/version pointers; consumers verify decisive facts against authoritative inputs and refresh affected conclusions when those inputs change. A completed note has one author and must be accessible from its consuming host. Its resource disposition follows existing retention rules, while formal research deliverables retain their Ticket acceptance obligations. Notes confer no product, dependency, or acceptance authority.

## Why there is no DAG Review Agent

`code-review` already defines its own review process. Repeating that process in the DAG contract would create two sources of truth, split finding ownership, and add lifecycle states without producing better evidence.

The Execution Agent invokes `code-review` and closes its in-scope findings. A Candidate Review Record binds the complete returned result to the fixed Ticket Base, candidate commit/tree, and evaluated range; the review output itself need not repeat those identities. The Coordinator verifies that evidence at handoff rather than repeating engineering review.

Recurring supported findings justify a causal audit of evidence-related neighboring paths within the same Ticket obligation. This keeps repair scope proportional to observed failures without adding an exhaustive matrix, repair limit, or review role. The [execution protocol](../skill/dag/references/ticket-execution.md#run-the-ticket-local-engineering-loop) owns this rule and the finding-disposition loop.

## State and ownership

Only one role may mutate each state surface at a time:

| State surface | Owner |
| --- | --- |
| Effective graph, claims, blockers, Runnable Frontier, acceptance | Coordinator Agent |
| DAG Definition binding and DAG Definition Checkpoints | Coordinator Agent |
| One Ticket workspace, implementation, gates, candidates, finding closure | Execution Agent |
| Review judgment for a fixed candidate | `code-review` |
| Integration Transition serialization and successor unlocking | Coordinator Agent |

One claim has one write-capable Execution Agent. A replacement is safe only after the previous writer has observably stopped and the existing workspace and evidence are handed over. This is an ownership invariant, not an assumption based on elapsed time.

Scheduling uses the live Runnable Frontier and the Skill's [independence, runtime-isolation, and capacity checks](../skill/dag/SKILL.md#compute-and-claim-the-runnable-frontier). Every claim or resume checks proposed assignments together with existing live claims, including the actual resources held by work awaiting finalization. Two or more qualifying Tickets preferentially implement and run focused checks concurrently; uncertain isolation or insufficient concurrent capacity falls back to feasible serial work. A worktree separates file copies, but does not by itself isolate shared interfaces or runtime resources. Routine Base advancement is handled by candidate refresh rather than prohibiting all concurrency, and a conflicting pair does not serialize unrelated eligible work. No mode switch or scheduler state is added.

Serial dispatch permits final gates and review directly. Concurrent work may defer finalization; the Coordinator later confirms the current Ticket Base and completion priority after preceding acceptance and required tracker updates. This avoids finalization on a known stale Base without adding another handshake to serial execution. The same owner and workspace continue, waiting is progress rather than an Execution Outcome, and capacity includes the Runtime Skills' internal Agents. Long repairs may yield completion priority to other eligible work; integration and acceptance remain serialized.

## DAG Definition binding

A Git-backed DAG must remain reconstructable without an untracked plan or available external service. The Coordinator binds governing Specs, effective Tickets, Hard Dependencies, and Acceptance Obligations to accepted integration history. Startup, Definition changes, and the final completion check account for each in-scope Spec obligation through an effective Ticket or an existing whole-DAG gate with a named owner. This checks delivery responsibility while the Execution Agent still discovers implementation probes. External trackers use complete normalized snapshots with source provenance. One DAG Definition Index selects the effective plan; its schema, object rules, equivalence, and exact-commit validator contract live in [`definition-binding.md`](../skill/dag/references/definition-binding.md). An already equivalent binding needs no new commit.

This is one deep Coordinator Agent interface: bind the DAG Definition and return the verified Accepted Integration Tip that future Tickets use as Ticket Base. The validator hides path normalization, targeted Git object inspection, schema, and identity checks behind one read-only command; it queries the index and selected paths without enumerating the full commit tree. Artifact discovery, snapshots, checkpoint review, and publication remain implementation details. The Execution Agent receives the same Ticket, Accepted inputs, Ticket Base, workspace, and authority pointers as before, so plan publication does not enlarge the Ticket-local context.

Run state is a different surface from the approved Definition. Claims, workspaces, liveness, and the Run Receipt stay off-delivery so recording a run does not change the artifact it describes. A source that mixes Definition and run state needs a project-defined split or normalized snapshot. Stable tracker or acceptance evidence enters history only when the project requires that audit trail; a checkpoint's own completion record stays off-delivery to avoid recursive identity changes.

Project-required stable tracker writes use the same DAG Definition Checkpoint path rather than a second state authority. The project determines timing and field mappings; the Coordinator's [tracker section](../skill/dag/SKILL.md#persist-target-project-required-stable-tracker-evidence) owns sequencing and pending-update handling. This keeps per-Ticket and explicitly batched rules distinct without inventing a tracker schema.

Unchanged Definition identities let a stable audit checkpoint receive fresh review focused on its changed tracker mappings and evidence. Changing the index or a selected input instead requires complete Definition rebinding and an acceptance-impact audit, even for an apparent metadata edit. The [Definition reference](../skill/dag/references/definition-binding.md#persist-required-stable-tracker-state) owns that classification and its scope-specific gates.

The Run Receipt supplies exact comparison identities for interrupted integration work. Its field inventory, frozen-evidence rules, and local or remote recovery cases have one authoritative home in [`integration-transitions.md`](../skill/dag/references/integration-transitions.md). Keeping those rules together avoids divergent startup and recovery recipes.

A Definition change is reviewed as its own isolated checkpoint, with gates scoped to the actual metadata change rather than automatic product-test reruns. It uses the same serialized promotion boundary as a Ticket candidate. This separates plan publication from product delivery while providing a verified downstream Ticket Base.

Later approved Definition changes preserve and pause affected Ticket ownership until the checkpoint completes; unaffected work may finish first. Promotion Candidates preserve the bound Definition. A Ticket that requires a Definition change therefore resumes from the completed checkpoint under the same owner and workspace, while transient run-state changes create no checkpoint.

A DAG Revision can invalidate prior acceptance. Affected Accepted or Superseded Tickets need a fresh audit against the new Definition or an approved reopening or reassignment of their obligations. Unclear rules remain Coordinator-owned decisions. The checkpoint freezes the resulting dispositions, and Complete is evaluated against the final Definition and its current evidence.

## Promotion Candidate identity invariants

A Ticket Base is fixed for one candidate lineage and its review. A review result is promotable only when all delivery bytes descend from that Ticket Base, preserve its bound DAG Definition Index, path set, and content identities, exclude transient run state, and have gates and a Candidate Review Record naming the same final candidate.

Parallel work can make a Ticket Base obsolete before promotion. The Coordinator explicitly assigns the current Accepted Integration Tip, and the same Ticket owner safely reapplies its delivery change and obtains fresh candidate-bound review. Gate refresh follows the execution protocol's [evidence-validity rule](../skill/dag/references/ticket-execution.md#keep-gate-evidence-valid): rerun invalidated and project-required candidate-specific checks; retain unchanged product results only with their original identities and a fresh equivalence and impact audit. Old records remain provenance rather than automatically becoming current evidence.

The DAG Integration Branch is a local ref kept out of every worktree. A serialized Integration Transition advances it directly from the recorded Base to one reviewed descendant commit using compare-and-swap and exact readback. This prevents merge-generated or amended bytes from bypassing review, avoids moving a checked-out branch, and makes downstream Bases deterministic. Graph and evidence remain fixed through completion; later evidence participates in the next graph recomputation.

The narrow `scripts/promote_local_transition.py` helper verifies the frozen request and performs local CAS and readback. Failed prerequisites stop ref mutation; post-CAS failures preserve the pending evidence for recovery. Evidence files, the Git ref, and receipt completion are separate persistence surfaces. The helper supplies no semantic acceptance, remote publication, or rollback; the [integration reference](../skill/dag/references/integration-transitions.md#start-one-serialized-transition) defines those boundaries.

Ticket acceptance is a semantic result; a DAG Milestone is the new artifact created by a non-empty Ticket candidate's completed Integration Transition. Definition checkpoints can advance the accepted tip without accepting a Ticket. Baseline Satisfaction and Superseded results can close graph obligations without creating a new artifact.

## Acceptance and integration publication

Accepted means every Ticket obligation is evidenced, not merely that tests pass or a candidate is committed. An approved verification, audit, or operational Ticket may define Baseline Satisfaction without product-byte changes; its existing contract supplies the rule without another approval solely for zero diff. Current Base/tree identities, a clean empty delivery diff, actual deliverables, and applicable authority still govern. The Coordinator owns the serialized acceptance decision; the [execution protocol](../skill/dag/references/ticket-execution.md#gather-zero-diff-evidence) owns the evidence handoff.

Product-equivalent metadata changes may retain valid product gates with their original artifact identities and a fresh equivalence and impact audit. Invalidated and project-required candidate-specific checks run again, and each new candidate receives fresh review. This preserves provenance without spending unchanged product-test effort on metadata. Operational deliverables and remote authority remain actual acceptance obligations.

Ticket acceptance history also needs an applicability check against the final Definition and Accepted Integration Tip. Execution Agents identify obligations affected by their later delivery changes within normal Ticket validation and review; the Coordinator verifies their dispositions. Final coverage links existing reports and retains their real Base, candidate, inputs, and environment. Whole-DAG gates use the final tip or earlier evidence whose applicability the project permits and an impact audit establishes. An unrelated Base advance alone does not reopen all Tickets or require all checks to run again. Unresolved defects or evidence gaps prevent Complete under the [completion rules](../skill/dag/SKILL.md#resume-safely-and-finish).

A proven failure returns to the effective obligation's responsible Ticket. An open Ticket continues its engineering loop; a closed one uses project reopening rules, required tracker checkpoints, and a restored single writer from the current Accepted Integration Tip. The [repair path](../skill/dag/SKILL.md#reopen-a-failed-accepted-obligation) preserves acceptance history and available workspaces, requires normal gates and fresh review, and pauses only consumers of invalidated outputs. Unaffected branches can continue. Responsibility, scope, dependency, or approved-meaning changes still use DAG Revision; unclear tracker mappings remain decisions owned by the Coordinator.

One run-level Integration Publication Mode keeps authorization predictable. Existing records or project requirements determine it; absent synchronization intent, Local-only remains the default even with configured remotes. Remote-mirrored maps one dedicated branch and requires authority for its exact remote/ref. An unambiguous synchronization instruction supplies that authority once. Missing mapping or remote-add authority remains a specific decision, and release operations retain their separate authorization boundary.

Remote initialization and established-mapping recovery differ because a missing new ref can be created while a missing established ref is drift. Recording the mapping and exact synchronized identities lets readback reconcile an unsent push or lost response without force-push, ref switching, or retry states. The [integration reference](../skill/dag/references/integration-transitions.md#complete-or-recover-the-transition) owns the allowed identity cases and recovery sequence.

## Progress without retry states

A fixed retry allowance is both too strict for difficult Tickets and too permissive for a loop doing the same ineffective work. A diagnostic attempt may eliminate a hypothesis without changing a Promotion Candidate or making a test pass. The execution rule therefore distinguishes an exhausted action from an exhausted path: stop repeating an unchanged failing action and use the evidence to choose another authorized diagnostic or repair path when one remains.

This keeps diagnosis and repair within the Ticket. A non-success Execution Outcome still requires evidence of its actual decision or unavailable external condition; one unsuccessful cycle alone establishes neither. No scheduler-level continuation state or fixed retry allowance is needed.

The graph changes only when the evidence changes a graph boundary: a prerequisite is missing, an edge is wrong, an Acceptance Obligation belongs to another Ticket, or the work has multiple independently acceptable results. Promotion Candidate count, diff size, and review count provide no such evidence.

## Recovery model

The Skill needs no separate scheduler database. Git-backed Definition and delivery evidence reconstruct the graph; a compact off-delivery Run Receipt indexes live ownership and recovery identities. Reports are linked rather than copied, so the receipt is a recovery index rather than another plan or evidence authority.

Run-owned resource records distinguish reclaimable inactive resources from live writers, unrelated resources, unique WIP or evidence, and required recovery material. Disposing of a resource requires preserved evidence and existing authority. Resource disposition is reported separately from Complete or Stalled so cleanup neither changes product acceptance nor grants destructive authority.

Authorized zero-diff external actions need recovery identities before invocation: the Ticket, target and artifact or necessary parameter identities, authority, and available query or idempotency correlation belong in the existing off-delivery recovery store. After a lost response or interruption, readback in the action's own system determines whether to observe a running operation, reuse a completed result, or safely continue. Missing or failed queries leave the result unresolved. The [zero-diff protocol](../skill/dag/references/ticket-execution.md#gather-zero-diff-evidence) owns this contract. Where reliable correlation or idempotency is unavailable, that limitation remains part of the next decision.

Recovery first resolves writer ownership. If liveness is uncertain, the existing claim and workspace remain untouched until the task is contacted, an acknowledged stop is obtained, or an authorized host-level termination establishes quiescence. The closing condition has an owner and a concrete recheck event, so “unknown” cannot silently become a duplicate writer or an unbounded retry loop. If the Agent must change, first confirm that the original Agent has stopped, then give the original Ticket, branch, worktree, and WIP to the replacement Agent.

Graph replacement uses the same boundary. Before a Ticket enters an active Integration Transition, it becomes a Superseded Ticket and closes its claim only after its writer is stopped and evidence is preserved; replacement work cannot begin while the old writer may still mutate the workspace. During a Transition, its frozen graph and evidence follow the [integration recovery rules](../skill/dag/references/integration-transitions.md#reconcile-the-local-integration-ref). Unrelated discoveries can await graph recomputation; evidence that disproves the candidate or its frozen evidence must follow those rules before acceptance. Accepted-obligation repair dispositions are recorded outside an active Transition.

An unresolved `Needs Decision` Execution Outcome is itself a live progression path, so it prevents a **Stalled** Terminal Outcome. The Coordinator Agent resolves it within existing authority or asks the user; only after the choice is made may any remaining unavailable condition be represented as an owned external block and participate in the whole-DAG terminal check.

## Runtime dependency bootstrap

The Execution Agent depends on the Runtime Skill Bundle: `tdd`, `codebase-design`, and `code-review`. Its anchored upstream commit is a minimum version. A complete Skill tree at that commit or a verified descendant meets the version requirement. Bootstrap records the Agent Host, stable Skills root, verified source commits, and content identities. A missing or unverified member is a recoverable Agent Host condition; the Coordinator Agent runs the bundled installer before the first claim when the complete bundle cannot be resolved and verified.

Copied Skill directories lack reliable Git identities. The installer recognizes exact anchor content offline and otherwise matches complete trees against upstream descendants; Git ancestry establishes the version floor independently of dates. This accepts intermediate newer versions, avoids downgrades, and preserves unverifiable or modified targets. Installer code and tests own the matching and conflict-preservation mechanics.

The optional `setup-matt-pocock-skills` helper is installed only for an explicit installation request or an already authorized configuration task that needs it. Existing authorization applies within its scope; installation alone does not authorize configuration.

Installation and runtime readiness are separate: the Agent Host must reload and resolve all three Runtime Skills before a Ticket is claimed. Startup does not execute a real Skill workflow as a probe. Missing capabilities or installation prerequisites leave one observable closing condition rather than a false readiness claim.

Runtime Skill invocations need the project's authoritative context and scoped existing approvals. The Ticket contract and [execution protocol](../skill/dag/references/ticket-execution.md#supply-runtime-skills) provide those inputs; an equivalent project tracker workflow can replace a dependency's conventional discovery path. Missing context is resolved as a specific gap without turning optional setup into a universal prerequisite.

Each DAG start or resume verifies the bundle once; ordinary Ticket execution uses that verified bundle without another dependency preflight.

## Compatibility boundary

The copyable artifact is [`skill/dag/`](../skill/dag/). Its references are disclosed by runtime branch; the Definition validator, Runtime Skill installer, and narrow local promotion helper each serve one existing contract. Validated Git evidence and active capabilities, rather than command exit alone, form the claim gate. A successful local promotion helper does not prove semantic acceptance or complete publication.

Delivery is intentionally Git-backed because the required `code-review` contract pins a Git fixed point, non-empty diff, candidate commit list, and `HEAD`. The Skill does not claim an equivalent non-Git review or promotion path.

The project intentionally adds no scheduler service, workflow DSL, model-profile negotiation layer, or compatibility state machine. Those mechanisms would add change surfaces without solving a demonstrated graph problem.
