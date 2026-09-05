#!/usr/bin/env python3
"""Expose non-blocking eMule Next source intelligence in the active Transfers list."""
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
    includes = '#include "EmuleNextRuntime.h"\n#include "DownloadIntelligence.h"\n'
    if '#include "DownloadIntelligence.h"' not in text:
        if include_anchor not in text:
            raise RuntimeError("DownloadListCtrl include anchor not found")
        text = text.replace(include_anchor, include_anchor + includes, 1)

    column_anchor = '\tInsertColumn(13,\t_T(""),\tLVCFMT_LEFT,\t120);\t\t\t\t\t\t\t//IDS_ADDEDON\n'
    columns = '\tInsertColumn(14,\t_T("Alias"),\tLVCFMT_LEFT,\t130);\n\tInsertColumn(15,\t_T("Live quality"),\tLVCFMT_RIGHT,\t90);\n'
    if 'InsertColumn(15,\t_T("Live quality")' not in text:
        if column_anchor not in text:
            raise RuntimeError("DownloadListCtrl column anchor not found")
        text = text.replace(column_anchor, column_anchor + columns, 1)

    localize_anchor = '''\tstrRes = GetResString(IDS_FD_LASTCHANGE);\n\tstrRes.Remove(_T(':'));\n\thdi.pszText = const_cast<LPTSTR>((LPCTSTR)strRes);\n\tpHeaderCtrl->SetItem(11, &hdi);\n'''
    localize = '''\n\tCString nextAlias(_T("Alias"));\n\thdi.pszText = const_cast<LPTSTR>((LPCTSTR)nextAlias);\n\tpHeaderCtrl->SetItem(14, &hdi);\n\tCString nextQuality(_T("Live quality"));\n\thdi.pszText = const_cast<LPTSTR>((LPCTSTR)nextQuality);\n\tpHeaderCtrl->SetItem(15, &hdi);\n'''
    if 'pHeaderCtrl->SetItem(15, &hdi);' not in text:
        if localize_anchor not in text:
            raise RuntimeError("DownloadListCtrl Localize anchor not found")
        text = text.replace(localize_anchor, localize_anchor + localize, 1)

    source_anchor = '''\t//case 9: //remaining time & size\n\t//case 10: //last seen complete\n\t//case 11: //last received\n\t//case 12: //category\n\t//case 13: //added on\n\t}\n\treturn sText;\n}\n'''
    source_cases = '''\tcase 14: // local alias; network username remains column 0\n\t\tif (pClient->HasValidHash())\n\t\t\ttheEmuleNext.GetPeerAlias(pClient->GetUserHash(), sText);\n\t\tbreak;\n\tcase 15: // cheap live-only intelligence: never query SQLite from a paint path\n\t\t{\n\t\t\tEmuleNextSourceSignals signals;\n\t\t\tsignals.currentBytesPerSecond = static_cast<double>(pClient->GetDownloadDatarate());\n\t\t\tsignals.remoteQueueRank = pClient->GetRemoteQueueRank();\n\t\t\tsignals.connected = pClient->socket != NULL && pClient->socket->IsConnected();\n\t\t\tsignals.currentlyTransferring = pClient->GetDownloadState() == DS_DOWNLOADING;\n\t\t\tsignals.secureIdentified = pClient->Credits() != NULL\n\t\t\t\t&& pClient->Credits()->GetCurrentIdentState(pClient->GetIP()) == IS_IDENTIFIED;\n\t\t\tfor (UINT part = 0; part < pClient->GetPartCount(); ++part) {\n\t\t\t\tif (pClient->IsPartAvailable(part))\n\t\t\t\t\t++signals.usefulPartCount;\n\t\t\t}\n\t\t\tconst uint32 quality = CDownloadIntelligence::SourceQuality(signals);\n\t\t\tsText.Format(_T("%u%%"), (quality + 5) / 10);\n\t\t}\n\t\tbreak;\n'''
    if 'case 15: // cheap live-only intelligence' not in text:
        if source_anchor not in text:
            raise RuntimeError("DownloadListCtrl source display anchor not found")
        replacement = source_cases + source_anchor
        text = text.replace(source_anchor, replacement, 1)

    save(text, newline)
    print("eMule Next live Transfers source intelligence active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
