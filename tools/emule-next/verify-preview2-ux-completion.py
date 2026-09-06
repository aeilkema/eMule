#!/usr/bin/env python3
'''Final-state gate for Preview 2 single-shell UX completion.'''
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def read(name: str) -> str:
    path = SRC / name
    if not path.exists():
        raise SystemExit(f"Preview2 UX verification: missing {name}")
    return path.read_bytes().decode("latin-1", errors="ignore")


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise SystemExit(f"Preview2 UX verification: {label} missing")


def main() -> int:
    main_h = read("EmuleDlg.h")
    main_cpp = read("EmuleDlg.cpp")
    search_h = read("SearchResultsWnd.h")
    search_cpp = read("SearchResultsWnd.cpp")
    search2_h = read("Search2Wnd.h")
    search2_cpp = read("Search2Wnd.cpp")
    settings_h = read("EmuleNextSettingsWnd.h")
    settings_cpp = read("EmuleNextSettingsWnd.cpp")
    dashboard_h = read("EmuleNextDashboardWnd.h")
    dashboard_cpp = read("EmuleNextDashboardWnd.cpp")

    for marker, label in (
        ('m_preview2MainNav.AddString(_T("Dashboard"))', "Dashboard primary navigation"),
        ('m_preview2MainNav.AddString(_T("Transfers"))', "Transfers primary navigation"),
        ('m_preview2MainNav.AddString(_T("Search"))', "Search primary navigation"),
        ('m_preview2MainNav.AddString(_T("Library"))', "Library primary navigation"),
        ('m_preview2MainNav.AddString(_T("Known Users"))', "Known Users primary navigation"),
        ('m_preview2MainNav.AddString(_T("Settings"))', "Settings primary navigation"),
        ('m_preview2MainNav.AddString(_T("Diagnostics"))', "Diagnostics primary navigation"),
        ("ShowNextWorkspace(EMULENEXT_SEARCH2_VIEW_ID)", "modern Search 2 primary route"),
        ("ShowNextWorkspace(EMULENEXT_LIBRARY_VIEW_ID)", "Library direct route"),
        ("ShowNextWorkspace(EMULENEXT_KNOWN_USERS_VIEW_ID)", "Known Users direct route"),
        ("ShowNextWorkspace(EMULENEXT_SETTINGS_VIEW_ID)", "Settings direct route"),
        ("ShowNextWorkspace(EMULENEXT_DIAGNOSTICS_VIEW_ID)", "Diagnostics direct route"),
        ("UpdatePreview2HeaderStatus();", "live header refresh"),
        ("GetConnectionStateString()", "header connection status"),
        ("GetTransferRateString()", "header transfer status"),
    ):
        require(main_cpp, marker, label)
    require(main_h, "CStatic m_preview2HeaderStatus;", "header status control")
    require(main_h, "void UpdatePreview2HeaderStatus();", "header status helper")

    require(search_h, "bool ShowNextWorkspace(uint32 searchID);", "public Next workspace router")
    require(search_h, "void ShowLegacySearchWorkspace();", "public legacy Search router")
    require(search_cpp, "ShowSearchSelector(false);", "direct Next workspace tab suppression")
    require(search_cpp, "ShowSearchSelector(true);", "legacy Search tab restoration")
    require(search_cpp, "m_nextNavigation.ShowWindow(SW_HIDE);", "internal sidebar suppression")

    for marker, label in (
        ("CButton m_networkSearch;", "Network search action control"),
        ("Network search...", "Network search action label"),
        ("OnNetworkSearchClicked", "Network search bridge handler"),
        ("ShowLegacySearchWorkspace()", "legacy Search bridge"),
        ("OpenParametersWnd()", "legacy Search parameter bridge"),
        ("place Network search beside the knowledge search", "Search 2 responsive action placement"),
    ):
        require(search2_h if marker == "CButton m_networkSearch;" else search2_cpp, marker, label)

    require(settings_h, "CButton m_classicPreferences;", "classic Preferences bridge control")
    require(settings_cpp, "Classic eMule settings...", "classic Preferences bridge label")
    require(settings_cpp, "OnClassicPreferencesClicked", "classic Preferences bridge handler")
    require(settings_cpp, "ShowPreferences()", "classic Preferences bridge action")

    for marker, label in (
        ("CButton m_more;", "Dashboard More action"),
        ("void CEmuleNextDashboardWnd::OnMoreClicked()", "Dashboard More menu"),
        ("primaryFilters", "Dashboard primary filter set"),
        ("primaryActions", "Dashboard primary action set"),
        ("Preview 2 progressive complexity", "Dashboard specialist-control suppression"),
        ("%u downloads   |   %u active", "Dashboard concise summary"),
    ):
        require(dashboard_h if marker == "CButton m_more;" else dashboard_cpp, marker, label)

    # Settings remains product configuration only. Diagnostics/runtime controls
    # are intentionally forbidden here.
    for forbidden in ("Run stress self-test", "Checkpoint WAL", "Restore backup", "sqlite3_"):
        if forbidden in settings_cpp:
            raise SystemExit(f"Preview2 UX verification: Diagnostics concern leaked into Settings: {forbidden}")

    # Main shell must remain a router over the authoritative legacy child views,
    # not a second protocol implementation.
    for forbidden in ("sqlite3_", "CSearchManager::", "AddFileLinkToDownload("):
        if forbidden in main_cpp:
            raise SystemExit(f"Preview2 UX verification: main shell owns forbidden backend logic: {forbidden}")

    print("eMule Next Preview 2 UX completion verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
