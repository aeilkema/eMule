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
    search2 = load("Search2Wnd.cpp")
    library = load("FileLibraryWnd.cpp")
    known = load("KnownUsersWnd.cpp")
    metrics = load("EmuleNextUiMetrics.cpp")
    workspace = load("EmuleNextWorkspaceUi.h")

    require(project, '<ClCompile Include="EmuleNextUiMetrics.cpp" />', "UI metrics cpp project entry")
    require(project, '<ClInclude Include="EmuleNextUiMetrics.h" />', "UI metrics header project entry")
    require(metrics, "MulDiv(value96Dpi", "DPI scaling implementation")
    require(workspace, "CEmuleNextUiMetrics::Scale", "workspace metrics delegation")

    require(dashboard, '#include "EmuleNextUiMetrics.h"', "Dashboard metrics include")
    require(dashboard, "const int margin = CEmuleNextWorkspaceUi::Margin(m_hWnd);", "Dashboard shared scaled margin")
    require(dashboard, "CEmuleNextUiMetrics::Scale(m_hWnd, widths[i])", "Dashboard scaled columns")
    require(dashboard, "const int filterHeight = CEmuleNextUiMetrics::Scale", "Dashboard scaled filters")
    require(settings, '#include "EmuleNextUiMetrics.h"', "Settings metrics include")
    require(settings, "const int fieldMin = CEmuleNextUiMetrics::Scale(m_hWnd, 150);", "Settings scaled minimum field geometry")
    require(settings, "const int fieldMax = CEmuleNextUiMetrics::Scale(m_hWnd, 290);", "Settings scaled maximum field geometry")
    require(settings, "m_historyCapacity.MoveWindow", "Settings history-capacity layout")

    require(search2, '#include "EmuleNextUiMetrics.h"', "Search 2 metrics include")
    require(search2, "const int queryTop = CEmuleNextUiMetrics::Scale", "Search 2 scaled layout")
    require(search2, "CEmuleNextUiMetrics::Scale(m_hWnd, 360)", "Search 2 scaled columns")
    require(search2, "CEmuleNextWorkspaceUi::Margin(m_hWnd)", "Search shared workspace margin")
    require(library, '#include "EmuleNextUiMetrics.h"', "Library metrics include")
    require(library, "const int controlsTop = CEmuleNextUiMetrics::Scale", "Library scaled layout")
    require(library, "m_results.InsertColumn(0, _T(\"File\"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 330));", "Library 2 scaled file column")
    require(library, "const int actionHeight = CEmuleNextWorkspaceUi::ActionHeight(m_hWnd);", "Library 2 shared action row")

    require(known, '#include "EmuleNextUiMetrics.h"', "Known Users metrics include")
    require(known, "const int margin = CEmuleNextWorkspaceUi::Margin(m_hWnd);", "Known Users 2.0 shared scaled margin")
    require(known, "const int modesWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 330);", "Known Users 2.0 scaled mode tabs")
    require(known, "const int searchWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 200);", "Known Users 2.0 scaled search field")
    require(known, "m_users.InsertColumn(0, _T(\"User\"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 170));", "Known Users 2.0 scaled user columns")
    require(known, "m_files.InsertColumn(0, _T(\"File\"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 300));", "Known Users 2.0 scaled file columns")
    require(known, "const int usersHeight = max(CEmuleNextUiMetrics::Scale(m_hWnd, 120)", "Known Users 2.0 scaled minimum list height")

    print("eMule Next DPI-aware UI metrics verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
