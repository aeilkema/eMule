#!/usr/bin/env python3
'''Run final Preview 2 materialization only after all legacy/product gates passed.'''
from __future__ import annotations

import ast
import pathlib
import runpy

HERE = pathlib.Path(__file__).resolve().parent

PREVIEW2_STEPS = (
    "activate-preview2-core.py",
    "activate-preview2-polish-search.py",
    "activate-preview2-polish-library.py",
    "activate-preview2-polish-known-users.py",
    "activate-preview2-polish-dashboard.py",
    "activate-preview2-polish-transfers.py",
    "activate-preview2-navigation.py",
    "activate-preview2-build-identity.py",
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
            raise SystemExit(f"Preview2 materialization: {name} syntax error line {exc.lineno}: {exc.msg}")

    for name in PREVIEW2_STEPS:
        try:
            runpy.run_path(str(HERE / name), run_name="__main__")
        except SystemExit as exc:
            if exc.code not in (None, 0):
                raise

    print("eMule Next Preview 2 final materialization complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
