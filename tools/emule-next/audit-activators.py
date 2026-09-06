#!/usr/bin/env python3
"""Static safety audit for eMule Next activators.

The audit protects repeated local builds: every helper must parse, top-level
activation order must remain safe, materialized Dashboard 2.0 must supersede
legacy Dashboard patchers, and Smart Scheduler hooks must preserve semantics.
"""
from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
ENTRY = HERE / "activate-features.py"

REQUIRED_ORDER = (
    "activate-next-views.py",
    "activate-search2-background-metadata.py",
    "activate-search2-background-actions.py",
    "finalize-search-results.py",
    "activate-smart-scheduler-runtime.py",
    "activate-scheduler-action-stability.py",
    "activate-scheduler-schema-v2.py",
    "activate-scheduler-persistence.py",
    "activate-scheduler-persistence-status.py",
    "activate-ui-metrics.py",
    "activate-next-view-dpi.py",
    "activate-transfer-insights-2.py",
    "activate-dashboard-intelligence2-fixes.py",
    "verify-search2-background-metadata.py",
    "verify-search2-background-actions.py",
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
    "verify-scheduler-database-maintenance.py",
    "verify-intelligence-goal-complete.py",
)


def read(path: pathlib.Path) -> str:
    return path.read_bytes().decode("utf-8-sig", errors="replace")


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

    for path in sorted(HERE.glob("*.py")):
        try:
            ast.parse(read(path), filename=str(path))
        except SyntaxError as exc:
            failures.append(f"Python syntax error in {path.name}:{exc.lineno}: {exc.msg}")

    source = read(ENTRY)
    try:
        ordered = script_order(source)
    except SyntaxError:
        ordered = []
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
            failures.append("eMule Next activation/verification order is unsafe")

        if "verify-intelligence-goal-complete.py" in ordered and "audit-activators.py" in ordered:
            if ordered.index("verify-intelligence-goal-complete.py") > ordered.index("audit-activators.py"):
                failures.append("intelligence completion gate must run before the activator audit")

    scheduler_activator = read(HERE / "activate-smart-scheduler-runtime.py")
    expected_a4af = (
        "PreferA4AFCandidate(SwapTo, cur_file, "
        "CPartFile::RightFileHasHigherPrio(SwapTo, cur_file))"
    )
    if expected_a4af not in scheduler_activator:
        failures.append("A4AF hook no longer preserves legacy left/right candidate semantics")

    stability = read(HERE / "activate-scheduler-action-stability.py")
    for marker in ("previousActionAt", "candidate.lastA4AFAt", "Preserve an active measurement window"):
        if marker not in stability:
            failures.append(f"scheduler action stability lost {marker}")

    goal_gate = read(HERE / "verify-intelligence-goal-complete.py")
    for marker in (
        "DashboardColumnWidth%d",
        "DASHBOARD_MAX_FILES = 1000",
        "scheduler_outcomes",
        "ResetFileIntelligence",
        "CEmuleNextSchedulerTelemetryReader",
    ):
        if marker not in goal_gate:
            failures.append(f"intelligence completion gate lost {marker}")

    search_metadata = read(HERE / "activate-search2-background-metadata.py")
    if "AfxBeginThread(SavedSearchLoadWorker" not in search_metadata:
        failures.append("Search 2 metadata activator no longer moves recurring reads to a worker")

    search_actions = read(HERE / "activate-search2-background-actions.py")
    for marker in ("service.SaveSearch", "service.DeleteSavedSearch", "service.AddHashBlock"):
        if marker not in search_actions:
            failures.append(f"Search 2 background action activator missing {marker}")

    if "has_dashboard_intelligence2()" not in source or "DASHBOARD_LEGACY_PATCHERS" not in source:
        failures.append("Dashboard Intelligence 2.0 legacy-patcher guard missing")
    for legacy in (
        "activate-dashboard.py",
        "activate-dashboard-actions.py",
        "activate-dashboard-source-profile.py",
        "activate-smart-scheduler-ui.py",
        "activate-dashboard-shared-insights.py",
    ):
        if legacy not in source:
            failures.append(f"Dashboard legacy-patcher guard lost {legacy}")

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
