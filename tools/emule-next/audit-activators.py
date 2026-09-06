#!/usr/bin/env python3
"""Static safety audit for eMule Next activators.

The audit protects the integration contract that made repeated local builds
reliable: one top-level activation order, no Dashboard injection through
SearchResultsWnd, stable Smart Scheduler hooks and no accidental duplicate
script execution.
"""
from __future__ import annotations

import ast
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
ENTRY = HERE / "activate-features.py"

REQUIRED_ORDER = (
    "activate-smart-scheduler-runtime.py",
    "activate-smart-scheduler-ui.py",
    "verify-smart-scheduling.py",
    "verify-smart-scheduler-runtime.py",
    "verify-smart-scheduler-product.py",
    "verify-no-hotpath-sqlite.py",
)


def read(path: pathlib.Path) -> str:
    return path.read_bytes().decode("latin-1", errors="ignore")


def script_order(source: str) -> list[str]:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Tuple, ast.List)):
            values: list[str] = []
            for item in node.elts:
                if isinstance(item, ast.Constant) and isinstance(item.value, str) and item.value.endswith(".py"):
                    values.append(item.value)
            if "activate-smart-scheduler-runtime.py" in values:
                return values
    return []


def main() -> int:
    failures: list[str] = []
    source = read(ENTRY)
    ordered = script_order(source)
    if not ordered:
        failures.append("unable to locate activation script order")
    else:
        duplicates = sorted({name for name in ordered if ordered.count(name) > 1})
        if duplicates:
            failures.append("duplicate activators: " + ", ".join(duplicates))
        indexes = []
        for required in REQUIRED_ORDER:
            if required not in ordered:
                failures.append(f"required activation step missing: {required}")
            else:
                indexes.append(ordered.index(required))
        if indexes and indexes != sorted(indexes):
            failures.append("Smart Scheduler activation/verification order is unsafe")

    scheduler_activator = read(HERE / "activate-smart-scheduler-runtime.py")
    expected_a4af = (
        "PreferA4AFCandidate(SwapTo, cur_file, "
        "CPartFile::RightFileHasHigherPrio(SwapTo, cur_file))"
    )
    if expected_a4af not in scheduler_activator:
        failures.append("A4AF hook no longer preserves legacy left/right candidate semantics")

    search_injectors: list[str] = []
    for path in HERE.glob("*.py"):
        if path.name in {"audit-activators.py", "activate-features.py"}:
            continue
        body = read(path)
        if "EmuleNextDashboardWnd" in body and "SearchResultsWnd" in body:
            search_injectors.append(path.name)
    if search_injectors:
        failures.append("Dashboard/SearchResults coupling found in: " + ", ".join(sorted(search_injectors)))

    if "has_next_multi_view()" not in source:
        failures.append("multi-view idempotence guard missing from activate-features.py")

    if failures:
        print("eMule Next activator audit FAILED")
        for failure in failures:
            print(" -", failure)
        return 1
    print("eMule Next activator audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
