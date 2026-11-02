# Ticket Dispositions

`record_ticket_disposition.py` is the Coordinator-owned CAS seam for closing one live Ticket claim after the semantic decision has already been made under the Target Project and Approved DAG rules. It records the decision and closes the live claim; it does not infer product meaning.

## Command

```bash
python3 <this-skill-root>/scripts/record_ticket_disposition.py \
  --receipt <off-delivery>/run-receipt.json \
  --decision <off-delivery>/ticket-disposition-decision.json \
  --promotion-evidence <off-delivery>/promotion/promotion-evidence.json \
  --promotion-evidence-sha256 <promotion-evidence-sha256> \
  --expected-generation <current-coordinator-generation> \
  --expected-receipt-sha256 <current-receipt-sha256>
```

For a zero-diff Accepted Ticket, replace the Promotion arguments with:

```bash
  --baseline-evidence <off-delivery>/baseline-evidence.json \
  --baseline-evidence-sha256 <baseline-evidence-sha256>
```

The decision has `schema_version: 1` and `kind: Ticket Disposition Decision`, and names the run, Ticket, claim generation, explicit `Accepted` or `Superseded` disposition, rule identity, Coordinator identity, timestamp, rationale, and digest-checked decision evidence. A non-empty `Accepted` candidate requires a matching `Promotion Evidence Package`. A zero-diff `Accepted` result requires a Base-bound `Baseline Satisfaction Evidence` package instead. `Superseded` carries neither package and still requires its own decision evidence.

The baseline package has `schema_version: 1` and `kind: Baseline Satisfaction Evidence`, and binds the run, Ticket, owner, claim generation, exact Ticket Base, disposition, and the same digest-checked evidence references as the decision. It permits `Accepted` without moving the Accepted Integration Tip or creating a Promotion Candidate.

The helper checks the current Receipt generation and exactly one matching live claim, validates decision evidence, validates the required Promotion or baseline package, appends a `Ticket Disposition`, removes the live claim, and increments the Receipt generation through CAS. Repeating the identical disposition is idempotent; a different decision for the same claim fails.

The disposition is an explicit Coordinator record. It does not derive `Accepted` from tests, review output, a Promotion package, or an exit code. Semantic meaning, obligation coverage, tracker updates, successor unlocking, and Terminal Outcome evaluation remain governed by the existing Skill protocol.
