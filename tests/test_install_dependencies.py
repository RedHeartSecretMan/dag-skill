from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path, PurePosixPath, PureWindowsPath
from unittest import mock

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skill"
    / "dag"
    / "scripts"
    / "install_dependencies.py"
)
SPEC = importlib.util.spec_from_file_location("dag_install_dependencies", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


def create_sources(root: Path) -> dict[str, Path]:
    sources: dict[str, Path] = {}
    for skill in installer.SKILLS:
        source = root / skill
        source.mkdir(parents=True)
        for relative in installer.REQUIRED_FILES[skill]:
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{skill}:{relative}\n", encoding="utf-8")
        metadata = source / "agents" / "openai.yaml"
        metadata.parent.mkdir()
        metadata.write_text(f'display_name: "{skill}"\n', encoding="utf-8")
        sources[skill] = source
    return sources


class GitIsolationTests(unittest.TestCase):
    def test_run_git_detaches_repository_environment_and_sets_a_timeout(self) -> None:
        contaminated = {
            "GIT_DIR": "/tmp/unrelated.git",
            "GIT_WORK_TREE": "/tmp/unrelated-worktree",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.worktree",
            "GIT_CONFIG_VALUE_0": "/tmp/other-worktree",
            "GIT_CONFIG_GLOBAL": "/tmp/global-config",
            "GIT_CONFIG_SYSTEM": "/tmp/system-config",
            "GIT_EXEC_PATH": "/tmp/git-exec",
            "GIT_ASKPASS": "/tmp/askpass",
            "GIT_TEMPLATE_DIR": "/tmp/git-template",
            "GIT_UNRECOGNIZED_INPUT": "/tmp/other-input",
        }
        completed = subprocess.CompletedProcess(
            ["git", "status"], returncode=0, stdout="ok\n", stderr=""
        )

        with (
            mock.patch.dict(os.environ, contaminated, clear=False),
            mock.patch.object(
                installer.subprocess, "run", return_value=completed
            ) as run,
        ):
            result = installer.run_git(["status"], Path("/tmp"))

        self.assertEqual(result, "ok")
        environment = run.call_args.kwargs["env"]
        self.assertEqual(
            {
                name: value
                for name, value in environment.items()
                if name.startswith("GIT_")
            },
            installer.SAFE_GIT_ENVIRONMENT,
        )
        self.assertEqual(
            run.call_args.args[0][1:3],
            ["-c", "core.hooksPath=/tmp/.git/dag-skill-disabled-hooks"],
        )
        self.assertEqual(run.call_args.kwargs["timeout"], installer.GIT_TIMEOUT_SECONDS)

    def test_run_git_reports_the_bounded_timeout(self) -> None:
        with mock.patch.object(
            installer.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(
                ["git", "fetch"], installer.GIT_TIMEOUT_SECONDS
            ),
        ):
            with self.assertRaisesRegex(installer.InstallError, "setup bound"):
                installer.run_git(["fetch"], Path("/tmp"))

    def test_fetch_uses_an_explicit_empty_template_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)

            with mock.patch.object(
                installer, "run_git", side_effect=["", "", "", installer.REVISION]
            ) as run:
                with self.assertRaisesRegex(
                    installer.InstallError, "source is missing"
                ):
                    installer.fetch_pinned_source(workspace)

            init_arguments = run.call_args_list[0].args[0]
            self.assertEqual(init_arguments[:2], ["init", "--quiet"])
            template_options = [
                argument
                for argument in init_arguments
                if argument.startswith("--template=")
            ]
            self.assertEqual(len(template_options), 1)
            self.assertTrue((workspace / "empty-git-templates").is_dir())


class PathSafetyTests(unittest.TestCase):
    def test_python_runtime_floor_is_3_12(self) -> None:
        installer.require_supported_python((3, 12))
        installer.require_supported_python((3, 14))
        with self.assertRaisesRegex(installer.InstallError, r"Python 3.12\+"):
            installer.require_supported_python((3, 11))

    def test_filesystem_roots_cover_posix_drive_and_unc_forms(self) -> None:
        roots = (
            PurePosixPath("/"),
            PureWindowsPath("C:/"),
            PureWindowsPath("//server/share/"),
        )
        for root in roots:
            with self.subTest(root=root):
                self.assertTrue(installer.is_filesystem_root(root))
        self.assertFalse(installer.is_filesystem_root(PurePosixPath("/tmp/skills")))
        self.assertFalse(installer.is_filesystem_root(PureWindowsPath("C:/skills")))

    def test_install_rejects_the_live_filesystem_root_before_fetch(self) -> None:
        with mock.patch.object(installer, "fetch_pinned_source") as fetch:
            with self.assertRaisesRegex(installer.InstallError, "filesystem root"):
                installer.install(Path("/"))
        fetch.assert_not_called()


class BundleInstallationTests(unittest.TestCase):
    def run_install(self, sources: dict[str, Path], skills_root: Path) -> str:
        output = io.StringIO()
        with (
            mock.patch.object(installer, "fetch_pinned_source", return_value=sources),
            mock.patch.object(installer.shutil, "which", return_value="/usr/bin/git"),
        ):
            with contextlib.redirect_stdout(output):
                installer.install(skills_root)
        return output.getvalue()

    def test_complete_bundle_install_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = create_sources(root / "sources")
            skills_root = root / "host" / "skills"

            first = self.run_install(sources, skills_root)
            digests = {
                skill: installer.tree_digest(skills_root / skill)
                for skill in installer.SKILLS
            }
            second = self.run_install(sources, skills_root)

            self.assertIn("Installed pinned Matt Skill bundle", first)
            self.assertIn("already current", second)
            for skill in installer.SKILLS:
                self.assertEqual(
                    installer.tree_digest(skills_root / skill), digests[skill]
                )
                self.assertTrue(
                    (skills_root / skill / "agents" / "openai.yaml").is_file()
                )

    def test_conflict_preflight_preserves_all_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = create_sources(root / "sources")
            skills_root = root / "skills"
            shutil.copytree(sources["tdd"], skills_root / "tdd")
            conflict = skills_root / "tdd" / "SKILL.md"
            conflict.write_text("local version\n", encoding="utf-8")

            with self.assertRaisesRegex(installer.InstallError, "tdd"):
                self.run_install(sources, skills_root)

            self.assertEqual(conflict.read_text(encoding="utf-8"), "local version\n")
            self.assertFalse((skills_root / "implement").exists())

    def test_symlink_target_is_preserved_as_a_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = create_sources(root / "sources")
            skills_root = root / "skills"
            skills_root.mkdir()
            target = skills_root / "implement"
            try:
                target.symlink_to(sources["implement"], target_is_directory=True)
            except OSError as error:
                self.skipTest(f"directory symlinks unavailable: {error}")

            with self.assertRaisesRegex(installer.InstallError, "implement"):
                self.run_install(sources, skills_root)

            self.assertTrue(target.is_symlink())
            self.assertFalse((skills_root / "code-review").exists())

    def test_target_created_after_preflight_preserves_every_completed_target(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = create_sources(root / "sources")
            skills_root = root / "skills"
            original = installer.install_staged_skill

            def create_racing_target(
                staged: Path, target: Path, expected_digest: str
            ) -> None:
                if target.name == "code-review":
                    target.mkdir()
                    (target / "owner.txt").write_text(
                        "other process\n", encoding="utf-8"
                    )
                return original(staged, target, expected_digest)

            with (
                mock.patch.object(
                    installer, "fetch_pinned_source", return_value=sources
                ),
                mock.patch.object(
                    installer.shutil, "which", return_value="/usr/bin/git"
                ),
                mock.patch.object(
                    installer, "install_staged_skill", side_effect=create_racing_target
                ),
            ):
                with self.assertRaisesRegex(installer.InstallError, "Target appeared"):
                    installer.install(skills_root)

            self.assertEqual(
                installer.tree_digest(skills_root / "implement"),
                installer.tree_digest(sources["implement"]),
            )
            self.assertEqual(
                (skills_root / "code-review" / "owner.txt").read_text(encoding="utf-8"),
                "other process\n",
            )

    def test_partial_reserved_target_is_preserved_after_copy_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = create_sources(root / "sources")
            target = root / "skills" / "implement"
            target.parent.mkdir()

            def fail_after_partial_copy(source: Path, destination: Path) -> None:
                del source
                (destination / "partial.txt").write_text("partial\n", encoding="utf-8")
                raise OSError("injected copy failure")

            with mock.patch.object(
                installer,
                "copy_directory_contents",
                side_effect=fail_after_partial_copy,
            ):
                with self.assertRaisesRegex(
                    installer.InstallError, "remains for inspection"
                ):
                    installer.install_staged_skill(
                        sources["implement"],
                        target,
                        installer.tree_digest(sources["implement"]),
                    )

            self.assertEqual(
                (target / "partial.txt").read_text(encoding="utf-8"), "partial\n"
            )


if __name__ == "__main__":
    unittest.main()
