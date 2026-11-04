# Publish, Verify, and Index Execution Artifacts

Read this reference before creating or verifying an `Artifact Handle`, `Exploration Note`, `Execution Checkpoint Record`, `Review Context Capsule`, or `Candidate Review Record`. These helpers keep large tool output and intermediate state outside Agent prompts while preserving exact content digests and Git identities.

## Artifact Handles

`scripts/publish.py artifact` turns an existing tool output into a compact, content-addressed `Artifact Handle`. The handle carries the artifact path, SHA-256, byte count, command, working directory, exit code, duration, observation time, environment identity, and optional Git commit/tree identities.

```bash
python3 <this-skill-root>/scripts/publish.py artifact \
  --artifact <off-delivery-or-workspace>/stdout.txt \
  --artifact-root <off-delivery-or-workspace> \
  --output <off-delivery-or-workspace>/handles/stdout.json \
  --artifact-kind stdout \
  --command '<command identity>' \
  --cwd <working-directory> \
  --exit-code <integer> \
  --duration-ms <integer> \
  --observed-at <ISO-8601 timestamp with timezone> \
  --environment-identity <environment identity>
```

The artifact must be a regular non-symlink file inside `--artifact-root`. Publication is create-once and atomic; an existing output is accepted only when its bytes are identical. Output parent hierarchies must not contain symlinks.

Verify an existing handle with:

```bash
python3 <this-skill-root>/scripts/verify.py artifact \
  --handle <off-delivery-or-workspace>/handles/stdout.json \
  --artifact-root <off-delivery-or-workspace>
```

Verification rereads the handle and referenced artifact, checking the authorized root, regular-file boundary, byte count, and SHA-256. Any mismatch returns an `error:` diagnostic and makes the artifact unavailable for review, promotion, or acceptance. Metadata describes an observed tool result; it never turns an exit code into a gate decision.

## Exploration Cache

`scripts/publish.py exploration-note` and `scripts/publish.py exploration-consumption` publish and consume identity-bound advisory notes for repeated exploration while keeping Ticket, Definition, dependency, authority, and acceptance sources authoritative.

```bash
python3 <this-skill-root>/scripts/publish.py exploration-note \
  --note <workspace>/exploration-note.json \
  --output <off-delivery>/exploration-cache/note.json
```

The input has `schema_version: 1` and `kind: Exploration Note`, with `note_id`, `question`, normalized relative `scope`, non-empty `source_identities`, `target_identity`, `environment_identity`, `author`, timezone-bearing `created_at`, `invalidation_conditions`, non-empty `conclusions` (each with `id`, `statement`, and `evidence`), `limitations`, and `unresolved`. The helper computes `cache_key` from the question, scope, source identities, target identity, and environment identity.

Consume a published note only when current context identities match:

```bash
python3 <this-skill-root>/scripts/publish.py exploration-consumption \
  --note <off-delivery>/exploration-cache/note.json \
  --context <workspace>/exploration-context.json \
  --output <off-delivery>/exploration-cache/consumption.json
```

The context (`kind: Exploration Context`) supplies the current question, scope, source identities, target identity, environment identity, and `observed_at`. Consumption requires the question to match, the current scope to cover the note scope, and every source, target, and environment identity to match. A mismatch is a cache miss and returns the caller to authoritative inputs. `valid_until` is absent by design; freshness follows source, target, and environment identities.

## Execution Checkpoint Records

`scripts/publish.py execution-record` validates a `Ticket Capsule` and `Execution Checkpoint` and publishes one compact off-delivery `Execution Checkpoint Record`. `scripts/commit.py execution-record` revalidates that record and CAS-indexes it into the Run Receipt. They do not change a Git ref, mutate a claim, or decide acceptance.

```bash
python3 <this-skill-root>/scripts/publish.py execution-record \
  --capsule <off-delivery-or-workspace>/ticket-capsule.json \
  --checkpoint <off-delivery-or-workspace>/execution-checkpoint.json \
  --artifact-root <off-delivery-or-workspace>/artifacts \
  --output <off-delivery-or-workspace>/shadow/execution-record.json
```

The `Ticket Capsule` (`schema_version: 1`, `kind: Ticket Capsule`) binds `run_id`, `ticket_id`, `owner_id`, `claim_generation`, `workspace`, `ticket_base`, `definition_identity`, `authorities` (`{name, path, identity}`), `scope`, `acceptance_obligations` (`{id, source, identity}`), `required_gates`, `permissions`, and `finalization_policy` (`serial` or `deferred`).

The `Execution Checkpoint` (`schema_version: 1`, `kind: Execution Checkpoint`) binds the same ownership and `ticket_base`, plus `phase` (`explore`, `implement`, `verify`, `review`, `promotion`, or `blocked`), `observed_at`, `changed_paths` (inside `capsule.scope`), `accepted_inputs`, optional `candidate` (`{commit, tree, range}`, forbidden during `explore` or `implement`), `evidence_delta` (Evidence Index entries verified against `--artifact-root`), `open_findings`, `resource_claims`, `next_action`, `blocking_condition`, `measurement_version: 1`, `context_budget`, and `metrics`.

After publication, the Coordinator indexes the shadow record into the Run Receipt through CAS:

```bash
python3 <this-skill-root>/scripts/commit.py execution-record \
  --receipt <off-delivery>/run-receipt.json \
  --record <off-delivery-or-workspace>/shadow/execution-record.json \
  --artifact-root <off-delivery-or-workspace>/artifacts \
  --expected-generation <current-coordinator-generation> \
  --expected-receipt-sha256 <current-receipt-sha256>
```

A byte-identical record for the same Ticket and claim generation is idempotent; a conflicting record for the same claim fails before Receipt mutation.

## Review Context Capsule and Candidate Review Record

`scripts/publish.py review-context` publishes a compact, candidate-bound `Review Context Capsule` for `$code-review`. It carries review inputs and digest-verified artifact references without a review verdict.

```bash
python3 <this-skill-root>/scripts/publish.py review-context \
  --context <workspace>/review-context.json \
  --output <off-delivery>/review/review-context-capsule.json
```

The input (`kind: Review Context`) binds `run_id`, `ticket_id`, `owner_id`, `claim_generation`, `ticket_base`, `candidate` (`{commit, tree, range, commits}` distinct from Base), `definition_identity`, `changed_paths`, `acceptance_obligations`, `required_gates`, `evidence_refs`, and `exploration_refs`. The helper verifies all referenced files, computes `review_context_key`, and sets `fresh_review_required: true`.

After `$code-review` completes, `scripts/publish.py candidate-review` binds the complete review `Artifact Handle` (`review-report` or `tool-output`) to the fresh `Review Context Capsule`:

```bash
python3 <this-skill-root>/scripts/publish.py candidate-review \
  --context-capsule <off-delivery>/review/review-context-capsule.json \
  --review-handle <off-delivery>/handles/review.json \
  --artifact-root <off-delivery-or-workspace> \
  --output <off-delivery>/review/candidate-review-record.json
```

The published `Candidate Review Record` embeds `review_artifact` and `review_record_key` without any `approved`, `findings`, or verdict field. Before handoff or Promotion, verify the record against the current Base and candidate identities:

```bash
python3 <this-skill-root>/scripts/verify.py candidate-review \
  --record <off-delivery>/review/candidate-review-record.json \
  --context-capsule <off-delivery>/review/review-context-capsule.json \
  --artifact-root <off-delivery-or-workspace> \
  --expected-base-commit <current-base-commit> \
  --expected-base-tree <current-base-tree> \
  --expected-candidate-commit <candidate-commit> \
  --expected-candidate-tree <candidate-tree> \
  --expected-candidate-range <candidate-range>
```

The verifier rereads the record, capsule, and embedded `review_artifact` file on disk. It returns a mechanical `verified` result; semantic acceptance and finding disposition remain Coordinator and `$code-review` responsibilities.
