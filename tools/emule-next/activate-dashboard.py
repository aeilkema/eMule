#!/usr/bin/env python3
"""Activate the live eMule Next Dashboard inside the Transfers view selector."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
_NEWLINES: dict[pathlib.Path, str] = {}


def load(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    _NEWLINES[path] = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n")


def save(path: pathlib.Path, text: str) -> None:
    newline = _NEWLINES.get(path, "\n")
    if newline != "\n":
        text = text.replace("\n", newline)
    path.write_bytes(text.encode("latin-1"))


def insert_after(text: str, anchor: str, addition: str, path: pathlib.Path, marker: str) -> str:
    if marker in text:
        return text
    if anchor not in text:
        raise RuntimeError(f"Dashboard anchor not found in {path}: {anchor!r}")
    return text.replace(anchor, anchor + addition, 1)


def replace_once(text: str, old: str, new: str, path: pathlib.Path, marker: str) -> str:
    if marker in text:
        return text
    if old not in text:
        raise RuntimeError(f"Dashboard replacement anchor not found in {path}: {old[:100]!r}")
    return text.replace(old, new, 1)


def patch_part_file() -> None:
    path = SRC / "PartFile.h"
    text = load(path)
    anchor = '\tUINT\tGetAvailablePartCount() const\t\t\t\t{ return (status == PS_COMPLETING || status == PS_COMPLETE) ? GetPartCount() : availablePartsCount; }\n'
    addition = '\tuint16\tGetPartSourceFrequency(UINT part) const\t\t{ return part < static_cast<UINT>(m_SrcPartFrequency.GetSize()) ? m_SrcPartFrequency[part] : 0; } // eMule Next live intelligence\n'
    text = insert_after(text, anchor, addition, path, 'GetPartSourceFrequency(UINT part)')
    save(path, text)


def patch_transfer_header() -> None:
    path = SRC / "TransferWnd.h"
    text = load(path)
    text = insert_after(text, '#include "DropDownButton.h"\n', '#include "EmuleNextDashboardWnd.h"\n', path, 'EmuleNextDashboardWnd.h')
    text = replace_once(text,
        '\t\tw1iOnQueue,\n\t\tw1iClientsKnown\n',
        '\t\tw1iOnQueue,\n\t\tw1iClientsKnown,\n\t\tw1iNextDashboard\n',
        path, 'w1iNextDashboard')
    text = insert_after(text, '\tCDownloadClientsCtrl\tdownloadclientsctrl;\n', '\tCEmuleNextDashboardWnd\tm_nextDashboard;\n', path, 'm_nextDashboard;')
    text = insert_after(text, '\tvoid\tShowList(uint32 dwListIDC);\n', '\tvoid\tShowNextDashboard();\n', path, 'ShowNextDashboard();')
    save(path, text)


def patch_transfer_cpp() -> None:
    path = SRC / "TransferWnd.cpp"
    text = load(path)

    constants = '''\nnamespace\n{\n\tconst UINT MP_NEXT_DASHBOARD = 0xEE20;\n\tconst uint32 EMULENEXT_DASHBOARD_VIEW = 0xE1D00001u;\n}\n'''
    text = insert_after(text, '#define\tWND2_NUM_BUTTONS\t4\n', constants, path, 'EMULENEXT_DASHBOARD_VIEW')
    text = text.replace('#define\tWND1_NUM_BUTTONS\t6', '#define\tWND1_NUM_BUTTONS\t7', 1)

    init_anchor = '\tdownloadclientsctrl.Init();\n'
    init_add = '\tif (!m_nextDashboard.Create(this))\n\t\tAddDebugLogLine(false, _T("eMule Next Dashboard creation failed"));\n\tm_nextDashboard.ShowWindow(SW_HIDE);\n'
    text = insert_after(text, init_anchor, init_add, path, 'Dashboard creation failed')

    old_lists = '''\tstatic const uint32 uLists[6] = {\n\t\t  IDC_DOWNLOADLIST + IDC_UPLOADLIST\t//0\n\t\t, IDC_DOWNLOADLIST\t\t\t\t\t//1\n\t\t, IDC_UPLOADLIST\t\t\t\t\t//2\n\t\t, IDC_QUEUELIST\t\t\t\t\t\t//3\n\t\t, IDC_DOWNLOADCLIENTS\t\t\t\t//4\n\t\t, IDC_CLIENTLIST};\t\t\t\t\t//5\n\tUINT uid = thePrefs.GetTransferWnd1();\n\tm_dwShowListIDC = uLists[uid > 5 ? 0 : uid];\n'''
    new_lists = '''\tstatic const uint32 uLists[7] = {\n\t\t  IDC_DOWNLOADLIST + IDC_UPLOADLIST\t//0\n\t\t, IDC_DOWNLOADLIST\t\t\t\t\t//1\n\t\t, IDC_UPLOADLIST\t\t\t\t\t//2\n\t\t, IDC_QUEUELIST\t\t\t\t\t\t//3\n\t\t, IDC_DOWNLOADCLIENTS\t\t\t\t//4\n\t\t, IDC_CLIENTLIST\t\t\t\t\t//5\n\t\t, EMULENEXT_DASHBOARD_VIEW};\t\t\t//6\n\tUINT uid = thePrefs.GetTransferWnd1();\n\tm_dwShowListIDC = uLists[uid > 6 ? 0 : uid];\n'''
    text = replace_once(text, old_lists, new_lists, path, 'static const uint32 uLists[7]')

    icon_anchor = '\timl.Add(CTempIconLoader(_T("ClientsKnown")));\n'
    text = insert_after(text, icon_anchor, '\timl.Add(CTempIconLoader(_T("DownloadFiles"))); // eMule Next Dashboard\n', path, '// eMule Next Dashboard')

    localize_old = '''\tif (m_dwShowListIDC == IDC_DOWNLOADLIST + IDC_UPLOADLIST)\n\t\tShowSplitWindow();\n\telse\n\t\tShowList(m_dwShowListIDC);\n'''
    localize_new = '''\tif (m_dwShowListIDC == IDC_DOWNLOADLIST + IDC_UPLOADLIST)\n\t\tShowSplitWindow();\n\telse if (m_dwShowListIDC == EMULENEXT_DASHBOARD_VIEW)\n\t\tShowNextDashboard();\n\telse\n\t\tShowList(m_dwShowListIDC);\n'''
    text = replace_once(text, localize_old, localize_new, path, 'else if (m_dwShowListIDC == EMULENEXT_DASHBOARD_VIEW)')

    text = insert_after(text,
        '\tm_btnWnd1.SetBtnText(MP_VIEW1_CLIENTS, GetResString(IDS_CLIENTLIST));\n',
        '\tm_btnWnd1.SetBtnText(MP_NEXT_DASHBOARD, _T("eMule Next Dashboard"));\n',
        path, 'SetBtnText(MP_NEXT_DASHBOARD')

    command_anchor = '''\tcase MP_VIEW1_CLIENTS:\n\t\tShowList(IDC_CLIENTLIST);\n\t\tbreak;\n'''
    command_add = '''\tcase MP_NEXT_DASHBOARD:\n\t\tShowNextDashboard();\n\t\tbreak;\n'''
    text = insert_after(text, command_anchor, command_add, path, 'case MP_NEXT_DASHBOARD:')

    # Any legacy list/split view must hide the dashboard first.
    text = insert_after(text, 'void CTransferWnd::ShowList(uint32 dwListIDC)\n{\n', '\tm_nextDashboard.ShowWindow(SW_HIDE);\n', path, 'ShowList(uint32 dwListIDC)\n{\n\tm_nextDashboard')
    text = insert_after(text, 'void CTransferWnd::ShowSplitWindow(bool bReDraw)\n{\n', '\tm_nextDashboard.ShowWindow(SW_HIDE);\n', path, 'ShowSplitWindow(bool bReDraw)\n{\n\tm_nextDashboard')

    dashboard_method_anchor = 'void CTransferWnd::ShowSplitWindow(bool bReDraw)\n'
    dashboard_method = '''void CTransferWnd::ShowNextDashboard()\n{\n\tif (!::IsWindow(m_nextDashboard.m_hWnd))\n\t\treturn;\n\n\tRECT rcWnd;\n\tGetWindowRect(&rcWnd);\n\tScreenToClient(&rcWnd);\n\tRECT rcDash;\n\tdownloadlistctrl.GetWindowRect(&rcDash);\n\tScreenToClient(&rcDash);\n\trcDash.top = WND1_BUTTON_YOFF + WND1_BUTTON_HEIGHT + 1;\n\trcDash.bottom = rcWnd.bottom - WND1_BUTTON_HEIGHT;\n\n\tm_wndSplitter.DestroyWindow();\n\tm_btnWnd2.ShowWindow(SW_HIDE);\n\tuploadlistctrl.ShowWindow(SW_HIDE);\n\tqueuelistctrl.ShowWindow(SW_HIDE);\n\tdownloadclientsctrl.ShowWindow(SW_HIDE);\n\tclientlistctrl.ShowWindow(SW_HIDE);\n\tdownloadlistctrl.ShowWindow(SW_HIDE);\n\tm_dlTab.ShowWindow(SW_HIDE);\n\tGetDlgItem(IDC_QUEUE_REFRESH_BUTTON)->ShowWindow(SW_HIDE);\n\ttheApp.emuledlg->transferwnd->ShowToolbar(false);\n\n\tm_dwShowListIDC = EMULENEXT_DASHBOARD_VIEW;\n\tm_nextDashboard.MoveWindow(&rcDash);\n\tm_nextDashboard.ShowWindow(SW_SHOW);\n\tm_nextDashboard.Refresh();\n\tm_btnWnd1.SetWindowText(_T("eMule Next Dashboard"));\n\tm_btnWnd1.CheckButton(MP_NEXT_DASHBOARD);\n\tSetWnd1Icon(w1iNextDashboard);\n\tthePrefs.SetTransferWnd1(6);\n\n\tRemoveAnchor(m_nextDashboard);\n\tAddAnchor(m_nextDashboard, TOP_LEFT, BOTTOM_RIGHT);\n}\n\n'''
    if 'void CTransferWnd::ShowNextDashboard()' not in text:
        if dashboard_method_anchor not in text:
            raise RuntimeError('ShowSplitWindow method anchor missing')
        text = text.replace(dashboard_method_anchor, dashboard_method + dashboard_method_anchor, 1)

    cycle_anchor = '''\tcase IDC_CLIENTLIST:\n\t\tShowSplitWindow();\n\t\tbreak;\n\tcase IDC_UPLOADLIST + IDC_DOWNLOADLIST:\n\t\tShowList(IDC_DOWNLOADLIST);\n'''
    cycle_new = '''\tcase IDC_CLIENTLIST:\n\t\tShowNextDashboard();\n\t\tbreak;\n\tcase EMULENEXT_DASHBOARD_VIEW:\n\t\tShowSplitWindow();\n\t\tbreak;\n\tcase IDC_UPLOADLIST + IDC_DOWNLOADLIST:\n\t\tShowList(IDC_DOWNLOADLIST);\n'''
    text = replace_once(text, cycle_anchor, cycle_new, path, 'case EMULENEXT_DASHBOARD_VIEW:')

    dropdown_anchor = '''\tif (!thePrefs.IsKnownClientListDisabled())\n\t\tmenu.AppendMenu(MF_STRING | (m_dwShowListIDC == IDC_CLIENTLIST ? MF_GRAYED : 0), MP_VIEW1_CLIENTS, GetResString(IDS_CLIENTLIST), _T("ClientsKnown"));\n'''
    dropdown_add = '\tmenu.AppendMenu(MF_SEPARATOR);\n\tmenu.AppendMenu(MF_STRING | (m_dwShowListIDC == EMULENEXT_DASHBOARD_VIEW ? MF_GRAYED : 0), MP_NEXT_DASHBOARD, _T("eMule Next Dashboard"), _T("DownloadFiles"));\n'
    text = insert_after(text, dropdown_anchor, dropdown_add, path, 'MP_NEXT_DASHBOARD, _T("eMule Next Dashboard")')

    toolbar_anchor = '''\t\tatb1[6].iBitmap = w1iClientsKnown;\n\t\tatb1[6].idCommand = MP_VIEW1_CLIENTS;\n\t\tatb1[6].fsState = thePrefs.IsKnownClientListDisabled() ? 0 : TBSTATE_ENABLED;\n\t\tatb1[6].fsStyle = BTNS_BUTTON | BTNS_CHECKGROUP | BTNS_AUTOSIZE;\n\t\tatb1[6].iString = -1;\n'''
    toolbar_add = '''\n\t\tatb1[7].iBitmap = w1iNextDashboard;\n\t\tatb1[7].idCommand = MP_NEXT_DASHBOARD;\n\t\tatb1[7].fsState = TBSTATE_ENABLED;\n\t\tatb1[7].fsStyle = BTNS_BUTTON | BTNS_CHECKGROUP | BTNS_AUTOSIZE;\n\t\tatb1[7].iString = -1;\n'''
    text = insert_after(text, toolbar_anchor, toolbar_add, path, 'atb1[7].idCommand = MP_NEXT_DASHBOARD')

    save(path, text)


def patch_project() -> None:
    path = SRC / "emule.vcxproj"
    text = load(path)
    compile_anchor = '    <ClCompile Include="DownloadListCtrl.cpp" />\n'
    text = insert_after(text, compile_anchor, '    <ClCompile Include="EmuleNextDashboardWnd.cpp" />\n', path, 'EmuleNextDashboardWnd.cpp')

    # Header ItemGroup is later in the project; anchor on a stable existing header.
    header_anchor = '    <ClInclude Include="DownloadListCtrl.h" />\n'
    text = insert_after(text, header_anchor, '    <ClInclude Include="EmuleNextDashboardWnd.h" />\n', path, 'EmuleNextDashboardWnd.h')
    save(path, text)


def main() -> int:
    for required in (SRC / 'EmuleNextDashboardWnd.cpp', SRC / 'EmuleNextDashboardWnd.h'):
        if not required.exists():
            raise RuntimeError(f'Missing Dashboard source: {required}')
    patch_part_file()
    patch_transfer_header()
    patch_transfer_cpp()
    patch_project()
    print('eMule Next Transfers Dashboard active')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
