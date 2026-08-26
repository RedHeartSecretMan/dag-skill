# Changelog

本文件记录每个已发布 tag 的用户可见变化，格式参考 Keep a Changelog。

## [Unreleased]

### Changed

- 统一主 Agent（Coordinator Agent）、执行 Agent 和审查 Agent 三种角色的命名、责任与实例边界，并将 Standards/Spec 明确为审查轴。
- 正式返工后的 DAG Revision 以失败原因和 Structural Progress 为准入依据，识别 Equivalent Revision，并根据一个完整目标或多个独立可验收结果选择替换 Ticket 或子图。
- DAG Revision 由交付契约和依赖证据触发，代码差异大小用于审查范围，新增公开验收入口用于完善 Ticket 契约；Split Independence Gate 支持原子验收目标的前置—消费者结构并确保父验收责任唯一归属。
- 修图次数作为审计证据，授权条件追溯至用户指令或目标项目规范；`Stalled` 只在没有可执行节点、运行中 Agent、获授权的恢复方式和可行的结构进展路径时成立。

## [0.1.1] - 2026-08-25

### Changed

- Ticket Worker Protocol 以 public-seam TDD 实施 Ticket，在固定 Review Candidate 上取得独立 Standards/Spec 报告，并以 RED→GREEN 关闭成立的 finding 后交付 Final Candidate 或带证据的 blocker。
- 主 Agent 通过 Review Sufficiency Gate 采用仍覆盖最终候选的 Worker 证据、补充定向审查或执行完整 fresh review；Formal Rework 从 Implementation Handoff gate 通过后开始计算。
- 入口检查、Operational Recovery、Operational Blocker、DAG Revision 与 `Stalled` 采用基于原因、有效进展和 Structural Progress 的统一推进条件。
- Git 项目使用独立 DAG Integration Branch、主 Agent worktree 及 ticket-scoped branch/worktree；候选经过串行对齐、集成门禁、固定身份审查和 fast-forward 晋级形成 DAG Milestone。
- 一次 Remote Checkpoint Authorization 覆盖每个 DAG Milestone 的选定 DAG 分支推送与远端 SHA 回读，并在恢复期间保留本地已验证里程碑和并行 Ticket 进展。
- Runtime Skill Bundle 固定 `code-review`、`tdd` 和 `codebase-design`，同 revision 的 `setup-matt-pocock-skills` 为需要配置的目标项目提供用户调用入口。
- Python 3.12+ 安装器使用固定目录摘要离线验证现有支持包，仅为缺失目录获取上游内容，以排他方式写入新路径，并在成功返回前复核全部四个目录。
- README 按任务的实际推进顺序解释启动信息、单票闭环、Git 隔离、返工、授权和终态，并为必要术语提供直白定义。

## [0.1.0] - 2026-08-24

### Added

- 首次发布跨项目、跨 Agent 宿主的 Approved Spec-and-Ticket DAG 协调 Skill。
- 提供基于 live evidence 的持续 frontier 调度、角色隔离、独立评审、集成与 Whole-DAG Acceptance Gate。
- 提供 Ticket Attempt、Formal Rework 和 DAG Revision 的恢复与修图机制。
- 提供固定 Skill Bundle 的 Python 3.12+ 安装器。
- 提供项目使用指南、设计说明、领域词汇、可选宿主界面元数据和安装器回归测试。

[Unreleased]: https://github.com/RedHeartSecretMan/dag-skill/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/RedHeartSecretMan/dag-skill/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/RedHeartSecretMan/dag-skill/releases/tag/v0.1.0
