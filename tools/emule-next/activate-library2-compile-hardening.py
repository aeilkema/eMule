#!/usr/bin/env python3
"""Compile-contract hardening for the materialized Library 2.0 view.

Runs after the Library 2 product/availability materializers. It keeps MFC list
selection helpers non-const and removes the Library UI's direct dependency on
legacy DownloadQueue.h/ED2KLink.h. The two required download operations are
bridged through CEmuleNextRuntime, with their implementations placed in
DownloadQueue.cpp where the legacy include graph is already valid.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
HEADER = SRC / "FileLibraryWnd.h"
CPP = SRC / "FileLibraryWnd.cpp"
RUNTIME_H = SRC / "EmuleNextRuntime.h"
DOWNLOAD_CPP = SRC / "DownloadQueue.cpp"


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


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Library 2 compile hardening: expected one {label} anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    header, henc = read(HEADER)
    cpp, cenc = read(CPP)
    runtime_h, rhenc = read(RUNTIME_H)
    download_cpp, denc = read(DOWNLOAD_CPP)

    header = header.replace("    int SelectedIndex() const;", "    int SelectedIndex();")
    header = header.replace(
        "    std::vector<size_t> SelectedIndices(size_t limit = 2000) const;",
        "    std::vector<size_t> SelectedIndices(size_t limit = 2000);",
    )
    cpp = cpp.replace("int CFileLibraryWnd::SelectedIndex() const", "int CFileLibraryWnd::SelectedIndex()")
    cpp = cpp.replace(
        "std::vector<size_t> CFileLibraryWnd::SelectedIndices(size_t limit) const",
        "std::vector<size_t> CFileLibraryWnd::SelectedIndices(size_t limit)",
    )

    # Library UI must not include legacy DownloadQueue.h directly; that header
    # relies on transitive legacy definitions such as MDX_DIGEST_SIZE.
    cpp = cpp.replace('#include "DownloadQueue.h"\n', "")
    cpp = cpp.replace('#include "ED2KLink.h"\n', "")

    include = "#include <afxdlgs.h>"
    if include not in cpp:
        anchor = '#include "emule.h"'
        if anchor not in cpp:
            raise SystemExit("Library 2 compile hardening: emule include anchor missing")
        cpp = cpp.replace(anchor, anchor + "\n\n" + include, 1)

    runtime_methods = (
        "\n    // Narrow bridge used by Library 2.0 so its UI does not depend on the\n"
        "    // legacy DownloadQueue header/include graph. File identity stays ED2K hash + size.\n"
        "    bool IsDownloadQueued(const unsigned char* fileHash) const;\n"
        "    bool AddLibraryDownload(LPCTSTR fileName, uint64 fileSize, LPCTSTR ed2kHash);\n"
    )
    if "bool IsDownloadQueued(const unsigned char* fileHash) const;" not in runtime_h:
        anchor = "\nprivate:\n"
        if anchor not in runtime_h:
            raise SystemExit("Library 2 compile hardening: runtime private anchor missing")
        runtime_h = runtime_h.replace(anchor, runtime_methods + anchor, 1)

    bridge_impl = r'''

bool CEmuleNextRuntime::IsDownloadQueued(const unsigned char* fileHash) const
{
    return fileHash != NULL && theApp.downloadqueue != NULL
        && theApp.downloadqueue->IsFileExisting(fileHash, false);
}

bool CEmuleNextRuntime::AddLibraryDownload(LPCTSTR fileName, uint64 fileSize, LPCTSTR ed2kHash)
{
    if (theApp.downloadqueue == NULL || fileName == NULL || ed2kHash == NULL || fileSize == 0)
        return false;

    CString size;
    size.Format(_T("%I64u"), fileSize);
    CStringArray params;
    try {
        CED2KFileLink link(fileName, size, ed2kHash, params, NULL);
        if (theApp.downloadqueue->IsFileExisting(link.GetHashKey(), false))
            return true;
        theApp.downloadqueue->AddFileLinkToDownload(link);
        return theApp.downloadqueue->IsFileExisting(link.GetHashKey(), false);
    }
    catch (...) {
        return false;
    }
}
'''
    if "bool CEmuleNextRuntime::AddLibraryDownload(" not in download_cpp:
        download_cpp += bridge_impl

    cpp = cpp.replace(
        "    if (theApp.downloadqueue == NULL)\n        return;\n",
        "",
        1,
    )
    cpp = cpp.replace(
        "if (theApp.downloadqueue->IsFileExisting(row.fileHash.bytes.data(), false))",
        "if (theEmuleNext.IsDownloadQueued(row.fileHash.bytes.data()))",
    )

    old_block = '''        CString size; size.Format(_T("%I64u"), row.fileSize);
        const CString hash = HashText(row.fileHash);
        CStringArray params;
        try {
            CED2KFileLink link(name, size, hash, params, NULL);
            theApp.downloadqueue->AddFileLinkToDownload(link);
            if (row.downloadLater) {
                theEmuleNext.Database().RemoveDownloadLater(row.fileHash, row.fileSize);
                row.downloadLater = false;
            }
            ++added;
        }
        catch (...) {
            ++failed;
        }'''
    new_block = '''        const CString hash = HashText(row.fileHash);
        if (theEmuleNext.AddLibraryDownload(name, row.fileSize, hash)) {
            if (row.downloadLater) {
                theEmuleNext.Database().RemoveDownloadLater(row.fileHash, row.fileSize);
                row.downloadLater = false;
            }
            ++added;
        }
        else {
            ++failed;
        }'''
    cpp = replace_once(cpp, old_block, new_block, "Download again bridge")

    required_header = (
        "    int SelectedIndex();",
        "    std::vector<size_t> SelectedIndices(size_t limit = 2000);",
    )
    required_cpp = (
        "int CFileLibraryWnd::SelectedIndex()",
        "std::vector<size_t> CFileLibraryWnd::SelectedIndices(size_t limit)",
        include,
        "theEmuleNext.IsDownloadQueued(row.fileHash.bytes.data())",
        "theEmuleNext.AddLibraryDownload(name, row.fileSize, hash)",
    )
    required_runtime = (
        "bool IsDownloadQueued(const unsigned char* fileHash) const;",
        "bool AddLibraryDownload(LPCTSTR fileName, uint64 fileSize, LPCTSTR ed2kHash);",
    )
    required_download = (
        "bool CEmuleNextRuntime::IsDownloadQueued(const unsigned char* fileHash) const",
        "bool CEmuleNextRuntime::AddLibraryDownload(LPCTSTR fileName, uint64 fileSize, LPCTSTR ed2kHash)",
        "theApp.downloadqueue->AddFileLinkToDownload(link);",
    )
    for marker in required_header:
        if marker not in header:
            raise SystemExit(f"Library 2 compile hardening: header contract missing {marker}")
    for marker in required_cpp:
        if marker not in cpp:
            raise SystemExit(f"Library 2 compile hardening: cpp contract missing {marker}")
    for marker in required_runtime:
        if marker not in runtime_h:
            raise SystemExit(f"Library 2 compile hardening: runtime contract missing {marker}")
    for marker in required_download:
        if marker not in download_cpp:
            raise SystemExit(f"Library 2 compile hardening: download bridge missing {marker}")

    if '#include "DownloadQueue.h"' in cpp or '#include "ED2KLink.h"' in cpp:
        raise SystemExit("Library 2 compile hardening: legacy download headers remain in Library UI")
    if "theApp.downloadqueue->" in cpp:
        raise SystemExit("Library 2 compile hardening: direct downloadqueue access remains in Library UI")
    if "SelectedIndex() const" in header or "SelectedIndices(size_t limit = 2000) const" in header:
        raise SystemExit("Library 2 compile hardening: stale const selection declaration remains")

    write(HEADER, header, henc)
    write(CPP, cpp, cenc)
    write(RUNTIME_H, runtime_h, rhenc)
    write(DOWNLOAD_CPP, download_cpp, denc)
    print("Library 2.0 MFC/download-bridge compile contracts hardened")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
