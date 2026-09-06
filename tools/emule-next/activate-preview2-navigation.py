#!/usr/bin/env python3
'''Add a dedicated Preview 2 sidebar for permanent Next workspaces only.'''
from __future__ import annotations
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
HEADER = SRC / "SearchResultsWnd.h"
CPP = SRC / "SearchResultsWnd.cpp"

IDC_EN_PREVIEW2_NAV = "0x7E95"


def main() -> int:
    header = HEADER.read_bytes().decode("latin-1")
    cpp = CPP.read_bytes().decode("latin-1")

    if "CListBox m_nextNavigation;" not in header:
        anchor = "\tCEmuleNextDiagnosticsWnd m_diagnosticsWnd;\n"
        if anchor not in header:
            raise SystemExit("Preview2 navigation: final Diagnostics host member missing")
        header = header.replace(anchor, anchor + "\tCListBox m_nextNavigation;\n", 1)
        handler_anchor = "\tafx_msg void OnSysColorChange();\n"
        if handler_anchor not in header:
            raise SystemExit("Preview2 navigation: handler anchor missing")
        header = header.replace(handler_anchor, handler_anchor + "\tafx_msg void OnNextNavigationChanged();\n", 1)

    if '#include "EmuleNextModernUi.h"' not in cpp:
        anchor = '#include "SearchResultsWnd.h"\n'
        if anchor not in cpp:
            raise SystemExit("Preview2 navigation: include anchor missing")
        cpp = cpp.replace(anchor, anchor + '#include "EmuleNextModernUi.h"\n', 1)

    # MFC message-map macros require the control ID to be declared before the
    # BEGIN_MESSAGE_MAP block is compiled. Checking for the token alone is not
    # sufficient because the token also appears in ON_LBN_SELCHANGE and Create.
    map_anchor = "BEGIN_MESSAGE_MAP(CSearchResultsWnd, CResizableFormView)\n"
    if map_anchor not in cpp:
        raise SystemExit("Preview2 navigation: message map anchor missing")
    definition = f"enum {{ IDC_EN_PREVIEW2_NAV = {IDC_EN_PREVIEW2_NAV} }};"
    if definition not in cpp:
        cpp = cpp.replace(map_anchor, definition + "\n\n" + map_anchor, 1)

    if "ON_LBN_SELCHANGE(IDC_EN_PREVIEW2_NAV, OnNextNavigationChanged)" not in cpp:
        cpp = cpp.replace(map_anchor, map_anchor + "\tON_LBN_SELCHANGE(IDC_EN_PREVIEW2_NAV, OnNextNavigationChanged)\n", 1)

    if 'm_nextNavigation.AddString(_T("Search"));' not in cpp:
        # DB2 deliberately inserts its complete Diagnostics creation block
        # immediately before this stable UI2 restore marker. Insert the sidebar
        # at the same boundary, never after a partial m_diagnosticsWnd.Create()
        # line; that previously risked materializing inside the if block.
        restore_anchor = "\t// Restore the last eMule Next workspace; fall back to Known Users."
        if restore_anchor not in cpp:
            raise SystemExit("Preview2 navigation: final workspace restore anchor missing")
        diagnostics_block = '''\tif (m_diagnosticsWnd.Create(this)) {\n\t\tm_diagnosticsWnd.ShowWindow(SW_HIDE);\n\t\tm_diagnosticsWnd.MoveWindow(&nextViewRect);\n\t\tAddAnchor(m_diagnosticsWnd, TOP_LEFT, BOTTOM_RIGHT);\n'''
        if diagnostics_block not in cpp:
            raise SystemExit("Preview2 navigation: expected final Diagnostics creation contract missing")
        addition = '''
\tCRect nextNavEmpty(0, 0, 0, 0);
\tif (!m_nextNavigation.Create(WS_CHILD | WS_TABSTOP | LBS_NOTIFY | LBS_NOINTEGRALHEIGHT,
\t\t\tnextNavEmpty, this, IDC_EN_PREVIEW2_NAV))
\t\treturn;
\tm_nextNavigation.AddString(_T("Search"));
\tm_nextNavigation.AddString(_T("Library"));
\tm_nextNavigation.AddString(_T("Known Users"));
\tm_nextNavigation.AddString(_T("Settings"));
\tm_nextNavigation.AddString(_T("Diagnostics"));
\tm_nextNavigation.SetFont(CFont::FromHandle(static_cast<HFONT>(::GetStockObject(DEFAULT_GUI_FONT))));
\tCEmuleNextModernUi::SetExplorerTheme(m_nextNavigation.m_hWnd);
\tm_nextNavigation.ShowWindow(SW_HIDE);

'''
        cpp = cpp.replace(restore_anchor, addition + restore_anchor, 1)

    show_signature = "void CSearchResultsWnd::ShowResults(const SSearchParams *pParams)\n{"
    if show_signature not in cpp:
        raise SystemExit("Preview2 navigation: ShowResults anchor missing")
    show_start = cpp.find(show_signature)
    if "m_nextNavigation.ShowWindow(SW_HIDE);" not in cpp[show_start:show_start + 650]:
        cpp = cpp.replace(show_signature, show_signature + "\n\tm_nextNavigation.ShowWindow(SW_HIDE);", 1)

    persistent_anchor = "\tif (IsEmuleNextPersistentView(pParams->dwSearchID)) {\n"
    if "CWnd* preview2ActiveView" not in cpp:
        if persistent_anchor not in cpp:
            raise SystemExit("Preview2 navigation: persistent branch anchor missing")
        addition = '''\t\tm_nextNavigation.ShowWindow(SW_SHOW);
\t\tCWnd* preview2ActiveView = NULL;
\t\tint preview2NavIndex = -1;
'''
        cpp = cpp.replace(persistent_anchor, persistent_anchor + addition, 1)

        mappings = (
            ("EMULENEXT_KNOWN_USERS_VIEW_ID", "m_knownUsersWnd", "2"),
            ("EMULENEXT_SEARCH2_VIEW_ID", "m_search2Wnd", "0"),
            ("EMULENEXT_LIBRARY_VIEW_ID", "m_fileLibraryWnd", "1"),
            ("EMULENEXT_SETTINGS_VIEW_ID", "m_nextSettingsWnd", "3"),
            ("EMULENEXT_DIAGNOSTICS_VIEW_ID", "m_diagnosticsWnd", "4"),
        )
        branch_start = cpp.find(persistent_anchor)
        for view_id, member, index in mappings:
            marker = f"pParams->dwSearchID == {view_id}) {{"
            pos = cpp.find(marker, branch_start)
            if pos < 0:
                raise SystemExit(f"Preview2 navigation: view branch missing {view_id}")
            line_end = cpp.find("\n", pos)
            cpp = cpp[:line_end + 1] + f"\t\t\tpreview2ActiveView = &{member};\n\t\t\tpreview2NavIndex = {index};\n" + cpp[line_end + 1:]

        return_anchor = "\t\treturn;\n\t}\n\n\tsearchlistctrl.ShowWindow(SW_SHOW);"
        if return_anchor not in cpp:
            raise SystemExit("Preview2 navigation: persistent return anchor missing")
        layout = '''\t\tif (preview2NavIndex >= 0)
\t\t\tm_nextNavigation.SetCurSel(preview2NavIndex);
\t\tCRect preview2Rect;
\t\tsearchlistctrl.GetWindowRect(&preview2Rect);
\t\tScreenToClient(&preview2Rect);
\t\tconst int preview2NavWidth = CEmuleNextModernUi::NavigationWidth(m_hWnd);
\t\tconst int preview2Gap = CEmuleNextModernUi::ControlGap(m_hWnd);
\t\tm_nextNavigation.MoveWindow(preview2Rect.left, preview2Rect.top, preview2NavWidth, preview2Rect.Height());
\t\tif (preview2ActiveView != NULL)
\t\t\tpreview2ActiveView->MoveWindow(preview2Rect.left + preview2NavWidth + preview2Gap, preview2Rect.top,
\t\t\t\tmax(0, preview2Rect.Width() - preview2NavWidth - preview2Gap), preview2Rect.Height());
'''
        cpp = cpp.replace(return_anchor, layout + return_anchor, 1)

    if "void CSearchResultsWnd::OnNextNavigationChanged()" not in cpp:
        cpp += '''

void CSearchResultsWnd::OnNextNavigationChanged()
{
\tconst int selection = m_nextNavigation.GetCurSel();
\tconst uint32 ids[] = {
\t\tEMULENEXT_SEARCH2_VIEW_ID,
\t\tEMULENEXT_LIBRARY_VIEW_ID,
\t\tEMULENEXT_KNOWN_USERS_VIEW_ID,
\t\tEMULENEXT_SETTINGS_VIEW_ID,
\t\tEMULENEXT_DIAGNOSTICS_VIEW_ID
\t};
\tif (selection < 0 || selection >= _countof(ids))
\t\treturn;

\tTCITEM item = {};
\titem.mask = TCIF_PARAM;
\tfor (int i = 0; i < searchselect.GetItemCount(); ++i) {
\t\tif (!searchselect.GetItem(i, &item) || item.lParam == NULL)
\t\t\tcontinue;
\t\tSSearchParams* params = reinterpret_cast<SSearchParams*>(item.lParam);
\t\tif (params->dwSearchID == ids[selection]) {
\t\t\tsearchselect.SetCurSel(i);
\t\t\tsearchselect.HighlightItem(i, FALSE);
\t\t\tShowResults(params);
\t\t\treturn;
\t\t}
\t}
}
'''

    # Structural final-state checks catch partial/misplaced materialization
    # before MSVC. In particular, the control ID must precede the MFC message
    # map and the navigation control must be created after Diagnostics but before
    # workspace restoration.
    definition_pos = cpp.find(definition)
    message_map_pos = cpp.find(map_anchor)
    message_entry_pos = cpp.find("ON_LBN_SELCHANGE(IDC_EN_PREVIEW2_NAV, OnNextNavigationChanged)")
    create_pos = cpp.find('m_nextNavigation.AddString(_T("Search"));')
    diag_pos = cpp.find("\tif (m_diagnosticsWnd.Create(this)) {")
    restore_pos = cpp.find("\t// Restore the last eMule Next workspace; fall back to Known Users.")
    if not (definition_pos >= 0 and message_map_pos > definition_pos and message_entry_pos > message_map_pos):
        raise SystemExit("Preview2 navigation: control ID/message-map compile ordering unsafe")
    if not (diag_pos >= 0 and create_pos > diag_pos and restore_pos > create_pos):
        raise SystemExit("Preview2 navigation: unsafe host creation ordering")

    HEADER.write_bytes(header.encode("latin-1"))
    CPP.write_bytes(cpp.encode("latin-1"))
    print("Preview 2 permanent workspace sidebar active")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
