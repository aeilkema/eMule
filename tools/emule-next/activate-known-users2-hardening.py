#!/usr/bin/env python3
"""Final compile/runtime hardening for the materialized Known Users 2.0 view."""
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


def patch_window() -> None:
    path = SRC / "KnownUsersWnd.cpp"
    text, newline = load(path)
    text = text.replace("void CKnownUsersWnd::SaveViewState() const", "void CKnownUsersWnd::SaveViewState()")
    text = text.replace('_T("%llud")', '_T("%I64ud")')
    text = text.replace('_T("%lluh")', '_T("%I64uh")')
    text = text.replace('_T("%llum")', '_T("%I64um")')
    text = text.replace('_T("%llus")', '_T("%I64us")')
    required = (
        "void CKnownUsersWnd::SaveViewState()",
        '_T("%I64ud")',
        "QueuePeerShareRefresh(hash)",
        "DeleteHistoryWorker",
    )
    for marker in required:
        if marker not in text:
            raise RuntimeError(f"Known Users 2 window hardening lost {marker}")
    save(path, text, newline)


def patch_live_peer_metadata() -> None:
    path = SRC / "ClientList.cpp"
    text, newline = load(path)
    old = (
        "\t\ttheEmuleNext.RecordPeerSeen(toadd->GetUserHash(), toadd->GetUserName(), CString(), CString(),\n"
        "\t\t\ttoadd->GetConnectIP(), toadd->GetUserPort(), toadd->GetUDPPort(), toadd->GetKadPort());"
    )
    new = (
        "\t\ttheEmuleNext.RecordPeerSeen(toadd->GetUserHash(), toadd->GetUserName(), toadd->GetClientSoftVer(), CString(),\n"
        "\t\t\ttoadd->GetConnectIP(), toadd->GetUserPort(), toadd->GetUDPPort(), toadd->GetKadPort());"
    )
    if new not in text:
        if old not in text:
            raise RuntimeError("Known Users 2 live peer metadata anchor missing")
        text = text.replace(old, new, 1)
    save(path, text, newline)


def main() -> int:
    patch_window()
    patch_live_peer_metadata()
    print("eMule Next Known Users 2.0 hardening active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
