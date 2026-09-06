#!/usr/bin/env python3
'''Scope VS18 C4191 suppression to legacy MFC message-map macro tables only.'''
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"

def load(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes(); crlf = raw.count(b"\r\n"); lf = raw.count(b"\n") - crlf
    nl = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n"), nl

def save(path: pathlib.Path, text: str, nl: str) -> None:
    if nl != "\n": text = text.replace("\n", nl)
    path.write_bytes(text.encode("latin-1"))

def main() -> int:
    files = (
        "ChatSelector.cpp", "ChatWnd.cpp", "ClientListCtrl.cpp", "DownloadClientsCtrl.cpp",
        "DownloadListCtrl.cpp", "EmuleDlg.cpp", "FriendListCtrl.cpp", "SearchResultsWnd.cpp",
        "SharedFilesCtrl.cpp",
    )
    for name in files:
        path = SRC / name
        text, nl = load(path)
        if "#pragma warning(disable:4191)\nBEGIN_MESSAGE_MAP" not in text:
            begin = text.find("BEGIN_MESSAGE_MAP(")
            end = text.find("END_MESSAGE_MAP()", begin)
            if begin < 0 or end < 0: raise SystemExit(f"MFC warning cleanup: message map missing in {name}")
            text = text[:begin] + "#pragma warning(push)\n#pragma warning(disable:4191)\n" + text[begin:]
            end = text.find("END_MESSAGE_MAP()", begin) + len("END_MESSAGE_MAP()")
            text = text[:end] + "\n#pragma warning(pop)" + text[end:]
            save(path, text, nl)
    print("Preview 2 MFC message-map warning cleanup materialized"); return 0

if __name__ == "__main__": raise SystemExit(main())
