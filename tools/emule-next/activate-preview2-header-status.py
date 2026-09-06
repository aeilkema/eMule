#!/usr/bin/env python3
'''Add live connection and transfer status to the visible Preview 2 header.'''
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
HEADER = SRC / "EmuleDlg.h"
CPP = SRC / "EmuleDlg.cpp"


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


def main() -> int:
    header, hn = load(HEADER)
    cpp, cn = load(CPP)

    if "CStatic m_preview2HeaderStatus;" not in header:
        anchor = "\tCStatic m_preview2Section;\n"
        if anchor not in header:
            raise SystemExit("Preview2 header: section member anchor missing")
        header = header.replace(anchor, anchor + "\tCStatic m_preview2HeaderStatus;\n", 1)
    if "void UpdatePreview2HeaderStatus();" not in header:
        anchor = "\tvoid UpdatePreview2MainSection(int selection);\n"
        if anchor not in header:
            raise SystemExit("Preview2 header: main section helper anchor missing")
        header = header.replace(anchor, anchor + "\tvoid UpdatePreview2HeaderStatus();\n", 1)

    if "m_preview2HeaderStatus.Create(" not in cpp:
        anchor = '''\tif (!m_preview2ConnectButton.Create(_T("Connect"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
\t\tpreview2Empty, this, IDC_EN_PREVIEW2_CONNECT))
\t\treturn FALSE;
'''
        if anchor not in cpp:
            raise SystemExit("Preview2 header: connect creation anchor missing")
        block = '''\tif (!m_preview2HeaderStatus.Create(_T("Starting..."), WS_CHILD | WS_VISIBLE | SS_RIGHT,
\t\tpreview2Empty, this))
\t\treturn FALSE;
'''
        cpp = cpp.replace(anchor, anchor + block, 1)

    if "m_preview2HeaderStatus.SetFont(&m_preview2NormalFont);" not in cpp:
        anchor = "\tm_preview2ConnectButton.SetFont(&m_preview2NormalFont);\n"
        if anchor not in cpp:
            raise SystemExit("Preview2 header: connect font anchor missing")
        cpp = cpp.replace(anchor, anchor + "\tm_preview2HeaderStatus.SetFont(&m_preview2NormalFont);\n", 1)

    if "m_preview2HeaderStatus.MoveWindow" not in cpp:
        anchor = '''\tm_preview2ConnectButton.MoveWindow(rcClient.right - preview2Margin - CEmuleNextModernUi::Scale(m_hWnd, 112),
\t\tCEmuleNextModernUi::Scale(m_hWnd, 14), CEmuleNextModernUi::Scale(m_hWnd, 112),
\t\tCEmuleNextModernUi::ControlHeight(m_hWnd));
'''
        if anchor not in cpp:
            raise SystemExit("Preview2 header: connect layout anchor missing")
        status_layout = '''\tm_preview2HeaderStatus.MoveWindow(
\t\tmax(preview2NavWidth + preview2Margin, rcClient.right - preview2Margin - CEmuleNextModernUi::Scale(m_hWnd, 430)),
\t\tCEmuleNextModernUi::Scale(m_hWnd, 44), CEmuleNextModernUi::Scale(m_hWnd, 410),
\t\tCEmuleNextModernUi::Scale(m_hWnd, 20));
'''
        cpp = cpp.replace(anchor, status_layout + anchor, 1)

    if "AddAnchor(m_preview2HeaderStatus" not in cpp:
        anchor = "\tAddAnchor(m_preview2Section, TOP_LEFT, TOP_RIGHT);\n"
        if anchor not in cpp:
            raise SystemExit("Preview2 header: section anchor contract missing")
        cpp = cpp.replace(anchor, anchor + "\tAddAnchor(m_preview2HeaderStatus, TOP_RIGHT, TOP_RIGHT);\n", 1)

    if "void CemuleDlg::UpdatePreview2HeaderStatus()" not in cpp:
        anchor = "void CemuleDlg::UpdatePreview2MainSection(int selection)\n"
        if anchor not in cpp:
            raise SystemExit("Preview2 header: main section method boundary missing")
        method = r'''void CemuleDlg::UpdatePreview2HeaderStatus()
{
	if (!::IsWindow(m_preview2HeaderStatus.m_hWnd))
		return;
	CString status = GetConnectionStateString();
	const CString rates = GetTransferRateString();
	if (!rates.IsEmpty()) {
		status += _T("   |   ");
		status += rates;
	}
	m_preview2HeaderStatus.SetWindowText(status);
}

'''
        cpp = cpp.replace(anchor, method + anchor, 1)

    if "UpdatePreview2HeaderStatus();\n\tif (::IsWindow(m_preview2ConnectButton.m_hWnd))" not in cpp:
        old = "\tif (::IsWindow(m_preview2ConnectButton.m_hWnd)) {\n"
        pos = cpp.find(old, cpp.find("void CemuleDlg::UpdatePreview2MainSection"))
        if pos < 0:
            raise SystemExit("Preview2 header: section status update anchor missing")
        cpp = cpp[:pos] + "\tUpdatePreview2HeaderStatus();\n" + cpp[pos:]

    # Piggyback on existing legacy refresh paths; do not create another timer.
    for signature in (
        "void CemuleDlg::ShowConnectionState()\n{",
        "void CemuleDlg::ShowTransferRate(bool bForceAll)\n{",
    ):
        start = cpp.find(signature)
        if start < 0:
            raise SystemExit(f"Preview2 header: refresh hook missing {signature.split('(')[0]}")
        body_start = start + len(signature)
        window = cpp[body_start:body_start + 160]
        if "UpdatePreview2HeaderStatus();" not in window:
            cpp = cpp[:body_start] + "\n\tUpdatePreview2HeaderStatus();" + cpp[body_start:]

    for text, marker in ((header, "m_preview2HeaderStatus"), (cpp, "UpdatePreview2HeaderStatus")):
        if marker not in text:
            raise SystemExit("Preview2 header: final status contract missing")

    save(HEADER, header, hn)
    save(CPP, cpp, cn)
    print("eMule Next Preview 2 live header status materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
