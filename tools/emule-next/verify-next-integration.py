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
        print("eMule Next integration verification FAILED")
        for item in missing:
            print(f"  - {item}")
        raise SystemExit(2)

    print("eMule Next integration verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
