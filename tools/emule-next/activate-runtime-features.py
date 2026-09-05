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
        raise RuntimeError(f"Required anchor not found in {path}: {old[:120]!r}")
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
        if (src.joinpath(name).exists() and f'Include="{name}"' not in text:
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=pathlib.Path)
    args = parser.parse_args()

    repo = pathlib.Path(__file__).resolve().parents[2]
    src = args.source_dir.resolve() if args.source_dir else repo / "srchybrid"
    for required in ("emule.vcxproj", "ClientList.cpp", "SearchList.cpp"):
        if not (src / required).exists():
            raise RuntimeError(f"Missing {src / required}")

    patch_project(src)
    patch_client_list(src)
    patch_search_list(src)
    print(f"eMule Next runtime features active in {src}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
