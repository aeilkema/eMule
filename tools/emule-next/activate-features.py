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
    runpy.run_path(str(HERE / script_name), run_name="__main__")
