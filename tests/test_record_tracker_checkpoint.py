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
VERIFY_SCRIPT = ROOT / "skill" / "dag" / "scripts" / "verify.py"
PROMOTE_SCRIPT = ROOT / "skill" / "dag" / "scripts" / "promote.py"
PUBLISH_SCRIPT = ROOT / "skill" / "dag" / "scripts" / "publish.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TrackerCheckpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.off_delivery = self.root / "off-delivery"
        self.off_delivery.mkdir()
        self.receipt = self.off_delivery / "run-receipt.json"
        self.policy_file = self.off_delivery / "tracker-policy.json"
        self.checkpoint_file = self.off_delivery / "tracker-checkpoint.json"
        self.review_artifact = self.off_delivery / "tracker-review.md"
        self.review_artifact.write_text(
            "Independent Standards/Spec review: no blocking finding.\n",
            encoding="utf-8",
        )
        self.disp_evidence = self.off_delivery / "disposition-evidence.txt"
        self.disp_evidence.write_text("Accepted evidence.\n", encoding="utf-8")
        self.integration_ref = "refs/heads/codex/dag-integration"
        self.init_repo()
        self.init_receipt_and_policy("in_repo")

    def git(self, *args: str, cwd: Path | None = None) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd or self.repo,
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
        (self.repo / "specs" / "tickets").mkdir(parents=True)
        (self.repo / ".scratch" / "active" / "0.8.8" / "issues").mkdir(parents=True)
        (self.repo / ".dag" / "snapshots").mkdir(parents=True)

        rule_file = self.repo / "docs" / "agents" / "issue-tracker.md"
        rule_file.write_text("# Tracker contract\n", encoding="utf-8")
        spec_ticket = self.repo / "specs" / "tickets" / "01.md"
        spec_ticket.write_text("# Ticket 01 definition\n", encoding="utf-8")
        tracker_ticket = (
            self.repo / ".scratch" / "active" / "0.8.8" / "issues" / "01.md"
        )
        tracker_ticket.write_text("Initial planning text.\n", encoding="utf-8")
        ext_snapshot = self.repo / ".dag" / "snapshots" / "jira-state.json"
        ext_snapshot.write_text('{"tickets":{"01":"open"}}\n', encoding="utf-8")

        self.rule_oid = self.git("hash-object", "-w", str(rule_file))
        self.spec_ticket_oid = self.git("hash-object", "-w", str(spec_ticket))
        self.initial_tracker_oid = self.git("hash-object", "-w", str(tracker_ticket))
        self.initial_snapshot_oid = self.git("hash-object", "-w", str(ext_snapshot))
        index = {
            "schema_version": 1,
            "inputs": [
                {"path": "docs/agents/issue-tracker.md", "blob_oid": self.rule_oid},
                {"path": "specs/tickets/01.md", "blob_oid": self.spec_ticket_oid},
            ],
        }
        (self.repo / ".dag" / "definition-index.json").write_text(
            json.dumps(index, indent=2) + "\n", encoding="utf-8"
        )
        self.git("add", ".")
        self.git("commit", "-q", "-m", "initial bound state")
        self.base_commit = self.git("rev-parse", "HEAD")
        self.base_tree = self.git("rev-parse", "HEAD^{tree}")
        self.git("update-ref", self.integration_ref, self.base_commit)
        # Detach main worktree so integration_ref is never checked out.
        self.git("checkout", "-q", "--detach", self.base_commit)

    def init_receipt_and_policy(
        self,
        mode: str,
        *,
        tracker_paths: list[str] | None = None,
        stateful_decision: dict[str, object] | None = None,
    ) -> str:
        self.receipt.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Run Receipt",
                    "run_id": "run-1",
                    "coordinator_generation": 1,
                    "integration_ref": self.integration_ref,
                    "claims": [],
                    "execution_records": [],
                    "ticket_dispositions": [
                        {
                            "schema_version": 1,
                            "kind": "Ticket Disposition",
                            "run_id": "run-1",
                            "coordinator_generation": 0,
                            "ticket_id": "01",
                            "claim_generation": 1,
                            "disposition": "Accepted",
                            "rule_identity": "rule:01",
                            "decided_by": "coordinator",
                            "decided_at": "2026-11-03T10:00:00Z",
                            "rationale": "Accepted Ticket 01.",
                            "evidence_refs": [
                                {
                                    "id": "disp-ev",
                                    "path": str(self.disp_evidence),
                                    "sha256": digest(self.disp_evidence),
                                }
                            ],
                            "promotion_evidence_sha256": "1" * 64,
                            "baseline_evidence_sha256": None,
                            "ticket_base": {
                                "commit": self.base_commit,
                                "tree": self.base_tree,
                            },
                            "claim_owner_id": "agent-01",
                        }
                    ],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        if mode == "external_snapshot":
            auth_paths = [".dag/snapshots"]
            default_tracker = [".dag/snapshots/jira-state.json"]
            scope = "per_ticket"
        elif mode == "none":
            auth_paths = []
            default_tracker = []
            scope = "none"
        else:
            auth_paths = [".scratch/active/0.8.8"]
            default_tracker = [".scratch/active/0.8.8/issues/01.md"]
            scope = "per_ticket"
        policy_payload = {
            "schema_version": 1,
            "kind": "Tracker Policy",
            "run_id": "run-1",
            "mode": mode,
            "authoritative_paths": auth_paths,
            "rule_refs": [
                {
                    "id": "issue-tracker",
                    "path": "docs/agents/issue-tracker.md",
                    "identity": self.rule_oid,
                }
            ],
            "definition_paths": [
                "docs/agents/issue-tracker.md",
                "specs/tickets/01.md",
            ],
            "tracker_paths": (
                default_tracker if tracker_paths is None else tracker_paths
            ),
            "update_scope": scope,
            "rationale": f"Use {mode} tracker mode.",
            "stateful_tracker_decision": stateful_decision,
        }
        self.policy_file.write_text(
            json.dumps(policy_payload, sort_keys=True) + "\n", encoding="utf-8"
        )
        res = subprocess.run(
            [
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
                str(self.policy_file),
                "--expected-generation",
                "1",
                "--expected-receipt-sha256",
                digest(self.receipt),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return str(json.loads(res.stdout)["policy_key"])

    def create_candidate_commit(
        self,
        edits: dict[str, str],
        *,
        parent_commit: str | None = None,
        promote: bool = True,
    ) -> tuple[str, str, dict[str, str]]:
        base = parent_commit or self.base_commit
        self.git("checkout", "-q", "--detach", base)
        after_oids: dict[str, str] = {}
        for rel_path, content in edits.items():
            target = self.repo / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            after_oids[rel_path] = self.git("hash-object", "-w", str(target))
        self.git("add", ".")
        self.git("commit", "-q", "-m", "tracker checkpoint commit")
        commit = self.git("rev-parse", "HEAD")
        tree = self.git("rev-parse", "HEAD^{tree}")
        if promote:
            transition = self.off_delivery / f"transition-{commit[:12]}.json"
            transition.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "candidate_kind": "DAG Definition Checkpoint",
                        "integration_ref": self.integration_ref,
                        "base": base,
                        "candidate": commit,
                        "candidate_tree": tree,
                        "evidence": [
                            {
                                "path": self.review_artifact.name,
                                "sha256": digest(self.review_artifact),
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    str(PROMOTE_SCRIPT),
                    "--repository",
                    str(self.repo),
                    "--transition",
                    str(transition),
                    "--expected-transition-sha256",
                    digest(transition),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        return commit, tree, after_oids

    def checkpoint_payload(
        self,
        *,
        policy_key: str,
        base_commit: str,
        base_tree: str,
        candidate_commit: str,
        candidate_tree: str,
        blob_changes: list[dict[str, str | None]],
        generation: int = 2,
        disposition: str = "Accepted",
    ) -> dict[str, object]:
        return {
            "schema_version": 1,
            "kind": "Tracker Checkpoint",
            "run_id": "run-1",
            "coordinator_generation": generation,
            "policy_key": policy_key,
            "integration_ref": self.integration_ref,
            "ticket_dispositions": [
                {
                    "ticket_id": "01",
                    "claim_generation": 1,
                    "disposition": disposition,
                }
            ],
            "base": {"commit": base_commit, "tree": base_tree},
            "candidate": {"commit": candidate_commit, "tree": candidate_tree},
            "changed_paths": sorted(str(item["path"]) for item in blob_changes),
            "blob_changes": blob_changes,
            "evidence_refs": [
                {
                    "id": "checkpoint-review",
                    "path": str(self.review_artifact),
                    "sha256": digest(self.review_artifact),
                }
            ],
        }

    def invoke(
        self,
        payload: dict[str, object] | None = None,
        *,
        generation: int | None = 2,
        receipt_digest: str | None = None,
        preflight: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        if payload is not None:
            self.checkpoint_file.write_text(
                json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8"
            )
        if preflight:
            command = [
                sys.executable,
                str(VERIFY_SCRIPT),
                "tracker-checkpoint",
                "--repository",
                str(self.repo),
                "--receipt",
                str(self.receipt),
                "--checkpoint",
                str(self.checkpoint_file),
            ]
        else:
            assert generation is not None
            command = [
                sys.executable,
                str(COMMIT_SCRIPT),
                "tracker-checkpoint",
                "--repository",
                str(self.repo),
                "--receipt",
                str(self.receipt),
                "--checkpoint",
                str(self.checkpoint_file),
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

    def test_completes_preflight_promotion_recording_and_unlocks_successor_idempotently(
        self,
    ) -> None:
        receipt_before = json.loads(self.receipt.read_text(encoding="utf-8"))
        policy_key = receipt_before["tracker_policy"]["policy_key"]
        self.assertEqual(len(receipt_before["pending_tracker_updates"]), 1)

        # Author tracker commit without promoting yet -> preflight passes, full record rejects.
        commit, tree, after_oids = self.create_candidate_commit(
            {
                ".scratch/active/0.8.8/issues/01.md": (
                    "已完成双材料合并存储验收，回归测试全部通过（无固定状态词要求）。\n"
                )
            },
            promote=False,
        )
        payload = self.checkpoint_payload(
            policy_key=policy_key,
            base_commit=self.base_commit,
            base_tree=self.base_tree,
            candidate_commit=commit,
            candidate_tree=tree,
            blob_changes=[
                {
                    "path": ".scratch/active/0.8.8/issues/01.md",
                    "before_blob_oid": self.initial_tracker_oid,
                    "after_blob_oid": after_oids[".scratch/active/0.8.8/issues/01.md"],
                }
            ],
        )
        pre = self.invoke(payload, preflight=True)
        self.assertEqual(pre.returncode, 0, pre.stderr)
        self.assertEqual(json.loads(pre.stdout)["status"], "verified")
        self.assert_rejected(self.invoke(payload), "integration_ref")

        # Promote Definition Checkpoint + readback, then record Tracker Checkpoint.
        transition = self.off_delivery / "transition.json"
        transition.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "candidate_kind": "DAG Definition Checkpoint",
                    "integration_ref": self.integration_ref,
                    "base": self.base_commit,
                    "candidate": commit,
                    "candidate_tree": tree,
                    "evidence": [
                        {
                            "path": self.review_artifact.name,
                            "sha256": digest(self.review_artifact),
                        },
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(PROMOTE_SCRIPT),
                "--repository",
                str(self.repo),
                "--transition",
                str(transition),
                "--expected-transition-sha256",
                digest(transition),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        first = self.invoke(payload, generation=2)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(json.loads(first.stdout)["status"], "recorded")
        receipt_after = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(receipt_after["coordinator_generation"], 3)
        self.assertEqual(receipt_after["pending_tracker_updates"], [])
        self.assertEqual(len(receipt_after["tracker_checkpoints"]), 1)
        self.assertEqual(
            receipt_after["accepted_integration_tip"],
            {"commit": commit, "tree": tree},
        )

        # Idempotent retry does not increment generation or duplicate checkpoints.
        second = self.invoke(generation=3, receipt_digest=digest(self.receipt))
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(second.stdout)["status"], "already-recorded")
        self.assertEqual(
            json.loads(self.receipt.read_text(encoding="utf-8"))[
                "coordinator_generation"
            ],
            3,
        )

        # Successor Ticket 02 can now be claimed.
        req = self.off_delivery / "req-02.json"
        dec = self.off_delivery / "dec-02.json"
        clm = self.off_delivery / "clm-02.json"
        req.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Execution Admission Request",
                    "run_id": "run-1",
                    "coordinator_generation": 3,
                    "capacity": {"agent_slots": 2, "runtime_skill_slots": 1},
                    "accepted_direct_inputs": [],
                    "accepted_prerequisites": [{"ticket_id": "01", "identity": commit}],
                    "live_claims": [],
                    "candidates": [
                        {
                            "ticket_id": "02",
                            "owner_id": "agent-02",
                            "phase": "implement",
                            "changed_paths": ["src/next.py"],
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
                            "hard_dependencies": [
                                {"ticket_id": "01", "identity": commit}
                            ],
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
                str(req),
                "--output",
                str(dec),
            ],
            capture_output=True,
            check=True,
        )
        clm.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Execution Claim",
                    "ticket_id": "02",
                    "owner_id": "agent-02",
                    "claim_generation": 1,
                    "workspace": str(self.root / "ws-02"),
                    "branch": "refs/heads/codex/ticket-02",
                    "phase": "implement",
                    "ticket_base": {"commit": commit, "tree": tree},
                    "changed_paths": ["src/next.py"],
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
                str(dec),
                "--claim",
                str(clm),
                "--expected-generation",
                "3",
                "--expected-receipt-sha256",
                digest(self.receipt),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(claim_res.returncode, 0, claim_res.stderr)

    def test_accepts_external_snapshot_and_enforces_exact_blob_identities(self) -> None:
        policy_key = self.init_receipt_and_policy(
            "external_snapshot",
        )
        commit, tree, after_oids = self.create_candidate_commit(
            {
                ".dag/snapshots/jira-state.json": (
                    '{"tickets":{"01":{"verdict":"done_in_custom_vocabulary"}}}\n'
                )
            }
        )
        # Mismatched after_blob_oid is rejected even though file path matches.
        wrong_blob = self.checkpoint_payload(
            policy_key=policy_key,
            base_commit=self.base_commit,
            base_tree=self.base_tree,
            candidate_commit=commit,
            candidate_tree=tree,
            blob_changes=[
                {
                    "path": ".dag/snapshots/jira-state.json",
                    "before_blob_oid": self.initial_snapshot_oid,
                    "after_blob_oid": "f" * 40,
                }
            ],
        )
        self.assert_rejected(self.invoke(wrong_blob), "blob_changes")

        # Exact blob identity succeeds regardless of custom wording.
        exact_blob = self.checkpoint_payload(
            policy_key=policy_key,
            base_commit=self.base_commit,
            base_tree=self.base_tree,
            candidate_commit=commit,
            candidate_tree=tree,
            blob_changes=[
                {
                    "path": ".dag/snapshots/jira-state.json",
                    "before_blob_oid": self.initial_snapshot_oid,
                    "after_blob_oid": after_oids[".dag/snapshots/jira-state.json"],
                }
            ],
        )
        ok = self.invoke(exact_blob)
        self.assertEqual(ok.returncode, 0, ok.stderr)

    def test_rejects_stale_policy_stale_checkpoint_and_stale_generation(self) -> None:
        old_policy_key = json.loads(self.receipt.read_text(encoding="utf-8"))[
            "tracker_policy"
        ]["policy_key"]
        commit, tree, after_oids = self.create_candidate_commit(
            {".scratch/active/0.8.8/issues/01.md": "Updated prose v1.\n"}
        )
        # Update policy to a new rationale -> old_policy_key becomes stale.
        updated_policy = json.loads(self.policy_file.read_text(encoding="utf-8"))
        updated_policy["rationale"] = "Updated tracker policy rationale."
        self.policy_file.write_text(
            json.dumps(updated_policy, sort_keys=True) + "\n", encoding="utf-8"
        )
        pol_res = subprocess.run(
            [
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
                str(self.policy_file),
                "--expected-generation",
                "2",
                "--expected-receipt-sha256",
                digest(self.receipt),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        new_policy_key = json.loads(pol_res.stdout)["policy_key"]

        stale_policy_payload = self.checkpoint_payload(
            policy_key=old_policy_key,
            base_commit=self.base_commit,
            base_tree=self.base_tree,
            candidate_commit=commit,
            candidate_tree=tree,
            generation=3,
            blob_changes=[
                {
                    "path": ".scratch/active/0.8.8/issues/01.md",
                    "before_blob_oid": self.initial_tracker_oid,
                    "after_blob_oid": after_oids[".scratch/active/0.8.8/issues/01.md"],
                }
            ],
        )
        self.assert_rejected(
            self.invoke(stale_policy_payload, generation=3), "stale policy"
        )

        # Stale Receipt generation fails without writing.
        valid_policy_payload = self.checkpoint_payload(
            policy_key=new_policy_key,
            base_commit=self.base_commit,
            base_tree=self.base_tree,
            candidate_commit=commit,
            candidate_tree=tree,
            generation=3,
            blob_changes=[
                {
                    "path": ".scratch/active/0.8.8/issues/01.md",
                    "before_blob_oid": self.initial_tracker_oid,
                    "after_blob_oid": after_oids[".scratch/active/0.8.8/issues/01.md"],
                }
            ],
        )
        self.assert_rejected(
            self.invoke(valid_policy_payload, generation=99),
            "coordinator_generation",
        )

        # Move integration_ref ahead to commit2 -> commit becomes a stale checkpoint!
        commit2, _tree2, _oids2 = self.create_candidate_commit(
            {".scratch/active/0.8.8/issues/01.md": "Updated prose v2.\n"},
            parent_commit=commit,
        )
        self.assertNotEqual(commit, commit2)
        self.assert_rejected(
            self.invoke(valid_policy_payload, generation=3),
            "stale checkpoint",
        )

    def test_stateful_tracker_overlap_requires_valid_definition_index_update(
        self,
    ) -> None:
        policy_key = self.init_receipt_and_policy(
            "in_repo",
            tracker_paths=["specs/tickets/01.md"],
            stateful_decision={
                "decision_id": "mixed-01",
                "approved_by": "user",
                "overlapping_paths": ["specs/tickets/01.md"],
                "rationale": "Project mixes definition and status in specs/tickets/01.md.",
            },
        )
        # Modifying specs/tickets/01.md WITHOUT updating .dag/definition-index.json fails.
        bad_commit, bad_tree, bad_oids = self.create_candidate_commit(
            {"specs/tickets/01.md": "# Ticket 01 definition\n\nResolved.\n"}
        )
        bad_payload = self.checkpoint_payload(
            policy_key=policy_key,
            base_commit=self.base_commit,
            base_tree=self.base_tree,
            candidate_commit=bad_commit,
            candidate_tree=bad_tree,
            blob_changes=[
                {
                    "path": "specs/tickets/01.md",
                    "before_blob_oid": self.spec_ticket_oid,
                    "after_blob_oid": bad_oids["specs/tickets/01.md"],
                }
            ],
        )
        self.assert_rejected(self.invoke(bad_payload), "definition-index.json")

        # Updating .dag/definition-index.json with the new blob OID succeeds.
        old_index_oid = self.git(
            "rev-parse", f"{bad_commit}:.dag/definition-index.json"
        )
        new_index_text = (
            json.dumps(
                {
                    "schema_version": 1,
                    "inputs": [
                        {
                            "path": "docs/agents/issue-tracker.md",
                            "blob_oid": self.rule_oid,
                        },
                        {
                            "path": "specs/tickets/01.md",
                            "blob_oid": bad_oids["specs/tickets/01.md"],
                        },
                    ],
                },
                indent=2,
            )
            + "\n"
        )
        good_commit, good_tree, good_oids = self.create_candidate_commit(
            {".dag/definition-index.json": new_index_text},
            parent_commit=bad_commit,
        )
        # Checkpoint range from self.base_commit to good_commit updates both paths:
        good_payload = self.checkpoint_payload(
            policy_key=policy_key,
            base_commit=self.base_commit,
            base_tree=self.base_tree,
            candidate_commit=good_commit,
            candidate_tree=good_tree,
            blob_changes=[
                {
                    "path": ".dag/definition-index.json",
                    "before_blob_oid": old_index_oid,
                    "after_blob_oid": good_oids[".dag/definition-index.json"],
                },
                {
                    "path": "specs/tickets/01.md",
                    "before_blob_oid": self.spec_ticket_oid,
                    "after_blob_oid": bad_oids["specs/tickets/01.md"],
                },
            ],
        )
        ok = self.invoke(good_payload)
        self.assertEqual(ok.returncode, 0, ok.stderr)


if __name__ == "__main__":
    unittest.main()
