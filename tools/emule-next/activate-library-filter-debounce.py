#!/usr/bin/env python3
"""Debounce Library text filtering to avoid rebuilding thousands of list rows per keystroke."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
CPP = SRC / "FileLibraryWnd.cpp"
HEADER = SRC / "FileLibraryWnd.h"


def read_text(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def write_text(path: pathlib.Path, text: str, encoding: str) -> None:
    path.write_bytes(text.encode(encoding))


def patch_header() -> None:
    text, encoding = read_text(HEADER)
    changed = False
    timer = "    afx_msg void OnTimer(UINT_PTR eventId);"
    if timer not in text:
        anchor = "    afx_msg void OnTextFilterChanged();"
        if anchor not in text:
            raise SystemExit("Library debounce: header filter anchor missing")
        text = text.replace(anchor, anchor + "\n" + timer, 1)
        changed = True
    if changed:
        write_text(HEADER, text, encoding)


def patch_cpp() -> None:
    text, encoding = read_text(CPP)
    changed = False

    timer_const = "    const UINT_PTR EN_LIBRARY_FILTER_TIMER = 0x7E6F;"
    if timer_const not in text:
        anchor = "    const UINT WM_EN_LIBRARY_LOADED = WM_APP + 0x571;"
        if anchor not in text:
            raise SystemExit("Library debounce: message constant anchor missing")
        text = text.replace(anchor, anchor + "\n" + timer_const, 1)
        changed = True

    if "    ON_WM_TIMER()" not in text:
        anchor = "    ON_WM_CTLCOLOR()"
        if anchor not in text:
            raise SystemExit("Library debounce: message map anchor missing")
        text = text.replace(anchor, anchor + "\n    ON_WM_TIMER()", 1)
        changed = True

    old_dtor = '''CFileLibraryWnd::~CFileLibraryWnd()
{
}'''
    new_dtor = '''CFileLibraryWnd::~CFileLibraryWnd()
{
    if (::IsWindow(m_hWnd))
        KillTimer(EN_LIBRARY_FILTER_TIMER);
}'''
    if old_dtor in text:
        text = text.replace(old_dtor, new_dtor, 1)
        changed = True
    elif "KillTimer(EN_LIBRARY_FILTER_TIMER)" not in text:
        raise SystemExit("Library debounce: destructor anchor changed unexpectedly")

    old_filter = '''void CFileLibraryWnd::OnTextFilterChanged()
{
    if (!m_loading)
        PopulateRows();
}'''
    new_filter = '''void CFileLibraryWnd::OnTextFilterChanged()
{
    KillTimer(EN_LIBRARY_FILTER_TIMER);
    SetTimer(EN_LIBRARY_FILTER_TIMER, 250, NULL);
}

void CFileLibraryWnd::OnTimer(UINT_PTR eventId)
{
    if (eventId == EN_LIBRARY_FILTER_TIMER) {
        KillTimer(EN_LIBRARY_FILTER_TIMER);
        if (!m_loading)
            PopulateRows();
        return;
    }
    CWnd::OnTimer(eventId);
}'''
    if old_filter in text:
        text = text.replace(old_filter, new_filter, 1)
        changed = True
    elif "SetTimer(EN_LIBRARY_FILTER_TIMER, 250, NULL)" not in text:
        raise SystemExit("Library debounce: filter handler changed unexpectedly")

    # If a background load completes while a debounce timer is pending, use the
    # newest filter immediately and cancel the redundant delayed rebuild.
    loaded_anchor = '''    m_rows.swap(result->rows);
    PopulateRows();'''
    loaded_replacement = '''    m_rows.swap(result->rows);
    KillTimer(EN_LIBRARY_FILTER_TIMER);
    PopulateRows();'''
    if loaded_anchor in text:
        text = text.replace(loaded_anchor, loaded_replacement, 1)
        changed = True
    elif "m_rows.swap(result->rows);\n    KillTimer(EN_LIBRARY_FILTER_TIMER);\n    PopulateRows();" not in text:
        raise SystemExit("Library debounce: load completion anchor missing")

    if changed:
        write_text(CPP, text, encoding)


def main() -> int:
    if not CPP.exists() or not HEADER.exists():
        raise SystemExit("Library debounce: source files missing")
    patch_header()
    patch_cpp()
    print("Library text-filter debounce materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())