#!/usr/bin/env python3
'''Final-state verification for Preview 2 Release x64 zero-warning policy.'''
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
ACTIVE_MAP = re.compile(
    r"^[ \t]*BEGIN_MESSAGE_MAP\([^\n]*\)\n.*?^[ \t]*END_MESSAGE_MAP\(\)",
    re.M | re.S,
)
CWND_CLASS = re.compile(
    r"class\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*public\s+CWnd\s*\n\{(?P<body>.*?)\n\};",
    re.S,
)


def read(rel: str) -> str:
    path = SRC / rel
    if not path.exists():
        raise SystemExit(f"Warning cleanup verification: missing {rel}")
    return path.read_bytes().decode("latin-1", errors="ignore").replace("\r\n", "\n").replace("\r", "\n")


def main() -> int:
    dashboard_h = read("EmuleNextDashboardWnd.h")
    dashboard_cpp = read("EmuleNextDashboardWnd.cpp")
    intelligence_h = read("DownloadIntelligenceWnd.h")
    intelligence_cpp = read("DownloadIntelligenceWnd.cpp")
    search2_h = read("Search2Wnd.h")
    search2_cpp = read("Search2Wnd.cpp")
    library_h = read("FileLibraryWnd.h")
    library_cpp = read("FileLibraryWnd.cpp")
    settings_h = read("EmuleNextSettingsWnd.h")
    settings_cpp = read("EmuleNextSettingsWnd.cpp")
    diagnostics_h = read("EmuleNextDiagnosticsWnd.h")
    transfer = read("TransferWnd.cpp")
    results = read("SearchResultsWnd.cpp")
    search_list = read("SearchList.cpp")
    kad_search = read("kademlia/kademlia/Search.cpp")
    shared = read("SharedFilesCtrl.cpp")
    shared_dirs = read("SharedDirsTreeCtrl.cpp")
    main_cpp = read("EmuleDlg.cpp")
    project = read("emule.vcxproj")
    oscope = read("OScopeCtrl.cpp")
    preview = read("Preview.cpp")
    smiley = read("SmileySelector.cpp")
    titled = read("TitledMenu.cpp")
    http_header = read("HttpDownloadDlg.h")

    for label, text in (
        ("Dashboard header", dashboard_h),
        ("Download Intelligence header", intelligence_h),
        ("Search2 header", search2_h),
        ("Library header", library_h),
        ("Settings header", settings_h),
    ):
        if "bool CreateView(CWnd* parent);" not in text or "bool Create(CWnd* parent);" in text:
            raise SystemExit(f"Warning cleanup verification: {label} still hides CWnd::Create")
    if "CEmuleNextDashboardWnd::CreateView(CWnd* parent)" not in dashboard_cpp:
        raise SystemExit("Warning cleanup verification: Dashboard CreateView definition missing")
    if "CDownloadIntelligenceWnd::CreateView(CWnd* parent)" not in intelligence_cpp:
        raise SystemExit("Warning cleanup verification: Download Intelligence CreateView definition missing")
    if "CSearch2Wnd::CreateView(CWnd* parent)" not in search2_cpp or "CSearch2Wnd::Create(CWnd* parent)" in search2_cpp:
        raise SystemExit("Warning cleanup verification: Search2 CreateView definition missing")
    if "CFileLibraryWnd::CreateView(CWnd* parent)" not in library_cpp or "CFileLibraryWnd::Create(CWnd* parent)" in library_cpp:
        raise SystemExit("Warning cleanup verification: Library CreateView definition missing")
    if "CEmuleNextSettingsWnd::CreateView(CWnd* parent)" not in settings_cpp or "CEmuleNextSettingsWnd::Create(CWnd* parent)" in settings_cpp:
        raise SystemExit("Warning cleanup verification: Settings CreateView definition missing")
    if "m_nextDashboard.CreateView(this)" not in transfer or "m_nextDashboard.Create(this)" in transfer:
        raise SystemExit("Warning cleanup verification: Dashboard host call not migrated to CreateView")
    if "m_downloadIntelligenceWnd.CreateView(this)" not in results or "m_downloadIntelligenceWnd.Create(this)" in results:
        raise SystemExit("Warning cleanup verification: Download Intelligence host call not migrated to CreateView")
    if re.search(r"\b[A-Za-z_][A-Za-z0-9_]*search2[A-Za-z0-9_]*\.Create\(", results, re.I):
        raise SystemExit("Warning cleanup verification: Search2 host call still uses Create")
    if re.search(r"\b[A-Za-z_][A-Za-z0-9_]*library[A-Za-z0-9_]*\.Create\(", results, re.I):
        raise SystemExit("Warning cleanup verification: Library host call still uses Create")
    if "m_nextSettingsWnd.Create(" in results or "m_nextSettingsWnd.CreateView(" not in results:
        raise SystemExit("Warning cleanup verification: Settings host call not migrated to CreateView")

    # Any remaining convenience Create overload on an eMule Next CWnd must
    # explicitly expose CWnd::Create. This catches Diagnostics and future views
    # without waiting for another full rebuild warning.
    checked_cwnd_classes = 0
    for path in sorted(SRC.glob("*.h")):
        if not (path.name.startswith("EmuleNext") or path.name in {
            "KnownUsersWnd.h", "Search2Wnd.h", "FileLibraryWnd.h", "DownloadIntelligenceWnd.h"
        }):
            continue
        text = path.read_bytes().decode("latin-1", errors="ignore").replace("\r\n", "\n").replace("\r", "\n")
        for match in CWND_CLASS.finditer(text):
            body = match.group("body")
            if not re.search(r"\b(?:bool|BOOL)\s+Create\s*\(", body):
                continue
            checked_cwnd_classes += 1
            if "using CWnd::Create;" not in body:
                raise SystemExit(
                    f"Warning cleanup verification: {path.name}:{match.group(1)} hides CWnd::Create"
                )
    if "bool Create(CWnd* parent);" in diagnostics_h and "using CWnd::Create;" not in diagnostics_h:
        raise SystemExit("Warning cleanup verification: Diagnostics Create overload not hardened")

    if "LPCTSTR pvPropValue = va_arg(args, LPCTSTR);" in search_list:
        raise SystemExit("Warning cleanup verification: Kad varargs still transport integers through pointers")
    if "const uint32 uPropValue = va_arg(args, uint32);" not in search_list:
        raise SystemExit("Warning cleanup verification: typed Kad uint32 vararg read missing")
    for old in ("(LPCTSTR)uLength", "(LPCTSTR)uBitrate", "(LPCTSTR)uAvailability"):
        if old in kad_search:
            raise SystemExit(f"Warning cleanup verification: legacy Kad integer pointer cast remains: {old}")

    if "(UINT)m_PrioMenu.m_hMenu" in shared:
        raise SystemExit("Warning cleanup verification: Shared Files HMENU-to-UINT truncation remains")
    if "submenu->m_hMenu == m_PrioMenu.m_hMenu" not in shared or "MF_BYPOSITION" not in shared:
        raise SystemExit("Warning cleanup verification: x64-safe Shared Files submenu enable logic missing")
    if "(UINT)m_PrioMenu.m_hMenu" in shared_dirs:
        raise SystemExit("Warning cleanup verification: SharedDirs HMENU-to-UINT truncation remains")
    if "submenu->m_hMenu == m_PrioMenu.m_hMenu" not in shared_dirs or "MF_BYPOSITION" not in shared_dirs:
        raise SystemExit("Warning cleanup verification: x64-safe SharedDirs submenu enable logic missing")

    if re.search(r"void CemuleDlg::UpdatePreview2HeaderStatus\(\).*?CString status =", main_cpp, re.S):
        raise SystemExit("Warning cleanup verification: Preview2 local status still shadows CemuleDlg::status")
    if "CString statusText = GetConnectionStateString();" not in main_cpp:
        raise SystemExit("Warning cleanup verification: renamed Preview2 header status variable missing")
    if "(PChangeWindowMessageFilter)(::GetProcAddress" in main_cpp or "reinterpret_cast<PChangeWindowMessageFilter>" in main_cpp:
        raise SystemExit("Warning cleanup verification: FARPROC function-pointer cast remains")
    if "changeWindowMessageFilterProc" not in main_cpp or "::CopyMemory(&ChangeWindowMessageFilter" not in main_cpp:
        raise SystemExit("Warning cleanup verification: x64-safe ChangeWindowMessageFilter resolution missing")

    if "(HMENU)nID" in oscope or "static_cast<UINT_PTR>(nID)" not in oscope:
        raise SystemExit("Warning cleanup verification: OScope child ID still truncates to HMENU")
    if "DWORD dwError = (DWORD)::ShellExecute" in preview or "const INT_PTR shellResult = reinterpret_cast<INT_PTR>(::ShellExecute" not in preview:
        raise SystemExit("Warning cleanup verification: ShellExecute result still truncates HINSTANCE")
    if "#pragma warning(disable:4191)\n//BEGIN_MESSAGE_MAP" in preview:
        raise SystemExit("Warning cleanup verification: commented Preview message map was modified")
    if "(HBRUSH)(crBackground + 1)" in smiley or "::GetSysColorBrush(nBackgroundColorIndex)" not in smiley:
        raise SystemExit("Warning cleanup verification: SmileySelector brush still uses integer-to-handle cast")
    if "nPos = (int)pvIndex;" in titled or "(void*)nPos" in titled:
        raise SystemExit("Warning cleanup verification: TitledMenu pointer/int truncation remains")
    if "PtrToInt(pvIndex)" not in titled or "IntToPtr(nPos)" not in titled:
        raise SystemExit("Warning cleanup verification: TitledMenu pointer-width helpers missing")
    if "#pragma warning(disable:4266)\n#include <afxinet.h>\n#pragma warning(pop)" not in http_header:
        raise SystemExit("Warning cleanup verification: vendor afxinet C4266 scope missing")

    total_maps = 0
    for path in SRC.rglob("*.cpp"):
        text = path.read_bytes().decode("latin-1", errors="ignore").replace("\r\n", "\n").replace("\r", "\n")
        maps = list(ACTIVE_MAP.finditer(text))
        total_maps += len(maps)
        for match in maps:
            prefix = text[max(0, match.start()-110):match.start()]
            suffix = text[match.end():match.end()+55]
            if "#pragma warning(disable:4191)" not in prefix or "#pragma warning(pop)" not in suffix:
                raise SystemExit(f"Warning cleanup verification: unguarded active MFC message map in {path.name}")
    if total_maps == 0:
        raise SystemExit("Warning cleanup verification: no active MFC message maps discovered")

    release_start = project.find('<ItemDefinitionGroup Condition="\'$(Configuration)\'==\'Release\'">')
    release_end = project.find("</ItemDefinitionGroup>", release_start)
    if release_start < 0 or release_end < 0:
        raise SystemExit("Warning cleanup verification: Release project group missing")
    release = project[release_start:release_end]
    if "<LinkTimeCodeGeneration>UseLinkTimeCodeGeneration</LinkTimeCodeGeneration>" not in release:
        raise SystemExit("Warning cleanup verification: Release LTCG not enabled")
    if "<TreatWarningAsError>true</TreatWarningAsError>" not in release:
        raise SystemExit("Warning cleanup verification: compiler /WX zero-warning contract missing")
    if "<TreatLinkerWarningAsErrors>true</TreatLinkerWarningAsErrors>" not in release:
        raise SystemExit("Warning cleanup verification: linker /WX zero-warning contract missing")

    print(
        f"eMule Next Preview 2 zero-warning verification passed "
        f"({total_maps} active MFC maps guarded; {checked_cwnd_classes} custom CWnd Create overloads hardened)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
