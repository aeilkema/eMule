#!/usr/bin/env python3
"""Normalize SearchResultsWnd::ShowResults for eMule Next activation.

The legacy file has changed indentation between upstream releases. This tiny
pre-patch replaces the function by structural boundaries instead of depending
on whitespace, after which activate-runtime-features.py remains idempotent.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "SearchResultsWnd.cpp"

raw = PATH.read_bytes()
crlf = raw.count(b"\r\n")
lf = raw.count(b"\n") - crlf
newline = "\r\n" if crlf >= lf and crlf else "\n"
text = raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n")

marker = "pParams->dwSearchID == EMULENEXT_KNOWN_USERS_VIEW_ID"
if marker not in text:
    start_token = "void CSearchResultsWnd::ShowResults(const SSearchParams *pParams)\n{"
    end_token = "\n}\n\nvoid CSearchResultsWnd::OnSelChangeTab"
    start = text.find(start_token)
    if start < 0:
        raise RuntimeError("ShowResults start not found")
    end = text.find(end_token, start)
    if end < 0:
        raise RuntimeError("ShowResults end not found")
    end += 2

    replacement = '''void CSearchResultsWnd::ShowResults(const SSearchParams *pParams)
{
\tif (pParams->dwSearchID == EMULENEXT_KNOWN_USERS_VIEW_ID) {
\t\tsearchlistctrl.ShowWindow(SW_HIDE);
\t\tm_knownUsersWnd.ShowWindow(SW_SHOW);
\t\tm_ctlFilter.ShowWindow(SW_HIDE);
\t\tGetDlgItem(IDC_SDOWNLOAD)->ShowWindow(SW_HIDE);
\t\tm_cattabs.ShowWindow(SW_HIDE);
\t\tGetDlgItem(IDC_STATIC_DLTOof)->ShowWindow(SW_HIDE);
\t\tm_knownUsersWnd.Refresh(true);
\t\treturn;
\t}

\tm_knownUsersWnd.ShowWindow(SW_HIDE);
\tsearchlistctrl.ShowWindow(SW_SHOW);
\tif (m_bTabs)
\t\tm_ctlFilter.ShowWindow(SW_SHOW);
\tGetDlgItem(IDC_SDOWNLOAD)->ShowWindow(SW_SHOW);
\tUpdateCatTabs();

\t// restoring the params works and is nice during development/testing but pretty annoying in practice.
\t// TODO: maybe it should be done explicitly via a context menu function or such.
\tif (GetKeyState(VK_CONTROL) < 0)
\t\tm_pwndParams->SetParameters(pParams);

\tbool bEnable = (pParams->eType == SearchTypeEd2kServer
\t\t\t\t\t&& pParams->dwSearchID == m_nEd2kSearchID && IsLocalEd2kSearchRunning())
\t\t\t\t\t|| (pParams->eType == SearchTypeEd2kGlobal
\t\t\t\t\t\t&& pParams->dwSearchID == m_nEd2kSearchID && (IsLocalEd2kSearchRunning() || IsGlobalEd2kSearchRunning()))
\t\t\t\t\t|| (pParams->eType == SearchTypeKademlia
\t\t\t\t\t\t&& Kademlia::CSearchManager::IsSearching(pParams->dwSearchID));
\tif (bEnable)
\t\tm_pwndParams->m_ctlCancel.EnableWindow(bEnable);
\tsearchlistctrl.ShowResults(pParams->dwSearchID);
}'''
    text = text[:start] + replacement + text[end:]

if newline != "\n":
    text = text.replace("\n", newline)
PATH.write_bytes(text.encode("latin-1"))
print("SearchResultsWnd ShowResults normalized for eMule Next")
