from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill" / "dag" / "scripts" / "record_ticket_disposition.py"


class TicketDispositionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.receipt = self.root / "receipt.json"
        self.decision = self.root / "decision.json"
        self.promotion = self.root / "promotion.json"
        self.evidence = self.root / "decision-evidence.txt"
        self.evidence.write_text("Coordinator decision evidence\n", encoding="utf-8")
        self.write_receipt()
        self.write_decision("Accepted")
        self.write_promotion()

    def digest(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def claim(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "kind": "Execution Claim",
            "ticket_id": "ticket-1",
            "owner_id": "agent-1",
            "claim_generation": 2,
            "workspace": str(self.root / "workspace"),
            "branch": "refs/heads/dag/ticket-1",
            "phase": "promotion",
            "ticket_base": {"commit": "a" * 40, "tree": "b" * 40},
            "changed_paths": ["src/a.py"],
            "shared_interfaces": [],
            "resources": [
                {"resource": "agent_slots", "quantity": 1, "mode": "exclusive"}
            ],
            "lane": "promotion",
            "request_sha256": "1" * 64,
            "decision_sha256": "2" * 64,
        }

    def write_receipt(self) -> None:
        self.receipt.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Run Receipt",
                    "run_id": "run-1",
                    "coordinator_generation": 4,
                    "claims": [self.claim()],
                    "execution_records": [],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def write_decision(self, disposition: str) -> None:
        self.decision.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Ticket Disposition Decision",
                    "run_id": "run-1",
                    "coordinator_generation": 4,
                    "ticket_id": "ticket-1",
                    "claim_generation": 2,
                    "disposition": disposition,
                    "rule_identity": "rule:acceptance-v1",
                    "decided_by": "coordinator-1",
                    "decided_at": "2026-10-27T14:00:00Z",
                    "rationale": "Decision recorded by the Coordinator.",
                    "evidence_refs": [
                        {
                            "id": "decision-evidence",
                            "path": str(self.evidence),
                            "sha256": self.digest(self.evidence),
                        }
                    ],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def write_promotion(self) -> None:
        self.promotion.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Promotion Evidence Package",
                    "run_id": "run-1",
                    "receipt_generation": 4,
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
                    "review_context_key": "1" * 64,
                    "review_record_key": "2" * 64,
                    "review_artifact_sha256": "3" * 64,
                    "fresh_review_required": True,
                    "promotion_allowed": True,
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def invoke(
        self,
        *,
        generation: int = 4,
        promotion: bool = True,
        receipt_digest: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(SCRIPT),
            "--receipt",
            str(self.receipt),
            "--decision",
            str(self.decision),
            "--expected-generation",
            str(generation),
            "--expected-receipt-sha256",
            receipt_digest or self.digest(self.receipt),
        ]
        if promotion:
            command.extend(
                [
                    "--promotion-evidence",
                    str(self.promotion),
                    "--promotion-evidence-sha256",
                    self.digest(self.promotion),
                ]
            )
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

    def test_accepts_and_closes_claim_idempotently(self) -> None:
        result = self.invoke()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["disposition"], "Accepted")
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(receipt["coordinator_generation"], 5)
        self.assertEqual(receipt["claims"], [])
        self.assertEqual(receipt["ticket_dispositions"][0]["disposition"], "Accepted")

        second = self.invoke(generation=5, receipt_digest=self.digest(self.receipt))
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(second.stdout)["status"], "already-recorded")

    def test_records_superseded_without_promotion_package(self) -> None:
        self.write_decision("Superseded")
        result = self.invoke(promotion=False)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["disposition"], "Superseded")

    def test_rejects_accepted_without_promotion_or_stale_receipt(self) -> None:
        self.assert_rejected(
            self.invoke(promotion=False), "requires promotion evidence"
        )
        self.assert_rejected(self.invoke(generation=5), "coordinator_generation")

    def test_rejects_changed_decision_evidence(self) -> None:
        self.evidence.write_text("changed\n", encoding="utf-8")

        self.assert_rejected(self.invoke(), "SHA-256 does not match")


if __name__ == "__main__":
    unittest.main()
