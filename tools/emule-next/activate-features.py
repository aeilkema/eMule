#!/usr/bin/env python3
"""Compatibility entry point for all eMule Next runtime/UI activation.

The original activation layer has already been materialized into the develop
overlay. Runtime integration and dark-mode integration now live in dedicated,
idempotent patchers so local builds and CI execute the same feature set.
"""
from __future__ import annotations

import pathlib
import runpy

HERE = pathlib.Path(__file__).resolve().parent

for script_name in (
    "prepare-search-results.py",
    "activate-runtime-features.py",
    "activate-theme.py",
):
    try:
        runpy.run_path(str(HERE / script_name), run_name="__main__")
    except SystemExit as exc:
        # The dedicated patchers use `raise SystemExit(main())`. A successful
        # patcher must not prevent the next activation layer from running.
        if exc.code not in (None, 0):
            raise

print("eMule Next runtime/UI activation complete")
