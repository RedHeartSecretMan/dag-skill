#!/usr/bin/env python3
"""Publish or verify a content-addressed tool-output Artifact Handle."""

from __future__ import annotations

import argparse
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
    require_sha256,
    require_text,
    require_timestamp,
    sha256,
)

SCHEMA_VERSION = 1
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


def fail(message: str) -> None:
    raise RecordError(message)


def validate_handle(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        fail("handle must be a JSON object")
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


def verify_handle(
    handle_path: Path, artifact_root: Path | None = None
) -> dict[str, Any]:
    handle_bytes = read_regular_file(handle_path, "handle")
    handle = validate_handle(parse_json(handle_bytes, "handle"))
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
        if supplied_root != root:
            fail("artifact_root does not match handle")
        root = supplied_root
    artifact = Path(handle["artifact_path"])
    if not artifact.resolve(strict=True).is_relative_to(root):
        fail("artifact escapes artifact_root")
    artifact_bytes = read_regular_file(artifact, "artifact")
    if len(artifact_bytes) != handle["byte_count"]:
        fail("artifact byte count does not match handle")
    if sha256(artifact_bytes) != handle["artifact_sha256"]:
        fail("artifact SHA-256 does not match handle")
    return handle


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish or verify a content-addressed tool-output Artifact Handle."
    )
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--artifact-kind", choices=sorted(ARTIFACT_KINDS))
    parser.add_argument("--command")
    parser.add_argument("--cwd")
    parser.add_argument("--exit-code", type=int)
    parser.add_argument("--duration-ms", type=int)
    parser.add_argument("--observed-at")
    parser.add_argument("--environment-identity")
    parser.add_argument("--commit")
    parser.add_argument("--tree")
    arguments = parser.parse_args()
    try:
        if arguments.verify is not None:
            if any(
                value is not None
                for value in (
                    arguments.artifact,
                    arguments.output,
                    arguments.artifact_kind,
                    arguments.command,
                    arguments.cwd,
                    arguments.exit_code,
                    arguments.duration_ms,
                    arguments.observed_at,
                    arguments.environment_identity,
                    arguments.commit,
                    arguments.tree,
                )
            ):
                fail("--verify cannot be combined with publication options")
            handle = verify_handle(arguments.verify, arguments.artifact_root)
            result = {
                "status": "verified",
                "kind": HANDLE_KIND,
                "artifact_sha256": handle["artifact_sha256"],
                "byte_count": handle["byte_count"],
            }
        else:
            required = {
                "--artifact": arguments.artifact,
                "--output": arguments.output,
                "--artifact-kind": arguments.artifact_kind,
                "--command": arguments.command,
                "--cwd": arguments.cwd,
                "--exit-code": arguments.exit_code,
                "--duration-ms": arguments.duration_ms,
                "--observed-at": arguments.observed_at,
                "--environment-identity": arguments.environment_identity,
            }
            missing = [name for name, value in required.items() if value is None]
            if missing:
                fail(f"missing publication options: {', '.join(missing)}")
            artifact_bytes = read_regular_file(arguments.artifact, "artifact")
            handle = create_handle(
                arguments.artifact,
                artifact_bytes,
                arguments.artifact_kind,
                arguments.command,
                arguments.cwd,
                arguments.exit_code,
                arguments.duration_ms,
                arguments.observed_at,
                arguments.environment_identity,
                arguments.commit,
                arguments.tree,
                arguments.artifact_root,
            )
            status = publish_once(
                arguments.output, canonical_json(handle), [arguments.artifact]
            )
            result = {
                "status": status,
                "kind": HANDLE_KIND,
                "artifact_sha256": handle["artifact_sha256"],
                "byte_count": handle["byte_count"],
            }
    except (OSError, RecordError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
