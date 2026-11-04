#!/usr/bin/env python3
"""Create-once atomic publication helpers for off-delivery DAG evidence artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib.artifacts import (
    ARTIFACT_KINDS,
    publish_artifact_handle,
    publish_candidate_review,
    publish_execution_record,
    publish_exploration_consumption,
    publish_exploration_note,
    publish_review_context,
)
from lib.common import (
    RecordError,
    print_json,
    require_supported_python,
)
from lib.scheduling import (
    WRITER_STATES,
    publish_admission_decision,
    publish_resume_capsule,
)
from lib.transitions import (
    publish_promotion_package,
    publish_terminal_evidence,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create-once atomic publication for off-delivery DAG capsules, records, and evidence packages."
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    artifact = subparsers.add_parser(
        "artifact",
        help="publish a content-addressed Artifact Handle for a tool output file",
    )
    artifact.add_argument("--artifact", required=True, type=Path)
    artifact.add_argument("--artifact-root", required=True, type=Path)
    artifact.add_argument("--output", required=True, type=Path)
    artifact.add_argument(
        "--artifact-kind", required=True, choices=sorted(ARTIFACT_KINDS)
    )
    artifact.add_argument("--command", required=True)
    artifact.add_argument("--cwd", required=True)
    artifact.add_argument("--exit-code", required=True, type=int)
    artifact.add_argument("--duration-ms", required=True, type=int)
    artifact.add_argument("--observed-at", required=True)
    artifact.add_argument("--environment-identity", required=True)
    artifact.add_argument("--commit")
    artifact.add_argument("--tree")

    note = subparsers.add_parser(
        "exploration-note",
        help="publish an identity-bound Exploration Note",
    )
    note.add_argument("--note", required=True, type=Path)
    note.add_argument("--output", required=True, type=Path)

    consumption = subparsers.add_parser(
        "exploration-consumption",
        help="verify context identities and publish an Exploration Consumption Record",
    )
    consumption.add_argument("--note", required=True, type=Path)
    consumption.add_argument("--context", required=True, type=Path)
    consumption.add_argument("--output", required=True, type=Path)

    execution_record = subparsers.add_parser(
        "execution-record",
        help="validate a Ticket Capsule and Execution Checkpoint and publish a shadow record",
    )
    execution_record.add_argument("--capsule", required=True, type=Path)
    execution_record.add_argument("--checkpoint", required=True, type=Path)
    execution_record.add_argument("--artifact-root", required=True, type=Path)
    execution_record.add_argument("--output", required=True, type=Path)

    admission = subparsers.add_parser(
        "admission-decision",
        help="evaluate live claims and candidates and publish an Execution Admission Decision",
    )
    admission.add_argument("--request", required=True, type=Path)
    admission.add_argument("--output", required=True, type=Path)

    resume = subparsers.add_parser(
        "resume-capsule",
        help="reconcile a live claim with writer-liveness evidence and publish an Execution Resume Capsule",
    )
    resume.add_argument("--receipt", required=True, type=Path)
    resume.add_argument("--ticket-id", required=True)
    resume.add_argument("--artifact-root", type=Path)
    resume.add_argument("--writer-state", required=True, choices=sorted(WRITER_STATES))
    resume.add_argument("--recheck-event")
    resume.add_argument("--liveness-evidence", type=Path)
    resume.add_argument("--output", required=True, type=Path)

    review_context = subparsers.add_parser(
        "review-context",
        help="publish a candidate-bound Review Context Capsule",
    )
    review_context.add_argument("--context", required=True, type=Path)
    review_context.add_argument("--output", required=True, type=Path)

    candidate_review = subparsers.add_parser(
        "candidate-review",
        help="bind one complete review Artifact Handle to a fresh Review Context Capsule",
    )
    candidate_review.add_argument("--context-capsule", required=True, type=Path)
    candidate_review.add_argument("--review-handle", required=True, type=Path)
    candidate_review.add_argument("--artifact-root", required=True, type=Path)
    candidate_review.add_argument("--output", required=True, type=Path)

    promotion = subparsers.add_parser(
        "promotion-package",
        help="verify mechanical inputs for one Promotion Candidate and publish a Promotion Evidence Package",
    )
    promotion.add_argument("--receipt", required=True, type=Path)
    promotion.add_argument("--ticket-id", required=True)
    promotion.add_argument("--context-capsule", required=True, type=Path)
    promotion.add_argument("--review-record", required=True, type=Path)
    promotion.add_argument("--artifact-root", required=True, type=Path)
    promotion.add_argument("--expected-tip-commit", required=True)
    promotion.add_argument("--expected-tip-tree", required=True)
    promotion.add_argument("--output", required=True, type=Path)

    terminal = subparsers.add_parser(
        "terminal-evidence",
        help="verify a Complete or Stalled terminal audit and publish Terminal Outcome Evidence",
    )
    terminal.add_argument("--receipt", required=True, type=Path)
    terminal.add_argument("--audit", required=True, type=Path)
    terminal.add_argument("--expected-tip-commit", required=True)
    terminal.add_argument("--expected-tip-tree", required=True)
    terminal.add_argument("--output", required=True, type=Path)

    return parser


def main() -> int:
    parser = build_parser()
    arguments = parser.parse_args()
    try:
        require_supported_python()
        if arguments.subcommand == "artifact":
            result = publish_artifact_handle(
                artifact=arguments.artifact,
                artifact_root=arguments.artifact_root,
                output=arguments.output,
                artifact_kind=arguments.artifact_kind,
                command=arguments.command,
                cwd=arguments.cwd,
                exit_code=arguments.exit_code,
                duration_ms=arguments.duration_ms,
                observed_at=arguments.observed_at,
                environment_identity=arguments.environment_identity,
                commit=arguments.commit,
                tree=arguments.tree,
            )
        elif arguments.subcommand == "exploration-note":
            result = publish_exploration_note(arguments.note, arguments.output)
        elif arguments.subcommand == "exploration-consumption":
            result = publish_exploration_consumption(
                arguments.note, arguments.context, arguments.output
            )
        elif arguments.subcommand == "execution-record":
            result = publish_execution_record(
                arguments.capsule,
                arguments.checkpoint,
                arguments.artifact_root,
                arguments.output,
            )
        elif arguments.subcommand == "admission-decision":
            result = publish_admission_decision(arguments.request, arguments.output)
        elif arguments.subcommand == "resume-capsule":
            result = publish_resume_capsule(
                receipt_path=arguments.receipt,
                ticket_id=arguments.ticket_id,
                artifact_root=arguments.artifact_root,
                writer_state=arguments.writer_state,
                recheck_event=arguments.recheck_event,
                liveness_evidence_path=arguments.liveness_evidence,
                output_path=arguments.output,
            )
        elif arguments.subcommand == "review-context":
            result = publish_review_context(arguments.context, arguments.output)
        elif arguments.subcommand == "candidate-review":
            result = publish_candidate_review(
                arguments.context_capsule,
                arguments.review_handle,
                arguments.artifact_root,
                arguments.output,
            )
        elif arguments.subcommand == "promotion-package":
            result = publish_promotion_package(
                receipt_path=arguments.receipt,
                ticket_id=arguments.ticket_id,
                context_path=arguments.context_capsule,
                review_record_path=arguments.review_record,
                artifact_root=arguments.artifact_root,
                expected_tip_commit=arguments.expected_tip_commit,
                expected_tip_tree=arguments.expected_tip_tree,
                output_path=arguments.output,
            )
        else:
            result = publish_terminal_evidence(
                receipt_path=arguments.receipt,
                audit_path=arguments.audit,
                expected_tip_commit=arguments.expected_tip_commit,
                expected_tip_tree=arguments.expected_tip_tree,
                output_path=arguments.output,
            )
    except (OSError, RecordError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
