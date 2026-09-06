#!/usr/bin/env python3
'''Compile/UI hardening for the complete Preview 2 Settings navigation.'''
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
CPP = ROOT / "srchybrid" / "EmuleNextSettingsWnd.cpp"


def main() -> int:
    raw = CPP.read_bytes()
    text = raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n")

    old = "LBS_NOTIFY | LBS_NOINTEGRALHEIGHT,\n            empty, this, IDC_EN_SETTINGS_NAV)"
    new = "LBS_NOTIFY | LBS_NOINTEGRALHEIGHT | WS_VSCROLL,\n            empty, this, IDC_EN_SETTINGS_NAV)"
    if "LBS_NOINTEGRALHEIGHT | WS_VSCROLL" not in text:
        if old not in text:
            raise SystemExit("Preview2 Settings hardening: navigation style anchor missing")
        text = text.replace(old, new, 1)

    start = text.find("void CEmuleNextSettingsWnd::LayoutControls(int cx, int cy)")
    end = text.find("void CEmuleNextSettingsWnd::OnPaint()", start)
    if start < 0 or end < 0:
        raise SystemExit("Preview2 Settings hardening: LayoutControls boundary missing")
    layout = text[start:end]
    if re.search(r"(?<![A-Za-z0-9_:])(?:min|max)\s*\(", layout):
        raise SystemExit("Preview2 Settings hardening: unqualified min/max remains in final Settings layout")
    if "CATEGORY_ORIGINAL_GENERAL" not in layout or "m_openOriginalSettings.MoveWindow" not in layout:
        raise SystemExit("Preview2 Settings hardening: original-page responsive layout missing")

    CPP.write_bytes(text.encode("latin-1"))
    print("eMule Next Preview 2 complete Settings compile/UI hardening passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
