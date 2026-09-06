//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later

#include "stdafx.h"
#include "KnownUsersWnd.h"

#include "ClientList.h"
#include "EmuleNextRuntime.h"
#include "EmuleNextTheme.h"
#include "EmuleNextUiMetrics.h"
#include "InputBox.h"
#include "OtherFunctions.h"
#include "emule.h"
#include "emuledlg.h"

#include <algorithm>
#include <memory>

namespace
{
    enum
    {
        IDC_EN_MODES = 0x7E10,
        IDC_EN_SEARCH,
        IDC_EN_REFRESH,
        IDC_EN_REFRESH_PEER,
        IDC_EN_FAVORITE,
        IDC_EN_ALIAS,
        IDC_EN_DELETE_HISTORY,
        IDC_EN_DARKMODE,
        IDC_EN_STATUS,
        IDC_EN_USERS,
        IDC_EN_FILES
    };

    const UINT WM_EN_USERS_LOADED = WM_APP + 0x561;
    const UINT WM_EN_FILES_LOADED = WM_APP + 0x562;
    const UINT WM_EN_HISTORY_DELETED = WM_APP + 0x563;
    const UINT_PTR TIMER_EN_REFRESH = 0x561;
    const LPCTSTR PROFILE_SECTION = _T("eMule Next Known Users");
    const int USER_COLUMN_COUNT = 12;

    struct UsersLoadContext
    {
        HWND target;
        CStringW databasePath;
        EmuleNextKnownUsersQuery query;
    };

    struct UsersLoadResult
    {
        bool ok;
        std::vector<EmuleNextKnownUserRecord> rows;
        UsersLoadResult() : ok(false) {}
    };

    struct FilesLoadContext
    {
        HWND target;
        CStringW databasePath;
        EmuleNextHash16 peerHash;
    };

    struct FilesLoadResult
    {
        bool ok;
        EmuleNextHash16 peerHash;
        std::vector<EmuleNextKnownFileRecord> rows;
        FilesLoadResult() : ok(false) {}
    };

    struct DeleteLoadContext
    {
        HWND target;
        CStringW databasePath;
        EmuleNextHash16 peerHash;
    };

    struct DeleteLoadResult
    {
        bool ok;
        EmuleNextHash16 peerHash;
        DeleteLoadResult() : ok(false) {}
    };

    UINT AFX_CDECL LoadUsersWorker(LPVOID value)
    {
        std::unique_ptr<UsersLoadContext> context(static_cast<UsersLoadContext*>(value));
        std::unique_ptr<UsersLoadResult> result(new UsersLoadResult);
        CKnownUsersService service(context->databasePath);
        result->ok = service.ListUsers(context->query, result->rows);
        if (::IsWindow(context->target)
            && ::PostMessage(context->target, WM_EN_USERS_LOADED, 0, reinterpret_cast<LPARAM>(result.get())))
            result.release();
        return 0;
    }

    UINT AFX_CDECL LoadFilesWorker(LPVOID value)
    {
        std::unique_ptr<FilesLoadContext> context(static_cast<FilesLoadContext*>(value));
        std::unique_ptr<FilesLoadResult> result(new FilesLoadResult);
        result->peerHash = context->peerHash;
        CKnownUsersService service(context->databasePath);
        result->ok = service.ListFiles(context->peerHash, result->rows);
        if (::IsWindow(context->target)
            && ::PostMessage(context->target, WM_EN_FILES_LOADED, 0, reinterpret_cast<LPARAM>(result.get())))
            result.release();
        return 0;
    }

    UINT AFX_CDECL DeleteHistoryWorker(LPVOID value)
    {
        std::unique_ptr<DeleteLoadContext> context(static_cast<DeleteLoadContext*>(value));
        std::unique_ptr<DeleteLoadResult> result(new DeleteLoadResult);
        result->peerHash = context->peerHash;
        CKnownUsersService service(context->databasePath);
        result->ok = service.DeletePeerHistory(context->peerHash);
        if (::IsWindow(context->target)
            && ::PostMessage(context->target, WM_EN_HISTORY_DELETED, 0, reinterpret_cast<LPARAM>(result.get())))
            result.release();
        return 0;
    }

    int CompareUInt64(uint64 left, uint64 right)
    {
        return left < right ? -1 : (left > right ? 1 : 0);
    }
}

BEGIN_MESSAGE_MAP(CKnownUsersWnd, CWnd)
    ON_WM_CREATE()
    ON_WM_SIZE()
    ON_WM_DESTROY()
    ON_WM_TIMER()
    ON_WM_ERASEBKGND()
    ON_WM_CTLCOLOR()
    ON_NOTIFY(LVN_ITEMCHANGED, IDC_EN_USERS, OnUserSelectionChanged)
    ON_NOTIFY(LVN_COLUMNCLICK, IDC_EN_USERS, OnUserColumnClick)
    ON_NOTIFY(TCN_SELCHANGE, IDC_EN_MODES, OnModeChanged)
    ON_EN_CHANGE(IDC_EN_SEARCH, OnSearchChanged)
    ON_BN_CLICKED(IDC_EN_REFRESH, OnRefreshClicked)
    ON_BN_CLICKED(IDC_EN_REFRESH_PEER, OnRefreshPeerClicked)
    ON_BN_CLICKED(IDC_EN_FAVORITE, OnFavoriteClicked)
    ON_BN_CLICKED(IDC_EN_ALIAS, OnAliasClicked)
    ON_BN_CLICKED(IDC_EN_DELETE_HISTORY, OnDeleteHistoryClicked)
    ON_BN_CLICKED(IDC_EN_DARKMODE, OnDarkModeClicked)
    ON_MESSAGE(WM_EN_USERS_LOADED, OnUsersLoaded)
    ON_MESSAGE(WM_EN_FILES_LOADED, OnFilesLoaded)
    ON_MESSAGE(WM_EN_HISTORY_DELETED, OnHistoryDeleted)
END_MESSAGE_MAP()

CKnownUsersWnd::CKnownUsersWnd()
    : m_mode(ENKUM_CURRENT)
    , m_sortColumn(7)
    , m_sortAscending(false)
    , m_usersLoading(false)
    , m_filesLoading(false)
    , m_deleteLoading(false)
    , m_refreshTimer(0)
{
}

CKnownUsersWnd::~CKnownUsersWnd()
{
}

bool CKnownUsersWnd::Create(CWnd* parent)
{
    if (parent == NULL)
        return false;
    const CString className = AfxRegisterWndClass(CS_DBLCLKS,
        ::LoadCursor(NULL, IDC_ARROW), reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1), NULL);
    CRect empty(0, 0, 0, 0);
    return CWnd::CreateEx(0, className, _T("eMule Next Known Users 2.0"),
        WS_CHILD | WS_CLIPCHILDREN | WS_CLIPSIBLINGS, empty, parent, 0) != FALSE;
}

int CKnownUsersWnd::OnCreate(LPCREATESTRUCT createStruct)
{
    if (CWnd::OnCreate(createStruct) == -1)
        return -1;

    m_darkBrush.CreateSolidBrush(CEmuleNextTheme::BackgroundColor());
    CRect empty(0, 0, 0, 0);
    if (!m_modes.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | TCS_TABS, empty, this, IDC_EN_MODES)
        || !m_search.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | WS_BORDER | ES_AUTOHSCROLL,
            empty, this, IDC_EN_SEARCH)
        || !m_refreshButton.Create(_T("Refresh all"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_REFRESH)
        || !m_refreshPeerButton.Create(_T("Refresh peer"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_REFRESH_PEER)
        || !m_favoriteButton.Create(_T("Favorite"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_FAVORITE)
        || !m_aliasButton.Create(_T("Alias..."), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_ALIAS)
        || !m_deleteHistoryButton.Create(_T("Delete history"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_DELETE_HISTORY)
        || !m_darkModeButton.Create(_T("Dark mode"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX,
            empty, this, IDC_EN_DARKMODE)
        || !m_status.Create(_T("Known Users 2.0 is loading..."), WS_CHILD | WS_VISIBLE | SS_LEFT,
            empty, this, IDC_EN_STATUS)
        || !m_users.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS,
            empty, this, IDC_EN_USERS)
        || !m_files.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS,
            empty, this, IDC_EN_FILES))
        return -1;

    CFont* font = CFont::FromHandle(static_cast<HFONT>(::GetStockObject(DEFAULT_GUI_FONT)));
    m_modes.SetFont(font);
    m_search.SetFont(font);
    m_refreshButton.SetFont(font);
    m_refreshPeerButton.SetFont(font);
    m_favoriteButton.SetFont(font);
    m_aliasButton.SetFont(font);
    m_deleteHistoryButton.SetFont(font);
    m_darkModeButton.SetFont(font);
    m_status.SetFont(font);
    m_users.SetFont(font);
    m_files.SetFont(font);

    m_modes.InsertItem(ENKUM_CURRENT, _T("Current"));
    m_modes.InsertItem(ENKUM_HISTORY, _T("History"));
    m_modes.InsertItem(ENKUM_FAVORITES, _T("Favorites"));
    m_modes.InsertItem(ENKUM_RECENT, _T("Recent 7d"));

    m_users.SetExtendedStyle(LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_GRIDLINES);
    m_files.SetExtendedStyle(LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_GRIDLINES);

    const int s = CEmuleNextUiMetrics::Scale(m_hWnd, 1);
    (void)s;
    m_users.InsertColumn(0, _T("User"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 170));
    m_users.InsertColumn(1, _T("Alias"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 130));
    m_users.InsertColumn(2, _T("Session"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 72));
    m_users.InsertColumn(3, _T("Client"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 125));
    m_users.InsertColumn(4, _T("Endpoint"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 145));
    m_users.InsertColumn(5, _T("Browse status"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 155));
    m_users.InsertColumn(6, _T("First seen"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 130));
    m_users.InsertColumn(7, _T("Last seen"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 130));
    m_users.InsertColumn(8, _T("Files"), LVCFMT_RIGHT, CEmuleNextUiMetrics::Scale(m_hWnd, 62));
    m_users.InsertColumn(9, _T("Shared size"), LVCFMT_RIGHT, CEmuleNextUiMetrics::Scale(m_hWnd, 95));
    m_users.InsertColumn(10, _T("Favorite"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 68));
    m_users.InsertColumn(11, _T("User hash"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 235));

    m_files.InsertColumn(0, _T("File"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 300));
    m_files.InsertColumn(1, _T("State"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 75));
    m_files.InsertColumn(2, _T("Size"), LVCFMT_RIGHT, CEmuleNextUiMetrics::Scale(m_hWnd, 95));
    m_files.InsertColumn(3, _T("First seen"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 130));
    m_files.InsertColumn(4, _T("Last seen"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 130));
    m_files.InsertColumn(5, _T("ED2K hash"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 235));
    m_files.InsertColumn(6, _T("AICH"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 245));

    LoadViewState();
    ApplyUserColumnWidths();
    m_modes.SetCurSel(static_cast<int>(m_mode));
    m_darkModeButton.SetCheck(CEmuleNextTheme::IsDarkMode() ? BST_CHECKED : BST_UNCHECKED);
    CEmuleNextTheme::ApplyToWindow(m_hWnd);

    m_refreshTimer = SetTimer(TIMER_EN_REFRESH, 5000, NULL);
    UpdateActionButtons();
    Refresh(true);
    return 0;
}

void CKnownUsersWnd::OnDestroy()
{
    SaveViewState();
    if (m_refreshTimer != 0) {
        KillTimer(m_refreshTimer);
        m_refreshTimer = 0;
    }
    CWnd::OnDestroy();
}

void CKnownUsersWnd::OnSize(UINT type, int cx, int cy)
{
    CWnd::OnSize(type, cx, cy);
    if (::IsWindow(m_users.m_hWnd))
        LayoutControls(cx, cy);
}

void CKnownUsersWnd::LayoutControls(int cx, int cy)
{
    const int margin = CEmuleNextUiMetrics::Scale(m_hWnd, 8);
    const int gap = CEmuleNextUiMetrics::Scale(m_hWnd, 6);
    const int row = CEmuleNextUiMetrics::Scale(m_hWnd, 25);
    const int modesWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 330);
    const int searchWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 200);
    const int refreshWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 82);
    const int darkWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 92);
    const int actionWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 92);
    const int deleteWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 105);

    int x = margin;
    m_modes.MoveWindow(x, margin, modesWidth, row + CEmuleNextUiMetrics::Scale(m_hWnd, 2));
    x += modesWidth + gap;
    m_search.MoveWindow(x, margin + CEmuleNextUiMetrics::Scale(m_hWnd, 2), searchWidth, row - CEmuleNextUiMetrics::Scale(m_hWnd, 2));
    x += searchWidth + gap;
    m_refreshButton.MoveWindow(x, margin, refreshWidth, row);
    x += refreshWidth + gap;
    m_darkModeButton.MoveWindow(x, margin + CEmuleNextUiMetrics::Scale(m_hWnd, 2), darkWidth, row - CEmuleNextUiMetrics::Scale(m_hWnd, 2));

    const int secondTop = margin + row + gap;
    x = margin;
    m_refreshPeerButton.MoveWindow(x, secondTop, actionWidth, row);
    x += actionWidth + gap;
    m_favoriteButton.MoveWindow(x, secondTop, actionWidth, row);
    x += actionWidth + gap;
    m_aliasButton.MoveWindow(x, secondTop, actionWidth, row);
    x += actionWidth + gap;
    m_deleteHistoryButton.MoveWindow(x, secondTop, deleteWidth, row);
    x += deleteWidth + gap + CEmuleNextUiMetrics::Scale(m_hWnd, 4);
    m_status.MoveWindow(x, secondTop + CEmuleNextUiMetrics::Scale(m_hWnd, 4),
        max(0, cx - margin - x), row);

    const int listTop = secondTop + row + gap;
    const int available = max(0, cy - listTop - margin - gap);
    const int usersHeight = max(CEmuleNextUiMetrics::Scale(m_hWnd, 120), available * 52 / 100);
    const int filesTop = listTop + usersHeight + gap;
    m_users.MoveWindow(margin, listTop, max(0, cx - margin * 2), usersHeight);
    m_files.MoveWindow(margin, filesTop, max(0, cx - margin * 2), max(0, cy - margin - filesTop));
}

void CKnownUsersWnd::LoadViewState()
{
    int mode = theApp.GetProfileInt(PROFILE_SECTION, _T("Mode"), ENKUM_CURRENT);
    if (mode < 0 || mode >= ENKUM_COUNT)
        mode = ENKUM_CURRENT;
    m_mode = static_cast<EmuleNextKnownUsersMode>(mode);
    m_sortColumn = theApp.GetProfileInt(PROFILE_SECTION, _T("SortColumn"), 7);
    if (m_sortColumn < 0 || m_sortColumn >= USER_COLUMN_COUNT)
        m_sortColumn = 7;
    m_sortAscending = theApp.GetProfileInt(PROFILE_SECTION, _T("SortAscending"), 0) != 0;
    m_search.SetWindowText(theApp.GetProfileString(PROFILE_SECTION, _T("Search"), _T("")));
}

void CKnownUsersWnd::SaveViewState() const
{
    theApp.WriteProfileInt(PROFILE_SECTION, _T("Mode"), static_cast<int>(m_mode));
    theApp.WriteProfileInt(PROFILE_SECTION, _T("SortColumn"), m_sortColumn);
    theApp.WriteProfileInt(PROFILE_SECTION, _T("SortAscending"), m_sortAscending ? 1 : 0);
    CString search;
    if (::IsWindow(m_search.m_hWnd))
        m_search.GetWindowText(search);
    theApp.WriteProfileString(PROFILE_SECTION, _T("Search"), search);
    if (::IsWindow(m_users.m_hWnd)) {
        for (int i = 0; i < USER_COLUMN_COUNT; ++i) {
            CString key;
            key.Format(_T("ColumnWidth%d"), i);
            theApp.WriteProfileInt(PROFILE_SECTION, key, m_users.GetColumnWidth(i));
        }
    }
}

void CKnownUsersWnd::ApplyUserColumnWidths()
{
    for (int i = 0; i < USER_COLUMN_COUNT; ++i) {
        CString key;
        key.Format(_T("ColumnWidth%d"), i);
        const int width = theApp.GetProfileInt(PROFILE_SECTION, key, -1);
        if (width >= CEmuleNextUiMetrics::Scale(m_hWnd, 24))
            m_users.SetColumnWidth(i, width);
    }
}

void CKnownUsersWnd::Refresh(bool force)
{
    if (!force && !IsWindowVisible())
        return;
    RefreshUsers();
    RefreshFiles();
    UpdateSelectedStatus();
}

void CKnownUsersWnd::RefreshUsers()
{
    if (m_usersLoading || !theEmuleNext.IsRunning())
        return;
    const CStringW path = theEmuleNext.Database().GetDatabasePath();
    if (path.IsEmpty())
        return;

    std::unique_ptr<UsersLoadContext> context(new UsersLoadContext);
    context->target = m_hWnd;
    context->databasePath = path;
    context->query = m_mode == ENKUM_FAVORITES ? ENKUQ_FAVORITES
        : (m_mode == ENKUM_RECENT ? ENKUQ_RECENT : ENKUQ_ALL);
    m_usersLoading = true;
    if (AfxBeginThread(LoadUsersWorker, context.get(), THREAD_PRIORITY_BELOW_NORMAL) == NULL) {
        m_usersLoading = false;
        m_status.SetWindowText(_T("Unable to start Known Users background refresh."));
        return;
    }
    context.release();
}

void CKnownUsersWnd::RefreshFiles()
{
    EmuleNextHash16 hash;
    if (m_filesLoading || !SelectedHash(hash) || !theEmuleNext.IsRunning())
        return;
    const CStringW path = theEmuleNext.Database().GetDatabasePath();
    if (path.IsEmpty())
        return;

    std::unique_ptr<FilesLoadContext> context(new FilesLoadContext);
    context->target = m_hWnd;
    context->databasePath = path;
    context->peerHash = hash;
    m_filesLoading = true;
    if (AfxBeginThread(LoadFilesWorker, context.get(), THREAD_PRIORITY_BELOW_NORMAL) == NULL) {
        m_filesLoading = false;
        return;
    }
    context.release();
}

bool CKnownUsersWnd::IsCurrent(const EmuleNextKnownUserRecord& user) const
{
    return user.userHash.valid && theApp.clientlist != NULL
        && theApp.clientlist->FindClientByUserHash(user.userHash.bytes.data()) != NULL;
}

bool CKnownUsersWnd::MatchesMode(const EmuleNextKnownUserRecord& user) const
{
    if (m_mode == ENKUM_CURRENT)
        return IsCurrent(user);
    if (m_mode == ENKUM_HISTORY)
        return !IsCurrent(user);
    if (m_mode == ENKUM_FAVORITES)
        return user.favorite;
    return true;
}

bool CKnownUsersWnd::MatchesSearch(const EmuleNextKnownUserRecord& user) const
{
    CString needle;
    m_search.GetWindowText(needle);
    needle.Trim();
    if (needle.IsEmpty())
        return true;
    needle.MakeLower();

    CString haystack = DisplayName(user) + _T(" ") + CString(user.alias) + _T(" ")
        + ClientText(user) + _T(" ") + EndpointText(user) + _T(" ") + HashText(user.userHash);
    haystack.MakeLower();
    return haystack.Find(needle) >= 0;
}

void CKnownUsersWnd::SortUserRows()
{
    const int column = m_sortColumn;
    const bool ascending = m_sortAscending;
    std::stable_sort(m_userRows.begin(), m_userRows.end(), [this, column, ascending](
        const EmuleNextKnownUserRecord& left, const EmuleNextKnownUserRecord& right) {
        int result = 0;
        switch (column) {
        case 0: result = DisplayName(left).CompareNoCase(DisplayName(right)); break;
        case 1: result = CString(left.alias).CompareNoCase(CString(right.alias)); break;
        case 2: result = static_cast<int>(IsCurrent(left)) - static_cast<int>(IsCurrent(right)); break;
        case 3: result = ClientText(left).CompareNoCase(ClientText(right)); break;
        case 4: result = EndpointText(left).CompareNoCase(EndpointText(right)); break;
        case 5: result = BrowseStatusText(left.userHash).CompareNoCase(BrowseStatusText(right.userHash)); break;
        case 6: result = CompareUInt64(left.firstSeen, right.firstSeen); break;
        case 7: result = CompareUInt64(left.lastSeen, right.lastSeen); break;
        case 8: result = left.fileCount < right.fileCount ? -1 : (left.fileCount > right.fileCount ? 1 : 0); break;
        case 9: result = CompareUInt64(left.totalBytes, right.totalBytes); break;
        case 10: result = static_cast<int>(left.favorite) - static_cast<int>(right.favorite); break;
        case 11: result = HashText(left.userHash).CompareNoCase(HashText(right.userHash)); break;
        default: break;
        }
        return ascending ? result < 0 : result > 0;
    });
}

void CKnownUsersWnd::PopulateUsers()
{
    m_users.SetRedraw(FALSE);
    m_users.DeleteAllItems();

    for (size_t i = 0; i < m_userRows.size(); ++i) {
        const EmuleNextKnownUserRecord& user = m_userRows[i];
        if (!MatchesMode(user) || !MatchesSearch(user))
            continue;
        const int row = m_users.InsertItem(m_users.GetItemCount(), DisplayName(user));
        m_users.SetItemData(row, static_cast<DWORD_PTR>(i));
        m_users.SetItemText(row, 1, CString(user.alias));
        m_users.SetItemText(row, 2, IsCurrent(user) ? _T("Current") : _T("History"));
        m_users.SetItemText(row, 3, ClientText(user));
        m_users.SetItemText(row, 4, EndpointText(user));
        m_users.SetItemText(row, 5, BrowseStatusText(user.userHash));
        m_users.SetItemText(row, 6, DateText(user.firstSeen));
        m_users.SetItemText(row, 7, DateText(user.lastSeen));
        CString count;
        count.Format(_T("%u"), user.fileCount);
        m_users.SetItemText(row, 8, count);
        m_users.SetItemText(row, 9, CastItoXBytes(user.totalBytes, false, false, 1));
        m_users.SetItemText(row, 10, user.favorite ? _T("Yes") : _T("No"));
        m_users.SetItemText(row, 11, HashText(user.userHash));
    }

    m_users.SetRedraw(TRUE);
    m_users.Invalidate(FALSE);
}

void CKnownUsersWnd::PopulateFiles()
{
    m_files.SetRedraw(FALSE);
    m_files.DeleteAllItems();
    for (size_t i = 0; i < m_fileRows.size(); ++i) {
        const EmuleNextKnownFileRecord& file = m_fileRows[i];
        CString name(file.fileName);
        if (name.IsEmpty())
            name = _T("<unnamed>");
        const int row = m_files.InsertItem(static_cast<int>(i), name);
        m_files.SetItemText(row, 1, FileStateText(file));
        m_files.SetItemText(row, 2, CastItoXBytes(file.fileSize, false, false, 1));
        m_files.SetItemText(row, 3, DateText(file.firstSeen));
        m_files.SetItemText(row, 4, DateText(file.lastSeen));
        m_files.SetItemText(row, 5, HashText(file.fileHash));
        m_files.SetItemText(row, 6, CString(file.aichHash));
    }
    m_files.SetRedraw(TRUE);
    m_files.Invalidate(FALSE);
}

int CKnownUsersWnd::SelectedUserIndex() const
{
    const int selected = m_users.GetNextItem(-1, LVNI_SELECTED);
    if (selected < 0)
        return -1;
    const DWORD_PTR value = m_users.GetItemData(selected);
    return value < m_userRows.size() ? static_cast<int>(value) : -1;
}

bool CKnownUsersWnd::SelectedHash(EmuleNextHash16& hash) const
{
    const int index = SelectedUserIndex();
    if (index < 0)
        return false;
    hash = m_userRows[static_cast<size_t>(index)].userHash;
    return hash.valid;
}

bool CKnownUsersWnd::GetShareState(const EmuleNextHash16& hash, EmuleNextPeerShareState& state) const
{
    return theApp.clientlist != NULL && hash.valid && theApp.clientlist->GetPeerShareState(hash, state);
}

CString CKnownUsersWnd::BrowseStatusText(const EmuleNextHash16& hash) const
{
    EmuleNextPeerShareState state;
    if (!GetShareState(hash, state))
        return _T("Idle");

    CString label;
    switch (state.status) {
    case ENPSS_QUEUED: label = _T("Queued"); break;
    case ENPSS_QUERYING: label = _T("Querying"); break;
    case ENPSS_SHARED: label = _T("Shared"); break;
    case ENPSS_DENIED: label = _T("Denied"); break;
    case ENPSS_TIMEOUT: label = _T("Timeout"); break;
    case ENPSS_UNSUPPORTED: label = _T("Unsupported"); break;
    case ENPSS_ERROR: label = _T("Error"); break;
    default: label = _T("Idle"); break;
    }
    if (state.nextAllowed > static_cast<uint64>(time(NULL)))
        label += _T(" (") + RemainingText(state.nextAllowed) + _T(")");
    return label;
}

CString CKnownUsersWnd::FileStateText(const EmuleNextKnownFileRecord& file) const
{
    EmuleNextPeerShareState state;
    if (GetShareState(m_fileRowsPeer, state) && state.status == ENPSS_SHARED
        && state.lastCompleted != 0 && file.lastSeen + 5 >= state.lastCompleted)
        return _T("Current");
    return _T("History");
}

CString CKnownUsersWnd::EndpointText(const EmuleNextKnownUserRecord& user) const
{
    if (user.endpointIp == 0)
        return CString();
    CString result(ipstr(user.endpointIp));
    if (user.endpointTcpPort != 0) {
        CString port;
        port.Format(_T(":%u"), static_cast<unsigned>(user.endpointTcpPort));
        result += port;
    }
    return result;
}

CString CKnownUsersWnd::ClientText(const EmuleNextKnownUserRecord& user) const
{
    CString value(user.clientSoftware);
    if (!user.clientVersion.IsEmpty()) {
        if (!value.IsEmpty())
            value += _T(" ");
        value += CString(user.clientVersion);
    }
    return value;
}

CString CKnownUsersWnd::HashText(const EmuleNextHash16& hash)
{
    if (!hash.valid)
        return CString();
    CString result;
    for (size_t i = 0; i < hash.bytes.size(); ++i) {
        CString pair;
        pair.Format(_T("%02X"), static_cast<unsigned>(hash.bytes[i]));
        result += pair;
    }
    return result;
}

CString CKnownUsersWnd::DateText(uint64 timestamp)
{
    if (timestamp == 0)
        return CString();
    CTime value(static_cast<time_t>(timestamp));
    return value.Format(_T("%Y-%m-%d %H:%M"));
}

CString CKnownUsersWnd::RemainingText(uint64 target)
{
    const uint64 now = static_cast<uint64>(time(NULL));
    if (target <= now)
        return _T("ready");
    uint64 seconds = target - now;
    CString result;
    if (seconds >= 24 * 60 * 60)
        result.Format(_T("%llud"), static_cast<unsigned long long>((seconds + 86399) / 86400));
    else if (seconds >= 60 * 60)
        result.Format(_T("%lluh"), static_cast<unsigned long long>((seconds + 3599) / 3600));
    else if (seconds >= 60)
        result.Format(_T("%llum"), static_cast<unsigned long long>((seconds + 59) / 60));
    else
        result.Format(_T("%llus"), static_cast<unsigned long long>(seconds));
    return result;
}

CString CKnownUsersWnd::DisplayName(const EmuleNextKnownUserRecord& user)
{
    CString name(user.userName);
    if (name.IsEmpty())
        name = _T("<unknown user>");
    return name;
}

bool CKnownUsersWnd::SameHash(const EmuleNextHash16& left, const EmuleNextHash16& right)
{
    return left.valid && right.valid && left.bytes == right.bytes;
}

void CKnownUsersWnd::UpdateSelectedStatus()
{
    const int index = SelectedUserIndex();
    if (index < 0) {
        CString status;
        status.Format(_T("%d visible peers; data is refreshed in background."), m_users.GetItemCount());
        m_status.SetWindowText(status);
        return;
    }

    const EmuleNextKnownUserRecord& user = m_userRows[static_cast<size_t>(index)];
    CString status;
    status.Format(_T("%s | %s | first %s | last %s"),
        (LPCTSTR)BrowseStatusText(user.userHash), (LPCTSTR)EndpointText(user),
        (LPCTSTR)DateText(user.firstSeen), (LPCTSTR)DateText(user.lastSeen));
    EmuleNextPeerShareState state;
    if (GetShareState(user.userHash, state) && !state.lastError.IsEmpty())
        status += _T(" | ") + state.lastError;
    m_status.SetWindowText(status);
}

void CKnownUsersWnd::UpdateActionButtons()
{
    const int index = SelectedUserIndex();
    const bool selected = index >= 0;
    bool current = false;
    bool favorite = false;
    if (selected) {
        current = IsCurrent(m_userRows[static_cast<size_t>(index)]);
        favorite = m_userRows[static_cast<size_t>(index)].favorite;
    }
    m_refreshPeerButton.EnableWindow(selected && current && !m_deleteLoading);
    m_favoriteButton.EnableWindow(selected && !m_deleteLoading);
    m_aliasButton.EnableWindow(selected && !m_deleteLoading);
    m_deleteHistoryButton.EnableWindow(selected && !m_deleteLoading);
    m_favoriteButton.SetWindowText(favorite ? _T("Unfavorite") : _T("Favorite"));
}

void CKnownUsersWnd::OnTimer(UINT_PTR timerId)
{
    if (timerId == TIMER_EN_REFRESH) {
        Refresh(false);
        return;
    }
    CWnd::OnTimer(timerId);
}

BOOL CKnownUsersWnd::OnEraseBkgnd(CDC* dc)
{
    if (!CEmuleNextTheme::IsDarkMode())
        return CWnd::OnEraseBkgnd(dc);
    CRect rect;
    GetClientRect(&rect);
    dc->FillSolidRect(rect, CEmuleNextTheme::BackgroundColor());
    return TRUE;
}

HBRUSH CKnownUsersWnd::OnCtlColor(CDC* dc, CWnd* wnd, UINT ctlColor)
{
    if (!CEmuleNextTheme::IsDarkMode())
        return CWnd::OnCtlColor(dc, wnd, ctlColor);
    dc->SetTextColor(CEmuleNextTheme::TextColor());
    dc->SetBkColor(CEmuleNextTheme::BackgroundColor());
    if (ctlColor == CTLCOLOR_STATIC || ctlColor == CTLCOLOR_DLG || ctlColor == CTLCOLOR_EDIT)
        return static_cast<HBRUSH>(m_darkBrush.GetSafeHandle());
    return CWnd::OnCtlColor(dc, wnd, ctlColor);
}

void CKnownUsersWnd::OnUserSelectionChanged(NMHDR* header, LRESULT* result)
{
    const NMLISTVIEW* change = reinterpret_cast<const NMLISTVIEW*>(header);
    if ((change->uChanged & LVIF_STATE) != 0 && (change->uNewState & LVIS_SELECTED) != 0) {
        m_fileRows.clear();
        m_fileRowsPeer = EmuleNextHash16();
        PopulateFiles();
        RefreshFiles();
        UpdateSelectedStatus();
        UpdateActionButtons();
    }
    *result = 0;
}

void CKnownUsersWnd::OnUserColumnClick(NMHDR* header, LRESULT* result)
{
    const NMLISTVIEW* click = reinterpret_cast<const NMLISTVIEW*>(header);
    EmuleNextHash16 selected;
    const bool hadSelection = SelectedHash(selected);
    if (m_sortColumn == click->iSubItem)
        m_sortAscending = !m_sortAscending;
    else {
        m_sortColumn = click->iSubItem;
        m_sortAscending = true;
    }
    SortUserRows();
    PopulateUsers();
    if (hadSelection) {
        for (int row = 0; row < m_users.GetItemCount(); ++row) {
            const DWORD_PTR index = m_users.GetItemData(row);
            if (index < m_userRows.size() && SameHash(selected, m_userRows[index].userHash)) {
                m_users.SetItemState(row, LVIS_SELECTED | LVIS_FOCUSED, LVIS_SELECTED | LVIS_FOCUSED);
                break;
            }
        }
    }
    SaveViewState();
    *result = 0;
}

void CKnownUsersWnd::OnModeChanged(NMHDR*, LRESULT* result)
{
    const int mode = m_modes.GetCurSel();
    if (mode >= 0 && mode < ENKUM_COUNT)
        m_mode = static_cast<EmuleNextKnownUsersMode>(mode);
    m_fileRows.clear();
    m_fileRowsPeer = EmuleNextHash16();
    PopulateFiles();
    RefreshUsers();
    SaveViewState();
    *result = 0;
}

void CKnownUsersWnd::OnSearchChanged()
{
    EmuleNextHash16 selected;
    const bool hadSelection = SelectedHash(selected);
    PopulateUsers();
    bool restored = false;
    if (hadSelection) {
        for (int row = 0; row < m_users.GetItemCount(); ++row) {
            const DWORD_PTR index = m_users.GetItemData(row);
            if (index < m_userRows.size() && SameHash(selected, m_userRows[index].userHash)) {
                m_users.SetItemState(row, LVIS_SELECTED | LVIS_FOCUSED, LVIS_SELECTED | LVIS_FOCUSED);
                restored = true;
                break;
            }
        }
    }
    if (!restored) {
        m_fileRows.clear();
        m_fileRowsPeer = EmuleNextHash16();
        PopulateFiles();
    }
    UpdateSelectedStatus();
    UpdateActionButtons();
}

void CKnownUsersWnd::OnRefreshClicked()
{
    Refresh(true);
}

void CKnownUsersWnd::OnRefreshPeerClicked()
{
    EmuleNextHash16 hash;
    if (!SelectedHash(hash) || theApp.clientlist == NULL)
        return;
    if (theApp.clientlist->QueuePeerShareRefresh(hash)) {
        m_status.SetWindowText(_T("Selected peer refresh queued through the normal eMule shared-file request."));
        UpdateActionButtons();
        return;
    }

    EmuleNextPeerShareState state;
    if (theApp.clientlist->GetPeerShareState(hash, state)) {
        if (state.status == ENPSS_QUERYING)
            m_status.SetWindowText(_T("Selected peer is already being queried."));
        else if (state.nextAllowed > static_cast<uint64>(time(NULL)))
            m_status.SetWindowText(_T("Selected peer refresh is in cooldown for ") + RemainingText(state.nextAllowed) + _T("."));
        else
            m_status.SetWindowText(_T("Selected peer is not currently available for a shared-file request."));
    }
    else
        m_status.SetWindowText(_T("Selected peer is offline or not currently requestable."));
}

void CKnownUsersWnd::OnFavoriteClicked()
{
    const int index = SelectedUserIndex();
    if (index < 0)
        return;
    EmuleNextKnownUserRecord& user = m_userRows[static_cast<size_t>(index)];
    if (theEmuleNext.SetPeerFavorite(user.userHash.bytes.data(), !user.favorite)) {
        user.favorite = !user.favorite;
        PopulateUsers();
        RefreshUsers();
    }
}

void CKnownUsersWnd::OnAliasClicked()
{
    const int index = SelectedUserIndex();
    if (index < 0)
        return;
    EmuleNextKnownUserRecord& user = m_userRows[static_cast<size_t>(index)];
    InputBox input(this);
    CString label;
    label.Format(_T("Local alias for %s:"), (LPCTSTR)DisplayName(user));
    input.SetLabels(_T("eMule Next peer alias"), label, CString(user.alias));
    if (input.DoModal() != IDOK || input.WasCancelled())
        return;
    CString alias(input.GetInput());
    alias.Trim();
    if (alias.GetLength() > 128)
        alias = alias.Left(128);
    if (theEmuleNext.SetPeerAlias(user.userHash.bytes.data(), alias)) {
        user.alias = CStringW(alias);
        PopulateUsers();
        RefreshUsers();
    }
}

void CKnownUsersWnd::OnDeleteHistoryClicked()
{
    EmuleNextHash16 hash;
    const int index = SelectedUserIndex();
    if (index < 0 || !SelectedHash(hash) || m_deleteLoading)
        return;
    CString prompt;
    prompt.Format(_T("Delete local intelligence history for '%s'?\n\nThe local alias/favorite is retained. A current peer may reappear when observed again."),
        (LPCTSTR)DisplayName(m_userRows[static_cast<size_t>(index)]));
    if (AfxMessageBox(prompt, MB_YESNO | MB_ICONWARNING) != IDYES)
        return;

    const CStringW path = theEmuleNext.Database().GetDatabasePath();
    if (path.IsEmpty())
        return;
    std::unique_ptr<DeleteLoadContext> context(new DeleteLoadContext);
    context->target = m_hWnd;
    context->databasePath = path;
    context->peerHash = hash;
    m_deleteLoading = true;
    UpdateActionButtons();
    m_status.SetWindowText(_T("Deleting selected peer intelligence history in background..."));
    if (AfxBeginThread(DeleteHistoryWorker, context.get(), THREAD_PRIORITY_BELOW_NORMAL) == NULL) {
        m_deleteLoading = false;
        UpdateActionButtons();
        m_status.SetWindowText(_T("Unable to start peer-history delete worker."));
        return;
    }
    context.release();
}

void CKnownUsersWnd::OnDarkModeClicked()
{
    const bool enabled = m_darkModeButton.GetCheck() == BST_CHECKED;
    CEmuleNextTheme::SetDarkMode(enabled);
    if (theApp.emuledlg != NULL)
        CEmuleNextTheme::ApplyToWindow(theApp.emuledlg->GetSafeHwnd());
    else
        CEmuleNextTheme::ApplyToWindow(m_hWnd);
    Invalidate(TRUE);
}

LRESULT CKnownUsersWnd::OnUsersLoaded(WPARAM, LPARAM value)
{
    std::unique_ptr<UsersLoadResult> result(reinterpret_cast<UsersLoadResult*>(value));
    m_usersLoading = false;
    if (result.get() == NULL || !result->ok) {
        m_status.SetWindowText(_T("Known Users database could not be read."));
        return 0;
    }

    EmuleNextHash16 previous;
    const bool hadSelection = SelectedHash(previous);
    m_users.DeleteAllItems();
    m_userRows.swap(result->rows);
    SortUserRows();
    PopulateUsers();

    int selectRow = -1;
    if (hadSelection) {
        for (int row = 0; row < m_users.GetItemCount(); ++row) {
            const DWORD_PTR index = m_users.GetItemData(row);
            if (index < m_userRows.size() && SameHash(previous, m_userRows[index].userHash)) {
                selectRow = row;
                break;
            }
        }
    }
    if (selectRow < 0 && m_users.GetItemCount() > 0)
        selectRow = 0;
    if (selectRow >= 0) {
        m_users.SetItemState(selectRow, LVIS_SELECTED | LVIS_FOCUSED, LVIS_SELECTED | LVIS_FOCUSED);
        m_users.EnsureVisible(selectRow, FALSE);
    }

    UpdateSelectedStatus();
    UpdateActionButtons();
    return 0;
}

LRESULT CKnownUsersWnd::OnFilesLoaded(WPARAM, LPARAM value)
{
    std::unique_ptr<FilesLoadResult> result(reinterpret_cast<FilesLoadResult*>(value));
    m_filesLoading = false;
    if (result.get() == NULL || !result->ok)
        return 0;

    EmuleNextHash16 selected;
    if (!SelectedHash(selected) || !SameHash(selected, result->peerHash))
        return 0;
    m_fileRowsPeer = result->peerHash;
    m_fileRows.swap(result->rows);
    PopulateFiles();
    UpdateSelectedStatus();
    return 0;
}

LRESULT CKnownUsersWnd::OnHistoryDeleted(WPARAM, LPARAM value)
{
    std::unique_ptr<DeleteLoadResult> result(reinterpret_cast<DeleteLoadResult*>(value));
    m_deleteLoading = false;
    if (result.get() == NULL || !result->ok) {
        m_status.SetWindowText(_T("Peer intelligence history could not be deleted."));
        UpdateActionButtons();
        return 0;
    }
    m_fileRows.clear();
    m_fileRowsPeer = EmuleNextHash16();
    PopulateFiles();
    m_status.SetWindowText(_T("Peer intelligence history deleted; alias/favorite retained."));
    RefreshUsers();
    UpdateActionButtons();
    return 0;
}
