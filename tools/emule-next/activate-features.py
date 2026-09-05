#!/usr/bin/env python3
"""Compatibility entry point for all eMule Next runtime/UI activation.

The develop overlay materializes the legacy runtime hooks. Once the newer
multi-view integration is present, the older single-Known-users patcher is
intentionally skipped on subsequent idempotence passes so it cannot try to
rewrite the already-upgraded SearchResultsWnd back to its intermediate form.
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
    return "IsEmuleNextPersistentView" in text and "m_search2Wnd" in text


for script_name in (
    "prepare-search-results.py",
    "activate-runtime-features.py",
    "finalize-peer-share-processing.py",
    "activate-theme.py",
    "activate-next-settings.py",
    "activate-next-views.py",
    "finalize-search-results.py",
    "activate-transfers-next.py",
    "activate-transfer-lifecycle.py",
    "activate-download-intelligence-view.py",
    "activate-branding.py",
    "fix-preview1-build.py",
):
    if script_name == "activate-runtime-features.py" and has_next_multi_view():
        print("eMule Next legacy single-view activation already superseded; skipping")
        continue
    try:
        runpy.run_path(str(HERE / script_name), run_name="__main__")
    except SystemExit as exc:
        if exc.code not in (None, 0):
            raise

print("eMule Next runtime/UI activation complete")
