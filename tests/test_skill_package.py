"""Check copyable artifacts and documentation wiring, not Agent Host behavior."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "dag"
PUBLIC_HELPERS = (
    "install_runtime_skills.py",
    "validate_definition_index.py",
    "promote_local_transition.py",
)


def local_targets(document: Path) -> list[Path]:
    """Resolve the repository's inline Markdown links, ignoring web/anchor links."""
    targets = []
    for target in re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", document.read_text("utf-8")):
        parsed = urlsplit(target)
        if not parsed.scheme and not parsed.netloc and parsed.path:
            targets.append((document.parent / unquote(parsed.path)).resolve())
    return targets


class SkillPackageTests(unittest.TestCase):
    def test_documentation_local_links_resolve(self) -> None:
        documents = [
            *ROOT.glob("*.md"),
            *(ROOT / "docs").rglob("*.md"),
            *SKILL.rglob("*.md"),
        ]
        for document in documents:
            for target in local_targets(document):
                with self.subTest(document=document.relative_to(ROOT), target=target):
                    self.assertTrue(target.exists(), f"Broken local link: {target}")

    def test_copied_skill_references_are_self_contained_and_reachable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "dag"
            shutil.copytree(SKILL, copied, ignore=shutil.ignore_patterns("__pycache__"))
            pending = [copied / "SKILL.md"]
            reached = set()
            while pending:
                document = pending.pop()
                if document in reached:
                    continue
                reached.add(document)
                for target in local_targets(document):
                    with self.subTest(document=document.name, target=target):
                        self.assertTrue(target.is_relative_to(copied.resolve()))
                        self.assertTrue(target.is_file())
                    if target.suffix == ".md":
                        pending.append(target)
            self.assertEqual(
                {path.resolve() for path in copied.rglob("*.md")},
                {path.resolve() for path in reached},
                "Every packaged reference must be discoverable from SKILL.md",
            )

    def test_copied_public_helpers_run_without_the_source_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copied = root / "dag"
            shutil.copytree(SKILL, copied, ignore=shutil.ignore_patterns("__pycache__"))
            caller = root / "unrelated"
            caller.mkdir()
            environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH="")
            for name in PUBLIC_HELPERS:
                with self.subTest(helper=name):
                    result = subprocess.run(
                        [sys.executable, str(copied / "scripts" / name), "--help"],
                        cwd=caller,
                        env=environment,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("usage:", result.stdout)
                    self.assertEqual(result.stderr, "")

    def test_active_documents_keep_public_names_and_host_neutral_protocol(self) -> None:
        documents = [
            ROOT / "README.md",
            ROOT / "README_ZH.md",
            ROOT / "CONTEXT.md",
            ROOT / "docs" / "DESIGN.md",
            *SKILL.rglob("*.md"),
        ]
        for document in documents:
            content = document.read_text("utf-8")
            with self.subTest(document=document.relative_to(ROOT)):
                self.assertNotIn("Needs Coordinator Decision", content)
                self.assertNotIn("install_dependencies.py", content)
                self.assertNotIn("fork_turns", content)
        self.assertFalse((SKILL / "scripts" / "install_dependencies.py").exists())

    def test_ci_checks_each_public_helper_interface(self) -> None:
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8")
        for name in PUBLIC_HELPERS:
            with self.subTest(helper=name):
                self.assertIn(f"skill/dag/scripts/{name} --help", ci)


if __name__ == "__main__":
    unittest.main()
