//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "Search2Service.h"
#include <vector>

static const uint32 EMULENEXT_SEARCH2_VIEW_ID = 0x7FFFFF02u;

class CSearch2Wnd : public CWnd
{
public:
    CSearch2Wnd();
    virtual ~CSearch2Wnd();

    bool Create(CWnd* parent);
    void Refresh(bool force = false);

protected:
    DECLARE_MESSAGE_MAP()
    afx_msg int OnCreate(LPCREATESTRUCT createStruct);
    afx_msg void OnSize(UINT type, int cx, int cy);
    afx_msg BOOL OnEraseBkgnd(CDC* dc);
    afx_msg HBRUSH OnCtlColor(CDC* dc, CWnd* wnd, UINT ctlColor);
    afx_msg void OnSearchClicked();
    afx_msg void OnFavoriteClicked();
    afx_msg void OnDownloadLaterClicked();
    afx_msg void OnBlockClicked();
    afx_msg void OnResultSelectionChanged(NMHDR* header, LRESULT* result);
    afx_msg LRESULT OnSearchLoaded(WPARAM, LPARAM value);

private:
    void LayoutControls(int cx, int cy);
    void StartSearch();
    void PopulateResults();
    int SelectedIndex() const;
    void UpdateActionButtons();
    static CString HashText(const EmuleNextHash16& hash);
    static CString DateText(uint64 timestamp);

    CEdit m_query;
    CButton m_search;
    CButton m_hideDownloaded;
    CButton m_favoritesOnly;
    CStatic m_status;
    CListCtrl m_results;
    CButton m_favorite;
    CButton m_downloadLater;
    CButton m_block;
    CBrush m_darkBrush;
    std::vector<EmuleNextSearchFileResult> m_rows;
    bool m_loading;
};
