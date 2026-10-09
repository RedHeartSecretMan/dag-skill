# Execute one Ticket

Read this protocol completely when dispatched or resumed as the **Execution Agent** for one claimed Ticket. Use the explicit Ticket contract and assigned live workspace; reconstruct implementation context from authoritative pointers rather than inherited Coordinator history.

## Read the assignment and preserve its boundaries

Reread the live Ticket, any governing Spec, Accepted direct inputs and their identities, project instructions, assigned Ticket Base, branch, workspace, and existing WIP before editing. Preserve valid work already present. The Coordinator Agent alone assigns or replaces the Ticket Base; a moving branch or current `HEAD` is not a replacement assignment.

Use linked optional shared exploration notes as advisory context. Verify facts affecting implementation or acceptance against the relevant authoritative sources, versions, and environment; refresh affected conclusions when those inputs change. Missing, unreadable, or conflicting notes fall back to authoritative sources. Formal research Ticket deliverables still follow their own acceptance and retention contract.

Own this Ticket's implementation, gates, candidates, and finding closure. Leave the DAG Integration Branch, remote writes, graph decisions, acceptance, and successor unlocking to the Coordinator Agent. Work on no other Ticket. Carry applicable user and Target Project constraints, including model, reasoning, tool, and downstream Agent requirements, into Runtime Skill invocations and dispatches. Reuse existing approvals within their scope, including test-seam approvals; report an unmet explicit constraint instead of silently substituting another configuration.

## Supply Runtime Skills

Use the Runtime Skill Bundle already verified at startup; do not repeat its preflight for an invocation. Supply each Runtime Skill with the applicable project instructions and authoritative inputs. For `$code-review`, include the fixed review Base, candidate range and commit list, scope and governing Spec pointers, and the project's existing tracker workflow. Project-provided instructions take precedence over a dependency's conventional discovery paths, including `docs/agents/issue-tracker.md`. A missing conventional file alone does not require project setup when equivalent authoritative context is supplied. Resolve genuinely missing context within existing authority or report the specific required decision. Project configuration requires its own authorization.

## Run the Ticket-local engineering loop

1. Implement and verify the Ticket. Invoke `$tdd` for changed behavior and use causal RED-to-GREEN evidence where applicable. Invoke `$codebase-design` for an interface, module-boundary, seam, or testability decision. Run focused checks while iterating. For changes to shared interfaces, configuration, dependencies, or previously delivered behavior, identify the relevant Accepted obligations and evidence that may be invalidated; include their impact and disposition in this Ticket's checks and review.
2. Follow the dispatch's finalization instruction. A serial assignment permits final gates and review without another confirmation. If concurrent scheduling explicitly defers that work, send an implementation checkpoint as progress, retain ownership, workspace, and WIP, and wait for the Coordinator Agent to confirm the current Ticket Base and grant completion priority. Waiting is not an Execution Outcome. After confirmation, refresh from any replacement Ticket Base before final work.
3. Complete project-required final gates before review, using the gate evidence validity rule below for any reuse. For a non-empty delivery diff, preserve the bound DAG Definition Index, selected path set, and content identities and exclude transient run state. Commit a clean candidate descending from the fixed Ticket Base. Record the Ticket Base, commit, tree, exact diff command, and commit list; invoke `$code-review` for that range and store the complete result and Candidate Review Record beside those identities. If approved Ticket work requires a DAG Definition change, report the exact change to the Coordinator Agent for a DAG Definition Checkpoint instead of including it in the Promotion Candidate. Continue the same Ticket ownership from the new Ticket Base only after that checkpoint completes. Any later delivery edit creates a new candidate and invalidates the prior Candidate Review Record for promotion.
4. Fix every supported in-scope blocking finding, rerun affected checks and all invalidated final gates, commit a new candidate, and invoke `$code-review` again. When a supported finding recurs under the same Acceptance Obligation, use its evidence to check neighboring paths against the same invariant within Ticket scope before resubmission. Dismiss a finding only with concrete Target Project, Spec, test, or code evidence recorded in its disposition.
5. Use each cycle's evidence to choose the next authorized diagnostic or repair action. A failed attempt may eliminate a hypothesis without changing delivery bytes. Stop repeating a failed action under unchanged conditions; continue when another authorized path remains. Return a non-success Execution Outcome only when evidence establishes its required decision or external closing condition.

There is no fixed review or repair count. Ticket-local defects, additional probes, corrected commands, and new candidates remain in this loop while the objective, approved scope, Accepted inputs, and Acceptance Obligation remain unchanged.

A regression introduced by this unaccepted candidate stays in this Ticket's loop. When evidence proves the current accepted delivery fails an obligation owned by a closed Accepted Ticket, report the responsible Ticket, obligation, affected outputs, and evidence to the Coordinator Agent for the [reopen path](../SKILL.md#reopen-a-failed-accepted-obligation). A reopened assignment follows the same engineering loop from its Coordinator-assigned Ticket Base.

A finding remains blocking when it cites an applicable Spec or documented standard, or demonstrates failing acceptance behavior, and its response does not disprove it with stronger project evidence. Return no successful outcome while such a finding remains. `$code-review` owns its review process; retain its complete result exactly as returned and give every finding an evidence-backed disposition.

## Keep gate evidence valid

A metadata-only change may reuse still-valid product gate evidence only when a fresh equivalence and impact audit proves that the evaluated product bytes, relevant inputs, gate definitions, execution environment, and coverage are unchanged. Keep the original tested commit/tree identities and bind the new audit to the current candidate. Rerun affected or invalidated gates and project-required candidate-specific checks. Each new candidate receives a fresh review under its applicable review contract.

On a Coordinator-issued Ticket Base replacement, apply this Ticket's delivery changes on top of that Base under the Target Project's safe policy and ensure the refreshed candidate descends from it. Apply the same gate evidence validity rule above; a changed Base alone does not prove product equivalence. Create a fresh Candidate Review Record for the new Base, candidate commit/tree, and range. Preserve the old record as superseded evidence.

## Gather zero-diff evidence

When no product delivery bytes are required, the workspace is clean, and the delivery diff is empty, run the applicable final gates and collect the exact artifact identity, Acceptance Obligation coverage, and evidence that every required deliverable is available.

An approved Ticket contract that explicitly defines verification, audit, or operational deliverables without requiring product-byte changes supplies a Baseline Satisfaction rule when every obligation is satisfied and the required output is available. Completing such an effective Ticket yields Accepted; Superseded requires a separate existing rule for its disposition. The contract need not name Baseline Satisfaction or obtain another approval merely for the empty delivery diff. Green tests alone do not satisfy an implementation Ticket's unfulfilled deliverables.

For operational deliverables, provide the Coordinator Agent with the required operation and its existing authorization. Before invoking an authorized action that could repeat side effects, the Coordinator Agent persists the Ticket, target, artifact or necessary parameter identities, authorization pointer, and available native lookup or idempotency correlation in the off-delivery [Run Receipt's outstanding work](integration-transitions.md#run-receipt-and-frozen-evidence). Use safe references for sensitive values. The Coordinator Agent performs specifically authorized remote operations while the Ticket remains claimed and promptly adds any native operation ID, actual result, and readback identities; verify those results before returning a successful outcome.

After an interruption, timeout, or lost response, the Coordinator Agent first queries the operation's owning system and associates the readback with the original request. Observe a confirmed running operation; reuse and verify a confirmed completed result. Retry within the original authorization only when native idempotency safely resumes that request or sufficient evidence proves no side effect occurred. A missing response or temporarily empty read under eventual consistency proves neither non-execution nor safe retry. Failed lookup, ambiguous correlation, or still-unavailable results remain outstanding with the exact uncertainty and next check; use the existing decision or external-blocking rules when their conditions are established. Continue authorized verification and coordinate outstanding operations; incomplete work alone establishes neither non-success outcome.

Return `Ready for Acceptance` through Baseline Satisfaction only when the Ticket contract or another existing Target Project rule recognizes the result and every required audit and gate is present. If no existing rule determines acceptance, return `Needs Decision` with the exact missing rule, current-state audit, or acceptance choice. When the rule is settled, continue gathering its required evidence unless a defined external closing condition prevents it. Do not create an empty commit or treat a non-existent diff as a `$code-review` candidate. The Coordinator Agent owns the serialized Base/publication readback and resulting Accepted or Superseded transition.

## Return one Execution Outcome and stop writing

### Ready for Acceptance

Identify exactly one evidence path:

- **Promotion Candidate**: Ticket and Ticket Base commit identities; final candidate commit and tree; exact diff command and commit list; changed scope and files; focused and final gates; the complete `$code-review` result exactly as returned; the Candidate Review Record binding the Ticket Base, candidate, tree, and evaluated range; and an evidence-backed disposition for every finding.
- **Baseline Satisfaction**: Ticket, Ticket Base commit, and tree identities; a clean empty delivery diff; focused and final gates; the existing Ticket or Target Project rule recognizing Baseline Satisfaction; complete evidence required by that rule; and whether the rule yields Accepted or Superseded.

For either path, include identified impacts on prior Accepted obligations and their dispositions, remaining risks, and omitted verification. Return this outcome only when the named acceptance path is fully evidenced without a new product, scope, graph, or authority choice; only Coordinator-owned verification or promotion remains.

### Needs Decision

- The dependency, acceptance ownership, product-semantic, scope, graph, or authority choice that the Coordinator Agent or user can make.
- Evidence showing why it cannot be resolved inside the approved Ticket.
- Affected Tickets or edges and the exact decision needed.

### Externally Blocked

- The unavailable credential, service, hardware, host capability, or already-required authorization.
- Evidence, the owner of the closing condition, and the observable event permitting retry.

Both non-success outcomes include the latest clean candidate and completed verification, if any. These are Execution Outcomes, not Ticket states: `Needs Decision` means an explicit choice can unblock work; `Externally Blocked` means the choice is settled and an external condition remains. Only the Coordinator Agent records graph transitions and acceptance.

After returning any outcome, stop writing to the Ticket workspace until the Coordinator Agent explicitly resumes this ownership path.
