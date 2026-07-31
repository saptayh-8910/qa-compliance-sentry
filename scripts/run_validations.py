#!/usr/bin/env python3
"""Run SQL data validation suite (Stage 1 Milestone 1B support)."""

from db.seed import DEFAULT_DB, init_db
from db.validation import DataValidator


def main() -> int:
    init_db(DEFAULT_DB)
    validator = DataValidator(DEFAULT_DB)
    results = validator.run_all()
    exit_code = 0
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name}: {result.detail}")
        if not result.passed:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
