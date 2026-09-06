#!/usr/bin/env python3
'''Remove the known Preview 2 Release x64 warning set without global suppression.

Real 64-bit issues are fixed structurally. C4191 is suppressed only around the
legacy MFC message-map macro blocks which perform the framework's own member
pointer casts; handler signatures remain unchanged and are checked separately.
'''
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"


def load(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    newline = "\r\n" if crlf >= lf and crlf else "\n"
    return raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n"), newline


def save(path: pathlib.Path, text: str, newline: str) -> None:
    if newline != "\n":
        text = text.replace("\n", newline)
    path.write_bytes(text.encode("latin-1"))


def patch_dashboard_create() -> None:
    h = SRC / "EmuleNextDashboardWnd.h"
    cpp = SRC / "EmuleNextDashboardWnd.cpp"
    ht, hn = load(h)
    ct, cn = load(cpp)
    if "bool CreateView(CWnd* parent);" not in ht:
        if "bool Create(CWnd* parent);" not in ht:
            raise SystemExit("Warning cleanup: Dashboard Create declaration missing")
        ht = ht.replace("bool Create(CWnd* parent);", "bool CreateView(CWnd* parent);", 1)
    if "CEmuleNextDashboardWnd::CreateView" not in ct:
        if "CEmuleNextDashboardWnd::Create(CWnd* parent)" not in ct:
            raise SystemExit("Warning cleanup: Dashboard Create definition missing")
        ct = ct.replace("CEmuleNextDashboardWnd::Create(CWnd* parent)", "CEmuleNextDashboardWnd::CreateView(CWnd* parent)", 1)
    save(h, ht, hn)
    save(cpp, ct, cn)

    found = False
    for path in SRC.glob("*.cpp"):
        text, nl = load(path)
        changed = text
        for member in ("m_nextDashboard", "m_dashboardWnd"):
            changed = changed.replace(f"{member}.Create(", f"{member}.CreateView(")
        if changed != text:
            found = True
            save(path, changed, nl)
    if not found:
        # Idempotent reruns may already contain CreateView.
        if not any("m_nextDashboard.CreateView(" in load(path)[0] for path in SRC.glob("*.cpp")):
            raise SystemExit("Warning cleanup: Dashboard host Create call missing")


def patch_download_intelligence_create() -> None:
    h = SRC / "DownloadIntelligenceWnd.h"
    cpp = SRC / "DownloadIntelligenceWnd.cpp"
    ht, hn = load(h)
    ct, cn = load(cpp)
    if "bool CreateView(CWnd* parent);" not in ht:
        if "bool Create(CWnd* parent);" not in ht:
            raise SystemExit("Warning cleanup: Download Intelligence Create declaration missing")
        ht = ht.replace("bool Create(CWnd* parent);", "bool CreateView(CWnd* parent);", 1)
    if "CDownloadIntelligenceWnd::CreateView" not in ct:
        if "CDownloadIntelligenceWnd::Create(CWnd* parent)" not in ct:
            raise SystemExit("Warning cleanup: Download Intelligence Create definition missing")
        ct = ct.replace("CDownloadIntelligenceWnd::Create(CWnd* parent)", "CDownloadIntelligenceWnd::CreateView(CWnd* parent)", 1)
    save(h, ht, hn)
    save(cpp, ct, cn)

    found = False
    for path in SRC.glob("*.cpp"):
        text, nl = load(path)
        changed = text
        for member in ("m_downloadIntelligenceWnd", "m_intelligenceWnd"):
            changed = changed.replace(f"{member}.Create(", f"{member}.CreateView(")
        if changed != text:
            found = True
            save(path, changed, nl)
    if not found:
        if not any("m_downloadIntelligenceWnd.CreateView(" in load(path)[0] for path in SRC.glob("*.cpp")):
            raise SystemExit("Warning cleanup: Download Intelligence host Create call missing")


def patch_kad_varargs() -> None:
    search_list = SRC / "SearchList.cpp"
    text, nl = load(search_list)
    old = '''\t\tUINT uPropType = va_arg(args, UINT);\n\t\tLPCSTR pszPropName = va_arg(args, LPCSTR);\n\t\tLPCTSTR pvPropValue = va_arg(args, LPCTSTR);\n\t\tif (uPropType == TAGTYPE_STRING) {\n\t\t\tif (pvPropValue && *pvPropValue) {\n\t\t\t\tif (strlen(pszPropName) == 1) {\n\t\t\t\t\tCTag tagProp((uint8)*pszPropName, pvPropValue);\n\t\t\t\t\ttagProp.WriteTagToFile(temp, eStrEncode);\n\t\t\t\t} else {\n\t\t\t\t\tCTag tagProp(pszPropName, pvPropValue);\n\t\t\t\t\ttagProp.WriteTagToFile(temp, eStrEncode);\n\t\t\t\t}\n\t\t\t\tverifierEntry.AddTag(new Kademlia::CKadTagStr(pszPropName, pvPropValue));\n\t\t\t\t++tagcount;\n\t\t\t}\n\t\t} else if (uPropType == TAGTYPE_UINT32) {\n\t\t\tif ((uint32)pvPropValue != 0) {\n\t\t\t\tCTag tagProp(pszPropName, (uint32)pvPropValue);\n\t\t\t\ttagProp.WriteTagToFile(temp, eStrEncode);\n\t\t\t\t++tagcount;\n\t\t\t\tverifierEntry.AddTag(new Kademlia::CKadTagUInt(pszPropName, (uint32)pvPropValue));\n\t\t\t}\n\t\t} else\n\t\t\tASSERT(0);\n'''
    new = '''\t\tUINT uPropType = va_arg(args, UINT);\n\t\tLPCSTR pszPropName = va_arg(args, LPCSTR);\n\t\tif (uPropType == TAGTYPE_STRING) {\n\t\t\tLPCTSTR pszPropValue = va_arg(args, LPCTSTR);\n\t\t\tif (pszPropValue && *pszPropValue) {\n\t\t\t\tif (strlen(pszPropName) == 1) {\n\t\t\t\t\tCTag tagProp((uint8)*pszPropName, pszPropValue);\n\t\t\t\t\ttagProp.WriteTagToFile(temp, eStrEncode);\n\t\t\t\t} else {\n\t\t\t\t\tCTag tagProp(pszPropName, pszPropValue);\n\t\t\t\t\ttagProp.WriteTagToFile(temp, eStrEncode);\n\t\t\t\t}\n\t\t\t\tverifierEntry.AddTag(new Kademlia::CKadTagStr(pszPropName, pszPropValue));\n\t\t\t\t++tagcount;\n\t\t\t}\n\t\t} else if (uPropType == TAGTYPE_UINT32) {\n\t\t\tconst uint32 uPropValue = va_arg(args, uint32);\n\t\t\tif (uPropValue != 0) {\n\t\t\t\tCTag tagProp(pszPropName, uPropValue);\n\t\t\t\ttagProp.WriteTagToFile(temp, eStrEncode);\n\t\t\t\t++tagcount;\n\t\t\t\tverifierEntry.AddTag(new Kademlia::CKadTagUInt(pszPropName, uPropValue));\n\t\t\t}\n\t\t} else {\n\t\t\tASSERT(0);\n\t\t\t(void)va_arg(args, LPCTSTR);\n\t\t}\n'''
    if old in text:
        text = text.replace(old, new, 1)
    elif "const uint32 uPropValue = va_arg(args, uint32);" not in text:
        raise SystemExit("Warning cleanup: Kad property varargs block missing")
    save(search_list, text, nl)

    kad = SRC / "kademlia" / "kademlia" / "Search.cpp"
    text, nl = load(kad)
    for name in ("uLength", "uBitrate", "uAvailability"):
        text = text.replace(f"(LPCTSTR){name}", name)
    if "#pragma warning(disable:4312)\nvoid CSearch::ProcessResultKeyword" in text:
        text = text.replace("#pragma warning(push)\n#pragma warning(disable:4312)\nvoid CSearch::ProcessResultKeyword", "void CSearch::ProcessResultKeyword", 1)
        text = text.replace("}\n#pragma warning(pop)\n\nvoid CSearch::SendFindValue", "}\n\nvoid CSearch::SendFindValue", 1)
    save(kad, text, nl)


def patch_shared_menu_x64() -> None:
    path = SRC / "SharedFilesCtrl.cpp"
    text, nl = load(path)
    old = '''\tm_SharedFilesMenu.EnableMenuItem((UINT)m_PrioMenu.m_hMenu, (!bContainsShareableFiles && iSelectedItems > 0) ? MF_ENABLED : MF_GRAYED);'''
    new = '''\tfor (int menuPos = 0; menuPos < m_SharedFilesMenu.GetMenuItemCount(); ++menuPos) {\n\t\tCMenu* submenu = m_SharedFilesMenu.GetSubMenu(menuPos);\n\t\tif (submenu != NULL && submenu->m_hMenu == m_PrioMenu.m_hMenu) {\n\t\t\tm_SharedFilesMenu.EnableMenuItem(menuPos, MF_BYPOSITION | ((!bContainsShareableFiles && iSelectedItems > 0) ? MF_ENABLED : MF_GRAYED));\n\t\t\tbreak;\n\t\t}\n\t}'''
    if old in text:
        text = text.replace(old, new, 1)
    elif "submenu->m_hMenu == m_PrioMenu.m_hMenu" not in text:
        raise SystemExit("Warning cleanup: Shared Files priority submenu anchor missing")
    save(path, text, nl)


def patch_mfc_message_map_warnings() -> None:
    # C4191 is emitted by VS 18 for MFC's own message-map member-pointer cast.
    # Suppress it only for the macro-generated table, never project-wide.
    files = (
        "ChatSelector.cpp", "ChatWnd.cpp", "ClientListCtrl.cpp", "DownloadClientsCtrl.cpp",
        "DownloadListCtrl.cpp", "EmuleDlg.cpp", "FriendListCtrl.cpp", "SearchResultsWnd.cpp",
        "SharedFilesCtrl.cpp",
    )
    for name in files:
        path = SRC / name
        text, nl = load(path)
        if "#pragma warning(disable:4191)\nBEGIN_MESSAGE_MAP" in text:
            continue
        begin = text.find("BEGIN_MESSAGE_MAP(")
        end = text.find("END_MESSAGE_MAP()", begin)
        if begin < 0 or end < 0:
            raise SystemExit(f"Warning cleanup: message map missing in {name}")
        text = text[:begin] + "#pragma warning(push)\n#pragma warning(disable:4191)\n" + text[begin:]
        end = text.find("END_MESSAGE_MAP()", begin) + len("END_MESSAGE_MAP()")
        text = text[:end] + "\n#pragma warning(pop)" + text[end:]
        save(path, text, nl)


def patch_header_status_shadow() -> None:
    path = SRC / "EmuleDlg.cpp"
    text, nl = load(path)
    block = re.search(r"void CemuleDlg::UpdatePreview2HeaderStatus\(\)\n\{.*?\n\}", text, re.S)
    if block is None:
        raise SystemExit("Warning cleanup: Preview2 header status method missing")
    replacement = block.group(0).replace("CString status =", "CString statusText =")
    replacement = replacement.replace("status +=", "statusText +=")
    replacement = replacement.replace("SetWindowText(status);", "SetWindowText(statusText);")
    text = text[:block.start()] + replacement + text[block.end():]
    save(path, text, nl)


def patch_ltcg() -> None:
    path = SRC / "emule.vcxproj"
    text, nl = load(path)
    # id3lib Release is /GL; explicitly enabling LTCG avoids the linker restart.
    release_start = text.find('<ItemDefinitionGroup Condition="\'$(Configuration)\'==\'Release\'">')
    release_end = text.find("</ItemDefinitionGroup>", release_start)
    if release_start < 0 or release_end < 0:
        raise SystemExit("Warning cleanup: Release ItemDefinitionGroup missing")
    block = text[release_start:release_end]
    if "<LinkTimeCodeGeneration>UseLinkTimeCodeGeneration</LinkTimeCodeGeneration>" not in block:
        anchor = "      <OptimizeReferences>true</OptimizeReferences>\n"
        if anchor not in block:
            raise SystemExit("Warning cleanup: Release linker optimization anchor missing")
        block = block.replace(anchor, anchor + "      <LinkTimeCodeGeneration>UseLinkTimeCodeGeneration</LinkTimeCodeGeneration>\n", 1)
        text = text[:release_start] + block + text[release_end:]
    save(path, text, nl)


def main() -> int:
    patch_dashboard_create()
    patch_download_intelligence_create()
    patch_kad_varargs()
    patch_shared_menu_x64()
    patch_mfc_message_map_warnings()
    patch_header_status_shadow()
    patch_ltcg()
    print("eMule Next Preview 2 warning cleanup materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
