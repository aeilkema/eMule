#!/usr/bin/env python3
"""Persist real download-session lifecycle events for eMule Next Intelligence.

The legacy CUpDownClient::SetDownloadState transition is the authoritative
session boundary. Recording there avoids GUI polling and keeps the hot path
non-blocking because CEmuleNextDatabase::RecordTransfer only queues an event.
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
    _NEWLINES[path] = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n")


def save(path: pathlib.Path, text: str) -> None:
    newline = _NEWLINES.get(path, "\n")
    if newline != "\n":
        text = text.replace("\n", newline)
    path.write_bytes(text.encode("latin-1"))


def insert_after(text: str, anchor: str, addition: str, path: pathlib.Path) -> str:
    if addition.strip() in text:
        return text
    if anchor not in text:
        raise RuntimeError(f"Required lifecycle anchor not found in {path}: {anchor!r}")
    return text.replace(anchor, anchor + addition, 1)


def patch_download_client() -> None:
    path = SRC / "DownloadClient.cpp"
    text = load(path)
    text = insert_after(text, '#include "Log.h"\n', '#include "EmuleNextRuntime.h"\n#include <time.h>\n', path)

    anchor = '''\t\t\tResetSessionDown();\n'''
    addition = '''\t\t\t// eMule Next Download Intelligence: persist the completed session at\n\t\t\t// the authoritative lifecycle boundary, before legacy counters reset.\n\t\t\t// RecordTransfer is queue-only and does not perform SQLite I/O here.\n\t\t\tif (m_reqfile != NULL && HasValidHash() && theEmuleNext.IsRunning()) {\n\t\t\t\tEmuleNextTransferObservation observation;\n\t\t\t\tobservation.peerHash = EmuleNextHash16(GetUserHash());\n\t\t\t\tobservation.fileHash = EmuleNextHash16(m_reqfile->GetFileHash());\n\t\t\t\tobservation.fileSize = m_reqfile->GetFileSize();\n\t\t\t\tobservation.bytesTransferred = GetSessionDown();\n\t\t\t\tconst uint64 durationMs = GetDownloadTicks(false);\n\t\t\t\tobservation.averageBytesPerSecond = durationMs > 0\n\t\t\t\t\t? static_cast<uint32>(min<uint64>((observation.bytesTransferred * 1000ui64) / durationMs, _UI32_MAX))\n\t\t\t\t\t: 0;\n\t\t\t\tobservation.successful = m_bDownloadedAnyBytes && nNewState != DS_ERROR;\n\t\t\t\tobservation.direction = L"download";\n\t\t\t\tobservation.result = pszReason != NULL ? CStringW(pszReason)\n\t\t\t\t\t: (observation.successful ? CStringW(L"completed-session") : CStringW(L"empty-session"));\n\t\t\t\tobservation.finishedAt = static_cast<uint64>(::time(NULL));\n\t\t\t\tconst uint64 durationSeconds = durationMs / 1000ui64;\n\t\t\t\tobservation.startedAt = observation.finishedAt > durationSeconds\n\t\t\t\t\t? observation.finishedAt - durationSeconds : observation.finishedAt;\n\t\t\t\ttheEmuleNext.Database().RecordTransfer(observation);\n\t\t\t}\n\n'''
    if 'eMule Next Download Intelligence: persist the completed session' not in text:
        if anchor not in text:
            raise RuntimeError("SetDownloadState ResetSessionDown anchor not found")
        text = text.replace(anchor, addition + anchor, 1)
    save(path, text)


def main() -> int:
    path = SRC / "DownloadClient.cpp"
    if not path.exists():
        raise RuntimeError(f"Missing download lifecycle source: {path}")
    patch_download_client()
    print("eMule Next download transfer lifecycle active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
