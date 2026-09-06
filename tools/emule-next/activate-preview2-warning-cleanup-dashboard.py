#!/usr/bin/env python3
'''Remove Dashboard-specific C4263/C4264 Create name hiding.'''
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
    header = SRC / "EmuleNextDashboardWnd.h"
    source = SRC / "EmuleNextDashboardWnd.cpp"
    ht, hn = load(header)
    st, sn = load(source)

    if "bool CreateView(CWnd* parent);" not in ht:
        if "bool Create(CWnd* parent);" not in ht:
            raise SystemExit("Dashboard warning cleanup: Create declaration missing")
        ht = ht.replace("bool Create(CWnd* parent);", "bool CreateView(CWnd* parent);", 1)
    if "CEmuleNextDashboardWnd::CreateView(CWnd* parent)" not in st:
        if "CEmuleNextDashboardWnd::Create(CWnd* parent)" not in st:
            raise SystemExit("Dashboard warning cleanup: Create definition missing")
        st = st.replace("CEmuleNextDashboardWnd::Create(CWnd* parent)", "CEmuleNextDashboardWnd::CreateView(CWnd* parent)", 1)
    save(header, ht, hn)
    save(source, st, sn)

    changed_calls = 0
    for path in SRC.glob("*.cpp"):
        text, nl = load(path)
        changed = text.replace("m_nextDashboard.Create(", "m_nextDashboard.CreateView(")
        changed = changed.replace("m_dashboardWnd.Create(", "m_dashboardWnd.CreateView(")
        if changed != text:
            save(path, changed, nl)
            changed_calls += 1

    # The normal host is TransferWnd; accepting an already-materialized CreateView is idempotent.
    transfer, _ = load(SRC / "TransferWnd.cpp")
    if "m_nextDashboard.CreateView(" not in transfer:
        raise SystemExit("Dashboard warning cleanup: TransferWnd CreateView caller missing")

    print("Preview 2 Dashboard warning cleanup materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
