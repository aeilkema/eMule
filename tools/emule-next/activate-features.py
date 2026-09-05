#!/usr/bin/env python3
"""Activate eMule Next features which need legacy-core runtime hooks.

This layer is intentionally separate from integrate.py: integrate.py establishes
core source/build compatibility, while this script wires user-visible runtime
features and warning-policy cleanup. It is idempotent and fails when an expected
legacy anchor disappears.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
_NEWLINES: dict[pathlib.Path, str] = {}


def load(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    cr = raw.count(b"\r") - crlf
    if crlf >= lf and crlf >= cr and crlf:
        newline = "\r\n"
    elif cr > lf and cr:
        newline = "\r"
    else:
        newline = "\n"
    _NEWLINES[path] = newline
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n")


def save(path: pathlib.Path, text: str) -> None:
    newline = _NEWLINES.get(path, "\n")
    if newline != "\n":
        text = text.replace("\n", newline)
    path.write_bytes(text.encode("latin-1"))


def require(text: str, needle: str, path: pathlib.Path) -> None:
    if needle not in text:
        raise RuntimeError(f"Required anchor not found in {path}: {needle!r}")


def insert_after(text: str, anchor: str, addition: str, path: pathlib.Path) -> str:
    if addition.strip() in text:
        return text
    require(text, anchor, path)
    return text.replace(anchor, anchor + addition, 1)


def insert_before(text: str, anchor: str, addition: str, path: pathlib.Path) -> str:
    if addition.strip() in text:
        return text
    require(text, anchor, path)
    return text.replace(anchor, addition + anchor, 1)


def replace_once(text: str, old: str, new: str, path: pathlib.Path) -> str:
    if new in text:
        return text
    require(text, old, path)
    return text.replace(old, new, 1)


def patch_vcxproj() -> None:
    path = SRC / "emule.vcxproj"
    text = load(path)
    # /Wall on a legacy MFC application mostly reports Windows SDK/ATL/Crypto++
    # implementation details. /W4 keeps actionable project warnings visible.
    text = text.replace(
        "<WarningLevel>EnableAllWarnings</WarningLevel>",
        "<WarningLevel>Level4</WarningLevel>",
    )
    save(path, text)


def patch_emule_cpp() -> None:
    path = SRC / "Emule.cpp"
    text = load(path)
    text = text.replace(
        "m_aBigExtToSysImgIdx[pszCacheExt] = (LPVOID)sfi.iIcon;",
        "m_aBigExtToSysImgIdx[pszCacheExt] = reinterpret_cast<LPVOID>(static_cast<INT_PTR>(sfi.iIcon));",
    )
    text = text.replace(
        "m_aExtToSysImgIdx[pszCacheExt] = (LPVOID)sfi.iIcon;",
        "m_aExtToSysImgIdx[pszCacheExt] = reinterpret_cast<LPVOID>(static_cast<INT_PTR>(sfi.iIcon));",
    )
    text = text.replace(
        "return reinterpret_cast<int>(vData);",
        "return static_cast<int>(reinterpret_cast<INT_PTR>(vData));",
    )
    save(path, text)


def patch_client_list_h() -> None:
    path = SRC / "ClientList.h"
    text = load(path)
    text = insert_after(text, '#include "ClientIndex.h"\n', '#include "PeerShareScanner.h"\n', path)
    text = replace_once(
        text,
        "class CClientList\n{",
        "class CClientList : public IEmuleNextPeerShareTransport\n{",
        path,
    )

    public_anchor = "\tvoid\tProcess();\n"
    public_addition = (
        "\t// eMule Next: automatically inspect shares exposed by connected peers.\n"
        "\tvoid\tOnPeerSharedFileList(const uchar *peerHash, uint32 fileCount, uint64 totalBytes);\n"
        "\tvirtual bool RequestSharedFileList(const EmuleNextHash16& peerHash);\n"
        "\tvirtual bool IsPeerOnline(const EmuleNextHash16& peerHash) const;\n"
    )
    text = insert_after(text, public_anchor, public_addition, path)

    member_anchor = "\tCClientIndex m_index;\n"
    member_addition = (
        "\t// Privacy-respecting scanner: uses the normal eMule View Shared Files request,\n"
        "\t// honours peer denial and throttles concurrent/background requests.\n"
        "\tCPeerShareScanner m_peerShareScanner;\n"
    )
    text = insert_after(text, member_anchor, member_addition, path)
    save(path, text)


def patch_client_list_cpp() -> None:
    path = SRC / "ClientList.cpp"
    text = load(path)

    ctor_anchor = "\tm_globDeadSourceList.Init(true);\n"
    text = insert_after(
        text,
        ctor_anchor,
        "\tm_peerShareScanner.SetTransport(this);\n",
        path,
    )

    process_anchor = (
        "\t///////////////////////////////////////////////////////////////////////////\n"
        "\t// Cleanup client list\n"
        "\t//\n"
        "\tCleanUpClientList();\n"
    )
    scanner_process = (
        "\t///////////////////////////////////////////////////////////////////////////\n"
        "\t// eMule Next automatic peer-share discovery. Only already-connected peers\n"
        "\t// which advertise share browsing are queued. The scanner provides TTL,\n"
        "\t// timeout and concurrency limits, so Process() can call this every tick.\n"
        "\tif (theEmuleNext.IsRunning()) {\n"
        "\t\tfor (POSITION nextPos = list.GetHeadPosition(); nextPos != NULL;) {\n"
        "\t\t\tCUpDownClient *nextClient = list.GetNext(nextPos);\n"
        "\t\t\tif (nextClient != NULL && nextClient->HasValidHash()\n"
        "\t\t\t\t&& nextClient->GetViewSharedFilesSupport()\n"
        "\t\t\t\t&& nextClient->socket != NULL && nextClient->socket->IsConnected()\n"
        "\t\t\t\t&& nextClient->CheckHandshakeFinished()) {\n"
        "\t\t\t\tm_peerShareScanner.QueuePeer(EmuleNextHash16(nextClient->GetUserHash()));\n"
        "\t\t\t}\n"
        "\t\t}\n"
        "\t\tm_peerShareScanner.Tick();\n"
        "\t}\n\n"
    )
    text = insert_before(text, process_anchor, scanner_process, path)

    methods_anchor = "void CClientList::Process()\n{\n"
    methods = '''bool CClientList::IsPeerOnline(const EmuleNextHash16& peerHash) const
{
\tif (!peerHash.valid)
\t\treturn false;
\tCUpDownClient *client = FindClientByUserHash(peerHash.bytes.data());
\treturn client != NULL
\t\t&& client->HasValidHash()
\t\t&& client->GetViewSharedFilesSupport()
\t\t&& client->socket != NULL
\t\t&& client->socket->IsConnected()
\t\t&& client->CheckHandshakeFinished();
}

bool CClientList::RequestSharedFileList(const EmuleNextHash16& peerHash)
{
\tif (!IsPeerOnline(peerHash))
\t\treturn false;
\tCUpDownClient *client = FindClientByUserHash(peerHash.bytes.data());
\tif (client == NULL)
\t\treturn false;
\tclient->RequestSharedFileList();
\tAddDebugLogLine(false, _T("eMule Next: requested shared files from %s"),
\t\tclient->GetUserName() != NULL ? client->GetUserName() : _T("<unknown>"));
\treturn true;
}

void CClientList::OnPeerSharedFileList(const uchar *peerHash, uint32 fileCount, uint64 totalBytes)
{
\tEmuleNextHash16 hash(peerHash);
\tif (!hash.valid)
\t\treturn;
\tm_peerShareScanner.OnSharedFileList(hash, fileCount, totalBytes);
\tAddDebugLogLine(false, _T("eMule Next: peer shared-file scan completed: %u files, %I64u bytes"),
\t\tfileCount, totalBytes);
}

'''
    text = insert_before(text, methods_anchor, methods, path)
    save(path, text)


def patch_search_list_cpp() -> None:
    path = SRC / "SearchList.cpp"
    text = load(path)
    text = insert_after(text, '#include "Log.h"\n', '#include "EmuleNextRuntime.h"\n#include "ClientList.h"\n', path)

    function_anchor = (
        "UINT CSearchList::ProcessSearchAnswer(const uchar *in_packet, uint32 size\n"
        "\t, CUpDownClient &sender, bool *pbMoreResultsAvailable, LPCTSTR pszDirectory)\n"
        "{\n"
    )
    counters = "\tuint32 nextSharedFileCount = 0;\n\tuint64 nextSharedTotalBytes = 0;\n"
    text = insert_after(text, function_anchor, counters, path)

    add_anchor = "\t\ttoadd->SetPreviewPossible(sender.GetPreviewSupport() && ED2KFT_VIDEO == GetED2KFileTypeID(toadd->GetFileName()));\n\t\tAddToList(toadd, true);\n"
    add_replacement = (
        "\t\ttoadd->SetPreviewPossible(sender.GetPreviewSupport() && ED2KFT_VIDEO == GetED2KFileTypeID(toadd->GetFileName()));\n"
        "\t\t// Persist peer/file history before the legacy result object is merged into the UI list.\n"
        "\t\ttheEmuleNext.RecordFileSeen(toadd->GetFileHash(), toadd->GetFileSize(), toadd->GetFileName());\n"
        "\t\ttheEmuleNext.RecordPeerFileSeen(sender.GetUserHash(), toadd->GetFileHash(), toadd->GetFileSize(),\n"
        "\t\t\ttoadd->GetFileName(), CString(), _T(\"peer-shared-list\"));\n"
        "\t\t++nextSharedFileCount;\n"
        "\t\tnextSharedTotalBytes += toadd->GetFileSize();\n"
        "\t\tAddToList(toadd, true);\n"
    )
    text = replace_once(text, add_anchor, add_replacement, path)

    return_anchor = "\tpacket.Close();\n\treturn GetResultCount(uSearchID);\n}\n"
    return_replacement = (
        "\tpacket.Close();\n"
        "\t// Completing this callback also stops scanner timeout/retry state.\n"
        "\tif (theApp.clientlist != NULL)\n"
        "\t\ttheApp.clientlist->OnPeerSharedFileList(sender.GetUserHash(), nextSharedFileCount, nextSharedTotalBytes);\n"
        "\treturn GetResultCount(uSearchID);\n"
        "}\n"
    )
    text = replace_once(text, return_anchor, return_replacement, path)
    save(path, text)


def patch_file_library_cpp() -> None:
    path = SRC / "FileLibraryService.cpp"
    text = load(path)
    unused = '''    void BindHashValue(sqlite3_stmt* stmt, int index, const EmuleNextHash16& hash)
    {
        sqlite3_bind_blob(stmt, index, hash.bytes.data(), 16, SQLITE_TRANSIENT);
    }

'''
    text = text.replace(unused, "")
    save(path, text)


def main() -> int:
    required = [
        SRC / "emule.vcxproj",
        SRC / "Emule.cpp",
        SRC / "ClientList.h",
        SRC / "ClientList.cpp",
        SRC / "SearchList.cpp",
        SRC / "FileLibraryService.cpp",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        raise RuntimeError("Missing source files: " + ", ".join(missing))

    patch_vcxproj()
    patch_emule_cpp()
    patch_client_list_h()
    patch_client_list_cpp()
    patch_search_list_cpp()
    patch_file_library_cpp()
    print("eMule Next active feature wiring complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
