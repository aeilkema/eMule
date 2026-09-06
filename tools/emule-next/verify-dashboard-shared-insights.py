#!/usr/bin/env python3
"""Ensure Dashboard and Smart Scheduler consume the same transfer insight builder."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "srchybrid" / "EmuleNextDashboardWnd.cpp"


def main() -> int:
    if not DASHBOARD.exists():
        raise SystemExit("Dashboard insights: EmuleNextDashboardWnd.cpp missing")
    text = DASHBOARD.read_bytes().decode("latin-1", errors="ignore")

    required = (
        '#include "EmuleNextTransferInsights.h"',
        "CEmuleNextTransferInsights::Build(file, historicalBytesPerSecond)",
        "row.signals = sharedInsight.file;",
        "row.stall = sharedInsight.stall;",
        "row.health = sharedInsight.health;",
        "row.eta = sharedInsight.eta;",
        "row.attention = sharedInsight.attention;",
    )
    for marker in required:
        if marker not in text:
            raise SystemExit(f"Dashboard insights: missing {marker}")

    forbidden = (
        "EmuleNextFileSignals BuildSignals(",
        "uint32 AttentionScore(",
    )
    for marker in forbidden:
        if marker in text:
            raise SystemExit(f"Dashboard insights: duplicate intelligence remains: {marker}")

    print("Dashboard shared transfer intelligence verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
