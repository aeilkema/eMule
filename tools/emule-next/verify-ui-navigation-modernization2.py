#!/usr/bin/env python3
"""Final-state completion/compile gate for UI / Navigation Modernization 2.0."""
from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
HERE = pathlib.Path(__file__).resolve().parent


def read(name: str) -> str:
    path = SRC / name
    if not path.exists():
        raise SystemExit(f"UI2 verification: missing {name}")
    return path.read_bytes().decode("latin-1", errors="ignore")


def require(source: str, marker: str, label: str) -> None:
    if marker not in source:
        raise SystemExit(f"UI2 verification: missing {label}: {marker}")


def parse_script(name: str) -> None:
    path = HERE / name
    try:
        ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    except SyntaxError as exc:
        raise SystemExit(f"UI2 verification: {name} syntax error line {exc.lineno}: {exc.msg}")


def main() -> int:
    # Catch Python mistakes before C++ compilation can begin.
    parse_script("activate-ui-navigation-modernization2.py")
    parse_script("activate-ui-navigation-modernization2-layout.py")
    parse_script("activate-ui-navigation-modernization2-dashboard.py")

    helper = read("EmuleNextWorkspaceUi.h")
    search_h, search_cpp = read("Search2Wnd.h"), read("Search2Wnd.cpp")
    lib_h, lib_cpp = read("FileLibraryWnd.h"), read("FileLibraryWnd.cpp")
    known_h, known_cpp = read("KnownUsersWnd.h"), read("KnownUsersWnd.cpp")
    settings_h, settings_cpp = read("EmuleNextSettingsWnd.h"), read("EmuleNextSettingsWnd.cpp")
    dashboard = read("EmuleNextDashboardWnd.cpp")
    host = read("SearchResultsWnd.cpp")

    for marker, label in (
        ("EMULENEXT_WORKSPACE_UI2", "workspace helper marker"),
        ("CEmuleNextUiMetrics::Scale", "shared DPI scaling"),
        ("StyleList(CListCtrl& list)", "shared list styling"),
        ("SelectAllBounded(CListCtrl& list, int maximum = 2000)", "bounded multi-select shortcut"),
        ("CEmuleNextTheme::IsDarkMode()", "dark-mode list styling"),
        ("FocusEdit(CEdit& edit)", "shared search focus helper"),
        ("Margin(HWND wnd)", "shared workspace margin"),
        ("Gap(HWND wnd)", "shared workspace gap"),
        ("ActionHeight(HWND wnd)", "shared action height"),
    ):
        require(helper, marker, label)

    for header, cpp, cls, search_control, label in (
        (search_h, search_cpp, "CSearch2Wnd", "m_query", "Search"),
        (lib_h, lib_cpp, "CFileLibraryWnd", "m_textFilter", "Library"),
        (known_h, known_cpp, "CKnownUsersWnd", "m_search", "Known Users"),
    ):
        require(header, "virtual BOOL PreTranslateMessage(MSG* message);", f"{label} keyboard declaration")
        require(cpp, f"BOOL {cls}::PreTranslateMessage(MSG* message)", f"{label} keyboard implementation")
        require(cpp, '#include "EmuleNextWorkspaceUi.h"', f"{label} workspace helper include")
        require(cpp, "CEmuleNextWorkspaceUi::IsCtrlKey(message, 'F')", f"{label} Ctrl+F")
        require(cpp, f"CEmuleNextWorkspaceUi::FocusEdit({search_control})", f"{label} focus behavior")
        require(cpp, "CEmuleNextWorkspaceUi::StyleList", f"{label} shared list styling")
        require(cpp, "CEmuleNextWorkspaceUi::Margin(m_hWnd)", f"{label} shared spacing")

    require(search_cpp, "CEmuleNextWorkspaceUi::SelectAllBounded(m_results)", "Search bounded Ctrl+A")
    require(search_cpp, "message->wParam == VK_RETURN", "Search Enter action")
    require(lib_cpp, "CEmuleNextWorkspaceUi::SelectAllBounded(m_results)", "Library bounded Ctrl+A")
    require(lib_cpp, "message->wParam == VK_F5", "Library F5 refresh")
    require(known_cpp, "message->wParam == VK_F5", "Known Users F5 refresh")

    require(settings_h, "virtual BOOL PreTranslateMessage(MSG* message);", "Settings keyboard declaration")
    require(settings_cpp, "BOOL CEmuleNextSettingsWnd::PreTranslateMessage(MSG* message)", "Settings keyboard implementation")
    require(settings_cpp, "CEmuleNextWorkspaceUi::IsCtrlKey(message, VK_RETURN)", "Settings Ctrl+Enter apply")
    require(settings_cpp, "OnApplyClicked();", "Settings apply routing")
    require(settings_cpp, '#include "EmuleNextWorkspaceUi.h"', "Settings workspace helper include")

    for marker, label in (
        ('_T("eMule Next Workspace")', "workspace persistence section"),
        ('_T("ActiveView")', "workspace persistence key"),
        ("preferredNextView", "last workspace restore"),
        ("nextSelectedId", "workspace selection persistence"),
        ("IsEmuleNextPersistentView(nextSelectedId)", "persistent-view guard"),
        ('strSpecialTitle = _T("Known Users")', "Known Users navigation label"),
        ('strSpecialTitle = _T("Search")', "Search navigation label"),
        ('strSpecialTitle = _T("Library")', "Library navigation label"),
        ('strSpecialTitle = _T("Settings")', "Settings navigation label"),
        ("searchselect.SetPadding(CSize(CEmuleNextUiMetrics::Scale", "DPI-aware workspace tabs"),
    ):
        require(host, marker, label)

    for marker, label in (
        ('#include "EmuleNextWorkspaceUi.h"', "Dashboard workspace helper include"),
        ("CEmuleNextWorkspaceUi::StyleList(m_downloads)", "Dashboard shared list styling"),
        ("CEmuleNextWorkspaceUi::Margin(m_hWnd)", "Dashboard shared spacing"),
        ("CEmuleNextWorkspaceUi::ActionHeight(m_hWnd)", "Dashboard shared action height"),
        ("message->wParam == VK_F5", "Dashboard F5 refresh"),
        ("OnRefreshNow();", "Dashboard refresh route"),
    ):
        require(dashboard, marker, label)

    # Modernization must not create new DB/filesystem work in the view layer.
    for name, source in (
        ("Search2Wnd.cpp", search_cpp),
        ("FileLibraryWnd.cpp", lib_cpp),
        ("KnownUsersWnd.cpp", known_cpp),
        ("EmuleNextSettingsWnd.cpp", settings_cpp),
    ):
        if "sqlite3_" in source or "winsqlite3.h" in source.lower():
            raise SystemExit(f"UI2 verification: direct SQLite leaked into {name}")
    if "GetFileAttributesW" in search_cpp or "GetFileAttributesW" in known_cpp or "GetFileAttributesW" in settings_cpp:
        raise SystemExit("UI2 verification: filesystem work leaked into non-Library GUI")

    # Keep the helper header-only: no new linker unit and therefore no project
    # entry/include-order risk from this modernization tranche.
    project = read("emule.vcxproj")
    if "EmuleNextWorkspaceUi.cpp" in project:
        raise SystemExit("UI2 verification: workspace helper unexpectedly gained a linker unit")

    print("eMule Next UI / Navigation Modernization 2.0 verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
