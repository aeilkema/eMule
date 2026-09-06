#!/usr/bin/env python3
'''Fix remaining Release x64 warnings exposed by the full /WX rebuild.'''
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def load(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    nl = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n"), nl


def save(path: pathlib.Path, text: str, nl: str) -> None:
    if nl != "\n":
        text = text.replace("\n", nl)
    path.write_bytes(text.encode("latin-1"))


def replace_once(path: pathlib.Path, old: str, new: str, marker: str) -> None:
    text, nl = load(path)
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"Legacy warning cleanup: anchor missing for {marker} in {path.name}")
    save(path, text.replace(old, new, 1), nl)


def patch_library_create() -> None:
    header = SRC / "FileLibraryWnd.h"
    cpp = SRC / "FileLibraryWnd.cpp"
    replace_once(header, "    bool Create(CWnd* parent);", "    bool CreateView(CWnd* parent);", "Library Create declaration")
    replace_once(cpp, "bool CFileLibraryWnd::Create(CWnd* parent)", "bool CFileLibraryWnd::CreateView(CWnd* parent)", "Library Create definition")

    # The Search host is materialized before this late cleanup.  Update whatever
    # library member name is present without coupling this helper to one host type.
    for path in SRC.rglob("*.cpp"):
        text, nl = load(path)
        updated = re.sub(
            r"\b([A-Za-z_][A-Za-z0-9_]*library[A-Za-z0-9_]*)\.Create\((this|[^\n\)]*)\)",
            lambda m: f"{m.group(1)}.CreateView({m.group(2)})",
            text,
            flags=re.I,
        )
        if updated != text:
            save(path, updated, nl)


def patch_oscope() -> None:
    replace_once(
        SRC / "OScopeCtrl.cpp",
        "pParentWnd->GetSafeHwnd(), (HMENU)nID);",
        "pParentWnd->GetSafeHwnd(), reinterpret_cast<HMENU>(static_cast<UINT_PTR>(nID)));",
        "OScope child ID pointer-width conversion",
    )


def patch_smiley() -> None:
    path = SRC / "SmileySelector.cpp"
    old = '''\tCOLORREF crBackground = (::IsAppThemed() && ::IsThemeActive()) ? COLOR_WINDOW : COLOR_BTNFACE;\n\tstatic const CString &strClassName(AfxRegisterWndClass(\n\t\tCS_CLASSDC | CS_SAVEBITS | CS_HREDRAW | CS_VREDRAW\n\t\t, AfxGetApp()->LoadStandardCursor(IDC_ARROW), (HBRUSH)(crBackground + 1)\n\t\t, 0));'''
    new = '''\tconst int nBackgroundColorIndex = (::IsAppThemed() && ::IsThemeActive()) ? COLOR_WINDOW : COLOR_BTNFACE;\n\tstatic const CString &strClassName(AfxRegisterWndClass(\n\t\tCS_CLASSDC | CS_SAVEBITS | CS_HREDRAW | CS_VREDRAW\n\t\t, AfxGetApp()->LoadStandardCursor(IDC_ARROW), ::GetSysColorBrush(nBackgroundColorIndex)\n\t\t, 0));'''
    replace_once(path, old, new, "SmileySelector system brush")


def patch_preview() -> None:
    path = SRC / "Preview.cpp"
    old = '''\tDWORD dwError = (DWORD)::ShellExecute(NULL, pszVerb, strCommand, strArgs.IsEmpty() ? NULL : (LPCTSTR)strArgs, strCommandDir.IsEmpty() ? NULL : (LPCTSTR)strCommandDir, SW_SHOWNORMAL);\n\tif (dwError <= 32) {'''
    new = '''\tconst INT_PTR shellResult = reinterpret_cast<INT_PTR>(::ShellExecute(NULL, pszVerb, strCommand, strArgs.IsEmpty() ? NULL : (LPCTSTR)strArgs, strCommandDir.IsEmpty() ? NULL : (LPCTSTR)strCommandDir, SW_SHOWNORMAL));\n\tif (shellResult <= 32) {\n\t\tconst DWORD dwError = static_cast<DWORD>(shellResult);'''
    replace_once(path, old, new, "ShellExecute pointer-width result")


def patch_titled_menu() -> None:
    path = SRC / "TitledMenu.cpp"
    text, nl = load(path)
    text = text.replace("nPos = (int)pvIndex;", "nPos = PtrToInt(pvIndex);")
    text = text.replace("m_mapIconNameToIconIdx[strIconLower] = (void*)nPos;", "m_mapIconNameToIconIdx[strIconLower] = IntToPtr(nPos);")
    if "nPos = (int)pvIndex;" in text or "(void*)nPos" in text:
        raise SystemExit("Legacy warning cleanup: TitledMenu pointer/int casts remain")
    save(path, text, nl)


def patch_afxinet_vendor_warning() -> None:
    path = SRC / "HttpDownloadDlg.h"
    text, nl = load(path)
    old = "#pragma once\n#include <afxinet.h>"
    new = '''#pragma once\n// VS18 reports C4266 inside the shipped MFC afxinet.h implementation.\n// Scope the vendor-header warning locally; project code keeps C4266 enabled.\n#pragma warning(push)\n#pragma warning(disable:4266)\n#include <afxinet.h>\n#pragma warning(pop)'''
    if new not in text:
        if old not in text:
            raise SystemExit("Legacy warning cleanup: afxinet include anchor missing")
        text = text.replace(old, new, 1)
        save(path, text, nl)


def main() -> int:
    patch_library_create()
    patch_oscope()
    patch_smiley()
    patch_preview()
    patch_titled_menu()
    patch_afxinet_vendor_warning()
    print("Preview 2 full-rebuild legacy/x64 warning cleanup materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
