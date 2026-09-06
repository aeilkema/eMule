#!/usr/bin/env python3
"""Expose live file health, stall diagnosis and Smart ETA in Transfers.

This is a precursor for activate-transfer-insights-2.py. On a second activation
pass the final shared Intelligence 2.0 implementation is already present and
has deliberately removed/replaced parts of this legacy intermediate form. In
that case this activator must be a strict no-op instead of trying to recreate
its obsolete intermediate DrawFileItem implementation.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "DownloadListCtrl.cpp"


def load() -> tuple[str, str]:
    raw = PATH.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    newline = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n"), newline


def save(text: str, newline: str) -> None:
    if newline != "\n":
        text = text.replace("\n", newline)
    PATH.write_bytes(text.encode("latin-1"))


def final_shared_intelligence2(text: str) -> bool:
    """Return True only for the final state materialized by Transfers 2.0.

    All markers are required so a partially activated tree is never silently
    accepted. The old BuildNextFileSignals helper is intentionally absent in
    this final form.
    """
    return (
        '#include "EmuleNextTransferInsights.h"' in text
        and '#include "EmuleNextSmartScheduler.h"' in text
        and 'InsertColumn(22,\t_T("Scheduler")' in text
        and 'pHeaderCtrl->SetItem(22, &hdi);' in text
        and 'const EmuleNextTransferInsight insight = CEmuleNextTransferInsights::Build(file, historical);' in text
        and 'nColumn >= 16 && nColumn <= 22' in text
        and 'EmuleNextFileSignals BuildNextFileSignals(' not in text
    )


def main() -> int:
    text, newline = load()

    # activate-transfer-insights-2.py supersedes this intermediate form. This
    # guard is essential for second-pass idempotence: that later activator
    # intentionally removes BuildNextFileSignals and expands DrawFileItem from
    # columns 16..18 to 16..22.
    if final_shared_intelligence2(text):
        print("eMule Next legacy file intelligence superseded by shared Transfers Intelligence 2.0; skipping")
        return 0

    include_anchor = '#include "ImportParts.h"\n'
    if '#include "DownloadIntelligence.h"' not in text:
        if include_anchor not in text:
            raise RuntimeError("DownloadListCtrl include anchor not found")
        text = text.replace(include_anchor, include_anchor + '#include "DownloadIntelligence.h"\n', 1)

    # Existing source-intelligence activation creates columns 14/15 first.
    column_anchor = '\tInsertColumn(15,\t_T("Live quality"),\tLVCFMT_RIGHT,\t90);\n'
    columns = ('\tInsertColumn(16,\t_T("Health"),\tLVCFMT_RIGHT,\t80);\n'
               '\tInsertColumn(17,\t_T("Diagnosis"),\tLVCFMT_LEFT,\t135);\n'
               '\tInsertColumn(18,\t_T("Smart ETA"),\tLVCFMT_RIGHT,\t110);\n')
    if 'InsertColumn(18,\t_T("Smart ETA")' not in text:
        if column_anchor not in text:
            raise RuntimeError("Live quality column must be activated before file intelligence")
        text = text.replace(column_anchor, column_anchor + columns, 1)

    localize_anchor = '''\tCString nextQuality(_T("Live quality"));
\thdi.pszText = const_cast<LPTSTR>((LPCTSTR)nextQuality);
\tpHeaderCtrl->SetItem(15, &hdi);
'''
    localize = '''\tCString nextHealth(_T("Health"));
\thdi.pszText = const_cast<LPTSTR>((LPCTSTR)nextHealth);
\tpHeaderCtrl->SetItem(16, &hdi);
\tCString nextDiagnosis(_T("Diagnosis"));
\thdi.pszText = const_cast<LPTSTR>((LPCTSTR)nextDiagnosis);
\tpHeaderCtrl->SetItem(17, &hdi);
\tCString nextEta(_T("Smart ETA"));
\thdi.pszText = const_cast<LPTSTR>((LPCTSTR)nextEta);
\tpHeaderCtrl->SetItem(18, &hdi);
'''
    if 'pHeaderCtrl->SetItem(18, &hdi);' not in text:
        if localize_anchor not in text:
            raise RuntimeError("Live quality Localize anchor not found")
        text = text.replace(localize_anchor, localize_anchor + localize, 1)

    helper_anchor = '#define RATING_ICON_WIDTH\t16\n'
    helpers = r'''

namespace
{
\tEmuleNextFileSignals BuildNextFileSignals(const CPartFile* file)
\t{
\t\tEmuleNextFileSignals signals;
\t\tif (file == NULL)
\t\t\treturn signals;
\t\tsignals.totalSources = file->GetSourceCount();
\t\tconst int validSources = file->GetValidSourcesCount();
\t\tsignals.usableSources = validSources > 0 ? static_cast<uint32>(validSources) : 0;
\t\tsignals.queuedSources = file->GetSrcStatisticsValue(DS_ONQUEUE);
\t\tsignals.connectionFailures = file->GetSrcStatisticsValue(DS_ERROR)
\t\t\t+ file->GetSrcStatisticsValue(DS_TOOMANYCONNS)
\t\t\t+ file->GetSrcStatisticsValue(DS_TOOMANYCONNSKAD);
\t\tsignals.a4afCandidates = file->GetSrcA4AFCount();
\t\tsignals.currentBytesPerSecond = static_cast<double>(file->GetDatarate());
\t\tsignals.completionRatio = static_cast<double>(file->GetPercentCompleted()) / 100.0;
\t\tsignals.hashing = file->GetStatus() == PS_HASHING || file->GetStatus() == PS_WAITINGFORHASH
\t\t\t|| file->GetFileOp() == PFOP_HASHING;
\t\tsignals.highPriority = file->GetDownPriority() == PR_HIGH || file->GetDownPriority() == PR_VERYHIGH;
\t\t// Until Kad cycle telemetry is wired per file, avoid falsely diagnosing Kad itself.
\t\tsignals.kadResultsLastCycle = 1;
\t\tfor (UINT part = 0; part < file->GetPartCount(); ++part) {
\t\t\tif (file->IsComplete(part))
\t\t\t\tcontinue;
\t\t\t++signals.neededParts;
\t\t\tif (file->GetPartSourceFrequency(part) <= 2)
\t\t\t\t++signals.rareNeededParts;
\t\t}
\t\treturn signals;
\t}

\tCString NextStallText(EmuleNextStallReason reason)
\t{
\t\tswitch (reason) {
\t\tcase ENSR_NONE: return _T("Healthy");
\t\tcase ENSR_NO_SOURCES: return _T("No sources");
\t\tcase ENSR_NO_NEEDED_PARTS: return _T("No needed parts");
\t\tcase ENSR_ALL_REMOTE_QUEUED: return _T("All remote queued");
\t\tcase ENSR_RARE_PARTS: return _T("Rare parts");
\t\tcase ENSR_CONNECTION_FAILURE: return _T("Connection failures");
\t\tcase ENSR_KAD_DISCOVERY_FAILURE: return _T("Kad discovery");
\t\tcase ENSR_DISK_LIMITED: return _T("Disk limited");
\t\tcase ENSR_HASHING: return _T("Hashing");
\t\tcase ENSR_A4AF_CONFLICT: return _T("A4AF conflict");
\t\tdefault: return _T("Unknown");
\t\t}
\t}

\tCString NextDurationText(uint64 seconds)
\t{
\t\tCString text;
\t\tif (seconds < 60)
\t\t\ttext.Format(_T("%llus"), seconds);
\t\telse if (seconds < 3600)
\t\t\ttext.Format(_T("%llum"), seconds / 60);
\t\telse if (seconds < 86400)
\t\t\ttext.Format(_T("%lluh %02llum"), seconds / 3600, (seconds % 3600) / 60);
\t\telse
\t\t\ttext.Format(_T("%llud %lluh"), seconds / 86400, (seconds % 86400) / 3600);
\t\treturn text;
\t}

\tCString NextFileIntelligenceText(const CPartFile* file, int column)
\t{
\t\tconst EmuleNextFileSignals signals = BuildNextFileSignals(file);
\t\tif (column == 16) {
\t\t\tCString text;
\t\t\tconst uint32 health = CDownloadIntelligence::FileAvailabilityHealth(signals);
\t\t\ttext.Format(_T("%u%%"), (health + 5) / 10);
\t\t\treturn text;
\t\t}
\t\tif (column == 17)
\t\t\treturn NextStallText(CDownloadIntelligence::DiagnoseStall(signals));
\t\tif (column == 18) {
\t\t\tconst uint64 remaining = file->GetFileSize() > file->GetCompletedSize()
\t\t\t\t? file->GetFileSize() - file->GetCompletedSize() : 0;
\t\t\tconst EmuleNextEta eta = CDownloadIntelligence::EstimateEta(signals, remaining);
\t\t\tif (!eta.known)
\t\t\t\treturn _T("--");
\t\t\tCString text = NextDurationText(eta.seconds);
\t\t\tCString confidence;
\t\t\tconfidence.Format(_T(" (%u%%)"), eta.confidencePercent);
\t\t\ttext += confidence;
\t\t\treturn text;
\t\t}
\t\treturn CString();
\t}
}
'''
    if 'BuildNextFileSignals(const CPartFile* file)' not in text:
        if helper_anchor not in text:
            raise RuntimeError("DownloadListCtrl helper anchor not found")
        text = text.replace(helper_anchor, helper_anchor + helpers, 1)

    old_draw = '''\t/*const*/ CPartFile *pPartFile = static_cast<CPartFile*>(pCtrlItem->value);
\tconst CString &sItem(GetFileItemDisplayText(pPartFile, nColumn));
\tCRect rcDraw(lpRect);
'''
    new_draw = '''\t/*const*/ CPartFile *pPartFile = static_cast<CPartFile*>(pCtrlItem->value);
\tCString sItem = (nColumn >= 16 && nColumn <= 18)
\t\t? NextFileIntelligenceText(pPartFile, nColumn)
\t\t: GetFileItemDisplayText(pPartFile, nColumn);
\tCRect rcDraw(lpRect);
'''
    if new_draw not in text:
        if old_draw not in text:
            raise RuntimeError("DrawFileItem anchor not found")
        text = text.replace(old_draw, new_draw, 1)

    save(text, newline)
    print("eMule Next file health, stall diagnosis and Smart ETA active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
