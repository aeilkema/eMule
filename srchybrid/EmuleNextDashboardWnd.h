//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

class CEmuleNextDashboardWnd : public CWnd
{
public:
    CEmuleNextDashboardWnd();
    virtual ~CEmuleNextDashboardWnd();

    bool Create(CWnd* parent);
    void Refresh();

protected:
    CStatic m_summary;
    CListCtrl m_downloads;
    CBrush m_darkBrush;
    UINT_PTR m_refreshTimer;

    void LayoutControls(int cx, int cy);
    void PopulateDownloads();

    virtual BOOL PreTranslateMessage(MSG* message);

    afx_msg int OnCreate(LPCREATESTRUCT createStruct);
    afx_msg void OnSize(UINT type, int cx, int cy);
    afx_msg void OnTimer(UINT_PTR timerId);
    afx_msg BOOL OnEraseBkgnd(CDC* dc);
    afx_msg HBRUSH OnCtlColor(CDC* dc, CWnd* wnd, UINT ctlColor);

    DECLARE_MESSAGE_MAP()
};
