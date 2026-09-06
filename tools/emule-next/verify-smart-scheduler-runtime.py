#!/usr/bin/env python3
"""Fail fast when Smart Scheduler runtime activation is incomplete."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"

CHECKS = {
    "EmuleNextSmartScheduler.h": (
        "void Tick(CDownloadQueue* queue);",
        "ForceAnalyze",
        "ResetFileIntelligence",
        "AdjustPartRank",
        "PreferA4AFCandidate",
        "EmuleNextInterventionOutcome",
        "lastDiscoveryAt",
        "lastA4AFAt",
        "lastRarePartAt",
    ),
    "EmuleNextSmartScheduler.cpp": (
        "LoadMaxFilesPerRound()",
        "SmartSchedulerMaxFilesPerRound",
        "SmartHistoryCacheCapacity",
        "SmartTelemetryCapacity",
        "SendLocalSrcRequest(file)",
        "PruneSnapshots(queue, now)",
        "sinceDiscovery",
        "UpdateOutcome(file, insight, now)",
        "RecordOutcomeBaseline",
        "RecordOutcomeSample",
    ),
    "EmuleNextTransferInsights.cpp": (
        "kMaxSourceQualitySamples",
        "kMaxPartChecksPerSource",
        "BuildBoundedSourceProfile",
        "averageSourceQuality",
        "strongSources",
        "normalSources",
        "weakSources",
        "failedSources",
        "insight.parts.resize(partCount)",
    ),
    "EmuleNextSchedulerTelemetry.cpp": (
        "m_capacity(256)",
        "m_persistAppliedQueue",
        "m_persistOutcomeQueue",
        "scheduler_outcomes",
        "file_hash BLOB",
    ),
    "EmuleNextSchedulerTelemetryReader.cpp": (
        "LoadRecentForFile",
        "PRAGMA query_only=ON",
    ),
    "EmuleNextHistoryCache.cpp": (
        "ewmaBytesPerSecond * 0.82",
        "m_capacity(4096)",
        "EnforceCapacityLocked()",
        "bool CEmuleNextHistoryCache::Remove",
        "DELETE FROM scheduler_file_history",
    ),
    "DownloadQueue.cpp": ("theEmuleNextScheduler.Tick(this)",),
    "DownloadClient.cpp": ("theEmuleNextScheduler.PreferA4AFCandidate",),
    "PartFile.cpp": ("theEmuleNextScheduler.AdjustPartRank",),
    "emule.vcxproj": (
        'ClCompile Include="EmuleNextSmartScheduler.cpp"',
        'ClCompile Include="EmuleNextTransferInsights.cpp"',
        'ClCompile Include="EmuleNextHistoryCache.cpp"',
        'ClCompile Include="EmuleNextSchedulerTelemetry.cpp"',
        'ClCompile Include="EmuleNextSchedulerTelemetryReader.cpp"',
        'ClInclude Include="EmuleNextSchedulerTelemetryReader.h"',
    ),
}


def main() -> int:
    missing: list[str] = []
    for name, markers in CHECKS.items():
        path = SRC / name
        if not path.exists():
            missing.append(f"{name}: file missing")
            continue
        text = path.read_bytes().decode("latin-1", errors="ignore")
        for marker in markers:
            if marker not in text:
                missing.append(f"{name}: missing {marker!r}")

    if missing:
        print("Smart Scheduler runtime verification FAILED")
        for item in missing:
            print(f"  - {item}")
        raise SystemExit(2)

    print("Smart Scheduler runtime verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
