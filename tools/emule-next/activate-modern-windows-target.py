#!/usr/bin/env python3
"""Make the eMule Next x64 overlay target Windows 10/11 instead of XP.

The upstream project still defines XP_BUILD for every non-ARM64 build. eMule
Next uses WinSQLite, which is a Windows 10 API; winsqlite3.h hides parts of its
API surface when the compilation target is older. Keep XP_BUILD only for the
legacy Win32 configuration and explicitly target Windows 10 for x64.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROJECT = ROOT / "srchybrid" / "emule.vcxproj"

OLD = "      <PreprocessorDefinitions Condition=\"'$(Platform)'!='ARM64'\">XP_BUILD;%(PreprocessorDefinitions)</PreprocessorDefinitions>\n"
NEW = (
    "      <PreprocessorDefinitions Condition=\"'$(Platform)'=='Win32'\">XP_BUILD;%(PreprocessorDefinitions)</PreprocessorDefinitions>\n"
    "      <PreprocessorDefinitions Condition=\"'$(Platform)'=='x64'\">WINVER=0x0A00;_WIN32_WINNT=0x0A00;%(PreprocessorDefinitions)</PreprocessorDefinitions>\n"
)


def main() -> int:
    raw = PROJECT.read_bytes()
    text = raw.decode("utf-8-sig")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    old_count = text.count(OLD)
    modern_count = text.count("_WIN32_WINNT=0x0A00")

    if old_count:
        if old_count != 3:
            raise SystemExit(f"Modern Windows target: expected 3 legacy XP_BUILD definitions, found {old_count}")
        text = text.replace(OLD, NEW)
    elif modern_count != 3:
        raise SystemExit(
            "Modern Windows target: neither the 3 legacy definitions nor the 3 modern x64 definitions were found"
        )

    if "Condition=\"'$(Platform)'!='ARM64'\">XP_BUILD" in text:
        raise SystemExit("Modern Windows target: XP_BUILD still applies to x64")
    if text.count("Condition=\"'$(Platform)'=='Win32'\">XP_BUILD") != 3:
        raise SystemExit("Modern Windows target: Win32 XP compatibility definitions incomplete")
    if text.count("Condition=\"'$(Platform)'=='x64'\">WINVER=0x0A00;_WIN32_WINNT=0x0A00") != 3:
        raise SystemExit("Modern Windows target: x64 Windows 10 definitions incomplete")

    PROJECT.write_bytes(text.encode("utf-8-sig"))
    print("eMule Next x64 Windows 10/11 target active; XP_BUILD retained only for Win32")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
