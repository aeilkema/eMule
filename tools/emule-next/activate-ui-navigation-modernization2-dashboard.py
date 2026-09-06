#!/usr/bin/env python3
"""Apply UI 2 shared styling to the Dashboard without SearchResults coupling."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
CPP = SRC / "EmuleNextDashboardWnd.cpp"


def read(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def write(path: pathlib.Path, text: str, enc: str) -> None:
    path.write_bytes(text.encode(enc))


def main() -> int:
    if not CPP.exists():
        raise SystemExit("UI2 Dashboard: source missing")
    text, enc = read(CPP)

    helper = '#include "EmuleNextWorkspaceUi.h"'
    if helper not in text:
        anchor = '#include "EmuleNextTheme.h"'
        if anchor not in text:
            raise SystemExit("UI2 Dashboard: theme include missing")
        text = text.replace(anchor, anchor + "\n" + helper, 1)

    if "CEmuleNextWorkspaceUi::StyleList(m_downloads);" not in text:
        anchor = "    m_downloads.SetExtendedStyle(LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_GRIDLINES);"
        if anchor not in text:
            raise SystemExit("UI2 Dashboard: list-style anchor missing")
        text = text.replace(anchor, anchor + "\n    CEmuleNextWorkspaceUi::StyleList(m_downloads);", 1)

    function_start = text.find("BOOL CEmuleNextDashboardWnd::PreTranslateMessage(MSG* message)")
    if function_start < 0:
        raise SystemExit("UI2 Dashboard: keyboard handler missing")
    function_tail = text[function_start:function_start + 900]
    if "message->wParam == VK_F5" not in function_tail:
        anchor = "BOOL CEmuleNextDashboardWnd::PreTranslateMessage(MSG* message)\n{\n"
        if anchor not in text:
            raise SystemExit("UI2 Dashboard: keyboard opening missing")
        addition = "    if (message != NULL && message->message == WM_KEYDOWN && message->wParam == VK_F5) {\n        OnRefreshNow();\n        return TRUE;\n    }\n"
        text = text.replace(anchor, anchor + addition, 1)

    for old, new in {
        "const int margin = CEmuleNextUiMetrics::Scale(m_hWnd, 8);":
            "const int margin = CEmuleNextWorkspaceUi::Margin(m_hWnd);",
        "const int gap = CEmuleNextUiMetrics::Scale(m_hWnd, 5);":
            "const int gap = CEmuleNextWorkspaceUi::Gap(m_hWnd);",
        "const int actionHeight = CEmuleNextUiMetrics::Scale(m_hWnd, 27);":
            "const int actionHeight = CEmuleNextWorkspaceUi::ActionHeight(m_hWnd);",
    }.items():
        text = text.replace(old, new)

    write(CPP, text, enc)
    print("eMule Next Dashboard shared UI 2 styling materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
