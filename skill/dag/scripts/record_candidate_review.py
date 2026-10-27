#!/usr/bin/env python3
"""Bind one complete review Artifact Handle to a fresh Review Context Capsule."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from record_execution_checkpoint import (
    RecordError,
    canonical_json,
    parse_json,
    publish_once,
    read_regular_file,
)
from record_review_context import validate_capsule
from record_tool_artifact import verify_handle

SCHEMA_VERSION = 1
RECORD_KIND = "Candidate Review Record"


def fail(message: str) -> None:
    raise RecordError(message)


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value


def review_record_key(capsule: dict[str, Any], handle: dict[str, Any]) -> str:
    material = {
        "review_context_key": capsule["review_context_key"],
        "review_artifact": {
            "path": handle["artifact_path"],
            "sha256": handle["artifact_sha256"],
            "command": handle["command"],
            "cwd": handle["cwd"],
            "exit_code": handle["exit_code"],
            "duration_ms": handle["duration_ms"],
            "observed_at": handle["observed_at"],
            "environment_identity": handle["environment_identity"],
        },
    }
    return hashlib.sha256(canonical_json(material)).hexdigest()


def create_record(capsule: dict[str, Any], handle: dict[str, Any]) -> dict[str, Any]:
    if handle["artifact_kind"] not in {"review-report", "tool-output"}:
        fail("review handle artifact_kind must be review-report or tool-output")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": RECORD_KIND,
        "run_id": capsule["run_id"],
        "ticket_id": capsule["ticket_id"],
        "owner_id": capsule["owner_id"],
        "claim_generation": capsule["claim_generation"],
        "ticket_base": capsule["ticket_base"],
        "candidate": capsule["candidate"],
        "definition_identity": capsule["definition_identity"],
        "changed_paths": capsule["changed_paths"],
        "acceptance_obligations": capsule["acceptance_obligations"],
        "required_gates": capsule["required_gates"],
        "evidence_refs": capsule["evidence_refs"],
        "exploration_refs": capsule["exploration_refs"],
        "fresh_review_required": True,
        "review_context_key": capsule["review_context_key"],
        "review_artifact": handle,
        "review_record_key": review_record_key(capsule, handle),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bind one complete review Artifact Handle to a fresh Review Context Capsule."
    )
    parser.add_argument("--context-capsule", required=True, type=Path)
    parser.add_argument("--review-handle", required=True, type=Path)
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        capsule_bytes = read_regular_file(arguments.context_capsule, "context capsule")
        capsule = validate_capsule(parse_json(capsule_bytes, "context capsule"))
        handle = verify_handle(arguments.review_handle, arguments.artifact_root)
        record = create_record(capsule, handle)
        status = publish_once(
            arguments.output,
            canonical_json(record),
            [arguments.context_capsule, arguments.review_handle],
        )
    except (OSError, RecordError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": status,
                "kind": RECORD_KIND,
                "review_record_key": record["review_record_key"],
                "fresh_review_required": True,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
