#!/usr/bin/env python3
"""Activate eMule Next user-configurable runtime settings."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def load(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    newline = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n"), newline


def save(path: pathlib.Path, text: str, newline: str) -> None:
    if newline != "\n":
        text = text.replace("\n", newline)
    path.write_bytes(text.encode("latin-1"))


def insert_after(text: str, anchor: str, addition: str, path: pathlib.Path) -> str:
    if addition.strip() in text:
        return text
    if anchor not in text:
        raise RuntimeError(f"Settings anchor not found in {path}: {anchor!r}")
    return text.replace(anchor, anchor + addition, 1)


def patch_project() -> None:
    path = SRC / "emule.vcxproj"
    text, newline = load(path)
    anchor = '    <ClCompile Include="EmuleNextDatabase.cpp" />\n'
    for name in ("EmuleNextSettingsWnd.cpp",):
        if (SRC / name).exists() and f'Include="{name}"' not in text:
            if anchor not in text:
                raise RuntimeError("Unable to add eMule Next settings source")
            text = text.replace(anchor, anchor + f'    <ClCompile Include="{name}" />\n', 1)
    save(path, text, newline)


def patch_client_list() -> None:
    path = SRC / "ClientList.cpp"
    text, newline = load(path)

    constructor_anchor = '\tm_peerShareScanner.SetTransport(this);\n'
    constructor_addition = (
        '\tm_peerShareScanner.SetEnabled(theApp.GetProfileInt(_T("eMule Next"), _T("PeerShareDiscovery"), 1) != 0);\n'
        '\tint nextMaxConcurrent = theApp.GetProfileInt(_T("eMule Next"), _T("PeerShareMaxConcurrent"), 2);\n'
        '\tnextMaxConcurrent = max(1, min(8, nextMaxConcurrent));\n'
        '\tm_peerShareScanner.SetMaxConcurrent(static_cast<uint32>(nextMaxConcurrent));\n'
    )
    text = insert_after(text, constructor_anchor, constructor_addition, path)

    methods_anchor = 'CClientList::~CClientList()\n'
    methods = (
        'void CClientList::SetPeerShareDiscoveryEnabled(bool enabled)\n'
        '{\n'
        '\tm_peerShareScanner.SetEnabled(enabled);\n'
        '\ttheApp.WriteProfileInt(_T("eMule Next"), _T("PeerShareDiscovery"), enabled ? 1 : 0);\n'
        '}\n\n'
        'void CClientList::SetPeerShareMaxConcurrent(uint32 maxConcurrent)\n'
        '{\n'
        '\tmaxConcurrent = max<uint32>(1, min<uint32>(8, maxConcurrent));\n'
        '\tm_peerShareScanner.SetMaxConcurrent(maxConcurrent);\n'
        '\ttheApp.WriteProfileInt(_T("eMule Next"), _T("PeerShareMaxConcurrent"), static_cast<int>(maxConcurrent));\n'
        '}\n\n'
    )
    if methods.strip() not in text:
        if methods_anchor not in text:
            raise RuntimeError("Unable to add peer discovery settings methods")
        text = text.replace(methods_anchor, methods + methods_anchor, 1)

    save(path, text, newline)


def main() -> int:
    patch_project()
    patch_client_list()
    print("eMule Next settings activation complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
