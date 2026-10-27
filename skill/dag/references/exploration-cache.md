# Exploration Cache

`record_exploration_note.py` publishes and consumes identity-bound advisory notes for repeated exploration. It reduces repeated investigation while keeping the Ticket, Definition, dependency, authority, and acceptance sources authoritative.

## Publish a note

```bash
python3 <this-skill-root>/scripts/record_exploration_note.py \
  --note <workspace>/exploration-note.json \
  --output <off-delivery>/exploration-cache/note.json
```

The input has `schema_version: 1` and `kind: Exploration Note`, with `note_id`, `question`, normalized relative `scope`, non-empty `source_identities`, `target_identity`, `environment_identity`, `author`, timezone-bearing `created_at`, `invalidation_conditions`, non-empty `conclusions`, `limitations`, and `unresolved`. Each conclusion carries evidence paths and identities. The helper computes `cache_key` from the question, scope, source identities, target identity, and environment identity; a supplied key must match.

Publication is create-once and atomic. An existing output is accepted only when its bytes are identical. A source path, output parent, symlink, hardlink, or JSON schema failure stops publication.

## Consume a note

```bash
python3 <this-skill-root>/scripts/record_exploration_note.py \
  --note <off-delivery>/exploration-cache/note.json \
  --context <workspace>/exploration-context.json \
  --output <off-delivery>/exploration-cache/consumption.json
```

The context has `schema_version: 1` and `kind: Exploration Context`, with the current question, scope, source identities, target identity, environment identity, and a timezone-bearing `observed_at`. Consumption requires the note question to match, the current scope to cover the note scope, every note source identity to match, and target and environment identities to match. A mismatch is cache miss and returns an error; the caller rereads authoritative sources.

The resulting `Exploration Consumption Record` contains the note path and SHA-256, cache key, question, current scope, observation time, verified source identities, target identity, and environment identity. It records consumption for recovery and measurement only. It grants no product, dependency, permission, or acceptance authority.

`valid_until` is intentionally absent from the schema. Freshness follows source, target, and environment identities. A time reminder may be kept in the note's invalidation conditions, but it cannot override identity mismatch or prove identity stability.
