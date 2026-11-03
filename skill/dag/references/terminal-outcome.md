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

The audit identifies the run, outcome, final Definition identity, Accepted Integration Tip, every obligation (`id`, `owner`, optional `ticket_id` when `owner` names the Agent rather than the Ticket, `status`, and `evidence_applicable`), whole-DAG gate results, digest-bound authoritative snapshot references, pending tracker updates, unresolved decisions, `Needs Decision` outcomes, Runnable Tickets, running Agents, recovery paths, satisfiable external conditions, and writer-liveness resolution. Every authority reference, disposition evidence file, `Tracker Policy Record`, and `Tracker Checkpoint Record` is reread and SHA-256 checked before the audit is accepted.

`Complete` fails closed across both the audit and the Run Receipt:

- every obligation is `Accepted` or `Superseded` with `evidence_applicable: true`, and maps one-to-one with the Run Receipt's effective `ticket_dispositions` and matching statuses;
- all whole-DAG gates pass, no live claims remain, and both `audit.pending_tracker_updates` and `receipt.pending_tracker_updates` are empty alongside all decision, runnable, agent, recovery, and external-condition arrays;
- the Run Receipt contains a valid `Tracker Policy` ([`tracker-checkpoints.md`](tracker-checkpoints.md)) whose record file is intact on disk;
- when `Tracker Policy` mode is `in_repo` or `external_snapshot`, completed `Tracker Checkpoint` records cover every effective Ticket disposition under the current `policy_key`, all checkpoint and evidence artifacts verify on disk, and the latest `Tracker Checkpoint` `candidate` commit and tree equal the final Accepted Integration Tip.

`Stalled` requires resolved writer liveness, no `pending_tracker_updates` in either the audit or the Run Receipt, no decisions or executable progress paths, and at least one unfinished obligation. Legacy Run Receipts without `tracker_policy` remain readable for recovery and `Stalled` audits, and must be upgraded with `record_tracker_policy.py` (and `record_tracker_checkpoint.py` when `mode` is `in_repo` or `external_snapshot`) before `Complete`. The helper preserves the distinction between product outcome and resource disposition.
