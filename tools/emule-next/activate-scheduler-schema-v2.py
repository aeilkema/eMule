#!/usr/bin/env python3
"""Materialize DATA-01 schema v2 for Smart Scheduler persistence.

The core database initializer owns schema versioning. Existing Preview
databases may already contain scheduler_decisions without file_hash, so the
migration adds that column after the base transaction and only then creates the
hash index. Duplicate-column failure is intentionally harmless.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "EmuleNextDatabase.cpp"


def read_text() -> tuple[str, str]:
    raw = PATH.read_bytes()
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def main() -> int:
    text, encoding = read_text()
    changed = False

    if "VALUES('schema_version','2')" not in text:
        old = "VALUES('schema_version','1')"
        if old not in text:
            raise SystemExit("Scheduler schema v2: schema_version anchor missing")
        text = text.replace(old, "VALUES('schema_version','2')", 1)
        changed = True

    marker = '"CREATE TABLE IF NOT EXISTS scheduler_file_history("'
    if marker not in text:
        anchor = '            "CREATE TABLE IF NOT EXISTS peer_share_scans("\n            " peer_id INTEGER PRIMARY KEY REFERENCES peers(id) ON DELETE CASCADE,status TEXT NOT NULL DEFAULT \'unknown\',"\n            " last_requested INTEGER,last_completed INTEGER,next_allowed INTEGER,last_error TEXT);"\n'
        if anchor not in text:
            raise SystemExit("Scheduler schema v2: peer_share_scans anchor missing")
        addition = anchor + (
            '            "CREATE TABLE IF NOT EXISTS scheduler_file_history("\n'
            '            " file_hash BLOB PRIMARY KEY,ewma_bps REAL NOT NULL DEFAULT 0,samples INTEGER NOT NULL DEFAULT 0,last_observed INTEGER NOT NULL DEFAULT 0);"\n'
            '            "CREATE TABLE IF NOT EXISTS scheduler_decisions("\n'
            '            " id INTEGER PRIMARY KEY AUTOINCREMENT,ts INTEGER NOT NULL,file_name TEXT NOT NULL,file_hash BLOB,"\n'
            '            " mode INTEGER NOT NULL,action INTEGER NOT NULL,health INTEGER NOT NULL,attention INTEGER NOT NULL,"\n'
            '            " discovery_budget INTEGER NOT NULL,a4af_score INTEGER NOT NULL,rare_part_index INTEGER,applied INTEGER NOT NULL,reason TEXT);"\n'
            '            "CREATE INDEX IF NOT EXISTS idx_scheduler_decisions_ts ON scheduler_decisions(ts DESC);"\n'
            '            "CREATE TABLE IF NOT EXISTS scheduler_outcomes("\n'
            '            " id INTEGER PRIMARY KEY AUTOINCREMENT,ts INTEGER NOT NULL,file_name TEXT NOT NULL,file_hash BLOB,"\n'
            '            " action INTEGER NOT NULL,window_seconds INTEGER NOT NULL,bytes_per_second REAL NOT NULL,usable_sources INTEGER NOT NULL);"\n'
            '            "CREATE INDEX IF NOT EXISTS idx_scheduler_outcomes_hash_ts ON scheduler_outcomes(file_hash,ts DESC);"\n'
        )
        text = text.replace(anchor, addition, 1)
        changed = True

    migration_marker = "eMule Next schema v2 additive scheduler migration"
    if migration_marker not in text:
        old_return = '''        if (!ExecSql(db, schema, &error)) {
            ExecSql(db, "ROLLBACK;");
            SetError(error);
            return false;
        }
        return true;
'''
        new_return = '''        if (!ExecSql(db, schema, &error)) {
            ExecSql(db, "ROLLBACK;");
            SetError(error);
            return false;
        }

        // eMule Next schema v2 additive scheduler migration. Existing Preview
        // databases may already have scheduler_decisions without file_hash.
        // Duplicate-column failure is harmless; the index is created only after
        // this upgrade attempt so old databases cannot fail the base transaction.
        sqlite3_exec(db, "ALTER TABLE scheduler_decisions ADD COLUMN file_hash BLOB", NULL, NULL, NULL);
        if (!ExecSql(db,
            "CREATE INDEX IF NOT EXISTS idx_scheduler_decisions_hash_applied ON scheduler_decisions(file_hash,applied,id DESC);"
            "CREATE INDEX IF NOT EXISTS idx_scheduler_outcomes_hash_ts ON scheduler_outcomes(file_hash,ts DESC);",
            &error)) {
            SetError(error);
            return false;
        }
        return true;
'''
        if old_return not in text:
            raise SystemExit("Scheduler schema v2: Initialize return anchor missing")
        text = text.replace(old_return, new_return, 1)
        changed = True

    if changed:
        PATH.write_bytes(text.encode(encoding))
        print("eMule Next DATA-01 scheduler schema v2 materialized")
    else:
        print("eMule Next DATA-01 scheduler schema v2 already materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
