# Changelog

本文件记录每个已发布 tag 的用户可见变化，格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

### Changed

- 默认 `README.md` 改为英文，中文版移至 `README_ZH.md`，语言切换文字使用“简体中文”。
- 派发契约携带适用于当前及下游 Agent 的用户与项目约束，以及已有批准的指针；Runtime Skill 调用和后续派发继续遵守这些约束。
- Runtime Skill 调用优先使用 Target Project 已有的权威 Ticket、Spec 和 tracker 流程；仅缺少依赖约定的文档路径不要求项目配置，已有测试 seam 批准在原范围内复用。
- `setup-matt-pocock-skills` 仅由明确的安装请求或使用它完成已授权项目配置的需要触发安装；Coordinator 沿用已有授权补齐缺失副本，仅安装不授权执行配置。

### Fixed

- 单次诊断未取得交付变化时，只要还有获授权的诊断或修复路径，Execution Agent 就继续处理；停止重复失败操作不再自动触发不适用的 Execution Outcome。
- Definition Index 中超出 Python 整数解析限制的 JSON 数值现在按约定返回 `error: ...` 和非零退出码，不再输出 traceback。

## [0.4.1] - 2026-09-02

### Changed

- 将 `Needs Coordinator Decision` Execution Outcome 重命名为 `Needs Decision`，不保留旧名称；`Coordinator Agent` 仍负责在现有权限内处理，超出权限时交由用户决定。
- README 直接说明 `Promotion Candidate` 正常时序覆盖单票执行、`Ready for Acceptance` 交接和 Ticket 验收。
- README 只保留一张逐票 sequence diagram，按实际时序展示最小 Ticket context、Ticket 内 candidate/review 闭环、串行 promotion、可选 tracker checkpoint 和后继解锁。

### Fixed

- `Execution Agent` 派发现在显式使用 `Agent Host` 的零历史能力，不支持时采用排除无关 Ticket、`Run Receipt` 和既有工具输出的最小历史窗口。
- Git-tracked tracker 更新现在先结束当前验收或 `Integration Transition`，再以 pending update 和下一次 typed `DAG Definition Checkpoint` Transition 恢复；只有未选中的稳定审计路径可以保持 Definition identities，selected path 变化必须重绑 index 并完成验收影响审计。
- 项目没有规定 `Accepted`、`Superseded` 或 `PASS`/`FAIL`/`BLOCKED` 到 tracker 字段的映射时，Coordinator 保留未决决定；必需更新完成前不解锁依赖工作，也不报告 `Complete`。

## [0.4.0] - 2026-09-01

### Added

- 首张 Ticket 前绑定 DAG Definition：项目内 Spec/Tickets 进入集成历史，外部 tracker 使用包含完整计划内容和来源身份的规范化快照，固定的 `.dag/definition-index.json` 作为唯一 DAG Definition Index；Starting Base 或当前 Accepted Integration Tip 已包含相同定义和等价 index 时只验证身份。
- DAG Definition Checkpoint 作为非 Ticket 的受审查 commit/tree，通过 Integration Transition 复用串行 CAS、Remote-mirrored 同步和 SHA 回读，并在成功后成为后续 Ticket Base。
- 新增只读 `validate_definition_index.py`：只使用指定 commit 的本地 Git objects，禁用 replace refs 和 partial-clone lazy fetch，验证 canonical JSON、NFC 安全路径、UTF-8 字节序、Git blob 身份与模式，并准确拒绝 canonical/legacy Git LFS pointer、symlink 和 gitlink；新增对应 integration tests。
- 新增 Definition binding 与 Integration Transition branch references，让主 SKILL 保留常规步骤和完成条件，按运行分支披露 schema、publication 与 recovery 细节。
- 新增只读 GitHub Actions CI，在 Python 3.12/3.14 上运行完整 tests、Ruff、Markdown lint 和两个 CLI help，并以精确 commit 固定官方 checkout/setup-python Actions。

### Changed

- 将计划与运行状态显式分离：Run Receipt、claim、Agent、worktree、liveness 和 pending sync 保持 off-delivery；混合路径必须拆分或生成排除运行状态的规范化快照。
- 开始或恢复时以 Run Receipt 对账本地 DAG Integration Branch ref；Promotion Candidate 必须保持已绑定的 DAG Definition 字节不变并排除瞬态运行状态，计划变更只通过 DAG Definition Checkpoint 进入历史。
- DAG Revision 必须重新处置受影响的 Accepted Ticket 和 Superseded Ticket 证据：fresh audit 证明新 Acceptance Obligation 仍满足，或按 Target Project 规则重开/转交给有效 Ticket；旧证据不能自动沿用。
- DAG Definition Checkpoint 的 acceptance-impact dispositions 与 audit 身份在本地 CAS 前随 typed pending Integration Transition 一起冻结；崩溃恢复只能采用同一证据集，CAS 前证据变化必须显式取消旧 Transition 并新建。
- Remote-mirrored 的运行级授权和恢复对账同时覆盖 DAG Milestones 与 DAG Definition Checkpoints；普通运行状态变化不会创建 DAG Definition Checkpoint，也不改变 Execution Agent 的接口。
- README、SKILL 和 DESIGN 统一使用 CONTEXT 中的 canonical terms；CONTEXT 新增 Agent Host，删除与 Integration Transition 重叠的串行验收别名，并保留英文术语配中文定义。
- Coordinator 自身发现的未决选择不再冒充 Execution Outcome；Checkpoint 候选完成前不再成为 Ticket Base；pending Transition 的冻结证据变化改为 CAS 前显式取消并新建，禁止原地替换。
- Runtime Skill Bundle 的 README 恢复条件覆盖无法解析、缺失和固定身份不一致；安装器示例统一以 `<this-skill-root>` 指向实际复制目录。
- 将公开安装入口从 `scripts/install_dependencies.py` 重命名为 `scripts/install_runtime_skills.py`，直接表达其默认只安装 Runtime Skills，同时保留显式 opt-in setup helper；旧路径不再保留。
- Execution Agent 派发改为 Agent Host 中立的零历史契约；不支持零历史时仅继承排除无关 Ticket、Run Receipt 和既有工具输出的最小窗口。
- Definition Index validator 先定点读取 index，再批量查询其选择的路径，不再枚举整个 commit tree。

## [0.3.1] - 2026-08-29

### Changed

- 每次开始或恢复 DAG 时只检查一次 `tdd`、`codebase-design` 和 `code-review`；无法解析或固定身份不一致时默认运行安装器，让 Agent Host 重新加载 Skill 列表并确认三项都能解析，后续 Tickets 不再重复检查。
- 安装器默认只处理三个 Runtime Skills，继续保留冲突预检和不覆盖保证；`setup-matt-pocock-skills` 改为仅通过 `--include-setup-helper` 显式安装。
- DAG 不再解释 `$code-review` 内部如何发现 Spec 或组织审查，只保存它返回的完整结果并绑定 Base、candidate commit/tree 和评估范围。
- 本地 DAG 集成分支改为不签出到 worktree 的 ref，推广使用 Base 到 Candidate 的原子比较更新；换 Agent 时必须先确认原 Agent 已停止，再交接原 Ticket、branch、worktree 和 WIP。
- 远端模式在首张 Ticket 前一次确定；新映射只初始化一次，恢复已有映射先只读对账；里程碑同步改为比较 Candidate、上次同步 commit 与远端 SHA，不再保留重发计数或额外自动 push 状态。
- README 改用启动、派票、验收和远端处理的直白流程说明。

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
- DAG Milestone 明确定义为非空候选串行完成本地推广、所选远端同步和 Accepted 后形成的新 integration commit/tree；Ticket 候选、中间 commits、zero-diff Accepted 和 Superseded 都不产生新 Milestone。
- 恢复时对存活状态不明的旧写入者保留 claim 和工作区，以具名 owner 和可观察 recheck event 建立关闭条件；未形成静止交接前不派发替代写入者。
- 候选在串行推广入口最后核对图、候选证据和 Base，之后固定这些输入直至完成本地推广、所选远端同步和 Accepted；期间新到的图证据在完成后处理，不引入候选回滚或 force-push 分支。推广前替换已 claim Ticket 时，先确认写入者停止并保留证据，再原子记录 Superseded 与 close claim。
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

[Unreleased]: https://github.com/RedHeartSecretMan/dag-skill/compare/v0.4.1...HEAD
[0.4.1]: https://github.com/RedHeartSecretMan/dag-skill/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/RedHeartSecretMan/dag-skill/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/RedHeartSecretMan/dag-skill/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/RedHeartSecretMan/dag-skill/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/RedHeartSecretMan/dag-skill/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/RedHeartSecretMan/dag-skill/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/RedHeartSecretMan/dag-skill/releases/tag/v0.1.0
