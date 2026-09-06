#!/usr/bin/env python3
'''Final-state verification for the known Preview 2 Release x64 warning set.'''
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def read(rel: str) -> str:
    path = SRC / rel
    if not path.exists():
        raise SystemExit(f"Warning cleanup verification: missing {rel}")
    return path.read_bytes().decode("latin-1", errors="ignore")


def main() -> int:
    dashboard_h = read("EmuleNextDashboardWnd.h")
    dashboard_cpp = read("EmuleNextDashboardWnd.cpp")
    intelligence_h = read("DownloadIntelligenceWnd.h")
    intelligence_cpp = read("DownloadIntelligenceWnd.cpp")
    search_list = read("SearchList.cpp")
    kad_search = read("kademlia/kademlia/Search.cpp")
    shared = read("SharedFilesCtrl.cpp")
    main_cpp = read("EmuleDlg.cpp")
    project = read("emule.vcxproj")

    for label, text, cls in (
        ("Dashboard header", dashboard_h, "CEmuleNextDashboardWnd"),
        ("Download Intelligence header", intelligence_h, "CDownloadIntelligenceWnd"),
    ):
        if "bool CreateView(CWnd* parent);" not in text or "bool Create(CWnd* parent);" in text:
            raise SystemExit(f"Warning cleanup verification: {label} still hides CWnd::Create")
    if "CEmuleNextDashboardWnd::CreateView(CWnd* parent)" not in dashboard_cpp:
        raise SystemExit("Warning cleanup verification: Dashboard CreateView definition missing")
    if "CDownloadIntelligenceWnd::CreateView(CWnd* parent)" not in intelligence_cpp:
        raise SystemExit("Warning cleanup verification: Download Intelligence CreateView definition missing")

    if "LPCTSTR pvPropValue = va_arg(args, LPCTSTR);" in search_list:
        raise SystemExit("Warning cleanup verification: Kad varargs still transport integers through pointers")
    if "const uint32 uPropValue = va_arg(args, uint32);" not in search_list:
        raise SystemExit("Warning cleanup verification: typed Kad uint32 vararg read missing")
    for old in ("(LPCTSTR)uLength", "(LPCTSTR)uBitrate", "(LPCTSTR)uAvailability"):
        if old in kad_search:
            raise SystemExit(f"Warning cleanup verification: legacy Kad integer pointer cast remains: {old}")

    if "(UINT)m_PrioMenu.m_hMenu" in shared:
        raise SystemExit("Warning cleanup verification: HMENU-to-UINT truncation remains")
    if "submenu->m_hMenu == m_PrioMenu.m_hMenu" not in shared or "MF_BYPOSITION" not in shared:
        raise SystemExit("Warning cleanup verification: x64-safe Shared Files submenu enable logic missing")

    if re.search(r"void CemuleDlg::UpdatePreview2HeaderStatus\(\).*?CString status =", main_cpp, re.S):
        raise SystemExit("Warning cleanup verification: Preview2 local status still shadows CemuleDlg::status")
    if "CString statusText = GetConnectionStateString();" not in main_cpp:
        raise SystemExit("Warning cleanup verification: renamed Preview2 header status variable missing")

    mfc_files = (
        "ChatSelector.cpp", "ChatWnd.cpp", "ClientListCtrl.cpp", "DownloadClientsCtrl.cpp",
        "DownloadListCtrl.cpp", "EmuleDlg.cpp", "FriendListCtrl.cpp", "SearchResultsWnd.cpp",
        "SharedFilesCtrl.cpp",
    )
    for name in mfc_files:
        text = read(name)
        if "#pragma warning(disable:4191)\nBEGIN_MESSAGE_MAP" not in text:
            raise SystemExit(f"Warning cleanup verification: local MFC C4191 guard missing in {name}")
        if "END_MESSAGE_MAP()\n#pragma warning(pop)" not in text:
            raise SystemExit(f"Warning cleanup verification: MFC warning scope not closed in {name}")

    release_start = project.find('<ItemDefinitionGroup Condition="\'$(Configuration)\'==\'Release\'">')
    release_end = project.find("</ItemDefinitionGroup>", release_start)
    if release_start < 0 or release_end < 0:
        raise SystemExit("Warning cleanup verification: Release project group missing")
    release = project[release_start:release_end]
    if "<LinkTimeCodeGeneration>UseLinkTimeCodeGeneration</LinkTimeCodeGeneration>" not in release:
        raise SystemExit("Warning cleanup verification: Release LTCG not enabled")

    print("eMule Next Preview 2 warning-cleanup verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
