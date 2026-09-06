#!/usr/bin/env python3
"""Verify scheduler persistence is owned by formal DATA-01 schema v2."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "EmuleNextDatabase.cpp"


def main() -> int:
    text = PATH.read_bytes().decode("latin-1", errors="ignore")
    required = (
        "VALUES('schema_version','2')",
        "CREATE TABLE IF NOT EXISTS scheduler_file_history",
        "CREATE TABLE IF NOT EXISTS scheduler_decisions",
        "CREATE TABLE IF NOT EXISTS scheduler_outcomes",
        "idx_scheduler_decisions_hash_applied",
        "idx_scheduler_outcomes_hash_ts",
    )
    for marker in required:
        if marker not in text:
            raise SystemExit(f"Scheduler schema v2 missing {marker}")
    print("eMule Next scheduler DATA-01 schema v2 verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
