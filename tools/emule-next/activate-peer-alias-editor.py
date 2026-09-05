#!/usr/bin/env python3
"""Replace clipboard-only peer aliases with eMule's native InputBox editor."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "ClientListCtrl.cpp"


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

    if '#include "InputBox.h"' not in text:
        anchor = '#include "ClientDetailDialog.h"\n'
        if anchor not in text:
            raise RuntimeError("ClientListCtrl include anchor not found")
        text = text.replace(anchor, anchor + '#include "InputBox.h"\n', 1)

    text = text.replace(
        '_T("Set eMule Next alias from clipboard")',
        '_T("Edit eMule Next alias...")',
    )

    old = '''\t\tcase MP_NEXT_SET_ALIAS:\n\t\t\t{\n\t\t\t\tCString alias = GetClipboardAlias(m_hWnd);\n\t\t\t\tif (alias.IsEmpty()) {\n\t\t\t\t\tAfxMessageBox(_T("Copy the desired alias to the clipboard first."), MB_OK | MB_ICONINFORMATION);\n\t\t\t\t\tbreak;\n\t\t\t\t}\n\t\t\t\tif (theEmuleNext.SetPeerAlias(client->GetUserHash(), alias)) {\n\t\t\t\t\tUpdate(iSel);\n\t\t\t\t\tSortItems(SortProc, MAKELONG(GetSortItem(), !GetSortAscending()));\n\t\t\t\t}\n\t\t\t}\n\t\t\tbreak;\n'''
    new = '''\t\tcase MP_NEXT_SET_ALIAS:\n\t\t\t{\n\t\t\t\tCString currentAlias;\n\t\t\t\ttheEmuleNext.GetPeerAlias(client->GetUserHash(), currentAlias);\n\t\t\t\tInputBox input(this);\n\t\t\t\tCString label;\n\t\t\t\tlabel.Format(_T("Local alias for %s:"), (LPCTSTR)GetPeerNetworkName(client));\n\t\t\t\tinput.SetLabels(_T("eMule Next peer alias"), label, currentAlias);\n\t\t\t\tif (input.DoModal() != IDOK || input.WasCancelled())\n\t\t\t\t\tbreak;\n\t\t\t\tCString alias(input.GetInput());\n\t\t\t\talias.Trim();\n\t\t\t\tif (alias.GetLength() > 128)\n\t\t\t\t\talias = alias.Left(128);\n\t\t\t\tif (theEmuleNext.SetPeerAlias(client->GetUserHash(), alias)) {\n\t\t\t\t\tUpdate(iSel);\n\t\t\t\t\tSortItems(SortProc, MAKELONG(GetSortItem(), !GetSortAscending()));\n\t\t\t\t}\n\t\t\t}\n\t\t\tbreak;\n'''
    if new not in text:
        if old not in text:
            raise RuntimeError("Clipboard alias command anchor not found")
        text = text.replace(old, new, 1)

    save(text, newline)
    print("eMule Next native peer alias editor active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
