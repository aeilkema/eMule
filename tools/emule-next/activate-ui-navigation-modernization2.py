#!/usr/bin/env python3
"""Materialize eMule Next UI / Navigation Modernization 2.0.

This is deliberately a final-state activator: it runs after Search 2, Library 2,
Known Users, Dashboard and DPI materialization. It patches only stable MFC
contracts and creates a small header-only workspace helper, avoiding new linker
units or additional legacy-header coupling.
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"

SEARCH_H = SRC / "Search2Wnd.h"
SEARCH_CPP = SRC / "Search2Wnd.cpp"
LIB_H = SRC / "FileLibraryWnd.h"
LIB_CPP = SRC / "FileLibraryWnd.cpp"
KNOWN_H = SRC / "KnownUsersWnd.h"
KNOWN_CPP = SRC / "KnownUsersWnd.cpp"
SETTINGS_H = SRC / "EmuleNextSettingsWnd.h"
SETTINGS_CPP = SRC / "EmuleNextSettingsWnd.cpp"
SEARCH_RESULTS = SRC / "SearchResultsWnd.cpp"
HELPER = SRC / "EmuleNextWorkspaceUi.h"

HELPER_TEXT = r'''//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "EmuleNextTheme.h"
#include "EmuleNextUiMetrics.h"
#include <algorithm>

#define EMULENEXT_WORKSPACE_UI2 1

class CEmuleNextWorkspaceUi
{
public:
    static int Margin(HWND wnd) { return CEmuleNextUiMetrics::Scale(wnd, 10); }
    static int Gap(HWND wnd) { return CEmuleNextUiMetrics::Scale(wnd, 7); }
    static int Row(HWND wnd) { return CEmuleNextUiMetrics::Scale(wnd, 27); }
    static int ActionHeight(HWND wnd) { return CEmuleNextUiMetrics::Scale(wnd, 30); }
    static int HeaderHeight(HWND wnd) { return CEmuleNextUiMetrics::Scale(wnd, 22); }
    static int SubtitleHeight(HWND wnd) { return CEmuleNextUiMetrics::Scale(wnd, 18); }

    static void StyleList(CListCtrl& list)
    {
        list.SetExtendedStyle(list.GetExtendedStyle()
            | LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_GRIDLINES);
        if (CEmuleNextTheme::IsDarkMode()) {
            list.SetBkColor(CEmuleNextTheme::BackgroundColor());
            list.SetTextBkColor(CEmuleNextTheme::BackgroundColor());
            list.SetTextColor(CEmuleNextTheme::TextColor());
        }
    }

    static void SelectAllBounded(CListCtrl& list, int maximum = 2000)
    {
        const int count = (std::min)(list.GetItemCount(), maximum);
        for (int i = 0; i < count; ++i)
            list.SetItemState(i, LVIS_SELECTED, LVIS_SELECTED);
    }

    static bool IsCtrlKey(const MSG* message, UINT key)
    {
        return message != NULL && message->message == WM_KEYDOWN
            && message->wParam == key && (::GetKeyState(VK_CONTROL) & 0x8000) != 0;
    }

    static void FocusEdit(CEdit& edit)
    {
        edit.SetFocus();
        edit.SetSel(0, -1);
    }
};
'''


def read(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def write(path: pathlib.Path, text: str, encoding: str) -> None:
    path.write_bytes(text.encode(encoding))


def ensure_include(text: str, include: str, anchor: str) -> str:
    if include in text:
        return text
    if anchor not in text:
        raise SystemExit(f"UI2: include anchor missing: {anchor}")
    return text.replace(anchor, anchor + "\n" + include, 1)


def ensure_pretranslate_decl(path: pathlib.Path) -> None:
    text, enc = read(path)
    marker = "    virtual BOOL PreTranslateMessage(MSG* message);"
    if marker not in text:
        anchor = "    virtual ~"
        pos = text.find(anchor)
        if pos < 0:
            raise SystemExit(f"UI2: destructor anchor missing in {path.name}")
        line_end = text.find("\n", pos)
        text = text[:line_end + 1] + marker + "\n" + text[line_end + 1:]
    write(path, text, enc)


def inject_before_function(text: str, function_marker: str, block: str, unique: str) -> str:
    if unique in text:
        return text
    pos = text.find(function_marker)
    if pos < 0:
        raise SystemExit(f"UI2: function anchor missing: {function_marker}")
    return text[:pos] + block + "\n" + text[pos:]


def patch_search() -> None:
    ensure_pretranslate_decl(SEARCH_H)
    text, enc = read(SEARCH_CPP)
    text = ensure_include(text, '#include "EmuleNextWorkspaceUi.h"', '#include "EmuleNextTheme.h"')
    if "CEmuleNextWorkspaceUi::StyleList(m_results);" not in text:
        anchor = "m_results.SetExtendedStyle("
        pos = text.find(anchor)
        if pos < 0:
            raise SystemExit("UI2: Search2 list style anchor missing")
        end = text.find(";", pos)
        text = text[:end + 1] + "\n    CEmuleNextWorkspaceUi::StyleList(m_results);" + text[end + 1:]
    block = r'''BOOL CSearch2Wnd::PreTranslateMessage(MSG* message)
{
    if (CEmuleNextWorkspaceUi::IsCtrlKey(message, 'F')) {
        CEmuleNextWorkspaceUi::FocusEdit(m_query);
        return TRUE;
    }
    if (CEmuleNextWorkspaceUi::IsCtrlKey(message, 'A') && GetFocus() == &m_results) {
        CEmuleNextWorkspaceUi::SelectAllBounded(m_results);
        return TRUE;
    }
    if (message != NULL && message->message == WM_KEYDOWN && message->wParam == VK_RETURN
        && GetFocus() == &m_query) {
        OnSearchClicked();
        return TRUE;
    }
    return CWnd::PreTranslateMessage(message);
}
'''
    text = inject_before_function(text, "BOOL CSearch2Wnd::OnEraseBkgnd", block, "BOOL CSearch2Wnd::PreTranslateMessage(MSG* message)")
    # clearer workspace terminology; harmless if the final product already uses it
    text = text.replace('_T("Search 2")', '_T("Search")')
    write(SEARCH_CPP, text, enc)


def patch_library() -> None:
    ensure_pretranslate_decl(LIB_H)
    text, enc = read(LIB_CPP)
    text = ensure_include(text, '#include "EmuleNextWorkspaceUi.h"', '#include "EmuleNextTheme.h"')
    if "CEmuleNextWorkspaceUi::StyleList(m_results);" not in text:
        anchor = "m_results.SetExtendedStyle("
        pos = text.find(anchor)
        if pos < 0:
            raise SystemExit("UI2: Library list style anchor missing")
        end = text.find(";", pos)
        text = text[:end + 1] + "\n    CEmuleNextWorkspaceUi::StyleList(m_results);" + text[end + 1:]
    block = r'''BOOL CFileLibraryWnd::PreTranslateMessage(MSG* message)
{
    if (CEmuleNextWorkspaceUi::IsCtrlKey(message, 'F')) {
        CEmuleNextWorkspaceUi::FocusEdit(m_textFilter);
        return TRUE;
    }
    if (CEmuleNextWorkspaceUi::IsCtrlKey(message, 'A') && GetFocus() == &m_results) {
        CEmuleNextWorkspaceUi::SelectAllBounded(m_results);
        return TRUE;
    }
    if (message != NULL && message->message == WM_KEYDOWN && message->wParam == VK_F5) {
        OnRefreshClicked();
        return TRUE;
    }
    return CWnd::PreTranslateMessage(message);
}
'''
    text = inject_before_function(text, "BOOL CFileLibraryWnd::OnEraseBkgnd", block, "BOOL CFileLibraryWnd::PreTranslateMessage(MSG* message)")
    write(LIB_CPP, text, enc)


def patch_known() -> None:
    ensure_pretranslate_decl(KNOWN_H)
    text, enc = read(KNOWN_CPP)
    text = ensure_include(text, '#include "EmuleNextWorkspaceUi.h"', '#include "EmuleNextTheme.h"')
    if "CEmuleNextWorkspaceUi::StyleList(m_users);" not in text:
        anchor = "m_users.SetExtendedStyle("
        pos = text.find(anchor)
        if pos < 0:
            raise SystemExit("UI2: Known Users list style anchor missing")
        end = text.find(";", pos)
        text = text[:end + 1] + "\n    CEmuleNextWorkspaceUi::StyleList(m_users);\n    CEmuleNextWorkspaceUi::StyleList(m_files);" + text[end + 1:]
    block = r'''BOOL CKnownUsersWnd::PreTranslateMessage(MSG* message)
{
    if (CEmuleNextWorkspaceUi::IsCtrlKey(message, 'F')) {
        CEmuleNextWorkspaceUi::FocusEdit(m_search);
        return TRUE;
    }
    if (message != NULL && message->message == WM_KEYDOWN && message->wParam == VK_F5) {
        OnRefreshClicked();
        return TRUE;
    }
    return CWnd::PreTranslateMessage(message);
}
'''
    text = inject_before_function(text, "BOOL CKnownUsersWnd::OnEraseBkgnd", block, "BOOL CKnownUsersWnd::PreTranslateMessage(MSG* message)")
    write(KNOWN_CPP, text, enc)


def patch_settings() -> None:
    ensure_pretranslate_decl(SETTINGS_H)
    text, enc = read(SETTINGS_CPP)
    text = ensure_include(text, '#include "EmuleNextWorkspaceUi.h"', '#include "EmuleNextTheme.h"')
    block = r'''BOOL CEmuleNextSettingsWnd::PreTranslateMessage(MSG* message)
{
    if (CEmuleNextWorkspaceUi::IsCtrlKey(message, VK_RETURN)) {
        OnApplyClicked();
        return TRUE;
    }
    return CWnd::PreTranslateMessage(message);
}
'''
    text = inject_before_function(text, "BOOL CEmuleNextSettingsWnd::OnEraseBkgnd", block, "BOOL CEmuleNextSettingsWnd::PreTranslateMessage(MSG* message)")
    write(SETTINGS_CPP, text, enc)


def patch_navigation() -> None:
    text, enc = read(SEARCH_RESULTS)
    # Consistent workspace labels; persistent views remain normal tab items so
    # all legacy search routing stays intact.
    text = text.replace('strExpression = _T("Known users")', 'strExpression = _T("Known Users")')
    text = text.replace('strSpecialTitle = _T("Known users")', 'strSpecialTitle = _T("Known Users")')
    text = text.replace('strExpression = _T("Search 2")', 'strExpression = _T("Search")')
    text = text.replace('strSpecialTitle = _T("Search 2")', 'strSpecialTitle = _T("Search")')

    # Restore the last selected eMule Next workspace. Legacy search tabs are not
    # persisted through this key and therefore keep their existing behavior.
    old = '''\t// Start on Known users rather than the last permanent tab created above.\n\tTCITEM nextTabItem;\n\tnextTabItem.mask = TCIF_PARAM;\n\tfor (int nextTab = 0; nextTab < searchselect.GetItemCount(); ++nextTab) {\n\t\tif (searchselect.GetItem(nextTab, &nextTabItem) && nextTabItem.lParam != NULL\n\t\t\t&& reinterpret_cast<SSearchParams*>(nextTabItem.lParam)->dwSearchID == EMULENEXT_KNOWN_USERS_VIEW_ID) {\n\t\t\tsearchselect.SetCurSel(nextTab);\n\t\t\tShowResults(reinterpret_cast<SSearchParams*>(nextTabItem.lParam));\n\t\t\tbreak;\n\t\t}\n\t}\n'''
    new = '''\t// Restore the last eMule Next workspace; fall back to Known Users.\n\tuint32 preferredNextView = static_cast<uint32>(theApp.GetProfileInt(_T("eMule Next Workspace"), _T("ActiveView"), EMULENEXT_KNOWN_USERS_VIEW_ID));\n\tif (!IsEmuleNextPersistentView(preferredNextView))\n\t\tpreferredNextView = EMULENEXT_KNOWN_USERS_VIEW_ID;\n\tTCITEM nextTabItem;\n\tnextTabItem.mask = TCIF_PARAM;\n\tfor (int nextTab = 0; nextTab < searchselect.GetItemCount(); ++nextTab) {\n\t\tif (searchselect.GetItem(nextTab, &nextTabItem) && nextTabItem.lParam != NULL\n\t\t\t&& reinterpret_cast<SSearchParams*>(nextTabItem.lParam)->dwSearchID == preferredNextView) {\n\t\t\tsearchselect.SetCurSel(nextTab);\n\t\t\tShowResults(reinterpret_cast<SSearchParams*>(nextTabItem.lParam));\n\t\t\tbreak;\n\t\t}\n\t}\n'''
    if "preferredNextView" not in text:
        if old not in text:
            raise SystemExit("UI2: persistent workspace startup anchor missing")
        text = text.replace(old, new, 1)

    # Save new persistent-view selection at the start of the existing handler.
    if "eMule Next Workspace\"), _T(\"ActiveView\")" not in text[text.find("void CSearchResultsWnd::OnSelChangeTab"):]:
        pattern = re.compile(r"(void CSearchResultsWnd::OnSelChangeTab\([^\n]*\)\n\{)")
        addition = r'''\1
\tconst int nextSelectedTab = searchselect.GetCurSel();
\tif (nextSelectedTab >= 0) {
\t\tTCITEM nextSelectedItem; nextSelectedItem.mask = TCIF_PARAM;
\t\tif (searchselect.GetItem(nextSelectedTab, &nextSelectedItem) && nextSelectedItem.lParam != NULL) {
\t\t\tconst uint32 nextSelectedId = reinterpret_cast<SSearchParams*>(nextSelectedItem.lParam)->dwSearchID;
\t\t\tif (IsEmuleNextPersistentView(nextSelectedId))
\t\t\t\ttheApp.WriteProfileInt(_T("eMule Next Workspace"), _T("ActiveView"), static_cast<int>(nextSelectedId));
\t\t}
\t}
'''
        text, count = pattern.subn(addition, text, count=1)
        if count != 1:
            raise SystemExit("UI2: OnSelChangeTab handler anchor missing")

    write(SEARCH_RESULTS, text, enc)


def main() -> int:
    for path in (SEARCH_H, SEARCH_CPP, LIB_H, LIB_CPP, KNOWN_H, KNOWN_CPP, SETTINGS_H, SETTINGS_CPP, SEARCH_RESULTS):
        if not path.exists():
            raise SystemExit(f"UI2: source missing: {path}")
    HELPER.write_text(HELPER_TEXT, encoding="utf-8")
    patch_search()
    patch_library()
    patch_known()
    patch_settings()
    patch_navigation()
    print("eMule Next UI / Navigation Modernization 2.0 materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
