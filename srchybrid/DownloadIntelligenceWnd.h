//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "DownloadIntelligenceService.h"

#include <vector>

static const uint32 EMULENEXT_DOWNLOAD_INTELLIGENCE_VIEW_ID = 0x7FFFFF05u;

class CDownloadIntelligenceWnd : public CWnd
{
public:
    CDownloadIntelligenceWnd();
    virtual ~CDownloadIntelligenceWnd();

    bool Create(CWnd* parent);
    void Refresh(bool force = false);

protected:
    DECLARE_MESSAGE_MAP()
    afx_msg int OnCreate(LPCREATESTRUCT createStruct);
    afx_msg void OnSize(UINT type, int cx, int cy);
    afx_msg void OnDestroy();
    afx_msg void OnTimer(UINT_PTR timerId);
    afx_msg BOOL OnEraseBkgnd(CDC* dc);
    afx_msg HBRUSH OnCtlColor(CDC* dc, CWnd* wnd, UINT ctlColor);
    afx_msg void OnRefreshClicked();
    afx_msg LRESULT OnTransfersLoaded(WPARAM, LPARAM value);

private:
    void LayoutControls(int cx, int cy);
    void Populate();
    void UpdateSummary();
    static CString DateText(uint64 timestamp);

    CButton m_refreshButton;
    CStatic m_summary;
    CListCtrl m_transfers;
    CBrush m_darkBrush;
    std::vector<EmuleNextTransferHistoryRecord> m_rows;
    bool m_loading;
    UINT_PTR m_refreshTimer;
};
