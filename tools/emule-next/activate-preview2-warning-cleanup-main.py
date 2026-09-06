#!/usr/bin/env python3
'''Remove remaining Preview2 warning classes in EmuleDlg/project linker settings.'''
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def load(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes(); crlf = raw.count(b"\r\n"); lf = raw.count(b"\n") - crlf
    nl = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n"), nl


def save(path: pathlib.Path, text: str, nl: str) -> None:
    if nl != "\n": text = text.replace("\n", nl)
    path.write_bytes(text.encode("latin-1"))


def main() -> int:
    path = SRC / "EmuleDlg.cpp"
    text, nl = load(path)
    block = re.search(r"void CemuleDlg::UpdatePreview2HeaderStatus\(\)\n\{.*?\n\}", text, re.S)
    if block is None:
        raise SystemExit("Main warning cleanup: Preview2 header status method missing")
    replacement = block.group(0).replace("CString status =", "CString statusText =")
    replacement = replacement.replace("status +=", "statusText +=")
    replacement = replacement.replace("SetWindowText(status);", "SetWindowText(statusText);")
    text = text[:block.start()] + replacement + text[block.end():]

    old = '''\t\t\ttypedef BOOL(WINAPI *PChangeWindowMessageFilter)(UINT message, DWORD dwFlag);\n\t\t\tPChangeWindowMessageFilter ChangeWindowMessageFilter\n\t\t\t\t= (PChangeWindowMessageFilter)(::GetProcAddress(::GetModuleHandle(_T("user32.dll")), "ChangeWindowMessageFilter"));'''
    new = '''\t\t\ttypedef BOOL(WINAPI *PChangeWindowMessageFilter)(UINT message, DWORD dwFlag);\n\t\t\tPChangeWindowMessageFilter ChangeWindowMessageFilter = NULL;\n\t\t\tFARPROC changeWindowMessageFilterProc = ::GetProcAddress(::GetModuleHandle(_T("user32.dll")), "ChangeWindowMessageFilter");\n\t\t\tstatic_assert(sizeof(changeWindowMessageFilterProc) == sizeof(ChangeWindowMessageFilter), "function pointer size mismatch");\n\t\t\t::CopyMemory(&ChangeWindowMessageFilter, &changeWindowMessageFilterProc, sizeof(ChangeWindowMessageFilter));'''
    if old in text:
        text = text.replace(old, new, 1)
    elif "changeWindowMessageFilterProc" not in text:
        raise SystemExit("Main warning cleanup: ChangeWindowMessageFilter cast anchor missing")
    text = text.replace("memcpy(&ChangeWindowMessageFilter, &changeWindowMessageFilterProc, sizeof(ChangeWindowMessageFilter));", "::CopyMemory(&ChangeWindowMessageFilter, &changeWindowMessageFilterProc, sizeof(ChangeWindowMessageFilter));")
    save(path, text, nl)

    project = SRC / "emule.vcxproj"
    text, nl = load(project)
    start = text.find('<ItemDefinitionGroup Condition="\'$(Configuration)\'==\'Release\'">')
    end = text.find("</ItemDefinitionGroup>", start)
    if start < 0 or end < 0:
        raise SystemExit("Main warning cleanup: Release ItemDefinitionGroup missing")
    block = text[start:end]
    ltcg = "<LinkTimeCodeGeneration>UseLinkTimeCodeGeneration</LinkTimeCodeGeneration>"
    if ltcg not in block:
        anchor = "      <OptimizeReferences>true</OptimizeReferences>\n"
        if anchor not in block:
            raise SystemExit("Main warning cleanup: Release linker optimization anchor missing")
        block = block.replace(anchor, anchor + f"      {ltcg}\n", 1)
    if "<TreatLinkerWarningAsErrors>true</TreatLinkerWarningAsErrors>" not in block:
        link_anchor = "    <Link>\n"
        if link_anchor not in block:
            raise SystemExit("Main warning cleanup: Release linker group missing")
        block = block.replace(link_anchor, link_anchor + "      <TreatLinkerWarningAsErrors>true</TreatLinkerWarningAsErrors>\n", 1)
    if "<TreatWarningAsError>true</TreatWarningAsError>" not in block:
        compile_anchor = "    <ClCompile>\n"
        if compile_anchor not in block:
            raise SystemExit("Main warning cleanup: Release compiler group missing")
        block = block.replace(compile_anchor, compile_anchor + "      <TreatWarningAsError>true</TreatWarningAsError>\n", 1)
    text = text[:start] + block + text[end:]
    save(project, text, nl)

    print("Preview 2 compiler/linker zero-warning policy materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
