#!/usr/bin/env python3
"""Fix Search 2 generated C++ compile contracts after product materialization."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
SERVICE_CPP = SRC / "Search2Service.cpp"
WND_H = SRC / "Search2Wnd.h"
WND_CPP = SRC / "Search2Wnd.cpp"


def read(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def write(path: pathlib.Path, text: str, encoding: str) -> None:
    path.write_bytes(text.encode(encoding))


def patch_service() -> None:
    text, enc = read(SERVICE_CPP)
    # Namespace helper and public service method had the same name. Inside
    # CSearch2Service methods, unqualified LoadRules(db, rules) resolves to the
    # member first and causes C2660. Give the internal helper a unique name.
    text = text.replace(
        "    bool LoadRules(sqlite3* db, std::vector<SearchRule>& rules)",
        "    bool LoadInternalRules(sqlite3* db, std::vector<SearchRule>& rules)")
    text = text.replace("LoadRules(ruleDb, rules)", "LoadInternalRules(ruleDb, rules)")
    text = text.replace("LoadRules(db, rules)", "LoadInternalRules(db, rules)")
    write(SERVICE_CPP, text, enc)


def patch_window() -> None:
    header, henc = read(WND_H)
    header = header.replace(
        "    void SnapshotLiveResults(const EmuleNextSearchRequest& request, std::vector<EmuleNextUnifiedSearchResult>& rows) const;",
        "    void SnapshotLiveResults(const EmuleNextSearchRequest& request, std::vector<EmuleNextUnifiedSearchResult>& rows);")
    write(WND_H, header, henc)

    cpp, cenc = read(WND_CPP)
    cpp = cpp.replace(
        "void CSearch2Wnd::SnapshotLiveResults(const EmuleNextSearchRequest& request, std::vector<EmuleNextUnifiedSearchResult>& rows) const",
        "void CSearch2Wnd::SnapshotLiveResults(const EmuleNextSearchRequest& request, std::vector<EmuleNextUnifiedSearchResult>& rows)")
    cpp = cpp.replace(
        "    const CSearchResultsWnd* host = DYNAMIC_DOWNCAST(CSearchResultsWnd, GetParent());",
        "    CSearchResultsWnd* host = DYNAMIC_DOWNCAST(CSearchResultsWnd, GetParent());")
    write(WND_CPP, cpp, cenc)


def main() -> int:
    for path in (SERVICE_CPP, WND_H, WND_CPP):
        if not path.exists():
            raise SystemExit(f"Search 2 compile fixes: missing {path}")
    patch_service()
    patch_window()
    print("Search 2 internal rule-loader naming and live-snapshot const contracts fixed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
