#!/usr/bin/env python3
"""Verify frozen pending evidence and CAS-promote one local integration ref."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib.common import RecordError, print_json, require_supported_python
from lib.git_ops import ValidationError
from lib.transitions import promote_local_transition


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify frozen pending evidence and CAS-promote one local integration ref. The Coordinator keeps writers and worktree changes quiescent; semantic acceptance remains separate."
    )
    parser.add_argument(
        "--repository", required=True, type=Path, help="existing non-bare Git worktree"
    )
    parser.add_argument("--transition", required=True, type=Path)
    parser.add_argument(
        "--expected-transition-sha256",
        required=True,
        help="SHA-256 of the exact pending transition record bytes",
    )
    parser.add_argument("--promotion-evidence", type=Path)
    parser.add_argument("--expected-promotion-sha256")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--expected-receipt-sha256")
    return parser


def main() -> int:
    parser = build_parser()
    arguments = parser.parse_args()
    try:
        require_supported_python()
        result = promote_local_transition(
            arguments.repository,
            arguments.transition,
            arguments.expected_transition_sha256,
            arguments.promotion_evidence,
            arguments.expected_promotion_sha256,
            arguments.receipt,
            arguments.expected_receipt_sha256,
        )
    except (
        OSError,
        RecordError,
        ValidationError,
        ValueError,
        UnicodeError,
        TypeError,
        RecursionError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print_json(result)  # type: ignore[arg-type]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
