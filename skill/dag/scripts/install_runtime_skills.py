#!/usr/bin/env python3
"""Install DAG Runtime Skills with a minimum revision and conflict-safe preflight."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePath

REPOSITORY = "https://github.com/mattpocock/skills.git"
# Minimum accepted upstream commit and the source for bootstrapping missing Skills.
REVISION = "5b15a47f2d7150f545fbcacbfe381787fc0230dc"
UPSTREAM_BUNDLE_ROOT = Path("skills/engineering")
RUNTIME_SKILLS = ("code-review", "tdd", "codebase-design")
SETUP_SKILL = "setup-matt-pocock-skills"
AVAILABLE_SKILLS = (*RUNTIME_SKILLS, SETUP_SKILL)
MINIMUM_PYTHON = (3, 12)
GIT_TIMEOUT_SECONDS = 120
SAFE_GIT_ENVIRONMENT = {
    "GIT_ATTR_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_TERMINAL_PROMPT": "0",
}
REQUIRED_FILES = {
    "code-review": ("SKILL.md",),
    "tdd": ("SKILL.md", "tests.md", "mocking.md"),
    "codebase-design": ("SKILL.md", "DEEPENING.md", "DESIGN-IT-TWICE.md"),
    "setup-matt-pocock-skills": (
        "SKILL.md",
        "domain.md",
        "issue-tracker-github.md",
        "issue-tracker-gitlab.md",
        "issue-tracker-local.md",
        "triage-labels.md",
    ),
}
PINNED_TREE_DIGESTS = {
    "code-review": "469775f63f281a7f74f5ca03c08030ba48bdd5fe146003a6a0231a91051202f6",
    "tdd": "e91b8b8c3fb7e55f6432b4c7023291135ea2141578af432459b6c57b25a1bf2f",
    "codebase-design": "d8500952a6f5631d8b3f748155d70b81e18bf74d28f1f41116f3eb64988a873a",
    "setup-matt-pocock-skills": "b2dda865f0a6069d7d2c60ca3c3b95a622fe4a7bf98c96764a2f4ed6c091e0d3",
}


class InstallError(RuntimeError):
    """A safe, user-actionable installation failure."""


def require_supported_python(version: tuple[int, int]) -> None:
    """Validate the supported Python runtime floor."""

    if version < MINIMUM_PYTHON:
        required = ".".join(str(part) for part in MINIMUM_PYTHON)
        actual = ".".join(str(part) for part in version)
        raise InstallError(f"Python {required}+ is required; detected Python {actual}")


def isolated_git_environment() -> dict[str, str]:
    """Return a non-interactive Git environment detached from the caller's repository."""

    environment = {
        name: value for name, value in os.environ.items() if not name.startswith("GIT_")
    }
    environment.update(SAFE_GIT_ENVIRONMENT)
    return environment


def run_git(arguments: list[str], cwd: Path) -> str:
    disabled_hooks = cwd / ".git" / "dag-skill-disabled-hooks"
    command = ["git", "-c", f"core.hooksPath={disabled_hooks}", *arguments]
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            env=isolated_git_environment(),
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        operation = arguments[0] if arguments else "command"
        raise InstallError(
            f"Git {operation} exceeded the {GIT_TIMEOUT_SECONDS}-second installation bound"
        ) from error
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown Git error"
        raise InstallError(detail)
    return result.stdout.strip()


def framed(value: bytes) -> bytes:
    """Encode one digest field with an unambiguous length prefix."""

    return len(value).to_bytes(8, byteorder="big") + value


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    entries = sorted(
        root.rglob("*"), key=lambda path: path.relative_to(root).as_posix()
    )
    for entry in entries:
        relative = entry.relative_to(root).as_posix().encode()
        if entry.is_symlink():
            kind = b"L"
            payload = os.readlink(entry).encode()
        elif entry.is_dir():
            kind = b"D"
            payload = b""
        elif entry.is_file():
            kind = b"F"
            content_digest = hashlib.sha256()
            with entry.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    content_digest.update(block)
            payload = content_digest.digest()
        else:
            raise InstallError(f"Unsupported source entry: {entry}")
        digest.update(framed(kind) + framed(relative) + framed(payload))
    return digest.hexdigest()


def is_filesystem_root(path: PurePath) -> bool:
    """Return whether a resolved path is a POSIX, drive, or UNC filesystem root."""

    return path.parent == path


def copy_directory_contents(source: Path, target: Path) -> None:
    """Copy one staged Skill into an empty, exclusively reserved directory."""

    for entry in sorted(source.iterdir(), key=lambda path: path.name):
        destination = target / entry.name
        if entry.is_symlink():
            os.symlink(
                os.readlink(entry), destination, target_is_directory=entry.is_dir()
            )
        elif entry.is_dir():
            destination.mkdir()
            copy_directory_contents(entry, destination)
        elif entry.is_file():
            with (
                entry.open("rb") as source_handle,
                destination.open("xb") as destination_handle,
            ):
                shutil.copyfileobj(source_handle, destination_handle)
            shutil.copystat(entry, destination, follow_symlinks=False)
        else:
            raise InstallError(f"Unsupported staged entry: {entry}")
    shutil.copystat(source, target, follow_symlinks=False)


def install_staged_skill(staged: Path, target: Path, expected_digest: str) -> None:
    """Reserve and populate one target without replacing an existing path."""

    try:
        target.mkdir()
    except FileExistsError as error:
        raise InstallError(f"Target appeared during installation: {target}") from error

    try:
        copy_directory_contents(staged, target)
        if tree_digest(target) != expected_digest:
            raise InstallError(f"Installed copy verification failed for {target.name}")
    except Exception as error:
        raise InstallError(
            f"Installation stopped; the reserved target remains for inspection: {target}"
        ) from error


def fetch_pinned_source(
    workspace: Path, skills: tuple[str, ...] = RUNTIME_SKILLS
) -> dict[str, Path]:
    checkout = workspace / "checkout"
    templates = workspace / "empty-git-templates"
    checkout.mkdir()
    templates.mkdir()
    run_git(["init", "--quiet", f"--template={templates}"], checkout)
    run_git(
        ["fetch", "--quiet", "--depth=1", "--no-tags", REPOSITORY, REVISION],
        checkout,
    )
    run_git(["checkout", "--quiet", "--detach", "FETCH_HEAD"], checkout)

    actual_revision = run_git(["rev-parse", "HEAD"], checkout)
    if actual_revision != REVISION:
        raise InstallError(
            f"Fetched revision {actual_revision}, expected pinned revision {REVISION}"
        )

    sources: dict[str, Path] = {}
    for skill in skills:
        source = checkout / UPSTREAM_BUNDLE_ROOT / skill
        missing = [
            name for name in REQUIRED_FILES[skill] if not (source / name).is_file()
        ]
        if missing:
            raise InstallError(
                f"Pinned {skill} source is missing: {', '.join(missing)}"
            )
        actual_digest = tree_digest(source)
        expected_digest = PINNED_TREE_DIGESTS[skill]
        if actual_digest != expected_digest:
            raise InstallError(
                f"Pinned {skill} source digest is {actual_digest}; "
                f"expected {expected_digest}"
            )
        sources[skill] = source
    return sources


def inspect_targets(
    skills_root: Path,
    skills: tuple[str, ...] = RUNTIME_SKILLS,
    *,
    expected_digests: dict[str, str] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    """Classify targets against the fixed content identities for this invocation."""

    expected_digests = (
        PINNED_TREE_DIGESTS if expected_digests is None else expected_digests
    )
    missing: list[str] = []
    current: list[str] = []
    conflicts: list[str] = []
    for skill in skills:
        target = skills_root / skill
        if not target.exists() and not target.is_symlink():
            missing.append(skill)
        elif target.is_symlink() or not target.is_dir():
            conflicts.append(f"{skill}: target is not an ordinary directory")
        elif tree_digest(target) == expected_digests[skill]:
            current.append(skill)
        else:
            conflicts.append(f"{skill}: existing directory has no verified source")
    return missing, current, conflicts


def match_descendant_sources(
    workspace: Path, target_digests: dict[str, str]
) -> dict[str, tuple[str, str]]:
    """Match copied Skills to complete trees in upstream descendant commits."""

    checkout = workspace / "checkout"
    templates = workspace / "empty-git-templates"
    checkout.mkdir()
    templates.mkdir()
    run_git(["init", "--quiet", f"--template={templates}"], checkout)
    run_git(
        [
            "fetch",
            "--quiet",
            "--no-tags",
            REPOSITORY,
            "+refs/heads/*:refs/remotes/upstream/*",
            "+refs/tags/*:refs/tags/*",
        ],
        checkout,
    )
    run_git(["rev-parse", "--verify", f"{REVISION}^{{commit}}"], checkout)
    revisions = run_git(
        ["rev-list", "--all", "--ancestry-path", f"^{REVISION}"], checkout
    ).splitlines()
    remaining = dict(target_digests)
    matches: dict[str, tuple[str, str]] = {}
    seen_trees: dict[str, set[str]] = {skill: set() for skill in remaining}
    for revision in revisions:
        for skill in list(remaining):
            source_path = UPSTREAM_BUNDLE_ROOT / skill
            entry = run_git(
                ["ls-tree", "-d", revision, "--", source_path.as_posix()], checkout
            )
            if not entry:
                continue
            tree_oid = entry.split("\t", 1)[0].split()[2]
            if tree_oid in seen_trees[skill]:
                continue
            seen_trees[skill].add(tree_oid)
            run_git(["checkout", "--quiet", "--detach", revision], checkout)
            source = checkout / source_path
            if not (source / "SKILL.md").is_file():
                continue
            digest = tree_digest(source)
            if digest == remaining[skill]:
                run_git(["merge-base", "--is-ancestor", REVISION, revision], checkout)
                matches[skill] = (digest, revision)
                del remaining[skill]
        if not remaining:
            break
    return matches


def verify_complete_bundle(
    skills_root: Path,
    skills: tuple[str, ...] = RUNTIME_SKILLS,
    *,
    expected_digests: dict[str, str] | None = None,
) -> None:
    """Verify all selected targets still match their accepted source identities."""

    missing, _, conflicts = inspect_targets(
        skills_root, skills, expected_digests=expected_digests
    )
    problems = [*(f"{skill}: target is missing" for skill in missing), *conflicts]
    if problems:
        details = "\n".join(f"  - {problem}" for problem in problems)
        raise InstallError("Skill bundle verification failed:\n" + details)


def install(skills_root: Path, *, include_setup_helper: bool = False) -> None:
    skills_root = skills_root.expanduser().resolve(strict=False)
    selected_skills = AVAILABLE_SKILLS if include_setup_helper else RUNTIME_SKILLS
    bundle_name = (
        "DAG Runtime Skills and setup helper"
        if include_setup_helper
        else "DAG Runtime Skill Bundle"
    )
    if is_filesystem_root(skills_root):
        raise InstallError("Skills root must be a directory below the filesystem root")
    if skills_root.exists() and not skills_root.is_dir():
        raise InstallError(f"Skills root is not a directory: {skills_root}")

    expected_digests = dict(PINNED_TREE_DIGESTS)
    missing, current, conflicts = inspect_targets(skills_root, selected_skills)
    different = [skill for skill in selected_skills if skill not in missing + current]
    matches: dict[str, tuple[str, str]] = {}
    if different and all(
        (skills_root / skill).is_dir() and not (skills_root / skill).is_symlink()
        for skill in different
    ):
        if shutil.which("git") is None:
            raise InstallError("Git is required to verify newer Skill sources")
        target_digests = {
            skill: tree_digest(skills_root / skill) for skill in different
        }
        with tempfile.TemporaryDirectory(prefix="dag-skill-verify-") as temporary:
            matches = match_descendant_sources(Path(temporary), target_digests)
        for skill, (digest, _) in matches.items():
            expected_digests[skill] = digest
        missing, current, conflicts = inspect_targets(
            skills_root, selected_skills, expected_digests=expected_digests
        )
    if conflicts:
        details = "\n".join(f"  - {conflict}" for conflict in conflicts)
        raise InstallError(
            "Existing Skill targets were preserved; resolve these conflicts before installation:\n"
            + details
        )

    versions = [f"Minimum revision: {REVISION}"]
    versions.extend(
        f"Verified {skill} at descendant revision: {revision}"
        for skill, (_, revision) in matches.items()
    )
    if not missing:
        verify_complete_bundle(
            skills_root, selected_skills, expected_digests=expected_digests
        )
        print(f"{bundle_name} is already current at {skills_root}")
        print("\n".join(versions))
        return

    if shutil.which("git") is None:
        raise InstallError("Git is required to fetch the pinned Skill sources")

    with tempfile.TemporaryDirectory(prefix="dag-skill-install-") as temporary:
        workspace = Path(temporary)
        sources = fetch_pinned_source(workspace, selected_skills)

        skills_root.mkdir(parents=True, exist_ok=True)
        staging = workspace / "stage"
        staging.mkdir()
        installed: list[Path] = []
        try:
            for skill in missing:
                staged = staging / skill
                shutil.copytree(sources[skill], staged, symlinks=True)
                if tree_digest(staged) != PINNED_TREE_DIGESTS[skill]:
                    raise InstallError(f"Staged copy verification failed for {skill}")

            for skill in missing:
                target = skills_root / skill
                install_staged_skill(
                    staging / skill, target, PINNED_TREE_DIGESTS[skill]
                )
                installed.append(target)
        except Exception as error:
            if installed:
                paths = ", ".join(str(path) for path in installed)
                raise InstallError(
                    "Bundle installation stopped; verified targets remain at "
                    f"{paths}. Resolve this condition and run the installer again: {error}"
                ) from error
            raise

        verify_complete_bundle(
            skills_root, selected_skills, expected_digests=expected_digests
        )

    print(f"Installed missing {bundle_name} members at {skills_root}")
    print("\n".join(versions))
    print(f"Installed: {', '.join(missing)}")
    if current:
        print(f"Already current: {', '.join(current)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Install the DAG Skill's Runtime Skills at or after its minimum revision into an explicit host "
            "Skills root."
        )
    )
    parser.add_argument(
        "--skills-root",
        required=True,
        type=Path,
        help="stable host Skills root; selected Skills are installed directly beneath it",
    )
    parser.add_argument(
        "--include-setup-helper",
        action="store_true",
        help="also install the optional setup-matt-pocock-skills helper",
    )
    arguments = parser.parse_args()

    try:
        require_supported_python(sys.version_info[:2])
        install(
            arguments.skills_root,
            include_setup_helper=arguments.include_setup_helper,
        )
    except (InstallError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
