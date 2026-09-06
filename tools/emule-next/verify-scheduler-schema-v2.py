#!/usr/bin/env python3
"""Verify scheduler persistence is owned by upgrade-safe DATA-01 schema v2."""
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
        "eMule Next schema v2 additive scheduler migration",
        "ALTER TABLE scheduler_decisions ADD COLUMN file_hash BLOB",
        "idx_scheduler_decisions_hash_applied",
        "idx_scheduler_outcomes_hash_ts",
    )
    for marker in required:
        if marker not in text:
            raise SystemExit(f"Scheduler schema v2 missing {marker}")

    # Existing Preview databases can have scheduler_decisions without file_hash.
    # The hash index must therefore be created by the additive migration after
    # ALTER TABLE, not inside the base schema transaction.
    schema_start = text.find("static const char schema[]")
    migration_start = text.find("eMule Next schema v2 additive scheduler migration")
    if schema_start < 0 or migration_start < 0:
        raise SystemExit("Scheduler schema v2 migration boundaries missing")
    schema_section = text[schema_start:migration_start]
    if "idx_scheduler_decisions_hash_applied" in schema_section:
        raise SystemExit("Scheduler schema v2 creates file_hash index before legacy column migration")

    print("eMule Next scheduler DATA-01 schema v2 verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
