#!/usr/bin/env python3
"""Harden the TransferWnd host bridge for Dashboard Intelligence 2.0.

The core Dashboard host activator adds the custom Transfers view. This narrow
follow-up keeps persisted Dashboard selection safe during the first real layout
and prevents a later toolbar rebuild from silently forcing Split View.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "TransferWnd.cpp"


def load() -> tuple[str, str]:
    raw = PATH.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    newline = "\r\n" if crlf >= lf and crlf else "\n"
    text = raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n")
    return text, newline


def save(text: str, newline: str) -> None:
    if newline != "\n":
        text = text.replace("\n", newline)
    PATH.write_bytes(text.encode("latin-1"))


def main() -> int:
    if not PATH.exists():
        raise SystemExit("Dashboard host hardening: TransferWnd.cpp missing")

    text, newline = load()
    changed = False

    restore_old = '''\tif (!m_bLayoutInited && rcWnd.Height() > 400) {
\t\tm_bLayoutInited = true;
\t\tif (m_dwShowListIDC == IDC_DOWNLOADLIST + IDC_UPLOADLIST)
\t\t\tShowSplitWindow(true);
\t\telse
\t\t\tShowList(m_dwShowListIDC);
\t}'''
    restore_new = '''\tif (!m_bLayoutInited && rcWnd.Height() > 400) {
\t\tm_bLayoutInited = true;
\t\tif (m_dwShowListIDC == IDC_DOWNLOADLIST + IDC_UPLOADLIST)
\t\t\tShowSplitWindow(true);
\t\telse if (m_dwShowListIDC == EMULENEXT_DASHBOARD_VIEW) {
\t\t\t// eMule Next: restore persisted Dashboard safely after first real layout.
\t\t\tShowNextDashboard();
\t\t}
\t\telse
\t\t\tShowList(m_dwShowListIDC);
\t}'''
    if restore_old in text:
        text = text.replace(restore_old, restore_new, 1)
        changed = True
    elif "restore persisted Dashboard safely after first real layout" not in text:
        raise SystemExit("Dashboard host hardening: OnPaint restore anchor missing")

    toolbar_old = '''\tif (bResetLists) {
\t\tLocalizeToolbars();
\t\tShowSplitWindow(true);
\t\tShowWnd2(m_uWnd2);
\t}'''
    toolbar_new = '''\tif (bResetLists) {
\t\tLocalizeToolbars();
\t\tif (m_dwShowListIDC == EMULENEXT_DASHBOARD_VIEW) {
\t\t\t// eMule Next: rebuilding toolbar chrome must not discard Dashboard selection.
\t\t\tShowNextDashboard();
\t\t}
\t\telse {
\t\t\tShowSplitWindow(true);
\t\t\tShowWnd2(m_uWnd2);
\t\t}
\t}'''
    if toolbar_old in text:
        text = text.replace(toolbar_old, toolbar_new, 1)
        changed = True
    elif "rebuilding toolbar chrome must not discard Dashboard selection" not in text:
        raise SystemExit("Dashboard host hardening: toolbar reset anchor missing")

    if changed:
        save(text, newline)
        print("eMule Next Dashboard host restore hardening materialized")
    else:
        print("eMule Next Dashboard host restore hardening already materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
