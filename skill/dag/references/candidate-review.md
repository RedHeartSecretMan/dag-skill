# Candidate Review Record

`record_candidate_review.py` binds one complete `$code-review` Artifact Handle to one validated, fresh Review Context Capsule. It provides the evidence identity used by the Coordinator at the handoff and Promotion boundary. It does not parse the review body or decide whether the candidate is approved.

## Command

```bash
python3 <this-skill-root>/scripts/record_candidate_review.py \
  --context-capsule <off-delivery>/review/review-context-capsule.json \
  --review-handle <off-delivery>/handles/review.json \
  --artifact-root <off-delivery-or-workspace> \
  --output <off-delivery>/review/candidate-review-record.json
```

The helper rereads and validates the Capsule, requiring `fresh_review_required: true` and a context key that matches all Base, candidate, Definition, path, obligation, gate, evidence, and exploration identities. It then verifies the review handle and requires `review-report` or `tool-output` as its artifact kind.

The output binds the Ticket, owner, claim generation, Base, candidate, Definition, obligations, gate and reference identities to the complete review handle. It carries `review_context_key`, `review_artifact`, `fresh_review_required: true`, and a `review_record_key` derived from the context key and review execution identity.

The record contains no `approved`, `findings`, or verdict field. The complete review artifact remains the authority for review findings and dispositions. A changed candidate, context identity, review artifact, command, environment, or observation produces a new record key; the old record remains provenance and cannot authorize Promotion for the new candidate.

## Verify before handoff or Promotion

```bash
python3 <this-skill-root>/scripts/verify_candidate_review.py \
  --record <off-delivery>/review/candidate-review-record.json \
  --context-capsule <off-delivery>/review/review-context-capsule.json \
  --review-handle <off-delivery>/handles/review.json \
  --artifact-root <off-delivery-or-workspace> \
  --expected-base-commit <current-base-commit> \
  --expected-base-tree <current-base-tree> \
  --expected-candidate-commit <candidate-commit> \
  --expected-candidate-tree <candidate-tree> \
  --expected-candidate-range <candidate-range>
```

The verifier rereads all three artifacts and checks the current identities. It returns a mechanical `verified` result only; semantic acceptance and review finding disposition remain Coordinator and `$code-review` responsibilities.
