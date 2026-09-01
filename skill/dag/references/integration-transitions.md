# Create, promote, and recover Integration Transitions

Read this reference before creating or resuming a DAG Integration Branch, choosing its Integration Publication Mode, starting any Integration Transition, or recovering local or remote synchronization. Only one Integration Transition may be active at a time.

## Select one publication mode

- **Local-only** keeps the Accepted Integration Tip in the local repository.
- **Remote-mirrored** maps the local DAG Integration Branch to one configured Git remote and one full `refs/heads/...` branch. Use the local branch name remotely unless the user or Target Project selects another.

Reuse a mode and mapping fixed by the Target Project or recoverable Run Receipt. Otherwise decide once before the first Ticket claim:

- an explicit instruction to mirror or push the DAG Integration Branch selects Remote-mirrored when the remote and ref are unambiguous;
- “if a remote exists, synchronize it” selects the only configured remote, selects Local-only when none exists, and requires a choice when several exist;
- no configured remote and no synchronization requirement selects Local-only;
- configured remotes without stated synchronization intent require one Local-only versus Remote-mirrored decision;
- required synchronization without a configured remote requires the user to supply its name and URL and authorize `git remote add`;
- an ambiguous remote or branch requires only the missing selection.

Use a dedicated integration branch. A default or protected branch, pull-request-only path, alternate ref, Ticket branch, force-push, or mapping change needs separate authority and reconciliation before claims or promotion.

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
5. persist the complete pending Transition before moving the ref.

Hold that graph and evidence fixed until completion. Process later graph evidence afterward.

Advance the full local ref with exact compare-and-swap, for example:

```bash
git update-ref <integration-ref> <candidate> <Base>
```

Read back the commit and tree. The ref must not be checked out. The reviewed bytes are promoted directly: no merge, recreation, amendment, or evidence substitution.

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

- **Promotion Candidate**: record an Accepted Ticket, make the candidate the DAG Milestone and Accepted Integration Tip, record last synchronization when applicable, close the claim, unlock successors, and recompute the Runnable Frontier.
- **DAG Definition Checkpoint**: record the same frozen index result, selected inputs, acceptance-impact dispositions, and audit identities; make the candidate the Accepted Integration Tip and downstream Ticket Base; accept no Ticket, apply the dispositions, and recompute the graph and Runnable Frontier.

Until completion, do not accept the Ticket, unlock successors, claim the next Ticket, or start another Integration Transition.
