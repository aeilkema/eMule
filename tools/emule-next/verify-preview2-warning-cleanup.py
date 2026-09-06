#!/usr/bin/env python3
'''Final-state verification for Preview 2 Release x64 zero-warning policy.'''
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


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
    transfer = read("TransferWnd.cpp")
    results = read("SearchResultsWnd.cpp")
    search_list = read("SearchList.cpp")
    kad_search = read("kademlia/kademlia/Search.cpp")
    shared = read("SharedFilesCtrl.cpp")
    shared_dirs = read("SharedDirsTreeCtrl.cpp")
    main_cpp = read("EmuleDlg.cpp")
    project = read("emule.vcxproj")

    for label, text in (
        ("Dashboard header", dashboard_h),
        ("Download Intelligence header", intelligence_h),
        ("Search2 header", search2_h),
    ):
        if "bool CreateView(CWnd* parent);" not in text or "bool Create(CWnd* parent);" in text:
            raise SystemExit(f"Warning cleanup verification: {label} still hides CWnd::Create")
    if "CEmuleNextDashboardWnd::CreateView(CWnd* parent)" not in dashboard_cpp:
        raise SystemExit("Warning cleanup verification: Dashboard CreateView definition missing")
    if "CDownloadIntelligenceWnd::CreateView(CWnd* parent)" not in intelligence_cpp:
        raise SystemExit("Warning cleanup verification: Download Intelligence CreateView definition missing")
    if "CSearch2Wnd::CreateView(CWnd* parent)" not in search2_cpp or "CSearch2Wnd::Create(CWnd* parent)" in search2_cpp:
        raise SystemExit("Warning cleanup verification: Search2 CreateView definition missing")
    if "m_nextDashboard.CreateView(this)" not in transfer or "m_nextDashboard.Create(this)" in transfer:
        raise SystemExit("Warning cleanup verification: Dashboard host call not migrated to CreateView")
    if "m_downloadIntelligenceWnd.CreateView(this)" not in results or "m_downloadIntelligenceWnd.Create(this)" in results:
        raise SystemExit("Warning cleanup verification: Download Intelligence host call not migrated to CreateView")
    if re.search(r"\b[A-Za-z_][A-Za-z0-9_]*search2[A-Za-z0-9_]*\.Create\(", results, re.I):
        raise SystemExit("Warning cleanup verification: Search2 host call still uses Create")

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

    mfc_files = (
        "ChatSelector.cpp", "ChatWnd.cpp", "ClientListCtrl.cpp", "CollectionCreateDialog.cpp",
        "CollectionViewDialog.cpp", "DownloadClientsCtrl.cpp", "DownloadListCtrl.cpp", "EmuleDlg.cpp",
        "FriendListCtrl.cpp", "SearchResultsWnd.cpp", "SharedFilesCtrl.cpp",
    )
    for name in mfc_files:
        text = read(name)
        maps = list(re.finditer(r"BEGIN_MESSAGE_MAP\(.*?END_MESSAGE_MAP\(\)", text, re.S))
        if not maps:
            raise SystemExit(f"Warning cleanup verification: message map missing in {name}")
        for match in maps:
            prefix = text[max(0, match.start()-90):match.start()]
            suffix = text[match.end():match.end()+45]
            if "#pragma warning(disable:4191)" not in prefix or "#pragma warning(pop)" not in suffix:
                raise SystemExit(f"Warning cleanup verification: unguarded MFC message map in {name}")

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

    print("eMule Next Preview 2 zero-warning verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
