#!/usr/bin/env python3
'''Final-state gate for eMule Next Preview 2 UI/product materialization.'''
from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
HERE = pathlib.Path(__file__).resolve().parent


def read(name: str) -> str:
    path = SRC / name
    if not path.exists():
        raise SystemExit(f"Preview2 verification: missing {name}")
    return path.read_bytes().decode("latin-1", errors="ignore")


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise SystemExit(f"Preview2 verification: {label} missing {marker}")


def preview2_order() -> list[str]:
    tree = ast.parse((HERE / "activate-preview2.py").read_text(encoding="utf-8-sig"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Tuple, ast.List)):
            values = [item.value for item in node.elts if isinstance(item, ast.Constant) and isinstance(item.value, str) and item.value.endswith(".py")]
            if "activate-preview2-core.py" in values:
                return values
    return []


def main() -> int:
    version = read("EmuleNextVersion.h")
    identity = read("EmuleNextBuildIdentity.h")
    modern_h = read("EmuleNextModernUi.h")
    modern_cpp = read("EmuleNextModernUi.cpp")
    settings_h = read("EmuleNextSettingsWnd.h")
    settings_cpp = read("EmuleNextSettingsWnd.cpp")
    diag_h = read("EmuleNextDiagnosticsWnd.h")
    diag_cpp = read("EmuleNextDiagnosticsWnd.cpp")
    host_h = read("SearchResultsWnd.h")
    host_cpp = read("SearchResultsWnd.cpp")
    search = read("Search2Wnd.cpp")
    library = read("FileLibraryWnd.cpp")
    users = read("KnownUsersWnd.cpp")
    dashboard = read("EmuleNextDashboardWnd.cpp")
    transfers = read("DownloadListCtrl.cpp")
    project = read("emule.vcxproj")

    for marker in (
        "EMULENEXT_VERSION_MINOR 2",
        'EMULENEXT_VERSION_STAGE _T("Preview 2")',
        'EMULENEXT_VERSION_TEXT _T("0.2.0 Preview 2")',
        'EMULENEXT_PRODUCT_TEXT _T("eMule Next 0.2.0 Preview 2")',
    ):
        require(version, marker, "Preview 2 version identity")
    require(identity, "EMULENEXT_BUILD_HEAD", "build identity")

    for marker in (
        "class CEmuleNextModernUi",
        "NavigationWidth",
        "DrawRoundedCard",
        "class CEmuleNextCard",
    ):
        require(modern_h, marker, "modern UI toolkit")
    for marker in (
        "Segoe UI Variable Text",
        "Segoe UI Variable Display",
        "LVS_EX_DOUBLEBUFFER",
        "DarkMode_Explorer",
        "DrawRoundedCard",
    ):
        require(modern_cpp, marker, "modern UI implementation")

    for marker in (
        "CATEGORY_APPEARANCE",
        "CATEGORY_PEERS",
        "CATEGORY_INTELLIGENCE",
        "CATEGORY_ADVANCED",
        'm_navigation.AddString(_T("Appearance"))',
        'm_navigation.AddString(_T("Peer knowledge"))',
        'm_navigation.AddString(_T("Intelligence"))',
        'm_navigation.AddString(_T("Advanced"))',
        "Use custom scheduler tuning",
        "Analysis only - observe and recommend",
        "Automatically learn from peers",
        "SmartHistoryCacheCapacity\"), 4096",
        "SmartTelemetryCapacity\"), 256",
    ):
        require(settings_cpp, marker, "categorized Settings")
    for forbidden in (
        "m_historyCapacity",
        "m_telemetryCapacity",
        "m_schedulerRuntime",
        "Run stress self-test",
        "Restore backup",
        "Checkpoint WAL",
    ):
        if forbidden in settings_h or forbidden in settings_cpp:
            raise SystemExit(f"Preview2 verification: technical diagnostics leaked into Settings: {forbidden}")

    for marker in (
        "CEmuleNextCard m_databaseCard",
        "CEmuleNextCard m_queueCard",
        "CEmuleNextCard m_schedulerCard",
        "CEmuleNextCard m_performanceCard",
        "CListCtrl m_runtimeTests",
        "OnTestPassClicked",
        "OnExportClicked",
    ):
        require(diag_h, marker, "Diagnostics dashboard contract")
    for marker in (
        "ED2K-01",
        "KAD-01",
        "UP-01",
        "SCHED-01",
        "HASH-01",
        "RunWriterQueueStress(10000",
        "Mark pass",
        "Mark fail",
        "Export report",
        "Build head: ",
        "Maintenance and stress actions run outside the GUI thread",
    ):
        require(diag_cpp, marker, "Diagnostics runtime validation")
    if "sqlite3_" in diag_cpp or "winsqlite3" in diag_cpp.lower():
        raise SystemExit("Preview2 verification: SQLite leaked into Diagnostics GUI")

    require(host_h, "CListBox m_nextNavigation", "Preview 2 workspace sidebar")
    for marker in (
        "IDC_EN_PREVIEW2_NAV",
        'm_nextNavigation.AddString(_T("Search"))',
        'm_nextNavigation.AddString(_T("Library"))',
        'm_nextNavigation.AddString(_T("Known Users"))',
        'm_nextNavigation.AddString(_T("Settings"))',
        'm_nextNavigation.AddString(_T("Diagnostics"))',
        "OnNextNavigationChanged",
        "CEmuleNextModernUi::NavigationWidth",
    ):
        require(host_cpp, marker, "Preview 2 workspace navigation")

    for source, marker, label in (
        (search, "CEmuleNextModernUi::ApplyList(m_results);", "Search modern list"),
        (library, "CEmuleNextModernUi::ApplyList(m_results);", "Library modern list"),
        (users, "CEmuleNextModernUi::ApplyList(m_users);", "Known Users primary list"),
        (users, "CEmuleNextModernUi::ApplyList(m_files);", "Known Users file list"),
        (dashboard, "CEmuleNextModernUi::ApplyList(m_downloads);", "Dashboard modern list"),
        (transfers, "CEmuleNextModernUi::ApplyList(*this);", "Transfers modern list"),
    ):
        require(source, marker, label)

    require(project, '<ClCompile Include="EmuleNextModernUi.cpp" />', "modern UI project source")
    require(project, '<ClInclude Include="EmuleNextModernUi.h" />', "modern UI project header")
    require(project, '<ClInclude Include="EmuleNextBuildIdentity.h" />', "build identity project header")

    order = preview2_order()
    if not order:
        raise SystemExit("Preview2 verification: Preview 2 orchestrator order unavailable")
    required = (
        "activate-preview2-core.py",
        "activate-preview2-polish-search.py",
        "activate-preview2-polish-library.py",
        "activate-preview2-polish-known-users.py",
        "activate-preview2-polish-dashboard.py",
        "activate-preview2-polish-transfers.py",
        "activate-preview2-navigation.py",
        "activate-preview2-build-identity.py",
        "verify-preview2-product.py",
    )
    for name in required:
        if name not in order:
            raise SystemExit(f"Preview2 verification: materialization step missing {name}")
    indexes = [order.index(name) for name in required]
    if indexes != sorted(indexes):
        raise SystemExit("Preview2 verification: unsafe Preview 2 materialization order")

    base_entry = (HERE / "activate-features.py").read_text(encoding="utf-8-sig")
    if '"fix-preview1-build.py"' not in base_entry:
        raise SystemExit("Preview2 verification: base final compatibility stage missing")

    print("eMule Next Preview 2 final-state product verification passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
