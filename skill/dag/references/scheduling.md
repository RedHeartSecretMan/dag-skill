# Plan Admission, Record Claims, and Recover Writers

Read this reference before evaluating candidate Tickets on the Runnable Frontier, recording a live `Execution Claim`, or reconciling writer liveness during recovery.

## Plan deterministic admission

`scripts/publish.py admission-decision` is a read-only Coordinator planner for the admission step. It evaluates live claims and candidate Tickets together, then atomically publishes a deterministic `Execution Admission Decision`. It does not create a claim, assign a writer, change a workspace, move a Git ref, or enter a Promotion transition.

```bash
python3 <this-skill-root>/scripts/publish.py admission-decision \
  --request <off-delivery>/admission-request.json \
  --output <off-delivery>/admission-decision.json
```

The request has `schema_version: 1` and `kind: Execution Admission Request`, a `run_id`, `coordinator_generation`, known `agent_slots` and `runtime_skill_slots` capacity, `accepted_direct_inputs` (`name` + identity), `accepted_prerequisites` (`ticket_id` + output identity), current `live_claims`, and open `candidates`. Each claim declares its phase, changed paths, shared interfaces, and resource reservations. Candidates additionally declare non-negative `priority`, `age`, `required_inputs` (`name` + identity), and `hard_dependencies` (`ticket_id` + output identity).

The planner checks all live claims before admitting a candidate. It compares required input and dependency identities, then rejects missing or stale Accepted direct inputs, unmet or stale Hard Dependencies, overlapping changed paths or shared interfaces (including parent/child path overlap), exclusive resources already held, capacity overflow, duplicate Ticket identities, and unknown agent or Runtime Skill capacity. Resource quantities must be positive. Unknown capacity produces `capacity_unknown` and selects no candidate that requires the unknown resource.

Build / Review work can be admitted concurrently when its paths and resources are independent. At most one live or newly selected `promotion` candidate enters the Promotion lane. Candidate ordering is deterministic: priority descending, age descending, then Ticket ID ascending. A lower-ranked Promotion candidate receives `promotion_lane_busy` after a higher-ranked one is selected.

The output contains a digest-bound `request_path` and `request_sha256`, `run_id`, `coordinator_generation`, `selected` candidates with owner, phase, lane, rank, `admission_reason: accepted`, and embedded `changed_paths`, `shared_interfaces`, `resources`, and `hard_dependencies`, plus `rejected` candidates with actionable reasons (`missing_accepted_input`, `hard_dependency_unmet`, `path_or_interface_conflict`, `resource_conflict`, `capacity_exceeded`, `capacity_unknown`, or `promotion_lane_busy`). `commit.py claim` rereads the embedded request path and rechecks its digest and selected candidate fields, so the caller does not need to pass `--request` again.

The decision is an admission proposal. The Coordinator rereads current live state before atomically recording a claim and its Ticket Base. A stale decision cannot authorize a writer; a changed frontier requires a new request and decision.

## Commit an Execution Claim

`scripts/commit.py claim` is the Coordinator's locked CAS boundary after admission planning. It records one live Ticket claim in the off-delivery Run Receipt; it does not start an Agent, create a worktree, or change a Git ref.

```bash
python3 <this-skill-root>/scripts/commit.py claim \
  --receipt <off-delivery>/run-receipt.json \
  --decision <off-delivery>/admission-decision.json \
  --claim <off-delivery>/execution-claim.json \
  --expected-generation <current-coordinator-generation> \
  --expected-receipt-sha256 <current-receipt-sha256>
```

The claim contains `ticket_id`, `owner_id`, `claim_generation`, workspace, branch, phase, exact `ticket_base` commit/tree, changed paths, shared interfaces, and resource reservations. The Coordinator supplies these values after preparing the safe workspace and current Base.

Before writing, the helper verifies:

- the Receipt digest and `coordinator_generation` are current;
- the decision, claim, and Receipt share one `run_id` and `coordinator_generation`;
- the decision accepted this Ticket and the owner, phase, lane, `changed_paths`, `shared_interfaces`, and `resources` match the embedded candidate record;
- the claim's Ticket Base, workspace, branch, paths, and resources satisfy the claim schema;
- no different live claim already owns the Ticket.

When the Run Receipt contains a `Tracker Policy` ([`completion.md`](completion.md#tracker-policy)), the helper also verifies that `changed_paths` and `shared_interfaces` do not overlap `tracker_paths`, rejects new claims while `pending_tracker_updates` remain under `per_ticket` scope, and rejects dependent claims whose prerequisites remain in `pending_tracker_updates` under `batched` scope.

The helper appends the claim and increments `coordinator_generation` through the locked Receipt CAS writer, returning the new `coordinator_generation` and `receipt_sha256`. Repeating the same claim with the updated Receipt generation is idempotent. A stale decision, old generation, conflicting owner, or changed claim fails before Receipt mutation.

## Reconcile writer liveness and publish a Resume Capsule

`scripts/publish.py resume-capsule` consumes one current live claim and publishes an off-delivery `Execution Resume Capsule`. It does not terminate an Agent, replace a writer, mutate the Run Receipt, or dispatch work.

```bash
python3 <this-skill-root>/scripts/publish.py resume-capsule \
  --receipt <off-delivery>/run-receipt.json \
  --ticket-id <ticket-id> \
  --writer-state stopped \
  --liveness-evidence <off-delivery>/stop-evidence.txt \
  --artifact-root <off-delivery-or-workspace>/artifacts \
  --output <off-delivery>/resume/resume-capsule.json
```

The helper validates the single live claim, its owner, workspace, branch, phase, Base, and reservations. If the Receipt contains an indexed `Execution Checkpoint Record` ([`execution-artifacts.md`](execution-artifacts.md#execution-checkpoint-records)) for the same claim generation, it rereads the record, Capsule, Checkpoint, and evidence artifacts before adding a compact checkpoint summary.

`--writer-state` has three meanings:

- `live`: require liveness evidence, preserve the current owner, and report `resume_allowed: false`.
- `stopped`: require a regular stop-evidence file and report `resume_allowed: true`.
- `unknown`: require a named `--recheck-event`, preserve the claim, and report `resume_allowed: false`.

Silence, timeout, resource disappearance, or an absent liveness proof never becomes `stopped`. The output is a resume input for the Coordinator workflow; a replacement Agent still receives the original Ticket, branch, workspace, WIP, Base, and evidence only after the writer boundary is established.
