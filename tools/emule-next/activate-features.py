#!/usr/bin/env python3
"""Compatibility entry point for all eMule Next runtime/UI activation.

Materialized Next views are preferred over historic patch chains. Dashboard
host integration (TransferWnd, DownloadListCtrl and PartFile bridges) must
always run, even when Dashboard Intelligence 2.0 is already materialized.
Only obsolete Dashboard render/content patchers are skipped in that case.

Windows Git checkouts commonly use CRLF. Before any activator runs, the isolated
source overlay is normalized byte-for-byte to LF so multiline anchors are
deterministic. No decoding/re-encoding of legacy source text is involved.
"""
from __future__ import annotations

import pathlib
import runpy

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE_ROOT = ROOT / "srchybrid"
SEARCH_RESULTS = SOURCE_ROOT / "SearchResultsWnd.cpp"
DASHBOARD_HEADER = SOURCE_ROOT / "EmuleNextDashboardWnd.h"

ACTIVATION_TEXT_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cxx",
    ".h", ".hh", ".hpp", ".hxx", ".inl",
    ".rc", ".rc2",
    ".vcxproj", ".filters", ".props", ".targets",
}


def normalize_activation_sources() -> None:
    if not SOURCE_ROOT.is_dir():
        raise SystemExit(f"eMule Next source overlay missing: {SOURCE_ROOT}")
    changed = 0
    for path in SOURCE_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in ACTIVATION_TEXT_SUFFIXES:
            continue
        raw = path.read_bytes()
        normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        if normalized != raw:
            path.write_bytes(normalized)
            changed += 1
    print(f"eMule Next activation newline preflight: {changed} files normalized to LF")


def has_next_multi_view() -> bool:
    if not SEARCH_RESULTS.exists():
        return False
    text = SEARCH_RESULTS.read_bytes().decode("latin-1", errors="ignore")
    return (
        "static bool IsEmuleNextPersistentView(uint32 searchID)" in text
        and "m_search2Wnd.Create(this)" in text
        and "m_fileLibraryWnd.Create(this)" in text
        and "m_nextSettingsWnd.Create(this)" in text
        and "void CSearchResultsWnd::ShowResults(const SSearchParams *pParams)" in text
    )


def has_dashboard_intelligence2() -> bool:
    if not DASHBOARD_HEADER.exists():
        return False
    text = DASHBOARD_HEADER.read_bytes().decode("latin-1", errors="ignore")
    return "EMULENEXT_DASHBOARD_INTELLIGENCE2" in text


normalize_activation_sources()

DASHBOARD_HOST_INTEGRATORS = {
    "activate-dashboard.py",
    "activate-dashboard-navigation.py",
}

DASHBOARD_RENDER_PATCHERS = {
    "fix-dashboard-compile.py",
    "activate-dashboard-actions.py",
    "activate-dashboard-source-profile.py",
    "activate-smart-scheduler-ui.py",
    "activate-dashboard-shared-insights.py",
}

for script_name in (
    "prepare-search-results.py",
    "activate-runtime-features.py",
    "activate-modern-windows-target.py",
    "activate-winsqlite-compat.py",
    "finalize-peer-share-processing.py",
    "activate-known-users2-runtime.py",
    "activate-known-users2-hardening.py",
    "activate-theme.py",
    "activate-next-settings.py",
    "activate-next-views.py",
    "activate-search2-background-metadata.py",
    "activate-search2-background-actions.py",
    "activate-search2-product.py",
    "activate-library-filter-debounce.py",
    "finalize-search-results.py",
    "activate-transfers-next.py",
    "activate-peer-alias-editor.py",
    "activate-transfer-intelligence-columns.py",
    "activate-dashboard.py",
    "fix-dashboard-compile.py",
    "activate-dashboard-navigation.py",
    "activate-dashboard-host-hardening.py",
    "fix-dashboard-host-compile.py",
    "activate-dashboard-actions.py",
    "activate-dashboard-source-profile.py",
    "activate-file-intelligence-columns.py",
    "verify-file-intelligence-transition.py",
    "activate-transfer-lifecycle.py",
    "activate-upload-transfer-lifecycle.py",
    "activate-transfer-statusbars.py",
    "activate-download-intelligence-view.py",
    "activate-transfer-history-direction.py",
    "activate-smart-scheduler-runtime.py",
    "activate-scheduler-action-stability.py",
    "activate-scheduler-schema-v2.py",
    "activate-scheduler-persistence.py",
    "activate-smart-scheduler-ui.py",
    "activate-scheduler-persistence-status.py",
    "activate-dashboard-shared-insights.py",
    "activate-ui-metrics.py",
    "activate-next-view-dpi.py",
    "activate-transfer-insights-2.py",
    "activate-dashboard-intelligence2-fixes.py",
    "verify-search2-background-metadata.py",
    "verify-search2-background-actions.py",
    "verify-search2-product.py",
    "verify-library-filter-debounce.py",
    "verify-ui-data-bounds.py",
    "verify-known-users2.py",
    "verify-smart-scheduling.py",
    "verify-smart-scheduler-runtime.py",
    "verify-smart-scheduler-product.py",
    "verify-transfer-insights-bounds.py",
    "verify-dashboard-shared-insights.py",
    "verify-dashboard-intelligence2.py",
    "verify-transfer-insights-2.py",
    "verify-ui-metrics.py",
    "verify-no-hotpath-sqlite.py",
    "verify-scheduler-persistence.py",
    "verify-scheduler-schema-v2.py",
    "verify-scheduler-database-maintenance.py",
    "verify-intelligence-goal-complete.py",
    "audit-activators.py",
    "verify-next-integration.py",
    "activate-branding.py",
    "fix-preview1-build.py",
):
    if script_name in (
        "prepare-search-results.py",
        "activate-runtime-features.py",
        "activate-next-views.py",
    ) and has_next_multi_view():
        print(f"eMule Next {script_name} already materialized; skipping")
        continue
    if script_name in DASHBOARD_RENDER_PATCHERS and has_dashboard_intelligence2():
        print(f"eMule Next {script_name} superseded by Dashboard Intelligence 2.0; skipping")
        continue
    try:
        runpy.run_path(str(HERE / script_name), run_name="__main__")
    except SystemExit as exc:
        if exc.code not in (None, 0):
            raise

print("eMule Next runtime/UI activation complete")
