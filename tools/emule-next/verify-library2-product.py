#!/usr/bin/env python3
"""Completion gate for the Library 2.0 product tranche."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def read(name: str) -> str:
    path = SRC / name
    if not path.exists():
        raise SystemExit(f"Library 2 verifier: missing {path}")
    return path.read_bytes().decode("latin-1", errors="ignore")


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise SystemExit(f"Library 2 verifier: missing {label}: {marker}")


def main() -> int:
    db_h = read("EmuleNextDatabase.h")
    db_cpp = read("EmuleNextDatabase.cpp")
    svc_h = read("LibraryBrowserService.h")
    svc_cpp = read("LibraryBrowserService.cpp")
    wnd_h = read("FileLibraryWnd.h")
    wnd_cpp = read("FileLibraryWnd.cpp")
    runtime_h = read("EmuleNextRuntime.h")
    download_cpp = read("DownloadQueue.cpp")

    for marker, label in (
        ("RemoveDownloadLater(const EmuleNextHash16& fileHash, uint64 fileSize)", "Download Later removal queue API"),
        ("UpdateLibraryVerification(const EmuleNextHash16& fileHash, uint64 fileSize, bool missing)", "path verification queue API"),
        ("RelinkLibraryFile(const EmuleNextHash16& fileHash, uint64 fileSize, const CStringW& localPath)", "relink queue API"),
    ):
        require(db_h, marker, label)

    for marker, label in (
        ("EventKind::RemoveDownloadLater", "queued Download Later deletion"),
        ("EventKind::LibraryVerified", "queued Library verification"),
        ("EventKind::LibraryRelinked", "queued Library relink"),
        ("DELETE FROM download_later", "Download Later delete SQL"),
        ("missing_since=COALESCE(missing_since,?3)", "missing state persistence"),
        ("missing_since=NULL", "recovered state persistence"),
        ("UPDATE library_entries SET local_path=?3", "relink path persistence"),
    ):
        require(db_cpp, marker, label)

    for marker, label in (
        ("uint32 recentPeerCount", "recent peer availability"),
        ("bool availableAgain", "available-again state"),
        ("uint64 lastVerified", "verification timestamp"),
        ("uint64 missingSince", "missing timestamp"),
        ("uint64 completedAt", "completion timestamp for rediscovery matching"),
    ):
        require(svc_h, marker, label)

    for marker, label in (
        ("PRAGMA query_only=ON", "query-only Library read connection"),
        ("LIBRARY_SQL_LIMIT = 10000", "hard SQL result bound"),
        ("rows.size() >= maximumRows", "caller result bound"),
        ("GetFileAttributesW", "background filesystem verification"),
        ("COUNT(DISTINCT pf.peer_id)", "hash-linked peer availability"),
        ("pf.last_seen>=?1", "recent availability window"),
        ("COALESCE(le.completed_at,0)", "completion timestamp query"),
        ("row.completed = row.completedAt != 0", "completion timestamp decode"),
        ("row.lastSeen > row.completedAt + 60", "Search/history rediscovery availability"),
        ("row.recentPeerCount != 0", "known-peer rediscovery availability"),
    ):
        require(svc_cpp, marker, label)

    for marker, label in (
        ("EMULENEXT_LIBRARY2_PRODUCT", "Library 2 product marker"),
        ("std::vector<size_t> SelectedIndices(size_t limit = 2000);", "bounded multi-selection contract"),
        ("OnDownloadAgainClicked", "Download again action"),
        ("OnRelinkClicked", "relink action"),
        ("OnColumnClick", "column sorting"),
        ("OnContextMenu", "context menu"),
        ("LoadViewState", "persistent view state"),
        ("ApplyColumnWidths", "persistent column widths"),
    ):
        require(wnd_h, marker, label)

    for marker, label in (
        ("LVS_REPORT | LVS_SHOWSELALWAYS", "multi-select result list"),
        ("std::stable_sort", "stable Library sorting"),
        ("PROFILE_SECTION = _T(\"eMule Next Library 2\")", "Library persistence namespace"),
        ("WriteProfileInt(PROFILE_SECTION, _T(\"View\")", "view persistence"),
        ("WriteProfileInt(PROFILE_SECTION, _T(\"SortColumn\")", "sort persistence"),
        ("WriteProfileString(PROFILE_SECTION, _T(\"TextFilter\")", "text filter persistence"),
        ("ColumnWidth%d", "column width persistence"),
        ("CFileLibraryWnd::SelectedIndices(size_t limit)", "bulk selection implementation"),
        ("indices.size() < limit", "bounded bulk selection implementation"),
        ("RemoveDownloadLater(row.fileHash, row.fileSize)", "Download Later toggle removal"),
        ("theEmuleNext.AddLibraryDownload(name, row.fileSize, hash)", "Library runtime download bridge"),
        ("theEmuleNext.IsDownloadQueued(row.fileHash.bytes.data())", "Library runtime duplicate guard"),
        ("CKnownFile candidate", "legacy ED2K hashing implementation"),
        ("candidate.CreateFromFile(directory, name, NULL)", "background relink hashing"),
        ("memcmp(candidate.GetFileHash(), context->hash.bytes.data(), 16) == 0", "ED2K hash match"),
        ("candidate.GetFileSize()) == context->fileSize", "size match"),
        ("RelinkLibraryFile(result->hash, result->fileSize, result->path)", "verified relink persistence"),
        ("Available again", "available-again UI"),
        ("Verify paths", "explicit path refresh"),
        ("Export selected", "bulk export action"),
        ("Export current view", "view export action"),
        ("ON_WM_CONTEXTMENU()", "context menu message map"),
        ("ON_NOTIFY(LVN_COLUMNCLICK", "sort message map"),
        ("AfxBeginThread(RelinkWorker", "background relink verification"),
        ("AfxBeginThread(LibraryWorker", "background Library load"),
        ("UpdateLibraryVerification(row.fileHash, row.fileSize, row.missing)", "queued verification persistence"),
    ):
        require(wnd_cpp, marker, label)

    for marker, label in (
        ("bool AddLibraryDownload(LPCTSTR fileName, uint64 fileSize, LPCTSTR ed2kHash);", "runtime download bridge declaration"),
        ("bool IsDownloadQueued(const unsigned char* fileHash) const;", "runtime duplicate bridge declaration"),
    ):
        require(runtime_h, marker, label)

    for marker, label in (
        ("CED2KFileLink link(fileName, size, ed2kHash, params, NULL);", "legacy ED2K link construction"),
        ("theApp.downloadqueue->AddFileLinkToDownload(link);", "legacy authoritative download route"),
        ("theApp.downloadqueue->IsFileExisting(link.GetHashKey(), false)", "legacy post-add duplicate check"),
    ):
        require(download_cpp, marker, label)

    if "LVS_SINGLESEL" in wnd_cpp:
        raise SystemExit("Library 2 verifier: result list is still single-select")
    if "sqlite3_" in wnd_cpp or "winsqlite3" in wnd_cpp.lower():
        raise SystemExit("Library 2 verifier: direct SQLite remains in Library GUI")
    if "GetFileAttributesW" in wnd_cpp:
        raise SystemExit("Library 2 verifier: filesystem existence checks remain in Library GUI")
    if '#include "DownloadQueue.h"' in wnd_cpp or "theApp.downloadqueue->" in wnd_cpp:
        raise SystemExit("Library 2 verifier: Library UI bypasses runtime download bridge")

    worker_start = wnd_cpp.find("UINT AFX_CDECL RelinkWorker")
    worker_end = wnd_cpp.find("int CompareUInt64", worker_start)
    if worker_start < 0 or worker_end < 0 or "CreateFromFile" not in wnd_cpp[worker_start:worker_end]:
        raise SystemExit("Library 2 verifier: relink hash verification is not confined to worker code")

    print("Library 2.0 completion verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
