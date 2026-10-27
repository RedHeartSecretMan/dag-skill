from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill" / "dag" / "scripts" / "verify_terminal_outcome.py"


class TerminalOutcomeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.receipt = self.root / "receipt.json"
        self.audit = self.root / "audit.json"
        self.authority = self.root / "authority.json"
        self.authority.write_text("authoritative snapshot\n", encoding="utf-8")
        self.output = self.root / "terminal" / "evidence.json"
        self.output.parent.mkdir()
        self.write_receipt()
        self.write_audit("Complete")

    @staticmethod
    def digest(path: Path) -> str:
        import hashlib

        return hashlib.sha256(path.read_bytes()).hexdigest()

    def write_receipt(self, claims: list[dict[str, object]] | None = None) -> None:
        self.receipt.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Run Receipt",
                    "run_id": "run-1",
                    "coordinator_generation": 8,
                    "claims": claims or [],
                    "execution_records": [],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def write_audit(self, outcome: str) -> None:
        if outcome == "Complete":
            obligations = [
                {
                    "id": "obligation-1",
                    "owner": "ticket-1",
                    "status": "Accepted",
                    "evidence_applicable": True,
                }
            ]
            gates = [
                {
                    "id": "whole-dag",
                    "result": "pass",
                    "evidence_identity": "sha256:" + "a" * 64,
                }
            ]
        else:
            obligations = [
                {
                    "id": "obligation-1",
                    "owner": "ticket-1",
                    "status": "Blocked",
                    "evidence_applicable": True,
                }
            ]
            gates = []
        self.audit.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Terminal Outcome Audit",
                    "run_id": "run-1",
                    "outcome": outcome,
                    "definition_identity": "sha256:" + "b" * 64,
                    "accepted_tip": {"commit": "a" * 40, "tree": "b" * 40},
                    "authority_refs": [
                        {
                            "id": "definition-snapshot",
                            "path": str(self.authority),
                            "sha256": self.digest(self.authority),
                        }
                    ],
                    "obligations": obligations,
                    "whole_dag_gates": gates,
                    "pending_tracker_updates": [],
                    "unresolved_decisions": [],
                    "needs_decisions": [],
                    "runnable_tickets": [],
                    "running_agents": [],
                    "recovery_paths": [],
                    "satisfiable_external_conditions": [],
                    "writer_liveness_resolved": True,
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def invoke(self, *, output: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--receipt",
                str(self.receipt),
                "--audit",
                str(self.audit),
                "--expected-tip-commit",
                "a" * 40,
                "--expected-tip-tree",
                "b" * 40,
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

    def test_verifies_complete_and_is_idempotent(self) -> None:
        result = self.invoke()

        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(evidence["outcome"], "Complete")
        self.assertTrue(evidence["verified"])
        self.assertEqual(
            json.loads(self.invoke().stdout)["status"], "already-published"
        )

    def test_verifies_stalled_with_no_progress_paths(self) -> None:
        self.write_audit("Stalled")
        output = self.root / "terminal" / "stalled.json"
        result = self.invoke(output=output)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(output.read_text(encoding="utf-8"))["outcome"], "Stalled"
        )

    def test_rejects_complete_with_open_obligation_or_live_claim(self) -> None:
        audit = json.loads(self.audit.read_text(encoding="utf-8"))
        audit["obligations"][0]["status"] = "Open"
        self.audit.write_text(json.dumps(audit), encoding="utf-8")
        self.assert_rejected(self.invoke(), "obligations to be closed")

        audit["obligations"][0]["status"] = "Accepted"
        self.audit.write_text(json.dumps(audit), encoding="utf-8")
        self.write_receipt(
            claims=[
                {
                    "ticket_id": "ticket-1",
                    "claim_generation": 1,
                }
            ]
        )
        self.assert_rejected(self.invoke(), "live claims remain")

    def test_rejects_stalled_with_runnable_work(self) -> None:
        self.write_audit("Stalled")
        audit = json.loads(self.audit.read_text(encoding="utf-8"))
        audit["runnable_tickets"] = ["ticket-2"]
        self.audit.write_text(json.dumps(audit), encoding="utf-8")

        self.assert_rejected(self.invoke(), "Stalled cannot have runnable_tickets")


if __name__ == "__main__":
    unittest.main()
