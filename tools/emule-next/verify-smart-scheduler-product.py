#!/usr/bin/env python3
"""Fail-fast verification for the Smart Scheduler product layer."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def require(path: pathlib.Path, needles: tuple[str, ...]) -> None:
    text = path.read_bytes().decode("latin-1", errors="ignore")
    for needle in needles:
        if needle not in text:
            raise SystemExit(f"Smart Scheduler product verification failed: {path.name}: {needle}")


def main() -> int:
    require(SRC / "EmuleNextSmartScheduler.h", (
        "EmuleNextSchedulerRuntimeStatus",
        "GetRuntimeStatusText",
        "maxFilesPerRound",
        "telemetryEnabled",
        "MarkApplied",
    ))
    require(SRC / "EmuleNextSmartScheduler.cpp", (
        "SmartSchedulerMaxFilesPerRound",
        "SmartHistoryCache",
        "SmartTelemetryCapacity",
        "event.applied = intervened",
        "MarkApplied(candidateFile->GetFileHash())",
        "MarkApplied(file->GetFileHash())",
    ))
    require(SRC / "EmuleNextSchedulerTelemetry.h", (
        "EmuleNextSchedulerTelemetrySummary",
        "appliedInterventions",
        "MarkAppliedIntervention",
        "void Clear()",
    ))
    require(SRC / "EmuleNextSettingsWnd.cpp", (
        "SmartSchedulerProfile",
        "SmartSchedulerCooldown",
        "SmartSchedulerMaxFilesPerRound",
        "SmartA4AFMinimumScore",
        "SmartHistoryCache",
        "SmartTelemetry",
        "SmartTelemetryCapacity",
    ))
    require(SRC / "EmuleNextDashboardWnd.cpp", (
        'InsertColumn(14, _T("Scheduler")',
        "theEmuleNextScheduler.GetRuntimeStatusText()",
        "schedulerSnapshot.applied",
    ))

    for hot in ("EmuleNextDashboardWnd.cpp", "DownloadQueue.cpp", "PartFile.cpp", "DownloadListCtrl.cpp"):
        text = (SRC / hot).read_bytes().decode("latin-1", errors="ignore").lower()
        if "sqlite3_" in text:
            raise SystemExit(f"Smart Scheduler product verification failed: SQLite in hot/UI path {hot}")

    print("eMule Next Smart Scheduler product verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
