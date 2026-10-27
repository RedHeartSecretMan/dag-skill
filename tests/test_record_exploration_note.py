from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill" / "dag" / "scripts" / "record_exploration_note.py"


class ExplorationNoteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.note = self.root / "note.json"
        self.published = self.root / "cache" / "note.json"
        self.context = self.root / "context.json"
        self.consumption = self.root / "consumption.json"
        self.published.parent.mkdir()
        self.write_note()
        self.write_context()

    def write_note(self) -> None:
        self.note.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Exploration Note",
                    "note_id": "note-1",
                    "question": "where is the shared interface?",
                    "scope": ["src/a.py"],
                    "source_identities": [
                        {"path": "docs/design.md", "identity": "sha256:" + "a" * 64}
                    ],
                    "target_identity": "tree:" + "b" * 40,
                    "environment_identity": "host-1",
                    "author": "agent-1",
                    "created_at": "2026-10-27T10:00:00Z",
                    "invalidation_conditions": ["design source changes"],
                    "conclusions": [
                        {
                            "id": "finding-1",
                            "statement": "The interface is defined in the design document.",
                            "evidence": [
                                {
                                    "path": "docs/design.md",
                                    "identity": "sha256:" + "a" * 64,
                                }
                            ],
                        }
                    ],
                    "limitations": ["The note does not decide acceptance."],
                    "unresolved": [],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def write_context(self) -> None:
        self.context.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Exploration Context",
                    "question": "where is the shared interface?",
                    "scope": ["src/a.py", "src/b.py"],
                    "source_identities": [
                        {"path": "docs/design.md", "identity": "sha256:" + "a" * 64}
                    ],
                    "target_identity": "tree:" + "b" * 40,
                    "environment_identity": "host-1",
                    "observed_at": "2026-10-27T11:00:00Z",
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def invoke(
        self,
        *,
        note: Path | None = None,
        context: Path | None = None,
        output: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(SCRIPT),
            "--note",
            str(note or self.note),
            "--output",
            str(output or self.published),
        ]
        if context is not None:
            command.extend(["--context", str(context)])
        return subprocess.run(
            command,
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

    def test_publishes_identity_bound_note_idempotently(self) -> None:
        first = self.invoke()

        self.assertEqual(first.returncode, 0, first.stderr)
        result = json.loads(first.stdout)
        self.assertEqual(result["status"], "published")
        note = json.loads(self.published.read_text(encoding="utf-8"))
        self.assertEqual(note["kind"], "Exploration Note")
        self.assertEqual(len(note["cache_key"]), 64)

        second = self.invoke()

        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(second.stdout)["status"], "already-published")

    def test_consumes_note_only_when_context_identities_match(self) -> None:
        self.assertEqual(self.invoke().returncode, 0)

        result = self.invoke(
            note=self.published, context=self.context, output=self.consumption
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "published")
        consumption = json.loads(self.consumption.read_text(encoding="utf-8"))
        self.assertEqual(consumption["kind"], "Exploration Consumption Record")
        self.assertEqual(
            consumption["verified_source_identities"][0]["path"], "docs/design.md"
        )

    def test_rejects_changed_source_identity(self) -> None:
        self.assertEqual(self.invoke().returncode, 0)
        context = json.loads(self.context.read_text(encoding="utf-8"))
        context["source_identities"][0]["identity"] = "sha256:" + "c" * 64
        self.context.write_text(json.dumps(context), encoding="utf-8")

        self.assert_rejected(
            self.invoke(note=self.published, context=self.context),
            "source identity does not match",
        )

    def test_rejects_changed_target_and_scope(self) -> None:
        self.assertEqual(self.invoke().returncode, 0)
        context = json.loads(self.context.read_text(encoding="utf-8"))
        context["target_identity"] = "tree:" + "d" * 40
        context["scope"] = ["src/b.py"]
        self.context.write_text(json.dumps(context), encoding="utf-8")

        result = self.invoke(note=self.published, context=self.context)
        self.assert_rejected(result, "context.scope does not cover note.scope")

    def test_rejects_note_with_unsafe_source_path(self) -> None:
        payload = json.loads(self.note.read_text(encoding="utf-8"))
        payload["source_identities"][0]["path"] = "../design.md"
        self.note.write_text(json.dumps(payload), encoding="utf-8")

        self.assert_rejected(self.invoke(), "unsafe path component")

    def test_rejects_output_collision(self) -> None:
        self.published.write_text("different\n", encoding="utf-8")

        self.assert_rejected(
            self.invoke(), "output already exists with different content"
        )


if __name__ == "__main__":
    unittest.main()
