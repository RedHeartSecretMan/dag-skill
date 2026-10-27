from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLANNER = ROOT / "skill" / "dag" / "scripts" / "plan_execution_admission.py"
CLAIM_SCRIPT = ROOT / "skill" / "dag" / "scripts" / "record_execution_claim.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ExecutionClaimTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.request = self.root / "request.json"
        self.decision = self.root / "decision.json"
        self.claim = self.root / "claim.json"
        self.receipt = self.root / "receipt.json"
        self.write_request()
        planner = subprocess.run(
            [
                sys.executable,
                str(PLANNER),
                "--request",
                str(self.request),
                "--output",
                str(self.decision),
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(planner.returncode, 0, planner.stderr)
        self.write_claim()
        self.receipt.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Run Receipt",
                    "run_id": "run-1",
                    "coordinator_generation": 3,
                    "claims": [],
                    "execution_records": [],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def write_request(self) -> None:
        self.request.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Execution Admission Request",
                    "run_id": "run-1",
                    "coordinator_generation": 3,
                    "capacity": {"agent_slots": 2, "runtime_skill_slots": 1},
                    "accepted_direct_inputs": [],
                    "accepted_prerequisites": [],
                    "live_claims": [],
                    "candidates": [
                        {
                            "ticket_id": "ticket-1",
                            "owner_id": "agent-1",
                            "phase": "implement",
                            "changed_paths": ["src/a.py"],
                            "shared_interfaces": [],
                            "resources": [
                                {
                                    "resource": "agent_slots",
                                    "quantity": 1,
                                    "mode": "exclusive",
                                }
                            ],
                            "priority": 1,
                            "age": 0,
                            "required_inputs": [],
                            "hard_dependencies": [],
                        }
                    ],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def write_claim(self, *, owner_id: str = "agent-1") -> None:
        self.claim.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Execution Claim",
                    "ticket_id": "ticket-1",
                    "owner_id": owner_id,
                    "claim_generation": 1,
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
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def invoke(
        self,
        *,
        generation: int = 3,
        receipt_digest: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(CLAIM_SCRIPT),
                "--receipt",
                str(self.receipt),
                "--request",
                str(self.request),
                "--decision",
                str(self.decision),
                "--claim",
                str(self.claim),
                "--expected-generation",
                str(generation),
                "--expected-receipt-sha256",
                receipt_digest or digest(self.receipt),
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

    def test_records_claim_after_matching_admission_and_is_idempotent(self) -> None:
        result = self.invoke()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "claimed")
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(receipt["coordinator_generation"], 4)
        self.assertEqual(receipt["claims"][0]["ticket_id"], "ticket-1")
        self.assertEqual(receipt["claims"][0]["lane"], "build-review")

        second = self.invoke(generation=4, receipt_digest=digest(self.receipt))
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(second.stdout)["status"], "already-claimed")
        self.assertEqual(
            json.loads(self.receipt.read_text(encoding="utf-8"))[
                "coordinator_generation"
            ],
            4,
        )

    def test_rejects_stale_receipt_and_owner_mismatch_without_writing(self) -> None:
        before = self.receipt.read_bytes()
        self.assert_rejected(self.invoke(generation=4), "coordinator_generation")
        self.assertEqual(self.receipt.read_bytes(), before)
        self.write_claim(owner_id="other-agent")
        self.assert_rejected(self.invoke(), "owner or phase")
        self.assertEqual(self.receipt.read_bytes(), before)

    def test_rejects_decision_from_different_request(self) -> None:
        self.request.write_text(
            self.request.read_text(encoding="utf-8").replace("src/a.py", "src/b.py"),
            encoding="utf-8",
        )

        self.assert_rejected(self.invoke(), "not produced from this request")

    def test_rejects_invalid_ticket_base(self) -> None:
        self.write_claim()
        payload = json.loads(self.claim.read_text(encoding="utf-8"))
        payload["ticket_base"]["commit"] = "invalid"
        self.claim.write_text(json.dumps(payload), encoding="utf-8")

        self.assert_rejected(self.invoke(), "Git object id")


if __name__ == "__main__":
    unittest.main()
