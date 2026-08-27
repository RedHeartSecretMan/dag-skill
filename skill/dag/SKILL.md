---
name: dag
description: Coordinate an approved multi-Ticket dependency DAG from live project evidence through execution, review, integration, and whole-DAG acceptance. Use when the user asks to execute, advance, continue, or resume the DAG.
---

# Coordinate an Approved Ticket DAG

Act as the Coordinator Agent for an approved directed acyclic graph of delivery Tickets. Advance it from live Target Project evidence, using chat history and Agent reports as pointers to verify.

## Use three Agent roles

- The single **Coordinator Agent** owns claims, graph and tracker transitions, dispatch, evidence adjudication, DAG Integration Branch promotion, rework and revision decisions, Ticket acceptance, and successor unlocking.
- An **Execution Agent** implements exactly one Ticket in its isolated Ticket Workspace through one finite dispatch and returns an Implementation Handoff or Blocked Handoff. Graph-independent Tickets may use separate Execution Agent instances concurrently.
- A **Review Agent** independently inspects one fixed artifact along the Standards axis, Spec axis, or a targeted scope. Multiple Review Agent instances may cover separate axes concurrently.

Every Agent returns evidence to the Coordinator Agent, and completion rests on integrated evidence that the Coordinator Agent verifies. Ticket Worker Protocol and Worker Self-Check name Execution Agent workflows; Standards and Spec name Review Agent axes.

## Establish the run

1. Resolve the Target Project, Approved Spec, in-scope Tickets and dependency carrier, and the user's authorization to execute, advance, continue, or resume the DAG. Keep the Runnable Frontier empty until one precise clarification resolves any ambiguous pointer.
2. Read the live instruction hierarchy, domain and engineering documents, Tracker Contract, Approved Spec, Tickets, repository state, tests, and review evidence.
3. Verify that the Agent Host can dispatch fresh role-isolated contexts, provide write-capable Execution Agent and read-only Review Agent boundaries, expose liveness and terminal state, and access the Target Project's evidence and tools. Tickets may run serially; any nested concurrency required by a validated supporting Skill remains an entry capability.
4. Resolve and validate the complete Runtime Skill Bundle: `code-review`, `tdd`, and `codebase-design` from `mattpocock/skills` revision `5b15a47f2d7150f545fbcacbfe381787fc0230dc`. Verify each resolved identity, referenced file, immutable content identity, live contract, and model-invoked host path. Prove that the Execution Agent can execute `tdd` at the Ticket's public test seams and obtain fresh independent Standards and Spec reports for a non-empty committed Ticket diff through `code-review`, directly or through a Coordinator Agent relay that returns the reports to the same Execution Agent for closure. Also prove that the Coordinator Agent can dispatch fresh read-only Review Agents for the zero-delivery current-state review defined below. Record host-specific policy and provenance fields when exposed.
5. Treat the Runtime Skill Bundle and the Target Project's live `code-review` prerequisites as the entry gate. With separate setup authorization, Python 3.12+, and an explicit host Skills root, use `scripts/install_dependencies.py --skills-root <host-skills-root>` relative to this Skill to install the pinned runtime Skills and `setup-matt-pocock-skills` helper. A Target Project whose live prerequisites already pass proceeds directly. When setup is required, ask the user to run the installed helper, then reread its output and validate the complete runtime path before claiming a Ticket.
6. Identify the Target Project's governed Spec/Ticket Authoring Process. Discover live models, reasoning controls, tools, and runtime metadata, then build a run-scoped Agent Profile for each role:
   - exact user or Target Project model, Agent, and reasoning requirements are hard constraints;
   - otherwise match the Coordinator Agent, Execution Agent, and Review Agent profiles to capability, context, tools, complexity, and risk;
   - establish review independence with fresh role context; model diversity remains optional unless required;
   - record exposed metadata and represent unavailable fields as unknown.
7. Explain any exact-profile mismatch, recommend available alternatives, and obtain authorization before substitution. A post-dispatch mismatch that invalidates evidence enters Operational Recovery.
8. For a Git-backed Target Project, resolve the Approved Baseline, the existing or new run-scoped DAG Integration Branch, the Coordinator Agent's isolated worktree, every existing Ticket Workspace, and the local and remote branch tips. When the project has a configured writable remote, select the exact remote and remote DAG branch and obtain one run-scoped Remote Checkpoint Authorization before Ticket scheduling.

## Recover the entry baseline

Run the Target Project's entry checks in a project-governed execution context. When a check fails, preserve the exact evidence and classify it before changing the graph:

- **Host environment variance**: prove that host-global configuration, permissions, cache state, or tool placement caused the difference; establish one reproducible run-level environment and rerun the unchanged gate. The normalized environment may remove host variance while preserving dependencies, acceptance, and every gate.
- **Target baseline defect**: use the Spec/Ticket Authoring Process to append the smallest semantics-preserving prerequisite repair Ticket, then validate and schedule that node under DAG Run Authorization.
- **Graph contract defect**: repair the affected Ticket, seam, or dependency through a semantics-preserving DAG Revision and revalidate the graph.
- **Authority or semantic boundary**: record the affected nodes and closing condition, continue independent branches, and obtain user authorization for the required semantic, acceptance, gate, or High-impact change.
- **Unresolved cause**: keep affected nodes unclaimed while gathering evidence; preserve their Attempt and Formal Rework state and continue independent work.

Treat an entry failure as actionable by the Coordinator Agent while an authorized environment correction, baseline repair, graph repair, or independent Runnable branch exists. Claim a Ticket only after its applicable entry condition is current and satisfied.

## Work within authority

DAG Run Authorization covers continuous, locally auditable coordination under the Target Project's contract:

- local Ticket claims, tracker evidence, and state transitions;
- Agent dispatch;
- a run-scoped DAG Integration Branch and the Coordinator Agent's isolated worktree;
- one ticket-scoped branch and worktree per active Ticket;
- ticket-scoped implementation, verification, and commits in a safe Git context;
- project-governed candidate alignment with the pre-alignment identity preserved as Recovery Evidence;
- semantics-preserving local Ticket repairs and DAG Revisions through the Target Project's governed process;
- local integration, acceptance evidence, and successor unlocking.

Remote Checkpoint Authorization covers ordinary fast-forward publication of the selected DAG Integration Branch after each DAG Milestone, followed by remote-ref readback. Obtain it once for the run, then execute every checkpoint without repeated confirmation. Remote tracker writes, other pushes, pull requests, tags, releases, deployment, external API or database writes, state-changing remote CI, destructive Git, product-semantic or acceptance changes, and gate weakening retain separate authorization.

Trace every approval boundary to current Normative Authority. Agent-authored State Evidence carries an approval condition only when that condition already follows from user scope or the Target Project's governing contracts; it does not narrow or expire DAG Run Authorization. Treat revision and recovery counts as audit evidence, while Structural Progress and the High-impact boundary determine whether work may continue.

Preserve the repository's live baseline and unrelated work. Classify pre-existing changes as the current Ticket candidate, protected unrelated work, or unaccepted evidence; adopt unaccepted work only through a live approved Ticket.

## Reconstruct the live graph

Represent each executable node as one approved Ticket with an authoritative identity, one delivery objective, scope boundaries, dependency inputs, downstream outputs, acceptance and verification requirements, one or more pre-agreed public test seams, current state, ownership, and blockers.

Before claim, derive a **Ticket Execution Contract** from the approved Ticket and its accepted direct inputs. Its minimum complete form identifies the owned acceptance obligation, consumed accepted inputs or an evidenced empty input set, delivered output, every acceptance requirement mapped to at least one public probe and observable result, scope and out-of-scope, and required gates. Add equivalence classes, state transitions, and forbidden outcomes when live Normative Authority defines them or an acceptance requirement needs them for execution. Record an inapplicable optional field as `N/A` with its source or rationale. Keep the contract a projection of approved meaning; hold the Ticket when a required field cannot be derived without changing semantics, then route it through the Spec/Ticket Authoring Process, DAG Revision, or the required authority decision.

Orient each dependency edge `prerequisite -> dependent` when the dependent consumes an accepted output of the prerequisite. Keep preferred order, similar files, shared ownership, implementation phases, and external blockers as scheduling facts.

On every start or continuation:

1. project the live tracker carrier into a carrier-neutral DAG view while retaining the Target Project as authority;
2. validate unique nodes, complete Ticket contracts and public test seams, defensible edges, acyclicity, hard-dependency coverage, and acceptance evidence;
3. retain Superseded Tickets as provenance and schedule their approved replacements;
4. reconcile accepted, in-progress, blocked, superseded, and unclaimed Tickets from live evidence.

When a public test seam or another required Ticket Execution Contract field is missing, hold that node before claim. A semantics-preserving Ticket repair proceeds through the Target Project's governed process under DAG Run Authorization; a change to approved acceptance or product semantics requires user authorization.

Use the Target Project's tracker or repository as the recovery store. For every started Ticket, reconstruct:

- Runtime Skill Bundle identities and activation state;
- Ticket Attempt identity, ownership, blockers, the availability or consumption of its single implementation continuation, the source Handoff, continuation candidate and closing condition, Formal Rework state, and Ticket Lineage;
- operational causes, Invocation Corrections, Operational Recoveries, and closing conditions;
- Coordinator Agent, Execution Agent, and Review Agent profiles, progress checkpoints, observed states, and evidence-bearing milestones;
- Ticket Execution Contract, Ticket Base, Ticket Workspace, Review Candidate, Final Candidate, pre-handoff review identities and raw reports, Review Fixed Point, Final Artifact Identity, DAG Integration Branch and reachability, verification commands and outcomes, findings, and dispositions;
- selected remote and remote DAG branch, last verified Remote Checkpoint, and any pending checkpoint cause;
- DAG Revisions, violated obligations, causal mechanisms, owning seams, prior effective shapes, gate outcomes, Structural Progress, and acceptance evidence.

Maintain a compact **Run Receipt** in an existing tracker or repository evidence location allowed by current authority. Index the current DAG Milestone, last recorded and pending remote checkpoints, Runnable Frontier, active Ticket Attempt/Base/Candidate/Workspace identities, implementation-continuation state, Agent checkpoints, pending gates or reviews, graph identity, and live closing conditions. Point to detailed Recovery Evidence instead of copying raw reports or long lineage, and update the receipt only at evidence-bearing milestones. A repository-backed receipt records the preceding verified checkpoint and the closing condition for its own publication; matching local and remote refs complete that condition and serve as the receipt's terminal checkpoint evidence.

A Ticket becomes Runnable after its recovery evidence is reconstructable and persistable under the Tracker Contract. A cross-task handoff completes when the receiving Coordinator Agent rereads the live project, reconstructs this evidence, and recomputes the frontier.

On resume, treat matching local and remote DAG refs as a verified checkpoint. When the local branch is ahead by known DAG Milestones, complete the pending Remote Checkpoint before accepting that milestone, unlocking dependent successors, or promoting another candidate. A graph-independent Ticket may start or resume from the last checkpointed accepted tip when its contract does not consume the pending milestone. An unknown remote-only commit or divergence enters Operational Recovery or an Operational Blocker according to the observed cause.

For each claimed or in-progress Ticket, reconcile the prior dispatch identity, liveness, workspace, and latest trusted milestone. Resume from a current completed milestone. When a prior dispatch is no longer observable, first establish a quiescent or isolated write boundary and mark it terminal or superseded, then recover its missing evidence by cause within the same Ticket Attempt. Keep ownership unchanged while the prior write boundary remains live or uncertain.

## Compute and schedule the frontier

Include a Ticket in the Runnable Frontier when:

- its acceptance state is open;
- every hard predecessor is accepted;
- blockers are cleared;
- its Ticket Execution Contract contains every minimum required field, including one or more pre-agreed public test seams and a complete acceptance-to-probe map;
- current authorization supports claiming and evidence persistence;
- a suitable Agent Profile and required capabilities are verified;
- a Ticket Workspace isolates its candidate from the DAG Integration Branch until promotion.

Use ready-like tracker statuses as inputs to this calculation. Prioritize handed-off candidates without idling graph-independent implementation capacity, and recompute the frontier after every claim, handoff, acceptance, block, recovery, or graph revision.

Select the largest safe frontier subset whose direct and nested Agent demand fits current capacity. Use serial scheduling when demand is uncertain. Break capacity ties by tracker priority, downstream-unlock or critical-path value, then stable Ticket identity.

Run graph-independent Tickets concurrently in isolated Ticket Workspaces. Keep one write-capable Execution Agent per workspace. Read-only review of different fixed candidates may proceed concurrently. Serialize candidate alignment, promotion, and Remote Checkpoint through one integration lane owned by the Coordinator Agent; review or gates join that lane only when alignment creates a relevant delta.

Give every directly dispatched Agent a bounded progress checkpoint. Valid outcomes are a new evidence-bearing milestone that reduces or clarifies remaining work, an evidenced blocker, or a terminal result. Correct an invocation that did not reach its intended action at the same checkpoint. A repeated or non-advancing outcome after a cause-specific correction becomes an Operational Blocker.

Maintain the continuous loop until **Complete** or **Stalled**: dispatch the safe Runnable Frontier, wait or monitor to the earliest bounded checkpoint or terminal event, reconcile returned artifacts against live evidence, advance affected Tickets, persist authorized transitions, recompute the graph and frontier, and repeat. An empty frontier with observable running Agents is a waiting state. An empty frontier with an authorized recovery or graph transition remains actionable by the Coordinator Agent.

## Advance one Ticket

A **Ticket Attempt** begins with the initial claim or the single Formal Rework. Persist its identity, Ticket Base, Ticket Workspace, and whether its single implementation continuation remains available. Coordinator-directed continuation, review, integration, Invocation Correction, and Operational Recovery remain within that identity. An evidenced external blocker suspends the Attempt with its ownership, milestones, and closing condition intact. The Attempt ends when the Ticket is accepted, superseded, or replaced by its Formal Rework Attempt.

### 1. Confirm the contract, claim, and create the Ticket Workspace

Immediately before claim, reread the Ticket, direct accepted inputs, blockers, repository, tracker, and Runtime Skill Bundle identities. Confirm and persist its Ticket Execution Contract. Then claim the Ticket under the Tracker Contract, capture the current accepted DAG Integration Branch tip as the immutable Ticket Base, and create or resume one ticket-scoped branch and isolated worktree from it. For graph-independent work during a pending Remote Checkpoint, use the last checkpointed accepted tip. Persist the Attempt's recovery evidence before dispatch.

### 2. Dispatch the Execution Agent

Dispatch one fresh Execution Agent for exactly one Ticket. Supply its Agent Profile, Target Project instructions, Ticket Execution Contract, relevant Approved Spec clauses, Ticket, direct accepted dependency outputs, Ticket Base, Ticket Workspace, and authorization boundary. Use source pointers for additional evidence and omit unrelated Tickets, lineage, and review history from the initial context.

For an initial or Formal Rework dispatch, the Ticket Worker Protocol requires the Execution Agent to:

1. reread the live Ticket Execution Contract, direct accepted inputs, repository baseline, applicable project instructions, and relevant existing evidence in its fresh context;
2. keep all work within that contract, Ticket Workspace, and authority; return a Blocked Handoff when live evidence contradicts the approved contract or requires graph or semantic change;
3. use the validated `tdd` Skill to implement the Ticket through its agreed public seams, and `codebase-design` when an applicable seam or module boundary needs design;
4. for every applicable changed behavior, observe a causal RED against the pre-implementation behavior, implement the target behavior, and observe GREEN from that implementation; use equivalent before-and-after proof for non-behavioral obligations, and use the baseline-satisfaction route below when no delivery change is required;
5. run focused checks during implementation, then run every applicable final-byte project gate and freeze an immutable clean Review Candidate commit;
6. for a non-empty Ticket delta, request one complete, independent, read-only `code-review` pass with the Ticket Base as fixed point plus the relevant Spec clauses, Ticket, standards sources, commit list, acceptance-to-probe map, and exact scope; invoke it directly when supported, otherwise return a review-request checkpoint so the Coordinator Agent can dispatch fresh Review Agent contexts and relay both raw reports to the same Execution Agent;
7. inspect both raw reports and respond to every finding. When no credible in-scope blocker remains, keep the Review Candidate as the Final Candidate and return an Implementation Handoff. Preserve graph-changing, external, and unresolved credible blockers in a Blocked Handoff;
8. when the review reports repairable in-scope blockers, select the credible findings to repair and perform one review-driven repair phase: reproduce each behavioral repair target with causal RED, implement the smallest contract-preserving repair to GREEN, capture equivalent proof for non-behavioral repair targets, rerun affected and applicable final-byte gates, freeze a clean Final Candidate, and map its complete delta to the repair targets and proof;
9. request one independent, read-only **Targeted Closure Review** limited to the repair-target findings, repair delta, and directly affected contract surface. PASS returns an Implementation Handoff. FAIL returns a Blocked Handoff with the remaining findings and exact evidence. This terminal review transfers control to the Coordinator Agent through that Handoff.

A valid causal RED exercises the live Ticket Execution Contract through an agreed public seam and delivered seam where applicable. It fails because the target behavior is missing or wrong, rather than because of environment, import, fixture, mock, or unrelated failure. GREEN uses the same causal probe and results from implementing the target behavior without weakening the test, acceptance, or gate.

Classify an initially GREEN probe before changing delivery bytes:

- when the probe lacks discrimination, refine it within the approved acceptance-to-probe map and obtain causal RED for the missing behavior;
- when only part of the contract already exists, target the missing obligation and continue the ordinary TDD flow;
- when the seam is wrong or the live contract conflicts with the baseline, return a Blocked Handoff for contract repair, DAG Revision, or the required authority decision;
- when the Ticket Base already appears to satisfy the complete Ticket Execution Contract, run every applicable final-byte gate and use the immutable Ticket Base as both Review Candidate and Final Candidate. Return a review-request checkpoint so the Coordinator Agent can dispatch fresh read-only Review Agents directly over the fixed Ticket-owned artifact, contract surface, probes, and results; this current-state review is the explicit zero-delta path, while the diff-based `code-review` Skill remains assigned to non-empty Ticket deltas. Relay both raw reports to the same Execution Agent. A supported non-blocking disposition for every finding returns an Implementation Handoff with baseline-satisfaction proof and zero delivery delta; a bounded missing Ticket obligation refines the probe to causal RED and enters the ordinary TDD flow; a graph-changing, external, or unresolved blocker returns a Blocked Handoff.

Keep the candidate isolated from the DAG Integration Branch until promotion. Review Agents remain fresh and read-only; code changes belong to the Execution Agent. Each Execution Agent dispatch ends with exactly one Implementation Handoff or Blocked Handoff. A review-request checkpoint may pause the dispatch for Coordinator relay, but it does not complete the dispatch.

The Worker Self-Check clears only when the Final Candidate has current applicable gates, complete raw Standards and Spec reports, an evidenced response for every finding, complete terminal review coverage for every repair, a complete Review-Candidate-to-Final-Candidate delta map, and no unresolved credible in-scope blocker. Use Targeted Closure Review only when the complete repair delta maps to bounded repair targets and its affected contract and review surface are established; obtain complete Worker review when that coverage boundary cannot be established or expands. Additional independent review belongs to the Coordinator Agent's post-handoff risk decision.

### 3. Validate the handoff

A valid Implementation Handoff contains:

- Ticket identity, Ticket Execution Contract, delivered scope, changed files or zero delivery delta, Ticket Base, Review Candidate commit, and Final Candidate commit;
- the acceptance-to-probe map, causal RED-to-GREEN, baseline-satisfaction, or equivalent proof, and exact verification commands, contexts, and actual outcomes;
- both raw Standards and Spec reports with Review Agent profiles, an evidenced response for every finding, the terminal review that covers each repair, the complete Review-Candidate-to-Final-Candidate delta map, and the final candidate artifact identity;
- each failure classified as an introduced regression, evidenced baseline exception, operational failure, external blocker, or unverified result;
- actual Agent Profile, deviations, risks, and blockers.

A valid Blocked Handoff preserves the same available identities and evidence, the latest clean candidate when one exists, every completed milestone, the exact blocker, affected contract surface, and a concrete closing condition or the evidence that no bounded closure is available.

Verify the live diff, candidate commit, repository state, Ticket Execution Contract, probe causality, scope, gates, review reports, artifact identity, delivered public seam, and generated or dependency-lock changes. Reproduce claimed environment, tool, or probe failures in a suitable authorized context; otherwise retain the unverified classification.

The handoff clears its verification gate when the Coordinator Agent verifies the Worker Self-Check completion criteria against the live commits and evidence. A Blocked Handoff preserves progress and routes the cause without clearing this gate.

Route a failed handoff by its evidenced cause:

- an invocation that did not reach the intended action receives an Invocation Correction at the same checkpoint;
- missing, corrupt, or unverifiable evidence caused by an Agent, tool, profile, report, or integration failure enters Operational Recovery;
- a Blocked Handoff whose closing condition is a bounded in-scope repair, or another pre-clearance in-scope implementation defect, may receive the Ticket Attempt's single Coordinator-directed implementation continuation only when the prior dispatch is terminal, its result contains a new evidence-bearing milestone, and the next finite dispatch has a concrete closing condition; persist consumption plus the source Handoff, latest trusted candidate, repair target, and closing condition before dispatch;
- an evidenced external blocker suspends the Ticket with an owner and closing condition;
- a graph-changing objective, seam, scope, or semantic issue returns to the Coordinator Agent for DAG Revision or the required authority decision.

Persist coexisting failures and choose the most substantive evidenced route. When the single implementation continuation does not clear the handoff gate, its boundary is exhausted. Record the unresolved acceptance obligation, failed repair shape, latest candidate, and a recovery condition requiring new evidence, capability, authority, or Structural Progress; then route the Ticket to the applicable Operational Recovery, DAG Revision, evidenced blocker suspension, rejection, or deferral. Complete missing pre-handoff evidence within the current Ticket Attempt. After the Coordinator Agent records gate clearance, a later accepted in-scope implementation defect uses Formal Rework.

For the single implementation continuation, preserve the Ticket Attempt, Ticket Base, branch, and Ticket Workspace. Dispatch a fresh Execution Agent from the latest trusted candidate with the verified Blocked Handoff or defect evidence, bounded repair target, and closing condition. The new dispatch uses TDD for that target, reruns affected and applicable final-byte gates, freezes a clean continuation candidate, and extends the complete candidate-delta map. Reuse complete current review evidence: when it does not cover every changed and unchanged review surface, freeze that commit as the new Review Candidate and obtain complete Worker review; when it remains complete for unchanged scope and the repair delta has a bounded coverage boundary, freeze the commit as the continued Final Candidate and request one Targeted Closure Review over the bounded repair, prior remaining findings, and directly affected surface. Whichever review path applies is the continuation's terminal checkpoint: a passing result returns an Implementation Handoff and a blocking result returns a Blocked Handoff.

## Recover operational failures

Classify recovery by what actually happened:

- **Invocation Correction** applies when a command, path, patch, dispatch request, capacity allocation, or approval attempt did not start or reach the intended action. Correct the input or execution boundary and continue the same checkpoint.
- **Operational Recovery** applies when the intended action began but an Agent, tool, profile, report, or integration failure prevented valid evidence. Record the cause and correction, then rerun that cause once in a suitable authorized context within the same Ticket Attempt.
- **Operational Blocker** applies when the same cause repeats after its correction without an advancing milestone, or when its closing condition requires unavailable capability or authority.

A new operational cause after an evidence-bearing milestone is a new failure episode; earlier recovery does not consume it. Promote a repeated host-wide cause to the run environment, establish one verified correction, and apply that context to later Tickets.

Implementation and review recovery redispatch the corresponding role when needed. Integration recovery remains owned by the Coordinator Agent. Before write-capable redispatch, establish the prior writer's terminal or superseded state plus a quiescent or isolated write boundary. Persist any blocker and closing condition before recomputing the graph.

Formal Rework and DAG Revision state remain unchanged during Operational Recovery. An evidenced blocker becomes a graph decision when it requires a new prerequisite, split, reorder, rejection, or deferral.

## Classify change impact

Classify every post-gate or post-review delta by its effect:

- a **Delivery-affecting Change** can alter accepted behavior, tests, dependencies, generated delivery artifacts, required gates, or acceptance-bearing documentation; rerun its affected and applicable final-byte gates and cover its review surface;
- an **Evidence-only Change** records tracker state, identities, gate outcomes, review summaries, Finding Dispositions, graph evidence, or remote readback without changing a delivery surface; verify the delta with the Target Project's applicable tracker, format, secret, diff, graph, and targeted consistency checks;
- a byte-preserving alignment replays the reviewed Ticket delivery delta unchanged onto already accepted bytes without conflict resolution or a changed review surface; retain current delivery evidence after applicable integration and location- or history-sensitive gates pass.

Classify by contract effect rather than path name. Bind gate and review evidence to the fixed candidate, relevant inputs, gate definitions, execution context, and verified scope. Run the complete delivery gate set once for each stable set of final delivery bytes and again after a Delivery-affecting Change or when one of those bindings is no longer current. An evidenced Evidence-only descendant does not invalidate current delivery gates or review while those bindings remain current.

### 4. Establish post-handoff review evidence

Freeze the handed-off Final Candidate while the Coordinator Agent applies the Review Sufficiency Gate against its Ticket Base and Ticket Execution Contract. The Coordinator Agent may:

- adopt the Worker review when both raw axes are complete and independent, the Final Candidate has current gates, every finding has evidence, every repair has passing terminal review coverage, and the complete post-review delta adds no uncovered concern;
- dispatch a fresh **Targeted Formal Review** when one bounded request over an identifiable finding, repair delta, contract surface, or other bounded risk can close the remaining uncertainty;
- dispatch complete fresh Standards and Spec Review Agents when the coverage boundary cannot be established or the Target Project requires complete review.

Use complete fresh review when the targeted request cannot close the gate in one dispatch or its scope expands during review.

Different fixed candidates may undergo read-only review concurrently within Agent capacity. Give every Review Agent the relevant Spec clauses, Ticket Execution Contract, fixed base and candidate identities, standards sources, commit list, acceptance-to-probe map, and exact scope. Each report includes the observed Agent Profile, artifact identities, raw findings, and actual verification. A failed launch receives Invocation Correction; a timeout or missing report enters cause-scoped Operational Recovery. Reconcile every Review Agent after terminal or explicitly superseded state.

### 5. Adjudicate

Inspect the implementation evidence and raw review results. A blocking finding maps to current Ticket acceptance or a direct accepted-input contract, has a causal reproduction or direct code path on the fixed candidate, identifies the root behavior class or state transition where applicable, and belongs to the current Ticket's scope under the Target Project's mandatory standards. Give every finding one supported disposition:

- blocking within the Ticket's approved scope;
- valid but graph-changing;
- advisory, with non-blocking rationale;
- false positive, with evidence;
- unresolved.

Promotion becomes available after all mandatory Target Project, Spec, and Ticket violations are resolved and every finding has a supported non-blocking disposition. Route graph-changing findings through DAG Revision; semantic, acceptance, and gate changes require user authorization. A disposition that changes or abandons the fixed candidate preserves its evidence before Formal Rework, DAG Revision, suspension, rejection, or deferral.

### 6. Align and prepare the promotion candidate

Enter the serialized integration lane after post-handoff review and adjudication pass. Reread the DAG Integration Branch, record the pre-alignment candidate identity, and align the ticket branch onto its current tip using the Target Project's merge or rebase policy. The aligned candidate must contain that tip as an ancestor and keep its Ticket diff bounded to the approved scope.

Classify the alignment delta. A byte-preserving or Evidence-only alignment remains in the current Ticket Attempt and retains review and delivery evidence after its applicable targeted and integration checks pass. A conflict or alignment that requires Delivery-affecting implementation changes uses the remaining Formal Rework; exhausted Formal Rework or scope drift enters DAG Revision. Operational failures in alignment remain Operational Recovery owned by the Coordinator Agent.

Run every affected integration, delivered-public-seam, and location-sensitive acceptance gate required by the classified delta. An implementation failure uses the remaining Formal Rework; an evidenced baseline, operational, external, or graph-contract failure follows its corresponding route. Capture the current DAG Integration Branch tip as the immutable Review Fixed Point and freeze the aligned candidate commit as the Final Artifact Identity.

Reapply the Review Sufficiency Gate to the alignment delta. Retain prior reports for verified unchanged scope, dispatch Targeted Formal Review for a bounded review-relevant delta, and obtain complete fresh review when the changed coverage boundary cannot be established. Adjudicate every resulting finding under step 5. Promotion proceeds only after all alignment-delta findings have supported non-blocking dispositions; an in-scope blocking finding uses the remaining Formal Rework, and a graph-changing or authority-bound finding follows its corresponding route. Preserve the aligned candidate and release the integration lane before a disposition changes or abandons it. Hold the lane through successful delta closure, promotion, and any required Remote Checkpoint so another promotion cannot stale the fixed point.

### 7. Promote, checkpoint, and accept

Immediately before promotion, verify that the DAG Integration Branch still equals the Review Fixed Point and the aligned candidate still equals the reviewed Final Artifact Identity. An identity mismatch preserves the candidate as evidence and returns to live reconciliation. Otherwise advance the DAG Integration Branch to that candidate with a fast-forward-only operation, update the Coordinator Agent's worktree, and verify the resulting commit and content identities.

Persist and reread the promotion identity and every repository-backed acceptance record that the Tracker Contract permits before remote readback. Treat a verified receipt-only commit as an Evidence-only Change and retain the reviewed delivery identity it cites. The resulting locally verified DAG Integration Branch tip is the DAG Milestone for this Ticket.

When a configured writable remote and Remote Checkpoint Authorization apply, publish the selected DAG Integration Branch to the selected remote branch with an ordinary fast-forward push, then reread the remote ref and require it to equal the local DAG Milestone. Treat a transient publication or readback failure as Operational Recovery owned by the Coordinator Agent and keep the local milestone intact. A non-fast-forward rejection or unknown remote divergence becomes an Operational Blocker with the observed refs and closing condition; reconciliation preserves locally verified commits and uses a new authorization for any non-fast-forward remote change.

After the required Remote Checkpoint agrees, persist and reread the Accepted transition under the Tracker Contract. When that transition must follow remote readback and creates a new DAG-branch commit, classify it as an Evidence-only finalization DAG Milestone, perform its required Remote Checkpoint without rerunning delivery gates or review, and reread acceptance. Use matching local and remote refs as terminal checkpoint evidence and fold their summary into the next otherwise-required Run Receipt update. Unlock successors after the integrated Final Artifact Identity, verification, Formal Review, finding dispositions, scope, final DAG Milestone, and acceptance evidence agree. A pending checkpoint or acceptance write holds the integration lane, milestone acceptance, and dependent successors. Graph-independent Ticket Workspaces may continue or start from the last checkpointed accepted tip when their contracts do not consume the pending milestone. Retire a clean terminal Ticket worktree after its commit and recovery evidence remain reachable.

## Bound rework and revise the graph

Each Ticket has one Formal Rework for an in-scope blocking finding that the Coordinator Agent accepts after the candidate cleared the Implementation Handoff gate, including a finding discovered during post-handoff review, alignment, or integration. Persist its consumption, open the second Ticket Attempt from the current accepted DAG Integration Branch tip with a new Ticket Base and Ticket Workspace, and provide the complete accepted findings to a fresh suitable Execution Agent. The Formal Rework repeats the complete finite Ticket Worker Protocol from its initial probe through its terminal Handoff.

Move to DAG Revision when blockers remain after Formal Rework, evidence reveals multiple independently acceptable delivery results, a missing prerequisite, an owning-seam defect, an invalid dependency, or an operational blocker reveals missing graph work. Additional public test seams update the Ticket contract, and diff size informs review scoping. Enter DAG Revision from either fact when it evidences one of these graph conditions. Before proposing a revision, the Coordinator Agent records:

- the failed Ticket and Ticket Lineage;
- the violated acceptance obligation and observable public seam;
- the causal mechanism and the interface or seam that owns the violated invariant;
- the affected dependency input, downstream output, or graph edge;
- the effective shapes and outcomes of prior failed revisions in the lineage;
- the proposed structural response and its governing authority.

Apply the **Revision Progress Gate** to the proposed graph change. A semantics-preserving local revision proceeds under DAG Run Authorization when it:

- preserves approved product semantics, acceptance, gates, acyclicity, and Ticket Lineage;
- records the contradicted evidence, revision rationale, and predecessor-to-successor acceptance mapping;
- demonstrates Structural Progress through narrower acceptance ownership, a consumed prerequisite, an invariant assigned to its owning seam, a corrected dependency, or an evidenced rejection, deferral, or blocker; every executable replacement must differ from each failed ancestor in a cause-addressing part of its effective objective, acceptance ownership, hard dependencies, or owning seam.

Choose the smallest complete graph transition that passes this gate:

- correct dependency edges directly when the Ticket contracts remain valid;
- use one replacement Ticket when one delivery objective, causal mechanism, and owning seam form one independently acceptable result;
- use a replacement subgraph when the work contains multiple independently acceptable results or an evidenced prerequisite-to-consumer relationship;
- record a supported rejection, deferral, or blocker when the current authority and evidence provide no executable replacement.

A replacement subgraph passes the **Split Independence Gate** when every executable child has a distinct non-empty acceptance responsibility, one or more public test seams, and acceptance that can be decided from its accepted hard-predecessor outputs plus its own artifact and public seams. Assign each unresolved parent acceptance obligation to exactly one child. A child may retain the complete set of unresolved parent acceptance obligations when it consumes a newly evidenced prerequisite from another child; otherwise its owned parent obligations form a strict subset of the unresolved parent obligations. A child without a mapped parent obligation produces a newly evidenced prerequisite output consumed by one or more named successors. Place combined behavior in a convergence Ticket only when the combination adds its own public contract. Keep files, functions, implementation phases, and individual review findings as implementation facts inside the Ticket that owns their accepted result.

A proposal is an **Equivalent Revision** when its effective delivery objective, acceptance ownership, hard dependencies, and owning seam all match a failed ancestor under a new identity. It does not enter the graph. Preserve the failed proposal as evidence, then select a structurally advancing shape or record the supported rejection, deferral, blocker, or authority condition.

A Ticket Lineage may receive further revisions whenever each proposed shape passes the Revision Progress Gate; revision count remains audit evidence rather than a continuation or authorization boundary. Reobserving the same causal mechanism can justify a new structural response, while returning to any failed effective shape cannot.

When the unresolved obligation already has Independent Acceptance and no narrower ownership, consumed prerequisite, owning-seam change, dependency correction, or supported disposition is available, persist the blocker and its closing condition instead of creating another Ticket. Obtain user authorization when continuation requires a product-semantic, acceptance, gate, remote, destructive, or other High-impact change. Use the Target Project's Spec/Ticket Authoring Process for every accepted revision, retain displaced Tickets as Superseded, and revalidate the whole graph before scheduling.

When a governed local DAG Revision advances the DAG Integration Branch, treat its verified tip as a DAG Milestone and complete the required Remote Checkpoint before scheduling nodes that depend on that revision.

A valid late finding or Whole-DAG failure freezes dispatch, integration, and acceptance across the subgraph that consumed the contradicted output. Bring active affected Agents to verified terminal or superseded state, establish quiescent write boundaries, and preserve candidates as unaccepted evidence. Invalidate contradicted acceptance evidence within current authority, then use remaining Formal Rework or a semantics-preserving remediation lineage before recomputing the graph.

## Reach a terminal outcome

Continue independent Runnable branches while another branch is blocked. Count an Agent as running while liveness is observable and its checkpoint remains valid. Report and persist progress at evidence-bearing milestones; unchanged waits and liveness observations retain the current Run Receipt.

Count an approval-dependent closing condition only when it cites current Normative Authority. When Agent-authored State Evidence adds an unsupported retry, recovery, or revision boundary, record it as non-authoritative, correct it where current authorization permits, and continue the already authorized path.

Report **Stalled** only when effective Tickets remain unfinished, running Agent count is zero, the Runnable Frontier is empty, and no authorized Invocation Correction, Operational Recovery, entry repair, Ticket repair, DAG Revision, or independent branch can make progress. Give every stopped path its live evidenced cause, authority source where applicable, and closing condition.

Report **Complete** after every effective Ticket is accepted and the Whole-DAG Acceptance Gate verifies:

- complete Approved Spec coverage;
- every accepted candidate on the DAG Integration Branch and every accepted predecessor output consumed by dependents;
- every required Remote Checkpoint aligned with its local DAG Milestone;
- current Final Artifact Identities aligned with Ticket and review evidence;
- all Target Project graph-wide verification gates;
- resolved findings, blockers, and in-scope changes;
- tracker, commit, Ticket Lineage, and acceptance-evidence consistency.

Return an evidence-backed summary of accepted, superseded, and stalled Tickets; verification performed and omitted; review dispositions; graph revisions; local and remote DAG branch identities; and pending High-impact Operations. Complete includes authorized DAG-branch checkpoints when the run has a configured writable remote. Main-branch integration, pull requests, tags, releases, and other publication remain separately authorized.
