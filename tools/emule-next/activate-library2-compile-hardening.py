#!/usr/bin/env python3
"""Compile-contract hardening for the materialized Library 2.0 view.

Runs after the Library 2 product/availability materializers. It keeps MFC list
selection helpers non-const (matching CMFC/CListCtrl APIs used by this legacy
codebase), makes the file-dialog dependency explicit, and preserves the legacy
include-order prerequisite for DownloadQueue.h by ensuring emule.h is included
before that header.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
HEADER = SRC / "FileLibraryWnd.h"
CPP = SRC / "FileLibraryWnd.cpp"


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


def main() -> int:
    header, henc = read(HEADER)
    cpp, cenc = read(CPP)

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

    emule_include = '#include "emule.h"'
    queue_include = '#include "DownloadQueue.h"'
    if emule_include not in cpp or queue_include not in cpp:
        raise SystemExit("Library 2 compile hardening: emule/DownloadQueue include anchor missing")
    if cpp.find(emule_include) > cpp.find(queue_include):
        cpp = cpp.replace(emule_include + "\n", "", 1)
        queue_pos = cpp.find(queue_include)
        cpp = cpp[:queue_pos] + emule_include + "\n" + cpp[queue_pos:]

    include = "#include <afxdlgs.h>"
    if include not in cpp:
        anchor = emule_include
        cpp = cpp.replace(anchor, anchor + "\n\n" + include, 1)

    required_header = (
        "    int SelectedIndex();",
        "    std::vector<size_t> SelectedIndices(size_t limit = 2000);",
    )
    required_cpp = (
        "int CFileLibraryWnd::SelectedIndex()",
        "std::vector<size_t> CFileLibraryWnd::SelectedIndices(size_t limit)",
        include,
        emule_include,
        queue_include,
    )
    for marker in required_header:
        if marker not in header:
            raise SystemExit(f"Library 2 compile hardening: header contract missing {marker}")
    for marker in required_cpp:
        if marker not in cpp:
            raise SystemExit(f"Library 2 compile hardening: cpp contract missing {marker}")
    if cpp.find(emule_include) > cpp.find(queue_include):
        raise SystemExit("Library 2 compile hardening: emule.h must precede DownloadQueue.h")
    if "SelectedIndex() const" in header or "SelectedIndices(size_t limit = 2000) const" in header:
        raise SystemExit("Library 2 compile hardening: stale const selection declaration remains")

    write(HEADER, header, henc)
    write(CPP, cpp, cenc)
    print("Library 2.0 MFC/include compile contracts hardened")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
