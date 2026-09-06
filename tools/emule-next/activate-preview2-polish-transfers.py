#!/usr/bin/env python3
'''Apply final Preview 2 visual polish to the legacy-authoritative Transfers list.'''
from __future__ import annotations
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "DownloadListCtrl.cpp"


def main() -> int:
    text = PATH.read_bytes().decode("latin-1")
    if '#include "EmuleNextModernUi.h"' not in text:
        anchor = '#include "DownloadListCtrl.h"\n'
        if anchor not in text:
            raise SystemExit("Preview2 Transfers: include anchor missing")
        text = text.replace(anchor, anchor + '#include "EmuleNextModernUi.h"\n', 1)
    if "CEmuleNextModernUi::ApplyList(*this);" not in text:
        anchor = "\tLoadSettings();\n\tm_curTab = 0;"
        if anchor not in text:
            raise SystemExit("Preview2 Transfers: Init anchor missing")
        text = text.replace(anchor, "\tLoadSettings();\n\tCEmuleNextModernUi::ApplyList(*this);\n\tm_curTab = 0;", 1)
    PATH.write_bytes(text.encode("latin-1"))
    print("Preview 2 Transfers visual polish active")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
