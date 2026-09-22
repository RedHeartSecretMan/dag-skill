from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath, PureWindowsPath
from unittest import mock

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skill"
    / "dag"
    / "scripts"
    / "install_runtime_skills.py"
)
SPEC = importlib.util.spec_from_file_location("dag_install_runtime_skills", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


def create_sources(root: Path) -> dict[str, Path]:
    sources: dict[str, Path] = {}
    for skill in installer.AVAILABLE_SKILLS:
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
            with self.assertRaisesRegex(installer.InstallError, "installation bound"):
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

    def test_fetch_rejects_content_outside_the_pinned_tree_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)

            def emulate_git(arguments: list[str], cwd: Path) -> str:
                if arguments[0] == "checkout":
                    create_sources(cwd / installer.UPSTREAM_BUNDLE_ROOT)
                if arguments[0] == "rev-parse":
                    return installer.REVISION
                return ""

            with mock.patch.object(installer, "run_git", side_effect=emulate_git):
                with self.assertRaisesRegex(installer.InstallError, "source digest"):
                    installer.fetch_pinned_source(workspace)

    def test_fetch_checks_out_a_matching_local_revision(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("Git is unavailable")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            upstream = root / "upstream"
            templates = root / "empty-git-templates"
            workspace = root / "workspace"
            upstream.mkdir()
            templates.mkdir()
            workspace.mkdir()
            installer.run_git(["init", "--quiet", f"--template={templates}"], upstream)
            sources = create_sources(upstream / installer.UPSTREAM_BUNDLE_ROOT)
            installer.run_git(["add", "."], upstream)
            installer.run_git(
                [
                    "-c",
                    "user.name=DAG Skill Tests",
                    "-c",
                    "user.email=dag-skill-tests@example.invalid",
                    "commit",
                    "--quiet",
                    "-m",
                    "fixture",
                ],
                upstream,
            )
            revision = installer.run_git(["rev-parse", "HEAD"], upstream)
            source_digests = {
                skill: installer.tree_digest(source)
                for skill, source in sources.items()
            }

            with (
                mock.patch.object(installer, "REPOSITORY", str(upstream)),
                mock.patch.object(installer, "REVISION", revision),
                mock.patch.object(installer, "PINNED_TREE_DIGESTS", source_digests),
            ):
                fetched = installer.fetch_pinned_source(workspace)

            self.assertEqual(set(fetched), set(installer.RUNTIME_SKILLS))
            for skill in installer.RUNTIME_SKILLS:
                self.assertEqual(
                    installer.tree_digest(fetched[skill]), source_digests[skill]
                )


class MinimumRevisionInstallationTests(unittest.TestCase):
    def setUp(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("Git is unavailable")
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.upstream = self.root / "upstream"
        self.upstream.mkdir()
        installer.run_git(["init", "--quiet", "--template="], self.upstream)
        self.sources = create_sources(self.upstream / installer.UPSTREAM_BUNDLE_ROOT)
        self.before = self.commit("before minimum")
        self.review = self.sources["code-review"] / "SKILL.md"
        self.review.write_text("minimum review\n", encoding="utf-8")
        self.minimum = self.commit("minimum")
        self.minimum_digests = {
            name: installer.tree_digest(path) for name, path in self.sources.items()
        }
        self.skills_root = self.root / "host" / "skills"

    def commit(self, message: str) -> str:
        installer.run_git(["add", "."], self.upstream)
        installer.run_git(
            [
                "-c",
                "user.name=DAG Skill Tests",
                "-c",
                "user.email=dag-skill-tests@example.invalid",
                "commit",
                "--quiet",
                "-m",
                message,
            ],
            self.upstream,
        )
        return installer.run_git(["rev-parse", "HEAD"], self.upstream)

    def install(self) -> str:
        output = io.StringIO()
        with (
            mock.patch.object(installer, "REPOSITORY", str(self.upstream)),
            mock.patch.object(installer, "REVISION", self.minimum),
            mock.patch.object(installer, "PINNED_TREE_DIGESTS", self.minimum_digests),
            contextlib.redirect_stdout(output),
        ):
            installer.install(self.skills_root)
        return output.getvalue()

    def test_reuses_an_intermediate_descendant_and_installs_missing_skills(
        self,
    ) -> None:
        self.review.write_text("newer review\n", encoding="utf-8")
        descendant = self.commit("newer review")
        shutil.copytree(self.sources["code-review"], self.skills_root / "code-review")
        self.review.write_text("latest review\n", encoding="utf-8")
        self.commit("latest review")

        output = self.install()

        self.assertEqual(
            (self.skills_root / "code-review" / "SKILL.md").read_text(),
            "newer review\n",
        )
        self.assertIn(descendant, output)
        for name in ("tdd", "codebase-design"):
            self.assertEqual(
                installer.tree_digest(self.skills_root / name),
                self.minimum_digests[name],
            )
        self.assertFalse((self.skills_root / installer.SETUP_SKILL).exists())

    def test_reuses_a_descendant_from_an_upstream_branch(self) -> None:
        installer.run_git(["checkout", "--quiet", "-b", "newer"], self.upstream)
        self.review.write_text("branch review\n", encoding="utf-8")
        descendant = self.commit("branch review")
        shutil.copytree(self.sources["code-review"], self.skills_root / "code-review")
        installer.run_git(
            ["checkout", "--quiet", "--detach", self.minimum], self.upstream
        )

        output = self.install()

        self.assertIn(descendant, output)
        self.assertEqual(
            (self.skills_root / "code-review" / "SKILL.md").read_text(),
            "branch review\n",
        )

    def test_reuses_a_complete_newer_bundle_without_reinstalling(self) -> None:
        self.review.write_text("newer review\n", encoding="utf-8")
        descendant = self.commit("newer bundle")
        for skill in installer.RUNTIME_SKILLS:
            shutil.copytree(self.sources[skill], self.skills_root / skill)
        before = installer.tree_digest(self.skills_root)

        output = self.install()

        self.assertIn("already current", output)
        self.assertIn(descendant, output)
        self.assertEqual(installer.tree_digest(self.skills_root), before)

    def test_reuses_a_descendant_reachable_only_from_a_tag(self) -> None:
        branch = installer.run_git(["symbolic-ref", "HEAD"], self.upstream)
        self.review.write_text("tagged review\n", encoding="utf-8")
        descendant = self.commit("tagged review")
        installer.run_git(["tag", "newer-release"], self.upstream)
        shutil.copytree(self.sources["code-review"], self.skills_root / "code-review")
        installer.run_git(
            ["checkout", "--quiet", "--detach", self.minimum], self.upstream
        )
        installer.run_git(["update-ref", branch, self.minimum], self.upstream)

        output = self.install()

        self.assertIn(descendant, output)
        self.assertEqual(
            (self.skills_root / "code-review" / "SKILL.md").read_text(),
            "tagged review\n",
        )

    def test_unavailable_source_preserves_newer_targets_without_writing(self) -> None:
        self.review.write_text("newer review\n", encoding="utf-8")
        self.commit("newer review")
        shutil.copytree(self.sources["code-review"], self.skills_root / "code-review")
        before = installer.tree_digest(self.skills_root)
        self.upstream.rename(self.root / "unavailable-upstream")

        with self.assertRaises(installer.InstallError):
            self.install()

        self.assertEqual(installer.tree_digest(self.skills_root), before)
        self.assertFalse((self.skills_root / "tdd").exists())

    def test_rejects_content_from_before_the_minimum_without_writing(self) -> None:
        installer.run_git(
            ["checkout", "--quiet", "--detach", self.before], self.upstream
        )
        shutil.copytree(self.sources["code-review"], self.skills_root / "code-review")
        before = installer.tree_digest(self.skills_root / "code-review")
        installer.run_git(
            ["checkout", "--quiet", "--detach", self.minimum], self.upstream
        )

        with self.assertRaisesRegex(installer.InstallError, "code-review"):
            self.install()

        self.assertEqual(
            installer.tree_digest(self.skills_root / "code-review"), before
        )
        self.assertFalse((self.skills_root / "tdd").exists())

    def test_rejects_a_later_commit_without_minimum_ancestry(self) -> None:
        installer.run_git(
            ["checkout", "--quiet", "-b", "diverged", self.before], self.upstream
        )
        self.review.write_text("diverged review\n", encoding="utf-8")
        self.commit("not a descendant")
        shutil.copytree(self.sources["code-review"], self.skills_root / "code-review")
        before = installer.tree_digest(self.skills_root / "code-review")

        with self.assertRaisesRegex(installer.InstallError, "code-review"):
            self.install()

        self.assertEqual(
            installer.tree_digest(self.skills_root / "code-review"), before
        )
        self.assertFalse((self.skills_root / "tdd").exists())

    def test_preserves_local_edits_to_a_descendant(self) -> None:
        self.review.write_text("newer review\n", encoding="utf-8")
        self.commit("newer review")
        shutil.copytree(self.sources["code-review"], self.skills_root / "code-review")
        local = self.skills_root / "code-review" / "SKILL.md"
        local.write_text("local edits\n", encoding="utf-8")

        with self.assertRaisesRegex(installer.InstallError, "code-review"):
            self.install()

        self.assertEqual(local.read_text(), "local edits\n")
        self.assertFalse((self.skills_root / "tdd").exists())

    def test_final_verification_rejects_changes_to_a_reused_descendant(self) -> None:
        self.review.write_text("newer review\n", encoding="utf-8")
        self.commit("newer review")
        shutil.copytree(self.sources["code-review"], self.skills_root / "code-review")
        self.review.write_text("latest review\n", encoding="utf-8")
        self.commit("latest review")
        original = installer.install_staged_skill

        def concurrent_update(staged: Path, target: Path, expected: str) -> None:
            original(staged, target, expected)
            (self.skills_root / "code-review" / "SKILL.md").write_text(
                "latest review\n", encoding="utf-8"
            )

        with mock.patch.object(
            installer, "install_staged_skill", side_effect=concurrent_update
        ):
            with self.assertRaisesRegex(installer.InstallError, "bundle verification"):
                self.install()

        self.assertEqual(
            (self.skills_root / "code-review" / "SKILL.md").read_text(),
            "latest review\n",
        )


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

    def test_tree_digest_frames_file_content_and_following_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first"
            second = root / "second"
            first.mkdir()
            second.mkdir()
            (first / "a").write_bytes(b"x\0F\0b\0y")
            (second / "a").write_bytes(b"x")
            (second / "b").write_bytes(b"y")

            self.assertNotEqual(
                installer.tree_digest(first), installer.tree_digest(second)
            )


class BundleContractTests(unittest.TestCase):
    def test_bundle_matches_runtime_bootstrap_contract(self) -> None:
        self.assertEqual(
            installer.AVAILABLE_SKILLS,
            (
                "code-review",
                "tdd",
                "codebase-design",
                "setup-matt-pocock-skills",
            ),
        )
        self.assertEqual(
            installer.RUNTIME_SKILLS,
            ("code-review", "tdd", "codebase-design"),
        )
        self.assertEqual(installer.SETUP_SKILL, "setup-matt-pocock-skills")
        self.assertEqual(
            installer.PINNED_TREE_DIGESTS,
            {
                "code-review": "469775f63f281a7f74f5ca03c08030ba48bdd5fe146003a6a0231a91051202f6",
                "tdd": "e91b8b8c3fb7e55f6432b4c7023291135ea2141578af432459b6c57b25a1bf2f",
                "codebase-design": "d8500952a6f5631d8b3f748155d70b81e18bf74d28f1f41116f3eb64988a873a",
                "setup-matt-pocock-skills": "b2dda865f0a6069d7d2c60ca3c3b95a622fe4a7bf98c96764a2f4ed6c091e0d3",
            },
        )
        self.assertEqual(
            installer.REQUIRED_FILES,
            {
                "code-review": ("SKILL.md",),
                "tdd": ("SKILL.md", "tests.md", "mocking.md"),
                "codebase-design": (
                    "SKILL.md",
                    "DEEPENING.md",
                    "DESIGN-IT-TWICE.md",
                ),
                "setup-matt-pocock-skills": (
                    "SKILL.md",
                    "domain.md",
                    "issue-tracker-github.md",
                    "issue-tracker-gitlab.md",
                    "issue-tracker-local.md",
                    "triage-labels.md",
                ),
            },
        )


class CommandLineTests(unittest.TestCase):
    def test_main_installs_only_runtime_skills_by_default(self) -> None:
        with (
            mock.patch.object(
                sys,
                "argv",
                [str(SCRIPT), "--skills-root", "/tmp/host-skills"],
            ),
            mock.patch.object(installer, "require_supported_python"),
            mock.patch.object(installer, "install") as install,
        ):
            result = installer.main()

        self.assertEqual(result, 0)
        install.assert_called_once_with(
            Path("/tmp/host-skills"), include_setup_helper=False
        )

    def test_main_passes_the_setup_helper_opt_in(self) -> None:
        with (
            mock.patch.object(
                sys,
                "argv",
                [
                    str(SCRIPT),
                    "--skills-root",
                    "/tmp/host-skills",
                    "--include-setup-helper",
                ],
            ),
            mock.patch.object(installer, "require_supported_python"),
            mock.patch.object(installer, "install") as install,
        ):
            result = installer.main()

        self.assertEqual(result, 0)
        install.assert_called_once_with(
            Path("/tmp/host-skills"), include_setup_helper=True
        )


class BundleInstallationTests(unittest.TestCase):
    def run_install(
        self,
        sources: dict[str, Path],
        skills_root: Path,
        *,
        include_setup_helper: bool = False,
    ) -> str:
        output = io.StringIO()
        source_digests = {
            skill: installer.tree_digest(source) for skill, source in sources.items()
        }
        with (
            mock.patch.object(installer, "fetch_pinned_source", return_value=sources),
            mock.patch.object(installer, "match_descendant_sources", return_value={}),
            mock.patch.object(installer, "PINNED_TREE_DIGESTS", source_digests),
            mock.patch.object(installer.shutil, "which", return_value="/usr/bin/git"),
        ):
            with contextlib.redirect_stdout(output):
                installer.install(
                    skills_root, include_setup_helper=include_setup_helper
                )
        return output.getvalue()

    def test_complete_bundle_install_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = create_sources(root / "sources")
            skills_root = root / "host" / "skills"

            first = self.run_install(sources, skills_root)
            digests = {
                skill: installer.tree_digest(skills_root / skill)
                for skill in installer.RUNTIME_SKILLS
            }
            source_digests = {
                skill: installer.tree_digest(source)
                for skill, source in sources.items()
            }
            output = io.StringIO()
            with (
                mock.patch.object(installer, "PINNED_TREE_DIGESTS", source_digests),
                mock.patch.object(installer, "fetch_pinned_source") as fetch,
                mock.patch.object(installer.shutil, "which", return_value=None),
                contextlib.redirect_stdout(output),
            ):
                installer.install(skills_root)
            second = output.getvalue()

            self.assertIn("Installed missing DAG Runtime Skill Bundle members", first)
            self.assertIn("already current", second)
            fetch.assert_not_called()
            for skill in installer.RUNTIME_SKILLS:
                self.assertEqual(
                    installer.tree_digest(skills_root / skill), digests[skill]
                )
                self.assertTrue(
                    (skills_root / skill / "agents" / "openai.yaml").is_file()
                )

    def test_default_install_only_installs_runtime_skills(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = create_sources(root / "sources")
            skills_root = root / "skills"

            self.run_install(sources, skills_root)

            for skill in installer.RUNTIME_SKILLS:
                self.assertTrue((skills_root / skill / "SKILL.md").is_file())
            self.assertFalse((skills_root / installer.SETUP_SKILL).exists())

    def test_default_install_ignores_a_conflicting_setup_helper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = create_sources(root / "sources")
            skills_root = root / "skills"
            helper = skills_root / installer.SETUP_SKILL
            helper.mkdir(parents=True)
            local_content = helper / "SKILL.md"
            local_content.write_text("local helper\n", encoding="utf-8")

            self.run_install(sources, skills_root)

            for skill in installer.RUNTIME_SKILLS:
                self.assertTrue((skills_root / skill / "SKILL.md").is_file())
            self.assertEqual(
                local_content.read_text(encoding="utf-8"), "local helper\n"
            )

    def test_opt_in_install_includes_the_setup_helper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = create_sources(root / "sources")
            skills_root = root / "skills"

            self.run_install(sources, skills_root, include_setup_helper=True)

            for skill in installer.AVAILABLE_SKILLS:
                self.assertTrue((skills_root / skill / "SKILL.md").is_file())

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
            self.assertFalse((skills_root / "code-review").exists())

    def test_symlink_target_is_preserved_as_a_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = create_sources(root / "sources")
            skills_root = root / "skills"
            skills_root.mkdir()
            target = skills_root / "code-review"
            try:
                target.symlink_to(sources["code-review"], target_is_directory=True)
            except OSError as error:
                self.skipTest(f"directory symlinks unavailable: {error}")

            with self.assertRaisesRegex(installer.InstallError, "code-review"):
                self.run_install(sources, skills_root)

            self.assertTrue(target.is_symlink())
            self.assertFalse((skills_root / "tdd").exists())

    def test_target_created_after_preflight_preserves_every_completed_target(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = create_sources(root / "sources")
            skills_root = root / "skills"
            source_digests = {
                skill: installer.tree_digest(source)
                for skill, source in sources.items()
            }
            original = installer.install_staged_skill

            def create_racing_target(
                staged: Path, target: Path, expected_digest: str
            ) -> None:
                if target.name == "tdd":
                    target.mkdir()
                    (target / "owner.txt").write_text(
                        "other process\n", encoding="utf-8"
                    )
                return original(staged, target, expected_digest)

            with (
                mock.patch.object(
                    installer, "fetch_pinned_source", return_value=sources
                ),
                mock.patch.object(installer, "PINNED_TREE_DIGESTS", source_digests),
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
                installer.tree_digest(skills_root / "code-review"),
                installer.tree_digest(sources["code-review"]),
            )
            self.assertEqual(
                (skills_root / "tdd" / "owner.txt").read_text(encoding="utf-8"),
                "other process\n",
            )

    def test_final_verification_detects_a_concurrent_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = create_sources(root / "sources")
            skills_root = root / "skills"
            shutil.copytree(sources["code-review"], skills_root / "code-review")
            source_digests = {
                skill: installer.tree_digest(source)
                for skill, source in sources.items()
            }
            original = installer.install_staged_skill
            changed = False

            def mutate_current_target(
                staged: Path, target: Path, expected_digest: str
            ) -> None:
                nonlocal changed
                original(staged, target, expected_digest)
                if not changed:
                    changed = True
                    (skills_root / "code-review" / "SKILL.md").write_text(
                        "concurrent change\n", encoding="utf-8"
                    )

            with (
                mock.patch.object(
                    installer, "fetch_pinned_source", return_value=sources
                ),
                mock.patch.object(installer, "PINNED_TREE_DIGESTS", source_digests),
                mock.patch.object(
                    installer.shutil, "which", return_value="/usr/bin/git"
                ),
                mock.patch.object(
                    installer,
                    "install_staged_skill",
                    side_effect=mutate_current_target,
                ),
            ):
                with self.assertRaisesRegex(
                    installer.InstallError, "bundle verification failed"
                ):
                    installer.install(skills_root)

            self.assertEqual(
                (skills_root / "code-review" / "SKILL.md").read_text(encoding="utf-8"),
                "concurrent change\n",
            )

    def test_child_created_after_reservation_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = create_sources(root / "sources")
            target = root / "skills" / "code-review"
            target.parent.mkdir()
            original = installer.copy_directory_contents

            def create_racing_child(source: Path, destination: Path) -> None:
                (destination / "SKILL.md").write_text(
                    "other process\n", encoding="utf-8"
                )
                original(source, destination)

            with mock.patch.object(
                installer,
                "copy_directory_contents",
                side_effect=create_racing_child,
            ):
                with self.assertRaisesRegex(
                    installer.InstallError, "remains for inspection"
                ):
                    installer.install_staged_skill(
                        sources["code-review"],
                        target,
                        installer.tree_digest(sources["code-review"]),
                    )

            self.assertEqual(
                (target / "SKILL.md").read_text(encoding="utf-8"),
                "other process\n",
            )

    def test_partial_reserved_target_is_preserved_after_copy_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = create_sources(root / "sources")
            target = root / "skills" / "code-review"
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
                        sources["code-review"],
                        target,
                        installer.tree_digest(sources["code-review"]),
                    )

            self.assertEqual(
                (target / "partial.txt").read_text(encoding="utf-8"), "partial\n"
            )


if __name__ == "__main__":
    unittest.main()
