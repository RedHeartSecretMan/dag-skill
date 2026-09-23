"""Validate the canonical DAG Definition Index at one Git commit."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path, PurePosixPath

INDEX_PATH = ".dag/definition-index.json"
REGULAR_BLOB_MODES = {"100644", "100755"}
LFS_POINTER_VERSIONS = {
    "http://git-media.io/v/2",
    "https://hawser.github.com/spec/v1",
    "https://git-lfs.github.com/spec/v1",
}
LFS_POINTER_SIZE_LIMIT = 1024
LFS_OID = re.compile(r"sha256:[0-9a-f]{64}\Z")
LFS_EXTENSION_PREFIX = re.compile(r"ext-[0-9]-[A-Za-z0-9_]+")
LFS_SIZE = re.compile(r"[-+]?[0-9]+\Z")
SAFE_GIT_ENVIRONMENT = {
    "GIT_ATTR_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_LITERAL_PATHSPECS": "1",
    "GIT_NO_LAZY_FETCH": "1",
    "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_TERMINAL_PROMPT": "0",
}


class ValidationError(RuntimeError):
    """A deterministic, user-actionable Definition Index failure."""


def is_normalized_safe_path(path: object) -> bool:
    if not isinstance(path, str) or not path or "\\" in path or "\0" in path:
        return False
    try:
        path.encode("utf-8")
    except UnicodeEncodeError:
        return False
    if path == INDEX_PATH or path.startswith("/"):
        return False
    if unicodedata.normalize("NFC", path) != path:
        return False
    parts = path.split("/")
    if any(part in {"", ".", "..", ".git"} for part in parts):
        return False
    return PurePosixPath(path).as_posix() == path


def isolated_git_environment() -> dict[str, str]:
    environment = {
        name: value for name, value in os.environ.items() if not name.startswith("GIT_")
    }
    environment.update(SAFE_GIT_ENVIRONMENT)
    return environment


def unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, value in pairs:
        if name in result:
            raise ValidationError(f"duplicate JSON field: {name}")
        result[name] = value
    return result


def is_git_lfs_pointer(content: bytes) -> bool:
    if not content or len(content) >= LFS_POINTER_SIZE_LIMIT:
        return False
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return False

    expected_keys = ("version", "oid", "size")
    expected_index = 0
    extensions: dict[str, str] = {}
    for line in text.strip().split("\n"):
        line = line.removesuffix("\r")
        if not line:
            continue
        parts = line.split(" ", 1)
        if len(parts) != 2 or not parts[1]:
            return False
        key, value = parts
        if expected_index < len(expected_keys) and key == expected_keys[expected_index]:
            if key == "version" and value not in LFS_POINTER_VERSIONS:
                return False
            if key == "oid" and LFS_OID.fullmatch(value) is None:
                return False
            if key == "size":
                if LFS_SIZE.fullmatch(value) is None:
                    return False
                try:
                    size = int(value, 10)
                    if size < 0 or size > 2**63 - 1:
                        return False
                except ValueError:
                    return False
            expected_index += 1
            continue

        if (
            expected_index >= len(expected_keys)
            or LFS_EXTENSION_PREFIX.match(key) is None
        ):
            return False
        extensions[key] = value

    extension_priorities: set[int] = set()
    for key, value in extensions.items():
        key_parts = key.split("-", 2)
        if len(key_parts) != 3 or key_parts[0] != "ext":
            return False
        try:
            priority = int(key_parts[1], 10)
        except ValueError:
            return False
        if (
            priority < 0
            or priority in extension_priorities
            or LFS_OID.fullmatch(value) is None
        ):
            return False
        extension_priorities.add(priority)

    return expected_index == len(expected_keys)


def run_git(repository: Path, arguments: list[str]) -> bytes:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        capture_output=True,
        check=False,
        env=isolated_git_environment(),
    )
    if result.returncode != 0:
        detail = result.stderr.decode(errors="replace").strip()
        raise ValidationError(detail or "Git command failed")
    return result.stdout


def tree_entries_for_paths(
    repository: Path, commit_oid: str, paths: list[str]
) -> dict[str, tuple[str, str, str]]:
    output = run_git(
        repository,
        ["ls-tree", "-z", "--full-tree", commit_oid, "--", *paths],
    )
    expected_paths = {path.encode("utf-8"): path for path in paths}
    entries: dict[str, tuple[str, str, str]] = {}
    for record in output.split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, object_type, object_oid = metadata.decode("ascii").split(" ")
        try:
            path = expected_paths[raw_path]
        except KeyError as error:
            raise ValidationError(
                "targeted tree lookup returned an unexpected path"
            ) from error
        entries[path] = (mode, object_type, object_oid)
    return entries


def validate_definition_index(repository: Path, commit: str) -> dict[str, object]:
    repository = repository.resolve(strict=True)
    commit_oid = (
        run_git(
            repository,
            ["rev-parse", "--verify", "--end-of-options", f"{commit}^{{commit}}"],
        )
        .decode("ascii")
        .strip()
    )
    index_entries = tree_entries_for_paths(repository, commit_oid, [INDEX_PATH])
    try:
        index_mode, index_type, index_oid = index_entries[INDEX_PATH]
    except KeyError as error:
        raise ValidationError(f"{INDEX_PATH}: index is missing") from error
    if index_type != "blob" or index_mode != "100644":
        raise ValidationError(
            f"{INDEX_PATH}: index must be a regular non-executable blob"
        )

    index_bytes = run_git(repository, ["cat-file", "blob", index_oid])
    try:
        index_text = index_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValidationError("index must be UTF-8 JSON") from error
    try:
        payload = json.loads(index_text, object_pairs_hook=unique_json_object)
    except ValueError as error:
        raise ValidationError(f"index JSON could not be decoded: {error}") from error
    if not isinstance(payload, dict):
        raise ValidationError("index must be a JSON object")
    if set(payload) != {"schema_version", "inputs"}:
        raise ValidationError("index fields must be exactly inputs, schema_version")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise ValidationError("schema_version must be the integer 1")
    inputs = payload["inputs"]
    if not isinstance(inputs, list):
        raise ValidationError("inputs must be an array")
    if not inputs:
        raise ValidationError("inputs must contain at least one definition blob")
    paths: list[str] = []
    for item in inputs:
        if not isinstance(item, dict) or set(item) != {"path", "blob_oid"}:
            raise ValidationError("each input must contain exactly blob_oid and path")
        if not isinstance(item["blob_oid"], str):
            raise ValidationError("each input blob_oid must be a string")
        path = item["path"]
        if not is_normalized_safe_path(path):
            raise ValidationError(f"{path}: path is not normalized and safe")
        paths.append(path)
    if len(paths) != len(set(paths)):
        raise ValidationError("input paths must be unique")
    if paths != sorted(paths, key=lambda path: path.encode("utf-8")):
        raise ValidationError("inputs must be sorted by UTF-8 path bytes")

    input_entries = tree_entries_for_paths(repository, commit_oid, paths)
    for item in inputs:
        path = item["path"]
        try:
            mode, object_type, actual_oid = input_entries[path]
        except KeyError as error:
            raise ValidationError(
                f"{path}: input is missing from the commit"
            ) from error
        if object_type != "blob" or mode not in REGULAR_BLOB_MODES:
            raise ValidationError(f"{path}: input must be an ordinary tracked blob")
        if item["blob_oid"] != actual_oid:
            raise ValidationError(f"{path}: blob_oid does not match the commit")
        content = run_git(repository, ["cat-file", "blob", actual_oid])
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValidationError(
                f"{path}: definition content must be UTF-8"
            ) from error
        if is_git_lfs_pointer(content):
            raise ValidationError(
                f"{path}: Git LFS pointer is not full definition content"
            )
    return {
        "commit": commit_oid,
        "index": {"path": INDEX_PATH, "blob_oid": index_oid},
        "inputs": inputs,
        "schema_version": payload["schema_version"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate .dag/definition-index.json at one exact Git commit."
    )
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    arguments = parser.parse_args()

    try:
        result = validate_definition_index(arguments.repository, arguments.commit)
    except (
        OSError,
        ValidationError,
        UnicodeDecodeError,
        KeyError,
        TypeError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
