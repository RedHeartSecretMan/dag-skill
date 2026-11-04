# Ticket Dispositions, Tracker Checkpoints, and Terminal Outcome Audit

Read this reference before recording the Run Receipt's `Tracker Policy`, closing a live Ticket claim with an `Accepted` or `Superseded` disposition, completing a `Tracker Checkpoint`, or verifying a `Complete` or `Stalled` Terminal Outcome.

## Tracker Policy

Before the first Ticket claim (and after any approved Definition change that alters path roles), record the run's `Tracker Policy` in the off-delivery Run Receipt through `scripts/commit.py tracker-policy`:

```bash
python3 <this-skill-root>/scripts/commit.py tracker-policy \
  --repository <target-project-root> \
  --commit <accepted-integration-tip> \
  --receipt <off-delivery>/run-receipt.json \
  --policy <off-delivery>/tracker-policy.json \
  --expected-generation <current-coordinator-generation> \
  --expected-receipt-sha256 <current-receipt-sha256>
```

The `Tracker Policy` has `schema_version: 1` and `kind: Tracker Policy`, and defines:

- `run_id`: active run identity matching the Run Receipt;
- `mode`: `none`, `in_repo`, or `external_snapshot`;
- `authoritative_paths`: repository-relative tracker or normalized snapshot roots (`[]` when `mode` is `none`, non-empty otherwise);
- `rule_refs`: non-empty list of `{id, path, identity}` entries naming the Target Project rule documents and their tracked Git blob OID or `sha256:` digest at `--commit`;
- `definition_paths`: repository-relative paths selected by `.dag/definition-index.json` at `--commit`;
- `tracker_paths`: repository-relative paths mutated by Coordinator tracker updates (`[]` when `mode` is `none`, non-empty otherwise);
- `update_scope`: `none` when `mode` is `none`, or `per_ticket` / `batched` when `mode` is `in_repo` or `external_snapshot`;
- `rationale`: concise explanation of the selected mode and rule basis;
- `stateful_tracker_decision`: `null` by default, or `{decision_id, approved_by, overlapping_paths, rationale}` when an explicit mixed-file exception is authorized.

`definition_paths` and `tracker_paths` cannot overlap by default, including parent/child directory prefixes. Split mixed plans into stateless Definition inputs and separate tracker files before binding. Record `stateful_tracker_decision` only when an explicit user or Target Project decision requires mixed stateful files; `overlapping_paths` must cover every overlap, and `mode: none` never permits overlap. When Target Project tracker rules are ambiguous, record `Needs Decision` as an unresolved decision in the Run Receipt instead of defaulting to `none`.

Execution Agents never modify `tracker_paths`; `scripts/commit.py claim` rejects claims whose paths overlap `tracker_paths` and blocks successor unlocking (or all claims under `per_ticket` scope) while `pending_tracker_updates` remain in the Run Receipt.

## Ticket Dispositions

`scripts/commit.py disposition` is the Coordinator-owned CAS seam for closing one live Ticket claim after the semantic decision has been made under Target Project and Approved DAG rules. It records the decision and closes the live claim without inferring product meaning.

```bash
python3 <this-skill-root>/scripts/commit.py disposition \
  --receipt <off-delivery>/run-receipt.json \
  --decision <off-delivery>/ticket-disposition-decision.json \
  --promotion-evidence <off-delivery>/promotion/promotion-evidence.json \
  --expected-promotion-sha256 <promotion-evidence-sha256> \
  --expected-generation <current-coordinator-generation> \
  --expected-receipt-sha256 <current-receipt-sha256>
```

For a zero-diff Accepted Ticket, replace the Promotion arguments with:

```bash
  --baseline-evidence <off-delivery>/baseline-evidence.json \
  --expected-baseline-sha256 <baseline-evidence-sha256>
```

The decision (`schema_version: 1`, `kind: Ticket Disposition Decision`) names `run_id`, `coordinator_generation`, `ticket_id`, `claim_generation`, explicit `Accepted` or `Superseded` disposition, `rule_identity`, `decided_by`, `decided_at`, `rationale`, and digest-checked `evidence_refs`. A non-empty `Accepted` candidate requires a matching `Promotion Evidence Package` ([`integration-transitions.md`](integration-transitions.md#publish-the-promotion-evidence-package)). A zero-diff `Accepted` result requires a Base-bound `Baseline Satisfaction Evidence` package instead. `Superseded` carries neither package and still requires its own decision evidence.

The helper verifies the current Receipt generation and matching live claim, validates decision and package evidence, appends a `Ticket Disposition`, atomically updates `pending_tracker_updates` when the Receipt carries an `in_repo` or `external_snapshot` `Tracker Policy`, removes the live claim, and increments `coordinator_generation`. Repeating the identical disposition is idempotent.

## Tracker Checkpoints

Follow the fixed Ticket completion sequence:

`Accepted/Superseded → Tracker Policy → Tracker Checkpoint → review → Definition Checkpoint → readback → successor unlock`

Helpers never parse Markdown, checklists, or project-specific status words; the Coordinator interprets Target Project rules and authors tracker edits, while helpers verify schemas, paths, Git object/blob identities, SHA-256 digests, and Receipt CAS.

When `mode` is `in_repo` or `external_snapshot`, complete the owed update before unlocking successors or evaluating `Complete`:

1. Create an isolated Coordinator checkpoint commit (`candidate`) from the current Accepted Integration Tip (`base`), updating only `tracker_paths` (plus `.dag/definition-index.json` when `stateful_tracker_decision` covers a changed Definition path).
2. Run the read-only preflight verifier to check schema, `policy_key`, bound dispositions, path scope, exact `git diff-tree` `changed_paths`, and `before_blob_oid` / `after_blob_oid` identities before review:

   ```bash
   python3 <this-skill-root>/scripts/verify.py tracker-checkpoint \
     --repository <target-project-root> \
     --receipt <off-delivery>/run-receipt.json \
     --checkpoint <off-delivery>/tracker-checkpoint.json
   ```

3. Obtain fresh `$code-review` on `base...candidate`, promote the candidate through the serialized `DAG Definition Checkpoint` Integration Transition (`scripts/promote.py`), and verify local (and applicable remote) readback.
4. Commit the completed `Tracker Checkpoint` into the Run Receipt through CAS:

   ```bash
   python3 <this-skill-root>/scripts/commit.py tracker-checkpoint \
     --repository <target-project-root> \
     --receipt <off-delivery>/run-receipt.json \
     --checkpoint <off-delivery>/tracker-checkpoint.json \
     --expected-generation <current-coordinator-generation> \
     --expected-receipt-sha256 <current-receipt-sha256>
   ```

The `Tracker Checkpoint` (`schema_version: 1`, `kind: Tracker Checkpoint`) binds `run_id`, `coordinator_generation`, `policy_key`, `integration_ref`, `ticket_dispositions` (`{ticket_id, claim_generation, disposition}`), `base` (`{commit, tree}`), `candidate` (`{commit, tree}`), `changed_paths`, `blob_changes` (`{path, before_blob_oid, after_blob_oid}`), and `evidence_refs` (`{id, path, sha256}`).

`scripts/commit.py tracker-checkpoint` verifies exact Git ancestry, `integration_ref` readback equal to `candidate.commit`, exact `changed_paths` and `before`/`after` blob OIDs from `git diff-tree`, current `policy_key`, effective Receipt dispositions, `.dag/definition-index.json` validity when stateful Definition paths change, off-delivery file placement, and evidence digests. It then CAS-appends the checkpoint, advances `receipt.accepted_integration_tip` to `checkpoint.candidate`, clears covered `pending_tracker_updates`, and increments `coordinator_generation`. Repeating the identical submission is idempotent.

## Terminal Outcome Audit

`scripts/publish.py terminal-evidence` verifies a Coordinator-owned `Complete` or `Stalled` audit against the current Run Receipt and Accepted Integration Tip, publishing `Terminal Outcome Evidence`.

```bash
python3 <this-skill-root>/scripts/publish.py terminal-evidence \
  --receipt <off-delivery>/run-receipt.json \
  --audit <off-delivery>/terminal/terminal-audit.json \
  --expected-tip-commit <accepted-tip-commit> \
  --expected-tip-tree <accepted-tip-tree> \
  --output <off-delivery>/terminal/terminal-evidence.json
```

The audit (`schema_version: 1`, `kind: Terminal Outcome Audit`) identifies `run_id`, `outcome`, `definition_identity`, `accepted_tip`, every obligation (`id`, `owner`, optional `ticket_id`, `status`, and `evidence_applicable`), `whole_dag_gates`, digest-bound `authority_refs`, `pending_tracker_updates`, `unresolved_decisions`, `needs_decisions`, `runnable_tickets`, `running_agents`, `recovery_paths`, `satisfiable_external_conditions`, and `writer_liveness_resolved`.

`Complete` fails closed across both the audit and the Run Receipt:

- every obligation is `Accepted` or `Superseded` with `evidence_applicable: true`, and maps one-to-one with the Run Receipt's effective `ticket_dispositions` and matching statuses;
- all whole-DAG gates pass, no live claims or active `pending_transition` remain, and both `audit.pending_tracker_updates` and `receipt.pending_tracker_updates` are empty alongside all decision, runnable, agent, recovery, and external-condition arrays;
- the Run Receipt contains a valid `Tracker Policy`;
- when `Tracker Policy` mode is `in_repo` or `external_snapshot`, completed `Tracker Checkpoint` entries cover every effective Ticket disposition under the current `policy_key`, all evidence files verify on disk, and the latest `Tracker Checkpoint` `candidate` commit and tree equal the final Accepted Integration Tip.

`Stalled` requires resolved writer liveness, no `pending_tracker_updates` in either the audit or the Run Receipt, no decisions or executable progress paths, and at least one unfinished obligation. Legacy Run Receipts without `tracker_policy` remain readable for recovery and `Stalled` audits, and must be upgraded with `scripts/commit.py tracker-policy` (and `scripts/commit.py tracker-checkpoint` when `mode` is `in_repo` or `external_snapshot`) before `Complete`.
