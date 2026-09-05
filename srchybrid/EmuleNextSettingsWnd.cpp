//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later

#include "stdafx.h"
#include "EmuleNextSettingsWnd.h"
#include "EmuleNextTheme.h"
#include "EmuleNextVersion.h"
#include "ClientList.h"
#include "emule.h"
#include "emuledlg.h"

namespace
{
    enum
    {
        IDC_EN_THEME = 0x7E40,
        IDC_EN_DISCOVERY,
        IDC_EN_CONCURRENCY,
        IDC_EN_APPLY
    };
}

BEGIN_MESSAGE_MAP(CEmuleNextSettingsWnd, CWnd)
    ON_WM_CREATE()
    ON_WM_SIZE()
    ON_WM_ERASEBKGND()
    ON_WM_CTLCOLOR()
    ON_BN_CLICKED(IDC_EN_APPLY, OnApplyClicked)
END_MESSAGE_MAP()

CEmuleNextSettingsWnd::CEmuleNextSettingsWnd()
{
}

CEmuleNextSettingsWnd::~CEmuleNextSettingsWnd()
{
}

bool CEmuleNextSettingsWnd::Create(CWnd* parent)
{
    if (parent == NULL)
        return false;
    const CString className = AfxRegisterWndClass(CS_DBLCLKS, ::LoadCursor(NULL, IDC_ARROW),
        reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1), NULL);
    CRect empty(0, 0, 0, 0);
    return CWnd::CreateEx(0, className, _T("eMule Next Settings"),
        WS_CHILD | WS_CLIPCHILDREN | WS_CLIPSIBLINGS, empty, parent, 0) != FALSE;
}

int CEmuleNextSettingsWnd::OnCreate(LPCREATESTRUCT createStruct)
{
    if (CWnd::OnCreate(createStruct) == -1)
        return -1;

    m_darkBrush.CreateSolidBrush(CEmuleNextTheme::BackgroundColor());
    CRect empty(0, 0, 0, 0);
    if (!m_heading.Create(EMULENEXT_PRODUCT_WITH_CORE_TEXT, WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_themeLabel.Create(_T("Appearance"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_themeMode.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST,
            empty, this, IDC_EN_THEME)
        || !m_discoveryLabel.Create(_T("Peer knowledge"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_discoveryEnabled.Create(_T("Automatically inspect shared files exposed by connected peers"),
            WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX, empty, this, IDC_EN_DISCOVERY)
        || !m_concurrencyLabel.Create(_T("Maximum concurrent shared-file requests"),
            WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_maxConcurrent.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST,
            empty, this, IDC_EN_CONCURRENCY)
        || !m_apply.Create(_T("Apply"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_APPLY)
        || !m_status.Create(_T("Changes are stored in the eMule profile."),
            WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)) {
        return -1;
    }

    CFont* font = CFont::FromHandle(static_cast<HFONT>(::GetStockObject(DEFAULT_GUI_FONT)));
    m_heading.SetFont(font);
    m_themeLabel.SetFont(font);
    m_themeMode.SetFont(font);
    m_discoveryLabel.SetFont(font);
    m_discoveryEnabled.SetFont(font);
    m_concurrencyLabel.SetFont(font);
    m_maxConcurrent.SetFont(font);
    m_apply.SetFont(font);
    m_status.SetFont(font);

    m_themeMode.AddString(_T("System"));
    m_themeMode.AddString(_T("Light"));
    m_themeMode.AddString(_T("Dark"));
    for (int i = 1; i <= 8; ++i) {
        CString value;
        value.Format(_T("%d"), i);
        m_maxConcurrent.AddString(value);
    }

    Refresh();
    CEmuleNextTheme::ApplyToWindow(m_hWnd);
    return 0;
}

void CEmuleNextSettingsWnd::Refresh()
{
    if (!::IsWindow(m_hWnd))
        return;

    m_themeMode.SetCurSel(static_cast<int>(CEmuleNextTheme::GetMode()));
    const bool discovery = theApp.GetProfileInt(_T("eMule Next"), _T("PeerShareDiscovery"), 1) != 0;
    int concurrent = theApp.GetProfileInt(_T("eMule Next"), _T("PeerShareMaxConcurrent"), 2);
    if (concurrent < 1)
        concurrent = 1;
    else if (concurrent > 8)
        concurrent = 8;
    m_discoveryEnabled.SetCheck(discovery ? BST_CHECKED : BST_UNCHECKED);
    m_maxConcurrent.SetCurSel(concurrent - 1);
}

void CEmuleNextSettingsWnd::OnSize(UINT type, int cx, int cy)
{
    CWnd::OnSize(type, cx, cy);
    if (::IsWindow(m_heading.m_hWnd))
        LayoutControls(cx, cy);
}

void CEmuleNextSettingsWnd::LayoutControls(int cx, int /*cy*/)
{
    const int margin = 22;
    const int labelWidth = 260;
    const int fieldLeft = margin + labelWidth + 18;
    const int fieldWidth = min(260, max(160, cx - fieldLeft - margin));
    int y = 22;

    m_heading.MoveWindow(margin, y, max(200, cx - margin * 2), 24);
    y += 44;
    m_themeLabel.MoveWindow(margin, y + 4, labelWidth, 20);
    m_themeMode.MoveWindow(fieldLeft, y, fieldWidth, 240);
    y += 48;
    m_discoveryLabel.MoveWindow(margin, y + 3, labelWidth, 20);
    m_discoveryEnabled.MoveWindow(fieldLeft, y, max(300, cx - fieldLeft - margin), 24);
    y += 42;
    m_concurrencyLabel.MoveWindow(margin, y + 4, labelWidth, 20);
    m_maxConcurrent.MoveWindow(fieldLeft, y, 90, 220);
    y += 55;
    m_apply.MoveWindow(fieldLeft, y, 100, 28);
    m_status.MoveWindow(fieldLeft + 118, y + 5, max(100, cx - fieldLeft - 118 - margin), 20);
}

BOOL CEmuleNextSettingsWnd::OnEraseBkgnd(CDC* dc)
{
    if (!CEmuleNextTheme::IsDarkMode())
        return CWnd::OnEraseBkgnd(dc);
    CRect rect;
    GetClientRect(&rect);
    dc->FillSolidRect(rect, CEmuleNextTheme::BackgroundColor());
    return TRUE;
}

HBRUSH CEmuleNextSettingsWnd::OnCtlColor(CDC* dc, CWnd* wnd, UINT ctlColor)
{
    if (!CEmuleNextTheme::IsDarkMode())
        return CWnd::OnCtlColor(dc, wnd, ctlColor);
    dc->SetTextColor(CEmuleNextTheme::TextColor());
    dc->SetBkColor(CEmuleNextTheme::BackgroundColor());
    if (ctlColor == CTLCOLOR_STATIC || ctlColor == CTLCOLOR_DLG)
        return static_cast<HBRUSH>(m_darkBrush.GetSafeHandle());
    return CWnd::OnCtlColor(dc, wnd, ctlColor);
}

void CEmuleNextSettingsWnd::OnApplyClicked()
{
    int theme = m_themeMode.GetCurSel();
    if (theme < ENTM_SYSTEM || theme > ENTM_DARK)
        theme = ENTM_SYSTEM;
    CEmuleNextTheme::SetMode(static_cast<EmuleNextThemeMode>(theme));

    const bool discovery = m_discoveryEnabled.GetCheck() == BST_CHECKED;
    int concurrent = m_maxConcurrent.GetCurSel() + 1;
    if (concurrent < 1)
        concurrent = 1;
    else if (concurrent > 8)
        concurrent = 8;
    theApp.WriteProfileInt(_T("eMule Next"), _T("PeerShareDiscovery"), discovery ? 1 : 0);
    theApp.WriteProfileInt(_T("eMule Next"), _T("PeerShareMaxConcurrent"), concurrent);
    if (theApp.clientlist != NULL) {
        theApp.clientlist->SetPeerShareDiscoveryEnabled(discovery);
        theApp.clientlist->SetPeerShareMaxConcurrent(static_cast<uint32>(concurrent));
    }

    if (theApp.emuledlg != NULL)
        CEmuleNextTheme::ApplyToWindow(theApp.emuledlg->GetSafeHwnd());
    else
        CEmuleNextTheme::ApplyToWindow(m_hWnd);
    m_status.SetWindowText(_T("Settings applied."));
    Invalidate(TRUE);
}