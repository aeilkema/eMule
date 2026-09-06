#!/usr/bin/env python3
'''Scope VS18 C4191 suppression to every MFC message-map macro table.

C4191 is emitted by the MFC message-map implementation itself when the macros
store typed member-function pointers in AFX_PMSG/AFX_PMSGW.  Keep the warning
enabled everywhere else and suppress it only around each generated map table.
'''
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


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


def wrap_all_message_maps(text: str) -> tuple[str, int]:
    # Remove only guards previously created by this activator.  Do not touch
    # unrelated warning push/pop scopes in legacy sources.
    guarded = re.compile(
        r"#pragma warning\(push\)\n#pragma warning\(disable:4191\)\n"
        r"(BEGIN_MESSAGE_MAP\(.*?END_MESSAGE_MAP\(\))\n#pragma warning\(pop\)",
        re.S,
    )
    text = guarded.sub(lambda m: m.group(1), text)
    pattern = re.compile(r"BEGIN_MESSAGE_MAP\(.*?END_MESSAGE_MAP\(\)", re.S)
    count = len(pattern.findall(text))
    if count:
        text = pattern.sub(
            lambda m: "#pragma warning(push)\n#pragma warning(disable:4191)\n"
            + m.group(0)
            + "\n#pragma warning(pop)",
            text,
        )
    return text, count


def main() -> int:
    files_changed = 0
    maps_guarded = 0
    for path in sorted(SRC.rglob("*.cpp")):
        text, nl = load(path)
        if "BEGIN_MESSAGE_MAP(" not in text:
            continue
        updated, count = wrap_all_message_maps(text)
        maps_guarded += count
        if updated != text:
            save(path, updated, nl)
            files_changed += 1

    if maps_guarded == 0:
        raise SystemExit("MFC warning cleanup: no message maps found")

    print(
        f"Preview 2 MFC message-map warning cleanup materialized "
        f"({maps_guarded} maps across {files_changed} changed files)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
