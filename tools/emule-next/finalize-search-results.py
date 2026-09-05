#!/usr/bin/env python3
"""Small post-runtime adjustments for the permanent eMule Next search views."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "SearchResultsWnd.cpp"

raw = PATH.read_bytes()
crlf = raw.count(b"\r\n")
lf = raw.count(b"\n") - crlf
newline = "\r\n" if crlf >= lf and crlf else "\n"
text = raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n")

flag = '\t\tknownUsers->bClientSharedFiles = true;\n'
if flag not in text:
    anchor = '\t\tknownUsers->strSpecialTitle = _T("Known users");\n'
    if anchor not in text:
        raise RuntimeError("Known Users tab construction was not found")
    # Reuse the existing client/shared-files icon without adding another icon
    # resource. All behavioral paths still identify the permanent view by its
    # reserved ID, so this flag is presentation-only here.
    text = text.replace(anchor, anchor + flag, 1)

if newline != "\n":
    text = text.replace("\n", newline)
PATH.write_bytes(text.encode("latin-1"))
print("eMule Next permanent search views finalized")
