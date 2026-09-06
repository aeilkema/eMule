#!/usr/bin/env python3
'''Make Search 2 the primary Preview 2 search experience while preserving legacy network search.

The main Search route opens Search 2. A Network search... action in Search 2
returns to the authoritative legacy eD2K/Kad search parameters/results. No
network search implementation is duplicated.
'''
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
HEADER = SRC / "Search2Wnd.h"
CPP = SRC / "Search2Wnd.cpp"
MAIN = SRC / "EmuleDlg.cpp"


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


def patch_search2() -> None:
    header, hn = load(HEADER)
    cpp, cn = load(CPP)

    if "CButton m_networkSearch;" not in header:
        anchor = "    CButton m_rules;\n"
        if anchor not in header:
            raise SystemExit("Preview2 Search UX: final Search2 rules member missing")
        header = header.replace(anchor, anchor + "    CButton m_networkSearch;\n", 1)
    if "afx_msg void OnNetworkSearchClicked();" not in header:
        anchor = "    afx_msg void OnRulesClicked();\n"
        if anchor not in header:
            raise SystemExit("Preview2 Search UX: rules handler anchor missing")
        header = header.replace(anchor, anchor + "    afx_msg void OnNetworkSearchClicked();\n", 1)

    # SearchDlg.h exposes methods used by the legacy-network bridge, but its
    # public surface references CSearchResultsWnd. Keep SearchResultsWnd.h ahead
    # of SearchDlg.h so this late materialization has an explicit compile-order
    # contract instead of relying on precompiled-header side effects.
    if '#include "SearchResultsWnd.h"' not in cpp:
        anchor = '#include "emule.h"\n'
        if anchor not in cpp:
            raise SystemExit("Preview2 Search UX: emule include anchor missing")
        cpp = cpp.replace(anchor, anchor + '#include "SearchResultsWnd.h"\n', 1)
    if '#include "SearchDlg.h"' not in cpp:
        anchor = '#include "SearchResultsWnd.h"\n'
        if anchor not in cpp:
            raise SystemExit("Preview2 Search UX: SearchResults include anchor missing")
        cpp = cpp.replace(anchor, anchor + '#include "SearchDlg.h"\n', 1)
    if '#include "emuledlg.h"' not in cpp:
        anchor = '#include "SearchDlg.h"\n'
        if anchor not in cpp:
            raise SystemExit("Preview2 Search UX: SearchDlg include anchor missing")
        cpp = cpp.replace(anchor, anchor + '#include "emuledlg.h"\n', 1)

    # Normalize a previously materialized unsafe order if this script is run
    # against a retained activation stage.
    includes = ('#include "SearchResultsWnd.h"', '#include "SearchDlg.h"', '#include "emuledlg.h"')
    if all(item in cpp for item in includes):
        for item in includes:
            cpp = cpp.replace(item + "\n", "", 1)
        anchor = '#include "emule.h"\n'
        if anchor not in cpp:
            raise SystemExit("Preview2 Search UX: include normalization anchor missing")
        cpp = cpp.replace(anchor, anchor + "\n".join(includes) + "\n", 1)

    if "IDC_EN_SEARCH2_NETWORK" not in cpp:
        old = "        IDC_EN_SEARCH2_RULES\n"
        new = "        IDC_EN_SEARCH2_RULES,\n        IDC_EN_SEARCH2_NETWORK\n"
        if old not in cpp:
            raise SystemExit("Preview2 Search UX: final Search2 id anchor missing")
        cpp = cpp.replace(old, new, 1)

    if "ON_BN_CLICKED(IDC_EN_SEARCH2_NETWORK, OnNetworkSearchClicked)" not in cpp:
        anchor = "    ON_BN_CLICKED(IDC_EN_SEARCH2_RULES, OnRulesClicked)\n"
        if anchor not in cpp:
            raise SystemExit("Preview2 Search UX: Search2 message-map anchor missing")
        cpp = cpp.replace(anchor, anchor + "    ON_BN_CLICKED(IDC_EN_SEARCH2_NETWORK, OnNetworkSearchClicked)\n", 1)

    if 'm_networkSearch.Create(_T("Network search..."' not in cpp:
        old = '''        || !m_rules.Create(_T("Block rules"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_SEARCH2_RULES)) {'''
        new = '''        || !m_rules.Create(_T("Block rules"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_SEARCH2_RULES)
        || !m_networkSearch.Create(_T("Network search..."), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_SEARCH2_NETWORK)) {'''
        if old not in cpp:
            raise SystemExit("Preview2 Search UX: Search2 create-chain anchor missing")
        cpp = cpp.replace(old, new, 1)

    if "m_networkSearch.SetFont(font);" not in cpp:
        anchor = "    m_export.SetFont(font); m_rules.SetFont(font);\n"
        if anchor not in cpp:
            raise SystemExit("Preview2 Search UX: Search2 font anchor missing")
        cpp = cpp.replace(anchor, anchor + "    m_networkSearch.SetFont(font);\n", 1)

    # Do not replace Search2's generated filter/action layout. Reuse the final
    # query/search rectangles after LayoutControls so this remains compatible
    # with the proven Search2 product activators and DPI spacing substitutions.
    if "Preview 2: place Network search beside the knowledge search" not in cpp:
        signature = "void CSearch2Wnd::OnSize(UINT type, int cx, int cy)\n{"
        start = cpp.find(signature)
        if start < 0:
            raise SystemExit("Preview2 Search UX: Search2 OnSize missing")
        close = cpp.find("\n}", start)
        if close < 0:
            raise SystemExit("Preview2 Search UX: Search2 OnSize boundary missing")
        body = cpp[start:close]
        layout_call = "        LayoutControls(cx, cy);"
        if layout_call not in body:
            raise SystemExit("Preview2 Search UX: Search2 LayoutControls call missing")
        addition = r'''
    // Preview 2: place Network search beside the knowledge search without
    // coupling this late product layer to the generated filter layout.
    if (::IsWindow(m_networkSearch.m_hWnd) && ::IsWindow(m_search.m_hWnd) && ::IsWindow(m_query.m_hWnd)) {
        CRect searchRect;
        CRect queryRect;
        m_search.GetWindowRect(&searchRect);
        m_query.GetWindowRect(&queryRect);
        ScreenToClient(&searchRect);
        ScreenToClient(&queryRect);
        const int gap = CEmuleNextModernUi::ControlGap(m_hWnd);
        const int networkWidth = CEmuleNextModernUi::Scale(m_hWnd, 132);
        const int searchWidth = CEmuleNextModernUi::Scale(m_hWnd, 112);
        searchRect.left = searchRect.right - searchWidth;
        m_search.MoveWindow(&searchRect);
        CRect networkRect(searchRect.left - gap - networkWidth, searchRect.top,
            searchRect.left - gap, searchRect.bottom);
        m_networkSearch.MoveWindow(&networkRect);
        queryRect.right = max(queryRect.left + CEmuleNextModernUi::Scale(m_hWnd, 120), networkRect.left - gap);
        m_query.MoveWindow(&queryRect);
    }
'''
        cpp = cpp[:close] + addition + cpp[close:]

    if "void CSearch2Wnd::OnNetworkSearchClicked()" not in cpp:
        anchor = "void CSearch2Wnd::OnRulesClicked()"
        pos = cpp.find(anchor)
        if pos < 0:
            raise SystemExit("Preview2 Search UX: rules handler boundary missing")
        handler = r'''void CSearch2Wnd::OnNetworkSearchClicked()
{
    if (theApp.emuledlg == NULL || theApp.emuledlg->searchwnd == NULL)
        return;
    theApp.emuledlg->SetActiveDialog(theApp.emuledlg->searchwnd);
    if (theApp.emuledlg->searchwnd->m_pwndResults != NULL)
        theApp.emuledlg->searchwnd->m_pwndResults->ShowLegacySearchWorkspace();
    theApp.emuledlg->searchwnd->OpenParametersWnd();
}

'''
        cpp = cpp[:pos] + handler + cpp[pos:]

    save(HEADER, header, hn)
    save(CPP, cpp, cn)


def patch_primary_route() -> None:
    text, newline = load(MAIN)
    old = '''\tcase 2: // Legacy-authoritative Search
\t\tSetActiveDialog(searchwnd);
\t\tif (searchwnd != NULL && searchwnd->m_pwndResults != NULL)
\t\t\tsearchwnd->m_pwndResults->ShowLegacySearchWorkspace();
\t\tbreak;
'''
    new = '''\tcase 2: // Modern Search 2; legacy network search remains explicit inside it.
\t\tSetActiveDialog(searchwnd);
\t\tif (searchwnd != NULL && searchwnd->m_pwndResults != NULL)
\t\t\tsearchwnd->m_pwndResults->ShowNextWorkspace(EMULENEXT_SEARCH2_VIEW_ID);
\t\tbreak;
'''
    if old in text:
        text = text.replace(old, new, 1)
    elif "ShowNextWorkspace(EMULENEXT_SEARCH2_VIEW_ID)" not in text:
        raise SystemExit("Preview2 Search UX: primary Search route anchor missing")
    save(MAIN, text, newline)


def verify() -> None:
    header = HEADER.read_bytes().decode("latin-1", errors="ignore")
    cpp = CPP.read_bytes().decode("latin-1", errors="ignore")
    main = MAIN.read_bytes().decode("latin-1", errors="ignore")
    for marker in (
        "m_networkSearch",
        "Network search...",
        "OnNetworkSearchClicked",
        "ShowLegacySearchWorkspace()",
        "OpenParametersWnd()",
        "place Network search beside the knowledge search",
    ):
        if marker not in header + "\n" + cpp:
            raise SystemExit(f"Preview2 Search UX: final contract missing {marker}")
    if "ShowNextWorkspace(EMULENEXT_SEARCH2_VIEW_ID)" not in main:
        raise SystemExit("Preview2 Search UX: main Search route is not Search 2")
    if cpp.find('#include "SearchResultsWnd.h"') > cpp.find('#include "SearchDlg.h"'):
        raise SystemExit("Preview2 Search UX: unsafe SearchDlg/SearchResults include order")


def main() -> int:
    patch_search2()
    patch_primary_route()
    verify()
    print("eMule Next Preview 2 Search UX materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
