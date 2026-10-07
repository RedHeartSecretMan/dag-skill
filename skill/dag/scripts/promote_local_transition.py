"""Verify one frozen pending transition and promote its local integration ref.

The Coordinator supplies the pending record's digest from the Run Receipt and
keeps writers and worktree changes quiescent during this command. This helper
checks mechanical identities; the Coordinator still owns semantic acceptance.
It never modifies the pending record, evidence, or an acceptance record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

from validate_definition_index import (
    ValidationError,
    isolated_git_environment,
    run_git,
    unique_json_object,
)

SHA256 = re.compile(r"[0-9a-f]{64}\Z")
OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
FIELDS = {
    "schema_version",
    "candidate_kind",
    "integration_ref",
    "base",
    "candidate",
    "candidate_tree",
    "evidence",
}
CANDIDATE_KINDS = {"Promotion Candidate", "DAG Definition Checkpoint"}


def parse_integer(value: str) -> int:
    if len(value.lstrip("-")) > 20:
        raise ValidationError("JSON integer is oversized")
    return int(value)


def read_regular_file(path: Path) -> bytes:
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValidationError(f"{path}: must be a regular file, not a symlink")
    return path.read_bytes()


def read_transition(path: Path, digest: str) -> tuple[bytes, dict[str, object]]:
    content = read_regular_file(path)
    if hashlib.sha256(content).hexdigest() != digest:
        raise ValidationError("pending transition SHA-256 does not match")
    try:
        payload = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=unique_json_object,
            parse_int=parse_integer,
        )
    except (UnicodeDecodeError, ValueError) as error:
        raise ValidationError(
            f"pending transition must be UTF-8 JSON: {error}"
        ) from error
    if not isinstance(payload, dict) or set(payload) != FIELDS:
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
        if not isinstance(value, str) or OBJECT_ID.fullmatch(value) is None:
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
            or SHA256.fullmatch(item["sha256"]) is None
        ):
            raise ValidationError(
                "each evidence SHA-256 must be 64 lowercase hex digits"
            )
    return content, payload


def evidence_paths(transition: Path, payload: dict[str, object]) -> list[Path]:
    paths = [transition.parent / item["path"] for item in payload["evidence"]]
    resolved = [path.resolve(strict=True) for path in paths]
    if len(resolved) != len(set(resolved)) or transition.resolve() in resolved:
        raise ValidationError(
            "evidence paths must be unique and distinct from the transition"
        )
    return paths


def verify_frozen_files(
    transition: Path,
    content: bytes,
    payload: dict[str, object],
    paths: list[Path],
) -> None:
    if read_regular_file(transition) != content:
        raise ValidationError("pending transition changed during preflight")
    for item, path in zip(payload["evidence"], paths, strict=True):
        if hashlib.sha256(read_regular_file(path)).hexdigest() != item["sha256"]:
            raise ValidationError(f"{path}: evidence SHA-256 does not match")


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
        raise ValidationError("integration_ref must not be symbolic")
    if symbolic.returncode != 1:
        raise ValidationError(
            "could not inspect integration_ref for symbolic indirection"
        )
    return (
        run_git(repository, ["show-ref", "--verify", "--hash", integration_ref])
        .decode("ascii")
        .strip()
    )


def worktree_roots(repository: Path, integration_ref: str) -> list[Path]:
    roots = []
    for field in run_git(repository, ["worktree", "list", "--porcelain", "-z"]).split(
        b"\0"
    ):
        if field == b"branch " + integration_ref.encode("utf-8"):
            raise ValidationError("integration_ref is checked out in a worktree")
        if field.startswith(b"worktree "):
            roots.append(Path(os.fsdecode(field[9:])).resolve())
    return roots


def verify_off_delivery(
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
    for revision in (payload["base"], payload["candidate"]):
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


def verify_objects(repository: Path, payload: dict[str, object]) -> None:
    object_format = run_git(repository, ["rev-parse", "--show-object-format"]).strip()
    oid_length = {b"sha1": 40, b"sha256": 64}.get(object_format)
    if oid_length is None:
        raise ValidationError("unsupported Git object format")
    for field, object_type in (
        ("base", "commit"),
        ("candidate", "commit"),
        ("candidate_tree", "tree"),
    ):
        oid = payload[field]
        if len(oid) != oid_length:
            raise ValidationError(
                f"{field} does not match the repository object format"
            )
        if run_git(repository, ["cat-file", "-t", oid]).strip() != object_type.encode():
            raise ValidationError(f"{field} must identify a local {object_type} object")
    tree = (
        run_git(repository, ["rev-parse", f"{payload['candidate']}^{{tree}}"])
        .decode("ascii")
        .strip()
    )
    if tree != payload["candidate_tree"]:
        raise ValidationError("candidate_tree does not match the candidate commit")
    if (
        git_probe(
            repository,
            ["merge-base", "--is-ancestor", payload["base"], payload["candidate"]],
        ).returncode
        != 0
    ):
        raise ValidationError("Base must be a local ancestor of the candidate")


def promote_local_transition(
    repository: Path, transition: Path, digest: str
) -> dict[str, object]:
    if SHA256.fullmatch(digest) is None:
        raise ValidationError("--sha256 must be 64 lowercase hex digits")
    repository = repository.resolve(strict=True)
    # Keep the final path component unresolved so a symlink record is rejected.
    transition = transition.absolute()
    content, payload = read_transition(transition, digest)
    paths = evidence_paths(transition, payload)
    repository = Path(
        os.fsdecode(run_git(repository, ["rev-parse", "--show-toplevel"]).strip())
    ).resolve(strict=True)
    run_git(repository, ["check-ref-format", payload["integration_ref"]])
    verify_objects(repository, payload)
    roots = worktree_roots(repository, payload["integration_ref"])
    verify_off_delivery(repository, payload, [transition, *paths], roots)
    verify_frozen_files(transition, content, payload, paths)

    # Repeat mutable preflight, then reread the exact frozen bytes immediately
    # before CAS. Atomicity across Git refs and external files requires the
    # Coordinator's documented single-writer/quiescent-worktree discipline.
    roots = worktree_roots(repository, payload["integration_ref"])
    verify_off_delivery(repository, payload, [transition, *paths], roots)
    live = read_direct_ref(repository, payload["integration_ref"])
    if live not in {payload["base"], payload["candidate"]}:
        raise ValidationError("integration_ref has drifted from Base and candidate")
    verify_frozen_files(transition, content, payload, paths)
    if live == payload["base"]:
        run_git(
            repository,
            [
                "-c",
                f"core.hooksPath={os.devnull}",
                "update-ref",
                "--no-deref",
                payload["integration_ref"],
                payload["candidate"],
                payload["base"],
            ],
        )
        status = "local-promoted"
    else:
        status = "local-already-promoted"
    try:
        if (
            read_direct_ref(repository, payload["integration_ref"])
            != payload["candidate"]
        ):
            raise ValidationError("integration_ref does not match candidate")
    except (OSError, ValidationError, UnicodeError) as error:
        raise ValidationError(
            "local promotion readback failed; preserve pending evidence and inspect the ref before recovery"
        ) from error
    return {
        "status": status,
        "candidate_kind": payload["candidate_kind"],
        "integration_ref": payload["integration_ref"],
        "base": payload["base"],
        "candidate": payload["candidate"],
        "candidate_tree": payload["candidate_tree"],
        "transition_sha256": digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify frozen pending evidence and CAS-promote one local integration ref. The Coordinator keeps writers and worktree changes quiescent; semantic acceptance remains separate."
    )
    parser.add_argument(
        "--repository", required=True, type=Path, help="existing non-bare Git worktree"
    )
    parser.add_argument("--transition", required=True, type=Path)
    parser.add_argument(
        "--sha256",
        required=True,
        help="SHA-256 of the exact pending record bytes, recorded in the Run Receipt",
    )
    arguments = parser.parse_args()
    try:
        result = promote_local_transition(
            arguments.repository, arguments.transition, arguments.sha256
        )
    except (
        OSError,
        ValidationError,
        ValueError,
        UnicodeError,
        TypeError,
        RecursionError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
