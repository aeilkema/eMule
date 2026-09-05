#!/usr/bin/env python3
"""Add explicit user actions to the eMule Next Dashboard workspace."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "EmuleNextDashboardWnd.cpp"


def load() -> tuple[str, str]:
    raw = PATH.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    newline = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n"), newline


def save(text: str, newline: str) -> None:
    if newline != "\n":
        text = text.replace("\n", newline)
    PATH.write_bytes(text.encode("latin-1"))


def main() -> int:
    text, newline = load()

    enum_old = '''        IDC_EN_DASH_DOWNLOADS,\n        IDC_EN_DASH_DETAILS\n'''
    enum_new = '''        IDC_EN_DASH_DOWNLOADS,\n        IDC_EN_DASH_OPEN_TRANSFERS,\n        IDC_EN_DASH_OPEN_SOURCES,\n        IDC_EN_DASH_PAUSE_RESUME,\n        IDC_EN_DASH_PRIORITY_HIGH,\n        IDC_EN_DASH_PRIORITY_NORMAL,\n        IDC_EN_DASH_REFRESH_NOW,\n        IDC_EN_DASH_DETAILS\n'''
    if 'IDC_EN_DASH_OPEN_TRANSFERS' not in text:
        if enum_old not in text:
            raise RuntimeError('Dashboard action ID anchor not found')
        text = text.replace(enum_old, enum_new, 1)

    map_anchor = '''    ON_BN_CLICKED(IDC_EN_DASH_FILTER_ACTIVE, OnFilterActive)\n'''
    map_add = '''    ON_BN_CLICKED(IDC_EN_DASH_OPEN_TRANSFERS, OnOpenTransfers)\n    ON_BN_CLICKED(IDC_EN_DASH_OPEN_SOURCES, OnOpenSources)\n    ON_BN_CLICKED(IDC_EN_DASH_PAUSE_RESUME, OnPauseResume)\n    ON_BN_CLICKED(IDC_EN_DASH_PRIORITY_HIGH, OnPriorityHigh)\n    ON_BN_CLICKED(IDC_EN_DASH_PRIORITY_NORMAL, OnPriorityNormal)\n    ON_BN_CLICKED(IDC_EN_DASH_REFRESH_NOW, OnRefreshNow)\n'''
    if 'ON_BN_CLICKED(IDC_EN_DASH_OPEN_TRANSFERS' not in text:
        if map_anchor not in text:
            raise RuntimeError('Dashboard action message-map anchor not found')
        text = text.replace(map_anchor, map_anchor + map_add, 1)

    create_old = '''        || !m_downloads.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS,\n            empty, this, IDC_EN_DASH_DOWNLOADS)\n        || !m_details.Create(_T("Select a download for detailed intelligence."),\n            WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this, IDC_EN_DASH_DETAILS)) {\n'''
    create_new = '''        || !m_downloads.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS,\n            empty, this, IDC_EN_DASH_DOWNLOADS)\n        || !m_openTransfers.Create(_T("Open in Transfers"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DASH_OPEN_TRANSFERS)\n        || !m_openSources.Create(_T("Open + sources"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DASH_OPEN_SOURCES)\n        || !m_pauseResume.Create(_T("Pause / Resume"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DASH_PAUSE_RESUME)\n        || !m_priorityHigh.Create(_T("Priority high"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DASH_PRIORITY_HIGH)\n        || !m_priorityNormal.Create(_T("Priority normal"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DASH_PRIORITY_NORMAL)\n        || !m_refreshNow.Create(_T("Refresh"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DASH_REFRESH_NOW)\n        || !m_details.Create(_T("Select a download for detailed intelligence."),\n            WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this, IDC_EN_DASH_DETAILS)) {\n'''
    if '!m_openTransfers.Create' not in text:
        if create_old not in text:
            raise RuntimeError('Dashboard action Create anchor not found')
        text = text.replace(create_old, create_new, 1)

    font_anchor = '''    m_downloads.SetFont(font);\n    m_details.SetFont(font);\n'''
    font_new = '''    m_downloads.SetFont(font);\n    m_openTransfers.SetFont(font);\n    m_openSources.SetFont(font);\n    m_pauseResume.SetFont(font);\n    m_priorityHigh.SetFont(font);\n    m_priorityNormal.SetFont(font);\n    m_refreshNow.SetFont(font);\n    m_details.SetFont(font);\n'''
    if 'm_openTransfers.SetFont(font);' not in text:
        if font_anchor not in text:
            raise RuntimeError('Dashboard action font anchor not found')
        text = text.replace(font_anchor, font_new, 1)

    layout_old = '''    const int listTop = filterTop + filterHeight + 5;\n    const int listHeight = std::max(80, cy - listTop - detailsHeight - margin - 6);\n    m_downloads.MoveWindow(margin, listTop, std::max(0, cx - margin * 2), listHeight);\n    m_details.MoveWindow(margin, listTop + listHeight + 6,\n        std::max(0, cx - margin * 2), std::max(0, cy - (listTop + listHeight + 6) - margin));\n'''
    layout_new = '''    const int actionHeight = 25;\n    const int actionGap = 5;\n    const int listTop = filterTop + filterHeight + 5;\n    const int listHeight = std::max(80, cy - listTop - detailsHeight - actionHeight - margin - 12);\n    m_downloads.MoveWindow(margin, listTop, std::max(0, cx - margin * 2), listHeight);\n\n    const int actionTop = listTop + listHeight + 5;\n    const int actionWidth = std::max(84, std::min(125, (cx - margin * 2 - actionGap * 5) / 6));\n    int actionX = margin;\n    CButton* actions[] = {\n        &m_openTransfers, &m_openSources, &m_pauseResume,\n        &m_priorityHigh, &m_priorityNormal, &m_refreshNow\n    };\n    for (int i = 0; i < _countof(actions); ++i) {\n        actions[i]->MoveWindow(actionX, actionTop, actionWidth, actionHeight);\n        actionX += actionWidth + actionGap;\n    }\n\n    const int detailsTop = actionTop + actionHeight + 5;\n    m_details.MoveWindow(margin, detailsTop,\n        std::max(0, cx - margin * 2), std::max(0, cy - detailsTop - margin));\n'''
    if 'CButton* actions[]' not in text:
        if layout_old not in text:
            raise RuntimeError('Dashboard action layout anchor not found')
        text = text.replace(layout_old, layout_new, 1)

    old_enter = '''        CPartFile* file = GetSelectedFile();\n        if (file != NULL)\n            GetParent()->SendMessage(WM_EN_DASH_OPEN_FILE, 0, reinterpret_cast<LPARAM>(file));\n        return TRUE;\n'''
    new_enter = '''        JumpToTransfers(false);\n        return TRUE;\n'''
    if 'JumpToTransfers(false);' not in text:
        if old_enter not in text:
            raise RuntimeError('Dashboard Enter navigation anchor not found')
        text = text.replace(old_enter, new_enter, 1)

    null_details_old = '''    if (file == NULL) {\n        m_details.SetWindowText(_T("Select a download for detailed intelligence. Double-click or press Enter to open it in Transfers."));\n        return;\n    }\n'''
    null_details_new = '''    if (file == NULL) {\n        m_details.SetWindowText(_T("Select a download for detailed intelligence. Double-click or press Enter to open it in Transfers."));\n        UpdateActionButtons();\n        return;\n    }\n'''
    if 'UpdateActionButtons();\n        return;' not in text:
        if null_details_old not in text:
            raise RuntimeError('Dashboard empty-details anchor not found')
        text = text.replace(null_details_old, null_details_new, 1)

    details_anchor = '''    m_details.SetWindowText(details);\n}\n\nvoid CEmuleNextDashboardWnd::OnFilterAll()\n'''
    methods = '''    m_details.SetWindowText(details);\n    UpdateActionButtons();\n}\n\nvoid CEmuleNextDashboardWnd::UpdateActionButtons()\n{\n    CPartFile* file = GetSelectedFile();\n    const BOOL hasFile = file != NULL ? TRUE : FALSE;\n    m_openTransfers.EnableWindow(hasFile);\n    m_openSources.EnableWindow(hasFile);\n    m_priorityHigh.EnableWindow(hasFile);\n    m_priorityNormal.EnableWindow(hasFile);\n    if (file == NULL) {\n        m_pauseResume.EnableWindow(FALSE);\n        m_pauseResume.SetWindowText(_T("Pause / Resume"));\n        return;\n    }\n\n    if (file->CanResumeFile()) {\n        m_pauseResume.EnableWindow(TRUE);\n        m_pauseResume.SetWindowText(_T("Resume"));\n    } else if (file->CanPauseFile()) {\n        m_pauseResume.EnableWindow(TRUE);\n        m_pauseResume.SetWindowText(_T("Pause"));\n    } else {\n        m_pauseResume.EnableWindow(FALSE);\n        m_pauseResume.SetWindowText(_T("Pause / Resume"));\n    }\n}\n\nvoid CEmuleNextDashboardWnd::JumpToTransfers(bool expandSources)\n{\n    CPartFile* file = GetSelectedFile();\n    if (file != NULL && GetParent() != NULL)\n        GetParent()->SendMessage(WM_EN_DASH_OPEN_FILE, expandSources ? 1 : 0, reinterpret_cast<LPARAM>(file));\n}\n\nvoid CEmuleNextDashboardWnd::OnOpenTransfers()\n{\n    JumpToTransfers(false);\n}\n\nvoid CEmuleNextDashboardWnd::OnOpenSources()\n{\n    JumpToTransfers(true);\n}\n\nvoid CEmuleNextDashboardWnd::OnPauseResume()\n{\n    CPartFile* file = GetSelectedFile();\n    if (file == NULL)\n        return;\n    if (file->CanResumeFile())\n        file->ResumeFile();\n    else if (file->CanPauseFile())\n        file->PauseFile();\n    Refresh();\n}\n\nvoid CEmuleNextDashboardWnd::OnPriorityHigh()\n{\n    CPartFile* file = GetSelectedFile();\n    if (file == NULL)\n        return;\n    file->SetAutoDownPriority(false);\n    file->SetDownPriority(PR_HIGH);\n    Refresh();\n}\n\nvoid CEmuleNextDashboardWnd::OnPriorityNormal()\n{\n    CPartFile* file = GetSelectedFile();\n    if (file == NULL)\n        return;\n    file->SetAutoDownPriority(false);\n    file->SetDownPriority(PR_NORMAL);\n    Refresh();\n}\n\nvoid CEmuleNextDashboardWnd::OnRefreshNow()\n{\n    Refresh();\n}\n\nvoid CEmuleNextDashboardWnd::OnFilterAll()\n'''
    if 'void CEmuleNextDashboardWnd::UpdateActionButtons()' not in text:
        if details_anchor not in text:
            raise RuntimeError('Dashboard action methods anchor not found')
        text = text.replace(details_anchor, methods, 1)

    dbl_old = '''    CPartFile* file = GetSelectedFile();\n    if (file != NULL)\n        GetParent()->SendMessage(WM_EN_DASH_OPEN_FILE, 0, reinterpret_cast<LPARAM>(file));\n    if (result != NULL)\n'''
    dbl_new = '''    JumpToTransfers(true);\n    if (result != NULL)\n'''
    if 'void CEmuleNextDashboardWnd::OnDownloadDoubleClick' in text and 'JumpToTransfers(true);' not in text.split('void CEmuleNextDashboardWnd::OnDownloadDoubleClick', 1)[1].split('}', 1)[0]:
        if dbl_old not in text:
            raise RuntimeError('Dashboard double-click navigation anchor not found')
        text = text.replace(dbl_old, dbl_new, 1)

    save(text, newline)
    print('eMule Next Dashboard explicit file actions active')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
