#!/usr/bin/env python3
"""Materialize shared DPI-aware layout metrics in eMule Next views."""
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


def write_text(path: pathlib.Path, text: str, encoding: str) -> None:
    path.write_bytes(text.encode(encoding))


def patch_project() -> None:
    path = SRC / "emule.vcxproj"
    text, encoding = read_text(path)
    changed = False
    for kind, name, anchor in (
        ("ClCompile", "EmuleNextUiMetrics.cpp", '    <ClCompile Include="DownloadIntelligence.cpp" />'),
        ("ClInclude", "EmuleNextUiMetrics.h", '    <ClInclude Include="DownloadIntelligence.h" />'),
    ):
        marker = f'    <{kind} Include="{name}" />'
        if marker not in text:
            if anchor not in text:
                raise SystemExit(f"UI metrics: project anchor missing for {name}")
            text = text.replace(anchor, marker + "\n" + anchor, 1)
            changed = True
    if changed:
        write_text(path, text, encoding)


def patch_dashboard() -> None:
    path = SRC / "EmuleNextDashboardWnd.cpp"
    text, encoding = read_text(path)
    changed = False
    include = '#include "EmuleNextUiMetrics.h"'
    if include not in text:
        anchor = '#include "EmuleNextTheme.h"'
        if anchor not in text:
            raise SystemExit("UI metrics: Dashboard include anchor missing")
        text = text.replace(anchor, anchor + "\n" + include, 1)
        changed = True

    def width_repl(match: re.Match[str]) -> str:
        value = match.group(2)
        if "CEmuleNextUiMetrics::Scale" in match.group(0):
            return match.group(0)
        return match.group(1) + f"CEmuleNextUiMetrics::Scale(m_hWnd, {value})" + match.group(3)

    updated = re.sub(r'(m_downloads\.InsertColumn\([^\n]*?,\s*)(\d+)(\);)', width_repl, text)
    if updated != text:
        text = updated
        changed = True

    replacements = {
        "const int margin = 8;": "const int margin = CEmuleNextUiMetrics::Scale(m_hWnd, 8);",
        "const int filterHeight = 25;": "const int filterHeight = CEmuleNextUiMetrics::Scale(m_hWnd, 25);",
        "const int summaryHeight = 22;": "const int summaryHeight = CEmuleNextUiMetrics::Scale(m_hWnd, 22);",
        "const int buttonGap = 5;": "const int buttonGap = CEmuleNextUiMetrics::Scale(m_hWnd, 5);",
        "const int buttonWidth = std::max(74, std::min(105, (clientWidth - buttonGap * 6) / 7));":
            "const int buttonWidth = std::max(CEmuleNextUiMetrics::Scale(m_hWnd, 74), std::min(CEmuleNextUiMetrics::Scale(m_hWnd, 105), (clientWidth - buttonGap * 6) / 7));",
        "detailsHeight = std::max(126, std::min(260, cy / 4));":
            "detailsHeight = std::max(CEmuleNextUiMetrics::Scale(m_hWnd, 126), std::min(CEmuleNextUiMetrics::Scale(m_hWnd, 260), cy / 4));",
    }
    for old, new in replacements.items():
        if old in text:
            text = text.replace(old, new, 1)
            changed = True

    if changed:
        write_text(path, text, encoding)


def patch_settings() -> None:
    path = SRC / "EmuleNextSettingsWnd.cpp"
    text, encoding = read_text(path)
    changed = False
    include = '#include "EmuleNextUiMetrics.h"'
    if include not in text:
        anchor = '#include "EmuleNextTheme.h"'
        if anchor not in text:
            raise SystemExit("UI metrics: Settings include anchor missing")
        text = text.replace(anchor, anchor + "\n" + include, 1)
        changed = True

    old = """    const int margin = 18, labelWidth = 250, fieldLeft = margin + labelWidth + 16;
    const int fieldWidth = cx - fieldLeft - margin > 290 ? 290 : (cx - fieldLeft - margin < 150 ? 150 : cx - fieldLeft - margin);
    const int checkWidth = cx - fieldLeft - margin > 280 ? cx - fieldLeft - margin : 280;
    int y = 14;"""
    new = """    const int margin = CEmuleNextUiMetrics::Scale(m_hWnd, 18);
    const int labelWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 250);
    const int fieldLeft = margin + labelWidth + CEmuleNextUiMetrics::Scale(m_hWnd, 16);
    const int availableFieldWidth = cx - fieldLeft - margin;
    const int fieldMinWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 150);
    const int fieldMaxWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 290);
    const int checkMinWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 280);
    const int fieldWidth = availableFieldWidth > fieldMaxWidth ? fieldMaxWidth : (availableFieldWidth < fieldMinWidth ? fieldMinWidth : availableFieldWidth);
    const int checkWidth = availableFieldWidth > checkMinWidth ? availableFieldWidth : checkMinWidth;
    int y = CEmuleNextUiMetrics::Scale(m_hWnd, 14);"""
    if old in text:
        text = text.replace(old, new, 1)
        changed = True
    elif "CEmuleNextUiMetrics::Scale(m_hWnd, 18)" not in text or "CEmuleNextUiMetrics::Scale(m_hWnd, 250)" not in text:
        raise SystemExit("UI metrics: Settings layout anchor changed unexpectedly")

    settings_replacements = {
        "cx - margin * 2 > 200 ? cx - margin * 2 : 200":
            "cx - margin * 2 > CEmuleNextUiMetrics::Scale(m_hWnd, 200) ? cx - margin * 2 : CEmuleNextUiMetrics::Scale(m_hWnd, 200)",
        "m_maxConcurrent.MoveWindow(fieldLeft, y, 90, 220)":
            "m_maxConcurrent.MoveWindow(fieldLeft, y, CEmuleNextUiMetrics::Scale(m_hWnd, 90), CEmuleNextUiMetrics::Scale(m_hWnd, 220))",
        "m_schedulerCooldown.MoveWindow(fieldLeft, y, 120, 220)":
            "m_schedulerCooldown.MoveWindow(fieldLeft, y, CEmuleNextUiMetrics::Scale(m_hWnd, 120), CEmuleNextUiMetrics::Scale(m_hWnd, 220))",
        "m_schedulerBatch.MoveWindow(fieldLeft, y, 120, 220)":
            "m_schedulerBatch.MoveWindow(fieldLeft, y, CEmuleNextUiMetrics::Scale(m_hWnd, 120), CEmuleNextUiMetrics::Scale(m_hWnd, 220))",
        "m_a4afThreshold.MoveWindow(fieldLeft, y, 120, 220)":
            "m_a4afThreshold.MoveWindow(fieldLeft, y, CEmuleNextUiMetrics::Scale(m_hWnd, 120), CEmuleNextUiMetrics::Scale(m_hWnd, 220))",
        "m_historyCapacity.MoveWindow(fieldLeft, y, 120, 220)":
            "m_historyCapacity.MoveWindow(fieldLeft, y, CEmuleNextUiMetrics::Scale(m_hWnd, 120), CEmuleNextUiMetrics::Scale(m_hWnd, 220))",
        "m_telemetryCapacity.MoveWindow(fieldLeft, y, 120, 220)":
            "m_telemetryCapacity.MoveWindow(fieldLeft, y, CEmuleNextUiMetrics::Scale(m_hWnd, 120), CEmuleNextUiMetrics::Scale(m_hWnd, 220))",
    }
    for old_text, new_text in settings_replacements.items():
        if old_text in text:
            text = text.replace(old_text, new_text)
            changed = True

    if changed:
        write_text(path, text, encoding)


def main() -> int:
    for name in ("EmuleNextUiMetrics.cpp", "EmuleNextUiMetrics.h"):
        if not (SRC / name).exists():
            raise SystemExit(f"UI metrics: required source missing: {name}")
    patch_project()
    patch_dashboard()
    patch_settings()
    print("eMule Next DPI-aware UI metrics activation complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())