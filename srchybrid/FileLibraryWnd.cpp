//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later

#include "stdafx.h"
#include "FileLibraryWnd.h"
#include "EmuleNextRuntime.h"
#include "EmuleNextTheme.h"
#include "OtherFunctions.h"
#include "emule.h"

#include <memory>

namespace
{
    enum
    {
        IDC_EN_LIBRARY_FILTER = 0x7E60,
        IDC_EN_LIBRARY_REFRESH,
        IDC_EN_LIBRARY_RESULTS,
        IDC_EN_LIBRARY_FAVORITE,
        IDC_EN_LIBRARY_LATER,
        IDC_EN_LIBRARY_LOCATION,
        IDC_EN_LIBRARY_TEXT_FILTER
    };

    const UINT WM_EN_LIBRARY_LOADED = WM_APP + 0x571;

    struct LibraryContext
    {
        HWND target;
        CStringW databasePath;
        EmuleNextLibraryViewFilter filter;
    };

    struct LibraryResult
    {
        bool ok;
        std::vector<EmuleNextLibraryBrowseRow> rows;
        LibraryResult() : ok(false) {}
    };

    UINT AFX_CDECL LibraryWorker(LPVOID value)
    {
        std::unique_ptr<LibraryContext> context(static_cast<LibraryContext*>(value));
        std::unique_ptr<LibraryResult> result(new LibraryResult);
        CLibraryBrowserService service(context->databasePath);
        result->ok = service.List(context->filter, result->rows, 5000);
        if (::IsWindow(context->target)
            && ::PostMessage(context->target, WM_EN_LIBRARY_LOADED, 0, reinterpret_cast<LPARAM>(result.get()))) {
            result.release();
        }
        return 0;
    }
}

BEGIN_MESSAGE_MAP(CFileLibraryWnd, CWnd)
    ON_WM_CREATE()
    ON_WM_SIZE()
    ON_WM_ERASEBKGND()
    ON_WM_CTLCOLOR()
    ON_BN_CLICKED(IDC_EN_LIBRARY_REFRESH, OnRefreshClicked)
    ON_CBN_SELCHANGE(IDC_EN_LIBRARY_FILTER, OnFilterChanged)
    ON_EN_CHANGE(IDC_EN_LIBRARY_TEXT_FILTER, OnTextFilterChanged)
    ON_BN_CLICKED(IDC_EN_LIBRARY_FAVORITE, OnFavoriteClicked)
    ON_BN_CLICKED(IDC_EN_LIBRARY_LATER, OnDownloadLaterClicked)
    ON_BN_CLICKED(IDC_EN_LIBRARY_LOCATION, OnOpenLocationClicked)
    ON_NOTIFY(LVN_ITEMCHANGED, IDC_EN_LIBRARY_RESULTS, OnSelectionChanged)
    ON_MESSAGE(WM_EN_LIBRARY_LOADED, OnLibraryLoaded)
END_MESSAGE_MAP()

CFileLibraryWnd::CFileLibraryWnd()
    : m_loading(false)
{
}

CFileLibraryWnd::~CFileLibraryWnd()
{
}

bool CFileLibraryWnd::Create(CWnd* parent)
{
    if (parent == NULL)
        return false;
    const CString className = AfxRegisterWndClass(CS_DBLCLKS, ::LoadCursor(NULL, IDC_ARROW),
        reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1), NULL);
    CRect empty(0, 0, 0, 0);
    return CWnd::CreateEx(0, className, _T("eMule Next File Library"),
        WS_CHILD | WS_CLIPCHILDREN | WS_CLIPSIBLINGS, empty, parent, 0) != FALSE;
}

int CFileLibraryWnd::OnCreate(LPCREATESTRUCT createStruct)
{
    if (CWnd::OnCreate(createStruct) == -1)
        return -1;

    m_darkBrush.CreateSolidBrush(CEmuleNextTheme::BackgroundColor());
    CRect empty(0, 0, 0, 0);
    if (!m_title.Create(_T("Library"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_subtitle.Create(_T("Persistent file history, favorites, missing items and Download Later."),
            WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_viewLabel.Create(_T("View"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_filter.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST,
            empty, this, IDC_EN_LIBRARY_FILTER)
        || !m_findLabel.Create(_T("Find"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_textFilter.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | WS_BORDER | ES_AUTOHSCROLL,
            empty, this, IDC_EN_LIBRARY_TEXT_FILTER)
        || !m_refresh.Create(_T("Refresh"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_LIBRARY_REFRESH)
        || !m_status.Create(_T("Ready."), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_results.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS,
            empty, this, IDC_EN_LIBRARY_RESULTS)
        || !m_favorite.Create(_T("Add favorite"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_LIBRARY_FAVORITE)
        || !m_downloadLater.Create(_T("Download later"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_LIBRARY_LATER)
        || !m_openLocation.Create(_T("Open location"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_LIBRARY_LOCATION)) {
        return -1;
    }

    CFont* font = CFont::FromHandle(static_cast<HFONT>(::GetStockObject(DEFAULT_GUI_FONT)));
    m_title.SetFont(font); m_subtitle.SetFont(font); m_viewLabel.SetFont(font); m_filter.SetFont(font);
    m_findLabel.SetFont(font); m_textFilter.SetFont(font); m_refresh.SetFont(font); m_status.SetFont(font);
    m_results.SetFont(font); m_favorite.SetFont(font); m_downloadLater.SetFont(font); m_openLocation.SetFont(font);

    m_filter.AddString(_T("History"));
    m_filter.AddString(_T("Favorites"));
    m_filter.AddString(_T("Completed"));
    m_filter.AddString(_T("Missing"));
    m_filter.AddString(_T("Download Later"));
    m_filter.SetCurSel(0);

    m_results.SetExtendedStyle(LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_GRIDLINES);
    m_results.InsertColumn(0, _T("File"), LVCFMT_LEFT, 340);
    m_results.InsertColumn(1, _T("Size"), LVCFMT_RIGHT, 95);
    m_results.InsertColumn(2, _T("State"), LVCFMT_LEFT, 105);
    m_results.InsertColumn(3, _T("Last seen"), LVCFMT_LEFT, 135);
    m_results.InsertColumn(4, _T("Local path"), LVCFMT_LEFT, 300);
    m_results.InsertColumn(5, _T("ED2K hash"), LVCFMT_LEFT, 245);

    UpdateActions();
    CEmuleNextTheme::ApplyToWindow(m_hWnd);
    return 0;
}

void CFileLibraryWnd::Refresh(bool force)
{
    if (force || IsWindowVisible())
        StartLoad();
}

void CFileLibraryWnd::OnSize(UINT type, int cx, int cy)
{
    CWnd::OnSize(type, cx, cy);
    if (::IsWindow(m_filter.m_hWnd))
        LayoutControls(cx, cy);
}

void CFileLibraryWnd::LayoutControls(int cx, int cy)
{
    const int margin = 12;
    const int titleTop = 10;
    const int controlsTop = 58;
    const int statusTop = 91;
    const int listTop = 115;
    const int actionHeight = 30;
    const int actionTop = max(listTop + 70, cy - margin - actionHeight);

    m_title.MoveWindow(margin, titleTop, max(160, cx - margin * 2), 22);
    m_subtitle.MoveWindow(margin, titleTop + 24, max(160, cx - margin * 2), 18);

    m_viewLabel.MoveWindow(margin, controlsTop + 5, 34, 18);
    m_filter.MoveWindow(margin + 38, controlsTop, 160, 240);
    m_findLabel.MoveWindow(margin + 212, controlsTop + 5, 30, 18);
    m_textFilter.MoveWindow(margin + 246, controlsTop, max(120, cx - (margin + 246) - 108), 25);
    m_refresh.MoveWindow(max(margin, cx - margin - 92), controlsTop, 92, 25);

    m_status.MoveWindow(margin, statusTop, max(100, cx - margin * 2), 18);
    m_results.MoveWindow(margin, listTop, max(0, cx - margin * 2),
        max(60, actionTop - listTop - 8));
    m_favorite.MoveWindow(margin, actionTop, 108, actionHeight);
    m_downloadLater.MoveWindow(margin + 116, actionTop, 112, actionHeight);
    m_openLocation.MoveWindow(margin + 236, actionTop, 108, actionHeight);
}

BOOL CFileLibraryWnd::OnEraseBkgnd(CDC* dc)
{
    if (!CEmuleNextTheme::IsDarkMode())
        return CWnd::OnEraseBkgnd(dc);
    CRect rect; GetClientRect(&rect);
    dc->FillSolidRect(rect, CEmuleNextTheme::BackgroundColor());
    return TRUE;
}

HBRUSH CFileLibraryWnd::OnCtlColor(CDC* dc, CWnd* wnd, UINT ctlColor)
{
    if (!CEmuleNextTheme::IsDarkMode())
        return CWnd::OnCtlColor(dc, wnd, ctlColor);
    dc->SetTextColor(CEmuleNextTheme::TextColor());
    dc->SetBkColor(CEmuleNextTheme::BackgroundColor());
    if (ctlColor == CTLCOLOR_STATIC || ctlColor == CTLCOLOR_DLG)
        return static_cast<HBRUSH>(m_darkBrush.GetSafeHandle());
    return CWnd::OnCtlColor(dc, wnd, ctlColor);
}

void CFileLibraryWnd::OnRefreshClicked()
{
    StartLoad();
}

void CFileLibraryWnd::OnFilterChanged()
{
    StartLoad();
}

void CFileLibraryWnd::OnTextFilterChanged()
{
    if (!m_loading)
        PopulateRows();
}

void CFileLibraryWnd::StartLoad()
{
    if (m_loading || !theEmuleNext.IsRunning())
        return;
    int selected = m_filter.GetCurSel();
    if (selected < ENLV_HISTORY || selected > ENLV_DOWNLOAD_LATER)
        selected = ENLV_HISTORY;

    std::unique_ptr<LibraryContext> context(new LibraryContext);
    context->target = m_hWnd;
    context->databasePath = theEmuleNext.Database().GetDatabasePath();
    context->filter = static_cast<EmuleNextLibraryViewFilter>(selected);
    m_loading = true;
    m_refresh.EnableWindow(FALSE);
    m_status.SetWindowText(_T("Loading Library in the background..."));
    if (AfxBeginThread(LibraryWorker, context.get(), THREAD_PRIORITY_BELOW_NORMAL) == NULL) {
        m_loading = false;
        m_refresh.EnableWindow(TRUE);
        m_status.SetWindowText(_T("Unable to start Library refresh."));
        return;
    }
    context.release();
}

LRESULT CFileLibraryWnd::OnLibraryLoaded(WPARAM, LPARAM value)
{
    std::unique_ptr<LibraryResult> result(reinterpret_cast<LibraryResult*>(value));
    m_loading = false;
    m_refresh.EnableWindow(TRUE);
    if (result.get() == NULL || !result->ok) {
        m_status.SetWindowText(_T("Library could not be read."));
        return 0;
    }
    m_rows.swap(result->rows);
    PopulateRows();
    return 0;
}

void CFileLibraryWnd::PopulateRows()
{
    CString needle;
    if (::IsWindow(m_textFilter.m_hWnd))
        m_textFilter.GetWindowText(needle);
    needle.Trim();
    needle.MakeLower();

    m_results.SetRedraw(FALSE);
    m_results.DeleteAllItems();
    unsigned displayed = 0;
    for (size_t i = 0; i < m_rows.size(); ++i) {
        const EmuleNextLibraryBrowseRow& file = m_rows[i];
        CString name(file.fileName);
        if (name.IsEmpty())
            name = _T("<unnamed>");

        if (!needle.IsEmpty()) {
            CString haystack(name);
            if (!file.localPath.IsEmpty()) {
                haystack += _T(" ");
                haystack += CString(file.localPath);
            }
            haystack.MakeLower();
            if (haystack.Find(needle) < 0)
                continue;
        }

        const int row = m_results.InsertItem(static_cast<int>(displayed), name);
        m_results.SetItemData(row, static_cast<DWORD_PTR>(i));
        m_results.SetItemText(row, 1, CastItoXBytes(file.fileSize, false, false, 1));
        CString state;
        if (file.missing) state = _T("Missing");
        else if (file.completed) state = _T("Completed");
        else if (file.downloadLater) state = _T("Download later");
        else if (file.favorite) state = _T("Favorite");
        else state = _T("History");
        m_results.SetItemText(row, 2, state);
        m_results.SetItemText(row, 3, DateText(file.lastSeen));
        m_results.SetItemText(row, 4, CString(file.localPath));
        m_results.SetItemText(row, 5, HashText(file.fileHash));
        ++displayed;
    }
    m_results.SetRedraw(TRUE);
    m_results.Invalidate(FALSE);
    UpdateActions();

    CString status;
    if (needle.IsEmpty())
        status.Format(_T("%u files in this Library view."), static_cast<unsigned>(m_rows.size()));
    else
        status.Format(_T("%u of %u files match the filter."), displayed, static_cast<unsigned>(m_rows.size()));
    m_status.SetWindowText(status);
}

int CFileLibraryWnd::SelectedIndex() const
{
    const int selected = m_results.GetNextItem(-1, LVNI_SELECTED);
    if (selected < 0)
        return -1;
    const DWORD_PTR value = m_results.GetItemData(selected);
    return value < m_rows.size() ? static_cast<int>(value) : -1;
}

void CFileLibraryWnd::UpdateActions()
{
    const int index = SelectedIndex();
    const BOOL enabled = index >= 0 ? TRUE : FALSE;
    m_favorite.EnableWindow(enabled);
    m_downloadLater.EnableWindow(enabled);
    m_openLocation.EnableWindow(enabled && !m_rows[static_cast<size_t>(index)].localPath.IsEmpty());
    if (index >= 0)
        m_favorite.SetWindowText(m_rows[static_cast<size_t>(index)].favorite ? _T("Remove favorite") : _T("Add favorite"));
    else
        m_favorite.SetWindowText(_T("Add favorite"));
}

void CFileLibraryWnd::OnSelectionChanged(NMHDR*, LRESULT* result)
{
    UpdateActions();
    *result = 0;
}

void CFileLibraryWnd::OnFavoriteClicked()
{
    const int index = SelectedIndex();
    if (index < 0) return;
    EmuleNextLibraryBrowseRow& row = m_rows[static_cast<size_t>(index)];
    if (row.favorite) {
        theEmuleNext.Database().RemoveFavorite(row.fileHash, row.fileSize);
        row.favorite = false;
    }
    else {
        EmuleNextFavoriteRecord favorite;
        favorite.fileHash = row.fileHash;
        favorite.fileSize = row.fileSize;
        favorite.fileName = row.fileName;
        favorite.aichHash = row.aichHash;
        favorite.localPath = row.localPath;
        theEmuleNext.Database().SaveFavorite(favorite);
        row.favorite = true;
    }
    PopulateRows();
}

void CFileLibraryWnd::OnDownloadLaterClicked()
{
    const int index = SelectedIndex();
    if (index < 0) return;
    EmuleNextLibraryBrowseRow& row = m_rows[static_cast<size_t>(index)];
    EmuleNextFileObservation file;
    file.ed2kHash = row.fileHash;
    file.fileSize = row.fileSize;
    file.fileName = row.fileName;
    file.aichHash = row.aichHash;
    theEmuleNext.Database().SaveDownloadLater(file);
    row.downloadLater = true;
    PopulateRows();
    m_status.SetWindowText(_T("Added to Download Later."));
}

void CFileLibraryWnd::OnOpenLocationClicked()
{
    const int index = SelectedIndex();
    if (index < 0) return;
    const CString path(m_rows[static_cast<size_t>(index)].localPath);
    if (path.IsEmpty()) return;
    CString arguments;
    arguments.Format(_T("/select,\"%s\""), static_cast<LPCTSTR>(path));
    ::ShellExecute(m_hWnd, _T("open"), _T("explorer.exe"), arguments, NULL, SW_SHOWNORMAL);
}

CString CFileLibraryWnd::HashText(const EmuleNextHash16& hash)
{
    CString result;
    if (!hash.valid) return result;
    for (size_t i = 0; i < hash.bytes.size(); ++i) {
        CString pair; pair.Format(_T("%02X"), static_cast<unsigned>(hash.bytes[i]));
        result += pair;
    }
    return result;
}

CString CFileLibraryWnd::DateText(uint64 timestamp)
{
    if (timestamp == 0) return CString();
    CTime value(static_cast<time_t>(timestamp));
    return value.Format(_T("%Y-%m-%d %H:%M"));
}
