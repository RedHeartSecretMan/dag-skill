#!/usr/bin/env python3
"""Verify a Coordinator-owned Complete or Stalled terminal audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from index_execution_record import validate_receipt
from record_execution_checkpoint import (
    RecordError,
    canonical_json,
    parse_json,
    publish_once,
    read_regular_file,
    require_exact_fields,
    require_identity,
    require_oid,
    require_string_array,
    require_text,
    sha256,
    validate_ticket_base,
)
from record_tracker_checkpoint import validate_receipt_tracker_checkpoints
from record_tracker_policy import (
    compute_pending_tracker_updates,
    effective_ticket_dispositions,
    validate_receipt_tracker_policy,
)

SCHEMA_VERSION = 1
AUDIT_KIND = "Terminal Outcome Audit"
EVIDENCE_KIND = "Terminal Outcome Evidence"
OUTCOMES = {"Complete", "Stalled"}
OBLIGATION_STATUSES = {"Accepted", "Superseded", "Open", "Blocked"}
GATE_RESULTS = {"pass", "fail", "unknown", "not-run"}


def fail(message: str) -> None:
    raise RecordError(message)


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value


def validate_obligations(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        fail("audit.obligations must be a non-empty array")
    result = []
    ids = set()
    for index, item in enumerate(value):
        label = f"audit.obligations[{index}]"
        item = require_object(item, label)
        actual_fields = set(item)
        required_fields = {"id", "owner", "status", "evidence_applicable"}
        optional_fields = {"ticket_id"}
        if not required_fields.issubset(actual_fields) or (
            actual_fields - (required_fields | optional_fields)
        ):
            require_exact_fields(item, required_fields, label)
        obligation_id = require_identity(item["id"], f"{label}.id")
        if obligation_id in ids:
            fail(f"{label}.id is duplicated")
        ids.add(obligation_id)
        status = require_text(item["status"], f"{label}.status", safe_name=True)
        if status not in OBLIGATION_STATUSES:
            fail(f"{label}.status is unsupported")
        if type(item["evidence_applicable"]) is not bool:
            fail(f"{label}.evidence_applicable must be boolean")
        entry: dict[str, Any] = {
            "id": obligation_id,
            "owner": require_identity(item["owner"], f"{label}.owner"),
            "status": status,
            "evidence_applicable": item["evidence_applicable"],
        }
        if "ticket_id" in item and item["ticket_id"] is not None:
            entry["ticket_id"] = require_identity(
                item["ticket_id"], f"{label}.ticket_id"
            )
        result.append(entry)
    return result


def validate_gates(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        fail("audit.whole_dag_gates must be an array")
    result = []
    ids = set()
    for index, item in enumerate(value):
        label = f"audit.whole_dag_gates[{index}]"
        item = require_object(item, label)
        require_exact_fields(item, {"id", "result", "evidence_identity"}, label)
        gate_id = require_identity(item["id"], f"{label}.id")
        if gate_id in ids:
            fail(f"{label}.id is duplicated")
        ids.add(gate_id)
        result_value = require_text(item["result"], f"{label}.result", safe_name=True)
        if result_value not in GATE_RESULTS:
            fail(f"{label}.result is unsupported")
        result.append(
            {
                "id": gate_id,
                "result": result_value,
                "evidence_identity": require_identity(
                    item["evidence_identity"], f"{label}.evidence_identity"
                ),
            }
        )
    return result


def validate_authority_refs(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        fail("audit.authority_refs must be a non-empty array")
    result = []
    ids = set()
    for index, item in enumerate(value):
        label = f"audit.authority_refs[{index}]"
        item = require_object(item, label)
        require_exact_fields(item, {"id", "path", "sha256"}, label)
        ref_id = require_identity(item["id"], f"{label}.id")
        if ref_id in ids:
            fail(f"{label}.id is duplicated")
        ids.add(ref_id)
        path = Path(require_text(item["path"], f"{label}.path"))
        declared = require_text(item["sha256"], f"{label}.sha256", safe_name=True)
        if len(declared) != 64 or any(
            character not in "0123456789abcdef" for character in declared
        ):
            fail(f"{label}.sha256 must be 64 lowercase hexadecimal characters")
        content = read_regular_file(path, f"{label}.path")
        if sha256(content) != declared:
            fail(f"{label}.path SHA-256 does not match")
        result.append({"id": ref_id, "path": str(path.resolve()), "sha256": declared})
    return result


def validate_audit(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "audit")
    expected = {
        "schema_version",
        "kind",
        "run_id",
        "outcome",
        "definition_identity",
        "accepted_tip",
        "authority_refs",
        "obligations",
        "whole_dag_gates",
        "pending_tracker_updates",
        "unresolved_decisions",
        "needs_decisions",
        "runnable_tickets",
        "running_agents",
        "recovery_paths",
        "satisfiable_external_conditions",
        "writer_liveness_resolved",
    }
    require_exact_fields(payload, expected, "audit")
    if payload["schema_version"] != SCHEMA_VERSION or payload["kind"] != AUDIT_KIND:
        fail("audit schema_version or kind is unsupported")
    outcome = require_text(payload["outcome"], "audit.outcome", safe_name=True)
    if outcome not in OUTCOMES:
        fail("audit.outcome is unsupported")
    if type(payload["writer_liveness_resolved"]) is not bool:
        fail("audit.writer_liveness_resolved must be boolean")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": AUDIT_KIND,
        "run_id": require_identity(payload["run_id"], "audit.run_id"),
        "outcome": outcome,
        "definition_identity": require_identity(
            payload["definition_identity"], "audit.definition_identity"
        ),
        "accepted_tip": validate_ticket_base(
            payload["accepted_tip"], "audit.accepted_tip"
        ),
        "authority_refs": validate_authority_refs(payload["authority_refs"]),
        "obligations": validate_obligations(payload["obligations"]),
        "whole_dag_gates": validate_gates(payload["whole_dag_gates"]),
        "pending_tracker_updates": require_string_array(
            payload["pending_tracker_updates"], "audit.pending_tracker_updates"
        ),
        "unresolved_decisions": require_string_array(
            payload["unresolved_decisions"], "audit.unresolved_decisions"
        ),
        "needs_decisions": require_string_array(
            payload["needs_decisions"], "audit.needs_decisions"
        ),
        "runnable_tickets": require_string_array(
            payload["runnable_tickets"], "audit.runnable_tickets"
        ),
        "running_agents": require_string_array(
            payload["running_agents"], "audit.running_agents"
        ),
        "recovery_paths": require_string_array(
            payload["recovery_paths"], "audit.recovery_paths"
        ),
        "satisfiable_external_conditions": require_string_array(
            payload["satisfiable_external_conditions"],
            "audit.satisfiable_external_conditions",
        ),
        "writer_liveness_resolved": payload["writer_liveness_resolved"],
    }


def verify_dispositions_match_obligations(
    effective: dict[str, dict[str, Any]],
    obligations: list[dict[str, Any]],
    *,
    complete: bool,
) -> None:
    mapped_tickets: set[str] = set()
    for obligation in obligations:
        ticket_id = str(obligation.get("ticket_id") or obligation["owner"])
        if ticket_id in mapped_tickets:
            fail("terminal obligations must map one-to-one with Ticket dispositions")
        mapped_tickets.add(ticket_id)
        status = obligation["status"]
        if status in {"Accepted", "Superseded"} or complete:
            recorded = effective.get(ticket_id)
            if recorded is None:
                fail(
                    f"obligation {obligation['id']} ({ticket_id}) has no recorded Ticket disposition in receipt"
                )
            if recorded["disposition"] != status:
                fail(
                    f"obligation {obligation['id']} status {status} does not match recorded Ticket disposition {recorded['disposition']}"
                )
            if (
                "ticket_id" in obligation
                and recorded.get("claim_owner_id") is not None
                and obligation["owner"] not in {recorded["claim_owner_id"], ticket_id}
            ):
                fail(
                    f"obligation {obligation['id']} owner does not match recorded Ticket disposition owner"
                )
    missing = sorted(set(effective) - mapped_tickets)
    if missing:
        fail(
            f"recorded Ticket dispositions missing from terminal obligations: {', '.join(missing)}"
        )


def verify_audit(
    receipt_path: Path,
    audit_path: Path,
    expected_tip_commit: str,
    expected_tip_tree: str,
) -> dict[str, Any]:
    receipt = validate_receipt(
        parse_json(read_regular_file(receipt_path, "receipt"), "receipt")
    )
    audit = validate_audit(parse_json(read_regular_file(audit_path, "audit"), "audit"))
    if receipt["run_id"] != audit["run_id"]:
        fail("receipt and audit run_id do not match")
    if audit["accepted_tip"]["commit"] != expected_tip_commit:
        fail("audit accepted tip commit does not match current tip")
    if audit["accepted_tip"]["tree"] != expected_tip_tree:
        fail("audit accepted tip tree does not match current tip")
    receipt_tip = receipt.get("accepted_integration_tip")
    if receipt_tip is not None:
        receipt_tip = validate_ticket_base(
            receipt_tip, "receipt.accepted_integration_tip"
        )
        if receipt_tip != audit["accepted_tip"]:
            fail(
                "receipt.accepted_integration_tip does not match terminal accepted tip"
            )
    claims = receipt.get("claims", [])
    if not isinstance(claims, list):
        fail("receipt.claims must be an array")
    if claims:
        fail("live claims remain at terminal outcome")
    if not audit["writer_liveness_resolved"]:
        fail("writer liveness is unresolved")
    receipt_pending = receipt.get("pending_tracker_updates", [])
    if not isinstance(receipt_pending, list):
        fail("receipt.pending_tracker_updates must be an array")
    if audit["outcome"] == "Complete":
        if any(
            obligation["status"] not in {"Accepted", "Superseded"}
            or not obligation["evidence_applicable"]
            for obligation in audit["obligations"]
        ):
            fail(
                "Complete requires all obligations to be closed with applicable evidence"
            )
        if any(gate["result"] != "pass" for gate in audit["whole_dag_gates"]):
            fail("Complete requires every whole-DAG gate to pass")
        for field in (
            "pending_tracker_updates",
            "unresolved_decisions",
            "needs_decisions",
            "runnable_tickets",
            "running_agents",
            "recovery_paths",
            "satisfiable_external_conditions",
        ):
            if audit[field]:
                fail(f"Complete cannot have {field}")
        if receipt_pending:
            fail("Complete cannot have pending_tracker_updates in receipt")
        policy = validate_receipt_tracker_policy(receipt, reread_record=True)
        if policy is None:
            fail("Complete requires a recorded Tracker Policy in receipt")
        effective = effective_ticket_dispositions(receipt, verify_evidence=True)
        verify_dispositions_match_obligations(
            effective, audit["obligations"], complete=True
        )
        checkpoints = validate_receipt_tracker_checkpoints(receipt)
        if policy["mode"] == "none":
            if checkpoints:
                fail("Tracker Policy mode none cannot have Tracker Checkpoints")
        else:
            if not checkpoints:
                fail(
                    f"Complete requires a completed Tracker Checkpoint when mode is {policy['mode']}"
                )
            current_checkpoints = [
                item
                for item in checkpoints
                if item["policy_key"] == policy["policy_key"]
            ]
            if not current_checkpoints:
                fail(
                    "stale policy: no Tracker Checkpoint matches current Tracker Policy"
                )
            uncheckpointed = compute_pending_tracker_updates(receipt, policy)
            if uncheckpointed:
                fail(
                    "Complete requires a completed Tracker Checkpoint for every Ticket disposition"
                )
            latest = checkpoints[-1]
            if latest["policy_key"] != policy["policy_key"]:
                fail(
                    "stale policy: latest Tracker Checkpoint does not match current Tracker Policy"
                )
            if (
                latest["candidate"]["commit"] != expected_tip_commit
                or latest["candidate"]["tree"] != expected_tip_tree
            ):
                fail(
                    "stale checkpoint: latest Tracker Checkpoint candidate does not match Accepted Integration Tip"
                )
    else:
        if not any(
            obligation["status"] in {"Open", "Blocked"}
            for obligation in audit["obligations"]
        ):
            fail("Stalled requires at least one unfinished obligation")
        for field in (
            "pending_tracker_updates",
            "unresolved_decisions",
            "needs_decisions",
            "runnable_tickets",
            "running_agents",
            "recovery_paths",
            "satisfiable_external_conditions",
        ):
            if audit[field]:
                fail(f"Stalled cannot have {field}")
        if receipt_pending:
            fail("Stalled cannot have pending_tracker_updates in receipt")
        if receipt.get("tracker_policy") is not None:
            validate_receipt_tracker_policy(receipt, reread_record=True)
        if receipt.get("ticket_dispositions"):
            effective = effective_ticket_dispositions(receipt, verify_evidence=True)
            verify_dispositions_match_obligations(
                effective, audit["obligations"], complete=False
            )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": EVIDENCE_KIND,
        "run_id": audit["run_id"],
        "outcome": audit["outcome"],
        "definition_identity": audit["definition_identity"],
        "accepted_tip": audit["accepted_tip"],
        "audit_sha256": sha256(read_regular_file(audit_path, "audit")),
        "verified": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify a Coordinator-owned Complete or Stalled terminal audit."
    )
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--expected-tip-commit", required=True)
    parser.add_argument("--expected-tip-tree", required=True)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        evidence = verify_audit(
            arguments.receipt,
            arguments.audit,
            require_oid(arguments.expected_tip_commit, "expected_tip_commit"),
            require_oid(arguments.expected_tip_tree, "expected_tip_tree"),
        )
        status = publish_once(
            arguments.output,
            canonical_json(evidence),
            [arguments.receipt, arguments.audit],
        )
    except (OSError, RecordError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": status,
                "kind": EVIDENCE_KIND,
                "outcome": evidence["outcome"],
                "verified": True,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
