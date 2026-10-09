# 共享探索笔记与 DAG 的最小设计研究

本报告保留研究时的依据与建议。仓库对照基于 `16445a12e4557bba24f0bfc5cd70523207e444ed`；上游对照固定到 `b0618bc436ad893b3c5e84e55fba86586d34a404`，外部来源于 2026-10-09 核验。后续实施见 [0.4.3 方案](../plans/0.4.3.md)，执行以[当前派发契约](../../skill/dag/SKILL.md#dispatch-the-fixed-ticket-contract)和[输入读取规则](../../skill/dag/references/ticket-execution.md#read-the-assignment-and-preserve-its-boundaries)为准。

建议保留两种 DAG 角色和两种 Integration Transition，仅在确有重复探索时，通过已有 Ticket 上下文指针提供共享笔记。笔记的价值是省去重复搜索和定位；决定实现、依赖或验收的关键事实仍应回到当前权威来源核验。这是待验证的收益假设，本仓库没有运行对比结果证明其时间、token 或缺陷收益。

## 一手依据与实际差异

| 一手来源 | 已确认内容 | 对本仓库的含义 |
| --- | --- | --- |
| [上游 implement-spec 协议](https://github.com/mattpocock/skills/blob/b0618bc436ad893b3c5e84e55fba86586d34a404/skills/engineering/implement-spec/SKILL.md) | 沟通以 Spec、Ticket、研究笔记和提交的指针为主；探索子代理可选，其 Markdown 笔记放在仓库外，并让后续子代理可访问。 | 可借鉴按需共享的资料流；这不要求 DAG 增加永久探索角色、统一预探索阶段或笔记门禁。 |
| [上游 implement-spec 使用说明](https://github.com/mattpocock/skills/blob/b0618bc436ad893b3c5e84e55fba86586d34a404/docs/engineering/implement-spec.md#common-questions) | 作者报告过并行 web、mobile Ticket 分别采用 `blockedSince` 和 `blockedOn` 的案例，并建议共享探索笔记对齐名称。 | 这是上游报告，未在本仓库复现；对齐已有名称与决定新接口语义必须区分。 |
| [Anthropic 的上下文工程说明](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) | 支持用轻量标识按需读取资料，以及将笔记保存在上下文窗口外；同时指出运行时探索存在成本。 | 支持小指针和按需读取的设计方向，没有证明共享笔记对当前 DAG 的定量收益。 |
| [DAG 的派发契约](../../skill/dag/SKILL.md#dispatch-the-fixed-ticket-contract)与[设计说明](../DESIGN.md#objective) | Execution Agent 接收一个 Ticket 的权威指针与明确协议，通过零历史或最小相关历史重建实现上下文。 | 当前已具备指针和上下文隔离；缺少的是可选共享探索资料的明确使用边界。 |
| [Definition 分类](../../skill/dag/references/definition-binding.md#classify-definition-content)与 [Run Receipt](../../skill/dag/references/integration-transitions.md#run-receipt-and-frozen-evidence) | 完整批准计划绑定到 Git；运行状态留在交付之外；收据引用完整报告。 | 共享探索缓存可复用现有运行资源与指针，不应成为第二份计划或验收权威。 |

这里采用的分析方法是：指针写清资料回答什么问题及何时读取，只加载相关分支，把每个含义留在一个权威来源。它符合上述按需检索原则；本文的具体机制是针对当前 DAG 的推导，而非外部来源已经实现的 DAG 规范。

## 何时值得使用

当多个 Ticket 将重复定位同一模块、同一依赖版本的文档或同一已有接口约定，且一次探索能提供可核验的入口时，共享笔记可能有收益。即使原始文件仍要读，读者可以直接到相关符号、规则或测试，不必再次重走无效搜索路径。

单个 Ticket 的局部调查、可用一条命令找到的入口、已有清晰权威文档，通常不值得另建共享笔记。也不宜预先扫描整个仓库，再把长篇总结发给所有 Execution Agents。一次探索发现与当前 Ticket 无关的信息，可以留在文件中，但不因此进入派发上下文。

是否采用应按具体重复问题判断；不强制每个 run 产出笔记。最小试用只需观察重复搜索是否减少、指针是否被相关 Ticket 使用、版本复核与维护成本是否抵消收益，以及是否出现笔记错误扩散。无需为此增加常驻服务或新的测量流程。

## 权威边界

| 材料 | 回答的问题 | 对执行和验收的效力 |
| --- | --- | --- |
| Spec 与有效 Tickets | 批准要交付什么、义务属于谁 | 作为 [DAG Definition](../../skill/dag/SKILL.md#bind-the-dag-definition) 绑定，按已有授权和变更规则演进。 |
| Accepted direct inputs | 当前 Ticket 可以消费哪些已验收输出 | 携带身份；确实消费前置 Ticket 输出才形成 [Hard Dependency](../../skill/dag/SKILL.md#reconstruct-the-live-run)。 |
| Gate 与 review evidence | 这个精确候选是否满足义务 | 按[执行协议](../../skill/dag/references/ticket-execution.md#return-one-execution-outcome-and-stop-writing)绑定 Base、候选和实际验证，并按[证据有效性规则](../../skill/dag/references/ticket-execution.md#keep-gate-evidence-valid)刷新。 |
| 共享探索笔记 | 去哪里核查、某个来源版本上观察到什么、还有什么不确定 | 建议性导航和调查缓存；本身不批准产品语义、不创建依赖、不验收输出，也不证明共享文件或资源已隔离。 |

多位 Agent 读到同一笔记并同意其结论，不是独立验证。共同错误会随共享而扩散；实现、测试和审查仍以原始权威输入为准。若笔记记录的事实用于正式验收，应在既有证据报告中核验并绑定来源、候选和实际结果，保持[冻结证据](../../skill/dag/references/integration-transitions.md#run-receipt-and-frozen-evidence)的现行要求。

字段名尤其容易越界。若 `blockedSince` 已由批准的 Spec、当前公共类型或 Accepted input 确定，笔记可以标明该来源，帮助各 Ticket 找到同一约定。若当前材料没有共识，探索者直接写“所有 Ticket 都使用 `blockedSince`”，就开始制定跨 Ticket 契约。应先判断是否在既有授权和范围内；需要改变批准语义、依赖、义务或 gates 时，按现有决策与 DAG Revision 规则处理。笔记不能自行授予这个决定权。

## 可选机制的最小范围

以下均为建议，不是本轮新增的现行规则。

1. **按问题委派。** Coordinator 或当前 Ticket 责任人可以在自己的已有责任范围内安排短期探索。辅助任务只调查所需来源、写指定笔记；既有 DAG 角色继续拥有图决策和 Ticket 实现。发现边界变化时返回证据，由原责任人处理。
2. **核实共享可达性。** 为确有共享需要的问题选用已获权限的、交付之外的运行目录，例如 `<shared-off-delivery-root>/<run-id>/`。确认作者能写、预期读者在其真实宿主和权限下能读；后续替代 Agent 或跨宿主派发需重新确认。仓库外、相同字符串路径或不同 worktree 本身均不证明共享。不可达时省略共享指针，继续在 Ticket 内查原始来源；若原始来源也不可达，才按已有决策或外部阻塞规则处理。
3. **每份笔记一个写者。** 发布中的同一文件由一个责任人写；消费者只读。修改时可另发一个完成的版本，或等读者结束后更新，避免读取半成品。不同问题可由不同作者分别写；无需锁服务、共享编辑协议或新的 DAG 状态。替换未知存活状态的作者时，沿用[现有写者恢复边界](../../skill/dag/SKILL.md#resume-safely-and-finish)。
4. **只保存必要信息。** 四项通常足够：回答的问题和适用 Tickets；来源定位与版本；已确认事实和待验证假设；影响结论成立的条件。这是内容建议，不是必填模板。源码观察可记录 commit 和相关路径或 blob 身份；依赖文档记录版本、官方链接和检索时间。涉及运行观察时补充相关配置、依赖和环境假设，保留原始日志指针。避免复制完整 Spec、Ticket、历史工具输出或收据。
5. **按影响刷新。** 消费者只读取当前 Ticket 相关部分。Base 改变后，比对结论依赖的源码、配置、依赖版本、Accepted inputs 及环境条件；无关变更不自动作废整份笔记，受影响部分重新查证。依赖范围不清时，回查该结论的原始来源。笔记日期和来源文件未改都不足以单独证明仍然适用。正式 gates 与 review 是否重用，继续由[现有证据有效性规则](../../skill/dag/references/ticket-execution.md#keep-gate-evidence-valid)判断。
6. **保持小派发与现有清理路径。** Ticket payload 只增加相关问题的读取条件、文件或章节指针及适用身份，继续零历史或最小相关历史派发。Run Receipt 若需恢复，只索引路径、作者和资源处置，不复制内容或新增权威状态。将笔记归入[现有资源清单](../../skill/dag/SKILL.md#resume-safely-and-finish)：无人使用且可重建的缓存按已有权限回收；被验收、审查或恢复证据引用的版本先核实保留位置和链接。清理不改变 Ticket 验收或 Terminal Outcome。

若后续批准实施，最小落点可以是[派发契约](../../skill/dag/SKILL.md#dispatch-the-fixed-ticket-contract)与[执行协议的输入读取段](../../skill/dag/references/ticket-execution.md#read-the-assignment-and-preserve-its-boundaries)各一小段。无需更改 Definition Index、Integration Transition、Runtime Skill Bundle 或 Promotion helper。

以下英文仅为 **proposed** 协议片段，未成为当前规则：

```text
For repeated exploration relevant to a Ticket, optionally supply an advisory
note pointer with its question, source identities, and applicability. Resolve
an off-delivery location reachable by its intended readers and preserve
zero-history or minimal relevant-history dispatch.

Consult only notes relevant to this Ticket. Verify decision-critical facts
against current authoritative inputs and refresh affected conclusions when
source or environmental assumptions change. Missing or conflicting notes
fall back to source lookup; notes are neither governing inputs nor acceptance
evidence. Route boundary changes through the existing Ticket and DAG Revision
rules.
```

## 六个场景的静态推演

下表是依据现有契约推演的预期处理，尚未运行多 Agent 试验。

| 场景 | 预期处理 | 不能用笔记替代的边界 |
| --- | --- | --- |
| 两个独立 Ticket 查询同一版本 SDK 的调用规则 | 可共享相关官方入口、符号定位与版本；各自核验影响实现的规则。 | 缓存阅读经验不能替代各 Ticket 的 TDD、gates 或 review。 |
| 并行 Ticket 采用 `blockedSince` 与 `blockedOn` | 已有权威名称时，笔记指向它；没有共识时，原责任人处理接口选择，必要时修订 Definition。 | 笔记不能创设跨 Ticket 产品语义；仍需检查共享文件冲突。 |
| Ticket B 实际需要 Ticket A 新交付的 schema，A 尚未 Accepted | 若有效图漏了此消费关系，提交确切证据，走已有 DAG Revision；B 等待可消费的 Accepted output。 | 阅读 A 的探索笔记不能充当前置输出，也不能凭此解锁 B。 |
| Integration Tip 更新：无关说明变了，或相关锁文件、配置变了 | 前者保留适用结论；后者重新核验受影响部分。Ticket Base 仍由 Coordinator 指定。 | 笔记刷新不能替代候选刷新、gate 有效性审计与新候选 review。 |
| 后续 Agent 在另一宿主，原共享路径不可读 | 省略该指针并本地查权威来源；只有已有可达且获授权的共享方式才继续共享。 | 不自动建立同步服务、增加权限或将笔记缺失变成全 DAG 阻塞。 |
| 作者尚在写、run 恢复或结束时计划清理笔记 | 每份文件一个写者，只提供完成版本；恢复先确认写者；清理前保留仍被证据引用的版本。 | 不推定作者死亡，不删除唯一证据，不改变验收结果。 |

## 何时回到 Ticket 或 DAG Revision

只改调查入口、定位、假设或笔记的适用说明，通常留在当前任务的调查路径。探索发现 Ticket 内的实现缺陷、测试边界、命令错误或 review finding，继续由同一 Execution Agent 的[工程循环](../../skill/dag/references/ticket-execution.md#run-the-ticket-local-engineering-loop)处理。

发现缺失的前置输出、错误依赖、义务归属错误、可独立验收的拆分、产品或 gate 选择、权限边界，或无法按当前约束解决的跨 Ticket 冲突，应按[现有边界升级规则](../../skill/dag/SKILL.md#escalate-only-boundary-changes)交给 Coordinator。并非每个发现都需要新审批：Coordinator 可在已有授权内解决；只有批准计划或授权边界确实变化时，才需要相应决策。

需要修改有效 Tickets、Spec、Hard Dependencies 或 Acceptance Obligations 时，沿用现有 DAG Revision 和 [DAG Definition Checkpoint](../../skill/dag/references/definition-binding.md#complete-a-dag-definition-checkpoint)。若某份研究报告本身是批准的独立交付物，就按已有 Ticket 契约验收和保留，不能归为可丢弃缓存；无产品字节变化时，也只有 Approved Ticket 或项目规则认可且义务全部有证据，才可走 [Baseline Satisfaction](../../skill/dag/references/ticket-execution.md#gather-zero-diff-evidence)。若报告内容成为 governing Definition，纳入现有 Definition 绑定。共享笔记不得改写待完成 Transition 的冻结证据；若新发现证明候选或证据无效，沿用[现有停止与恢复规则](../../skill/dag/references/integration-transitions.md#reconcile-the-local-integration-ref)，不能为完成 Transition 而忽略失效事实。

当前证据足以支持一个可选的小补充，尚不足以证明需要普遍预探索、强制模板、第三种角色或 Transition、额外审批层。下一步如获准，可先在一个存在重复探索的 run 中验证上述收益与失败边界，再决定是否写入正式协议。
