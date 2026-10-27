#!/usr/bin/env python3
"""Publish or consume an identity-bound Exploration Cache note."""

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
    require_relative_path,
    require_string_array,
    require_text,
    require_timestamp,
    sha256,
)

SCHEMA_VERSION = 1
NOTE_KIND = "Exploration Note"
CONTEXT_KIND = "Exploration Context"
CONSUMPTION_KIND = "Exploration Consumption Record"


def fail(message: str) -> None:
    raise RecordError(message)


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value


def validate_source_identities(value: Any, label: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        fail(f"{label} must be a non-empty array")
    result = []
    paths = set()
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        item = require_object(item, item_label)
        require_exact_fields(item, {"path", "identity"}, item_label)
        path = require_relative_path(item["path"], f"{item_label}.path")
        if path in paths:
            fail(f"{item_label}.path is duplicated")
        paths.add(path)
        result.append(
            {
                "path": path,
                "identity": require_identity(
                    item["identity"], f"{item_label}.identity"
                ),
            }
        )
    return sorted(result, key=lambda item: item["path"].encode("utf-8"))


def validate_conclusions(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        fail("note.conclusions must be a non-empty array")
    result = []
    ids = set()
    for index, item in enumerate(value):
        label = f"note.conclusions[{index}]"
        item = require_object(item, label)
        require_exact_fields(item, {"id", "statement", "evidence"}, label)
        conclusion_id = require_identity(item["id"], f"{label}.id")
        if conclusion_id in ids:
            fail(f"{label}.id is duplicated")
        ids.add(conclusion_id)
        evidence = item["evidence"]
        if not isinstance(evidence, list) or not evidence:
            fail(f"{label}.evidence must be a non-empty array")
        normalized_evidence = []
        evidence_paths = set()
        for evidence_index, evidence_item in enumerate(evidence):
            evidence_label = f"{label}.evidence[{evidence_index}]"
            evidence_item = require_object(evidence_item, evidence_label)
            require_exact_fields(evidence_item, {"path", "identity"}, evidence_label)
            path = require_relative_path(
                evidence_item["path"], f"{evidence_label}.path"
            )
            if path in evidence_paths:
                fail(f"{evidence_label}.path is duplicated")
            evidence_paths.add(path)
            normalized_evidence.append(
                {
                    "path": path,
                    "identity": require_identity(
                        evidence_item["identity"], f"{evidence_label}.identity"
                    ),
                }
            )
        result.append(
            {
                "id": conclusion_id,
                "statement": require_text(item["statement"], f"{label}.statement"),
                "evidence": sorted(
                    normalized_evidence,
                    key=lambda evidence_item: evidence_item["path"].encode("utf-8"),
                ),
            }
        )
    return result


def validate_note(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "note")
    expected = {
        "schema_version",
        "kind",
        "note_id",
        "question",
        "scope",
        "source_identities",
        "target_identity",
        "environment_identity",
        "author",
        "created_at",
        "invalidation_conditions",
        "conclusions",
        "limitations",
        "unresolved",
    }
    actual = set(payload)
    if "cache_key" in actual:
        expected_with_key = expected | {"cache_key"}
        if actual != expected_with_key:
            fail("note fields do not match schema_version 1")
    elif actual != expected:
        fail("note fields do not match schema_version 1")
    if payload["schema_version"] != SCHEMA_VERSION or payload["kind"] != NOTE_KIND:
        fail("note schema_version or kind is unsupported")
    result = {
        "schema_version": SCHEMA_VERSION,
        "kind": NOTE_KIND,
        "note_id": require_identity(payload["note_id"], "note.note_id"),
        "question": require_text(payload["question"], "note.question"),
        "scope": sorted(
            require_string_array(payload["scope"], "note.scope", paths=True),
            key=lambda path: path.encode("utf-8"),
        ),
        "source_identities": validate_source_identities(
            payload["source_identities"], "note.source_identities"
        ),
        "target_identity": require_identity(
            payload["target_identity"], "note.target_identity"
        ),
        "environment_identity": require_identity(
            payload["environment_identity"], "note.environment_identity"
        ),
        "author": require_identity(payload["author"], "note.author"),
        "created_at": require_timestamp(payload["created_at"], "note.created_at"),
        "invalidation_conditions": validate_text_array(
            payload["invalidation_conditions"], "note.invalidation_conditions"
        ),
        "conclusions": validate_conclusions(payload["conclusions"]),
        "limitations": validate_text_array(payload["limitations"], "note.limitations"),
        "unresolved": validate_text_array(payload["unresolved"], "note.unresolved"),
    }
    result["cache_key"] = compute_cache_key(result)
    if "cache_key" in payload and payload["cache_key"] != result["cache_key"]:
        fail("note.cache_key does not match its source identities")
    return result


def validate_text_array(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        fail(f"{label} must be an array")
    return [require_text(item, f"{label}[{index}]") for index, item in enumerate(value)]


def compute_cache_key(note: dict[str, Any]) -> str:
    material = {
        "question": note["question"],
        "scope": note["scope"],
        "source_identities": note["source_identities"],
        "target_identity": note["target_identity"],
        "environment_identity": note["environment_identity"],
    }
    return hashlib.sha256(canonical_json(material)).hexdigest()


def validate_context(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "context")
    expected = {
        "schema_version",
        "kind",
        "question",
        "scope",
        "source_identities",
        "target_identity",
        "environment_identity",
        "observed_at",
    }
    require_exact_fields(payload, expected, "context")
    if payload["schema_version"] != SCHEMA_VERSION or payload["kind"] != CONTEXT_KIND:
        fail("context schema_version or kind is unsupported")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": CONTEXT_KIND,
        "question": require_text(payload["question"], "context.question"),
        "scope": set(
            require_string_array(payload["scope"], "context.scope", paths=True)
        ),
        "source_identities": validate_source_identities(
            payload["source_identities"], "context.source_identities"
        ),
        "target_identity": require_identity(
            payload["target_identity"], "context.target_identity"
        ),
        "environment_identity": require_identity(
            payload["environment_identity"], "context.environment_identity"
        ),
        "observed_at": require_timestamp(payload["observed_at"], "context.observed_at"),
    }


def validate_context_against_note(
    note: dict[str, Any], context: dict[str, Any]
) -> None:
    if note["question"] != context["question"]:
        fail("context.question does not match note.question")
    if not set(note["scope"]).issubset(context["scope"]):
        fail("context.scope does not cover note.scope")
    current_sources = {
        item["path"]: item["identity"] for item in context["source_identities"]
    }
    for source in note["source_identities"]:
        if current_sources.get(source["path"]) != source["identity"]:
            fail(f"context source identity does not match {source['path']}")
    if note["target_identity"] != context["target_identity"]:
        fail("context.target_identity does not match note.target_identity")
    if note["environment_identity"] != context["environment_identity"]:
        fail("context.environment_identity does not match note.environment_identity")


def consume_note(
    note_path: Path,
    note_bytes: bytes,
    note: dict[str, Any],
    context: dict[str, Any],
    context_path: Path,
    output: Path,
) -> tuple[str, dict[str, Any]]:
    validate_context_against_note(note, context)
    record = {
        "schema_version": SCHEMA_VERSION,
        "kind": CONSUMPTION_KIND,
        "note_ref": {"path": str(note_path.resolve()), "sha256": sha256(note_bytes)},
        "cache_key": note["cache_key"],
        "question": note["question"],
        "scope": sorted(context["scope"], key=lambda path: path.encode("utf-8")),
        "observed_at": context["observed_at"],
        "verified_source_identities": note["source_identities"],
        "target_identity": note["target_identity"],
        "environment_identity": note["environment_identity"],
    }
    return publish_once(
        output, canonical_json(record), [note_path, context_path]
    ), record


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish or consume an identity-bound Exploration Cache note."
    )
    parser.add_argument("--note", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--context", type=Path)
    arguments = parser.parse_args()
    try:
        note_bytes = read_regular_file(arguments.note, "note")
        note = validate_note(parse_json(note_bytes, "note"))
        if arguments.context is None:
            status = publish_once(
                arguments.output, canonical_json(note), [arguments.note]
            )
            result = {
                "status": status,
                "kind": NOTE_KIND,
                "cache_key": note["cache_key"],
            }
        else:
            context_bytes = read_regular_file(arguments.context, "context")
            context = validate_context(parse_json(context_bytes, "context"))
            status, record = consume_note(
                arguments.note,
                note_bytes,
                note,
                context,
                arguments.context,
                arguments.output,
            )
            result = {
                "status": status,
                "kind": CONSUMPTION_KIND,
                "cache_key": record["cache_key"],
            }
    except (OSError, RecordError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
