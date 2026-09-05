#!/usr/bin/env python3
"""Apply eMule Next dark-mode hooks to the materialized legacy core."""
from __future__ import annotations

import pathlib
import re

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


def insert_after(text: str, anchor: str, addition: str, path: pathlib.Path) -> str:
    if addition.strip() in text:
        return text
    if anchor not in text:
        raise RuntimeError(f"Required dark-mode anchor not found in {path}: {anchor!r}")
    return text.replace(anchor, anchor + addition, 1)


def patch_project() -> None:
    path = SRC / "emule.vcxproj"
    text = load(path)
    dep_pattern = re.compile(r"<AdditionalDependencies>(.*?)</AdditionalDependencies>")

    def add_theme_libraries(match: re.Match[str]) -> str:
        value = match.group(1)
        lower = value.lower()
        prefix = ""
        # EmuleNextTheme calls both APIs directly; unlike the optional ordinal
        # probes those calls need normal SDK import libraries at link time.
        for library in ("dwmapi.lib", "uxtheme.lib"):
            if library not in lower:
                prefix += library + ";"
        if not prefix:
            return match.group(0)
        return f"<AdditionalDependencies>{prefix}{value}</AdditionalDependencies>"

    text, count = dep_pattern.subn(add_theme_libraries, text)
    if count == 0:
        raise RuntimeError("No linker dependency entries found for dark mode")

    if (SRC / "EmuleNextTheme.cpp").exists() and 'Include="EmuleNextTheme.cpp"' not in text:
        anchor = '    <ClCompile Include="EmuleNextDatabase.cpp" />\n'
        if anchor not in text:
            raise RuntimeError("Unable to add EmuleNextTheme.cpp to project")
        text = text.replace(anchor, anchor + '    <ClCompile Include="EmuleNextTheme.cpp" />\n', 1)
    save(path, text)


def patch_emule() -> None:
    path = SRC / "Emule.cpp"
    text = load(path)
    text = insert_after(text, '#include "EmuleNextRuntime.h"\n', '#include "EmuleNextTheme.h"\n', path)
    text = insert_after(
        text,
        '\tthePrefs.Init();\n',
        '\t// eMule Next dark mode is persisted in the normal profile and defaults on.\n'
        '\tCEmuleNextTheme::Initialize();\n',
        path,
    )
    save(path, text)


def patch_search_results() -> None:
    path = SRC / "SearchResultsWnd.cpp"
    text = load(path)
    text = insert_after(text, '#include "Log.h"\n', '#include "EmuleNextTheme.h"\n', path)
    text = insert_after(
        text,
        '\tShowSearchSelector(false); //hide tabs, anchor list control\n',
        '\t// Apply after the main search controls exist; eMule Next controls also\n'
        '\t// apply the theme from their own OnCreate handlers.\n'
        '\tif (theApp.emuledlg != NULL)\n'
        '\t\tCEmuleNextTheme::ApplyToWindow(theApp.emuledlg->GetSafeHwnd());\n',
        path,
    )
    save(path, text)


def main() -> int:
    for required in ("emule.vcxproj", "Emule.cpp", "SearchResultsWnd.cpp", "EmuleNextTheme.cpp"):
        if not (SRC / required).exists():
            raise RuntimeError(f"Missing dark-mode source: {SRC / required}")
    patch_project()
    patch_emule()
    patch_search_results()
    print("eMule Next dark mode hooks active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
