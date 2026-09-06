#!/usr/bin/env python3
'''Expose every production eMule Preferences page from the Preview 2 Settings shell.

Next-specific options stay native in the modern page. The 15 upstream property
pages remain authoritative for legacy settings; Preview 2 routes directly to
those pages instead of copying hundreds of values into a second configuration
model.
'''
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
H = SRC / "EmuleNextSettingsWnd.h"
CPP = SRC / "EmuleNextSettingsWnd.cpp"

PAGES = (
    ("GENERAL", "General", "PPgGeneral.h"),
    ("DISPLAY", "Display", "PPgDisplay.h"),
    ("CONNECTION", "Connection", "PPgConnection.h"),
    ("PROXY", "Proxy", "PPgProxy.h"),
    ("SERVER", "Server", "PPgServer.h"),
    ("DIRECTORIES", "Directories", "PPgDirectories.h"),
    ("FILES", "Files", "PPgFiles.h"),
    ("NOTIFICATIONS", "Notifications", "PPgNotify.h"),
    ("STATISTICS", "Statistics", "PPgStats.h"),
    ("IRC", "IRC", "PPgIRC.h"),
    ("MESSAGES", "Messages", "PPgMessages.h"),
    ("SECURITY", "Security", "PPgSecurity.h"),
    ("SCHEDULER", "Scheduler", "PPgScheduler.h"),
    ("WEB_SERVER", "Web Server", "PPgWebServer.h"),
    ("TWEAKS", "Tweaks", "PPgTweaks.h"),
)


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


def page_ids() -> dict[str, str]:
    result: dict[str, str] = {}
    for key, _label, filename in PAGES:
        text = (SRC / filename).read_text(encoding="latin-1")
        match = re.search(r"\bIDD\s*=\s*(IDD_[A-Z0-9_]+)", text)
        if not match:
            raise SystemExit(f"Preview2 Settings completeness: page ID unavailable in {filename}")
        result[key] = match.group(1)
    return result


def replace_function(text: str, signature: str, next_signature: str, body: str) -> str:
    start = text.find(signature)
    end = text.find(next_signature, start + len(signature))
    if start < 0 or end < 0:
        raise SystemExit(f"Preview2 Settings completeness: function boundary missing {signature}")
    return text[:start] + body.rstrip() + "\n\n" + text[end:]


def main() -> int:
    ids = page_ids()
    header, hn = load(H)
    cpp, cn = load(CPP)

    old_enum = '''    enum Category
    {
        CATEGORY_APPEARANCE = 0,
        CATEGORY_PEERS,
        CATEGORY_INTELLIGENCE,
        CATEGORY_ADVANCED,
        CATEGORY_COUNT
    };
'''
    enum_lines = [
        "    enum Category",
        "    {",
        "        CATEGORY_APPEARANCE = 0,",
        "        CATEGORY_PEERS,",
        "        CATEGORY_INTELLIGENCE,",
        "        CATEGORY_ADVANCED,",
    ]
    for key, _label, _filename in PAGES:
        enum_lines.append(f"        CATEGORY_ORIGINAL_{key},")
    enum_lines += ["        CATEGORY_COUNT", "    };", ""]
    new_enum = "\n".join(enum_lines)
    if "CATEGORY_ORIGINAL_GENERAL" not in header:
        if old_enum not in header:
            raise SystemExit("Preview2 Settings completeness: category enum anchor missing")
        header = header.replace(old_enum, new_enum, 1)

    if "OnOpenOriginalSettingsClicked" not in header:
        anchor = "    afx_msg void OnApplyClicked();\n"
        if anchor not in header:
            raise SystemExit("Preview2 Settings completeness: apply handler anchor missing")
        header = header.replace(anchor, anchor + "    afx_msg void OnOpenOriginalSettingsClicked();\n", 1)
    if "CButton m_openOriginalSettings;" not in header:
        anchor = "    CButton m_apply;\n"
        if anchor not in header:
            raise SystemExit("Preview2 Settings completeness: apply member anchor missing")
        header = header.replace(anchor, "    CStatic m_originalSettingsNote;\n    CButton m_openOriginalSettings;\n" + anchor, 1)

    if "IDC_EN_OPEN_ORIGINAL_SETTINGS" not in cpp:
        cpp = cpp.replace("        IDC_EN_CLASSIC_PREFS\n    };", "        IDC_EN_CLASSIC_PREFS,\n        IDC_EN_OPEN_ORIGINAL_SETTINGS\n    };", 1)
    if "ON_BN_CLICKED(IDC_EN_OPEN_ORIGINAL_SETTINGS, OnOpenOriginalSettingsClicked)" not in cpp:
        anchor = "    ON_BN_CLICKED(IDC_EN_APPLY, OnApplyClicked)\n"
        if anchor not in cpp:
            raise SystemExit("Preview2 Settings completeness: message map anchor missing")
        cpp = cpp.replace(anchor, anchor + "    ON_BN_CLICKED(IDC_EN_OPEN_ORIGINAL_SETTINGS, OnOpenOriginalSettingsClicked)\n", 1)

    if 'm_openOriginalSettings.Create(_T("Open settings page..."' not in cpp:
        anchor = '        || !m_classicPreferences.Create(_T("Classic eMule settings..."), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_CLASSIC_PREFS)\n'
        if anchor not in cpp:
            raise SystemExit("Preview2 Settings completeness: classic settings create anchor missing")
        addition = '        || !m_originalSettingsNote.Create(_T("This category uses the original eMule preference page so every existing option remains available."), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)\n        || !m_openOriginalSettings.Create(_T("Open settings page..."), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_OPEN_ORIGINAL_SETTINGS)\n'
        cpp = cpp.replace(anchor, addition + anchor, 1)

    nav_anchor = '    m_navigation.AddString(_T("Advanced"));\n'
    if 'm_navigation.AddString(_T("General"));' not in cpp:
        if nav_anchor not in cpp:
            raise SystemExit("Preview2 Settings completeness: navigation anchor missing")
        nav = "".join(f'    m_navigation.AddString(_T("{label}"));\n' for _key, label, _file in PAGES)
        cpp = cpp.replace(nav_anchor, nav_anchor + nav, 1)

    cpp = cpp.replace("&m_a4afThreshold, &m_advancedNote, &m_classicPreferences, &m_apply, &m_status",
                      "&m_a4afThreshold, &m_advancedNote, &m_originalSettingsNote, &m_openOriginalSettings, &m_classicPreferences, &m_apply, &m_status")

    show_category = r'''void CEmuleNextSettingsWnd::ShowCategory(Category category)
{
    CWnd* appearance[] = { &m_themeLabel, &m_theme, &m_etaHealth };
    CWnd* peers[] = { &m_peerDiscovery, &m_peerConcurrencyLabel, &m_peerConcurrency, &m_peerPrivacyNote };
    CWnd* intelligence[] = { &m_schedulerModeLabel, &m_schedulerMode, &m_schedulerProfileLabel, &m_schedulerProfile,
        &m_sourceDiscovery, &m_a4af, &m_rareParts, &m_schedulerSafety };
    CWnd* advanced[] = { &m_customTuning, &m_cooldownLabel, &m_cooldown, &m_batchLabel, &m_batch,
        &m_a4afThresholdLabel, &m_a4afThreshold, &m_advancedNote };

    const bool original = category >= CATEGORY_ORIGINAL_GENERAL;
    for (int i = 0; i < _countof(appearance); ++i) appearance[i]->ShowWindow(category == CATEGORY_APPEARANCE ? SW_SHOW : SW_HIDE);
    for (int i = 0; i < _countof(peers); ++i) peers[i]->ShowWindow(category == CATEGORY_PEERS ? SW_SHOW : SW_HIDE);
    for (int i = 0; i < _countof(intelligence); ++i) intelligence[i]->ShowWindow(category == CATEGORY_INTELLIGENCE ? SW_SHOW : SW_HIDE);
    for (int i = 0; i < _countof(advanced); ++i) advanced[i]->ShowWindow(category == CATEGORY_ADVANCED ? SW_SHOW : SW_HIDE);
    m_originalSettingsNote.ShowWindow(original ? SW_SHOW : SW_HIDE);
    m_openOriginalSettings.ShowWindow(original ? SW_SHOW : SW_HIDE);
    m_classicPreferences.ShowWindow(SW_HIDE);
    m_apply.ShowWindow(original ? SW_HIDE : SW_SHOW);
    m_status.ShowWindow(original ? SW_HIDE : SW_SHOW);

    CString title;
    CString description;
    switch (category) {
    case CATEGORY_APPEARANCE: title = _T("Appearance"); description = _T("Theme and presentation options. System mode follows Windows appearance."); break;
    case CATEGORY_PEERS: title = _T("Peer knowledge"); description = _T("Passive knowledge collection through existing eMule shared-file capabilities."); break;
    case CATEGORY_INTELLIGENCE: title = _T("Intelligence"); description = _T("Smart Scheduling behavior. Analysis only remains the safe default."); break;
    case CATEGORY_ADVANCED: title = _T("Advanced"); description = _T("Optional eMule Next expert overrides. Leave custom tuning off for bounded defaults."); break;
'''
    for key, label, _filename in PAGES:
        show_category += f'    case CATEGORY_ORIGINAL_{key}: title = _T("{label}"); description = _T("Original eMule {label} preferences. All existing options on this page remain authoritative."); break;\n'
    show_category += r'''    default: title = _T("Settings"); description = _T(""); break;
    }
    m_sectionTitle.SetWindowText(title);
    m_sectionDescription.SetWindowText(description);
    if (original) {
        CString button;
        button.Format(_T("Open %s settings..."), (LPCTSTR)title);
        m_openOriginalSettings.SetWindowText(button);
    }
    CRect rect;
    GetClientRect(&rect);
    LayoutControls(rect.Width(), rect.Height());
}'''
    cpp = replace_function(cpp, "void CEmuleNextSettingsWnd::ShowCategory(Category category)\n{", "void CEmuleNextSettingsWnd::UpdateEnabledState()", show_category)

    handler = r'''void CEmuleNextSettingsWnd::OnOpenOriginalSettingsClicked()
{
    if (theApp.emuledlg == NULL)
        return;
    switch (m_category) {
'''
    for key, _label, _filename in PAGES:
        handler += f'    case CATEGORY_ORIGINAL_{key}: theApp.emuledlg->ShowPreferences({ids[key]}); break;\n'
    handler += r'''    default: break;
    }
}'''
    if "void CEmuleNextSettingsWnd::OnOpenOriginalSettingsClicked()" not in cpp:
        anchor = "void CEmuleNextSettingsWnd::OnApplyClicked()"
        pos = cpp.find(anchor)
        if pos < 0:
            raise SystemExit("Preview2 Settings completeness: apply function boundary missing")
        cpp = cpp[:pos] + handler + "\n\n" + cpp[pos:]

    layout = r'''void CEmuleNextSettingsWnd::LayoutControls(int cx, int cy)
{
    const int margin = CEmuleNextModernUi::PageMargin(m_hWnd);
    const int navWidth = CEmuleNextModernUi::NavigationWidth(m_hWnd);
    const int gap = CEmuleNextModernUi::ControlGap(m_hWnd);
    const int sectionGap = CEmuleNextModernUi::SectionGap(m_hWnd);
    const int controlHeight = CEmuleNextModernUi::ControlHeight(m_hWnd);
    const int compactHeight = CEmuleNextModernUi::CompactHeight(m_hWnd);
    const int titleHeight = CEmuleNextModernUi::Scale(m_hWnd, 34);
    const int descriptionHeight = CEmuleNextModernUi::Scale(m_hWnd, 42);
    const int contentLeft = margin + navWidth + sectionGap;
    int contentWidth = cx - contentLeft - margin;
    const int minimumWidth = CEmuleNextModernUi::Scale(m_hWnd, 360);
    if (contentWidth < minimumWidth) contentWidth = minimumWidth;
    int fieldWidth = contentWidth - CEmuleNextModernUi::Scale(m_hWnd, 24);
    const int fieldMaximum = CEmuleNextModernUi::Scale(m_hWnd, 360);
    if (fieldWidth > fieldMaximum) fieldWidth = fieldMaximum;

    int navHeight = cy - margin * 2 - titleHeight - gap;
    const int navMinimum = CEmuleNextModernUi::Scale(m_hWnd, 220);
    if (navHeight < navMinimum) navHeight = navMinimum;
    m_navigation.MoveWindow(margin, margin + titleHeight + gap, navWidth, navHeight);
    m_title.MoveWindow(contentLeft, margin, contentWidth, titleHeight);
    m_subtitle.MoveWindow(contentLeft, margin + titleHeight, contentWidth, compactHeight);

    int y = margin + titleHeight + compactHeight + sectionGap;
    m_sectionTitle.MoveWindow(contentLeft + gap, y, contentWidth - gap * 2, compactHeight); y += compactHeight;
    m_sectionDescription.MoveWindow(contentLeft + gap, y, contentWidth - gap * 2, descriptionHeight); y += descriptionHeight + sectionGap;
    const int x = contentLeft + CEmuleNextModernUi::Scale(m_hWnd, 18);
    const int width = contentWidth - CEmuleNextModernUi::Scale(m_hWnd, 36);

    if (m_category == CATEGORY_APPEARANCE) {
        m_themeLabel.MoveWindow(x, y, width, compactHeight); y += compactHeight;
        m_theme.MoveWindow(x, y, fieldWidth, CEmuleNextModernUi::Scale(m_hWnd, 220)); y += controlHeight + sectionGap;
        m_etaHealth.MoveWindow(x, y, width, controlHeight);
    } else if (m_category == CATEGORY_PEERS) {
        m_peerDiscovery.MoveWindow(x, y, width, controlHeight); y += controlHeight + gap;
        m_peerConcurrencyLabel.MoveWindow(x, y, width, compactHeight); y += compactHeight;
        m_peerConcurrency.MoveWindow(x, y, fieldWidth, CEmuleNextModernUi::Scale(m_hWnd, 220)); y += controlHeight + sectionGap;
        m_peerPrivacyNote.MoveWindow(x, y, width, descriptionHeight);
    } else if (m_category == CATEGORY_INTELLIGENCE) {
        m_schedulerModeLabel.MoveWindow(x, y, width, compactHeight); y += compactHeight;
        m_schedulerMode.MoveWindow(x, y, fieldWidth, CEmuleNextModernUi::Scale(m_hWnd, 220)); y += controlHeight + gap;
        m_schedulerProfileLabel.MoveWindow(x, y, width, compactHeight); y += compactHeight;
        m_schedulerProfile.MoveWindow(x, y, fieldWidth, CEmuleNextModernUi::Scale(m_hWnd, 220)); y += controlHeight + sectionGap;
        m_sourceDiscovery.MoveWindow(x, y, width, controlHeight); y += controlHeight;
        m_a4af.MoveWindow(x, y, width, controlHeight); y += controlHeight;
        m_rareParts.MoveWindow(x, y, width, controlHeight); y += controlHeight + sectionGap;
        m_schedulerSafety.MoveWindow(x, y, width, descriptionHeight);
    } else if (m_category == CATEGORY_ADVANCED) {
        m_customTuning.MoveWindow(x, y, width, controlHeight); y += controlHeight + gap;
        m_cooldownLabel.MoveWindow(x, y, width, compactHeight); y += compactHeight;
        m_cooldown.MoveWindow(x, y, fieldWidth, CEmuleNextModernUi::Scale(m_hWnd, 220)); y += controlHeight + gap;
        m_batchLabel.MoveWindow(x, y, width, compactHeight); y += compactHeight;
        m_batch.MoveWindow(x, y, fieldWidth, CEmuleNextModernUi::Scale(m_hWnd, 220)); y += controlHeight + gap;
        m_a4afThresholdLabel.MoveWindow(x, y, width, compactHeight); y += compactHeight;
        m_a4afThreshold.MoveWindow(x, y, fieldWidth, CEmuleNextModernUi::Scale(m_hWnd, 220)); y += controlHeight + sectionGap;
        m_advancedNote.MoveWindow(x, y, width, descriptionHeight);
    } else {
        m_originalSettingsNote.MoveWindow(x, y, width, descriptionHeight); y += descriptionHeight + sectionGap;
        m_openOriginalSettings.MoveWindow(x, y, CEmuleNextModernUi::Scale(m_hWnd, 220), controlHeight);
    }

    if (m_category < CATEGORY_ORIGINAL_GENERAL) {
        const int actionWidth = CEmuleNextModernUi::Scale(m_hWnd, 150);
        int actionY = cy - margin - controlHeight;
        if (actionY < y + sectionGap) actionY = y + sectionGap;
        m_apply.MoveWindow(contentLeft + contentWidth - actionWidth, actionY, actionWidth, controlHeight);
        int statusWidth = contentWidth - actionWidth - gap * 3;
        if (statusWidth < 0) statusWidth = 0;
        m_status.MoveWindow(contentLeft + gap, actionY, statusWidth, controlHeight);
    }
}'''
    cpp = replace_function(cpp, "void CEmuleNextSettingsWnd::LayoutControls(int cx, int cy)\n{", "void CEmuleNextSettingsWnd::OnPaint()", layout)

    # Original-page helper text should use muted palette as well.
    if "wnd->m_hWnd == m_originalSettingsNote.m_hWnd" not in cpp:
        cpp = cpp.replace("wnd->m_hWnd == m_sectionDescription.m_hWnd || wnd->m_hWnd == m_peerPrivacyNote.m_hWnd",
                          "wnd->m_hWnd == m_sectionDescription.m_hWnd || wnd->m_hWnd == m_originalSettingsNote.m_hWnd || wnd->m_hWnd == m_peerPrivacyNote.m_hWnd", 1)

    final = header + "\n" + cpp
    for _key, label, _filename in PAGES:
        if f'm_navigation.AddString(_T("{label}"));' not in final:
            raise SystemExit(f"Preview2 Settings completeness: navigation missing {label}")
    for key, ident in ids.items():
        if f"ShowPreferences({ident})" not in final:
            raise SystemExit(f"Preview2 Settings completeness: direct page route missing {key}")

    save(H, header, hn)
    save(CPP, cpp, cn)
    print("eMule Next Preview 2 complete Settings navigation materialized (4 Next + 15 original pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
