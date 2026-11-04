"""Coordinator-owned Tracker Policy and Tracker Checkpoint validation and CAS."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from lib.common import (
    DISPOSITIONS,
    OID,
    SCHEMA_VERSION,
    canonical_json,
    fail,
    parse_json,
    path_contains,
    paths_overlap,
    read_regular_file,
    require_exact_fields,
    require_identity,
    require_integer,
    require_object,
    require_oid,
    require_relative_path,
    require_sha256,
    require_string_array,
    require_text,
    sha256,
    sort_paths,
    validate_evidence_refs,
    validate_ticket_base,
)
from lib.git_ops import (
    INDEX_PATH,
    REGULAR_BLOB_MODES,
    ValidationError,
    git_probe,
    read_direct_ref,
    run_git,
    tree_entries_for_paths,
    validate_definition_index,
)
from lib.receipt import (
    receipt_lock,
    replace_receipt,
    safe_receipt_target,
    validate_receipt,
)

POLICY_KIND = "Tracker Policy"
LEGACY_POLICY_RECORD_KIND = "Tracker Policy Record"
CHECKPOINT_KIND = "Tracker Checkpoint"
LEGACY_CHECKPOINT_RECORD_KIND = "Tracker Checkpoint Record"
MODES = {"none", "in_repo", "external_snapshot"}
UPDATE_SCOPES = {"none", "per_ticket", "batched"}
ALLOWED_DIFF_MODES = {"000000", *REGULAR_BLOB_MODES}

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
RECEIPT_POLICY_CORE_FIELDS = {
    "policy_key",
    "mode",
    "authoritative_paths",
    "rule_refs",
    "definition_paths",
    "tracker_paths",
    "update_scope",
    "rationale",
    "stateful_tracker_decision",
}
LEGACY_RECEIPT_POLICY_FIELDS = {"policy_path", "policy_sha256"}

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
RECEIPT_CHECKPOINT_CORE_FIELDS = {
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
}
LEGACY_RECEIPT_CHECKPOINT_FIELDS = {"record_path", "record_sha256"}


# --- Tracker Policy ---


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


def _validate_legacy_policy_record(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "policy record")
    expected = REQUIRED_POLICY_FIELDS | OPTIONAL_POLICY_FIELDS | {"policy_key"}
    require_exact_fields(payload, expected, "policy record")
    if (
        payload["schema_version"] != SCHEMA_VERSION
        or payload["kind"] != LEGACY_POLICY_RECORD_KIND
    ):
        fail("policy record schema_version or kind is unsupported")
    common = _validate_policy_common(payload, "policy record")
    expected_key = compute_policy_key(common)
    declared_key = require_sha256(payload["policy_key"], "policy record.policy_key")
    if declared_key != expected_key:
        fail("policy record policy_key does not match its fields")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": LEGACY_POLICY_RECORD_KIND,
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
            fail(f"Tracker Policy files must be off-delivery: {path}")


def validate_receipt_tracker_policy(
    receipt: dict[str, Any], *, reread_record: bool = False
) -> dict[str, Any] | None:
    raw = receipt.get("tracker_policy")
    if raw is None:
        return None
    entry = require_object(raw, "receipt.tracker_policy")
    actual_fields = set(entry)
    has_legacy = bool(actual_fields & LEGACY_RECEIPT_POLICY_FIELDS)
    expected_fields = (
        RECEIPT_POLICY_CORE_FIELDS | LEGACY_RECEIPT_POLICY_FIELDS
        if has_legacy
        else RECEIPT_POLICY_CORE_FIELDS
    )
    require_exact_fields(entry, expected_fields, "receipt.tracker_policy")
    common = _validate_policy_common(
        {"run_id": receipt["run_id"], **entry}, "receipt.tracker_policy"
    )
    expected_key = compute_policy_key(common)
    policy_key = require_sha256(
        entry["policy_key"], "receipt.tracker_policy.policy_key"
    )
    if policy_key != expected_key:
        fail("receipt.tracker_policy.policy_key does not match its fields")
    normalized: dict[str, Any] = {
        "policy_key": policy_key,
        "mode": common["mode"],
        "authoritative_paths": common["authoritative_paths"],
        "rule_refs": common["rule_refs"],
        "definition_paths": common["definition_paths"],
        "tracker_paths": common["tracker_paths"],
        "update_scope": common["update_scope"],
        "rationale": common["rationale"],
        "stateful_tracker_decision": common["stateful_tracker_decision"],
    }
    if has_legacy:
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
            record = _validate_legacy_policy_record(
                parse_json(record_bytes, "policy record")
            )
            if record["run_id"] != receipt["run_id"]:
                fail("Tracker Policy Record run_id does not match receipt")
            if record["policy_key"] != policy_key:
                fail("Tracker Policy Record policy_key does not match receipt")
        normalized["policy_path"] = str(policy_path.resolve(strict=False))
        normalized["policy_sha256"] = policy_sha256
    return normalized


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
            validate_evidence_refs(item.get("evidence_refs"), f"{label}.evidence_refs")
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


def commit_tracker_policy(
    *,
    repository: Path,
    commit: str,
    receipt_path: Path,
    policy_path: Path,
    expected_generation: int,
    expected_receipt_digest: str,
) -> dict[str, Any]:
    expected_generation = require_integer(expected_generation, "expected_generation")
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

        policy = validate_policy(
            parse_json(read_regular_file(policy_path, "policy"), "policy")
        )
        if policy["run_id"] != receipt["run_id"]:
            fail("receipt and policy run_id do not match")
        verify_policy_against_commit(repository, commit, policy)
        ensure_off_delivery_paths(repository, [receipt_path, policy_path])

        policy_key = compute_policy_key(policy)
        entry = {
            "policy_key": policy_key,
            "mode": policy["mode"],
            "authoritative_paths": policy["authoritative_paths"],
            "rule_refs": policy["rule_refs"],
            "definition_paths": policy["definition_paths"],
            "tracker_paths": policy["tracker_paths"],
            "update_scope": policy["update_scope"],
            "rationale": policy["rationale"],
            "stateful_tracker_decision": policy["stateful_tracker_decision"],
        }
        existing = validate_receipt_tracker_policy(receipt)
        if existing is not None:
            existing_core = {key: existing[key] for key in RECEIPT_POLICY_CORE_FIELDS}
            if existing_core == entry:
                return {
                    "status": "already-recorded",
                    "kind": POLICY_KIND,
                    "mode": entry["mode"],
                    "policy_key": entry["policy_key"],
                    "coordinator_generation": expected_generation,
                    "receipt_sha256": expected_receipt_digest,
                }
        claims = receipt.get("claims", [])
        if claims:
            fail("cannot record or change tracker_policy while live claims exist")
        receipt["tracker_policy"] = entry
        receipt["pending_tracker_updates"] = compute_pending_tracker_updates(
            receipt, entry
        )
        receipt["coordinator_generation"] += 1
        new_bytes = canonical_json(receipt)
        replace_receipt(receipt_path, receipt_bytes, new_bytes, locked=True)
        return {
            "status": "recorded",
            "kind": POLICY_KIND,
            "mode": entry["mode"],
            "policy_key": entry["policy_key"],
            "coordinator_generation": receipt["coordinator_generation"],
            "receipt_sha256": sha256(new_bytes),
        }


# --- Tracker Checkpoints ---


def _read_checkpoint_ref(repository: Path, integration_ref: str) -> str:
    try:
        return read_direct_ref(repository, integration_ref)
    except ValidationError as error:
        fail(str(error))
    raise AssertionError("unreachable")


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


def validate_tracker_checkpoint(payload: Any) -> dict[str, Any]:
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


def _validate_legacy_checkpoint_record(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "checkpoint record")
    require_exact_fields(
        payload, CHECKPOINT_FIELDS | {"checkpoint_key"}, "checkpoint record"
    )
    if (
        payload["schema_version"] != SCHEMA_VERSION
        or payload["kind"] != LEGACY_CHECKPOINT_RECORD_KIND
    ):
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
        "kind": LEGACY_CHECKPOINT_RECORD_KIND,
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

    live_ref = _read_checkpoint_ref(toplevel, checkpoint["integration_ref"])
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
    *,
    check_accepted_tip_base: bool = True,
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
    if check_accepted_tip_base:
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
        actual_fields = set(item)
        has_legacy = bool(actual_fields & LEGACY_RECEIPT_CHECKPOINT_FIELDS)
        expected_fields = (
            RECEIPT_CHECKPOINT_CORE_FIELDS | LEGACY_RECEIPT_CHECKPOINT_FIELDS
            if has_legacy
            else RECEIPT_CHECKPOINT_CORE_FIELDS
        )
        require_exact_fields(item, expected_fields, label)
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
        entry: dict[str, Any] = {
            "checkpoint_key": checkpoint_key,
            **common,
        }
        if has_legacy:
            record_path = Path(
                require_text(item["record_path"], f"{label}.record_path")
            )
            record_sha256 = require_sha256(
                item["record_sha256"], f"{label}.record_sha256"
            )
            record_bytes = read_regular_file(record_path, f"{label}.record_path")
            if sha256(record_bytes) != record_sha256:
                fail(
                    f"{label} Tracker Checkpoint Record SHA-256 does not match receipt"
                )
            record = _validate_legacy_checkpoint_record(
                parse_json(record_bytes, "checkpoint record")
            )
            if record["run_id"] != receipt["run_id"]:
                fail(f"{label} Tracker Checkpoint Record run_id does not match receipt")
            if record["checkpoint_key"] != checkpoint_key:
                fail(
                    f"{label} Tracker Checkpoint Record checkpoint_key does not match receipt"
                )
            entry["record_path"] = str(record_path.resolve())
            entry["record_sha256"] = record_sha256
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
        validated.append(entry)
    return validated


def verify_tracker_checkpoint(
    *,
    repository: Path,
    receipt_path: Path,
    checkpoint_path: Path,
) -> dict[str, Any]:
    receipt = validate_receipt(
        parse_json(read_regular_file(receipt_path, "receipt"), "receipt")
    )
    checkpoint = validate_tracker_checkpoint(
        parse_json(read_regular_file(checkpoint_path, "checkpoint"), "checkpoint")
    )
    if checkpoint["run_id"] != receipt["run_id"]:
        fail("receipt and checkpoint run_id do not match")
    off_delivery = [
        receipt_path,
        checkpoint_path,
        *(Path(item["path"]) for item in checkpoint["evidence_refs"]),
    ]
    toplevel = verify_git_diff_and_identities(
        repository, checkpoint, off_delivery, preflight=True
    )
    policy = validate_receipt_tracker_policy(receipt, reread_record=True)
    verify_policy_and_scope(toplevel, receipt, policy, checkpoint)
    return {
        "status": "verified",
        "kind": CHECKPOINT_KIND,
        "checkpoint_key": compute_checkpoint_key(checkpoint),
        "candidate": checkpoint["candidate"]["commit"],
    }


def commit_tracker_checkpoint(
    *,
    repository: Path,
    receipt_path: Path,
    checkpoint_path: Path,
    expected_generation: int,
    expected_receipt_digest: str,
) -> dict[str, Any]:
    expected_generation = require_integer(expected_generation, "expected_generation")
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

        checkpoint = validate_tracker_checkpoint(
            parse_json(read_regular_file(checkpoint_path, "checkpoint"), "checkpoint")
        )
        if checkpoint["run_id"] != receipt["run_id"]:
            fail("receipt and checkpoint run_id do not match")
        off_delivery = [
            receipt_path,
            checkpoint_path,
            *(Path(item["path"]) for item in checkpoint["evidence_refs"]),
        ]
        toplevel = verify_git_diff_and_identities(
            repository, checkpoint, off_delivery, preflight=False
        )
        checkpoint_key = compute_checkpoint_key(checkpoint)
        expected_entry = {
            "checkpoint_key": checkpoint_key,
            "coordinator_generation": checkpoint["coordinator_generation"],
            "policy_key": checkpoint["policy_key"],
            "integration_ref": checkpoint["integration_ref"],
            "ticket_dispositions": checkpoint["ticket_dispositions"],
            "base": checkpoint["base"],
            "candidate": checkpoint["candidate"],
            "changed_paths": checkpoint["changed_paths"],
            "blob_changes": checkpoint["blob_changes"],
            "evidence_refs": checkpoint["evidence_refs"],
        }
        checkpoints = receipt.setdefault("tracker_checkpoints", [])
        if not isinstance(checkpoints, list):
            fail("receipt.tracker_checkpoints must be an array")
        matching = [
            item
            for item in checkpoints
            if isinstance(item, dict)
            and (
                item.get("checkpoint_key") == checkpoint_key
                or (
                    item.get("policy_key") == checkpoint["policy_key"]
                    and isinstance(item.get("candidate"), dict)
                    and item["candidate"].get("commit")
                    == checkpoint["candidate"]["commit"]
                )
            )
        ]
        if matching:
            core_match = {
                key: matching[0][key]
                for key in RECEIPT_CHECKPOINT_CORE_FIELDS
                if key in matching[0]
            }
            if len(matching) != 1 or core_match != expected_entry:
                fail("receipt already contains a conflicting Tracker Checkpoint")
            verify_policy_and_scope(
                toplevel,
                receipt,
                validate_receipt_tracker_policy(receipt, reread_record=True),
                checkpoint,
                check_accepted_tip_base=False,
            )
            return {
                "status": "already-recorded",
                "kind": CHECKPOINT_KIND,
                "checkpoint_key": checkpoint_key,
                "candidate": checkpoint["candidate"]["commit"],
                "coordinator_generation": expected_generation,
                "receipt_sha256": expected_receipt_digest,
            }

        policy = verify_policy_and_scope(
            toplevel,
            receipt,
            validate_receipt_tracker_policy(receipt, reread_record=True),
            checkpoint,
            check_accepted_tip_base=True,
        )
        if checkpoint["coordinator_generation"] != expected_generation:
            fail("checkpoint coordinator_generation does not match receipt")
        for prior in checkpoints:
            if not isinstance(prior, dict) or not isinstance(
                prior.get("candidate"), dict
            ):
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

        checkpoints.append(expected_entry)
        receipt["accepted_integration_tip"] = checkpoint["candidate"]
        receipt["pending_tracker_updates"] = compute_pending_tracker_updates(
            receipt, policy
        )
        receipt["coordinator_generation"] += 1
        new_bytes = canonical_json(receipt)
        replace_receipt(receipt_path, receipt_bytes, new_bytes, locked=True)
        return {
            "status": "recorded",
            "kind": CHECKPOINT_KIND,
            "checkpoint_key": checkpoint_key,
            "candidate": checkpoint["candidate"]["commit"],
            "coordinator_generation": receipt["coordinator_generation"],
            "receipt_sha256": sha256(new_bytes),
        }
