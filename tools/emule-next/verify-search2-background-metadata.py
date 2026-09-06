#!/usr/bin/env python3
"""Verify Search 2 recurring saved-search metadata reads stay off the MFC UI thread."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
CPP = ROOT / "srchybrid" / "Search2Wnd.cpp"
HEADER = ROOT / "srchybrid" / "Search2Wnd.h"


def main() -> int:
    cpp = CPP.read_bytes().decode("latin-1", errors="ignore")
    header = HEADER.read_bytes().decode("latin-1", errors="ignore")

    required_cpp = (
        "SavedSearchLoadWorker",
        "AfxBeginThread(SavedSearchLoadWorker",
        "THREAD_PRIORITY_BELOW_NORMAL",
        "WM_EN_SEARCH2_SAVED_LOADED",
        "OnSavedSearchesLoaded",
        "PopulateSavedSearches",
        "m_savedSearchesLoading = true",
        "service.LoadSavedSearches(result->searches)",
    )
    for marker in required_cpp:
        if marker not in cpp:
            raise SystemExit(f"Search 2 background metadata verification failed: missing {marker}")

    required_header = (
        "OnSavedSearchesLoaded(WPARAM, LPARAM value)",
        "PopulateSavedSearches(const CString& previous)",
        "bool m_savedSearchesLoading",
    )
    for marker in required_header:
        if marker not in header:
            raise SystemExit(f"Search 2 background metadata verification failed: header missing {marker}")

    # ReloadSavedSearches itself must only start the worker. A direct service
    # construction in that method would put SQLite back onto the UI thread.
    start = cpp.find("void CSearch2Wnd::ReloadSavedSearches()")
    end = cpp.find("LRESULT CSearch2Wnd::OnSavedSearchesLoaded", start)
    if start < 0 or end < 0:
        raise SystemExit("Search 2 background metadata verification failed: reload method boundaries missing")
    body = cpp[start:end]
    if "CSearch2Service service" in body or ".LoadSavedSearches(" in body:
        raise SystemExit("Search 2 background metadata verification failed: synchronous saved-search read remains in UI reload")

    print("Search 2 background metadata verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())