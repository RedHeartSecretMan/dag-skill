# Bind and validate a DAG Definition

Read this reference before accepting an existing DAG Definition, creating a DAG Definition Checkpoint, or applying a DAG Revision. The binding is complete only when an exact commit passes the deterministic index validator and every semantic check below.

## Validate the exact commit

Run the bundled validator against the Starting Base, current Accepted Integration Tip, or exact DAG Definition Checkpoint commit under review:

```bash
python3 <this-skill-root>/scripts/validate_definition_index.py \
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
- Stable tracker or acceptance evidence joins a DAG Definition Checkpoint only when the Target Project explicitly requires that audit trail.

When a source mixes Definition and run state, use the Target Project's existing definition-only paths or snapshot format. If no safe rule preserves the complete approved plan without persisting sensitive or unauthorized content, record the exact Coordinator-owned unresolved classification, persistence, or layout decision and stop binding.

## Complete a DAG Definition Checkpoint

Create an isolated checkpoint from Starting Base before the first Accepted Integration Tip, or from the current Accepted Integration Tip later. The checkpoint:

1. changes only approved Definition inputs, `.dag/definition-index.json`, and Target Project-required stable audit evidence;
2. excludes the Run Receipt, transient state, and its own completion record;
3. passes the validator on its exact candidate commit plus graph identity, acyclicity, reference, scope, sensitive-data, acceptance-impact, and applicable documentation gates;
4. receives fresh independent Standards/Spec review bound to its Base, candidate commit/tree, and evaluated range, with every finding disposition complete;
5. freezes all candidate-bound evidence before local compare-and-swap and completes the applicable Integration Publication Mode.

Any byte change invalidates prior gates and review. A completed checkpoint becomes the Accepted Integration Tip and downstream Ticket Base, accepts no Ticket, and creates no DAG Milestone.

For a DAG Revision, identify every affected active, Accepted, or Superseded Ticket before promotion. Preserve and pause affected active ownership; audit old evidence against the new obligations or use approved rules to reopen or reassign it. Freeze the complete disposition and audit set with the checkpoint. Only after the checkpoint completes may affected work receive its new Ticket Base and resume.
