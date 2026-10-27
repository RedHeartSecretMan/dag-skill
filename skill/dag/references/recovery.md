# Claim Recovery and Resume

`reconcile_execution_claim.py` consumes one current live claim and produces an off-delivery `Execution Resume Capsule`. It does not terminate an Agent, replace a writer, mutate the Run Receipt, or dispatch work.

## Command

```bash
python3 <this-skill-root>/scripts/reconcile_execution_claim.py \
  --receipt <off-delivery>/run-receipt.json \
  --ticket-id <ticket-id> \
  --writer-state stopped \
  --liveness-evidence <off-delivery>/stop-evidence.txt \
  --artifact-root <off-delivery-or-workspace>/artifacts \
  --output <off-delivery>/resume/resume-capsule.json
```

The helper validates the single claim, its owner, workspace, branch, phase, Base and reservations. If the Receipt contains an Execution Checkpoint Record for the same claim generation, it rereads the record, Capsule, Checkpoint and evidence artifacts before adding a compact checkpoint summary.

`writer-state` has three meanings:

- `live`: preserve the current owner and report `resume_allowed: false`.
- `stopped`: require a regular liveness evidence file and report `resume_allowed: true`.
- `unknown`: require a named `recheck_event`, preserve the claim, and report `resume_allowed: false`.

Silence, timeout, resource disappearance, or an absent liveness proof never becomes `stopped`. The output is a resume input for the existing Coordinator workflow; a replacement Agent still receives the original Ticket, branch, workspace, WIP, Base and evidence only after the writer boundary is established.
