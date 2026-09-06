#!/usr/bin/env python3
"""Verify Transfers file rows use the canonical shared intelligence builder."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "DownloadListCtrl.cpp"


def main() -> int:
    text = PATH.read_bytes().decode("latin-1", errors="ignore")
    required = (
        '#include "EmuleNextTransferInsights.h"',
        '#include "EmuleNextSmartScheduler.h"',
        'InsertColumn(19,\t_T("Hist. speed")',
        'InsertColumn(20,\t_T("Source quality")',
        'InsertColumn(21,\t_T("Source profile")',
        'InsertColumn(22,\t_T("Scheduler")',
        'const EmuleNextTransferInsight insight = CEmuleNextTransferInsights::Build(file, historical);',
        'insight.averageSourceQuality',
        'insight.strongSources',
        'theEmuleNextScheduler.GetSnapshot',
        'nColumn >= 16 && nColumn <= 22',
    )
    for marker in required:
        if marker not in text:
            raise SystemExit(f"Transfers Intelligence 2.0 missing {marker}")
    if "EmuleNextFileSignals BuildNextFileSignals" in text:
        raise SystemExit("Transfers Intelligence 2.0 duplicate file-signal builder remains")
    print("Transfers shared Intelligence 2.0 verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
