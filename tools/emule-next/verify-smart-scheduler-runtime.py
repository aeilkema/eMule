#!/usr/bin/env python3
"""Fail fast when Smart Scheduler runtime activation is incomplete."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"

CHECKS = {
    "EmuleNextSmartScheduler.h": (
        "void Tick(CDownloadQueue* queue);",
        "AdjustPartRank",
        "PreferA4AFCandidate",
        "CEmuleNextSchedulerTelemetry",
        "CEmuleNextHistoryCache",
    ),
    "EmuleNextSmartScheduler.cpp": (
        "maxPerRound = 8",
        "SmartSchedulerProfile",
        "SmartSchedulerCooldown",
        "SendLocalSrcRequest(file)",
        "PreferA4AFCandidate",
    ),
    "EmuleNextTransferInsights.cpp": (
        "insight.parts.resize(partCount)",
        "GetPartSourceFrequency(part)",
        "historicalBytesPerSecond",
    ),
    "EmuleNextSchedulerTelemetry.cpp": (
        "m_capacity(256)",
        "m_interventions",
    ),
    "EmuleNextHistoryCache.cpp": (
        "ewmaBytesPerSecond * 0.82",
        "m_files.size() > 4096",
    ),
    "DownloadQueue.cpp": (
        "theEmuleNextScheduler.Tick(this)",
    ),
    "DownloadClient.cpp": (
        "theEmuleNextScheduler.PreferA4AFCandidate",
    ),
    "PartFile.cpp": (
        "theEmuleNextScheduler.AdjustPartRank",
    ),
    "emule.vcxproj": (
        'ClCompile Include="EmuleNextSmartScheduler.cpp"',
        'ClCompile Include="EmuleNextTransferInsights.cpp"',
        'ClCompile Include="EmuleNextHistoryCache.cpp"',
        'ClCompile Include="EmuleNextSchedulerTelemetry.cpp"',
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
