#!/usr/bin/env python3
"""Publish a candidate-bound Review Context Capsule."""

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
    require_exact_fields,
    require_identity,
    require_integer,
    require_oid,
    require_relative_path,
    require_string_array,
    require_text,
    sha256,
    validate_ticket_base,
)

SCHEMA_VERSION = 1
INPUT_KIND = "Review Context"
OUTPUT_KIND = "Review Context Capsule"


def fail(message: str) -> None:
    raise RecordError(message)


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value


def validate_obligations(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        fail("context.acceptance_obligations must be a non-empty array")
    result = []
    ids = set()
    for index, item in enumerate(value):
        label = f"context.acceptance_obligations[{index}]"
        item = require_object(item, label)
        require_exact_fields(item, {"id", "source", "identity"}, label)
        obligation_id = require_identity(item["id"], f"{label}.id")
        if obligation_id in ids:
            fail(f"{label}.id is duplicated")
        ids.add(obligation_id)
        result.append(
            {
                "id": obligation_id,
                "source": require_relative_path(item["source"], f"{label}.source"),
                "identity": require_identity(item["identity"], f"{label}.identity"),
            }
        )
    return result


def validate_identity_refs(value: Any, label: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        fail(f"{label} must be an array")
    result = []
    names = set()
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        item = require_object(item, item_label)
        require_exact_fields(item, {"name", "identity"}, item_label)
        name = require_identity(item["name"], f"{item_label}.name")
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


def validate_file_refs(value: Any, label: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        fail(f"{label} must be an array")
    result = []
    ids = set()
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        item = require_object(item, item_label)
        require_exact_fields(item, {"id", "path", "sha256"}, item_label)
        ref_id = require_identity(item["id"], f"{item_label}.id")
        if ref_id in ids:
            fail(f"{item_label}.id is duplicated")
        ids.add(ref_id)
        path = Path(require_text(item["path"], f"{item_label}.path"))
        declared = require_text(item["sha256"], f"{item_label}.sha256", safe_name=True)
        if len(declared) != 64 or any(
            character not in "0123456789abcdef" for character in declared
        ):
            fail(f"{item_label}.sha256 must be 64 lowercase hexadecimal characters")
        actual = read_regular_file(path, f"{item_label}.path")
        if sha256(actual) != declared:
            fail(f"{item_label}.path SHA-256 does not match")
        result.append({"id": ref_id, "path": str(path.resolve()), "sha256": declared})
    return result


def validate_candidate(value: Any) -> dict[str, Any]:
    value = require_object(value, "context.candidate")
    require_exact_fields(
        value, {"commit", "tree", "range", "commits"}, "context.candidate"
    )
    commit = require_oid(value["commit"], "context.candidate.commit")
    tree = require_oid(value["tree"], "context.candidate.tree")
    commit_list = value["commits"]
    if not isinstance(commit_list, list) or not commit_list:
        fail("context.candidate.commits must be a non-empty array")
    commits = [
        require_oid(item, f"context.candidate.commits[{index}]")
        for index, item in enumerate(commit_list)
    ]
    if len(commits) != len(set(commits)):
        fail("context.candidate.commits must not contain duplicates")
    if commits[-1] != commit:
        fail("context.candidate.commit must be the last commit in commits")
    return {
        "commit": commit,
        "tree": tree,
        "range": require_text(value["range"], "context.candidate.range"),
        "commits": commits,
    }


def validate_context(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "context")
    expected = {
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
    }
    require_exact_fields(payload, expected, "context")
    if payload["schema_version"] != SCHEMA_VERSION or payload["kind"] != INPUT_KIND:
        fail("context schema_version or kind is unsupported")
    base = validate_ticket_base(payload["ticket_base"], "context.ticket_base")
    candidate = validate_candidate(payload["candidate"])
    if base["commit"] == candidate["commit"]:
        fail("context candidate must differ from ticket_base")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": INPUT_KIND,
        "run_id": require_identity(payload["run_id"], "context.run_id"),
        "ticket_id": require_identity(payload["ticket_id"], "context.ticket_id"),
        "owner_id": require_identity(payload["owner_id"], "context.owner_id"),
        "claim_generation": require_integer(
            payload["claim_generation"], "context.claim_generation"
        ),
        "ticket_base": base,
        "candidate": candidate,
        "definition_identity": require_identity(
            payload["definition_identity"], "context.definition_identity"
        ),
        "changed_paths": require_string_array(
            payload["changed_paths"], "context.changed_paths", paths=True
        ),
        "acceptance_obligations": validate_obligations(
            payload["acceptance_obligations"]
        ),
        "required_gates": validate_identity_refs(
            payload["required_gates"], "context.required_gates"
        ),
        "evidence_refs": validate_file_refs(
            payload["evidence_refs"], "context.evidence_refs"
        ),
        "exploration_refs": validate_file_refs(
            payload["exploration_refs"], "context.exploration_refs"
        ),
    }


def context_key(context: dict[str, Any]) -> str:
    material = {
        "run_id": context["run_id"],
        "ticket_id": context["ticket_id"],
        "ticket_base": context["ticket_base"],
        "candidate": context["candidate"],
        "definition_identity": context["definition_identity"],
        "changed_paths": context["changed_paths"],
        "acceptance_obligations": context["acceptance_obligations"],
        "required_gates": context["required_gates"],
        "evidence_refs": context["evidence_refs"],
        "exploration_refs": context["exploration_refs"],
    }
    return hashlib.sha256(canonical_json(material)).hexdigest()


def create_capsule(context: dict[str, Any]) -> dict[str, Any]:
    return {
        **context,
        "kind": OUTPUT_KIND,
        "fresh_review_required": True,
        "review_context_key": context_key(context),
    }


def validate_capsule(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "capsule")
    expected = {
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
    }
    require_exact_fields(payload, expected, "capsule")
    if payload["kind"] != OUTPUT_KIND or payload["fresh_review_required"] is not True:
        fail("capsule kind or fresh_review_required is invalid")
    context_payload = {
        key: payload[key]
        for key in expected
        if key not in {"kind", "fresh_review_required", "review_context_key"}
    }
    context_payload["kind"] = INPUT_KIND
    context = validate_context(context_payload)
    expected_key = context_key(context)
    if payload["review_context_key"] != expected_key:
        fail("capsule.review_context_key does not match its identities")
    return {
        **context,
        "kind": OUTPUT_KIND,
        "fresh_review_required": True,
        "review_context_key": expected_key,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish a candidate-bound Review Context Capsule."
    )
    parser.add_argument("--context", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        context_bytes = read_regular_file(arguments.context, "context")
        context = validate_context(parse_json(context_bytes, "context"))
        capsule = create_capsule(context)
        status = publish_once(
            arguments.output, canonical_json(capsule), [arguments.context]
        )
    except (OSError, RecordError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": status,
                "kind": OUTPUT_KIND,
                "review_context_key": capsule["review_context_key"],
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
