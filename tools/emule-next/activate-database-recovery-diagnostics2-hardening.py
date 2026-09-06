#!/usr/bin/env python3
'''Final compile-contract hardening for Database / Recovery / Diagnostics 2.0.'''
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
DB_CPP = SRC / "EmuleNextDatabase.cpp"
RT_H = SRC / "EmuleNextRuntime.h"
DIAG_CPP = SRC / "EmuleNextDiagnosticsWnd.cpp"


def read(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def write(path: pathlib.Path, text: str, enc: str) -> None:
    path.write_bytes(text.encode(enc))


def main() -> int:
    db, enc = read(DB_CPP)
    declarations = (
        "    std::atomic<uint64> m_peakQueue;\n"
        "    std::atomic<uint64> m_processedEvents;\n"
        "    std::atomic<uint64> m_droppedEvents;\n"
        "    std::atomic<uint64> m_writeErrors;\n"
    )
    if "std::atomic<uint64> m_peakQueue;" not in db:
        anchor = "    CStringW m_lastError;\n"
        if anchor not in db:
            raise SystemExit("DB2 hardening: writer diagnostics member anchor missing")
        db = db.replace(anchor, anchor + declarations, 1)
    for marker in (
        "std::atomic<uint64> m_peakQueue;",
        "std::atomic<uint64> m_processedEvents;",
        "std::atomic<uint64> m_droppedEvents;",
        "std::atomic<uint64> m_writeErrors;",
        "m_peakQueue.compare_exchange_weak",
        "m_processedEvents.fetch_add",
    ):
        if marker not in db:
            raise SystemExit(f"DB2 hardening: missing writer diagnostic compile contract {marker}")
    write(DB_CPP, db, enc)

    runtime, renc = read(RT_H)
    for marker in (
        "#include <thread>",
        "#include <condition_variable>",
        "#include <atomic>",
        "std::thread m_maintenanceThread;",
        "std::condition_variable m_maintenanceCondition;",
        "std::atomic<bool> m_recoveryRequired;",
    ):
        if marker not in runtime:
            raise SystemExit(f"DB2 hardening: missing runtime compile contract {marker}")
    write(RT_H, runtime, renc)

    diag, denc = read(DIAG_CPP)
    # Keep MFC map entries as separate lines; this is both easier to audit and
    # avoids depending on whitespace between macro expansions.
    diag = diag.replace(
        "    ON_WM_CREATE() ON_WM_SIZE() ON_WM_ERASEBKGND() ON_WM_CTLCOLOR()\n",
        "    ON_WM_CREATE()\n    ON_WM_SIZE()\n    ON_WM_ERASEBKGND()\n    ON_WM_CTLCOLOR()\n",
    )
    diag = diag.replace(
        "    ON_BN_CLICKED(IDC_EN_DIAG_REFRESH, OnRefreshClicked) ON_BN_CLICKED(IDC_EN_DIAG_CHECK, OnCheckClicked)\n",
        "    ON_BN_CLICKED(IDC_EN_DIAG_REFRESH, OnRefreshClicked)\n    ON_BN_CLICKED(IDC_EN_DIAG_CHECK, OnCheckClicked)\n",
    )
    diag = diag.replace(
        "    ON_BN_CLICKED(IDC_EN_DIAG_BACKUP, OnBackupClicked) ON_BN_CLICKED(IDC_EN_DIAG_RESTORE, OnRestoreClicked)\n",
        "    ON_BN_CLICKED(IDC_EN_DIAG_BACKUP, OnBackupClicked)\n    ON_BN_CLICKED(IDC_EN_DIAG_RESTORE, OnRestoreClicked)\n",
    )
    diag = diag.replace(
        "    ON_BN_CLICKED(IDC_EN_DIAG_PRUNE, OnPruneClicked) ON_BN_CLICKED(IDC_EN_DIAG_CHECKPOINT, OnCheckpointClicked)\n",
        "    ON_BN_CLICKED(IDC_EN_DIAG_PRUNE, OnPruneClicked)\n    ON_BN_CLICKED(IDC_EN_DIAG_CHECKPOINT, OnCheckpointClicked)\n",
    )
    diag = diag.replace(
        "    ON_BN_CLICKED(IDC_EN_DIAG_OPEN, OnOpenBackupsClicked) ON_MESSAGE(WM_EN_DIAG_RESULT, OnMaintenanceResult)\n",
        "    ON_BN_CLICKED(IDC_EN_DIAG_OPEN, OnOpenBackupsClicked)\n    ON_MESSAGE(WM_EN_DIAG_RESULT, OnMaintenanceResult)\n",
    )
    for marker in ("ON_WM_CREATE()", "ON_WM_SIZE()", "ON_MESSAGE(WM_EN_DIAG_RESULT, OnMaintenanceResult)"):
        if marker not in diag:
            raise SystemExit(f"DB2 hardening: missing Diagnostics message-map contract {marker}")
    write(DIAG_CPP, diag, denc)

    print("eMule Next Database / Recovery / Diagnostics 2.0 compile contracts hardened")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
