#!/usr/bin/env python3
"""Activate eMule Next runtime features in the legacy v0.72a MFC core.

This patcher complements integrate.py. It is deliberately idempotent and keeps
behavior which belongs to the original/manual eMule UI separate from automatic
background discovery.
"""
from __future__ import annotations

import argparse
import pathlib


def load(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    newline = "\r\n" if crlf >= lf and crlf else "\n"
    text = raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n")
    return text, newline


def save(path: pathlib.Path, text: str, newline: str) -> None:
    if newline != "\n":
        text = text.replace("\n", newline)
    path.write_bytes(text.encode("latin-1"))


def replace_once(text: str, old: str, new: str, path: pathlib.Path) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Required anchor not found in {path}: {old[:160]!r}")
    return text.replace(old, new, 1)


def insert_after(text: str, anchor: str, addition: str, path: pathlib.Path) -> str:
    if addition.strip() in text:
        return text
    if anchor not in text:
        raise RuntimeError(f"Required anchor not found in {path}: {anchor!r}")
    return text.replace(anchor, anchor + addition, 1)


def patch_project(src: pathlib.Path) -> None:
    path = src / "emule.vcxproj"
    text, newline = load(path)
    anchor = '    <ClCompile Include="EmuleNextDatabase.cpp" />\n'
    additions = ""
    for name in (
        "EmuleNextSearchBridge.cpp",
        "KnownUsersService.cpp",
        "KnownUsersWnd.cpp",
        "EmuleNextTheme.cpp",
    ):
        if src.joinpath(name).exists() and f'Include="{name}"' not in text:
            additions += f'    <ClCompile Include="{name}" />\n'
    if additions:
        if anchor not in text:
            raise RuntimeError(f"Unable to add eMule Next runtime files to {path}")
        text = text.replace(anchor, anchor + additions, 1)
    save(path, text, newline)


def patch_client_list(src: pathlib.Path) -> None:
    path = src / "ClientList.cpp"
    text, newline = load(path)
    text = insert_after(text, '#include "DownloadQueue.h"\n', '#include "SearchList.h"\n', path)

    old_add = (
        '\t\ttheEmuleNext.RecordPeerSeen(toadd->GetUserHash(), toadd->GetUserName(), CString(), CString(),\n'
        '\t\t\ttoadd->GetConnectIP(), toadd->GetUserPort(), toadd->GetUDPPort(), toadd->GetKadPort());\n'
    )
    new_add = old_add + (
        '\t\t// Reuse a restored legacy shared-file tab instead of immediately requesting\n'
        '\t\t// the same peer again after restart. The restored files are imported into\n'
        '\t\t// eMule Next history once the peer hash is known.\n'
        '\t\tif (toadd->HasValidHash() && theApp.searchlist != NULL) {\n'
        '\t\t\tuint32 restoredFileCount = 0;\n'
        '\t\t\tuint64 restoredTotalBytes = 0;\n'
        '\t\t\tif (theApp.searchlist->ImportClientSharedFilesForPeer(toadd->GetUserName(), toadd->GetUserHash(),\n'
        '\t\t\t\ttoadd->GetIP(), toadd->GetUserPort(), restoredFileCount, restoredTotalBytes)) {\n'
        '\t\t\t\tEmuleNextHash16 restoredHash(toadd->GetUserHash());\n'
        '\t\t\t\tm_peerShareScanner.QueuePeer(restoredHash);\n'
        '\t\t\t\tm_peerShareScanner.OnSharedFileList(restoredHash, restoredFileCount, restoredTotalBytes);\n'
        '\t\t\t}\n'
        '\t\t}\n'
    )
    text = replace_once(text, old_add, new_add, path)

    old_request = (
        '\tCUpDownClient *client = FindClientByUserHash(peerHash.bytes.data());\n'
        '\tif (client == NULL)\n'
        '\t\treturn false;\n'
        '\tclient->RequestSharedFileList();\n'
    )
    new_request = (
        '\tCUpDownClient *client = FindClientByUserHash(peerHash.bytes.data());\n'
        '\tif (client == NULL)\n'
        '\t\treturn false;\n'
        '\t// Tag this request as automatic before using the normal eMule protocol.\n'
        '\t// SearchList will persist the response without creating/updating a legacy\n'
        '\t// user tab, keeping the GUI responsive even for very large shares.\n'
        '\ttheEmuleNext.MarkAutomaticPeerShareRequest(client->GetUserHash());\n'
        '\tclient->RequestSharedFileList();\n'
    )
    text = replace_once(text, old_request, new_request, path)

    old_scan = (
        '\t\tfor (POSITION nextPos = list.GetHeadPosition(); nextPos != NULL;) {\n'
        '\t\t\tCUpDownClient *nextClient = list.GetNext(nextPos);\n'
        '\t\t\tif (nextClient != NULL && nextClient->HasValidHash()\n'
        '\t\t\t\t&& nextClient->GetViewSharedFilesSupport()\n'
        '\t\t\t\t&& nextClient->socket != NULL && nextClient->socket->IsConnected()\n'
        '\t\t\t\t&& nextClient->CheckHandshakeFinished()) {\n'
        '\t\t\t\tm_peerShareScanner.QueuePeer(EmuleNextHash16(nextClient->GetUserHash()));\n'
        '\t\t\t}\n'
        '\t\t}\n'
    )
    new_scan = (
        '\t\tfor (POSITION nextPos = list.GetHeadPosition(); nextPos != NULL;) {\n'
        '\t\t\tCUpDownClient *nextClient = list.GetNext(nextPos);\n'
        '\t\t\tif (nextClient != NULL && nextClient->HasValidHash()\n'
        '\t\t\t\t&& nextClient->GetViewSharedFilesSupport()\n'
        '\t\t\t\t&& nextClient->socket != NULL && nextClient->socket->IsConnected()\n'
        '\t\t\t\t&& nextClient->CheckHandshakeFinished()) {\n'
        '\t\t\t\tEmuleNextHash16 nextHash(nextClient->GetUserHash());\n'
        '\t\t\t\tEmuleNextPeerShareState existingState;\n'
        '\t\t\t\tif (!m_peerShareScanner.GetState(nextHash, existingState) && theApp.searchlist != NULL) {\n'
        '\t\t\t\t\tuint32 restoredFileCount = 0;\n'
        '\t\t\t\t\tuint64 restoredTotalBytes = 0;\n'
        '\t\t\t\t\tif (theApp.searchlist->ImportClientSharedFilesForPeer(nextClient->GetUserName(), nextClient->GetUserHash(),\n'
        '\t\t\t\t\t\tnextClient->GetIP(), nextClient->GetUserPort(), restoredFileCount, restoredTotalBytes)) {\n'
        '\t\t\t\t\t\tm_peerShareScanner.QueuePeer(nextHash);\n'
        '\t\t\t\t\t\tm_peerShareScanner.OnSharedFileList(nextHash, restoredFileCount, restoredTotalBytes);\n'
        '\t\t\t\t\t\tcontinue;\n'
        '\t\t\t\t\t}\n'
        '\t\t\t\t}\n'
        '\t\t\t\tm_peerShareScanner.QueuePeer(nextHash);\n'
        '\t\t\t}\n'
        '\t\t}\n'
    )
    text = replace_once(text, old_scan, new_scan, path)
    save(path, text, newline)


def patch_search_list(src: pathlib.Path) -> None:
    path = src / "SearchList.cpp"
    text, newline = load(path)

    old_head = (
        '\tuint32 nextSharedFileCount = 0;\n'
        '\tuint64 nextSharedTotalBytes = 0;\n'
        '\tuint32 uSearchID = sender.GetSearchID();\n'
        '\tif (!uSearchID) {\n'
        '\t\tuSearchID = theApp.emuledlg->searchwnd->m_pwndResults->GetNextSearchID();\n'
        '\t\tsender.SetSearchID(uSearchID);\n'
        '\t}\n'
        '\tASSERT(uSearchID);\n'
        '\tSSearchParams *pParams = new SSearchParams;\n'
        '\tpParams->strExpression = sender.GetUserName();\n'
        '\tpParams->dwSearchID = uSearchID;\n'
        '\tpParams->bClientSharedFiles = true;\n'
        '\tif (theApp.emuledlg->searchwnd->CreateOrFindTab(pParams, true)) {\n'
        '\t\tm_foundFilesCount[uSearchID] = 0;\n'
        '\t\tm_foundSourcesCount[uSearchID] = 0;\n'
        '\t} else\n'
        '\t\tdelete pParams; //found tab with this ID\n'
    )
    new_head = (
        '\tuint32 nextSharedFileCount = 0;\n'
        '\tuint64 nextSharedTotalBytes = 0;\n'
        '\tconst bool bEmuleNextAutomaticShare = theEmuleNext.IsAutomaticPeerShareRequest(sender.GetUserHash());\n'
        '\tuint32 uSearchID = sender.GetSearchID();\n'
        '\tif (!bEmuleNextAutomaticShare) {\n'
        '\t\tif (!uSearchID) {\n'
        '\t\t\tuSearchID = theApp.emuledlg->searchwnd->m_pwndResults->GetNextSearchID();\n'
        '\t\t\tsender.SetSearchID(uSearchID);\n'
        '\t\t}\n'
        '\t\tASSERT(uSearchID);\n'
        '\t\tSSearchParams *pParams = new SSearchParams;\n'
        '\t\tpParams->strExpression = sender.GetUserName();\n'
        '\t\tpParams->dwSearchID = uSearchID;\n'
        '\t\tpParams->bClientSharedFiles = true;\n'
        '\t\tif (theApp.emuledlg->searchwnd->CreateOrFindTab(pParams, true)) {\n'
        '\t\t\tm_foundFilesCount[uSearchID] = 0;\n'
        '\t\t\tm_foundSourcesCount[uSearchID] = 0;\n'
        '\t\t} else\n'
        '\t\t\tdelete pParams; //found tab with this ID\n'
        '\t}\n'
    )
    text = replace_once(text, old_head, new_head, path)

    old_add = (
        '\t\t++nextSharedFileCount;\n'
        '\t\tnextSharedTotalBytes += toadd->GetFileSize();\n'
        '\t\tAddToList(toadd, true);\n'
        '\t}\n'
        '\tif (m_outputwnd)\n'
        '\t\tm_outputwnd->UpdateTabHeader(uSearchID);\n'
    )
    new_add = (
        '\t\t++nextSharedFileCount;\n'
        '\t\tnextSharedTotalBytes += toadd->GetFileSize();\n'
        '\t\tif (bEmuleNextAutomaticShare)\n'
        '\t\t\tdelete toadd;\n'
        '\t\telse\n'
        '\t\t\tAddToList(toadd, true);\n'
        '\t}\n'
        '\tif (!bEmuleNextAutomaticShare && m_outputwnd)\n'
        '\t\tm_outputwnd->UpdateTabHeader(uSearchID);\n'
    )
    text = replace_once(text, old_add, new_add, path)

    old_tail = (
        '\t// Completing this callback also stops scanner timeout/retry state.\n'
        '\tif (theApp.clientlist != NULL)\n'
        '\t\ttheApp.clientlist->OnPeerSharedFileList(sender.GetUserHash(), nextSharedFileCount, nextSharedTotalBytes);\n'
        '\treturn GetResultCount(uSearchID);\n'
    )
    new_tail = (
        '\t// Completing this callback also stops scanner timeout/retry state.\n'
        '\tif (theApp.clientlist != NULL)\n'
        '\t\ttheApp.clientlist->OnPeerSharedFileList(sender.GetUserHash(), nextSharedFileCount, nextSharedTotalBytes);\n'
        '\tif (bEmuleNextAutomaticShare) {\n'
        '\t\ttheEmuleNext.CompleteAutomaticPeerShareRequest(sender.GetUserHash());\n'
        '\t\treturn nextSharedFileCount;\n'
        '\t}\n'
        '\treturn GetResultCount(uSearchID);\n'
    )
    text = replace_once(text, old_tail, new_tail, path)
    save(path, text, newline)


def patch_search_results(src: pathlib.Path) -> None:
    header_path = src / "SearchResultsWnd.h"
    header, header_newline = load(header_path)
    header = insert_after(header, '#include "SearchListCtrl.h"\n', '#include "KnownUsersWnd.h"\n', header_path)
    header = insert_after(
        header,
        '\tCSearchResultsSelector searchselect;\n',
        '\tCKnownUsersWnd m_knownUsersWnd;\n',
        header_path,
    )
    save(header_path, header, header_newline)

    path = src / "SearchResultsWnd.cpp"
    text, newline = load(path)

    init_anchor = '\tShowSearchSelector(false); //hide tabs, anchor list control\n'
    init_addition = (
        '\n\t// eMule Next has one permanent history view. It is deliberately not a\n'
        '\t// CSearchList entry, so background discovery never becomes a legacy search.\n'
        '\tif (m_knownUsersWnd.Create(this)) {\n'
        '\t\tm_knownUsersWnd.ShowWindow(SW_HIDE);\n'
        '\t\tSSearchParams *knownUsers = new SSearchParams;\n'
        '\t\tknownUsers->dwSearchID = EMULENEXT_KNOWN_USERS_VIEW_ID;\n'
        '\t\tknownUsers->strExpression = _T("Known users");\n'
        '\t\tknownUsers->strSpecialTitle = _T("Known users");\n'
        '\t\tif (!CreateOrFindTab(knownUsers, false))\n'
        '\t\t\tdelete knownUsers;\n'
        '\t\tCRect knownRect;\n'
        '\t\tsearchlistctrl.GetWindowRect(&knownRect);\n'
        '\t\tScreenToClient(&knownRect);\n'
        '\t\tm_knownUsersWnd.MoveWindow(&knownRect);\n'
        '\t\tAddAnchor(m_knownUsersWnd, TOP_LEFT, BOTTOM_RIGHT);\n'
        '\t}\n'
    )
    text = insert_after(text, init_anchor, init_addition, path)

    old_create_tail = (
        '\tsearchselect.SetCurSel(itemnr);\n'
        '\tsearchlistctrl.ShowResults(pParams->dwSearchID);\n'
        '\treturn true; //created new tab\n'
    )
    new_create_tail = (
        '\tsearchselect.SetCurSel(itemnr);\n'
        '\tif (pParams->dwSearchID == EMULENEXT_KNOWN_USERS_VIEW_ID)\n'
        '\t\tShowResults(pParams);\n'
        '\telse\n'
        '\t\tsearchlistctrl.ShowResults(pParams->dwSearchID);\n'
        '\treturn true; //created new tab\n'
    )
    text = replace_once(text, old_create_tail, new_create_tail, path)

    old_show = '''void CSearchResultsWnd::ShowResults(const SSearchParams *pParams)
{
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
    new_show = '''void CSearchResultsWnd::ShowResults(const SSearchParams *pParams)
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
    text = replace_once(text, old_show, new_show, path)

    old_close = (
        '\t\tuint32 uSearchID = reinterpret_cast<SSearchParams*>(ti.lParam)->dwSearchID;\n'
        '\t\tif (uSearchID == m_nEd2kSearchID && !m_cancelled)\n'
    )
    new_close = (
        '\t\tuint32 uSearchID = reinterpret_cast<SSearchParams*>(ti.lParam)->dwSearchID;\n'
        '\t\tif (uSearchID == EMULENEXT_KNOWN_USERS_VIEW_ID)\n'
        '\t\t\treturn TRUE;\n'
        '\t\tif (uSearchID == m_nEd2kSearchID && !m_cancelled)\n'
    )
    text = replace_once(text, old_close, new_close, path)

    delete_anchor = 'void CSearchResultsWnd::DeleteSearch(uint32 uSearchID)\n{\n'
    delete_addition = '\tif (uSearchID == EMULENEXT_KNOWN_USERS_VIEW_ID)\n\t\treturn;\n\n'
    text = insert_after(text, delete_anchor, delete_addition, path)

    old_delete_all = '''void CSearchResultsWnd::DeleteAllSearches()
{
\tCancelEd2kSearch();

\tTCITEM ti;
\tti.mask = TCIF_PARAM;
\tfor (int i = searchselect.GetItemCount(); --i >= 0;)
\t\tif (searchselect.GetItem(i, &ti) && ti.lParam != NULL) {
\t\t\tconst SSearchParams *params = reinterpret_cast<SSearchParams*>(ti.lParam);
\t\t\tKademlia::CSearchManager::StopSearch(params->dwSearchID, false);
\t\t\tdelete params;
\t\t}

\tNoTabItems();
}'''
    new_delete_all = '''void CSearchResultsWnd::DeleteAllSearches()
{
\tCancelEd2kSearch();

\tTCITEM ti;
\tti.mask = TCIF_PARAM;
\tfor (int i = searchselect.GetItemCount(); --i >= 0;) {
\t\tif (!searchselect.GetItem(i, &ti) || ti.lParam == NULL)
\t\t\tcontinue;
\t\tSSearchParams *params = reinterpret_cast<SSearchParams*>(ti.lParam);
\t\tif (params->dwSearchID == EMULENEXT_KNOWN_USERS_VIEW_ID)
\t\t\tcontinue;
\t\tKademlia::CSearchManager::StopSearch(params->dwSearchID, false);
\t\ttheApp.searchlist->RemoveResults(params->dwSearchID);
\t\tsearchlistctrl.ClearResultViewState(params->dwSearchID);
\t\tsearchselect.DeleteItem(i);
\t\tdelete params;
\t}

\tsearchlistctrl.DeleteAllItems();
\tfor (int i = 0; i < searchselect.GetItemCount(); ++i) {
\t\tif (searchselect.GetItem(i, &ti) && ti.lParam != NULL
\t\t\t&& reinterpret_cast<SSearchParams*>(ti.lParam)->dwSearchID == EMULENEXT_KNOWN_USERS_VIEW_ID) {
\t\t\tsearchselect.SetCurSel(i);
\t\t\tShowSearchSelector(true);
\t\t\tShowResults(reinterpret_cast<SSearchParams*>(ti.lParam));
\t\t\treturn;
\t\t}
\t}
\tNoTabItems();
}'''
    text = replace_once(text, old_delete_all, new_delete_all, path)
    save(path, text, newline)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=pathlib.Path)
    args = parser.parse_args()

    repo = pathlib.Path(__file__).resolve().parents[2]
    src = args.source_dir.resolve() if args.source_dir else repo / "srchybrid"
    for required in ("emule.vcxproj", "ClientList.cpp", "SearchList.cpp", "SearchResultsWnd.cpp", "SearchResultsWnd.h"):
        if not (src / required).exists():
            raise RuntimeError(f"Missing {src / required}")

    patch_project(src)
    patch_client_list(src)
    patch_search_list(src)
    if (src.joinpath("KnownUsersWnd.cpp").exists()):
        patch_search_results(src)
    print(f"eMule Next runtime features active in {src}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
