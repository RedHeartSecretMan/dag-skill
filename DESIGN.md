# DAG Skill Design

This document specifies a minimal, project-independent Agent Skill for continuously advancing an already approved Spec-and-Ticket dependency DAG. The consuming project's live contracts remain authoritative. The Skill supplies coordination, not a tracker, workflow engine, or authoring system.

## Deliverable Boundary

The Agent-facing runtime artifact is one English `SKILL.md`. It is the sole normative runtime source and must not depend on `README.md`, this document, or `CONTEXT.md` at runtime.

The final deliverable also includes one Chinese, human-facing `README.md` that explains the Skill's purpose, prerequisites, invocation boundary, core DAG flow, fallbacks, authorization boundary, and terminal outcomes without restating the complete state machine or becoming runtime instructions.

The project will not add references, scripts, fixtures, persistent scheduler state, a graph DSL, a CLI, or `check`, `start`, `resume`, or `status` commands. `CONTEXT.md` and this document are non-runtime design evidence only.

## Scope

The Skill consumes an Approved DAG whose Spec, Tickets, and dependency semantics have already been produced and approved through other project-appropriate Skills or processes. It does not silently author a new Spec, invent Tickets, infer product semantics, or replace the Target Project's Tracker Contract.

The Skill may normalize different carriers into a live DAG Projection. Local Markdown, GitHub Issues, and other trackers remain valid when their project contracts allow them.

Historical bidevs, A-share research, vLLM E2E Report, and other repositories are design experience only. They are not runtime dependencies. This project neither depends on nor modifies the Everythings project.

## Invocation and Inputs

The Skill is model-invoked and remains directly user-invocable. Its frontmatter omits `disable-model-invocation` and uses only:

- `name: dag-skill`;
- a narrow description that triggers on explicit requests to execute, advance, continue, or resume an already approved multi-Ticket DAG and routes Spec or Ticket authoring and isolated single-Ticket work to their dedicated Skills.

Before acting, the Coordinator must receive or uniquely discover the Target Project, Approved Spec, in-scope Ticket set and dependency carrier, and DAG Run Authorization. A missing or ambiguous pointer pauses execution and requires one precise clarification rather than a guessed scope.

## Authority and Evidence

A DAG Run Authorization is an explicit user request to execute, advance, or continue an Approved DAG. It authorizes continuous locally auditable work without per-Ticket confirmation:

- claiming and updates in a local tracker carrier;
- Agent dispatch;
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

Each executable node is one Ticket. Ticket implementation, Implementation-Side Review, review sufficiency, Formal Review, acceptance, and bounded rework are gates inside the node, not additional dependency nodes.

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

The Runnable Frontier contains only unaccepted Tickets whose hard predecessors are Accepted Tickets, blockers are cleared, claim and acceptance evidence can be persisted under current authorization, required Agent profiles and capabilities are verified, and a safe write boundary is available without ownership conflict. A status string such as `ready-for-agent` or dependency readiness alone is insufficient.

## Roles and Execution Profiles

| Role | Responsibility | Required profile |
| --- | --- | --- |
| Coordinator | Live reconciliation, graph validation, scheduling, tracker state, evidence adjudication, rework or revision decisions, and final acceptance | `gpt-5.6-sol`, `max` |
| Execution Agent | One Ticket's implementation through Implementation Handoff | `gpt-5.6-sol`, `high` |
| Review Agent | Runs a fresh Code Review Skill when the Coordinator determines that existing review evidence is insufficient | `gpt-5.6-sol`, `high` |
| DAG-native Standards or Spec Reviewer | Supplies the corresponding independent review when the Code Review Skill is unavailable or inapplicable | `gpt-5.6-sol`, `high` |

The Coordinator verifies actual visible runtime metadata. A requested profile is not proof. A mismatch or unverifiable profile must be reported and corrected; the affected work pauses unless the user explicitly authorizes a substitute.

Only the Coordinator owns DAG and tracker state. Execution and Review Agents return artifacts and evidence but cannot accept Tickets, change graph state, or unlock successors.

## Start and Resume

The Skill has no command modes. On every authorized start or continuation, the Coordinator:

1. rereads applicable instructions, the live Spec, all in-scope Tickets, dependency and blocker evidence, tracker rules, Git state, test contracts, and existing formal-review evidence;
2. discovers the currently available `implement`, `code-review`, and any Target Project authoring Skills without trusting chat memory;
3. reconstructs and validates the DAG Projection;
4. reconciles already accepted, in-progress, blocked, superseded, and unclaimed Tickets against live Recovery Evidence;
5. computes the Runnable Frontier and available safe capacity.

The Skill never initializes Git. It preserves unrelated dirty work and does not manufacture a clean baseline with reset or clean.

Recovery Evidence must remain in the Target Project's existing tracker or repository evidence under its Tracker Contract, not in a DAG Skill scheduler file. For every started Ticket, it must reconstruct the current attempt and ownership, Review Fixed Point, Final Artifact Identity when available, consumed Operational Retry and Formal Rework, accepted findings and dispositions, acceptance evidence, and Ticket Lineage with any consumed automatic DAG Revision. If required evidence cannot be reconstructed or legally persisted, the Ticket is not Runnable and the Coordinator fails closed on that path.

## Continuous Scheduling

After authorization, the Coordinator continues without asking for confirmation after each Ticket:

1. finish formal review and acceptance work already in progress before opening more implementation work;
2. recompute the Runnable Frontier from live state;
3. choose the largest safe subset within available Agent capacity;
4. use tracker priority first, then obvious downstream-unlock or critical-path value, then stable Ticket identity when capacity requires a tie-break;
5. recheck and claim each selected Ticket immediately before dispatch;
6. advance each returned Ticket through evidence validation, Formal Review, and adjudication;
7. persist and reread acceptance evidence before unlocking successors;
8. repeat until Complete or genuinely Stalled.

Graph independence is necessary but not sufficient for parallel writes. A workspace has one write-capable Execution Agent at a time. Parallel implementations require Target Project-provided or explicitly authorized isolation and an integration boundary. If safety is uncertain, serialize. Read-only reviews may still run concurrently.

## Per-Ticket Flow

### 1. Dispatch

The Coordinator captures an immutable Review Fixed Point before implementation, then dispatches one fresh Execution Agent for exactly one Ticket.

When the installed `implement` Skill is available and applicable, the dispatch explicitly tells the Agent to use it as installed, including its required `code-review` step. That nested review is an Implementation-Side Review: its raw Standards and Spec artifacts are candidate evidence for the Coordinator, but neither the Execution Agent nor its reviewers may accept the Ticket or unlock successors.

The Coordinator supplies the Review Fixed Point, approved Spec and Ticket, applicable standards, and exact scope needed by the nested review. A nested Skill may not install prerequisites or mutate project configuration under DAG Run Authorization. If the required review context cannot be supplied safely, `implement` is inapplicable rather than partially followed.

If the Target Project is not a safe Git commit context, the installed `implement` Skill's commit contract is inapplicable rather than silently ignored.

If `implement` is unavailable or inapplicable, the Coordinator discloses DAG-Native Fallback and dispatches a fresh Execution Agent directly under the Target Project's live instructions, Spec, Ticket, and verification contracts. The fallback need not manufacture an Implementation-Side Review; missing reusable review evidence will cause the Review Sufficiency Gate to dispatch a fresh review. No fallback is represented as successful Skill use.

### 2. Implementation Handoff

The Execution Agent returns at least:

- Ticket identity and delivered scope;
- the actual changed files and commit when applicable;
- exact verification commands and outcomes, including failures and checks not run;
- raw Standards and Spec review artifacts, actual reviewer metadata, and the artifact identity examined by the Implementation-Side Review when available;
- any implementation change made after that review;
- deviations, unresolved risks, and blockers.

The Coordinator independently checks the live diff, commit, verification results, scope, repository state, review artifacts, reviewer independence, and artifact identities. A Worker completion claim or review summary is not an Implementation Handoff.

An Agent crash, tool failure, execution-profile mismatch, or invalid handoff permits one total corrected Operational Retry per Ticket attempt and does not consume the Rework Budget. Persist the consumed retry before redispatch. After that budget is consumed, any further operational failure blocks the Ticket; it does not create an automatic loop.

### 3. Review Sufficiency and Formal Review

After a valid handoff, the Coordinator identifies the immutable Final Artifact Identity and applies the Review Sufficiency Gate to the raw Implementation-Side Review evidence. Existing review evidence is sufficient only when:

- both raw Standards and Spec reports are available rather than only an Execution Agent summary;
- the reviewers did not implement the Ticket, their actual profiles are verified, and their contexts were fit for the assigned axes;
- both reports examine the same Final Artifact Identity and no implementation change followed that review;
- their scope and evidence are complete enough for the Coordinator to substantiate every finding disposition; and
- neither the Target Project's contract nor the change risk requires a fresh Coordinator-dispatched review.

When all conditions hold, the Coordinator adopts the Implementation-Side Review as the Ticket's Formal Review evidence and proceeds to adjudication without mechanically repeating the same review.

When the evidence is missing, stale, incomplete, contradictory, unverifiable, or inadequate for the risk, the Coordinator dispatches a fresh Review Agent with the Review Fixed Point, approved Spec and Ticket, applicable standards sources, commit list, and exact review scope. High-impact surfaces and any Target Project mandate are sufficient reasons to require the fresh review.

When `code-review` is available and applicable, the Review Agent explicitly uses it. Its Standards and Spec reviews remain independent and are returned side by side. The approved Spec always exists for this workflow; the Spec axis may not be silently skipped.

A reused Skill may not install prerequisites, mutate project configuration, or ask the user to repair missing review context under DAG Run Authorization. If its fixed point, diff, Spec, tracker, or other required inputs cannot be supplied safely, it is inapplicable and the Coordinator uses the disclosed fallback.

If `code-review` is unavailable or inapplicable, the Coordinator discloses DAG-Native Fallback and directly dispatches fresh, independent Standards and Spec Reviewers against the same Final Artifact Identity.

Any implementation change, amend, or rebase after an adopted or fresh review invalidates both review axes. The changed Final Artifact Identity must pass the Review Sufficiency Gate again.

### 4. Coordinator Adjudication

The Coordinator combines live implementation evidence with the separate review reports and gives every finding one evidence-backed disposition:

- valid and blocking within the Ticket;
- valid but requiring a graph change;
- advisory and non-blocking, with rationale;
- false positive, with evidence;
- unresolved.

An unresolved or valid blocking finding prevents acceptance. If no blocking issue remains, the Coordinator persists the Target Project's required acceptance state and evidence, rereads it, and only then allows successors into the Runnable Frontier.

## Rework and DAG Revision

Each Ticket has one Formal Rework. It begins only when the Coordinator accepts a blocking finding from adopted or freshly dispatched Formal Review evidence and returns the Ticket for implementation within the original scope. Persist the consumed rework before redispatch. Self-correction before handoff, duplicate findings, false positives, and Operational Retry do not consume it.

Formal Rework returns to the original Execution Agent when that Agent remains available with the required profile; otherwise a fresh `implement` Agent receives the complete accepted findings. Rework keeps the DAG topology unchanged. The resulting implementation receives a new Final Artifact Identity, new Implementation-Side Review evidence when `implement` applies, and another Review Sufficiency Gate before adjudication.

If valid blocking problems remain after Formal Rework, the Coordinator does not retry again or add a back edge. It determines whether to split the Ticket, add a prerequisite, reorder work, reject or defer scope, or record an external blocker.

When new or revised Ticket content is required, a current Target Project authoring Skill creates it. The DAG Skill owns the revision decision but does not author the replacement Tickets and has no authoring fallback. A semantics-preserving local revision may proceed under DAG Run Authorization after its rationale and provenance are recorded. A semantic, acceptance, or gate change requires user approval. The revised graph must pass the Whole-Graph Validity Gate before scheduling resumes, and displaced Tickets remain visible as superseded evidence.

Only one automatic semantics-preserving DAG Revision may be consumed by an original Ticket Lineage. Persist that consumption before scheduling the replacement subgraph. A further revision in the same lineage requires explicit user authorization; without it, leave the lineage unfinished with evidence and allow the run to become Stalled after independent branches finish.

## Terminal Outcomes

A blocked branch does not stop independent runnable branches.

An Agent counts as running only while its liveness remains observable; a lost Agent becomes an Operational Failure rather than holding the run open indefinitely. Complete and Stalled are mutually exclusive.

The run is **Stalled** only when unfinished Tickets remain, no Agent is running, and no Runnable Frontier exists. Every stopped path must have a live evidenced cause such as an external blocker, missing authorization, invalid graph, unavailable required capability, repeated operational failure, exhausted rework, or an exhausted automatic DAG Revision awaiting authoring or approval.

The effective graph excludes Superseded Tickets from execution while retaining their provenance and includes every approved replacement Ticket. The run is **Complete** only after every Ticket in that effective graph is accepted and the Coordinator passes a Whole-DAG Acceptance Gate covering:

- Approved Spec coverage;
- integration of predecessor outputs into dependents;
- current Final Artifact Identities and matching Ticket evidence;
- Target Project graph-wide verification gates;
- absence of unresolved findings, blockers, and unexplained in-scope changes;
- tracker, commit, and acceptance-evidence consistency.

Complete does not imply or authorize remote publication.

## Acceptance Criteria for Final Deliverables

The implementation is acceptable when:

- `SKILL.md` is the only runtime artifact and is written in accurate Agent-facing English;
- `README.md` is a concise Chinese human-facing companion that remains consistent with `SKILL.md` and is not a runtime dependency;
- it expresses implementation through `implement`, including its Implementation-Side Review, followed by the Coordinator's Review Sufficiency Gate, conditional fresh review through `code-review`, and Coordinator adjudication;
- it defines the disclosed DAG-native fallbacks without silently claiming unavailable Skill use;
- it keeps Ticket dependencies acyclic and bounds both Operational Retry and Formal Rework;
- it derives scheduling from live project evidence and the Target Project's Tracker Contract;
- it preserves Coordinator authority, same-final-bytes review, atomic acceptance-before-unlock, Safe Parallelism, and Whole-DAG final acceptance;
- it contains no project-specific tracker, authoring implementation, persistent state, CLI, or extra-file dependency;
- it does not broaden local authorization into remote or high-impact actions.
