# Review Context Capsule

`record_review_context.py` publishes a compact, candidate-bound input for `$code-review`. It reduces reviewer rediscovery while preserving the required fresh review contract. It carries review inputs and artifact references; it never carries a review verdict.

## Command

```bash
python3 <this-skill-root>/scripts/record_review_context.py \
  --context <workspace>/review-context.json \
  --output <off-delivery>/review/review-context-capsule.json
```

The input has `schema_version: 1` and `kind: Review Context`, with:

- run, Ticket, owner, and claim generation identities;
- exact Ticket Base commit/tree;
- candidate commit/tree, range, and ordered commit list ending at the candidate commit;
- DAG Definition identity and changed paths;
- non-empty Acceptance Obligation references and required gate identities;
- digest-checked evidence and Exploration Cache consumption references.

The helper computes a `review_context_key` from all candidate, Base, Definition, path, obligation, gate, evidence, and exploration identities. The output always contains `fresh_review_required: true`. A new candidate, Base, changed path, obligation, gate, or referenced evidence produces a different key and requires a new Candidate Review Record.

The capsule does not accept `review_result`, `approved`, `findings`, or another verdict field. Existing review records remain provenance and are not reused as current approval. Review still receives the fixed Base, candidate range and commit list required by the execution protocol.

The helper rereads every referenced artifact and checks its digest before publishing. A changed or unavailable artifact stops capsule creation; the caller must refresh evidence or return to the Ticket execution loop.
