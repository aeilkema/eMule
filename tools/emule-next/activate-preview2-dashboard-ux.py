#!/usr/bin/env python3
'''Apply progressive-complexity UX to the Preview 2 Dashboard.

Primary filters/actions stay visible. Specialist intelligence filters and
maintenance-like transfer actions remain fully available through one More menu.
No transfer/scheduler backend behavior is changed.
'''
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
HEADER = SRC / "EmuleNextDashboardWnd.h"
CPP = SRC / "EmuleNextDashboardWnd.cpp"


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


def main() -> int:
    header, hn = load(HEADER)
    cpp, cn = load(CPP)

    if "CButton m_more;" not in header:
        anchor = "    CButton m_refreshNow;\n"
        if anchor not in header:
            raise SystemExit("Preview2 Dashboard UX: refresh member anchor missing")
        header = header.replace(anchor, anchor + "    CButton m_more;\n", 1)
    if "afx_msg void OnMoreClicked();" not in header:
        anchor = "    afx_msg void OnRefreshNow();\n"
        if anchor not in header:
            raise SystemExit("Preview2 Dashboard UX: refresh handler anchor missing")
        header = header.replace(anchor, anchor + "    afx_msg void OnMoreClicked();\n", 1)

    if "IDC_EN_DASH_MORE" not in cpp:
        old = "        IDC_EN_DASH_REFRESH_NOW,\n        IDC_EN_DASH_DETAILS\n"
        new = "        IDC_EN_DASH_REFRESH_NOW,\n        IDC_EN_DASH_DETAILS,\n        IDC_EN_DASH_MORE\n"
        if old not in cpp:
            raise SystemExit("Preview2 Dashboard UX: control-id anchor missing")
        cpp = cpp.replace(old, new, 1)

    if "ON_BN_CLICKED(IDC_EN_DASH_MORE, OnMoreClicked)" not in cpp:
        anchor = "    ON_BN_CLICKED(IDC_EN_DASH_REFRESH_NOW, OnRefreshNow)\n"
        if anchor not in cpp:
            raise SystemExit("Preview2 Dashboard UX: message-map anchor missing")
        cpp = cpp.replace(anchor, anchor + "    ON_BN_CLICKED(IDC_EN_DASH_MORE, OnMoreClicked)\n", 1)

    if 'm_more.Create(_T("More..."' not in cpp:
        old = '        || !m_refreshNow.Create(_T("Refresh"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DASH_REFRESH_NOW)\n        || !m_details.Create(_T("Select a download for detailed intelligence."), WS_CHILD | WS_VISIBLE | SS_LEFT,\n            empty, this, IDC_EN_DASH_DETAILS)) {'
        new = '        || !m_refreshNow.Create(_T("Refresh"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DASH_REFRESH_NOW)\n        || !m_more.Create(_T("More..."), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_DASH_MORE)\n        || !m_details.Create(_T("Select a download for detailed intelligence."), WS_CHILD | WS_VISIBLE | SS_LEFT,\n            empty, this, IDC_EN_DASH_DETAILS)) {'
        if old not in cpp:
            raise SystemExit("Preview2 Dashboard UX: create-chain anchor missing")
        cpp = cpp.replace(old, new, 1)

    cpp = cpp.replace("&m_priorityNormal, &m_forceAnalysis, &m_resetIntelligence, &m_refreshNow, &m_details",
                      "&m_priorityNormal, &m_forceAnalysis, &m_resetIntelligence, &m_refreshNow, &m_more, &m_details")

    hide_marker = "    // Preview 2 progressive complexity: specialist controls live in More.\n"
    if hide_marker not in cpp:
        anchor = "    for (int i = 0; i < _countof(controls); ++i)\n        controls[i]->SetFont(font);\n"
        if anchor not in cpp:
            raise SystemExit("Preview2 Dashboard UX: font loop anchor missing")
        hide = hide_marker + '''    m_filterRare.ShowWindow(SW_HIDE);
    m_filterLowHealth.ShowWindow(SW_HIDE);
    m_filterIntervention.ShowWindow(SW_HIDE);
    m_filterA4AF.ShowWindow(SW_HIDE);
    m_priorityHigh.ShowWindow(SW_HIDE);
    m_priorityNormal.ShowWindow(SW_HIDE);
    m_forceAnalysis.ShowWindow(SW_HIDE);
    m_resetIntelligence.ShowWindow(SW_HIDE);
'''
        cpp = cpp.replace(anchor, anchor + hide, 1)

    start = cpp.find("void CEmuleNextDashboardWnd::OnSize(UINT type, int cx, int cy)\n{")
    end = cpp.find("\nvoid CEmuleNextDashboardWnd::OnTimer", start)
    if start < 0 or end < 0:
        raise SystemExit("Preview2 Dashboard UX: OnSize boundary missing")
    modern_size = r'''void CEmuleNextDashboardWnd::OnSize(UINT type, int cx, int cy)
{
    CWnd::OnSize(type, cx, cy);
    if (!::IsWindow(m_downloads.m_hWnd))
        return;

    const int margin = CEmuleNextModernUi::PageMargin(m_hWnd);
    const int gap = CEmuleNextModernUi::ControlGap(m_hWnd);
    const int summaryHeight = CEmuleNextModernUi::Scale(m_hWnd, 28);
    const int controlHeight = CEmuleNextModernUi::ControlHeight(m_hWnd);
    const int clientWidth = max(0, cx - margin * 2);

    m_summary.MoveWindow(margin, margin, clientWidth, summaryHeight);

    CButton* primaryFilters[] = {
        &m_filterAll, &m_filterAttention, &m_filterStalled, &m_filterNoSources, &m_filterActive
    };
    const int filterTop = margin + summaryHeight + gap;
    const int filterWidth = max(CEmuleNextModernUi::Scale(m_hWnd, 96),
        (clientWidth - gap * (_countof(primaryFilters) - 1)) / _countof(primaryFilters));
    for (int i = 0; i < _countof(primaryFilters); ++i)
        primaryFilters[i]->MoveWindow(margin + i * (filterWidth + gap), filterTop, filterWidth, controlHeight);

    const int actionHeight = CEmuleNextModernUi::ControlHeight(m_hWnd);
    const int listTop = filterTop + controlHeight + gap;
    const int detailsHeight = max(CEmuleNextModernUi::Scale(m_hWnd, 130), min(CEmuleNextModernUi::Scale(m_hWnd, 220), cy / 4));
    const int listHeight = max(CEmuleNextModernUi::Scale(m_hWnd, 100),
        cy - listTop - detailsHeight - actionHeight - margin - gap * 3);
    m_downloads.MoveWindow(margin, listTop, clientWidth, listHeight);

    CButton* primaryActions[] = { &m_openTransfers, &m_openSources, &m_pauseResume, &m_refreshNow, &m_more };
    const int actionTop = listTop + listHeight + gap;
    const int actionWidth = max(CEmuleNextModernUi::Scale(m_hWnd, 110),
        (clientWidth - gap * (_countof(primaryActions) - 1)) / _countof(primaryActions));
    for (int i = 0; i < _countof(primaryActions); ++i)
        primaryActions[i]->MoveWindow(margin + i * (actionWidth + gap), actionTop, actionWidth, actionHeight);

    const int detailsTop = actionTop + actionHeight + gap;
    m_details.MoveWindow(margin, detailsTop, clientWidth, max(0, cy - detailsTop - margin));
}
'''
    cpp = cpp[:start] + modern_size + cpp[end:]

    old_summary = '''    summary.Format(_T("Downloads: %u   Active: %u   Attention: %u   Stalled: %u   Rare: %u   No sources: %u   Down: %s/s   Uploads: %u   Showing: %u%s   Refresh: %ums   |   Scheduler: %s"),
        total, transferring, attentionCount, stalled, rare, noSources,
        (LPCTSTR)CastItoXBytes(totalRate, false, false, 1), activeUploads,
        static_cast<unsigned>(m_downloads.GetItemCount()), truncated ? _T(" (capped at 1000)") : _T(""),
        static_cast<unsigned>(m_lastRefreshDurationMs), (LPCTSTR)theEmuleNextScheduler.GetRuntimeStatusText());
'''
    new_summary = '''    summary.Format(_T("%u downloads   |   %u active   |   %u need attention   |   %s/s down   |   %u uploads   |   Scheduler: %s%s"),
        total, transferring, attentionCount,
        (LPCTSTR)CastItoXBytes(totalRate, false, false, 1), activeUploads,
        (LPCTSTR)theEmuleNextScheduler.GetRuntimeStatusText(), truncated ? _T("   |   showing first 1000") : _T(""));
'''
    if old_summary in cpp:
        cpp = cpp.replace(old_summary, new_summary, 1)
    elif "%u downloads   |   %u active" not in cpp:
        raise SystemExit("Preview2 Dashboard UX: summary format anchor missing")

    if "void CEmuleNextDashboardWnd::OnMoreClicked()" not in cpp:
        anchor = "void CEmuleNextDashboardWnd::OnRefreshNow()"
        pos = cpp.find(anchor)
        if pos < 0:
            raise SystemExit("Preview2 Dashboard UX: refresh handler boundary missing")
        handler = r'''void CEmuleNextDashboardWnd::OnMoreClicked()
{
    CMenu menu;
    if (!menu.CreatePopupMenu())
        return;

    enum { CMD_RARE = 1, CMD_LOW_HEALTH, CMD_INTERVENTION, CMD_A4AF, CMD_PRIORITY_HIGH,
        CMD_PRIORITY_NORMAL, CMD_FORCE_ANALYSIS, CMD_RESET_INTELLIGENCE };

    menu.AppendMenu(MF_STRING | (m_filter == DASH_RARE ? MF_CHECKED : 0), CMD_RARE, _T("Filter: Rare parts"));
    menu.AppendMenu(MF_STRING | (m_filter == DASH_LOW_HEALTH ? MF_CHECKED : 0), CMD_LOW_HEALTH, _T("Filter: Low health"));
    menu.AppendMenu(MF_STRING | (m_filter == DASH_INTERVENTION ? MF_CHECKED : 0), CMD_INTERVENTION, _T("Filter: Intervention"));
    menu.AppendMenu(MF_STRING | (m_filter == DASH_A4AF_OPPORTUNITY ? MF_CHECKED : 0), CMD_A4AF, _T("Filter: A4AF opportunity"));
    menu.AppendMenu(MF_SEPARATOR);
    menu.AppendMenu(MF_STRING, CMD_PRIORITY_HIGH, _T("Set priority high"));
    menu.AppendMenu(MF_STRING, CMD_PRIORITY_NORMAL, _T("Set priority normal"));
    menu.AppendMenu(MF_STRING, CMD_FORCE_ANALYSIS, _T("Force intelligence analysis"));
    menu.AppendMenu(MF_SEPARATOR);
    menu.AppendMenu(MF_STRING, CMD_RESET_INTELLIGENCE, _T("Reset selected intelligence history"));

    CRect rect;
    m_more.GetWindowRect(&rect);
    const UINT command = menu.TrackPopupMenu(TPM_LEFTALIGN | TPM_TOPALIGN | TPM_RETURNCMD,
        rect.left, rect.bottom, this);
    switch (command) {
    case CMD_RARE: SetFilter(DASH_RARE); break;
    case CMD_LOW_HEALTH: SetFilter(DASH_LOW_HEALTH); break;
    case CMD_INTERVENTION: SetFilter(DASH_INTERVENTION); break;
    case CMD_A4AF: SetFilter(DASH_A4AF_OPPORTUNITY); break;
    case CMD_PRIORITY_HIGH: OnPriorityHigh(); break;
    case CMD_PRIORITY_NORMAL: OnPriorityNormal(); break;
    case CMD_FORCE_ANALYSIS: OnForceAnalysis(); break;
    case CMD_RESET_INTELLIGENCE: OnResetIntelligence(); break;
    }
}

'''
        cpp = cpp[:pos] + handler + cpp[pos:]

    required = (
        "m_more",
        "Preview 2 progressive complexity",
        "primaryFilters",
        "primaryActions",
        "OnMoreClicked",
        "%u downloads   |   %u active",
    )
    final = header + "\n" + cpp
    for marker in required:
        if marker not in final:
            raise SystemExit(f"Preview2 Dashboard UX: final marker missing {marker}")

    save(HEADER, header, hn)
    save(CPP, cpp, cn)
    print("eMule Next Preview 2 Dashboard progressive UX materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
