#!/usr/bin/env python3
"""Compatibility entry point for all eMule Next runtime/UI activation.

Materialized Next views are preferred over historic patch chains. Legacy
structural patchers are skipped once their final result is present, keeping
repeated local builds idempotent and preventing newer code from being
accidentally downgraded by an older activator.
"""
from __future__ import annotations

import pathlib
import runpy

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SEARCH_RESULTS = ROOT / "srchybrid" / "SearchResultsWnd.cpp"
DASHBOARD_HEADER = ROOT / "srchybrid" / "EmuleNextDashboardWnd.h"


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


DASHBOARD_LEGACY_PATCHERS = {
    "activate-dashboard.py",
    "fix-dashboard-compile.py",
    "activate-dashboard-navigation.py",
    "activate-dashboard-actions.py",
    "activate-dashboard-source-profile.py",
    "activate-smart-scheduler-ui.py",
    "activate-dashboard-shared-insights.py",
}

for script_name in (
    "prepare-search-results.py",
    "activate-runtime-features.py",
    "finalize-peer-share-processing.py",
    "activate-theme.py",
    "activate-next-settings.py",
    "activate-next-views.py",
    "activate-search2-background-metadata.py",
    "activate-search2-background-actions.py",
    "activate-library-filter-debounce.py",
    "finalize-search-results.py",
    "activate-transfers-next.py",
    "activate-peer-alias-editor.py",
    "activate-transfer-intelligence-columns.py",
    "activate-dashboard.py",
    "fix-dashboard-compile.py",
    "activate-dashboard-navigation.py",
    "activate-dashboard-actions.py",
    "activate-dashboard-source-profile.py",
    "activate-file-intelligence-columns.py",
    "activate-transfer-lifecycle.py",
    "activate-upload-transfer-lifecycle.py",
    "activate-transfer-statusbars.py",
    "activate-download-intelligence-view.py",
    "activate-transfer-history-direction.py",
    "activate-smart-scheduler-runtime.py",
    "activate-scheduler-schema-v2.py",
    "activate-scheduler-persistence.py",
    "activate-smart-scheduler-ui.py",
    "activate-scheduler-persistence-status.py",
    "activate-dashboard-shared-insights.py",
    "activate-ui-metrics.py",
    "activate-next-view-dpi.py",
    "activate-transfer-insights-2.py",
    "verify-search2-background-metadata.py",
    "verify-search2-background-actions.py",
    "verify-library-filter-debounce.py",
    "verify-ui-data-bounds.py",
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
    if script_name in DASHBOARD_LEGACY_PATCHERS and has_dashboard_intelligence2():
        print(f"eMule Next {script_name} superseded by Dashboard Intelligence 2.0; skipping")
        continue
    try:
        runpy.run_path(str(HERE / script_name), run_name="__main__")
    except SystemExit as exc:
        if exc.code not in (None, 0):
            raise

print("eMule Next runtime/UI activation complete")
