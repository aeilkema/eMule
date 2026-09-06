#!/usr/bin/env python3
'''Apply the active Preview 2 theme whenever legacy workspaces/preferences are shown.'''
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
MAIN = SRC / "EmuleDlg.cpp"
PREFS = SRC / "PreferencesDlg.cpp"


def load(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    newline = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n"), newline


def save(path: pathlib.Path, text: str, newline: str) -> None:
    if newline != "\n":
        text = text.replace("\n", newline)
    path.write_bytes(text.encode("latin-1"))


def main() -> int:
    main, mn = load(MAIN)
    prefs, pn = load(PREFS)

    if '#include "EmuleNextTheme.h"' not in main:
        anchor = '#include "emuleDlg.h"\n'
        if anchor not in main:
            raise SystemExit("Preview2 legacy theme: EmuleDlg include anchor missing")
        main = main.replace(anchor, anchor + '#include "EmuleNextTheme.h"\n', 1)

    marker = "\tactivewnd = dlg;\n"
    if "Preview 2: re-apply the active theme to every legacy workspace" not in main:
        if marker not in main:
            raise SystemExit("Preview2 legacy theme: SetActiveDialog anchor missing")
        addition = '''\t// Preview 2: re-apply the active theme to every legacy workspace when shown.
\t// This keeps Servers, Kad, Shared Files, Statistics, IRC and Messages from
\t// falling back to default system-white child controls after navigation.
\tCEmuleNextTheme::ApplyToWindow(dlg->m_hWnd);
'''
        main = main.replace(marker, marker + addition, 1)

    if '#include "EmuleNextTheme.h"' not in prefs:
        anchor = '#include "PreferencesDlg.h"\n'
        if anchor not in prefs:
            raise SystemExit("Preview2 legacy theme: Preferences include anchor missing")
        prefs = prefs.replace(anchor, anchor + '#include "EmuleNextTheme.h"\n', 1)

    oninit_anchor = "\tInitWindowStyles(this);\n"
    if "Preview 2 themes the complete original Preferences tree" not in prefs:
        if oninit_anchor not in prefs:
            raise SystemExit("Preview2 legacy theme: Preferences OnInit anchor missing")
        addition = '''\t// Preview 2 themes the complete original Preferences tree while keeping
\t// every upstream property page and its existing apply/save logic authoritative.
\tCEmuleNextTheme::ApplyToWindow(m_hWnd);
'''
        prefs = prefs.replace(oninit_anchor, oninit_anchor + addition, 1)

    save(MAIN, main, mn)
    save(PREFS, prefs, pn)
    print("eMule Next Preview 2 legacy workspace/Preferences theme routing materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
