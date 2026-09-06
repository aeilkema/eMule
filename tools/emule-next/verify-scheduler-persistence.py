#!/usr/bin/env python3
"""Fail fast when Smart Scheduler persistence is incomplete or hot-path SQL leaks in."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHED = ROOT / "srchybrid" / "EmuleNextSmartScheduler.cpp"
HISTORY = ROOT / "srchybrid" / "EmuleNextHistoryCache.cpp"
TELEMETRY = ROOT / "srchybrid" / "EmuleNextSchedulerTelemetry.cpp"
READER = ROOT / "srchybrid" / "EmuleNextSchedulerTelemetryReader.cpp"


def text(path: pathlib.Path) -> str:
    if not path.exists():
        raise SystemExit(f"Scheduler persistence: missing {path.relative_to(ROOT)}")
    return path.read_bytes().decode("latin-1", errors="ignore")


def require(haystack: str, needle: str, label: str) -> None:
    if needle not in haystack:
        raise SystemExit(f"Scheduler persistence: missing {label}")


def main() -> int:
    scheduler = text(SCHED)
    history = text(HISTORY)
    telemetry = text(TELEMETRY)
    reader = text(READER)

    require(scheduler, "m_history.SetDatabasePath(database.GetDatabasePath());", "history database wiring")
    require(scheduler, "m_telemetry.SetDatabasePath(database.GetDatabasePath());", "telemetry database wiring")
    require(scheduler, "m_history.PendingPersistenceWrites()", "history runtime queue diagnostics")
    require(scheduler, "m_history.DroppedPersistenceWrites()", "history runtime drop diagnostics")
    require(scheduler, "RecordOutcomeBaseline", "intervention baseline persistence")
    require(scheduler, "RecordOutcomeSample", "intervention sample persistence")
    require(scheduler, "m_history.Remove(fileHash)", "per-file persistent history reset")

    require(history, "void CEmuleNextHistoryCache::PersistenceMain()", "history worker")
    require(history, "CREATE TABLE IF NOT EXISTS scheduler_file_history", "scheduler history schema")
    require(history, "bool CEmuleNextHistoryCache::Remove", "history reset API")
    require(history, "DELETE FROM scheduler_file_history WHERE file_hash=?1", "async durable history reset")
    require(history, "m_lastPersistenceAttempt", "history retry backoff")

    require(telemetry, "void CEmuleNextSchedulerTelemetry::PersistenceMain()", "telemetry worker")
    require(telemetry, "CREATE TABLE IF NOT EXISTS scheduler_decisions", "scheduler_decisions schema")
    require(telemetry, "CREATE TABLE IF NOT EXISTS scheduler_outcomes", "scheduler_outcomes schema")
    require(telemetry, "idx_scheduler_outcomes_hash_ts", "outcome lookup index")
    require(telemetry, "m_persistOutcomeQueue", "outcome persistence queue")
    require(telemetry, "m_persistAppliedQueue", "delayed applied-state queue")
    require(telemetry, "UPDATE scheduler_decisions SET applied=1", "durable applied-state update")
    require(telemetry, "m_lastPersistenceAttempt", "telemetry retry backoff")

    require(reader, "PRAGMA query_only=ON", "read-only diagnosis service")
    require(reader, "FROM scheduler_decisions WHERE file_hash=?1", "decision query by hash")
    require(reader, "FROM scheduler_outcomes WHERE file_hash=?1", "outcome query by hash")

    forbidden = ("sqlite3_open", "sqlite3_exec", "sqlite3_prepare", "winsqlite3.h")
    for token in forbidden:
        if token in scheduler:
            raise SystemExit(f"Scheduler persistence: hot-path SQL token found in EmuleNextSmartScheduler.cpp: {token}")

    if "m_persistQueue.size() >= 8192" not in history:
        raise SystemExit("Scheduler persistence: history queue is not explicitly bounded")
    if "PendingCount(m_persistQueue, m_persistOutcomeQueue, m_persistAppliedQueue.size()) >= 8192" not in telemetry:
        raise SystemExit("Scheduler persistence: combined telemetry queues are not explicitly bounded")

    for label, worker in (("history", history), ("telemetry", telemetry)):
        if "BEGIN IMMEDIATE" not in worker or "ROLLBACK" not in worker or "COMMIT" not in worker:
            raise SystemExit(f"Scheduler persistence: {label} transaction handling incomplete")
        if "now - m_lastPersistenceAttempt < 30" not in worker:
            raise SystemExit(f"Scheduler persistence: {label} retry backoff is missing")

    print("Smart Scheduler persistence verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
