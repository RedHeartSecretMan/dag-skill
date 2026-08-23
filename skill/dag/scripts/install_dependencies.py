#!/usr/bin/env python3
"""Install the pinned DAG Skill dependencies with conflict-safe preflight."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


REPOSITORY = "https://github.com/mattpocock/skills.git"
REVISION = "5b15a47f2d7150f545fbcacbfe381787fc0230dc"
UPSTREAM_BUNDLE_ROOT = Path("skills/engineering")
SKILLS = ("implement", "code-review", "tdd", "codebase-design")
REQUIRED_FILES = {
    "implement": ("SKILL.md",),
    "code-review": ("SKILL.md",),
    "tdd": ("SKILL.md", "tests.md", "mocking.md"),
    "codebase-design": ("SKILL.md", "DEEPENING.md", "DESIGN-IT-TWICE.md"),
}


class InstallError(RuntimeError):
    """A safe, user-actionable installation failure."""


def run_git(arguments: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown Git error"
        raise InstallError(detail)
    return result.stdout.strip()


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    entries = sorted(root.rglob("*"), key=lambda path: path.relative_to(root).as_posix())
    for entry in entries:
        relative = entry.relative_to(root).as_posix().encode()
        if entry.is_symlink():
            digest.update(b"L\0" + relative + b"\0" + os.readlink(entry).encode() + b"\0")
        elif entry.is_dir():
            digest.update(b"D\0" + relative + b"\0")
        elif entry.is_file():
            digest.update(b"F\0" + relative + b"\0")
            with entry.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
            digest.update(b"\0")
        else:
            raise InstallError(f"Unsupported source entry: {entry}")
    return digest.hexdigest()


def fetch_pinned_source(workspace: Path) -> dict[str, Path]:
    checkout = workspace / "checkout"
    checkout.mkdir()
    run_git(["init", "--quiet"], checkout)
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
    for skill in SKILLS:
        source = checkout / UPSTREAM_BUNDLE_ROOT / skill
        missing = [name for name in REQUIRED_FILES[skill] if not (source / name).is_file()]
        if missing:
            raise InstallError(f"Pinned {skill} source is missing: {', '.join(missing)}")
        sources[skill] = source
    return sources


def install(skills_root: Path) -> None:
    if shutil.which("git") is None:
        raise InstallError("Git is required to fetch the pinned dependency bundle")

    skills_root = skills_root.expanduser().resolve(strict=False)
    if skills_root == Path("/"):
        raise InstallError("Refusing to use the filesystem root as the Skills root")
    if skills_root.exists() and not skills_root.is_dir():
        raise InstallError(f"Skills root is not a directory: {skills_root}")

    with tempfile.TemporaryDirectory(prefix="dag-skill-dependencies-") as temporary:
        sources = fetch_pinned_source(Path(temporary))
        source_digests = {skill: tree_digest(source) for skill, source in sources.items()}

        missing: list[str] = []
        current: list[str] = []
        conflicts: list[str] = []
        for skill in SKILLS:
            target = skills_root / skill
            if not target.exists() and not target.is_symlink():
                missing.append(skill)
            elif target.is_symlink() or not target.is_dir():
                conflicts.append(f"{skill}: target is not an ordinary directory")
            elif tree_digest(target) == source_digests[skill]:
                current.append(skill)
            else:
                conflicts.append(f"{skill}: existing directory differs from pinned source")

        if conflicts:
            details = "\n".join(f"  - {conflict}" for conflict in conflicts)
            raise InstallError(
                "Refusing to overwrite existing Skill targets; no dependencies were changed:\n"
                + details
            )

        if not missing:
            print(f"Required Skill Bundle is already current at {skills_root}")
            print(f"Revision: {REVISION}")
            return

        skills_root.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".dag-skill-stage-", dir=skills_root))
        installed: list[str] = []
        try:
            for skill in missing:
                staged = staging / skill
                shutil.copytree(sources[skill], staged, symlinks=True)
                if tree_digest(staged) != source_digests[skill]:
                    raise InstallError(f"Staged copy verification failed for {skill}")

            for skill in missing:
                target = skills_root / skill
                if target.exists() or target.is_symlink():
                    raise InstallError(f"Target appeared during installation: {target}")
                os.rename(staging / skill, target)
                installed.append(skill)
        except Exception:
            for skill in reversed(installed):
                shutil.rmtree(skills_root / skill)
            raise
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    print(f"Installed pinned Matt Skill bundle at {skills_root}")
    print(f"Revision: {REVISION}")
    print(f"Installed: {', '.join(missing)}")
    if current:
        print(f"Already current: {', '.join(current)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install the DAG Skill's pinned dependencies into an explicit host Skills root."
    )
    parser.add_argument(
        "--skills-root",
        required=True,
        type=Path,
        help="stable host Skills root; dependencies are installed directly beneath it",
    )
    arguments = parser.parse_args()

    try:
        install(arguments.skills_root)
    except (InstallError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
