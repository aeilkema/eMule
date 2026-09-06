#!/usr/bin/env python3
'''Complete Preview 2 primary UX routing and Settings integration.

This runs after the visible main shell is materialized. It promotes permanent
Next workspaces into the primary application navigation without replacing the
legacy Search/tab/network engines, and keeps classic eMule Preferences available
from the modern Settings entry point.
'''
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
SEARCH_H = SRC / "SearchResultsWnd.h"
SEARCH_CPP = SRC / "SearchResultsWnd.cpp"
MAIN_CPP = SRC / "EmuleDlg.cpp"
SETTINGS_H = SRC / "EmuleNextSettingsWnd.h"
SETTINGS_CPP = SRC / "EmuleNextSettingsWnd.cpp"


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


def patch_search_router() -> None:
    header, hn = load(SEARCH_H)
    cpp, cn = load(SEARCH_CPP)

    if "bool ShowNextWorkspace(uint32 searchID);" not in header:
        anchor = "\tvoid\tLocalize();\n"
        if anchor not in header:
            raise SystemExit("Preview2 UX: SearchResults public router anchor missing")
        header = header.replace(anchor, anchor +
            "\tbool ShowNextWorkspace(uint32 searchID);\n"
            "\tvoid ShowLegacySearchWorkspace();\n", 1)

    if "bool CSearchResultsWnd::ShowNextWorkspace(uint32 searchID)" not in cpp:
        anchor = "\nvoid CSearchResultsWnd::OnSelChangeTab"
        if anchor not in cpp:
            raise SystemExit("Preview2 UX: SearchResults method boundary missing")
        methods = r'''

bool CSearchResultsWnd::ShowNextWorkspace(uint32 searchID)
{
	if (!IsEmuleNextPersistentView(searchID))
		return false;

	TCITEM item = {};
	item.mask = TCIF_PARAM;
	SSearchParams* target = NULL;
	int targetTab = -1;
	for (int i = 0; i < searchselect.GetItemCount(); ++i) {
		if (!searchselect.GetItem(i, &item) || item.lParam == NULL)
			continue;
		SSearchParams* params = reinterpret_cast<SSearchParams*>(item.lParam);
		if (params->dwSearchID == searchID) {
			target = params;
			targetTab = i;
			break;
		}
	}
	if (target == NULL)
		return false;

	if (targetTab >= 0) {
		searchselect.SetCurSel(targetTab);
		searchselect.HighlightItem(targetTab, FALSE);
	}
	ShowResults(target);
	ShowSearchSelector(false);
	if (::IsWindow(m_nextNavigation.m_hWnd))
		m_nextNavigation.ShowWindow(SW_HIDE);

	CWnd* active = NULL;
	if (searchID == EMULENEXT_SEARCH2_VIEW_ID) active = &m_search2Wnd;
	else if (searchID == EMULENEXT_LIBRARY_VIEW_ID) active = &m_fileLibraryWnd;
	else if (searchID == EMULENEXT_KNOWN_USERS_VIEW_ID) active = &m_knownUsersWnd;
	else if (searchID == EMULENEXT_SETTINGS_VIEW_ID) active = &m_nextSettingsWnd;
	else if (searchID == EMULENEXT_DIAGNOSTICS_VIEW_ID) active = &m_diagnosticsWnd;

	if (active != NULL && ::IsWindow(active->m_hWnd)) {
		CRect rect;
		searchlistctrl.GetWindowRect(&rect);
		ScreenToClient(&rect);
		active->MoveWindow(&rect);
	}
	return true;
}

void CSearchResultsWnd::ShowLegacySearchWorkspace()
{
	ShowSearchSelector(true);
	if (::IsWindow(m_nextNavigation.m_hWnd))
		m_nextNavigation.ShowWindow(SW_HIDE);

	TCITEM item = {};
	item.mask = TCIF_PARAM;
	for (int i = 0; i < searchselect.GetItemCount(); ++i) {
		if (!searchselect.GetItem(i, &item) || item.lParam == NULL)
			continue;
		SSearchParams* params = reinterpret_cast<SSearchParams*>(item.lParam);
		if (!IsEmuleNextPersistentView(params->dwSearchID)) {
			searchselect.SetCurSel(i);
			searchselect.HighlightItem(i, FALSE);
			ShowResults(params);
			return;
		}
	}

	m_knownUsersWnd.ShowWindow(SW_HIDE);
	m_search2Wnd.ShowWindow(SW_HIDE);
	m_fileLibraryWnd.ShowWindow(SW_HIDE);
	m_nextSettingsWnd.ShowWindow(SW_HIDE);
	m_diagnosticsWnd.ShowWindow(SW_HIDE);
	searchlistctrl.ShowWindow(SW_SHOW);
	m_ctlFilter.ShowWindow(SW_SHOW);
	GetDlgItem(IDC_SDOWNLOAD)->ShowWindow(SW_SHOW);
	UpdateCatTabs();
}
'''
        cpp = cpp.replace(anchor, methods + anchor, 1)

    save(SEARCH_H, header, hn)
    save(SEARCH_CPP, cpp, cn)


def patch_main_navigation() -> None:
    text, newline = load(MAIN_CPP)

    if '#include "SearchResultsWnd.h"' not in text:
        anchor = '#include "SearchDlg.h"\n'
        if anchor not in text:
            raise SystemExit("Preview2 UX: SearchDlg include anchor missing")
        text = text.replace(anchor, anchor + '#include "SearchResultsWnd.h"\n', 1)

    old_items = '''\tm_preview2MainNav.AddString(_T("Dashboard"));
\tm_preview2MainNav.AddString(_T("Transfers"));
\tm_preview2MainNav.AddString(_T("Search"));
\tm_preview2MainNav.AddString(_T("Shared Files"));
\tm_preview2MainNav.AddString(_T("Servers"));
\tm_preview2MainNav.AddString(_T("Kad"));
\tm_preview2MainNav.AddString(_T("Messages"));
\tm_preview2MainNav.AddString(_T("IRC"));
\tm_preview2MainNav.AddString(_T("Statistics"));
\tm_preview2MainNav.AddString(_T("Settings"));
'''
    new_items = '''\tm_preview2MainNav.AddString(_T("Dashboard"));
\tm_preview2MainNav.AddString(_T("Transfers"));
\tm_preview2MainNav.AddString(_T("Search"));
\tm_preview2MainNav.AddString(_T("Library"));
\tm_preview2MainNav.AddString(_T("Shared Files"));
\tm_preview2MainNav.AddString(_T("Known Users"));
\tm_preview2MainNav.AddString(_T("Messages"));
\tm_preview2MainNav.AddString(_T("Servers"));
\tm_preview2MainNav.AddString(_T("Kad"));
\tm_preview2MainNav.AddString(_T("Statistics"));
\tm_preview2MainNav.AddString(_T("Settings"));
\tm_preview2MainNav.AddString(_T("Diagnostics"));
\tm_preview2MainNav.AddString(_T("IRC"));
'''
    if old_items in text:
        text = text.replace(old_items, new_items, 1)
    elif 'm_preview2MainNav.AddString(_T("Diagnostics"));' not in text:
        raise SystemExit("Preview2 UX: main navigation item block missing")

    start = text.find("void CemuleDlg::UpdatePreview2MainSection(int selection)")
    end = text.find("void CemuleDlg::SetClientIconList()", start)
    if start < 0 or end < 0:
        raise SystemExit("Preview2 UX: main shell routing method boundary missing")

    methods = r'''void CemuleDlg::UpdatePreview2MainSection(int selection)
{
	static LPCTSTR const labels[] = {
		_T("Overview and attention"),
		_T("Downloads and transfers"),
		_T("Search and discovery"),
		_T("History, favorites and download later"),
		_T("Files shared by this client"),
		_T("Known peers and shared-file knowledge"),
		_T("Messages"),
		_T("eD2K servers"),
		_T("Kad network"),
		_T("Statistics"),
		_T("Application settings"),
		_T("Health, recovery and runtime validation"),
		_T("IRC")
	};
	if (selection >= 0 && selection < _countof(labels))
		m_preview2Section.SetWindowText(labels[selection]);

	if (::IsWindow(m_preview2ConnectButton.m_hWnd)) {
		LPCTSTR action = theApp.serverconnect->IsConnected() || theApp.serverconnect->IsConnecting()
			? _T("Disconnect") : _T("Connect");
		m_preview2ConnectButton.SetWindowText(action);
	}
}

void CemuleDlg::OnPreview2Connect()
{
	OnBnClickedConnect();
	UpdatePreview2MainSection(m_preview2MainNav.GetCurSel());
}

void CemuleDlg::OnPreview2MainNavChanged()
{
	const int selection = m_preview2MainNav.GetCurSel();
	if (selection < 0)
		return;

	UpdatePreview2MainSection(selection);
	if (selection <= 9 || selection == 12)
		theApp.WriteProfileInt(_T("eMule Next Workspace"), _T("Preview2MainSection"), selection);

	switch (selection) {
	case 0: // Dashboard
		SetActiveDialog(transferwnd);
		if (transferwnd != NULL && transferwnd->m_pwndTransfer != NULL)
			transferwnd->m_pwndTransfer->SendMessage(WM_COMMAND, 0xEE20, 0);
		break;
	case 1: // Transfers
		SetActiveDialog(transferwnd);
		if (transferwnd != NULL && transferwnd->m_pwndTransfer != NULL)
			transferwnd->m_pwndTransfer->SendMessage(WM_COMMAND, MP_VIEW1_DOWNLOADS, 0);
		break;
	case 2: // Legacy-authoritative Search
		SetActiveDialog(searchwnd);
		if (searchwnd != NULL && searchwnd->m_pwndResults != NULL)
			searchwnd->m_pwndResults->ShowLegacySearchWorkspace();
		break;
	case 3: // Library
		SetActiveDialog(searchwnd);
		if (searchwnd != NULL && searchwnd->m_pwndResults != NULL)
			searchwnd->m_pwndResults->ShowNextWorkspace(EMULENEXT_LIBRARY_VIEW_ID);
		break;
	case 4:
		SetActiveDialog(sharedfileswnd);
		break;
	case 5: // Known Users
		SetActiveDialog(searchwnd);
		if (searchwnd != NULL && searchwnd->m_pwndResults != NULL)
			searchwnd->m_pwndResults->ShowNextWorkspace(EMULENEXT_KNOWN_USERS_VIEW_ID);
		break;
	case 6:
		SetActiveDialog(chatwnd);
		break;
	case 7:
		SetActiveDialog(serverwnd);
		break;
	case 8:
		SetActiveDialog(kademliawnd);
		break;
	case 9:
		SetActiveDialog(statisticswnd);
		break;
	case 10: // Modern Settings entry point
		SetActiveDialog(searchwnd);
		if (searchwnd != NULL && searchwnd->m_pwndResults != NULL)
			searchwnd->m_pwndResults->ShowNextWorkspace(EMULENEXT_SETTINGS_VIEW_ID);
		break;
	case 11: // Diagnostics
		SetActiveDialog(searchwnd);
		if (searchwnd != NULL && searchwnd->m_pwndResults != NULL)
			searchwnd->m_pwndResults->ShowNextWorkspace(EMULENEXT_DIAGNOSTICS_VIEW_ID);
		break;
	case 12:
		SetActiveDialog(ircwnd);
		break;
	}
}

'''
    text = text[:start] + methods + text[end:]

    text = text.replace("if (preview2Section < 0 || preview2Section > 8)",
                        "if (preview2Section < 0 || preview2Section > 12 || preview2Section == 10 || preview2Section == 11)")

    save(MAIN_CPP, text, newline)


def patch_settings_bridge() -> None:
    header, hn = load(SETTINGS_H)
    cpp, cn = load(SETTINGS_CPP)

    if "afx_msg void OnClassicPreferencesClicked();" not in header:
        anchor = "    afx_msg void OnApplyClicked();\n"
        if anchor not in header:
            raise SystemExit("Preview2 UX: Settings handler anchor missing")
        header = header.replace(anchor, anchor + "    afx_msg void OnClassicPreferencesClicked();\n", 1)
    if "CButton m_classicPreferences;" not in header:
        anchor = "    CButton m_apply;\n"
        if anchor not in header:
            raise SystemExit("Preview2 UX: Settings action member anchor missing")
        header = header.replace(anchor, "    CButton m_classicPreferences;\n" + anchor, 1)

    if '#include "emuledlg.h"' not in cpp:
        anchor = '#include "emule.h"\n'
        if anchor not in cpp:
            raise SystemExit("Preview2 UX: Settings emule include anchor missing")
        cpp = cpp.replace(anchor, anchor + '#include "emuledlg.h"\n', 1)

    if "IDC_EN_CLASSIC_PREFS" not in cpp:
        cpp = cpp.replace("        IDC_EN_APPLY\n    };", "        IDC_EN_APPLY,\n        IDC_EN_CLASSIC_PREFS\n    };", 1)
    if "ON_BN_CLICKED(IDC_EN_CLASSIC_PREFS, OnClassicPreferencesClicked)" not in cpp:
        anchor = "    ON_BN_CLICKED(IDC_EN_APPLY, OnApplyClicked)\n"
        if anchor not in cpp:
            raise SystemExit("Preview2 UX: Settings message-map anchor missing")
        cpp = cpp.replace(anchor, anchor + "    ON_BN_CLICKED(IDC_EN_CLASSIC_PREFS, OnClassicPreferencesClicked)\n", 1)

    if 'm_classicPreferences.Create(_T("Classic eMule settings..."' not in cpp:
        old = '        || !m_apply.Create(_T("Apply changes"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_DEFPUSHBUTTON, empty, this, IDC_EN_APPLY)\n        || !m_status.Create(_T(""), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)) {'
        new = '        || !m_classicPreferences.Create(_T("Classic eMule settings..."), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_CLASSIC_PREFS)\n        || !m_apply.Create(_T("Apply changes"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_DEFPUSHBUTTON, empty, this, IDC_EN_APPLY)\n        || !m_status.Create(_T(""), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)) {'
        if old not in cpp:
            raise SystemExit("Preview2 UX: Settings creation chain anchor missing")
        cpp = cpp.replace(old, new, 1)

    cpp = cpp.replace("&m_a4afThreshold, &m_advancedNote, &m_apply, &m_status",
                      "&m_a4afThreshold, &m_advancedNote, &m_classicPreferences, &m_apply, &m_status")

    old_layout = '''    const int actionWidth = CEmuleNextModernUi::Scale(m_hWnd, 150);
    const int actionY = max(y + sectionGap, cy - margin - controlHeight);
    m_apply.MoveWindow(contentLeft + contentWidth - actionWidth, actionY, actionWidth, controlHeight);
    m_status.MoveWindow(contentLeft + gap, actionY, max(0, contentWidth - actionWidth - gap * 3), controlHeight);
'''
    new_layout = '''    const int actionWidth = CEmuleNextModernUi::Scale(m_hWnd, 150);
    const int classicWidth = CEmuleNextModernUi::Scale(m_hWnd, 190);
    const int actionY = max(y + sectionGap, cy - margin - controlHeight);
    m_classicPreferences.MoveWindow(contentLeft, actionY, classicWidth, controlHeight);
    m_apply.MoveWindow(contentLeft + contentWidth - actionWidth, actionY, actionWidth, controlHeight);
    m_status.MoveWindow(contentLeft + classicWidth + gap, actionY,
        max(0, contentWidth - classicWidth - actionWidth - gap * 3), controlHeight);
'''
    if old_layout in cpp:
        cpp = cpp.replace(old_layout, new_layout, 1)
    elif "m_classicPreferences.MoveWindow" not in cpp:
        raise SystemExit("Preview2 UX: Settings action layout anchor missing")

    if "void CEmuleNextSettingsWnd::OnClassicPreferencesClicked()" not in cpp:
        anchor = "void CEmuleNextSettingsWnd::OnApplyClicked()\n"
        if anchor not in cpp:
            raise SystemExit("Preview2 UX: Settings apply handler boundary missing")
        handler = '''void CEmuleNextSettingsWnd::OnClassicPreferencesClicked()
{
    if (theApp.emuledlg != NULL)
        theApp.emuledlg->ShowPreferences();
}

'''
        cpp = cpp.replace(anchor, handler + anchor, 1)

    save(SETTINGS_H, header, hn)
    save(SETTINGS_CPP, cpp, cn)


def verify_final_state() -> None:
    search_h = SEARCH_H.read_bytes().decode("latin-1", errors="ignore")
    search_cpp = SEARCH_CPP.read_bytes().decode("latin-1", errors="ignore")
    main = MAIN_CPP.read_bytes().decode("latin-1", errors="ignore")
    settings = SETTINGS_CPP.read_bytes().decode("latin-1", errors="ignore")

    required = (
        (search_h, "ShowNextWorkspace(uint32 searchID)", "public Next workspace router"),
        (search_h, "ShowLegacySearchWorkspace()", "legacy Search router"),
        (search_cpp, "ShowSearchSelector(false)", "hidden internal navigation for direct workspaces"),
        (main, 'm_preview2MainNav.AddString(_T("Library"))', "Library in primary navigation"),
        (main, 'm_preview2MainNav.AddString(_T("Known Users"))', "Known Users in primary navigation"),
        (main, 'm_preview2MainNav.AddString(_T("Diagnostics"))', "Diagnostics in primary navigation"),
        (main, "ShowNextWorkspace(EMULENEXT_SETTINGS_VIEW_ID)", "modern Settings primary route"),
        (main, "ShowNextWorkspace(EMULENEXT_DIAGNOSTICS_VIEW_ID)", "Diagnostics primary route"),
        (settings, "Classic eMule settings...", "classic settings bridge"),
    )
    for text, marker, label in required:
        if marker not in text:
            raise SystemExit(f"Preview2 UX completion: {label} missing")


def main() -> int:
    for path in (SEARCH_H, SEARCH_CPP, MAIN_CPP, SETTINGS_H, SETTINGS_CPP):
        if not path.exists():
            raise SystemExit(f"Preview2 UX completion: missing {path.name}")
    patch_search_router()
    patch_main_navigation()
    patch_settings_bridge()
    verify_final_state()
    print("eMule Next Preview 2 UX completion materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
