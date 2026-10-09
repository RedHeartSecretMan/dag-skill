# Create, promote, and recover Integration Transitions

Read this reference before creating or resuming a DAG Integration Branch, choosing its Integration Publication Mode, starting any Integration Transition, or recovering local or remote synchronization. Only one Integration Transition may be active at a time.

## Select one publication mode

- **Local-only** keeps the Accepted Integration Tip in the local repository.
- **Remote-mirrored** maps the local DAG Integration Branch to one configured Git remote and one full `refs/heads/...` branch. Use the local branch name remotely unless the user or Target Project selects another.

Reuse a mode and mapping fixed by the Target Project or recoverable Run Receipt. Otherwise decide once before the first Ticket claim:

- an explicit instruction to mirror or push the DAG Integration Branch selects Remote-mirrored when the remote and ref are unambiguous;
- “if a remote exists, synchronize it” selects the only configured remote, selects Local-only when none exists, and requires a choice when several exist;
- no stated synchronization requirement selects Local-only, whether or not remotes are configured; record the selection and continue local execution;
- required synchronization without a configured remote requires the user to supply its name and URL and authorize `git remote add`;
- an ambiguous remote or branch requires only the missing selection.

Use a dedicated integration branch. A default or protected branch, pull-request-only path, alternate ref, Ticket branch, force-push, or mapping change needs separate authority and reconciliation before claims or promotion.

Keep the recovered mode during failures: an unavailable remote does not turn Remote-mirrored into Local-only. A separately authorized release Ticket can perform its specified external operations in either mode; integration mirroring alone grants no release authority.

## Run Receipt and frozen evidence

Use the Target Project's tracker as the recovery store only when it remains off-delivery; otherwise use a separate off-delivery store. Keep the Run Receipt as a compact index of current identities and evidence pointers:

| Concern | Required recoverable information |
| --- | --- |
| Integration | Starting Base; Accepted Integration Tip once established; local integration ref; publication mode; selected remote/ref and last synchronized commit when applicable |
| Definition | Index identity and validated result; selected input identities; binding commit/tree and latest completed Definition checkpoint |
| Capability | Verified Agent Host, stable Skills root, Runtime Skill source commits and content identities |
| Ticket ownership | Claims, Agent liveness, Ticket Base, candidate, branch/worktree and WIP pointers; Execution Outcomes and their evidence |
| Outstanding work | Pending tracker update or typed Integration Transition; authorized external operation request and native lookup/idempotency identities, result/readback pointers and unresolved conditions; decisions and external closing conditions with owners and next actions |
| Resources | Run-owned resources, ownership, retained evidence and recovery pointers, and disposition |

Link complete reports instead of copying them into the receipt. The receipt indexes the tracked Definition binding; it never replaces it or enters delivery history. Target Project-required stable tracker or acceptance evidence enters history through an authorized Definition checkpoint, whose own completion record remains off-delivery.

For zero-diff external actions that could repeat side effects, follow [operation preparation and result recovery](ticket-execution.md#gather-zero-diff-evidence).

Before moving the integration ref, freeze one pending Integration Transition with its candidate kind, Base, candidate commit/tree, and exact gate/review evidence. A Definition checkpoint also binds its validated index and inputs, acceptance-impact dispositions, and audit identities. The frozen local promotion record below can be that Transition's authoritative record, referenced by path and digest from the receipt. Record subsequent local/remote readbacks without replacing the frozen evidence. The receipt remains the compare source for reconciliation; ordinary claim or resource updates do not create checkpoints.

## Reconcile the local integration ref

Select Starting Base only from a Target Project rule, explicit user instruction, or existing accepted integration evidence. Keep the full local DAG Integration Branch ref out of every worktree and use the Run Receipt as its compare source.

| Receipt state | Allowed local ref | Action |
| --- | --- | --- |
| No Accepted Integration Tip, no pending Transition | Starting Base | Revalidate initial Definition binding and publication |
| Accepted Integration Tip, no pending Transition | Accepted Integration Tip | Continue from the accepted state |
| Pending Transition before compare-and-swap | Recorded Base | Verify and reuse the exact frozen evidence, then resume |
| Pending Transition after compare-and-swap | Recorded candidate | Verify the commit/tree and exact frozen evidence, then complete Local-only or reconcile Remote-mirrored |

Any missing ref, other SHA, or incomplete receipt is drift. Preserve refs and evidence and obtain explicit reconciliation.

Frozen evidence is immutable within one pending Transition. On a Base match, changed or invalid review, gate, disposition, audit, Base, or candidate identity requires the Coordinator Agent to cancel the pending Integration Transition before local promotion, preserve its record as superseded evidence, and create and freeze a new Integration Transition. On a candidate match, evidence replacement is impossible.

## Initialize Remote-mirrored

Initialize only after the local DAG Definition bytes and DAG Integration Branch tip are verified and live evidence proves the mapping has never existed.

1. Query the full remote ref.
2. Exact equality with the local tip completes initialization without a push.
3. An absent ref, or a remote commit proved to be an ancestor of the local tip, permits one ordinary `git push -u <remote> <local-integration-ref>:<remote-integration-ref>`.
4. Query again; only exact equality establishes the first Accepted Integration Tip and records the last synchronized commit.

A non-ancestor SHA is drift. A failed push or read leaves initialization pending; resume starts with readback. A missing receipt field never proves a new mapping.

For an established mapping with no pending Transition, require the local Accepted Integration Tip and remote ref to equal the recorded last synchronized commit before claims or checkpoint promotion. An absent or different remote ref is drift.

## Start one serialized transition

An Integration Transition records one candidate kind, exact Base, candidate commit/tree, and frozen candidate-bound evidence. Candidate kind is Promotion Candidate or DAG Definition Checkpoint.

Immediately before promotion:

1. reread the live Base, graph, candidate kind, commit/tree, and bound evidence;
2. require the candidate to descend from Base and every frozen identity to match;
3. for a Promotion Candidate, require its Ticket and Candidate Review Record to remain acceptable;
4. for a DAG Definition Checkpoint, require the approved Definition source, validator result, review, and acceptance-impact evidence to remain current;
5. persist the complete pending Transition and reread its exact bytes and evidence identities before moving the ref.

Hold that graph and evidence fixed until completion. Process later graph evidence afterward.

Complete preparation, persistence/readback, local compare-and-swap, and ref readback as a fail-closed sequence. A nonzero exit, incomplete output, or identity mismatch stops the sequence. Preserve the pending evidence and repair the failed prerequisite before retrying; a later tool call must not skip directly to ref mutation.

Use the bundled helper for the local compare-and-swap and readback:

```bash
python3 <this-skill-root>/scripts/promote_local_transition.py \
  --repository <target-project-root> \
  --transition <off-delivery-pending-record.json> \
  --sha256 <verified-record-sha256>
```

Run the helper from an existing non-bare Target Project checkout. It advances only the exact un-checked-out local branch from Base to candidate and reads back its commit/tree, with Git hooks disabled for that ref update. The reviewed bytes are promoted directly: no merge, recreation, amendment, or evidence substitution. The Coordinator retains responsibility for the semantic checks above, publication authority, and eventual acceptance.

### Frozen local promotion record

The helper consumes one immutable JSON record for the existing pending Integration Transition. Store its path and SHA-256 in the Run Receipt as that Transition's reference, rather than maintaining another mutable copy of the pending state. After successfully preparing and persisting it, verify the record and retain its digest for both the initial call and recovery.

```json
{
  "schema_version": 1,
  "candidate_kind": "Promotion Candidate",
  "integration_ref": "refs/heads/codex/example-integration",
  "base": "<full-commit-object-id>",
  "candidate": "<full-commit-object-id>",
  "candidate_tree": "<full-tree-object-id>",
  "evidence": [
    {"path": "acceptance-audit.json", "sha256": "<file-sha256>"}
  ]
}
```

`candidate_kind` is `Promotion Candidate` or `DAG Definition Checkpoint`. The other fields are required exactly as shown; object IDs name full local objects and the candidate must be a descendant commit distinct from Base. Evidence paths resolve relative to the record's directory unless absolute. Bind the off-delivery reports and logs needed to verify frozen gates, complete reviews, finding dispositions, and applicable Definition/acceptance-impact audits. Source inputs already bound by Git retain their commit/blob identities in those reports; they need no duplicate filesystem copy. Unbound external artifacts need their own evidence entries. The helper verifies file bytes and Git identities; it does not infer whether project-specific evidence proves acceptance.

Keep the record and evidence off-delivery and unchanged for the duration of the pending Transition. Run with one Coordinator and quiescent record, evidence, and integration-worktree ownership; this is a local Git CAS, not a transaction across arbitrary concurrent filesystem writers. The helper checks the record digest, evidence hashes, ancestry, candidate tree, direct branch identity, and worktree use before mutation. Git replace refs and grafts are disabled so ancestry comes from the actual commit objects. It leaves the record and evidence untouched and never writes a remote, completes the Run Receipt, or marks a Ticket Accepted.

Exit `0` returns JSON with `status` equal to `local-promoted` or `local-already-promoted`, plus the frozen identities and record digest. The latter recognizes the same candidate during recovery after rechecking the same frozen evidence. Both are local readback results; Remote-mirrored still requires remote reconciliation. Errors return nonzero with `error: ...` on stderr. After an error, reread the ref: Base means promotion has not happened; candidate means preserve the pending Transition and resume readback/publication; any other SHA is drift. A post-CAS error never authorizes rollback or evidence replacement.

## Complete or recover the transition

Local-only completes after exact local readback. Remote-mirrored keeps the typed Transition pending until the selected remote ref equals its candidate.

For an established mapping:

1. Query the selected remote and full remote ref.
2. Candidate equality completes synchronization without pushing.
3. Last-synchronized equality permits the same ordinary fast-forward push from the local integration ref, followed by another query.
4. An absent ref or any other SHA is remote drift; report candidate, last synchronized commit, and observed identity without pushing.
5. A failed push or read preserves the pending Transition and exact error; resume again from step 1.

Never force-push, switch refs, invent a retry state, or substitute a pull-request workflow.

After publication agrees, complete exactly one candidate kind:

- **Promotion Candidate**: record an Accepted Ticket, make the candidate the DAG Milestone and Accepted Integration Tip, record last synchronization when applicable, and close the claim.
- **DAG Definition Checkpoint**: record the same frozen index result, selected inputs, acceptance-impact dispositions, audit identities, and any completed Target Project-required stable tracker/evidence update; make the candidate the Accepted Integration Tip and downstream Ticket Base; accept no Ticket and apply the dispositions.

This completes and clears the typed pending Integration Transition. Only after that completion, apply the Target Project-required tracker/evidence rule in [`SKILL.md`](../SKILL.md#persist-target-project-required-stable-tracker-evidence). If it requires another DAG Definition Checkpoint, start it as the next serialized Integration Transition; do not nest it inside the completed Transition. Recompute the graph and Runnable Frontier, unlock successors, or claim another Ticket only after any required per-Ticket update completes.

Until the current Transition completes, do not accept the Ticket, unlock successors, claim the next Ticket, or start another Integration Transition.
