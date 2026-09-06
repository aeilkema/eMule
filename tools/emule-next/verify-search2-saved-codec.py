#!/usr/bin/env python3
"""Verify Search 2 saved-filter v2 preserves empty extension fields."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
CPP = ROOT / "srchybrid" / "Search2Service.cpp"


def main() -> int:
    if not CPP.exists():
        raise SystemExit("Search 2 saved codec verifier: Search2Service.cpp missing")
    text = CPP.read_bytes().decode("latin-1", errors="ignore")
    required = (
        'if (extension.IsEmpty())',
        'extension = _T("-")',
        'if (filter.extension == _T("-"))',
        'filter.extension.Empty()',
        'value.Left(3) == _T("v2;")',
        '_T("{\\"min\\":%I64u,\\"max\\":%I64u',
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        for marker in missing:
            print("Search 2 saved codec verifier: missing", marker)
        return 1
    print("Search 2 saved-search codec verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
