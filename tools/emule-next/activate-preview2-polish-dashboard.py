#!/usr/bin/env python3
'''Apply final Preview 2 visual polish to Dashboard after its completion gate.'''
from __future__ import annotations
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "EmuleNextDashboardWnd.cpp"


def main() -> int:
    text = PATH.read_bytes().decode("latin-1")
    if '#include "EmuleNextModernUi.h"' not in text:
        anchor = '#include "EmuleNextTheme.h"\n'
        if anchor not in text:
            raise SystemExit("Preview2 Dashboard: theme include anchor missing")
        text = text.replace(anchor, anchor + '#include "EmuleNextModernUi.h"\n', 1)
    if "CEmuleNextModernUi::ApplyList(m_downloads);" not in text:
        anchor = "CEmuleNextTheme::ApplyToWindow(m_hWnd);"
        if anchor not in text:
            raise SystemExit("Preview2 Dashboard: theme application anchor missing")
        text = text.replace(anchor, "CEmuleNextModernUi::ApplyList(m_downloads);\n    " + anchor, 1)
    text = text.replace('_T("Dashboard 2.0")', '_T("Dashboard")')
    PATH.write_bytes(text.encode("latin-1"))
    print("Preview 2 Dashboard visual polish active")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
