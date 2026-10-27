#!/usr/bin/env python3
"""CAS-record an explicit Coordinator-owned Ticket disposition."""

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
from record_execution_checkpoint import (
    RecordError,
    canonical_json,
    parse_json,
    read_regular_file,
    require_exact_fields,
    require_identity,
    require_integer,
    require_sha256,
    require_text,
    sha256,
)

SCHEMA_VERSION = 1
DECISION_KIND = "Ticket Disposition Decision"
DISPOSITION_KIND = "Ticket Disposition"
DISPOSITIONS = {"Accepted", "Superseded"}
DECISION_FIELDS = {
    "schema_version",
    "kind",
    "run_id",
    "coordinator_generation",
    "ticket_id",
    "claim_generation",
    "disposition",
    "rule_identity",
    "decided_by",
    "decided_at",
    "rationale",
    "evidence_refs",
}


def fail(message: str) -> None:
    raise RecordError(message)


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value


def validate_evidence_refs(value: Any, label: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        fail(f"{label} must be a non-empty array")
    result = []
    ids = set()
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        item = require_object(item, item_label)
        require_exact_fields(item, {"id", "path", "sha256"}, item_label)
        evidence_id = require_identity(item["id"], f"{item_label}.id")
        if evidence_id in ids:
            fail(f"{item_label}.id is duplicated")
        ids.add(evidence_id)
        path = Path(require_text(item["path"], f"{item_label}.path"))
        declared = require_sha256(item["sha256"], f"{item_label}.sha256")
        content = read_regular_file(path, f"{item_label}.path")
        if sha256(content) != declared:
            fail(f"{item_label}.path SHA-256 does not match")
        result.append(
            {"id": evidence_id, "path": str(path.resolve()), "sha256": declared}
        )
    return result


def validate_decision(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "decision")
    require_exact_fields(payload, DECISION_FIELDS, "decision")
    if payload["schema_version"] != SCHEMA_VERSION or payload["kind"] != DECISION_KIND:
        fail("decision schema_version or kind is unsupported")
    disposition = require_text(
        payload["disposition"], "decision.disposition", safe_name=True
    )
    if disposition not in DISPOSITIONS:
        fail("decision.disposition is unsupported")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": DECISION_KIND,
        "run_id": require_identity(payload["run_id"], "decision.run_id"),
        "coordinator_generation": require_integer(
            payload["coordinator_generation"], "decision.coordinator_generation"
        ),
        "ticket_id": require_identity(payload["ticket_id"], "decision.ticket_id"),
        "claim_generation": require_integer(
            payload["claim_generation"], "decision.claim_generation"
        ),
        "disposition": disposition,
        "rule_identity": require_identity(
            payload["rule_identity"], "decision.rule_identity"
        ),
        "decided_by": require_identity(payload["decided_by"], "decision.decided_by"),
        "decided_at": require_text(payload["decided_at"], "decision.decided_at"),
        "rationale": require_text(payload["rationale"], "decision.rationale"),
        "evidence_refs": validate_evidence_refs(
            payload["evidence_refs"], "decision.evidence_refs"
        ),
    }


def validate_promotion_package(
    path: Path,
    digest: str,
    decision: dict[str, Any],
    expected_generation: int,
    claim: dict[str, Any],
) -> str:
    content = read_regular_file(path, "promotion evidence")
    if sha256(content) != digest:
        fail("promotion evidence SHA-256 does not match")
    package = require_object(
        parse_json(content, "promotion evidence"), "promotion evidence"
    )
    required = {
        "schema_version",
        "kind",
        "run_id",
        "receipt_generation",
        "ticket_id",
        "owner_id",
        "claim_generation",
        "ticket_base",
        "candidate",
        "review_context_key",
        "review_record_key",
        "review_artifact_sha256",
        "fresh_review_required",
        "promotion_allowed",
    }
    require_exact_fields(package, required, "promotion evidence")
    if (
        package["schema_version"] != 1
        or package["kind"] != "Promotion Evidence Package"
        or package["promotion_allowed"] is not True
        or package["fresh_review_required"] is not True
    ):
        fail("promotion evidence is not allowed")
    if package["run_id"] != decision["run_id"]:
        fail("promotion evidence run_id does not match decision")
    if package["ticket_id"] != decision["ticket_id"]:
        fail("promotion evidence ticket_id does not match decision")
    if package["claim_generation"] != decision["claim_generation"]:
        fail("promotion evidence claim_generation does not match decision")
    if package["receipt_generation"] != expected_generation:
        fail("promotion evidence receipt_generation does not match receipt")
    if package["owner_id"] != claim.get("owner_id"):
        fail("promotion evidence owner_id does not match live claim")
    if package["ticket_base"] != claim.get("ticket_base"):
        fail("promotion evidence Ticket Base does not match live claim")
    return digest


def _record_disposition_locked(
    receipt_path: Path,
    decision_path: Path,
    promotion_path: Path | None,
    promotion_digest: str | None,
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
    decision = validate_decision(
        parse_json(read_regular_file(decision_path, "decision"), "decision")
    )
    if decision["run_id"] != receipt["run_id"]:
        fail("receipt and decision run_id do not match")
    dispositions = receipt.setdefault("ticket_dispositions", [])
    if not isinstance(dispositions, list):
        fail("receipt.ticket_dispositions must be an array")
    existing = [
        item
        for item in dispositions
        if isinstance(item, dict)
        and item.get("ticket_id") == decision["ticket_id"]
        and item.get("claim_generation") == decision["claim_generation"]
    ]
    if existing:
        if len(existing) != 1:
            fail("receipt contains duplicate dispositions for this claim")
        current = existing[0]
        if decision["disposition"] == "Accepted":
            if promotion_path is None or promotion_digest is None:
                fail("Accepted disposition requires promotion evidence")
            promotion_sha = require_sha256(
                promotion_digest, "promotion_evidence_sha256"
            )
        elif promotion_path is not None or promotion_digest is not None:
            fail("Superseded disposition cannot carry promotion evidence")
        else:
            promotion_sha = None
        expected = {
            "schema_version": SCHEMA_VERSION,
            "kind": DISPOSITION_KIND,
            "run_id": decision["run_id"],
            "coordinator_generation": decision["coordinator_generation"],
            "ticket_id": decision["ticket_id"],
            "claim_generation": decision["claim_generation"],
            "disposition": decision["disposition"],
            "rule_identity": decision["rule_identity"],
            "decided_by": decision["decided_by"],
            "decided_at": decision["decided_at"],
            "rationale": decision["rationale"],
            "evidence_refs": decision["evidence_refs"],
            "promotion_evidence_sha256": promotion_sha,
            "claim_owner_id": current.get("claim_owner_id"),
        }
        if current == expected:
            return "already-recorded", current
        fail("receipt already contains a different disposition for this claim")
    if decision["coordinator_generation"] != expected_generation:
        fail("decision coordinator_generation does not match receipt")
    claims = receipt.get("claims", [])
    if not isinstance(claims, list):
        fail("receipt.claims must be an array")
    matches = [
        item
        for item in claims
        if isinstance(item, dict)
        and item.get("ticket_id") == decision["ticket_id"]
        and item.get("claim_generation") == decision["claim_generation"]
    ]
    if len(matches) != 1:
        fail("receipt must contain exactly one live claim matching the decision")
    claim = matches[0]
    if decision["disposition"] == "Accepted":
        if promotion_path is None or promotion_digest is None:
            fail("Accepted disposition requires promotion evidence")
        promotion_sha = validate_promotion_package(
            promotion_path,
            promotion_digest,
            decision,
            expected_generation,
            claim,
        )
    elif promotion_path is not None or promotion_digest is not None:
        fail("Superseded disposition cannot carry promotion evidence")
    else:
        promotion_sha = None
    entry = {
        "schema_version": SCHEMA_VERSION,
        "kind": DISPOSITION_KIND,
        "run_id": decision["run_id"],
        "coordinator_generation": decision["coordinator_generation"],
        "ticket_id": decision["ticket_id"],
        "claim_generation": decision["claim_generation"],
        "disposition": decision["disposition"],
        "rule_identity": decision["rule_identity"],
        "decided_by": decision["decided_by"],
        "decided_at": decision["decided_at"],
        "rationale": decision["rationale"],
        "evidence_refs": decision["evidence_refs"],
        "promotion_evidence_sha256": promotion_sha,
        "claim_owner_id": claim.get("owner_id"),
    }
    receipt["claims"] = [
        item
        for item in claims
        if not (
            isinstance(item, dict)
            and item.get("ticket_id") == decision["ticket_id"]
            and item.get("claim_generation") == decision["claim_generation"]
        )
    ]
    dispositions.append(entry)
    receipt["coordinator_generation"] += 1
    replace_receipt(receipt_path, receipt_bytes, canonical_json(receipt), locked=True)
    return "recorded", entry


def record_disposition(
    receipt_path: Path,
    decision_path: Path,
    promotion_path: Path | None,
    promotion_digest: str | None,
    expected_generation: int,
    expected_receipt_digest: str,
) -> tuple[str, dict[str, Any]]:
    with receipt_lock(receipt_path):
        return _record_disposition_locked(
            receipt_path,
            decision_path,
            promotion_path,
            promotion_digest,
            expected_generation,
            expected_receipt_digest,
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CAS-record an explicit Coordinator-owned Ticket disposition."
    )
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--decision", required=True, type=Path)
    parser.add_argument("--promotion-evidence", type=Path)
    parser.add_argument("--promotion-evidence-sha256")
    parser.add_argument("--expected-generation", required=True, type=int)
    parser.add_argument("--expected-receipt-sha256", required=True)
    arguments = parser.parse_args()
    try:
        status, entry = record_disposition(
            arguments.receipt,
            arguments.decision,
            arguments.promotion_evidence,
            arguments.promotion_evidence_sha256,
            arguments.expected_generation,
            require_sha256(
                arguments.expected_receipt_sha256, "expected_receipt_sha256"
            ),
        )
    except (OSError, ReceiptIndexError, RecordError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": status,
                "kind": DISPOSITION_KIND,
                "ticket_id": entry["ticket_id"],
                "disposition": entry["disposition"],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
