# Terminal Outcome Audit

`verify_terminal_outcome.py` verifies a Coordinator-owned `Complete` or `Stalled` audit against the current Run Receipt and Accepted Integration Tip. It produces mechanical evidence only; it does not infer product meaning or change the Receipt.

## Command

```bash
python3 <this-skill-root>/scripts/verify_terminal_outcome.py \
  --receipt <off-delivery>/run-receipt.json \
  --audit <off-delivery>/terminal/terminal-audit.json \
  --expected-tip-commit <accepted-tip-commit> \
  --expected-tip-tree <accepted-tip-tree> \
  --output <off-delivery>/terminal/terminal-evidence.json
```

The audit identifies the run, outcome, final Definition identity, Accepted Integration Tip, every obligation owner/status/applicability, whole-DAG gate results, digest-bound authoritative snapshot references, pending tracker updates, unresolved decisions, `Needs Decision` outcomes, Runnable Tickets, running Agents, recovery paths, satisfiable external conditions, and writer-liveness resolution. Every authority reference is reread and SHA-256 checked before the audit is accepted.

`Complete` requires every obligation to be `Accepted` or `Superseded` with applicable evidence, all whole-DAG gates to pass, no live claims, no pending tracker updates, decisions, runnable work, running Agents, recovery paths, or satisfiable external conditions. `Stalled` requires resolved writer liveness, no decisions or executable progress paths, and at least one unfinished obligation. The helper preserves the distinction between product outcome and resource disposition.
