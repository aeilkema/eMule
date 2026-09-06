#!/usr/bin/env python3
'''Scope VS18 C4191 suppression to MFC message-map macro tables only.'''
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def load(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes(); crlf = raw.count(b"\r\n"); lf = raw.count(b"\n") - crlf
    nl = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n"), nl


def save(path: pathlib.Path, text: str, nl: str) -> None:
    if nl != "\n": text = text.replace("\n", nl)
    path.write_bytes(text.encode("latin-1"))


def wrap_all_message_maps(text: str) -> str:
    guarded = re.compile(
        r"#pragma warning\(push\)\n#pragma warning\(disable:4191\)\n"
        r"(BEGIN_MESSAGE_MAP\(.*?END_MESSAGE_MAP\(\))\n#pragma warning\(pop\)",
        re.S,
    )
    text = guarded.sub(lambda m: m.group(1), text)
    pattern = re.compile(r"BEGIN_MESSAGE_MAP\(.*?END_MESSAGE_MAP\(\)", re.S)
    return pattern.sub(
        lambda m: "#pragma warning(push)\n#pragma warning(disable:4191)\n"
        + m.group(0) + "\n#pragma warning(pop)",
        text,
    )


def main() -> int:
    files = (
        "ChatSelector.cpp", "ChatWnd.cpp", "ClientListCtrl.cpp", "CollectionCreateDialog.cpp",
        "CollectionViewDialog.cpp", "DownloadClientsCtrl.cpp", "DownloadListCtrl.cpp", "EmuleDlg.cpp",
        "FriendListCtrl.cpp", "SearchResultsWnd.cpp", "SharedFilesCtrl.cpp",
    )
    for name in files:
        path = SRC / name
        text, nl = load(path)
        if "BEGIN_MESSAGE_MAP(" not in text:
            raise SystemExit(f"MFC warning cleanup: message map missing in {name}")
        text = wrap_all_message_maps(text)
        save(path, text, nl)
    print("Preview 2 MFC message-map warning cleanup materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
