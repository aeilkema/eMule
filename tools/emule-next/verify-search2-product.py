#!/usr/bin/env python3
"""Completion gate for the Search 2.0 product tranche."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def text(name: str) -> str:
    path = SRC / name
    if not path.exists():
        raise SystemExit(f"Search 2 verifier: missing {path}")
    return path.read_bytes().decode("latin-1", errors="ignore")


def require(haystack: str, needle: str, label: str) -> None:
    if needle not in haystack:
        raise SystemExit(f"Search 2 verifier: missing {label}: {needle}")


def has_database_call(source: str) -> bool:
    forbidden = (
        "theEmuleNext.Database()",
        "Database().",
        "sqlite3_",
        "winsqlite3",
        "CSearch2Service service",
        "CLibraryBrowserService",
    )
    return any(token in source for token in forbidden)


def main() -> int:
    service_h = text("Search2Service.h")
    service_cpp = text("Search2Service.cpp")
    wnd_h = text("Search2Wnd.h")
    wnd_cpp = text("Search2Wnd.cpp")

    for needle, label in (
        ("ENS2_SOURCE_LIVE_ED2K", "live eD2K provenance"),
        ("ENS2_SOURCE_LIVE_KAD", "live Kad provenance"),
        ("ENS2_SOURCE_HISTORICAL", "historical provenance"),
        ("ENS2_SOURCE_PREVIOUSLY_DOWNLOADED", "previous-download provenance"),
        ("ENS2_SOURCE_KNOWN_PEER", "known-peer provenance"),
        ("EmuleNextUnifiedSearchResult", "unified result model"),
        ("CString extension", "extension filter"),
        ("uint64 lastSeenAfter", "last-seen filter"),
        ("uint32 minSources", "minimum source filter"),
        ("uint32 maxSources", "maximum source filter"),
        ("LoadRules(std::vector<EmuleNextSearchBlockRule>& rules) const", "block-rule read API"),
    ):
        require(service_h, needle, label)

    for needle, label in (
        ("v2;%I64u;%I64u;%u;%u;%u;%s;%I64u;%u;%u", "saved-filter v2 codec"),
        ("filter.lastSeenAfter != 0", "last-seen filtering"),
        ("filter.minSources != 0", "minimum source filtering"),
        ("filter.maxSources != 0", "maximum source filtering"),
        ("CSearch2Service::LoadRules", "visible block-rule loading"),
    ):
        require(service_cpp, needle, label)

    for needle, label in (
        ("SnapshotLiveResults", "legacy live-result snapshot"),
        ("SortRows", "result sorting"),
        ("ExportRows", "result export"),
        ("ShowRulesMenu", "block-rule management UI"),
        ("CEdit m_extension", "extension UI"),
        ("CEdit m_minSize", "minimum-size UI"),
        ("CEdit m_maxSize", "maximum-size UI"),
        ("CComboBox m_lastSeen", "last-seen UI"),
        ("CEdit m_minSources", "availability UI"),
        ("CButton m_export", "export action"),
        ("CButton m_rules", "block-rule action"),
    ):
        require(wnd_h, needle, label)

    for needle, label in (
        ("min(host->searchlistctrl.GetItemCount(), 2000)", "bounded live snapshot"),
        ("live->IsKademlia() ? ENS2_SOURCE_LIVE_KAD : ENS2_SOURCE_LIVE_ED2K", "network provenance classification"),
        ("existing.fileHash.bytes == row.fileHash.bytes && existing.fileSize == row.fileSize", "hash+size merge identity"),
        ("ENS2_SOURCE_PREVIOUSLY_DOWNLOADED", "previous-download source label"),
        ("ENS2_SOURCE_KNOWN_PEER", "known-peer source label"),
        ("Live eD2K", "live eD2K label"),
        ("Live Kad", "live Kad label"),
        ("Historical", "historical label"),
        ("Previously downloaded", "previous-download label"),
        ("Known peer", "known-peer label"),
        ("LVN_COLUMNCLICK", "column sorting event"),
        ("std::stable_sort", "stable result sort"),
        ("new since last run", "saved-search delta UX"),
        ("LVS_REPORT | LVS_SHOWSELALWAYS", "multi-selection list"),
        ("Export selected", "bulk export action"),
        ("Export all results", "full result export"),
        ("Manage block rules", "context-menu rule management"),
        ("service.AddRule(ENSBR_EXTENSION", "extension block rule"),
        ("service.RemoveRule(rule.type, rule.pattern)", "block rule removal"),
        ("SearchFiles", "historical database search contract"),
    ):
        require(wnd_cpp if needle != "SearchFiles" else service_cpp, needle, label)

    if "LVS_SINGLESEL" in wnd_cpp:
        raise SystemExit("Search 2 verifier: result list is still single-select")

    snapshot_start = wnd_cpp.find("void CSearch2Wnd::SnapshotLiveResults")
    snapshot_end = wnd_cpp.find("CString CSearch2Wnd::SourceText", snapshot_start)
    if snapshot_start < 0 or snapshot_end < 0:
        raise SystemExit("Search 2 verifier: snapshot body not found")
    snapshot = wnd_cpp[snapshot_start:snapshot_end]
    if has_database_call(snapshot):
        raise SystemExit("Search 2 verifier: live snapshot performs database work on the UI thread")

    print("Search 2.0 completion gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
