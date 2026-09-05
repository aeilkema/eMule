#!/usr/bin/env python3
"""Activate Download Intelligence UI and persist network names during share discovery."""
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


def add_after(text: str, anchor: str, addition: str, path: pathlib.Path) -> str:
    if addition.strip() in text:
        return text
    if anchor not in text:
        raise RuntimeError(f"Required anchor not found in {path}: {anchor!r}")
    return text.replace(anchor, anchor + addition, 1)


def patch_share_peer_name() -> None:
    path = SRC / "SearchList.cpp"
    text = load(path)
    anchor = "\t\tconst unsigned char* peerHash = sender.GetUserHash();\n"
    addition = (
        "\t\t// Preserve the real network username for peers discovered through\n"
        "\t\t// shared-file responses. Alias remains separate local metadata.\n"
        "\t\ttheEmuleNext.RecordPeerSeen(peerHash, sender.GetUserName(),\n"
        "\t\t\tsender.GetClientSoftVer(), CString(), sender.GetIP(),\n"
        "\t\t\tsender.GetUserPort(), sender.GetKadPort(), sender.GetKadPort());\n"
    )
    text = add_after(text, anchor, addition, path)
    save(path, text)


def patch_header() -> None:
    path = SRC / "SearchResultsWnd.h"
    text = load(path)
    text = add_after(text, '#include "KnownUsersWnd.h"\n', '#include "DownloadIntelligenceWnd.h"\n', path)
    text = add_after(text, '\tCKnownUsersWnd m_knownUsersWnd;\n', '\tCDownloadIntelligenceWnd m_downloadIntelligenceWnd;\n', path)
    save(path, text)


def patch_results() -> None:
    path = SRC / "SearchResultsWnd.cpp"
    text = load(path)

    old_persistent = (
        "\treturn searchID == EMULENEXT_KNOWN_USERS_VIEW_ID\n"
        "\t\t|| searchID == EMULENEXT_SEARCH2_VIEW_ID\n"
    )
    new_persistent = (
        "\treturn searchID == EMULENEXT_KNOWN_USERS_VIEW_ID\n"
        "\t\t|| searchID == EMULENEXT_DOWNLOAD_INTELLIGENCE_VIEW_ID\n"
        "\t\t|| searchID == EMULENEXT_SEARCH2_VIEW_ID\n"
    )
    if "|| searchID == EMULENEXT_DOWNLOAD_INTELLIGENCE_VIEW_ID" not in text:
        if old_persistent not in text:
            raise RuntimeError("Persistent-view anchor not found")
        text = text.replace(old_persistent, new_persistent, 1)

    create_anchor = "\tif (m_search2Wnd.Create(this)) {\n"
    create_block = (
        "\tif (m_downloadIntelligenceWnd.Create(this)) {\n"
        "\t\tm_downloadIntelligenceWnd.ShowWindow(SW_HIDE);\n"
        "\t\tm_downloadIntelligenceWnd.MoveWindow(&nextViewRect);\n"
        "\t\tAddAnchor(m_downloadIntelligenceWnd, TOP_LEFT, BOTTOM_RIGHT);\n"
        "\t\tSSearchParams *intelligence = new SSearchParams;\n"
        "\t\tintelligence->dwSearchID = EMULENEXT_DOWNLOAD_INTELLIGENCE_VIEW_ID;\n"
        "\t\tintelligence->strExpression = _T(\"Download Intelligence\");\n"
        "\t\tintelligence->strSpecialTitle = _T(\"Download Intelligence\");\n"
        "\t\tif (!CreateOrFindTab(intelligence, false)) delete intelligence;\n"
        "\t}\n\n"
    )
    if "intelligence->dwSearchID = EMULENEXT_DOWNLOAD_INTELLIGENCE_VIEW_ID" not in text:
        if create_anchor not in text:
            raise RuntimeError("Download Intelligence create anchor not found")
        text = text.replace(create_anchor, create_block + create_anchor, 1)

    show_results_anchor = (
        "void CSearchResultsWnd::ShowResults(const SSearchParams *pParams)\n"
        "{\n"
        "\tm_knownUsersWnd.ShowWindow(SW_HIDE);\n"
    )
    show_results_replacement = (
        "void CSearchResultsWnd::ShowResults(const SSearchParams *pParams)\n"
        "{\n"
        "\tm_knownUsersWnd.ShowWindow(SW_HIDE);\n"
        "\tm_downloadIntelligenceWnd.ShowWindow(SW_HIDE);\n"
    )
    if show_results_replacement not in text:
        if show_results_anchor not in text:
            raise RuntimeError("ShowResults hide anchor not found")
        text = text.replace(show_results_anchor, show_results_replacement, 1)

    branch_anchor = (
        "\t\tif (pParams->dwSearchID == EMULENEXT_KNOWN_USERS_VIEW_ID) {\n"
        "\t\t\tm_knownUsersWnd.ShowWindow(SW_SHOW);\n"
        "\t\t\tm_knownUsersWnd.Refresh(true);\n"
        "\t\t}\n"
        "\t\telse if (pParams->dwSearchID == EMULENEXT_SEARCH2_VIEW_ID) {\n"
    )
    branch_replacement = (
        "\t\tif (pParams->dwSearchID == EMULENEXT_KNOWN_USERS_VIEW_ID) {\n"
        "\t\t\tm_knownUsersWnd.ShowWindow(SW_SHOW);\n"
        "\t\t\tm_knownUsersWnd.Refresh(true);\n"
        "\t\t}\n"
        "\t\telse if (pParams->dwSearchID == EMULENEXT_DOWNLOAD_INTELLIGENCE_VIEW_ID) {\n"
        "\t\t\tm_downloadIntelligenceWnd.ShowWindow(SW_SHOW);\n"
        "\t\t\tm_downloadIntelligenceWnd.Refresh(true);\n"
        "\t\t}\n"
        "\t\telse if (pParams->dwSearchID == EMULENEXT_SEARCH2_VIEW_ID) {\n"
    )
    if "pParams->dwSearchID == EMULENEXT_DOWNLOAD_INTELLIGENCE_VIEW_ID" not in text:
        if branch_anchor not in text:
            raise RuntimeError("ShowResults branch anchor not found")
        text = text.replace(branch_anchor, branch_replacement, 1)

    save(path, text)


def patch_project() -> None:
    path = SRC / "emule.vcxproj"
    text = load(path)
    additions = (
        '    <ClCompile Include="DownloadIntelligenceService.cpp" />\n'
        '    <ClCompile Include="DownloadIntelligenceWnd.cpp" />\n'
    )
    if 'Include="DownloadIntelligenceWnd.cpp"' not in text:
        anchor = '    <ClCompile Include="DownloadIntelligence.cpp" />\n'
        if anchor not in text:
            raise RuntimeError("DownloadIntelligence.cpp project anchor not found")
        text = text.replace(anchor, anchor + additions, 1)
    save(path, text)


def main() -> int:
    for required in (
        "SearchList.cpp", "SearchResultsWnd.h", "SearchResultsWnd.cpp", "emule.vcxproj",
        "DownloadIntelligenceService.cpp", "DownloadIntelligenceWnd.cpp"
    ):
        if not (SRC / required).exists():
            raise RuntimeError(f"Missing Download Intelligence source: {SRC / required}")
    patch_share_peer_name()
    patch_header()
    patch_results()
    patch_project()
    print("eMule Next peer names and Download Intelligence view active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
