#!/usr/bin/env python3
"""Validate and CAS-record a Coordinator-owned Tracker Policy."""

from __future__ import annotations

import argparse
import hashlib
import json
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
    OID,
    RecordError,
    canonical_json,
    parse_json,
    path_contains,
    publish_once,
    read_regular_file,
    require_exact_fields,
    require_identity,
    require_integer,
    require_relative_path,
    require_sha256,
    require_string_array,
    require_text,
    sha256,
)
from validate_definition_index import (
    INDEX_PATH,
    REGULAR_BLOB_MODES,
    ValidationError,
    run_git,
    tree_entries_for_paths,
    validate_definition_index,
)

SCHEMA_VERSION = 1
POLICY_KIND = "Tracker Policy"
RECORD_KIND = "Tracker Policy Record"
MODES = {"none", "in_repo", "external_snapshot"}
UPDATE_SCOPES = {"none", "per_ticket", "batched"}
DISPOSITIONS = {"Accepted", "Superseded"}
REQUIRED_POLICY_FIELDS = {
    "schema_version",
    "kind",
    "run_id",
    "mode",
    "authoritative_paths",
    "rule_refs",
    "definition_paths",
    "tracker_paths",
    "update_scope",
    "rationale",
}
OPTIONAL_POLICY_FIELDS = {"stateful_tracker_decision"}
DECISION_FIELDS = {
    "decision_id",
    "approved_by",
    "overlapping_paths",
    "rationale",
}
RECEIPT_POLICY_FIELDS = {
    "policy_key",
    "mode",
    "authoritative_paths",
    "rule_refs",
    "definition_paths",
    "tracker_paths",
    "update_scope",
    "rationale",
    "stateful_tracker_decision",
    "policy_path",
    "policy_sha256",
}


def fail(message: str) -> None:
    raise RecordError(message)


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value


def paths_overlap(left: str, right: str) -> bool:
    return path_contains(left, right) or path_contains(right, left)


def sort_paths(paths: list[str]) -> list[str]:
    return sorted(paths, key=lambda item: item.encode("utf-8"))


def validate_rule_refs(value: Any, label: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        fail(f"{label} must be a non-empty array")
    result = []
    ids = set()
    paths = set()
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        item = require_object(item, item_label)
        require_exact_fields(item, {"id", "path", "identity"}, item_label)
        ref_id = require_identity(item["id"], f"{item_label}.id")
        if ref_id in ids:
            fail(f"{item_label}.id is duplicated")
        ids.add(ref_id)
        ref_path = require_relative_path(item["path"], f"{item_label}.path")
        if ref_path in paths:
            fail(f"{item_label}.path is duplicated")
        paths.add(ref_path)
        result.append(
            {
                "id": ref_id,
                "path": ref_path,
                "identity": require_identity(
                    item["identity"], f"{item_label}.identity"
                ),
            }
        )
    return sorted(result, key=lambda entry: entry["id"])


def validate_stateful_decision(
    value: Any, label: str = "policy.stateful_tracker_decision"
) -> dict[str, Any] | None:
    if value is None:
        return None
    value = require_object(value, label)
    require_exact_fields(value, DECISION_FIELDS, label)
    overlapping = sort_paths(
        require_string_array(
            value["overlapping_paths"], f"{label}.overlapping_paths", paths=True
        )
    )
    if not overlapping:
        fail(f"{label}.overlapping_paths must be a non-empty array")
    if INDEX_PATH in overlapping:
        fail(f"{label}.overlapping_paths must not include {INDEX_PATH}")
    return {
        "decision_id": require_identity(value["decision_id"], f"{label}.decision_id"),
        "approved_by": require_identity(value["approved_by"], f"{label}.approved_by"),
        "overlapping_paths": overlapping,
        "rationale": require_text(value["rationale"], f"{label}.rationale"),
    }


def verify_path_separation(
    mode: str,
    definition_paths: list[str],
    tracker_paths: list[str],
    decision: dict[str, Any] | None,
) -> None:
    overlaps: list[str] = []
    for def_path in definition_paths:
        for tracker_path in tracker_paths:
            if paths_overlap(def_path, tracker_path):
                narrower = (
                    tracker_path if path_contains(def_path, tracker_path) else def_path
                )
                overlaps.append(narrower)
    if not overlaps:
        if decision is not None:
            fail(
                "stateful_tracker_decision requires overlapping definition_paths and tracker_paths"
            )
        return
    if mode == "none":
        fail("mode none cannot have overlapping definition_paths and tracker_paths")
    if decision is None:
        joined = ", ".join(sorted(set(overlaps)))
        fail(
            f"definition_paths and tracker_paths overlap ({joined}); split Definition and tracker files or record stateful_tracker_decision"
        )
    allowed = decision["overlapping_paths"]
    for narrower in overlaps:
        if not any(path_contains(item, narrower) for item in allowed):
            fail(
                f"stateful_tracker_decision.overlapping_paths does not cover overlapping path {narrower}"
            )
    for item in allowed:
        if not any(paths_overlap(item, narrower) for narrower in overlaps):
            fail(
                f"stateful_tracker_decision.overlapping_paths entry {item} does not overlap definition_paths and tracker_paths"
            )


def compute_policy_key(policy: dict[str, Any]) -> str:
    material = {
        "run_id": policy["run_id"],
        "mode": policy["mode"],
        "authoritative_paths": policy["authoritative_paths"],
        "rule_refs": policy["rule_refs"],
        "definition_paths": policy["definition_paths"],
        "tracker_paths": policy["tracker_paths"],
        "update_scope": policy["update_scope"],
        "rationale": policy["rationale"],
        "stateful_tracker_decision": policy["stateful_tracker_decision"],
    }
    return hashlib.sha256(canonical_json(material)).hexdigest()


def _validate_policy_common(payload: dict[str, Any], label: str) -> dict[str, Any]:
    mode = require_text(payload["mode"], f"{label}.mode", safe_name=True)
    if mode not in MODES:
        fail(f"{label}.mode is unsupported")
    authoritative_paths = sort_paths(
        require_string_array(
            payload["authoritative_paths"],
            f"{label}.authoritative_paths",
            paths=True,
        )
    )
    definition_paths = sort_paths(
        require_string_array(
            payload["definition_paths"], f"{label}.definition_paths", paths=True
        )
    )
    tracker_paths = sort_paths(
        require_string_array(
            payload["tracker_paths"], f"{label}.tracker_paths", paths=True
        )
    )
    if not definition_paths:
        fail(f"{label}.definition_paths must be a non-empty array")
    for group_name, group in (
        ("authoritative_paths", authoritative_paths),
        ("definition_paths", definition_paths),
        ("tracker_paths", tracker_paths),
    ):
        if INDEX_PATH in group:
            fail(f"{label}.{group_name} must not include {INDEX_PATH}")
    update_scope = require_text(
        payload["update_scope"], f"{label}.update_scope", safe_name=True
    )
    if update_scope not in UPDATE_SCOPES:
        fail(f"{label}.update_scope is unsupported")
    decision = validate_stateful_decision(
        payload.get("stateful_tracker_decision"),
        f"{label}.stateful_tracker_decision",
    )
    if mode == "none":
        if authoritative_paths:
            fail(f"{label}.authoritative_paths must be empty when mode is none")
        if tracker_paths:
            fail(f"{label}.tracker_paths must be empty when mode is none")
        if update_scope != "none":
            fail(f"{label}.update_scope must be 'none' when mode is none")
        if decision is not None:
            fail(f"{label}.stateful_tracker_decision must be null when mode is none")
    else:
        if not authoritative_paths:
            fail(f"{label}.authoritative_paths must be non-empty when mode is {mode}")
        if not tracker_paths:
            fail(f"{label}.tracker_paths must be non-empty when mode is {mode}")
        if update_scope == "none":
            fail(f"{label}.update_scope cannot be 'none' when mode is {mode}")
    verify_path_separation(mode, definition_paths, tracker_paths, decision)
    return {
        "run_id": require_identity(payload["run_id"], f"{label}.run_id"),
        "mode": mode,
        "authoritative_paths": authoritative_paths,
        "rule_refs": validate_rule_refs(payload["rule_refs"], f"{label}.rule_refs"),
        "definition_paths": definition_paths,
        "tracker_paths": tracker_paths,
        "update_scope": update_scope,
        "rationale": require_text(payload["rationale"], f"{label}.rationale"),
        "stateful_tracker_decision": decision,
    }


def validate_policy(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "policy")
    actual = set(payload)
    missing = sorted(REQUIRED_POLICY_FIELDS - actual)
    unknown = sorted(actual - (REQUIRED_POLICY_FIELDS | OPTIONAL_POLICY_FIELDS))
    if missing or unknown:
        details = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if unknown:
            details.append(f"unknown {', '.join(unknown)}")
        fail(f"policy fields are invalid: {'; '.join(details)}")
    if payload["schema_version"] != SCHEMA_VERSION or payload["kind"] != POLICY_KIND:
        fail("policy schema_version or kind is unsupported")
    common = _validate_policy_common(payload, "policy")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": POLICY_KIND,
        **common,
    }


def create_policy_record(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        **policy,
        "kind": RECORD_KIND,
        "policy_key": compute_policy_key(policy),
    }


def validate_policy_record(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "policy record")
    expected = REQUIRED_POLICY_FIELDS | OPTIONAL_POLICY_FIELDS | {"policy_key"}
    require_exact_fields(payload, expected, "policy record")
    if payload["schema_version"] != SCHEMA_VERSION or payload["kind"] != RECORD_KIND:
        fail("policy record schema_version or kind is unsupported")
    common = _validate_policy_common(payload, "policy record")
    expected_key = compute_policy_key(common)
    declared_key = require_sha256(payload["policy_key"], "policy record.policy_key")
    if declared_key != expected_key:
        fail("policy record policy_key does not match its fields")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": RECORD_KIND,
        "policy_key": expected_key,
        **common,
    }


def verify_policy_against_commit(
    repository: Path, commit: str, policy: dict[str, Any]
) -> None:
    try:
        validated = validate_definition_index(repository, commit)
    except ValidationError as error:
        fail(f"Definition Index validation failed: {error}")
    commit_oid = str(validated["commit"])
    index_paths = [str(item["path"]) for item in validated["inputs"]]  # type: ignore[index]
    if index_paths != policy["definition_paths"]:
        fail(
            "policy.definition_paths do not match .dag/definition-index.json at commit"
        )
    rule_paths = sorted({item["path"] for item in policy["rule_refs"]})
    try:
        resolved_repo = repository.resolve(strict=True)
        entries = tree_entries_for_paths(resolved_repo, commit_oid, rule_paths)
    except ValidationError as error:
        fail(f"rule_refs lookup failed: {error}")
    for ref in policy["rule_refs"]:
        entry = entries.get(ref["path"])
        if entry is None:
            fail(f"rule_refs path {ref['path']} is missing from commit {commit_oid}")
        mode, object_type, blob_oid = entry
        if object_type != "blob" or mode not in REGULAR_BLOB_MODES:
            fail(f"rule_refs path {ref['path']} must be a regular tracked blob")
        declared = ref["identity"]
        if declared == blob_oid:
            continue
        try:
            blob_bytes = run_git(resolved_repo, ["cat-file", "blob", blob_oid])
        except ValidationError as error:
            fail(f"rule_refs blob could not be read: {error}")
        blob_sha256 = sha256(blob_bytes)
        if declared in {blob_sha256, f"sha256:{blob_sha256}"}:
            continue
        if OID.fullmatch(declared) is not None or declared.startswith("sha256:"):
            fail(
                f"rule_refs identity for {ref['path']} does not match commit {commit_oid}"
            )
        fail(
            f"rule_refs identity for {ref['path']} must match the tracked blob OID or SHA-256"
        )


def ensure_off_delivery_paths(repository: Path, paths: list[Path]) -> None:
    try:
        root = repository.resolve(strict=True)
    except OSError as error:
        fail(f"repository could not be resolved: {error}")
    for path in paths:
        resolved = path.absolute().resolve(strict=False)
        if resolved.is_relative_to(root):
            fail(f"Tracker Policy records must be off-delivery: {path}")


def validate_receipt_tracker_policy(
    receipt: dict[str, Any], *, reread_record: bool = False
) -> dict[str, Any] | None:
    raw = receipt.get("tracker_policy")
    if raw is None:
        return None
    entry = require_object(raw, "receipt.tracker_policy")
    require_exact_fields(entry, RECEIPT_POLICY_FIELDS, "receipt.tracker_policy")
    common = _validate_policy_common(
        {"run_id": receipt["run_id"], **entry}, "receipt.tracker_policy"
    )
    expected_key = compute_policy_key(common)
    policy_key = require_sha256(
        entry["policy_key"], "receipt.tracker_policy.policy_key"
    )
    if policy_key != expected_key:
        fail("receipt.tracker_policy.policy_key does not match its fields")
    policy_path = Path(
        require_text(entry["policy_path"], "receipt.tracker_policy.policy_path")
    )
    policy_sha256 = require_sha256(
        entry["policy_sha256"], "receipt.tracker_policy.policy_sha256"
    )
    if reread_record:
        record_bytes = read_regular_file(
            policy_path, "receipt.tracker_policy.policy_path"
        )
        if sha256(record_bytes) != policy_sha256:
            fail("Tracker Policy Record SHA-256 does not match receipt")
        record = validate_policy_record(parse_json(record_bytes, "policy record"))
        if record["run_id"] != receipt["run_id"]:
            fail("Tracker Policy Record run_id does not match receipt")
        if record["policy_key"] != policy_key:
            fail("Tracker Policy Record policy_key does not match receipt")
    return {
        "policy_key": policy_key,
        "mode": common["mode"],
        "authoritative_paths": common["authoritative_paths"],
        "rule_refs": common["rule_refs"],
        "definition_paths": common["definition_paths"],
        "tracker_paths": common["tracker_paths"],
        "update_scope": common["update_scope"],
        "rationale": common["rationale"],
        "stateful_tracker_decision": common["stateful_tracker_decision"],
        "policy_path": str(policy_path.resolve(strict=False)),
        "policy_sha256": policy_sha256,
    }


def effective_ticket_dispositions(
    receipt: dict[str, Any], *, verify_evidence: bool = False
) -> dict[str, dict[str, Any]]:
    raw = receipt.get("ticket_dispositions", [])
    if not isinstance(raw, list):
        fail("receipt.ticket_dispositions must be an array")
    seen_claims: set[tuple[str, int]] = set()
    by_ticket: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw):
        label = f"receipt.ticket_dispositions[{index}]"
        item = require_object(item, label)
        ticket_id = require_identity(item.get("ticket_id"), f"{label}.ticket_id")
        claim_generation = require_integer(
            item.get("claim_generation"), f"{label}.claim_generation", minimum=1
        )
        disposition = require_text(
            item.get("disposition"), f"{label}.disposition", safe_name=True
        )
        if disposition not in DISPOSITIONS:
            fail(f"{label}.disposition is unsupported")
        claim_key = (ticket_id, claim_generation)
        if claim_key in seen_claims:
            fail(f"{label} duplicates ticket_id and claim_generation")
        seen_claims.add(claim_key)
        if verify_evidence:
            evidence_refs = item.get("evidence_refs")
            if not isinstance(evidence_refs, list) or not evidence_refs:
                fail(f"{label}.evidence_refs must be a non-empty array")
            for ref_index, ref in enumerate(evidence_refs):
                ref_label = f"{label}.evidence_refs[{ref_index}]"
                ref = require_object(ref, ref_label)
                require_exact_fields(ref, {"id", "path", "sha256"}, ref_label)
                require_identity(ref["id"], f"{ref_label}.id")
                ref_path = Path(require_text(ref["path"], f"{ref_label}.path"))
                declared = require_sha256(ref["sha256"], f"{ref_label}.sha256")
                if sha256(read_regular_file(ref_path, f"{ref_label}.path")) != declared:
                    fail(f"{ref_label}.path SHA-256 does not match")
        previous = by_ticket.get(ticket_id)
        if previous is None or claim_generation > previous["claim_generation"]:
            by_ticket[ticket_id] = {
                "ticket_id": ticket_id,
                "claim_generation": claim_generation,
                "disposition": disposition,
                "claim_owner_id": item.get("claim_owner_id"),
            }
    return by_ticket


def compute_pending_tracker_updates(
    receipt: dict[str, Any], policy_entry: dict[str, Any]
) -> list[dict[str, Any]]:
    if policy_entry["mode"] == "none":
        return []
    effective = effective_ticket_dispositions(receipt)
    checkpoints = receipt.get("tracker_checkpoints", [])
    if not isinstance(checkpoints, list):
        fail("receipt.tracker_checkpoints must be an array")
    covered: set[tuple[str, int, str]] = set()
    for item in checkpoints:
        if not isinstance(item, dict):
            fail("receipt.tracker_checkpoints entry must be a JSON object")
        if item.get("policy_key") != policy_entry["policy_key"]:
            continue
        dispositions = item.get("ticket_dispositions", [])
        if not isinstance(dispositions, list):
            fail("checkpoint ticket_dispositions must be an array")
        for bound in dispositions:
            if not isinstance(bound, dict):
                fail("checkpoint ticket_dispositions entry must be a JSON object")
            covered.add(
                (
                    str(bound.get("ticket_id")),
                    int(bound.get("claim_generation", -1)),
                    str(bound.get("disposition")),
                )
            )
    pending = []
    for ticket_id in sorted(effective):
        disp = effective[ticket_id]
        key = (ticket_id, disp["claim_generation"], disp["disposition"])
        if key not in covered:
            pending.append(
                {
                    "ticket_id": ticket_id,
                    "claim_generation": disp["claim_generation"],
                    "disposition": disp["disposition"],
                    "policy_key": policy_entry["policy_key"],
                }
            )
    return pending


def _record_policy_locked(
    receipt_path: Path,
    policy_path: Path,
    output_path: Path,
    expected_generation: int,
    expected_receipt_digest: str,
    repository: Path | None,
    commit: str | None,
) -> tuple[str, dict[str, Any], int]:
    safe_receipt_target(receipt_path)
    receipt_bytes = read_regular_file(receipt_path, "receipt")
    if sha256(receipt_bytes) != expected_receipt_digest:
        fail("receipt SHA-256 does not match")
    receipt = validate_receipt(parse_json(receipt_bytes, "receipt"))
    if receipt["coordinator_generation"] != expected_generation:
        fail("receipt coordinator_generation does not match")

    policy = validate_policy(
        parse_json(read_regular_file(policy_path, "policy"), "policy")
    )
    if policy["run_id"] != receipt["run_id"]:
        fail("receipt and policy run_id do not match")
    if (repository is None) != (commit is None):
        fail("--repository and --commit must be supplied together")
    if repository is not None and commit is not None:
        verify_policy_against_commit(repository, commit, policy)
        ensure_off_delivery_paths(repository, [policy_path, output_path])

    record = create_policy_record(policy)
    record_bytes = canonical_json(record)
    publish_once(output_path, record_bytes, [receipt_path, policy_path])
    entry = {
        "policy_key": record["policy_key"],
        "mode": record["mode"],
        "authoritative_paths": record["authoritative_paths"],
        "rule_refs": record["rule_refs"],
        "definition_paths": record["definition_paths"],
        "tracker_paths": record["tracker_paths"],
        "update_scope": record["update_scope"],
        "rationale": record["rationale"],
        "stateful_tracker_decision": record["stateful_tracker_decision"],
        "policy_path": str(output_path.resolve()),
        "policy_sha256": sha256(record_bytes),
    }
    existing = validate_receipt_tracker_policy(receipt)
    if existing == entry:
        return "already-recorded", entry, expected_generation
    claims = receipt.get("claims", [])
    if not isinstance(claims, list):
        fail("receipt.claims must be an array")
    if claims:
        fail("cannot record or change tracker_policy while live claims exist")
    receipt["tracker_policy"] = entry
    receipt["pending_tracker_updates"] = compute_pending_tracker_updates(receipt, entry)
    receipt["coordinator_generation"] += 1
    replace_receipt(receipt_path, receipt_bytes, canonical_json(receipt), locked=True)
    return "recorded", entry, expected_generation + 1


def record_tracker_policy(
    receipt_path: Path,
    policy_path: Path,
    output_path: Path,
    expected_generation: int,
    expected_receipt_digest: str,
    repository: Path | None = None,
    commit: str | None = None,
) -> tuple[str, dict[str, Any], int]:
    with receipt_lock(receipt_path):
        return _record_policy_locked(
            receipt_path,
            policy_path,
            output_path,
            expected_generation,
            expected_receipt_digest,
            repository,
            commit,
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and CAS-record a Coordinator-owned Tracker Policy."
    )
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-generation", required=True, type=int)
    parser.add_argument("--expected-receipt-sha256", required=True)
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    arguments = parser.parse_args()
    try:
        status, entry, generation = record_tracker_policy(
            arguments.receipt,
            arguments.policy,
            arguments.output,
            require_integer(arguments.expected_generation, "expected_generation"),
            require_sha256(
                arguments.expected_receipt_sha256, "expected_receipt_sha256"
            ),
            arguments.repository,
            arguments.commit,
        )
    except (OSError, ReceiptIndexError, RecordError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": status,
                "kind": RECORD_KIND,
                "mode": entry["mode"],
                "policy_key": entry["policy_key"],
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
