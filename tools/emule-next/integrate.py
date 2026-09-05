#!/usr/bin/env python3
"""Idempotently integrate eMule Next services into the v0.72a legacy core.

This script intentionally edits the legacy MFC files in one audited place.  It
fails if expected anchors disappear instead of silently producing a partial
integration.  It can be run repeatedly; a second run should produce no diff.

The historic eMule sources are a mixture of ANSI/Windows-1252 and UTF-8 files.
All injected source text is ASCII, so the integrator uses a Latin-1 round-trip
for target files.  That maps every input byte 1:1 and prevents an integration
run from corrupting or needlessly re-encoding untouched legacy source text.
Original CRLF/LF line endings are preserved as well.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"

CPP_FILES = [
    "EmuleNextDatabase.cpp",
    "EmuleNextRuntime.cpp",
    "DownloadIntelligence.cpp",
    "PeerShareScanner.cpp",
    "FileLibraryService.cpp",
    "Search2Service.cpp",
    "ClientIndex.cpp",
    "DownloadIndex.cpp",
]
HEADER_FILES = [
    "EmuleNextDatabase.h",
    "EmuleNextRuntime.h",
    "DownloadIntelligence.h",
    "PeerShareScanner.h",
    "FileLibraryService.h",
    "Search2Service.h",
    "ClientIndex.h",
    "DownloadIndex.h",
]

# load() normalizes newlines for deterministic anchors. save() restores the
# dominant newline sequence seen in the original byte stream.
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

    # Latin-1 is deliberately used as a byte-preserving transport encoding.
    # Existing UTF-8 multibyte sequences/BOMs are not interpreted and therefore
    # survive unchanged. All additions below are 7-bit ASCII.
    text = raw.decode("latin-1")
    return text.replace("\r\n", "\n").replace("\r", "\n")


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

    # Windows 10/11 ships winsqlite3.dll; using the SDK import library avoids
    # vendoring a second SQLite source tree.  eMule Next intentionally targets
    # Windows 10/11 rather than preserving the historic XP runtime contract.
    dep_pattern = re.compile(r"<AdditionalDependencies>(.*?)</AdditionalDependencies>")

    def add_sqlite(match: re.Match[str]) -> str:
        value = match.group(1)

        required = [
            "winsqlite3.lib",
            "bcrypt.lib",
            r"..\mbedtls\visualc\vs2017\$(Platform)\$(Configuration)\mbedx509.lib",
            r"..\mbedtls\visualc\vs2017\$(Platform)\$(Configuration)\tfpsacrypto.lib",
        ]

        existing = value.lower()
        missing = [dependency for dependency in required if dependency.lower() not in existing]

        if not missing:
            return match.group(0)

        prefix = ";".join(missing) + ";"
        return f"<AdditionalDependencies>{prefix}{value}</AdditionalDependencies>"

    text, count = dep_pattern.subn(add_sqlite, text)
    if count == 0:
        raise RuntimeError("No AdditionalDependencies entries found in emule.vcxproj")

    compile_anchor = '    <ClCompile Include="Emule.cpp" />\n'
    require(text, compile_anchor, path)
    compile_lines = "".join(
        f'    <ClCompile Include="{name}" />\n' for name in CPP_FILES if f'Include="{name}"' not in text
    )
    if compile_lines:
        text = text.replace(compile_anchor, compile_anchor + compile_lines, 1)

    include_anchor = '    <ClInclude Include="Emule.h" />\n'
    require(text, include_anchor, path)
    include_lines = "".join(
        f'    <ClInclude Include="{name}" />\n' for name in HEADER_FILES if f'Include="{name}"' not in text
    )
    if include_lines:
        text = text.replace(include_anchor, include_anchor + include_lines, 1)

    save(path, text)


def patch_emule_cpp() -> None:
    path = SRC / "Emule.cpp"
    text = load(path)
    text = insert_after(text, '#include "Preferences.h"\n', '#include "EmuleNextRuntime.h"\n', path)
    text = insert_after(
        text,
        '\tthePrefs.Init();\n',
        '\t// eMule Next is additive: failure disables history/intelligence but never core networking.\n'
        '\ttheEmuleNext.Start();\n',
        path,
    )
    text = insert_after(
        text,
        '\temuledlg->DoModal();\n',
        '\t// Drain the async intelligence queue while core objects are still valid.\n'
        '\ttheEmuleNext.Stop();\n',
        path,
    )
    save(path, text)


def patch_client_list_h() -> None:
    path = SRC / "ClientList.h"
    text = load(path)
    text = insert_after(text, '#include "DeadSourceList.h"\n', '#include "ClientIndex.h"\n', path)
    text = insert_before(
        text,
        '\tCUpDownClientPtrList list;\n',
        '\t// Fast identity/endpoint lookup kept in lock-step with the canonical MFC list.\n'
        '\tCClientIndex m_index;\n',
        path,
    )
    save(path, text)


def patch_client_list_cpp() -> None:
    path = SRC / "ClientList.cpp"
    text = load(path)
    text = insert_after(text, '#include "Statistics.h"\n', '#include "EmuleNextRuntime.h"\n', path)

    old_add = (
        '\t\ttheApp.emuledlg->transferwnd->GetClientList().AddClient(toadd);\n'
        '\t\tlist.AddTail(toadd);\n'
    )
    new_add = old_add + (
        '\t\tm_index.RegisterClient(toadd, toadd->GetUserHash(), toadd->GetConnectIP(),\n'
        '\t\t\ttoadd->GetUserPort(), toadd->GetUDPPort(), toadd->GetKadPort());\n'
        '\t\ttheEmuleNext.RecordPeerSeen(toadd->GetUserHash(), toadd->GetUserName(), CString(), CString(),\n'
        '\t\t\ttoadd->GetConnectIP(), toadd->GetUserPort(), toadd->GetUDPPort(), toadd->GetKadPort());\n'
    )
    text = replace_once(text, old_add, new_add, path)

    old_remove = '\t\ttheApp.emuledlg->transferwnd->GetClientList().RemoveClient(toremove);\n\t\tlist.RemoveAt(pos);\n'
    new_remove = (
        '\t\ttheApp.emuledlg->transferwnd->GetClientList().RemoveClient(toremove);\n'
        '\t\tm_index.UnregisterClient(toremove);\n'
        '\t\tlist.RemoveAt(pos);\n'
    )
    text = replace_once(text, old_remove, new_remove, path)

    # Use the index as the fast path. Keep the legacy scan as a fallback while
    # handshake-time identity refresh hooks are being validated.
    conn_pattern = re.compile(
        r'CUpDownClient \*CClientList::FindClientByConnIP\(uint32 clientip, UINT port\) const\n\{.*?\n\}',
        re.S,
    )
    conn_replacement = '''CUpDownClient *CClientList::FindClientByConnIP(uint32 clientip, UINT port) const
{
\tCUpDownClient *indexed = m_index.FindByTcpEndpoint(clientip, static_cast<uint16>(port));
\tif (indexed != NULL)
\t\treturn indexed;
\tfor (POSITION pos = list.GetHeadPosition(); pos != NULL;) {
\t\tCUpDownClient *cur_client = list.GetNext(pos);
\t\tif (cur_client->GetConnectIP() == clientip && cur_client->GetUserPort() == port)
\t\t\treturn cur_client;
\t}
\treturn NULL;
}'''
    if "m_index.FindByTcpEndpoint(clientip" not in text:
        text, count = conn_pattern.subn(conn_replacement, text, count=1)
        if count != 1:
            raise RuntimeError("Unable to patch FindClientByConnIP")

    user_pattern = re.compile(
        r'CUpDownClient\* CClientList::FindClientByUserHash\(const uchar \*clienthash, uint32 dwIP, uint16 nTCPPort\) const\n\{.*?\n\}',
        re.S,
    )
    user_replacement = '''CUpDownClient* CClientList::FindClientByUserHash(const uchar *clienthash, uint32 dwIP, uint16 nTCPPort) const
{
\tCUpDownClient *indexed = m_index.FindByUserHash(clienthash, dwIP, nTCPPort);
\tif (indexed != NULL)
\t\treturn indexed;

\tCUpDownClient *pFound = NULL;
\tfor (POSITION pos = list.GetHeadPosition(); pos != NULL;) {
\t\tCUpDownClient *cur_client = list.GetNext(pos);
\t\tif (md4equ(cur_client->GetUserHash(), clienthash)) {
\t\t\t// Warm/refresh the index when a client acquired its hash after AddClient.
\t\t\tconst_cast<CClientList*>(this)->m_index.UpdateClient(cur_client, cur_client->GetUserHash(),
\t\t\t\tcur_client->GetConnectIP(), cur_client->GetUserPort(), cur_client->GetUDPPort(), cur_client->GetKadPort());
\t\t\tif ((dwIP == 0 || dwIP == cur_client->GetConnectIP()) && (nTCPPort == 0 || nTCPPort == cur_client->GetUserPort()))
\t\t\t\treturn cur_client;
\t\t\tif (pFound == NULL)
\t\t\t\tpFound = cur_client;
\t\t}
\t}
\treturn pFound;
}'''
    if "m_index.FindByUserHash(clienthash" not in text:
        text, count = user_pattern.subn(user_replacement, text, count=1)
        if count != 1:
            raise RuntimeError("Unable to patch FindClientByUserHash")

    save(path, text)


def patch_download_queue_h() -> None:
    path = SRC / "DownloadQueue.h"
    text = load(path)
    text = insert_after(text, '#include "ring.h"\n', '#include "DownloadIndex.h"\n', path)
    text = insert_before(
        text,
        '\tCTypedPtrList<CPtrList, CPartFile*> filelist;\n',
        '\t// Hash/Kad lookup index; the MFC list remains canonical during migration.\n'
        '\tmutable CDownloadIndex m_index;\n',
        path,
    )
    save(path, text)


def patch_download_queue_cpp() -> None:
    path = SRC / "DownloadQueue.cpp"
    text = load(path)
    text = insert_after(text, '#include "Log.h"\n', '#include "EmuleNextRuntime.h"\n', path)

    # Every loaded/new part file enters the index and historical file store.
    # Guard the pair as a unit so a second integrator run is byte-identical.
    if 'm_index.RegisterFile(toadd, toadd->GetFileHash()' not in text:
        text = text.replace(
            '\t\t\t\tfilelist.AddTail(toadd); // to download queue\n',
            '\t\t\t\tfilelist.AddTail(toadd); // to download queue\n'
            '\t\t\t\tm_index.RegisterFile(toadd, toadd->GetFileHash(), toadd->GetKadFileSearchID());\n'
            '\t\t\t\ttheEmuleNext.RecordFileSeen(toadd->GetFileHash(), toadd->GetFileSize(), toadd->GetFileName());\n'
        )
        text = text.replace(
            '\t\t\t\t\tfilelist.AddTail(toadd);\t\t\t// to download queue\n',
            '\t\t\t\t\tfilelist.AddTail(toadd);\t\t\t// to download queue\n'
            '\t\t\t\t\tm_index.RegisterFile(toadd, toadd->GetFileHash(), toadd->GetKadFileSearchID());\n'
            '\t\t\t\t\ttheEmuleNext.RecordFileSeen(toadd->GetFileHash(), toadd->GetFileSize(), toadd->GetFileName());\n'
        )

    add_anchor = '\tfilelist.AddTail(newfile);\n'
    if 'm_index.RegisterFile(newfile, newfile->GetFileHash()' not in text:
        require(text, add_anchor, path)
        text = text.replace(
            add_anchor,
            add_anchor
            + '\tm_index.RegisterFile(newfile, newfile->GetFileHash(), newfile->GetKadFileSearchID());\n'
            + '\ttheEmuleNext.RecordFileSeen(newfile->GetFileHash(), newfile->GetFileSize(), newfile->GetFileName());\n',
            1,
        )

    # A recovered duplicate may be removed before normal RemoveFile is called.
    duplicate_anchor = '\t\t\t\t\tif (pos)\n\t\t\t\t\t\tfilelist.RemoveAt(pos);\n'
    if 'm_index.UnregisterFile(afile);' not in text:
        require(text, duplicate_anchor, path)
        text = text.replace(
            duplicate_anchor,
            '\t\t\t\t\tif (pos) {\n'
            '\t\t\t\t\t\tm_index.UnregisterFile(afile);\n'
            '\t\t\t\t\t\tfilelist.RemoveAt(pos);\n'
            '\t\t\t\t\t}\n',
            1,
        )

    remove_anchor = '\tPOSITION pos = filelist.Find(toremove);\n\tif (pos != NULL)\n\t\tfilelist.RemoveAt(pos);\n'
    if 'm_index.UnregisterFile(toremove);' not in text:
        require(text, remove_anchor, path)
        text = text.replace(
            remove_anchor,
            '\tPOSITION pos = filelist.Find(toremove);\n'
            '\tif (pos != NULL) {\n'
            '\t\tm_index.UnregisterFile(toremove);\n'
            '\t\tfilelist.RemoveAt(pos);\n'
            '\t}\n',
            1,
        )

    get_by_id_pattern = re.compile(
        r'CPartFile\* CDownloadQueue::GetFileByID\(const uchar \*filehash\) const\n\{.*?\n\}',
        re.S,
    )
    get_by_id = '''CPartFile* CDownloadQueue::GetFileByID(const uchar *filehash) const
{
\tCPartFile *indexed = m_index.FindByHash(filehash);
\tif (indexed != NULL)
\t\treturn indexed;

\t// Compatibility fallback also warms files loaded before the index was
\t// introduced. Once migration telemetry shows no fallbacks this scan can go.
\tfor (POSITION pos = filelist.GetHeadPosition(); pos != NULL;) {
\t\tCPartFile *cur_file = filelist.GetNext(pos);
\t\tif (md4equ(filehash, cur_file->GetFileHash())) {
\t\t\tm_index.RegisterFile(cur_file, cur_file->GetFileHash(), cur_file->GetKadFileSearchID());
\t\t\treturn cur_file;
\t\t}
\t}
\treturn NULL;
}'''
    if "m_index.FindByHash(filehash)" not in text:
        text, count = get_by_id_pattern.subn(get_by_id, text, count=1)
        if count != 1:
            raise RuntimeError("Unable to patch GetFileByID")

    get_by_kad_pattern = re.compile(
        r'CPartFile\* CDownloadQueue::GetFileByKadFileSearchID\(uint32 id\) const\n\{.*?\n\}',
        re.S,
    )
    get_by_kad = '''CPartFile* CDownloadQueue::GetFileByKadFileSearchID(uint32 id) const
{
\tCPartFile *indexed = m_index.FindByKadSearchId(id);
\tif (indexed != NULL)
\t\treturn indexed;

\tfor (POSITION pos = filelist.GetHeadPosition(); pos != NULL;) {
\t\tCPartFile *cur_file = filelist.GetNext(pos);
\t\tif (id == cur_file->GetKadFileSearchID()) {
\t\t\tm_index.UpdateKadSearchId(cur_file, id);
\t\t\treturn cur_file;
\t\t}
\t}
\treturn NULL;
}'''
    if "m_index.FindByKadSearchId(id)" not in text:
        text, count = get_by_kad_pattern.subn(get_by_kad, text, count=1)
        if count != 1:
            raise RuntimeError("Unable to patch GetFileByKadFileSearchID")

    save(path, text)


def validate_required_source() -> None:
    # v0.72a is an overlay-style branch. Surface packaging problems early.
    required = [
        SRC / "emule.vcxproj",
        SRC / "Emule.cpp",
        SRC / "ClientList.cpp",
        SRC / "ClientList.h",
        SRC / "DownloadQueue.cpp",
        SRC / "DownloadQueue.h",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        raise RuntimeError("Missing required v0.72a source files: " + ", ".join(missing))

    # Case-sensitive CI catches this even though Windows would hide the naming
    # issue. The current upstream overlay references UpDownClient.h but does not
    # ship it; bootstrap-source.py is responsible for compatibility restoration.
    if not (SRC / "UpDownClient.h").exists() and not (SRC / "updownclient.h").exists():
        print("WARNING: srchybrid/UpDownClient.h is absent; run bootstrap-source.py before compiling", file=sys.stderr)


def main() -> int:
    validate_required_source()
    for name in CPP_FILES + HEADER_FILES:
        if not (SRC / name).exists():
            raise RuntimeError(f"eMule Next source not found: srchybrid/{name}")

    patch_vcxproj()
    patch_emule_cpp()
    patch_client_list_h()
    patch_client_list_cpp()
    patch_download_queue_h()
    patch_download_queue_cpp()
    print("eMule Next legacy integration complete")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise


