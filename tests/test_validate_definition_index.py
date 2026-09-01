from __future__ import annotations

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
    / "validate_definition_index.py"
)


def run_git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def run_git_with_input(repository: Path, arguments: list[str], payload: bytes) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        input=payload,
        capture_output=True,
        check=True,
    )
    return result.stdout.decode("ascii").strip()


def commit(repository: Path, message: str) -> str:
    run_git(repository, "add", ".")
    run_git(
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
    return run_git(repository, "rev-parse", "HEAD")


class DefinitionIndexValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("Git is unavailable")
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repository = Path(self.temporary.name) / "target"
        self.repository.mkdir()
        run_git(self.repository, "init", "--quiet")

    def write(self, path: str, content: str | bytes) -> Path:
        destination = self.repository / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            destination.write_bytes(content)
        else:
            destination.write_text(content, encoding="utf-8")
        return destination

    def oid(self, path: str, revision: str = "HEAD") -> str:
        return run_git(self.repository, "rev-parse", f"{revision}:{path}")

    def bind(self, payload: object) -> str:
        self.write(
            ".dag/definition-index.json",
            json.dumps(payload, ensure_ascii=False) + "\n",
        )
        return commit(self.repository, "bind definition")

    def validate(
        self, revision: str, repository: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        repository = repository or self.repository
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repository",
                str(repository),
                "--commit",
                revision,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_validates_the_exact_commit_without_reading_worktree_bytes(self) -> None:
        spec = self.write("spec.md", "approved definition\n")
        commit(self.repository, "definition")
        spec_oid = self.oid("spec.md")
        validated_commit = self.bind(
            {
                "schema_version": 1,
                "inputs": [{"path": "spec.md", "blob_oid": spec_oid}],
            }
        )
        index_oid = self.oid(".dag/definition-index.json")
        spec.write_text("uncommitted drift\n", encoding="utf-8")

        result = self.validate(validated_commit)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "commit": validated_commit,
                "index": {
                    "path": ".dag/definition-index.json",
                    "blob_oid": index_oid,
                },
                "inputs": [{"path": "spec.md", "blob_oid": spec_oid}],
                "schema_version": 1,
            },
        )

    def test_queries_only_the_index_and_selected_git_paths(self) -> None:
        self.write("spec.md", "approved definition\n")
        self.write("ticket.md", "ticket\n")
        self.write("unrelated.md", "not selected\n")
        commit(self.repository, "definition")
        validated_commit = self.bind(
            {
                "schema_version": 1,
                "inputs": [
                    {"path": "spec.md", "blob_oid": self.oid("spec.md")},
                    {"path": "ticket.md", "blob_oid": self.oid("ticket.md")},
                ],
            }
        )
        real_git = shutil.which("git")
        assert real_git is not None
        wrapper_root = Path(self.temporary.name) / "git-wrapper"
        wrapper_root.mkdir()
        log = wrapper_root / "calls.jsonl"
        wrapper = wrapper_root / "git"
        wrapper.write_text(
            f"#!{sys.executable}\n"
            "import json\n"
            "import os\n"
            "import sys\n"
            f"with open({str(log)!r}, 'a', encoding='utf-8') as handle:\n"
            "    handle.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            f"os.execv({real_git!r}, [{real_git!r}, *sys.argv[1:]])\n",
            encoding="utf-8",
        )
        wrapper.chmod(0o755)

        with mock.patch.dict(
            os.environ,
            {"PATH": str(wrapper_root) + os.pathsep + os.environ["PATH"]},
            clear=False,
        ):
            result = self.validate(validated_commit)

        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        ls_tree_calls = [call for call in calls if call and call[0] == "ls-tree"]
        self.assertEqual(len(ls_tree_calls), 2)
        queried_paths = [call[call.index("--") + 1 :] for call in ls_tree_calls]
        self.assertEqual(
            queried_paths,
            [[".dag/definition-index.json"], ["spec.md", "ticket.md"]],
        )
        self.assertTrue(
            all("-r" not in call and "-rz" not in call for call in ls_tree_calls)
        )

    def test_treats_selected_git_paths_as_literals(self) -> None:
        path = "ticket[1]*?.md"
        self.write(path, "literal path\n")
        self.write("ticket1-other.md", "must not match\n")
        commit(self.repository, "definition")
        validated_commit = self.bind(
            {
                "schema_version": 1,
                "inputs": [{"path": path, "blob_oid": self.oid(path)}],
            }
        )

        result = self.validate(validated_commit)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["inputs"][0]["path"], path)

    def test_ignores_ambient_git_repository_environment(self) -> None:
        self.write("spec.md", "approved definition\n")
        commit(self.repository, "definition")
        spec_oid = self.oid("spec.md")
        validated_commit = self.bind(
            {
                "schema_version": 1,
                "inputs": [{"path": "spec.md", "blob_oid": spec_oid}],
            }
        )
        unrelated = Path(self.temporary.name) / "unrelated"
        unrelated.mkdir()
        run_git(unrelated, "init", "--quiet")
        (unrelated / "unrelated.md").write_text("other\n", encoding="utf-8")
        commit(unrelated, "unrelated")

        with mock.patch.dict(
            os.environ,
            {
                "GIT_DIR": str(unrelated / ".git"),
                "GIT_WORK_TREE": str(unrelated),
                "GIT_OBJECT_DIRECTORY": str(unrelated / ".git" / "objects"),
            },
            clear=False,
        ):
            result = self.validate(validated_commit)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["commit"], validated_commit)

    def test_does_not_lazy_fetch_missing_definition_blobs(self) -> None:
        self.write("spec.md", "approved definition\n")
        commit(self.repository, "definition")
        validated_commit = self.bind(
            {
                "schema_version": 1,
                "inputs": [{"path": "spec.md", "blob_oid": self.oid("spec.md")}],
            }
        )
        index_oid = self.oid(".dag/definition-index.json")
        run_git(self.repository, "config", "uploadpack.allowFilter", "true")
        partial = Path(self.temporary.name) / "partial"
        subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--filter=blob:none",
                "--no-checkout",
                self.repository.as_uri(),
                str(partial),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        no_lazy_fetch = {**os.environ, "GIT_NO_LAZY_FETCH": "1"}
        missing_before = subprocess.run(
            ["git", "cat-file", "-e", index_oid],
            cwd=partial,
            env=no_lazy_fetch,
            capture_output=True,
            check=False,
        )
        if missing_before.returncode == 0:
            self.skipTest("Git partial clone did not omit the index blob")

        result = self.validate(validated_commit, partial)
        missing_after = subprocess.run(
            ["git", "cat-file", "-e", index_oid],
            cwd=partial,
            env=no_lazy_fetch,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertNotEqual(missing_after.returncode, 0)

    def test_rejects_an_input_oid_that_does_not_match_the_commit_path(self) -> None:
        self.write("spec.md", "approved\n")
        self.write("other.md", "other\n")
        commit(self.repository, "definition")
        index_commit = self.bind(
            {
                "schema_version": 1,
                "inputs": [{"path": "spec.md", "blob_oid": self.oid("other.md")}],
            }
        )

        result = self.validate(index_commit)

        self.assertEqual(result.returncode, 1)
        self.assertIn("spec.md: blob_oid does not match the commit", result.stderr)

    def test_rejects_an_unsafe_repository_relative_path(self) -> None:
        self.write("spec.md", "approved\n")
        commit(self.repository, "definition")
        index_commit = self.bind(
            {
                "schema_version": 1,
                "inputs": [{"path": "/spec.md", "blob_oid": self.oid("spec.md")}],
            }
        )

        result = self.validate(index_commit)

        self.assertEqual(result.returncode, 1)
        self.assertIn("/spec.md: path is not normalized and safe", result.stderr)

    def test_rejects_a_json_surrogate_path_without_a_traceback(self) -> None:
        self.write("spec.md", "approved\n")
        commit(self.repository, "definition")
        self.write(
            ".dag/definition-index.json",
            '{"schema_version":1,"inputs":['
            f'{{"path":"\\ud800","blob_oid":"{self.oid("spec.md")}"}}]}}\n',
        )
        index_commit = commit(self.repository, "bind definition")

        result = self.validate(index_commit)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stderr.startswith("error: "), result.stderr)
        self.assertIn("path is not normalized and safe", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_ignores_unselected_non_utf8_git_paths(self) -> None:
        spec_oid = run_git_with_input(
            self.repository,
            ["hash-object", "-w", "--stdin"],
            b"approved definition\n",
        )
        index_payload = (
            json.dumps(
                {
                    "schema_version": 1,
                    "inputs": [{"path": "spec.md", "blob_oid": spec_oid}],
                }
            )
            + "\n"
        ).encode()
        index_oid = run_git_with_input(
            self.repository, ["hash-object", "-w", "--stdin"], index_payload
        )
        unrelated_oid = run_git_with_input(
            self.repository, ["hash-object", "-w", "--stdin"], b"unrelated\n"
        )
        dag_tree = run_git_with_input(
            self.repository,
            ["mktree", "-z"],
            f"100644 blob {index_oid}\tdefinition-index.json\0".encode(),
        )
        root_tree = run_git_with_input(
            self.repository,
            ["mktree", "-z"],
            (
                f"040000 tree {dag_tree}\t.dag\0".encode()
                + f"100644 blob {unrelated_oid}\t".encode()
                + b"bad\xff\0"
                + f"100644 blob {spec_oid}\tspec.md\0".encode()
            ),
        )
        commit_oid = run_git(
            self.repository,
            "-c",
            "user.name=DAG Skill Tests",
            "-c",
            "user.email=dag-skill-tests@example.invalid",
            "commit-tree",
            root_tree,
            "-m",
            "raw path fixture",
        )

        result = self.validate(commit_oid)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["inputs"][0]["path"], "spec.md")

    def test_rejects_unknown_index_fields(self) -> None:
        self.write("spec.md", "approved\n")
        commit(self.repository, "definition")
        index_commit = self.bind(
            {
                "schema_version": 1,
                "inputs": [{"path": "spec.md", "blob_oid": self.oid("spec.md")}],
                "selected_plan": "latest",
            }
        )

        result = self.validate(index_commit)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "index fields must be exactly inputs, schema_version", result.stderr
        )

    def test_rejects_duplicate_json_fields(self) -> None:
        self.write("spec.md", "approved\n")
        commit(self.repository, "definition")
        self.write(
            ".dag/definition-index.json",
            '{"schema_version":1,"inputs":[],"inputs":[]}\n',
        )
        index_commit = commit(self.repository, "bind definition")

        result = self.validate(index_commit)

        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate JSON field: inputs", result.stderr)

    def test_rejects_an_empty_definition(self) -> None:
        self.write("spec.md", "approved\n")
        commit(self.repository, "definition")
        index_commit = self.bind({"schema_version": 1, "inputs": []})

        result = self.validate(index_commit)

        self.assertEqual(result.returncode, 1)
        self.assertIn("inputs must contain at least one definition blob", result.stderr)

    def test_rejects_a_utf16_definition_index(self) -> None:
        self.write("spec.md", "approved\n")
        commit(self.repository, "definition")
        payload = json.dumps(
            {
                "schema_version": 1,
                "inputs": [{"path": "spec.md", "blob_oid": self.oid("spec.md")}],
            }
        ).encode("utf-16")
        self.write(".dag/definition-index.json", payload)
        index_commit = commit(self.repository, "bind definition")

        result = self.validate(index_commit)

        self.assertEqual(result.returncode, 1)
        self.assertIn("index must be UTF-8 JSON", result.stderr)

    def test_rejects_inputs_not_sorted_by_utf8_path_bytes(self) -> None:
        self.write("a.md", "a\n")
        self.write("b.md", "b\n")
        commit(self.repository, "definition")
        index_commit = self.bind(
            {
                "schema_version": 1,
                "inputs": [
                    {"path": "b.md", "blob_oid": self.oid("b.md")},
                    {"path": "a.md", "blob_oid": self.oid("a.md")},
                ],
            }
        )

        result = self.validate(index_commit)

        self.assertEqual(result.returncode, 1)
        self.assertIn("inputs must be sorted by UTF-8 path bytes", result.stderr)

    def test_rejects_a_symlink_as_definition_content(self) -> None:
        self.write("spec.md", "approved\n")
        linked = self.repository / "tickets.md"
        try:
            linked.symlink_to("spec.md")
        except OSError as error:
            self.skipTest(f"symlinks unavailable: {error}")
        commit(self.repository, "definition")
        index_commit = self.bind(
            {
                "schema_version": 1,
                "inputs": [{"path": "tickets.md", "blob_oid": self.oid("tickets.md")}],
            }
        )

        result = self.validate(index_commit)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "tickets.md: input must be an ordinary tracked blob", result.stderr
        )

    def test_rejects_a_git_lfs_pointer_as_definition_content(self) -> None:
        self.write(
            "tracker-snapshot.md",
            "version https://git-lfs.github.com/spec/v1\n"
            f"ext-0-encryption sha256:{'2' * 64}\n"
            f"oid sha256:{'0' * 64}\n"
            "size 123\n",
        )
        commit(self.repository, "definition")
        index_commit = self.bind(
            {
                "schema_version": 1,
                "inputs": [
                    {
                        "path": "tracker-snapshot.md",
                        "blob_oid": self.oid("tracker-snapshot.md"),
                    }
                ],
            }
        )

        result = self.validate(index_commit)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "tracker-snapshot.md: Git LFS pointer is not full definition content",
            result.stderr,
        )

    def test_rejects_legacy_git_lfs_pointer_versions(self) -> None:
        for index, version in enumerate(
            (
                "http://git-media.io/v/2",
                "https://hawser.github.com/spec/v1",
            )
        ):
            path = f"legacy-{index}.md"
            self.write(
                path,
                f"version {version}\noid sha256:{'1' * 64}\nsize 456\n",
            )
        commit(self.repository, "definition")
        index_commit = self.bind(
            {
                "schema_version": 1,
                "inputs": [
                    {"path": "legacy-0.md", "blob_oid": self.oid("legacy-0.md")},
                    {"path": "legacy-1.md", "blob_oid": self.oid("legacy-1.md")},
                ],
            }
        )

        result = self.validate(index_commit)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "legacy-0.md: Git LFS pointer is not full definition content",
            result.stderr,
        )

    def test_rejects_lfs_pointer_with_extension_before_version(self) -> None:
        self.write(
            "pre-version-extension.md",
            f"ext-0-foo sha256:{'3' * 64}\n"
            "version https://git-lfs.github.com/spec/v1\n"
            f"oid sha256:{'4' * 64}\n"
            f"ext-1-bar sha256:{'5' * 64}\n"
            "size 4\n",
        )
        commit(self.repository, "definition")
        index_commit = self.bind(
            {
                "schema_version": 1,
                "inputs": [
                    {
                        "path": "pre-version-extension.md",
                        "blob_oid": self.oid("pre-version-extension.md"),
                    }
                ],
            }
        )

        result = self.validate(index_commit)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "pre-version-extension.md: Git LFS pointer is not full definition content",
            result.stderr,
        )

    def test_accepts_plain_text_that_mentions_the_lfs_version_first(self) -> None:
        self.write(
            "lfs-notes.md",
            "version https://git-lfs.github.com/spec/v1\n"
            "This document explains why Definition inputs cannot use LFS.\n",
        )
        commit(self.repository, "definition")
        index_commit = self.bind(
            {
                "schema_version": 1,
                "inputs": [
                    {"path": "lfs-notes.md", "blob_oid": self.oid("lfs-notes.md")}
                ],
            }
        )

        result = self.validate(index_commit)

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_a_symlink_definition_index(self) -> None:
        self.write("spec.md", "approved\n")
        self.write("index.json", '{"schema_version":1,"inputs":[]}\n')
        index = self.repository / ".dag" / "definition-index.json"
        index.parent.mkdir()
        try:
            index.symlink_to("../../index.json")
        except OSError as error:
            self.skipTest(f"symlinks unavailable: {error}")
        index_commit = commit(self.repository, "bind definition")

        result = self.validate(index_commit)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            ".dag/definition-index.json: index must be a regular non-executable blob",
            result.stderr,
        )


if __name__ == "__main__":
    unittest.main()
