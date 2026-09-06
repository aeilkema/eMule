#!/usr/bin/env python3
"""Idempotently wire Smart Scheduler history and telemetry persistence.

SQLite work remains inside the dedicated worker classes. This activator only
passes the runtime database path from the bounded scheduler tick.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "EmuleNextSmartScheduler.cpp"


def read_text(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def main() -> int:
    text, encoding = read_text(PATH)
    marker = "m_telemetry.SetDatabasePath(database.GetDatabasePath());"
    if marker in text:
        print("Smart Scheduler telemetry persistence already wired")
        return 0

    anchor = "    if (historyEnabled) {\n        const UINT historyCapacity"
    if anchor not in text:
        raise SystemExit("Scheduler persistence: history setup anchor missing")

    telemetry_block = (
        "    if (telemetryEnabled) {\n"
        "        CEmuleNextDatabase& database = theEmuleNextRuntime.Database();\n"
        "        if (database.IsRunning())\n"
        "            m_telemetry.SetDatabasePath(database.GetDatabasePath());\n"
        "    }\n\n"
    )
    text = text.replace(anchor, telemetry_block + anchor, 1)
    PATH.write_bytes(text.encode(encoding))
    print("Smart Scheduler telemetry persistence wired")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
