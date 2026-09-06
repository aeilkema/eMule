#!/usr/bin/env python3
"""Verify the materialized Dashboard Intelligence 2.0 contract."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def require(path: pathlib.Path, markers: tuple[str, ...]) -> None:
    text = path.read_bytes().decode("latin-1", errors="ignore")
    for marker in markers:
        if marker not in text:
            raise SystemExit(f"Dashboard Intelligence 2.0: {path.name} missing {marker!r}")


def main() -> int:
    require(SRC / "EmuleNextDashboardWnd.h", (
        "EMULENEXT_DASHBOARD_INTELLIGENCE2",
        "DASH_LOW_HEALTH",
        "DASH_INTERVENTION",
        "DASH_A4AF_OPPORTUNITY",
        "OnDownloadColumnClick",
        "OnForceAnalysis",
        "OnResetIntelligence",
        "OnPersistentDetailsLoaded",
    ))
    require(SRC / "EmuleNextDashboardWnd.cpp", (
        "CEmuleNextTransferInsights::Build(file, row.historicalBytesPerSecond)",
        'DashboardColumnWidth%d',
        'DashboardSortColumn',
        'DashboardFilter',
        '_T("Low health")',
        '_T("Intervention")',
        '_T("A4AF")',
        '_T("Last intervention")',
        '_T("Last useful source")',
        '_T("Source profile")',
        "insight.strongSources",
        "insight.normalSources",
        "insight.weakSources",
        "insight.failedSources",
        "theEmuleNextScheduler.ForceAnalyze",
        "theEmuleNextScheduler.ResetFileIntelligence",
        "CEmuleNextSchedulerTelemetryReader",
        "DASHBOARD_MAX_FILES = 1000",
        "m_lastRefreshDurationMs > 250 ? 6000 : 3000",
    ))
    print("Dashboard Intelligence 2.0 verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
