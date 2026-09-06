#!/usr/bin/env python3
"""Fail fast when the eMule Next local overlay is only partially activated."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"

CHECKS = {
    "EmuleNextDashboardWnd.h": (
        "EMULENEXT_DASHBOARD_INTELLIGENCE2",
        "void UpdateActionButtons();",
        "afx_msg void OnForceAnalysis();",
        "afx_msg void OnDownloadColumnClick",
    ),
    "EmuleNextDashboardWnd.cpp": (
        "void CEmuleNextDashboardWnd::OnOpenTransfers()",
        "void CEmuleNextDashboardWnd::OnPauseResume()",
        "CEmuleNextTransferInsights::Build(file, row.historicalBytesPerSecond)",
        "theEmuleNextScheduler.ForceAnalyze",
        "theEmuleNextScheduler.ResetFileIntelligence",
        "JumpToTransfers(true)",
        "Source profile",
        "Last intervention",
    ),
    "DownloadListCtrl.h": (
        "SelectFile(CPartFile *file, bool expand = false)",
    ),
    "DownloadListCtrl.cpp": (
        "bool CDownloadListCtrl::SelectFile(CPartFile *file, bool expand)",
        "Live quality",
        "Smart ETA",
        "Hist. speed",
        "Source quality",
        "Source profile",
        "CEmuleNextTransferInsights::Build(file, historical)",
    ),
    "TransferWnd.h": (
        "EmuleNextDashboardWnd.h",
        "w1iNextDashboard",
        "CEmuleNextDashboardWnd\tm_nextDashboard",
        "ShowNextDashboard();",
    ),
    "TransferWnd.cpp": (
        "EMULENEXT_DASHBOARD_VIEW",
        "void CTransferWnd::ShowNextDashboard()",
        "message == WM_APP + 0x568",
        "downloadlistctrl.SelectFile(file, wParam != 0)",
        "restore persisted Dashboard safely after first real layout",
        "rebuilding toolbar chrome must not discard Dashboard selection",
    ),
    "PartFile.h": (
        "GetPartSourceFrequency(UINT part)",
    ),
    "EmuleNextSmartScheduler.cpp": (
        "theEmuleNext.Database()",
    ),
    "EmuleNextWinSqliteCompat.h": (
        "#include <winsqlite3.h>",
        "sqlite3_reset(sqlite3_stmt* statement)",
        "sqlite3_clear_bindings(sqlite3_stmt* statement)",
        "sqlite3_bind_double(sqlite3_stmt* statement, int index, double value)",
        "sqlite3_column_double(sqlite3_stmt* statement, int column)",
        "sqlite3_column_type(sqlite3_stmt* statement, int column)",
        "#define SQLITE_NULL 5",
    ),
    "EmuleNextDatabase.cpp": (
        '#include "EmuleNextWinSqliteCompat.h"',
    ),
    "EmuleNextHistoryCache.cpp": (
        '#include "EmuleNextWinSqliteCompat.h"',
    ),
    "EmuleNextSchedulerTelemetry.cpp": (
        '#include "EmuleNextWinSqliteCompat.h"',
    ),
    "EmuleNextSchedulerTelemetryReader.cpp": (
        '#include "EmuleNextWinSqliteCompat.h"',
    ),
    "emule.vcxproj": (
        "Condition=\"'$(Platform)'=='x64'\">WINVER=0x0A00;_WIN32_WINNT=0x0A00;NTDDI_VERSION=0x0A000001;%(PreprocessorDefinitions)",
        "Condition=\"'$(Platform)'=='Win32'\">XP_BUILD;%(PreprocessorDefinitions)",
        "winsqlite3.lib",
    ),
}

FORBIDDEN = {
    "TransferWnd.cpp": (
        "AddDebugLogLine",
    ),
    "EmuleNextSmartScheduler.cpp": (
        "theEmuleNextRuntime.Database()",
    ),
    "EmuleNextDatabase.cpp": (
        "#include <winsqlite3.h>",
    ),
    "EmuleNextHistoryCache.cpp": (
        "#include <winsqlite3.h>",
    ),
    "EmuleNextSchedulerTelemetry.cpp": (
        "#include <winsqlite3.h>",
    ),
    "EmuleNextSchedulerTelemetryReader.cpp": (
        "#include <winsqlite3.h>",
    ),
    "emule.vcxproj": (
        "Condition=\"'$(Platform)'!='ARM64'\">XP_BUILD",
        "Condition=\"'$(Platform)'=='x64'\">WINVER=0x0A00;_WIN32_WINNT=0x0A00;%(PreprocessorDefinitions)",
    ),
}


def main() -> int:
    failures: list[str] = []
    for name, markers in CHECKS.items():
        path = SRC / name
        if not path.exists():
            failures.append(f"{name}: file missing")
            continue
        text = path.read_bytes().decode("latin-1", errors="ignore")
        for marker in markers:
            if marker not in text:
                failures.append(f"{name}: missing {marker!r}")

    for name, markers in FORBIDDEN.items():
        path = SRC / name
        if not path.exists():
            continue
        text = path.read_bytes().decode("latin-1", errors="ignore")
        for marker in markers:
            if marker in text:
                failures.append(f"{name}: forbidden compile-regression marker present {marker!r}")

    if failures:
        print("eMule Next integration verification FAILED")
        for item in failures:
            print(f"  - {item}")
        raise SystemExit(2)

    print("eMule Next integration verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
