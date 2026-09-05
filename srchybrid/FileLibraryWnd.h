//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "LibraryBrowserService.h"
#include <vector>

static const uint32 EMULENEXT_LIBRARY_VIEW_ID = 0x7FFFFF03u;

class CFileLibraryWnd : public CWnd
{
public:
    CFileLibraryWnd();
    virtual ~CFileLibraryWnd();

    bool Create(CWnd* parent);
    void Refresh(bool force = false);

protected:
    DECLARE_MESSAGE_MAP()
    afx_msg int OnCreate(LPCREATESTRUCT createStruct);
    afx_msg void OnSize(UINT type, int cx, int cy);
    afx_msg BOOL OnEraseBkgnd(CDC* dc);
    afx_msg HBRUSH OnCtlColor(CDC* dc, CWnd* wnd, UINT ctlColor);
    afx_msg void OnRefreshClicked();
    afx_msg void OnFilterChanged();
    afx_msg void OnFavoriteClicked();
    afx_msg void OnDownloadLaterClicked();
    afx_msg void OnOpenLocationClicked();
    afx_msg void OnSelectionChanged(NMHDR* header, LRESULT* result);
    afx_msg LRESULT OnLibraryLoaded(WPARAM, LPARAM value);

private:
    void LayoutControls(int cx, int cy);
    void StartLoad();
    void PopulateRows();
    int SelectedIndex() const;
    void UpdateActions();
    static CString HashText(const EmuleNextHash16& hash);
    static CString DateText(uint64 timestamp);

    CComboBox m_filter;
    CButton m_refresh;
    CStatic m_status;
    CListCtrl m_results;
    CButton m_favorite;
    CButton m_downloadLater;
    CButton m_openLocation;
    CBrush m_darkBrush;
    std::vector<EmuleNextLibraryBrowseRow> m_rows;
    bool m_loading;
};
