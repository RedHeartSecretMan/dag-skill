from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD_SCRIPT = ROOT / "skill" / "dag" / "scripts" / "record_execution_checkpoint.py"
INDEX_SCRIPT = ROOT / "skill" / "dag" / "scripts" / "index_execution_record.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RunReceiptIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()
        self.evidence = self.artifacts / "test-output.txt"
        self.evidence.write_text("test passed\n", encoding="utf-8")
        self.capsule = self.root / "capsule.json"
        self.checkpoint = self.root / "checkpoint.json"
        self.record = self.root / "shadow" / "record.json"
        self.record.parent.mkdir()
        self.receipt = self.root / "receipt.json"
        self.write_inputs()
        self.publish_record()
        self.receipt.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Run Receipt",
                    "run_id": "run-1",
                    "coordinator_generation": 0,
                    "claims": [],
                },
                sort_keys=True,
            )
            + "\n",
        )

    def base(self) -> dict[str, str]:
        return {"commit": "a" * 40, "tree": "b" * 40}

    def write_inputs(self) -> None:
        self.capsule.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Ticket Capsule",
                    "run_id": "run-1",
                    "ticket_id": "ticket-1",
                    "owner_id": "agent-1",
                    "claim_generation": 2,
                    "workspace": str(self.root / "workspace"),
                    "ticket_base": self.base(),
                    "definition_identity": "sha256:" + "c" * 64,
                    "authorities": [
                        {
                            "name": "ticket",
                            "path": "tickets/ticket-1.md",
                            "identity": "sha256:" + "d" * 64,
                        }
                    ],
                    "scope": ["src/a.py"],
                    "acceptance_obligations": [
                        {
                            "id": "obligation-1",
                            "source": "tickets/ticket-1.md",
                            "identity": "sha256:" + "e" * 64,
                        }
                    ],
                    "required_gates": ["unit"],
                    "permissions": ["local"],
                    "finalization_policy": "deferred",
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        self.checkpoint.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Execution Checkpoint",
                    "run_id": "run-1",
                    "ticket_id": "ticket-1",
                    "owner_id": "agent-1",
                    "claim_generation": 2,
                    "workspace": str(self.root / "workspace"),
                    "phase": "implement",
                    "observed_at": "2026-10-27T10:00:00Z",
                    "ticket_base": self.base(),
                    "changed_paths": ["src/a.py"],
                    "accepted_inputs": [],
                    "candidate": None,
                    "evidence_delta": [
                        {
                            "evidence_id": "evidence-1",
                            "type": "test",
                            "producer": "agent-1",
                            "operation": "unit-test",
                            "artifact_path": "test-output.txt",
                            "artifact_sha256": digest(self.evidence),
                            "observed_result": "pass",
                            "commit": None,
                            "tree": None,
                            "environment_identity": "host-1",
                            "applicability": "ticket",
                            "invalidation_reason": None,
                        }
                    ],
                    "open_findings": [],
                    "resource_claims": [
                        {
                            "resource": "agent_slots",
                            "quantity": 1,
                            "mode": "exclusive",
                        }
                    ],
                    "next_action": "continue implementation",
                    "blocking_condition": None,
                    "measurement_version": 1,
                    "context_budget": {
                        "dispatch_bytes": 120,
                        "retained_bytes": 80,
                        "handoff_bytes": 64,
                        "measurement_kind": "bytes",
                        "estimated": True,
                    },
                    "metrics": [
                        {
                            "name": "dispatch.input_bytes",
                            "value": 120,
                            "unit": "bytes",
                            "tags": {"phase": "implement"},
                        }
                    ],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def publish_record(
        self, output: Path | None = None, checkpoint: Path | None = None
    ) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(RECORD_SCRIPT),
                "--capsule",
                str(self.capsule),
                "--checkpoint",
                str(checkpoint or self.checkpoint),
                "--artifact-root",
                str(self.artifacts),
                "--output",
                str(output or self.record),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def invoke(
        self,
        *,
        receipt: Path | None = None,
        record: Path | None = None,
        generation: int = 0,
        receipt_digest: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        receipt = receipt or self.receipt
        record = record or self.record
        return subprocess.run(
            [
                sys.executable,
                str(INDEX_SCRIPT),
                "--receipt",
                str(receipt),
                "--record",
                str(record),
                "--artifact-root",
                str(self.artifacts),
                "--expected-generation",
                str(generation),
                "--expected-receipt-sha256",
                receipt_digest or digest(receipt),
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

    def test_indexes_record_with_generation_cas_and_preserves_receipt_fields(
        self,
    ) -> None:
        before = self.receipt.read_bytes()
        result = self.invoke()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "indexed")
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(receipt["claims"], [])
        self.assertEqual(receipt["coordinator_generation"], 1)
        self.assertEqual(len(receipt["execution_records"]), 1)
        entry = receipt["execution_records"][0]
        self.assertEqual(entry["ticket_id"], "ticket-1")
        self.assertEqual(entry["claim_generation"], 2)
        self.assertEqual(entry["record_sha256"], digest(self.record))
        self.assertNotEqual(self.receipt.read_bytes(), before)

    def test_retries_same_record_idempotently_without_generation_change(self) -> None:
        self.assertEqual(self.invoke().returncode, 0)
        current_digest = digest(self.receipt)

        result = self.invoke(generation=1, receipt_digest=current_digest)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "already-indexed")
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(receipt["coordinator_generation"], 1)

    def test_rejects_stale_generation_or_receipt_digest_without_writing(self) -> None:
        before = self.receipt.read_bytes()
        self.assert_rejected(self.invoke(generation=1), "coordinator_generation")
        self.assertEqual(self.receipt.read_bytes(), before)
        self.assert_rejected(self.invoke(receipt_digest="0" * 64), "SHA-256")
        self.assertEqual(self.receipt.read_bytes(), before)

    def test_rejects_changed_referenced_checkpoint(self) -> None:
        self.assertEqual(self.invoke().returncode, 0)
        current_digest = digest(self.receipt)
        self.checkpoint.write_text(
            self.checkpoint.read_text(encoding="utf-8") + "\n", encoding="utf-8"
        )

        result = self.invoke(generation=1, receipt_digest=current_digest)

        self.assert_rejected(result, "checkpoint SHA-256 does not match")

    def test_rejects_conflicting_record_for_same_claim(self) -> None:
        second_checkpoint = self.root / "checkpoint-2.json"
        second_checkpoint.write_text(
            self.checkpoint.read_text(encoding="utf-8").replace(
                "continue implementation", "different action"
            ),
            encoding="utf-8",
        )
        second_record = self.root / "shadow" / "record-2.json"
        self.publish_record(second_record, checkpoint=second_checkpoint)
        self.assertEqual(self.invoke().returncode, 0)
        current_digest = digest(self.receipt)

        result = self.invoke(
            record=second_record, generation=1, receipt_digest=current_digest
        )

        self.assert_rejected(result, "different record for this claim")

    def test_rejects_receipt_symlink(self) -> None:
        real_receipt = self.root / "real-receipt.json"
        real_receipt.write_bytes(self.receipt.read_bytes())
        self.receipt.unlink()
        self.receipt.symlink_to(real_receipt)

        self.assert_rejected(self.invoke(), "regular non-symlink")


if __name__ == "__main__":
    unittest.main()
