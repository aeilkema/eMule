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
    dashboard = load("EmuleNextDashboardWnd.cpp")
    reader = load("EmuleNextSchedulerTelemetryReader.cpp")

    require(known, "kMaximumKnownUsers = 2000", "Known Users row cap")
    require(known, "kMaximumKnownFilesPerUser = 2000", "Known User file row cap")
    require(known, "LIMIT ?5", "parameterized Known Users limit")
    require(known, "LIMIT ?2", "parameterized Known User files limit")
    require(known, "PRAGMA query_only=ON", "Known Users query-only read connection")

    require(search_service, "request.maximumResults", "Search 2 result cap")
    require(search_service, "request.pageSize", "Search 2 paging")
    require(search_service, "std::min<size_t>(5000", "Search 2 page-size safety cap")
    require(search_ui, "context->request.maximumResults = 2000", "Search 2 UI result cap")
    require(search_ui, "context->request.pageSize = 500", "Search 2 UI page size")

    require(library_service, "LIBRARY_SQL_LIMIT = 10000", "Library database safety cap")
    require(library_service, "ORDER BY f.last_seen DESC LIMIT ?2", "parameterized Library SQL limit")
    require(library_service, "sqlite3_bind_int64(statement, 2, static_cast<sqlite3_int64>(LIBRARY_SQL_LIMIT))", "bound Library SQL cap")
    require(library_service, "maximumRows", "Library caller result cap")
    require(library_ui, "service.List(context->filter, result->rows, 5000)", "Library UI result cap")

    require(transfer_insights, "kMaxSourceQualitySamples = 32", "source-quality sample cap")
    require(transfer_insights, "kMaxPartChecksPerSource = 256", "per-source part-check cap")
    require(dashboard, "DASHBOARD_MAX_FILES = 1000", "Dashboard row-analysis cap")
    require(dashboard, "m_lastRefreshDurationMs > 250 ? 6000 : 3000", "Dashboard adaptive refresh")
    require(reader, "std::min<size_t>(100", "scheduler diagnostic query cap")

    print("eMule Next UI/data bounds verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
