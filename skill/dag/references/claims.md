# Execution Claims

`record_execution_claim.py` is the Coordinator's CAS boundary after a read-only admission decision. It records one live Ticket claim in the existing off-delivery Run Receipt; it does not start an Agent, create a worktree, or change a Git ref.

## Command

```bash
python3 <this-skill-root>/scripts/record_execution_claim.py \
  --receipt <off-delivery>/run-receipt.json \
  --request <off-delivery>/admission-request.json \
  --decision <off-delivery>/admission-decision.json \
  --claim <off-delivery>/execution-claim.json \
  --expected-generation <current-coordinator-generation> \
  --expected-receipt-sha256 <current-receipt-sha256>
```

The claim contains `ticket_id`, `owner_id`, `claim_generation`, workspace, branch, phase, exact `ticket_base` commit/tree, changed paths, shared interfaces, and resource reservations. The Coordinator supplies these values after preparing the safe workspace and current Base.

Before writing, the helper verifies:

- the Receipt digest and generation are current;
- the request, decision, claim, and Receipt share one `run_id`;
- the decision's request digest matches the exact request bytes;
- the decision accepted this Ticket and the owner and phase match;
- the claim's Ticket Base, workspace, branch, paths, and resources satisfy the claim schema;
- no different live claim already owns the Ticket.

When the Run Receipt contains a `Tracker Policy` ([`tracker-checkpoints.md`](tracker-checkpoints.md)), the helper also verifies that `changed_paths` and `shared_interfaces` do not overlap `tracker_paths`, rejects new claims while `pending_tracker_updates` remain under `per_ticket` scope, and rejects dependent claims whose prerequisites remain in `pending_tracker_updates` under `batched` scope.

The helper appends the claim and increments `coordinator_generation` through the existing Receipt CAS writer. Repeating the same claim with the updated Receipt generation is idempotent. The claim's paths, shared interfaces, and resource reservations must exactly match the admitted candidate, and its lane must match its phase. A stale decision, old generation, conflicting owner, or changed claim fails before Receipt mutation. The successful record still leaves Agent dispatch and writer liveness under the Coordinator workflow.
