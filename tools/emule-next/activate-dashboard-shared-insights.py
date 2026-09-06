#!/usr/bin/env python3
"""Make Dashboard consume the same transfer-insight builder as Smart Scheduler."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "EmuleNextDashboardWnd.cpp"


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

    for include, anchor in (
        ('#include "EmuleNextTransferInsights.h"', '#include "DownloadIntelligence.h"'),
        ('#include "EmuleNextSmartScheduler.h"', '#include "DownloadIntelligence.h"'),
    ):
        if include not in text:
            if anchor not in text:
                raise SystemExit("Dashboard shared insights: include anchor missing")
            text = text.replace(anchor, anchor + "\n" + include, 1)
            changed = True

    refresh_old = '''            row.signals = BuildSignals(file);
            row.stall = CDownloadIntelligence::DiagnoseStall(row.signals);
            row.health = CDownloadIntelligence::FileAvailabilityHealth(row.signals);
            const uint64 completed = file->GetCompletedSize();
            const uint64 fileSize = file->GetFileSize();
            const uint64 remaining = fileSize > completed ? fileSize - completed : 0;
            row.eta = CDownloadIntelligence::EstimateEta(row.signals, remaining);
            row.discoveryBudget = CDownloadIntelligence::SourceDiscoveryBudget(row.signals, NORMAL_DISCOVERY_BUDGET);
            row.a4afScore = CDownloadIntelligence::A4AFPriority(row.signals, row.health);
            row.attention = AttentionScore(file, row.signals, row.stall, row.health);'''
    refresh_new = '''            double historicalBytesPerSecond = 0.0;
            EmuleNextFileHistory sharedHistory;
            if (theEmuleNextScheduler.History().GetHistory(file->GetFileHash(), sharedHistory))
                historicalBytesPerSecond = sharedHistory.ewmaBytesPerSecond;
            const EmuleNextTransferInsight sharedInsight = CEmuleNextTransferInsights::Build(file, historicalBytesPerSecond);
            row.signals = sharedInsight.file;
            row.stall = sharedInsight.stall;
            row.health = sharedInsight.health;
            row.eta = sharedInsight.eta;
            row.discoveryBudget = CDownloadIntelligence::SourceDiscoveryBudget(row.signals, NORMAL_DISCOVERY_BUDGET);
            row.a4afScore = CDownloadIntelligence::A4AFPriority(row.signals, row.health);
            row.attention = sharedInsight.attention;'''
    if refresh_old in text:
        text = text.replace(refresh_old, refresh_new, 1)
        changed = True
    elif "const EmuleNextTransferInsight sharedInsight" not in text:
        raise SystemExit("Dashboard shared insights: Refresh intelligence block changed unexpectedly")

    details_old = '''    row.signals = BuildSignals(file);
    row.stall = CDownloadIntelligence::DiagnoseStall(row.signals);
    row.health = CDownloadIntelligence::FileAvailabilityHealth(row.signals);
    row.discoveryBudget = CDownloadIntelligence::SourceDiscoveryBudget(row.signals, NORMAL_DISCOVERY_BUDGET);
    row.a4afScore = CDownloadIntelligence::A4AFPriority(row.signals, row.health);
    row.attention = AttentionScore(file, row.signals, row.stall, row.health);
    const uint64 completed = file->GetCompletedSize();
    const uint64 fileSize = file->GetFileSize();
    row.eta = CDownloadIntelligence::EstimateEta(row.signals, fileSize > completed ? fileSize - completed : 0);'''
    details_new = '''    double historicalBytesPerSecond = 0.0;
    EmuleNextFileHistory sharedHistory;
    if (theEmuleNextScheduler.History().GetHistory(file->GetFileHash(), sharedHistory))
        historicalBytesPerSecond = sharedHistory.ewmaBytesPerSecond;
    const EmuleNextTransferInsight sharedInsight = CEmuleNextTransferInsights::Build(file, historicalBytesPerSecond);
    row.signals = sharedInsight.file;
    row.stall = sharedInsight.stall;
    row.health = sharedInsight.health;
    row.eta = sharedInsight.eta;
    row.discoveryBudget = CDownloadIntelligence::SourceDiscoveryBudget(row.signals, NORMAL_DISCOVERY_BUDGET);
    row.a4afScore = CDownloadIntelligence::A4AFPriority(row.signals, row.health);
    row.attention = sharedInsight.attention;'''
    if details_old in text:
        text = text.replace(details_old, details_new, 1)
        changed = True
    elif text.count("const EmuleNextTransferInsight sharedInsight") < 2:
        raise SystemExit("Dashboard shared insights: UpdateDetails intelligence block changed unexpectedly")

    # Remove Dashboard-only builders only after every call site was migrated.
    if "BuildSignals(file)" in text or "AttentionScore(file," in text:
        raise SystemExit("Dashboard shared insights: legacy helper call remains after migration")

    start = text.find("    EmuleNextFileSignals BuildSignals(")
    if start >= 0:
        end = text.find("    CString StallText(", start)
        if end < 0:
            raise SystemExit("Dashboard shared insights: BuildSignals end anchor missing")
        text = text[:start] + text[end:]
        changed = True

    start = text.find("    uint32 AttentionScore(")
    if start >= 0:
        end = text.find("    CString RecommendationText(", start)
        if end < 0:
            raise SystemExit("Dashboard shared insights: AttentionScore end anchor missing")
        text = text[:start] + text[end:]
        changed = True

    if changed:
        PATH.write_bytes(text.encode(encoding))
        print("Dashboard now uses shared transfer intelligence in list and detail paths")
    else:
        print("Dashboard shared transfer intelligence already materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())