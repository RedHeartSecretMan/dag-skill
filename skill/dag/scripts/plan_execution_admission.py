#!/usr/bin/env python3
"""Plan a deterministic, read-only admission set for independent Tickets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from record_execution_checkpoint import (
    PHASES,
    RESOURCE_MODES,
    RecordError,
    canonical_json,
    parse_json,
    publish_once,
    read_regular_file,
    require_exact_fields,
    require_identity,
    require_integer,
    require_string_array,
    require_text,
    sha256,
)

SCHEMA_VERSION = 1
REQUEST_KIND = "Execution Admission Request"
DECISION_KIND = "Execution Admission Decision"
ADMITTABLE_PHASES = {"explore", "implement", "verify", "review", "promotion"}
LANE_NAMES = {"build-review", "promotion"}


def fail(message: str) -> None:
    raise RecordError(message)


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value


def validate_resources(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        fail(f"{label} must be an array")
    result = []
    names = set()
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        item = require_object(item, item_label)
        require_exact_fields(item, {"resource", "quantity", "mode"}, item_label)
        resource = require_text(
            item["resource"], f"{item_label}.resource", safe_name=True
        )
        if resource in names:
            fail(f"{item_label}.resource is duplicated")
        names.add(resource)
        mode = require_text(item["mode"], f"{item_label}.mode", safe_name=True)
        if mode not in RESOURCE_MODES:
            fail(f"{item_label}.mode is unsupported")
        result.append(
            {
                "resource": resource,
                "quantity": require_integer(item["quantity"], f"{item_label}.quantity"),
                "mode": mode,
            }
        )
    return result


def validate_input_refs(value: Any, label: str) -> list[dict[str, str]]:
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


def validate_claim(value: Any, label: str, *, candidate: bool) -> dict[str, Any]:
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
        "resources": validate_resources(value["resources"], f"{label}.resources"),
        "required_inputs": validate_input_refs(
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


def validate_request(payload: Any) -> dict[str, Any]:
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
    accepted_direct_inputs = validate_input_refs(
        payload["accepted_direct_inputs"], "request.accepted_direct_inputs"
    )
    accepted_prerequisites = validate_dependency_refs(
        payload["accepted_prerequisites"], "request.accepted_prerequisites"
    )
    live_claims = payload["live_claims"]
    if not isinstance(live_claims, list):
        fail("request.live_claims must be an array")
    normalized_live = [
        validate_claim(item, f"request.live_claims[{index}]", candidate=False)
        for index, item in enumerate(live_claims)
    ]
    candidates = payload["candidates"]
    if not isinstance(candidates, list):
        fail("request.candidates must be an array")
    normalized_candidates = [
        validate_claim(item, f"request.candidates[{index}]", candidate=True)
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


def resource_map(resources: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["resource"]: item for item in resources}


def conflict_reason(
    candidate: dict[str, Any],
    existing: list[dict[str, Any]],
    used_resources: dict[str, int],
) -> tuple[str, str | None]:
    candidate_paths = candidate["changed_paths"] | candidate["shared_interfaces"]
    candidate_resources = resource_map(candidate["resources"])
    for item in existing:
        existing_paths = item["changed_paths"] | item["shared_interfaces"]
        if candidate_paths & existing_paths:
            return "path_or_interface_conflict", item["ticket_id"]
        for resource, claim in resource_map(item["resources"]).items():
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


def plan_admission(request: dict[str, Any], request_digest: str) -> dict[str, Any]:
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
        reason, conflicting_ticket = conflict_reason(
            candidate, live + admitted_claims, occupied_resources
        )
        if reason:
            item = {
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
            if name in {"agent_slots", "runtime_skill_slots"} and capacity is not None:
                if proposed_resources[name] > capacity:
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
        "request_sha256": request_digest,
        "selected": selected,
        "rejected": rejected,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Plan a deterministic, read-only admission set for independent Tickets."
    )
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        request_bytes = read_regular_file(arguments.request, "request")
        request = validate_request(parse_json(request_bytes, "request"))
        decision = plan_admission(request, sha256(request_bytes))
        status = publish_once(
            arguments.output, canonical_json(decision), [arguments.request]
        )
    except (OSError, RecordError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": status,
                "kind": DECISION_KIND,
                "selected_count": len(decision["selected"]),
                "rejected_count": len(decision["rejected"]),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
