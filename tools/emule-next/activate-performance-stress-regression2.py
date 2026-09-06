#!/usr/bin/env python3
'''Wire Performance / Stress / Protocol Regression 2.0 into the final tree.'''
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
PROJECT = SRC / "emule.vcxproj"


def read(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def main() -> int:
    text, enc = read(PROJECT)
    compile_anchor = '    <ClCompile Include="EmuleNextDatabaseMaintenance.cpp" />\n'
    if '<ClCompile Include="EmuleNextStressDiagnostics.cpp" />' not in text:
        if compile_anchor not in text:
            raise SystemExit("Perf2: project compile anchor missing")
        text = text.replace(compile_anchor, compile_anchor + '    <ClCompile Include="EmuleNextStressDiagnostics.cpp" />\n', 1)

    header_anchor = '    <ClInclude Include="EmuleNextDatabaseMaintenance.h" />\n'
    if '<ClInclude Include="EmuleNextStressDiagnostics.h" />' not in text:
        if header_anchor not in text:
            raise SystemExit("Perf2: project header anchor missing")
        text = text.replace(header_anchor, header_anchor + '    <ClInclude Include="EmuleNextStressDiagnostics.h" />\n', 1)

    PROJECT.write_bytes(text.encode(enc))
    print("eMule Next Performance / Stress / Protocol Regression 2.0 project wiring active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
