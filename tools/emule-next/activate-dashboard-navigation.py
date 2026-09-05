#!/usr/bin/env python3
"""Wire eMule Next Dashboard rows back to the authoritative Transfers list."""
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


def patch_download_list_header() -> None:
    path = SRC / "DownloadListCtrl.h"
    text = load(path)
    marker = "bool\tSelectFile(CPartFile *file, bool expand = false);"
    if marker not in text:
        anchor = "\tvoid\tUpdateCurrentCategoryView(CPartFile *thisfile);\n"
        if anchor not in text:
            raise RuntimeError("DownloadListCtrl SelectFile header anchor not found")
        text = text.replace(anchor, anchor + "\tbool\tSelectFile(CPartFile *file, bool expand = false); // eMule Next Dashboard navigation\n", 1)
    save(path, text)


def patch_download_list_cpp() -> None:
    path = SRC / "DownloadListCtrl.cpp"
    text = load(path)
    if "bool CDownloadListCtrl::SelectFile(CPartFile *file, bool expand)" not in text:
        anchor = "void CDownloadListCtrl::UpdateItem(void *toupdate)\n"
        if anchor not in text:
            raise RuntimeError("DownloadListCtrl SelectFile implementation anchor not found")
        method = '''bool CDownloadListCtrl::SelectFile(CPartFile *file, bool expand)\n{\n\tif (file == NULL)\n\t\treturn false;\n\n\tListItems::const_iterator it = m_ListItems.find(file);\n\tif (it == m_ListItems.end())\n\t\treturn false;\n\n\tLVFINDINFO find = {};\n\tfind.flags = LVFI_PARAM;\n\tfind.lParam = reinterpret_cast<LPARAM>(it->second);\n\tconst int item = FindItem(&find);\n\tif (item < 0)\n\t\treturn false;\n\n\tSetItemState(-1, 0, LVIS_SELECTED | LVIS_FOCUSED);\n\tSetItemState(item, LVIS_SELECTED | LVIS_FOCUSED, LVIS_SELECTED | LVIS_FOCUSED);\n\tSetSelectionMark(item);\n\tEnsureVisible(item, FALSE);\n\tif (expand)\n\t\tExpandCollapseItem(item, EXPAND_ONLY);\n\tSetFocus();\n\treturn true;\n}\n\n'''
        text = text.replace(anchor, method + anchor, 1)
    save(path, text)


def patch_transfer_cpp() -> None:
    path = SRC / "TransferWnd.cpp"
    text = load(path)
    marker = "message == WM_APP + 0x568"
    if marker not in text:
        anchor = '''LRESULT CTransferWnd::DefWindowProc(UINT message, WPARAM wParam, LPARAM lParam)\n{\n\tif (message == WM_WINDOWPOSCHANGED && m_wndSplitter)\n\t\tm_wndSplitter.Invalidate();\n\n\treturn CResizableFormView::DefWindowProc(message, wParam, lParam);\n}\n'''
        replacement = '''LRESULT CTransferWnd::DefWindowProc(UINT message, WPARAM wParam, LPARAM lParam)\n{\n\tif (message == WM_APP + 0x568) {\n\t\tCPartFile *file = reinterpret_cast<CPartFile*>(lParam);\n\t\tif (file != NULL) {\n\t\t\tShowList(IDC_DOWNLOADLIST);\n\t\t\tm_dlTab.SetCurSel(0);\n\t\t\tdownloadlistctrl.ChangeCategory(0);\n\t\t\treturn downloadlistctrl.SelectFile(file, wParam != 0) ? 1 : 0;\n\t\t}\n\t\treturn 0;\n\t}\n\n\tif (message == WM_WINDOWPOSCHANGED && m_wndSplitter)\n\t\tm_wndSplitter.Invalidate();\n\n\treturn CResizableFormView::DefWindowProc(message, wParam, lParam);\n}\n'''
        if anchor not in text:
            raise RuntimeError("TransferWnd Dashboard message anchor not found")
        text = text.replace(anchor, replacement, 1)
    else:
        text = text.replace('downloadlistctrl.SelectFile(file, false)', 'downloadlistctrl.SelectFile(file, wParam != 0)', 1)
    save(path, text)


def main() -> int:
    patch_download_list_header()
    patch_download_list_cpp()
    patch_transfer_cpp()
    print("eMule Next Dashboard-to-Transfers navigation active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
