"""Core schema validation, JSON decoding, hashing, and atomic file publication primitives."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

MINIMUM_PYTHON = (3, 12)
SCHEMA_VERSION = 1
MAX_JSON_INTEGER_DIGITS = 20
OID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}\Z")
PHASES = {"explore", "implement", "verify", "review", "promotion", "blocked"}
ADMITTABLE_PHASES = {"explore", "implement", "verify", "review", "promotion"}
LANE_NAMES = {"build-review", "promotion"}
FINALIZATION_POLICIES = {"serial", "deferred"}
FINDING_DISPOSITIONS = {"open", "resolved", "deferred"}
OBSERVED_RESULTS = {"pass", "fail", "unknown", "not-run"}
RESOURCE_MODES = {"shared", "exclusive"}
CONTEXT_MEASUREMENT_KINDS = {"bytes", "characters", "tokens"}
DISPOSITIONS = {"Accepted", "Superseded"}
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

MACOS_SYSTEM_PATH_ALIASES = {
    Path("/tmp"): Path("/private/tmp"),
    Path("/var"): Path("/private/var"),
}


class RecordError(RuntimeError):
    """A deterministic, user-actionable validation or CAS failure."""


def fail(message: str) -> None:
    raise RecordError(message)


def require_supported_python(version: tuple[int, int] | None = None) -> None:
    current = version or sys.version_info[:2]
    if current < MINIMUM_PYTHON:
        minimum = ".".join(str(part) for part in MINIMUM_PYTHON)
        actual = ".".join(str(part) for part in current)
        fail(f"Python {minimum}+ is required (running {actual})")


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


def path_contains(parent: str, child: str) -> bool:
    return parent == child or child.startswith(f"{parent}/")


def paths_overlap(left: str, right: str) -> bool:
    return path_contains(left, right) or path_contains(right, left)


def sort_paths(paths: list[str]) -> list[str]:
    return sorted(paths, key=lambda item: item.encode("utf-8"))


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


def parse_integer(value: str) -> int:
    if len(value.lstrip("-")) > MAX_JSON_INTEGER_DIGITS:
        raise ValueError("JSON integer is oversized")
    return int(value)


def unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def parse_json(content: bytes, label: str) -> Any:
    try:
        return json.loads(
            content.decode("utf-8"),
            object_pairs_hook=unique_json_object,
            parse_int=parse_integer,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        RecordError,
        RecursionError,
    ) as error:
        fail(f"{label} is not valid UTF-8 JSON: {error}")


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def is_allowed_system_path_alias(path: Path) -> bool:
    if sys.platform != "darwin" or not path.is_symlink():
        return False
    target = MACOS_SYSTEM_PATH_ALIASES.get(path)
    return target is not None and path.resolve(strict=False) == target


def ensure_no_symlink_ancestors(path: Path, label: str) -> None:
    current = path.absolute().parent
    while True:
        try:
            if current.is_symlink() and not is_allowed_system_path_alias(current):
                fail(f"{label} parent hierarchy must not contain symlinks")
        except OSError as error:
            fail(f"{label} parent could not be inspected: {error}")
        if current.parent == current:
            break
        current = current.parent


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
    ensure_no_symlink_ancestors(path, "output")
    parent = path.parent
    if not parent.is_dir() or (
        parent.is_symlink() and not is_allowed_system_path_alias(parent)
    ):
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


def print_json(result: dict[str, Any]) -> None:
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
