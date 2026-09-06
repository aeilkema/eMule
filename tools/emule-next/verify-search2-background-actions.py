#!/usr/bin/env python3
"""Verify Search 2 user-triggered SQLite mutations run in a background worker."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
CPP = ROOT / "srchybrid" / "Search2Wnd.cpp"
HEADER = ROOT / "srchybrid" / "Search2Wnd.h"


def method(text: str, signature: str, next_signature: str) -> str:
    start = text.find(signature)
    end = text.find(next_signature, start + len(signature))
    if start < 0 or end < 0:
        raise SystemExit(f"Search 2 background actions verification failed: method boundary missing for {signature}")
    return text[start:end]


def main() -> int:
    cpp = CPP.read_bytes().decode("latin-1", errors="ignore")
    header = HEADER.read_bytes().decode("latin-1", errors="ignore")

    for marker in (
        "SearchActionWorker",
        "ENS2_ACTION_SAVE_SEARCH",
        "ENS2_ACTION_DELETE_SEARCH",
        "ENS2_ACTION_BLOCK_HASH",
        "AfxBeginThread(SearchActionWorker",
        "WM_EN_SEARCH2_ACTION_FINISHED",
        "OnSearchActionFinished",
        "m_actionLoading",
    ):
        if marker not in cpp and marker not in header:
            raise SystemExit(f"Search 2 background actions verification failed: missing {marker}")

    save = method(cpp, "void CSearch2Wnd::OnSaveSearchClicked()", "void CSearch2Wnd::OnDeleteSearchClicked()")
    delete = method(cpp, "void CSearch2Wnd::OnDeleteSearchClicked()", "EmuleNextSearchFilter CSearch2Wnd::CurrentFilter()")
    block = method(cpp, "void CSearch2Wnd::OnBlockClicked()", "LRESULT CSearch2Wnd::OnSearchActionFinished")
    for label, body in (("save", save), ("delete", delete), ("block", block)):
        if "CSearch2Service service" in body:
            raise SystemExit(f"Search 2 background actions verification failed: synchronous service remains in UI {label} handler")
        if "AfxBeginThread(SearchActionWorker" not in body:
            raise SystemExit(f"Search 2 background actions verification failed: {label} handler does not start worker")

    worker_start = cpp.find("UINT AFX_CDECL SearchActionWorker")
    worker_end = cpp.find("struct SavedSearchLoadContext", worker_start)
    if worker_start < 0 or worker_end < 0:
        raise SystemExit("Search 2 background actions verification failed: worker boundary missing")
    worker = cpp[worker_start:worker_end]
    for marker in ("service.SaveSearch", "service.DeleteSavedSearch", "service.AddHashBlock"):
        if marker not in worker:
            raise SystemExit(f"Search 2 background actions verification failed: worker missing {marker}")

    print("Search 2 background actions verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())