# Execution Records

`record_execution_checkpoint.py` publishes one validated, off-delivery shadow record for a claimed Ticket. `index_execution_record.py` revalidates that record and CAS-indexes it into the existing off-delivery Run Receipt. Together they provide the first P0/P1 data seam for context, evidence, phase, resource, and wait measurements. They do not change a Git ref, mutate a claim, decide acceptance, or replace the Run Receipt.

## Ownership and publication

The Execution Agent prepares a `Ticket Capsule` and an `Execution Checkpoint` in its assigned workspace. The Coordinator Agent is the only owner that may treat the resulting shadow record as current run state. The helper validates the two inputs and publishes a compact `Execution Checkpoint Record` to an output path chosen by the Coordinator.

The output is an advisory artifact until the Coordinator verifies its owner, claim generation, Ticket Base, source identities, evidence, and current Run Receipt generation. A missing, stale, conflicting, or unverifiable record is an observability or recovery gap. It never authorizes a replacement writer and never grants acceptance.

Publication is create-once and content-addressed by the input identities. Existing output is accepted only when its bytes are identical; a different existing file, symlink, hardlink, output collision, unsafe parent, or changed evidence causes a failure. The helper writes a temporary file, flushes and syncs it, links it into place without overwriting an existing output, and syncs the parent directory.

## Command

```bash
python3 <this-skill-root>/scripts/record_execution_checkpoint.py \
  --capsule <off-delivery-or-workspace>/ticket-capsule.json \
  --checkpoint <off-delivery-or-workspace>/execution-checkpoint.json \
  --artifact-root <off-delivery-or-workspace>/artifacts \
  --output <off-delivery-or-workspace>/shadow/execution-record.json
```

The helper requires Python 3.12+, regular non-symlink input files, an existing non-symlink artifact root, and repository-relative evidence paths. Evidence files must exist and match their declared SHA-256 digest. The command emits one compact JSON result on success and an `error:` diagnostic without a traceback on failure.

After publishing the record, the Coordinator indexes it with a receipt CAS:

```bash
python3 <this-skill-root>/scripts/index_execution_record.py \
  --receipt <off-delivery>/run-receipt.json \
  --record <off-delivery-or-workspace>/shadow/execution-record.json \
  --artifact-root <off-delivery-or-workspace>/artifacts \
  --expected-generation <current-coordinator-generation> \
  --expected-receipt-sha256 <current-receipt-sha256>
```

The indexer requires a regular non-symlink Run Receipt and verifies its current digest and generation before writing. It rereads the record, Capsule, Checkpoint, and evidence artifacts; a stale generation, changed receipt, changed referenced artifact, conflicting record for the same Ticket claim, symlink, or hardlink fails before the Receipt is changed. A byte-identical record for the same Ticket and claim generation is idempotent and does not advance the Coordinator generation.

## Ticket Capsule

The Capsule is an immutable dispatch input. Its `schema_version` and `kind` are `1` and `Ticket Capsule`. It contains:

- `run_id`, `ticket_id`, `owner_id`, `claim_generation`, and `workspace`;
- `ticket_base` with the exact commit and tree identities;
- `definition_identity`;
- `authorities`, each with a name, normalized relative source path, and content identity;
- `scope` as normalized relative paths;
- non-empty `acceptance_obligations`, each with an ID, source path, and content identity;
- `required_gates`, `permissions`, and `finalization_policy` (`serial` or `deferred`).

The helper allows small normalized fields to reduce dispatch context, but source paths and identities remain mandatory. A copied obligation without its source identity is invalid.

## Execution Checkpoint

The Checkpoint is an immutable observation from one owner and claim generation. Its `schema_version` and `kind` are `1` and `Execution Checkpoint`. It contains:

```text
run_id, ticket_id, owner_id, claim_generation, workspace
phase: explore | implement | verify | review | promotion | blocked
observed_at: ISO-8601 timestamp with timezone
ticket_base: {commit, tree}
changed_paths[], accepted_inputs[]
candidate: null or {commit, tree, range}
evidence_delta[], open_findings[], resource_claims[]
next_action, blocking_condition
measurement_version, context_budget, metrics[]
```

`changed_paths` must be inside the Capsule scope. A candidate is forbidden in an `explore` or `implement` Checkpoint because candidate identity is created by the later execution stages. `blocking_condition`, when present, names its kind, owner, and concrete `recheck_event`; it does not silently convert an unresolved condition into an external block.

Each metric uses a fixed name, numeric finite value, unit, and string tags. Version `1` recognizes `dispatch.input_bytes`, `handoff.input_bytes`, `tool.output_bytes`, `tool.retained_bytes`, `phase.duration_ms`, `resource.agent_slots`, `resource.runtime_skill_slots`, `wait.duration_ms`, `rework.count`, and `wall_clock_ms`. Unsupported names are rejected so measurements remain comparable.

`context_budget` contains `dispatch_bytes`, `retained_bytes`, `handoff_bytes`, `measurement_kind` (`bytes`, `characters`, or `tokens`), and `estimated`. It is an observation and warning budget; it cannot remove mandatory obligations, authority, identity, unknown-operation, finding, or closing-condition fields from a dispatch.

## Evidence Index entries

`evidence_delta` is a list of Evidence Index entries. Each entry binds an evidence ID to its type, producer, operation, artifact path, artifact SHA-256, observed result (`pass`, `fail`, `unknown`, or `not-run`), optional commit and tree identities, environment identity, applicability, and optional invalidation reason.

The entry records an observed result. It cannot produce `Accepted`, `Superseded`, or gate applicability by itself. The Coordinator must load the original artifact and reread Git identities before using it for review, promotion, or acceptance.

## Record output

The published `Execution Checkpoint Record` contains only the compact recovery index:

```text
run_id, ticket_id, owner_id, claim_generation, phase
checkpoint_ref: {path, sha256}
capsule_ref: {path, sha256}
ticket_base, candidate, evidence_ids
measurement_version, metrics, observed_at
capsule_definition_identity
```

The full Capsule, Checkpoint, and evidence artifacts remain at their referenced paths. The record is useful for shadow recovery and measurement; it is not a second Run Receipt and it cannot be used without revalidating the referenced artifacts.

## Run Receipt index

The Run Receipt keeps its existing fields and adds an optional `execution_records` array. The array entries contain the Ticket identity, owner, claim generation, phase, record path and digest, Checkpoint digest, Capsule digest, and observation timestamp. The Receipt also carries a non-negative `coordinator_generation`. The Coordinator supplies the generation and exact Receipt SHA-256 for every index attempt; a successful append increments the generation atomically.

The index is a recovery and measurement pointer. It does not copy the Checkpoint, evidence body, Acceptance Obligation, review result, or semantic Ticket state. Current acceptance still comes from the existing Coordinator-owned graph and the original evidence authorities.
