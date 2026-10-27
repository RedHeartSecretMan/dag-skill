# Artifact Handles

`record_tool_artifact.py` turns an existing tool output into a compact, content-addressed `Artifact Handle`. The handle carries the artifact path, SHA-256, byte count, command, working directory, exit code, duration, observation time, environment identity, and optional Git commit/tree identities. It keeps large output out of dispatch and handoff context while preserving a verifiable source.

## Publish

```bash
python3 <this-skill-root>/scripts/record_tool_artifact.py \
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

The artifact must be a regular non-symlink file inside the explicit `artifact-root`. Publication is create-once and atomic; an existing output is accepted only when its bytes are identical. The handle stores no output body and does not change the artifact.

## Verify

```bash
python3 <this-skill-root>/scripts/record_tool_artifact.py \
  --verify <off-delivery-or-workspace>/handles/stdout.json \
  --artifact-root <off-delivery-or-workspace>
```

Verification rereads the handle and the referenced artifact, then checks the authorized root, regular-file boundary, byte count, and SHA-256. Any mismatch returns an error and the artifact is unavailable for review, promotion, or acceptance. The handle's metadata describes an observed tool result; it does not turn an exit code into a gate decision.

The handle is a C3 runtime artifact pointer. A Ticket Capsule, Checkpoint, or Run Receipt may reference it by path and digest, while the Coordinator remains responsible for loading the body when a decision requires it.
