//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "KnownUsersService.h"
#include "PeerShareScanner.h"

#include <vector>

// Reserved outside normal restored search IDs (0...) and live server-search IDs
// (0x80000000...). This tab is a permanent eMule Next view, not a network search.
static const uint32 EMULENEXT_KNOWN_USERS_VIEW_ID = 0x7FFFFF01u;

enum EmuleNextKnownUsersMode
{
    ENKUM_CURRENT = 0,
    ENKUM_HISTORY,
    ENKUM_FAVORITES,
    ENKUM_RECENT,
    ENKUM_COUNT
};

class CKnownUsersWnd : public CWnd
{
public:
    CKnownUsersWnd();
    virtual ~CKnownUsersWnd();

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
    afx_msg void OnUserSelectionChanged(NMHDR* header, LRESULT* result);
    afx_msg void OnUserColumnClick(NMHDR* header, LRESULT* result);
    afx_msg void OnModeChanged(NMHDR* header, LRESULT* result);
    afx_msg void OnSearchChanged();
    afx_msg void OnRefreshClicked();
    afx_msg void OnRefreshPeerClicked();
    afx_msg void OnFavoriteClicked();
    afx_msg void OnAliasClicked();
    afx_msg void OnDeleteHistoryClicked();
    afx_msg void OnDarkModeClicked();
    afx_msg LRESULT OnUsersLoaded(WPARAM, LPARAM value);
    afx_msg LRESULT OnFilesLoaded(WPARAM, LPARAM value);
    afx_msg LRESULT OnHistoryDeleted(WPARAM, LPARAM value);

private:
    void LayoutControls(int cx, int cy);
    void RefreshUsers();
    void RefreshFiles();
    void PopulateUsers();
    void PopulateFiles();
    void UpdateSelectedStatus();
    void UpdateActionButtons();
    void LoadViewState();
    void SaveViewState() const;
    void ApplyUserColumnWidths();
    void SortUserRows();
    int SelectedUserIndex() const;
    bool SelectedHash(EmuleNextHash16& hash) const;
    bool IsCurrent(const EmuleNextKnownUserRecord& user) const;
    bool MatchesMode(const EmuleNextKnownUserRecord& user) const;
    bool MatchesSearch(const EmuleNextKnownUserRecord& user) const;
    bool GetShareState(const EmuleNextHash16& hash, EmuleNextPeerShareState& state) const;
    CString BrowseStatusText(const EmuleNextHash16& hash) const;
    CString FileStateText(const EmuleNextKnownFileRecord& file) const;
    CString EndpointText(const EmuleNextKnownUserRecord& user) const;
    CString ClientText(const EmuleNextKnownUserRecord& user) const;
    static CString HashText(const EmuleNextHash16& hash);
    static CString DateText(uint64 timestamp);
    static CString RemainingText(uint64 target);
    static CString DisplayName(const EmuleNextKnownUserRecord& user);
    static bool SameHash(const EmuleNextHash16& left, const EmuleNextHash16& right);

    CTabCtrl m_modes;
    CEdit m_search;
    CButton m_refreshButton;
    CButton m_refreshPeerButton;
    CButton m_favoriteButton;
    CButton m_aliasButton;
    CButton m_deleteHistoryButton;
    CButton m_darkModeButton;
    CStatic m_status;
    CListCtrl m_users;
    CListCtrl m_files;
    CBrush m_darkBrush;
    std::vector<EmuleNextKnownUserRecord> m_userRows;
    std::vector<EmuleNextKnownFileRecord> m_fileRows;
    EmuleNextHash16 m_fileRowsPeer;
    EmuleNextKnownUsersMode m_mode;
    int m_sortColumn;
    bool m_sortAscending;
    bool m_usersLoading;
    bool m_filesLoading;
    bool m_deleteLoading;
    UINT_PTR m_refreshTimer;
};
