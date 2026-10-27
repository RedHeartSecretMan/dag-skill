#!/usr/bin/env python3
"""Verify mechanical inputs for one Promotion Candidate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from index_execution_record import validate_receipt
from reconcile_execution_claim import validate_claim_entry
from record_execution_checkpoint import (
    RecordError,
    canonical_json,
    parse_json,
    publish_once,
    read_regular_file,
    require_identity,
    require_oid,
)
from record_review_context import validate_capsule
from record_tool_artifact import verify_handle
from verify_candidate_review import verify_candidate_review

SCHEMA_VERSION = 1
PACKAGE_KIND = "Promotion Evidence Package"


def fail(message: str) -> None:
    raise RecordError(message)


def verify_promotion_package(
    receipt_path: Path,
    ticket_id: str,
    context_path: Path,
    review_record_path: Path,
    review_handle_path: Path,
    artifact_root: Path,
    expected_tip_commit: str,
    expected_tip_tree: str,
) -> dict[str, Any]:
    receipt = validate_receipt(
        parse_json(read_regular_file(receipt_path, "receipt"), "receipt")
    )
    claims = receipt.get("claims", [])
    if not isinstance(claims, list):
        fail("receipt.claims must be an array")
    matching = [
        validate_claim_entry(item, f"receipt.claims[{index}]")
        for index, item in enumerate(claims)
        if isinstance(item, dict) and item.get("ticket_id") == ticket_id
    ]
    if len(matching) != 1:
        fail("receipt must contain exactly one live claim for the Ticket")
    claim = matching[0]
    capsule = validate_capsule(
        parse_json(
            read_regular_file(context_path, "context capsule"), "context capsule"
        )
    )
    if receipt["run_id"] != capsule["run_id"]:
        fail("receipt and context capsule run_id do not match")
    if claim["ticket_id"] != capsule["ticket_id"]:
        fail("live claim and context capsule ticket_id do not match")
    if claim["owner_id"] != capsule["owner_id"]:
        fail("live claim and context capsule owner_id do not match")
    if claim["claim_generation"] != capsule["claim_generation"]:
        fail("live claim and context capsule claim_generation do not match")
    if claim["ticket_base"] != capsule["ticket_base"]:
        fail("live claim and context capsule Ticket Base do not match")
    if capsule["ticket_base"]["commit"] != expected_tip_commit:
        fail("current Accepted Integration Tip commit does not match Ticket Base")
    if capsule["ticket_base"]["tree"] != expected_tip_tree:
        fail("current Accepted Integration Tip tree does not match Ticket Base")
    review_result = verify_candidate_review(
        review_record_path,
        context_path,
        review_handle_path,
        artifact_root,
        expected_tip_commit,
        expected_tip_tree,
        capsule["candidate"]["commit"],
        capsule["candidate"]["tree"],
        capsule["candidate"]["range"],
    )
    handle = verify_handle(review_handle_path, artifact_root)
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": PACKAGE_KIND,
        "run_id": receipt["run_id"],
        "receipt_generation": receipt["coordinator_generation"],
        "ticket_id": capsule["ticket_id"],
        "owner_id": capsule["owner_id"],
        "claim_generation": capsule["claim_generation"],
        "ticket_base": capsule["ticket_base"],
        "candidate": capsule["candidate"],
        "review_context_key": review_result["review_context_key"],
        "review_record_key": review_result["review_record_key"],
        "review_artifact_sha256": handle["artifact_sha256"],
        "fresh_review_required": True,
        "promotion_allowed": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify mechanical inputs for one Promotion Candidate."
    )
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--ticket-id", required=True)
    parser.add_argument("--context-capsule", required=True, type=Path)
    parser.add_argument("--review-record", required=True, type=Path)
    parser.add_argument("--review-handle", required=True, type=Path)
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--expected-tip-commit", required=True)
    parser.add_argument("--expected-tip-tree", required=True)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        package = verify_promotion_package(
            arguments.receipt,
            require_identity(arguments.ticket_id, "ticket_id"),
            arguments.context_capsule,
            arguments.review_record,
            arguments.review_handle,
            arguments.artifact_root,
            require_oid(arguments.expected_tip_commit, "expected_tip_commit"),
            require_oid(arguments.expected_tip_tree, "expected_tip_tree"),
        )
        status = publish_once(
            arguments.output,
            canonical_json(package),
            [
                arguments.receipt,
                arguments.context_capsule,
                arguments.review_record,
                arguments.review_handle,
            ],
        )
    except (OSError, RecordError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": status,
                "kind": PACKAGE_KIND,
                "ticket_id": package["ticket_id"],
                "promotion_allowed": True,
                "review_record_key": package["review_record_key"],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
