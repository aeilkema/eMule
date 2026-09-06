#!/usr/bin/env python3
"""Static safety audit for eMule Next activators.

The audit protects repeated local builds: every helper must parse, top-level
activation order must remain safe, Windows CRLF must be normalized before
multiline patchers run, Dashboard 2.0 host integration must remain active while
obsolete render patchers are skipped, Known Users 2.0 must be fully materialized
before its completion gate, precursor activators must recognize their final
superseding state, and Smart Scheduler hooks must preserve semantics.
"""
from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
ENTRY = HERE / "activate-features.py"
NORMALIZER = HERE / "normalize-stage-newlines.py"

MUTATING_HELPER_PREFIXES = (
    "activate-",
    "finalize-",
    "prepare-",
    "fix-",
    "integrate",
)

REQUIRED_ORDER = (
    "activate-known-users2-runtime.py",
    "activate-known-users2-hardening.py",
    "activate-next-views.py",
    "activate-search2-background-metadata.py",
    "activate-search2-background-actions.py",
    "finalize-search-results.py",
    "activate-dashboard.py",
    "activate-dashboard-navigation.py",
    "activate-dashboard-host-hardening.py",
    "activate-file-intelligence-columns.py",
    "verify-file-intelligence-transition.py",
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


def assigned_string_set(source: str, name: str) -> set[str]:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                continue
            if isinstance(node.value, (ast.Set, ast.Tuple, ast.List)):
                values: set[str] = set()
                for item in node.value.elts:
                    if isinstance(item, ast.Constant) and isinstance(item.value, str):
                        values.add(item.value)
                return values
    return set()


def is_mutating_helper(path: pathlib.Path) -> bool:
    name = path.name
    if name in {"activate-features.py", "audit-activators.py"}:
        return False
    return name.startswith(MUTATING_HELPER_PREFIXES)


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
        if "verify-known-users2.py" in ordered and "audit-activators.py" in ordered:
            if ordered.index("verify-known-users2.py") > ordered.index("audit-activators.py"):
                failures.append("Known Users 2.0 completion gate must run before the activator audit")

    hosts = assigned_string_set(source, "DASHBOARD_HOST_INTEGRATORS")
    render_patchers = assigned_string_set(source, "DASHBOARD_RENDER_PATCHERS")
    expected_hosts = {"activate-dashboard.py", "activate-dashboard-navigation.py"}
    if hosts != expected_hosts:
        failures.append("Dashboard host integrator classification is incomplete")
    if hosts & render_patchers:
        failures.append("Dashboard host integrator incorrectly classified as render patcher")
    for required in (
        "fix-dashboard-compile.py",
        "activate-dashboard-actions.py",
        "activate-dashboard-source-profile.py",
        "activate-smart-scheduler-ui.py",
        "activate-dashboard-shared-insights.py",
    ):
        if required not in render_patchers:
            failures.append(f"Dashboard render-patcher guard lost {required}")
    if "has_dashboard_intelligence2()" not in source:
        failures.append("Dashboard Intelligence 2.0 materialization guard missing")

    for marker in (
        "def normalize_activation_sources()",
        "normalize_activation_sources()",
        'raw.replace(b"\\r\\n", b"\\n").replace(b"\\r", b"\\n")',
        "ACTIVATION_TEXT_SUFFIXES",
    ):
        if marker not in source:
            failures.append(f"activation newline preflight lost {marker}")
    if not NORMALIZER.exists():
        failures.append("normalize-stage-newlines.py missing")
    else:
        normalizer = read(NORMALIZER)
        for marker in (
            "def normalize_tree",
            'raw.replace(b"\\r\\n", b"\\n").replace(b"\\r", b"\\n")',
            "activation newline normalization incomplete",
        ):
            if marker not in normalizer:
                failures.append(f"stage newline normalizer lost {marker}")

    known_runtime = read(HERE / "activate-known-users2-runtime.py")
    for marker in (
        "QueuePeerShareRefresh", "QueuePeerManual", "OnUnsupported", "GetPeerShareState",
    ):
        if marker not in known_runtime:
            failures.append(f"Known Users 2.0 runtime bridge lost {marker}")
    known_hardening = read(HERE / "activate-known-users2-hardening.py")
    for marker in (
        "SaveViewState()", "%I64u", "GetClientSoftVer",
    ):
        if marker not in known_hardening:
            failures.append(f"Known Users 2.0 hardening lost {marker}")
    known_gate = read(HERE / "verify-known-users2.py")
    for marker in (
        "duplicate_username_sql_smoke", "endpoint match is required",
        "DeleteHistoryWorker", "QueuePeerManual", "PRAGMA query_only=ON",
    ):
        if marker not in known_gate:
            failures.append(f"Known Users 2.0 completion gate lost {marker}")

    # The 16..18 precursor and 16..22 consumer form an explicit contract. Raw
    # Python strings must not be used for C++ snippets containing \t/\" escapes,
    # otherwise literal escape characters leak into DownloadListCtrl.cpp.
    file_intelligence = read(HERE / "activate-file-intelligence-columns.py")
    for marker in (
        "def final_shared_intelligence2",
        "legacy file intelligence superseded by shared Transfers Intelligence 2.0; skipping",
        'InsertColumn(22,\\t_T("Scheduler")',
        "nColumn >= 16 && nColumn <= 22",
        "File intelligence materialized escaped Python text",
    ):
        if marker not in file_intelligence:
            failures.append(f"file-intelligence precursor contract lost {marker}")
    if "helpers = r'''" in file_intelligence or 'helpers = r"""' in file_intelligence:
        failures.append("file-intelligence precursor uses a raw C++ helper string")

    transfer2 = read(HERE / "activate-transfer-insights-2.py")
    for marker in (
        "precursor contract missing",
        "escaped Python text remains in C++",
        "function_pattern.sub(lambda _:",
        "final contract missing",
    ):
        if marker not in transfer2:
            failures.append(f"Transfers Intelligence 2 transition contract lost {marker}")
    if "replacement = r'''" in transfer2 or 'replacement = r"""' in transfer2:
        failures.append("Transfers Intelligence 2 uses a raw regex replacement for C++")

    transition_verifier = HERE / "verify-file-intelligence-transition.py"
    if not transition_verifier.exists():
        failures.append("Transfers intelligence transition verifier missing")
    else:
        transition = read(transition_verifier)
        for marker in (
            "precursor contract passed",
            "shared Intelligence 2.0 already satisfies transition contract",
            "escaped Python text leaked into C++",
        ):
            if marker not in transition:
                failures.append(f"Transfers transition verifier lost {marker}")

    scheduler_activator = read(HERE / "activate-smart-scheduler-runtime.py")
    expected_a4af = (
        "PreferA4AFCandidate(SwapTo, cur_file, "
        "CPartFile::RightFileHasHigherPrio(SwapTo, cur_file))"
    )
    if expected_a4af not in scheduler_activator:
        failures.append("A4AF hook no longer preserves legacy left/right candidate semantics")
    for marker in (
        '"EmuleNextSchedulerTelemetryReader.cpp"',
        '"EmuleNextSchedulerTelemetryReader.h"',
    ):
        if marker not in scheduler_activator:
            failures.append(f"Smart Scheduler project activation lost {marker}")

    dashboard_host = read(HERE / "activate-dashboard.py")
    for marker in (
        "GetPartSourceFrequency(UINT part)",
        "ShowNextDashboard()",
        "EMULENEXT_DASHBOARD_VIEW",
        "m_nextDashboard.Create(this)",
    ):
        if marker not in dashboard_host:
            failures.append(f"Dashboard host integration lost {marker}")
    dashboard_navigation = read(HERE / "activate-dashboard-navigation.py")
    for marker in (
        "SelectFile(CPartFile *file, bool expand = false)",
        "message == WM_APP + 0x568",
        "downloadlistctrl.SelectFile(file, wParam != 0)",
    ):
        if marker not in dashboard_navigation:
            failures.append(f"Dashboard navigation integration lost {marker}")
    dashboard_hardening = read(HERE / "activate-dashboard-host-hardening.py")
    for marker in (
        "restore persisted Dashboard safely after first real layout",
        "rebuilding toolbar chrome must not discard Dashboard selection",
    ):
        if marker not in dashboard_hardening:
            failures.append(f"Dashboard host hardening lost {marker}")

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
        "EmuleNextSchedulerTelemetryReader.cpp",
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

    search_injectors: list[str] = []
    for path in HERE.glob("*.py"):
        if not is_mutating_helper(path):
            continue
        body = read(path)
        if "EmuleNextDashboardWnd" in body and "SearchResultsWnd" in body:
            search_injectors.append(path.name)
    if search_injectors:
        failures.append("Dashboard/SearchResults coupling found in mutating helper(s): " + ", ".join(sorted(search_injectors)))

    verifier = HERE / "verify-no-hotpath-sqlite.py"
    if verifier.exists():
        verifier_body = read(verifier)
        if "EmuleNextDashboardWnd" in verifier_body and "SearchResultsWnd" in verifier_body and is_mutating_helper(verifier):
            failures.append("read-only verifier incorrectly classified as source mutator")

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
