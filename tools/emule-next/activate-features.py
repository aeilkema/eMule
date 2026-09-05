#!/usr/bin/env python3
"""Compatibility entry point for eMule Next runtime activation.

The first activation layer has already been materialized into the develop
overlay. Runtime/UI activation now lives in activate-runtime-features.py so the
local build, integration workflow and Windows CI all execute one idempotent
feature patcher and cannot drift into two conflicting scanner implementations.
"""
from __future__ import annotations

import pathlib
import runpy

SCRIPT = pathlib.Path(__file__).with_name("activate-runtime-features.py")
runpy.run_path(str(SCRIPT), run_name="__main__")
