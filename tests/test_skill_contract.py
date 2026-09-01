from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "dag" / "SKILL.md"
CONTEXT = ROOT / "CONTEXT.md"
README = ROOT / "README.md"
DESIGN = ROOT / "docs" / "DESIGN.md"
CI = ROOT / ".github" / "workflows" / "ci.yml"
RUNTIME_SKILL_INSTALLER = (
    ROOT / "skill" / "dag" / "scripts" / "install_runtime_skills.py"
)
LEGACY_INSTALLER = ROOT / "skill" / "dag" / "scripts" / "install_dependencies.py"
DEFINITION_REFERENCE = ROOT / "skill" / "dag" / "references" / "definition-binding.md"
TRANSITION_REFERENCE = (
    ROOT / "skill" / "dag" / "references" / "integration-transitions.md"
)


class SkillContractTests(unittest.TestCase):
    def test_coordinator_owned_decisions_are_not_execution_outcomes(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        context = CONTEXT.read_text(encoding="utf-8")

        self.assertEqual(skill.count("return `Needs Coordinator Decision`"), 1)
        self.assertIn("record a Coordinator-owned unresolved decision", skill)
        self.assertIn(
            "Coordinator Agent 在自身流程中发现的未决决定不是 Execution Outcome",
            context,
        )

    def test_pending_transition_evidence_is_reused_or_explicitly_replaced(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        transitions = TRANSITION_REFERENCE.read_text(encoding="utf-8")

        self.assertNotIn("refreeze", skill)
        self.assertNotIn(
            "cancel the pending Integration Transition before local promotion",
            skill,
        )
        self.assertIn(
            "cancel the pending Integration Transition before local promotion",
            transitions,
        )
        self.assertIn("create and freeze a new Integration Transition", transitions)

    def test_checkpoint_becomes_ticket_base_only_after_completion(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")

        self.assertNotIn(
            "Refresh active Ticket ownership under the new Ticket Base", skill
        )
        self.assertIn("pause affected active Ticket ownership before promotion", skill)
        self.assertIn(
            "After the DAG Definition Checkpoint completes, assign its Accepted Integration Tip as the new Ticket Base",
            skill,
        )

    def test_bootstrap_docs_cover_all_recoverable_bundle_failures(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        readme = README.read_text(encoding="utf-8")

        self.assertIn("无法解析、缺失或固定身份不一致时运行安装器", readme)
        self.assertIn(
            "python3 <this-skill-root>/scripts/install_runtime_skills.py",
            skill,
        )
        self.assertIn(
            "python3 <this-skill-root>/scripts/install_runtime_skills.py",
            readme,
        )

    def test_runtime_skill_installer_has_one_public_path(self) -> None:
        self.assertTrue(RUNTIME_SKILL_INSTALLER.is_file())
        self.assertFalse(LEGACY_INSTALLER.exists())
        for document in (SKILL, README, DESIGN, CI):
            with self.subTest(document=document):
                self.assertNotIn(
                    "install_dependencies.py",
                    document.read_text(encoding="utf-8"),
                )

    def test_branch_contracts_are_reached_through_explicit_pointers(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        definition = DEFINITION_REFERENCE.read_text(encoding="utf-8")
        transitions = TRANSITION_REFERENCE.read_text(encoding="utf-8")

        self.assertIn("read and follow [`references/definition-binding.md`]", skill)
        self.assertIn("read [`references/integration-transitions.md`]", skill)
        self.assertIn("validate_definition_index.py", definition)
        self.assertIn("Frozen evidence is immutable", transitions)

    def test_execution_agent_dispatch_does_not_inherit_coordinator_history(
        self,
    ) -> None:
        skill = SKILL.read_text(encoding="utf-8")

        for document in (SKILL, README, DESIGN):
            content = document.read_text(encoding="utf-8")
            with self.subTest(document=document):
                self.assertNotIn("fork_turns", content)
                self.assertNotIn("Codex", content)
        self.assertIn("Agent Host's zero-history dispatch setting", skill)
        self.assertIn("default full-history inheritance", skill)

    def test_context_is_a_glossary_not_an_integration_ref_state_machine(self) -> None:
        context = CONTEXT.read_text(encoding="utf-8")

        self.assertNotIn("首次 acceptance 前且无 pending", context)
        self.assertNotIn("pending Integration Transition 不会提前改变它", context)

    def test_readme_single_ticket_sequence_preserves_acceptance_order(self) -> None:
        readme = README.read_text(encoding="utf-8")

        self.assertIn("sequenceDiagram", readme)
        self.assertIn("以零历史或最小历史派发固定 Ticket contract", readme)
        self.assertIn("重新执行 candidate-bound review", readme)
        ticket_loop = readme.index("单票执行默认在 Ticket 内闭环")
        outcomes = readme.index("| `Ready for Acceptance`")
        handoff_ownership = readme.index("交接结果，不是 Ticket 状态")
        sequence = readme.index("sequenceDiagram")
        self.assertLess(ticket_loop, outcomes)
        self.assertLess(outcomes, handoff_ownership)
        self.assertLess(handoff_ownership, sequence)
        sequence_intro = readme[handoff_ownership:sequence]
        self.assertIn("`Ready for Acceptance`", sequence_intro)
        self.assertIn("`Promotion Candidate`", sequence_intro)
        self.assertIn(
            "`Promotion Candidate` 或 `Baseline Satisfaction` 的证据已完整",
            readme,
        )
        self.assertIn("只有 `Coordinator Agent` 负责记录验收和图状态变更", readme)
        self.assertIn(
            "才由 `Coordinator Agent` 按 `Target Project` 的规则发起 `DAG Revision`",
            readme,
        )
        local_cas = readme.index("C->>I: 原子 CAS 推进 integration ref")
        remote_readback = readme.index("M-->>C: 回读精确 candidate SHA")
        accepted = readme.index("C->>C: 记录 Accepted Ticket、关闭 claim")
        self.assertLess(local_cas, remote_readback)
        self.assertLess(remote_readback, accepted)


if __name__ == "__main__":
    unittest.main()
