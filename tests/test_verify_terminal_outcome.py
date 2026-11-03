from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill" / "dag" / "scripts" / "verify_terminal_outcome.py"
POLICY_SCRIPT = ROOT / "skill" / "dag" / "scripts" / "record_tracker_policy.py"
CHECKPOINT_SCRIPT = ROOT / "skill" / "dag" / "scripts" / "record_tracker_checkpoint.py"
PROMOTE_SCRIPT = ROOT / "skill" / "dag" / "scripts" / "promote_local_transition.py"


class TerminalOutcomeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.off_delivery = self.root / "off-delivery"
        self.off_delivery.mkdir()
        self.receipt = self.off_delivery / "receipt.json"
        self.audit = self.off_delivery / "audit.json"
        self.authority = self.off_delivery / "authority.json"
        self.authority.write_text("authoritative snapshot\n", encoding="utf-8")
        self.disp_evidence = self.off_delivery / "disp-evidence.txt"
        self.disp_evidence.write_text("disposition evidence\n", encoding="utf-8")
        self.review_evidence = self.off_delivery / "checkpoint-review.md"
        self.review_evidence.write_text("checkpoint review ok\n", encoding="utf-8")
        self.output = self.off_delivery / "terminal" / "evidence.json"
        self.output.parent.mkdir()
        self.integration_ref = "refs/heads/codex/dag-integration"
        self.init_repo()
        self.setup_run(mode="none")
        self.write_audit(
            "Complete", tip_commit=self.base_commit, tip_tree=self.base_tree
        )

    @staticmethod
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

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
        (self.repo / "docs").mkdir()
        (self.repo / "specs").mkdir()
        (self.repo / ".scratch" / "issues").mkdir(parents=True)
        (self.repo / ".dag" / "snapshots").mkdir(parents=True)

        rule = self.repo / "docs" / "tracker.md"
        rule.write_text("# Tracker rule\n", encoding="utf-8")
        spec = self.repo / "specs" / "ticket-1.md"
        spec.write_text("# Ticket 1 spec\n", encoding="utf-8")
        tracker = self.repo / ".scratch" / "issues" / "ticket-1.md"
        tracker.write_text("Open ticket.\n", encoding="utf-8")
        snapshot = self.repo / ".dag" / "snapshots" / "tracker.json"
        snapshot.write_text('{"ticket-1":"open"}\n', encoding="utf-8")

        self.rule_oid = self.git("hash-object", "-w", str(rule))
        self.spec_oid = self.git("hash-object", "-w", str(spec))
        self.tracker_oid = self.git("hash-object", "-w", str(tracker))
        self.snapshot_oid = self.git("hash-object", "-w", str(snapshot))
        (self.repo / ".dag" / "definition-index.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "inputs": [
                        {"path": "docs/tracker.md", "blob_oid": self.rule_oid},
                        {"path": "specs/ticket-1.md", "blob_oid": self.spec_oid},
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        self.git("add", ".")
        self.git("commit", "-q", "-m", "initial")
        self.base_commit = self.git("rev-parse", "HEAD")
        self.base_tree = self.git("rev-parse", "HEAD^{tree}")
        self.git("update-ref", self.integration_ref, self.base_commit)
        self.git("checkout", "-q", "--detach", self.base_commit)

    def disposition_entry(
        self,
        ticket_id: str = "ticket-1",
        disposition: str = "Accepted",
        claim_generation: int = 1,
    ) -> dict[str, object]:
        return {
            "schema_version": 1,
            "kind": "Ticket Disposition",
            "run_id": "run-1",
            "coordinator_generation": 1,
            "ticket_id": ticket_id,
            "claim_generation": claim_generation,
            "disposition": disposition,
            "rule_identity": "rule:v1",
            "decided_by": "coordinator",
            "decided_at": "2026-11-03T10:00:00Z",
            "rationale": "Disposition recorded.",
            "evidence_refs": [
                {
                    "id": "disp-evidence",
                    "path": str(self.disp_evidence),
                    "sha256": self.digest(self.disp_evidence),
                }
            ],
            "promotion_evidence_sha256": (
                "1" * 64 if disposition == "Accepted" else None
            ),
            "baseline_evidence_sha256": None,
            "ticket_base": {"commit": self.base_commit, "tree": self.base_tree},
            "claim_owner_id": "agent-1",
        }

    def write_legacy_receipt(
        self,
        *,
        claims: list[dict[str, object]] | None = None,
        dispositions: list[dict[str, object]] | None = None,
    ) -> None:
        payload: dict[str, object] = {
            "schema_version": 1,
            "kind": "Run Receipt",
            "run_id": "run-1",
            "coordinator_generation": 8,
            "integration_ref": self.integration_ref,
            "claims": claims or [],
            "execution_records": [],
        }
        if dispositions is not None:
            payload["ticket_dispositions"] = dispositions
        self.receipt.write_text(
            json.dumps(payload, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def record_policy(
        self, mode: str, *, suffix: str = "default", rationale: str | None = None
    ) -> str:
        receipt_data = json.loads(self.receipt.read_text(encoding="utf-8"))
        generation = receipt_data["coordinator_generation"]
        if mode == "none":
            auth_paths: list[str] = []
            tracker_paths: list[str] = []
            scope = "none"
        elif mode == "external_snapshot":
            auth_paths = [".dag/snapshots"]
            tracker_paths = [".dag/snapshots/tracker.json"]
            scope = "per_ticket"
        else:
            auth_paths = [".scratch"]
            tracker_paths = [".scratch/issues/ticket-1.md"]
            scope = "per_ticket"
        policy_path = self.off_delivery / f"policy-{mode}-{suffix}.json"
        record_path = self.off_delivery / f"policy-record-{mode}-{suffix}.json"
        policy_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Tracker Policy",
                    "run_id": "run-1",
                    "mode": mode,
                    "authoritative_paths": auth_paths,
                    "rule_refs": [
                        {
                            "id": "tracker-rule",
                            "path": "docs/tracker.md",
                            "identity": self.rule_oid,
                        }
                    ],
                    "definition_paths": ["docs/tracker.md", "specs/ticket-1.md"],
                    "tracker_paths": tracker_paths,
                    "update_scope": scope,
                    "rationale": rationale or f"Policy mode {mode}.",
                    "stateful_tracker_decision": None,
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        res = subprocess.run(
            [
                sys.executable,
                str(POLICY_SCRIPT),
                "--receipt",
                str(self.receipt),
                "--policy",
                str(policy_path),
                "--output",
                str(record_path),
                "--expected-generation",
                str(generation),
                "--expected-receipt-sha256",
                self.digest(self.receipt),
                "--repository",
                str(self.repo),
                "--commit",
                self.base_commit,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return str(json.loads(res.stdout)["policy_key"])

    def setup_run(
        self,
        *,
        mode: str,
        with_checkpoint: bool = False,
        suffix: str = "init",
    ) -> tuple[str, str]:
        self.git("update-ref", self.integration_ref, self.base_commit)
        self.write_legacy_receipt(dispositions=[self.disposition_entry()])
        policy_key = self.record_policy(mode, suffix=suffix)
        if not with_checkpoint:
            return self.base_commit, self.base_tree
        rel_path = (
            ".dag/snapshots/tracker.json"
            if mode == "external_snapshot"
            else ".scratch/issues/ticket-1.md"
        )
        before_oid = (
            self.snapshot_oid if mode == "external_snapshot" else self.tracker_oid
        )
        new_content = (
            '{"ticket-1":"closed-with-evidence"}\n'
            if mode == "external_snapshot"
            else "Ticket-1 已验收完成，附回归证据。\n"
        )
        return self.promote_and_record_tracker_checkpoint(
            policy_key=policy_key,
            base_commit=self.base_commit,
            base_tree=self.base_tree,
            rel_path=rel_path,
            before_oid=before_oid,
            new_content=new_content,
            suffix=suffix,
        )

    def promote_and_record_tracker_checkpoint(
        self,
        *,
        policy_key: str,
        base_commit: str,
        base_tree: str,
        rel_path: str,
        before_oid: str,
        new_content: str,
        suffix: str,
    ) -> tuple[str, str]:
        self.git("checkout", "-q", "--detach", base_commit)
        target = self.repo / rel_path
        target.write_text(new_content, encoding="utf-8")
        after_oid = self.git("hash-object", "-w", str(target))
        self.git("add", rel_path)
        self.git("commit", "-q", "-m", f"tracker {suffix}")
        commit = self.git("rev-parse", "HEAD")
        tree = self.git("rev-parse", "HEAD^{tree}")

        transition = self.off_delivery / f"transition-{suffix}.json"
        transition.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "candidate_kind": "DAG Definition Checkpoint",
                    "integration_ref": self.integration_ref,
                    "base": base_commit,
                    "candidate": commit,
                    "candidate_tree": tree,
                    "evidence": [
                        {
                            "path": self.review_evidence.name,
                            "sha256": self.digest(self.review_evidence),
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
                "--sha256",
                self.digest(transition),
            ],
            capture_output=True,
            check=True,
        )
        generation = json.loads(self.receipt.read_text(encoding="utf-8"))[
            "coordinator_generation"
        ]
        cp_file = self.off_delivery / f"cp-{suffix}.json"
        cp_record = self.off_delivery / f"cp-record-{suffix}.json"
        cp_file.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "Tracker Checkpoint",
                    "run_id": "run-1",
                    "coordinator_generation": generation,
                    "policy_key": policy_key,
                    "integration_ref": self.integration_ref,
                    "ticket_dispositions": [
                        {
                            "ticket_id": "ticket-1",
                            "claim_generation": 1,
                            "disposition": "Accepted",
                        }
                    ],
                    "base": {"commit": base_commit, "tree": base_tree},
                    "candidate": {"commit": commit, "tree": tree},
                    "changed_paths": [rel_path],
                    "blob_changes": [
                        {
                            "path": rel_path,
                            "before_blob_oid": before_oid,
                            "after_blob_oid": after_oid,
                        }
                    ],
                    "evidence_refs": [
                        {
                            "id": "review",
                            "path": str(self.review_evidence),
                            "sha256": self.digest(self.review_evidence),
                        }
                    ],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(CHECKPOINT_SCRIPT),
                "--repository",
                str(self.repo),
                "--receipt",
                str(self.receipt),
                "--checkpoint",
                str(cp_file),
                "--output",
                str(cp_record),
                "--expected-generation",
                str(generation),
                "--expected-receipt-sha256",
                self.digest(self.receipt),
            ],
            capture_output=True,
            check=True,
        )
        return commit, tree

    def write_audit(
        self,
        outcome: str,
        *,
        tip_commit: str | None = None,
        tip_tree: str | None = None,
        obligations: list[dict[str, object]] | None = None,
    ) -> None:
        commit = tip_commit or self.base_commit
        tree = tip_tree or self.base_tree
        if outcome == "Complete":
            default_obligations: list[dict[str, object]] = [
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
            default_obligations = [
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
                    "accepted_tip": {"commit": commit, "tree": tree},
                    "authority_refs": [
                        {
                            "id": "definition-snapshot",
                            "path": str(self.authority),
                            "sha256": self.digest(self.authority),
                        }
                    ],
                    "obligations": (
                        default_obligations if obligations is None else obligations
                    ),
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

    def invoke(
        self,
        *,
        output: Path | None = None,
        tip_commit: str | None = None,
        tip_tree: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--receipt",
                str(self.receipt),
                "--audit",
                str(self.audit),
                "--expected-tip-commit",
                tip_commit or self.base_commit,
                "--expected-tip-tree",
                tip_tree or self.base_tree,
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

    def test_verifies_complete_across_none_in_repo_and_external_snapshot_modes(
        self,
    ) -> None:
        for mode, needs_cp in (
            ("none", False),
            ("in_repo", True),
            ("external_snapshot", True),
        ):
            with self.subTest(mode=mode):
                tip_commit, tip_tree = self.setup_run(
                    mode=mode, with_checkpoint=needs_cp, suffix=mode
                )
                out = self.off_delivery / "terminal" / f"complete-{mode}.json"
                self.write_audit("Complete", tip_commit=tip_commit, tip_tree=tip_tree)
                first = self.invoke(
                    output=out, tip_commit=tip_commit, tip_tree=tip_tree
                )
                self.assertEqual(first.returncode, 0, first.stderr)
                evidence = json.loads(out.read_text(encoding="utf-8"))
                self.assertEqual(evidence["outcome"], "Complete")
                self.assertTrue(evidence["verified"])
                second = self.invoke(
                    output=out, tip_commit=tip_commit, tip_tree=tip_tree
                )
                self.assertEqual(
                    json.loads(second.stdout)["status"], "already-published"
                )

    def test_verifies_stalled_with_no_progress_paths(self) -> None:
        self.write_legacy_receipt()
        self.write_audit("Stalled")
        output = self.off_delivery / "terminal" / "stalled.json"
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
        self.write_legacy_receipt(
            claims=[
                {
                    "ticket_id": "ticket-1",
                    "claim_generation": 1,
                }
            ]
        )
        self.assert_rejected(self.invoke(), "live claims remain")

    def test_rejects_stalled_with_runnable_work(self) -> None:
        self.write_legacy_receipt()
        self.write_audit("Stalled")
        audit = json.loads(self.audit.read_text(encoding="utf-8"))
        audit["runnable_tickets"] = ["ticket-2"]
        self.audit.write_text(json.dumps(audit), encoding="utf-8")

        self.assert_rejected(self.invoke(), "Stalled cannot have runnable_tickets")

    def test_rejects_stalled_with_pending_tracker_update(self) -> None:
        self.write_legacy_receipt()
        self.write_audit("Stalled")
        audit = json.loads(self.audit.read_text(encoding="utf-8"))
        audit["pending_tracker_updates"] = ["ticket-1"]
        self.audit.write_text(json.dumps(audit), encoding="utf-8")

        self.assert_rejected(
            self.invoke(), "Stalled cannot have pending_tracker_updates"
        )

    def test_rejects_complete_when_tracker_checkpoint_missing_even_if_audit_claims_none_pending(
        self,
    ) -> None:
        for mode in ("in_repo", "external_snapshot"):
            with self.subTest(mode=mode):
                tip_commit, tip_tree = self.setup_run(
                    mode=mode, with_checkpoint=False, suffix=f"missing-{mode}"
                )
                self.write_audit("Complete", tip_commit=tip_commit, tip_tree=tip_tree)
                # Audit claims pending_tracker_updates=[] while receipt has pending updates.
                self.assert_rejected(
                    self.invoke(tip_commit=tip_commit, tip_tree=tip_tree),
                    "pending_tracker_updates",
                )
                # Even if receipt.pending_tracker_updates were manually cleared, missing checkpoint rejects!
                receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
                receipt["pending_tracker_updates"] = []
                self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
                self.assert_rejected(
                    self.invoke(tip_commit=tip_commit, tip_tree=tip_tree),
                    "Tracker Checkpoint",
                )

    def test_rejects_complete_when_policy_checkpoint_or_evidence_is_missing_and_upgrades_legacy_receipt(
        self,
    ) -> None:
        # Legacy receipt without tracker_policy rejects Complete, then succeeds after upgrade.
        self.write_legacy_receipt(dispositions=[self.disposition_entry()])
        self.write_audit("Complete")
        self.assert_rejected(self.invoke(), "Tracker Policy")

        policy_key = self.record_policy("in_repo", suffix="legacy-upgrade")
        tip_commit, tip_tree = self.promote_and_record_tracker_checkpoint(
            policy_key=policy_key,
            base_commit=self.base_commit,
            base_tree=self.base_tree,
            rel_path=".scratch/issues/ticket-1.md",
            before_oid=self.tracker_oid,
            new_content="Upgraded legacy receipt tracker state.\n",
            suffix="legacy-upgrade",
        )
        self.write_audit("Complete", tip_commit=tip_commit, tip_tree=tip_tree)
        upgraded_out = self.off_delivery / "terminal" / "upgraded.json"
        ok = self.invoke(output=upgraded_out, tip_commit=tip_commit, tip_tree=tip_tree)
        self.assertEqual(ok.returncode, 0, ok.stderr)

        # Deleting the review evidence referenced by the Tracker Checkpoint rejects Complete.
        saved_review = self.review_evidence.read_bytes()
        self.review_evidence.unlink()
        self.assert_rejected(
            self.invoke(
                output=self.off_delivery / "terminal" / "missing-ev.json",
                tip_commit=tip_commit,
                tip_tree=tip_tree,
            ),
            "could not be read",
        )
        self.review_evidence.write_bytes(saved_review)

        # Deleting the Tracker Checkpoint record file rejects Complete.
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        cp_record_path = Path(receipt["tracker_checkpoints"][0]["record_path"])
        cp_record_path.unlink()
        self.assert_rejected(
            self.invoke(
                output=self.off_delivery / "terminal" / "missing-cp.json",
                tip_commit=tip_commit,
                tip_tree=tip_tree,
            ),
            "could not be read",
        )

    def test_rejects_stale_policy_and_stale_checkpoint_candidate_vs_final_tip(
        self,
    ) -> None:
        tip_commit, tip_tree = self.setup_run(
            mode="in_repo", with_checkpoint=True, suffix="stale-check"
        )
        # Tip moves after the last Tracker Checkpoint -> stale checkpoint!
        self.git("checkout", "-q", "--detach", tip_commit)
        (self.repo / "code.py").write_text("x = 1\n", encoding="utf-8")
        self.git("add", "code.py")
        self.git("commit", "-q", "-m", "post-checkpoint code commit")
        later_commit = self.git("rev-parse", "HEAD")
        later_tree = self.git("rev-parse", "HEAD^{tree}")
        self.write_audit("Complete", tip_commit=later_commit, tip_tree=later_tree)
        self.assert_rejected(
            self.invoke(tip_commit=later_commit, tip_tree=later_tree),
            "Accepted Integration Tip",
        )

        # Policy updated after Tracker Checkpoint without a new checkpoint -> stale policy!
        self.record_policy(
            "in_repo", suffix="stale-policy-v2", rationale="New policy rationale."
        )
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        receipt["pending_tracker_updates"] = []
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        self.write_audit("Complete", tip_commit=tip_commit, tip_tree=tip_tree)
        self.assert_rejected(
            self.invoke(tip_commit=tip_commit, tip_tree=tip_tree),
            "stale policy",
        )

    def test_rejects_mismatched_dispositions_and_terminal_obligations(self) -> None:
        self.setup_run(mode="none", suffix="mismatch")
        # Status mismatch: Receipt has Accepted, audit claims Superseded.
        self.write_audit(
            "Complete",
            obligations=[
                {
                    "id": "obligation-1",
                    "owner": "ticket-1",
                    "status": "Superseded",
                    "evidence_applicable": True,
                }
            ],
        )
        self.assert_rejected(self.invoke(), "disposition")

        # Extra obligation with no recorded Ticket disposition in Receipt.
        self.write_audit(
            "Complete",
            obligations=[
                {
                    "id": "obligation-1",
                    "owner": "ticket-1",
                    "status": "Accepted",
                    "evidence_applicable": True,
                },
                {
                    "id": "obligation-2",
                    "owner": "ticket-2",
                    "status": "Accepted",
                    "evidence_applicable": True,
                },
            ],
        )
        self.assert_rejected(self.invoke(), "disposition")

        # Duplicate ticket mapping in obligations violates 1-to-1 correspondence.
        self.write_audit(
            "Complete",
            obligations=[
                {
                    "id": "obligation-1a",
                    "owner": "ticket-1",
                    "status": "Accepted",
                    "evidence_applicable": True,
                },
                {
                    "id": "obligation-1b",
                    "owner": "ticket-1",
                    "status": "Accepted",
                    "evidence_applicable": True,
                },
            ],
        )
        self.assert_rejected(self.invoke(), "one-to-one")

        # Extra Ticket disposition in Receipt missing from terminal obligations.
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        receipt["ticket_dispositions"].append(
            self.disposition_entry(ticket_id="ticket-2", disposition="Superseded")
        )
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        self.write_audit("Complete")
        self.assert_rejected(self.invoke(), "terminal obligations")


if __name__ == "__main__":
    unittest.main()
