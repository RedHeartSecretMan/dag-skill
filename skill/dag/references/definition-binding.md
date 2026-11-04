# Bind and validate a DAG Definition

Read this reference before accepting an existing DAG Definition, creating a DAG Definition Checkpoint, or applying a DAG Revision. The binding is complete only when an exact commit passes the deterministic index validator and every semantic check below.

## Validate the exact commit

Run the bundled validator against the Starting Base, current Accepted Integration Tip, or exact DAG Definition Checkpoint commit under review:

```bash
python3 <this-skill-root>/scripts/verify.py definition-index \
  --repository <target-project-root> \
  --commit <exact-commit>
```

The command first queries only `.dag/definition-index.json`, then queries only the paths selected by that index. It reads locally available Git objects from the named commit, ignores ambient `GIT_*` repository overrides, disables replace refs, and disables partial-clone lazy fetch. A missing object blocks validation without contacting a promisor remote or changing the object store. Unselected Git paths are never enumerated and cannot affect validation. Exit `0` writes one normalized JSON result to stdout containing the resolved commit, index blob identity, schema version, and ordered inputs. A contract failure writes `error: ...` to stderr and exits nonzero. Never substitute working-tree bytes for this result.

The validator enforces:

- the sole selector is repository-root `.dag/definition-index.json`, stored as one regular non-executable Git blob;
- the UTF-8 JSON object contains exactly `schema_version` and a non-empty `inputs` array, with integer `schema_version: 1`;
- duplicate JSON object fields are invalid, and every input object contains exactly `path` and `blob_oid`;
- paths are unique NFC UTF-8 POSIX repository-relative paths, sorted by UTF-8 bytes, with no absolute path, empty segment, `.`, `..`, `.git`, backslash, NUL, or reference to the index itself;
- every selected path resolves at the named commit to an ordinary tracked blob (`100644` or `100755`) whose Git object identity equals `blob_oid`;
- every selected blob is UTF-8 full content, not a symlink, gitlink, missing object, or Git LFS pointer.

Two indexes are **equivalent** only when their validator results have the same schema version and identical ordered `(path, blob_oid)` inputs. JSON whitespace, object-key order, and the index blob's own identity do not change that semantic comparison; record the actual index blob identity from the validated commit as binding evidence.

If the Target Project forbids the canonical selector, record a Coordinator-owned unresolved decision for compatibility. Keep Definition binding incomplete instead of creating another selector.

## Classify Definition content

- In-repository governing Specs and Tickets are Definition inputs.
- Represent an external tracker with a tracked normalized snapshot containing the complete governing Spec and Ticket content, Hard Dependencies, Acceptance Obligations, source system and project, source item identities, and available version or update identities. Copy authoritative fields without semantic summarization; a pointer, digest, manifest, symlink, or LFS pointer is insufficient.
- Claims, Agents, workspaces, liveness, pending synchronization, acceptance results, and the Run Receipt are transient run state and stay off-delivery.
- Stable tracker or acceptance evidence joins a DAG Definition Checkpoint when the Run Receipt's `Tracker Policy` (`in_repo` or `external_snapshot`) requires it under [`completion.md`](completion.md#tracker-policy).

`definition_paths` and `tracker_paths` in the `Tracker Policy` must not overlap by default. When a source mixes Definition obligations with mutable Ticket status or checklists, split it into stateless Definition inputs and separate tracker files before binding. Record an explicit `stateful_tracker_decision` in the `Tracker Policy` only when an authorized Target Project or user decision requires mixed stateful files; `mode: none` never allows overlap. If Target Project rules are ambiguous or no safe rule preserves the approved plan without persisting sensitive or unauthorized content, record `Needs Decision` as a Coordinator-owned unresolved decision in the Run Receipt and stop binding.

## Persist required stable tracker state

Follow the fixed sequence `Accepted/Superseded → Tracker Policy → Tracker Checkpoint → review → Definition Checkpoint → readback → successor unlock` in [`completion.md`](completion.md#tracker-checkpoints). When `Tracker Policy` uses `in_repo` or `external_snapshot`, freeze the affected Tickets' `Accepted`, `Superseded`, or reopened dispositions, active `policy_key`, changed tracker paths, before/after Git blob identities, and evidence digests before promotion. Record a reopen disposition only with no active Integration Transition, preserving historical acceptance and evidence. Classify every changed path against the currently validated DAG Definition Index:

- With disjoint `definition_paths` and `tracker_paths`, a tracker checkpoint changes only `tracker_paths` unselected by the index, preserving the validated index, selected path set, and every selected blob identity.
- When an authorized `stateful_tracker_decision` covers overlapping paths, any edit to a selected Definition path is a full DAG Definition change: update `.dag/definition-index.json` to the new blob identities in the same checkpoint and perform the complete Definition and acceptance-impact audit.

If one tracked path mixes Definition with run state, use the split or normalized snapshot rule above before either path. Every checkpoint excludes the Run Receipt and all transient run state.

Apply the Target Project's exact rules for status, checklist, verdict, comments, and evidence, including reopening. Helpers never parse Markdown or project status prose. If those rules do not determine a field from the frozen acceptance disposition, PASS, FAIL, or BLOCKED result, record a Coordinator-owned unresolved decision (`Needs Decision`) instead of inferring status or checklist changes. Run the applicable tracker integrity, scope, sensitive-data, documentation, review, and publication gates on the exact candidate, complete the [DAG Definition Checkpoint](#complete-a-dag-definition-checkpoint) and [Integration Transition](integration-transitions.md#start-one-serialized-transition) with readback, and then CAS-record completion with `scripts/commit.py tracker-checkpoint` before unlocking successors.

Complete a required per-Ticket reopen update before restoring its claim or resuming affected work; then assign the current Accepted Integration Tip as Ticket Base. An explicitly batched rule permits only the independent work it allows while the update is pending, under the [required tracker update lifecycle](../SKILL.md#persist-target-project-required-stable-tracker-evidence).

For a state/evidence-only checkpoint, compare the exact candidate's validator result with its Base and require an unchanged index blob identity, selected path set, and every selected blob identity. Use that invariance to preserve conclusions about unchanged graph identity, Hard Dependencies, and Acceptance Obligations. Bind a fresh tracker impact audit and independent Standards/Spec review to the checkpoint candidate, focused on the changed state mappings, verdicts, evidence identities and links, scope, sensitive data, tracker integrity, and required documentation gates. Existing Ticket delivery evidence keeps its original artifact identities; valid product gate reuse follows [Keep gate evidence valid](ticket-execution.md#keep-gate-evidence-valid). An index or selected input change takes the full Definition and acceptance-impact audit path instead.

## Complete a DAG Definition Checkpoint

Create an isolated checkpoint from Starting Base before the first Accepted Integration Tip, or from the current Accepted Integration Tip later. The checkpoint:

1. changes only approved Definition inputs, `.dag/definition-index.json`, and Target Project-required stable audit evidence;
2. excludes the Run Receipt, transient state, and its own completion record;
3. passes the validator on its exact candidate commit and the gates for its classified scope above; a Definition change requires the full graph identity, acyclicity, reference, scope, sensitive-data, acceptance-impact, and applicable documentation checks, including [governing Spec obligation ownership coverage](../SKILL.md#reconstruct-the-live-run);
4. receives fresh independent Standards/Spec review for that scope, bound to its Base, candidate commit/tree, and evaluated range, with every finding disposition complete;
5. freezes all candidate-bound evidence before local compare-and-swap and completes the applicable Integration Publication Mode.

Any byte change invalidates the prior checkpoint review and affected gate evidence. Revalidate the exact candidate and rerun all invalidated or project-required candidate-specific checks; retain other gate results only with the original identities and a fresh equivalence and impact audit under the reuse rule above. A completed checkpoint becomes the Accepted Integration Tip and downstream Ticket Base, accepts no Ticket, and creates no DAG Milestone.

For a DAG Revision, identify every affected active, Accepted, or Superseded Ticket before promotion. Preserve and pause affected active ownership; audit old evidence against the new obligations or use approved rules to reopen or reassign it. Freeze the complete disposition and audit set with the checkpoint. Only after the checkpoint completes may affected work receive its new Ticket Base and resume.
