#!/usr/bin/env python3
'''Final-state gate for complete Settings coverage and Preview 2 theme coverage.'''
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def read(name: str) -> str:
    path = SRC / name
    if not path.exists():
        raise SystemExit(f"Preview2 Settings/theme verification: missing {name}")
    return path.read_bytes().decode("latin-1", errors="ignore")


def main() -> int:
    prefs = read("PreferencesDlg.cpp")
    main_cpp = read("EmuleDlg.cpp")
    settings_h = read("EmuleNextSettingsWnd.h")
    settings = read("EmuleNextSettingsWnd.cpp")
    chat_h = read("ChatWnd.h")
    chat = read("ChatWnd.cpp")
    selector_h = read("ChatSelector.h")
    selector = read("ChatSelector.cpp")

    expected_members = [
        "m_wndGeneral", "m_wndDisplay", "m_wndConnection", "m_wndProxy", "m_wndServer",
        "m_wndDirectories", "m_wndFiles", "m_wndNotify", "m_wndStats", "m_wndIRC",
        "m_wndMessages", "m_wndSecurity", "m_wndScheduler", "m_wndWebServer", "m_wndTweaks",
    ]
    add_pages = re.findall(r"AddPage\(&([A-Za-z0-9_]+)\);", prefs)
    production = [name for name in add_pages if name != "m_wndDebug"]
    if production != expected_members:
        raise SystemExit(
            "Preview2 Settings/theme verification: upstream Preferences page set changed; "
            f"expected {expected_members}, found {production}"
        )

    labels = [
        "General", "Display", "Connection", "Proxy", "Server", "Directories", "Files",
        "Notifications", "Statistics", "IRC", "Messages", "Security", "Scheduler",
        "Web Server", "Tweaks",
    ]
    for label in labels:
        marker = f'm_navigation.AddString(_T("{label}"));'
        if marker not in settings:
            raise SystemExit(f"Preview2 Settings/theme verification: Settings navigation missing {label}")

    if "CATEGORY_COUNT" not in settings_h or "CATEGORY_ORIGINAL_GENERAL" not in settings_h:
        raise SystemExit("Preview2 Settings/theme verification: complete category enum missing")
    if "OnOpenOriginalSettingsClicked" not in settings_h or "OnOpenOriginalSettingsClicked" not in settings:
        raise SystemExit("Preview2 Settings/theme verification: original-page routing handler missing")
    if settings.count("ShowPreferences(IDD_") < 15:
        raise SystemExit("Preview2 Settings/theme verification: fewer than 15 direct original-page routes")
    if "Open settings page..." not in settings or "original eMule preference page" not in settings:
        raise SystemExit("Preview2 Settings/theme verification: original-page UX missing")
    if "LBS_NOINTEGRALHEIGHT | WS_VSCROLL" not in settings:
        raise SystemExit("Preview2 Settings/theme verification: complete Settings navigation is not scrollable")
    if "CEmuleNextTheme::ApplyToWindow(theApp.emuledlg != NULL ? theApp.emuledlg->m_hWnd : m_hWnd);" not in settings:
        raise SystemExit("Preview2 Settings/theme verification: Settings does not refresh the complete application theme tree")

    # Every legacy workspace is re-themed when activated; Preferences gets the
    # same recursive theme application after all original property pages exist.
    for marker in (
        "Preview 2: re-apply the active theme to every legacy workspace",
        "CEmuleNextTheme::ApplyToWindow(dlg->m_hWnd);",
    ):
        if marker not in main_cpp:
            raise SystemExit(f"Preview2 Settings/theme verification: legacy workspace routing missing {marker}")
    for marker in (
        "Preview 2 themes the complete original Preferences tree",
        "CEmuleNextTheme::ApplyToWindow(m_hWnd);",
    ):
        if marker not in prefs:
            raise SystemExit(f"Preview2 Settings/theme verification: Preferences theming missing {marker}")

    for marker in (
        "CBrush m_preview2ThemeBrush;",
        "void ApplyPreview2Theme();",
    ):
        if marker not in chat_h:
            raise SystemExit(f"Preview2 Settings/theme verification: Chat theme header missing {marker}")
    if "ApplyPreview2Theme();" not in selector_h:
        raise SystemExit("Preview2 Settings/theme verification: ChatSelector theme refresh API missing")

    for marker in (
        '#include "EmuleNextTheme.h"',
        "ApplyPreview2Theme();",
        "CEmuleNextModernUi::ApplyList(m_FriendListCtrl);",
        "CEmuleNextModernUi::SetExplorerTheme(chatselector.m_hWnd);",
        "chatselector.ApplyPreview2Theme();",
        "CEmuleNextTheme::IsDarkMode()",
        "m_preview2ThemeBrush.GetSafeHandle()",
    ):
        if marker not in chat:
            raise SystemExit(f"Preview2 Settings/theme verification: Chat theme implementation missing {marker}")
    for marker in (
        "void CChatSelector::ApplyPreview2Theme()",
        "SetDfltForegroundColor(CEmuleNextTheme::TextColor())",
        "SetDfltBackgroundColor(CEmuleNextTheme::SurfaceColor())",
        "SetBackgroundColor(FALSE, CEmuleNextTheme::SurfaceColor())",
    ):
        if marker not in selector:
            raise SystemExit(f"Preview2 Settings/theme verification: chat log dark surface missing {marker}")

    print("eMule Next Preview 2 Settings completeness + theme coverage verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
