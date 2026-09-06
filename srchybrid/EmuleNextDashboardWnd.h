//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include <array>

#define EMULENEXT_DASHBOARD_INTELLIGENCE2 1

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
        DASH_ACTIVE,
        DASH_LOW_HEALTH,
        DASH_INTERVENTION,
        DASH_A4AF_OPPORTUNITY,
        DASH_FILTER_COUNT
    };

    CStatic m_summary;
    CButton m_filterAll;
    CButton m_filterAttention;
    CButton m_filterStalled;
    CButton m_filterRare;
    CButton m_filterNoSources;
    CButton m_filterActive;
    CButton m_filterLowHealth;
    CButton m_filterIntervention;
    CButton m_filterA4AF;
    CListCtrl m_downloads;
    CButton m_openTransfers;
    CButton m_openSources;
    CButton m_pauseResume;
    CButton m_priorityHigh;
    CButton m_priorityNormal;
    CButton m_forceAnalysis;
    CButton m_resetIntelligence;
    CButton m_refreshNow;
    CStatic m_details;
    CBrush m_darkBrush;
    UINT_PTR m_refreshTimer;
    DashboardFilter m_filter;
    int m_sortColumn;
    bool m_sortAscending;
    DWORD m_lastAutoRefreshTick;
    DWORD m_lastRefreshDurationMs;
    bool m_persistedLoading;
    bool m_persistedHashValid;
    std::array<unsigned char, 16> m_persistedHash;
    CString m_persistedSummary;

    void SetFilter(DashboardFilter filter);
    void UpdateFilterButtons();
    void UpdateDetails();
    void UpdateActionButtons();
    void LoadViewState();
    void SaveViewState();
    void RequestPersistentDetails();
    CPartFile* GetSelectedFile() const;
    void JumpToTransfers(bool expandSources);

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
    afx_msg void OnFilterLowHealth();
    afx_msg void OnFilterIntervention();
    afx_msg void OnFilterA4AF();
    afx_msg void OnOpenTransfers();
    afx_msg void OnOpenSources();
    afx_msg void OnPauseResume();
    afx_msg void OnPriorityHigh();
    afx_msg void OnPriorityNormal();
    afx_msg void OnForceAnalysis();
    afx_msg void OnResetIntelligence();
    afx_msg void OnRefreshNow();
    afx_msg void OnDownloadSelectionChanged(NMHDR* header, LRESULT* result);
    afx_msg void OnDownloadDoubleClick(NMHDR* header, LRESULT* result);
    afx_msg void OnDownloadColumnClick(NMHDR* header, LRESULT* result);
    afx_msg LRESULT OnPersistentDetailsLoaded(WPARAM, LPARAM value);

    DECLARE_MESSAGE_MAP()
};
