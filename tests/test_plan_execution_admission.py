from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill" / "dag" / "scripts" / "plan_execution_admission.py"


class AdmissionPlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.request = self.root / "request.json"
        self.output = self.root / "decision.json"
        self.write_request()

    def resource(
        self, name: str = "agent_slots", quantity: int = 1, mode: str = "exclusive"
    ) -> dict[str, object]:
        return {"resource": name, "quantity": quantity, "mode": mode}

    def claim(
        self,
        ticket_id: str,
        phase: str,
        path: str,
        *,
        priority: int | None = None,
        age: int | None = None,
        resource: dict[str, object] | None = None,
    ) -> dict[str, object]:
        result: dict[str, object] = {
            "ticket_id": ticket_id,
            "owner_id": f"agent-{ticket_id}",
            "phase": phase,
            "changed_paths": [path],
            "shared_interfaces": [],
            "resources": [resource or self.resource()],
        }
        if priority is not None:
            result["priority"] = priority
        if age is not None:
            result["age"] = age
        if priority is not None:
            result["required_inputs"] = []
            result["hard_dependencies"] = []
        return result

    def write_request(
        self,
        *,
        live: list[dict[str, object]] | None = None,
        candidates: list[dict[str, object]] | None = None,
        capacity: dict[str, object] | None = None,
    ) -> None:
        self.request.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Execution Admission Request",
                    "run_id": "run-1",
                    "coordinator_generation": 3,
                    "capacity": capacity
                    or {"agent_slots": 3, "runtime_skill_slots": 2},
                    "accepted_direct_inputs": [],
                    "accepted_prerequisites": [],
                    "live_claims": live or [],
                    "candidates": candidates
                    or [
                        self.claim(
                            "ticket-a", "implement", "src/a.py", priority=2, age=1
                        ),
                        self.claim("ticket-b", "review", "src/b.py", priority=1, age=3),
                    ],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def invoke(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--request",
                str(self.request),
                "--output",
                str(self.output),
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

    def test_admits_independent_candidates_deterministically(self) -> None:
        result = self.invoke()

        self.assertEqual(result.returncode, 0, result.stderr)
        decision = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(
            [item["ticket_id"] for item in decision["selected"]],
            ["ticket-a", "ticket-b"],
        )
        self.assertEqual(decision["rejected"], [])

        second = self.invoke()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(second.stdout)["status"], "already-published")

    def test_rejects_path_conflict_with_live_claim_and_keeps_other_work(self) -> None:
        self.write_request(
            live=[self.claim("live", "implement", "src/a.py")],
            candidates=[
                self.claim("conflict", "implement", "src/a.py", priority=3, age=0),
                self.claim("independent", "implement", "src/b.py", priority=1, age=0),
            ],
        )

        result = self.invoke()

        self.assertEqual(result.returncode, 0, result.stderr)
        decision = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(
            [item["ticket_id"] for item in decision["selected"]], ["independent"]
        )
        self.assertEqual(
            decision["rejected"][0]["admission_reason"], "path_or_interface_conflict"
        )
        self.assertEqual(decision["rejected"][0]["conflicting_ticket_id"], "live")

    def test_promotion_lane_is_single_and_priority_ordered(self) -> None:
        self.write_request(
            candidates=[
                self.claim("low", "promotion", "src/low.py", priority=1, age=0),
                self.claim("high", "promotion", "src/high.py", priority=3, age=0),
            ]
        )

        result = self.invoke()

        self.assertEqual(result.returncode, 0, result.stderr)
        decision = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual([item["ticket_id"] for item in decision["selected"]], ["high"])
        self.assertEqual(
            decision["rejected"][0]["admission_reason"], "promotion_lane_busy"
        )

    def test_rejects_capacity_excess_and_unknown_capacity(self) -> None:
        self.write_request(
            capacity={"agent_slots": 1, "runtime_skill_slots": 1},
            candidates=[
                self.claim("one", "implement", "src/one.py", priority=2, age=0),
                self.claim("two", "implement", "src/two.py", priority=1, age=0),
            ],
        )
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        decision = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual([item["ticket_id"] for item in decision["selected"]], ["one"])
        self.assertEqual(
            decision["rejected"][0]["admission_reason"], "capacity_exceeded"
        )

        self.output.unlink()
        self.write_request(
            capacity={"agent_slots": None, "runtime_skill_slots": 1},
            candidates=[
                self.claim("unknown", "implement", "src/unknown.py", priority=1, age=0)
            ],
        )
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        decision = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(decision["selected"], [])
        self.assertEqual(
            decision["rejected"][0]["admission_reason"], "capacity_unknown"
        )

    def test_rejects_duplicate_ticket_ids(self) -> None:
        self.write_request(
            candidates=[
                self.claim("same", "implement", "src/a.py", priority=1, age=0),
                self.claim("same", "review", "src/b.py", priority=1, age=0),
            ]
        )

        self.assert_rejected(self.invoke(), "duplicate ticket_id")

    def test_rejects_missing_accepted_inputs_and_hard_dependencies(self) -> None:
        candidate = self.claim(
            "dependent", "implement", "src/dependent.py", priority=1, age=0
        )
        candidate["required_inputs"] = [
            {"name": "prerequisite-output", "identity": "sha256:" + "a" * 64}
        ]
        candidate["hard_dependencies"] = [
            {"ticket_id": "ticket-prerequisite", "identity": "output:" + "b" * 40}
        ]
        self.write_request(candidates=[candidate])

        result = self.invoke()

        self.assertEqual(result.returncode, 0, result.stderr)
        decision = json.loads(self.output.read_text(encoding="utf-8"))
        reasons = {item["admission_reason"] for item in decision["rejected"]}
        self.assertEqual(reasons, {"missing_accepted_input"})

        self.output.unlink()
        self.write_request(
            candidates=[candidate],
        )
        request = json.loads(self.request.read_text(encoding="utf-8"))
        request["accepted_direct_inputs"] = [
            {"name": "prerequisite-output", "identity": "sha256:" + "a" * 64}
        ]
        self.request.write_text(json.dumps(request), encoding="utf-8")
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        decision = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(
            decision["rejected"][0]["admission_reason"], "hard_dependency_unmet"
        )


if __name__ == "__main__":
    unittest.main()
