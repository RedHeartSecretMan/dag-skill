# Promotion Evidence Package

`verify_promotion_package.py` performs the mechanical preflight immediately before a Promotion Candidate enters the serialized Integration Transition. It binds the current Run Receipt claim, current Accepted Integration Tip, Review Context Capsule, Candidate Review Record, and review Artifact Handle.

## Command

```bash
python3 <this-skill-root>/scripts/verify_promotion_package.py \
  --receipt <off-delivery>/run-receipt.json \
  --ticket-id <ticket-id> \
  --context-capsule <off-delivery>/review/review-context-capsule.json \
  --review-record <off-delivery>/review/candidate-review-record.json \
  --review-handle <off-delivery>/handles/review.json \
  --artifact-root <off-delivery-or-workspace> \
  --expected-tip-commit <accepted-tip-commit> \
  --expected-tip-tree <accepted-tip-tree> \
  --output <off-delivery>/promotion/promotion-evidence.json
```

The verifier requires exactly one live claim for the Ticket. It checks the claim owner, generation, Base, context Capsule, candidate identities, fresh review flag, review context key, review record key, and current review artifact digest. The claim Base must equal the expected current Accepted Integration Tip.

On success it publishes a `Promotion Evidence Package` with `promotion_allowed: true`. This is a mechanical gate only. It does not decide semantic acceptance, classify review findings, move a Git ref, publish remotely, or close the claim. The Coordinator still runs the existing final gate, frozen evidence, CAS, publication, and acceptance sequence.

The existing `promote_local_transition.py` can consume the package during its frozen preflight and immediately before CAS:

```bash
python3 <this-skill-root>/scripts/promote_local_transition.py \
  --repository <target-worktree> \
  --transition <off-delivery>/pending-transition.json \
  --sha256 <pending-transition-sha256> \
  --promotion-evidence <off-delivery>/promotion/promotion-evidence.json \
  --promotion-evidence-sha256 <promotion-evidence-sha256> \
  --promotion-receipt <off-delivery>/run-receipt.json \
  --promotion-receipt-sha256 <current-receipt-sha256>
```

When supplied, a changed package, Receipt generation/digest mismatch, missing live claim, or Base/candidate mismatch stops the local ref update before CAS. Promotion evidence requires the current Receipt path and digest. The helper remains mechanical; Ticket acceptance and disposition follow the existing Coordinator sequence.
