#!/usr/bin/env python3
"""Validate and CAS-record a Coordinator-owned Tracker Checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from index_execution_record import (
    IndexError as ReceiptIndexError,
)
from index_execution_record import (
    receipt_lock,
    replace_receipt,
    safe_receipt_target,
    validate_receipt,
)
from record_execution_checkpoint import (
    RecordError,
    canonical_json,
    parse_json,
    path_contains,
    publish_once,
    read_regular_file,
    require_exact_fields,
    require_identity,
    require_integer,
    require_oid,
    require_relative_path,
    require_sha256,
    require_string_array,
    require_text,
    sha256,
    validate_ticket_base,
)
from record_ticket_disposition import validate_evidence_refs
from record_tracker_policy import (
    DISPOSITIONS,
    compute_pending_tracker_updates,
    effective_ticket_dispositions,
    paths_overlap,
    sort_paths,
    validate_receipt_tracker_policy,
)
from validate_definition_index import (
    INDEX_PATH,
    REGULAR_BLOB_MODES,
    ValidationError,
    isolated_git_environment,
    run_git,
    validate_definition_index,
)

SCHEMA_VERSION = 1
CHECKPOINT_KIND = "Tracker Checkpoint"
PREFLIGHT_KIND = "Tracker Checkpoint Preflight"
RECORD_KIND = "Tracker Checkpoint Record"
ALLOWED_DIFF_MODES = {"000000", *REGULAR_BLOB_MODES}
CHECKPOINT_FIELDS = {
    "schema_version",
    "kind",
    "run_id",
    "coordinator_generation",
    "policy_key",
    "integration_ref",
    "ticket_dispositions",
    "base",
    "candidate",
    "changed_paths",
    "blob_changes",
    "evidence_refs",
}
RECEIPT_CHECKPOINT_FIELDS = {
    "checkpoint_key",
    "coordinator_generation",
    "policy_key",
    "integration_ref",
    "ticket_dispositions",
    "base",
    "candidate",
    "changed_paths",
    "blob_changes",
    "evidence_refs",
    "record_path",
    "record_sha256",
}


def fail(message: str) -> None:
    raise RecordError(message)


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value


def git_probe(
    repository: Path, arguments: list[str]
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        capture_output=True,
        check=False,
        env=isolated_git_environment(),
    )


def read_direct_ref(repository: Path, integration_ref: str) -> str:
    symbolic = git_probe(repository, ["symbolic-ref", "--quiet", integration_ref])
    if symbolic.returncode == 0:
        fail("integration_ref must not be symbolic")
    if symbolic.returncode != 1:
        fail("could not inspect integration_ref for symbolic indirection")
    try:
        return (
            run_git(repository, ["show-ref", "--verify", "--hash", integration_ref])
            .decode("ascii")
            .strip()
        )
    except ValidationError as error:
        fail(f"integration_ref could not be read: {error}")


def validate_bound_dispositions(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        fail(f"{label} must be a non-empty array")
    result = []
    seen: set[tuple[str, int]] = set()
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        item = require_object(item, item_label)
        require_exact_fields(
            item, {"ticket_id", "claim_generation", "disposition"}, item_label
        )
        ticket_id = require_identity(item["ticket_id"], f"{item_label}.ticket_id")
        claim_generation = require_integer(
            item["claim_generation"], f"{item_label}.claim_generation", minimum=1
        )
        disposition = require_text(
            item["disposition"], f"{item_label}.disposition", safe_name=True
        )
        if disposition not in DISPOSITIONS:
            fail(f"{item_label}.disposition is unsupported")
        key = (ticket_id, claim_generation)
        if key in seen:
            fail(f"{item_label} duplicates ticket_id and claim_generation")
        seen.add(key)
        result.append(
            {
                "ticket_id": ticket_id,
                "claim_generation": claim_generation,
                "disposition": disposition,
            }
        )
    return sorted(
        result, key=lambda entry: (entry["ticket_id"], entry["claim_generation"])
    )


def validate_blob_changes(
    value: Any, changed_paths: list[str], label: str
) -> list[dict[str, str | None]]:
    if not isinstance(value, list) or not value:
        fail(f"{label} must be a non-empty array")
    result = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        item = require_object(item, item_label)
        require_exact_fields(
            item, {"path", "before_blob_oid", "after_blob_oid"}, item_label
        )
        path = require_relative_path(item["path"], f"{item_label}.path")
        if path in seen:
            fail(f"{item_label}.path is duplicated")
        seen.add(path)
        before = item["before_blob_oid"]
        after = item["after_blob_oid"]
        if before is not None:
            before = require_oid(before, f"{item_label}.before_blob_oid")
        if after is not None:
            after = require_oid(after, f"{item_label}.after_blob_oid")
        if before == after:
            fail(
                f"{item_label} before_blob_oid and after_blob_oid must differ and not both be null"
            )
        result.append(
            {
                "path": path,
                "before_blob_oid": before,
                "after_blob_oid": after,
            }
        )
    ordered = sorted(result, key=lambda entry: str(entry["path"]).encode("utf-8"))
    if [entry["path"] for entry in ordered] != changed_paths:
        fail("blob_changes paths must match changed_paths exactly")
    return ordered


def compute_checkpoint_key(checkpoint: dict[str, Any]) -> str:
    material = {
        "run_id": checkpoint["run_id"],
        "policy_key": checkpoint["policy_key"],
        "integration_ref": checkpoint["integration_ref"],
        "ticket_dispositions": checkpoint["ticket_dispositions"],
        "base": checkpoint["base"],
        "candidate": checkpoint["candidate"],
        "changed_paths": checkpoint["changed_paths"],
        "blob_changes": checkpoint["blob_changes"],
        "evidence_refs": checkpoint["evidence_refs"],
    }
    return hashlib.sha256(canonical_json(material)).hexdigest()


def _validate_checkpoint_common(payload: dict[str, Any], label: str) -> dict[str, Any]:
    integration_ref = require_text(
        payload["integration_ref"], f"{label}.integration_ref"
    )
    if not integration_ref.startswith("refs/heads/"):
        fail(f"{label}.integration_ref must be a full refs/heads/ reference")
    base = validate_ticket_base(payload["base"], f"{label}.base")
    candidate = validate_ticket_base(payload["candidate"], f"{label}.candidate")
    if base["commit"] == candidate["commit"]:
        fail(f"{label}.candidate must differ from base")
    changed_paths = sort_paths(
        require_string_array(
            payload["changed_paths"], f"{label}.changed_paths", paths=True
        )
    )
    if not changed_paths:
        fail(f"{label}.changed_paths must be a non-empty array")
    blob_changes = validate_blob_changes(
        payload["blob_changes"], changed_paths, f"{label}.blob_changes"
    )
    return {
        "run_id": require_identity(payload["run_id"], f"{label}.run_id"),
        "coordinator_generation": require_integer(
            payload["coordinator_generation"], f"{label}.coordinator_generation"
        ),
        "policy_key": require_sha256(payload["policy_key"], f"{label}.policy_key"),
        "integration_ref": integration_ref,
        "ticket_dispositions": validate_bound_dispositions(
            payload["ticket_dispositions"], f"{label}.ticket_dispositions"
        ),
        "base": base,
        "candidate": candidate,
        "changed_paths": changed_paths,
        "blob_changes": blob_changes,
        "evidence_refs": validate_evidence_refs(
            payload["evidence_refs"], f"{label}.evidence_refs"
        ),
    }


def validate_checkpoint(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "checkpoint")
    require_exact_fields(payload, CHECKPOINT_FIELDS, "checkpoint")
    if (
        payload["schema_version"] != SCHEMA_VERSION
        or payload["kind"] != CHECKPOINT_KIND
    ):
        fail("checkpoint schema_version or kind is unsupported")
    common = _validate_checkpoint_common(payload, "checkpoint")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": CHECKPOINT_KIND,
        **common,
    }


def create_checkpoint_record(
    checkpoint: dict[str, Any], *, kind: str = RECORD_KIND
) -> dict[str, Any]:
    return {
        **checkpoint,
        "kind": kind,
        "checkpoint_key": compute_checkpoint_key(checkpoint),
    }


def validate_checkpoint_record(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "checkpoint record")
    require_exact_fields(
        payload, CHECKPOINT_FIELDS | {"checkpoint_key"}, "checkpoint record"
    )
    if payload["schema_version"] != SCHEMA_VERSION or payload["kind"] != RECORD_KIND:
        fail("checkpoint record schema_version or kind is unsupported")
    common = _validate_checkpoint_common(payload, "checkpoint record")
    expected_key = compute_checkpoint_key(common)
    declared_key = require_sha256(
        payload["checkpoint_key"], "checkpoint record.checkpoint_key"
    )
    if declared_key != expected_key:
        fail("checkpoint record checkpoint_key does not match its fields")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": RECORD_KIND,
        "checkpoint_key": expected_key,
        **common,
    }


def verify_git_diff_and_identities(
    repository: Path,
    checkpoint: dict[str, Any],
    off_delivery_paths: list[Path],
    *,
    preflight: bool,
) -> Path:
    try:
        resolved_repo = repository.resolve(strict=True)
        toplevel = Path(
            os.fsdecode(
                run_git(resolved_repo, ["rev-parse", "--show-toplevel"]).strip()
            )
        ).resolve(strict=True)
        run_git(toplevel, ["check-ref-format", checkpoint["integration_ref"]])
        object_format = run_git(toplevel, ["rev-parse", "--show-object-format"]).strip()
    except (OSError, RuntimeError, ValidationError) as error:
        fail(f"repository inspection failed: {error}")
    oid_length = {b"sha1": 40, b"sha256": 64}.get(object_format)
    if oid_length is None:
        fail("unsupported Git object format")
    for label, commit_tree in (
        ("base", checkpoint["base"]),
        ("candidate", checkpoint["candidate"]),
    ):
        commit_oid = commit_tree["commit"]
        tree_oid = commit_tree["tree"]
        if len(commit_oid) != oid_length or len(tree_oid) != oid_length:
            fail(f"{label} OID length does not match repository object format")
        try:
            if run_git(toplevel, ["cat-file", "-t", commit_oid]).strip() != b"commit":
                fail(f"{label}.commit must identify a local commit object")
            if run_git(toplevel, ["cat-file", "-t", tree_oid]).strip() != b"tree":
                fail(f"{label}.tree must identify a local tree object")
            actual_tree = (
                run_git(toplevel, ["rev-parse", f"{commit_oid}^{{tree}}"])
                .decode("ascii")
                .strip()
            )
        except ValidationError as error:
            fail(f"{label} Git object verification failed: {error}")
        if actual_tree != tree_oid:
            fail(f"{label}.tree does not match {label}.commit")
    if (
        git_probe(
            toplevel,
            [
                "merge-base",
                "--is-ancestor",
                checkpoint["base"]["commit"],
                checkpoint["candidate"]["commit"],
            ],
        ).returncode
        != 0
    ):
        fail("base.commit must be a local ancestor of candidate.commit")

    live_ref = read_direct_ref(toplevel, checkpoint["integration_ref"])
    if preflight:
        if live_ref != checkpoint["base"]["commit"]:
            fail(
                "preflight requires integration_ref to equal base.commit before promotion"
            )
    else:
        if live_ref == checkpoint["base"]["commit"]:
            fail(
                "integration_ref has not been promoted to candidate; promote Definition Checkpoint and read back first"
            )
        if live_ref != checkpoint["candidate"]["commit"]:
            fail("stale checkpoint: integration_ref does not point to candidate.commit")

    try:
        raw_diff = run_git(
            toplevel,
            [
                "diff-tree",
                "-r",
                "--no-commit-id",
                "--no-renames",
                "-z",
                checkpoint["base"]["commit"],
                checkpoint["candidate"]["commit"],
            ],
        )
    except ValidationError as error:
        fail(f"diff-tree failed: {error}")
    tokens = [token for token in raw_diff.split(b"\0") if token]
    if len(tokens) % 2 != 0:
        fail("unexpected git diff-tree output format")
    actual_changes: dict[str, tuple[str | None, str | None]] = {}
    zero_oid = "0" * oid_length
    for index in range(0, len(tokens), 2):
        header = tokens[index].decode("ascii")
        path = tokens[index + 1].decode("utf-8")
        if not header.startswith(":"):
            fail("unexpected git diff-tree header")
        old_mode, new_mode, old_oid, new_oid, _status = header[1:].split(" ", 4)
        if old_mode not in ALLOWED_DIFF_MODES or new_mode not in ALLOWED_DIFF_MODES:
            fail(
                f"changed path {path} must use regular file modes, not symlinks or submodules"
            )
        before_oid = None if old_oid == zero_oid else old_oid
        after_oid = None if new_oid == zero_oid else new_oid
        actual_changes[path] = (before_oid, after_oid)
    if sort_paths(list(actual_changes)) != checkpoint["changed_paths"]:
        fail("changed_paths do not match the exact Git diff between base and candidate")
    for item in checkpoint["blob_changes"]:
        actual_pair = actual_changes.get(str(item["path"]))
        if actual_pair != (item["before_blob_oid"], item["after_blob_oid"]):
            fail(
                f"blob_changes for {item['path']} do not match Git blob identities at base and candidate"
            )

    tracked: set[bytes] = set()
    for revision in (checkpoint["base"]["commit"], checkpoint["candidate"]["commit"]):
        tracked.update(
            run_git(toplevel, ["ls-tree", "-r", "-z", "--name-only", revision]).split(
                b"\0"
            )
        )
    tracked.discard(b"")
    for external in off_delivery_paths:
        for candidate_path in (external.absolute(), external.resolve(strict=False)):
            if not candidate_path.is_relative_to(toplevel):
                continue
            relative = os.fsencode(candidate_path.relative_to(toplevel).as_posix())
            if relative in tracked or any(
                relative.startswith(entry + b"/") for entry in tracked
            ):
                fail(
                    f"{external}: Tracker Checkpoint records and evidence must be off-delivery"
                )
    return toplevel


def verify_policy_and_scope(
    repository: Path,
    receipt: dict[str, Any],
    policy: dict[str, Any] | None,
    checkpoint: dict[str, Any],
) -> dict[str, Any]:
    if policy is None:
        fail("receipt has no recorded Tracker Policy")
    if policy["mode"] == "none":
        fail("Tracker Policy mode none does not accept Tracker Checkpoints")
    if checkpoint["policy_key"] != policy["policy_key"]:
        fail(
            "stale policy: checkpoint policy_key does not match current receipt Tracker Policy"
        )
    if (
        "integration_ref" in receipt
        and receipt["integration_ref"] is not None
        and receipt["integration_ref"] != checkpoint["integration_ref"]
    ):
        fail("checkpoint integration_ref does not match receipt.integration_ref")
    accepted_tip = receipt.get("accepted_integration_tip")
    if accepted_tip is not None:
        accepted_tip = validate_ticket_base(
            accepted_tip, "receipt.accepted_integration_tip"
        )
        if checkpoint["base"] != accepted_tip:
            fail(
                "stale checkpoint: checkpoint.base does not match receipt.accepted_integration_tip"
            )

    decision = policy["stateful_tracker_decision"]
    changed = checkpoint["changed_paths"]
    def_overlaps = [
        path
        for path in changed
        if path != INDEX_PATH
        and any(
            paths_overlap(def_path, path) for def_path in policy["definition_paths"]
        )
    ]
    if decision is None:
        if INDEX_PATH in changed or def_overlaps:
            fail(
                f"Tracker Checkpoint cannot modify {INDEX_PATH} or definition_paths without stateful_tracker_decision"
            )
        for path in changed:
            if not any(
                path_contains(tracker_path, path)
                for tracker_path in policy["tracker_paths"]
            ):
                fail(f"changed path {path} is outside policy.tracker_paths")
    else:
        for path in changed:
            if path == INDEX_PATH:
                continue
            if not any(
                path_contains(tracker_path, path)
                for tracker_path in policy["tracker_paths"]
            ):
                fail(f"changed path {path} is outside policy.tracker_paths")
        if def_overlaps:
            for path in def_overlaps:
                if not any(
                    path_contains(allowed, path)
                    for allowed in decision["overlapping_paths"]
                ):
                    fail(
                        f"changed Definition path {path} is not covered by stateful_tracker_decision.overlapping_paths"
                    )
            if INDEX_PATH not in changed:
                fail(
                    f"modifying stateful Definition path requires updating {INDEX_PATH} in the same checkpoint"
                )
            try:
                validate_definition_index(repository, checkpoint["candidate"]["commit"])
            except ValidationError as error:
                fail(f"candidate {INDEX_PATH} validation failed: {error}")
        elif INDEX_PATH in changed:
            fail(
                f"{INDEX_PATH} cannot change when no overlapping Definition path changed"
            )

    effective = effective_ticket_dispositions(receipt, verify_evidence=True)
    for bound in checkpoint["ticket_dispositions"]:
        current = effective.get(bound["ticket_id"])
        if current is None:
            fail(
                f"checkpoint binds Ticket {bound['ticket_id']} without a recorded disposition in receipt"
            )
        if (
            current["claim_generation"] != bound["claim_generation"]
            or current["disposition"] != bound["disposition"]
        ):
            fail(
                f"checkpoint disposition for Ticket {bound['ticket_id']} does not match effective receipt disposition"
            )
    return policy


def validate_receipt_tracker_checkpoints(
    receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    raw = receipt.get("tracker_checkpoints", [])
    if not isinstance(raw, list):
        fail("receipt.tracker_checkpoints must be an array")
    recorded_dispositions = {
        (
            item.get("ticket_id"),
            item.get("claim_generation"),
            item.get("disposition"),
        )
        for item in receipt.get("ticket_dispositions", [])
        if isinstance(item, dict)
    }
    validated = []
    seen_keys: set[str] = set()
    for index, item in enumerate(raw):
        label = f"receipt.tracker_checkpoints[{index}]"
        item = require_object(item, label)
        require_exact_fields(item, RECEIPT_CHECKPOINT_FIELDS, label)
        common = _validate_checkpoint_common(
            {"run_id": receipt["run_id"], **item}, label
        )
        expected_key = compute_checkpoint_key(common)
        checkpoint_key = require_sha256(
            item["checkpoint_key"], f"{label}.checkpoint_key"
        )
        if checkpoint_key != expected_key:
            fail(f"{label}.checkpoint_key does not match its fields")
        if checkpoint_key in seen_keys:
            fail(f"{label} duplicates checkpoint_key")
        seen_keys.add(checkpoint_key)
        record_path = Path(require_text(item["record_path"], f"{label}.record_path"))
        record_sha256 = require_sha256(item["record_sha256"], f"{label}.record_sha256")
        record_bytes = read_regular_file(record_path, f"{label}.record_path")
        if sha256(record_bytes) != record_sha256:
            fail(f"{label} Tracker Checkpoint Record SHA-256 does not match receipt")
        record = validate_checkpoint_record(
            parse_json(record_bytes, "checkpoint record")
        )
        if record["run_id"] != receipt["run_id"]:
            fail(f"{label} Tracker Checkpoint Record run_id does not match receipt")
        if record["checkpoint_key"] != checkpoint_key:
            fail(
                f"{label} Tracker Checkpoint Record checkpoint_key does not match receipt"
            )
        for bound in common["ticket_dispositions"]:
            key = (
                bound["ticket_id"],
                bound["claim_generation"],
                bound["disposition"],
            )
            if key not in recorded_dispositions:
                fail(
                    f"{label} binds Ticket {bound['ticket_id']} disposition not present in receipt.ticket_dispositions"
                )
        validated.append(
            {
                "checkpoint_key": checkpoint_key,
                **common,
                "record_path": str(record_path.resolve()),
                "record_sha256": record_sha256,
            }
        )
    return validated


def run_preflight(
    repository: Path,
    receipt_path: Path,
    checkpoint_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    receipt = validate_receipt(
        parse_json(read_regular_file(receipt_path, "receipt"), "receipt")
    )
    checkpoint = validate_checkpoint(
        parse_json(read_regular_file(checkpoint_path, "checkpoint"), "checkpoint")
    )
    if checkpoint["run_id"] != receipt["run_id"]:
        fail("receipt and checkpoint run_id do not match")
    off_delivery = [
        receipt_path,
        checkpoint_path,
        output_path,
        *(Path(item["path"]) for item in checkpoint["evidence_refs"]),
    ]
    toplevel = verify_git_diff_and_identities(
        repository, checkpoint, off_delivery, preflight=True
    )
    policy = validate_receipt_tracker_policy(receipt, reread_record=True)
    verify_policy_and_scope(toplevel, receipt, policy, checkpoint)
    record = create_checkpoint_record(checkpoint, kind=PREFLIGHT_KIND)
    status = publish_once(
        output_path, canonical_json(record), [receipt_path, checkpoint_path]
    )
    return {
        "status": status,
        "kind": PREFLIGHT_KIND,
        "checkpoint_key": record["checkpoint_key"],
        "candidate": checkpoint["candidate"]["commit"],
    }


def _record_checkpoint_locked(
    repository: Path,
    receipt_path: Path,
    checkpoint_path: Path,
    output_path: Path,
    expected_generation: int,
    expected_receipt_digest: str,
) -> tuple[str, dict[str, Any], int]:
    safe_receipt_target(receipt_path)
    receipt_bytes = read_regular_file(receipt_path, "receipt")
    if sha256(receipt_bytes) != expected_receipt_digest:
        fail("receipt SHA-256 does not match")
    receipt = validate_receipt(parse_json(receipt_bytes, "receipt"))
    if receipt["coordinator_generation"] != expected_generation:
        fail("receipt coordinator_generation does not match")

    checkpoint = validate_checkpoint(
        parse_json(read_regular_file(checkpoint_path, "checkpoint"), "checkpoint")
    )
    if checkpoint["run_id"] != receipt["run_id"]:
        fail("receipt and checkpoint run_id do not match")
    off_delivery = [
        receipt_path,
        checkpoint_path,
        output_path,
        *(Path(item["path"]) for item in checkpoint["evidence_refs"]),
    ]
    toplevel = verify_git_diff_and_identities(
        repository, checkpoint, off_delivery, preflight=False
    )
    policy = verify_policy_and_scope(
        toplevel,
        receipt,
        validate_receipt_tracker_policy(receipt, reread_record=True),
        checkpoint,
    )

    record = create_checkpoint_record(checkpoint, kind=RECORD_KIND)
    record_bytes = canonical_json(record)
    expected_entry = {
        "checkpoint_key": record["checkpoint_key"],
        "coordinator_generation": checkpoint["coordinator_generation"],
        "policy_key": checkpoint["policy_key"],
        "integration_ref": checkpoint["integration_ref"],
        "ticket_dispositions": checkpoint["ticket_dispositions"],
        "base": checkpoint["base"],
        "candidate": checkpoint["candidate"],
        "changed_paths": checkpoint["changed_paths"],
        "blob_changes": checkpoint["blob_changes"],
        "evidence_refs": checkpoint["evidence_refs"],
        "record_path": str(output_path.resolve()),
        "record_sha256": sha256(record_bytes),
    }
    checkpoints = receipt.setdefault("tracker_checkpoints", [])
    if not isinstance(checkpoints, list):
        fail("receipt.tracker_checkpoints must be an array")
    matching = [
        item
        for item in checkpoints
        if isinstance(item, dict)
        and (
            item.get("checkpoint_key") == record["checkpoint_key"]
            or (
                item.get("policy_key") == checkpoint["policy_key"]
                and isinstance(item.get("candidate"), dict)
                and item["candidate"].get("commit") == checkpoint["candidate"]["commit"]
            )
        )
    ]
    if matching:
        if len(matching) != 1 or matching[0] != expected_entry:
            fail("receipt already contains a conflicting Tracker Checkpoint")
        publish_once(output_path, record_bytes, [receipt_path, checkpoint_path])
        return "already-recorded", expected_entry, expected_generation

    if checkpoint["coordinator_generation"] != expected_generation:
        fail("checkpoint coordinator_generation does not match receipt")
    for prior in checkpoints:
        if not isinstance(prior, dict) or not isinstance(prior.get("candidate"), dict):
            fail("receipt.tracker_checkpoints entry is malformed")
        prior_commit = str(prior["candidate"].get("commit", ""))
        if (
            git_probe(
                toplevel,
                [
                    "merge-base",
                    "--is-ancestor",
                    prior_commit,
                    checkpoint["candidate"]["commit"],
                ],
            ).returncode
            != 0
        ):
            fail(
                "stale checkpoint: candidate.commit does not descend from prior Tracker Checkpoint"
            )

    publish_once(output_path, record_bytes, [receipt_path, checkpoint_path])
    checkpoints.append(expected_entry)
    receipt["pending_tracker_updates"] = compute_pending_tracker_updates(
        receipt, policy
    )
    receipt["coordinator_generation"] += 1
    replace_receipt(receipt_path, receipt_bytes, canonical_json(receipt), locked=True)
    return "recorded", expected_entry, expected_generation + 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and CAS-record a Coordinator-owned Tracker Checkpoint."
    )
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-generation", type=int)
    parser.add_argument("--expected-receipt-sha256")
    parser.add_argument("--preflight", action="store_true")
    arguments = parser.parse_args()
    try:
        if arguments.preflight:
            result = run_preflight(
                arguments.repository,
                arguments.receipt,
                arguments.checkpoint,
                arguments.output,
            )
            print(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 0
        if (
            arguments.expected_generation is None
            or arguments.expected_receipt_sha256 is None
        ):
            fail(
                "--expected-generation and --expected-receipt-sha256 are required unless --preflight is set"
            )
        with receipt_lock(arguments.receipt):
            status, entry, generation = _record_checkpoint_locked(
                arguments.repository,
                arguments.receipt,
                arguments.checkpoint,
                arguments.output,
                require_integer(arguments.expected_generation, "expected_generation"),
                require_sha256(
                    arguments.expected_receipt_sha256, "expected_receipt_sha256"
                ),
            )
    except (OSError, ReceiptIndexError, RecordError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": status,
                "kind": RECORD_KIND,
                "checkpoint_key": entry["checkpoint_key"],
                "candidate": entry["candidate"]["commit"],
                "coordinator_generation": generation,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
