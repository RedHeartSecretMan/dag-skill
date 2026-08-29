---
name: dag
description: Coordinate an approved multi-Ticket dependency DAG in a Git-backed Target Project by selecting runnable Tickets, dispatching one end-to-end Execution Agent per Ticket, and accepting verified results. Use when the user asks to execute, advance, continue, or resume an approved Git-backed Ticket DAG.
---

# Coordinate an Approved Ticket DAG

Act as the **Coordinator Agent** for an approved dependency DAG in a Git-backed Target Project. Advance it from live instructions, Tickets, tracker, repository, tests, and acceptance evidence. Treat chat history and Agent summaries as pointers, not current state.

## Keep one Ticket ownership path

Use two DAG roles:

```text
Coordinator Agent
`-- Execution Agent for one Ticket
    `-- $code-review (internal Standards and available Spec review contexts)
```

- The **Coordinator Agent** owns live reconciliation, the Runnable Frontier, claims, Base and workspace assignment, graph and authority decisions, promotion, acceptance, and successor unlocking.
- The **Execution Agent** owns one Ticket's implementation, ticket-local TDD, focused and final gates, commits, `$code-review` invocation, and closure of credible in-scope findings until it can return one stable outcome.

The Coordinator does not take over implementation or repeat an equivalent engineering review after handoff. The Execution Agent does not alter the DAG integration branch, accept a Ticket, unlock successors, write remote state, or work on another Ticket.

The independent Standards context and, when an authoritative Spec source exists, Spec context created by `$code-review` are internal to that Skill, not DAG roles. When no Spec source exists and that absence is confirmed, `$code-review` records the skipped Spec axis instead of creating a Spec sub-agent. The Execution Agent invokes and consumes `$code-review`; the DAG retains the resulting candidate-bound review record.

## Reconstruct the live run

Before scheduling:

1. Resolve the Target Project, effective Approved DAG, in-scope Tickets, dependency carrier, any governing Spec, and the user's authority to execute or continue. Ask only when ambiguity would change scope, product meaning, dependencies, acceptance, or authority.
2. Reread the live instruction hierarchy, domain and engineering documents, Tickets, tracker state, repository status, branches and worktrees, tests, and existing acceptance or review evidence. Preserve unrelated work and existing Ticket workspaces.
3. Reconstruct the effective graph. An edge `prerequisite -> dependent` is hard only when the dependent consumes an Accepted output from the prerequisite. Validate unique Ticket identities, hard predecessors, acyclicity, blockers, and acceptance evidence.
4. Resolve the delivery Git repository and create or resume one run-scoped local DAG integration branch. Before the first claim, establish its Integration Publication Mode under the rules below. Reconcile existing Ticket workspaces and WIP; create or resume an isolated Ticket worktree only when claiming that Ticket.
5. Before claim, verify that the selected Execution Agent can use the Target Project's required tools and invoke `$code-review` with its project prerequisites, independent Standards context, and Spec-source discovery. An available Spec source receives an independent Spec context; confirmed absence follows `$code-review`'s no-Spec path and is not a capability failure. If invocation itself is unavailable, leave the Ticket unclaimed and record the unavailable capability, owner, and observable closing condition. A pinned bundle identity, installer, model metadata field, or unused optional Skill is not a global scheduling gate.
6. Treat exact model, Agent, reasoning, and tool requirements stated by the user or Target Project as constraints. Otherwise choose a capable available Agent without adding a profile-approval ceremony.

Use the Target Project's tracker or an off-delivery coordination store as the recovery store. Keep a compact Run Receipt containing the accepted integration tip; Integration Publication Mode; the local integration ref; the selected remote name, full remote branch ref, and last synchronized commit when applicable; claims; active Ticket/Base/Candidate/Workspace identities; any pending remote synchronization and its Candidate-bound automatic-push-closed marker; execution outcomes; and unresolved decisions or external closing conditions. For an in-flight promotion, persist its exact Base and Candidate before updating the integration ref, then record the verified local and remote identities. Link reports instead of copying them. Never commit the receipt to a Ticket candidate or the integration delivery history, or otherwise let it change an Accepted artifact identity. If the Target Project requires an in-history acceptance record, hold promotion until that project defines its distinct reviewed checkpoint and downstream Base contract.

## Stay within authority

DAG execution authorization normally covers locally auditable work needed for the approved graph: local claims, isolated workspaces, Agent dispatch, ticket-scoped edits, tests, commits, local promotion, acceptance evidence, and successor unlocking.

Selecting Remote-mirrored mode must explicitly include run-scoped authority to create and fast-forward one integration branch on one selected Git remote, and to read that branch back after each milestone push. That one selection covers those updates for the run; do not request per-milestone approval. Obtain separate authority for every other push, remote tracker write, pull request, tag, release, deployment, state-changing remote CI, external API or database write, destructive Git action, approved product or acceptance change, and gate weakening.

## Choose one integration publication mode

Create or resume the local integration branch with exactly one run-level mode:

- **Local-only**: the Accepted integration tip is maintained and verified only in the local repository.
- **Remote-mirrored**: one selected configured Git remote and one full `refs/heads/...` branch ref mirror the local integration branch. Use the local branch name as the default remote branch name unless the user or Target Project selects another.

A **DAG Milestone** is the exact commit and tree established at the local integration tip when one non-empty Promotion Candidate clears the serialized acceptance lane. Once its Ticket is Accepted, that milestone is the Accepted integration tip and Ticket Base for later claims. A Ticket-branch candidate, its intermediate commits, a Baseline Satisfaction transition that leaves the integration tip unchanged, and a Superseded transition are not new DAG Milestones.

Use a mode already fixed by the Target Project or recoverable Run Receipt. Otherwise, before the first Ticket claim, ask once for Local-only or Remote-mirrored and, for Remote-mirrored, the configured remote and remote branch. If no remote is configured, use Local-only unless remote synchronization is required; when it is required, wait for one configured remote to be selected. Record the choice in the Run Receipt and keep it unchanged for the run.

Initialize Remote-mirrored mode by running ordinary `git push -u <remote> <local-integration-branch>:<remote-branch>` from the current local integration tip, then query that remote and full branch ref for its exact SHA. This creates an absent branch, fast-forwards a branch that is behind, or confirms an already aligned branch. Initialization succeeds only when the remote SHA equals the local tip. If the ordinary push is rejected or the SHAs differ, stop before claiming a Ticket and report both identities so the user or Target Project can reconcile them or select another branch. Do not force-push or switch refs automatically.

Only the integration branch is mirrored. Ticket branches and worktrees remain local unless separately authorized for another purpose. Changing the mode or its ref mapping later is an explicit run-level authority and reconciliation decision made before further claims or promotions.

## Compute and claim the Runnable Frontier

A Ticket is Runnable when:

- it remains open and belongs to the effective Approved DAG;
- every hard predecessor is Accepted and its required output is available;
- its explicit blockers are clear;
- the Ticket and any governing Spec provide enough scope, acceptance, and gate information to start without inventing product meaning;
- current authority permits local execution and evidence persistence;
- the required execution capability and a safe isolated workspace can be provided.

Do not require a coordinator-authored exhaustive acceptance-to-probe map before claim. The Execution Agent may discover test cases, equivalence classes, and additional probes while implementing. Hold the Ticket only when missing information would change accepted meaning, dependency ownership, or authority.

Claim atomically: record the Ticket, one write-capable Execution Agent, its worktree, and a **Ticket Base** equal to the current Accepted integration tip. The Base stays fixed until the Coordinator explicitly replaces it after an Accepted-tip change or live recovery proves the assignment wrong; every replacement invalidates prior candidate and review evidence. Do not dispatch a second writer for the same claim.

Schedule serially by default. Run Tickets concurrently only when hard dependencies and write boundaries are genuinely independent. Serialize promotion through the integration branch, and recompute the frontier after every claim, acceptance, graph decision, external block, or recovered live-state change.

## Dispatch the fixed Ticket contract

Give the Execution Agent only the context needed for one Ticket:

- Ticket identity, authoritative Ticket pointer, and any governing Spec pointer;
- Accepted direct inputs and their identities;
- the assigned Ticket Base identity;
- assigned branch and isolated workspace;
- scope, acceptance, and required-gate pointers;
- local and external authority boundaries.

It returns one of three outcomes.

### Ready for Acceptance

Identify exactly one evidence path:

- **Promotion Candidate**: Ticket and Base commit identities; final candidate commit and tree; exact diff command and commit list; changed scope and files; focused and final gates; the complete `$code-review` result with Standards findings plus either Spec findings or an explicit confirmed no-Spec record, all in a record that binds the Base, candidate, tree, and evaluated range; and an evidence-backed disposition for every finding.
- **Baseline Satisfaction**: Ticket, Base commit, and tree identities; a clean empty delivery diff; focused and final gates; the existing Target Project rule that recognizes baseline satisfaction; complete evidence required by that rule; and whether the rule yields Accepted or Superseded.

For either path, include remaining risks and omitted verification. Return this outcome only when the named acceptance path is fully evidenced without a new product, scope, graph, or authority choice.

### Needs Coordinator Decision

- the dependency, acceptance ownership, product-semantic, scope, graph, or authority choice that the Coordinator or user can make;
- evidence showing why it cannot be resolved inside the approved Ticket;
- affected Tickets or edges and the exact decision needed;
- the latest clean candidate and completed verification, if any.

### Externally Blocked

- the unavailable credential, service, hardware, host capability, or already-required authorization;
- evidence, the owner of the closing condition, and the observable event that permits retry;
- the latest clean candidate and completed verification, if any.

These are execution outcomes, not Ticket states. `Ready for Acceptance` means an existing rule determines the successful transition and only Coordinator-owned verification or promotion remains. `Needs Coordinator Decision` means an explicit choice can unblock the work. `Externally Blocked` means the choice is settled and an external condition remains. Only the Coordinator records graph transitions and acceptance.

After returning an outcome, the Execution Agent stops writing to the Ticket workspace until the Coordinator explicitly resumes it.

## Run the Ticket-local engineering loop

Within the Ticket workspace, the Execution Agent:

1. Rereads the live Ticket, Accepted inputs, project instructions, current branch, and existing WIP before editing. It preserves valid work already present.
2. Implements and verifies the Ticket. It uses causal RED-to-GREEN evidence for changed behavior where applicable, focused checks while iterating, and project-required final gates before review.
3. For a non-empty delivery diff, commits a clean candidate that descends from the fixed Base, records its Base, commit, tree, exact diff command, and commit list, and invokes `$code-review` for that range. It stores the complete result beside those identities. Any later delivery edit creates a new candidate and invalidates the prior review for promotion.
4. Fixes every supported in-scope blocking finding, reruns affected checks and all invalidated final gates, commits a new candidate, and invokes `$code-review` again. It may dismiss a finding only with concrete Target Project, Spec, test, or code evidence recorded in its disposition.
5. Continues when a completed cycle has an observable change: it closes a finding, changes the candidate to address a named finding or failed acceptance probe, makes a required failing check pass, or produces new evidence that maps the remaining issue to a named decision or external closing condition. If a cycle changes none of these, it returns the applicable outcome with the evidence already obtained.

There is no fixed review or repair count. Ticket-local defects, additional probes, corrected commands, and new candidates remain in this loop while the Ticket objective, approved scope, Accepted inputs, and acceptance obligation remain unchanged.

A finding remains blocking when it cites an applicable Spec or documented standard, or demonstrates failing acceptance behavior, and its response does not disprove it with stronger project evidence. Do not return a successful outcome while such a finding remains.

Retry a failed Ticket-local tool action only after correcting its command, input, path, environment, or another evidenced cause. If it fails again under the same relevant conditions, stop retrying and return the applicable decision or external-block outcome.

### Handle a zero-diff Ticket explicitly

If the Ticket Base already satisfies the Ticket, the workspace is clean, and the delivery diff is empty, run the applicable final gates and collect the exact artifact identity, acceptance-obligation coverage, and evidence that no delivery bytes are required.

Return `Ready for Acceptance` through the Baseline Satisfaction path only when an existing Ticket or Target Project rule explicitly recognizes that result and every required audit and gate is present. Otherwise return `Needs Coordinator Decision` with the exact missing rule, current-state audit, or acceptance choice. Do not create an empty commit or treat a non-existent diff as a `$code-review` candidate.

For an evidence-complete Baseline Satisfaction outcome, the Coordinator locks the acceptance lane and rereads the current Accepted integration commit and tree. They must still equal the audited Base identities. In Remote-mirrored mode, the Coordinator also reads the selected remote branch and requires it to equal the same Base because the integration tip will not move. On a local mismatch, do not transition: preserve the identities, assign the current Accepted tip as the new Ticket Base, and return the same worktree to the same Ticket execution ownership to refresh its audit and gates. If the local Base is unchanged but the remote branch differs or cannot be read, leave the Ticket unaccepted and report the synchronization failure; do not turn it into a DAG Revision.

When those identities agree, verify the named rule and evidence. If the rule yields Accepted, record acceptance and close the claim in the off-delivery recovery store, confirm the required output is available, unlock successors, and recompute the frontier without moving the integration tip. If it yields Superseded, record that transition and close the claim in the same store, then recompute the effective graph; unlock work only from its effective Accepted dependencies. Do not use Superseded as proof that a missing output exists.

## Promote exactly the reviewed candidate

For `Ready for Acceptance` through the Promotion Candidate path, the Coordinator verifies:

- the current Accepted integration tip equals the recorded Ticket Base;
- the candidate descends from that Base and the recorded range resolves to the candidate's exact commit and tree;
- the candidate workspace is clean and the diff is within the approved Ticket scope;
- required gates are current for the candidate's final bytes;
- the review record binds the complete Standards result and either the Spec result or confirmed no-Spec record to that Base, candidate, tree, and range;
- every review finding and declared omission has an evidence-backed disposition, and no supported blocking finding remains.

Do not reinterpret the implementation or repeat equivalent review. Return missing or inconsistent evidence to the same Ticket execution ownership with one precise condition.

### Refresh an outdated Base

If another acceptance changed the integration tip, or live recovery proves the assigned Base wrong, do not promote or review against that Base. The Coordinator records a corrected Ticket Base equal to the current Accepted tip and returns the same worktree to the same Ticket execution ownership. The Execution Agent applies the Ticket's delivery changes on top of that Base under the Target Project's safe policy, ensures the new candidate descends from it, reruns affected and final gates, and creates a new candidate-bound `$code-review` record. Preserve the old record as superseded evidence.

### Use one serialized acceptance lane

Lock the acceptance lane and reread the integration tip, effective graph, and candidate evidence immediately before promotion. The tip must still equal the exact Base, and the Ticket must still be acceptable under that graph and evidence. Once these checks pass, hold the graph and acceptance lane unchanged through local promotion, any required remote synchronization, and the Accepted transition. Record graph evidence that arrives later and process it immediately after this transaction; do not revise the in-flight Ticket.

Persist the in-flight Base and Candidate, then advance the local integration ref from the exact Base to the exact Candidate with a fast-forward-only compare-and-swap. Read back its commit and tree; if the ref has a worktree, verify that it is clean and at the same identity. Never merge, recreate, or amend delivery bytes after review.

In Remote-mirrored mode, mark the Candidate as pending remote synchronization with automatic push still open, push the local integration branch to the selected remote branch with an ordinary fast-forward push, then query that remote and full branch ref for its exact SHA. Only a remote SHA equal to the Candidate completes synchronization. Do not use force push.

Only after every check required by the selected Integration Publication Mode agrees, record the Ticket as Accepted in the off-delivery recovery store; the exact Candidate is now the DAG Milestone and Accepted integration tip. Record the last synchronized commit when applicable, close the claim, unlock successors, and recompute the frontier.

If the run stops before the Remote-mirrored push, the push fails, its response is lost, or the run resumes with pending synchronization, keep the local Candidate and do not accept the Ticket, unlock successors, claim the next Ticket, or promote another Candidate. Read the selected remote branch; if it equals the Candidate, finish acceptance without another push. Perform another automatic push only when the Candidate-bound automatic-push-closed marker is explicitly open: send an original push known not to have started; before one repeat after a lost response, persist the marker as closed; after any explicit error other than non-fast-forward, correct that cause before retrying. Always use the same ordinary fast-forward push and read the remote branch again afterward. If Git reported non-fast-forward, report the exact local and remote identities and wait for reconciliation. Whenever the remote SHA is not the Candidate and the marker is missing, closed, or uncertain, issue no automatic push and immediately record the responsible owner and observable event for a new read or explicit decision. Do the same when an explicit error cannot be corrected now or a corrected retry returns the same error. Never force-push or switch to another ref automatically. A synchronization failure is not a DAG Revision.

## Escalate only boundary changes

Keep implementation defects, tests, review findings, probes, command corrections, candidate rounds, and diff size inside the Ticket execution ownership.

The Coordinator handles a missing or unaccepted predecessor output, an incorrect dependency, an Acceptance Obligation assigned to the wrong Ticket, work that belongs to another Ticket, a required change to approved semantics or gates, an authority decision, an external scheduling or promotion condition, or a cross-Ticket contract conflict exposed by integration.

Revise the DAG only when live evidence establishes a graph condition: a missing prerequisite, invalid edge, an Acceptance Obligation assigned to the wrong Ticket, or multiple independently acceptable delivery results. Follow the Target Project's authoring process, preserve replaced Tickets as provenance, map every unresolved acceptance obligation to an effective Ticket, and revalidate identities, acyclicity, and hard dependencies.

This graph-replacement rule applies only before a Ticket enters the locked acceptance transaction. A Candidate pending remote synchronization stays assigned to its original Ticket until synchronization and acceptance finish. Then recompute the graph with any evidence queued during the transaction. The remote failure itself cannot revise or replace that Ticket.

When a revision removes any other claimed Ticket, first establish that its writer has stopped and its worktree is quiescent. Preserve its worktree, candidate, review, and outcome evidence; then atomically record the Ticket as Superseded and close its claim in the off-delivery recovery store before dispatching any replacement Ticket. If the writer is still live or uncertain, use the recovery boundary below and do not start a replacement writer.

## Resume safely and finish

On resume, reread the tracker, repository, refs, workspaces, candidate and review identities, acceptance evidence, and Agent liveness. Continue a live execution instead of duplicating it.

If writer liveness is uncertain, preserve the claim and workspace and do not dispatch. The Coordinator must establish one observable boundary: resume/contact the existing task, obtain an acknowledged stop, or use an authorized host-level termination and then verify the workspace is quiescent. Until then, record the liveness owner and recheck event as an external closing condition and continue only graph-independent work. Never infer writer death from silence or elapsed time.

After a verified stop, resume the existing workspace and evidence with one writer. A replacement Execution Agent receives an explicit handoff and must reread the live state; it does not reset or recreate WIP.

Report **Complete** only when every effective Ticket is Accepted, every Superseded Ticket's acceptance obligation is accounted for, no active claim remains, whole-DAG gates and dependency consumption agree, and the selected Integration Publication Mode is satisfied. In Remote-mirrored mode, the local integration tip and readback of the selected remote branch must agree.

Resolve every `Needs Coordinator Decision` before evaluating Stalled. While an actionable choice is unanswered, retain its owner and required decision in the Run Receipt and report that outcome; do not relabel it Stalled. If a completed decision leaves only an unavailable external condition, record its owner and closing event as `Externally Blocked`.

Report **Stalled** only after writer liveness is resolved, no unresolved Coordinator decision remains, and unfinished Tickets have no running Agent, Runnable Frontier entry, authorized ticket-local recovery, graph correction, independent work, or currently satisfiable external closing condition. A still-running Agent prevents Stalled, and an ordinary in-scope finding stays ticket-local.

Return an evidence-backed summary of Accepted, Superseded, active, decision-needed, and externally blocked Tickets; the integration identity and selected publication mode; the selected remote, remote branch, and exact readback when applicable; verification and review performed or omitted; graph decisions; and liveness conditions.
