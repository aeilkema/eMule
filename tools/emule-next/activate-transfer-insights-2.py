#!/usr/bin/env python3
"""Make file rows in Transfers consume CEmuleNextTransferInsights.

The per-source Live quality column remains source-specific. File-level Health,
Diagnosis, ETA, historical speed, source quality/profile and scheduler state
all come from the same bounded builder/cache used by Dashboard and scheduler.
"""
from __future__ import annotations

import pathlib
import re

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


def main() -> int:
    text, newline = load()
    changed = False

    include_anchor = '#include "DownloadIntelligence.h"\n'
    additions = '#include "EmuleNextTransferInsights.h"\n#include "EmuleNextSmartScheduler.h"\n'
    if '#include "EmuleNextTransferInsights.h"' not in text:
        if include_anchor not in text:
            raise SystemExit("Transfers Intelligence 2: DownloadIntelligence include missing")
        text = text.replace(include_anchor, include_anchor + additions, 1)
        changed = True

    column_anchor = '\tInsertColumn(18,\t_T("Smart ETA"),\tLVCFMT_RIGHT,\t110);\n'
    if 'InsertColumn(22,\t_T("Scheduler")' not in text:
        if column_anchor not in text:
            raise SystemExit("Transfers Intelligence 2: legacy file-intelligence columns missing")
        columns = (
            '\tInsertColumn(19,\t_T("Hist. speed"),\tLVCFMT_RIGHT,\t100);\n'
            '\tInsertColumn(20,\t_T("Source quality"),\tLVCFMT_RIGHT,\t105);\n'
            '\tInsertColumn(21,\t_T("Source profile"),\tLVCFMT_LEFT,\t125);\n'
            '\tInsertColumn(22,\t_T("Scheduler"),\tLVCFMT_LEFT,\t130);\n'
        )
        text = text.replace(column_anchor, column_anchor + columns, 1)
        changed = True

    localize_anchor = '''\tCString nextEta(_T("Smart ETA"));\n\thdi.pszText = const_cast<LPTSTR>((LPCTSTR)nextEta);\n\tpHeaderCtrl->SetItem(18, &hdi);\n'''
    if 'pHeaderCtrl->SetItem(22, &hdi);' not in text:
        if localize_anchor not in text:
            raise SystemExit("Transfers Intelligence 2: Localize ETA anchor missing")
        localize = '''\tCString nextHist(_T("Hist. speed"));\n\thdi.pszText = const_cast<LPTSTR>((LPCTSTR)nextHist);\n\tpHeaderCtrl->SetItem(19, &hdi);\n\tCString nextSourceQuality(_T("Source quality"));\n\thdi.pszText = const_cast<LPTSTR>((LPCTSTR)nextSourceQuality);\n\tpHeaderCtrl->SetItem(20, &hdi);\n\tCString nextSourceProfile(_T("Source profile"));\n\thdi.pszText = const_cast<LPTSTR>((LPCTSTR)nextSourceProfile);\n\tpHeaderCtrl->SetItem(21, &hdi);\n\tCString nextScheduler(_T("Scheduler"));\n\thdi.pszText = const_cast<LPTSTR>((LPCTSTR)nextScheduler);\n\tpHeaderCtrl->SetItem(22, &hdi);\n'''
        text = text.replace(localize_anchor, localize_anchor + localize, 1)
        changed = True

    # Remove the old duplicate file-signal builder. Source-specific intelligence
    # remains untouched.
    start = text.find('\tEmuleNextFileSignals BuildNextFileSignals(')
    if start >= 0:
        end = text.find('\tCString NextStallText(', start)
        if end < 0:
            raise SystemExit("Transfers Intelligence 2: duplicate builder end missing")
        text = text[:start] + text[end:]
        changed = True

    function_pattern = re.compile(
        r'\tCString NextFileIntelligenceText\(const CPartFile\* file, int column\)\n\t\{.*?\n\t\}\n', re.S)
    replacement = r'''\tCString NextFileIntelligenceText(const CPartFile* file, int column)
\t{
\t\tif (file == NULL)
\t\t\treturn CString();
\t\tEmuleNextFileHistory history;
\t\tdouble historical = 0.0;
\t\tif (theEmuleNextScheduler.History().GetHistory(file->GetFileHash(), history))
\t\t\thistorical = history.ewmaBytesPerSecond;
\t\tconst EmuleNextTransferInsight insight = CEmuleNextTransferInsights::Build(file, historical);
\t\tif (column == 16) {
\t\t\tCString value; value.Format(_T("%u%%"), (insight.health + 5) / 10); return value;
\t\t}
\t\tif (column == 17)
\t\t\treturn NextStallText(insight.stall);
\t\tif (column == 18) {
\t\t\tif (!insight.eta.known) return _T("--");
\t\t\tCString value = NextDurationText(insight.eta.seconds);
\t\t\tCString confidence; confidence.Format(_T(" (%u%%)"), insight.eta.confidencePercent);
\t\t\treturn value + confidence;
\t\t}
\t\tif (column == 19) {
\t\t\tif (historical <= 0.0) return _T("--");
\t\t\treturn CastItoXBytes(static_cast<uint64>(historical), false, false, 1) + _T("/s");
\t\t}
\t\tif (column == 20) {
\t\t\tCString value; value.Format(_T("%u/%u%%"),
\t\t\t\t(insight.averageSourceQuality + 5) / 10, (insight.bestSourceQuality + 5) / 10); return value;
\t\t}
\t\tif (column == 21) {
\t\t\tCString value; value.Format(_T("S%u N%u W%u F%u"), insight.strongSources,
\t\t\t\tinsight.normalSources, insight.weakSources, insight.failedSources); return value;
\t\t}
\t\tif (column == 22) {
\t\t\tEmuleNextSchedulerSnapshot snapshot;
\t\t\tif (!theEmuleNextScheduler.GetSnapshot(file->GetFileHash(), snapshot)) return _T("pending");
\t\t\tCString value = CDownloadIntelligence::SchedulingActionText(snapshot.decision.primaryAction);
\t\t\tif (snapshot.applied) value += _T(" *");
\t\t\treturn value;
\t\t}
\t\treturn CString();
\t}
'''
    if function_pattern.search(text):
        updated = function_pattern.sub(replacement, text, count=1)
        if updated != text:
            text = updated
            changed = True
    elif 'const EmuleNextTransferInsight insight = CEmuleNextTransferInsights::Build' not in text:
        raise SystemExit("Transfers Intelligence 2: NextFileIntelligenceText missing")

    old = '''\tCString sItem = (nColumn >= 16 && nColumn <= 18)\n\t\t? NextFileIntelligenceText(pPartFile, nColumn)\n\t\t: GetFileItemDisplayText(pPartFile, nColumn);'''
    new = '''\tCString sItem = (nColumn >= 16 && nColumn <= 22)\n\t\t? NextFileIntelligenceText(pPartFile, nColumn)\n\t\t: GetFileItemDisplayText(pPartFile, nColumn);'''
    if old in text:
        text = text.replace(old, new, 1)
        changed = True
    elif new not in text:
        raise SystemExit("Transfers Intelligence 2: DrawFileItem range missing")

    if changed:
        save(text, newline)
        print("Transfers now use shared file intelligence 2.0")
    else:
        print("Transfers shared intelligence 2.0 already materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
