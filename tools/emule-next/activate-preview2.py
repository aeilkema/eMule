#!/usr/bin/env python3
'''Run final Preview 2 materialization only after all legacy/product gates passed.'''
from __future__ import annotations

import ast
import pathlib
import runpy
import traceback

HERE = pathlib.Path(__file__).resolve().parent

PREVIEW2_STEPS = (
    "activate-preview2-core.py",
    "activate-preview2-polish-search.py",
    "activate-preview2-polish-library.py",
    "activate-preview2-polish-known-users.py",
    "activate-preview2-polish-dashboard.py",
    "activate-preview2-dashboard-ux.py",
    "activate-preview2-dashboard-compile-hardening.py",
    "activate-preview2-polish-transfers.py",
    "activate-preview2-navigation.py",
    "activate-preview2-main-shell.py",
    "activate-preview2-ux-completion.py",
    "activate-preview2-settings-complete.py",
    "activate-preview2-settings-complete-hardening.py",
    "activate-preview2-search-ux.py",
    "activate-preview2-header-status.py",
    "activate-preview2-legacy-theme-routing.py",
    "activate-preview2-theme-coverage.py",
    "activate-preview2-warning-cleanup-dashboard.py",
    "activate-preview2-warning-cleanup-intelligence.py",
    "activate-preview2-warning-cleanup-kad.py",
    "activate-preview2-warning-cleanup-shared.py",
    "activate-preview2-warning-cleanup-mfc.py",
    "activate-preview2-warning-cleanup-main.py",
    "activate-preview2-build-identity.py",
    "verify-preview2-activation-chain.py",
    "verify-preview2-warning-cleanup.py",
    "verify-preview2-settings-theme.py",
    "verify-preview2-ux-completion.py",
    "verify-preview2-product.py",
)


def main() -> int:
    for name in PREVIEW2_STEPS:
        path = HERE / name
        if not path.exists():
            raise SystemExit(f"Preview2 materialization: missing {name}")
        try:
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except SyntaxError as exc:
            raise SystemExit(
                f"Preview2 materialization: {name} syntax error line {exc.lineno}: {exc.msg}"
            )

    for index, name in enumerate(PREVIEW2_STEPS, start=1):
        print(f"Preview2 step {index}/{len(PREVIEW2_STEPS)}: {name}")
        try:
            runpy.run_path(str(HERE / name), run_name="__main__")
        except SystemExit as exc:
            if exc.code not in (None, 0):
                print(f"Preview2 FAILED in {name}: {exc.code}")
                raise
        except Exception as exc:
            print(f"Preview2 FAILED in {name}: {type(exc).__name__}: {exc}")
            traceback.print_exc()
            raise

    print("eMule Next Preview 2 final materialization complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
