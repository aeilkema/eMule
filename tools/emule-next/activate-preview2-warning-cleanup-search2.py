#!/usr/bin/env python3
'''Rename Search2's helper Create method so it does not hide CWnd::Create.'''
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def load(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes(); crlf = raw.count(b"\r\n"); lf = raw.count(b"\n") - crlf
    nl = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n"), nl


def save(path: pathlib.Path, text: str, nl: str) -> None:
    if nl != "\n": text = text.replace("\n", nl)
    path.write_bytes(text.encode("latin-1"))


def main() -> int:
    header = SRC / "Search2Wnd.h"
    text, nl = load(header)
    text = text.replace("bool Create(CWnd* parent);", "bool CreateView(CWnd* parent);")
    if "bool CreateView(CWnd* parent);" not in text:
        raise SystemExit("Search2 warning cleanup: CreateView declaration missing")
    save(header, text, nl)

    impl = SRC / "Search2Wnd.cpp"
    text, nl = load(impl)
    text = text.replace("bool CSearch2Wnd::Create(CWnd* parent)", "bool CSearch2Wnd::CreateView(CWnd* parent)")
    if "bool CSearch2Wnd::CreateView(CWnd* parent)" not in text:
        raise SystemExit("Search2 warning cleanup: CreateView definition missing")
    save(impl, text, nl)

    changed_call = False
    call_pattern = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*search2[A-Za-z0-9_]*)\.Create\(", re.I)
    for path in SRC.rglob("*.cpp"):
        body, pnl = load(path)
        updated, count = call_pattern.subn(r"\1.CreateView(", body)
        if count:
            save(path, updated, pnl)
            changed_call = True
    # Idempotent runs need not change a call, but final state must contain one.
    all_cpp = "\n".join(load(p)[0] for p in SRC.rglob("*.cpp"))
    if ".CreateView(this)" not in all_cpp and not changed_call:
        raise SystemExit("Search2 warning cleanup: Search2 host CreateView call missing")

    print("Preview 2 Search2 Create-hiding warning cleanup materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
