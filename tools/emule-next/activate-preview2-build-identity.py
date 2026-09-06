#!/usr/bin/env python3
'''Expose generated Preview 2 build identity without coupling it to protocol versioning.'''
from __future__ import annotations
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "EmuleNextDiagnosticsWnd.cpp"


def main() -> int:
    text = PATH.read_bytes().decode("latin-1")

    # Do not depend on one exact Version include location. Preview2 replaces the
    # Diagnostics source late in activation and earlier newline/materialization
    # passes are free to move or normalize includes. The Diagnostics header is
    # the stable compile contract for this translation unit.
    stable_anchor = '#include "EmuleNextDiagnosticsWnd.h"\n'
    if stable_anchor not in text:
        raise SystemExit("Preview2 identity: Diagnostics include anchor missing")

    additions = []
    if '#include "EmuleNextVersion.h"' not in text:
        additions.append('#include "EmuleNextVersion.h"')
    if '#include "EmuleNextBuildIdentity.h"' not in text:
        additions.append('#include "EmuleNextBuildIdentity.h"')
    if additions:
        text = text.replace(stable_anchor, stable_anchor + "\n".join(additions) + "\n", 1)

    if '#include "EmuleNextVersion.h"' not in text:
        raise SystemExit("Preview2 identity: product version include unavailable after repair")
    if '#include "EmuleNextBuildIdentity.h"' not in text:
        raise SystemExit("Preview2 identity: build identity include unavailable after repair")

    # Anchor on the first product line of the diagnostics export. If that exact
    # line changes later, fall back to the Generated line rather than failing on
    # harmless formatting differences.
    build_line = '    file.WriteString(_T("Build head: ") EMULENEXT_BUILD_HEAD _T("\\n"));'
    if 'Build head: ' not in text:
        product_marker = 'file.WriteString(EMULENEXT_PRODUCT_WITH_CORE_TEXT _T("\\n"));'
        generated_marker = 'file.WriteString(_T("Generated: ")'
        if product_marker in text:
            text = text.replace(product_marker, product_marker + "\n" + build_line, 1)
        elif generated_marker in text:
            pos = text.find(generated_marker)
            line_end = text.find("\n", pos)
            if line_end < 0:
                raise SystemExit("Preview2 identity: diagnostics export line boundary missing")
            text = text[:line_end + 1] + build_line + "\n" + text[line_end + 1:]
        else:
            raise SystemExit("Preview2 identity: diagnostics export anchor missing")

    if 'Build head: ' not in text:
        raise SystemExit("Preview2 identity: build head export not materialized")

    PATH.write_bytes(text.encode("latin-1"))
    print("Preview 2 build identity exposed in diagnostics")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
