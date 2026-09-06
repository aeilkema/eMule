#!/usr/bin/env python3
"""Verify Library text filtering does not rebuild the list on every keystroke.

Library 2.0 rewrites FileLibraryWnd.cpp as a coherent product surface, so this
verifier must inspect the OnTextFilterChanged function itself rather than assume
that OnTimer immediately follows it in source order.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
CPP = ROOT / "srchybrid" / "FileLibraryWnd.cpp"
HEADER = ROOT / "srchybrid" / "FileLibraryWnd.h"


def function_body(source: str, signature: str) -> str:
    start = source.find(signature)
    if start < 0:
        raise SystemExit(f"Library debounce verification failed: missing {signature}")

    brace = source.find("{", start + len(signature))
    if brace < 0:
        raise SystemExit(f"Library debounce verification failed: opening brace missing for {signature}")

    depth = 0
    for pos in range(brace, len(source)):
        char = source[pos]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:pos]

    raise SystemExit(f"Library debounce verification failed: unterminated function {signature}")


def main() -> int:
    cpp = CPP.read_bytes().decode("latin-1", errors="ignore")
    header = HEADER.read_bytes().decode("latin-1", errors="ignore")

    for marker in (
        "EN_LIBRARY_FILTER_TIMER",
        "ON_WM_TIMER()",
        "SetTimer(EN_LIBRARY_FILTER_TIMER, 250, NULL)",
        "KillTimer(EN_LIBRARY_FILTER_TIMER)",
        "void CFileLibraryWnd::OnTimer(UINT_PTR eventId)",
    ):
        if marker not in cpp:
            raise SystemExit(f"Library debounce verification failed: missing {marker}")

    if "afx_msg void OnTimer(UINT_PTR eventId);" not in header:
        raise SystemExit("Library debounce verification failed: timer handler declaration missing")

    filter_body = function_body(cpp, "void CFileLibraryWnd::OnTextFilterChanged()")
    if "KillTimer(EN_LIBRARY_FILTER_TIMER);" not in filter_body:
        raise SystemExit("Library debounce verification failed: text change does not reset debounce timer")
    if "SetTimer(EN_LIBRARY_FILTER_TIMER, 250, NULL);" not in filter_body:
        raise SystemExit("Library debounce verification failed: text change does not arm 250ms debounce timer")
    if "PopulateRows()" in filter_body:
        raise SystemExit("Library debounce verification failed: immediate full list rebuild remains in text-change handler")

    timer_body = function_body(cpp, "void CFileLibraryWnd::OnTimer(UINT_PTR eventId)")
    for marker in (
        "eventId == EN_LIBRARY_FILTER_TIMER",
        "KillTimer(EN_LIBRARY_FILTER_TIMER);",
        "PopulateRows();",
    ):
        if marker not in timer_body:
            raise SystemExit(f"Library debounce verification failed: timer handler missing {marker}")

    print("Library text-filter debounce verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
