#!/usr/bin/env python3
"""Materialize the eMule Next Smart Scheduler runtime hooks.

The intelligence implementation lives in normal C++ translation units. This
compatibility activator only adds those files to the upstream vcxproj and places
three narrow, idempotent legacy hooks: queue scheduling, A4AF preference and
rare-part ranking.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"

CPP_FILES = (
    "EmuleNextSchedulerTelemetry.cpp",
    "EmuleNextTransferInsights.cpp",
    "EmuleNextHistoryCache.cpp",
    "EmuleNextSmartScheduler.cpp",
)
HEADER_FILES = (
    "EmuleNextSchedulerTelemetry.h",
    "EmuleNextTransferInsights.h",
    "EmuleNextHistoryCache.h",
    "EmuleNextSmartScheduler.h",
)


def read_text(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def write_text(path: pathlib.Path, text: str, encoding: str) -> None:
    path.write_bytes(text.encode(encoding))


def patch_project() -> None:
    path = SRC / "emule.vcxproj"
    text, encoding = read_text(path)
    changed = False

    compile_anchor = '    <ClCompile Include="DownloadIntelligence.cpp" />'
    include_anchor = '    <ClInclude Include="DownloadIntelligence.h" />'

    for name in CPP_FILES:
        marker = f'    <ClCompile Include="{name}" />'
        if marker not in text:
            if compile_anchor not in text:
                raise SystemExit("Smart Scheduler activation: compile anchor missing in emule.vcxproj")
            text = text.replace(compile_anchor, marker + "\n" + compile_anchor, 1)
            changed = True

    for name in HEADER_FILES:
        marker = f'    <ClInclude Include="{name}" />'
        if marker not in text:
            if include_anchor not in text:
                raise SystemExit("Smart Scheduler activation: header anchor missing in emule.vcxproj")
            text = text.replace(include_anchor, marker + "\n" + include_anchor, 1)
            changed = True

    if changed:
        write_text(path, text, encoding)
        print("Smart Scheduler: project entries materialized")
    else:
        print("Smart Scheduler: project entries already present")


def patch_download_queue() -> None:
    path = SRC / "DownloadQueue.cpp"
    text, encoding = read_text(path)
    changed = False

    include_marker = '#include "EmuleNextSmartScheduler.h"'
    if include_marker not in text:
        anchor = '#include "EmuleNextRuntime.h"'
        if anchor not in text:
            raise SystemExit("Smart Scheduler activation: DownloadQueue include anchor missing")
        text = text.replace(anchor, anchor + "\n" + include_marker, 1)
        changed = True

    hook = "\ttheEmuleNextScheduler.Tick(this); // eMule Next bounded Smart Scheduler pass"
    if hook not in text:
        anchor = "void CDownloadQueue::Process()\n{\n"
        if anchor not in text:
            anchor = "void CDownloadQueue::Process()\r\n{\r\n"
        if anchor not in text:
            raise SystemExit("Smart Scheduler activation: DownloadQueue::Process anchor missing")
        newline = "\r\n" if "\r\n" in anchor else "\n"
        text = text.replace(anchor, anchor + hook + newline, 1)
        changed = True

    if changed:
        write_text(path, text, encoding)
        print("Smart Scheduler: DownloadQueue runtime hook materialized")
    else:
        print("Smart Scheduler: DownloadQueue hook already present")


def patch_download_client() -> None:
    path = SRC / "DownloadClient.cpp"
    text, encoding = read_text(path)
    changed = False

    include_marker = '#include "EmuleNextSmartScheduler.h"'
    if include_marker not in text:
        anchor = '#include "PartFile.h"'
        if anchor not in text:
            raise SystemExit("Smart Scheduler activation: DownloadClient include anchor missing")
        text = text.replace(anchor, anchor + "\n" + include_marker, 1)
        changed = True

    legacy = "bool rightFileHasHigherPrio = CPartFile::RightFileHasHigherPrio(SwapTo, cur_file);"
    hook = "bool rightFileHasHigherPrio = theEmuleNextScheduler.PreferA4AFCandidate(SwapTo, cur_file, CPartFile::RightFileHasHigherPrio(SwapTo, cur_file));"
    if hook not in text:
        if legacy not in text:
            raise SystemExit("Smart Scheduler activation: A4AF priority anchor missing")
        text = text.replace(legacy, hook, 1)
        changed = True

    if changed:
        write_text(path, text, encoding)
        print("Smart Scheduler: A4AF preference hook materialized")
    else:
        print("Smart Scheduler: A4AF hook already present")


def patch_part_file() -> None:
    path = SRC / "PartFile.cpp"
    text, encoding = read_text(path)
    changed = False

    include_marker = '#include "EmuleNextSmartScheduler.h"'
    if include_marker not in text:
        anchor = '#include "PartFileWriteThread.h"'
        if anchor not in text:
            raise SystemExit("Smart Scheduler activation: PartFile include anchor missing")
        text = text.replace(anchor, anchor + "\n" + include_marker, 1)
        changed = True

    hook = "cur_chunk.rank = theEmuleNextScheduler.AdjustPartRank(this, cur_chunk.part, cur_chunk.frequency, cur_chunk.rank);"
    if hook not in text:
        anchor = '//AddDebugLogLine(DLP_VERYLOW, false, _T("Rank: %u"), cur_chunk.rank);'
        if anchor not in text:
            raise SystemExit("Smart Scheduler activation: rare-part rank anchor missing")
        text = text.replace(anchor, hook + "\n\t\t\t\t" + anchor, 1)
        changed = True

    if changed:
        write_text(path, text, encoding)
        print("Smart Scheduler: rare-part ranking hook materialized")
    else:
        print("Smart Scheduler: rare-part hook already present")


def main() -> int:
    for name in CPP_FILES + HEADER_FILES:
        if not (SRC / name).exists():
            raise SystemExit(f"Smart Scheduler activation: required source missing: {name}")
    patch_project()
    patch_download_queue()
    patch_download_client()
    patch_part_file()
    print("Smart Scheduler runtime activation complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
