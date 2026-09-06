#!/usr/bin/env python3
"""Materialize eMule Next UI / Navigation Modernization 2.0.

Runs after the product/DPI activators and patches the final source shape only.
The implementation deliberately stays on stable MFC contracts: no new linker
unit, no owner-draw framework and no extra legacy header coupling.
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


def write(path: pathlib.Path, text: str, enc: str) -> None:
    path.write_bytes(text.encode(enc))


def add_include(text: str) -> str:
    marker = '#include "EmuleNextWorkspaceUi.h"'
    if marker in text:
        return text
    anchor = '#include "EmuleNextTheme.h"'
    if anchor not in text:
        raise SystemExit("UI2: theme include anchor missing")
    return text.replace(anchor, anchor + "\n" + marker, 1)


def add_pretranslate_decl(path: pathlib.Path) -> None:
    text, enc = read(path)
    marker = "    virtual BOOL PreTranslateMessage(MSG* message);"
    if marker not in text:
        match = re.search(r"^(\s*)virtual\s+~[^;]+;\s*$", text, re.M)
        if not match:
            raise SystemExit(f"UI2: destructor declaration missing in {path.name}")
        text = text[:match.end()] + "\n" + match.group(1) + "virtual BOOL PreTranslateMessage(MSG* message);" + text[match.end():]
    write(path, text, enc)


def insert_before(text: str, marker: str, block: str, unique: str) -> str:
    if unique in text:
        return text
    pos = text.find(marker)
    if pos < 0:
        raise SystemExit(f"UI2: function marker missing: {marker}")
    return text[:pos] + block + "\n" + text[pos:]


def style_list_after_extended(text: str, control: str, additions: str) -> str:
    if additions.strip() in text:
        return text
    start = text.find(control + ".SetExtendedStyle(")
    if start < 0:
        raise SystemExit(f"UI2: list style anchor missing for {control}")
    end = text.find(";", start)
    if end < 0:
        raise SystemExit(f"UI2: malformed list style for {control}")
    return text[:end + 1] + "\n" + additions + text[end + 1:]


def patch_search() -> None:
    add_pretranslate_decl(SEARCH_H)
    text, enc = read(SEARCH_CPP)
    text = add_include(text)
    text = style_list_after_extended(text, "m_results", "    CEmuleNextWorkspaceUi::StyleList(m_results);")
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
    text = insert_before(text, "BOOL CSearch2Wnd::OnEraseBkgnd", block,
        "BOOL CSearch2Wnd::PreTranslateMessage(MSG* message)")
    write(SEARCH_CPP, text, enc)


def patch_library() -> None:
    add_pretranslate_decl(LIB_H)
    text, enc = read(LIB_CPP)
    text = add_include(text)
    text = style_list_after_extended(text, "m_results", "    CEmuleNextWorkspaceUi::StyleList(m_results);")
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
    text = insert_before(text, "BOOL CFileLibraryWnd::OnEraseBkgnd", block,
        "BOOL CFileLibraryWnd::PreTranslateMessage(MSG* message)")
    write(LIB_CPP, text, enc)


def patch_known() -> None:
    add_pretranslate_decl(KNOWN_H)
    text, enc = read(KNOWN_CPP)
    text = add_include(text)
    text = style_list_after_extended(text, "m_users",
        "    CEmuleNextWorkspaceUi::StyleList(m_users);\n    CEmuleNextWorkspaceUi::StyleList(m_files);")
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
    text = insert_before(text, "BOOL CKnownUsersWnd::OnEraseBkgnd", block,
        "BOOL CKnownUsersWnd::PreTranslateMessage(MSG* message)")
    write(KNOWN_CPP, text, enc)


def patch_settings() -> None:
    add_pretranslate_decl(SETTINGS_H)
    text, enc = read(SETTINGS_CPP)
    text = add_include(text)
    block = r'''BOOL CEmuleNextSettingsWnd::PreTranslateMessage(MSG* message)
{
    if (CEmuleNextWorkspaceUi::IsCtrlKey(message, VK_RETURN)) {
        OnApplyClicked();
        return TRUE;
    }
    return CWnd::PreTranslateMessage(message);
}
'''
    text = insert_before(text, "BOOL CEmuleNextSettingsWnd::OnEraseBkgnd", block,
        "BOOL CEmuleNextSettingsWnd::PreTranslateMessage(MSG* message)")
    write(SETTINGS_CPP, text, enc)


def patch_navigation() -> None:
    text, enc = read(SEARCH_RESULTS)
    text = text.replace('strExpression = _T("Known users")', 'strExpression = _T("Known Users")')
    text = text.replace('strSpecialTitle = _T("Known users")', 'strSpecialTitle = _T("Known Users")')
    text = text.replace('strExpression = _T("Search 2")', 'strExpression = _T("Search")')
    text = text.replace('strSpecialTitle = _T("Search 2")', 'strSpecialTitle = _T("Search")')

    if "preferredNextView" not in text:
        startup = re.compile(
            r"\t// Start on Known users rather than the last permanent tab created above\.\n"
            r"\tTCITEM nextTabItem;.*?\n\t\}\n",
            re.S,
        )
        replacement = '''\t// Restore the last eMule Next workspace; fall back to Known Users.\n\tuint32 preferredNextView = static_cast<uint32>(theApp.GetProfileInt(_T("eMule Next Workspace"), _T("ActiveView"), EMULENEXT_KNOWN_USERS_VIEW_ID));\n\tif (!IsEmuleNextPersistentView(preferredNextView))\n\t\tpreferredNextView = EMULENEXT_KNOWN_USERS_VIEW_ID;\n\tTCITEM nextTabItem;\n\tnextTabItem.mask = TCIF_PARAM;\n\tfor (int nextTab = 0; nextTab < searchselect.GetItemCount(); ++nextTab) {\n\t\tif (searchselect.GetItem(nextTab, &nextTabItem) && nextTabItem.lParam != NULL\n\t\t\t&& reinterpret_cast<SSearchParams*>(nextTabItem.lParam)->dwSearchID == preferredNextView) {\n\t\t\tsearchselect.SetCurSel(nextTab);\n\t\t\tShowResults(reinterpret_cast<SSearchParams*>(nextTabItem.lParam));\n\t\t\tbreak;\n\t\t}\n\t}\n'''
        text, count = startup.subn(lambda _: replacement, text, count=1)
        if count != 1:
            raise SystemExit("UI2: persistent workspace startup block not found")

    handler_pos = text.find("void CSearchResultsWnd::OnSelChangeTab")
    if handler_pos < 0:
        raise SystemExit("UI2: OnSelChangeTab missing")
    tail = text[handler_pos:]
    if "nextSelectedId" not in tail:
        opening = re.compile(r"(void CSearchResultsWnd::OnSelChangeTab\([^\n]*\)\n\{)")
        injected = '''\1\n\tconst int nextSelectedTab = searchselect.GetCurSel();\n\tif (nextSelectedTab >= 0) {\n\t\tTCITEM nextSelectedItem; nextSelectedItem.mask = TCIF_PARAM;\n\t\tif (searchselect.GetItem(nextSelectedTab, &nextSelectedItem) && nextSelectedItem.lParam != NULL) {\n\t\t\tconst uint32 nextSelectedId = reinterpret_cast<SSearchParams*>(nextSelectedItem.lParam)->dwSearchID;\n\t\t\tif (IsEmuleNextPersistentView(nextSelectedId))\n\t\t\t\ttheApp.WriteProfileInt(_T("eMule Next Workspace"), _T("ActiveView"), static_cast<int>(nextSelectedId));\n\t\t}\n\t}\n'''
        text, count = opening.subn(lambda m: m.group(1) + injected[2:], text, count=1)
        if count != 1:
            raise SystemExit("UI2: OnSelChangeTab opening not found")

    write(SEARCH_RESULTS, text, enc)


def main() -> int:
    required = (SEARCH_H, SEARCH_CPP, LIB_H, LIB_CPP, KNOWN_H, KNOWN_CPP,
        SETTINGS_H, SETTINGS_CPP, SEARCH_RESULTS)
    for path in required:
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
