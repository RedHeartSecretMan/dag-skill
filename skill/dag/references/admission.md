# Execution Admission

`plan_execution_admission.py` is a read-only Coordinator helper for the admission step. It evaluates live claims and candidate Tickets together, then emits a deterministic `Execution Admission Decision`. It does not create a claim, assign a writer, change a workspace, move a Git ref, or enter a Promotion transition.

## Command

```bash
python3 <this-skill-root>/scripts/plan_execution_admission.py \
  --request <off-delivery>/admission-request.json \
  --output <off-delivery>/admission-decision.json
```

The request has `schema_version: 1` and `kind: Execution Admission Request`, a `run_id`, `coordinator_generation`, known `agent_slots` and `runtime_skill_slots` capacity, `accepted_direct_inputs` (`name` + identity), `accepted_prerequisites` (`ticket_id` + output identity), current `live_claims`, and open `candidates`. Each claim declares its phase, changed paths, shared interfaces, and resource reservations. Candidates additionally declare non-negative `priority`, `age`, `required_inputs` (`name` + identity), and `hard_dependencies` (`ticket_id` + output identity).

The planner checks all live claims before admitting a candidate. It compares required input and dependency identities, then rejects missing or stale Accepted direct inputs, unmet or stale Hard Dependencies, overlapping changed paths or shared interfaces, exclusive resources already held, capacity overflow, duplicate Ticket identities, and unknown agent or Runtime Skill capacity. Unknown capacity produces `capacity_unknown` and selects no candidate that requires the unknown resource.

Build / Review work can be admitted concurrently when its paths and resources are independent. At most one live or newly selected `promotion` candidate enters the Promotion lane. Candidate ordering is deterministic: priority descending, age descending, then Ticket ID ascending. A lower-ranked Promotion candidate receives `promotion_lane_busy` after a higher-ranked one is selected.

## Decision output

The output contains the request digest, run and Coordinator generation, selected candidates with owner, phase, lane, rank, and `accepted`, and rejected candidates with an actionable reason. Reasons include `path_or_interface_conflict`, `resource_conflict`, `capacity_exceeded`, `capacity_unknown`, and `promotion_lane_busy`.

The decision is an admission proposal. The Coordinator rereads current live state before atomically recording a claim and its Ticket Base. A stale request or decision cannot authorize a writer; a changed frontier requires a new request and decision.
