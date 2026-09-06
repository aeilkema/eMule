#!/usr/bin/env python3
"""Compile-contract gate for WinSQLite APIs used by DB maintenance."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def read(path: pathlib.Path) -> str:
    if not path.exists():
        raise SystemExit(f"WinSQLite maintenance verification: missing {path.name}")
    return path.read_bytes().decode("latin-1", errors="ignore")


def main() -> int:
    compat = read(SRC / "EmuleNextWinSqliteCompat.h")
    maintenance = read(SRC / "EmuleNextDatabaseMaintenance.cpp")

    for marker in (
        "sqlite3_bind_text(sqlite3_stmt* statement, int index, const char* value, int bytes, void(*destructor)(void*))",
        "#define SQLITE_CHECKPOINT_TRUNCATE 3",
    ):
        if marker not in compat:
            raise SystemExit(f"WinSQLite maintenance verification: compat shim missing {marker}")

    if '#include "EmuleNextWinSqliteCompat.h"' not in maintenance:
        raise SystemExit("WinSQLite maintenance verification: maintenance source bypasses compat shim")
    if "#include <winsqlite3.h>" in maintenance:
        raise SystemExit("WinSQLite maintenance verification: maintenance source includes raw WinSQLite header")

    for marker in ("sqlite3_bind_text(", "SQLITE_CHECKPOINT_TRUNCATE"):
        if marker not in maintenance:
            raise SystemExit(f"WinSQLite maintenance verification: maintenance contract missing {marker}")

    print("eMule Next WinSQLite database-maintenance compatibility verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
