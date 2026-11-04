#!/usr/bin/env python3
"""Coordinator-only locked CAS state mutations on the off-delivery Run Receipt."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib.artifacts import commit_execution_record
from lib.common import (
    RecordError,
    print_json,
    require_supported_python,
)
from lib.receipt import initialize_receipt
from lib.scheduling import commit_execution_claim
from lib.tracker import commit_tracker_checkpoint, commit_tracker_policy
from lib.transitions import commit_ticket_disposition, commit_transition_state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Coordinator-owned locked CAS state updates to the off-delivery Run Receipt."
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    init_cmd = subparsers.add_parser(
        "receipt-init",
        help="atomically initialize a canonical Run Receipt at coordinator_generation 0",
    )
    init_cmd.add_argument("--receipt", required=True, type=Path)
    init_cmd.add_argument("--init", required=True, type=Path)

    policy = subparsers.add_parser(
        "tracker-policy",
        help="validate and CAS-record the run's Tracker Policy in the Run Receipt",
    )
    policy.add_argument("--repository", required=True, type=Path)
    policy.add_argument("--commit", required=True)
    policy.add_argument("--receipt", required=True, type=Path)
    policy.add_argument("--policy", required=True, type=Path)
    policy.add_argument("--expected-generation", required=True, type=int)
    policy.add_argument("--expected-receipt-sha256", required=True)

    claim = subparsers.add_parser(
        "claim",
        help="CAS-record one live Execution Claim in the Run Receipt after admission",
    )
    claim.add_argument("--receipt", required=True, type=Path)
    claim.add_argument("--decision", required=True, type=Path)
    claim.add_argument("--claim", required=True, type=Path)
    claim.add_argument("--expected-generation", required=True, type=int)
    claim.add_argument("--expected-receipt-sha256", required=True)

    record = subparsers.add_parser(
        "execution-record",
        help="CAS-index one validated Execution Checkpoint Record into the Run Receipt",
    )
    record.add_argument("--receipt", required=True, type=Path)
    record.add_argument("--record", required=True, type=Path)
    record.add_argument("--artifact-root", required=True, type=Path)
    record.add_argument("--expected-generation", required=True, type=int)
    record.add_argument("--expected-receipt-sha256", required=True)

    transition = subparsers.add_parser(
        "transition",
        help="freeze, cancel, or complete a pending Integration Transition in the Run Receipt",
    )
    transition.add_argument("--receipt", required=True, type=Path)
    transition.add_argument(
        "--action", required=True, choices=("freeze", "complete", "cancel")
    )
    transition.add_argument("--transition", required=True, type=Path)
    transition.add_argument("--expected-transition-sha256", required=True)
    transition.add_argument("--synchronized-commit")
    transition.add_argument("--expected-generation", required=True, type=int)
    transition.add_argument("--expected-receipt-sha256", required=True)

    disposition = subparsers.add_parser(
        "disposition",
        help="CAS-record an explicit Ticket Disposition and close the live claim",
    )
    disposition.add_argument("--receipt", required=True, type=Path)
    disposition.add_argument("--decision", required=True, type=Path)
    disposition.add_argument("--promotion-evidence", type=Path)
    disposition.add_argument("--expected-promotion-sha256")
    disposition.add_argument("--baseline-evidence", type=Path)
    disposition.add_argument("--expected-baseline-sha256")
    disposition.add_argument("--expected-generation", required=True, type=int)
    disposition.add_argument("--expected-receipt-sha256", required=True)

    checkpoint = subparsers.add_parser(
        "tracker-checkpoint",
        help="validate and CAS-record a completed Tracker Checkpoint in the Run Receipt",
    )
    checkpoint.add_argument("--repository", required=True, type=Path)
    checkpoint.add_argument("--receipt", required=True, type=Path)
    checkpoint.add_argument("--checkpoint", required=True, type=Path)
    checkpoint.add_argument("--expected-generation", required=True, type=int)
    checkpoint.add_argument("--expected-receipt-sha256", required=True)

    return parser


def main() -> int:
    parser = build_parser()
    arguments = parser.parse_args()
    try:
        require_supported_python()
        if arguments.subcommand == "receipt-init":
            _status, result = initialize_receipt(arguments.receipt, arguments.init)
        elif arguments.subcommand == "tracker-policy":
            result = commit_tracker_policy(
                repository=arguments.repository,
                commit=arguments.commit,
                receipt_path=arguments.receipt,
                policy_path=arguments.policy,
                expected_generation=arguments.expected_generation,
                expected_receipt_digest=arguments.expected_receipt_sha256,
            )
        elif arguments.subcommand == "claim":
            result = commit_execution_claim(
                receipt_path=arguments.receipt,
                decision_path=arguments.decision,
                claim_path=arguments.claim,
                expected_generation=arguments.expected_generation,
                expected_receipt_digest=arguments.expected_receipt_sha256,
            )
        elif arguments.subcommand == "execution-record":
            result = commit_execution_record(
                arguments.receipt,
                arguments.record,
                arguments.artifact_root,
                arguments.expected_generation,
                arguments.expected_receipt_sha256,
            )
        elif arguments.subcommand == "transition":
            result = commit_transition_state(
                receipt_path=arguments.receipt,
                action=arguments.action,
                transition_path=arguments.transition,
                expected_transition_digest=arguments.expected_transition_sha256,
                synchronized_commit=arguments.synchronized_commit,
                expected_generation=arguments.expected_generation,
                expected_receipt_digest=arguments.expected_receipt_sha256,
            )
        elif arguments.subcommand == "disposition":
            result = commit_ticket_disposition(
                receipt_path=arguments.receipt,
                decision_path=arguments.decision,
                promotion_path=arguments.promotion_evidence,
                promotion_digest=arguments.expected_promotion_sha256,
                baseline_path=arguments.baseline_evidence,
                baseline_digest=arguments.expected_baseline_sha256,
                expected_generation=arguments.expected_generation,
                expected_receipt_digest=arguments.expected_receipt_sha256,
            )
        else:
            result = commit_tracker_checkpoint(
                repository=arguments.repository,
                receipt_path=arguments.receipt,
                checkpoint_path=arguments.checkpoint,
                expected_generation=arguments.expected_generation,
                expected_receipt_digest=arguments.expected_receipt_sha256,
            )
    except (OSError, RecordError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
