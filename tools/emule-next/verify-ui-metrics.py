#!/usr/bin/env python3
"""Verify shared DPI-aware metrics are compiled and used by core eMule Next views."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def load(name: str) -> str:
    path = SRC / name
    if not path.exists():
        raise SystemExit(f"UI metrics verification: missing {name}")
    return path.read_bytes().decode("latin-1", errors="ignore")


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise SystemExit(f"UI metrics verification: missing {label}")


def main() -> int:
    project = load("emule.vcxproj")
    dashboard = load("EmuleNextDashboardWnd.cpp")
    settings = load("EmuleNextSettingsWnd.cpp")
    metrics = load("EmuleNextUiMetrics.cpp")

    require(project, '<ClCompile Include="EmuleNextUiMetrics.cpp" />', "UI metrics cpp project entry")
    require(project, '<ClInclude Include="EmuleNextUiMetrics.h" />', "UI metrics header project entry")
    require(metrics, "MulDiv(value96Dpi", "DPI scaling implementation")
    require(dashboard, '#include "EmuleNextUiMetrics.h"', "Dashboard metrics include")
    require(dashboard, "const int margin = CEmuleNextUiMetrics::Scale(m_hWnd, 8);", "Dashboard scaled margin")
    require(dashboard, "CEmuleNextUiMetrics::Scale(m_hWnd, 290)", "Dashboard scaled columns")
    require(settings, '#include "EmuleNextUiMetrics.h"', "Settings metrics include")
    require(settings, "const int fieldMinWidth = CEmuleNextUiMetrics::Scale", "Settings scaled field geometry")

    print("eMule Next DPI-aware UI metrics verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
