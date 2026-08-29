# DAG Skill Design

This document explains the stable design choices behind the DAG Skill. [`SKILL.md`](../skill/dag/SKILL.md) is the single normative runtime contract; [`CONTEXT.md`](../CONTEXT.md) is the shared glossary. The Git-backed Target Project's live instructions, any Specs, Tickets, tracker, repository, and acceptance rules remain authoritative for an actual run.

## Objective

The scheduler should make graph decisions, not manage a Ticket's internal engineering loop. A Ticket should keep moving while its objective, accepted inputs, and acceptance obligation remain stable, even when it needs several implementation, test, candidate, and review rounds.

The smallest architecture that preserves those boundaries is:

```text
thin Coordinator Agent
`-- end-to-end Execution Agent for one Ticket
    `-- code-review (internal Standards and available Spec review contexts)
```

This design exposes only graph-relevant outcomes to the Coordinator. Test failures and ordinary review findings stay with the Ticket owner; acceptance and successor unlocking stay with the graph owner.

## Why there is no DAG Review Agent

`code-review` already creates an independent Standards context and an independent Spec context when an authoritative Spec source exists; confirmed absence is recorded as a skipped Spec axis, not independently reviewed. Recreating those contexts as DAG roles would give the Coordinator a second review workflow, split finding ownership, and add lifecycle states without producing more independent evidence.

The Execution Agent therefore invokes `code-review` and closes its in-scope findings. The Coordinator receives a candidate review record rather than managing reviewer identities. That record binds the fixed Base, candidate commit/tree, evaluated range, and the complete result containing both axes. The identity wrapper matters because the review text itself is not required to repeat Git identities. A dismissal is valid only when its disposition carries stronger project evidence; a supported blocking finding cannot pass merely because it was labeled “handled.”

## State and ownership

Only one role may mutate each state surface at a time:

| State surface | Owner |
| --- | --- |
| Effective graph, claims, blockers, frontier, acceptance | Coordinator Agent |
| One Ticket workspace, implementation, gates, candidates, finding closure | Execution Agent |
| Standards judgment and available Spec judgment for a fixed candidate | `code-review` review contexts |
| Serialized integration lane and successor unlocking | Coordinator Agent |

One claim has one write-capable Execution Agent. A replacement is safe only after the previous writer has observably stopped and the existing workspace and evidence are handed over. This is an ownership invariant, not an assumption based on elapsed time.

## Candidate identity invariants

A Ticket Base is fixed for one candidate lineage and its review. A review result is promotable only when all delivery bytes descend from that Base and the gates and review record name the same final candidate.

Parallel work can make a Base obsolete before promotion. Silently retaining the old Base would review accepted changes from other Tickets as though they belonged to the current Ticket; silently changing it would break the recorded identity. The Coordinator instead issues a new Base equal to the current Accepted tip. The same Ticket ownership then reapplies its delivery change, reruns invalidated gates, and obtains a new review record. The old record remains provenance, not promotion evidence.

The integration lane is fast-forward-only. This rules out merge-generated or amended bytes that were never present in the reviewed candidate. Promotion is serialized even when implementation is parallel, which keeps acceptance order and downstream bases deterministic. The Coordinator revalidates the graph, candidate evidence, and Base before entering this lane, then holds them fixed through local promotion, any selected remote synchronization, and Accepted. Later graph evidence is processed after that transaction, avoiding a rollback protocol for an already promoted candidate.

Ticket and DAG Milestone describe different surfaces. A Ticket is the semantic acceptance unit; a DAG Milestone is the exact Git commit/tree produced only when that Ticket's non-empty final candidate clears the serialized acceptance lane and becomes the new Accepted integration tip. Candidate history before promotion is implementation evidence, not a milestone. Baseline Satisfaction and Superseded transitions may change graph state without moving the integration tip, so they create no new milestone.

## Acceptance and integration publication

Accepted is a semantic result, not a synonym for committed or Ready for Acceptance. The normal evidence path is a reviewed delivery candidate promoted with exact identity. A zero-diff Ticket is a different successful path only when the Target Project already defines its baseline-satisfaction contract and all required evidence is present. Its Base identity is rechecked under the same serialized acceptance lane so parallel promotion cannot make the audit stale. Otherwise it needs an explicit current-state audit or acceptance decision; manufacturing an empty commit would create form without evidence.

Publication is chosen once when the run-scoped local integration branch is created or resumed. Local-only keeps the Accepted tip in the local repository. Remote-mirrored selects one configured Git remote and one remote integration branch, with run-level authority to create that branch and update it after each milestone. The local branch name is the default remote branch name. This is a branch synchronization choice, not a second release protocol.

Remote-mirrored initialization runs one ordinary `git push -u` from the current local integration tip to the selected remote branch. That operation creates an absent branch, fast-forwards a branch that is behind, or confirms an aligned branch and its upstream. A matching readback completes initialization. A rejected push or different readback stops scheduling until the user or Target Project reconciles the branch or selects another one. Ticket branches stay local, so the remote branch shows accepted DAG progress rather than implementation churn.

For each non-empty candidate, the Coordinator first performs the same reviewed fast-forward promotion on the local integration branch used by Local-only mode. Remote-mirrored then performs an ordinary fast-forward push to the selected remote branch and reads back the Candidate SHA. Acceptance and successor unlocking happen only after that readback. An interruption before push, a failed push, or a lost response leaves the local Candidate pending remote synchronization. Resume by reading the branch: accept immediately if it already matches, send an unsent push, repeat once after a lost response that did not synchronize, stop for explicit reconciliation after a non-fast-forward rejection, or correct any other reported cause before retrying. The Candidate-bound automatic-push-closed marker is persisted before a lost-response repeat. Whenever the remote is not the Candidate and that marker is missing, closed, or uncertain, automatic pushing stays closed and an owner plus recheck condition is recorded immediately; the same applies when a corrected retry repeats its error. The Coordinator never force-pushes or silently selects another branch, and a synchronization problem does not revise the Ticket DAG.

## Progress without retry states

A fixed retry allowance is both too strict for difficult Tickets and too permissive for a loop doing the same ineffective work. The design instead uses observable progress: a cycle must close a finding, change the candidate in response to a named finding or failed probe, repair a required gate, or produce new evidence that identifies a decision or external closing condition.

This yields one Ticket-local loop without scheduler-level “continuation” or “formal rework” states. A corrected command remains ordinary execution; repeating the same failed operation under the same conditions does not. The latter returns an evidenced decision or external block rather than consuming another arbitrary retry.

The graph changes only when the evidence changes a graph boundary: a prerequisite is missing, an edge is wrong, an Acceptance Obligation belongs to another Ticket, or the work has multiple independently acceptable results. Candidate count, diff size, and review count provide no such evidence.

## Recovery model

The Skill deliberately avoids a separate scheduler database. Live tracker and repository state remain authoritative, with a compact Run Receipt indexing identities, claims, outcomes, and closing conditions. The receipt lives outside delivery history: committing acceptance metadata after review would create an unreviewed descendant and make the next Base ambiguous.

Recovery first resolves writer ownership. If liveness is uncertain, the existing claim and workspace remain untouched until the task is contacted, an acknowledged stop is obtained, or an authorized host-level termination establishes quiescence. The closing condition has an owner and a concrete recheck event, so “unknown” cannot silently become a duplicate writer or an unbounded retry loop.

Graph replacement uses the same boundary. Before a Ticket enters the locked acceptance transaction, it becomes Superseded and closes its claim only after its writer is stopped and evidence is preserved; replacement work cannot begin while the old writer may still mutate the workspace. Once the transaction begins, the Ticket finishes local promotion, any selected remote synchronization, and Accepted under the graph and evidence checked at entry. Evidence arriving later participates in the next graph recomputation.

An unresolved Coordinator decision is itself a live progression path, so it prevents Stalled. Only after the choice is made may any remaining unavailable condition be represented as an owned external block and participate in the whole-DAG terminal check.

## Compatibility boundary

The copyable artifact is [`skill/dag/`](../skill/dag/). Its optional [`install_dependencies.py`](../skill/dag/scripts/install_dependencies.py) is retained because it was previously published and still provides conflict-safe installation of a pinned support bundle. It is not a runtime state machine or global scheduling gate; capability is checked where a Ticket needs it.

Delivery is intentionally Git-backed because the required `code-review` contract pins a Git fixed point, non-empty diff, candidate commit list, and `HEAD`. The Skill does not claim an equivalent non-Git review or promotion path.

The project intentionally adds no scheduler service, workflow DSL, model-profile negotiation layer, or compatibility state machine. Those mechanisms would add change surfaces without solving a demonstrated graph problem.

## Behavioral checks

These scenarios exercise the design boundaries rather than its headings:

| Scenario | Expected result |
| --- | --- |
| Three successive candidates close alternating Spec and Standards findings | One Ticket execution ownership completes all rounds; only the final candidate record is promotable |
| An independent Ticket is accepted before this candidate | Coordinator issues a new Base; refreshed candidate descends from it and receives fresh gates and review |
| Ticket Base already satisfies the obligation with no diff | Evidence-complete project baseline rule yields Ready for Acceptance; absent that rule, an exact decision is requested |
| Repository has remotes but no recorded publication mode | User selects Local-only or one configured remote/branch before the first claim |
| Repository has no remote but synchronization is required | Configure and select one remote/branch before the first claim |
| Remote-mirrored initialization | Use ordinary `git push -u` to create or fast-forward the selected branch, then verify its readback |
| Initialization is non-fast-forward or reads back another SHA | Report both SHAs and wait for explicit reconciliation or another branch selection |
| Milestone push fails or its response is lost | Keep the local Candidate pending, read back, and complete synchronization before acceptance or further scheduling |
| Milestone push is non-fast-forward | Report both SHAs; never force-push, switch refs automatically, or revise the DAG |
| Review launch fails because of a correctable path or environment error | Execution Agent corrects the cause and retries inside the Ticket loop |
| Review capability is unavailable before claim | Ticket remains unclaimed with an owned, observable external closing condition |
| Existing writer liveness cannot be established | Claim and workspace are preserved; no replacement writer starts before a quiescent handoff |
