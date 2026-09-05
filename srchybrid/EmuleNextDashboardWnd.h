//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

class CPartFile;

class CEmuleNextDashboardWnd : public CWnd
{
public:
    CEmuleNextDashboardWnd();
    virtual ~CEmuleNextDashboardWnd();

    bool Create(CWnd* parent);
    void Refresh();

protected:
    enum DashboardFilter
    {
        DASH_ALL = 0,
        DASH_ATTENTION,
        DASH_STALLED,
        DASH_RARE,
        DASH_NO_SOURCES,
        DASH_ACTIVE
    };

    CStatic m_summary;
    CButton m_filterAll;
    CButton m_filterAttention;
    CButton m_filterStalled;
    CButton m_filterRare;
    CButton m_filterNoSources;
    CButton m_filterActive;
    CListCtrl m_downloads;
    CStatic m_details;
    CBrush m_darkBrush;
    UINT_PTR m_refreshTimer;
    DashboardFilter m_filter;

    void UpdateFilterButtons();
    void UpdateDetails();
    CPartFile* GetSelectedFile() const;

    virtual BOOL PreTranslateMessage(MSG* message);

    afx_msg int OnCreate(LPCREATESTRUCT createStruct);
    afx_msg void OnDestroy();
    afx_msg void OnSize(UINT type, int cx, int cy);
    afx_msg void OnTimer(UINT_PTR timerId);
    afx_msg BOOL OnEraseBkgnd(CDC* dc);
    afx_msg HBRUSH OnCtlColor(CDC* dc, CWnd* wnd, UINT ctlColor);
    afx_msg void OnFilterAll();
    afx_msg void OnFilterAttention();
    afx_msg void OnFilterStalled();
    afx_msg void OnFilterRare();
    afx_msg void OnFilterNoSources();
    afx_msg void OnFilterActive();
    afx_msg void OnDownloadSelectionChanged(NMHDR* header, LRESULT* result);
    afx_msg void OnDownloadDoubleClick(NMHDR* header, LRESULT* result);

    DECLARE_MESSAGE_MAP()
};
