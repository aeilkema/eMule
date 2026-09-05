//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later

#include "stdafx.h"
#include "KnownUsersWnd.h"

#include "ClientList.h"
#include "EmuleNextRuntime.h"
#include "EmuleNextTheme.h"
#include "OtherFunctions.h"
#include "emule.h"

#include <memory>

namespace
{
    enum
    {
        IDC_EN_REFRESH = 0x7E10,
        IDC_EN_DARKMODE,
        IDC_EN_STATUS,
        IDC_EN_USERS,
        IDC_EN_FILES
    };

    const UINT WM_EN_USERS_LOADED = WM_APP + 0x561;
    const UINT WM_EN_FILES_LOADED = WM_APP + 0x562;
    const UINT_PTR TIMER_EN_REFRESH = 0x561;

    struct UsersLoadContext
    {
        HWND target;
        CStringW databasePath;
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

    UINT AFX_CDECL LoadUsersWorker(LPVOID value)
    {
        std::unique_ptr<UsersLoadContext> context(static_cast<UsersLoadContext*>(value));
        std::unique_ptr<UsersLoadResult> result(new UsersLoadResult);
        CKnownUsersService service(context->databasePath);
        result->ok = service.ListUsers(result->rows);
        if (::IsWindow(context->target)
            && ::PostMessage(context->target, WM_EN_USERS_LOADED, 0, reinterpret_cast<LPARAM>(result.get()))) {
            result.release();
        }
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
            && ::PostMessage(context->target, WM_EN_FILES_LOADED, 0, reinterpret_cast<LPARAM>(result.get()))) {
            result.release();
        }
        return 0;
    }

    bool SameHash(const EmuleNextHash16& left, const EmuleNextHash16& right)
    {
        return left.valid && right.valid && left.bytes == right.bytes;
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
    ON_BN_CLICKED(IDC_EN_REFRESH, OnRefreshClicked)
    ON_BN_CLICKED(IDC_EN_DARKMODE, OnDarkModeClicked)
    ON_MESSAGE(WM_EN_USERS_LOADED, OnUsersLoaded)
    ON_MESSAGE(WM_EN_FILES_LOADED, OnFilesLoaded)
END_MESSAGE_MAP()

CKnownUsersWnd::CKnownUsersWnd()
    : m_usersLoading(false)
    , m_filesLoading(false)
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
        ::LoadCursor(NULL, IDC_ARROW),
        reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1), NULL);
    CRect empty(0, 0, 0, 0);
    return CWnd::CreateEx(0, className, _T("eMule Next Known Users"),
        WS_CHILD | WS_CLIPCHILDREN | WS_CLIPSIBLINGS,
        empty, parent, 0) != FALSE;
}

int CKnownUsersWnd::OnCreate(LPCREATESTRUCT createStruct)
{
    if (CWnd::OnCreate(createStruct) == -1)
        return -1;

    m_darkBrush.CreateSolidBrush(CEmuleNextTheme::BackgroundColor());

    CRect empty(0, 0, 0, 0);
    if (!m_refreshButton.Create(_T("Refresh"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_REFRESH)
        || !m_darkModeButton.Create(_T("Dark mode"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX,
            empty, this, IDC_EN_DARKMODE)
        || !m_status.Create(_T("Known users are loaded in the background..."), WS_CHILD | WS_VISIBLE | SS_LEFT,
            empty, this, IDC_EN_STATUS)
        || !m_users.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS,
            empty, this, IDC_EN_USERS)
        || !m_files.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS,
            empty, this, IDC_EN_FILES)) {
        return -1;
    }

    CFont* font = CFont::FromHandle(static_cast<HFONT>(::GetStockObject(DEFAULT_GUI_FONT)));
    m_refreshButton.SetFont(font);
    m_darkModeButton.SetFont(font);
    m_status.SetFont(font);
    m_users.SetFont(font);
    m_files.SetFont(font);
    m_darkModeButton.SetCheck(CEmuleNextTheme::IsDarkMode() ? BST_CHECKED : BST_UNCHECKED);

    m_users.SetExtendedStyle(LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_GRIDLINES);
    m_files.SetExtendedStyle(LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_GRIDLINES);

    m_users.InsertColumn(0, _T("User"), LVCFMT_LEFT, 190);
    m_users.InsertColumn(1, _T("Session"), LVCFMT_LEFT, 80);
    m_users.InsertColumn(2, _T("Last seen"), LVCFMT_LEFT, 135);
    m_users.InsertColumn(3, _T("Files"), LVCFMT_RIGHT, 70);
    m_users.InsertColumn(4, _T("Shared size"), LVCFMT_RIGHT, 105);
    m_users.InsertColumn(5, _T("User hash"), LVCFMT_LEFT, 245);

    m_files.InsertColumn(0, _T("File"), LVCFMT_LEFT, 310);
    m_files.InsertColumn(1, _T("Size"), LVCFMT_RIGHT, 100);
    m_files.InsertColumn(2, _T("Last seen"), LVCFMT_LEFT, 135);
    m_files.InsertColumn(3, _T("ED2K hash"), LVCFMT_LEFT, 245);
    m_files.InsertColumn(4, _T("AICH"), LVCFMT_LEFT, 260);

    CEmuleNextTheme::ApplyToWindow(m_hWnd);
    m_refreshTimer = SetTimer(TIMER_EN_REFRESH, 10000, NULL);
    Refresh(true);
    return 0;
}

void CKnownUsersWnd::OnDestroy()
{
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
    const int margin = 8;
    const int refreshWidth = 84;
    const int darkWidth = 105;
    const int headerHeight = 25;
    const int gap = 8;
    const int statusLeft = margin + refreshWidth + 8 + darkWidth + 10;
    const int usableHeight = max(0, cy - margin * 2 - headerHeight - gap);
    const int userHeight = max(110, usableHeight * 42 / 100);
    const int fileTop = margin + headerHeight + userHeight + gap;
    const int fileHeight = max(0, cy - margin - fileTop);

    m_refreshButton.MoveWindow(margin, margin, refreshWidth, 23);
    m_darkModeButton.MoveWindow(margin + refreshWidth + 8, margin + 2, darkWidth, 21);
    m_status.MoveWindow(statusLeft, margin + 4, max(0, cx - margin - statusLeft), 20);
    m_users.MoveWindow(margin, margin + headerHeight,
        max(0, cx - margin * 2), userHeight);
    m_files.MoveWindow(margin, fileTop,
        max(0, cx - margin * 2), fileHeight);
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

    std::unique_ptr<UsersLoadContext> context(new UsersLoadContext);
    context->target = m_hWnd;
    context->databasePath = path;
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

void CKnownUsersWnd::PopulateUsers()
{
    m_users.SetRedraw(FALSE);
    m_users.DeleteAllItems();

    for (size_t i = 0; i < m_userRows.size(); ++i) {
        const EmuleNextKnownUserRecord& user = m_userRows[i];
        CString name(user.userName);
        if (name.IsEmpty())
            name = _T("<unknown user>");
        const int row = m_users.InsertItem(static_cast<int>(i), name);
        m_users.SetItemData(row, static_cast<DWORD_PTR>(i));

        CUpDownClient* current = theApp.clientlist != NULL
            ? theApp.clientlist->FindClientByUserHash(user.userHash.bytes.data()) : NULL;
        m_users.SetItemText(row, 1, current != NULL ? _T("Current") : _T("History"));
        m_users.SetItemText(row, 2, DateText(user.lastSeen));

        CString count;
        count.Format(_T("%u"), user.fileCount);
        m_users.SetItemText(row, 3, count);
        m_users.SetItemText(row, 4, CastItoXBytes(user.totalBytes, false, false, 1));
        m_users.SetItemText(row, 5, HashText(user.userHash));
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
        m_files.SetItemText(row, 1, CastItoXBytes(file.fileSize, false, false, 1));
        m_files.SetItemText(row, 2, DateText(file.lastSeen));
        m_files.SetItemText(row, 3, HashText(file.fileHash));
        m_files.SetItemText(row, 4, CString(file.aichHash));
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
    CTime time(static_cast<time_t>(timestamp));
    return time.Format(_T("%Y-%m-%d %H:%M"));
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
    if (ctlColor == CTLCOLOR_STATIC || ctlColor == CTLCOLOR_DLG)
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
    }
    *result = 0;
}

void CKnownUsersWnd::OnRefreshClicked()
{
    Refresh(true);
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
    m_userRows.swap(result->rows);
    PopulateUsers();

    int selectRow = -1;
    if (hadSelection) {
        for (size_t i = 0; i < m_userRows.size(); ++i) {
            if (SameHash(previous, m_userRows[i].userHash)) {
                selectRow = static_cast<int>(i);
                break;
            }
        }
    }
    if (selectRow < 0 && !m_userRows.empty())
        selectRow = 0;
    if (selectRow >= 0) {
        m_users.SetItemState(selectRow, LVIS_SELECTED | LVIS_FOCUSED, LVIS_SELECTED | LVIS_FOCUSED);
        m_users.EnsureVisible(selectRow, FALSE);
    }

    CString status;
    status.Format(_T("%u known users with shared files. Automatic scans update this view in the background."),
        static_cast<unsigned>(m_userRows.size()));
    m_status.SetWindowText(status);
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
    return 0;
}
