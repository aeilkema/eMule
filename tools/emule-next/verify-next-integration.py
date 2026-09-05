#!/usr/bin/env python3
"""Fail fast when the eMule Next local overlay is only partially activated."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"

CHECKS = {
    "EmuleNextDashboardWnd.cpp": (
        "void CEmuleNextDashboardWnd::OnOpenTransfers()",
        "void CEmuleNextDashboardWnd::OnPauseResume()",
        "BuildLiveSourceProfile(CPartFile* file)",
        "Live sources: %u tracked",
        "JumpToTransfers(true)",
    ),
    "EmuleNextDashboardWnd.h": (
        "CButton m_openTransfers;",
        "void UpdateActionButtons();",
        "afx_msg void OnPriorityHigh();",
    ),
    "DownloadListCtrl.h": (
        "SelectFile(CPartFile *file, bool expand = false)",
    ),
    "DownloadListCtrl.cpp": (
        "bool CDownloadListCtrl::SelectFile(CPartFile *file, bool expand)",
        "Live quality",
        "Smart ETA",
    ),
    "TransferWnd.cpp": (
        "EMULENEXT_DASHBOARD_VIEW",
        "void CTransferWnd::ShowNextDashboard()",
        "message == WM_APP + 0x568",
        "downloadlistctrl.SelectFile(file, wParam != 0)",
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
