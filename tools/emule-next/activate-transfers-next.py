#!/usr/bin/env python3
"""Finish the first eMule Next Transfers modernization slice.

The legacy CMuleListCtrl caches system colours for owner-drawn controls, so
setting native LISTVIEW colours alone is not enough for dark mode. This patch
makes that cache use the central eMule Next palette and refreshes it whenever
the theme engine reapplies a list-view theme.

Known Clients is also upgraded to expose the persistent peer metadata as real
columns instead of overloading the network username: Network name, Alias and
Favorite are independent and sortable, and a Favorite-only view can be toggled
from the context menu. Legacy Friend state and the network username are never
changed.
"""
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


def replace_once(text: str, old: str, new: str, path: pathlib.Path) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Required Transfers anchor not found in {path}: {old[:120]!r}")
    return text.replace(old, new, 1)


def insert_after(text: str, anchor: str, addition: str, path: pathlib.Path) -> str:
    if addition.strip() in text:
        return text
    if anchor not in text:
        raise RuntimeError(f"Required Transfers anchor not found in {path}: {anchor!r}")
    return text.replace(anchor, anchor + addition, 1)


def patch_mule_list() -> None:
    path = SRC / "MuleListCtrl.cpp"
    text = load(path)
    text = insert_after(text, '#include "MuleListCtrl.h"\n', '#include "EmuleNextTheme.h"\n', path)

    old = '''void CMuleListCtrl::SetColors()\n{\n\tm_crWindow = ::GetSysColor(COLOR_WINDOW);\n\tm_crWindowText = ::GetSysColor(COLOR_WINDOWTEXT);\n\tm_crWindowTextBk = m_crWindow;\n\n\tCOLORREF crHighlight = ::GetSysColor(COLOR_HIGHLIGHT);\n'''
    new = '''void CMuleListCtrl::SetColors()\n{\n\t// Owner-drawn eMule lists cache their colours. Native LISTVIEW dark-mode\n\t// theming therefore is not enough: use the eMule Next palette here too.\n\tif (CEmuleNextTheme::IsDarkMode()) {\n\t\tm_crWindow = CEmuleNextTheme::SurfaceColor();\n\t\tm_crWindowText = CEmuleNextTheme::TextColor();\n\t}\n\telse {\n\t\tm_crWindow = ::GetSysColor(COLOR_WINDOW);\n\t\tm_crWindowText = ::GetSysColor(COLOR_WINDOWTEXT);\n\t}\n\tm_crWindowTextBk = m_crWindow;\n\n\tCOLORREF crHighlight = CEmuleNextTheme::IsDarkMode()\n\t\t? CEmuleNextTheme::AccentColor() : ::GetSysColor(COLOR_HIGHLIGHT);\n'''
    text = replace_once(text, old, new, path)

    old = '''\t\tm_crHighlightText = ::GetSysColor(COLOR_HIGHLIGHTTEXT);\n'''
    new = '''\t\tm_crHighlightText = CEmuleNextTheme::IsDarkMode()\n\t\t\t? CEmuleNextTheme::TextColor() : ::GetSysColor(COLOR_HIGHLIGHTTEXT);\n'''
    text = replace_once(text, old, new, path)
    save(path, text)


def patch_theme_refresh() -> None:
    path = SRC / "EmuleNextTheme.cpp"
    text = load(path)
    old = '''        if (SameClass(className, WC_LISTVIEWW)) {\n            ListView_SetBkColor(window, background);\n            ListView_SetTextBkColor(window, background);\n            ListView_SetTextColor(window, text);\n        }\n'''
    new = '''        if (SameClass(className, WC_LISTVIEWW)) {\n            ListView_SetBkColor(window, background);\n            ListView_SetTextBkColor(window, background);\n            ListView_SetTextColor(window, text);\n            // CMuleListCtrl owner-draw colours are cached; refresh that cache\n            // on every System/Light/Dark re-application before repainting.\n            ::SendMessage(window, WM_SYSCOLORCHANGE, 0, 0);\n        }\n'''
    text = replace_once(text, old, new, path)
    save(path, text)


def patch_known_clients() -> None:
    path = SRC / "ClientListCtrl.cpp"
    text = load(path)

    text = insert_after(
        text,
        '\tconst UINT MP_NEXT_FAVORITE = 0xEE12;\n',
        '\tconst UINT MP_NEXT_FAVORITES_ONLY = 0xEE13;\n\tbool g_nextFavoritesOnly = false;\n',
        path,
    )

    old = '''\tCString GetPeerDisplayName(const CUpDownClient* client)\n\t{\n\t\tCString name;\n\t\tif (client == NULL)\n\t\t\treturn name;\n\n\t\tif (!theEmuleNext.GetPeerAlias(client->GetUserHash(), name)) {\n\t\t\tif (client->GetUserName() != NULL)\n\t\t\t\tname = client->GetUserName();\n\t\t\telse\n\t\t\t\tname.Format(_T("(%s)"), (LPCTSTR)GetResString(IDS_UNKNOWN));\n\t\t}\n\n\t\tif (theEmuleNext.IsPeerFavorite(client->GetUserHash()))\n\t\t\tname = _T("[*] ") + name;\n\t\treturn name;\n\t}\n'''
    new = '''\tCString GetPeerNetworkName(const CUpDownClient* client)\n\t{\n\t\tCString name;\n\t\tif (client != NULL && client->GetUserName() != NULL)\n\t\t\tname = client->GetUserName();\n\t\telse\n\t\t\tname.Format(_T("(%s)"), (LPCTSTR)GetResString(IDS_UNKNOWN));\n\t\treturn name;\n\t}\n\n\tCString GetPeerAlias(const CUpDownClient* client)\n\t{\n\t\tCString alias;\n\t\tif (client != NULL)\n\t\t\ttheEmuleNext.GetPeerAlias(client->GetUserHash(), alias);\n\t\treturn alias;\n\t}\n'''
    text = replace_once(text, old, new, path)

    old = '''\tInsertColumn(7, _T(""), LVCFMT_LEFT,\tDFLT_HASH_COL_WIDTH);\t\t//IDS_CD_UHASH\n'''
    new = '''\tInsertColumn(7, _T(""), LVCFMT_LEFT,\tDFLT_HASH_COL_WIDTH);\t\t//IDS_CD_UHASH\n\tInsertColumn(8, _T("Alias"), LVCFMT_LEFT, 150);\n\tInsertColumn(9, _T("Favorite"), LVCFMT_LEFT, 70);\n'''
    text = replace_once(text, old, new, path)

    old = '''\tGetHeaderCtrl()->SetItem(7, &hdi);\n}\n'''
    new = '''\tGetHeaderCtrl()->SetItem(7, &hdi);\n\n\tCString networkName(_T("Network name"));\n\thdi.pszText = const_cast<LPTSTR>((LPCTSTR)networkName);\n\tGetHeaderCtrl()->SetItem(0, &hdi);\n\tCString alias(_T("Alias"));\n\thdi.pszText = const_cast<LPTSTR>((LPCTSTR)alias);\n\tGetHeaderCtrl()->SetItem(8, &hdi);\n\tCString favorite(_T("Favorite"));\n\thdi.pszText = const_cast<LPTSTR>((LPCTSTR)favorite);\n\tGetHeaderCtrl()->SetItem(9, &hdi);\n}\n'''
    text = replace_once(text, old, new, path)

    old = '''\tcase 0: //user name / eMule Next alias\n\t\tsText = GetPeerDisplayName(client);\n\t\tbreak;\n'''
    new = '''\tcase 0: // network username - never modified by eMule Next metadata\n\t\tsText = GetPeerNetworkName(client);\n\t\tbreak;\n'''
    text = replace_once(text, old, new, path)

    old = '''\tcase 7: //hash\n\t\tsText = md4str(client->GetUserHash());\n\t}\n'''
    new = '''\tcase 7: //hash\n\t\tsText = md4str(client->GetUserHash());\n\t\tbreak;\n\tcase 8: // persistent local alias, keyed by userhash\n\t\tsText = GetPeerAlias(client);\n\t\tbreak;\n\tcase 9: // eMule Next favorite; deliberately independent from Friend\n\t\tsText = theEmuleNext.IsPeerFavorite(client->GetUserHash()) ? _T("Yes") : _T("No");\n\t\tbreak;\n\t}\n'''
    text = replace_once(text, old, new, path)

    old = '''\tcase 0: //user name / eMule Next alias\n\t\t{\n\t\t\tconst CString name1 = GetPeerDisplayName(item1);\n\t\t\tconst CString name2 = GetPeerDisplayName(item2);\n\t\t\tiResult = CompareLocaleStringNoCase(name1, name2);\n\t\t}\n\t\tbreak;\n'''
    new = '''\tcase 0: // network username\n\t\tiResult = CompareLocaleStringNoCase(GetPeerNetworkName(item1), GetPeerNetworkName(item2));\n\t\tbreak;\n'''
    text = replace_once(text, old, new, path)

    old = '''\tcase 7: //hash\n\t\tiResult = memcmp(item1->GetUserHash(), item2->GetUserHash(), 16);\n\t}\n'''
    new = '''\tcase 7: //hash\n\t\tiResult = memcmp(item1->GetUserHash(), item2->GetUserHash(), 16);\n\t\tbreak;\n\tcase 8: // alias\n\t\tiResult = CompareLocaleStringNoCase(GetPeerAlias(item1), GetPeerAlias(item2));\n\t\tbreak;\n\tcase 9: // favorite\n\t\tiResult = static_cast<int>(theEmuleNext.IsPeerFavorite(item1->GetUserHash()))\n\t\t\t- static_cast<int>(theEmuleNext.IsPeerFavorite(item2->GetUserHash()));\n\t\tbreak;\n\t}\n'''
    text = replace_once(text, old, new, path)

    old = '''\tClientMenu.AppendMenu(MF_STRING | (client ? MF_ENABLED : MF_GRAYED) | (isFavorite ? MF_CHECKED : MF_UNCHECKED), MP_NEXT_FAVORITE, _T("eMule Next favorite"));\n\n\tClientMenu.AppendMenu(MF_SEPARATOR);\n'''
    new = '''\tClientMenu.AppendMenu(MF_STRING | (client ? MF_ENABLED : MF_GRAYED) | (isFavorite ? MF_CHECKED : MF_UNCHECKED), MP_NEXT_FAVORITE, _T("eMule Next favorite"));\n\tClientMenu.AppendMenu(MF_STRING | (g_nextFavoritesOnly ? MF_CHECKED : MF_UNCHECKED), MP_NEXT_FAVORITES_ONLY, _T("Show favorites only"));\n\n\tClientMenu.AppendMenu(MF_SEPARATOR);\n'''
    text = replace_once(text, old, new, path)

    old = '''\tif (wParam == MP_FIND) {\n\t\tOnFindStart();\n\t\treturn TRUE;\n\t}\n\n\tint iSel = GetNextItem(-1, LVIS_SELECTED | LVIS_FOCUSED);\n'''
    new = '''\tif (wParam == MP_FIND) {\n\t\tOnFindStart();\n\t\treturn TRUE;\n\t}\n\tif (wParam == MP_NEXT_FAVORITES_ONLY) {\n\t\tg_nextFavoritesOnly = !g_nextFavoritesOnly;\n\t\tShowKnownClients();\n\t\tSortItems(SortProc, MAKELONG(GetSortItem(), !GetSortAscending()));\n\t\treturn TRUE;\n\t}\n\n\tint iSel = GetNextItem(-1, LVIS_SELECTED | LVIS_FOCUSED);\n'''
    text = replace_once(text, old, new, path)

    old = '''\t\tcase MP_NEXT_FAVORITE:\n\t\t\tif (theEmuleNext.SetPeerFavorite(client->GetUserHash(), !theEmuleNext.IsPeerFavorite(client->GetUserHash()))) {\n\t\t\t\tUpdate(iSel);\n\t\t\t\tSortItems(SortProc, MAKELONG(GetSortItem(), !GetSortAscending()));\n\t\t\t}\n\t\t\tbreak;\n'''
    new = '''\t\tcase MP_NEXT_FAVORITE:\n\t\t\tif (theEmuleNext.SetPeerFavorite(client->GetUserHash(), !theEmuleNext.IsPeerFavorite(client->GetUserHash()))) {\n\t\t\t\tif (g_nextFavoritesOnly && !theEmuleNext.IsPeerFavorite(client->GetUserHash()))\n\t\t\t\t\tDeleteItem(iSel);\n\t\t\t\telse\n\t\t\t\t\tUpdate(iSel);\n\t\t\t\tSortItems(SortProc, MAKELONG(GetSortItem(), !GetSortAscending()));\n\t\t\t\ttheApp.emuledlg->transferwnd->UpdateListCount(CTransferWnd::wnd2Clients);\n\t\t\t}\n\t\t\tbreak;\n'''
    text = replace_once(text, old, new, path)

    old = '''\tif (!thePrefs.IsKnownClientListDisabled() && !theApp.IsClosing()) {\n\t\tint iItemCount = GetItemCount();\n\t\tInsertItem(LVIF_TEXT | LVIF_PARAM, iItemCount, LPSTR_TEXTCALLBACK, 0, 0, 0, (LPARAM)client);\n'''
    new = '''\tif (!thePrefs.IsKnownClientListDisabled() && !theApp.IsClosing()) {\n\t\tif (g_nextFavoritesOnly && !theEmuleNext.IsPeerFavorite(client->GetUserHash()))\n\t\t\treturn;\n\t\tint iItemCount = GetItemCount();\n\t\tInsertItem(LVIF_TEXT | LVIF_PARAM, iItemCount, LPSTR_TEXTCALLBACK, 0, 0, 0, (LPARAM)client);\n'''
    text = replace_once(text, old, new, path)

    old = '''\tfor (POSITION pos = theApp.clientlist->list.GetHeadPosition(); pos != NULL;) {\n\t\tint iItem = InsertItem(LVIF_TEXT | LVIF_PARAM, iItemCount, LPSTR_TEXTCALLBACK, 0, 0, 0, (LPARAM)theApp.clientlist->list.GetNext(pos));\n\t\tUpdate(iItem);\n\t\t++iItemCount;\n\t}\n'''
    new = '''\tfor (POSITION pos = theApp.clientlist->list.GetHeadPosition(); pos != NULL;) {\n\t\tconst CUpDownClient* client = theApp.clientlist->list.GetNext(pos);\n\t\tif (g_nextFavoritesOnly && !theEmuleNext.IsPeerFavorite(client->GetUserHash()))\n\t\t\tcontinue;\n\t\tint iItem = InsertItem(LVIF_TEXT | LVIF_PARAM, iItemCount, LPSTR_TEXTCALLBACK, 0, 0, 0, (LPARAM)client);\n\t\tUpdate(iItem);\n\t\t++iItemCount;\n\t}\n'''
    text = replace_once(text, old, new, path)
    save(path, text)


def main() -> int:
    for required in ("MuleListCtrl.cpp", "ClientListCtrl.cpp", "EmuleNextTheme.cpp"):
        if not (SRC / required).exists():
            raise RuntimeError(f"Missing Transfers source: {SRC / required}")
    patch_mule_list()
    patch_theme_refresh()
    patch_known_clients()
    print("eMule Next Transfers dark mode and Known Users metadata active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
