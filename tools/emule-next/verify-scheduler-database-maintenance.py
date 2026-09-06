#!/usr/bin/env python3
"""Smoke-test DATA-01 integrity/backup semantics for scheduler schema v2.

This uses Python's SQLite only as a portable schema smoke test. The verifier
also checks that the production C++ database exposes integrity_check and the
SQLite backup API on the same main database that owns scheduler tables.
"""
from __future__ import annotations

import pathlib
import sqlite3
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATABASE = ROOT / "srchybrid" / "EmuleNextDatabase.cpp"

SCHEMA = """
CREATE TABLE scheduler_file_history(
 file_hash BLOB PRIMARY KEY,ewma_bps REAL NOT NULL DEFAULT 0,
 samples INTEGER NOT NULL DEFAULT 0,last_observed INTEGER NOT NULL DEFAULT 0);
CREATE TABLE scheduler_decisions(
 id INTEGER PRIMARY KEY AUTOINCREMENT,ts INTEGER NOT NULL,file_name TEXT NOT NULL,file_hash BLOB,
 mode INTEGER NOT NULL,action INTEGER NOT NULL,health INTEGER NOT NULL,attention INTEGER NOT NULL,
 discovery_budget INTEGER NOT NULL,a4af_score INTEGER NOT NULL,rare_part_index INTEGER,
 applied INTEGER NOT NULL,reason TEXT);
CREATE INDEX idx_scheduler_decisions_hash_applied ON scheduler_decisions(file_hash,applied,id DESC);
CREATE TABLE scheduler_outcomes(
 id INTEGER PRIMARY KEY AUTOINCREMENT,ts INTEGER NOT NULL,file_name TEXT NOT NULL,file_hash BLOB,
 action INTEGER NOT NULL,window_seconds INTEGER NOT NULL,bytes_per_second REAL NOT NULL,
 usable_sources INTEGER NOT NULL);
CREATE INDEX idx_scheduler_outcomes_hash_ts ON scheduler_outcomes(file_hash,ts DESC);
"""


def main() -> int:
    cpp = DATABASE.read_bytes().decode("latin-1", errors="ignore")
    for marker in (
        '"PRAGMA integrity_check"',
        "sqlite3_backup_init",
        "CREATE TABLE IF NOT EXISTS scheduler_file_history",
        "CREATE TABLE IF NOT EXISTS scheduler_decisions",
        "CREATE TABLE IF NOT EXISTS scheduler_outcomes",
    ):
        if marker not in cpp:
            raise SystemExit(f"Scheduler DB maintenance: production database missing {marker}")

    with tempfile.TemporaryDirectory(prefix="emule-next-db-") as tmp:
        source_path = pathlib.Path(tmp) / "source.sqlite3"
        backup_path = pathlib.Path(tmp) / "backup.sqlite3"
        db = sqlite3.connect(source_path)
        db.executescript(SCHEMA)
        h = bytes(range(16))
        db.execute("INSERT INTO scheduler_file_history VALUES(?,?,?,?)", (h, 12345.0, 4, 1000))
        db.execute(
            "INSERT INTO scheduler_decisions(ts,file_name,file_hash,mode,action,health,attention,discovery_budget,a4af_score,rare_part_index,applied,reason) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (1000, "sample.bin", h, 2, 1, 700, 800, 20, 650, None, 1, "smoke"),
        )
        db.execute(
            "INSERT INTO scheduler_outcomes(ts,file_name,file_hash,action,window_seconds,bytes_per_second,usable_sources) VALUES(?,?,?,?,?,?,?)",
            (1030, "sample.bin", h, 1, 30, 20480.0, 4),
        )
        db.commit()
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity.lower() != "ok":
            raise SystemExit(f"Scheduler DB maintenance: source integrity failed: {integrity}")

        backup = sqlite3.connect(backup_path)
        db.backup(backup)
        backup.commit()
        db.close()

        backup_integrity = backup.execute("PRAGMA integrity_check").fetchone()[0]
        if backup_integrity.lower() != "ok":
            raise SystemExit(f"Scheduler DB maintenance: backup integrity failed: {backup_integrity}")
        for table in ("scheduler_file_history", "scheduler_decisions", "scheduler_outcomes"):
            count = backup.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if count != 1:
                raise SystemExit(f"Scheduler DB maintenance: backup lost data from {table}")
        backup.close()

    print("Scheduler schema v2 integrity/backup smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
