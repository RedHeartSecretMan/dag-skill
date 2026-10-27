#!/usr/bin/env python3
"""Validate and atomically publish one Execution Checkpoint shadow record."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = 1
CHECKPOINT_KIND = "Execution Checkpoint"
CAPSULE_KIND = "Ticket Capsule"
RECORD_KIND = "Execution Checkpoint Record"
OID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}\Z")
PHASES = {"explore", "implement", "verify", "review", "promotion", "blocked"}
FINALIZATION_POLICIES = {"serial", "deferred"}
FINDING_DISPOSITIONS = {"open", "resolved", "deferred"}
OBSERVED_RESULTS = {"pass", "fail", "unknown", "not-run"}
RESOURCE_MODES = {"shared", "exclusive"}
CONTEXT_MEASUREMENT_KINDS = {"bytes", "characters", "tokens"}
METRIC_NAMES = {
    "dispatch.input_bytes",
    "handoff.input_bytes",
    "tool.output_bytes",
    "tool.retained_bytes",
    "phase.duration_ms",
    "resource.agent_slots",
    "resource.runtime_skill_slots",
    "wait.duration_ms",
    "rework.count",
    "wall_clock_ms",
}
METRIC_UNITS = {
    "dispatch.input_bytes": "bytes",
    "handoff.input_bytes": "bytes",
    "tool.output_bytes": "bytes",
    "tool.retained_bytes": "bytes",
    "phase.duration_ms": "ms",
    "resource.agent_slots": "slots",
    "resource.runtime_skill_slots": "slots",
    "wait.duration_ms": "ms",
    "rework.count": "count",
    "wall_clock_ms": "ms",
}


class RecordError(RuntimeError):
    """A deterministic, user-actionable record validation failure."""


def fail(message: str) -> None:
    raise RecordError(message)


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value


def require_exact_fields(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        details = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if unknown:
            details.append(f"unknown {', '.join(unknown)}")
        fail(f"{label} fields are invalid: {'; '.join(details)}")


def require_text(value: Any, label: str, *, safe_name: bool = False) -> str:
    if not isinstance(value, str) or not value or "\0" in value:
        fail(f"{label} must be a non-empty string")
    if "\r" in value or "\n" in value:
        fail(f"{label} must not contain line breaks")
    if len(value) > 4096:
        fail(f"{label} is too long")
    if safe_name and SAFE_NAME.fullmatch(value) is None:
        fail(f"{label} contains unsupported characters")
    return value


def require_integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        fail(f"{label} must be an integer >= {minimum}")
    return value


def require_oid(value: Any, label: str) -> str:
    if not isinstance(value, str) or OID.fullmatch(value) is None:
        fail(f"{label} must be a lowercase 40- or 64-character Git object id")
    return value


def require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA256.fullmatch(value) is None:
        fail(f"{label} must be 64 lowercase hexadecimal characters")
    return value


def require_identity(value: Any, label: str) -> str:
    return require_text(value, label, safe_name=True)


def require_timestamp(value: Any, label: str) -> str:
    value = require_text(value, label)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"{label} must be an ISO-8601 timestamp: {error}")
    if parsed.tzinfo is None:
        fail(f"{label} must include a timezone")
    return value


def require_relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\0" in value:
        fail(f"{label} must be a non-empty repository-relative path")
    if unicodedata.normalize("NFC", value) != value:
        fail(f"{label} must use NFC-normalized text")
    if value.startswith("/") or value.endswith("/"):
        fail(f"{label} must be relative and must not end with '/'")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        fail(f"{label} contains an unsafe path component")
    if PurePosixPath(value).as_posix() != value:
        fail(f"{label} is not a normalized POSIX path")
    return value


def require_string_array(value: Any, label: str, *, paths: bool = False) -> list[str]:
    if not isinstance(value, list):
        fail(f"{label} must be an array")
    result = []
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        result.append(
            require_relative_path(item, item_label)
            if paths
            else require_text(item, item_label, safe_name=True)
        )
    if len(result) != len(set(result)):
        fail(f"{label} must not contain duplicates")
    return result


def require_schema(value: dict[str, Any], kind: str) -> None:
    if "schema_version" not in value or "kind" not in value:
        fail("record header must contain schema_version and kind")
    if value["schema_version"] != SCHEMA_VERSION:
        fail(f"schema_version must be the integer {SCHEMA_VERSION}")
    if value["kind"] != kind:
        fail(f"kind must be {kind!r}")


def validate_ticket_base(value: Any, label: str = "ticket_base") -> dict[str, str]:
    value = require_object(value, label)
    require_exact_fields(value, {"commit", "tree"}, label)
    return {
        "commit": require_oid(value["commit"], f"{label}.commit"),
        "tree": require_oid(value["tree"], f"{label}.tree"),
    }


def validate_authorities(value: Any) -> list[dict[str, str]]:
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


def validate_obligations(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        fail("capsule.acceptance_obligations must be a non-empty array")
    result = []
    ids = set()
    for index, item in enumerate(value):
        label = f"capsule.acceptance_obligations[{index}]"
        item = require_object(item, label)
        require_exact_fields(item, {"id", "source", "identity"}, label)
        obligation_id = require_text(item["id"], f"{label}.id", safe_name=True)
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


def validate_capsule(payload: Any) -> dict[str, Any]:
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
        "authorities": validate_authorities(payload["authorities"]),
        "scope": require_string_array(payload["scope"], "capsule.scope", paths=True),
        "acceptance_obligations": validate_obligations(
            payload["acceptance_obligations"]
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


def validate_evidence(value: Any, label: str) -> dict[str, Any]:
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


def validate_findings(value: Any) -> list[dict[str, Any]]:
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


def validate_resources(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        fail("checkpoint.resource_claims must be an array")
    result = []
    names = set()
    for index, item in enumerate(value):
        label = f"checkpoint.resource_claims[{index}]"
        item = require_object(item, label)
        require_exact_fields(item, {"resource", "quantity", "mode"}, label)
        resource = require_text(item["resource"], f"{label}.resource", safe_name=True)
        if resource in names:
            fail(f"{label}.resource is duplicated")
        names.add(resource)
        mode = require_text(item["mode"], f"{label}.mode", safe_name=True)
        if mode not in RESOURCE_MODES:
            fail(f"{label}.mode is unsupported")
        result.append(
            {
                "resource": resource,
                "quantity": require_integer(item["quantity"], f"{label}.quantity"),
                "mode": mode,
            }
        )
    return result


def validate_metrics(value: Any) -> list[dict[str, Any]]:
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


def validate_context_budget(value: Any) -> dict[str, Any]:
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


def validate_blocking_condition(value: Any) -> dict[str, str] | None:
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


def validate_checkpoint(payload: Any) -> dict[str, Any]:
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
        normalized = validate_evidence(item, f"checkpoint.evidence_delta[{index}]")
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
        "open_findings": validate_findings(payload["open_findings"]),
        "resource_claims": validate_resources(payload["resource_claims"]),
        "next_action": require_text(payload["next_action"], "checkpoint.next_action"),
        "blocking_condition": validate_blocking_condition(
            payload["blocking_condition"]
        ),
        "measurement_version": measurement_version,
        "metrics": validate_metrics(payload["metrics"]),
        "observed_at": require_timestamp(
            payload["observed_at"], "checkpoint.observed_at"
        ),
        "context_budget": validate_context_budget(payload["context_budget"]),
    }


def read_regular_file(path: Path, label: str) -> bytes:
    try:
        path.lstat()
    except OSError as error:
        fail(f"{label} could not be read: {error}")
    if not path.is_file() or path.is_symlink():
        fail(f"{label} must be a regular non-symlink file")
    try:
        return path.read_bytes()
    except OSError as error:
        fail(f"{label} could not be read: {error}")


def parse_json(content: bytes, label: str) -> Any:
    try:
        return json.loads(content.decode("utf-8"), object_pairs_hook=unique_json_object)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecordError,
        RecursionError,
    ) as error:
        fail(f"{label} is not valid UTF-8 JSON: {error}")


def unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def verify_artifact_paths(root: Path, evidence: list[dict[str, Any]]) -> None:
    try:
        root = root.resolve(strict=True)
    except OSError as error:
        fail(f"artifact root could not be resolved: {error}")
    if not root.is_dir():
        fail("artifact root must be a directory")
    for item in evidence:
        relative = PurePosixPath(item["artifact_path"])
        artifact = root.joinpath(*relative.parts)
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


def validate_relationships(capsule: dict[str, Any], checkpoint: dict[str, Any]) -> None:
    for field in ("run_id", "ticket_id", "owner_id", "claim_generation", "workspace"):
        if capsule[field] != checkpoint[field]:
            fail(f"capsule and checkpoint {field} do not match")
    if capsule["ticket_base"] != checkpoint["ticket_base"]:
        fail("capsule and checkpoint ticket_base do not match")
    if not set(checkpoint["changed_paths"]).issubset(set(capsule["scope"])):
        fail("checkpoint.changed_paths must be within capsule.scope")


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def safe_output_path(path: Path, inputs: list[Path]) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        metadata = None
    except OSError as error:
        fail(f"output could not be inspected: {error}")
    if metadata is not None:
        if path.is_symlink() or not path.is_file():
            fail("output must be a regular non-symlink file")
        if metadata.st_nlink != 1:
            fail("output must not be a hardlink")
    if any(
        path.resolve(strict=False) == input_path.resolve(strict=False)
        for input_path in inputs
    ):
        fail("output must be different from every input")
    parent = path.parent
    if not parent.is_dir() or parent.is_symlink():
        fail("output parent must be an existing non-symlink directory")


def publish_once(path: Path, content: bytes, inputs: list[Path]) -> str:
    safe_output_path(path, inputs)
    if path.exists():
        existing = read_regular_file(path, "output")
        if existing != content:
            fail("output already exists with different content")
        return "already-published"

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.tmp-", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError as error:
            fail(f"output appeared during publication: {error}")
        directory_descriptor = os.open(
            path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        )
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
        return "published"
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def create_record(
    capsule_path: Path,
    capsule_bytes: bytes,
    capsule: dict[str, Any],
    checkpoint_path: Path,
    checkpoint_bytes: bytes,
    checkpoint: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": RECORD_KIND,
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


def record_checkpoint(
    capsule_path: Path, checkpoint_path: Path, output_path: Path, artifact_root: Path
) -> tuple[str, dict[str, Any]]:
    capsule_bytes = read_regular_file(capsule_path, "capsule")
    checkpoint_bytes = read_regular_file(checkpoint_path, "checkpoint")
    capsule = validate_capsule(parse_json(capsule_bytes, "capsule"))
    checkpoint = validate_checkpoint(parse_json(checkpoint_bytes, "checkpoint"))
    validate_relationships(capsule, checkpoint)
    verify_artifact_paths(artifact_root, checkpoint["evidence_delta"])
    if checkpoint["candidate"] is not None and checkpoint["phase"] in {
        "explore",
        "implement",
    }:
        fail("checkpoint.candidate is not allowed before verify, review, or promotion")
    record = create_record(
        capsule_path,
        capsule_bytes,
        capsule,
        checkpoint_path,
        checkpoint_bytes,
        checkpoint,
    )
    record_bytes = canonical_json(record)
    status = publish_once(output_path, record_bytes, [capsule_path, checkpoint_path])
    return status, record


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and atomically publish one Execution Checkpoint shadow record."
    )
    parser.add_argument("--capsule", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        status, record = record_checkpoint(
            arguments.capsule,
            arguments.checkpoint,
            arguments.output,
            arguments.artifact_root,
        )
    except (OSError, RecordError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    result = {
        "status": status,
        "kind": RECORD_KIND,
        "run_id": record["run_id"],
        "ticket_id": record["ticket_id"],
        "claim_generation": record["claim_generation"],
        "output": str(arguments.output.resolve()),
        "checkpoint_sha256": record["checkpoint_ref"]["sha256"],
        "capsule_sha256": record["capsule_ref"]["sha256"],
        "metric_count": len(record["metrics"]),
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
