#!/usr/bin/env python3
"""Hardening gate for Search 2.0 filter parity and bulk actions."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def read(name: str) -> str:
    path = SRC / name
    if not path.exists():
        raise SystemExit(f"Search 2 hardening verifier: missing {path}")
    return path.read_bytes().decode("latin-1", errors="ignore")


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise SystemExit(f"Search 2 hardening verifier: missing {label}: {marker}")


def main() -> int:
    service_h = read("Search2Service.h")
    service_cpp = read("Search2Service.cpp")
    wnd_h = read("Search2Wnd.h")
    wnd_cpp = read("Search2Wnd.cpp")

    require(service_h, "FilterBlocked(std::vector<EmuleNextUnifiedSearchResult>& rows) const", "unified block filtering API")
    require(service_cpp, "std::remove_if(rows.begin(), rows.end()", "single-pass block-rule filtering")
    require(service_cpp, "MatchesAnyRule(row, rules)", "shared block matching")
    require(wnd_h, "CEdit m_maxSources", "max-peers UI")
    require(wnd_h, "ApplyBulkAction(bool favorite)", "bulk action helper")

    for marker, label in (
        ("SnapshotLiveResults(context->request, context->liveRows)", "request-aware live snapshot"),
        ("request.filter.minSize", "live min-size filter"),
        ("request.filter.maxSize", "live max-size filter"),
        ("request.filter.extension", "live extension filter"),
        ("request.filter.minSources", "live min-peer filter"),
        ("request.filter.maxSources", "live max-peer filter"),
        ("request.filter.excludePreviouslyDownloaded", "live previous-download filter"),
        ("request.filter.favoritesOnly || request.filter.missingOnly", "historical-only predicate guard"),
        ("service.FilterBlocked(result->rows)", "worker-side unified rule filter"),
        ("m_maxSources.GetWindowText", "max-peer filter read"),
        ("search.filter.maxSources", "max-peer saved-search restore"),
        ("Favorite selected", "bulk favorite menu"),
        ("Add selected to Download Later", "bulk download-later menu"),
        ("changed < 2000", "bounded bulk action"),
        ("SaveFavorite(record)", "non-blocking favorite queue"),
        ("SaveDownloadLater(file)", "non-blocking download-later queue"),
    ):
        require(wnd_cpp, marker, label)

    snapshot_start = wnd_cpp.find("void CSearch2Wnd::SnapshotLiveResults")
    snapshot_end = wnd_cpp.find("CString CSearch2Wnd::SourceText", snapshot_start)
    if snapshot_start < 0 or snapshot_end < 0:
        raise SystemExit("Search 2 hardening verifier: live snapshot body missing")
    snapshot = wnd_cpp[snapshot_start:snapshot_end]
    if "Database()" in snapshot or "sqlite" in snapshot.lower():
        raise SystemExit("Search 2 hardening verifier: live snapshot performs database work on the GUI thread")

    worker_start = wnd_cpp.find("UINT AFX_CDECL SearchWorker")
    worker_end = wnd_cpp.find("BEGIN_MESSAGE_MAP", worker_start)
    if worker_start < 0 or worker_end < 0 or "FilterBlocked" not in wnd_cpp[worker_start:worker_end]:
        raise SystemExit("Search 2 hardening verifier: unified block filtering is not in the background worker")

    print("Search 2.0 hardening gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
