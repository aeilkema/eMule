#!/usr/bin/env python3
"""Make the eMule Next x64 overlay target the WinSQLite API baseline.

The upstream project still defines XP_BUILD for every non-ARM64 build. eMule
Next uses WinSQLite. A number of SQLite entry points used by scheduler/history
(reset, bind/column double, column type, etc.) were added to winsqlite3.dll in
Windows 10 1511 / TH2 (10.0.10586). `_WIN32_WINNT=0x0A00` alone maps the SDK
header default `NTDDI_VERSION` to Windows 10 1507, so those declarations remain
hidden. Keep XP_BUILD only for legacy Win32 and explicitly target TH2 for x64.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROJECT = ROOT / "srchybrid" / "emule.vcxproj"

OLD = "      <PreprocessorDefinitions Condition=\"'$(Platform)'!='ARM64'\">XP_BUILD;%(PreprocessorDefinitions)</PreprocessorDefinitions>\n"
OLD_MODERN = "      <PreprocessorDefinitions Condition=\"'$(Platform)'=='x64'\">WINVER=0x0A00;_WIN32_WINNT=0x0A00;%(PreprocessorDefinitions)</PreprocessorDefinitions>\n"
X64_MODERN = "      <PreprocessorDefinitions Condition=\"'$(Platform)'=='x64'\">WINVER=0x0A00;_WIN32_WINNT=0x0A00;NTDDI_VERSION=0x0A000001;%(PreprocessorDefinitions)</PreprocessorDefinitions>\n"
NEW = (
    "      <PreprocessorDefinitions Condition=\"'$(Platform)'=='Win32'\">XP_BUILD;%(PreprocessorDefinitions)</PreprocessorDefinitions>\n"
    + X64_MODERN
)


def main() -> int:
    raw = PROJECT.read_bytes()
    text = raw.decode("utf-8-sig")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    old_count = text.count(OLD)
    if old_count:
        if old_count != 3:
            raise SystemExit(f"Modern Windows target: expected 3 legacy XP_BUILD definitions, found {old_count}")
        text = text.replace(OLD, NEW)
    elif OLD_MODERN in text:
        # Upgrade an earlier eMule Next stage that only selected generic Win10.
        text = text.replace(OLD_MODERN, X64_MODERN)

    if "Condition=\"'$(Platform)'!='ARM64'\">XP_BUILD" in text:
        raise SystemExit("Modern Windows target: XP_BUILD still applies to x64")
    if text.count("Condition=\"'$(Platform)'=='Win32'\">XP_BUILD") != 3:
        raise SystemExit("Modern Windows target: Win32 XP compatibility definitions incomplete")
    if text.count("Condition=\"'$(Platform)'=='x64'\">WINVER=0x0A00;_WIN32_WINNT=0x0A00;NTDDI_VERSION=0x0A000001") != 3:
        raise SystemExit("Modern Windows target: x64 Windows 10 TH2 definitions incomplete")

    PROJECT.write_bytes(text.encode("utf-8-sig"))
    print("eMule Next x64 WinSQLite target active: Windows 10 TH2+; XP_BUILD retained only for Win32")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
