#!/usr/bin/env python3
'''Harden generated Preview 2 Dashboard layout for legacy MSVC/MFC min/max semantics.'''
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
CPP = ROOT / "srchybrid" / "EmuleNextDashboardWnd.cpp"


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
    if not CPP.exists():
        raise SystemExit("Preview2 Dashboard compile hardening: Dashboard source missing")

    text, newline = load(CPP)
    start = text.find("void CEmuleNextDashboardWnd::OnSize(UINT type, int cx, int cy)\n{")
    end = text.find("\nvoid CEmuleNextDashboardWnd::OnTimer", start)
    if start < 0 or end < 0:
        raise SystemExit("Preview2 Dashboard compile hardening: OnSize boundary missing")

    hardened = r'''void CEmuleNextDashboardWnd::OnSize(UINT type, int cx, int cy)
{
    CWnd::OnSize(type, cx, cy);
    if (!::IsWindow(m_downloads.m_hWnd))
        return;

    const int margin = CEmuleNextModernUi::PageMargin(m_hWnd);
    const int gap = CEmuleNextModernUi::ControlGap(m_hWnd);
    const int summaryHeight = CEmuleNextModernUi::Scale(m_hWnd, 28);
    const int controlHeight = CEmuleNextModernUi::ControlHeight(m_hWnd);
    int clientWidth = cx - margin * 2;
    if (clientWidth < 0)
        clientWidth = 0;

    m_summary.MoveWindow(margin, margin, clientWidth, summaryHeight);

    CButton* primaryFilters[] = {
        &m_filterAll, &m_filterAttention, &m_filterStalled, &m_filterNoSources, &m_filterActive
    };
    const int filterTop = margin + summaryHeight + gap;
    const int minFilterWidth = CEmuleNextModernUi::Scale(m_hWnd, 96);
    int filterWidth = (clientWidth - gap * (_countof(primaryFilters) - 1)) / _countof(primaryFilters);
    if (filterWidth < minFilterWidth)
        filterWidth = minFilterWidth;
    for (int i = 0; i < _countof(primaryFilters); ++i)
        primaryFilters[i]->MoveWindow(margin + i * (filterWidth + gap), filterTop, filterWidth, controlHeight);

    const int actionHeight = CEmuleNextModernUi::ControlHeight(m_hWnd);
    const int listTop = filterTop + controlHeight + gap;
    const int minDetailsHeight = CEmuleNextModernUi::Scale(m_hWnd, 130);
    const int maxDetailsHeight = CEmuleNextModernUi::Scale(m_hWnd, 220);
    int detailsHeight = cy / 4;
    if (detailsHeight < minDetailsHeight)
        detailsHeight = minDetailsHeight;
    else if (detailsHeight > maxDetailsHeight)
        detailsHeight = maxDetailsHeight;

    const int minListHeight = CEmuleNextModernUi::Scale(m_hWnd, 100);
    int listHeight = cy - listTop - detailsHeight - actionHeight - margin - gap * 3;
    if (listHeight < minListHeight)
        listHeight = minListHeight;
    m_downloads.MoveWindow(margin, listTop, clientWidth, listHeight);

    CButton* primaryActions[] = { &m_openTransfers, &m_openSources, &m_pauseResume, &m_refreshNow, &m_more };
    const int actionTop = listTop + listHeight + gap;
    const int minActionWidth = CEmuleNextModernUi::Scale(m_hWnd, 110);
    int actionWidth = (clientWidth - gap * (_countof(primaryActions) - 1)) / _countof(primaryActions);
    if (actionWidth < minActionWidth)
        actionWidth = minActionWidth;
    for (int i = 0; i < _countof(primaryActions); ++i)
        primaryActions[i]->MoveWindow(margin + i * (actionWidth + gap), actionTop, actionWidth, actionHeight);

    const int detailsTop = actionTop + actionHeight + gap;
    int remainingDetailsHeight = cy - detailsTop - margin;
    if (remainingDetailsHeight < 0)
        remainingDetailsHeight = 0;
    m_details.MoveWindow(margin, detailsTop, clientWidth, remainingDetailsHeight);
}
'''
    text = text[:start] + hardened + text[end:]

    window = text[start:start + len(hardened) + 256]
    for forbidden in (" max(", " min(", "std::max", "std::min"):
        if forbidden in window:
            raise SystemExit(f"Preview2 Dashboard compile hardening: incompatible layout helper remains: {forbidden.strip()}")

    save(CPP, text, newline)
    print("eMule Next Preview 2 Dashboard compile hardening materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
