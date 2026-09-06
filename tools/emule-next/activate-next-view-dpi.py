#!/usr/bin/env python3
"""Apply shared DPI metrics to Search 2, Library and Known Users layouts."""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def read_text(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def add_include(text: str) -> str:
    marker = '#include "EmuleNextUiMetrics.h"'
    if marker in text:
        return text
    anchor = '#include "EmuleNextTheme.h"'
    if anchor not in text:
        raise SystemExit("Next view DPI: theme include anchor missing")
    return text.replace(anchor, anchor + "\n" + marker, 1)


def scale_columns(text: str, control: str) -> str:
    pattern = re.compile(rf'({re.escape(control)}\.InsertColumn\([^\n]*?,\s*)(\d+)(\);)')
    def repl(match: re.Match[str]) -> str:
        return match.group(1) + f"CEmuleNextUiMetrics::Scale(m_hWnd, {match.group(2)})" + match.group(3)
    return pattern.sub(repl, text)


def patch_search2() -> None:
    path = SRC / "Search2Wnd.cpp"
    text, encoding = read_text(path)
    original = text
    text = add_include(text)
    text = scale_columns(text, "m_results")
    for old, new in {
        "const int margin = 12;": "const int margin = CEmuleNextUiMetrics::Scale(m_hWnd, 12);",
        "const int titleTop = 10;": "const int titleTop = CEmuleNextUiMetrics::Scale(m_hWnd, 10);",
        "const int queryTop = 58;": "const int queryTop = CEmuleNextUiMetrics::Scale(m_hWnd, 58);",
        "const int queryHeight = 26;": "const int queryHeight = CEmuleNextUiMetrics::Scale(m_hWnd, 26);",
        "const int filterTop = 92;": "const int filterTop = CEmuleNextUiMetrics::Scale(m_hWnd, 92);",
        "const int statusTop = 121;": "const int statusTop = CEmuleNextUiMetrics::Scale(m_hWnd, 121);",
        "const int listTop = 145;": "const int listTop = CEmuleNextUiMetrics::Scale(m_hWnd, 145);",
        "const int searchWidth = 104;": "const int searchWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 104);",
        "const int actionHeight = 30;": "const int actionHeight = CEmuleNextUiMetrics::Scale(m_hWnd, 30);",
    }.items():
        text = text.replace(old, new, 1)
    if text != original:
        path.write_bytes(text.encode(encoding))


def patch_library() -> None:
    path = SRC / "FileLibraryWnd.cpp"
    text, encoding = read_text(path)
    original = text
    text = add_include(text)
    text = scale_columns(text, "m_results")
    for old, new in {
        "const int margin = 12;": "const int margin = CEmuleNextUiMetrics::Scale(m_hWnd, 12);",
        "const int titleTop = 10;": "const int titleTop = CEmuleNextUiMetrics::Scale(m_hWnd, 10);",
        "const int controlsTop = 58;": "const int controlsTop = CEmuleNextUiMetrics::Scale(m_hWnd, 58);",
        "const int statusTop = 91;": "const int statusTop = CEmuleNextUiMetrics::Scale(m_hWnd, 91);",
        "const int listTop = 115;": "const int listTop = CEmuleNextUiMetrics::Scale(m_hWnd, 115);",
        "const int actionHeight = 30;": "const int actionHeight = CEmuleNextUiMetrics::Scale(m_hWnd, 30);",
    }.items():
        text = text.replace(old, new, 1)
    if text != original:
        path.write_bytes(text.encode(encoding))


def patch_known_users() -> None:
    path = SRC / "KnownUsersWnd.cpp"
    text, encoding = read_text(path)
    original = text
    text = add_include(text)
    text = scale_columns(text, "m_users")
    text = scale_columns(text, "m_files")
    for old, new in {
        "const int margin = 8;": "const int margin = CEmuleNextUiMetrics::Scale(m_hWnd, 8);",
        "const int refreshWidth = 84;": "const int refreshWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 84);",
        "const int darkWidth = 105;": "const int darkWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 105);",
        "const int headerHeight = 25;": "const int headerHeight = CEmuleNextUiMetrics::Scale(m_hWnd, 25);",
        "const int gap = 8;": "const int gap = CEmuleNextUiMetrics::Scale(m_hWnd, 8);",
        "const int statusLeft = margin + refreshWidth + 8 + darkWidth + 10;":
            "const int statusLeft = margin + refreshWidth + CEmuleNextUiMetrics::Scale(m_hWnd, 8) + darkWidth + CEmuleNextUiMetrics::Scale(m_hWnd, 10);",
    }.items():
        text = text.replace(old, new, 1)
    if text != original:
        path.write_bytes(text.encode(encoding))


def main() -> int:
    for name in ("Search2Wnd.cpp", "FileLibraryWnd.cpp", "KnownUsersWnd.cpp"):
        if not (SRC / name).exists():
            raise SystemExit(f"Next view DPI: missing {name}")
    patch_search2()
    patch_library()
    patch_known_users()
    print("Search 2, Library and Known Users DPI activation complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
