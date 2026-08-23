# DAG Skill Design

This document specifies a minimal, project-independent and host-neutral Agent Skill for continuously advancing an already approved Spec-and-Ticket dependency DAG. The consuming project's live contracts remain authoritative. The Skill supplies coordination, not a tracker, workflow engine, or authoring system.

## Deliverable Boundary

The Agent-facing normative runtime artifact authored by this project is one English `skill/dag/SKILL.md` in the open Agent Skills format. The complete copyable DAG Skill artifact is `skill/dag/`; it may also contain optional host metadata and the setup helper defined below, but `SKILL.md` remains the sole normative DAG runtime source and must not depend on `README.md`, this document, or `CONTEXT.md` for DAG semantics. It has the explicit external Required Skill Bundle defined below.

The final deliverable also includes one Chinese, human-facing `README.md` that explains the Skill's purpose, prerequisites, invocation boundary, core DAG flow, fallbacks, authorization boundary, and terminal outcomes without restating the complete state machine or becoming runtime instructions.

`skill/dag/agents/openai.yaml` is optional, non-normative OpenAI/Codex interface metadata; unsupported hosts may ignore it. `skill/dag/scripts/install_dependencies.py` is the only executable helper: it performs separately authorized, setup-only installation of the pinned Required Skill Bundle and never schedules Tickets or changes a Target Project. The project will not add references, fixtures, persistent scheduler state, a graph DSL, a general CLI, runtime scheduling scripts, or `check`, `start`, `resume`, or `status` commands. `CONTEXT.md` and this document are non-runtime design evidence only.

## Scope

The Skill consumes an Approved DAG whose Spec, Tickets, and dependency semantics have already been produced and approved through other project-appropriate Skills or processes. It does not silently author a new Spec, invent Tickets, infer product semantics, or replace the Target Project's Tracker Contract.

The Skill may normalize different carriers into a live DAG Projection. Local Markdown, GitHub Issues, and other trackers remain valid when their project contracts allow them.

Historical bidevs, A-share research, vLLM E2E Report, and other repositories are design experience only. They are not runtime dependencies. This project neither depends on nor modifies the Everythings project.

## Invocation and Inputs

The Skill is discoverable from its description where the Agent Host supports automatic activation and remains explicitly selectable through the Agent Host's native mechanism. Exact mention prefixes, slash commands, host installation paths, and invocation APIs are outside the runtime contract. Its frontmatter uses the portable minimum defined by the open Agent Skills specification:

- `name: dag`, matching the `skill/dag/` artifact directory;
- a narrow `description` that triggers on explicit requests to execute, advance, continue, or resume an already approved multi-Ticket DAG and routes Spec or Ticket authoring and isolated single-Ticket work to their dedicated Skills.

Host capability requirements remain in the Skill body so the frontmatter stays at the common portable minimum.

Before acting, the Coordinator must receive or uniquely discover the Target Project, Approved Spec, in-scope Ticket set and dependency carrier, and DAG Run Authorization. A missing or ambiguous pointer pauses execution and requires one precise clarification rather than a guessed scope.

## Agent Host Compatibility

The workflow is contract-portable, not universally executable by every conversational tool. A supported Agent Host can load and explicitly activate named Skills, dispatch fresh role-isolated Agent contexts, establish write-capable Execution and read-only Review boundaries, observe liveness and terminal states, and access the Target Project's tracker, repository, and verification tools.

Parallel and nested dispatch are optimizations rather than universal requirements. The Coordinator serializes when parallelism is unavailable. When a present reusable Skill requires unsupported nested behavior, that Skill is inapplicable and the disclosed DAG-Native Fallback may be used only if the Agent Host can still preserve fresh context and role independence. Without those core isolation or observability capabilities, the affected role is unavailable and the run stops before Ticket claim rather than weakening a gate.

Host-specific installation locations, activation syntax, policy extensions, and APIs are setup concerns, not DAG semantics. The Coordinator records only the runtime and policy metadata the Agent Host actually exposes and never treats a missing vendor-specific field as proof of failure by itself.

## Required Skill Bundle

The supported execution profile requires complete installed or registered Matt Skill directories named `implement`, `code-review`, `tdd`, and `codebase-design`. The default bundle is pinned to `mattpocock/skills` revision `5b15a47f2d7150f545fbcacbfe381787fc0230dc`. The upstream repository groups their sources under `skills/engineering/`; installation flattens that repository-only grouping and places each whole directory directly under the stable user or shared Skills root documented by the Agent Host.

Before any Ticket claim or Agent dispatch, the Coordinator resolves and contract-checks every bundle member through the Agent Host's native discovery and explicit-activation mechanism. It verifies exact names, unique resolved identifiers or locations, required bundled files, actual call contracts, explicit activation, and immutable content identity. Host-specific policy or provenance fields are checked only when exposed. A missing, disabled or non-activatable, unreadable, incomplete, differently resolved, duplicate-name, or contract-mismatched member fails the bundle as a whole.

A bundle failure pauses the run before Ticket work. It is neither DAG-Native Fallback nor an Operational Retry. DAG Run Authorization does not authorize installing, registering, updating, or overwriting user Skills. With separate user authorization and an explicit stable Agent Host Skills root, the Coordinator may invoke `scripts/install_dependencies.py --skills-root <host-skills-root>` relative to the DAG Skill. The helper fetches the fixed Matt revision, installs the four complete directories directly beneath that root, treats identical targets as current, and fails the entire preflight without overwriting any differing target. An unavailable helper requires equivalent manual repair, never a weaker bundle gate. Every repair must be followed by a full catalog and bundle reread.

`setup-matt-pocock-skills` is not a bundle member. It is a project-configuration capability whose writes require separate authorization. The Coordinator treats the pinned Code Review Skill as inapplicable when its Agent Host or project setup contract is unsatisfied and uses DAG-Native Fallback rather than activating setup under DAG Run Authorization.

## Authority and Evidence

A DAG Run Authorization is an explicit user request to execute, advance, continue, or resume an Approved DAG. It authorizes continuous locally auditable work without per-Ticket confirmation:

- claiming and updates in a local tracker carrier;
- Agent dispatch;
- creation and use of non-destructive, ticket-scoped local candidate branches or worktrees when the Target Project permits them;
- ticket-scoped code changes, verification, and commits when Git and the Target Project permit them;
- local acceptance evidence and successor unlocking.

Separate authorization remains required for:

- every external-system mutation, including remote tracker writes, deployments, external API or database writes, and state-changing remote CI triggers, unless the user has granted a bounded run-scoped authorization;
- push, pull request creation, tag, release, or other publication;
- destructive Git operations;
- product-semantic or acceptance-criteria changes;
- gate weakening.

Normative Authority comes from the current user scope, applicable project instructions, the approved Spec, approved Tickets, and the Tracker Contract. A contradiction that changes scope, semantics, acceptance, or required delivery behavior pauses the affected node for repair or approval; the Coordinator does not silently choose an authority. Live tracker, Git, code, tests, and formal-review artifacts are State Evidence. Chat history, plans, Worker claims, Reviewer summaries, and green tests alone are never completion proof.

## Graph Contract

Each executable node is one Ticket. Ticket implementation, Implementation-Side Review, review sufficiency, Formal Review, integration, acceptance, and bounded rework are gates inside the node, not additional dependency nodes.

A schedulable Ticket must have live, unambiguous semantics for:

- identity and authoritative source;
- one delivery objective;
- in-scope and out-of-scope boundaries;
- dependency inputs;
- observable outputs consumed downstream;
- acceptance and verification requirements;
- current state, ownership, and blockers.

An edge is oriented `prerequisite -> dependent` and exists only when the dependent consumes an accepted output of the prerequisite. Preferred order, shared ownership, similar files, implementation phases, and external blockers are not dependency edges.

Before start or resume, the Coordinator fails closed unless the DAG Projection has unique and resolvable nodes, no self-edge or directed cycle, approved and contract-complete Tickets, defensible dependency edges, no known missing hard dependency, and live state consistent with acceptance evidence. Multiple roots, sinks, and independent components are allowed.

The Runnable Frontier contains only unaccepted Tickets whose hard predecessors are Accepted Tickets, blockers are cleared, claim and acceptance evidence can be persisted under current authorization, suitable resolved Execution Profiles and capabilities are verified, and a safe write boundary is available without ownership conflict or premature advancement of the Authoritative Integration Baseline. A status string such as `ready-for-agent` or dependency readiness alone is insufficient.

## Roles and Execution Profiles

| Role | Responsibility | Default selection |
| --- | --- | --- |
| Coordinator | Live reconciliation, graph validation, scheduling, tracker state, evidence adjudication, integration, rework or revision decisions, and final acceptance | Suitable active primary Agent; favor the strongest available graph-wide reasoning and context capacity |
| Execution Agent | One Ticket's implementation through Implementation Handoff | Available Agent matched to the Ticket's repository, coding, tool, context, complexity, and risk needs |
| Review Agent | Runs a fresh Code Review Skill when the Coordinator determines that existing review evidence is insufficient | Fresh independent context matched to the review surface; use stronger available capability for high-risk work |
| DAG-native Standards or Spec Reviewer | Supplies the corresponding independent review when the verified Code Review Skill is inapplicable | Fresh independent context with the relevant Standards or Spec capability |

An exact user or Target Project model, Agent, or reasoning-effort requirement is a hard constraint. Without one, the Coordinator resolves profiles from live availability and work-specific capability, using the highest useful supported reasoning effort for coordination and high-risk work and proportional effort for bounded lower-risk work. Review independence is a context and role boundary; model diversity is optional unless a governing contract requires it.

When the user names a model or asks for model selection, the Coordinator inspects the live available choices and recommends concrete role assignments based on the requested role, work risk, context, and tool needs. A suitable available choice is honored. An unavailable or incapable exact request is not silently replaced: the Coordinator explains the mismatch, proposes suitable available alternatives, and obtains user authorization before substitution.

The Coordinator inspects and records all runtime metadata the Agent Host exposes for itself and every dispatched Agent, including unavailable fields, the resolved profile, and any run-time change. It never infers a missing model or reasoning effort. An unverifiable exact requirement leaves that role unavailable. Without an exact constraint, an Agent may run when its required identity and capabilities are substantiated even if the Agent Host omits a model or effort field, provided that omission is disclosed. Before dispatch, a move to another suitable substantiated profile is ordinary scheduling and does not pause unrelated work; after dispatch, an observed profile mismatch is an Operational Failure.

Only the Coordinator owns DAG and tracker state. Execution and Review Agents return artifacts and evidence but cannot accept Tickets, change graph state, or unlock successors.

## Start and Resume

The Skill has no command modes. On every authorized start or continuation, the Coordinator:

1. rereads the Target Project's applicable instruction hierarchy, live Spec, all in-scope Tickets, dependency and blocker evidence, tracker rules, Git state, test contracts, and existing formal-review evidence;
2. verifies the Agent Host capabilities, validates the complete Required Skill Bundle, then discovers any Target Project authoring Skills plus live Agent models, reasoning controls, tools, and runtime metadata, without trusting chat memory;
3. reconstructs and validates the DAG Projection;
4. reconciles already accepted, in-progress, blocked, superseded, and unclaimed Tickets against live Recovery Evidence;
5. computes the Runnable Frontier and available safe capacity.

The Skill never initializes Git. It preserves unrelated dirty work and does not manufacture a clean baseline with reset or clean.

Inherited changes are classified as the current Ticket candidate, protected unrelated work, or unaccepted historical work. Unaccepted historical work remains evidence-only unless a live approved Ticket explicitly adopts it.

Recovery Evidence must remain in the Target Project's existing tracker or repository evidence under its Tracker Contract, not in a DAG Skill scheduler file. For every started Ticket, it must reconstruct the resolved Required Skill Bundle identifiers or locations, content identities, activation status, and unavailable provenance fields; the current attempt and ownership; the active Coordinator's and every dispatched Agent's resolved and observed Execution Profile, including unavailable metadata fields, mismatches, and changes; every directly dispatched Agent's bounded progress checkpoint, observed state, and last milestone; Review Fixed Point; Final Artifact Identity when available; integration state, Authoritative Integration Baseline identity, candidate representation or reachability, and integrated-gate commands, contexts, outcomes, and bound artifact identities when available; consumed Operational Retry and Formal Rework; findings and dispositions; known failing gates with their context, classification, owner and closing condition; acceptance evidence; and Ticket Lineage with any consumed automatic DAG Revision. If required evidence cannot be reconstructed or legally persisted, the Ticket is not Runnable and the Coordinator fails closed on that path.

An optional, already-authorized Agent Host goal may preserve run liveness but never Target Project or recovery state. A cross-task handoff becomes valid only after the receiving Coordinator rereads the live project, reconstructs all required Recovery Evidence, and recomputes the frontier.

## Continuous Scheduling

After authorization, the Coordinator continues without asking for confirmation after each Ticket:

1. finish formal review, integration, and acceptance work already in progress before opening more implementation work;
2. recompute the Runnable Frontier from live state;
3. choose the largest safe subset whose peak direct and nested Agent demand fits available capacity, serializing when that demand is unknown;
4. use tracker priority first, then obvious downstream-unlock or critical-path value, then stable Ticket identity when capacity requires a tie-break;
5. recheck and claim each selected Ticket immediately before dispatch;
6. advance each returned Ticket through evidence validation, Formal Review, adjudication, integration, and integrated-byte verification;
7. persist and reread acceptance evidence before unlocking successors;
8. repeat until Complete or genuinely Stalled.

Graph independence is necessary but not sufficient for parallel writes. A workspace has one write-capable Execution Agent at a time. Parallel implementations require Target Project-permitted isolation and an integration boundary; the Coordinator may create and use ticket-scoped local candidate branches or worktrees under DAG Run Authorization and the Target Project's contract. If safety is uncertain, serialize. Read-only reviews may still run concurrently.

## Per-Ticket Flow

### 1. Dispatch

Immediately before claiming, the Coordinator confirms that every Required Skill Bundle member still resolves to the recorded content identity; any drift returns to bundle failure. It then captures an immutable Review Fixed Point before implementation and dispatches one fresh Execution Agent for exactly one Ticket in a write boundary that cannot advance the Authoritative Integration Baseline before adjudication.

Each Agent dispatched directly by the Coordinator receives a persisted bounded progress checkpoint appropriate to its role, Ticket, and Agent Host. A dispatching Agent is responsible for equivalent bounded monitoring of any nested Agents it creates and for reporting their resolved and observed Execution Profiles, unavailable metadata fields, changes, and terminal states. A live Agent that reaches its checkpoint without an evidence-bearing milestone, evidenced blocker, or terminal result incurs an Operational Failure rather than holding the run open.

When the verified `implement` Skill is applicable, the dispatch explicitly activates it through the Agent Host's native mechanism, with every nested use of `tdd`, conditionally required `codebase-design`, and `code-review` resolved from the same Required Skill Bundle regardless of invocation syntax. That nested review is an Implementation-Side Review: its raw Standards and Spec artifacts are candidate evidence for the Coordinator, but neither the Execution Agent nor its reviewers may accept the Ticket or unlock successors.

The Coordinator supplies the Review Fixed Point, approved Spec and Ticket, applicable standards, and exact scope needed by the nested review. A nested Skill may not install prerequisites or mutate project configuration under DAG Run Authorization. If the Agent Host cannot provide the required nested behavior or the review context cannot be supplied safely, `implement` is inapplicable rather than partially followed.

If the Agent Host and Target Project cannot provide a safe Git candidate-commit context that leaves the Authoritative Integration Baseline unchanged, the installed `implement` Skill's commit contract is inapplicable rather than silently ignored.

If the verified `implement` Skill is inapplicable to the Agent Host or Target Project, the Coordinator discloses DAG-Native Fallback and dispatches a fresh Execution Agent directly under the Target Project's live instructions, Spec, Ticket, and verification contracts. This Agent still explicitly activates the verified `tdd` Skill at a pre-agreed public seam when feasible and the verified `codebase-design` Skill when the seam's shape is in question. The fallback need not manufacture an Implementation-Side Review; missing reusable review evidence will cause the Review Sufficiency Gate to dispatch a fresh review. A missing or invalid bundle blocks before this branch and is never represented as fallback.

A RED is evidence only when it uses the live Ticket contract through its agreed public and real delivered seam where applicable, and fails because of target behavior rather than environment, tooling, or probe error. Claiming, reading, and exploration are not RED or candidate evidence.

### 2. Implementation Handoff

The Execution Agent returns at least:

- Ticket identity and delivered scope;
- the actual changed files and commit when applicable;
- exact verification commands, contexts, and outcomes, including failures and checks not run, with each failure classified as an introduced regression, an evidenced baseline exception with an owner and closing condition, an environment/tool/probe failure, or unverified;
- raw Standards and Spec review artifacts, actual Execution Agent and reviewer metadata, and the artifact identity examined by the Implementation-Side Review when available;
- any implementation change made after that review;
- deviations, unresolved risks, and blockers.

The Coordinator independently checks the live diff, commit, verification results, scope, repository state, review artifacts, reviewer independence, artifact identities, delivered public seam, and unexplained generated or dependency-lock churn. A Worker completion claim or review summary is not an Implementation Handoff. A required non-green or unverified gate blocks acceptance unless the Target Project explicitly permits the exact evidenced exception.

An Agent crash, tool failure, execution-profile mismatch, invalid handoff or report, or integration tool failure permits one total corrected Operational Retry per Ticket attempt across implementation, review, and integration and does not consume the Rework Budget. Persist the consumed retry before redispatch. After that budget is consumed, any further operational failure blocks the Ticket; it does not create an automatic loop or transfer implementation or review work to the Coordinator.

### 3. Review Sufficiency and Formal Review

After a valid handoff, the Coordinator identifies the immutable Final Artifact Identity and applies the Review Sufficiency Gate to the raw Implementation-Side Review evidence. Existing review evidence is sufficient only when:

- both raw Standards and Spec reports are available rather than only an Execution Agent summary;
- the reviewers did not implement the Ticket, their actual profiles are verified, and their contexts were fit for the assigned axes;
- both reports examine the same Final Artifact Identity and no implementation change followed that review;
- their scope and evidence are complete enough for the Coordinator to substantiate every finding disposition; and
- neither the Target Project's contract nor the change risk requires a fresh Coordinator-dispatched review.

When all conditions hold, the Coordinator adopts the Implementation-Side Review as the Ticket's Formal Review evidence and proceeds to adjudication without mechanically repeating the same review.

When the evidence is missing, stale, incomplete, contradictory, unverifiable, or inadequate for the risk, the Coordinator dispatches a fresh Review Agent with the Review Fixed Point, approved Spec and Ticket, applicable standards sources, commit list, and exact review scope. High-impact surfaces and any Target Project mandate are sufficient reasons to require the fresh review.

When the verified `code-review` Skill is applicable, the Review Agent explicitly activates it through the Agent Host's native mechanism. Its Standards and Spec reviews remain independent and are returned side by side. The approved Spec always exists for this workflow; the Spec axis may not be silently skipped.

A reused Skill may not install prerequisites, mutate project configuration, or ask the user to repair missing review context under DAG Run Authorization. If the Agent Host cannot supply its required execution behavior or its fixed point, diff, Spec, tracker, or other inputs cannot be supplied safely, it is inapplicable and the Coordinator uses the disclosed fallback.

If the verified `code-review` Skill is inapplicable to the Agent Host or Target Project, the Coordinator discloses DAG-Native Fallback and directly dispatches fresh, independent Standards and Spec Reviewers against the same Final Artifact Identity. A missing `docs/agents/issue-tracker.md` required by the pinned Skill is inapplicability; it does not authorize `setup-matt-pocock-skills`.

Every Review Agent report includes its own and any nested Reviewers' resolved and observed Execution Profiles, unavailable metadata fields, run-time changes, artifact identities, and raw findings. Missing required profile evidence or a violated exact constraint prevents adoption of that review evidence.

A review timeout or missing report is missing evidence. A replacement caused by operational failure consumes the remaining Operational Retry; before adjudication, every dispatched reviewer is terminal or explicitly superseded and every queued or late report is reconciled.

Any change to reviewed bytes or review-relevant identity or history invalidates both review axes. The changed Final Artifact Identity must pass the Review Sufficiency Gate again. A topology-only integration may retain evidence only when equivalence is verifiable and its changed identity or history lies outside both review scopes.

### 4. Coordinator Adjudication

The Coordinator combines live implementation evidence with the separate review reports and gives every finding one evidence-backed disposition:

- valid and blocking within the Ticket;
- valid but requiring a graph change;
- advisory and non-blocking, with rationale;
- false positive, with evidence;
- unresolved.

An unresolved, valid blocking, or graph-changing finding prevents integration. A graph-changing finding returns to the DAG Revision path.

### 5. Integration and Acceptance

Only after adjudication is clear does the Coordinator incorporate the exact reviewed candidate into the Target Project's Authoritative Integration Baseline, verify reachability or representation, and run affected, integration, and delivered-public-seam gates on the integrated bytes. Integration remains byte-preserving. A conflict requiring reviewed-byte changes within the original Ticket scope consumes its remaining Formal Rework and returns to an Execution Agent; exhausted rework or scope drift enters DAG Revision rather than Coordinator implementation.

A change to reviewed bytes or review-relevant identity or history reapplies the Review Sufficiency Gate. The Coordinator accepts the Ticket, persists and rereads its evidence, and unlocks successors only when integrated artifact, verification, review, dispositions, scope, baseline, and tracker evidence agree. An external resolved state that promises availability also requires the designated reference to contain the artifact and every required remote-write or publication authorization.

## Rework and DAG Revision

Each Ticket has one Formal Rework. It begins only when the Coordinator accepts a blocking Formal Review or integration finding and returns the Ticket for implementation within the original scope. Persist the consumed rework before redispatch. Self-correction before handoff, duplicate findings, false positives, and Operational Retry do not consume it.

Formal Rework returns to the original Execution Agent when that Agent remains available with a suitable resolved Execution Profile; otherwise a fresh Execution Agent receives the complete accepted findings. The Coordinator reapplies the initial Skill applicability gate, using `implement` when applicable and the disclosed DAG-Native Fallback otherwise. Rework keeps the DAG topology unchanged. The resulting implementation receives a new Final Artifact Identity, new Implementation-Side Review evidence when `implement` applies, and another Review Sufficiency Gate before adjudication.

Implementation stops for DAG Revision as soon as a Ticket gains another independent objective or acceptance seam, or its fixed diff no longer permits bounded review. It does not wait for the Formal Rework budget to be consumed.

If valid blocking problems remain after Formal Rework, the Coordinator does not retry again or add a back edge. It determines whether to split the Ticket, add a prerequisite, reorder work, reject or defer scope, or record an external blocker.

When new or revised Ticket content is required, a current Target Project authoring Skill creates it. The DAG Skill owns the revision decision but does not author the replacement Tickets and has no authoring fallback. A semantics-preserving local revision may proceed under DAG Run Authorization after its rationale and provenance are recorded. A semantic, acceptance, or gate change requires user approval. The revised graph must pass the Whole-Graph Validity Gate before scheduling resumes, and displaced Tickets remain visible as superseded evidence.

Only one automatic semantics-preserving DAG Revision may be consumed by an original Ticket Lineage. Persist that consumption before scheduling the replacement subgraph. A further revision in the same lineage requires explicit user authorization; without it, leave the lineage unfinished with evidence and allow the run to become Stalled after independent branches finish.

A valid late finding or Whole-DAG failure invalidates the contradicted Ticket and every accepted descendant that consumes its output, pausing the affected subgraph. The Coordinator persists that invalidation when authorized and blocks when it cannot; remaining Formal Rework may reopen the original scope, otherwise the authoring capability appends a remediation lineage.

## Terminal Outcomes

A blocked branch does not stop independent runnable branches.

An Agent counts as running only while its liveness remains observable and its bounded progress checkpoint has not failed; a lost or non-progressing Agent becomes an Operational Failure rather than holding the run open indefinitely. Complete and Stalled are mutually exclusive.

The run is **Stalled** only when unfinished Tickets remain, no Agent is running, and no Runnable Frontier exists. Every stopped path must have a live evidenced cause such as an external blocker, missing authorization, invalid graph, unavailable required capability, repeated operational failure, exhausted rework, or an exhausted automatic DAG Revision awaiting authoring or approval.

The effective graph excludes Superseded Tickets from execution while retaining their provenance and includes every approved replacement Ticket. The run is **Complete** only after every Ticket in that effective graph is accepted and the Coordinator passes a Whole-DAG Acceptance Gate covering:

- Approved Spec coverage;
- integration of every accepted candidate into the Authoritative Integration Baseline and of predecessor outputs into dependents;
- current Final Artifact Identities and matching Ticket evidence;
- Target Project graph-wide verification gates;
- absence of unresolved findings, blockers, and unexplained in-scope changes;
- tracker, commit, Ticket Lineage, and acceptance-evidence consistency.

Complete does not imply or authorize remote publication.

## Acceptance Criteria for Final Deliverables

The implementation is acceptable when:

- `skill/dag/SKILL.md` is the only normative DAG runtime artifact and is written in accurate Agent-facing English;
- `skill/dag/agents/openai.yaml` contains only optional interface metadata, and `skill/dag/scripts/install_dependencies.py` remains a setup-only, explicit-Skills-root, pinned, no-overwrite helper;
- `README.md` is a concise Chinese human-facing companion that remains consistent with `SKILL.md` and is not a runtime dependency;
- it uses only open Agent Skills frontmatter and host-neutral runtime language, with no required vendor-specific path, invocation syntax, policy extension, or Agent API;
- it verifies the Agent Host's isolation, access-boundary, observability, Skill-activation, and project-access capabilities before Ticket work while allowing serial scheduling when parallelism is unavailable;
- it expresses implementation through `implement`, including its Implementation-Side Review, followed by the Coordinator's Review Sufficiency Gate, conditional fresh review through `code-review`, and Coordinator adjudication;
- it requires and validates the pinned, complete `implement`, `code-review`, `tdd`, and `codebase-design` bundle before Ticket work;
- it defines DAG-native fallback only for verified-but-inapplicable Skill contracts and never for a missing or invalid bundle;
- it keeps Ticket dependencies acyclic and bounds both Operational Retry and Formal Rework;
- it derives scheduling from live project evidence and the Target Project's Tracker Contract;
- it resolves model and Agent profiles from live constraints, capability, and risk without binding the workflow to one model version or silently replacing an exact request;
- it preserves Coordinator authority, same-final-bytes review, integration-before-acceptance, atomic acceptance-before-unlock, Safe Parallelism, and Whole-DAG final acceptance;
- it contains no project-specific tracker, authoring implementation, persistent state, general CLI, or additional DAG scheduling runtime artifact beyond the explicit external Required Skill Bundle;
- it does not broaden local authorization into remote or high-impact actions.
