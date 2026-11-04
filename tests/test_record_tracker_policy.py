from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT_SCRIPT = ROOT / "skill" / "dag" / "scripts" / "commit.py"
PUBLISH_SCRIPT = ROOT / "skill" / "dag" / "scripts" / "publish.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TrackerPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.off_delivery = self.root / "off-delivery"
        self.off_delivery.mkdir()
        self.receipt = self.off_delivery / "run-receipt.json"
        self.policy = self.off_delivery / "tracker-policy.json"
        self.init_repo()
        self.write_receipt()

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def init_repo(self) -> None:
        self.git("init", "-q")
        self.git("config", "user.name", "Test User")
        self.git("config", "user.email", "test@example.com")
        (self.repo / "docs" / "agents").mkdir(parents=True)
        (self.repo / "specs" / "0.8.8" / "tickets").mkdir(parents=True)
        (self.repo / ".scratch" / "active" / "0.8.8" / "issues").mkdir(parents=True)
        (self.repo / ".dag").mkdir()

        rule_file = self.repo / "docs" / "agents" / "issue-tracker.md"
        rule_file.write_text("# Tracker rules\n", encoding="utf-8")
        spec_file = self.repo / "specs" / "0.8.8" / "spec.md"
        spec_file.write_text("# Spec\n", encoding="utf-8")
        def_ticket = self.repo / "specs" / "0.8.8" / "tickets" / "01.md"
        def_ticket.write_text("# Ticket 01 obligation\n", encoding="utf-8")
        tracker_ticket = (
            self.repo / ".scratch" / "active" / "0.8.8" / "issues" / "01.md"
        )
        tracker_ticket.write_text("**Status:** ready-for-agent\n", encoding="utf-8")

        self.rule_oid = self.git("hash-object", "-w", str(rule_file))
        spec_oid = self.git("hash-object", "-w", str(spec_file))
        def_ticket_oid = self.git("hash-object", "-w", str(def_ticket))
        self.definition_paths = [
            "docs/agents/issue-tracker.md",
            "specs/0.8.8/spec.md",
            "specs/0.8.8/tickets/01.md",
        ]
        index = {
            "schema_version": 1,
            "inputs": [
                {"path": "docs/agents/issue-tracker.md", "blob_oid": self.rule_oid},
                {"path": "specs/0.8.8/spec.md", "blob_oid": spec_oid},
                {"path": "specs/0.8.8/tickets/01.md", "blob_oid": def_ticket_oid},
            ],
        }
        (self.repo / ".dag" / "definition-index.json").write_text(
            json.dumps(index, indent=2) + "\n", encoding="utf-8"
        )
        self.git("add", ".")
        self.git("commit", "-q", "-m", "bind definition")
        self.base_commit = self.git("rev-parse", "HEAD")
        self.base_tree = self.git("rev-parse", "HEAD^{tree}")

    def write_receipt(
        self,
        *,
        generation: int = 1,
        claims: list[dict[str, object]] | None = None,
        dispositions: list[dict[str, object]] | None = None,
    ) -> None:
        payload: dict[str, object] = {
            "schema_version": 1,
            "kind": "Run Receipt",
            "run_id": "run-1",
            "coordinator_generation": generation,
            "claims": claims or [],
            "execution_records": [],
        }
        if dispositions is not None:
            payload["ticket_dispositions"] = dispositions
        self.receipt.write_text(
            json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8"
        )

    def policy_payload(
        self,
        mode: str = "in_repo",
        *,
        definition_paths: list[str] | None = None,
        tracker_paths: list[str] | None = None,
        authoritative_paths: list[str] | None = None,
        update_scope: str | None = None,
        stateful_decision: dict[str, object] | None = None,
    ) -> dict[str, object]:
        if mode == "none":
            default_auth: list[str] = []
            default_tracker: list[str] = []
            default_scope = "none"
        elif mode == "external_snapshot":
            default_auth = [".dag/snapshots/jira-0.8.8.json"]
            default_tracker = [".dag/snapshots/jira-0.8.8-state.json"]
            default_scope = "per_ticket"
        else:
            default_auth = [".scratch/active/0.8.8"]
            default_tracker = [".scratch/active/0.8.8/issues/01.md"]
            default_scope = "per_ticket"
        payload: dict[str, object] = {
            "schema_version": 1,
            "kind": "Tracker Policy",
            "run_id": "run-1",
            "mode": mode,
            "authoritative_paths": (
                default_auth if authoritative_paths is None else authoritative_paths
            ),
            "rule_refs": [
                {
                    "id": "issue-tracker",
                    "path": "docs/agents/issue-tracker.md",
                    "identity": self.rule_oid,
                }
            ],
            "definition_paths": (
                list(self.definition_paths)
                if definition_paths is None
                else definition_paths
            ),
            "tracker_paths": (
                default_tracker if tracker_paths is None else tracker_paths
            ),
            "update_scope": default_scope if update_scope is None else update_scope,
            "rationale": f"Configured {mode} tracker policy for run-1.",
            "stateful_tracker_decision": stateful_decision,
        }
        return payload

    def invoke(
        self,
        payload: dict[str, object] | None = None,
        *,
        generation: int = 1,
        receipt_digest: str | None = None,
        policy_path: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        target_policy = policy_path or self.policy
        if payload is not None:
            target_policy.write_text(
                json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8"
            )
        command = [
            sys.executable,
            str(COMMIT_SCRIPT),
            "tracker-policy",
            "--repository",
            str(self.repo),
            "--commit",
            self.base_commit,
            "--receipt",
            str(self.receipt),
            "--policy",
            str(target_policy),
            "--expected-generation",
            str(generation),
            "--expected-receipt-sha256",
            receipt_digest or digest(self.receipt),
        ]
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

    def test_records_none_in_repo_and_external_snapshot_modes_idempotently(
        self,
    ) -> None:
        for mode in ("none", "in_repo", "external_snapshot"):
            with self.subTest(mode=mode):
                self.write_receipt(generation=10)
                first = self.invoke(
                    self.policy_payload(mode),
                    generation=10,
                )
                self.assertEqual(first.returncode, 0, first.stderr)
                body = json.loads(first.stdout)
                self.assertEqual(body["status"], "recorded")
                self.assertEqual(body["mode"], mode)

                receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
                self.assertEqual(receipt["coordinator_generation"], 11)
                self.assertEqual(receipt["tracker_policy"]["mode"], mode)
                self.assertEqual(
                    receipt["tracker_policy"]["policy_key"], body["policy_key"]
                )

                second = self.invoke(
                    generation=11,
                    receipt_digest=digest(self.receipt),
                )
                self.assertEqual(second.returncode, 0, second.stderr)
                self.assertEqual(
                    json.loads(second.stdout)["status"], "already-recorded"
                )
                self.assertEqual(
                    json.loads(self.receipt.read_text(encoding="utf-8"))[
                        "coordinator_generation"
                    ],
                    11,
                )

    def test_rejects_definition_and_tracker_path_overlap_by_default(self) -> None:
        before = self.receipt.read_bytes()
        exact_overlap = self.policy_payload(
            "in_repo",
            tracker_paths=["specs/0.8.8/tickets/01.md"],
        )
        self.assert_rejected(self.invoke(exact_overlap), "overlap")
        self.assertEqual(self.receipt.read_bytes(), before)

        parent_child_overlap = self.policy_payload(
            "in_repo",
            tracker_paths=["specs/0.8.8"],
        )
        self.assert_rejected(self.invoke(parent_child_overlap), "overlap")
        self.assertEqual(self.receipt.read_bytes(), before)

    def test_accepts_overlap_only_with_complete_stateful_tracker_decision(
        self,
    ) -> None:
        incomplete = self.policy_payload(
            "in_repo",
            tracker_paths=["specs/0.8.8/tickets/01.md", "specs/0.8.8/spec.md"],
            stateful_decision={
                "decision_id": "stateful-01",
                "approved_by": "user",
                "overlapping_paths": ["specs/0.8.8/tickets/01.md"],
                "rationale": "Only one path was listed.",
            },
        )
        self.assert_rejected(self.invoke(incomplete), "overlapping_paths")

        complete = self.policy_payload(
            "in_repo",
            tracker_paths=["specs/0.8.8/tickets/01.md"],
            stateful_decision={
                "decision_id": "stateful-01",
                "approved_by": "user",
                "overlapping_paths": ["specs/0.8.8/tickets/01.md"],
                "rationale": "Project explicitly keeps status in the Ticket file.",
            },
        )
        result = self.invoke(complete)
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(
            receipt["tracker_policy"]["stateful_tracker_decision"]["decision_id"],
            "stateful-01",
        )

    def test_rejects_stale_receipt_generation_and_definition_index_mismatch(
        self,
    ) -> None:
        before = self.receipt.read_bytes()
        self.assert_rejected(
            self.invoke(self.policy_payload("in_repo"), generation=99),
            "coordinator_generation",
        )
        self.assertEqual(self.receipt.read_bytes(), before)

        mismatched = self.policy_payload(
            "in_repo",
            definition_paths=["docs/agents/issue-tracker.md", "specs/0.8.8/spec.md"],
        )
        self.assert_rejected(self.invoke(mismatched), "definition-index.json")
        self.assertEqual(self.receipt.read_bytes(), before)

    def test_policy_records_must_stay_off_delivery(self) -> None:
        in_repo_policy = self.repo / "tracker-policy.json"
        result = self.invoke(
            self.policy_payload("in_repo"),
            policy_path=in_repo_policy,
        )
        self.assert_rejected(result, "off-delivery")

    def test_blocks_execution_agent_from_claiming_tracker_paths_and_records_pending_disposition(
        self,
    ) -> None:
        recorded = self.invoke(self.policy_payload("in_repo"), generation=1)
        self.assertEqual(recorded.returncode, 0, recorded.stderr)

        # Execution Agent attempting to reserve tracker_paths is rejected.
        bad_request = self.off_delivery / "bad-request.json"
        bad_decision = self.off_delivery / "bad-decision.json"
        bad_claim = self.off_delivery / "bad-claim.json"
        bad_request.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Execution Admission Request",
                    "run_id": "run-1",
                    "coordinator_generation": 2,
                    "capacity": {"agent_slots": 2, "runtime_skill_slots": 1},
                    "accepted_direct_inputs": [],
                    "accepted_prerequisites": [],
                    "live_claims": [],
                    "candidates": [
                        {
                            "ticket_id": "01",
                            "owner_id": "agent-01",
                            "phase": "implement",
                            "changed_paths": [".scratch/active/0.8.8/issues/01.md"],
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
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(PUBLISH_SCRIPT),
                "admission-decision",
                "--request",
                str(bad_request),
                "--output",
                str(bad_decision),
            ],
            capture_output=True,
            check=True,
        )
        bad_claim.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Execution Claim",
                    "ticket_id": "01",
                    "owner_id": "agent-01",
                    "claim_generation": 1,
                    "workspace": str(self.root / "ws-01"),
                    "branch": "refs/heads/codex/ticket-01",
                    "phase": "implement",
                    "ticket_base": {"commit": self.base_commit, "tree": self.base_tree},
                    "changed_paths": [".scratch/active/0.8.8/issues/01.md"],
                    "shared_interfaces": [],
                    "resources": [
                        {
                            "resource": "agent_slots",
                            "quantity": 1,
                            "mode": "exclusive",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        claim_res = subprocess.run(
            [
                sys.executable,
                str(COMMIT_SCRIPT),
                "claim",
                "--receipt",
                str(self.receipt),
                "--decision",
                str(bad_decision),
                "--claim",
                str(bad_claim),
                "--expected-generation",
                "2",
                "--expected-receipt-sha256",
                digest(self.receipt),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assert_rejected(claim_res, "tracker_paths")

        # Valid code claim succeeds, then disposition records a pending tracker update
        # that blocks a subsequent claim under per_ticket scope.
        good_request = self.off_delivery / "good-request.json"
        good_decision = self.off_delivery / "good-decision.json"
        good_claim = self.off_delivery / "good-claim.json"
        good_request.write_text(
            bad_request.read_text(encoding="utf-8").replace(
                ".scratch/active/0.8.8/issues/01.md", "src/auth.py"
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(PUBLISH_SCRIPT),
                "admission-decision",
                "--request",
                str(good_request),
                "--output",
                str(good_decision),
            ],
            capture_output=True,
            check=True,
        )
        good_claim.write_text(
            bad_claim.read_text(encoding="utf-8").replace(
                ".scratch/active/0.8.8/issues/01.md", "src/auth.py"
            ),
            encoding="utf-8",
        )
        good_res = subprocess.run(
            [
                sys.executable,
                str(COMMIT_SCRIPT),
                "claim",
                "--receipt",
                str(self.receipt),
                "--decision",
                str(good_decision),
                "--claim",
                str(good_claim),
                "--expected-generation",
                "2",
                "--expected-receipt-sha256",
                digest(self.receipt),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(good_res.returncode, 0, good_res.stderr)

        ev = self.off_delivery / "disp-ev.txt"
        ev.write_text("superseded rationale\n", encoding="utf-8")
        disp = self.off_delivery / "disp.json"
        disp.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Ticket Disposition Decision",
                    "run_id": "run-1",
                    "coordinator_generation": 3,
                    "ticket_id": "01",
                    "claim_generation": 1,
                    "disposition": "Superseded",
                    "rule_identity": "rule-01",
                    "decided_by": "coordinator",
                    "decided_at": "2026-11-03T10:00:00Z",
                    "rationale": "Superseded for test.",
                    "evidence_refs": [
                        {"id": "ev-1", "path": str(ev), "sha256": digest(ev)}
                    ],
                }
            ),
            encoding="utf-8",
        )
        disp_res = subprocess.run(
            [
                sys.executable,
                str(COMMIT_SCRIPT),
                "disposition",
                "--receipt",
                str(self.receipt),
                "--decision",
                str(disp),
                "--expected-generation",
                "3",
                "--expected-receipt-sha256",
                digest(self.receipt),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(disp_res.returncode, 0, disp_res.stderr)
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(len(receipt["pending_tracker_updates"]), 1)
        self.assertEqual(receipt["pending_tracker_updates"][0]["ticket_id"], "01")

        # Next claim is blocked until Tracker Checkpoint completes.
        next_request = self.off_delivery / "next-request.json"
        next_decision = self.off_delivery / "next-decision.json"
        next_claim = self.off_delivery / "next-claim.json"
        next_request.write_text(
            good_request.read_text(encoding="utf-8")
            .replace('"coordinator_generation": 2', '"coordinator_generation": 4')
            .replace('"ticket_id": "01"', '"ticket_id": "02"'),
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(PUBLISH_SCRIPT),
                "admission-decision",
                "--request",
                str(next_request),
                "--output",
                str(next_decision),
            ],
            capture_output=True,
            check=True,
        )
        next_claim.write_text(
            good_claim.read_text(encoding="utf-8").replace(
                '"ticket_id": "01"', '"ticket_id": "02"'
            ),
            encoding="utf-8",
        )
        blocked_res = subprocess.run(
            [
                sys.executable,
                str(COMMIT_SCRIPT),
                "claim",
                "--receipt",
                str(self.receipt),
                "--decision",
                str(next_decision),
                "--claim",
                str(next_claim),
                "--expected-generation",
                "4",
                "--expected-receipt-sha256",
                digest(self.receipt),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assert_rejected(blocked_res, "pending_tracker_updates")


if __name__ == "__main__":
    unittest.main()
