#!/usr/bin/env python3
"""CAS-index one validated Execution Checkpoint Record into a Run Receipt."""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

from record_execution_checkpoint import (
    RECORD_KIND,
    RecordError,
    canonical_json,
    parse_json,
    read_regular_file,
    require_exact_fields,
    require_identity,
    require_integer,
    require_sha256,
    require_text,
    sha256,
    validate_capsule,
    validate_checkpoint,
    validate_relationships,
    verify_artifact_paths,
)

RECEIPT_SCHEMA_VERSION = 1
RECEIPT_KIND = "Run Receipt"
RECEIPT_REQUIRED_FIELDS = {
    "schema_version",
    "kind",
    "run_id",
    "coordinator_generation",
}
INDEX_ENTRY_FIELDS = {
    "ticket_id",
    "owner_id",
    "claim_generation",
    "phase",
    "record_path",
    "record_sha256",
    "checkpoint_sha256",
    "capsule_sha256",
    "observed_at",
}
RECORD_FIELDS = {
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


class IndexError(RuntimeError):
    """A deterministic, user-actionable Run Receipt indexing failure."""


def fail(message: str) -> None:
    raise IndexError(message)


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value


def validate_receipt(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "receipt")
    if not RECEIPT_REQUIRED_FIELDS.issubset(payload):
        missing = sorted(RECEIPT_REQUIRED_FIELDS - set(payload))
        fail(f"receipt is missing fields: {', '.join(missing)}")
    if payload["schema_version"] != RECEIPT_SCHEMA_VERSION:
        fail(f"receipt schema_version must be {RECEIPT_SCHEMA_VERSION}")
    if payload["kind"] != RECEIPT_KIND:
        fail(f"receipt kind must be {RECEIPT_KIND!r}")
    run_id = require_identity(payload["run_id"], "receipt.run_id")
    generation = require_integer(
        payload["coordinator_generation"], "receipt.coordinator_generation"
    )
    records = payload.get("execution_records", [])
    if not isinstance(records, list):
        fail("receipt.execution_records must be an array")
    normalized_records = []
    identities: set[tuple[str, int]] = set()
    for index, item in enumerate(records):
        label = f"receipt.execution_records[{index}]"
        item = require_object(item, label)
        require_exact_fields(item, INDEX_ENTRY_FIELDS, label)
        ticket_id = require_identity(item["ticket_id"], f"{label}.ticket_id")
        claim_generation = require_integer(
            item["claim_generation"], f"{label}.claim_generation"
        )
        identity = (ticket_id, claim_generation)
        if identity in identities:
            fail(f"{label} duplicates a ticket and claim generation")
        identities.add(identity)
        normalized_records.append(
            {
                "ticket_id": ticket_id,
                "owner_id": require_identity(item["owner_id"], f"{label}.owner_id"),
                "claim_generation": claim_generation,
                "phase": require_text(item["phase"], f"{label}.phase", safe_name=True),
                "record_path": require_text(
                    item["record_path"], f"{label}.record_path"
                ),
                "record_sha256": require_sha256(
                    item["record_sha256"], f"{label}.record_sha256"
                ),
                "checkpoint_sha256": require_sha256(
                    item["checkpoint_sha256"], f"{label}.checkpoint_sha256"
                ),
                "capsule_sha256": require_sha256(
                    item["capsule_sha256"], f"{label}.capsule_sha256"
                ),
                "observed_at": require_text(
                    item["observed_at"], f"{label}.observed_at"
                ),
            }
        )
    payload["run_id"] = run_id
    payload["coordinator_generation"] = generation
    payload["execution_records"] = normalized_records
    return payload


def validate_ref(value: Any, label: str) -> tuple[Path, str]:
    value = require_object(value, label)
    require_exact_fields(value, {"path", "sha256"}, label)
    path = Path(require_text(value["path"], f"{label}.path"))
    digest = require_sha256(value["sha256"], f"{label}.sha256")
    return path, digest


def validate_record(
    record_path: Path, artifact_root: Path
) -> tuple[dict[str, Any], str, dict[str, Any], dict[str, Any]]:
    record_bytes = read_regular_file(record_path, "record")
    record = require_object(parse_json(record_bytes, "record"), "record")
    require_exact_fields(record, RECORD_FIELDS, "record")
    if record["schema_version"] != 1 or record["kind"] != RECORD_KIND:
        fail("record schema_version or kind is unsupported")
    record_run_id = require_identity(record["run_id"], "record.run_id")
    ticket_id = require_identity(record["ticket_id"], "record.ticket_id")
    owner_id = require_identity(record["owner_id"], "record.owner_id")
    claim_generation = require_integer(
        record["claim_generation"], "record.claim_generation"
    )
    phase = require_text(record["phase"], "record.phase", safe_name=True)
    observed_at = require_text(record["observed_at"], "record.observed_at")
    checkpoint_path, checkpoint_digest = validate_ref(
        record["checkpoint_ref"], "record.checkpoint_ref"
    )
    capsule_path, capsule_digest = validate_ref(
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
    checkpoint = validate_checkpoint(parse_json(checkpoint_bytes, "checkpoint"))
    capsule = validate_capsule(parse_json(capsule_bytes, "capsule"))
    validate_relationships(capsule, checkpoint)
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


def entry_for_record(
    record: dict[str, Any], record_path: Path, record_digest: str
) -> dict[str, Any]:
    checkpoint_path, checkpoint_digest = validate_ref(
        record["checkpoint_ref"], "record.checkpoint_ref"
    )
    capsule_path, capsule_digest = validate_ref(
        record["capsule_ref"], "record.capsule_ref"
    )
    del checkpoint_path, capsule_path
    return {
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


def safe_receipt_target(path: Path) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        fail(f"receipt could not be inspected: {error}")
    if path.is_symlink() or not path.is_file():
        fail("receipt must be a regular non-symlink file")
    if metadata.st_nlink != 1:
        fail("receipt must not be a hardlink")
    if path.parent.is_symlink() or not path.parent.is_dir():
        fail("receipt parent must be an existing non-symlink directory")


@contextlib.contextmanager
def receipt_lock(path: Path):
    lock_path = path.with_name(f".{path.name}.lock")
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            fail("receipt lock must be a regular single-link file")
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def replace_receipt(
    path: Path, expected_bytes: bytes, new_bytes: bytes, *, locked: bool = False
) -> None:
    lock_context = contextlib.nullcontext() if locked else receipt_lock(path)
    with lock_context:
        safe_receipt_target(path)
        if read_regular_file(path, "receipt") != expected_bytes:
            fail("receipt changed during indexing")
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.tmp-", dir=path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(new_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            directory_descriptor = os.open(
                path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            )
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
            if read_regular_file(path, "receipt") != new_bytes:
                fail("receipt readback does not match the indexed state")
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def index_execution_record(
    receipt_path: Path,
    record_path: Path,
    artifact_root: Path,
    expected_generation: int,
    expected_receipt_digest: str,
) -> tuple[str, dict[str, Any]]:
    safe_receipt_target(receipt_path)
    expected_receipt_digest = require_sha256(
        expected_receipt_digest, "expected_receipt_sha256"
    )
    receipt_bytes = read_regular_file(receipt_path, "receipt")
    if sha256(receipt_bytes) != expected_receipt_digest:
        fail("receipt SHA-256 does not match")
    receipt = validate_receipt(parse_json(receipt_bytes, "receipt"))
    if receipt["coordinator_generation"] != expected_generation:
        fail("receipt coordinator_generation does not match")
    record, record_digest, _capsule, _checkpoint = validate_record(
        record_path, artifact_root
    )
    if receipt["run_id"] != record["run_id"]:
        fail("receipt and record run_id do not match")
    entry = entry_for_record(record, record_path, record_digest)
    key = (entry["ticket_id"], entry["claim_generation"])
    for current in receipt["execution_records"]:
        if (current["ticket_id"], current["claim_generation"]) != key:
            continue
        if current != entry:
            fail("receipt already contains a different record for this claim")
        return "already-indexed", entry

    receipt["execution_records"].append(entry)
    receipt["coordinator_generation"] += 1
    new_bytes = canonical_json(receipt)
    replace_receipt(receipt_path, receipt_bytes, new_bytes)
    return "indexed", entry


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CAS-index one validated Execution Checkpoint Record into a Run Receipt."
    )
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--expected-generation", required=True, type=int)
    parser.add_argument("--expected-receipt-sha256", required=True)
    arguments = parser.parse_args()
    try:
        status, entry = index_execution_record(
            arguments.receipt,
            arguments.record,
            arguments.artifact_root,
            arguments.expected_generation,
            arguments.expected_receipt_sha256,
        )
    except (OSError, IndexError, RecordError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": status,
                "kind": RECEIPT_KIND,
                "ticket_id": entry["ticket_id"],
                "claim_generation": entry["claim_generation"],
                "record_sha256": entry["record_sha256"],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
