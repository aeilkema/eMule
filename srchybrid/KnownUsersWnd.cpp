//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later

#include "stdafx.h"
#include "KnownUsersWnd.h"

#include "ClientList.h"
#include "EmuleNextRuntime.h"
#include "EmuleNextTheme.h"
#include "EmuleNextUiMetrics.h"
#include "resource.h"
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

void CKnownUsersWnd::Refresh(bool force)
{
    if (!force && !IsWindowVisible())
        return;
    RefreshUsers();
    RefreshFiles();
}

void CKnownUsersWnd::RefreshUsers()
{
    if (m_usersLoading || !theEmuleNext.IsRunning())
        return;
    const CStringW path = theEmuleNext.Database().GetDatabasePath();
    if (path.IsEmpty())
        return;

    CString search;
    m_search.GetWindowText(search);
    search.Trim();
    m_searchText = search;

    std::unique_ptr<UsersLoadContext> context(new UsersLoadContext);
    context->target = m_hWnd;
    context->databasePath = path;
    context->query.mode = m_mode == ENKUM_FAVORITES ? ENKUQ_FAVORITES
        : (m_mode == ENKUM_RECENT ? ENKUQ_RECENT : ENKUQ_ALL);
    context->query.text = CStringW(search);
    context->query.recentSince = m_mode == ENKUM_RECENT
        ? static_cast<uint64>(time(NULL)) - 7u * 24u * 60u * 60u : 0;
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

bool CKnownUsersWnd::RowVisible(const EmuleNextKnownUserRecord& user) const
{
    const bool current = IsCurrent(user);
    if (m_mode == ENKUM_CURRENT && !current)
        return false;
    if (m_mode == ENKUM_HISTORY && current)
        return false;
    return true;
}

bool CKnownUsersWnd::IsCurrent(const EmuleNextKnownUserRecord& user) const
{
    return theApp.clientlist != NULL && user.userHash.valid
        && theApp.clientlist->FindClientByUserHash(user.userHash.bytes.data()) != NULL;
}

void CKnownUsersWnd::SortUserRows()
{
    const int column = m_sortColumn;
    const bool ascending = m_sortAscending;
    std::stable_sort(m_userRows.begin(), m_userRows.end(),
        [this, column, ascending](const EmuleNextKnownUserRecord& a, const EmuleNextKnownUserRecord& b) {
            int value = 0;
            switch (column) {
            case 0: value = CString(a.userName).CompareNoCase(CString(b.userName)); break;
            case 1: value = CString(a.alias).CompareNoCase(CString(b.alias)); break;
            case 2: value = static_cast<int>(IsCurrent(a)) - static_cast<int>(IsCurrent(b)); break;
            case 3: value = CString(a.clientSoftware).CompareNoCase(CString(b.clientSoftware)); break;
            case 4:
                value = a.endpointIp < b.endpointIp ? -1 : (a.endpointIp > b.endpointIp ? 1
                    : (a.endpointTcpPort < b.endpointTcpPort ? -1 : (a.endpointTcpPort > b.endpointTcpPort ? 1 : 0)));
                break;
            case 6: value = CompareUInt64(a.firstSeen, b.firstSeen); break;
            case 7: value = CompareUInt64(a.lastSeen, b.lastSeen); break;
            case 8: value = a.fileCount < b.fileCount ? -1 : (a.fileCount > b.fileCount ? 1 : 0); break;
            case 9: value = CompareUInt64(a.totalBytes, b.totalBytes); break;
            case 10: value = static_cast<int>(a.favorite) - static_cast<int>(b.favorite); break;
            default: value = CString(a.userName).CompareNoCase(CString(b.userName)); break;
            }
            return ascending ? value < 0 : value > 0;
        });
}

void CKnownUsersWnd::PopulateUsers()
{
    SortUserRows();
    m_users.SetRedraw(FALSE);
    m_users.DeleteAllItems();
    for (size_t i = 0; i < m_userRows.size(); ++i) {
        const EmuleNextKnownUserRecord& user = m_userRows[i];
        if (!RowVisible(user))
            continue;
        CString name(user.userName);
        if (name.IsEmpty()) name = _T("<unknown user>");
        const int row = m_users.InsertItem(m_users.GetItemCount(), name);
        m_users.SetItemData(row, static_cast<DWORD_PTR>(i));
        m_users.SetItemText(row, 1, CString(user.alias));
        m_users.SetItemText(row, 2, IsCurrent(user) ? _T("Current") : _T("History"));

        CString client(user.clientSoftware);
        if (!user.clientVersion.IsEmpty()) {
            if (!client.IsEmpty()) client += _T(" ");
            client += CString(user.clientVersion);
        }
        m_users.SetItemText(row, 3, client);
        m_users.SetItemText(row, 4, EndpointText(user));

        EmuleNextPeerShareState state;
        const bool haveState = theApp.clientlist != NULL && theApp.clientlist->GetPeerShareState(user.userHash, state);
        m_users.SetItemText(row, 5, BrowseStatusText(haveState ? &state : NULL, IsCurrent(user)));
        m_users.SetItemText(row, 6, DateText(user.firstSeen));
        m_users.SetItemText(row, 7, DateText(user.lastSeen));
        CString count; count.Format(_T("%u"), user.fileCount); m_users.SetItemText(row, 8, count);
        m_users.SetItemText(row, 9, CastItoXBytes(user.totalBytes, false, false, 1));
        m_users.SetItemText(row, 10, user.favorite ? _T("Yes") : _T("No"));
        m_users.SetItemText(row, 11, HashText(user.userHash));
    }
    m_users.SetRedraw(TRUE);
    m_users.Invalidate(FALSE);
}

void CKnownUsersWnd::PopulateFiles()
{
    EmuleNextPeerShareState state;
    const bool haveState = theApp.clientlist != NULL && m_fileRowsPeer.valid
        && theApp.clientlist->GetPeerShareState(m_fileRowsPeer, state);

    m_files.SetRedraw(FALSE);
    m_files.DeleteAllItems();
    for (size_t i = 0; i < m_fileRows.size(); ++i) {
        const EmuleNextKnownFileRecord& file = m_fileRows[i];
        CString name(file.fileName); if (name.IsEmpty()) name = _T("<unnamed>");
        const int row = m_files.InsertItem(static_cast<int>(i), name);
        bool current = false;
        if (haveState && state.status == ENPSS_SHARED && state.lastCompleted != 0)
            current = file.lastSeen + 5 >= state.lastCompleted;
        m_files.SetItemText(row, 1, current ? _T("Current") : _T("History"));
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
    if (selected < 0) return -1;
    const DWORD_PTR value = m_users.GetItemData(selected);
    return value < m_userRows.size() ? static_cast<int>(value) : -1;
}

bool CKnownUsersWnd::SelectedHash(EmuleNextHash16& hash) const
{
    const int index = SelectedUserIndex();
    if (index < 0) return false;
    hash = m_userRows[static_cast<size_t>(index)].userHash;
    return hash.valid;
}

CString CKnownUsersWnd::HashText(const EmuleNextHash16& hash)
{
    if (!hash.valid) return CString();
    CString result;
    for (size_t i = 0; i < hash.bytes.size(); ++i) {
        CString pair; pair.Format(_T("%02X"), static_cast<unsigned>(hash.bytes[i])); result += pair;
    }
    return result;
}

CString CKnownUsersWnd::DateText(uint64 timestamp)
{
    if (timestamp == 0) return CString();
    CTime value(static_cast<time_t>(timestamp));
    return value.Format(_T("%Y-%m-%d %H:%M"));
}

CString CKnownUsersWnd::EndpointText(const EmuleNextKnownUserRecord& user)
{
    if (user.endpointIp == 0) return CString();
    CString result;
    result.Format(_T("%s:%u"), (LPCTSTR)ipstr(user.endpointIp), static_cast<unsigned>(user.endpointTcpPort));
    return result;
}

CString CKnownUsersWnd::RemainingText(uint64 timestamp)
{
    const uint64 now = static_cast<uint64>(time(NULL));
    if (timestamp <= now) return _T("now");
    uint64 seconds = timestamp - now;
    CString value;
    if (seconds >= 3600) value.Format(_T("%lluh %02llum"), seconds / 3600, (seconds % 3600) / 60);
    else if (seconds >= 60) value.Format(_T("%llum %02llus"), seconds / 60, seconds % 60);
    else value.Format(_T("%llus"), seconds);
    return value;
}

CString CKnownUsersWnd::BrowseStatusText(const EmuleNextPeerShareState* state, bool current)
{
    if (state == NULL) return current ? _T("Ready") : _T("Offline");
    CString label;
    switch (state->status) {
    case ENPSS_QUEUED: label = _T("Queued"); break;
    case ENPSS_QUERYING: label = _T("Querying"); break;
    case ENPSS_SHARED: label = _T("Shared"); break;
    case ENPSS_DENIED: label = _T("Denied"); break;
    case ENPSS_TIMEOUT: label = _T("Timeout"); break;
    case ENPSS_UNSUPPORTED: label = _T("Unsupported"); break;
    case ENPSS_ERROR: label = _T("Error"); break;
    default: label = current ? _T("Ready") : _T("Offline"); break;
    }
    if (state->nextAllowed > static_cast<uint64>(time(NULL))) {
        label += _T("; retry ");
        label += RemainingText(state->nextAllowed);
    }
    if (!state->lastError.IsEmpty()) {
        label += _T("; ");
        label += state->lastError;
    }
    return label;
}

void CKnownUsersWnd::OnTimer(UINT_PTR timerId)
{
    if (timerId == TIMER_EN_REFRESH) { Refresh(false); return; }
    CWnd::OnTimer(timerId);
}

BOOL CKnownUsersWnd::OnEraseBkgnd(CDC* dc)
{
    if (!CEmuleNextTheme::IsDarkMode()) return CWnd::OnEraseBkgnd(dc);
    CRect rect; GetClientRect(&rect); dc->FillSolidRect(rect, CEmuleNextTheme::BackgroundColor()); return TRUE;
}

HBRUSH CKnownUsersWnd::OnCtlColor(CDC* dc, CWnd* wnd, UINT ctlColor)
{
    if (!CEmuleNextTheme::IsDarkMode()) return CWnd::OnCtlColor(dc, wnd, ctlColor);
    dc->SetTextColor(CEmuleNextTheme::TextColor()); dc->SetBkColor(CEmuleNextTheme::BackgroundColor());
    if (ctlColor == CTLCOLOR_STATIC || ctlColor == CTLCOLOR_DLG) return static_cast<HBRUSH>(m_darkBrush.GetSafeHandle());
    return CWnd::OnCtlColor(dc, wnd, ctlColor);
}

void CKnownUsersWnd::OnUserSelectionChanged(NMHDR* header, LRESULT* result)
{
    const NMLISTVIEW* change = reinterpret_cast<const NMLISTVIEW*>(header);
    if ((change->uChanged & LVIF_STATE) != 0 && (change->uNewState & LVIS_SELECTED) != 0) {
        m_fileRows.clear(); m_fileRowsPeer = EmuleNextHash16(); PopulateFiles(); RefreshFiles(); UpdateActionButtons();
    }
    *result = 0;
}

void CKnownUsersWnd::OnUserColumnClick(NMHDR* header, LRESULT* result)
{
    const NMLISTVIEW* click = reinterpret_cast<const NMLISTVIEW*>(header);
    if (click->iSubItem == m_sortColumn) m_sortAscending = !m_sortAscending;
    else { m_sortColumn = click->iSubItem; m_sortAscending = click->iSubItem == 0 || click->iSubItem == 1; }
    PopulateUsers(); SaveViewState(); *result = 0;
}

void CKnownUsersWnd::OnModeChanged(NMHDR*, LRESULT* result)
{
    int selected = m_modes.GetCurSel();
    if (selected >= 0 && selected < ENKUM_COUNT) m_mode = static_cast<EmuleNextKnownUsersMode>(selected);
    SaveViewState(); RefreshUsers(); *result = 0;
}

void CKnownUsersWnd::OnSearchChanged()
{
    CString value; m_search.GetWindowText(value); m_searchText = value; SaveViewState(); RefreshUsers();
}

void CKnownUsersWnd::OnRefreshClicked()
{
    Refresh(true);
}

void CKnownUsersWnd::OnRefreshPeerClicked()
{
    EmuleNextHash16 hash;
    if (!SelectedHash(hash) || theApp.clientlist == NULL) return;
    if (theApp.clientlist->QueuePeerShareRefresh(hash))
        m_status.SetWindowText(_T("Selected peer queued for a safe shared-file refresh."));
    else
        m_status.SetWindowText(_T("Peer refresh not queued: offline, unsupported, active, or still in cooldown."));
    PopulateUsers(); UpdateActionButtons();
}

void CKnownUsersWnd::OnFavoriteClicked()
{
    const int index = SelectedUserIndex();
    if (index < 0) return;
    EmuleNextKnownUserRecord& user = m_userRows[static_cast<size_t>(index)];
    if (theEmuleNext.SetPeerFavorite(user.userHash.bytes.data(), !user.favorite)) {
        user.favorite = !user.favorite; PopulateUsers(); UpdateActionButtons();
    }
}

void CKnownUsersWnd::OnAliasClicked()
{
    const int index = SelectedUserIndex();
    if (index < 0) return;
    EmuleNextKnownUserRecord& user = m_userRows[static_cast<size_t>(index)];
    InputBox input(this);
    CString label; label.Format(_T("Local alias for %s:"), user.userName.IsEmpty() ? _T("peer") : CString(user.userName).GetString());
    input.SetLabels(_T("eMule Next peer alias"), label, CString(user.alias));
    if (input.DoModal() != IDOK || input.WasCancelled()) return;
    CString alias(input.GetInput()); alias.Trim(); if (alias.GetLength() > 128) alias = alias.Left(128);
    if (theEmuleNext.SetPeerAlias(user.userHash.bytes.data(), alias)) { user.alias = CStringW(alias); PopulateUsers(); }
}

void CKnownUsersWnd::OnDeleteHistoryClicked()
{
    if (m_deleteLoading || !theEmuleNext.IsRunning()) return;
    EmuleNextHash16 hash; if (!SelectedHash(hash)) return;
    if (AfxMessageBox(_T("Delete the local intelligence history for this peer? Alias/favorite metadata is kept."),
            MB_YESNO | MB_ICONQUESTION) != IDYES) return;
    const CStringW path = theEmuleNext.Database().GetDatabasePath(); if (path.IsEmpty()) return;
    std::unique_ptr<DeleteLoadContext> context(new DeleteLoadContext);
    context->target = m_hWnd; context->databasePath = path; context->peerHash = hash; m_deleteLoading = true;
    if (AfxBeginThread(DeleteHistoryWorker, context.get(), THREAD_PRIORITY_BELOW_NORMAL) == NULL) { m_deleteLoading = false; return; }
    context.release(); m_status.SetWindowText(_T("Deleting selected peer history in the background...")); UpdateActionButtons();
}

void CKnownUsersWnd::OnDarkModeClicked()
{
    CEmuleNextTheme::SetDarkMode(m_darkModeButton.GetCheck() == BST_CHECKED);
    CEmuleNextTheme::ApplyToWindow(theApp.emuledlg != NULL ? theApp.emuledlg->GetSafeHwnd() : m_hWnd); Invalidate(TRUE);
}

void CKnownUsersWnd::UpdateActionButtons()
{
    const int index = SelectedUserIndex(); const bool have = index >= 0; bool current = false;
    if (have) current = IsCurrent(m_userRows[static_cast<size_t>(index)]);
    m_refreshPeerButton.EnableWindow(have && current && !m_deleteLoading);
    m_favoriteButton.EnableWindow(have && !m_deleteLoading);
    m_aliasButton.EnableWindow(have && !m_deleteLoading);
    m_deleteHistoryButton.EnableWindow(have && !m_deleteLoading);
    if (have) m_favoriteButton.SetWindowText(m_userRows[static_cast<size_t>(index)].favorite ? _T("Unfavorite") : _T("Favorite"));
    else m_favoriteButton.SetWindowText(_T("Favorite"));
}

void CKnownUsersWnd::LoadViewState()
{
    int mode = theApp.GetProfileInt(PROFILE_SECTION, _T("Mode"), ENKUM_CURRENT);
    if (mode < 0 || mode >= ENKUM_COUNT) mode = ENKUM_CURRENT;
    m_mode = static_cast<EmuleNextKnownUsersMode>(mode);
    m_sortColumn = theApp.GetProfileInt(PROFILE_SECTION, _T("SortColumn"), 7);
    if (m_sortColumn < 0 || m_sortColumn >= USER_COLUMN_COUNT) m_sortColumn = 7;
    m_sortAscending = theApp.GetProfileInt(PROFILE_SECTION, _T("SortAscending"), 0) != 0;
    m_searchText = theApp.GetProfileString(PROFILE_SECTION, _T("Search"), _T("")); m_search.SetWindowText(m_searchText);
}

void CKnownUsersWnd::SaveViewState() const
{
    theApp.WriteProfileInt(PROFILE_SECTION, _T("Mode"), static_cast<int>(m_mode));
    theApp.WriteProfileInt(PROFILE_SECTION, _T("SortColumn"), m_sortColumn);
    theApp.WriteProfileInt(PROFILE_SECTION, _T("SortAscending"), m_sortAscending ? 1 : 0);
    CString search; if (::IsWindow(m_search.m_hWnd)) m_search.GetWindowText(search); else search = m_searchText;
    theApp.WriteProfileString(PROFILE_SECTION, _T("Search"), search);
    if (::IsWindow(m_users.m_hWnd)) for (int i = 0; i < USER_COLUMN_COUNT; ++i) {
        CString key; key.Format(_T("ColumnWidth%d"), i); theApp.WriteProfileInt(PROFILE_SECTION, key, m_users.GetColumnWidth(i));
    }
}

void CKnownUsersWnd::ApplyUserColumnWidths()
{
    if (!::IsWindow(m_users.m_hWnd)) return;
    for (int i = 0; i < USER_COLUMN_COUNT; ++i) {
        CString key; key.Format(_T("ColumnWidth%d"), i);
        const int stored = theApp.GetProfileInt(PROFILE_SECTION, key, 0);
        if (stored >= CEmuleNextUiMetrics::Scale(m_hWnd, 36) && stored <= CEmuleNextUiMetrics::Scale(m_hWnd, 700))
            m_users.SetColumnWidth(i, stored);
    }
}

LRESULT CKnownUsersWnd::OnUsersLoaded(WPARAM, LPARAM value)
{
    std::unique_ptr<UsersLoadResult> result(reinterpret_cast<UsersLoadResult*>(value)); m_usersLoading = false;
    if (result.get() == NULL || !result->ok) { m_status.SetWindowText(_T("Known Users database could not be read.")); return 0; }
    EmuleNextHash16 previous; const bool hadSelection = SelectedHash(previous); m_userRows.swap(result->rows); PopulateUsers();
    int selectRow = -1;
    if (hadSelection) for (int row = 0; row < m_users.GetItemCount(); ++row) {
        const DWORD_PTR index = m_users.GetItemData(row);
        if (index < m_userRows.size() && m_userRows[index].userHash.valid && m_userRows[index].userHash.bytes == previous.bytes) { selectRow = row; break; }
    }
    if (selectRow < 0 && m_users.GetItemCount() > 0) selectRow = 0;
    if (selectRow >= 0) { m_users.SetItemState(selectRow, LVIS_SELECTED | LVIS_FOCUSED, LVIS_SELECTED | LVIS_FOCUSED); m_users.EnsureVisible(selectRow, FALSE); }
    CString status; status.Format(_T("%u database peers; %u shown in %s mode. Background reads are bounded."),
        static_cast<unsigned>(m_userRows.size()), static_cast<unsigned>(m_users.GetItemCount()),
        m_mode == ENKUM_CURRENT ? _T("Current") : m_mode == ENKUM_HISTORY ? _T("History") : m_mode == ENKUM_FAVORITES ? _T("Favorites") : _T("Recent"));
    m_status.SetWindowText(status); UpdateActionButtons(); return 0;
}

LRESULT CKnownUsersWnd::OnFilesLoaded(WPARAM, LPARAM value)
{
    std::unique_ptr<FilesLoadResult> result(reinterpret_cast<FilesLoadResult*>(value)); m_filesLoading = false;
    if (result.get() == NULL || !result->ok) return 0;
    EmuleNextHash16 selected; if (!SelectedHash(selected) || !selected.valid || selected.bytes != result->peerHash.bytes) return 0;
    m_fileRowsPeer = result->peerHash; m_fileRows.swap(result->rows); PopulateFiles(); return 0;
}

LRESULT CKnownUsersWnd::OnHistoryDeleted(WPARAM, LPARAM value)
{
    std::unique_ptr<DeleteLoadResult> result(reinterpret_cast<DeleteLoadResult*>(value)); m_deleteLoading = false;
    m_status.SetWindowText(result.get() != NULL && result->ok ? _T("Selected peer history deleted; metadata retained.") : _T("Peer history delete failed."));
    Refresh(true); UpdateActionButtons(); return 0;
}
