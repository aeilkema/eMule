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

old = "\tif (pParams->bClientSharedFiles)\n\t\tti.iImage = sriClient;\n"
new = (
    "\tif (pParams->dwSearchID == EMULENEXT_KNOWN_USERS_VIEW_ID || pParams->bClientSharedFiles)\n"
    "\t\tti.iImage = sriClient;\n"
)
if new not in text:
    if old not in text:
        raise RuntimeError("Search tab icon branch was not found")
    # Keep the runtime insertion block byte-for-byte unchanged so the main
    # activator remains idempotent. The permanent view simply reuses the
    # existing client icon by its reserved view ID.
    text = text.replace(old, new, 1)

if newline != "\n":
    text = text.replace("\n", newline)
PATH.write_bytes(text.encode("latin-1"))
print("eMule Next permanent search views finalized")
