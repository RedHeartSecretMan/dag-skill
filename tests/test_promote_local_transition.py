from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skill"
    / "dag"
    / "scripts"
    / "promote_local_transition.py"
)
INTEGRATION_REF = "refs/heads/integration"


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        env={
            name: value
            for name, value in os.environ.items()
            if not name.startswith("GIT_")
        },
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def commit(repository: Path, message: str) -> str:
    git(repository, "add", ".")
    git(
        repository,
        "-c",
        "user.name=DAG Skill Tests",
        "-c",
        "user.email=dag-skill-tests@example.invalid",
        "commit",
        "--quiet",
        "-m",
        message,
    )
    return git(repository, "rev-parse", "HEAD")


class LocalPromotionTests(unittest.TestCase):
    def setUp(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("Git is unavailable")
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repository = self.root / "target"
        self.repository.mkdir()
        git(self.repository, "init", "--quiet", "-b", "work")
        (self.repository / "product.txt").write_text("base\n", encoding="utf-8")
        self.base = commit(self.repository, "base")
        git(self.repository, "branch", "integration", self.base)
        (self.repository / "product.txt").write_text("candidate\n", encoding="utf-8")
        self.candidate = commit(self.repository, "candidate")
        self.tree = git(self.repository, "rev-parse", f"{self.candidate}^{{tree}}")
        self.record_directory = self.root / "receipt"
        self.record_directory.mkdir()
        self.evidence = self.record_directory / "review.md"
        self.evidence.write_bytes(b"project-specific reviewed evidence\n")
        self.transition = self.record_directory / "pending.json"
        self.payload = {
            "schema_version": 1,
            "candidate_kind": "Promotion Candidate",
            "integration_ref": INTEGRATION_REF,
            "base": self.base,
            "candidate": self.candidate,
            "candidate_tree": self.tree,
            "evidence": [{"path": "review.md", "sha256": self.digest(self.evidence)}],
        }
        self.freeze()

    @staticmethod
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def freeze(self) -> None:
        self.transition.write_text(json.dumps(self.payload) + "\n", encoding="utf-8")
        self.transition_digest = self.digest(self.transition)

    def promote(self, digest: str | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repository",
                str(self.repository),
                "--transition",
                str(self.transition),
                "--sha256",
                self.transition_digest if digest is None else digest,
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def assert_rejected(
        self, result: subprocess.CompletedProcess[str], expected: str
    ) -> None:
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.startswith("error: "), result.stderr)
        self.assertIn(expected, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(git(self.repository, "rev-parse", INTEGRATION_REF), self.base)

    def git_wrapper(self, code: str) -> str:
        real_git = shutil.which("git")
        assert real_git is not None
        wrapper_directory = self.root / "wrapper"
        wrapper_directory.mkdir()
        wrapper = wrapper_directory / "git"
        wrapper.write_text(
            f"#!{sys.executable}\n"
            "import os\nimport subprocess\nimport sys\nfrom pathlib import Path\n"
            f"real_git = {real_git!r}\n"
            + code
            + "\nos.execv(real_git, [real_git, *sys.argv[1:]])\n",
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
        return str(wrapper_directory) + os.pathsep + os.environ["PATH"]

    def test_promotes_exact_candidate_and_preserves_frozen_input(self) -> None:
        record_bytes = self.transition.read_bytes()
        evidence_bytes = self.evidence.read_bytes()

        result = self.promote()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "status": "local-promoted",
                "candidate_kind": "Promotion Candidate",
                "integration_ref": INTEGRATION_REF,
                "base": self.base,
                "candidate": self.candidate,
                "candidate_tree": self.tree,
                "transition_sha256": self.transition_digest,
            },
        )
        self.assertEqual(
            git(self.repository, "rev-parse", INTEGRATION_REF), self.candidate
        )
        self.assertEqual(self.transition.read_bytes(), record_bytes)
        self.assertEqual(self.evidence.read_bytes(), evidence_bytes)
        self.assertEqual(git(self.repository, "status", "--porcelain"), "")

    def test_recovers_the_same_frozen_transition_after_promotion(self) -> None:
        self.assertEqual(self.promote().returncode, 0)

        result = self.promote()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "local-already-promoted")

    def test_accepts_a_definition_checkpoint_with_absolute_evidence_path(self) -> None:
        self.payload["candidate_kind"] = "DAG Definition Checkpoint"
        self.payload["evidence"][0]["path"] = str(self.evidence)
        self.freeze()

        result = self.promote()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout)["candidate_kind"], "DAG Definition Checkpoint"
        )

    def test_missing_pending_record_does_not_move_ref(self) -> None:
        self.transition.unlink()
        self.assert_rejected(self.promote(), "No such file")

    def test_malformed_or_non_utf8_record_does_not_move_ref(self) -> None:
        for content in (b"not JSON", b"\xff", b"[]", b"{}"):
            with self.subTest(content=content):
                self.transition.write_bytes(content)
                self.transition_digest = self.digest(self.transition)
                self.assert_rejected(self.promote(), "pending transition")

    def test_exact_record_digest_is_required(self) -> None:
        self.assert_rejected(self.promote("0" * 64), "SHA-256 does not match")
        self.assert_rejected(self.promote("short"), "64 lowercase hex digits")

    def test_rejects_duplicate_fields_and_oversized_integers(self) -> None:
        contents = (
            '{"schema_version":1,"schema_version":1}',
            '{"schema_version":' + "1" * 5000 + "}",
        )
        for content, expected in zip(
            contents, ("duplicate JSON field", "oversized"), strict=True
        ):
            with self.subTest(expected=expected):
                self.transition.write_text(content, encoding="utf-8")
                self.transition_digest = self.digest(self.transition)
                self.assert_rejected(self.promote(), expected)

    def test_rejects_incomplete_or_unsupported_schema(self) -> None:
        modifications = (
            ("schema_version", True, "integer 1"),
            ("schema_version", 2, "integer 1"),
            ("candidate_kind", "Baseline Satisfaction", "Integration Transition kind"),
            ("integration_ref", "integration", "full refs/heads/"),
            ("base", self.base[:12], "full lowercase Git object ID"),
            ("candidate", self.base, "differ from Base"),
            ("evidence", [], "nonempty array"),
            ("evidence", [{"path": "review.md"}], "exactly path and sha256"),
            (
                "evidence",
                [{"path": "review.md", "sha256": "wrong"}],
                "64 lowercase hex",
            ),
        )
        for field, value, expected in modifications:
            with self.subTest(field=field, value=value):
                original = self.payload[field]
                self.payload[field] = value
                self.freeze()
                self.assert_rejected(self.promote(), expected)
                self.payload[field] = original
        self.payload["unexpected"] = "ignored?"
        self.freeze()
        self.assert_rejected(self.promote(), "fields do not match")

    def test_missing_or_modified_evidence_does_not_move_ref(self) -> None:
        self.evidence.unlink()
        self.assert_rejected(self.promote(), "No such file")
        self.evidence.write_bytes(b"changed after review\n")
        self.assert_rejected(self.promote(), "evidence SHA-256 does not match")

    def test_rejects_duplicate_evidence_aliases(self) -> None:
        self.payload["evidence"].append(
            {"path": "./review.md", "sha256": self.digest(self.evidence)}
        )
        self.freeze()
        self.assert_rejected(self.promote(), "evidence paths must be unique")

    def test_rejects_symlink_pending_record_or_evidence(self) -> None:
        saved = self.transition.with_name("saved.json")
        self.transition.rename(saved)
        self.transition.symlink_to(saved)
        self.assert_rejected(self.promote(), "regular file, not a symlink")
        self.transition.unlink()
        saved.rename(self.transition)
        saved_evidence = self.evidence.with_name("saved.md")
        self.evidence.rename(saved_evidence)
        self.evidence.symlink_to(saved_evidence)
        self.assert_rejected(self.promote(), "regular file, not a symlink")

    def test_rejects_wrong_or_missing_objects(self) -> None:
        for field, oid, expected in (
            (
                "candidate_tree",
                git(self.repository, "rev-parse", f"{self.base}^{{tree}}"),
                "candidate_tree does not match",
            ),
            ("candidate_tree", self.candidate, "local tree object"),
            ("candidate", self.tree, "local commit object"),
            ("candidate", "0" * len(self.candidate), "could not get object info"),
        ):
            with self.subTest(field=field, expected=expected):
                original = self.payload[field]
                self.payload[field] = oid
                self.freeze()
                self.assert_rejected(self.promote(), expected)
                self.payload[field] = original

    def test_rejects_candidate_without_base_ancestry(self) -> None:
        unrelated = git(
            self.repository,
            "-c",
            "user.name=DAG Skill Tests",
            "-c",
            "user.email=dag-skill-tests@example.invalid",
            "commit-tree",
            self.tree,
            "-m",
            "unrelated root",
        )
        self.payload["candidate"] = unrelated
        self.freeze()
        self.assert_rejected(self.promote(), "Base must be a local ancestor")

    def test_rejects_fabricated_ancestry_from_repository_grafts(self) -> None:
        unrelated = git(
            self.repository,
            "-c",
            "user.name=DAG Skill Tests",
            "-c",
            "user.email=dag-skill-tests@example.invalid",
            "commit-tree",
            self.tree,
            "-m",
            "unrelated root",
        )
        headers = git(self.repository, "cat-file", "-p", unrelated).split("\n\n", 1)[0]
        self.assertFalse(
            any(line.startswith("parent ") for line in headers.splitlines())
        )
        grafts = self.repository / ".git" / "info" / "grafts"
        grafts.write_text(f"{unrelated} {self.base}\n", encoding="ascii")
        # Establish that ordinary Git sees the fabricated edge while the
        # immutable commit object above has no parent.
        git(self.repository, "merge-base", "--is-ancestor", self.base, unrelated)
        self.payload["candidate"] = unrelated
        self.freeze()

        self.assert_rejected(self.promote(), "Base must be a local ancestor")

    def test_rejects_checked_out_branch_in_main_or_linked_worktree(self) -> None:
        git(self.repository, "checkout", "--quiet", "integration")
        self.assert_rejected(self.promote(), "checked out in a worktree")
        git(self.repository, "checkout", "--quiet", "work")
        linked = self.root / "linked"
        git(self.repository, "worktree", "add", "--quiet", str(linked), "integration")
        self.assert_rejected(self.promote(), "checked out in a worktree")

    def test_rejects_symbolic_integration_ref_without_writing_its_target(self) -> None:
        git(self.repository, "branch", "other", self.base)
        git(self.repository, "symbolic-ref", INTEGRATION_REF, "refs/heads/other")
        self.assert_rejected(self.promote(), "must not be symbolic")
        self.assertEqual(
            git(self.repository, "rev-parse", "refs/heads/other"), self.base
        )
        self.assertEqual(
            git(self.repository, "symbolic-ref", INTEGRATION_REF), "refs/heads/other"
        )

    def test_rejects_invalid_branch_ref(self) -> None:
        self.payload["integration_ref"] = "refs/heads/bad..name"
        self.freeze()
        self.assert_rejected(self.promote(), "Git command failed")

    def test_rejects_base_drift(self) -> None:
        (self.repository / "product.txt").write_text("later\n", encoding="utf-8")
        later = commit(self.repository, "later")
        git(self.repository, "update-ref", INTEGRATION_REF, later, self.base)

        result = self.promote()

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("drifted", result.stderr)
        self.assertEqual(git(self.repository, "rev-parse", INTEGRATION_REF), later)

    def test_rejects_transition_or_evidence_inside_delivery(self) -> None:
        self.payload["evidence"] = [
            {
                "path": str(self.repository / "product.txt"),
                "sha256": self.digest(self.repository / "product.txt"),
            }
        ]
        self.freeze()
        self.assert_rejected(self.promote(), "must be off-delivery")
        original = self.transition
        self.transition = self.repository / "product.txt"
        self.freeze()
        self.payload["evidence"] = [
            {"path": str(self.evidence), "sha256": self.digest(self.evidence)}
        ]
        self.freeze()
        self.assert_rejected(self.promote(), "must be off-delivery")
        self.transition = original

    def test_rejects_evidence_added_only_in_current_index(self) -> None:
        staged = self.repository / "staged-report.md"
        staged.write_bytes(self.evidence.read_bytes())
        git(self.repository, "add", "staged-report.md")
        self.payload["evidence"][0]["path"] = str(staged)
        self.freeze()
        self.assert_rejected(self.promote(), "must be off-delivery")

    def test_rejects_evidence_staged_in_a_linked_worktree(self) -> None:
        linked = self.root / "linked"
        git(
            self.repository,
            "worktree",
            "add",
            "--quiet",
            "--detach",
            str(linked),
            self.base,
        )
        staged = linked / "staged-report.md"
        staged.write_bytes(self.evidence.read_bytes())
        git(linked, "add", "staged-report.md")
        self.payload["evidence"][0]["path"] = str(staged)
        self.freeze()
        self.assert_rejected(self.promote(), "must be off-delivery")

    def test_rejects_a_candidate_tracked_path_removed_from_current_checkout(
        self,
    ) -> None:
        report = self.repository / "candidate-report.md"
        report.write_bytes(self.evidence.read_bytes())
        self.candidate = commit(self.repository, "candidate with tracked report")
        self.payload["candidate"] = self.candidate
        self.payload["candidate_tree"] = git(
            self.repository, "rev-parse", f"{self.candidate}^{{tree}}"
        )
        git(self.repository, "rm", "candidate-report.md")
        commit(self.repository, "later checkout without report")
        report.write_bytes(self.evidence.read_bytes())
        self.payload["evidence"][0]["path"] = str(report)
        self.freeze()
        self.assert_rejected(self.promote(), "must be off-delivery")

    def test_ignores_ambient_git_repository_config_and_replace_environment(
        self,
    ) -> None:
        unrelated = self.root / "unrelated"
        unrelated.mkdir()
        git(unrelated, "init", "--quiet")
        with mock.patch.dict(
            os.environ,
            {
                "GIT_DIR": str(unrelated / ".git"),
                "GIT_WORK_TREE": str(unrelated),
                "GIT_OBJECT_DIRECTORY": str(unrelated / ".git" / "objects"),
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "core.bare",
                "GIT_CONFIG_VALUE_0": "true",
                "GIT_NO_REPLACE_OBJECTS": "0",
            },
            clear=False,
        ):
            result = self.promote()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            git(self.repository, "rev-parse", INTEGRATION_REF), self.candidate
        )

    def test_ignores_actual_git_replace_refs(self) -> None:
        git(self.repository, "replace", self.candidate, self.base)

        result = self.promote()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["candidate_tree"], self.tree)
        self.assertEqual(
            git(self.repository, "rev-parse", INTEGRATION_REF), self.candidate
        )

    def test_supports_full_sha256_git_object_ids(self) -> None:
        repository = self.root / "sha256"
        repository.mkdir()
        try:
            git(repository, "init", "--quiet", "--object-format=sha256", "-b", "work")
        except subprocess.CalledProcessError:
            self.skipTest("Git does not support SHA-256 repositories")
        self.repository = repository
        (repository / "product.txt").write_text("base\n", encoding="utf-8")
        self.base = commit(repository, "base")
        git(repository, "branch", "integration", self.base)
        (repository / "product.txt").write_text("candidate\n", encoding="utf-8")
        self.candidate = commit(repository, "candidate")
        self.tree = git(repository, "rev-parse", f"{self.candidate}^{{tree}}")
        self.payload.update(
            base=self.base, candidate=self.candidate, candidate_tree=self.tree
        )
        self.freeze()

        result = self.promote()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)["candidate"]), 64)
        self.assertEqual(git(repository, "rev-parse", INTEGRATION_REF), self.candidate)

    def test_does_not_lazy_fetch_a_missing_candidate_tree(self) -> None:
        git(self.repository, "config", "uploadpack.allowFilter", "true")
        partial = self.root / "partial"
        subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--filter=tree:0",
                "--no-checkout",
                self.repository.as_uri(),
                str(partial),
            ],
            capture_output=True,
            check=True,
        )
        probe_environment = {**os.environ, "GIT_NO_LAZY_FETCH": "1"}
        missing_before = subprocess.run(
            ["git", "cat-file", "-e", self.tree],
            cwd=partial,
            env=probe_environment,
            capture_output=True,
            check=False,
        )
        if missing_before.returncode == 0:
            self.skipTest("Git partial clone did not omit the candidate tree")
        git(partial, "update-ref", INTEGRATION_REF, self.base)
        self.repository = partial

        result = self.promote()
        missing_after = subprocess.run(
            ["git", "cat-file", "-e", self.tree],
            cwd=partial,
            env=probe_environment,
            capture_output=True,
            check=False,
        )

        self.assert_rejected(result, "could not get object info")
        self.assertNotEqual(
            missing_after.returncode, 0, "promotion fetched a missing object"
        )

    def test_disables_reference_transaction_hooks_during_local_promotion(self) -> None:
        hooks = self.root / "hooks"
        hooks.mkdir()
        marker = self.root / "hook-invoked"
        hook = hooks / "reference-transaction"
        hook.write_text(
            f"#!{sys.executable}\n"
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).touch()\n",
            encoding="utf-8",
        )
        hook.chmod(0o755)
        git(self.repository, "config", "core.hooksPath", str(hooks))

        result = self.promote()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists(), "local CAS executed a project hook")

    def test_rereads_evidence_after_mutable_preflight(self) -> None:
        counter = self.root / "counter"
        path = self.git_wrapper(
            "if sys.argv[1:3] == ['worktree', 'list']:\n"
            f"    counter = Path({str(counter)!r})\n"
            "    count = int(counter.read_text()) if counter.exists() else 0\n"
            "    counter.write_text(str(count + 1))\n"
            "    if count == 1:\n"
            f"        Path({str(self.evidence)!r}).write_bytes(b'changed during preflight')\n"
        )
        with mock.patch.dict(os.environ, {"PATH": path}):
            result = self.promote()
        self.assert_rejected(result, "evidence SHA-256 does not match")

    def test_rereads_transition_after_mutable_preflight(self) -> None:
        path = self.git_wrapper(
            "if sys.argv[1] == 'show-ref':\n"
            f"    record = Path({str(self.transition)!r})\n"
            "    record.write_bytes(record.read_bytes() + b' ')\n"
        )
        with mock.patch.dict(os.environ, {"PATH": path}):
            result = self.promote()
        self.assert_rejected(result, "pending transition changed during preflight")

    def test_failed_cas_preserves_inputs_and_does_not_move_ref(self) -> None:
        before = self.transition.read_bytes(), self.evidence.read_bytes()
        path = self.git_wrapper(
            "if 'update-ref' in sys.argv[1:]:\n"
            "    print('injected CAS failure', file=sys.stderr)\n"
            "    sys.exit(1)\n"
        )
        with mock.patch.dict(os.environ, {"PATH": path}):
            result = self.promote()
        self.assert_rejected(result, "injected CAS failure")
        self.assertEqual(
            (self.transition.read_bytes(), self.evidence.read_bytes()), before
        )

    def test_cas_refuses_base_drift_after_preflight(self) -> None:
        (self.repository / "product.txt").write_text("later\n", encoding="utf-8")
        later = commit(self.repository, "later")
        path = self.git_wrapper(
            "if 'update-ref' in sys.argv[1:]:\n"
            f"    subprocess.run([real_git, 'update-ref', {INTEGRATION_REF!r}, {later!r}, {self.base!r}], check=True)\n"
        )
        before = self.transition.read_bytes(), self.evidence.read_bytes()

        with mock.patch.dict(os.environ, {"PATH": path}):
            result = self.promote()

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("cannot lock ref", result.stderr)
        self.assertEqual(git(self.repository, "rev-parse", INTEGRATION_REF), later)
        self.assertEqual(
            (self.transition.read_bytes(), self.evidence.read_bytes()), before
        )

    def test_failed_post_cas_readback_leaves_pending_and_allows_recovery(self) -> None:
        marker = self.root / "promoted"
        before = self.transition.read_bytes(), self.evidence.read_bytes()
        path = self.git_wrapper(
            "if 'update-ref' in sys.argv[1:]:\n"
            "    completed = subprocess.run([real_git, *sys.argv[1:]], check=False)\n"
            "    if completed.returncode == 0:\n"
            f"        Path({str(marker)!r}).touch()\n"
            "    sys.exit(completed.returncode)\n"
            f"if sys.argv[1] == 'show-ref' and Path({str(marker)!r}).exists():\n"
            "    print('injected readback failure', file=sys.stderr)\n"
            "    sys.exit(1)\n"
        )
        with mock.patch.dict(os.environ, {"PATH": path}):
            result = self.promote()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("readback failed; preserve pending evidence", result.stderr)
        self.assertEqual(
            git(self.repository, "rev-parse", INTEGRATION_REF), self.candidate
        )
        self.assertEqual(
            (self.transition.read_bytes(), self.evidence.read_bytes()), before
        )
        recovery = self.promote()
        self.assertEqual(recovery.returncode, 0, recovery.stderr)
        self.assertEqual(
            json.loads(recovery.stdout)["status"], "local-already-promoted"
        )


if __name__ == "__main__":
    unittest.main()
