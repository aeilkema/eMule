#!/usr/bin/env python3
"""Small compile-safety normalization for the Transfers Dashboard activation."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "TransferWnd.cpp"


def main() -> int:
    raw = PATH.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    newline = "\r\n" if crlf >= lf and crlf else "\n"
    text = raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n")

    old = '''\tif (!m_nextDashboard.Create(this))\n\t\tAddDebugLogLine(false, _T("eMule Next Dashboard creation failed"));\n\tm_nextDashboard.ShowWindow(SW_HIDE);\n'''
    new = '''\tVERIFY(m_nextDashboard.Create(this));\n\tm_nextDashboard.ShowWindow(SW_HIDE);\n'''
    if old in text:
        text = text.replace(old, new, 1)

    # RemoveAnchor on a newly created dynamic child is unnecessary. AddAnchor
    # replaces/establishes its layout rule when the dashboard is first shown.
    text = text.replace('\tRemoveAnchor(m_nextDashboard);\n\tAddAnchor(m_nextDashboard, TOP_LEFT, BOTTOM_RIGHT);\n',
                        '\tAddAnchor(m_nextDashboard, TOP_LEFT, BOTTOM_RIGHT);\n', 1)

    if newline != "\n":
        text = text.replace("\n", newline)
    PATH.write_bytes(text.encode("latin-1"))
    print("eMule Next Dashboard compile-safety normalization active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
