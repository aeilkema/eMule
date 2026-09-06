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
        "historyPendingWrites",
        "historyDroppedWrites",
        "telemetryEnabled",
        "MarkApplied",
    ))
    require(SRC / "EmuleNextSmartScheduler.cpp", (
        "SmartSchedulerMaxFilesPerRound",
        "SmartHistoryCache",
        "SmartHistoryCacheCapacity",
        "SmartTelemetryCapacity",
        "event.applied = intervened",
        "event.fileHash = key",
        "MarkApplied(candidateFile->GetFileHash(), candidateFile->GetFileName())",
        "MarkApplied(file->GetFileHash(), file->GetFileName())",
        "m_telemetry.MarkAppliedIntervention(fileHash, fileName)",
    ))
    require(SRC / "EmuleNextSchedulerTelemetry.h", (
        "EmuleNextSchedulerTelemetrySummary",
        "fileHashValid",
        "appliedInterventions",
        "MarkAppliedIntervention(const unsigned char* fileHash, const CString& fileName)",
        "void Clear()",
    ))
    require(SRC / "EmuleNextSchedulerTelemetry.cpp", (
        "file_hash BLOB",
        "idx_scheduler_decisions_hash_applied",
        "m_persistAppliedQueue",
    ))
    require(SRC / "EmuleNextSettingsWnd.cpp", (
        "SmartSchedulerProfile",
        "SmartSchedulerCooldown",
        "SmartSchedulerMaxFilesPerRound",
        "SmartA4AFMinimumScore",
        "SmartHistoryCache",
        "SmartHistoryCacheCapacity",
        "SmartTelemetry",
        "SmartTelemetryCapacity",
    ))
    require(SRC / "EmuleNextDashboardWnd.cpp", (
        'InsertColumn(14, _T("Scheduler")',
        "theEmuleNextScheduler.GetRuntimeStatusText()",
        "schedulerSnapshot.applied",
        "CEmuleNextTransferInsights::Build(file, historicalBytesPerSecond)",
    ))

    for hot in ("EmuleNextDashboardWnd.cpp", "EmuleNextSmartScheduler.cpp", "DownloadQueue.cpp", "PartFile.cpp", "DownloadListCtrl.cpp"):
        text = (SRC / hot).read_bytes().decode("latin-1", errors="ignore").lower()
        if "sqlite3_" in text or "winsqlite3.h" in text:
            raise SystemExit(f"Smart Scheduler product verification failed: SQLite in hot/UI path {hot}")

    print("eMule Next Smart Scheduler product verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())