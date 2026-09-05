#!/usr/bin/env python3
"""Apply the central eMule Next palette to legacy transfer status bars."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
_NEWLINES: dict[pathlib.Path, str] = {}


def load(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    _NEWLINES[path] = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n")


def save(path: pathlib.Path, text: str) -> None:
    newline = _NEWLINES.get(path, "\n")
    if newline != "\n":
        text = text.replace("\n", newline)
    path.write_bytes(text.encode("latin-1"))


def replace_once(text: str, old: str, new: str, path: pathlib.Path) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Required status-bar anchor not found in {path}: {old[:160]!r}")
    return text.replace(old, new, 1)


def insert_after(text: str, anchor: str, addition: str, path: pathlib.Path) -> str:
    if addition.strip() in text:
        return text
    if anchor not in text:
        raise RuntimeError(f"Required include anchor not found in {path}: {anchor!r}")
    return text.replace(anchor, anchor + addition, 1)


def patch_download() -> None:
    path = SRC / "DownloadClient.cpp"
    text = load(path)
    text = insert_after(text, '#include "EmuleNextRuntime.h"\n', '#include "EmuleNextTheme.h"\n', path)
    old = '''\tCOLORREF crNeither;\n\tif (bFlat)\n\t\tcrNeither = g_bLowColorDesktop ? RGB(192, 192, 192) : RGB(224, 224, 224);\n\telse\n\t\tcrNeither = RGB(240, 240, 240);\n'''
    new = '''\tCOLORREF crNeither;\n\tif (CEmuleNextTheme::IsDarkMode())\n\t\tcrNeither = bFlat ? CEmuleNextTheme::SurfaceAltColor() : CEmuleNextTheme::SurfaceColor();\n\telse if (bFlat)\n\t\tcrNeither = g_bLowColorDesktop ? RGB(192, 192, 192) : RGB(224, 224, 224);\n\telse\n\t\tcrNeither = RGB(240, 240, 240);\n'''
    text = replace_once(text, old, new, path)
    save(path, text)


def patch_upload() -> None:
    path = SRC / "UploadClient.cpp"
    text = load(path)
    text = insert_after(text, '#include "UploadDiskIOThread.h"\n', '#include "EmuleNextTheme.h"\n', path)
    old = '''\tif (GetSlotNumber() <= (UINT)theApp.uploadqueue->GetActiveUploadsCount()\n\t\t|| (GetUploadState() != US_UPLOADING && GetUploadState() != US_CONNECTING))\n\t{\n\t\tcrNeither = RGB(224, 224, 224); //light grey\n\t\tcrNextSending = RGB(255, 208, 0); //dark yellow\n\t\tcrBoth = bFlat ? RGB(0, 0, 0) : RGB(104, 104, 104); //black : very dark gray\n\t\tcrSending = RGB(0, 150, 0); //dark green\n\t} else {\n\t\t// grayed out\n\t\tcrNeither = RGB(248, 248, 248); //very light grey\n\t\tcrNextSending = RGB(255, 244, 191); //pale yellow\n\t\tcrBoth = /*bFlat ? RGB(191, 191, 191) :*/ RGB(191, 191, 191); //mid-grey\n\t\tcrSending = RGB(191, 229, 191); //pale green\n\t}\n'''
    new = '''\tif (GetSlotNumber() <= (UINT)theApp.uploadqueue->GetActiveUploadsCount()\n\t\t|| (GetUploadState() != US_UPLOADING && GetUploadState() != US_CONNECTING))\n\t{\n\t\tcrNeither = CEmuleNextTheme::IsDarkMode() ? CEmuleNextTheme::SurfaceAltColor() : RGB(224, 224, 224);\n\t\tcrNextSending = CEmuleNextTheme::IsDarkMode() ? RGB(196, 155, 0) : RGB(255, 208, 0);\n\t\tcrBoth = CEmuleNextTheme::IsDarkMode() ? CEmuleNextTheme::BorderColor() : (bFlat ? RGB(0, 0, 0) : RGB(104, 104, 104));\n\t\tcrSending = RGB(0, 150, 0);\n\t} else {\n\t\t// grayed out\n\t\tcrNeither = CEmuleNextTheme::IsDarkMode() ? CEmuleNextTheme::SurfaceColor() : RGB(248, 248, 248);\n\t\tcrNextSending = CEmuleNextTheme::IsDarkMode() ? RGB(120, 105, 40) : RGB(255, 244, 191);\n\t\tcrBoth = CEmuleNextTheme::IsDarkMode() ? CEmuleNextTheme::BorderColor() : RGB(191, 191, 191);\n\t\tcrSending = CEmuleNextTheme::IsDarkMode() ? RGB(55, 100, 55) : RGB(191, 229, 191);\n\t}\n'''
    text = replace_once(text, old, new, path)
    save(path, text)


def main() -> int:
    for required in ("DownloadClient.cpp", "UploadClient.cpp"):
        if not (SRC / required).exists():
            raise RuntimeError(f"Missing transfer source: {SRC / required}")
    patch_download()
    patch_upload()
    print("eMule Next transfer status bars themed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
