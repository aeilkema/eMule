#!/usr/bin/env python3
"""Expose live file health, stall diagnosis and Smart ETA in Transfers."""
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


def main() -> int:
    text, newline = load()

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

    localize_anchor = '''\tCString nextQuality(_T("Live quality"));\n\thdi.pszText = const_cast<LPTSTR>((LPCTSTR)nextQuality);\n\tpHeaderCtrl->SetItem(15, &hdi);\n'''
    localize = '''\tCString nextHealth(_T("Health"));\n\thdi.pszText = const_cast<LPTSTR>((LPCTSTR)nextHealth);\n\tpHeaderCtrl->SetItem(16, &hdi);\n\tCString nextDiagnosis(_T("Diagnosis"));\n\thdi.pszText = const_cast<LPTSTR>((LPCTSTR)nextDiagnosis);\n\tpHeaderCtrl->SetItem(17, &hdi);\n\tCString nextEta(_T("Smart ETA"));\n\thdi.pszText = const_cast<LPTSTR>((LPCTSTR)nextEta);\n\tpHeaderCtrl->SetItem(18, &hdi);\n'''
    if 'pHeaderCtrl->SetItem(18, &hdi);' not in text:
        if localize_anchor not in text:
            raise RuntimeError("Live quality Localize anchor not found")
        text = text.replace(localize_anchor, localize_anchor + localize, 1)

    helper_anchor = '#define RATING_ICON_WIDTH\t16\n'
    helpers = r'''

namespace
{
	EmuleNextFileSignals BuildNextFileSignals(const CPartFile* file)
	{
		EmuleNextFileSignals signals;
		if (file == NULL)
			return signals;
		signals.totalSources = file->GetSourceCount();
		const int validSources = file->GetValidSourcesCount();
		signals.usableSources = validSources > 0 ? static_cast<uint32>(validSources) : 0;
		signals.queuedSources = file->GetSrcStatisticsValue(DS_ONQUEUE);
		signals.connectionFailures = file->GetSrcStatisticsValue(DS_ERROR)
			+ file->GetSrcStatisticsValue(DS_TOOMANYCONNS)
			+ file->GetSrcStatisticsValue(DS_TOOMANYCONNSKAD);
		signals.a4afCandidates = file->GetSrcA4AFCount();
		signals.currentBytesPerSecond = static_cast<double>(file->GetDatarate());
		signals.completionRatio = static_cast<double>(file->GetPercentCompleted()) / 100.0;
		signals.hashing = file->GetStatus() == PS_HASHING || file->GetStatus() == PS_WAITINGFORHASH
			|| file->GetFileOp() == PFOP_HASHING;
		signals.highPriority = file->GetDownPriority() == PR_HIGH || file->GetDownPriority() == PR_VERYHIGH;
		// Until Kad cycle telemetry is wired per file, avoid falsely diagnosing Kad itself.
		signals.kadResultsLastCycle = 1;
		for (UINT part = 0; part < file->GetPartCount(); ++part) {
			if (file->IsComplete(part))
				continue;
			++signals.neededParts;
			if (file->GetPartSourceFrequency(part) <= 2)
				++signals.rareNeededParts;
		}
		return signals;
	}

	CString NextStallText(EmuleNextStallReason reason)
	{
		switch (reason) {
		case ENSR_NONE: return _T("Healthy");
		case ENSR_NO_SOURCES: return _T("No sources");
		case ENSR_NO_NEEDED_PARTS: return _T("No needed parts");
		case ENSR_ALL_REMOTE_QUEUED: return _T("All remote queued");
		case ENSR_RARE_PARTS: return _T("Rare parts");
		case ENSR_CONNECTION_FAILURE: return _T("Connection failures");
		case ENSR_KAD_DISCOVERY_FAILURE: return _T("Kad discovery");
		case ENSR_DISK_LIMITED: return _T("Disk limited");
		case ENSR_HASHING: return _T("Hashing");
		case ENSR_A4AF_CONFLICT: return _T("A4AF conflict");
		default: return _T("Unknown");
		}
	}

	CString NextDurationText(uint64 seconds)
	{
		CString text;
		if (seconds < 60)
			text.Format(_T("%llus"), seconds);
		else if (seconds < 3600)
			text.Format(_T("%llum"), seconds / 60);
		else if (seconds < 86400)
			text.Format(_T("%lluh %02llum"), seconds / 3600, (seconds % 3600) / 60);
		else
			text.Format(_T("%llud %lluh"), seconds / 86400, (seconds % 86400) / 3600);
		return text;
	}

	CString NextFileIntelligenceText(const CPartFile* file, int column)
	{
		const EmuleNextFileSignals signals = BuildNextFileSignals(file);
		if (column == 16) {
			CString text;
			const uint32 health = CDownloadIntelligence::FileAvailabilityHealth(signals);
			text.Format(_T("%u%%"), (health + 5) / 10);
			return text;
		}
		if (column == 17)
			return NextStallText(CDownloadIntelligence::DiagnoseStall(signals));
		if (column == 18) {
			const uint64 remaining = file->GetFileSize() > file->GetCompletedSize()
				? file->GetFileSize() - file->GetCompletedSize() : 0;
			const EmuleNextEta eta = CDownloadIntelligence::EstimateEta(signals, remaining);
			if (!eta.known)
				return _T("--");
			CString text = NextDurationText(eta.seconds);
			CString confidence;
			confidence.Format(_T(" (%u%%)"), eta.confidencePercent);
			text += confidence;
			return text;
		}
		return CString();
	}
}
'''
    if 'BuildNextFileSignals(const CPartFile* file)' not in text:
        if helper_anchor not in text:
            raise RuntimeError("DownloadListCtrl helper anchor not found")
        text = text.replace(helper_anchor, helper_anchor + helpers, 1)

    old_draw = '''\t/*const*/ CPartFile *pPartFile = static_cast<CPartFile*>(pCtrlItem->value);\n\tconst CString &sItem(GetFileItemDisplayText(pPartFile, nColumn));\n\tCRect rcDraw(lpRect);\n'''
    new_draw = '''\t/*const*/ CPartFile *pPartFile = static_cast<CPartFile*>(pCtrlItem->value);\n\tCString sItem = (nColumn >= 16 && nColumn <= 18)\n\t\t? NextFileIntelligenceText(pPartFile, nColumn)\n\t\t: GetFileItemDisplayText(pPartFile, nColumn);\n\tCRect rcDraw(lpRect);\n'''
    if new_draw not in text:
        if old_draw not in text:
            raise RuntimeError("DrawFileItem anchor not found")
        text = text.replace(old_draw, new_draw, 1)

    save(text, newline)
    print("eMule Next file health, stall diagnosis and Smart ETA active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
