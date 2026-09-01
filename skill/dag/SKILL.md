---
name: dag
description: Coordinate an Approved DAG in a Git-backed Target Project by selecting runnable Tickets, dispatching one end-to-end Execution Agent per Ticket, and accepting verified results. Use when the user asks to execute, advance, continue, or resume an Approved DAG.
---

# Coordinate an Approved DAG

Act as the **Coordinator Agent** for an Approved DAG in a Git-backed Target Project. Advance it from live instructions, Tickets, tracker, repository, tests, and acceptance evidence. Treat chat history and Agent summaries as pointers, not current state.

## Keep one Ticket ownership path

Use two DAG roles:

```text
Coordinator Agent
`-- Execution Agent for one Ticket
    |-- $tdd and $codebase-design when applicable
    `-- $code-review
```

- The **Coordinator Agent** owns live reconciliation, the Runnable Frontier, claims, Ticket Base and workspace assignment, graph and authority decisions, promotion, acceptance, and successor unlocking.
- The **Execution Agent** owns one Ticket's implementation, ticket-local TDD, focused and final gates, commits, `$code-review` invocation, and closure of credible in-scope findings until it can return one stable Execution Outcome.

The Coordinator Agent does not take over implementation or repeat an equivalent engineering review after handoff. The Execution Agent does not alter the DAG Integration Branch, accept a Ticket, unlock successors, write remote state, or work on another Ticket.

`$code-review` owns its review process. The Execution Agent invokes it and handles its findings; the DAG only binds the complete result to the reviewed candidate.

## Reconstruct the live run

Before scheduling:

1. Resolve the Target Project, effective Approved DAG, in-scope Tickets, dependency carrier, any governing Spec, and the user's authority to execute or continue. Ask only when ambiguity would change scope, product meaning, dependencies, acceptance, or authority.
2. Reread the live instruction hierarchy, domain and engineering documents, Tickets, tracker state, repository status, branches and worktrees, tests, and existing acceptance or review evidence. Preserve unrelated work and existing Ticket workspaces.
3. Reconstruct the effective graph. A **Hard Dependency** exists only when the dependent Ticket consumes an Accepted output from the prerequisite Ticket. Validate unique Ticket identities, Hard Dependencies, acyclicity, blockers, and acceptance evidence.
4. Treat exact model, Agent, reasoning, and tool requirements stated by the user or Target Project as constraints. Otherwise choose a capable available Agent without adding a profile-approval ceremony.
5. Resolve the active Agent Host and prepare the Runtime Skill Bundle under the rules below. Complete this Agent Host check before changing Git refs.
6. Before creating or resuming the DAG Integration Branch, read [`references/integration-transitions.md`](references/integration-transitions.md) completely. Apply its local ref, frozen-evidence, publication-mode, and remote-recovery contract from an exact Target Project-authorized **Starting Base**. Each claimed Ticket receives its own branch and worktree.
7. Bind the effective DAG Definition from Starting Base on a new run or from the current Accepted Integration Tip later, then satisfy the selected Integration Publication Mode. The result must be an Accepted Integration Tip before the first claim.

Use the Target Project's tracker as the off-delivery recovery store only when it remains off-delivery for the run; otherwise use a separate off-delivery recovery store. Keep a compact Run Receipt containing the Starting Base; the Accepted Integration Tip once established; the DAG Definition Index path and identity; the bound DAG Definition inputs and content identities; the binding commit/tree and latest completed DAG Definition Checkpoint; the verified Agent Host, Skills root, Runtime Skill Bundle revision and tree identities; Integration Publication Mode; the local DAG Integration Branch ref; the selected remote name, full remote branch ref, and last synchronized commit when applicable; claims; active Ticket, Ticket Base, Promotion Candidate, and workspace identities; any typed pending Integration Transition; Execution Outcomes; and unresolved decisions or external closing conditions. Before updating the DAG Integration Branch ref, persist an in-flight Integration Transition's candidate kind, Base, candidate commit/tree, and exact candidate-bound review and gate identities; for a DAG Definition Checkpoint also persist the selected DAG Definition Index and inputs plus every acceptance-impact disposition and audit identity. Then record verified local and remote identities without replacing that frozen evidence. Link reports instead of copying them. Keep the receipt off-delivery so recording the run never changes an Accepted artifact identity; it indexes the tracked DAG Definition binding but never replaces it. Stable tracker or acceptance evidence enters history only through a Target Project-authorized DAG Definition Checkpoint; that DAG Definition Checkpoint's own completion record remains off-delivery.

The Run Receipt is the compare source for every local or remote reconciliation. Reconcile pending Integration Transitions only through the immutable-evidence recovery table in [`references/integration-transitions.md`](references/integration-transitions.md).

## Bootstrap the Runtime Skill Bundle

The Runtime Skill Bundle contains `code-review`, `tdd`, and `codebase-design` from the revision pinned by `scripts/install_runtime_skills.py`. On each DAG start or resume, resolve the active Agent Host and stable Skills root, then check once that all three Skills resolve through that Agent Host and that their entrypoints, referenced resources, revision, and tree identities match. Do not run a review or other real Skill workflow as a startup probe.

If any bundle member cannot be resolved through the active Agent Host or does not match its pinned identity during bootstrap, run the bundled installer by default before the first Ticket claim:

```bash
python3 <this-skill-root>/scripts/install_runtime_skills.py \
  --skills-root <resolved-host-skills-root>
```

Resolve the stable Agent Host Skills root from Agent Host configuration or an already resolved sibling Skill. Do not guess a location. The DAG execution request authorizes this conflict-safe creation of missing pinned Skill directories; satisfy any Agent Host-enforced filesystem or network approval at the tool boundary. Installer preflight classifies every target as current, missing, or conflicting. It may reuse exact pinned copies and create missing directories, but it preserves and reports every unreadable, incomplete, differently versioned, or otherwise conflicting existing target instead of updating or overwriting it.

After the installer succeeds, make the Agent Host reload its Skill list and confirm that all three Runtime Skills resolve. A successful file copy alone is not readiness. If the Agent Host requires a reload or new task, leave Tickets unclaimed and report that requirement. Do the same when Python 3.12+, Git/network access, the Skills root, write permission, or a conflict prevents installation.

Once the startup check succeeds, every Ticket in that run uses the verified bundle without another dependency preflight. A later DAG start or resume repeats the one startup check. Execution Agents invoke Skills normally when needed; ordinary tool-failure handling applies if the Agent Host changes during a run.

The optional `setup-matt-pocock-skills` helper is not part of the Runtime Skill Bundle. Install it only with `--include-setup-helper`, and invoke it only when the Target Project needs that setup and the user authorizes the configuration change.

## Stay within authority

DAG execution authorization normally covers locally auditable work needed for the approved graph: conflict-safe bootstrap of missing Runtime Skill Bundle directories in the resolved Agent Host Skills root; binding the already-approved DAG Definition through a local DAG Definition Checkpoint; local claims; isolated workspaces; Agent dispatch; ticket-scoped edits; tests; commits; local promotion; acceptance evidence; and successor unlocking. It does not cover changing approved product meaning, scope, Hard Dependencies, Acceptance Obligations, or gates; replacing an existing Skill; or automatically changing Target Project configuration.

Selecting Remote-mirrored mode must explicitly include run-scoped authority to create and fast-forward one integration branch on one selected Git remote, and to read that branch back after each Integration Transition. An explicit user or Target Project instruction to mirror or push that branch supplies this authority for DAG Milestones and reviewed DAG Definition Checkpoints when it names an unambiguous remote and ref; do not ask again at each transition. Obtain separate authority for `git remote add`, for writing a default or protected branch, and for every other push, remote tracker write, pull request, tag, release, deployment, state-changing remote CI, external API or database write, destructive Git action, approved product or acceptance change, and gate weakening.

## Choose one Integration Publication Mode

Use exactly one run-level mode: Local-only or Remote-mirrored to one dedicated remote branch. Resolve and record it before the first claim, then keep the mapping stable. The selection, initialization, drift, and retry rules are defined only in [`references/integration-transitions.md`](references/integration-transitions.md); apply them without inventing another publication path.

A non-empty Promotion Candidate that completes its Integration Transition becomes a DAG Milestone and Accepted Integration Tip when its Ticket is Accepted. A DAG Definition Checkpoint may become the Accepted Integration Tip and Ticket Base but accepts no Ticket and creates no DAG Milestone. Baseline Satisfaction and Superseded Ticket transitions do not move the tip.

## Bind the DAG Definition

The **DAG Definition** is the governing Spec, effective Tickets, Hard Dependencies, and Acceptance Obligations needed to reconstruct the Approved DAG from Git history alone. Before accepting an existing Definition, creating a checkpoint, or applying a DAG Revision, read and follow [`references/definition-binding.md`](references/definition-binding.md) completely. It is the branch-specific contract for source classification, the canonical index validator, equivalence, checkpoint review, and acceptance-impact audits.

Before the first claim and after every approved Definition change, validate Starting Base before the first Accepted Integration Tip exists or the current Accepted Integration Tip afterward. Record the validated DAG Definition Index result, selected input identities, and binding commit/tree. If the exact Definition is not already bound, create an isolated DAG Definition Checkpoint from that commit and complete its gates, fresh review, frozen evidence, and Integration Transition.

Only a DAG Definition Checkpoint may change the index, selected inputs, content identities, or snapshot. Every Promotion Candidate preserves them and excludes transient run state. The Coordinator Agent owns checkpoint-local repair without taking over Ticket implementation; every byte change invalidates the prior checkpoint gates and review.

For a DAG Revision, preserve every affected claim, workspace, and WIP, and pause affected active Ticket ownership before promotion. A DAG Definition Checkpoint commit is not a Ticket Base until its Integration Transition completes. Record a Coordinator-owned unresolved decision when transition rules or authority are unclear. After the DAG Definition Checkpoint completes, assign its Accepted Integration Tip as the new Ticket Base for affected active or reopened Tickets, apply the frozen dispositions, resume the preserved ownership paths, and recompute the graph and Runnable Frontier.

## Compute and claim the Runnable Frontier

A Ticket is Runnable when:

- the exact DAG Definition Index and selected inputs are bound to the current Accepted Integration Tip and the selected Integration Publication Mode is satisfied;
- it remains open and belongs to the effective Approved DAG;
- every prerequisite connected by a Hard Dependency is Accepted and its required output is available;
- its explicit blockers are clear;
- the Ticket and any governing Spec provide enough scope, acceptance, and gate information to start without inventing product meaning;
- current authority permits local execution and evidence persistence;
- the required execution capability and a safe isolated workspace can be provided.

Do not require a coordinator-authored exhaustive acceptance-to-probe map before claim. The Execution Agent may discover test cases, equivalence classes, and additional probes while implementing. Hold the Ticket only when missing information would change accepted meaning, dependency ownership, or authority.

Claim atomically: record the Ticket, one write-capable Execution Agent, its worktree, and a **Ticket Base** equal to the current Accepted Integration Tip. The Ticket Base stays fixed until the Coordinator Agent explicitly replaces it after an Accepted Integration Tip change or live recovery proves the assignment wrong; every replacement invalidates prior candidate and review evidence. Do not dispatch a second writer for the same claim.

Schedule serially by default. Run Tickets concurrently only when no Hard Dependency orders them and their write boundaries are genuinely independent. Serialize promotion through the DAG Integration Branch, and recompute the Runnable Frontier after every claim, acceptance, graph decision, external block, or recovered live-state change.

## Dispatch the fixed Ticket contract

Give the Execution Agent only the context needed for one Ticket:

- Ticket identity, authoritative Ticket pointer, and any governing Spec pointer;
- Accepted direct inputs and their identities;
- the assigned Ticket Base identity;
- assigned branch and isolated workspace;
- scope, acceptance, and required-gate pointers;
- local and external authority boundaries.

Scope inherited history as part of dispatch. Use the Agent Host's zero-history dispatch setting and provide the explicit Ticket contract above. When zero-history dispatch is unavailable, use the smallest available history window that excludes unrelated Tickets, Run Receipt state, and prior tool output. Do not rely on default full-history inheritance. The Execution Agent reconstructs implementation context from the assigned live workspace and authoritative pointers.

It returns one of three Execution Outcomes.

### Ready for Acceptance

Identify exactly one evidence path:

- **Promotion Candidate**: Ticket and Ticket Base commit identities; final candidate commit and tree; exact diff command and commit list; changed scope and files; focused and final gates; the complete `$code-review` result exactly as returned; the Candidate Review Record binding the Ticket Base, candidate, tree, and evaluated range; and an evidence-backed disposition for every finding.
- **Baseline Satisfaction**: Ticket, Ticket Base commit, and tree identities; a clean empty delivery diff; focused and final gates; the existing Target Project rule that recognizes Baseline Satisfaction; complete evidence required by that rule; and whether the rule yields Accepted or Superseded.

For either path, include remaining risks and omitted verification. Return this outcome only when the named acceptance path is fully evidenced without a new product, scope, graph, or authority choice.

### Needs Coordinator Decision

- the dependency, acceptance ownership, product-semantic, scope, graph, or authority choice that the Coordinator Agent or user can make;
- evidence showing why it cannot be resolved inside the approved Ticket;
- affected Tickets or edges and the exact decision needed.

### Externally Blocked

- the unavailable credential, service, hardware, host capability, or already-required authorization;
- evidence, the owner of the closing condition, and the observable event that permits retry.

Both non-success outcomes include the latest clean candidate and completed verification, if any.

These are Execution Outcomes, not Ticket states. `Ready for Acceptance` means an existing rule determines the successful transition and only verification or promotion owned by the Coordinator Agent remains. `Needs Coordinator Decision` means an explicit choice can unblock the work. `Externally Blocked` means the choice is settled and an external condition remains. Only the Coordinator Agent records graph transitions and acceptance.

After returning an outcome, the Execution Agent stops writing to the Ticket workspace until the Coordinator Agent explicitly resumes it.

## Run the Ticket-local engineering loop

Within the Ticket workspace, the Execution Agent:

1. Rereads the live Ticket, Accepted inputs, project instructions, current branch, and existing WIP before editing. It preserves valid work already present.
2. Implements and verifies the Ticket. It invokes `$tdd` for changed behavior and uses causal RED-to-GREEN evidence where applicable. It invokes `$codebase-design` when the Ticket requires an interface, module-boundary, seam, or testability decision. It runs focused checks while iterating and project-required final gates before review.
3. For a non-empty delivery diff, ensures the diff preserves the bound DAG Definition Index, selected path set, and content identities and excludes transient run state, then commits a clean candidate that descends from the fixed Ticket Base. It records the Ticket Base, commit, tree, exact diff command, and commit list and invokes `$code-review` for that range. It stores the complete result and Candidate Review Record beside those identities. If approved Ticket work requires a DAG Definition change, it reports that exact change to the Coordinator Agent for a DAG Definition Checkpoint instead of including it in the Promotion Candidate; after the DAG Definition Checkpoint, the same Ticket ownership continues from the new Ticket Base. Any later delivery edit creates a new candidate and invalidates the prior Candidate Review Record for promotion.
4. Fixes every supported in-scope blocking finding, reruns affected checks and all invalidated final gates, commits a new candidate, and invokes `$code-review` again. It may dismiss a finding only with concrete Target Project, Spec, test, or code evidence recorded in its disposition.
5. Continues when a completed cycle has an observable change: it closes a finding, changes the candidate to address a named finding or failed acceptance probe, makes a required failing check pass, or produces new evidence that maps the remaining issue to a named decision or external closing condition. If a cycle changes none of these, it returns the applicable outcome with the evidence already obtained.

There is no fixed review or repair count. Ticket-local defects, additional probes, corrected commands, and new candidates remain in this loop while the Ticket objective, approved scope, Accepted inputs, and acceptance obligation remain unchanged.

A finding remains blocking when it cites an applicable Spec or documented standard, or demonstrates failing acceptance behavior, and its response does not disprove it with stronger project evidence. Do not return a successful outcome while such a finding remains.

Retry a failed Ticket-local tool action only after correcting its command, input, path, environment, or another evidenced cause. If it fails again under the same relevant conditions, stop retrying and return the applicable decision or external-block outcome.

### Handle a zero-diff Ticket explicitly

If the Ticket Base already satisfies the Ticket, the workspace is clean, and the delivery diff is empty, run the applicable final gates and collect the exact artifact identity, acceptance-obligation coverage, and evidence that no delivery bytes are required.

Return `Ready for Acceptance` through the Baseline Satisfaction path only when an existing Ticket or Target Project rule explicitly recognizes that result and every required audit and gate is present. Otherwise return `Needs Coordinator Decision` with the exact missing rule, current-state audit, or acceptance choice. Do not create an empty commit or treat a non-existent diff as a `$code-review` candidate.

For an evidence-complete Baseline Satisfaction outcome, the Coordinator Agent serializes the decision against all Integration Transitions and rereads the Accepted Integration Tip commit and tree. They must still equal the audited Ticket Base identities. In Remote-mirrored mode, the Coordinator Agent also reads the selected remote branch and requires it to equal the same Ticket Base because the Accepted Integration Tip will not move. On a local mismatch, do not transition: preserve the identities, assign the current Accepted Integration Tip as the new Ticket Base, and return the same worktree to the same Ticket execution ownership to refresh its audit and gates. If the local Ticket Base is unchanged but the remote branch differs or cannot be read, leave the Ticket unaccepted and report the synchronization failure.

When those identities agree, verify the named rule and evidence. If the rule yields Accepted, record an Accepted Ticket and close the claim in the off-delivery recovery store, confirm the required output is available, unlock successors, and recompute the Runnable Frontier without moving the Accepted Integration Tip. If it yields Superseded, record a Superseded Ticket and close the claim in the same store, then recompute the effective graph; unlock work only when its effective prerequisite outputs are Accepted. Do not use Superseded as proof that a missing output exists.

## Promote exact reviewed Integration Transitions

Before the Coordinator Agent begins the serialized Integration Transition for a `Ready for Acceptance` Promotion Candidate, verify:

- the current Accepted Integration Tip equals the recorded Ticket Base;
- the candidate descends from that Ticket Base and the recorded range resolves to the candidate's exact commit and tree;
- the candidate workspace is clean and the diff is within the approved Ticket scope;
- the candidate preserves the recorded DAG Definition Index, selected path set, and content identities and excludes every Run Receipt or other transient run-state path;
- required gates are current for the candidate's final bytes;
- the Candidate Review Record binds the complete `$code-review` result exactly as returned to that Ticket Base, candidate, tree, and range;
- every review finding and declared omission has an evidence-backed disposition, and no supported blocking finding remains.

Do not reinterpret the implementation or repeat equivalent review. Return missing or inconsistent evidence to the same Ticket execution ownership with one precise condition.

### Refresh an outdated Ticket Base

If another acceptance changed the Accepted Integration Tip, or live recovery proves the assigned Ticket Base wrong, do not promote or review against that Ticket Base. The Coordinator Agent records a corrected Ticket Base equal to the current Accepted Integration Tip and returns the same worktree to the same Ticket execution ownership. The Execution Agent applies the Ticket's delivery changes on top of that Ticket Base under the Target Project's safe policy, ensures the new candidate descends from it, reruns affected and final gates, and creates a new Candidate Review Record. Preserve the old record as superseded evidence.

### Serialize Integration Transitions

Apply the pre-CAS, local readback, publication, and recovery sequence in [`references/integration-transitions.md`](references/integration-transitions.md). Only one Integration Transition may run, and it completes from the identities frozen under that reference.

Complete a Promotion Candidate only after it becomes the published Accepted Integration Tip, then accept its Ticket and unlock successors. Complete a DAG Definition Checkpoint with the same frozen Definition and audit evidence, accept no Ticket, and only then assign its Accepted Integration Tip as downstream Ticket Base. Pending or drifted synchronization blocks both transitions and every later promotion.

## Escalate only boundary changes

Keep implementation defects, tests, review findings, probes, command corrections, candidate rounds, and diff size inside the Ticket execution ownership. Escalate only evidence that changes a graph, product, authority, or integration boundary: a missing predecessor output, invalid edge, misplaced Acceptance Obligation, independently acceptable split, semantic or gate decision, external promotion condition, or cross-Ticket conflict.

When Tickets must be created, replaced, or changed, apply the Target Project's existing DAG Revision rules. Preserve replaced Tickets as provenance, map every unresolved Acceptance Obligation to an effective Ticket, and revalidate identities, acyclicity, Hard Dependencies, and acceptance-impact dispositions through the DAG Definition Checkpoint rules above. If the rule or authority is unclear, record a Coordinator-owned unresolved decision and leave the graph unchanged.

This graph-replacement rule applies only before a Ticket enters an active Integration Transition. A Promotion Candidate pending remote synchronization stays assigned to its original Ticket until synchronization and acceptance finish; a pending DAG Definition Checkpoint remains owned by the Coordinator Agent until DAG Definition binding finishes. Then recompute the graph with any evidence queued during the Integration Transition.

When a revision removes any other claimed Ticket, first establish that its writer has stopped and its worktree is quiescent. Preserve its worktree, candidate, Candidate Review Record, and Execution Outcome evidence; then atomically record a Superseded Ticket and close its claim in the off-delivery recovery store before dispatching any replacement Ticket. If the writer is still live or uncertain, use the recovery boundary below and do not start a replacement writer.

## Resume safely and finish

On resume, repeat **Reconstruct the live run** and reread [`references/integration-transitions.md`](references/integration-transitions.md) before reconciling refs or frozen evidence. Before the first Accepted Integration Tip exists, revalidate Starting Base plus initial DAG Definition binding and publication; afterward require the recorded Accepted Integration Tip to preserve the validated DAG Definition Index result and selected input identities. Continue live execution instead of duplicating it.

If writer liveness is uncertain, preserve the claim and workspace and do not dispatch. The Coordinator Agent must establish one observable boundary: resume/contact the existing task, obtain an acknowledged stop, or use an authorized Agent Host-level termination and then verify the workspace is quiescent. Until then, record the liveness owner and recheck event as an external closing condition and continue only graph-independent work. Never infer writer death from silence or elapsed time.

After a verified stop, resume the existing workspace and evidence with one writer. If the Agent must change, first confirm that the original Agent has stopped, then hand the original Ticket, branch, worktree, and WIP to the replacement Agent. The replacement rereads the live state and continues it without resetting or recreating WIP.

Report a **Complete** Terminal Outcome only when the final DAG Definition Index and selected inputs are bound to the Accepted Integration Tip, every effective Ticket is an Accepted Ticket with evidence bound to that DAG Definition, every Superseded Ticket's current Acceptance Obligation is accounted for, no active claim remains, whole-DAG gates and dependency consumption agree, and the selected Integration Publication Mode is satisfied. In Remote-mirrored mode, the local Accepted Integration Tip and readback of the selected remote branch must agree.

Resolve every Coordinator-owned unresolved decision and every `Needs Coordinator Decision` Execution Outcome before evaluating a Terminal Outcome. While an actionable choice is unanswered, retain its owner and required decision in the Run Receipt and report the applicable decision evidence; do not relabel it Stalled. If a completed decision leaves only an unavailable external condition, record its owner and closing event as `Externally Blocked` when an Execution Agent owns that outcome, or as an external closing condition otherwise.

Report a **Stalled** Terminal Outcome only after writer liveness is resolved, no Coordinator-owned unresolved decision or `Needs Coordinator Decision` Execution Outcome remains, and unfinished Tickets have no running Execution Agent, Runnable Frontier entry, authorized ticket-local recovery, graph correction, independent work, or currently satisfiable external closing condition. A still-running Execution Agent prevents Stalled, and an ordinary in-scope finding stays ticket-local.

Return an evidence-backed summary of the Terminal Outcome; DAG Definition Index, selected inputs, and latest DAG Definition Checkpoint; Accepted Tickets, Superseded Tickets, active Tickets, decision-needed and externally blocked Execution Outcomes, and acceptance-impact dispositions; the Accepted Integration Tip and selected Integration Publication Mode; the selected remote, remote branch, and exact readback when applicable; verification and review performed or omitted; graph decisions; and liveness conditions.
