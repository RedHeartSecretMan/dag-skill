#!/usr/bin/env python3
"""Read-only deterministic verification helpers for DAG definitions, artifacts, reviews, and checkpoints."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib.artifacts import (
    HANDLE_KIND,
    verify_candidate_review,
    verify_handle_file,
)
from lib.common import (
    RecordError,
    print_json,
    require_oid,
    require_supported_python,
    require_text,
)
from lib.git_ops import ValidationError, validate_definition_index
from lib.tracker import verify_tracker_checkpoint


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only deterministic verification for DAG definitions, artifacts, reviews, and tracker checkpoints."
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    definition = subparsers.add_parser(
        "definition-index",
        help="validate .dag/definition-index.json at one exact Git commit",
    )
    definition.add_argument("--repository", required=True, type=Path)
    definition.add_argument("--commit", required=True)

    artifact = subparsers.add_parser(
        "artifact",
        help="verify a content-addressed Artifact Handle and its referenced file",
    )
    artifact.add_argument("--handle", required=True, type=Path)
    artifact.add_argument("--artifact-root", type=Path)

    review = subparsers.add_parser(
        "candidate-review",
        help="verify a Candidate Review Record against its Review Context Capsule and review artifact",
    )
    review.add_argument("--record", required=True, type=Path)
    review.add_argument("--context-capsule", required=True, type=Path)
    review.add_argument("--artifact-root", required=True, type=Path)
    review.add_argument("--expected-base-commit", required=True)
    review.add_argument("--expected-base-tree", required=True)
    review.add_argument("--expected-candidate-commit", required=True)
    review.add_argument("--expected-candidate-tree", required=True)
    review.add_argument("--expected-candidate-range", required=True)

    tracker = subparsers.add_parser(
        "tracker-checkpoint",
        help="read-only preflight verification of a Tracker Checkpoint candidate before review and promotion",
    )
    tracker.add_argument("--repository", required=True, type=Path)
    tracker.add_argument("--receipt", required=True, type=Path)
    tracker.add_argument("--checkpoint", required=True, type=Path)

    return parser


def main() -> int:
    parser = build_parser()
    arguments = parser.parse_args()
    try:
        require_supported_python()
        if arguments.subcommand == "definition-index":
            result = validate_definition_index(arguments.repository, arguments.commit)
        elif arguments.subcommand == "artifact":
            handle = verify_handle_file(arguments.handle, arguments.artifact_root)
            result = {
                "status": "verified",
                "kind": HANDLE_KIND,
                "artifact_sha256": handle["artifact_sha256"],
                "byte_count": handle["byte_count"],
            }
        elif arguments.subcommand == "candidate-review":
            result, _handle = verify_candidate_review(
                arguments.record,
                arguments.context_capsule,
                arguments.artifact_root,
                require_oid(arguments.expected_base_commit, "expected_base_commit"),
                require_oid(arguments.expected_base_tree, "expected_base_tree"),
                require_oid(
                    arguments.expected_candidate_commit, "expected_candidate_commit"
                ),
                require_oid(
                    arguments.expected_candidate_tree, "expected_candidate_tree"
                ),
                require_text(
                    arguments.expected_candidate_range, "expected_candidate_range"
                ),
            )
        else:
            result = verify_tracker_checkpoint(
                repository=arguments.repository,
                receipt_path=arguments.receipt,
                checkpoint_path=arguments.checkpoint,
            )
    except (
        OSError,
        RecordError,
        ValidationError,
        UnicodeDecodeError,
        KeyError,
        TypeError,
        RuntimeError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print_json(result)  # type: ignore[arg-type]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
