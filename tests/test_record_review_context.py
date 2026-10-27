from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill" / "dag" / "scripts" / "record_review_context.py"


class ReviewContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.evidence = self.root / "evidence.txt"
        self.evidence.write_text("gate evidence\n", encoding="utf-8")
        self.exploration = self.root / "exploration.json"
        self.exploration.write_text("exploration note\n", encoding="utf-8")
        self.context = self.root / "context.json"
        self.output = self.root / "capsule" / "review-context.json"
        self.output.parent.mkdir()
        self.write_context()

    def write_context(self) -> None:
        import hashlib

        evidence_digest = hashlib.sha256(self.evidence.read_bytes()).hexdigest()
        exploration_digest = hashlib.sha256(self.exploration.read_bytes()).hexdigest()
        self.context.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Review Context",
                    "run_id": "run-1",
                    "ticket_id": "ticket-1",
                    "owner_id": "agent-1",
                    "claim_generation": 2,
                    "ticket_base": {"commit": "a" * 40, "tree": "b" * 40},
                    "candidate": {
                        "commit": "c" * 40,
                        "tree": "d" * 40,
                        "range": "base..candidate",
                        "commits": ["c" * 40],
                    },
                    "definition_identity": "sha256:" + "e" * 64,
                    "changed_paths": ["src/a.py"],
                    "acceptance_obligations": [
                        {
                            "id": "obligation-1",
                            "source": "tickets/ticket-1.md",
                            "identity": "sha256:" + "f" * 64,
                        }
                    ],
                    "required_gates": [
                        {"name": "unit", "identity": "sha256:" + "1" * 64}
                    ],
                    "evidence_refs": [
                        {
                            "id": "gate-1",
                            "path": str(self.evidence),
                            "sha256": evidence_digest,
                        }
                    ],
                    "exploration_refs": [
                        {
                            "id": "note-1",
                            "path": str(self.exploration),
                            "sha256": exploration_digest,
                        }
                    ],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def invoke(self, output: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--context",
                str(self.context),
                "--output",
                str(output or self.output),
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

    def test_publishes_fresh_review_capsule_idempotently(self) -> None:
        first = self.invoke()

        self.assertEqual(first.returncode, 0, first.stderr)
        capsule = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(capsule["kind"], "Review Context Capsule")
        self.assertTrue(capsule["fresh_review_required"])
        self.assertEqual(len(capsule["review_context_key"]), 64)

        second = self.invoke()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(second.stdout)["status"], "already-published")

    def test_candidate_change_produces_new_review_key(self) -> None:
        self.assertEqual(self.invoke().returncode, 0)
        first_key = json.loads(self.output.read_text(encoding="utf-8"))[
            "review_context_key"
        ]
        changed = json.loads(self.context.read_text(encoding="utf-8"))
        changed["candidate"]["commit"] = "9" * 40
        changed["candidate"]["commits"] = ["9" * 40]
        self.context.write_text(json.dumps(changed), encoding="utf-8")

        second_output = self.root / "capsule" / "review-context-2.json"
        result = self.invoke(second_output)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotEqual(
            json.loads(second_output.read_text(encoding="utf-8"))["review_context_key"],
            first_key,
        )

    def test_obligation_change_produces_new_review_key(self) -> None:
        self.assertEqual(self.invoke().returncode, 0)
        first_key = json.loads(self.output.read_text(encoding="utf-8"))[
            "review_context_key"
        ]
        changed = json.loads(self.context.read_text(encoding="utf-8"))
        changed["acceptance_obligations"][0]["identity"] = "sha256:" + "0" * 64
        self.context.write_text(json.dumps(changed), encoding="utf-8")

        second_output = self.root / "capsule" / "review-context-2.json"
        self.assertEqual(self.invoke(second_output).returncode, 0)
        self.assertNotEqual(
            json.loads(second_output.read_text(encoding="utf-8"))["review_context_key"],
            first_key,
        )

    def test_rejects_changed_evidence_and_review_result_fields(self) -> None:
        changed = json.loads(self.context.read_text(encoding="utf-8"))
        changed["evidence_refs"][0]["sha256"] = "0" * 64
        self.context.write_text(json.dumps(changed), encoding="utf-8")
        self.assert_rejected(self.invoke(), "SHA-256 does not match")

        changed.pop("evidence_refs")
        changed["evidence_refs"] = []
        changed["review_result"] = {"approved": True}
        self.context.write_text(json.dumps(changed), encoding="utf-8")
        self.assert_rejected(self.invoke(), "unknown review_result")

    def test_rejects_candidate_equal_to_base(self) -> None:
        changed = json.loads(self.context.read_text(encoding="utf-8"))
        changed["candidate"]["commit"] = changed["ticket_base"]["commit"]
        changed["candidate"]["commits"] = [changed["ticket_base"]["commit"]]
        self.context.write_text(json.dumps(changed), encoding="utf-8")

        self.assert_rejected(self.invoke(), "candidate must differ from ticket_base")


if __name__ == "__main__":
    unittest.main()
