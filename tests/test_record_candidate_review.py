from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTEXT_SCRIPT = ROOT / "skill" / "dag" / "scripts" / "record_review_context.py"
HANDLE_SCRIPT = ROOT / "skill" / "dag" / "scripts" / "record_tool_artifact.py"
RECORD_SCRIPT = ROOT / "skill" / "dag" / "scripts" / "record_candidate_review.py"
VERIFY_SCRIPT = ROOT / "skill" / "dag" / "scripts" / "verify_candidate_review.py"
PROMOTION_SCRIPT = ROOT / "skill" / "dag" / "scripts" / "verify_promotion_package.py"


class CandidateReviewRecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.context = self.root / "context.json"
        self.capsule = self.root / "capsule.json"
        self.review = self.root / "review.txt"
        self.handle = self.root / "handles" / "review.json"
        self.output = self.root / "records" / "review-record.json"
        self.handle.parent.mkdir()
        self.output.parent.mkdir()
        self.evidence = self.root / "gate.txt"
        self.evidence.write_text("gate\n", encoding="utf-8")
        self.exploration = self.root / "note.json"
        self.exploration.write_text("note\n", encoding="utf-8")
        self.review.write_text("review findings\n", encoding="utf-8")
        self.write_context()
        self.publish_capsule()
        self.publish_handle()

    def digest(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def write_context(self) -> None:
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
                            "sha256": self.digest(self.evidence),
                        }
                    ],
                    "exploration_refs": [
                        {
                            "id": "note-1",
                            "path": str(self.exploration),
                            "sha256": self.digest(self.exploration),
                        }
                    ],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def publish_capsule(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(CONTEXT_SCRIPT),
                "--context",
                str(self.context),
                "--output",
                str(self.capsule),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def publish_handle(self, kind: str = "review-report") -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(HANDLE_SCRIPT),
                "--artifact",
                str(self.review),
                "--artifact-root",
                str(self.root),
                "--output",
                str(self.handle),
                "--artifact-kind",
                kind,
                "--command",
                "code-review",
                "--cwd",
                str(self.root),
                "--exit-code",
                "0",
                "--duration-ms",
                "20",
                "--observed-at",
                "2026-10-27T13:00:00Z",
                "--environment-identity",
                "host-1",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def invoke(self, output: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(RECORD_SCRIPT),
                "--context-capsule",
                str(self.capsule),
                "--review-handle",
                str(self.handle),
                "--artifact-root",
                str(self.root),
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

    def verify(
        self, *, candidate_commit: str = "c" * 40
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(VERIFY_SCRIPT),
                "--record",
                str(self.output),
                "--context-capsule",
                str(self.capsule),
                "--review-handle",
                str(self.handle),
                "--artifact-root",
                str(self.root),
                "--expected-base-commit",
                "a" * 40,
                "--expected-base-tree",
                "b" * 40,
                "--expected-candidate-commit",
                candidate_commit,
                "--expected-candidate-tree",
                "d" * 40,
                "--expected-candidate-range",
                "base..candidate",
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_binds_fresh_review_artifact_and_is_idempotent(self) -> None:
        first = self.invoke()

        self.assertEqual(first.returncode, 0, first.stderr)
        record = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(record["kind"], "Candidate Review Record")
        self.assertTrue(record["fresh_review_required"])
        self.assertEqual(record["review_artifact"]["artifact_kind"], "review-report")
        self.assertEqual(len(record["review_record_key"]), 64)

        second = self.invoke()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(second.stdout)["status"], "already-published")

    def test_rejects_changed_review_artifact(self) -> None:
        self.review.write_text("changed findings\n", encoding="utf-8")

        self.assert_rejected(self.invoke(), "byte count does not match")

    def test_rejects_non_review_artifact_kind(self) -> None:
        self.handle.unlink()
        self.publish_handle(kind="stdout")

        self.assert_rejected(self.invoke(), "artifact_kind must be review-report")

    def test_rejects_capsule_without_fresh_review(self) -> None:
        capsule = json.loads(self.capsule.read_text(encoding="utf-8"))
        capsule["fresh_review_required"] = False
        self.capsule.write_text(json.dumps(capsule), encoding="utf-8")

        self.assert_rejected(self.invoke(), "fresh_review_required")

    def test_verifies_record_against_current_candidate_and_base(self) -> None:
        self.assertEqual(self.invoke().returncode, 0)

        result = self.verify()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "verified")
        self.assertTrue(json.loads(result.stdout)["fresh_review_required"])

        mismatch = self.verify(candidate_commit="9" * 40)
        self.assert_rejected(mismatch, "candidate commit does not match")

    def write_receipt_with_claim(self) -> Path:
        receipt = self.root / "receipt.json"
        receipt.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Run Receipt",
                    "run_id": "run-1",
                    "coordinator_generation": 4,
                    "claims": [
                        {
                            "schema_version": 1,
                            "kind": "Execution Claim",
                            "ticket_id": "ticket-1",
                            "owner_id": "agent-1",
                            "claim_generation": 2,
                            "workspace": str(self.root / "workspace"),
                            "branch": "refs/heads/dag/ticket-1",
                            "phase": "implement",
                            "ticket_base": {"commit": "a" * 40, "tree": "b" * 40},
                            "changed_paths": ["src/a.py"],
                            "shared_interfaces": [],
                            "resources": [
                                {
                                    "resource": "agent_slots",
                                    "quantity": 1,
                                    "mode": "exclusive",
                                }
                            ],
                            "lane": "build-review",
                            "request_sha256": "1" * 64,
                            "decision_sha256": "2" * 64,
                        }
                    ],
                    "execution_records": [],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return receipt

    def test_verifies_promotion_package_against_live_claim_and_tip(self) -> None:
        self.assertEqual(self.invoke().returncode, 0)
        receipt = self.write_receipt_with_claim()
        output = self.root / "promotion" / "package.json"
        output.parent.mkdir()
        command = [
            sys.executable,
            str(PROMOTION_SCRIPT),
            "--receipt",
            str(receipt),
            "--ticket-id",
            "ticket-1",
            "--context-capsule",
            str(self.capsule),
            "--review-record",
            str(self.output),
            "--review-handle",
            str(self.handle),
            "--artifact-root",
            str(self.root),
            "--expected-tip-commit",
            "a" * 40,
            "--expected-tip-tree",
            "b" * 40,
            "--output",
            str(output),
        ]
        result = subprocess.run(
            command, cwd=self.root, capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            json.loads(output.read_text(encoding="utf-8"))["promotion_allowed"]
        )

        mismatch_command = command.copy()
        mismatch_command[mismatch_command.index("--expected-tip-commit") + 1] = "9" * 40
        mismatch_command[mismatch_command.index("--output") + 1] = str(
            self.root / "promotion" / "mismatch.json"
        )
        mismatch = subprocess.run(
            mismatch_command,
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assert_rejected(mismatch, "Accepted Integration Tip commit")


if __name__ == "__main__":
    unittest.main()
