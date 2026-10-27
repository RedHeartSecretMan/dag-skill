#!/usr/bin/env python3
"""Consume one live claim and produce a writer-liveness-aware resume capsule."""

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
    validate_receipt,
    validate_record,
)
from record_execution_checkpoint import (
    RecordError,
    canonical_json,
    parse_json,
    publish_once,
    read_regular_file,
    require_exact_fields,
    require_identity,
    require_text,
    sha256,
)
from record_execution_claim import CLAIM_ENTRY_FIELDS, validate_claim

SCHEMA_VERSION = 1
CAPSULE_KIND = "Execution Resume Capsule"
WRITER_STATES = {"live", "stopped", "unknown"}


def fail(message: str) -> None:
    raise RecordError(message)


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value


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


def make_liveness_evidence(path: Path) -> dict[str, str]:
    content = read_regular_file(path, "liveness evidence")
    return {"path": str(path.resolve()), "sha256": sha256(content)}


def reconcile_claim(
    receipt_path: Path,
    ticket_id: str,
    artifact_root: Path | None,
    writer_state: str,
    recheck_event: str | None,
    liveness_evidence_path: Path | None,
) -> dict[str, Any]:
    receipt_bytes = read_regular_file(receipt_path, "receipt")
    receipt = validate_receipt(parse_json(receipt_bytes, "receipt"))
    claims = receipt.get("claims", [])
    if not isinstance(claims, list):
        fail("receipt.claims must be an array")
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
        liveness_evidence = make_liveness_evidence(liveness_evidence_path)
        if recheck_event is not None:
            fail(f"{writer_state} writer_state cannot set recheck_event")

    checkpoint_summary = None
    records = receipt.get("execution_records", [])
    if not isinstance(records, list):
        fail("receipt.execution_records must be an array")
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
        require_exact_fields(
            record_entry,
            {
                "ticket_id",
                "owner_id",
                "claim_generation",
                "phase",
                "record_path",
                "record_sha256",
                "checkpoint_sha256",
                "capsule_sha256",
                "observed_at",
            },
            "receipt.execution_records entry",
        )
        if artifact_root is None:
            fail("artifact_root is required when a Checkpoint Record is indexed")
        record_path = Path(require_text(record_entry["record_path"], "record_path"))
        record_bytes = read_regular_file(record_path, "execution record")
        if sha256(record_bytes) != record_entry["record_sha256"]:
            fail("execution record SHA-256 does not match Receipt")
        record, _digest, _capsule, checkpoint = validate_record(
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

    return {
        "schema_version": SCHEMA_VERSION,
        "kind": CAPSULE_KIND,
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consume a live claim with explicit writer-liveness recovery rules."
    )
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--ticket-id", required=True)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--writer-state", required=True, choices=sorted(WRITER_STATES))
    parser.add_argument("--recheck-event")
    parser.add_argument("--liveness-evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        ticket_id = require_identity(arguments.ticket_id, "ticket_id")
        capsule = reconcile_claim(
            arguments.receipt,
            ticket_id,
            arguments.artifact_root,
            arguments.writer_state,
            arguments.recheck_event,
            arguments.liveness_evidence,
        )
        status = publish_once(
            arguments.output, canonical_json(capsule), [arguments.receipt]
        )
    except (OSError, ReceiptIndexError, RecordError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": status,
                "kind": CAPSULE_KIND,
                "ticket_id": capsule["ticket_id"],
                "writer_state": capsule["writer_state"],
                "resume_allowed": capsule["resume_allowed"],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
