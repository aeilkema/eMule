#!/usr/bin/env python3
"""Completion gate for TODO sections Dashboard/Transfers 2.0 and Scheduler persistence.

This is intentionally stricter than individual feature verifiers. A local build
must pass this gate before the two TODO blocks can be treated as implementation-complete.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def load(name: str) -> str:
    path = SRC / name
    if not path.exists():
        raise SystemExit(f"Intelligence goal gate: missing {name}")
    return path.read_bytes().decode("latin-1", errors="ignore")


def require(text: str, markers: tuple[str, ...], label: str) -> None:
    for marker in markers:
        if marker not in text:
            raise SystemExit(f"Intelligence goal gate: {label} missing {marker}")


def main() -> int:
    dashboard_h = load("EmuleNextDashboardWnd.h")
    dashboard = load("EmuleNextDashboardWnd.cpp")
    transfers = load("DownloadListCtrl.cpp")
    insight = load("EmuleNextTransferInsights.cpp")
    scheduler = load("EmuleNextSmartScheduler.cpp")
    history = load("EmuleNextHistoryCache.cpp")
    telemetry = load("EmuleNextSchedulerTelemetry.cpp")
    reader = load("EmuleNextSchedulerTelemetryReader.cpp")
    database = load("EmuleNextDatabase.cpp")

    require(dashboard_h, (
        "EMULENEXT_DASHBOARD_INTELLIGENCE2",
        "DASH_LOW_HEALTH", "DASH_INTERVENTION", "DASH_A4AF_OPPORTUNITY",
    ), "Dashboard")
    require(dashboard, (
        "DashboardColumnWidth%d", "DashboardSortColumn", "DashboardFilter",
        "Last intervention", "Last useful source", "Source profile",
        "ForceAnalyze", "ResetFileIntelligence", "case 15:",
        "DASHBOARD_MAX_FILES = 1000", "m_lastRefreshDurationMs > 250 ? 6000 : 3000",
        "CEmuleNextSchedulerTelemetryReader",
    ), "Dashboard")
    require(transfers, (
        'InsertColumn(19,\t_T("Hist. speed")',
        'InsertColumn(20,\t_T("Source quality")',
        'InsertColumn(21,\t_T("Source profile")',
        'InsertColumn(22,\t_T("Scheduler")',
        "CEmuleNextTransferInsights::Build(file, historical)",
    ), "Transfers")
    if "EmuleNextFileSignals BuildNextFileSignals" in transfers:
        raise SystemExit("Intelligence goal gate: duplicate Transfers file-signal builder remains")

    require(insight, (
        "BuildBoundedSourceProfile", "averageSourceQuality", "strongSources",
        "normalSources", "weakSources", "failedSources",
    ), "shared transfer insight")

    require(scheduler, (
        "PruneSnapshots(queue, now)", "sinceDiscovery", "previousActionAt",
        "now - candidate.lastA4AFAt < cooldown", "Preserve an active measurement window",
        "RecordOutcomeSample", "ForceAnalyze", "ResetFileIntelligence",
        "lastUsefulSourceAt",
    ), "scheduler")
    require(history, (
        "bool CEmuleNextHistoryCache::Remove", "DELETE FROM scheduler_file_history",
        "std::vector<std::pair<Key, EmuleNextFileHistory> > loaded",
    ), "history")
    require(telemetry, (
        "scheduler_decisions", "scheduler_outcomes", "m_persistOutcomeQueue",
        "UPDATE scheduler_decisions SET applied=1",
    ), "telemetry")
    require(reader, (
        "PRAGMA query_only=ON", "FROM scheduler_decisions WHERE file_hash=?1",
        "FROM scheduler_outcomes WHERE file_hash=?1",
    ), "telemetry reader")
    require(database, (
        "VALUES('schema_version','2')", "eMule Next schema v2 additive scheduler migration",
        "scheduler_file_history", "scheduler_decisions", "scheduler_outcomes",
        "ALTER TABLE scheduler_decisions ADD COLUMN file_hash BLOB",
    ), "DATA-01 schema")

    print("TODO goals Dashboard/Transfers Intelligence 2.0 + Scheduler persistence: implementation gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
