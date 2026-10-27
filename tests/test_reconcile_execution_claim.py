from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill" / "dag" / "scripts" / "reconcile_execution_claim.py"


class ReconcileExecutionClaimTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.receipt = self.root / "receipt.json"
        self.evidence = self.root / "stop-evidence.txt"
        self.evidence.write_text("writer acknowledged stop\n", encoding="utf-8")
        self.write_receipt()

    def write_receipt(self) -> None:
        claim = {
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
                {"resource": "agent_slots", "quantity": 1, "mode": "exclusive"}
            ],
            "lane": "build-review",
            "request_sha256": "1" * 64,
            "decision_sha256": "2" * 64,
        }
        self.receipt.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Run Receipt",
                    "run_id": "run-1",
                    "coordinator_generation": 4,
                    "claims": [claim],
                    "execution_records": [],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def invoke(
        self, state: str, output: Path, *extra: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--receipt",
                str(self.receipt),
                "--ticket-id",
                "ticket-1",
                "--writer-state",
                state,
                "--output",
                str(output),
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

    def test_unknown_writer_preserves_claim_and_requires_recheck_event(self) -> None:
        output = self.root / "unknown.json"
        result = self.invoke(
            "unknown", output, "--recheck-event", "contact-agent-1-again"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        capsule = json.loads(output.read_text(encoding="utf-8"))
        self.assertFalse(capsule["resume_allowed"])
        self.assertEqual(capsule["recheck_event"], "contact-agent-1-again")

        missing = self.invoke("unknown", self.root / "missing.json")
        self.assert_rejected(missing, "requires recheck_event")

    def test_stopped_writer_allows_resume_only_with_stop_evidence(self) -> None:
        output = self.root / "stopped.json"
        result = self.invoke(
            "stopped",
            output,
            "--liveness-evidence",
            str(self.evidence),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        capsule = json.loads(output.read_text(encoding="utf-8"))
        self.assertTrue(capsule["resume_allowed"])
        self.assertEqual(capsule["writer_state"], "stopped")
        self.assertEqual(capsule["claim_generation"], 2)

        missing = self.invoke("stopped", self.root / "missing.json")
        self.assert_rejected(missing, "requires liveness evidence")

    def test_live_writer_does_not_allow_resume(self) -> None:
        output = self.root / "live.json"
        result = self.invoke(
            "live",
            output,
            "--liveness-evidence",
            str(self.evidence),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(
            json.loads(output.read_text(encoding="utf-8"))["resume_allowed"]
        )


if __name__ == "__main__":
    unittest.main()
