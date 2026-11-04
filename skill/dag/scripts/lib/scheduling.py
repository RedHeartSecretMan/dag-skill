"""Admission planning, Execution Claim CAS, and writer-liveness recovery."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lib.artifacts import (
    validate_execution_record,
    validate_resource_reservations,
)
from lib.common import (
    ADMITTABLE_PHASES,
    PHASES,
    SCHEMA_VERSION,
    canonical_json,
    fail,
    parse_json,
    paths_overlap,
    publish_once,
    read_regular_file,
    require_exact_fields,
    require_identity,
    require_integer,
    require_object,
    require_sha256,
    require_string_array,
    require_text,
    sha256,
    sort_paths,
    validate_ticket_base,
)
from lib.receipt import (
    receipt_lock,
    replace_receipt,
    safe_receipt_target,
    validate_receipt,
)
from lib.tracker import validate_receipt_tracker_policy

REQUEST_KIND = "Execution Admission Request"
DECISION_KIND = "Execution Admission Decision"
CLAIM_KIND = "Execution Claim"
RESUME_CAPSULE_KIND = "Execution Resume Capsule"
WRITER_STATES = {"live", "stopped", "unknown"}

DECISION_FIELDS = {
    "schema_version",
    "kind",
    "run_id",
    "coordinator_generation",
    "request_path",
    "request_sha256",
    "selected",
    "rejected",
}
SELECTED_CORE_FIELDS = {
    "ticket_id",
    "owner_id",
    "phase",
    "lane",
    "rank",
    "admission_reason",
}
SELECTED_EMBEDDED_FIELDS = {
    "changed_paths",
    "shared_interfaces",
    "resources",
    "hard_dependencies",
}
CLAIM_FIELDS = {
    "schema_version",
    "kind",
    "ticket_id",
    "owner_id",
    "claim_generation",
    "workspace",
    "branch",
    "phase",
    "ticket_base",
    "changed_paths",
    "shared_interfaces",
    "resources",
}
CLAIM_ENTRY_FIELDS = CLAIM_FIELDS | {
    "lane",
    "request_sha256",
    "decision_sha256",
}


# --- Admission Planning ---


def _validate_input_refs(value: Any, label: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        fail(f"{label} must be an array")
    result = []
    names = set()
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        item = require_object(item, item_label)
        require_exact_fields(item, {"name", "identity"}, item_label)
        name = require_text(item["name"], f"{item_label}.name", safe_name=True)
        if name in names:
            fail(f"{item_label}.name is duplicated")
        names.add(name)
        result.append(
            {
                "name": name,
                "identity": require_identity(
                    item["identity"], f"{item_label}.identity"
                ),
            }
        )
    return result


def validate_dependency_refs(value: Any, label: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        fail(f"{label} must be an array")
    result = []
    ticket_ids = set()
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        item = require_object(item, item_label)
        require_exact_fields(item, {"ticket_id", "identity"}, item_label)
        ticket_id = require_identity(item["ticket_id"], f"{item_label}.ticket_id")
        if ticket_id in ticket_ids:
            fail(f"{item_label}.ticket_id is duplicated")
        ticket_ids.add(ticket_id)
        result.append(
            {
                "ticket_id": ticket_id,
                "identity": require_identity(
                    item["identity"], f"{item_label}.identity"
                ),
            }
        )
    return result


def _validate_admission_claim(
    value: Any, label: str, *, candidate: bool
) -> dict[str, Any]:
    value = require_object(value, label)
    expected = {
        "ticket_id",
        "owner_id",
        "phase",
        "changed_paths",
        "shared_interfaces",
        "resources",
    }
    if candidate:
        expected.update({"priority", "age", "required_inputs", "hard_dependencies"})
    require_exact_fields(value, expected, label)
    phase = require_text(value["phase"], f"{label}.phase", safe_name=True)
    if phase not in PHASES:
        fail(f"{label}.phase is unsupported")
    if candidate and phase not in ADMITTABLE_PHASES:
        fail(f"{label}.phase cannot enter the Runnable Frontier")
    return {
        "ticket_id": require_identity(value["ticket_id"], f"{label}.ticket_id"),
        "owner_id": require_identity(value["owner_id"], f"{label}.owner_id"),
        "phase": phase,
        "changed_paths": set(
            require_string_array(
                value["changed_paths"], f"{label}.changed_paths", paths=True
            )
        ),
        "shared_interfaces": set(
            require_string_array(
                value["shared_interfaces"], f"{label}.shared_interfaces", paths=True
            )
        ),
        "resources": validate_resource_reservations(
            value["resources"], f"{label}.resources"
        ),
        "required_inputs": _validate_input_refs(
            value["required_inputs"], f"{label}.required_inputs"
        )
        if candidate
        else [],
        "hard_dependencies": validate_dependency_refs(
            value["hard_dependencies"], f"{label}.hard_dependencies"
        )
        if candidate
        else [],
        "priority": require_integer(value["priority"], f"{label}.priority")
        if candidate
        else 0,
        "age": require_integer(value["age"], f"{label}.age") if candidate else 0,
    }


def validate_admission_request(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "request")
    expected = {
        "schema_version",
        "kind",
        "run_id",
        "coordinator_generation",
        "capacity",
        "accepted_direct_inputs",
        "accepted_prerequisites",
        "live_claims",
        "candidates",
    }
    require_exact_fields(payload, expected, "request")
    if payload["schema_version"] != SCHEMA_VERSION or payload["kind"] != REQUEST_KIND:
        fail("request schema_version or kind is unsupported")
    capacity = require_object(payload["capacity"], "request.capacity")
    require_exact_fields(
        capacity, {"agent_slots", "runtime_skill_slots"}, "request.capacity"
    )
    normalized_capacity = {}
    for name in ("agent_slots", "runtime_skill_slots"):
        value = capacity[name]
        if value is not None:
            value = require_integer(value, f"request.capacity.{name}")
        normalized_capacity[name] = value
    accepted_direct_inputs = _validate_input_refs(
        payload["accepted_direct_inputs"], "request.accepted_direct_inputs"
    )
    accepted_prerequisites = validate_dependency_refs(
        payload["accepted_prerequisites"], "request.accepted_prerequisites"
    )
    live_claims = payload["live_claims"]
    if not isinstance(live_claims, list):
        fail("request.live_claims must be an array")
    normalized_live = [
        _validate_admission_claim(
            item, f"request.live_claims[{index}]", candidate=False
        )
        for index, item in enumerate(live_claims)
    ]
    candidates = payload["candidates"]
    if not isinstance(candidates, list):
        fail("request.candidates must be an array")
    normalized_candidates = [
        _validate_admission_claim(item, f"request.candidates[{index}]", candidate=True)
        for index, item in enumerate(candidates)
    ]
    all_ids = [item["ticket_id"] for item in normalized_live + normalized_candidates]
    if len(all_ids) != len(set(all_ids)):
        fail("live_claims and candidates must not contain duplicate ticket_id values")
    promotion_claims = [
        item for item in normalized_live if item["phase"] == "promotion"
    ]
    if len(promotion_claims) > 1:
        fail("live_claims contains more than one Promotion lane owner")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": REQUEST_KIND,
        "run_id": require_identity(payload["run_id"], "request.run_id"),
        "coordinator_generation": require_integer(
            payload["coordinator_generation"], "request.coordinator_generation"
        ),
        "capacity": normalized_capacity,
        "accepted_direct_inputs": accepted_direct_inputs,
        "accepted_prerequisites": accepted_prerequisites,
        "live_claims": normalized_live,
        "candidates": normalized_candidates,
    }


def _resource_map(resources: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["resource"]: item for item in resources}


def _path_sets_overlap(left: set[str], right: set[str]) -> bool:
    return any(
        paths_overlap(candidate, existing) for candidate in left for existing in right
    )


def _conflict_reason(
    candidate: dict[str, Any],
    existing: list[dict[str, Any]],
    used_resources: dict[str, int],
) -> tuple[str, str | None]:
    candidate_paths = candidate["changed_paths"] | candidate["shared_interfaces"]
    candidate_resources = _resource_map(candidate["resources"])
    for item in existing:
        existing_paths = item["changed_paths"] | item["shared_interfaces"]
        if _path_sets_overlap(candidate_paths, existing_paths):
            return "path_or_interface_conflict", item["ticket_id"]
        for resource, claim in _resource_map(item["resources"]).items():
            if resource in {"agent_slots", "runtime_skill_slots"}:
                continue
            proposed = candidate_resources.get(resource)
            if proposed is None:
                continue
            if claim["mode"] == "exclusive" or proposed["mode"] == "exclusive":
                return "resource_conflict", item["ticket_id"]
    for resource, proposed in candidate_resources.items():
        if resource in {"agent_slots", "runtime_skill_slots"}:
            continue
        if proposed["mode"] == "exclusive" and used_resources.get(resource, 0) > 0:
            return "resource_conflict", None
    return "", None


def plan_admission(
    request: dict[str, Any], request_digest: str, request_path: Path
) -> dict[str, Any]:
    live = request["live_claims"]
    selected: list[dict[str, Any]] = []
    admitted_claims: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    occupied_resources: dict[str, int] = {}
    for claim in live:
        for resource in claim["resources"]:
            occupied_resources[resource["resource"]] = (
                occupied_resources.get(resource["resource"], 0) + resource["quantity"]
            )
    promotion_busy = any(claim["phase"] == "promotion" for claim in live)
    ordered = sorted(
        request["candidates"],
        key=lambda item: (-item["priority"], -item["age"], item["ticket_id"]),
    )
    for rank, candidate in enumerate(ordered, start=1):
        lane = "promotion" if candidate["phase"] == "promotion" else "build-review"
        accepted_input_identities = {
            item["name"]: item["identity"] for item in request["accepted_direct_inputs"]
        }
        missing_inputs = [
            item["name"]
            for item in candidate["required_inputs"]
            if accepted_input_identities.get(item["name"]) != item["identity"]
        ]
        if missing_inputs:
            rejected.append(
                {
                    "ticket_id": candidate["ticket_id"],
                    "admission_reason": "missing_accepted_input",
                    "missing_inputs": missing_inputs,
                }
            )
            continue
        accepted_dependency_identities = {
            item["ticket_id"]: item["identity"]
            for item in request["accepted_prerequisites"]
        }
        missing_dependencies = [
            item["ticket_id"]
            for item in candidate["hard_dependencies"]
            if accepted_dependency_identities.get(item["ticket_id"]) != item["identity"]
        ]
        if missing_dependencies:
            rejected.append(
                {
                    "ticket_id": candidate["ticket_id"],
                    "admission_reason": "hard_dependency_unmet",
                    "missing_dependencies": missing_dependencies,
                }
            )
            continue
        if (
            any(
                resource["resource"] == "agent_slots" and resource["quantity"] > 0
                for resource in candidate["resources"]
            )
            and request["capacity"]["agent_slots"] is None
        ):
            rejected.append(
                {
                    "ticket_id": candidate["ticket_id"],
                    "admission_reason": "capacity_unknown",
                }
            )
            continue
        if (
            any(
                resource["resource"] == "runtime_skill_slots"
                and resource["quantity"] > 0
                for resource in candidate["resources"]
            )
            and request["capacity"]["runtime_skill_slots"] is None
        ):
            rejected.append(
                {
                    "ticket_id": candidate["ticket_id"],
                    "admission_reason": "capacity_unknown",
                }
            )
            continue
        if lane == "promotion" and promotion_busy:
            rejected.append(
                {
                    "ticket_id": candidate["ticket_id"],
                    "admission_reason": "promotion_lane_busy",
                }
            )
            continue
        reason, conflicting_ticket = _conflict_reason(
            candidate, live + admitted_claims, occupied_resources
        )
        if reason:
            item: dict[str, Any] = {
                "ticket_id": candidate["ticket_id"],
                "admission_reason": reason,
            }
            if conflicting_ticket is not None:
                item["conflicting_ticket_id"] = conflicting_ticket
            rejected.append(item)
            continue
        proposed_resources = dict(occupied_resources)
        exceeds = None
        for resource in candidate["resources"]:
            name = resource["resource"]
            proposed_resources[name] = (
                proposed_resources.get(name, 0) + resource["quantity"]
            )
            capacity = request["capacity"].get(name)
            if (
                name in {"agent_slots", "runtime_skill_slots"}
                and capacity is not None
                and proposed_resources[name] > capacity
            ):
                exceeds = name
                break
        if exceeds is not None:
            rejected.append(
                {
                    "ticket_id": candidate["ticket_id"],
                    "admission_reason": "capacity_exceeded",
                    "resource": exceeds,
                }
            )
            continue
        selected.append(
            {
                "ticket_id": candidate["ticket_id"],
                "owner_id": candidate["owner_id"],
                "phase": candidate["phase"],
                "lane": lane,
                "rank": rank,
                "admission_reason": "accepted",
                "changed_paths": sort_paths(list(candidate["changed_paths"])),
                "shared_interfaces": sort_paths(list(candidate["shared_interfaces"])),
                "resources": candidate["resources"],
                "hard_dependencies": candidate["hard_dependencies"],
            }
        )
        admitted_claims.append(candidate)
        occupied_resources = proposed_resources
        if lane == "promotion":
            promotion_busy = True
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": DECISION_KIND,
        "run_id": request["run_id"],
        "coordinator_generation": request["coordinator_generation"],
        "request_path": str(request_path.resolve()),
        "request_sha256": request_digest,
        "selected": selected,
        "rejected": rejected,
    }


def publish_admission_decision(request_path: Path, output_path: Path) -> dict[str, Any]:
    request_bytes = read_regular_file(request_path, "request")
    request = validate_admission_request(parse_json(request_bytes, "request"))
    decision = plan_admission(request, sha256(request_bytes), request_path)
    status = publish_once(output_path, canonical_json(decision), [request_path])
    return {
        "status": status,
        "kind": DECISION_KIND,
        "selected_count": len(decision["selected"]),
        "rejected_count": len(decision["rejected"]),
    }


# --- Execution Claims ---


def validate_claim(payload: Any, label: str = "claim") -> dict[str, Any]:
    payload = require_object(payload, label)
    require_exact_fields(payload, CLAIM_FIELDS, label)
    phase = require_text(payload["phase"], f"{label}.phase", safe_name=True)
    if phase not in ADMITTABLE_PHASES:
        fail(f"{label}.phase cannot be claimed")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": CLAIM_KIND,
        "ticket_id": require_identity(payload["ticket_id"], f"{label}.ticket_id"),
        "owner_id": require_identity(payload["owner_id"], f"{label}.owner_id"),
        "claim_generation": require_integer(
            payload["claim_generation"], f"{label}.claim_generation"
        ),
        "workspace": require_text(payload["workspace"], f"{label}.workspace"),
        "branch": require_text(payload["branch"], f"{label}.branch"),
        "phase": phase,
        "ticket_base": validate_ticket_base(
            payload["ticket_base"], f"{label}.ticket_base"
        ),
        "changed_paths": require_string_array(
            payload["changed_paths"], f"{label}.changed_paths", paths=True
        ),
        "shared_interfaces": require_string_array(
            payload["shared_interfaces"], f"{label}.shared_interfaces", paths=True
        ),
        "resources": validate_resource_reservations(
            payload["resources"], f"{label}.resources"
        ),
    }


def validate_claim_entry(value: Any, label: str) -> dict[str, Any]:
    value = require_object(value, label)
    require_exact_fields(value, CLAIM_ENTRY_FIELDS, label)
    base = {
        field: value[field]
        for field in CLAIM_ENTRY_FIELDS
        if field not in {"lane", "request_sha256", "decision_sha256"}
    }
    claim = validate_claim(base, label)
    claim.update(
        {
            "lane": require_text(value["lane"], f"{label}.lane", safe_name=True),
            "request_sha256": require_text(
                value["request_sha256"], f"{label}.request_sha256", safe_name=True
            ),
            "decision_sha256": require_text(
                value["decision_sha256"], f"{label}.decision_sha256", safe_name=True
            ),
        }
    )
    return claim


def validate_admission_decision(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "decision")
    require_exact_fields(payload, DECISION_FIELDS, "decision")
    if payload["schema_version"] != 1 or payload["kind"] != DECISION_KIND:
        fail("decision schema_version or kind is unsupported")
    selected = payload["selected"]
    rejected = payload["rejected"]
    if not isinstance(selected, list) or not isinstance(rejected, list):
        fail("decision selected and rejected must be arrays")
    normalized_selected = []
    selected_ids = set()
    for index, item in enumerate(selected):
        label = f"decision.selected[{index}]"
        item = require_object(item, label)
        require_exact_fields(
            item,
            SELECTED_CORE_FIELDS | SELECTED_EMBEDDED_FIELDS,
            label,
        )
        ticket_id = require_identity(item["ticket_id"], f"{label}.ticket_id")
        if ticket_id in selected_ids:
            fail(f"{label}.ticket_id is duplicated")
        selected_ids.add(ticket_id)
        admission_reason = require_text(
            item["admission_reason"], f"{label}.admission_reason", safe_name=True
        )
        if admission_reason != "accepted":
            fail(f"{label}.admission_reason must be accepted")
        normalized_selected.append(
            {
                "ticket_id": ticket_id,
                "owner_id": require_identity(item["owner_id"], f"{label}.owner_id"),
                "phase": require_text(item["phase"], f"{label}.phase", safe_name=True),
                "lane": require_text(item["lane"], f"{label}.lane", safe_name=True),
                "rank": require_integer(item["rank"], f"{label}.rank", minimum=1),
                "admission_reason": admission_reason,
                "changed_paths": require_string_array(
                    item["changed_paths"], f"{label}.changed_paths", paths=True
                ),
                "shared_interfaces": require_string_array(
                    item["shared_interfaces"],
                    f"{label}.shared_interfaces",
                    paths=True,
                ),
                "resources": validate_resource_reservations(
                    item["resources"], f"{label}.resources"
                ),
                "hard_dependencies": validate_dependency_refs(
                    item["hard_dependencies"], f"{label}.hard_dependencies"
                ),
            }
        )
    return {
        "schema_version": 1,
        "kind": DECISION_KIND,
        "run_id": require_identity(payload["run_id"], "decision.run_id"),
        "coordinator_generation": require_integer(
            payload["coordinator_generation"], "decision.coordinator_generation"
        ),
        "request_path": require_text(payload["request_path"], "decision.request_path"),
        "request_sha256": require_sha256(
            payload["request_sha256"], "decision.request_sha256"
        ),
        "selected": normalized_selected,
        "rejected": rejected,
    }


def commit_execution_claim(
    *,
    receipt_path: Path,
    decision_path: Path,
    claim_path: Path,
    expected_generation: int,
    expected_receipt_digest: str,
) -> dict[str, Any]:
    expected_generation = require_integer(expected_generation, "expected_generation")
    expected_receipt_digest = require_sha256(
        expected_receipt_digest, "expected_receipt_sha256"
    )
    with receipt_lock(receipt_path):
        safe_receipt_target(receipt_path)
        receipt_bytes = read_regular_file(receipt_path, "receipt")
        if sha256(receipt_bytes) != expected_receipt_digest:
            fail("receipt SHA-256 does not match")
        receipt = validate_receipt(parse_json(receipt_bytes, "receipt"))
        if receipt["coordinator_generation"] != expected_generation:
            fail("receipt coordinator_generation does not match")

        decision_bytes = read_regular_file(decision_path, "decision")
        decision = validate_admission_decision(parse_json(decision_bytes, "decision"))
        request_path = Path(decision["request_path"])
        request_bytes = read_regular_file(request_path, "admission request")
        if sha256(request_bytes) != decision["request_sha256"]:
            fail("admission request SHA-256 does not match the decision")
        request = validate_admission_request(
            parse_json(request_bytes, "admission request")
        )
        claim = validate_claim(
            parse_json(read_regular_file(claim_path, "claim"), "claim")
        )
        decision_digest = sha256(decision_bytes)
        if decision["run_id"] != receipt["run_id"]:
            fail("receipt and decision run_id do not match")
        if request["run_id"] != receipt["run_id"]:
            fail("receipt and admission request run_id do not match")

        selected = next(
            (
                item
                for item in decision["selected"]
                if item["ticket_id"] == claim["ticket_id"]
            ),
            None,
        )
        if selected is None:
            fail("claim Ticket was not accepted by the admission decision")
        candidate = next(
            (
                item
                for item in request["candidates"]
                if item["ticket_id"] == claim["ticket_id"]
            ),
            None,
        )
        if candidate is None:
            fail("claim Ticket is absent from the admission request")
        if (
            selected["owner_id"] != candidate["owner_id"]
            or selected["phase"] != candidate["phase"]
        ):
            fail("admission decision does not match its source request")
        if set(selected["changed_paths"]) != set(candidate["changed_paths"]):
            fail("admission decision changed_paths do not match its source request")
        if set(selected["shared_interfaces"]) != set(candidate["shared_interfaces"]):
            fail("admission decision shared_interfaces do not match its source request")
        if sorted(
            (item["resource"], item["quantity"], item["mode"])
            for item in selected["resources"]
        ) != sorted(
            (item["resource"], item["quantity"], item["mode"])
            for item in candidate["resources"]
        ):
            fail("admission decision resources do not match its source request")
        if selected["hard_dependencies"] != candidate["hard_dependencies"]:
            fail("admission decision hard_dependencies do not match its source request")
        if (
            selected["owner_id"] != claim["owner_id"]
            or selected["phase"] != claim["phase"]
        ):
            fail("claim owner or phase does not match the admission decision")
        expected_lane = "promotion" if claim["phase"] == "promotion" else "build-review"
        if selected["lane"] != expected_lane:
            fail("admission decision lane does not match the claim phase")
        if set(selected["changed_paths"]) != set(claim["changed_paths"]):
            fail("claim changed_paths do not match the admission decision")
        if set(selected["shared_interfaces"]) != set(claim["shared_interfaces"]):
            fail("claim shared_interfaces do not match the admission decision")
        selected_resources = sorted(
            (item["resource"], item["quantity"], item["mode"])
            for item in selected["resources"]
        )
        claim_resources = sorted(
            (item["resource"], item["quantity"], item["mode"])
            for item in claim["resources"]
        )
        if selected_resources != claim_resources:
            fail("claim resources do not match the admission decision")

        entry = {
            **claim,
            "lane": selected["lane"],
            "request_sha256": decision["request_sha256"],
            "decision_sha256": decision_digest,
        }

        claims = receipt.setdefault("claims", [])
        for current in claims:
            current = require_object(current, "receipt.claims entry")
            require_exact_fields(current, CLAIM_ENTRY_FIELDS, "receipt.claims entry")
            if current["ticket_id"] != entry["ticket_id"]:
                continue
            if current == entry:
                return {
                    "status": "already-claimed",
                    "kind": CLAIM_KIND,
                    "ticket_id": entry["ticket_id"],
                    "claim_generation": entry["claim_generation"],
                    "coordinator_generation": expected_generation,
                    "receipt_sha256": expected_receipt_digest,
                }
            fail("receipt already contains a different live claim for this Ticket")

        if request["coordinator_generation"] != expected_generation:
            fail("admission request coordinator_generation does not match receipt")
        if decision["coordinator_generation"] != expected_generation:
            fail("decision coordinator_generation does not match receipt")
        policy = validate_receipt_tracker_policy(receipt)
        if policy is not None:
            reserved_paths = set(claim["changed_paths"]) | set(
                claim["shared_interfaces"]
            )
            if any(
                paths_overlap(reserved, tracker_path)
                for reserved in reserved_paths
                for tracker_path in policy["tracker_paths"]
            ):
                fail("Execution Agent claim cannot modify tracker_paths")
            pending = receipt.get("pending_tracker_updates", [])
            if pending:
                if policy["update_scope"] == "per_ticket":
                    fail(
                        "pending_tracker_updates must complete before another claim under per_ticket scope"
                    )
                pending_ids = {
                    item.get("ticket_id") for item in pending if isinstance(item, dict)
                }
                dependency_ids = {
                    item["ticket_id"] for item in selected["hard_dependencies"]
                }
                if claim["ticket_id"] in pending_ids or pending_ids & dependency_ids:
                    fail(
                        "claim cannot proceed while its Ticket or prerequisite pending_tracker_updates remain"
                    )
        claims.append(entry)
        receipt["coordinator_generation"] += 1
        new_bytes = canonical_json(receipt)
        replace_receipt(receipt_path, receipt_bytes, new_bytes, locked=True)
        return {
            "status": "claimed",
            "kind": CLAIM_KIND,
            "ticket_id": entry["ticket_id"],
            "claim_generation": entry["claim_generation"],
            "coordinator_generation": receipt["coordinator_generation"],
            "receipt_sha256": sha256(new_bytes),
        }


# --- Resume Capsule ---


def _make_liveness_evidence(path: Path) -> dict[str, str]:
    content = read_regular_file(path, "liveness evidence")
    return {"path": str(path.resolve()), "sha256": sha256(content)}


def publish_resume_capsule(
    *,
    receipt_path: Path,
    ticket_id: str,
    artifact_root: Path | None,
    writer_state: str,
    recheck_event: str | None,
    liveness_evidence_path: Path | None,
    output_path: Path,
) -> dict[str, Any]:
    ticket_id = require_identity(ticket_id, "ticket_id")
    receipt_bytes = read_regular_file(receipt_path, "receipt")
    receipt = validate_receipt(parse_json(receipt_bytes, "receipt"))
    claims = receipt.get("claims", [])
    matches = [
        validate_claim_entry(item, f"receipt.claims[{index}]")
        for index, item in enumerate(claims)
        if isinstance(item, dict) and item.get("ticket_id") == ticket_id
    ]
    if len(matches) != 1:
        fail("receipt must contain exactly one live claim for the Ticket")
    claim = matches[0]

    if writer_state not in WRITER_STATES:
        fail("writer_state is unsupported")
    if writer_state == "unknown":
        if not recheck_event:
            fail("unknown writer_state requires recheck_event")
        if liveness_evidence_path is not None:
            fail("unknown writer_state cannot claim liveness evidence")
        liveness_evidence = None
    else:
        if liveness_evidence_path is None:
            fail(f"{writer_state} writer_state requires liveness evidence")
        liveness_evidence = _make_liveness_evidence(liveness_evidence_path)
        if recheck_event is not None:
            fail(f"{writer_state} writer_state cannot set recheck_event")

    checkpoint_summary = None
    records = receipt.get("execution_records", [])
    matching_records = [
        item
        for item in records
        if isinstance(item, dict)
        and item.get("ticket_id") == ticket_id
        and item.get("claim_generation") == claim["claim_generation"]
    ]
    if len(matching_records) > 1:
        fail("receipt contains multiple execution records for the live claim")
    if matching_records:
        record_entry = matching_records[0]
        if artifact_root is None:
            fail("artifact_root is required when a Checkpoint Record is indexed")
        record_path = Path(require_text(record_entry["record_path"], "record_path"))
        record_bytes = read_regular_file(record_path, "execution record")
        if sha256(record_bytes) != record_entry["record_sha256"]:
            fail("execution record SHA-256 does not match Receipt")
        record, _digest, _capsule, checkpoint = validate_execution_record(
            record_path, artifact_root
        )
        if record["owner_id"] != claim["owner_id"]:
            fail("Checkpoint Record owner does not match live claim")
        checkpoint_summary = {
            "record_path": str(record_path.resolve()),
            "record_sha256": record_entry["record_sha256"],
            "checkpoint_sha256": record_entry["checkpoint_sha256"],
            "capsule_sha256": record_entry["capsule_sha256"],
            "phase": checkpoint["phase"],
            "next_action": checkpoint["next_action"],
            "candidate": checkpoint["candidate"],
            "evidence_ids": [
                item["evidence_id"] for item in checkpoint["evidence_delta"]
            ],
        }

    capsule = {
        "schema_version": SCHEMA_VERSION,
        "kind": RESUME_CAPSULE_KIND,
        "run_id": receipt["run_id"],
        "receipt_generation": receipt["coordinator_generation"],
        "ticket_id": claim["ticket_id"],
        "owner_id": claim["owner_id"],
        "claim_generation": claim["claim_generation"],
        "workspace": claim["workspace"],
        "branch": claim["branch"],
        "phase": claim["phase"],
        "ticket_base": claim["ticket_base"],
        "resources": claim["resources"],
        "writer_state": writer_state,
        "resume_allowed": writer_state == "stopped",
        "recheck_event": recheck_event,
        "liveness_evidence": liveness_evidence,
        "checkpoint": checkpoint_summary,
    }
    inputs = [receipt_path]
    if liveness_evidence_path is not None:
        inputs.append(liveness_evidence_path)
    status = publish_once(output_path, canonical_json(capsule), inputs)
    return {
        "status": status,
        "kind": RESUME_CAPSULE_KIND,
        "ticket_id": capsule["ticket_id"],
        "writer_state": capsule["writer_state"],
        "resume_allowed": capsule["resume_allowed"],
    }
