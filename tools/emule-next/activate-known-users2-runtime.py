#!/usr/bin/env python3
"""Expose the existing peer-share scanner safely to Known Users 2.0."""
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


def patch_header() -> None:
    path = SRC / "ClientList.h"
    text, newline = load(path)
    marker = "\tbool\tQueuePeerShareRefresh(const EmuleNextHash16& peerHash);\n"
    if marker not in text:
        anchor = "\tvoid\tOnPeerSharedFileList(const uchar *peerHash, uint32 fileCount, uint64 totalBytes);\n"
        if anchor not in text:
            raise RuntimeError("Known Users 2 runtime header anchor missing")
        addition = (
            "\tbool\tQueuePeerShareRefresh(const EmuleNextHash16& peerHash);\n"
            "\tbool\tGetPeerShareState(const EmuleNextHash16& peerHash, EmuleNextPeerShareState& state) const;\n"
        )
        text = text.replace(anchor, anchor + addition, 1)
    save(path, text, newline)


def patch_cpp() -> None:
    path = SRC / "ClientList.cpp"
    text, newline = load(path)
    if "bool CClientList::QueuePeerShareRefresh(const EmuleNextHash16& peerHash)" not in text:
        anchor = "CClientList::~CClientList()\n{\n\tRemoveAllTrackedClients();\n}\n"
        if anchor not in text:
            raise RuntimeError("Known Users 2 runtime implementation anchor missing")
        addition = '''

bool CClientList::QueuePeerShareRefresh(const EmuleNextHash16& peerHash)
{
\tif (!peerHash.valid || !IsPeerOnline(peerHash))
\t\treturn false;
\tif (!m_peerShareScanner.QueuePeerManual(peerHash))
\t\treturn false;
\tm_peerShareScanner.Tick();
\treturn true;
}

bool CClientList::GetPeerShareState(const EmuleNextHash16& peerHash,
\tEmuleNextPeerShareState& state) const
{
\treturn m_peerShareScanner.GetState(peerHash, state);
}
'''
        text = text.replace(anchor, anchor + addition, 1)
    save(path, text, newline)


def main() -> int:
    patch_header()
    patch_cpp()
    print("eMule Next Known Users 2.0 peer-share runtime bridge active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
