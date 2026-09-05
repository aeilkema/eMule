#!/usr/bin/env python3
"""Small post-runtime adjustments for permanent eMule Next search views."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "SearchResultsWnd.cpp"

raw = PATH.read_bytes()
crlf = raw.count(b"\r\n")
lf = raw.count(b"\n") - crlf
newline = "\r\n" if crlf >= lf and crlf else "\n"
text = raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n")

current = "\tif (IsEmuleNextPersistentView(pParams->dwSearchID) || pParams->bClientSharedFiles)\n\t\tti.iImage = sriClient;\n"
known_only = "\tif (pParams->dwSearchID == EMULENEXT_KNOWN_USERS_VIEW_ID || pParams->bClientSharedFiles)\n\t\tti.iImage = sriClient;\n"
legacy = "\tif (pParams->bClientSharedFiles)\n\t\tti.iImage = sriClient;\n"

if current not in text:
    if known_only in text:
        text = text.replace(known_only, current, 1)
    elif legacy in text:
        text = text.replace(legacy, current, 1)
    else:
        raise RuntimeError("Search tab icon branch was not found")

if newline != "\n":
    text = text.replace("\n", newline)
PATH.write_bytes(text.encode("latin-1"))
print("eMule Next permanent search views finalized")
