from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill" / "dag" / "scripts" / "record_execution_checkpoint.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ExecutionCheckpointRecordTests(unittest.TestCase):
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
        self.output = self.root / "shadow" / "record.json"
        self.output.parent.mkdir()
        self.write_inputs()

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

    def invoke(self, output: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--capsule",
                str(self.capsule),
                "--checkpoint",
                str(self.checkpoint),
                "--artifact-root",
                str(self.artifacts),
                "--output",
                str(output or self.output),
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def assert_rejected(
        self, result: subprocess.CompletedProcess[str], text: str
    ) -> None:
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.startswith("error: "), result.stderr)
        self.assertIn(text, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_publishes_a_compact_record_and_is_idempotent(self) -> None:
        first = self.invoke()

        self.assertEqual(first.returncode, 0, first.stderr)
        summary = json.loads(first.stdout)
        self.assertEqual(summary["status"], "published")
        record_bytes = self.output.read_bytes()
        record = json.loads(record_bytes)
        self.assertEqual(record["kind"], "Execution Checkpoint Record")
        self.assertEqual(record["claim_generation"], 2)
        self.assertEqual(record["observed_at"], "2026-10-27T10:00:00Z")
        self.assertEqual(record["evidence_ids"], ["evidence-1"])

        second = self.invoke()

        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(second.stdout)["status"], "already-published")
        self.assertEqual(self.output.read_bytes(), record_bytes)

    def test_rejects_changed_paths_outside_capsule_scope(self) -> None:
        payload = json.loads(self.checkpoint.read_text(encoding="utf-8"))
        payload["changed_paths"] = ["src/other.py"]
        self.checkpoint.write_text(json.dumps(payload), encoding="utf-8")

        self.assert_rejected(
            self.invoke(), "changed_paths must be within capsule.scope"
        )
        self.assertFalse(self.output.exists())

    def test_rejects_mismatched_claim_identity(self) -> None:
        payload = json.loads(self.checkpoint.read_text(encoding="utf-8"))
        payload["claim_generation"] = 3
        self.checkpoint.write_text(json.dumps(payload), encoding="utf-8")

        self.assert_rejected(self.invoke(), "claim_generation do not match")

    def test_rejects_evidence_digest_mismatch(self) -> None:
        payload = json.loads(self.checkpoint.read_text(encoding="utf-8"))
        payload["evidence_delta"][0]["artifact_sha256"] = "0" * 64
        self.checkpoint.write_text(json.dumps(payload), encoding="utf-8")

        self.assert_rejected(self.invoke(), "artifact digest does not match")

    def test_rejects_evidence_symlink_escape(self) -> None:
        outside = self.root / "outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        link = self.artifacts / "link.txt"
        link.symlink_to(outside)
        payload = json.loads(self.checkpoint.read_text(encoding="utf-8"))
        payload["evidence_delta"][0]["artifact_path"] = "link.txt"
        payload["evidence_delta"][0]["artifact_sha256"] = digest(outside)
        self.checkpoint.write_text(json.dumps(payload), encoding="utf-8")

        self.assert_rejected(self.invoke(), "artifact path escapes its root")

    def test_rejects_output_collision_and_input_overwrite(self) -> None:
        self.output.write_text("different\n", encoding="utf-8")
        self.assert_rejected(
            self.invoke(), "output already exists with different content"
        )

        self.output.unlink()
        result = self.invoke(self.checkpoint)
        self.assert_rejected(result, "output must be different from every input")

    def test_rejects_duplicate_json_fields_without_writing(self) -> None:
        self.checkpoint.write_text(
            '{"schema_version":1,"schema_version":1}', encoding="utf-8"
        )

        self.assert_rejected(self.invoke(), "duplicate JSON field")
        self.assertFalse(self.output.exists())

    def test_rejects_candidate_before_verification(self) -> None:
        payload = json.loads(self.checkpoint.read_text(encoding="utf-8"))
        payload["candidate"] = {
            "commit": "a" * 40,
            "tree": "b" * 40,
            "range": "base..candidate",
        }
        self.checkpoint.write_text(json.dumps(payload), encoding="utf-8")

        self.assert_rejected(
            self.invoke(),
            "candidate is not allowed before verify, review, or promotion",
        )

    def test_rejects_unsafe_output_parent(self) -> None:
        outside = self.root / "real"
        outside.mkdir()
        link = self.root / "linked"
        link.symlink_to(outside, target_is_directory=True)

        self.assert_rejected(self.invoke(link / "record.json"), "output parent")


if __name__ == "__main__":
    unittest.main()
