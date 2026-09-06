#!/usr/bin/env python3
'''Expose generated Preview 2 build identity without coupling it to protocol versioning.'''
from __future__ import annotations
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "EmuleNextDiagnosticsWnd.cpp"


def ensure_product_includes(text: str) -> str:
    required = (
        '#include "EmuleNextVersion.h"',
        '#include "EmuleNextBuildIdentity.h"',
    )
    missing = [item for item in required if item not in text]
    if not missing:
        return text

    # Insert into the translation unit's actual include block rather than
    # depending on any particular neighbouring include or newline convention.
    lines = text.splitlines(keepends=True)
    include_indexes = [i for i, line in enumerate(lines[:80]) if line.lstrip().startswith("#include ")]
    if not include_indexes:
        raise SystemExit("Preview2 identity: no include block found in Diagnostics source")

    insert_at = include_indexes[-1] + 1
    newline = "\r\n" if any(line.endswith("\r\n") for line in lines[:80]) else "\n"
    additions = [item + newline for item in missing]
    lines[insert_at:insert_at] = additions
    return "".join(lines)


def ensure_build_head_export(text: str) -> str:
    if 'Build head: ' in text:
        return text

    signature = "void CEmuleNextDiagnosticsWnd::ExportDiagnosticsReport()"
    start = text.find(signature)
    if start < 0:
        raise SystemExit("Preview2 identity: diagnostics export function missing")

    end = text.find("\n}\n", start)
    if end < 0:
        end = min(len(text), start + 12000)
    body = text[start:end]

    build_line = '    file.WriteString(_T("Build head: ") EMULENEXT_BUILD_HEAD _T("\\n"));'
    preferred = 'file.WriteString(EMULENEXT_PRODUCT_WITH_CORE_TEXT _T("\\n"));'
    preferred_pos = body.find(preferred)
    if preferred_pos >= 0:
        absolute = start + preferred_pos
        line_end = text.find("\n", absolute)
        if line_end < 0:
            raise SystemExit("Preview2 identity: diagnostics product line boundary missing")
        return text[:line_end + 1] + build_line + "\n" + text[line_end + 1:]

    # Formatting-independent fallback: put the identity immediately before the
    # Generated timestamp line inside ExportDiagnosticsReport.
    generated = 'file.WriteString(_T("Generated: ")'
    generated_pos = body.find(generated)
    if generated_pos >= 0:
        absolute = start + generated_pos
        line_start = text.rfind("\n", start, absolute) + 1
        return text[:line_start] + build_line + "\n" + text[line_start:]

    raise SystemExit("Preview2 identity: no stable export insertion point found")


def main() -> int:
    if not PATH.exists():
        raise SystemExit("Preview2 identity: Diagnostics source missing")

    text = PATH.read_bytes().decode("latin-1")
    text = ensure_product_includes(text)
    text = ensure_build_head_export(text)

    for marker in (
        '#include "EmuleNextVersion.h"',
        '#include "EmuleNextBuildIdentity.h"',
        'Build head: ',
    ):
        if marker not in text:
            raise SystemExit(f"Preview2 identity: final contract missing {marker}")

    PATH.write_bytes(text.encode("latin-1"))
    print("Preview 2 build identity exposed in diagnostics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
