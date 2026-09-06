#!/usr/bin/env python3
"""Fix the Dashboard host creation path generated in TransferWnd.cpp.

The legacy global AddDebugLogLine helper is not available in this source tree.
Create the Dashboard defensively and only hide it when creation succeeded; the
ShowNextDashboard path already checks IsWindow before use.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "TransferWnd.cpp"

OLD = '''\tif (!m_nextDashboard.Create(this))
\t\tAddDebugLogLine(false, _T("eMule Next Dashboard creation failed"));
\tm_nextDashboard.ShowWindow(SW_HIDE);
'''
NEW = '''\tif (m_nextDashboard.Create(this))
\t\tm_nextDashboard.ShowWindow(SW_HIDE);
'''


def main() -> int:
    raw = PATH.read_bytes()
    text = raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n")

    if OLD in text:
        text = text.replace(OLD, NEW, 1)
        PATH.write_bytes(text.encode("latin-1"))
        print("eMule Next Dashboard host compile fix materialized")
    elif NEW in text and "AddDebugLogLine" not in text:
        print("eMule Next Dashboard host compile fix already materialized")
    else:
        raise SystemExit("Dashboard host compile fix: expected creation block not found")

    if "AddDebugLogLine" in text:
        raise SystemExit("Dashboard host compile fix: unavailable AddDebugLogLine remains")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
