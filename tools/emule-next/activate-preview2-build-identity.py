#!/usr/bin/env python3
'''Expose generated Preview 2 build identity without coupling it to protocol versioning.'''
from __future__ import annotations
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "EmuleNextDiagnosticsWnd.cpp"


def main() -> int:
    text = PATH.read_bytes().decode("latin-1")
    if '#include "EmuleNextBuildIdentity.h"' not in text:
        anchor = '#include "EmuleNextVersion.h"\n'
        if anchor not in text:
            raise SystemExit("Preview2 identity: version include anchor missing")
        text = text.replace(anchor, anchor + '#include "EmuleNextBuildIdentity.h"\n', 1)
    marker = 'file.WriteString(EMULENEXT_PRODUCT_WITH_CORE_TEXT _T("\\n"));'
    if 'Build head: ' not in text:
        if marker not in text:
            raise SystemExit("Preview2 identity: diagnostics export anchor missing")
        text = text.replace(marker, marker + '\n    file.WriteString(_T("Build head: ") EMULENEXT_BUILD_HEAD _T("\\n"));', 1)
    PATH.write_bytes(text.encode("latin-1"))
    print("Preview 2 build identity exposed in diagnostics")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
