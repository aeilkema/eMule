#!/usr/bin/env python3
"""Add a live source-quality profile to Dashboard file details."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "EmuleNextDashboardWnd.cpp"


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

    helper_anchor = '''    CString RecommendationText(const DashboardRow& row)\n'''
    helper = '''    struct LiveSourceProfile\n    {\n        uint32 count;\n        uint32 transferring;\n        uint32 strong;\n        uint32 bestQuality;\n        uint32 averageQuality;\n        uint32 bestQueueRank;\n\n        LiveSourceProfile()\n            : count(0), transferring(0), strong(0), bestQuality(0), averageQuality(0), bestQueueRank(0) {}\n    };\n\n    LiveSourceProfile BuildLiveSourceProfile(CPartFile* file)\n    {\n        LiveSourceProfile profile;\n        if (file == NULL)\n            return profile;\n\n        uint64 qualityTotal = 0;\n        POSITION pos = file->srclist.GetHeadPosition();\n        while (pos != NULL) {\n            CUpDownClient* client = file->srclist.GetNext(pos);\n            if (client == NULL)\n                continue;\n\n            EmuleNextSourceSignals signals;\n            signals.currentBytesPerSecond = static_cast<double>(client->GetDownloadDatarate());\n            signals.remoteQueueRank = client->GetRemoteQueueRank();\n            const EDownloadState state = client->GetDownloadState();\n            signals.connected = state == DS_CONNECTED || state == DS_DOWNLOADING || state == DS_REQHASHSET;\n            signals.currentlyTransferring = state == DS_DOWNLOADING;\n            for (UINT part = 0; part < client->GetPartCount(); ++part) {\n                if (client->IsPartAvailable(part))\n                    ++signals.usefulPartCount;\n            }\n\n            const uint32 quality = CDownloadIntelligence::SourceQuality(signals);\n            ++profile.count;\n            qualityTotal += quality;\n            profile.bestQuality = std::max(profile.bestQuality, quality);\n            if (quality >= 700)\n                ++profile.strong;\n            if (signals.currentlyTransferring)\n                ++profile.transferring;\n            if (signals.remoteQueueRank > 0\n                && (profile.bestQueueRank == 0 || signals.remoteQueueRank < profile.bestQueueRank))\n                profile.bestQueueRank = signals.remoteQueueRank;\n        }\n        if (profile.count > 0)\n            profile.averageQuality = static_cast<uint32>(qualityTotal / profile.count);\n        return profile;\n    }\n\n'''
    if 'BuildLiveSourceProfile(CPartFile* file)' not in text:
        if helper_anchor not in text:
            raise RuntimeError('Dashboard live source helper anchor not found')
        text = text.replace(helper_anchor, helper + helper_anchor, 1)

    eta_anchor = '''    row.eta = CDownloadIntelligence::EstimateEta(row.signals, fileSize > completed ? fileSize - completed : 0);\n\n    CString confidence;\n'''
    eta_new = '''    row.eta = CDownloadIntelligence::EstimateEta(row.signals, fileSize > completed ? fileSize - completed : 0);\n    const LiveSourceProfile sourceProfile = BuildLiveSourceProfile(file);\n\n    CString confidence;\n'''
    if 'const LiveSourceProfile sourceProfile = BuildLiveSourceProfile(file);' not in text:
        if eta_anchor not in text:
            raise RuntimeError('Dashboard live source profile details anchor not found')
        text = text.replace(eta_anchor, eta_new, 1)

    old_format = '''        _T("Smart ETA: %s   Confidence: %s   Discovery budget: %u/%u   A4AF score: %u%%\\r\\n")\n        _T("ETA basis: %s\\r\\nRecommendation: %s\\r\\nDouble-click or press Enter to jump to this file in Transfers."),\n'''
    new_format = '''        _T("Smart ETA: %s   Confidence: %s   Discovery budget: %u/%u   A4AF score: %u%%\\r\\n")\n        _T("Live sources: %u tracked   Best quality: %u%%   Average: %u%%   Strong: %u   Transferring: %u   Best queue: %s\\r\\n")\n        _T("ETA basis: %s\\r\\nRecommendation: %s\\r\\nDouble-click or press Enter to jump to this file in Transfers."),\n'''
    if 'Live sources: %u tracked' not in text:
        if old_format not in text:
            raise RuntimeError('Dashboard live source format anchor not found')
        text = text.replace(old_format, new_format, 1)

    args_anchor = '''        (row.a4afScore + 5) / 10,\n        row.eta.reason.IsEmpty() ? _T("not enough stable rate data") : (LPCTSTR)row.eta.reason,\n'''
    args_new = '''        (row.a4afScore + 5) / 10,\n        sourceProfile.count,\n        (sourceProfile.bestQuality + 5) / 10,\n        (sourceProfile.averageQuality + 5) / 10,\n        sourceProfile.strong,\n        sourceProfile.transferring,\n        sourceProfile.bestQueueRank > 0 ? (LPCTSTR)CString(std::to_wstring(sourceProfile.bestQueueRank).c_str()) : _T("--"),\n        row.eta.reason.IsEmpty() ? _T("not enough stable rate data") : (LPCTSTR)row.eta.reason,\n'''
    if 'sourceProfile.count,' not in text:
        if args_anchor not in text:
            raise RuntimeError('Dashboard live source args anchor not found')
        text = text.replace(args_anchor, args_new, 1)

    save(text, newline)
    print('eMule Next Dashboard live source profile active')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
