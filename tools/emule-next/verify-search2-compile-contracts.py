#!/usr/bin/env python3
"""Verify Search 2 generated C++ avoids known overload/const compile failures."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def load(name: str) -> str:
    path = SRC / name
    if not path.exists():
        raise SystemExit(f"Search 2 compile verifier: missing {path}")
    return path.read_bytes().decode("latin-1", errors="ignore")


def main() -> int:
    service = load("Search2Service.cpp")
    header = load("Search2Wnd.h")
    wnd = load("Search2Wnd.cpp")

    required = (
        (service, "bool LoadInternalRules(sqlite3* db, std::vector<SearchRule>& rules)", "internal rule-loader rename"),
        (service, "LoadInternalRules(ruleDb, rules)", "history rule-load call"),
        (service, "LoadInternalRules(db, rules)", "service rule-load call"),
        (header, "SnapshotLiveResults(const EmuleNextSearchRequest& request, std::vector<EmuleNextUnifiedSearchResult>& rows);", "non-const snapshot declaration"),
        (wnd, "void CSearch2Wnd::SnapshotLiveResults(const EmuleNextSearchRequest& request, std::vector<EmuleNextUnifiedSearchResult>& rows)", "non-const snapshot implementation"),
        (wnd, "CSearchResultsWnd* host = DYNAMIC_DOWNCAST(CSearchResultsWnd, GetParent());", "mutable legacy list host"),
    )
    for text, marker, label in required:
        if marker not in text:
            raise SystemExit(f"Search 2 compile verifier: missing {label}")

    if "bool LoadRules(sqlite3* db, std::vector<SearchRule>& rules)" in service:
        raise SystemExit("Search 2 compile verifier: colliding internal LoadRules helper remains")
    if "std::vector<EmuleNextUnifiedSearchResult>& rows) const" in header:
        raise SystemExit("Search 2 compile verifier: const live-snapshot declaration remains")

    print("Search 2 compile-contract verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
