#!/usr/bin/env python3
"""Make Search 2 saved-filter v2 robust when the extension field is empty."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
CPP = ROOT / "srchybrid" / "Search2Service.cpp"


def read() -> tuple[str, str]:
    raw = CPP.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def main() -> int:
    if not CPP.exists():
        raise SystemExit("Search 2 saved codec: Search2Service.cpp missing")
    text, encoding = read()
    changed = False

    sentinel = '''        CString extension(filter.extension);
        extension.Replace(_T(";"), _T(""));
        if (extension.IsEmpty())
            extension = _T("-");
        CString value;'''
    if sentinel not in text:
        old = '''        CString extension(filter.extension);
        extension.Replace(_T(";"), _T(""));
        CString value;'''
        if old not in text:
            raise SystemExit("Search 2 saved codec: v2 encode anchor missing")
        text = text.replace(old, sentinel, 1)
        changed = True

    decode = '''            filter.extension = value.Tokenize(_T(";"), pos);
            if (filter.extension == _T("-"))
                filter.extension.Empty();
            token = value.Tokenize(_T(";"), pos); filter.lastSeenAfter = _tstoi64(token);'''
    if decode not in text:
        old = '''            filter.extension = value.Tokenize(_T(";"), pos);
            token = value.Tokenize(_T(";"), pos); filter.lastSeenAfter = _tstoi64(token);'''
        if old not in text:
            raise SystemExit("Search 2 saved codec: v2 decode anchor missing")
        text = text.replace(old, decode, 1)
        changed = True

    if changed:
        CPP.write_bytes(text.encode(encoding))
    print("Search 2 saved-search filter codec empty-extension sentinel materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
