#!/usr/bin/env python3
"""Reduce background shared-file processing pressure after runtime wiring."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "srchybrid" / "SearchList.cpp"

raw = PATH.read_bytes()
crlf = raw.count(b"\r\n")
lf = raw.count(b"\n") - crlf
newline = "\r\n" if crlf >= lf and crlf else "\n"
text = raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n")

old = (
    '\t\t// Persist peer/file history before the legacy result object is merged into the UI list.\n'
    '\t\ttheEmuleNext.RecordFileSeen(toadd->GetFileHash(), toadd->GetFileSize(), toadd->GetFileName());\n'
    '\t\ttheEmuleNext.RecordPeerFileSeen(sender.GetUserHash(), toadd->GetFileHash(), toadd->GetFileSize(),\n'
)
new = (
    '\t\t// PeerFileSeen already upserts the file. Automatic scans therefore queue\n'
    '\t\t// only one database event per result; this prevents large shares from\n'
    '\t\t// flooding the 50k-event writer queue and keeps the UI/network callback short.\n'
    '\t\tif (!bEmuleNextAutomaticShare)\n'
    '\t\t\ttheEmuleNext.RecordFileSeen(toadd->GetFileHash(), toadd->GetFileSize(), toadd->GetFileName());\n'
    '\t\ttheEmuleNext.RecordPeerFileSeen(sender.GetUserHash(), toadd->GetFileHash(), toadd->GetFileSize(),\n'
)
if new not in text:
    if old not in text:
        raise RuntimeError("Shared-file persistence block was not found")
    text = text.replace(old, new, 1)

if newline != "\n":
    text = text.replace("\n", newline)
PATH.write_bytes(text.encode("latin-1"))
print("eMule Next peer-share background processing finalized")
