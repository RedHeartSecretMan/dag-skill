"""Run Receipt validation, locking, atomic CAS replacement, and initialization."""

from __future__ import annotations

import contextlib
import fcntl
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

from lib.common import (
    canonical_json,
    ensure_no_symlink_ancestors,
    fail,
    is_allowed_system_path_alias,
    parse_json,
    publish_once,
    read_regular_file,
    require_exact_fields,
    require_identity,
    require_integer,
    require_object,
    require_sha256,
    require_text,
    sha256,
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
    if "tracker_policy" in payload and payload["tracker_policy"] is not None:
        require_object(payload["tracker_policy"], "receipt.tracker_policy")
    for field in (
        "claims",
        "ticket_dispositions",
        "tracker_checkpoints",
        "pending_tracker_updates",
    ):
        if field in payload and not isinstance(payload[field], list):
            fail(f"receipt.{field} must be an array")
    if "pending_transition" in payload and payload["pending_transition"] is not None:
        require_object(payload["pending_transition"], "receipt.pending_transition")
    return payload


def safe_receipt_target(path: Path) -> None:
    ensure_no_symlink_ancestors(path, "receipt")
    try:
        metadata = path.lstat()
    except OSError as error:
        fail(f"receipt could not be inspected: {error}")
    if path.is_symlink() or not path.is_file():
        fail("receipt must be a regular non-symlink file")
    if metadata.st_nlink != 1:
        fail("receipt must not be a hardlink")
    if (
        path.parent.is_symlink() and not is_allowed_system_path_alias(path.parent)
    ) or not path.parent.is_dir():
        fail("receipt parent must be an existing non-symlink directory")


@contextlib.contextmanager
def receipt_lock(path: Path):
    safe_receipt_target(path)
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
            fail("receipt changed during CAS update")
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
                fail("receipt readback does not match the updated state")
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def initialize_receipt(
    receipt_path: Path, init_path: Path
) -> tuple[str, dict[str, Any]]:
    init_bytes = read_regular_file(init_path, "init")
    raw = require_object(parse_json(init_bytes, "init"), "init")
    payload = dict(raw)
    payload.setdefault("schema_version", RECEIPT_SCHEMA_VERSION)
    payload.setdefault("kind", RECEIPT_KIND)
    payload.setdefault("coordinator_generation", 0)
    payload.setdefault("claims", [])
    payload.setdefault("execution_records", [])
    payload.setdefault("ticket_dispositions", [])
    payload.setdefault("tracker_checkpoints", [])
    payload.setdefault("pending_tracker_updates", [])
    receipt = validate_receipt(payload)
    if receipt["coordinator_generation"] != 0:
        fail("receipt-init requires coordinator_generation to be 0")
    if (
        receipt.get("claims")
        or receipt.get("execution_records")
        or receipt.get("ticket_dispositions")
        or receipt.get("tracker_checkpoints")
        or receipt.get("pending_tracker_updates")
    ):
        fail(
            "receipt-init requires empty claims, records, dispositions, and checkpoints"
        )
    content = canonical_json(receipt)
    published = publish_once(receipt_path, content, [init_path])
    status = "initialized" if published == "published" else "already-initialized"
    return status, {
        "status": status,
        "kind": RECEIPT_KIND,
        "run_id": receipt["run_id"],
        "coordinator_generation": 0,
        "receipt_sha256": sha256(content),
    }
