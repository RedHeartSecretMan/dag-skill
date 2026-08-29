# DAG Skill Design

This document explains the stable design choices behind the DAG Skill. [`SKILL.md`](../skill/dag/SKILL.md) is the single normative runtime contract; [`CONTEXT.md`](../CONTEXT.md) is the shared glossary. The Git-backed Target Project's live instructions, any Specs, Tickets, tracker, repository, and acceptance rules remain authoritative for an actual run.

## Objective

The scheduler should make graph decisions, not manage a Ticket's internal engineering loop. A Ticket should keep moving while its objective, accepted inputs, and acceptance obligation remain stable, even when it needs several implementation, test, candidate, and review rounds.

The smallest architecture that preserves those boundaries is:

```text
thin Coordinator Agent
`-- end-to-end Execution Agent for one Ticket
    |-- tdd and codebase-design when applicable
    `-- code-review
```

This design exposes only graph-relevant outcomes to the Coordinator. Test failures and ordinary review findings stay with the Ticket owner; acceptance and successor unlocking stay with the graph owner.

## Why there is no DAG Review Agent

`code-review` already defines its own review process. Repeating that process in the DAG contract would create two sources of truth, split finding ownership, and add lifecycle states without producing better evidence.

The Execution Agent therefore invokes `code-review` and closes its in-scope findings. The Coordinator receives the complete result exactly as returned, wrapped by a candidate review record that binds the fixed Base, candidate commit/tree, and evaluated range. The wrapper matters because the review output itself does not need to repeat Git identities. A dismissal is valid only when its disposition carries stronger project evidence; a supported blocking finding cannot pass merely because it was labeled “handled.”

## State and ownership

Only one role may mutate each state surface at a time:

| State surface | Owner |
| --- | --- |
| Effective graph, claims, blockers, frontier, acceptance | Coordinator Agent |
| One Ticket workspace, implementation, gates, candidates, finding closure | Execution Agent |
| Review judgment for a fixed candidate | `code-review` |
| Serialized integration lane and successor unlocking | Coordinator Agent |

One claim has one write-capable Execution Agent. A replacement is safe only after the previous writer has observably stopped and the existing workspace and evidence are handed over. This is an ownership invariant, not an assumption based on elapsed time.

## Candidate identity invariants

A Ticket Base is fixed for one candidate lineage and its review. A review result is promotable only when all delivery bytes descend from that Base and the gates and review record name the same final candidate.

Parallel work can make a Base obsolete before promotion. Silently retaining the old Base would review accepted changes from other Tickets as though they belonged to the current Ticket; silently changing it would break the recorded identity. The Coordinator instead issues a new Base equal to the current Accepted tip. The same Ticket ownership then reapplies its delivery change, reruns invalidated gates, and obtains a new review record. The old record remains provenance, not promotion evidence.

The integration branch is kept as a local ref that is not checked out in any worktree. Promotion verifies that Candidate descends from Base, then atomically compares and swaps that ref from the exact Base to the exact Candidate and reads it back. This rules out merge-generated or amended bytes that were never present in the reviewed candidate and avoids moving a ref behind a checked-out worktree. Promotion is serialized even when implementation is parallel, which keeps acceptance order and downstream bases deterministic. The Coordinator revalidates the graph, candidate evidence, and Base before entering this lane, then holds them fixed through local promotion, any selected remote synchronization, and Accepted. Later graph evidence is processed after that transaction, avoiding a rollback protocol for an already promoted candidate.

Ticket and DAG Milestone describe different surfaces. A Ticket is the semantic acceptance unit; a DAG Milestone is the exact Git commit/tree produced only when that Ticket's non-empty final candidate clears the serialized acceptance lane and becomes the new Accepted integration tip. Candidate history before promotion is implementation evidence, not a milestone. Baseline Satisfaction and Superseded transitions may change graph state without moving the integration tip, so they create no new milestone.

## Acceptance and integration publication

Accepted is a semantic result, not a synonym for committed or Ready for Acceptance. The normal evidence path is a reviewed delivery candidate promoted with exact identity. A zero-diff Ticket is a different successful path only when the Target Project already defines its baseline-satisfaction contract and all required evidence is present. Its Base identity is rechecked under the same serialized acceptance lane so parallel promotion cannot make the audit stale. Otherwise it needs an explicit current-state audit or acceptance decision; manufacturing an empty commit would create form without evidence.

Publication is resolved once before the first Ticket claim. Local-only keeps the Accepted tip in the local repository. Remote-mirrored selects one configured Git remote and one dedicated remote integration branch, with run-level authority to create that branch and update it after each milestone. The local branch name is the default remote branch name. An explicit synchronization instruction is enough when the mapping is unambiguous; configured remotes without a stated intent require one mode decision. No configured remote and no synchronization requirement selects Local-only without a question. Required synchronization without a configured remote requires the user to supply its name and URL and authorize `git remote add` before work begins. This is a branch synchronization choice, not a second release protocol.

Only a Remote-mirrored mapping selected for the first time and proved by live recovery evidence never to have been initialized runs one ordinary `git push -u` from the current local integration tip to the selected remote branch. A missing receipt field alone is not proof of a new mapping. The push creates an absent branch, fast-forwards a branch that is behind, or confirms an aligned branch and its upstream. A matching readback completes initialization and becomes the last synchronized commit. A rejected push or different readback stops scheduling until the user or Target Project reconciles the branch or selects another dedicated branch. Writing a default or protected branch needs separate explicit authority. A PR-only branch blocks initialization; the DAG does not silently switch to a pull-request protocol. Ticket branches stay local, so the remote branch shows accepted DAG progress rather than implementation churn.

An existing mapping is never initialized again. Resume first reads the local integration ref, Run Receipt, and remote ref. Without a pending Candidate, both live refs must equal the recorded last synchronized commit. With a pending Candidate, the normal three-identity reconciliation below applies. A missing remote ref, another SHA, or an incomplete receipt is drift or unresolved recovery state and cannot be repaired by an initialization push.

For each non-empty candidate, the Coordinator first performs the same reviewed local ref update used by Local-only mode. Remote-mirrored then reconciles one remote ref from three identities: Candidate, the last synchronized commit, and the observed remote SHA. If the remote already equals Candidate, synchronization is complete. If it still equals the last synchronized commit, one ordinary fast-forward push is safe; only a Candidate readback succeeds. If the ref is absent or has any other SHA, it has drifted and no push is sent. A failed push or read leaves the Candidate pending; resume starts by reading again, which safely distinguishes an unsent push from a lost response without a retry counter or an extra marker. Acceptance, successor unlocking, the next claim, and another promotion all wait for Candidate equality. The Coordinator never force-pushes or silently selects another branch.

## Progress without retry states

A fixed retry allowance is both too strict for difficult Tickets and too permissive for a loop doing the same ineffective work. The design instead uses observable progress: a cycle must close a finding, change the candidate in response to a named finding or failed probe, repair a required gate, or produce new evidence that identifies a decision or external closing condition.

This yields one Ticket-local loop without scheduler-level “continuation” or “formal rework” states. A corrected command remains ordinary execution; repeating the same failed operation under the same conditions does not. The latter returns an evidenced decision or external block rather than consuming another arbitrary retry.

The graph changes only when the evidence changes a graph boundary: a prerequisite is missing, an edge is wrong, an Acceptance Obligation belongs to another Ticket, or the work has multiple independently acceptable results. Candidate count, diff size, and review count provide no such evidence.

## Recovery model

The Skill deliberately avoids a separate scheduler database. Live tracker and repository state remain authoritative, with a compact Run Receipt indexing identities, claims, outcomes, and closing conditions. The receipt lives outside delivery history: committing acceptance metadata after review would create an unreviewed descendant and make the next Base ambiguous.

Recovery first resolves writer ownership. If liveness is uncertain, the existing claim and workspace remain untouched until the task is contacted, an acknowledged stop is obtained, or an authorized host-level termination establishes quiescence. The closing condition has an owner and a concrete recheck event, so “unknown” cannot silently become a duplicate writer or an unbounded retry loop. If the Agent must change, first confirm that the original Agent has stopped, then give the original Ticket, branch, worktree, and WIP to the replacement Agent.

Graph replacement uses the same boundary. Before a Ticket enters the locked acceptance transaction, it becomes Superseded and closes its claim only after its writer is stopped and evidence is preserved; replacement work cannot begin while the old writer may still mutate the workspace. Once the transaction begins, the Ticket finishes local promotion, any selected remote synchronization, and Accepted under the graph and evidence checked at entry. Evidence arriving later participates in the next graph recomputation.

An unresolved Coordinator decision is itself a live progression path, so it prevents Stalled. Only after the choice is made may any remaining unavailable condition be represented as an owned external block and participate in the whole-DAG terminal check.

## Runtime dependency bootstrap

The Execution Agent depends on one pinned Runtime Skill Bundle: `tdd`, `codebase-design`, and `code-review`. Bootstrap is keyed by Agent Host, stable Skills root, and pinned revision/tree identities. A missing or mismatched member is a recoverable host condition, not a reason to claim a Ticket that cannot finish its contract. The Coordinator therefore runs the bundled installer by default before the first claim whenever that bootstrap identity cannot resolve the complete pinned bundle.

The installer is deterministic and conflict-safe: it reuses exact pinned Runtime Skill trees, creates missing directories, and refuses to replace any different existing target. The matching `setup-matt-pocock-skills` helper is not a runtime dependency and is installed only through the explicit `--include-setup-helper` option; project configuration remains a separate authorized mutation.

Installation completion and runtime readiness are separate checks. After file installation, the Agent Host reloads its Skill list and must resolve all three Runtime Skills. Startup does not run a real review or another Skill workflow as a probe. A host reload requirement, unresolved Skills root, incompatible existing target, unavailable Python/Git/network, or denied write leaves the Ticket unclaimed with one observable closing condition. This prevents a successful copy from being mistaken for an active capability.

Each DAG start or resume performs this check once. After it succeeds, every Ticket in that run uses the same verified bundle without another preflight; the installer is not part of the per-Ticket loop. A later start or resume checks again and installs only when a Runtime Skill is missing or its pinned identity no longer matches.

## Compatibility boundary

The copyable artifact is [`skill/dag/`](../skill/dag/). Its [`install_dependencies.py`](../skill/dag/scripts/install_dependencies.py) is the default recovery path for a missing Runtime Skill Bundle. The Skill keeps this bootstrap small and stateless; the active capabilities, rather than installer exit alone, form the claim gate.

Delivery is intentionally Git-backed because the required `code-review` contract pins a Git fixed point, non-empty diff, candidate commit list, and `HEAD`. The Skill does not claim an equivalent non-Git review or promotion path.

The project intentionally adds no scheduler service, workflow DSL, model-profile negotiation layer, or compatibility state machine. Those mechanisms would add change surfaces without solving a demonstrated graph problem.

## Behavioral checks

These scenarios exercise the design boundaries rather than its headings:

| Scenario | Expected result |
| --- | --- |
| Three successive candidates close different review findings | One Ticket execution ownership completes all rounds; only the final candidate record is promotable |
| An independent Ticket is accepted before this candidate | Coordinator issues a new Base; refreshed candidate descends from it and receives fresh gates and review |
| Ticket Base already satisfies the obligation with no diff | Evidence-complete project baseline rule yields Ready for Acceptance; absent that rule, an exact decision is requested |
| One or more Runtime Skill Bundle members are missing from a resolved host Skills root | Run the bundled installer by default, reload the Host Skill list, and confirm all three names resolve before claim |
| An existing Skill target differs from the pinned bundle | Preserve it, report the conflict, and keep Tickets unclaimed until the host dependency is reconciled |
| Installation succeeds but the Agent Host has not activated the new Skills | Record the required reload or new-task event; file presence alone does not permit claim |
| Several Tickets use the same verified bundle during one run | Do not check or execute the installer per Ticket |
| A later DAG start or resume uses the same host and unchanged pinned bundle | Perform the one startup check; do not install when all three Skills already match |
| Repository has remotes but no recorded publication mode | User selects Local-only or one configured remote/branch before the first claim |
| Repository has no remote but synchronization is required | Configure and select one remote/branch before the first claim |
| Remote-mirrored initialization | Use ordinary `git push -u` to create or fast-forward the selected branch, then verify its readback |
| An existing Remote-mirrored mapping resumes without a pending Candidate | Read local and remote identities; both must equal the recorded last synchronized commit, and no initialization push is sent |
| Initialization is non-fast-forward or reads back another SHA | Report both SHAs and wait for explicit reconciliation or another branch selection |
| Milestone push fails or its response is lost | Keep the local Candidate pending, read back, and complete synchronization before acceptance or further scheduling |
| Milestone push is non-fast-forward | Report both SHAs; never force-push or switch refs automatically |
| Remote integration ref is deleted or rewound after initialization | Treat the absent or unexpected SHA as drift and do not push until it is reconciled |
| Review launch fails because of a correctable path or environment error | Execution Agent corrects the cause and retries inside the Ticket loop |
| A Runtime Skill remains unresolved after installation and Host reload | Ticket remains unclaimed with an owned, observable external closing condition |
| Existing writer liveness cannot be established | Preserve the claim, branch, worktree, and WIP; no replacement writer starts before a quiescent handoff |
