#!/usr/bin/env python3
"""Harmonize final Next workspace spacing, navigation tabs and Dashboard styling."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


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


def add_helper_include(text: str) -> str:
    marker = '#include "EmuleNextWorkspaceUi.h"'
    if marker in text:
        return text
    anchor = '#include "EmuleNextTheme.h"'
    if anchor not in text:
        raise SystemExit("UI2 layout: theme include missing")
    return text.replace(anchor, anchor + "\n" + marker, 1)


def harmonize(path: pathlib.Path) -> None:
    text, enc = read(path)
    text = add_helper_include(text)
    replacements = {
        "const int margin = CEmuleNextUiMetrics::Scale(m_hWnd, 12);":
            "const int margin = CEmuleNextWorkspaceUi::Margin(m_hWnd);",
        "const int margin = CEmuleNextUiMetrics::Scale(m_hWnd, 8);":
            "const int margin = CEmuleNextWorkspaceUi::Margin(m_hWnd);",
        "const int gap = CEmuleNextUiMetrics::Scale(m_hWnd, 6);":
            "const int gap = CEmuleNextWorkspaceUi::Gap(m_hWnd);",
        "const int gap = CEmuleNextUiMetrics::Scale(m_hWnd, 5);":
            "const int gap = CEmuleNextWorkspaceUi::Gap(m_hWnd);",
        "const int actionHeight = CEmuleNextUiMetrics::Scale(m_hWnd, 30);":
            "const int actionHeight = CEmuleNextWorkspaceUi::ActionHeight(m_hWnd);",
        "const int actionHeight = CEmuleNextUiMetrics::Scale(m_hWnd, 27);":
            "const int actionHeight = CEmuleNextWorkspaceUi::ActionHeight(m_hWnd);",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    write(path, text, enc)


def patch_dashboard() -> None:
    path = SRC / "EmuleNextDashboardWnd.cpp"
    text, enc = read(path)
    text = add_helper_include(text)
    if "CEmuleNextWorkspaceUi::StyleList(m_downloads);" not in text:
        anchor = "    m_downloads.SetExtendedStyle(LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_GRIDLINES);"
        if anchor not in text:
            raise SystemExit("UI2 layout: Dashboard list-style anchor missing")
        text = text.replace(anchor, anchor + "\n    CEmuleNextWorkspaceUi::StyleList(m_downloads);", 1)

    if "message->wParam == VK_F5" not in text[text.find("BOOL CEmuleNextDashboardWnd::PreTranslateMessage"):]:
        anchor = '''BOOL CEmuleNextDashboardWnd::PreTranslateMessage(MSG* message)
{
'''
        if anchor not in text:
            raise SystemExit("UI2 layout: Dashboard keyboard anchor missing")
        addition = '''    if (message != NULL && message->message == WM_KEYDOWN && message->wParam == VK_F5) {
        OnRefreshNow();
        return TRUE;
    }
'''
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
    write(path, text, enc)


def patch_navigation_tabs() -> None:
    path = SRC / "SearchResultsWnd.cpp"
    text, enc = read(path)
    text = add_helper_include(text)
    old = "searchselect.SetPadding(CSize(12, 3));"
    new = "searchselect.SetPadding(CSize(CEmuleNextUiMetrics::Scale(m_hWnd, 12), CEmuleNextUiMetrics::Scale(m_hWnd, 3)));"
    text = text.replace(old, new)
    write(path, text, enc)


def main() -> int:
    for name in ("Search2Wnd.cpp", "FileLibraryWnd.cpp", "KnownUsersWnd.cpp", "EmuleNextSettingsWnd.cpp"):
        path = SRC / name
        if not path.exists():
            raise SystemExit(f"UI2 layout: missing {name}")
        harmonize(path)
    patch_dashboard()
    patch_navigation_tabs()
    print("eMule Next UI 2 shared spacing, navigation tabs and Dashboard styling materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
