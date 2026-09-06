#!/usr/bin/env python3
"""Verify the legacy file-intelligence precursor can feed Transfers Intelligence 2.0.

On the first activation pass this runs immediately after
activate-file-intelligence-columns.py and requires its intermediate C++ form.
On the idempotence pass the final shared Intelligence 2.0 form is already
present, which is also accepted. Escaped Python source is never accepted.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "DownloadListCtrl.cpp"


def main() -> int:
    if not PATH.exists():
        raise SystemExit("Transfers intelligence transition verification: DownloadListCtrl.cpp missing")
    text = PATH.read_bytes().decode("latin-1", errors="ignore").replace("\r\n", "\n").replace("\r", "\n")

    forbidden = (
        "\\tEmuleNextFileSignals",
        "\\tCString NextFileIntelligenceText",
        '_T(\\"',
    )
    for marker in forbidden:
        if marker in text:
            raise SystemExit(f"Transfers intelligence transition verification: escaped Python text leaked into C++: {marker}")

    precursor = (
        "EmuleNextFileSignals BuildNextFileSignals(" in text
        and "CString NextFileIntelligenceText(const CPartFile* file, int column)" in text
        and "nColumn >= 16 && nColumn <= 18" in text
        and 'InsertColumn(18,\t_T("Smart ETA")' in text
    )
    final = (
        '#include "EmuleNextTransferInsights.h"' in text
        and "const EmuleNextTransferInsight insight = CEmuleNextTransferInsights::Build(file, historical);" in text
        and "nColumn >= 16 && nColumn <= 22" in text
        and 'InsertColumn(22,\t_T("Scheduler")' in text
    )

    if precursor:
        print("Transfers file-intelligence precursor contract passed")
        return 0
    if final:
        print("Transfers shared Intelligence 2.0 already satisfies transition contract")
        return 0

    raise SystemExit(
        "Transfers intelligence transition verification FAILED: neither valid precursor nor final Intelligence 2.0 form found"
    )


if __name__ == "__main__":
    raise SystemExit(main())
