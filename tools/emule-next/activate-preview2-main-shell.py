#!/usr/bin/env python3
'''Materialize the visible Preview 2 main application shell.

The legacy eMule child windows and command handlers remain authoritative. This
late product-layer activator replaces only the primary chrome: a modern left
navigation rail, Preview 2 header, connection action and content geometry.
'''
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


def patch_header() -> None:
    text, newline = load(HEADER)

    if '#include "EmuleNextModernUi.h"' not in text:
        anchor = '#include "TrayDialog.h"\n'
        if anchor not in text:
            raise SystemExit("Preview2 main shell: EmuleDlg include anchor missing")
        text = text.replace(anchor, anchor + '#include "EmuleNextModernUi.h"\n', 1)

    if "CEmuleNextNavList m_preview2MainNav;" not in text:
        anchor = "\tCReBarCtrl m_ctlMainTopReBar;\n"
        if anchor not in text:
            raise SystemExit("Preview2 main shell: main rebar member anchor missing")
        addition = '''\tCEmuleNextNavList m_preview2MainNav;
\tCStatic m_preview2Brand;
\tCStatic m_preview2Section;
\tCButton m_preview2ConnectButton;
\tCFont m_preview2NormalFont;
\tCFont m_preview2TitleFont;
\tCFont m_preview2SectionFont;
'''
        text = text.replace(anchor, anchor + addition, 1)

    if "void UpdatePreview2MainSection(int selection);" not in text:
        anchor = "\tvoid SetTaskbarIconColor();\n"
        if anchor not in text:
            raise SystemExit("Preview2 main shell: helper method anchor missing")
        addition = '''\tvoid UpdatePreview2MainSection(int selection);
\tafx_msg void OnPreview2MainNavChanged();
\tafx_msg void OnPreview2Connect();
'''
        text = text.replace(anchor, anchor + addition, 1)

    save(HEADER, text, newline)


def patch_cpp() -> None:
    text, newline = load(CPP)

    for include in ('#include "EmuleNextTheme.h"', '#include "EmuleNextVersion.h"'):
        if include not in text:
            anchor = '#include "emuleDlg.h"\n'
            if anchor not in text:
                raise SystemExit("Preview2 main shell: EmuleDlg source include anchor missing")
            text = text.replace(anchor, anchor + include + "\n", 1)

    if "IDC_EN_PREVIEW2_MAIN_NAV" not in text:
        anchor = "static const UINT UWM_ARE_YOU_EMULE = RegisterWindowMessage(EMULE_GUID);\n"
        if anchor not in text:
            raise SystemExit("Preview2 main shell: control-id anchor missing")
        ids = '''

enum
{
\tIDC_EN_PREVIEW2_MAIN_NAV = 0x7E20,
\tIDC_EN_PREVIEW2_BRAND,
\tIDC_EN_PREVIEW2_SECTION,
\tIDC_EN_PREVIEW2_CONNECT
};
'''
        text = text.replace(anchor, anchor + ids, 1)

    map_anchor = "BEGIN_MESSAGE_MAP(CemuleDlg, CTrayDialog)\n"
    if "ON_LBN_SELCHANGE(IDC_EN_PREVIEW2_MAIN_NAV, OnPreview2MainNavChanged)" not in text:
        if map_anchor not in text:
            raise SystemExit("Preview2 main shell: message map anchor missing")
        text = text.replace(map_anchor, map_anchor
            + "\tON_LBN_SELCHANGE(IDC_EN_PREVIEW2_MAIN_NAV, OnPreview2MainNavChanged)\n"
            + "\tON_BN_CLICKED(IDC_EN_PREVIEW2_CONNECT, OnPreview2Connect)\n", 1)

    # Preview 2 product title is deliberately separate from protocol versioning.
    old_title = '\tSetWindowText(_T("eMule v") + theApp.m_strCurVersionLong);\n'
    if "SetWindowText(EMULENEXT_PRODUCT_WITH_CORE_TEXT);" not in text:
        if old_title not in text:
            raise SystemExit("Preview2 main shell: window title anchor missing")
        text = text.replace(old_title, "\tSetWindowText(EMULENEXT_PRODUCT_WITH_CORE_TEXT);\n", 1)

    create_anchor = "\tDialogCreateIndirect(ircwnd, IDD_IRC);\n"
    if "m_preview2MainNav.AddString(_T(\"Dashboard\"));" not in text:
        if create_anchor not in text:
            raise SystemExit("Preview2 main shell: child creation boundary missing")
        block = r'''

	CRect preview2Empty(0, 0, 0, 0);
	if (!m_preview2MainNav.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | LBS_NOTIFY | LBS_OWNERDRAWFIXED |
		LBS_HASSTRINGS | LBS_NOINTEGRALHEIGHT, preview2Empty, this, IDC_EN_PREVIEW2_MAIN_NAV))
		return FALSE;
	if (!m_preview2Brand.Create(EMULENEXT_PRODUCT_TEXT, WS_CHILD | WS_VISIBLE | SS_LEFT,
		preview2Empty, this, IDC_EN_PREVIEW2_BRAND))
		return FALSE;
	if (!m_preview2Section.Create(_T("Dashboard"), WS_CHILD | WS_VISIBLE | SS_LEFT,
		preview2Empty, this, IDC_EN_PREVIEW2_SECTION))
		return FALSE;
	if (!m_preview2ConnectButton.Create(_T("Connect"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
		preview2Empty, this, IDC_EN_PREVIEW2_CONNECT))
		return FALSE;

	m_preview2MainNav.AddString(_T("Dashboard"));
	m_preview2MainNav.AddString(_T("Transfers"));
	m_preview2MainNav.AddString(_T("Search"));
	m_preview2MainNav.AddString(_T("Shared Files"));
	m_preview2MainNav.AddString(_T("Servers"));
	m_preview2MainNav.AddString(_T("Kad"));
	m_preview2MainNav.AddString(_T("Messages"));
	m_preview2MainNav.AddString(_T("IRC"));
	m_preview2MainNav.AddString(_T("Statistics"));
	m_preview2MainNav.AddString(_T("Settings"));

	CEmuleNextModernUi::ApplyFont(this, m_preview2NormalFont, m_preview2TitleFont, m_preview2SectionFont);
	m_preview2MainNav.SetFont(&m_preview2NormalFont);
	m_preview2Brand.SetFont(&m_preview2TitleFont);
	m_preview2Section.SetFont(&m_preview2SectionFont);
	m_preview2ConnectButton.SetFont(&m_preview2NormalFont);
	m_preview2MainNav.RefreshPalette();
	CEmuleNextModernUi::SetExplorerTheme(m_preview2ConnectButton.m_hWnd);
	CEmuleNextTheme::ApplyToWindow(m_hWnd);
'''
        text = text.replace(create_anchor, create_anchor + block, 1)

    # Replace the classic toolbar-driven content geometry with the Preview 2
    # shell. The legacy toolbar remains alive for command compatibility but is
    # hidden; command handlers and child dialogs are untouched.
    old_layout = '''\t// adjust all main window sizes for toolbar height and maximize the child windows
\tCRect rcClient, rcToolbar, rcStatusbar;
\tGetClientRect(&rcClient);
\tpwndToolbarX->GetWindowRect(&rcToolbar);
\tstatusbar->GetWindowRect(&rcStatusbar);
\trcClient.top += rcToolbar.Height();
\trcClient.bottom -= rcStatusbar.Height();

\t// anchor bars
\tAddAnchor(*pwndToolbarX, TOP_LEFT, TOP_RIGHT);
\tAddAnchor(*statusbar, BOTTOM_LEFT, BOTTOM_RIGHT);
'''
    new_layout = '''\t// Preview 2 main shell: persistent navigation rail + product header.
\tCRect rcClient, rcStatusbar;
\tGetClientRect(&rcClient);
\tstatusbar->GetWindowRect(&rcStatusbar);
\tif (::IsWindow(pwndToolbarX->m_hWnd))
\t\tpwndToolbarX->ShowWindow(SW_HIDE);

\tconst int preview2NavWidth = CEmuleNextModernUi::NavigationWidth(m_hWnd);
\tconst int preview2HeaderHeight = CEmuleNextModernUi::HeaderHeight(m_hWnd);
\tconst int preview2Margin = CEmuleNextModernUi::PageMargin(m_hWnd);
\tconst int preview2StatusHeight = rcStatusbar.Height();
\tm_preview2MainNav.MoveWindow(0, 0, preview2NavWidth, max(0, rcClient.Height() - preview2StatusHeight));
\tm_preview2Brand.MoveWindow(preview2NavWidth + preview2Margin, CEmuleNextModernUi::Scale(m_hWnd, 8),
\t\tmax(0, rcClient.Width() - preview2NavWidth - CEmuleNextModernUi::Scale(m_hWnd, 250)),
\t\tCEmuleNextModernUi::Scale(m_hWnd, 30));
\tm_preview2Section.MoveWindow(preview2NavWidth + preview2Margin, CEmuleNextModernUi::Scale(m_hWnd, 36),
\t\tmax(0, rcClient.Width() - preview2NavWidth - CEmuleNextModernUi::Scale(m_hWnd, 250)),
\t\tCEmuleNextModernUi::Scale(m_hWnd, 22));
\tm_preview2ConnectButton.MoveWindow(rcClient.right - preview2Margin - CEmuleNextModernUi::Scale(m_hWnd, 112),
\t\tCEmuleNextModernUi::Scale(m_hWnd, 14), CEmuleNextModernUi::Scale(m_hWnd, 112),
\t\tCEmuleNextModernUi::ControlHeight(m_hWnd));

\trcClient.left += preview2NavWidth;
\trcClient.top += preview2HeaderHeight;
\trcClient.bottom -= preview2StatusHeight;

\tAddAnchor(m_preview2MainNav, TOP_LEFT, BOTTOM_LEFT);
\tAddAnchor(m_preview2Brand, TOP_LEFT, TOP_RIGHT);
\tAddAnchor(m_preview2Section, TOP_LEFT, TOP_RIGHT);
\tAddAnchor(m_preview2ConnectButton, TOP_RIGHT, TOP_RIGHT);
\tAddAnchor(*statusbar, BOTTOM_LEFT, BOTTOM_RIGHT);
'''
    if "Preview 2 main shell: persistent navigation rail" not in text:
        if old_layout not in text:
            raise SystemExit("Preview2 main shell: classic content-layout block missing")
        text = text.replace(old_layout, new_layout, 1)

    # After all main child windows have received their final content rectangle,
    # restore the Preview 2 section. Settings is never auto-opened on startup.
    loop_end = '''\tfor (unsigned i = 0; i < _countof(apWnds); ++i) {
\t\tapWnds[i]->SetWindowPos(NULL, rcClient.left, rcClient.top, rcClient.Width(), rcClient.Height(), SWP_NOZORDER);
\t\tAddAnchor(*apWnds[i], TOP_LEFT, BOTTOM_RIGHT);
\t}
'''
    if "Preview2MainSection" not in text:
        if loop_end not in text:
            raise SystemExit("Preview2 main shell: child layout loop missing")
        restore = '''\n\tint preview2Section = static_cast<int>(theApp.GetProfileInt(_T("eMule Next Workspace"), _T("Preview2MainSection"), 0));
\tif (preview2Section < 0 || preview2Section > 8)
\t\tpreview2Section = 0;
\tm_preview2MainNav.SetCurSel(preview2Section);
\tOnPreview2MainNavChanged();
'''
        text = text.replace(loop_end, loop_end + restore, 1)

    if "void CemuleDlg::UpdatePreview2MainSection(int selection)" not in text:
        insert_anchor = "void CemuleDlg::SetClientIconList()\n"
        if insert_anchor not in text:
            raise SystemExit("Preview2 main shell: method insertion boundary missing")
        methods = r'''void CemuleDlg::UpdatePreview2MainSection(int selection)
{
	static LPCTSTR const labels[] = {
		_T("Dashboard overview"),
		_T("Transfers"),
		_T("Search and discovery"),
		_T("Shared files"),
		_T("eD2K servers"),
		_T("Kad network"),
		_T("Messages"),
		_T("IRC"),
		_T("Statistics"),
		_T("Settings")
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
	if (selection <= 8)
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
	case 2:
		SetActiveDialog(searchwnd);
		break;
	case 3:
		SetActiveDialog(sharedfileswnd);
		break;
	case 4:
		SetActiveDialog(serverwnd);
		break;
	case 5:
		SetActiveDialog(kademliawnd);
		break;
	case 6:
		SetActiveDialog(chatwnd);
		break;
	case 7:
		SetActiveDialog(ircwnd);
		break;
	case 8:
		SetActiveDialog(statisticswnd);
		break;
	case 9:
		ShowPreferences();
		break;
	}
}

'''
        text = text.replace(insert_anchor, methods + insert_anchor, 1)

    # Compile-order contract for the MFC message map.
    id_pos = text.find("IDC_EN_PREVIEW2_MAIN_NAV =")
    map_pos = text.find("BEGIN_MESSAGE_MAP(CemuleDlg, CTrayDialog)")
    handler_pos = text.find("ON_LBN_SELCHANGE(IDC_EN_PREVIEW2_MAIN_NAV")
    if not (id_pos >= 0 and map_pos > id_pos and handler_pos > map_pos):
        raise SystemExit("Preview2 main shell: control IDs must precede CemuleDlg message map")

    save(CPP, text, newline)


def main() -> int:
    for path in (HEADER, CPP):
        if not path.exists():
            raise SystemExit(f"Preview2 main shell: missing {path.name}")
    patch_header()
    patch_cpp()
    print("eMule Next Preview 2 visible main shell materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())