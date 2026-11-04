"""Artifact Handles, Exploration Cache, Execution Checkpoint Records, and Candidate Reviews."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path, PurePosixPath
from typing import Any

from lib.common import (
    CONTEXT_MEASUREMENT_KINDS,
    FINALIZATION_POLICIES,
    FINDING_DISPOSITIONS,
    METRIC_NAMES,
    METRIC_UNITS,
    OBSERVED_RESULTS,
    PHASES,
    RESOURCE_MODES,
    SCHEMA_VERSION,
    canonical_json,
    fail,
    parse_json,
    path_contains,
    publish_once,
    read_regular_file,
    require_exact_fields,
    require_identity,
    require_integer,
    require_object,
    require_oid,
    require_relative_path,
    require_schema,
    require_sha256,
    require_string_array,
    require_text,
    require_timestamp,
    sha256,
    validate_ticket_base,
)
from lib.receipt import (
    RECEIPT_KIND,
    receipt_lock,
    replace_receipt,
    safe_receipt_target,
    validate_receipt,
)

HANDLE_KIND = "Artifact Handle"
ARTIFACT_KINDS = {"stdout", "stderr", "tool-output", "test-log", "review-report", "log"}
HANDLE_FIELDS = {
    "schema_version",
    "kind",
    "artifact_kind",
    "artifact_root",
    "artifact_path",
    "artifact_sha256",
    "byte_count",
    "command",
    "cwd",
    "exit_code",
    "duration_ms",
    "observed_at",
    "environment_identity",
    "commit",
    "tree",
}

NOTE_KIND = "Exploration Note"
EXPLORATION_CONTEXT_KIND = "Exploration Context"
CONSUMPTION_KIND = "Exploration Consumption Record"

CHECKPOINT_KIND = "Execution Checkpoint"
CAPSULE_KIND = "Ticket Capsule"
EXECUTION_RECORD_KIND = "Execution Checkpoint Record"
EXECUTION_RECORD_FIELDS = {
    "schema_version",
    "kind",
    "run_id",
    "ticket_id",
    "owner_id",
    "claim_generation",
    "phase",
    "checkpoint_ref",
    "capsule_ref",
    "ticket_base",
    "candidate",
    "evidence_ids",
    "metrics",
    "context_budget",
    "measurement_version",
    "observed_at",
    "capsule_definition_identity",
}

REVIEW_INPUT_KIND = "Review Context"
REVIEW_CAPSULE_KIND = "Review Context Capsule"
CANDIDATE_REVIEW_KIND = "Candidate Review Record"
CANDIDATE_REVIEW_FIELDS = {
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


# --- Artifact Handles ---


def validate_handle(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "handle")
    require_exact_fields(payload, HANDLE_FIELDS, "handle")
    if payload["schema_version"] != SCHEMA_VERSION or payload["kind"] != HANDLE_KIND:
        fail("handle schema_version or kind is unsupported")
    artifact_kind = require_text(
        payload["artifact_kind"], "handle.artifact_kind", safe_name=True
    )
    if artifact_kind not in ARTIFACT_KINDS:
        fail("handle.artifact_kind is unsupported")
    commit = payload["commit"]
    tree = payload["tree"]
    if (commit is None) != (tree is None):
        fail("handle.commit and handle.tree must be supplied together")
    if commit is not None:
        commit = require_oid(commit, "handle.commit")
    if tree is not None:
        tree = require_oid(tree, "handle.tree")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": HANDLE_KIND,
        "artifact_kind": artifact_kind,
        "artifact_root": require_text(payload["artifact_root"], "handle.artifact_root"),
        "artifact_path": require_text(payload["artifact_path"], "handle.artifact_path"),
        "artifact_sha256": require_sha256(
            payload["artifact_sha256"], "handle.artifact_sha256"
        ),
        "byte_count": require_integer(payload["byte_count"], "handle.byte_count"),
        "command": require_text(payload["command"], "handle.command"),
        "cwd": require_text(payload["cwd"], "handle.cwd"),
        "exit_code": require_integer(
            payload["exit_code"], "handle.exit_code", minimum=-2147483648
        ),
        "duration_ms": require_integer(payload["duration_ms"], "handle.duration_ms"),
        "observed_at": require_timestamp(payload["observed_at"], "handle.observed_at"),
        "environment_identity": require_identity(
            payload["environment_identity"], "handle.environment_identity"
        ),
        "commit": commit,
        "tree": tree,
    }


def create_handle(
    artifact: Path,
    artifact_bytes: bytes,
    artifact_kind: str,
    command: str,
    cwd: str,
    exit_code: int,
    duration_ms: int,
    observed_at: str,
    environment_identity: str,
    commit: str | None,
    tree: str | None,
    artifact_root: Path,
) -> dict[str, Any]:
    if artifact_kind not in ARTIFACT_KINDS:
        fail("artifact_kind is unsupported")
    if exit_code < -2147483648 or exit_code > 2147483647:
        fail("exit_code is outside the supported range")
    if duration_ms < 0:
        fail("duration_ms must be >= 0")
    if (commit is None) != (tree is None):
        fail("commit and tree must be supplied together")
    if commit is not None:
        commit = require_oid(commit, "commit")
        tree = require_oid(tree, "tree")
    try:
        root = artifact_root.resolve(strict=True)
    except OSError as error:
        fail(f"artifact_root could not be resolved: {error}")
    if artifact_root.is_symlink() or not root.is_dir():
        fail("artifact_root must be an existing non-symlink directory")
    resolved_artifact = artifact.resolve(strict=True)
    if not resolved_artifact.is_relative_to(root):
        fail("artifact must be inside artifact_root")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": HANDLE_KIND,
        "artifact_kind": artifact_kind,
        "artifact_root": str(root),
        "artifact_path": str(resolved_artifact),
        "artifact_sha256": sha256(artifact_bytes),
        "byte_count": len(artifact_bytes),
        "command": require_text(command, "command"),
        "cwd": require_text(cwd, "cwd"),
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "observed_at": require_timestamp(observed_at, "observed_at"),
        "environment_identity": require_identity(
            environment_identity, "environment_identity"
        ),
        "commit": commit,
        "tree": tree,
    }


def verify_handle_object(
    raw_handle: Any, artifact_root: Path | None = None
) -> dict[str, Any]:
    handle = validate_handle(raw_handle)
    declared_root = Path(handle["artifact_root"])
    try:
        root = declared_root.resolve(strict=True)
    except OSError as error:
        fail(f"artifact_root could not be resolved: {error}")
    if declared_root.is_symlink() or not root.is_dir():
        fail("artifact_root must be an existing non-symlink directory")
    if artifact_root is not None:
        try:
            supplied_root = artifact_root.resolve(strict=True)
        except OSError as error:
            fail(f"artifact_root could not be resolved: {error}")
        if artifact_root.is_symlink() or supplied_root != root:
            fail("artifact_root does not match handle")
        root = supplied_root
    artifact = Path(handle["artifact_path"])
    try:
        resolved_artifact = artifact.resolve(strict=True)
    except OSError as error:
        fail(f"artifact could not be resolved: {error}")
    if not resolved_artifact.is_relative_to(root):
        fail("artifact escapes artifact_root")
    artifact_bytes = read_regular_file(artifact, "artifact")
    if len(artifact_bytes) != handle["byte_count"]:
        fail("artifact byte count does not match handle")
    if sha256(artifact_bytes) != handle["artifact_sha256"]:
        fail("artifact SHA-256 does not match handle")
    return handle


def verify_handle_file(
    handle_path: Path, artifact_root: Path | None = None
) -> dict[str, Any]:
    handle_bytes = read_regular_file(handle_path, "handle")
    return verify_handle_object(parse_json(handle_bytes, "handle"), artifact_root)


def publish_artifact_handle(
    *,
    artifact: Path,
    artifact_root: Path,
    output: Path,
    artifact_kind: str,
    command: str,
    cwd: str,
    exit_code: int,
    duration_ms: int,
    observed_at: str,
    environment_identity: str,
    commit: str | None = None,
    tree: str | None = None,
) -> dict[str, Any]:
    artifact_bytes = read_regular_file(artifact, "artifact")
    handle = create_handle(
        artifact,
        artifact_bytes,
        artifact_kind,
        command,
        cwd,
        exit_code,
        duration_ms,
        observed_at,
        environment_identity,
        commit,
        tree,
        artifact_root,
    )
    status = publish_once(output, canonical_json(handle), [artifact])
    return {
        "status": status,
        "kind": HANDLE_KIND,
        "artifact_sha256": handle["artifact_sha256"],
        "byte_count": handle["byte_count"],
    }


# --- Exploration Cache ---


def _validate_source_identities(value: Any, label: str) -> list[dict[str, str]]:
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


def _validate_conclusions(value: Any) -> list[dict[str, Any]]:
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
                    key=lambda entry: entry["path"].encode("utf-8"),
                ),
            }
        )
    return result


def _validate_text_array(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        fail(f"{label} must be an array")
    return [require_text(item, f"{label}[{index}]") for index, item in enumerate(value)]


def compute_exploration_cache_key(note: dict[str, Any]) -> str:
    material = {
        "question": note["question"],
        "scope": note["scope"],
        "source_identities": note["source_identities"],
        "target_identity": note["target_identity"],
        "environment_identity": note["environment_identity"],
    }
    return hashlib.sha256(canonical_json(material)).hexdigest()


def validate_exploration_note(payload: Any) -> dict[str, Any]:
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
        if actual != (expected | {"cache_key"}):
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
        "source_identities": _validate_source_identities(
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
        "invalidation_conditions": _validate_text_array(
            payload["invalidation_conditions"], "note.invalidation_conditions"
        ),
        "conclusions": _validate_conclusions(payload["conclusions"]),
        "limitations": _validate_text_array(payload["limitations"], "note.limitations"),
        "unresolved": _validate_text_array(payload["unresolved"], "note.unresolved"),
    }
    result["cache_key"] = compute_exploration_cache_key(result)
    if "cache_key" in payload and payload["cache_key"] != result["cache_key"]:
        fail("note.cache_key does not match its source identities")
    return result


def validate_exploration_context(payload: Any) -> dict[str, Any]:
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
    if (
        payload["schema_version"] != SCHEMA_VERSION
        or payload["kind"] != EXPLORATION_CONTEXT_KIND
    ):
        fail("context schema_version or kind is unsupported")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": EXPLORATION_CONTEXT_KIND,
        "question": require_text(payload["question"], "context.question"),
        "scope": set(
            require_string_array(payload["scope"], "context.scope", paths=True)
        ),
        "source_identities": _validate_source_identities(
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


def publish_exploration_note(note_path: Path, output_path: Path) -> dict[str, Any]:
    note_bytes = read_regular_file(note_path, "note")
    note = validate_exploration_note(parse_json(note_bytes, "note"))
    status = publish_once(output_path, canonical_json(note), [note_path])
    return {
        "status": status,
        "kind": NOTE_KIND,
        "cache_key": note["cache_key"],
    }


def publish_exploration_consumption(
    note_path: Path, context_path: Path, output_path: Path
) -> dict[str, Any]:
    note_bytes = read_regular_file(note_path, "note")
    note = validate_exploration_note(parse_json(note_bytes, "note"))
    context_bytes = read_regular_file(context_path, "context")
    context = validate_exploration_context(parse_json(context_bytes, "context"))
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
    status = publish_once(
        output_path, canonical_json(record), [note_path, context_path]
    )
    return {
        "status": status,
        "kind": CONSUMPTION_KIND,
        "cache_key": record["cache_key"],
    }


# --- Execution Checkpoint Records ---


def _validate_authorities(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        fail("capsule.authorities must be a non-empty array")
    result = []
    names = set()
    for index, item in enumerate(value):
        label = f"capsule.authorities[{index}]"
        item = require_object(item, label)
        require_exact_fields(item, {"name", "path", "identity"}, label)
        name = require_text(item["name"], f"{label}.name", safe_name=True)
        if name in names:
            fail(f"{label}.name is duplicated")
        names.add(name)
        result.append(
            {
                "name": name,
                "path": require_relative_path(item["path"], f"{label}.path"),
                "identity": require_identity(item["identity"], f"{label}.identity"),
            }
        )
    return result


def validate_obligation_refs(value: Any, label_prefix: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        fail(f"{label_prefix}.acceptance_obligations must be a non-empty array")
    result = []
    ids = set()
    for index, item in enumerate(value):
        label = f"{label_prefix}.acceptance_obligations[{index}]"
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


def validate_ticket_capsule(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "capsule")
    require_schema(payload, CAPSULE_KIND)
    expected = {
        "schema_version",
        "kind",
        "run_id",
        "ticket_id",
        "owner_id",
        "claim_generation",
        "workspace",
        "ticket_base",
        "definition_identity",
        "authorities",
        "scope",
        "acceptance_obligations",
        "required_gates",
        "permissions",
        "finalization_policy",
    }
    require_exact_fields(payload, expected, "capsule")
    result = {
        "schema_version": SCHEMA_VERSION,
        "kind": CAPSULE_KIND,
        "run_id": require_identity(payload["run_id"], "capsule.run_id"),
        "ticket_id": require_identity(payload["ticket_id"], "capsule.ticket_id"),
        "owner_id": require_identity(payload["owner_id"], "capsule.owner_id"),
        "claim_generation": require_integer(
            payload["claim_generation"], "capsule.claim_generation"
        ),
        "workspace": require_text(payload["workspace"], "capsule.workspace"),
        "ticket_base": validate_ticket_base(
            payload["ticket_base"], "capsule.ticket_base"
        ),
        "definition_identity": require_identity(
            payload["definition_identity"], "capsule.definition_identity"
        ),
        "authorities": _validate_authorities(payload["authorities"]),
        "scope": require_string_array(payload["scope"], "capsule.scope", paths=True),
        "acceptance_obligations": validate_obligation_refs(
            payload["acceptance_obligations"], "capsule"
        ),
        "required_gates": require_string_array(
            payload["required_gates"], "capsule.required_gates"
        ),
        "permissions": require_string_array(
            payload["permissions"], "capsule.permissions"
        ),
        "finalization_policy": require_text(
            payload["finalization_policy"],
            "capsule.finalization_policy",
            safe_name=True,
        ),
    }
    if result["finalization_policy"] not in FINALIZATION_POLICIES:
        fail("capsule.finalization_policy is unsupported")
    return result


def validate_resource_reservations(value: Any, label: str) -> list[dict[str, Any]]:
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
                "quantity": require_integer(
                    item["quantity"], f"{item_label}.quantity", minimum=1
                ),
                "mode": mode,
            }
        )
    return result


def _validate_checkpoint_evidence(value: Any, label: str) -> dict[str, Any]:
    value = require_object(value, label)
    expected = {
        "evidence_id",
        "type",
        "producer",
        "operation",
        "artifact_path",
        "artifact_sha256",
        "observed_result",
        "commit",
        "tree",
        "environment_identity",
        "applicability",
        "invalidation_reason",
    }
    require_exact_fields(value, expected, label)
    commit = value["commit"]
    tree = value["tree"]
    if commit is not None:
        commit = require_oid(commit, f"{label}.commit")
    if tree is not None:
        tree = require_oid(tree, f"{label}.tree")
    observed_result = require_text(
        value["observed_result"], f"{label}.observed_result", safe_name=True
    )
    if observed_result not in OBSERVED_RESULTS:
        fail(f"{label}.observed_result is unsupported")
    invalidation_reason = value["invalidation_reason"]
    if invalidation_reason is not None:
        invalidation_reason = require_text(
            invalidation_reason, f"{label}.invalidation_reason"
        )
    return {
        "evidence_id": require_identity(value["evidence_id"], f"{label}.evidence_id"),
        "type": require_text(value["type"], f"{label}.type", safe_name=True),
        "producer": require_identity(value["producer"], f"{label}.producer"),
        "operation": require_text(value["operation"], f"{label}.operation"),
        "artifact_path": require_relative_path(
            value["artifact_path"], f"{label}.artifact_path"
        ),
        "artifact_sha256": require_sha256(
            value["artifact_sha256"], f"{label}.artifact_sha256"
        ),
        "observed_result": observed_result,
        "commit": commit,
        "tree": tree,
        "environment_identity": require_identity(
            value["environment_identity"], f"{label}.environment_identity"
        ),
        "applicability": require_text(
            value["applicability"], f"{label}.applicability", safe_name=True
        ),
        "invalidation_reason": invalidation_reason,
    }


def _validate_findings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        fail("checkpoint.open_findings must be an array")
    result = []
    ids = set()
    for index, item in enumerate(value):
        label = f"checkpoint.open_findings[{index}]"
        item = require_object(item, label)
        require_exact_fields(item, {"id", "disposition", "evidence_ids"}, label)
        finding_id = require_identity(item["id"], f"{label}.id")
        if finding_id in ids:
            fail(f"{label}.id is duplicated")
        ids.add(finding_id)
        disposition = require_text(
            item["disposition"], f"{label}.disposition", safe_name=True
        )
        if disposition not in FINDING_DISPOSITIONS:
            fail(f"{label}.disposition is unsupported")
        result.append(
            {
                "id": finding_id,
                "disposition": disposition,
                "evidence_ids": require_string_array(
                    item["evidence_ids"], f"{label}.evidence_ids"
                ),
            }
        )
    return result


def _validate_metrics(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        fail("checkpoint.metrics must be an array")
    result = []
    metric_keys = set()
    for index, item in enumerate(value):
        label = f"checkpoint.metrics[{index}]"
        item = require_object(item, label)
        require_exact_fields(item, {"name", "value", "unit", "tags"}, label)
        name = require_text(item["name"], f"{label}.name", safe_name=True)
        if name not in METRIC_NAMES:
            fail(f"{label}.name is unsupported")
        metric_value = item["value"]
        if isinstance(metric_value, bool) or not isinstance(metric_value, (int, float)):
            fail(f"{label}.value must be a number")
        if not math.isfinite(metric_value) or metric_value < 0:
            fail(f"{label}.value must be finite and >= 0")
        tags = require_object(item["tags"], f"{label}.tags")
        normalized_tags = {}
        for tag_name, tag_value in tags.items():
            require_text(tag_name, f"{label}.tags key", safe_name=True)
            normalized_tags[tag_name] = require_text(
                tag_value, f"{label}.tags[{tag_name}]", safe_name=True
            )
        metric_key = (name, tuple(sorted(normalized_tags.items())))
        if metric_key in metric_keys:
            fail(f"{label} duplicates an existing metric with the same tags")
        metric_keys.add(metric_key)
        unit = require_text(item["unit"], f"{label}.unit", safe_name=True)
        if unit != METRIC_UNITS[name]:
            fail(f"{label}.unit must be {METRIC_UNITS[name]!r} for {name}")
        result.append(
            {
                "name": name,
                "value": metric_value,
                "unit": unit,
                "tags": normalized_tags,
            }
        )
    return result


def _validate_context_budget(value: Any) -> dict[str, Any]:
    value = require_object(value, "checkpoint.context_budget")
    require_exact_fields(
        value,
        {
            "dispatch_bytes",
            "retained_bytes",
            "handoff_bytes",
            "measurement_kind",
            "estimated",
        },
        "checkpoint.context_budget",
    )
    measurement_kind = require_text(
        value["measurement_kind"],
        "checkpoint.context_budget.measurement_kind",
        safe_name=True,
    )
    if measurement_kind not in CONTEXT_MEASUREMENT_KINDS:
        fail("checkpoint.context_budget.measurement_kind is unsupported")
    if type(value["estimated"]) is not bool:
        fail("checkpoint.context_budget.estimated must be boolean")
    return {
        "dispatch_bytes": require_integer(
            value["dispatch_bytes"], "checkpoint.context_budget.dispatch_bytes"
        ),
        "retained_bytes": require_integer(
            value["retained_bytes"], "checkpoint.context_budget.retained_bytes"
        ),
        "handoff_bytes": require_integer(
            value["handoff_bytes"], "checkpoint.context_budget.handoff_bytes"
        ),
        "measurement_kind": measurement_kind,
        "estimated": value["estimated"],
    }


def _validate_blocking_condition(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    value = require_object(value, "checkpoint.blocking_condition")
    require_exact_fields(
        value, {"kind", "owner", "recheck_event"}, "blocking_condition"
    )
    return {
        "kind": require_text(value["kind"], "blocking_condition.kind", safe_name=True),
        "owner": require_identity(value["owner"], "blocking_condition.owner"),
        "recheck_event": require_text(
            value["recheck_event"], "blocking_condition.recheck_event"
        ),
    }


def validate_execution_checkpoint(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "checkpoint")
    require_schema(payload, CHECKPOINT_KIND)
    expected = {
        "schema_version",
        "kind",
        "run_id",
        "ticket_id",
        "owner_id",
        "claim_generation",
        "workspace",
        "phase",
        "ticket_base",
        "changed_paths",
        "accepted_inputs",
        "candidate",
        "evidence_delta",
        "open_findings",
        "resource_claims",
        "next_action",
        "blocking_condition",
        "measurement_version",
        "metrics",
        "observed_at",
        "context_budget",
    }
    require_exact_fields(payload, expected, "checkpoint")
    phase = require_text(payload["phase"], "checkpoint.phase", safe_name=True)
    if phase not in PHASES:
        fail("checkpoint.phase is unsupported")
    accepted_inputs = payload["accepted_inputs"]
    if not isinstance(accepted_inputs, list):
        fail("checkpoint.accepted_inputs must be an array")
    normalized_inputs = []
    input_names = set()
    for index, item in enumerate(accepted_inputs):
        label = f"checkpoint.accepted_inputs[{index}]"
        item = require_object(item, label)
        require_exact_fields(item, {"name", "identity"}, label)
        name = require_text(item["name"], f"{label}.name", safe_name=True)
        if name in input_names:
            fail(f"{label}.name is duplicated")
        input_names.add(name)
        normalized_inputs.append(
            {
                "name": name,
                "identity": require_identity(item["identity"], f"{label}.identity"),
            }
        )
    candidate = payload["candidate"]
    if candidate is not None:
        candidate = require_object(candidate, "checkpoint.candidate")
        require_exact_fields(
            candidate, {"commit", "tree", "range"}, "checkpoint.candidate"
        )
        candidate = {
            "commit": require_oid(candidate["commit"], "checkpoint.candidate.commit"),
            "tree": require_oid(candidate["tree"], "checkpoint.candidate.tree"),
            "range": require_text(candidate["range"], "checkpoint.candidate.range"),
        }
    evidence = payload["evidence_delta"]
    if not isinstance(evidence, list):
        fail("checkpoint.evidence_delta must be an array")
    normalized_evidence = []
    evidence_ids = set()
    for index, item in enumerate(evidence):
        normalized = _validate_checkpoint_evidence(
            item, f"checkpoint.evidence_delta[{index}]"
        )
        if normalized["evidence_id"] in evidence_ids:
            fail("checkpoint.evidence_delta contains a duplicate evidence_id")
        evidence_ids.add(normalized["evidence_id"])
        normalized_evidence.append(normalized)
    measurement_version = require_integer(
        payload["measurement_version"], "checkpoint.measurement_version", minimum=1
    )
    if measurement_version != 1:
        fail("checkpoint.measurement_version is unsupported")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": CHECKPOINT_KIND,
        "run_id": require_identity(payload["run_id"], "checkpoint.run_id"),
        "ticket_id": require_identity(payload["ticket_id"], "checkpoint.ticket_id"),
        "owner_id": require_identity(payload["owner_id"], "checkpoint.owner_id"),
        "claim_generation": require_integer(
            payload["claim_generation"], "checkpoint.claim_generation"
        ),
        "workspace": require_text(payload["workspace"], "checkpoint.workspace"),
        "phase": phase,
        "ticket_base": validate_ticket_base(
            payload["ticket_base"], "checkpoint.ticket_base"
        ),
        "changed_paths": require_string_array(
            payload["changed_paths"], "checkpoint.changed_paths", paths=True
        ),
        "accepted_inputs": normalized_inputs,
        "candidate": candidate,
        "evidence_delta": normalized_evidence,
        "open_findings": _validate_findings(payload["open_findings"]),
        "resource_claims": validate_resource_reservations(
            payload["resource_claims"], "checkpoint.resource_claims"
        ),
        "next_action": require_text(payload["next_action"], "checkpoint.next_action"),
        "blocking_condition": _validate_blocking_condition(
            payload["blocking_condition"]
        ),
        "measurement_version": measurement_version,
        "metrics": _validate_metrics(payload["metrics"]),
        "observed_at": require_timestamp(
            payload["observed_at"], "checkpoint.observed_at"
        ),
        "context_budget": _validate_context_budget(payload["context_budget"]),
    }


def verify_artifact_paths(root: Path, evidence: list[dict[str, Any]]) -> None:
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as error:
        fail(f"artifact root could not be resolved: {error}")
    if root.is_symlink() or not resolved_root.is_dir():
        fail("artifact root must be a directory")
    for item in evidence:
        relative = PurePosixPath(item["artifact_path"])
        artifact = resolved_root.joinpath(*relative.parts)
        try:
            resolved = artifact.resolve(strict=True)
        except OSError as error:
            fail(f"evidence {item['evidence_id']} artifact is unavailable: {error}")
        if resolved != artifact:
            fail(f"evidence {item['evidence_id']} artifact path escapes its root")
        if artifact.is_symlink() or not artifact.is_file():
            fail(f"evidence {item['evidence_id']} artifact must be a regular file")
        actual = sha256(artifact.read_bytes())
        if actual != item["artifact_sha256"]:
            fail(f"evidence {item['evidence_id']} artifact digest does not match")


def validate_capsule_checkpoint_relationships(
    capsule: dict[str, Any], checkpoint: dict[str, Any]
) -> None:
    for field in ("run_id", "ticket_id", "owner_id", "claim_generation", "workspace"):
        if capsule[field] != checkpoint[field]:
            fail(f"capsule and checkpoint {field} do not match")
    if capsule["ticket_base"] != checkpoint["ticket_base"]:
        fail("capsule and checkpoint ticket_base do not match")
    if not all(
        any(path_contains(scope, changed) for scope in capsule["scope"])
        for changed in checkpoint["changed_paths"]
    ):
        fail("checkpoint.changed_paths must be within capsule.scope")


def publish_execution_record(
    capsule_path: Path, checkpoint_path: Path, artifact_root: Path, output_path: Path
) -> dict[str, Any]:
    capsule_bytes = read_regular_file(capsule_path, "capsule")
    checkpoint_bytes = read_regular_file(checkpoint_path, "checkpoint")
    capsule = validate_ticket_capsule(parse_json(capsule_bytes, "capsule"))
    checkpoint = validate_execution_checkpoint(
        parse_json(checkpoint_bytes, "checkpoint")
    )
    validate_capsule_checkpoint_relationships(capsule, checkpoint)
    verify_artifact_paths(artifact_root, checkpoint["evidence_delta"])
    if checkpoint["candidate"] is not None and checkpoint["phase"] in {
        "explore",
        "implement",
    }:
        fail("checkpoint.candidate is not allowed before verify, review, or promotion")
    record = {
        "schema_version": SCHEMA_VERSION,
        "kind": EXECUTION_RECORD_KIND,
        "run_id": checkpoint["run_id"],
        "ticket_id": checkpoint["ticket_id"],
        "owner_id": checkpoint["owner_id"],
        "claim_generation": checkpoint["claim_generation"],
        "phase": checkpoint["phase"],
        "checkpoint_ref": {
            "path": str(checkpoint_path.resolve()),
            "sha256": sha256(checkpoint_bytes),
        },
        "capsule_ref": {
            "path": str(capsule_path.resolve()),
            "sha256": sha256(capsule_bytes),
        },
        "ticket_base": checkpoint["ticket_base"],
        "candidate": checkpoint["candidate"],
        "evidence_ids": [item["evidence_id"] for item in checkpoint["evidence_delta"]],
        "metrics": checkpoint["metrics"],
        "context_budget": checkpoint["context_budget"],
        "measurement_version": checkpoint["measurement_version"],
        "observed_at": checkpoint["observed_at"],
        "capsule_definition_identity": capsule["definition_identity"],
    }
    status = publish_once(
        output_path, canonical_json(record), [capsule_path, checkpoint_path]
    )
    return {
        "status": status,
        "kind": EXECUTION_RECORD_KIND,
        "run_id": record["run_id"],
        "ticket_id": record["ticket_id"],
        "claim_generation": record["claim_generation"],
        "output": str(output_path.resolve()),
        "checkpoint_sha256": record["checkpoint_ref"]["sha256"],
        "capsule_sha256": record["capsule_ref"]["sha256"],
        "metric_count": len(record["metrics"]),
    }


def _validate_path_sha_ref(value: Any, label: str) -> tuple[Path, str]:
    value = require_object(value, label)
    require_exact_fields(value, {"path", "sha256"}, label)
    path = Path(require_text(value["path"], f"{label}.path"))
    digest = require_sha256(value["sha256"], f"{label}.sha256")
    return path, digest


def validate_execution_record(
    record_path: Path, artifact_root: Path
) -> tuple[dict[str, Any], str, dict[str, Any], dict[str, Any]]:
    record_bytes = read_regular_file(record_path, "record")
    record = require_object(parse_json(record_bytes, "record"), "record")
    require_exact_fields(record, EXECUTION_RECORD_FIELDS, "record")
    if record["schema_version"] != 1 or record["kind"] != EXECUTION_RECORD_KIND:
        fail("record schema_version or kind is unsupported")
    record_run_id = require_identity(record["run_id"], "record.run_id")
    ticket_id = require_identity(record["ticket_id"], "record.ticket_id")
    owner_id = require_identity(record["owner_id"], "record.owner_id")
    claim_generation = require_integer(
        record["claim_generation"], "record.claim_generation"
    )
    phase = require_text(record["phase"], "record.phase", safe_name=True)
    observed_at = require_text(record["observed_at"], "record.observed_at")
    checkpoint_path, checkpoint_digest = _validate_path_sha_ref(
        record["checkpoint_ref"], "record.checkpoint_ref"
    )
    capsule_path, capsule_digest = _validate_path_sha_ref(
        record["capsule_ref"], "record.capsule_ref"
    )
    if checkpoint_path.resolve() == record_path.resolve():
        fail("record must be distinct from its checkpoint")
    if capsule_path.resolve() == record_path.resolve():
        fail("record must be distinct from its capsule")
    checkpoint_bytes = read_regular_file(checkpoint_path, "checkpoint")
    capsule_bytes = read_regular_file(capsule_path, "capsule")
    if sha256(checkpoint_bytes) != checkpoint_digest:
        fail("record checkpoint SHA-256 does not match")
    if sha256(capsule_bytes) != capsule_digest:
        fail("record capsule SHA-256 does not match")
    checkpoint = validate_execution_checkpoint(
        parse_json(checkpoint_bytes, "checkpoint")
    )
    capsule = validate_ticket_capsule(parse_json(capsule_bytes, "capsule"))
    validate_capsule_checkpoint_relationships(capsule, checkpoint)
    if record_run_id != checkpoint["run_id"] or record_run_id != capsule["run_id"]:
        fail("record, checkpoint, and capsule run_id do not match")
    if ticket_id != checkpoint["ticket_id"] or ticket_id != capsule["ticket_id"]:
        fail("record, checkpoint, and capsule ticket_id do not match")
    if owner_id != checkpoint["owner_id"] or owner_id != capsule["owner_id"]:
        fail("record, checkpoint, and capsule owner_id do not match")
    if claim_generation != checkpoint["claim_generation"]:
        fail("record and checkpoint claim_generation do not match")
    if phase != checkpoint["phase"]:
        fail("record and checkpoint phase do not match")
    if observed_at != checkpoint["observed_at"]:
        fail("record and checkpoint observed_at do not match")
    verify_artifact_paths(artifact_root, checkpoint["evidence_delta"])
    return record, sha256(record_bytes), capsule, checkpoint


def commit_execution_record(
    receipt_path: Path,
    record_path: Path,
    artifact_root: Path,
    expected_generation: int,
    expected_receipt_digest: str,
) -> dict[str, Any]:
    expected_receipt_digest = require_sha256(
        expected_receipt_digest, "expected_receipt_sha256"
    )
    with receipt_lock(receipt_path):
        safe_receipt_target(receipt_path)
        receipt_bytes = read_regular_file(receipt_path, "receipt")
        if sha256(receipt_bytes) != expected_receipt_digest:
            fail("receipt SHA-256 does not match")
        receipt = validate_receipt(parse_json(receipt_bytes, "receipt"))
        if receipt["coordinator_generation"] != expected_generation:
            fail("receipt coordinator_generation does not match")
        record, record_digest, _capsule, _checkpoint = validate_execution_record(
            record_path, artifact_root
        )
        if receipt["run_id"] != record["run_id"]:
            fail("receipt and record run_id do not match")
        _cp_path, checkpoint_digest = _validate_path_sha_ref(
            record["checkpoint_ref"], "record.checkpoint_ref"
        )
        _cap_path, capsule_digest = _validate_path_sha_ref(
            record["capsule_ref"], "record.capsule_ref"
        )
        entry = {
            "ticket_id": record["ticket_id"],
            "owner_id": record["owner_id"],
            "claim_generation": record["claim_generation"],
            "phase": record["phase"],
            "record_path": str(record_path.resolve()),
            "record_sha256": record_digest,
            "checkpoint_sha256": checkpoint_digest,
            "capsule_sha256": capsule_digest,
            "observed_at": record["observed_at"],
        }
        key = (entry["ticket_id"], entry["claim_generation"])
        for current in receipt["execution_records"]:
            if (current["ticket_id"], current["claim_generation"]) != key:
                continue
            if current != entry:
                fail("receipt already contains a different record for this claim")
            return {
                "status": "already-indexed",
                "kind": RECEIPT_KIND,
                "ticket_id": entry["ticket_id"],
                "claim_generation": entry["claim_generation"],
                "record_sha256": entry["record_sha256"],
                "coordinator_generation": expected_generation,
                "receipt_sha256": expected_receipt_digest,
            }
        receipt["execution_records"].append(entry)
        receipt["coordinator_generation"] += 1
        new_bytes = canonical_json(receipt)
        replace_receipt(receipt_path, receipt_bytes, new_bytes, locked=True)
        return {
            "status": "indexed",
            "kind": RECEIPT_KIND,
            "ticket_id": entry["ticket_id"],
            "claim_generation": entry["claim_generation"],
            "record_sha256": entry["record_sha256"],
            "coordinator_generation": receipt["coordinator_generation"],
            "receipt_sha256": sha256(new_bytes),
        }


# --- Review Context Capsule & Candidate Review Record ---


def _validate_identity_refs(value: Any, label: str) -> list[dict[str, str]]:
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


def _validate_optional_file_refs(value: Any, label: str) -> list[dict[str, str]]:
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
        declared = require_sha256(item["sha256"], f"{item_label}.sha256")
        actual = read_regular_file(path, f"{item_label}.path")
        if sha256(actual) != declared:
            fail(f"{item_label}.path SHA-256 does not match")
        result.append({"id": ref_id, "path": str(path.resolve()), "sha256": declared})
    return result


def _validate_review_candidate(value: Any) -> dict[str, Any]:
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


def validate_review_context(payload: Any) -> dict[str, Any]:
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
    if (
        payload["schema_version"] != SCHEMA_VERSION
        or payload["kind"] != REVIEW_INPUT_KIND
    ):
        fail("context schema_version or kind is unsupported")
    base = validate_ticket_base(payload["ticket_base"], "context.ticket_base")
    candidate = _validate_review_candidate(payload["candidate"])
    if base["commit"] == candidate["commit"]:
        fail("context candidate must differ from ticket_base")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": REVIEW_INPUT_KIND,
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
        "acceptance_obligations": validate_obligation_refs(
            payload["acceptance_obligations"], "context"
        ),
        "required_gates": _validate_identity_refs(
            payload["required_gates"], "context.required_gates"
        ),
        "evidence_refs": _validate_optional_file_refs(
            payload["evidence_refs"], "context.evidence_refs"
        ),
        "exploration_refs": _validate_optional_file_refs(
            payload["exploration_refs"], "context.exploration_refs"
        ),
    }


def compute_review_context_key(context: dict[str, Any]) -> str:
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


def validate_review_capsule(payload: Any) -> dict[str, Any]:
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
    if (
        payload["kind"] != REVIEW_CAPSULE_KIND
        or payload["fresh_review_required"] is not True
    ):
        fail("capsule kind or fresh_review_required is invalid")
    context_payload = {
        key: payload[key]
        for key in expected
        if key not in {"kind", "fresh_review_required", "review_context_key"}
    }
    context_payload["kind"] = REVIEW_INPUT_KIND
    context = validate_review_context(context_payload)
    expected_key = compute_review_context_key(context)
    if payload["review_context_key"] != expected_key:
        fail("capsule.review_context_key does not match its identities")
    return {
        **context,
        "kind": REVIEW_CAPSULE_KIND,
        "fresh_review_required": True,
        "review_context_key": expected_key,
    }


def publish_review_context(context_path: Path, output_path: Path) -> dict[str, Any]:
    context_bytes = read_regular_file(context_path, "context")
    context = validate_review_context(parse_json(context_bytes, "context"))
    capsule = {
        **context,
        "kind": REVIEW_CAPSULE_KIND,
        "fresh_review_required": True,
        "review_context_key": compute_review_context_key(context),
    }
    status = publish_once(output_path, canonical_json(capsule), [context_path])
    return {
        "status": status,
        "kind": REVIEW_CAPSULE_KIND,
        "review_context_key": capsule["review_context_key"],
        "fresh_review_required": True,
    }


def compute_review_record_key(capsule: dict[str, Any], handle: dict[str, Any]) -> str:
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


def publish_candidate_review(
    context_capsule_path: Path,
    review_handle_path: Path,
    artifact_root: Path,
    output_path: Path,
) -> dict[str, Any]:
    capsule_bytes = read_regular_file(context_capsule_path, "context capsule")
    capsule = validate_review_capsule(parse_json(capsule_bytes, "context capsule"))
    handle = verify_handle_file(review_handle_path, artifact_root)
    if handle["artifact_kind"] not in {"review-report", "tool-output"}:
        fail("review handle artifact_kind must be review-report or tool-output")
    record = {
        "schema_version": SCHEMA_VERSION,
        "kind": CANDIDATE_REVIEW_KIND,
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
        "review_record_key": compute_review_record_key(capsule, handle),
    }
    status = publish_once(
        output_path,
        canonical_json(record),
        [context_capsule_path, review_handle_path],
    )
    return {
        "status": status,
        "kind": CANDIDATE_REVIEW_KIND,
        "review_record_key": record["review_record_key"],
        "fresh_review_required": True,
    }


def verify_candidate_review(
    record_path: Path,
    context_path: Path,
    artifact_root: Path,
    expected_base_commit: str,
    expected_base_tree: str,
    expected_candidate_commit: str,
    expected_candidate_tree: str,
    expected_candidate_range: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    record_bytes = read_regular_file(record_path, "review record")
    record = require_object(parse_json(record_bytes, "review record"), "review record")
    require_exact_fields(record, CANDIDATE_REVIEW_FIELDS, "review record")
    if record["schema_version"] != 1 or record["kind"] != CANDIDATE_REVIEW_KIND:
        fail("review record schema_version or kind is unsupported")
    if record["fresh_review_required"] is not True:
        fail("review record fresh_review_required must be true")
    capsule = validate_review_capsule(
        parse_json(
            read_regular_file(context_path, "context capsule"), "context capsule"
        )
    )
    handle = verify_handle_object(record["review_artifact"], artifact_root)
    if handle["artifact_kind"] not in {"review-report", "tool-output"}:
        fail("review handle artifact_kind is not review-capable")
    for field in (
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
        "review_context_key",
    ):
        if record[field] != capsule[field]:
            fail(f"review record and capsule {field} do not match")
    expected_key = compute_review_record_key(capsule, handle)
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
    summary = {
        "status": "verified",
        "kind": CANDIDATE_REVIEW_KIND,
        "run_id": record["run_id"],
        "ticket_id": record["ticket_id"],
        "owner_id": record["owner_id"],
        "claim_generation": record["claim_generation"],
        "review_context_key": record["review_context_key"],
        "review_record_key": record["review_record_key"],
        "fresh_review_required": True,
    }
    return summary, handle
