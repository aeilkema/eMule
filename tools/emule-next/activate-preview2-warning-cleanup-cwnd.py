#!/usr/bin/env python3
'''Prevent C4263/C4264 from custom Create overloads on eMule Next CWnd views.

If a CWnd-derived eMule Next view intentionally keeps a convenience
Create(CWnd*) overload, make the base CWnd::Create overload set visible with a
using-declaration. Views already migrated to CreateView need no change.
'''
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"

CLASS_RE = re.compile(
    r"class\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*public\s+CWnd\s*\n\{(?P<body>.*?)\n\};",
    re.S,
)


def load(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    nl = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n"), nl


def save(path: pathlib.Path, text: str, nl: str) -> None:
    if nl != "\n":
        text = text.replace("\n", nl)
    path.write_bytes(text.encode("latin-1"))


def patch_header(path: pathlib.Path) -> int:
    text, nl = load(path)
    changed = 0
    offset = 0
    for match in list(CLASS_RE.finditer(text)):
        body = match.group("body")
        if not re.search(r"\b(?:bool|BOOL)\s+Create\s*\(", body):
            continue
        if "using CWnd::Create;" in body:
            continue

        class_start = match.start() + offset
        body_start = text.find("\n{", class_start) + 2
        public_pos = text.find("public:", body_start, match.end() + offset)
        if public_pos < 0:
            raise SystemExit(f"CWnd warning cleanup: public section missing in {path.name}:{match.group(1)}")
        insert_pos = public_pos + len("public:")
        text = text[:insert_pos] + "\n    using CWnd::Create;" + text[insert_pos:]
        offset += len("\n    using CWnd::Create;")
        changed += 1

    if changed:
        save(path, text, nl)
    return changed


def main() -> int:
    classes_hardened = 0
    files_changed = 0
    for path in sorted(SRC.glob("*.h")):
        if not (path.name.startswith("EmuleNext") or path.name in {
            "KnownUsersWnd.h", "Search2Wnd.h", "FileLibraryWnd.h", "DownloadIntelligenceWnd.h"
        }):
            continue
        count = patch_header(path)
        if count:
            classes_hardened += count
            files_changed += 1

    print(
        f"Preview 2 CWnd Create-overload warning hardening materialized "
        f"({classes_hardened} classes across {files_changed} files)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
