from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill" / "dag" / "scripts" / "record_tool_artifact.py"


class ArtifactHandleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.artifact = self.root / "stdout.txt"
        self.artifact.write_text("tool output\n", encoding="utf-8")
        self.output = self.root / "handles" / "stdout.json"
        self.output.parent.mkdir()

    def invoke(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--artifact",
                str(self.artifact),
                "--artifact-root",
                str(self.root),
                "--output",
                str(self.output),
                "--artifact-kind",
                "stdout",
                "--command",
                "pytest -q",
                "--cwd",
                str(self.root),
                "--exit-code",
                "0",
                "--duration-ms",
                "12",
                "--observed-at",
                "2026-10-27T12:00:00Z",
                "--environment-identity",
                "host-1",
                *extra,
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

    def test_publishes_and_verifies_handle(self) -> None:
        result = self.invoke()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "published")
        handle = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(handle["kind"], "Artifact Handle")
        self.assertEqual(handle["byte_count"], len(b"tool output\n"))

        verified = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--verify",
                str(self.output),
                "--artifact-root",
                str(self.root),
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertEqual(json.loads(verified.stdout)["status"], "verified")

    def test_publication_is_idempotent_and_collision_safe(self) -> None:
        self.assertEqual(self.invoke().returncode, 0)
        second = self.invoke()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(second.stdout)["status"], "already-published")

        self.output.write_text("different\n", encoding="utf-8")
        self.assert_rejected(
            self.invoke(), "output already exists with different content"
        )

    def test_verification_rejects_changed_artifact(self) -> None:
        self.assertEqual(self.invoke().returncode, 0)
        self.artifact.write_text("changed\n", encoding="utf-8")

        verified = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--verify",
                str(self.output),
                "--artifact-root",
                str(self.root),
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assert_rejected(verified, "byte count does not match")

    def test_rejects_symlink_artifact_and_invalid_combined_modes(self) -> None:
        outside = self.root / "outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        self.artifact.unlink()
        self.artifact.symlink_to(outside)
        self.assert_rejected(self.invoke(), "regular non-symlink")

        self.artifact.unlink()
        self.artifact.write_text("tool output\n", encoding="utf-8")
        combined = self.invoke("--verify", str(self.output))
        self.assert_rejected(combined, "--verify cannot be combined")


if __name__ == "__main__":
    unittest.main()
