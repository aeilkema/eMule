#!/usr/bin/env python3
"""Extend Library 2 'Available again' to Search/history rediscovery.

A completed-but-missing file becomes available again when either a peer offered
the same ED2K hash + size in the recent peer window, or the canonical file row
was observed again after completion (for example by Search 2). The completion
observation itself is excluded with a small timestamp guard.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
H = SRC / "LibraryBrowserService.h"
CPP = SRC / "LibraryBrowserService.cpp"


def read(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    return raw.decode("utf-8"), "utf-8"


def write(path: pathlib.Path, text: str, enc: str) -> None:
    path.write_bytes(text.encode(enc))


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Library 2 availability: expected one {label} anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    header, henc = read(H)
    if "uint64 completedAt;" not in header:
        header = replace_once(
            header,
            "    uint64 missingSince;\n    uint32 recentPeerCount;",
            "    uint64 missingSince;\n    uint64 completedAt;\n    uint32 recentPeerCount;",
            "completedAt field",
        )
        write(H, header, henc)

    cpp, cenc = read(CPP)
    cpp = replace_once(
        cpp,
        "    , missingSince(0)\n    , recentPeerCount(0)",
        "    , missingSince(0)\n    , completedAt(0)\n    , recentPeerCount(0)",
        "completedAt constructor",
    )
    cpp = replace_once(
        cpp,
        '        "CASE WHEN le.completed_at IS NULL THEN 0 ELSE 1 END,"',
        '        "COALESCE(le.completed_at,0),"',
        "completed timestamp query",
    )
    cpp = replace_once(
        cpp,
        "            row.completed = sqlite3_column_int(statement, 6) != 0;",
        "            row.completedAt = static_cast<uint64>(sqlite3_column_int64(statement, 6));\n            row.completed = row.completedAt != 0;",
        "completed timestamp decode",
    )
    cpp = replace_once(
        cpp,
        "            row.availableAgain = row.completed && row.missing && row.recentPeerCount != 0;",
        "            row.availableAgain = row.completed && row.missing\n                && (row.recentPeerCount != 0 || (row.completedAt != 0 && row.lastSeen > row.completedAt + 60));",
        "rediscovery availability rule",
    )
    write(CPP, cpp, cenc)
    print("Library 2.0 Search/history rediscovery availability hardening materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
