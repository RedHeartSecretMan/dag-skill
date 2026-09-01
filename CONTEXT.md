# DAG 协调

术语名称使用英文，定义使用中文。README、Skill 和运行证据应使用统一的术语。

## 项目与计划

**Target Project**:
一次 DAG 运行所作用的 Git 项目；其指令、Spec、Tickets、tracker 和验收规则共同决定本次运行的权威事实。
_Avoid_: DAG Skill 仓库、聊天快照

**Approved DAG**:
已经获得用户批准、由多个 Ticket 和 Hard Dependency 组成的无环交付图。
_Avoid_: 草案、自动生成的待办列表

**DAG Definition**:
决定 Approved DAG 的完整计划，包括起约束作用的 Spec、有效 Tickets、Hard Dependencies 和 Acceptance Obligations。
_Avoid_: 未跟踪计划、聊天摘要、Run Receipt

**DAG Definition Index**:
在 Git 历史中唯一选择本次 DAG Definition 输入及其内容身份的已跟踪选择器。
_Avoid_: Run Receipt 指针、隐式最新版本、项目自定义别名

**Ticket**:
一个具有独立 Acceptance Obligation、可以单独验收的交付单元。
_Avoid_: prompt、重试轮次、实现阶段

**Acceptance Obligation**:
一个 Ticket 必须满足的外部可观察结果及其验收证据责任。
_Avoid_: 实现任务、文件归属

**Hard Dependency**:
后继 Ticket 必须消费前置 Ticket 的 Accepted 输出时形成的有向依赖。
_Avoid_: 偏好顺序、共享文件关系

**DAG Revision**:
由现场证据支持、会改变有效 Tickets、Hard Dependencies 或 Acceptance Obligations 的计划修订。
_Avoid_: 审查修复、候选重试、仅重命名

## 状态与执行

**Accepted Ticket**:
Acceptance Obligation 已由有效证据满足，并完成所选 Integration Publication Mode 要求的 Ticket。
_Avoid_: 实现完成、候选已就绪、本地已提交

**Superseded Ticket**:
已按批准规则退出有效 DAG，且其 Acceptance Obligation 已被证明满足或明确转交给其他有效 Ticket 的 Ticket。
_Avoid_: 放弃的 Ticket、隐藏失败

**Runnable Frontier**:
Hard Dependencies、阻塞条件、执行权限和写入边界均已满足，当前可以认领的开放 Tickets。
_Avoid_: ready 标签、所有未认领 Tickets

**Coordinator Agent**:
唯一负责现场对账、图状态、调度、认领、验收、Integration Transition 和后继解锁的 Agent。
_Avoid_: 实现者、重复 Coordinator Agent、审查者

**Execution Agent**:
在一个 Ticket 内持续负责实现、验证、Promotion Candidate、审查 finding 闭环并返回一个 Execution Outcome 的 Agent。
_Avoid_: DAG 调度者、验收决策者

**Agent Host**:
承载 Coordinator Agent 和 Execution Agent，并决定可解析 Skills 与可用运行能力的宿主环境。
_Avoid_: Agent 实例、Target Project、Skills root

**Runtime Skill Bundle**:
DAG 运行固定依赖的 `tdd`、`codebase-design` 和 `code-review` 三项能力。
_Avoid_: 可选安装辅助 Skill、每个 Ticket 各自安装的依赖

**Execution Outcome**:
Execution Agent 返回给 Coordinator Agent 的结果，只能是 Ready for Acceptance、Needs Coordinator Decision 或 Externally Blocked。Coordinator Agent 在自身流程中发现的未决决定不是 Execution Outcome。
_Avoid_: Ticket 状态、验收决定

**Baseline Satisfaction**:
Ticket Base 已满足 Acceptance Obligation、无需交付差异时使用的证据路径；只有 Target Project 的既有规则可以把它判定为 Accepted 或 Superseded。
_Avoid_: 空提交、对空 diff 发起审查、默认验收

## 集成与证据

**Starting Base**:
Target Project 为一次新 DAG 运行确认的精确起始 commit，也是该运行首次建立 Accepted Integration Tip 时使用的 Base。
_Avoid_: 当前 HEAD、尚未完成 publication 的起始 commit

**Accepted Integration Tip**:
最近一个已经完成所选 Integration Publication Mode 的精确 commit/tree，也是后续 Ticket Base 的来源。
_Avoid_: 当前 HEAD、最新分支名、尚未完成的候选 commit

**Ticket Base**:
一个 Promotion Candidate 构建和评估时固定使用的 Accepted Integration Tip。
_Avoid_: 移动中的分支、最新审查摘要

**DAG Integration Branch**:
一次 DAG 运行专用、串行承载 Integration Transitions 和 Accepted Integration Tip 历史的 Git 分支。
_Avoid_: Ticket 分支、默认分支、调度数据库

**DAG Milestone**:
一个非空 Promotion Candidate 完成 Integration Transition 后形成的新 Accepted Integration Tip commit/tree。
_Avoid_: Promotion Candidate、中间 commit、Baseline Satisfaction

**DAG Definition Checkpoint**:
把 DAG Definition 或已批准 DAG Revision 绑定到集成历史的精确受审查 commit/tree；它通过 Integration Transition 成为 Accepted Integration Tip，但不验收 Ticket，也不形成 DAG Milestone。
_Avoid_: Promotion Candidate、Run Receipt commit、未经审查的 tracker 更新

**Integration Publication Mode**:
一次运行对 Accepted Integration Tip 的发布要求，只能是 Local-only 或映射到一个专用远端分支的 Remote-mirrored。
_Avoid_: 每个 Ticket 单独选择、顺便同步 remote

**Integration Transition**:
把记录的精确 Base（首个 Accepted Integration Tip 建立前为 Starting Base，之后为 Accepted Integration Tip）串行推进到已审查候选 commit/tree 的过程；候选类型只能是 Promotion Candidate 或 DAG Definition Checkpoint。
_Avoid_: Ticket 状态、无类型的 pending sync、裸 Candidate

**Promotion Candidate**:
一个 Ticket 的固定交付 commit/tree；其交付字节、最终门禁和 Candidate Review Record 相互一致，并保持 DAG Definition 与运行状态边界不变。
_Avoid_: working tree、最新文件、DAG Definition Checkpoint

**Candidate Review Record**:
把 Ticket Base、Promotion Candidate、评估范围与 `$code-review` 完整结果绑定在一起的证据。
_Avoid_: 未绑定的审查文本、审查者身份

**Run Receipt**:
保存在交付历史之外、用于恢复 Accepted Integration Tip、DAG Definition、认领、候选、Integration Transitions 和未决条件的紧凑记录。
_Avoid_: DAG Definition、已跟踪选择器、调度数据库

## 终态

**Terminal Outcome**:
只能是 Complete 或 Stalled；Complete 表示最终 DAG Definition 下的全部责任均已闭环，Stalled 表示当前没有任何获授权且可执行的推进路径。
_Avoid_: 等待中、存在未决决定、未同步的 Remote-mirrored 运行
