#!/usr/bin/env python3
"""Final compile/runtime hardening for the materialized Known Users 2.0 view.

This is deliberately strict: every compatibility rewrite is performed against
an exact complete source line, never a substring. A fully materialized tree is
a no-op. A partially matching/unknown tree fails before compilation.
"""
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


FINAL_MARKERS = (
    "void CKnownUsersWnd::SaveViewState()\n",
    'if (seconds >= 3600) value.Format(_T("%I64uh %02I64um"), seconds / 3600, (seconds % 3600) / 60);',
    'else if (seconds >= 60) value.Format(_T("%I64um %02I64us"), seconds / 60, seconds % 60);',
    'else value.Format(_T("%I64us"), seconds);',
    '#include "resource.h"\n#include "InputBox.h"',
)

LEGACY_MARKERS = (
    "void CKnownUsersWnd::SaveViewState() const\n",
    'if (seconds >= 3600) value.Format(_T("%lluh %02llum"), seconds / 3600, (seconds % 3600) / 60);',
    'else if (seconds >= 60) value.Format(_T("%llum %02llus"), seconds / 60, seconds % 60);',
    'else value.Format(_T("%llus"), seconds);',
)


def final_window_state(text: str) -> bool:
    return all(marker in text for marker in FINAL_MARKERS) and not any(marker in text for marker in LEGACY_MARKERS)


def replace_exact_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Known Users 2 hardening expected exactly one {label} anchor, found {count}")
    return text.replace(old, new, 1)


def patch_window() -> None:
    path = SRC / "KnownUsersWnd.cpp"
    text, newline = load(path)

    if final_window_state(text):
        print("eMule Next Known Users 2.0 window hardening already materialized")
        return

    text = replace_exact_once(
        text,
        "void CKnownUsersWnd::SaveViewState() const\n",
        "void CKnownUsersWnd::SaveViewState()\n",
        "SaveViewState signature",
    )
    text = replace_exact_once(
        text,
        'if (seconds >= 3600) value.Format(_T("%lluh %02llum"), seconds / 3600, (seconds % 3600) / 60);',
        'if (seconds >= 3600) value.Format(_T("%I64uh %02I64um"), seconds / 3600, (seconds % 3600) / 60);',
        "hours/minutes format",
    )
    text = replace_exact_once(
        text,
        'else if (seconds >= 60) value.Format(_T("%llum %02llus"), seconds / 60, seconds % 60);',
        'else if (seconds >= 60) value.Format(_T("%I64um %02I64us"), seconds / 60, seconds % 60);',
        "minutes/seconds format",
    )
    text = replace_exact_once(
        text,
        'else value.Format(_T("%llus"), seconds);',
        'else value.Format(_T("%I64us"), seconds);',
        "seconds format",
    )

    if not final_window_state(text):
        missing = [marker for marker in FINAL_MARKERS if marker not in text]
        stale = [marker for marker in LEGACY_MARKERS if marker in text]
        raise RuntimeError(f"Known Users 2 final window contract incomplete; missing={missing!r}; stale={stale!r}")

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
    if new in text:
        return
    text = replace_exact_once(text, old, new, "live peer metadata")
    save(path, text, newline)


def main() -> int:
    patch_window()
    patch_live_peer_metadata()
    print("eMule Next Known Users 2.0 hardening active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
