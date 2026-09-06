#!/usr/bin/env python3
"""Fail fast when Smart Scheduler persistence is incomplete or hot-path SQL leaks in."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHED = ROOT / "srchybrid" / "EmuleNextSmartScheduler.cpp"
HISTORY = ROOT / "srchybrid" / "EmuleNextHistoryCache.cpp"
TELEMETRY = ROOT / "srchybrid" / "EmuleNextSchedulerTelemetry.cpp"


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

    require(scheduler, "m_history.SetDatabasePath(database.GetDatabasePath());", "history database wiring")
    require(scheduler, "m_telemetry.SetDatabasePath(database.GetDatabasePath());", "telemetry database wiring")
    require(scheduler, "m_history.PendingPersistenceWrites()", "history runtime queue diagnostics")
    require(scheduler, "m_telemetry.Summary(telemetry)", "telemetry runtime diagnostics")

    require(history, "void CEmuleNextHistoryCache::PersistenceMain()", "history worker")
    require(history, "CREATE TABLE IF NOT EXISTS scheduler_file_history", "scheduler history schema")
    require(history, "m_lastPersistenceAttempt", "history retry backoff")
    require(history, "DroppedPersistenceWrites", "history drop diagnostics")
    require(telemetry, "void CEmuleNextSchedulerTelemetry::PersistenceMain()", "telemetry worker")
    require(telemetry, "CREATE TABLE IF NOT EXISTS scheduler_decisions", "scheduler_decisions schema")
    require(telemetry, "m_lastPersistenceAttempt", "telemetry retry backoff")
    require(telemetry, "pendingPersistenceEvents", "telemetry persistence diagnostics")

    forbidden = ("sqlite3_open", "sqlite3_exec", "sqlite3_prepare", "winsqlite3.h")
    for token in forbidden:
        if token in scheduler:
            raise SystemExit(f"Scheduler persistence: hot-path SQL token found in EmuleNextSmartScheduler.cpp: {token}")

    for label, worker in (("history", history), ("telemetry", telemetry)):
        if "BEGIN IMMEDIATE" not in worker or "ROLLBACK" not in worker or "COMMIT" not in worker:
            raise SystemExit(f"Scheduler persistence: {label} transaction handling incomplete")
        if "m_persistQueue.size() >= 8192" not in worker:
            raise SystemExit(f"Scheduler persistence: {label} queue is not explicitly bounded")
        if "now - m_lastPersistenceAttempt < 30" not in worker:
            raise SystemExit(f"Scheduler persistence: {label} retry backoff is missing")

    print("Smart Scheduler persistence verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
