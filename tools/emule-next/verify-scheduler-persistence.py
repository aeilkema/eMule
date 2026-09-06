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
    require(history, "void CEmuleNextHistoryCache::PersistenceMain()", "history worker")
    require(telemetry, "void CEmuleNextSchedulerTelemetry::PersistenceMain()", "telemetry worker")
    require(telemetry, "CREATE TABLE IF NOT EXISTS scheduler_decisions", "scheduler_decisions schema")
    require(telemetry, "pendingPersistenceEvents", "telemetry persistence diagnostics")

    forbidden = ("sqlite3_open", "sqlite3_exec", "sqlite3_prepare", "winsqlite3.h")
    for token in forbidden:
        if token in scheduler:
            raise SystemExit(f"Scheduler persistence: hot-path SQL token found in EmuleNextSmartScheduler.cpp: {token}")

    if "BEGIN IMMEDIATE" not in telemetry or "ROLLBACK" not in telemetry or "COMMIT" not in telemetry:
        raise SystemExit("Scheduler persistence: telemetry transaction handling incomplete")

    print("Smart Scheduler persistence verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
