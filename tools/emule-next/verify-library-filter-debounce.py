#!/usr/bin/env python3
"""Verify Library text filtering does not rebuild the list on every keystroke."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
CPP = ROOT / "srchybrid" / "FileLibraryWnd.cpp"
HEADER = ROOT / "srchybrid" / "FileLibraryWnd.h"


def main() -> int:
    cpp = CPP.read_bytes().decode("latin-1", errors="ignore")
    header = HEADER.read_bytes().decode("latin-1", errors="ignore")
    for marker in (
        "EN_LIBRARY_FILTER_TIMER",
        "ON_WM_TIMER()",
        "SetTimer(EN_LIBRARY_FILTER_TIMER, 250, NULL)",
        "KillTimer(EN_LIBRARY_FILTER_TIMER)",
        "void CFileLibraryWnd::OnTimer(UINT_PTR eventId)",
    ):
        if marker not in cpp:
            raise SystemExit(f"Library debounce verification failed: missing {marker}")
    if "afx_msg void OnTimer(UINT_PTR eventId);" not in header:
        raise SystemExit("Library debounce verification failed: timer handler declaration missing")

    start = cpp.find("void CFileLibraryWnd::OnTextFilterChanged()")
    end = cpp.find("void CFileLibraryWnd::OnTimer", start)
    if start < 0 or end < 0:
        raise SystemExit("Library debounce verification failed: filter handler boundaries missing")
    body = cpp[start:end]
    if "PopulateRows()" in body:
        raise SystemExit("Library debounce verification failed: immediate full list rebuild remains in text-change handler")

    print("Library text-filter debounce verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())