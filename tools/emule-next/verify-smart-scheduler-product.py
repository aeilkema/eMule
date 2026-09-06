#!/usr/bin/env python3
"""Fail-fast verification for the completed Smart Scheduler product layer."""
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
        "ForceAnalyze",
        "ResetFileIntelligence",
        "lastDiscoveryAt",
        "lastA4AFAt",
        "lastRarePartAt",
        "lastUsefulSourceAt",
        "EmuleNextInterventionOutcome",
    ))
    require(SRC / "EmuleNextSmartScheduler.cpp", (
        "SmartSchedulerMaxFilesPerRound",
        "SmartHistoryCacheCapacity",
        "SmartTelemetryCapacity",
        "PruneSnapshots(queue, now)",
        "sinceDiscovery",
        "BeginOutcome(file, ENSA_DISCOVERY_BOOST, now)",
        "RecordOutcomeSample",
        "MarkApplied(candidateFile, ENSA_A4AF_PREFER)",
        "MarkApplied(file, ENSA_RARE_PART_PROTECT)",
        "m_history.Remove(fileHash)",
    ))
    require(SRC / "EmuleNextSchedulerTelemetry.h", (
        "EmuleNextSchedulerOutcomeRecord",
        "RecordOutcomeBaseline",
        "RecordOutcomeSample",
        "MarkAppliedIntervention(const unsigned char* fileHash, const CString& fileName)",
    ))
    require(SRC / "EmuleNextSchedulerTelemetry.cpp", (
        "scheduler_outcomes",
        "idx_scheduler_outcomes_hash_ts",
        "m_persistOutcomeQueue",
        "UPDATE scheduler_decisions SET applied=1",
    ))
    require(SRC / "EmuleNextSchedulerTelemetryReader.cpp", (
        "LoadRecentForFile",
        "scheduler_decisions",
        "scheduler_outcomes",
        "PRAGMA query_only=ON",
    ))
    require(SRC / "EmuleNextDashboardWnd.cpp", (
        "EMULENEXT_DASHBOARD_INTELLIGENCE2" if False else "CEmuleNextSchedulerTelemetryReader",
        "theEmuleNextScheduler.GetRuntimeStatusText()",
        "theEmuleNextScheduler.ForceAnalyze",
        "theEmuleNextScheduler.ResetFileIntelligence",
        "CEmuleNextTransferInsights::Build(file, historical)",
    ))

    for hot in ("EmuleNextDashboardWnd.cpp", "EmuleNextSmartScheduler.cpp", "DownloadQueue.cpp", "PartFile.cpp", "DownloadListCtrl.cpp"):
        text = (SRC / hot).read_bytes().decode("latin-1", errors="ignore").lower()
        if "sqlite3_" in text or "winsqlite3.h" in text:
            raise SystemExit(f"Smart Scheduler product verification failed: SQLite in hot/UI path {hot}")

    print("eMule Next Smart Scheduler product verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
