#!/usr/bin/env python3
'''Fix Shared Files HMENU-to-UINT x64 truncation.'''
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"

def load(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes(); crlf = raw.count(b"\r\n"); lf = raw.count(b"\n") - crlf
    nl = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n"), nl

def save(path: pathlib.Path, text: str, nl: str) -> None:
    if nl != "\n": text = text.replace("\n", nl)
    path.write_bytes(text.encode("latin-1"))

def main() -> int:
    path = SRC / "SharedFilesCtrl.cpp"
    text, nl = load(path)
    old = '\tm_SharedFilesMenu.EnableMenuItem((UINT)m_PrioMenu.m_hMenu, (!bContainsShareableFiles && iSelectedItems > 0) ? MF_ENABLED : MF_GRAYED);'
    new = '''\tfor (int menuPos = 0; menuPos < m_SharedFilesMenu.GetMenuItemCount(); ++menuPos) {\n\t\tCMenu* submenu = m_SharedFilesMenu.GetSubMenu(menuPos);\n\t\tif (submenu != NULL && submenu->m_hMenu == m_PrioMenu.m_hMenu) {\n\t\t\tm_SharedFilesMenu.EnableMenuItem(menuPos, MF_BYPOSITION | ((!bContainsShareableFiles && iSelectedItems > 0) ? MF_ENABLED : MF_GRAYED));\n\t\t\tbreak;\n\t\t}\n\t}'''
    if old in text: text = text.replace(old, new, 1)
    elif "submenu->m_hMenu == m_PrioMenu.m_hMenu" not in text: raise SystemExit("Shared Files warning cleanup: priority submenu anchor missing")
    save(path, text, nl)
    print("Preview 2 Shared Files x64 warning cleanup materialized"); return 0

if __name__ == "__main__": raise SystemExit(main())
