#!/usr/bin/env python3
"""Fail if SQLite calls leak into eMule Next scheduler/UI/network hot paths.

SQLite is allowed only in dedicated persistence/database implementations.
Scheduler decisions, A4AF/part ranking hooks, queue processing and UI refresh
code must stay memory-only.
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]

FORBIDDEN = (
    "sqlite3_open",
    "sqlite3_open16",
    "sqlite3_prepare",
    "sqlite3_prepare_v2",
    "sqlite3_step",
    "sqlite3_exec",
    "sqlite3_backup",
    "winsqlite3.h",
)

HOT_PATHS = (
    "srchybrid/EmuleNextSmartScheduler.cpp",
    "srchybrid/EmuleNextTransferInsights.cpp",
    "srchybrid/EmuleNextDashboardWnd.cpp",
    "srchybrid/DownloadIntelligence.cpp",
    "srchybrid/DownloadQueue.cpp",
    "srchybrid/DownloadClient.cpp",
    "srchybrid/PartFile.cpp",
    "srchybrid/SearchResultsWnd.cpp",
)

ALLOWED_SQLITE_FILES = (
    "srchybrid/EmuleNextDatabase.cpp",
    "srchybrid/EmuleNextHistoryCache.cpp",
    "srchybrid/EmuleNextSchedulerTelemetry.cpp",
)


def text(path: pathlib.Path) -> str:
    return path.read_bytes().decode("latin-1", errors="ignore")


def main() -> int:
    failures: list[str] = []
    for rel in HOT_PATHS:
        path = ROOT / rel
        if not path.exists():
            failures.append(f"missing hot-path source: {rel}")
            continue
        source = text(path)
        for token in FORBIDDEN:
            if re.search(r"\b" + re.escape(token) + r"\b", source):
                failures.append(f"SQLite token {token} found in hot path {rel}")

    for rel in ALLOWED_SQLITE_FILES:
        if not (ROOT / rel).exists():
            failures.append(f"missing persistence source: {rel}")

    history = text(ROOT / "srchybrid/EmuleNextHistoryCache.cpp")
    if "PersistenceMain" not in history or "m_persistQueue" not in history:
        failures.append("history persistence is not isolated behind its worker queue")
    if "No SQLite work runs on the scheduler/core thread" not in history:
        failures.append("history persistence hot-path invariant marker missing")

    telemetry = text(ROOT / "srchybrid/EmuleNextSchedulerTelemetry.cpp")
    if "PersistenceMain" not in telemetry or "m_persistQueue" not in telemetry:
        failures.append("telemetry persistence is not isolated behind its worker queue")
    if "BEGIN IMMEDIATE" not in telemetry:
        failures.append("telemetry worker transaction boundary missing")

    if failures:
        print("eMule Next hot-path SQLite verification FAILED")
        for failure in failures:
            print(" -", failure)
        return 1

    print("eMule Next hot-path SQLite verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
