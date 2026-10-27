#!/usr/bin/env python3
"""Verify a candidate-bound review record before handoff or Promotion."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from record_candidate_review import review_record_key
from record_execution_checkpoint import (
    RecordError,
    parse_json,
    read_regular_file,
    require_exact_fields,
    require_oid,
    require_text,
)
from record_review_context import validate_capsule
from record_tool_artifact import verify_handle

RECORD_KIND = "Candidate Review Record"
RECORD_FIELDS = {
    "schema_version",
    "kind",
    "run_id",
    "ticket_id",
    "owner_id",
    "claim_generation",
    "ticket_base",
    "candidate",
    "definition_identity",
    "changed_paths",
    "acceptance_obligations",
    "required_gates",
    "evidence_refs",
    "exploration_refs",
    "fresh_review_required",
    "review_context_key",
    "review_artifact",
    "review_record_key",
}


def fail(message: str) -> None:
    raise RecordError(message)


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value


def verify_candidate_review(
    record_path: Path,
    context_path: Path,
    handle_path: Path,
    artifact_root: Path,
    expected_base_commit: str,
    expected_base_tree: str,
    expected_candidate_commit: str,
    expected_candidate_tree: str,
    expected_candidate_range: str,
) -> dict[str, Any]:
    record_bytes = read_regular_file(record_path, "review record")
    record = require_object(parse_json(record_bytes, "review record"), "review record")
    require_exact_fields(record, RECORD_FIELDS, "review record")
    if record["schema_version"] != 1 or record["kind"] != RECORD_KIND:
        fail("review record schema_version or kind is unsupported")
    if record["fresh_review_required"] is not True:
        fail("review record fresh_review_required must be true")
    capsule = validate_capsule(
        parse_json(
            read_regular_file(context_path, "context capsule"), "context capsule"
        )
    )
    handle = verify_handle(handle_path, artifact_root)
    if handle["artifact_kind"] not in {"review-report", "tool-output"}:
        fail("review handle artifact_kind is not review-capable")
    for field in ("run_id", "ticket_id", "owner_id", "claim_generation"):
        if record[field] != capsule[field]:
            fail(f"review record and capsule {field} do not match")
    for field in (
        "ticket_base",
        "candidate",
        "definition_identity",
        "changed_paths",
        "acceptance_obligations",
        "required_gates",
        "evidence_refs",
        "exploration_refs",
        "review_context_key",
    ):
        if record[field] != capsule[field]:
            fail(f"review record and capsule {field} do not match")
    if record["review_artifact"] != handle:
        fail("review record and Artifact Handle do not match")
    expected_key = review_record_key(capsule, handle)
    if record["review_record_key"] != expected_key:
        fail("review_record_key does not match current context and artifact")
    if capsule["ticket_base"]["commit"] != expected_base_commit:
        fail("current Ticket Base commit does not match review record")
    if capsule["ticket_base"]["tree"] != expected_base_tree:
        fail("current Ticket Base tree does not match review record")
    if capsule["candidate"]["commit"] != expected_candidate_commit:
        fail("candidate commit does not match review record")
    if capsule["candidate"]["tree"] != expected_candidate_tree:
        fail("candidate tree does not match review record")
    if capsule["candidate"]["range"] != expected_candidate_range:
        fail("candidate range does not match review record")
    return {
        "status": "verified",
        "kind": RECORD_KIND,
        "run_id": record["run_id"],
        "ticket_id": record["ticket_id"],
        "claim_generation": record["claim_generation"],
        "review_context_key": record["review_context_key"],
        "review_record_key": record["review_record_key"],
        "fresh_review_required": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify a candidate-bound review record before handoff or Promotion."
    )
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--context-capsule", required=True, type=Path)
    parser.add_argument("--review-handle", required=True, type=Path)
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--expected-base-commit", required=True)
    parser.add_argument("--expected-base-tree", required=True)
    parser.add_argument("--expected-candidate-commit", required=True)
    parser.add_argument("--expected-candidate-tree", required=True)
    parser.add_argument("--expected-candidate-range", required=True)
    arguments = parser.parse_args()
    try:
        result = verify_candidate_review(
            arguments.record,
            arguments.context_capsule,
            arguments.review_handle,
            arguments.artifact_root,
            require_oid(arguments.expected_base_commit, "expected_base_commit"),
            require_oid(arguments.expected_base_tree, "expected_base_tree"),
            require_oid(
                arguments.expected_candidate_commit, "expected_candidate_commit"
            ),
            require_oid(arguments.expected_candidate_tree, "expected_candidate_tree"),
            require_text(
                arguments.expected_candidate_range, "expected_candidate_range"
            ),
        )
    except (OSError, RecordError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
