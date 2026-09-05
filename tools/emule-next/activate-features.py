#!/usr/bin/env python3
"""Compatibility entry point for all eMule Next runtime/UI activation.

The develop overlay already materializes several eMule Next runtime/UI hooks.
Legacy structural patchers are skipped once their multi-view result is present,
so repeated local builds stay idempotent and do not duplicate or downgrade
SearchResultsWnd helpers, permanent view blocks or tab routing.
"""
from __future__ import annotations

import pathlib
import runpy

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SEARCH_RESULTS = ROOT / "srchybrid" / "SearchResultsWnd.cpp"


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


for script_name in (
    "prepare-search-results.py",
    "activate-runtime-features.py",
    "finalize-peer-share-processing.py",
    "activate-theme.py",
    "activate-next-settings.py",
    "activate-next-views.py",
    "finalize-search-results.py",
    "activate-transfers-next.py",
    "activate-peer-alias-editor.py",
    "activate-transfer-intelligence-columns.py",
    "activate-dashboard.py",
    "fix-dashboard-compile.py",
    "activate-file-intelligence-columns.py",
    "activate-transfer-lifecycle.py",
    "activate-upload-transfer-lifecycle.py",
    "activate-transfer-statusbars.py",
    "activate-download-intelligence-view.py",
    "activate-transfer-history-direction.py",
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
    try:
        runpy.run_path(str(HERE / script_name), run_name="__main__")
    except SystemExit as exc:
        if exc.code not in (None, 0):
            raise

print("eMule Next runtime/UI activation complete")