#!/usr/bin/env python3
'''Apply final Preview 2 visual polish to Known Users after its product gate.'''
from __future__ import annotations
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "KnownUsersWnd.cpp"


def main() -> int:
    text = PATH.read_bytes().decode("latin-1")
    if '#include "EmuleNextModernUi.h"' not in text:
        anchor = '#include "EmuleNextTheme.h"\n'
        if anchor not in text:
            raise SystemExit("Preview2 Known Users: theme include anchor missing")
        text = text.replace(anchor, anchor + '#include "EmuleNextModernUi.h"\n', 1)
    if "CEmuleNextModernUi::ApplyList(m_users);" not in text:
        anchor = "CEmuleNextTheme::ApplyToWindow(m_hWnd);"
        if anchor not in text:
            raise SystemExit("Preview2 Known Users: theme application anchor missing")
        addition = "CEmuleNextModernUi::ApplyList(m_users);\n    CEmuleNextModernUi::ApplyList(m_files);\n    m_darkModeButton.ShowWindow(SW_HIDE);\n    "
        text = text.replace(anchor, addition + anchor, 1)
    text = text.replace('_T("Known Users 2.0")', '_T("Known Users")')
    text = text.replace('_T("Dark mode")', '_T("Theme in Settings")')
    PATH.write_bytes(text.encode("latin-1"))
    print("Preview 2 Known Users visual polish active")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
