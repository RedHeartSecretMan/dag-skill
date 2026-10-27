#!/usr/bin/env python3
"""CAS-record one Coordinator-owned claim after admission planning."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from index_execution_record import (
    IndexError as ReceiptIndexError,
)
from index_execution_record import (
    receipt_lock,
    replace_receipt,
    safe_receipt_target,
    validate_receipt,
)
from plan_execution_admission import (
    ADMITTABLE_PHASES,
    validate_request,
    validate_resources,
)
from record_execution_checkpoint import (
    RecordError,
    canonical_json,
    parse_json,
    read_regular_file,
    require_exact_fields,
    require_identity,
    require_integer,
    require_sha256,
    require_string_array,
    require_text,
    sha256,
)
from record_execution_checkpoint import (
    validate_ticket_base as require_ticket_base,
)

CLAIM_SCHEMA_VERSION = 1
CLAIM_KIND = "Execution Claim"
DECISION_KIND = "Execution Admission Decision"
DECISION_FIELDS = {
    "schema_version",
    "kind",
    "run_id",
    "coordinator_generation",
    "request_sha256",
    "selected",
    "rejected",
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


def fail(message: str) -> None:
    raise RecordError(message)


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value


def validate_claim(payload: Any, label: str = "claim") -> dict[str, Any]:
    payload = require_object(payload, label)
    require_exact_fields(payload, CLAIM_FIELDS, label)
    phase = require_text(payload["phase"], f"{label}.phase", safe_name=True)
    if phase not in ADMITTABLE_PHASES:
        fail(f"{label}.phase cannot be claimed")
    return {
        "schema_version": CLAIM_SCHEMA_VERSION,
        "kind": CLAIM_KIND,
        "ticket_id": require_identity(payload["ticket_id"], f"{label}.ticket_id"),
        "owner_id": require_identity(payload["owner_id"], f"{label}.owner_id"),
        "claim_generation": require_integer(
            payload["claim_generation"], f"{label}.claim_generation"
        ),
        "workspace": require_text(payload["workspace"], f"{label}.workspace"),
        "branch": require_text(payload["branch"], f"{label}.branch"),
        "phase": phase,
        "ticket_base": require_ticket_base(
            payload["ticket_base"], f"{label}.ticket_base"
        ),
        "changed_paths": require_string_array(
            payload["changed_paths"], f"{label}.changed_paths", paths=True
        ),
        "shared_interfaces": require_string_array(
            payload["shared_interfaces"], f"{label}.shared_interfaces", paths=True
        ),
        "resources": validate_resources(payload["resources"], f"{label}.resources"),
    }


def validate_decision(payload: Any) -> dict[str, Any]:
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
            {"ticket_id", "owner_id", "phase", "lane", "rank", "admission_reason"},
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
            }
        )
    return {
        "schema_version": 1,
        "kind": DECISION_KIND,
        "run_id": require_identity(payload["run_id"], "decision.run_id"),
        "coordinator_generation": require_integer(
            payload["coordinator_generation"], "decision.coordinator_generation"
        ),
        "request_sha256": require_sha256(
            payload["request_sha256"], "decision.request_sha256"
        ),
        "selected": normalized_selected,
        "rejected": rejected,
    }


def make_claim_entry(
    claim: dict[str, Any],
    decision: dict[str, Any],
    request_digest: str,
    decision_digest: str,
) -> dict[str, Any]:
    selected = next(
        item for item in decision["selected"] if item["ticket_id"] == claim["ticket_id"]
    )
    if selected["owner_id"] != claim["owner_id"] or selected["phase"] != claim["phase"]:
        fail("claim owner or phase does not match the admission decision")
    return {
        **claim,
        "lane": selected["lane"],
        "request_sha256": request_digest,
        "decision_sha256": decision_digest,
    }


def _record_claim_locked(
    receipt_path: Path,
    request_path: Path,
    decision_path: Path,
    claim_path: Path,
    expected_generation: int,
    expected_receipt_digest: str,
) -> tuple[str, dict[str, Any]]:
    safe_receipt_target(receipt_path)
    receipt_bytes = read_regular_file(receipt_path, "receipt")
    if sha256(receipt_bytes) != expected_receipt_digest:
        fail("receipt SHA-256 does not match")
    receipt = validate_receipt(parse_json(receipt_bytes, "receipt"))
    if receipt["coordinator_generation"] != expected_generation:
        fail("receipt coordinator_generation does not match")

    request_bytes = read_regular_file(request_path, "request")
    request = validate_request(parse_json(request_bytes, "request"))
    decision_bytes = read_regular_file(decision_path, "decision")
    decision = validate_decision(parse_json(decision_bytes, "decision"))
    claim = validate_claim(parse_json(read_regular_file(claim_path, "claim"), "claim"))
    request_digest = sha256(request_bytes)
    decision_digest = sha256(decision_bytes)
    if (
        request["run_id"] != receipt["run_id"]
        or decision["run_id"] != receipt["run_id"]
    ):
        fail("receipt, request, and decision run_id do not match")
    if decision["request_sha256"] != request_digest:
        fail("decision was not produced from this request")
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
        candidate["owner_id"] != claim["owner_id"]
        or candidate["phase"] != claim["phase"]
    ):
        fail("claim owner or phase does not match the admission request")
    selected_ids = {item["ticket_id"] for item in decision["selected"]}
    if claim["ticket_id"] not in selected_ids:
        fail("claim Ticket was not accepted by the admission decision")
    entry = make_claim_entry(claim, decision, request_digest, decision_digest)

    claims = receipt.setdefault("claims", [])
    if not isinstance(claims, list):
        fail("receipt.claims must be an array")
    for current in claims:
        current = require_object(current, "receipt.claims entry")
        require_exact_fields(current, CLAIM_ENTRY_FIELDS, "receipt.claims entry")
        if current["ticket_id"] != entry["ticket_id"]:
            continue
        if current == entry:
            return "already-claimed", entry
        fail("receipt already contains a different live claim for this Ticket")
    if request["coordinator_generation"] != expected_generation:
        fail("request coordinator_generation does not match receipt")
    if decision["coordinator_generation"] != expected_generation:
        fail("decision coordinator_generation does not match receipt")
    claims.append(entry)
    receipt["coordinator_generation"] += 1
    replace_receipt(receipt_path, receipt_bytes, canonical_json(receipt), locked=True)
    return "claimed", entry


def record_claim(
    receipt_path: Path,
    request_path: Path,
    decision_path: Path,
    claim_path: Path,
    expected_generation: int,
    expected_receipt_digest: str,
) -> tuple[str, dict[str, Any]]:
    with receipt_lock(receipt_path):
        return _record_claim_locked(
            receipt_path,
            request_path,
            decision_path,
            claim_path,
            expected_generation,
            expected_receipt_digest,
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CAS-record one Coordinator-owned claim after admission planning."
    )
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--decision", required=True, type=Path)
    parser.add_argument("--claim", required=True, type=Path)
    parser.add_argument("--expected-generation", required=True, type=int)
    parser.add_argument("--expected-receipt-sha256", required=True)
    arguments = parser.parse_args()
    try:
        status, entry = record_claim(
            arguments.receipt,
            arguments.request,
            arguments.decision,
            arguments.claim,
            arguments.expected_generation,
            arguments.expected_receipt_sha256,
        )
    except (OSError, ReceiptIndexError, RecordError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": status,
                "kind": CLAIM_KIND,
                "ticket_id": entry["ticket_id"],
                "claim_generation": entry["claim_generation"],
                "coordinator_generation": arguments.expected_generation
                if status == "already-claimed"
                else arguments.expected_generation + 1,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
