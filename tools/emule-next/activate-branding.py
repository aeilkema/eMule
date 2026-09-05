#!/usr/bin/env python3
"""Apply eMule Next Preview product branding without changing protocol versioning."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


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


def patch_resource() -> None:
    path = SRC / "emule.rc"
    text, newline = load(path)
    branded = 'CAPTION "eMule Next 0.1.0 Preview 1"'
    if branded not in text:
        dialog = 'IDD_EMULE_DIALOG DIALOGEX 0, 0, 515, 339\n'
        start = text.find(dialog)
        if start < 0:
            raise RuntimeError("IDD_EMULE_DIALOG not found")
        caption = 'CAPTION "eMule"'
        pos = text.find(caption, start, start + 700)
        if pos < 0:
            raise RuntimeError("main eMule caption not found")
        text = text[:pos] + branded + text[pos + len(caption):]
    save(path, text, newline)


def patch_search_results() -> None:
    path = SRC / "SearchResultsWnd.cpp"
    text, newline = load(path)
    include_anchor = '#include "EmuleNextTheme.h"\n'
    include_line = '#include "EmuleNextVersion.h"\n'
    if include_line not in text:
        if include_anchor not in text:
            raise RuntimeError("EmuleNextTheme include not found")
        text = text.replace(include_anchor, include_anchor + include_line, 1)

    start_anchor = '\tCResizableFormView::OnInitialUpdate();\n'
    branding = (
        '\n\t// Product branding only. The network/protocol core still reports its\n'
        '\t// upstream-compatible eMule version where protocol logic requires it.\n'
        '\tif (theApp.emuledlg != NULL)\n'
        '\t\ttheApp.emuledlg->SetWindowText(EMULENEXT_PRODUCT_WITH_CORE_TEXT);\n'
    )
    if branding.strip() not in text:
        if start_anchor not in text:
            raise RuntimeError("SearchResultsWnd::OnInitialUpdate anchor not found")
        text = text.replace(start_anchor, start_anchor + branding, 1)
    save(path, text, newline)


def main() -> int:
    patch_resource()
    patch_search_results()
    print("eMule Next Preview branding active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
