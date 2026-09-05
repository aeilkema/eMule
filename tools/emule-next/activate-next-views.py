#!/usr/bin/env python3
"""Integrate the visible eMule Next Search 2, Library and Settings views."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def load(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    newline = "\r\n" if crlf >= lf and crlf else "\n"
    text = raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n")
    return text, newline


def save(path: pathlib.Path, text: str, newline: str) -> None:
    if newline != "\n":
        text = text.replace("\n", newline)
    path.write_bytes(text.encode("latin-1"))


def insert_after(text: str, anchor: str, addition: str, path: pathlib.Path) -> str:
    if addition.strip() in text:
        return text
    if anchor not in text:
        raise RuntimeError(f"Next view anchor not found in {path}: {anchor!r}")
    return text.replace(anchor, anchor + addition, 1)


def patch_project() -> None:
    path = SRC / "emule.vcxproj"
    text, newline = load(path)
    anchor = '    <ClCompile Include="EmuleNextDatabase.cpp" />\n'
    for name in (
        "Search2Wnd.cpp",
        "LibraryBrowserService.cpp",
        "FileLibraryWnd.cpp",
        "EmuleNextSettingsWnd.cpp",
    ):
        if (SRC / name).exists() and f'Include="{name}"' not in text:
            if anchor not in text:
                raise RuntimeError(f"Unable to add {name} to project")
            text = text.replace(anchor, anchor + f'    <ClCompile Include="{name}" />\n', 1)
    save(path, text, newline)


def patch_header() -> None:
    path = SRC / "SearchResultsWnd.h"
    text, newline = load(path)
    text = insert_after(text, '#include "KnownUsersWnd.h"\n',
        '#include "Search2Wnd.h"\n#include "FileLibraryWnd.h"\n#include "EmuleNextSettingsWnd.h"\n', path)
    text = insert_after(text, '\tCKnownUsersWnd m_knownUsersWnd;\n',
        '\tCSearch2Wnd m_search2Wnd;\n\tCFileLibraryWnd m_fileLibraryWnd;\n\tCEmuleNextSettingsWnd m_nextSettingsWnd;\n', path)
    save(path, text, newline)


def patch_cpp() -> None:
    path = SRC / "SearchResultsWnd.cpp"
    text, newline = load(path)

    # Central predicate used by close/delete/icon logic.
    enum_anchor = 'enum ESearchResultImage\n{\n\tsriServerActive,\n\tsriGlobalActive,\n\tsriKadActice,\n\tsriClient,\n\tsriServer,\n\tsriGlobal,\n\tsriKad\n};\n'
    helper = (
        '\nstatic bool IsEmuleNextPersistentView(uint32 searchID)\n'
        '{\n'
        '\treturn searchID == EMULENEXT_KNOWN_USERS_VIEW_ID\n'
        '\t\t|| searchID == EMULENEXT_SEARCH2_VIEW_ID\n'
        '\t\t|| searchID == EMULENEXT_LIBRARY_VIEW_ID\n'
        '\t\t|| searchID == EMULENEXT_SETTINGS_VIEW_ID;\n'
        '}\n'
    )
    text = insert_after(text, enum_anchor, helper, path)

    # Create all permanent views after the already-materialized Known users block.
    known_block_end = '\t\tAddAnchor(m_knownUsersWnd, TOP_LEFT, BOTTOM_RIGHT);\n\t}\n'
    extra_views = (
        '\n\tCRect nextViewRect;\n'
        '\tsearchlistctrl.GetWindowRect(&nextViewRect);\n'
        '\tScreenToClient(&nextViewRect);\n'
        '\n\tif (m_search2Wnd.Create(this)) {\n'
        '\t\tm_search2Wnd.ShowWindow(SW_HIDE);\n'
        '\t\tm_search2Wnd.MoveWindow(&nextViewRect);\n'
        '\t\tAddAnchor(m_search2Wnd, TOP_LEFT, BOTTOM_RIGHT);\n'
        '\t\tSSearchParams *search2 = new SSearchParams;\n'
        '\t\tsearch2->dwSearchID = EMULENEXT_SEARCH2_VIEW_ID;\n'
        '\t\tsearch2->strExpression = _T("Search 2");\n'
        '\t\tsearch2->strSpecialTitle = _T("Search 2");\n'
        '\t\tif (!CreateOrFindTab(search2, false)) delete search2;\n'
        '\t}\n'
        '\n\tif (m_fileLibraryWnd.Create(this)) {\n'
        '\t\tm_fileLibraryWnd.ShowWindow(SW_HIDE);\n'
        '\t\tm_fileLibraryWnd.MoveWindow(&nextViewRect);\n'
        '\t\tAddAnchor(m_fileLibraryWnd, TOP_LEFT, BOTTOM_RIGHT);\n'
        '\t\tSSearchParams *library = new SSearchParams;\n'
        '\t\tlibrary->dwSearchID = EMULENEXT_LIBRARY_VIEW_ID;\n'
        '\t\tlibrary->strExpression = _T("Library");\n'
        '\t\tlibrary->strSpecialTitle = _T("Library");\n'
        '\t\tif (!CreateOrFindTab(library, false)) delete library;\n'
        '\t}\n'
        '\n\tif (m_nextSettingsWnd.Create(this)) {\n'
        '\t\tm_nextSettingsWnd.ShowWindow(SW_HIDE);\n'
        '\t\tm_nextSettingsWnd.MoveWindow(&nextViewRect);\n'
        '\t\tAddAnchor(m_nextSettingsWnd, TOP_LEFT, BOTTOM_RIGHT);\n'
        '\t\tSSearchParams *settings = new SSearchParams;\n'
        '\t\tsettings->dwSearchID = EMULENEXT_SETTINGS_VIEW_ID;\n'
        '\t\tsettings->strExpression = _T("Settings");\n'
        '\t\tsettings->strSpecialTitle = _T("Settings");\n'
        '\t\tif (!CreateOrFindTab(settings, false)) delete settings;\n'
        '\t}\n'
        '\n\t// Start on Known users rather than the last permanent tab created above.\n'
        '\tTCITEM nextTabItem;\n'
        '\tnextTabItem.mask = TCIF_PARAM;\n'
        '\tfor (int nextTab = 0; nextTab < searchselect.GetItemCount(); ++nextTab) {\n'
        '\t\tif (searchselect.GetItem(nextTab, &nextTabItem) && nextTabItem.lParam != NULL\n'
        '\t\t\t&& reinterpret_cast<SSearchParams*>(nextTabItem.lParam)->dwSearchID == EMULENEXT_KNOWN_USERS_VIEW_ID) {\n'
        '\t\t\tsearchselect.SetCurSel(nextTab);\n'
        '\t\t\tShowResults(reinterpret_cast<SSearchParams*>(nextTabItem.lParam));\n'
        '\t\t\tbreak;\n'
        '\t\t}\n'
        '\t}\n'
    )
    text = insert_after(text, known_block_end, extra_views, path)

    text = text.replace(
        'if (pParams->dwSearchID == EMULENEXT_KNOWN_USERS_VIEW_ID || pParams->bClientSharedFiles)',
        'if (IsEmuleNextPersistentView(pParams->dwSearchID) || pParams->bClientSharedFiles)')
    text = text.replace(
        'if (pParams->dwSearchID == EMULENEXT_KNOWN_USERS_VIEW_ID)\n\t\tShowResults(pParams);',
        'if (IsEmuleNextPersistentView(pParams->dwSearchID))\n\t\tShowResults(pParams);')
    text = text.replace(
        'if (uSearchID == EMULENEXT_KNOWN_USERS_VIEW_ID)\n\t\treturn;',
        'if (IsEmuleNextPersistentView(uSearchID))\n\t\treturn;')
    text = text.replace(
        'if (uSearchID == EMULENEXT_KNOWN_USERS_VIEW_ID)\n\t\t\treturn TRUE;',
        'if (IsEmuleNextPersistentView(uSearchID))\n\t\t\treturn TRUE;')
    text = text.replace(
        'if (params->dwSearchID == EMULENEXT_KNOWN_USERS_VIEW_ID)\n\t\t\tcontinue;',
        'if (IsEmuleNextPersistentView(params->dwSearchID))\n\t\t\tcontinue;')

    # Replace ShowResults structurally; the legacy function is long but bounded.
    start_token = 'void CSearchResultsWnd::ShowResults(const SSearchParams *pParams)\n{'
    end_token = '\nvoid CSearchResultsWnd::OnSelChangeTab'
    start = text.find(start_token)
    end = text.find(end_token, start)
    if start < 0 or end < 0:
        raise RuntimeError("Unable to replace SearchResultsWnd::ShowResults")

    show_results = '''void CSearchResultsWnd::ShowResults(const SSearchParams *pParams)
{
\tm_knownUsersWnd.ShowWindow(SW_HIDE);
\tm_search2Wnd.ShowWindow(SW_HIDE);
\tm_fileLibraryWnd.ShowWindow(SW_HIDE);
\tm_nextSettingsWnd.ShowWindow(SW_HIDE);

\tif (IsEmuleNextPersistentView(pParams->dwSearchID)) {
\t\tsearchlistctrl.ShowWindow(SW_HIDE);
\t\tm_ctlFilter.ShowWindow(SW_HIDE);
\t\tGetDlgItem(IDC_SDOWNLOAD)->ShowWindow(SW_HIDE);
\t\tm_cattabs.ShowWindow(SW_HIDE);
\t\tGetDlgItem(IDC_STATIC_DLTOof)->ShowWindow(SW_HIDE);

\t\tif (pParams->dwSearchID == EMULENEXT_KNOWN_USERS_VIEW_ID) {
\t\t\tm_knownUsersWnd.ShowWindow(SW_SHOW);
\t\t\tm_knownUsersWnd.Refresh(true);
\t\t}
\t\telse if (pParams->dwSearchID == EMULENEXT_SEARCH2_VIEW_ID) {
\t\t\tm_search2Wnd.ShowWindow(SW_SHOW);
\t\t\tm_search2Wnd.Refresh(false);
\t\t}
\t\telse if (pParams->dwSearchID == EMULENEXT_LIBRARY_VIEW_ID) {
\t\t\tm_fileLibraryWnd.ShowWindow(SW_SHOW);
\t\t\tm_fileLibraryWnd.Refresh(false);
\t\t}
\t\telse if (pParams->dwSearchID == EMULENEXT_SETTINGS_VIEW_ID) {
\t\t\tm_nextSettingsWnd.ShowWindow(SW_SHOW);
\t\t\tm_nextSettingsWnd.Refresh();
\t\t}
\t\treturn;
\t}

\tsearchlistctrl.ShowWindow(SW_SHOW);
\tif (m_bTabs)
\t\tm_ctlFilter.ShowWindow(SW_SHOW);
\tGetDlgItem(IDC_SDOWNLOAD)->ShowWindow(SW_SHOW);
\tUpdateCatTabs();

\tif (GetKeyState(VK_CONTROL) < 0)
\t\tm_pwndParams->SetParameters(pParams);

\tbool bEnable = (pParams->eType == SearchTypeEd2kServer
\t\t\t\t\t&& pParams->dwSearchID == m_nEd2kSearchID && IsLocalEd2kSearchRunning())
\t\t\t\t\t|| (pParams->eType == SearchTypeEd2kGlobal
\t\t\t\t\t\t&& pParams->dwSearchID == m_nEd2kSearchID && (IsLocalEd2kSearchRunning() || IsGlobalEd2kSearchRunning()))
\t\t\t\t\t|| (pParams->eType == SearchTypeKademlia
\t\t\t\t\t\t&& Kademlia::CSearchManager::IsSearching(pParams->dwSearchID));
\tif (bEnable)
\t\tm_pwndParams->m_ctlCancel.EnableWindow(bEnable);
\tsearchlistctrl.ShowResults(pParams->dwSearchID);
}
'''
    text = text[:start] + show_results + text[end:]
    save(path, text, newline)


def main() -> int:
    patch_project()
    patch_header()
    patch_cpp()
    print("eMule Next visible Search 2 / Library / Settings views active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
