#!/usr/bin/env python3
"""Materialize a narrow WinSQLite declaration compatibility shim.

Some serviced Windows SDK 26100 installations expose only part of the
winsqlite3.h declaration surface to this legacy MFC project even though the
corresponding exports have been present in winsqlite3.dll since Windows 10
1511.  Keep using the system DLL/import library and supply only the stable
SQLite declarations that eMule Next needs but that those headers may omit.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
HEADER = SRC / "EmuleNextWinSqliteCompat.h"

USERS = (
    "EmuleNextDatabase.cpp",
    "EmuleNextHistoryCache.cpp",
    "EmuleNextSchedulerTelemetry.cpp",
    "EmuleNextSchedulerTelemetryReader.cpp",
)

HEADER_TEXT = r'''//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

// Windows provides WinSQLite in winsqlite3.dll.  Include the SDK header first
// and then redeclare a small set of long-stable APIs which are absent from
// some Windows SDK 26100 header/toolchain combinations used by this project.
#include <winsqlite3.h>

#ifndef SQLITE_API
#define SQLITE_API
#endif
#ifndef SQLITE_APICALL
#define SQLITE_APICALL
#endif

// sqlite3_column_type() returns one of the five canonical SQLite storage class
// values. SQLITE_NULL has been 5 for the complete SQLite 3 API lifetime.
#ifndef SQLITE_NULL
#define SQLITE_NULL 5
#endif

#ifdef __cplusplus
extern "C" {
#endif

SQLITE_API int SQLITE_APICALL sqlite3_reset(sqlite3_stmt* statement);
SQLITE_API int SQLITE_APICALL sqlite3_clear_bindings(sqlite3_stmt* statement);
SQLITE_API int SQLITE_APICALL sqlite3_bind_double(sqlite3_stmt* statement, int index, double value);
SQLITE_API double SQLITE_APICALL sqlite3_column_double(sqlite3_stmt* statement, int column);
SQLITE_API int SQLITE_APICALL sqlite3_column_type(sqlite3_stmt* statement, int column);

#ifdef __cplusplus
}
#endif
'''


def load(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    newline = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n"), newline


def save(path: pathlib.Path, text: str, newline: str) -> None:
    if newline != "\n":
        text = text.replace("\n", newline)
    path.write_bytes(text.encode("latin-1"))


def main() -> int:
    HEADER.write_bytes(HEADER_TEXT.encode("ascii"))

    changed = 0
    for name in USERS:
        path = SRC / name
        if not path.exists():
            raise SystemExit(f"WinSQLite compatibility: missing source {name}")
        text, newline = load(path)
        if '#include "EmuleNextWinSqliteCompat.h"' in text:
            if "#include <winsqlite3.h>" in text:
                raise SystemExit(f"WinSQLite compatibility: both headers included in {name}")
            continue
        if "#include <winsqlite3.h>" not in text:
            raise SystemExit(f"WinSQLite compatibility: winsqlite include anchor missing in {name}")
        text = text.replace(
            "#include <winsqlite3.h>",
            '#include "EmuleNextWinSqliteCompat.h"',
            1,
        )
        save(path, text, newline)
        changed += 1

    # Fail here, before MSVC, if the generated shim ever loses the exact API
    # contract that fixed the SDK-specific compile failure.
    generated = HEADER.read_text(encoding="ascii")
    required = (
        "sqlite3_reset(sqlite3_stmt* statement)",
        "sqlite3_clear_bindings(sqlite3_stmt* statement)",
        "sqlite3_bind_double(sqlite3_stmt* statement, int index, double value)",
        "sqlite3_column_double(sqlite3_stmt* statement, int column)",
        "sqlite3_column_type(sqlite3_stmt* statement, int column)",
        "#define SQLITE_NULL 5",
    )
    missing = [marker for marker in required if marker not in generated]
    if missing:
        raise SystemExit("WinSQLite compatibility header incomplete: " + ", ".join(missing))

    print(f"eMule Next WinSQLite compatibility active ({changed} source includes updated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
