#!/usr/bin/env python3
'''Remove Download Intelligence C4263/C4264 Create name hiding.'''
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def load(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    newline = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n"), newline


def save(path: pathlib.Path, text: str, newline: str) -> None:
    if newline != "\n":
        text = text.replace("\n", newline)
    path.write_bytes(text.encode("latin-1"))


def main() -> int:
    header = SRC / "DownloadIntelligenceWnd.h"
    source = SRC / "DownloadIntelligenceWnd.cpp"
    ht, hn = load(header)
    st, sn = load(source)

    if "bool CreateView(CWnd* parent);" not in ht:
        if "bool Create(CWnd* parent);" not in ht:
            raise SystemExit("Download Intelligence warning cleanup: Create declaration missing")
        ht = ht.replace("bool Create(CWnd* parent);", "bool CreateView(CWnd* parent);", 1)
    if "CDownloadIntelligenceWnd::CreateView(CWnd* parent)" not in st:
        if "CDownloadIntelligenceWnd::Create(CWnd* parent)" not in st:
            raise SystemExit("Download Intelligence warning cleanup: Create definition missing")
        st = st.replace("CDownloadIntelligenceWnd::Create(CWnd* parent)", "CDownloadIntelligenceWnd::CreateView(CWnd* parent)", 1)
    save(header, ht, hn)
    save(source, st, sn)

    for path in SRC.glob("*.cpp"):
        text, nl = load(path)
        changed = text.replace("m_downloadIntelligenceWnd.Create(", "m_downloadIntelligenceWnd.CreateView(")
        changed = changed.replace("m_intelligenceWnd.Create(", "m_intelligenceWnd.CreateView(")
        if changed != text:
            save(path, changed, nl)

    host, _ = load(SRC / "SearchResultsWnd.cpp")
    if "m_downloadIntelligenceWnd.CreateView(" not in host:
        raise SystemExit("Download Intelligence warning cleanup: host CreateView caller missing")

    print("Preview 2 Download Intelligence warning cleanup materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
