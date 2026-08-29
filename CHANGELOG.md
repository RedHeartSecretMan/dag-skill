# Changelog

本文件记录每个已发布 tag 的用户可见变化，格式参考 Keep a Changelog。

## [Unreleased]

## [0.3.0] - 2026-08-29

### Changed

- 将运行范围明确为 Git-backed Ticket DAG，与必需的 `code-review` fixed-point、非空 diff 和 commit-list 契约保持一致，不再声称存在未实现的 non-Git 推广路径。
- 将运行模型收敛为 Coordinator Agent 与单票端到端 Execution Agent 两个 DAG 角色；`code-review` 的 Standards 和可用时的 Spec 审查上下文属于其内部实现，不再由主 Agent 派发或管理生命周期。
- 将简单的单票实施行为直接固化为 Ticket 执行契约，移除 `$implement` 适配器及其等价 prompt 分支。
- 单票实现、门禁、候选提交、双轴审查和批准范围内的 finding 修复由同一执行责任持续闭环；以关闭 finding、候选变化、门禁修复或新边界证据定义可观察进展，不再使用固定修复次数。
- 执行 Agent 只返回 Ready for Acceptance、Needs Coordinator Decision 或 Externally Blocked；成功态同时覆盖已审查候选和由既有规则确定的完整 baseline-satisfaction 证据。
- 候选审查记录显式绑定 Base、candidate commit/tree、评估范围和 `code-review` 的完整双轴结果；每个 finding 必须有证据化处置，仍成立的阻断 finding 不得推广。
- Base drift 由主 Agent 显式签发最新 Accepted tip 作为新 Base；刷新后的候选必须从新 Base 派生并重新完成门禁和审查，推广采用 fast-forward-only 精确身份回读。
- 零差异 Ticket 只有在目标项目已有 baseline-satisfaction 契约时才能 Accepted 或 Superseded，否则返回准确的 current-state audit 或验收决策需求。
- 零差异验收在状态转移前串行回读 commit/tree 必须仍等于审计 Base；发生漂移时签发新 Base 并重跑空 diff、audit、门禁和所选发布模式检查。
- 本地 integration branch 创建或恢复时固定 Local-only 或 Remote-mirrored；选择远端同步时一次确定 configured remote 与 branch，启动时用普通 `git push -u` 从本地 tip 创建或快进对齐远端分支并回读。
- Remote-mirrored 的运行级授权覆盖该 integration branch 的创建、每个里程碑的普通 fast-forward push 和 SHA 回读；不逐票询问，也不扩展到 Ticket branch、`main`、PR、tag 或 release。
- 每个非空候选先推广到本地 integration branch，再同步远端；push 失败时保留 `pending remote sync`，完成同步前不 Accepted、不解锁后继、不开始下一票。丢响应最多自动重发一次并在重发前持久关闭自动 push；非快进只报告并等待对账，不 force push、不自动换 ref，也不触发 DAG Revision。
- DAG Milestone 明确定义为非空候选通过串行验收通道后形成的新 Accepted integration commit/tree；Ticket 候选、中间 commits、zero-diff Accepted 和 Superseded 都不产生新 Milestone。
- 恢复时对存活状态不明的旧写入者保留 claim 和工作区，以具名 owner 和可观察 recheck event 建立关闭条件；未形成静止交接前不派发替代写入者。
- 串行验收事务在入口最后核对图、候选证据和 Base，之后固定这些输入直至完成本地推广、所选远端同步和 Accepted；期间新到的图证据在事务后处理，不引入候选回滚或 force-push 分支。事务外替换已 claim Ticket 时，先确认写入者停止并保留证据，再原子记录 Superseded 与 close claim。
- 未决的 Needs Coordinator Decision 明确阻止 Stalled；完成选择后若只剩不可用的外部条件，才转换为带 owner 和 closing event 的 Externally Blocked。
- Run Receipt 必须保存在交付 ref 之外，避免验收记录制造未经候选审查的新提交或改变下一张票的 Base。
- `code-review` 能力改为 Ticket 派发时检查；有 Spec 来源时创建独立 Spec 上下文，确认无 Spec 时记录 skip 而不误判为能力缺失。固定支持包安装器保留为可选兼容工具。

## [0.2.0] - 2026-08-27

### Changed

- Ticket 在 claim 前通过最小完整的 Ticket Execution Contract Gate，明确验收责任、直接依赖产物、交付产物、acceptance-to-probe 映射、scope 和最终门禁；状态变化、等价分类和禁止结果仅在适用且有权威来源时加入。
- 初次实施和 Formal Rework 派发采用有限闭环：因果 TDD、最终门禁、一次完整只读 Worker review，以及最多一次即时修复和终止性的 Targeted Closure Review；首次探针已 GREEN 时按缺失行为、合同冲突或完整 baseline satisfaction 分流，零交付差异由 fresh Review Agents 直接完成 current-state review。
- Blocked Handoff 只允许当前 Attempt 定点续派一次；续派消耗状态、来源候选和关闭条件可恢复，仍有效的审查证据被复用，完整或定向审查都直接形成终止 Handoff。
- 主 Agent 在交接后采用 Worker review、补充 Targeted Formal Review 或取得完整 Formal Review；不同固定候选的只读审查可以并行，alignment、增量审查与裁决、promotion 和 Remote Checkpoint 保持串行。
- Delivery-affecting Change 与 Evidence-only Change 使用不同验证范围；固定候选、相关输入、门禁定义、执行环境和覆盖范围保持有效时，纯证据提交和 byte-preserving alignment 在验证增量后保留现有交付门禁与审查证据。
- 精简 Run Receipt 只索引当前里程碑和活动状态；pending Remote Checkpoint 阻止当前里程碑接受、依赖后继和下一次推广，同时允许图独立 Ticket 从最后已核验的 accepted tip 继续，并以 ref 相等终止仓库内 Accepted 状态所需的纯证据最终检查点。
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

[Unreleased]: https://github.com/RedHeartSecretMan/dag-skill/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/RedHeartSecretMan/dag-skill/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/RedHeartSecretMan/dag-skill/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/RedHeartSecretMan/dag-skill/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/RedHeartSecretMan/dag-skill/releases/tag/v0.1.0
