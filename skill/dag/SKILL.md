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
3. Reconstruct the effective graph. A **Hard Dependency** exists only when the dependent Ticket consumes an Accepted output from the prerequisite Ticket. Validate unique Ticket identities, Hard Dependencies, acyclicity, blockers, and acceptance evidence. Account for every in-scope governing Spec obligation through an effective Ticket or an existing whole-DAG gate with an explicit owner. Resolve missing responsibility through the existing graph-decision rules; coverage identifies obligations and owners, not an exhaustive test plan.
4. Treat exact model, Agent, reasoning, and tool requirements stated by the user or Target Project as constraints. Otherwise choose a capable available Agent without adding a profile-approval ceremony.
5. Resolve the active Agent Host and prepare the Runtime Skill Bundle under the rules below. Complete this Agent Host check before changing Git refs.
6. Before creating or resuming the DAG Integration Branch, read [`references/integration-transitions.md`](references/integration-transitions.md) completely. Apply its local ref, frozen-evidence, publication-mode, and remote-recovery contract from an exact Target Project-authorized **Starting Base**. Each claimed Ticket receives its own branch and worktree.
7. Bind the effective DAG Definition from Starting Base on a new run or from the current Accepted Integration Tip later, then satisfy the selected Integration Publication Mode. The result must be an Accepted Integration Tip before the first claim.

During this reread, identify any Target Project rule that requires its Git-tracked tracker to be updated with stable Ticket state or acceptance evidence. Record when that update is required, which fields the project defines, and the authority to write them. Do not invent such a requirement when none exists.

Maintain the off-delivery Run Receipt under [Run Receipt and frozen evidence](references/integration-transitions.md#run-receipt-and-frozen-evidence). Read and follow that section before persisting run state or reconciling local or remote refs; it defines the recovery store, receipt identities, and immutable pending Integration Transition evidence. The required tracker update lifecycle is defined below.

## Bootstrap the Runtime Skill Bundle

The Runtime Skill Bundle contains `code-review`, `tdd`, and `codebase-design`. The revision anchored by [`scripts/install_runtime_skills.py`](scripts/install_runtime_skills.py) is the minimum: accept its exact contents or complete Skill contents verified at a descendant commit in the upstream repository. Use Git ancestry, not commit dates, to establish that a revision is newer. On each DAG start or resume, resolve the active Agent Host and stable Skills root, then check once that all three Skills resolve, their entrypoints and referenced resources are available, and their content identities meet this version floor. Record the verified source commits and content identities. Do not run a review or other real Skill workflow as a startup probe.

Resolve and record a Python 3.12+ executable for bundled helpers; use that verified executable in place of `python3` in the command examples throughout this Skill.

If any bundle member cannot be resolved through the active Agent Host, is missing, or has not been verified against this version floor, run the bundled installer by default before the first Ticket claim:

```bash
python3 <this-skill-root>/scripts/install_runtime_skills.py \
  --skills-root <resolved-host-skills-root>
```

Resolve the stable Agent Host Skills root from Agent Host configuration or an already resolved sibling Skill. Do not guess a location. The DAG execution request authorizes this conflict-safe creation of missing Skill directories; satisfy any Agent Host-enforced filesystem or network approval at the tool boundary. Installer preflight classifies every target as current, missing, or conflicting. Exact anchor copies are recognized locally. For different contents, the installer fetches upstream branch and tag history into a temporary checkout and checks complete Skill trees at descendant commits, including intermediate revisions. It reuses verified newer copies and installs missing Skills from the anchor. It preserves and reports unreadable, incomplete, locally modified, unverifiable, or otherwise conflicting targets instead of overwriting or downgrading them. A network or ancestry-verification failure leaves existing targets intact.

After the installer succeeds, make the Agent Host reload its Skill list and confirm that all three Runtime Skills resolve. A successful file copy alone is not readiness. If the Agent Host requires a reload or new task, leave Tickets unclaimed and report that requirement. Do the same when Python 3.12+, Git/network access, the Skills root, write permission, or a conflict prevents installation.

Once the startup check succeeds, every Ticket in that run uses the verified bundle without another dependency preflight. A later DAG start or resume repeats the one startup check. Execution Agents invoke Skills normally when needed; ordinary tool-failure handling applies if the Agent Host changes during a run.

Supply Runtime Skills with authoritative project inputs and existing approvals under [Supply Runtime Skills](references/ticket-execution.md#supply-runtime-skills), including the project's existing tracker workflow.

The optional `setup-matt-pocock-skills` helper is not part of the Runtime Skill Bundle. Install it only when the user explicitly requests its installation or when it is needed to carry out project configuration already authorized through this helper. In either case, the Coordinator Agent installs a missing helper by adding `--include-setup-helper` to the bundled installer, using the same conflict-preservation and Agent Host reload checks. Reuse existing authorization within its scope rather than requesting it again. Invoke the helper only for authorized configuration changes; an installation-only request leaves project configuration unchanged.

## Stay within authority

DAG execution authorization normally covers locally auditable work needed for the approved graph: verifying Runtime Skill versions and conflict-safe bootstrap of missing Runtime Skill Bundle directories in the resolved Agent Host Skills root; binding the already-approved DAG Definition through a local DAG Definition Checkpoint; local claims; isolated workspaces; Agent dispatch; ticket-scoped edits; tests; commits; local promotion; acceptance evidence; and successor unlocking. It does not cover changing approved product meaning, scope, Hard Dependencies, Acceptance Obligations, or gates; replacing an existing Skill; or automatically changing Target Project configuration.

Selecting Remote-mirrored mode must explicitly include run-scoped authority to create and fast-forward one integration branch on one selected Git remote, and to read that branch back after each Integration Transition. An explicit user or Target Project instruction to mirror or push that branch supplies this authority for DAG Milestones and reviewed DAG Definition Checkpoints when it names an unambiguous remote and ref; do not ask again at each transition. Obtain separate authority for `git remote add`, for writing a default or protected branch, and for every other push, remote tracker write, pull request, tag, release, deployment, state-changing remote CI, external API or database write, destructive Git action, approved product or acceptance change, and gate weakening.

## Choose one Integration Publication Mode

Use exactly one run-level mode: Local-only or Remote-mirrored to one dedicated remote branch. Resolve and record it before the first claim, then keep the mapping stable. The selection, initialization, drift, and retry rules are defined only in [`references/integration-transitions.md`](references/integration-transitions.md); apply them without inventing another publication path.

A non-empty Promotion Candidate that completes its Integration Transition becomes a DAG Milestone and Accepted Integration Tip when its Ticket is Accepted. A DAG Definition Checkpoint may become the Accepted Integration Tip and Ticket Base but accepts no Ticket and creates no DAG Milestone. Baseline Satisfaction and Superseded Ticket transitions do not move the tip.

## Bind the DAG Definition

The **DAG Definition** is the governing Spec, effective Tickets, Hard Dependencies, and Acceptance Obligations needed to reconstruct the Approved DAG from Git history alone. Before accepting an existing Definition, creating a checkpoint, or applying a DAG Revision, read and follow [`references/definition-binding.md`](references/definition-binding.md) completely. It is the branch-specific contract for source classification, the canonical index validator, equivalence, checkpoint review, and acceptance-impact audits.

Before the first claim and after every approved Definition change, validate Starting Base before the first Accepted Integration Tip exists or the current Accepted Integration Tip afterward. Record the validated DAG Definition Index result, selected input identities, and binding commit/tree. If the exact Definition is not already bound, create an isolated DAG Definition Checkpoint from that commit and complete its gates, fresh review, frozen evidence, and Integration Transition.

Only a DAG Definition Checkpoint may change the index, selected inputs, content identities, or snapshot. Every Promotion Candidate preserves them and excludes transient run state. The Coordinator Agent owns checkpoint-local repair without taking over Ticket implementation; every byte change requires current gates and a fresh checkpoint review under that reference.

For a DAG Revision, preserve every affected claim, workspace, and WIP, and pause affected active Ticket ownership before promotion. A DAG Definition Checkpoint commit is not a Ticket Base until its Integration Transition completes. Record a Coordinator-owned unresolved decision when transition rules or authority are unclear. After the DAG Definition Checkpoint completes, assign its Accepted Integration Tip as the new Ticket Base for affected active or reopened Tickets, apply the frozen dispositions, resume the preserved ownership paths, and recompute the graph and Runnable Frontier.

## Compute and claim the Runnable Frontier

A Ticket is Runnable when:

- the exact DAG Definition Index and selected inputs are bound to the current Accepted Integration Tip and the selected Integration Publication Mode is satisfied;
- it remains open and belongs to the effective Approved DAG;
- every prerequisite connected by a Hard Dependency is Accepted and its required output is available;
- its explicit blockers are clear;
- the Ticket and any governing Spec provide enough scope, acceptance, and gate information to start without inventing product meaning;
- current authority permits local execution and evidence persistence;
- no Target Project-required per-Ticket tracker update is pending;
- the required execution capability and a safe isolated workspace can be provided.

Do not require a coordinator-authored exhaustive acceptance-to-probe map before claim. The Execution Agent may discover test cases, equivalence classes, and additional probes while implementing. Hold the Ticket only when missing information would change accepted meaning, dependency ownership, or authority.

Choose scheduling from the current Runnable Frontier within applicable user and Target Project constraints. On every claim or resume, check the resulting execution set, including existing live claims and downstream Runtime Skill Agents, against the relevant live evidence:

- **Delivery independence:** no Hard Dependency orders work whose implementation or checks will overlap. A paused dependent may retain its claim during prerequisite repair only after its writes and checks are observably paused; still count its retained resources and capacity below. Inspect shared interfaces, configuration, and critical files for changes that could conflict or invalidate another Ticket's implementation or focused checks. Overlap needs a concrete isolation method; separate worktrees or filenames alone do not prove independence. Ordinary integration-tip changes are handled by the Base-refresh rules below and do not alone disqualify concurrency. A newly discovered prerequisite output follows the existing DAG Revision rules.
- **Runtime isolation:** implementation and focused checks have isolated access to shared resources such as ports, devices, databases, and run directories, or do not contend for them. Include resources outside the worktree.
- **Capacity:** the actual Agent Host can run the selected Execution Agents while leaving capacity for downstream Runtime Skill Agents, which retain their own orchestration. Select only a subset that fits those limits.

Prefer concurrent implementation and focused checks for work that passes these checks, including backfilling one Runnable Ticket alongside an existing live claim. Otherwise advance a feasible Ticket serially. Unproven concurrency conditions alone require neither a mode-selection approval nor an Execution Outcome. A conflicting pair does not prevent other independent Tickets from running concurrently. Serialize promotion through the DAG Integration Branch, and recompute the Runnable Frontier after every claim, acceptance, graph decision, external block, or recovered live-state change.

Claim atomically: record the Ticket, one write-capable Execution Agent, its worktree, and a **Ticket Base** equal to the current Accepted Integration Tip. The Ticket Base stays fixed until the Coordinator Agent explicitly replaces it after an Accepted Integration Tip change or live recovery proves the assignment wrong; every replacement invalidates prior candidate and review evidence. Do not dispatch a second writer for the same claim.

For concurrent Tickets, give one Ticket completion priority from final gates and review through promotion and its required tracker checkpoint. For a deferred Ticket, confirm a current Ticket Base and authorize final work after any preceding acceptance and required checkpoint; the same Execution Agent refreshes its candidate when necessary. Other Tickets retain their owner, workspace, and WIP while waiting; waiting is not an Execution Outcome. Long repair or blocking work may yield completion priority to another eligible Ticket instead of holding the whole frontier.

## Dispatch the fixed Ticket contract

Before dispatching or resuming an Execution Agent, or accepting its handoff, read [`references/ticket-execution.md`](references/ticket-execution.md) completely. It is the Execution Agent's protocol for the engineering loop, gate evidence, zero-diff verification, three Execution Outcomes, and stop/resume boundary. Give the Agent only that protocol and the context needed for one Ticket:

- Ticket identity, authoritative Ticket pointer, and any governing Spec pointer;
- Accepted direct inputs and their identities;
- the assigned Ticket Base identity;
- assigned branch and isolated workspace;
- scope, acceptance, and required-gate pointers;
- applicable user and Target Project constraints for this Agent and its downstream Agents, with pointers to existing approvals;
- local and external authority boundaries;
- the resolved execution-protocol pointer and a finalization instruction: a serial assignment permits work through final gates and review; a concurrent assignment either permits that work or explicitly defers it until current-Base confirmation and completion priority.

Carry these constraints into Runtime Skill invocations and downstream dispatches. Reuse existing approvals within their scope; if an explicit constraint cannot be met, report the limitation instead of silently substituting another configuration.

When multiple Tickets would repeat substantial exploration, optionally provide a relevant advisory note pointer with its question, source identities, applicability, and reading condition. Use a completed version with one writer in an off-delivery location reachable by the intended Agents; retain it under the existing resource rules. Exploration stays within the assigning owner's scope and does not delay otherwise runnable work. Consumption follows [Read the assignment and preserve its boundaries](references/ticket-execution.md#read-the-assignment-and-preserve-its-boundaries).

Scope inherited history as part of dispatch. Use the Agent Host's zero-history dispatch setting and provide the explicit Ticket contract above. When zero-history dispatch is unavailable, use the smallest available history window that excludes unrelated Tickets, Run Receipt state, and prior tool output. Do not rely on default full-history inheritance. The Execution Agent reconstructs implementation context from the assigned live workspace and authoritative pointers.

`Ready for Acceptance`, `Needs Decision`, and `Externally Blocked` are Execution Outcomes, not Ticket states. Apply the protocol's evidence requirements without repeating the engineering review. Resolve a `Needs Decision` choice within existing authority or ask the user; an `Externally Blocked` outcome has a settled choice and an owned external closing condition. Only the Coordinator Agent records graph transitions and acceptance.

## Accept a Baseline Satisfaction outcome

The Execution Agent gathers zero-diff evidence under the [execution protocol](references/ticket-execution.md#gather-zero-diff-evidence). For an operational deliverable, the Coordinator Agent follows that protocol's operation-identity and uncertain-result recovery rules before making or retrying specifically authorized remote operations. Keep the Ticket claimed and give actual results and readback identities to the Execution Agent to verify. Integration mirroring alone supplies no authority for these operations.

For an evidence-complete Baseline Satisfaction outcome, the Coordinator Agent serializes the decision against all Integration Transitions and rereads the Accepted Integration Tip commit and tree. They must still equal the audited Ticket Base identities. In Remote-mirrored mode, the Coordinator Agent also reads the selected remote branch and requires it to equal the same Ticket Base because the Accepted Integration Tip will not move. On a local mismatch, do not transition: preserve the identities, assign the current Accepted Integration Tip as the new Ticket Base, and return the same worktree to the same Ticket execution ownership to refresh its audit and gates. If the local Ticket Base is unchanged but the remote branch differs or cannot be read, leave the Ticket unaccepted and report the synchronization failure.

When those identities agree, recheck that direct prerequisites remain Accepted with their required outputs available, then verify the named rule and evidence. If the rule yields Accepted, record an Accepted Ticket and close the claim in the off-delivery recovery store, confirm the required output is available, then apply the Target Project-required stable tracker/evidence rule below before unlocking successors and recomputing the Runnable Frontier without moving the Accepted Integration Tip. If it yields Superseded, record a Superseded Ticket and close the claim in the same store, apply the same tracker/evidence rule, then recompute the effective graph; unlock work only when its effective prerequisite outputs are Accepted. Do not use Superseded as proof that a missing output exists.

## Persist Target Project-required stable tracker evidence

After an Accepted, Superseded, or reopened Ticket disposition is recorded, apply the Target Project's stable tracker/evidence rule with no active acceptance or Integration Transition. If the completing DAG Definition Checkpoint already contains the exact required update, record that update complete instead of creating another checkpoint. Otherwise, when the rule requires an in-history update, persist a pending required tracker update in the Run Receipt. Use the Target Project's exact field rules; when they do not determine a status, checklist, verdict, or evidence value, record a Coordinator-owned unresolved decision and leave that field unchanged.

Before a required tracker update has a candidate, record only the affected Tickets, governing rule, and exact stable state and evidence identities. Once its candidate exists, move those identities into one typed pending DAG Definition Checkpoint Integration Transition and clear the pre-candidate update entry; do not keep two pending states for the same work.

With no Integration Transition active, complete the pending update through the DAG Definition Checkpoint rules in [`references/definition-binding.md`](references/definition-binding.md). A required per-Ticket update completes before successor unlocking or another claim. An explicitly batched rule may remain pending while graph-independent work proceeds, but it must complete before a DAG Revision, before another checkpoint consumes live tracker state, and before evaluating a Terminal Outcome. When the Target Project requires no stable tracker or acceptance evidence in history, continue without creating a checkpoint.

After exact local and applicable remote publication, record the update complete and clear its pending state. A failed or drifted update preserves the recorded Ticket disposition and pending update; tracker failure alone neither changes acceptance nor reruns delivery work.

## Promote exact reviewed Integration Transitions

Before the Coordinator Agent begins the serialized Integration Transition for a `Ready for Acceptance` Promotion Candidate, verify:

- the current Accepted Integration Tip equals the recorded Ticket Base;
- the candidate descends from that Ticket Base and the recorded range resolves to the candidate's exact commit and tree;
- the candidate workspace is clean and the diff is within the approved Ticket scope;
- direct prerequisites remain Accepted with their required outputs available, and evidence dispositions account for affected previously accepted obligations;
- the candidate preserves the recorded DAG Definition Index, selected path set, and content identities and excludes every Run Receipt or other transient run-state path;
- required gates are current for the candidate's final bytes;
- the Candidate Review Record binds the complete `$code-review` result exactly as returned to that Ticket Base, candidate, tree, and range;
- every review finding and declared omission has an evidence-backed disposition, and no supported blocking finding remains.

Do not reinterpret the implementation or repeat equivalent review. Return missing or inconsistent evidence to the same Ticket execution ownership with one precise condition.

### Refresh an outdated Ticket Base

If another acceptance changed the Accepted Integration Tip, or live recovery proves the assigned Ticket Base wrong, do not promote or review against that Ticket Base. Record a corrected Ticket Base equal to the current Accepted Integration Tip and return the same worktree to the same Ticket execution ownership. The Execution Agent reapplies its changes safely and follows the [gate evidence validity rule](references/ticket-execution.md#keep-gate-evidence-valid): only proven valid product gates may be reused; affected, invalidated, and project-required candidate-specific checks run again. Every new candidate requires a fresh Candidate Review Record. Preserve the old record as superseded evidence.

### Serialize Integration Transitions

Apply the pre-CAS, local readback, publication, and recovery sequence in [`references/integration-transitions.md`](references/integration-transitions.md). Only one Integration Transition may run, and it completes from the identities frozen under that reference.

Complete a Promotion Candidate only after it becomes the published Accepted Integration Tip, then accept its Ticket and clear that Integration Transition before applying the Target Project-required stable tracker/evidence rule above. Complete a DAG Definition Checkpoint with the same frozen Definition and audit evidence, accept no Ticket, and only then assign its Accepted Integration Tip as downstream Ticket Base. Pending or drifted synchronization blocks both transitions and every later promotion.

## Escalate only boundary changes

Keep implementation defects, tests, review findings, probes, command corrections, candidate rounds, and diff size inside the Ticket execution ownership. Escalate only evidence that changes a graph, product, authority, or integration boundary: a missing predecessor output, invalid edge, misplaced Acceptance Obligation, independently acceptable split, semantic or gate decision, external promotion condition, or cross-Ticket conflict.

When Tickets must be created, replaced, or changed, apply the Target Project's existing DAG Revision rules. Preserve replaced Tickets as provenance, map every unresolved Acceptance Obligation to an effective Ticket, and revalidate identities, acyclicity, Hard Dependencies, and acceptance-impact dispositions through the DAG Definition Checkpoint rules above. If the rule or authority is unclear, record a Coordinator-owned unresolved decision and leave the graph unchanged.

This graph-replacement rule applies only before a Ticket enters an active Integration Transition. A Promotion Candidate pending remote synchronization stays assigned to its original Ticket until synchronization and acceptance finish; a pending DAG Definition Checkpoint remains owned by the Coordinator Agent until DAG Definition binding finishes. Then recompute the graph with any evidence queued during the Integration Transition.

When a revision removes any other claimed Ticket, first establish that its writer has stopped and its worktree is quiescent. Preserve its worktree, candidate, Candidate Review Record, and Execution Outcome evidence; then atomically record a Superseded Ticket, close its claim in the off-delivery recovery store, and apply the Target Project-required stable tracker/evidence rule before dispatching any replacement Ticket. If the writer is still live or uncertain, use the recovery boundary below and do not start a replacement writer.

## Reopen a failed Accepted obligation

When the current accepted delivery is shown to violate an obligation, identify its effective owning Ticket. Continue an active in-scope ownership path; otherwise, with no active Integration Transition, use existing project rules and authority to reopen that Ticket in the recovery store, preserving the historical acceptance and failure evidence. Keep the integration tip and later deliveries. A regression introduced by an unaccepted candidate stays in that candidate's execution loop. Changed responsibility, scope, dependencies, or accepted meaning follows the existing DAG Revision rules; an undefined status mapping or authority is a precise Coordinator-owned decision.

Complete any required per-Ticket tracker checkpoint before claiming the reopened Ticket. Assign the resulting current Accepted Integration Tip as Ticket Base and one Execution Agent after the writer-liveness checks below. Preserve and reuse available workspace and WIP; if an inactive workspace was already reclaimed, create one from that Base with the retained evidence pointers. The normal execution and acceptance paths apply, including current gates and fresh candidate review. An ordinary in-scope repair reuses existing execution authority.

Audit consumers by the affected output identities, contracts, and evidence. Preserve and pause active ownership that depends on invalid outputs; reopen an Accepted consumer only when its obligation is also shown unsatisfied. A prerequisite reopening does not automatically revoke all historical consumer acceptances, and its later acceptance does not restore failed consumers without evidence. New claims and final acceptance still require Accepted direct inputs; independent work can continue.

Queue unrelated findings until an active Integration Transition completes. Evidence invalidating its own candidate instead follows [frozen-evidence reconciliation](references/integration-transitions.md#reconcile-the-local-integration-ref); preserve the pending record and refs and resolve the failed prerequisite, rather than accepting a known-invalid candidate to reach the reopening path.

## Resume safely and finish

On resume, repeat [Reconstruct the live run](#reconstruct-the-live-run) and reread [`references/integration-transitions.md`](references/integration-transitions.md) before reconciling refs or frozen evidence. Before the first Accepted Integration Tip exists, revalidate Starting Base plus initial DAG Definition binding and publication; afterward require the recorded Accepted Integration Tip to preserve the validated DAG Definition Index result and selected input identities. Reconstruct any pending required tracker update from its recorded rule and identities; once it has a candidate, recover it only as the typed DAG Definition Checkpoint Integration Transition. Complete it before scheduling work that its recorded update rule blocks. Continue live execution instead of duplicating it.

If writer liveness is uncertain, preserve the claim and workspace and do not dispatch. The Coordinator Agent must establish one observable boundary: resume/contact the existing task, obtain an acknowledged stop, or use an authorized Agent Host-level termination and then verify the workspace is quiescent. Until then, record the liveness owner and recheck event as an external closing condition and continue only graph-independent work. Never infer writer death from silence or elapsed time.

After a verified stop, resume the existing workspace and evidence with one writer. If the Agent must change, first confirm that the original Agent has stopped, then hand the original Ticket, branch, worktree, and WIP to the replacement Agent. The replacement rereads the live state and continues it without resetting or recreating WIP.

Use the Run Receipt's resource inventory for run-owned branches, worktrees, Agent tasks, temporary environments, caches, and evidence. Reclaim reproducible inactive resources within existing authority. Preserve live writers, user or other-run resources, unique WIP or evidence, and anything still needed for recovery. Before disposing of an evidence-bearing resource, verify its retained artifacts and references. Record each resource as disposed, retained, or pending with its reason or required action; when additional destructive authority is needed, retain it and record that requirement.

Before Complete, account for every current in-scope governing Spec obligation and bind the coverage and evidence-applicability audit to the final Definition and Accepted Integration Tip commit/tree, after required checkpoints. Keep historical tested identities and review records intact. Retain coverage only with evidence that relevant product behavior, inputs, gate definitions, environment, and coverage still apply; refresh affected evidence and run project-required current-tip checks. Whole-DAG gates must cover this final delivery. This audit establishes current applicability, not a new Candidate Review Record or permission to weaken candidate-specific gates. Missing evidence calls for verification; a proved defect follows [Reopen a failed Accepted obligation](#reopen-a-failed-accepted-obligation). Tip movement alone requires neither reopening every Ticket nor rerunning every check.

Report a **Complete** Terminal Outcome only when this coverage and applicability audit is satisfied, the final DAG Definition Index and selected inputs are bound to the Accepted Integration Tip, every effective Ticket is Accepted under that Definition, every Superseded Ticket's current Acceptance Obligation is accounted for, no active claim remains, whole-DAG gates and dependency consumption agree, the selected Integration Publication Mode is satisfied, Target Project-required stable tracker and acceptance evidence are current, and no required tracker update remains pending. In Remote-mirrored mode, the local Accepted Integration Tip and readback of the selected remote branch must agree.

Resolve every Coordinator-owned unresolved decision affecting DAG execution or acceptance and every `Needs Decision` Execution Outcome before evaluating a Terminal Outcome. While an actionable choice is unanswered, retain its owner and required decision in the Run Receipt and report the applicable decision evidence; do not relabel it Stalled. If a completed decision leaves only an unavailable external condition, record its owner and closing event as `Externally Blocked` when an Execution Agent owns that outcome, or as an external closing condition otherwise.

Report a **Stalled** Terminal Outcome only after writer liveness is resolved, no Coordinator-owned unresolved decision affecting DAG execution or acceptance remains, no `Needs Decision` Execution Outcome remains, and unfinished Tickets have no running Execution Agent, Runnable Frontier entry, authorized ticket-local recovery, graph correction, independent work, or currently satisfiable external closing condition. A still-running Execution Agent prevents Stalled, and an ordinary in-scope finding stays ticket-local.

Return an evidence-backed summary of the Terminal Outcome; DAG Definition Index, selected inputs, and latest DAG Definition Checkpoint; Accepted Tickets, Superseded Tickets, active Tickets, decision-needed and externally blocked Execution Outcomes, acceptance-impact dispositions, and any pending required tracker update; the Accepted Integration Tip and selected Integration Publication Mode; the selected remote, remote branch, and exact readback when applicable; verification and review performed or omitted; graph decisions; and liveness conditions. Report resource dispositions separately from Complete or Stalled; pending disposal alone does not change that outcome when required acceptance and recovery evidence remains available.
