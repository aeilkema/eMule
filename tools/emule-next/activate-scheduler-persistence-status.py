#!/usr/bin/env python3
"""Expose history/telemetry persistence health in scheduler runtime text."""
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
    changed = False

    init_anchor = "    , historyGeneration(0)\n    , decisions(0)"
    init_replacement = "    , historyGeneration(0)\n    , historyPendingWrites(0)\n    , historyDroppedWrites(0)\n    , decisions(0)"
    if init_anchor in text:
        text = text.replace(init_anchor, init_replacement, 1)
        changed = True

    status_anchor = "    status.historyGeneration = m_history.Generation();\n    status.telemetryEnabled"
    status_replacement = (
        "    status.historyGeneration = m_history.Generation();\n"
        "    status.historyPendingWrites = m_history.PendingPersistenceWrites();\n"
        "    status.historyDroppedWrites = m_history.DroppedPersistenceWrites();\n"
        "    status.telemetryEnabled"
    )
    if status_anchor in text:
        text = text.replace(status_anchor, status_replacement, 1)
        changed = True

    old_format = '''    text.Format(_T("%s / %s | scan %u | cooldown %us | tracked %u | history %u%s | telemetry %s q:%u drop:%llu | decisions %llu | applied %llu"),
        (LPCTSTR)CDownloadIntelligence::SchedulingModeText(status.mode),
        (LPCTSTR)ProfileText(status.profile), status.maxFilesPerRound, status.cooldownSeconds,
        status.trackedFiles, status.historyFiles, status.historyPersistenceReady ? _T(" persistent") : _T(" memory"),
        status.telemetryPersistenceReady ? _T("persistent") : _T("memory"),
        static_cast<unsigned int>(status.telemetryPendingWrites), status.telemetryDroppedWrites,
        status.decisions, status.appliedInterventions);'''
    new_format = '''    text.Format(_T("%s / %s | scan %u | cooldown %us | tracked %u | history %u%s q:%u drop:%llu | telemetry %s q:%u drop:%llu | decisions %llu | applied %llu"),
        (LPCTSTR)CDownloadIntelligence::SchedulingModeText(status.mode),
        (LPCTSTR)ProfileText(status.profile), status.maxFilesPerRound, status.cooldownSeconds,
        status.trackedFiles, status.historyFiles, status.historyPersistenceReady ? _T(" persistent") : _T(" memory"),
        static_cast<unsigned int>(status.historyPendingWrites), status.historyDroppedWrites,
        status.telemetryPersistenceReady ? _T("persistent") : _T("memory"),
        static_cast<unsigned int>(status.telemetryPendingWrites), status.telemetryDroppedWrites,
        status.decisions, status.appliedInterventions);'''
    if old_format in text:
        text = text.replace(old_format, new_format, 1)
        changed = True

    required = (
        "status.historyPendingWrites = m_history.PendingPersistenceWrites();",
        "status.historyDroppedWrites = m_history.DroppedPersistenceWrites();",
        "status.telemetryPendingWrites = telemetry.pendingPersistenceEvents;",
        "status.telemetryDroppedWrites = telemetry.droppedPersistenceEvents;",
    )
    for marker in required:
        if marker not in text:
            raise SystemExit(f"Scheduler persistence status: missing {marker}")

    if changed:
        PATH.write_bytes(text.encode(encoding))
        print("Scheduler persistence diagnostics materialized")
    else:
        print("Scheduler persistence diagnostics already materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
