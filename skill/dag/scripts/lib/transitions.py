"""Promotion packages, local CAS ref promotion, pending transition CAS, dispositions, and terminal audit."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

from lib.artifacts import validate_review_capsule, verify_candidate_review
from lib.common import (
    DISPOSITIONS,
    SCHEMA_VERSION,
    canonical_json,
    fail,
    parse_json,
    publish_once,
    read_regular_file,
    require_exact_fields,
    require_identity,
    require_integer,
    require_object,
    require_oid,
    require_sha256,
    require_string_array,
    require_text,
    require_timestamp,
    sha256,
    validate_evidence_refs,
    validate_ticket_base,
)
from lib.git_ops import (
    ValidationError,
    git_probe,
    parse_git_integer,
    read_direct_ref,
    run_git,
    unique_json_object,
)
from lib.receipt import (
    RECEIPT_KIND,
    receipt_lock,
    replace_receipt,
    safe_receipt_target,
    validate_receipt,
)
from lib.scheduling import validate_claim_entry
from lib.tracker import (
    compute_pending_tracker_updates,
    effective_ticket_dispositions,
    validate_receipt_tracker_checkpoints,
    validate_receipt_tracker_policy,
)

PACKAGE_KIND = "Promotion Evidence Package"
TRANSITION_FIELDS = {
    "schema_version",
    "candidate_kind",
    "integration_ref",
    "base",
    "candidate",
    "candidate_tree",
    "evidence",
}
CANDIDATE_KINDS = {"Promotion Candidate", "DAG Definition Checkpoint"}
PROMOTION_FIELDS = {
    "schema_version",
    "kind",
    "run_id",
    "receipt_generation",
    "ticket_id",
    "owner_id",
    "claim_generation",
    "ticket_base",
    "candidate",
    "review_context_key",
    "review_record_key",
    "review_artifact_sha256",
    "review_context_ref",
    "review_record_ref",
    "artifact_root",
    "fresh_review_required",
    "promotion_allowed",
}
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
OBJECT_ID_RE = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")

DISPOSITION_DECISION_KIND = "Ticket Disposition Decision"
DISPOSITION_KIND = "Ticket Disposition"
BASELINE_KIND = "Baseline Satisfaction Evidence"
DISPOSITION_DECISION_FIELDS = {
    "schema_version",
    "kind",
    "run_id",
    "coordinator_generation",
    "ticket_id",
    "claim_generation",
    "disposition",
    "rule_identity",
    "decided_by",
    "decided_at",
    "rationale",
    "evidence_refs",
}
BASELINE_FIELDS = {
    "schema_version",
    "kind",
    "run_id",
    "ticket_id",
    "owner_id",
    "claim_generation",
    "ticket_base",
    "disposition",
    "evidence_refs",
}

AUDIT_KIND = "Terminal Outcome Audit"
TERMINAL_EVIDENCE_KIND = "Terminal Outcome Evidence"
OUTCOMES = {"Complete", "Stalled"}
OBLIGATION_STATUSES = {"Accepted", "Superseded", "Open", "Blocked"}
GATE_RESULTS = {"pass", "fail", "unknown", "not-run"}


def publish_promotion_package(
    *,
    receipt_path: Path,
    ticket_id: str,
    context_path: Path,
    review_record_path: Path,
    artifact_root: Path,
    expected_tip_commit: str,
    expected_tip_tree: str,
    output_path: Path,
) -> dict[str, Any]:
    ticket_id = require_identity(ticket_id, "ticket_id")
    expected_tip_commit = require_oid(expected_tip_commit, "expected_tip_commit")
    expected_tip_tree = require_oid(expected_tip_tree, "expected_tip_tree")
    receipt = validate_receipt(
        parse_json(read_regular_file(receipt_path, "receipt"), "receipt")
    )
    claims = receipt.get("claims", [])
    matching = [
        validate_claim_entry(item, f"receipt.claims[{index}]")
        for index, item in enumerate(claims)
        if isinstance(item, dict) and item.get("ticket_id") == ticket_id
    ]
    if len(matching) != 1:
        fail("receipt must contain exactly one live claim for the Ticket")
    claim = matching[0]
    capsule = validate_review_capsule(
        parse_json(
            read_regular_file(context_path, "context capsule"), "context capsule"
        )
    )
    if receipt["run_id"] != capsule["run_id"]:
        fail("receipt and context capsule run_id do not match")
    if claim["ticket_id"] != capsule["ticket_id"]:
        fail("live claim and context capsule ticket_id do not match")
    if claim["owner_id"] != capsule["owner_id"]:
        fail("live claim and context capsule owner_id do not match")
    if claim["claim_generation"] != capsule["claim_generation"]:
        fail("live claim and context capsule claim_generation do not match")
    if claim["ticket_base"] != capsule["ticket_base"]:
        fail("live claim and context capsule Ticket Base do not match")
    receipt_tip = receipt.get("accepted_integration_tip")
    if receipt_tip is None:
        fail("Promotion requires receipt.accepted_integration_tip")
    receipt_tip = validate_ticket_base(receipt_tip, "receipt.accepted_integration_tip")
    if receipt_tip != claim["ticket_base"]:
        fail("receipt Accepted Integration Tip does not match live claim Ticket Base")
    if receipt_tip["commit"] != expected_tip_commit:
        fail("current Accepted Integration Tip commit does not match Ticket Base")
    if receipt_tip["tree"] != expected_tip_tree:
        fail("current Accepted Integration Tip tree does not match Ticket Base")
    if capsule["ticket_base"]["commit"] != expected_tip_commit:
        fail("current Accepted Integration Tip commit does not match Ticket Base")
    if capsule["ticket_base"]["tree"] != expected_tip_tree:
        fail("current Accepted Integration Tip tree does not match Ticket Base")
    context_bytes = read_regular_file(context_path, "context capsule")
    review_record_bytes = read_regular_file(
        review_record_path, "candidate review record"
    )
    try:
        artifact_root_value = str(artifact_root.resolve(strict=True))
    except OSError as error:
        fail(f"artifact_root could not be resolved: {error}")
    review_result, handle = verify_candidate_review(
        review_record_path,
        context_path,
        artifact_root,
        expected_tip_commit,
        expected_tip_tree,
        capsule["candidate"]["commit"],
        capsule["candidate"]["tree"],
        capsule["candidate"]["range"],
    )
    package = {
        "schema_version": SCHEMA_VERSION,
        "kind": PACKAGE_KIND,
        "run_id": receipt["run_id"],
        "receipt_generation": receipt["coordinator_generation"],
        "ticket_id": capsule["ticket_id"],
        "owner_id": capsule["owner_id"],
        "claim_generation": capsule["claim_generation"],
        "ticket_base": capsule["ticket_base"],
        "candidate": capsule["candidate"],
        "review_context_key": review_result["review_context_key"],
        "review_record_key": review_result["review_record_key"],
        "review_artifact_sha256": handle["artifact_sha256"],
        "review_context_ref": {
            "path": str(context_path.resolve()),
            "sha256": sha256(context_bytes),
        },
        "review_record_ref": {
            "path": str(review_record_path.resolve()),
            "sha256": sha256(review_record_bytes),
        },
        "artifact_root": artifact_root_value,
        "fresh_review_required": True,
        "promotion_allowed": True,
    }
    status = publish_once(
        output_path,
        canonical_json(package),
        [receipt_path, context_path, review_record_path],
    )
    return {
        "status": status,
        "kind": PACKAGE_KIND,
        "ticket_id": package["ticket_id"],
        "promotion_allowed": True,
        "review_record_key": package["review_record_key"],
    }


def _read_regular_file_strict(path: Path) -> bytes:
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValidationError(f"{path}: must be a regular file, not a symlink")
    return path.read_bytes()


def read_transition_record(path: Path, digest: str) -> tuple[bytes, dict[str, object]]:
    content = _read_regular_file_strict(path)
    if hashlib.sha256(content).hexdigest() != digest:
        raise ValidationError("pending transition SHA-256 does not match")
    try:
        payload = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=unique_json_object,
            parse_int=parse_git_integer,
        )
    except (UnicodeDecodeError, ValueError) as error:
        raise ValidationError(
            f"pending transition must be UTF-8 JSON: {error}"
        ) from error
    if not isinstance(payload, dict) or set(payload) != TRANSITION_FIELDS:
        raise ValidationError("pending transition fields do not match schema_version 1")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise ValidationError("schema_version must be the integer 1")
    if (
        not isinstance(payload["candidate_kind"], str)
        or payload["candidate_kind"] not in CANDIDATE_KINDS
    ):
        raise ValidationError("candidate_kind must name an Integration Transition kind")
    integration_ref = payload["integration_ref"]
    if not isinstance(integration_ref, str) or not integration_ref.startswith(
        "refs/heads/"
    ):
        raise ValidationError("integration_ref must be a full refs/heads/ reference")
    for field in ("base", "candidate", "candidate_tree"):
        value = payload[field]
        if not isinstance(value, str) or OBJECT_ID_RE.fullmatch(value) is None:
            raise ValidationError(f"{field} must be a full lowercase Git object ID")
    if payload["base"] == payload["candidate"]:
        raise ValidationError("candidate must differ from Base")
    evidence = payload["evidence"]
    if not isinstance(evidence, list) or not evidence:
        raise ValidationError("evidence must be a nonempty array")
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ValidationError(
                "each evidence entry must contain exactly path and sha256"
            )
        if (
            not isinstance(item["path"], str)
            or not item["path"]
            or "\0" in item["path"]
        ):
            raise ValidationError(
                "each evidence path must be a nonempty filesystem path"
            )
        item["path"].encode("utf-8")
        if (
            not isinstance(item["sha256"], str)
            or SHA256_RE.fullmatch(item["sha256"]) is None
        ):
            raise ValidationError(
                "each evidence SHA-256 must be 64 lowercase hex digits"
            )
    return content, payload


def _read_promotion_evidence(
    path: Path,
    digest: str,
    transition: dict[str, object],
    frozen_paths: set[Path],
) -> tuple[bytes, dict[str, object]]:
    if SHA256_RE.fullmatch(digest) is None:
        raise ValidationError(
            "--expected-promotion-sha256 must be 64 lowercase hex digits"
        )
    content = _read_regular_file_strict(path)
    if hashlib.sha256(content).hexdigest() != digest:
        raise ValidationError("promotion evidence SHA-256 does not match")
    try:
        package = json.loads(
            content.decode("utf-8"), object_pairs_hook=unique_json_object
        )
    except (UnicodeDecodeError, ValueError) as error:
        raise ValidationError(
            f"promotion evidence must be UTF-8 JSON: {error}"
        ) from error
    if not isinstance(package, dict) or set(package) != PROMOTION_FIELDS:
        raise ValidationError("promotion evidence fields do not match schema_version 1")
    if (
        package["schema_version"] != 1
        or package["kind"] != PACKAGE_KIND
        or package["promotion_allowed"] is not True
        or package["fresh_review_required"] is not True
    ):
        raise ValidationError(
            "promotion evidence is not an allowed fresh-review package"
        )
    package_run_id = require_identity(package["run_id"], "promotion evidence.run_id")
    package_owner_id = require_identity(
        package["owner_id"], "promotion evidence.owner_id"
    )
    package_ticket_id = require_identity(
        package["ticket_id"], "promotion evidence.ticket_id"
    )
    package_claim_generation = require_integer(
        package["claim_generation"], "promotion evidence.claim_generation"
    )
    require_integer(
        package["receipt_generation"], "promotion evidence.receipt_generation"
    )
    package_review_context_key = require_sha256(
        package["review_context_key"], "promotion evidence.review_context_key"
    )
    package_review_record_key = require_sha256(
        package["review_record_key"], "promotion evidence.review_record_key"
    )
    package_review_artifact_sha256 = require_sha256(
        package["review_artifact_sha256"],
        "promotion evidence.review_artifact_sha256",
    )
    base = package["ticket_base"]
    candidate = package["candidate"]
    if not isinstance(base, dict) or set(base) != {"commit", "tree"}:
        raise ValidationError("promotion evidence ticket_base is malformed")
    if not isinstance(candidate, dict) or set(candidate) != {
        "commit",
        "tree",
        "range",
        "commits",
    }:
        raise ValidationError("promotion evidence candidate is malformed")
    if (
        base["commit"] != transition["base"]
        or candidate["commit"] != transition["candidate"]
        or candidate["tree"] != transition["candidate_tree"]
    ):
        raise ValidationError(
            "promotion evidence Base or candidate does not match pending transition"
        )
    if path.resolve(strict=True) not in frozen_paths:
        raise ValidationError(
            "promotion evidence must be part of the frozen Transition evidence"
        )
    context_path, _context_digest = _read_package_file_ref(
        package["review_context_ref"],
        "promotion evidence.review_context_ref",
    )
    review_record_path, _review_record_digest = _read_package_file_ref(
        package["review_record_ref"],
        "promotion evidence.review_record_ref",
    )
    if context_path not in frozen_paths:
        raise ValidationError(
            "review context capsule must be part of the frozen Transition evidence"
        )
    if review_record_path not in frozen_paths:
        raise ValidationError(
            "candidate review record must be part of the frozen Transition evidence"
        )
    artifact_root_value = package["artifact_root"]
    if not isinstance(artifact_root_value, str) or not artifact_root_value:
        raise ValidationError("promotion evidence.artifact_root must be a path string")
    artifact_root = Path(artifact_root_value)
    review_summary, review_handle = verify_candidate_review(
        review_record_path,
        context_path,
        artifact_root,
        str(package["ticket_base"]["commit"]),
        str(package["ticket_base"]["tree"]),
        str(package["candidate"]["commit"]),
        str(package["candidate"]["tree"]),
        str(package["candidate"]["range"]),
    )
    if review_summary["run_id"] != package_run_id:
        raise ValidationError("promotion evidence review run_id does not match")
    if review_summary["ticket_id"] != package_ticket_id:
        raise ValidationError("promotion evidence review ticket_id does not match")
    if review_summary["owner_id"] != package_owner_id:
        raise ValidationError("promotion evidence review owner_id does not match")
    if review_summary["claim_generation"] != package_claim_generation:
        raise ValidationError(
            "promotion evidence review claim_generation does not match"
        )
    if review_summary["review_context_key"] != package_review_context_key:
        raise ValidationError(
            "promotion evidence review_context_key does not match review evidence"
        )
    if review_summary["review_record_key"] != package_review_record_key:
        raise ValidationError(
            "promotion evidence review_record_key does not match review evidence"
        )
    if review_handle["artifact_sha256"] != package_review_artifact_sha256:
        raise ValidationError(
            "promotion evidence review_artifact_sha256 does not match review evidence"
        )
    return content, package


def _read_package_file_ref(value: Any, label: str) -> tuple[Path, str]:
    if not isinstance(value, dict) or set(value) != {"path", "sha256"}:
        raise ValidationError(f"{label} must contain exactly path and sha256")
    path_value = value["path"]
    digest = value["sha256"]
    if not isinstance(path_value, str) or not path_value or "\0" in path_value:
        raise ValidationError(f"{label}.path must be a nonempty filesystem path")
    if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
        raise ValidationError(
            f"{label}.sha256 must be 64 lowercase hexadecimal characters"
        )
    path = Path(path_value)
    content = _read_regular_file_strict(path)
    if hashlib.sha256(content).hexdigest() != digest:
        raise ValidationError(f"{label} SHA-256 does not match")
    return path.resolve(strict=True), digest


def _read_promotion_receipt(
    path: Path,
    digest: str,
    package: dict[str, object],
    transition_digest: str,
) -> bytes:
    if SHA256_RE.fullmatch(digest) is None:
        raise ValidationError(
            "--expected-receipt-sha256 must be 64 lowercase hex digits"
        )
    content = _read_regular_file_strict(path)
    if hashlib.sha256(content).hexdigest() != digest:
        raise ValidationError("promotion receipt SHA-256 does not match")
    receipt = validate_receipt(parse_json(content, "promotion receipt"))
    pending = receipt.get("pending_transition")
    frozen_for_transition = (
        isinstance(pending, dict)
        and pending.get("transition_sha256") == transition_digest
        and receipt["coordinator_generation"] == int(package["receipt_generation"]) + 1  # type: ignore[arg-type]
    )
    if (
        receipt["coordinator_generation"] != package["receipt_generation"]
        and not frozen_for_transition
    ):
        raise ValidationError("promotion receipt generation does not match package")
    if receipt["run_id"] != package["run_id"]:
        raise ValidationError("promotion receipt run_id does not match package")
    claims = [
        validate_claim_entry(item, f"promotion receipt.claims[{index}]")
        for index, item in enumerate(receipt.get("claims", []))
    ]
    matching = [
        item
        for item in claims
        if item["ticket_id"] == package["ticket_id"]
        and item["claim_generation"] == package["claim_generation"]
    ]
    if len(matching) != 1:
        raise ValidationError(
            "promotion receipt does not contain the package live claim"
        )
    claim = matching[0]
    if claim["owner_id"] != package["owner_id"]:
        raise ValidationError("promotion receipt claim owner does not match package")
    if claim["ticket_base"] != package["ticket_base"]:
        raise ValidationError(
            "promotion receipt claim Ticket Base does not match package"
        )
    accepted_tip_value = receipt.get("accepted_integration_tip")
    if accepted_tip_value is None:
        raise ValidationError("promotion receipt must contain accepted_integration_tip")
    accepted_tip = validate_ticket_base(
        accepted_tip_value, "promotion receipt.accepted_integration_tip"
    )
    if accepted_tip != package["ticket_base"]:
        raise ValidationError(
            "promotion receipt Accepted Integration Tip does not match package"
        )
    return content


def _evidence_paths(transition: Path, payload: dict[str, object]) -> list[Path]:
    paths = [transition.parent / str(item["path"]) for item in payload["evidence"]]  # type: ignore[index]
    try:
        resolved = [path.resolve(strict=True) for path in paths]
        record_path = transition.resolve()
    except RuntimeError as error:
        raise ValidationError(str(error)) from error
    if len(resolved) != len(set(resolved)) or record_path in resolved:
        raise ValidationError(
            "evidence paths must be unique and distinct from the transition"
        )
    return paths


def _verify_frozen_files(
    transition: Path,
    content: bytes,
    payload: dict[str, object],
    paths: list[Path],
) -> None:
    if _read_regular_file_strict(transition) != content:
        raise ValidationError("pending transition changed during preflight")
    for item, path in zip(payload["evidence"], paths, strict=True):  # type: ignore[arg-type]
        if (
            hashlib.sha256(_read_regular_file_strict(path)).hexdigest()
            != item["sha256"]
        ):
            raise ValidationError(f"{path}: evidence SHA-256 does not match")


def _worktree_roots(repository: Path, integration_ref: str) -> list[Path]:
    roots = []
    for field in run_git(repository, ["worktree", "list", "--porcelain", "-z"]).split(
        b"\0"
    ):
        if field == b"branch " + integration_ref.encode("utf-8"):
            raise ValidationError("integration_ref is checked out in a worktree")
        if field.startswith(b"worktree "):
            root = Path(os.fsdecode(field[9:]))
            try:
                root = root.resolve()
                root.stat()
            except FileNotFoundError:
                pass
            except RuntimeError as error:
                raise ValidationError(str(error)) from error
            roots.append(root)
    return roots


def _verify_off_delivery(
    repository: Path,
    payload: dict[str, object],
    paths: list[Path],
    roots: list[Path],
) -> None:
    locations = {path: {path.absolute(), path.resolve(strict=True)} for path in paths}
    if not any(
        location.is_relative_to(root)
        for variants in locations.values()
        for location in variants
        for root in roots
    ):
        return
    tracked: set[bytes] = set()
    for revision in (str(payload["base"]), str(payload["candidate"])):
        tracked.update(
            run_git(repository, ["ls-tree", "-r", "-z", "--name-only", revision]).split(
                b"\0"
            )
        )
    tracked.discard(b"")
    for root in roots:
        if not any(
            location.is_relative_to(root)
            for variants in locations.values()
            for location in variants
        ):
            continue
        current_tracked = tracked | set(
            run_git(root, ["ls-files", "--cached", "-z"]).split(b"\0")
        )
        current_tracked.discard(b"")
        for path, variants in locations.items():
            for location in variants:
                if not location.is_relative_to(root):
                    continue
                relative = os.fsencode(location.relative_to(root).as_posix())
                if relative in current_tracked or any(
                    relative.startswith(name + b"/") for name in current_tracked
                ):
                    raise ValidationError(
                        f"{path}: pending transition and evidence must be off-delivery"
                    )


def _verify_objects(repository: Path, payload: dict[str, object]) -> None:
    object_format = run_git(repository, ["rev-parse", "--show-object-format"]).strip()
    oid_length = {b"sha1": 40, b"sha256": 64}.get(object_format)
    if oid_length is None:
        raise ValidationError("unsupported Git object format")
    for field, object_type in (
        ("base", "commit"),
        ("candidate", "commit"),
        ("candidate_tree", "tree"),
    ):
        oid = str(payload[field])
        if len(oid) != oid_length:
            raise ValidationError(
                f"{field} does not match the repository object format"
            )
        try:
            actual_type = run_git(repository, ["cat-file", "-t", oid]).strip()
        except ValidationError as error:
            raise ValidationError(
                f"{field}: could not get object info: {error}"
            ) from error
        if actual_type != object_type.encode():
            raise ValidationError(f"{field} must identify a local {object_type} object")
    tree = (
        run_git(repository, ["rev-parse", f"{payload['candidate']}^{{tree}}"])
        .decode("ascii")
        .strip()
    )
    if tree != payload["candidate_tree"]:
        raise ValidationError("candidate_tree does not match the candidate commit")
    probe = git_probe(
        repository,
        [
            "merge-base",
            "--is-ancestor",
            str(payload["base"]),
            str(payload["candidate"]),
        ],
    )
    if probe.returncode != 0:
        raise ValidationError("Base must be a local ancestor of the candidate")


def promote_local_transition(
    repository: Path,
    transition: Path,
    digest: str,
    promotion_evidence: Path | None = None,
    promotion_evidence_digest: str | None = None,
    promotion_receipt: Path | None = None,
    promotion_receipt_digest: str | None = None,
) -> dict[str, object]:
    if SHA256_RE.fullmatch(digest) is None:
        raise ValidationError(
            "--expected-transition-sha256 must be 64 lowercase hex digits"
        )
    try:
        repository = repository.resolve(strict=True)
    except RuntimeError as error:
        raise ValidationError(str(error)) from error
    transition = transition.absolute()
    content, payload = read_transition_record(transition, digest)
    paths = _evidence_paths(transition, payload)
    frozen_paths = {path.resolve(strict=True) for path in paths}
    if (promotion_evidence is None) != (promotion_evidence_digest is None):
        raise ValidationError(
            "promotion evidence path and SHA-256 must be supplied together"
        )
    if promotion_evidence is not None and (
        promotion_receipt is None or promotion_receipt_digest is None
    ):
        raise ValidationError(
            "promotion evidence requires current Receipt path and SHA-256"
        )
    if (promotion_receipt is None) != (promotion_receipt_digest is None):
        raise ValidationError("Receipt path and SHA-256 must be supplied together")
    promotion_content = None
    promotion_package = None
    promotion_receipt_content = None
    if (
        promotion_evidence is not None
        and promotion_evidence_digest is not None
        and promotion_receipt is not None
        and promotion_receipt_digest is not None
    ):
        promotion_content, promotion_package = _read_promotion_evidence(
            promotion_evidence,
            promotion_evidence_digest,
            payload,
            frozen_paths,
        )
        promotion_receipt_content = _read_promotion_receipt(
            promotion_receipt,
            promotion_receipt_digest,
            promotion_package,
            digest,
        )
    repository = Path(
        os.fsdecode(run_git(repository, ["rev-parse", "--show-toplevel"]).strip())
    ).resolve(strict=True)
    integration_ref = str(payload["integration_ref"])
    run_git(repository, ["check-ref-format", integration_ref])
    _verify_objects(repository, payload)
    roots = _worktree_roots(repository, integration_ref)
    _verify_off_delivery(repository, payload, [transition, *paths], roots)
    _verify_frozen_files(transition, content, payload, paths)
    if (
        promotion_evidence is not None
        and promotion_evidence_digest is not None
        and promotion_receipt is not None
    ):
        if _read_regular_file_strict(promotion_evidence) != promotion_content:
            raise ValidationError("promotion evidence changed during preflight")
        if _read_regular_file_strict(promotion_receipt) != promotion_receipt_content:
            raise ValidationError("promotion receipt changed during preflight")

    roots = _worktree_roots(repository, integration_ref)
    _verify_off_delivery(repository, payload, [transition, *paths], roots)
    live = read_direct_ref(repository, integration_ref)
    if live not in {payload["base"], payload["candidate"]}:
        raise ValidationError("integration_ref has drifted from Base and candidate")
    _verify_frozen_files(transition, content, payload, paths)
    if (
        promotion_evidence is not None
        and promotion_evidence_digest is not None
        and promotion_receipt is not None
        and promotion_receipt_digest is not None
    ):
        promotion_content, verified_pkg = _read_promotion_evidence(
            promotion_evidence,
            promotion_evidence_digest,
            payload,
            frozen_paths,
        )
        promotion_receipt_content = _read_promotion_receipt(
            promotion_receipt,
            promotion_receipt_digest,
            verified_pkg,
            digest,
        )
    if live == payload["base"]:
        run_git(
            repository,
            [
                "-c",
                f"core.hooksPath={os.devnull}",
                "update-ref",
                "--no-deref",
                integration_ref,
                str(payload["candidate"]),
                str(payload["base"]),
            ],
        )
        status = "local-promoted"
    else:
        status = "local-already-promoted"
    try:
        if read_direct_ref(repository, integration_ref) != payload["candidate"]:
            raise ValidationError("integration_ref does not match candidate")
    except (OSError, ValidationError, UnicodeError) as error:
        raise ValidationError(
            "local promotion readback failed; preserve pending evidence and inspect the ref before recovery"
        ) from error
    result: dict[str, object] = {
        "status": status,
        "candidate_kind": payload["candidate_kind"],
        "integration_ref": integration_ref,
        "base": payload["base"],
        "candidate": payload["candidate"],
        "candidate_tree": payload["candidate_tree"],
        "transition_sha256": digest,
    }
    if promotion_evidence_digest is not None:
        result["promotion_evidence_sha256"] = promotion_evidence_digest
    return result


def commit_transition_state(
    *,
    receipt_path: Path,
    action: str,
    transition_path: Path,
    expected_transition_digest: str,
    synchronized_commit: str | None,
    expected_generation: int,
    expected_receipt_digest: str,
) -> dict[str, Any]:
    if action not in {"freeze", "complete", "cancel"}:
        fail("transition action must be freeze, complete, or cancel")
    expected_generation = require_integer(expected_generation, "expected_generation")
    expected_receipt_digest = require_sha256(
        expected_receipt_digest, "expected_receipt_sha256"
    )
    expected_transition_digest = require_sha256(
        expected_transition_digest, "expected_transition_sha256"
    )
    if synchronized_commit is not None:
        synchronized_commit = require_oid(synchronized_commit, "synchronized_commit")
        if action != "complete":
            fail("--synchronized-commit is only valid with --action complete")

    try:
        content, payload = read_transition_record(
            transition_path.absolute(), expected_transition_digest
        )
        paths = _evidence_paths(transition_path.absolute(), payload)
        _verify_frozen_files(transition_path.absolute(), content, payload, paths)
    except ValidationError as error:
        fail(str(error))

    pending_entry = {
        "candidate_kind": str(payload["candidate_kind"]),
        "integration_ref": str(payload["integration_ref"]),
        "base": str(payload["base"]),
        "candidate": {
            "commit": str(payload["candidate"]),
            "tree": str(payload["candidate_tree"]),
        },
        "transition_path": str(transition_path.resolve()),
        "transition_sha256": expected_transition_digest,
    }

    with receipt_lock(receipt_path):
        safe_receipt_target(receipt_path)
        receipt_bytes = read_regular_file(receipt_path, "receipt")
        if sha256(receipt_bytes) != expected_receipt_digest:
            fail("receipt SHA-256 does not match")
        receipt = validate_receipt(parse_json(receipt_bytes, "receipt"))
        if receipt["coordinator_generation"] != expected_generation:
            fail("receipt coordinator_generation does not match")
        if (
            "integration_ref" in receipt
            and receipt["integration_ref"] is not None
            and receipt["integration_ref"] != pending_entry["integration_ref"]
        ):
            fail("transition integration_ref does not match receipt.integration_ref")

        current_pending = receipt.get("pending_transition")
        if action == "freeze":
            if current_pending == pending_entry:
                return {
                    "status": "already-frozen",
                    "kind": RECEIPT_KIND,
                    "candidate_kind": pending_entry["candidate_kind"],
                    "candidate": pending_entry["candidate"]["commit"],
                    "coordinator_generation": expected_generation,
                    "receipt_sha256": expected_receipt_digest,
                }
            if current_pending is not None:
                fail("receipt already has an active pending_transition")
            accepted_tip = receipt.get("accepted_integration_tip")
            if accepted_tip is not None:
                tip = validate_ticket_base(
                    accepted_tip, "receipt.accepted_integration_tip"
                )
                if tip["commit"] != pending_entry["base"]:
                    fail(
                        "transition base does not match receipt.accepted_integration_tip"
                    )
            receipt["pending_transition"] = pending_entry
            status = "frozen"
        elif action == "cancel":
            if (
                current_pending is None
                and receipt.get("last_cancelled_transition_sha256")
                == expected_transition_digest
            ):
                return {
                    "status": "already-cancelled",
                    "kind": RECEIPT_KIND,
                    "candidate_kind": pending_entry["candidate_kind"],
                    "candidate": pending_entry["candidate"]["commit"],
                    "coordinator_generation": expected_generation,
                    "receipt_sha256": expected_receipt_digest,
                }
            if current_pending != pending_entry:
                fail("receipt pending_transition does not match transition to cancel")
            receipt["pending_transition"] = None
            receipt["last_cancelled_transition_sha256"] = expected_transition_digest
            status = "cancelled"
        else:
            if (
                synchronized_commit is not None
                and synchronized_commit != pending_entry["candidate"]["commit"]
            ):
                fail("synchronized_commit does not match transition candidate commit")
            if (
                current_pending is None
                and receipt.get("accepted_integration_tip")
                == pending_entry["candidate"]
                and receipt.get("last_completed_transition_sha256")
                == expected_transition_digest
            ):
                return {
                    "status": "already-completed",
                    "kind": RECEIPT_KIND,
                    "candidate_kind": pending_entry["candidate_kind"],
                    "candidate": pending_entry["candidate"]["commit"],
                    "coordinator_generation": expected_generation,
                    "receipt_sha256": expected_receipt_digest,
                }
            if current_pending != pending_entry:
                fail("receipt pending_transition does not match transition to complete")
            receipt["pending_transition"] = None
            receipt["accepted_integration_tip"] = pending_entry["candidate"]
            receipt["last_completed_transition_sha256"] = expected_transition_digest
            if synchronized_commit is not None:
                receipt["last_synchronized_commit"] = synchronized_commit
            status = "completed"

        receipt["coordinator_generation"] += 1
        new_bytes = canonical_json(receipt)
        replace_receipt(receipt_path, receipt_bytes, new_bytes, locked=True)
        return {
            "status": status,
            "kind": RECEIPT_KIND,
            "candidate_kind": pending_entry["candidate_kind"],
            "candidate": pending_entry["candidate"]["commit"],
            "coordinator_generation": receipt["coordinator_generation"],
            "receipt_sha256": sha256(new_bytes),
        }


def validate_disposition_decision(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "decision")
    require_exact_fields(payload, DISPOSITION_DECISION_FIELDS, "decision")
    if (
        payload["schema_version"] != SCHEMA_VERSION
        or payload["kind"] != DISPOSITION_DECISION_KIND
    ):
        fail("decision schema_version or kind is unsupported")
    disposition = require_text(
        payload["disposition"], "decision.disposition", safe_name=True
    )
    if disposition not in DISPOSITIONS:
        fail("decision.disposition is unsupported")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": DISPOSITION_DECISION_KIND,
        "run_id": require_identity(payload["run_id"], "decision.run_id"),
        "coordinator_generation": require_integer(
            payload["coordinator_generation"], "decision.coordinator_generation"
        ),
        "ticket_id": require_identity(payload["ticket_id"], "decision.ticket_id"),
        "claim_generation": require_integer(
            payload["claim_generation"], "decision.claim_generation"
        ),
        "disposition": disposition,
        "rule_identity": require_identity(
            payload["rule_identity"], "decision.rule_identity"
        ),
        "decided_by": require_identity(payload["decided_by"], "decision.decided_by"),
        "decided_at": require_timestamp(payload["decided_at"], "decision.decided_at"),
        "rationale": require_text(payload["rationale"], "decision.rationale"),
        "evidence_refs": validate_evidence_refs(
            payload["evidence_refs"], "decision.evidence_refs"
        ),
    }


def _validate_disposition_promotion_package(
    path: Path,
    digest: str,
    decision: dict[str, Any],
    claim: dict[str, Any],
    receipt: dict[str, Any],
) -> str:
    content = read_regular_file(path, "promotion evidence")
    if sha256(content) != digest:
        fail("promotion evidence SHA-256 does not match")
    package = require_object(
        parse_json(content, "promotion evidence"), "promotion evidence"
    )
    require_exact_fields(package, PROMOTION_FIELDS, "promotion evidence")
    if (
        package["schema_version"] != 1
        or package["kind"] != PACKAGE_KIND
        or package["promotion_allowed"] is not True
        or package["fresh_review_required"] is not True
    ):
        fail("promotion evidence is not allowed")
    if package["run_id"] != decision["run_id"]:
        fail("promotion evidence run_id does not match decision")
    if package["ticket_id"] != decision["ticket_id"]:
        fail("promotion evidence ticket_id does not match decision")
    if package["claim_generation"] != decision["claim_generation"]:
        fail("promotion evidence claim_generation does not match decision")
    candidate = package.get("candidate")
    candidate_tip = (
        {"commit": candidate.get("commit"), "tree": candidate.get("tree")}
        if isinstance(candidate, dict)
        else None
    )
    completed_for_candidate = (
        candidate_tip is not None
        and receipt.get("accepted_integration_tip") == candidate_tip
        and isinstance(receipt.get("last_completed_transition_sha256"), str)
        and decision["coordinator_generation"]
        in {package["receipt_generation"] + 1, package["receipt_generation"] + 2}
    )
    if (
        package["receipt_generation"] != decision["coordinator_generation"]
        and not completed_for_candidate
    ):
        fail("promotion evidence receipt_generation does not match decision")
    if package["owner_id"] != claim.get("owner_id"):
        fail("promotion evidence owner_id does not match live claim")
    if package["ticket_base"] != claim.get("ticket_base"):
        fail("promotion evidence Ticket Base does not match live claim")
    return digest


def _validate_baseline_package(
    path: Path,
    digest: str,
    decision: dict[str, Any],
    claim: dict[str, Any],
) -> str:
    content = read_regular_file(path, "baseline evidence")
    if sha256(content) != digest:
        fail("baseline evidence SHA-256 does not match")
    package = require_object(
        parse_json(content, "baseline evidence"), "baseline evidence"
    )
    require_exact_fields(package, BASELINE_FIELDS, "baseline evidence")
    if package["schema_version"] != SCHEMA_VERSION or package["kind"] != BASELINE_KIND:
        fail("baseline evidence schema_version or kind is unsupported")
    if package["run_id"] != decision["run_id"]:
        fail("baseline evidence run_id does not match decision")
    if package["ticket_id"] != decision["ticket_id"]:
        fail("baseline evidence ticket_id does not match decision")
    if package["owner_id"] != claim.get("owner_id"):
        fail("baseline evidence owner_id does not match live claim")
    if package["claim_generation"] != decision["claim_generation"]:
        fail("baseline evidence claim_generation does not match decision")
    if package["ticket_base"] != claim.get("ticket_base"):
        fail("baseline evidence Ticket Base does not match live claim")
    if package["disposition"] != decision["disposition"]:
        fail("baseline evidence disposition does not match decision")
    if (
        validate_evidence_refs(
            package["evidence_refs"], "baseline evidence.evidence_refs"
        )
        != decision["evidence_refs"]
    ):
        fail("baseline evidence references do not match decision evidence")
    return digest


def _validate_disposition_evidence(
    decision: dict[str, Any],
    claim: dict[str, Any],
    receipt: dict[str, Any],
    promotion_path: Path | None,
    promotion_digest: str | None,
    baseline_path: Path | None,
    baseline_digest: str | None,
) -> tuple[str | None, str | None]:
    if decision["disposition"] == "Accepted":
        if (promotion_path is None) == (baseline_path is None):
            fail(
                "Accepted disposition requires exactly one promotion or baseline evidence"
            )
        if promotion_path is not None:
            if promotion_digest is None or baseline_digest is not None:
                fail("promotion evidence path and SHA-256 must be supplied together")
            return (
                _validate_disposition_promotion_package(
                    promotion_path,
                    require_sha256(promotion_digest, "expected_promotion_sha256"),
                    decision,
                    claim,
                    receipt,
                ),
                None,
            )
        assert baseline_path is not None
        if baseline_digest is None or promotion_digest is not None:
            fail("baseline evidence path and SHA-256 must be supplied together")
        checked_baseline = require_sha256(baseline_digest, "expected_baseline_sha256")
        return (
            None,
            _validate_baseline_package(
                baseline_path,
                checked_baseline,
                decision,
                claim,
            ),
        )
    if any(
        value is not None
        for value in (promotion_path, promotion_digest, baseline_path, baseline_digest)
    ):
        fail("Superseded disposition cannot carry promotion or baseline evidence")
    return None, None


def _build_disposition_entry(
    decision: dict[str, Any],
    promotion_sha: str | None,
    baseline_sha: str | None,
    ticket_base: Any,
    claim_owner_id: Any,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": DISPOSITION_KIND,
        "run_id": decision["run_id"],
        "coordinator_generation": decision["coordinator_generation"],
        "ticket_id": decision["ticket_id"],
        "claim_generation": decision["claim_generation"],
        "disposition": decision["disposition"],
        "rule_identity": decision["rule_identity"],
        "decided_by": decision["decided_by"],
        "decided_at": decision["decided_at"],
        "rationale": decision["rationale"],
        "evidence_refs": decision["evidence_refs"],
        "promotion_evidence_sha256": promotion_sha,
        "baseline_evidence_sha256": baseline_sha,
        "ticket_base": ticket_base,
        "claim_owner_id": claim_owner_id,
    }


def commit_ticket_disposition(
    *,
    receipt_path: Path,
    decision_path: Path,
    promotion_path: Path | None,
    promotion_digest: str | None,
    baseline_path: Path | None,
    baseline_digest: str | None,
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
        decision = validate_disposition_decision(
            parse_json(read_regular_file(decision_path, "decision"), "decision")
        )
        if decision["run_id"] != receipt["run_id"]:
            fail("receipt and decision run_id do not match")
        policy = validate_receipt_tracker_policy(receipt)
        dispositions = receipt.setdefault("ticket_dispositions", [])
        existing = [
            item
            for item in dispositions
            if isinstance(item, dict)
            and item.get("ticket_id") == decision["ticket_id"]
            and item.get("claim_generation") == decision["claim_generation"]
        ]
        if existing:
            if len(existing) != 1:
                fail("receipt contains duplicate dispositions for this claim")
            current = existing[0]
            existing_claim = (
                {
                    "owner_id": current.get("claim_owner_id"),
                    "ticket_base": current.get("ticket_base"),
                }
                if decision["disposition"] == "Accepted"
                else {}
            )
            promotion_sha, baseline_sha = _validate_disposition_evidence(
                decision,
                existing_claim,
                receipt,
                promotion_path,
                promotion_digest,
                baseline_path,
                baseline_digest,
            )
            expected = _build_disposition_entry(
                decision,
                promotion_sha,
                baseline_sha,
                current.get("ticket_base"),
                current.get("claim_owner_id"),
            )
            if current == expected:
                return {
                    "status": "already-recorded",
                    "kind": DISPOSITION_KIND,
                    "ticket_id": current["ticket_id"],
                    "disposition": current["disposition"],
                    "coordinator_generation": expected_generation,
                    "receipt_sha256": expected_receipt_digest,
                }
            fail("receipt already contains a different disposition for this claim")

        if decision["coordinator_generation"] != expected_generation:
            fail("decision coordinator_generation does not match receipt")
        claims = receipt.get("claims", [])
        matches = [
            item
            for item in claims
            if isinstance(item, dict)
            and item.get("ticket_id") == decision["ticket_id"]
            and item.get("claim_generation") == decision["claim_generation"]
        ]
        if len(matches) != 1:
            fail("receipt must contain exactly one live claim matching the decision")
        claim = matches[0]
        promotion_sha, baseline_sha = _validate_disposition_evidence(
            decision,
            claim,
            receipt,
            promotion_path,
            promotion_digest,
            baseline_path,
            baseline_digest,
        )
        entry = _build_disposition_entry(
            decision,
            promotion_sha,
            baseline_sha,
            claim.get("ticket_base"),
            claim.get("owner_id"),
        )
        receipt["claims"] = [
            item
            for item in claims
            if not (
                isinstance(item, dict)
                and item.get("ticket_id") == decision["ticket_id"]
                and item.get("claim_generation") == decision["claim_generation"]
            )
        ]
        dispositions.append(entry)
        if policy is not None:
            receipt["pending_tracker_updates"] = compute_pending_tracker_updates(
                receipt, policy
            )
        receipt["coordinator_generation"] += 1
        new_bytes = canonical_json(receipt)
        replace_receipt(receipt_path, receipt_bytes, new_bytes, locked=True)
        return {
            "status": "recorded",
            "kind": DISPOSITION_KIND,
            "ticket_id": entry["ticket_id"],
            "disposition": entry["disposition"],
            "coordinator_generation": receipt["coordinator_generation"],
            "receipt_sha256": sha256(new_bytes),
        }


def _validate_terminal_obligations(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        fail("audit.obligations must be a non-empty array")
    result = []
    ids = set()
    for index, item in enumerate(value):
        label = f"audit.obligations[{index}]"
        item = require_object(item, label)
        actual_fields = set(item)
        required_fields = {"id", "owner", "status", "evidence_applicable"}
        optional_fields = {"ticket_id"}
        if not required_fields.issubset(actual_fields) or (
            actual_fields - (required_fields | optional_fields)
        ):
            require_exact_fields(item, required_fields, label)
        obligation_id = require_identity(item["id"], f"{label}.id")
        if obligation_id in ids:
            fail(f"{label}.id is duplicated")
        ids.add(obligation_id)
        status = require_text(item["status"], f"{label}.status", safe_name=True)
        if status not in OBLIGATION_STATUSES:
            fail(f"{label}.status is unsupported")
        if type(item["evidence_applicable"]) is not bool:
            fail(f"{label}.evidence_applicable must be boolean")
        entry: dict[str, Any] = {
            "id": obligation_id,
            "owner": require_identity(item["owner"], f"{label}.owner"),
            "status": status,
            "evidence_applicable": item["evidence_applicable"],
        }
        if "ticket_id" in item and item["ticket_id"] is not None:
            entry["ticket_id"] = require_identity(
                item["ticket_id"], f"{label}.ticket_id"
            )
        result.append(entry)
    return result


def _validate_gates(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        fail("audit.whole_dag_gates must be an array")
    result = []
    ids = set()
    for index, item in enumerate(value):
        label = f"audit.whole_dag_gates[{index}]"
        item = require_object(item, label)
        require_exact_fields(item, {"id", "result", "evidence_identity"}, label)
        gate_id = require_identity(item["id"], f"{label}.id")
        if gate_id in ids:
            fail(f"{label}.id is duplicated")
        ids.add(gate_id)
        result_value = require_text(item["result"], f"{label}.result", safe_name=True)
        if result_value not in GATE_RESULTS:
            fail(f"{label}.result is unsupported")
        result.append(
            {
                "id": gate_id,
                "result": result_value,
                "evidence_identity": require_identity(
                    item["evidence_identity"], f"{label}.evidence_identity"
                ),
            }
        )
    return result


def validate_terminal_audit(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "audit")
    expected = {
        "schema_version",
        "kind",
        "run_id",
        "outcome",
        "definition_identity",
        "accepted_tip",
        "authority_refs",
        "obligations",
        "whole_dag_gates",
        "pending_tracker_updates",
        "unresolved_decisions",
        "needs_decisions",
        "runnable_tickets",
        "running_agents",
        "recovery_paths",
        "satisfiable_external_conditions",
        "writer_liveness_resolved",
    }
    require_exact_fields(payload, expected, "audit")
    if payload["schema_version"] != SCHEMA_VERSION or payload["kind"] != AUDIT_KIND:
        fail("audit schema_version or kind is unsupported")
    outcome = require_text(payload["outcome"], "audit.outcome", safe_name=True)
    if outcome not in OUTCOMES:
        fail("audit.outcome is unsupported")
    if type(payload["writer_liveness_resolved"]) is not bool:
        fail("audit.writer_liveness_resolved must be boolean")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": AUDIT_KIND,
        "run_id": require_identity(payload["run_id"], "audit.run_id"),
        "outcome": outcome,
        "definition_identity": require_identity(
            payload["definition_identity"], "audit.definition_identity"
        ),
        "accepted_tip": validate_ticket_base(
            payload["accepted_tip"], "audit.accepted_tip"
        ),
        "authority_refs": validate_evidence_refs(
            payload["authority_refs"], "audit.authority_refs"
        ),
        "obligations": _validate_terminal_obligations(payload["obligations"]),
        "whole_dag_gates": _validate_gates(payload["whole_dag_gates"]),
        "pending_tracker_updates": require_string_array(
            payload["pending_tracker_updates"], "audit.pending_tracker_updates"
        ),
        "unresolved_decisions": require_string_array(
            payload["unresolved_decisions"], "audit.unresolved_decisions"
        ),
        "needs_decisions": require_string_array(
            payload["needs_decisions"], "audit.needs_decisions"
        ),
        "runnable_tickets": require_string_array(
            payload["runnable_tickets"], "audit.runnable_tickets"
        ),
        "running_agents": require_string_array(
            payload["running_agents"], "audit.running_agents"
        ),
        "recovery_paths": require_string_array(
            payload["recovery_paths"], "audit.recovery_paths"
        ),
        "satisfiable_external_conditions": require_string_array(
            payload["satisfiable_external_conditions"],
            "audit.satisfiable_external_conditions",
        ),
        "writer_liveness_resolved": payload["writer_liveness_resolved"],
    }


def _verify_dispositions_match_obligations(
    effective: dict[str, dict[str, Any]],
    obligations: list[dict[str, Any]],
    *,
    complete: bool,
) -> None:
    mapped_tickets: set[str] = set()
    for obligation in obligations:
        ticket_id = str(obligation.get("ticket_id") or obligation["owner"])
        if ticket_id in mapped_tickets:
            fail("terminal obligations must map one-to-one with Ticket dispositions")
        mapped_tickets.add(ticket_id)
        status = obligation["status"]
        if status in {"Accepted", "Superseded"} or complete:
            recorded = effective.get(ticket_id)
            if recorded is None:
                fail(
                    f"obligation {obligation['id']} ({ticket_id}) has no recorded Ticket disposition in receipt"
                )
            if recorded["disposition"] != status:
                fail(
                    f"obligation {obligation['id']} status {status} does not match recorded Ticket disposition {recorded['disposition']}"
                )
            if (
                "ticket_id" in obligation
                and recorded.get("claim_owner_id") is not None
                and obligation["owner"] not in {recorded["claim_owner_id"], ticket_id}
            ):
                fail(
                    f"obligation {obligation['id']} owner does not match recorded Ticket disposition owner"
                )
    missing = sorted(set(effective) - mapped_tickets)
    if missing:
        fail(
            f"recorded Ticket dispositions missing from terminal obligations: {', '.join(missing)}"
        )


def publish_terminal_evidence(
    *,
    receipt_path: Path,
    audit_path: Path,
    expected_tip_commit: str,
    expected_tip_tree: str,
    output_path: Path,
) -> dict[str, Any]:
    expected_tip_commit = require_oid(expected_tip_commit, "expected_tip_commit")
    expected_tip_tree = require_oid(expected_tip_tree, "expected_tip_tree")
    receipt = validate_receipt(
        parse_json(read_regular_file(receipt_path, "receipt"), "receipt")
    )
    audit_bytes = read_regular_file(audit_path, "audit")
    audit = validate_terminal_audit(parse_json(audit_bytes, "audit"))
    if receipt["run_id"] != audit["run_id"]:
        fail("receipt and audit run_id do not match")
    if audit["accepted_tip"]["commit"] != expected_tip_commit:
        fail("audit accepted tip commit does not match current tip")
    if audit["accepted_tip"]["tree"] != expected_tip_tree:
        fail("audit accepted tip tree does not match current tip")
    receipt_tip = receipt.get("accepted_integration_tip")
    if receipt_tip is not None:
        receipt_tip = validate_ticket_base(
            receipt_tip, "receipt.accepted_integration_tip"
        )
        if receipt_tip != audit["accepted_tip"]:
            fail(
                "receipt.accepted_integration_tip does not match terminal accepted tip"
            )
    if receipt.get("pending_transition") is not None:
        fail("pending_transition remains active at terminal outcome")
    if receipt.get("claims"):
        fail("live claims remain at terminal outcome")
    if not audit["writer_liveness_resolved"]:
        fail("writer liveness is unresolved")
    receipt_pending = receipt.get("pending_tracker_updates", [])
    if audit["outcome"] == "Complete":
        if any(
            obligation["status"] not in {"Accepted", "Superseded"}
            or not obligation["evidence_applicable"]
            for obligation in audit["obligations"]
        ):
            fail(
                "Complete requires all obligations to be closed with applicable evidence"
            )
        if any(gate["result"] != "pass" for gate in audit["whole_dag_gates"]):
            fail("Complete requires every whole-DAG gate to pass")
        for field in (
            "pending_tracker_updates",
            "unresolved_decisions",
            "needs_decisions",
            "runnable_tickets",
            "running_agents",
            "recovery_paths",
            "satisfiable_external_conditions",
        ):
            if audit[field]:
                fail(f"Complete cannot have {field}")
        if receipt_pending:
            fail("Complete cannot have pending_tracker_updates in receipt")
        policy = validate_receipt_tracker_policy(receipt, reread_record=True)
        if policy is None:
            fail("Complete requires a recorded Tracker Policy in receipt")
        effective = effective_ticket_dispositions(receipt, verify_evidence=True)
        _verify_dispositions_match_obligations(
            effective, audit["obligations"], complete=True
        )
        checkpoints = validate_receipt_tracker_checkpoints(receipt)
        if policy["mode"] == "none":
            if checkpoints:
                fail("Tracker Policy mode none cannot have Tracker Checkpoints")
        else:
            if not checkpoints:
                fail(
                    f"Complete requires a completed Tracker Checkpoint when mode is {policy['mode']}"
                )
            current_checkpoints = [
                item
                for item in checkpoints
                if item["policy_key"] == policy["policy_key"]
            ]
            if not current_checkpoints:
                fail(
                    "stale policy: no Tracker Checkpoint matches current Tracker Policy"
                )
            uncheckpointed = compute_pending_tracker_updates(receipt, policy)
            if uncheckpointed:
                fail(
                    "Complete requires a completed Tracker Checkpoint for every Ticket disposition"
                )
            latest = checkpoints[-1]
            if latest["policy_key"] != policy["policy_key"]:
                fail(
                    "stale policy: latest Tracker Checkpoint does not match current Tracker Policy"
                )
            if (
                latest["candidate"]["commit"] != expected_tip_commit
                or latest["candidate"]["tree"] != expected_tip_tree
            ):
                fail(
                    "stale checkpoint: latest Tracker Checkpoint candidate does not match Accepted Integration Tip"
                )
    else:
        if not any(
            obligation["status"] in {"Open", "Blocked"}
            for obligation in audit["obligations"]
        ):
            fail("Stalled requires at least one unfinished obligation")
        for field in (
            "pending_tracker_updates",
            "unresolved_decisions",
            "needs_decisions",
            "runnable_tickets",
            "running_agents",
            "recovery_paths",
            "satisfiable_external_conditions",
        ):
            if audit[field]:
                fail(f"Stalled cannot have {field}")
        if receipt_pending:
            fail("Stalled cannot have pending_tracker_updates in receipt")
        if receipt.get("tracker_policy") is not None:
            validate_receipt_tracker_policy(receipt, reread_record=True)
        if receipt.get("ticket_dispositions"):
            effective = effective_ticket_dispositions(receipt, verify_evidence=True)
            _verify_dispositions_match_obligations(
                effective, audit["obligations"], complete=False
            )
    evidence = {
        "schema_version": SCHEMA_VERSION,
        "kind": TERMINAL_EVIDENCE_KIND,
        "run_id": audit["run_id"],
        "outcome": audit["outcome"],
        "definition_identity": audit["definition_identity"],
        "accepted_tip": audit["accepted_tip"],
        "audit_sha256": sha256(audit_bytes),
        "verified": True,
    }
    status = publish_once(
        output_path,
        canonical_json(evidence),
        [receipt_path, audit_path],
    )
    return {
        "status": status,
        "kind": TERMINAL_EVIDENCE_KIND,
        "outcome": evidence["outcome"],
        "verified": True,
    }
