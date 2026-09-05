#!/usr/bin/env python3
"""Small compile/UX safety normalization for the Transfers Dashboard activation."""
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

    # Re-establish the resizable anchor when the dynamic Dashboard view is
    # reopened. This avoids duplicate anchor registrations after view switches.
    if '\tAddAnchor(m_nextDashboard, TOP_LEFT, BOTTOM_RIGHT);\n' in text and '\tRemoveAnchor(m_nextDashboard);\n\tAddAnchor(m_nextDashboard, TOP_LEFT, BOTTOM_RIGHT);\n' not in text:
        text = text.replace('\tAddAnchor(m_nextDashboard, TOP_LEFT, BOTTOM_RIGHT);\n',
                            '\tRemoveAnchor(m_nextDashboard);\n\tAddAnchor(m_nextDashboard, TOP_LEFT, BOTTOM_RIGHT);\n', 1)

    # The original activation marker could match SetBtnText and skip the actual
    # dropdown entry. Ensure the drop-down selector always exposes Dashboard.
    dropdown_line = '\tmenu.AppendMenu(MF_STRING | (m_dwShowListIDC == EMULENEXT_DASHBOARD_VIEW ? MF_GRAYED : 0), MP_NEXT_DASHBOARD, _T("eMule Next Dashboard"), _T("DownloadFiles"));\n'
    if dropdown_line not in text:
        anchor = '''\tif (!thePrefs.IsKnownClientListDisabled())\n\t\tmenu.AppendMenu(MF_STRING | (m_dwShowListIDC == IDC_CLIENTLIST ? MF_GRAYED : 0), MP_VIEW1_CLIENTS, GetResString(IDS_CLIENTLIST), _T("ClientsKnown"));\n'''
        if anchor not in text:
            raise RuntimeError("Dashboard dropdown anchor not found")
        text = text.replace(anchor, anchor + '\tmenu.AppendMenu(MF_SEPARATOR);\n' + dropdown_line, 1)

    if newline != "\n":
        text = text.replace("\n", newline)
    PATH.write_bytes(text.encode("latin-1"))
    print("eMule Next Dashboard compile/UX safety normalization active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
