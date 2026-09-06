#!/usr/bin/env python3
"""Static compile-contract gate for Library 2.0."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def read(name: str) -> str:
    path = SRC / name
    if not path.exists():
        raise SystemExit(f"Library 2 compile verifier: missing {path}")
    return path.read_bytes().decode("latin-1", errors="ignore")


def require(source: str, marker: str, label: str) -> None:
    if marker not in source:
        raise SystemExit(f"Library 2 compile verifier: missing {label}: {marker}")


def main() -> int:
    header = read("FileLibraryWnd.h")
    cpp = read("FileLibraryWnd.cpp")
    runtime_h = read("EmuleNextRuntime.h")
    download_cpp = read("DownloadQueue.cpp")
    queue_h = read("DownloadQueue.h")
    known_h = read("KnownFile.h")

    for marker, label in (
        ("int SelectedIndex();", "non-const selected-index helper"),
        ("std::vector<size_t> SelectedIndices(size_t limit = 2000);", "non-const bounded selection helper"),
    ):
        require(header, marker, label)

    for marker, label in (
        ('#include "KnownFile.h"', "legacy file-hash dependency"),
        ("#include <afxdlgs.h>", "MFC file-dialog dependency"),
        ("int CFileLibraryWnd::SelectedIndex()", "selected-index implementation"),
        ("std::vector<size_t> CFileLibraryWnd::SelectedIndices(size_t limit)", "selection implementation"),
        ("theEmuleNext.IsDownloadQueued(row.fileHash.bytes.data())", "download duplicate bridge call"),
        ("theEmuleNext.AddLibraryDownload(name, row.fileSize, hash)", "legacy download bridge call"),
        ("CKnownFile candidate;", "relink hash object"),
        ("candidate.CreateFromFile(directory, name, NULL)", "legacy file hash call"),
    ):
        require(cpp, marker, label)

    for marker, label in (
        ("bool IsDownloadQueued(const unsigned char* fileHash) const;", "runtime duplicate-check bridge declaration"),
        ("bool AddLibraryDownload(LPCTSTR fileName, uint64 fileSize, LPCTSTR ed2kHash);", "runtime add-download bridge declaration"),
    ):
        require(runtime_h, marker, label)

    for marker, label in (
        ("bool CEmuleNextRuntime::IsDownloadQueued(const unsigned char* fileHash) const", "duplicate bridge implementation"),
        ("bool CEmuleNextRuntime::AddLibraryDownload(LPCTSTR fileName, uint64 fileSize, LPCTSTR ed2kHash)", "download bridge implementation"),
        ("CED2KFileLink link(fileName, size, ed2kHash, params, NULL);", "legacy link construction in valid legacy TU"),
        ("theApp.downloadqueue->AddFileLinkToDownload(link);", "legacy download queue call in valid legacy TU"),
        ("theApp.downloadqueue->IsFileExisting(link.GetHashKey(), false)", "post-add duplicate verification"),
    ):
        require(download_cpp, marker, label)

    require(queue_h, "void\tAddFileLinkToDownload(const CED2KFileLink &Link, int cat = 0);", "download queue link API")
    require(queue_h, "bool\tIsFileExisting(const uchar *fileid, bool bLogWarnings = true) const;", "download duplicate API")
    require(known_h, "bool\tCreateFromFile(LPCTSTR directory, LPCTSTR filename, LPVOID pvProgressParam);", "known-file hash API")

    if '#include "DownloadQueue.h"' in cpp or '#include "ED2KLink.h"' in cpp:
        raise SystemExit("Library 2 compile verifier: Library UI directly includes legacy download headers")
    if "theApp.downloadqueue->" in cpp:
        raise SystemExit("Library 2 compile verifier: Library UI directly accesses downloadqueue")

    stale = (
        "SelectedIndex() const",
        "SelectedIndices(size_t limit = 2000) const",
        "CFileLibraryWnd::SelectedIndex() const",
        "CFileLibraryWnd::SelectedIndices(size_t limit) const",
    )
    for marker in stale:
        if marker in header or marker in cpp:
            raise SystemExit(f"Library 2 compile verifier: stale const MFC selection contract remains: {marker}")

    print("Library 2.0 compile-contract verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
