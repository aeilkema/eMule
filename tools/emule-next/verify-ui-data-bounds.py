#!/usr/bin/env python3
"""Guard bounded data loads for eMule Next history-heavy views."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def load(name: str) -> str:
    path = SRC / name
    if not path.exists():
        raise SystemExit(f"UI data bounds: missing {name}")
    return path.read_bytes().decode("latin-1", errors="ignore")


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise SystemExit(f"UI data bounds: missing {label}")


def main() -> int:
    known = load("KnownUsersService.cpp")
    search_service = load("Search2Service.cpp")
    search_ui = load("Search2Wnd.cpp")
    library_service = load("LibraryBrowserService.cpp")
    library_ui = load("FileLibraryWnd.cpp")
    transfer_insights = load("EmuleNextTransferInsights.cpp")

    require(known, "kMaximumKnownUsers = 5000", "Known Users row cap")
    require(known, "kMaximumKnownFilesPerUser = 5000", "Known User file row cap")
    require(known, "LIMIT ?1", "parameterized Known Users limit")
    require(known, "LIMIT ?2", "parameterized Known User files limit")

    require(search_service, "request.maximumResults", "Search 2 result cap")
    require(search_service, "request.pageSize", "Search 2 paging")
    require(search_service, "std::min<size_t>(5000", "Search 2 page-size safety cap")
    require(search_ui, "context->request.maximumResults = 2000", "Search 2 UI result cap")
    require(search_ui, "context->request.pageSize = 500", "Search 2 UI page size")

    require(library_service, "ORDER BY f.last_seen DESC LIMIT 10000", "Library database safety cap")
    require(library_service, "maximumRows", "Library caller result cap")
    require(library_ui, "service.List(context->filter, result->rows, 5000)", "Library UI result cap")

    require(transfer_insights, "kMaxSourceQualitySamples = 32", "source-quality sample cap")
    require(transfer_insights, "kMaxPartChecksPerSource = 256", "per-source part-check cap")

    print("eMule Next UI/data bounds verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())