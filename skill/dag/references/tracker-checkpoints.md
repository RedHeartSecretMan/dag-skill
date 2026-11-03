# Tracker Policy and Checkpoints

`record_tracker_policy.py` and `record_tracker_checkpoint.py` are the Coordinator-owned CAS boundaries for synchronizing Target Project tracker state without parsing Markdown, checklists, or project-specific status words. The Coordinator owns project-rule interpretation and prose edits; the helpers verify schemas, paths, Git object identities, SHA-256 digests, and Run Receipt generation CAS.

## Record the Tracker Policy before the first claim

```bash
python3 <this-skill-root>/scripts/record_tracker_policy.py \
  --receipt <off-delivery>/run-receipt.json \
  --policy <off-delivery>/tracker-policy.json \
  --output <off-delivery>/tracker-policy-record.json \
  --expected-generation <current-coordinator-generation> \
  --expected-receipt-sha256 <current-receipt-sha256> \
  --repository <target-project-root> \
  --commit <accepted-integration-tip>
```

The `Tracker Policy` has `schema_version: 1` and `kind: Tracker Policy`, and defines:

- `run_id`: active run identity matching the Run Receipt;
- `mode`: `none`, `in_repo`, or `external_snapshot`;
- `authoritative_paths`: repository-relative tracker or normalized snapshot roots (`[]` when `mode` is `none`, non-empty otherwise);
- `rule_refs`: non-empty list of `{id, path, identity}` entries naming the Target Project rule documents and their tracked Git blob OID or `sha256:` digest;
- `definition_paths`: repository-relative paths selected by `.dag/definition-index.json`;
- `tracker_paths`: repository-relative paths mutated by Coordinator tracker updates (`[]` when `mode` is `none`, non-empty otherwise);
- `update_scope`: `none` when `mode` is `none`, or `per_ticket` / `batched` when `mode` is `in_repo` or `external_snapshot`;
- `rationale`: concise explanation of the selected mode and rule basis;
- `stateful_tracker_decision`: `null` by default, or `{decision_id, approved_by, overlapping_paths, rationale}` when an explicit mixed-file exception is authorized.

`definition_paths` and `tracker_paths` cannot overlap by default, including parent/child directory prefixes. Split mixed plans into stateless Definition inputs and separate tracker files before binding. Record `stateful_tracker_decision` only when an explicit user or Target Project decision requires mixed stateful files; `overlapping_paths` must cover every overlap, and `mode: none` never permits overlap. When Target Project tracker rules are ambiguous, record `Needs Decision` as an unresolved decision in the Run Receipt instead of defaulting to `none`.

Execution Agents never modify `tracker_paths`; `record_execution_claim.py` rejects claims whose paths overlap `tracker_paths` and blocks successor unlocking (or all claims under `per_ticket` scope) while `pending_tracker_updates` remain in the Run Receipt.

## Complete a Tracker Checkpoint

Follow the fixed Ticket completion sequence:

`Accepted/Superseded → Tracker Policy → Tracker Checkpoint → review → Definition Checkpoint → readback → successor unlock`

When `mode` is `in_repo` or `external_snapshot`, `record_ticket_disposition.py` records a pending tracker update in the Run Receipt. Before unlocking successors or evaluating `Complete`:

1. Create an isolated Coordinator checkpoint commit (`candidate`) from the current Accepted Integration Tip (`base`), updating only `tracker_paths` (plus `.dag/definition-index.json` when `stateful_tracker_decision` covers a changed Definition path).
2. Optionally run `--preflight` to verify schema, `policy_key`, bound dispositions, path scope, exact `git diff-tree` `changed_paths`, and `before_blob_oid` / `after_blob_oid` identities before review:

   ```bash
   python3 <this-skill-root>/scripts/record_tracker_checkpoint.py \
     --preflight \
     --repository <target-project-root> \
     --receipt <off-delivery>/run-receipt.json \
     --checkpoint <off-delivery>/tracker-checkpoint.json \
     --output <off-delivery>/tracker-checkpoint-preflight.json
   ```

3. Obtain fresh `$code-review` on `base...candidate`, promote the candidate through the serialized `DAG Definition Checkpoint` Integration Transition (`promote_local_transition.py`), and verify local (and applicable remote) readback.
4. Record the completed `Tracker Checkpoint` through CAS:

   ```bash
   python3 <this-skill-root>/scripts/record_tracker_checkpoint.py \
     --repository <target-project-root> \
     --receipt <off-delivery>/run-receipt.json \
     --checkpoint <off-delivery>/tracker-checkpoint.json \
     --output <off-delivery>/tracker-checkpoint-record.json \
     --expected-generation <current-coordinator-generation> \
     --expected-receipt-sha256 <current-receipt-sha256>
   ```

The `Tracker Checkpoint` has `schema_version: 1` and `kind: Tracker Checkpoint`, and binds `run_id`, `coordinator_generation`, `policy_key`, `integration_ref`, `ticket_dispositions` (`{ticket_id, claim_generation, disposition}`), `base` (`{commit, tree}`), `candidate` (`{commit, tree}`), `changed_paths`, `blob_changes` (`{path, before_blob_oid, after_blob_oid}`), and `evidence_refs` (`{id, path, sha256}`).

The helper verifies exact Git ancestry, `integration_ref` readback equal to `candidate.commit`, exact `changed_paths` and `before`/`after` blob OIDs from `git diff-tree`, current `policy_key`, effective Receipt dispositions, `.dag/definition-index.json` validity when stateful Definition paths change, off-delivery file placement, and evidence digests. It then CAS-appends the checkpoint, clears covered `pending_tracker_updates`, and increments `coordinator_generation`. Repeating the identical submission with the updated Receipt generation is idempotent.
