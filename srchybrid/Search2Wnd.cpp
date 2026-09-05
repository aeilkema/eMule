//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later

#include "stdafx.h"
#include "Search2Wnd.h"
#include "EmuleNextRuntime.h"
#include "EmuleNextTheme.h"
#include "OtherFunctions.h"
#include "emule.h"

#include <memory>

namespace
{
    enum
    {
        IDC_EN_SEARCH2_QUERY = 0x7E50,
        IDC_EN_SEARCH2_START,
        IDC_EN_SEARCH2_HIDE_DOWNLOADED,
        IDC_EN_SEARCH2_FAVORITES,
        IDC_EN_SEARCH2_MISSING,
        IDC_EN_SEARCH2_SAVED,
        IDC_EN_SEARCH2_SAVE,
        IDC_EN_SEARCH2_DELETE,
        IDC_EN_SEARCH2_RESULTS,
        IDC_EN_SEARCH2_FAVORITE,
        IDC_EN_SEARCH2_LATER,
        IDC_EN_SEARCH2_BLOCK
    };

    const UINT WM_EN_SEARCH2_LOADED = WM_APP + 0x570;

    struct SearchContext
    {
        HWND target;
        EmuleNextSearchRequest request;
        CString savedSearchName;
    };

    struct SearchResult
    {
        bool ok;
        std::vector<EmuleNextSearchFileResult> rows;
        SearchResult() : ok(false) {}
    };

    UINT AFX_CDECL SearchWorker(LPVOID value)
    {
        std::unique_ptr<SearchContext> context(static_cast<SearchContext*>(value));
        std::unique_ptr<SearchResult> result(new SearchResult);
        CSearch2Service service(theEmuleNext.Database());
        result->ok = service.SearchHistory(context->request, result->rows);
        if (result->ok && !context->savedSearchName.IsEmpty()) {
            uint64 newestSeen = 0;
            for (size_t i = 0; i < result->rows.size(); ++i) {
                if (result->rows[i].lastSeen > newestSeen)
                    newestSeen = result->rows[i].lastSeen;
            }
            service.MarkSearchRun(context->savedSearchName, newestSeen);
        }
        if (::IsWindow(context->target)
            && ::PostMessage(context->target, WM_EN_SEARCH2_LOADED, 0, reinterpret_cast<LPARAM>(result.get()))) {
            result.release();
        }
        return 0;
    }
}

BEGIN_MESSAGE_MAP(CSearch2Wnd, CWnd)
    ON_WM_CREATE()
    ON_WM_SIZE()
    ON_WM_ERASEBKGND()
    ON_WM_CTLCOLOR()
    ON_BN_CLICKED(IDC_EN_SEARCH2_START, OnSearchClicked)
    ON_CBN_SELCHANGE(IDC_EN_SEARCH2_SAVED, OnSavedSearchChanged)
    ON_BN_CLICKED(IDC_EN_SEARCH2_SAVE, OnSaveSearchClicked)
    ON_BN_CLICKED(IDC_EN_SEARCH2_DELETE, OnDeleteSearchClicked)
    ON_BN_CLICKED(IDC_EN_SEARCH2_FAVORITE, OnFavoriteClicked)
    ON_BN_CLICKED(IDC_EN_SEARCH2_LATER, OnDownloadLaterClicked)
    ON_BN_CLICKED(IDC_EN_SEARCH2_BLOCK, OnBlockClicked)
    ON_NOTIFY(LVN_ITEMCHANGED, IDC_EN_SEARCH2_RESULTS, OnResultSelectionChanged)
    ON_MESSAGE(WM_EN_SEARCH2_LOADED, OnSearchLoaded)
END_MESSAGE_MAP()

CSearch2Wnd::CSearch2Wnd()
    : m_loading(false)
{
}

CSearch2Wnd::~CSearch2Wnd()
{
}

bool CSearch2Wnd::Create(CWnd* parent)
{
    if (parent == NULL)
        return false;
    const CString className = AfxRegisterWndClass(CS_DBLCLKS, ::LoadCursor(NULL, IDC_ARROW),
        reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1), NULL);
    CRect empty(0, 0, 0, 0);
    return CWnd::CreateEx(0, className, _T("eMule Next Search 2"),
        WS_CHILD | WS_CLIPCHILDREN | WS_CLIPSIBLINGS, empty, parent, 0) != FALSE;
}

int CSearch2Wnd::OnCreate(LPCREATESTRUCT createStruct)
{
    if (CWnd::OnCreate(createStruct) == -1)
        return -1;

    m_darkBrush.CreateSolidBrush(CEmuleNextTheme::BackgroundColor());
    CRect empty(0, 0, 0, 0);
    if (!m_title.Create(_T("Search"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_subtitle.Create(_T("Search current and historical file knowledge collected by eMule Next."),
            WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_query.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | WS_BORDER | ES_AUTOHSCROLL,
            empty, this, IDC_EN_SEARCH2_QUERY)
        || !m_search.Create(_T("Search"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_SEARCH2_START)
        || !m_hideDownloaded.Create(_T("Hide downloaded"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX,
            empty, this, IDC_EN_SEARCH2_HIDE_DOWNLOADED)
        || !m_favoritesOnly.Create(_T("Favorites only"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX,
            empty, this, IDC_EN_SEARCH2_FAVORITES)
        || !m_missingOnly.Create(_T("Missing only"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX,
            empty, this, IDC_EN_SEARCH2_MISSING)
        || !m_savedSearchLabel.Create(_T("Saved search"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_savedSearch.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | WS_VSCROLL | CBS_DROPDOWN | CBS_AUTOHSCROLL,
            empty, this, IDC_EN_SEARCH2_SAVED)
        || !m_saveSearch.Create(_T("Save"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_SEARCH2_SAVE)
        || !m_deleteSearch.Create(_T("Delete"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_SEARCH2_DELETE)
        || !m_status.Create(_T("Ready."), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_results.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS,
            empty, this, IDC_EN_SEARCH2_RESULTS)
        || !m_favorite.Create(_T("Add favorite"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_SEARCH2_FAVORITE)
        || !m_downloadLater.Create(_T("Download later"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_SEARCH2_LATER)
        || !m_block.Create(_T("Block hash"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_SEARCH2_BLOCK)) {
        return -1;
    }

    CFont* font = CFont::FromHandle(static_cast<HFONT>(::GetStockObject(DEFAULT_GUI_FONT)));
    m_title.SetFont(font); m_subtitle.SetFont(font); m_query.SetFont(font); m_search.SetFont(font);
    m_hideDownloaded.SetFont(font); m_favoritesOnly.SetFont(font); m_missingOnly.SetFont(font);
    m_savedSearchLabel.SetFont(font); m_savedSearch.SetFont(font); m_saveSearch.SetFont(font);
    m_deleteSearch.SetFont(font); m_status.SetFont(font); m_results.SetFont(font);
    m_favorite.SetFont(font); m_downloadLater.SetFont(font); m_block.SetFont(font);

    m_results.SetExtendedStyle(LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_GRIDLINES);
    m_results.InsertColumn(0, _T("File"), LVCFMT_LEFT, 360);
    m_results.InsertColumn(1, _T("Size"), LVCFMT_RIGHT, 95);
    m_results.InsertColumn(2, _T("Peers"), LVCFMT_RIGHT, 60);
    m_results.InsertColumn(3, _T("Last seen"), LVCFMT_LEFT, 135);
    m_results.InsertColumn(4, _T("Favorite"), LVCFMT_LEFT, 70);
    m_results.InsertColumn(5, _T("Downloaded"), LVCFMT_LEFT, 80);
    m_results.InsertColumn(6, _T("ED2K hash"), LVCFMT_LEFT, 245);

    m_query.SetWindowText(_T(""));
    ReloadSavedSearches();
    UpdateActionButtons();
    CEmuleNextTheme::ApplyToWindow(m_hWnd);
    return 0;
}

void CSearch2Wnd::Refresh(bool force)
{
    if (force || IsWindowVisible()) {
        ReloadSavedSearches();
        StartSearch();
    }
}

void CSearch2Wnd::OnSize(UINT type, int cx, int cy)
{
    CWnd::OnSize(type, cx, cy);
    if (::IsWindow(m_query.m_hWnd))
        LayoutControls(cx, cy);
}

void CSearch2Wnd::LayoutControls(int cx, int cy)
{
    const int margin = 12;
    const int titleTop = 10;
    const int queryTop = 58;
    const int queryHeight = 26;
    const int filterTop = 92;
    const int statusTop = 121;
    const int listTop = 145;
    const int searchWidth = 104;
    const int actionHeight = 30;
    const int actionTop = max(listTop + 70, cy - margin - actionHeight);
    const int listHeight = max(60, actionTop - listTop - 8);

    m_title.MoveWindow(margin, titleTop, max(160, cx - margin * 2), 22);
    m_subtitle.MoveWindow(margin, titleTop + 24, max(160, cx - margin * 2), 18);

    m_search.MoveWindow(max(margin, cx - margin - searchWidth), queryTop, searchWidth, queryHeight);
    m_query.MoveWindow(margin, queryTop, max(120, cx - margin * 3 - searchWidth), queryHeight);

    m_hideDownloaded.MoveWindow(margin, filterTop + 2, 124, 20);
    m_favoritesOnly.MoveWindow(margin + 132, filterTop + 2, 108, 20);
    m_missingOnly.MoveWindow(margin + 248, filterTop + 2, 100, 20);

    const int savedLeft = max(margin + 355, cx - margin - 380);
    m_savedSearchLabel.MoveWindow(savedLeft, filterTop + 4, 82, 18);
    m_savedSearch.MoveWindow(savedLeft + 84, filterTop, 170, 220);
    m_saveSearch.MoveWindow(savedLeft + 260, filterTop, 54, 24);
    m_deleteSearch.MoveWindow(savedLeft + 320, filterTop, 58, 24);

    m_status.MoveWindow(margin, statusTop, max(100, cx - margin * 2), 18);
    m_results.MoveWindow(margin, listTop, max(0, cx - margin * 2), listHeight);
    m_favorite.MoveWindow(margin, actionTop, 108, actionHeight);
    m_downloadLater.MoveWindow(margin + 116, actionTop, 112, actionHeight);
    m_block.MoveWindow(margin + 236, actionTop, 96, actionHeight);
}

BOOL CSearch2Wnd::OnEraseBkgnd(CDC* dc)
{
    if (!CEmuleNextTheme::IsDarkMode())
        return CWnd::OnEraseBkgnd(dc);
    CRect rect; GetClientRect(&rect);
    dc->FillSolidRect(rect, CEmuleNextTheme::BackgroundColor());
    return TRUE;
}

HBRUSH CSearch2Wnd::OnCtlColor(CDC* dc, CWnd* wnd, UINT ctlColor)
{
    if (!CEmuleNextTheme::IsDarkMode())
        return CWnd::OnCtlColor(dc, wnd, ctlColor);
    dc->SetTextColor(CEmuleNextTheme::TextColor());
    dc->SetBkColor(CEmuleNextTheme::BackgroundColor());
    if (ctlColor == CTLCOLOR_STATIC || ctlColor == CTLCOLOR_DLG)
        return static_cast<HBRUSH>(m_darkBrush.GetSafeHandle());
    return CWnd::OnCtlColor(dc, wnd, ctlColor);
}

void CSearch2Wnd::OnSearchClicked()
{
    StartSearch();
}

void CSearch2Wnd::OnSavedSearchChanged()
{
    const int selected = m_savedSearch.GetCurSel();
    if (selected < 0 || static_cast<size_t>(selected) >= m_savedSearches.size())
        return;
    ApplySavedSearch(m_savedSearches[static_cast<size_t>(selected)]);
    StartSearch();
}

void CSearch2Wnd::OnSaveSearchClicked()
{
    if (!theEmuleNext.IsRunning())
        return;

    CString name;
    CString query;
    m_savedSearch.GetWindowText(name);
    m_query.GetWindowText(query);
    name.Trim();
    query.Trim();

    if (query.IsEmpty()) {
        m_status.SetWindowText(_T("Enter a search query before saving."));
        return;
    }
    if (name.IsEmpty())
        name = query;

    EmuleNextSavedSearch saved;
    saved.name = name;
    saved.query = query;
    saved.filter = CurrentFilter();

    CSearch2Service service(theEmuleNext.Database());
    if (!service.SaveSearch(saved)) {
        m_status.SetWindowText(_T("Saved search could not be stored."));
        return;
    }

    ReloadSavedSearches();
    const int selected = m_savedSearch.FindStringExact(-1, name);
    if (selected >= 0)
        m_savedSearch.SetCurSel(selected);
    else
        m_savedSearch.SetWindowText(name);

    CString status;
    status.Format(_T("Saved search '%s'."), static_cast<LPCTSTR>(name));
    m_status.SetWindowText(status);
}

void CSearch2Wnd::OnDeleteSearchClicked()
{
    if (!theEmuleNext.IsRunning())
        return;

    CString name;
    m_savedSearch.GetWindowText(name);
    name.Trim();
    if (name.IsEmpty()) {
        m_status.SetWindowText(_T("Select a saved search to delete."));
        return;
    }

    CSearch2Service service(theEmuleNext.Database());
    if (!service.DeleteSavedSearch(name)) {
        m_status.SetWindowText(_T("Saved search could not be deleted."));
        return;
    }

    ReloadSavedSearches();
    m_savedSearch.SetWindowText(_T(""));
    m_status.SetWindowText(_T("Saved search deleted."));
}

EmuleNextSearchFilter CSearch2Wnd::CurrentFilter() const
{
    EmuleNextSearchFilter filter;
    filter.excludePreviouslyDownloaded = m_hideDownloaded.GetCheck() == BST_CHECKED;
    filter.favoritesOnly = m_favoritesOnly.GetCheck() == BST_CHECKED;
    filter.missingOnly = m_missingOnly.GetCheck() == BST_CHECKED;
    return filter;
}

void CSearch2Wnd::ReloadSavedSearches()
{
    if (!::IsWindow(m_savedSearch.m_hWnd) || !theEmuleNext.IsRunning())
        return;

    CString previous;
    m_savedSearch.GetWindowText(previous);

    CSearch2Service service(theEmuleNext.Database());
    std::vector<EmuleNextSavedSearch> searches;
    if (!service.LoadSavedSearches(searches))
        return;

    m_savedSearches.swap(searches);
    m_savedSearch.ResetContent();
    for (size_t i = 0; i < m_savedSearches.size(); ++i)
        m_savedSearch.AddString(m_savedSearches[i].name);

    const int selected = previous.IsEmpty() ? -1 : m_savedSearch.FindStringExact(-1, previous);
    if (selected >= 0)
        m_savedSearch.SetCurSel(selected);
    else
        m_savedSearch.SetWindowText(previous);
}

void CSearch2Wnd::ApplySavedSearch(const EmuleNextSavedSearch& search)
{
    m_query.SetWindowText(search.query);
    m_hideDownloaded.SetCheck(search.filter.excludePreviouslyDownloaded ? BST_CHECKED : BST_UNCHECKED);
    m_favoritesOnly.SetCheck(search.filter.favoritesOnly ? BST_CHECKED : BST_UNCHECKED);
    m_missingOnly.SetCheck(search.filter.missingOnly ? BST_CHECKED : BST_UNCHECKED);
}

void CSearch2Wnd::StartSearch()
{
    if (m_loading || !theEmuleNext.IsRunning())
        return;

    std::unique_ptr<SearchContext> context(new SearchContext);
    context->target = m_hWnd;
    m_query.GetWindowText(context->request.query);
    context->request.filter = CurrentFilter();
    context->request.maximumResults = 2000;
    context->request.pageSize = 500;

    const int savedIndex = m_savedSearch.GetCurSel();
    if (savedIndex >= 0 && static_cast<size_t>(savedIndex) < m_savedSearches.size())
        context->savedSearchName = m_savedSearches[static_cast<size_t>(savedIndex)].name;

    m_loading = true;
    m_search.EnableWindow(FALSE);
    m_status.SetWindowText(_T("Searching file knowledge in the background..."));
    if (AfxBeginThread(SearchWorker, context.get(), THREAD_PRIORITY_BELOW_NORMAL) == NULL) {
        m_loading = false;
        m_search.EnableWindow(TRUE);
        m_status.SetWindowText(_T("Unable to start history search."));
        return;
    }
    context.release();
}

LRESULT CSearch2Wnd::OnSearchLoaded(WPARAM, LPARAM value)
{
    std::unique_ptr<SearchResult> result(reinterpret_cast<SearchResult*>(value));
    m_loading = false;
    m_search.EnableWindow(TRUE);
    if (result.get() == NULL || !result->ok) {
        m_status.SetWindowText(_T("Search failed."));
        return 0;
    }
    m_rows.swap(result->rows);
    PopulateResults();
    CString text;
    text.Format(_T("%u files found."), static_cast<unsigned>(m_rows.size()));
    m_status.SetWindowText(text);
    return 0;
}

void CSearch2Wnd::PopulateResults()
{
    m_results.SetRedraw(FALSE);
    m_results.DeleteAllItems();
    for (size_t i = 0; i < m_rows.size(); ++i) {
        const EmuleNextSearchFileResult& file = m_rows[i];
        CString name(file.fileName);
        if (name.IsEmpty()) name = _T("<unnamed>");
        const int row = m_results.InsertItem(static_cast<int>(i), name);
        m_results.SetItemData(row, static_cast<DWORD_PTR>(i));
        m_results.SetItemText(row, 1, CastItoXBytes(file.fileSize, false, false, 1));
        CString peers; peers.Format(_T("%u"), file.historicalPeerCount);
        m_results.SetItemText(row, 2, peers);
        m_results.SetItemText(row, 3, DateText(file.lastSeen));
        m_results.SetItemText(row, 4, file.favorite ? _T("Yes") : _T(""));
        m_results.SetItemText(row, 5, file.completedBefore ? _T("Yes") : _T(""));
        m_results.SetItemText(row, 6, HashText(file.fileHash));
    }
    m_results.SetRedraw(TRUE);
    m_results.Invalidate(FALSE);
    UpdateActionButtons();
}

int CSearch2Wnd::SelectedIndex() const
{
    const int selected = m_results.GetNextItem(-1, LVNI_SELECTED);
    if (selected < 0)
        return -1;
    const DWORD_PTR value = m_results.GetItemData(selected);
    return value < m_rows.size() ? static_cast<int>(value) : -1;
}

void CSearch2Wnd::UpdateActionButtons()
{
    const int index = SelectedIndex();
    const BOOL enabled = index >= 0 ? TRUE : FALSE;
    m_favorite.EnableWindow(enabled);
    m_downloadLater.EnableWindow(enabled);
    m_block.EnableWindow(enabled);
    if (index >= 0)
        m_favorite.SetWindowText(m_rows[static_cast<size_t>(index)].favorite ? _T("Remove favorite") : _T("Add favorite"));
    else
        m_favorite.SetWindowText(_T("Add favorite"));
}

void CSearch2Wnd::OnResultSelectionChanged(NMHDR*, LRESULT* result)
{
    UpdateActionButtons();
    *result = 0;
}

void CSearch2Wnd::OnFavoriteClicked()
{
    const int index = SelectedIndex();
    if (index < 0)
        return;
    EmuleNextSearchFileResult& row = m_rows[static_cast<size_t>(index)];
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
        theEmuleNext.Database().SaveFavorite(favorite);
        row.favorite = true;
    }
    PopulateResults();
}

void CSearch2Wnd::OnDownloadLaterClicked()
{
    const int index = SelectedIndex();
    if (index < 0)
        return;
    const EmuleNextSearchFileResult& row = m_rows[static_cast<size_t>(index)];
    EmuleNextFileObservation file;
    file.ed2kHash = row.fileHash;
    file.fileSize = row.fileSize;
    file.fileName = row.fileName;
    file.aichHash = row.aichHash;
    theEmuleNext.Database().SaveDownloadLater(file);
    m_status.SetWindowText(_T("Added to Download Later."));
}

void CSearch2Wnd::OnBlockClicked()
{
    const int index = SelectedIndex();
    if (index < 0)
        return;
    const EmuleNextSearchFileResult row = m_rows[static_cast<size_t>(index)];
    CSearch2Service service(theEmuleNext.Database());
    if (service.AddHashBlock(row.fileHash, row.fileSize, _T("Blocked from Search 2"))) {
        m_rows.erase(m_rows.begin() + index);
        PopulateResults();
        m_status.SetWindowText(_T("Hash blocked from historical search."));
    }
}

CString CSearch2Wnd::HashText(const EmuleNextHash16& hash)
{
    CString result;
    if (!hash.valid) return result;
    for (size_t i = 0; i < hash.bytes.size(); ++i) {
        CString pair; pair.Format(_T("%02X"), static_cast<unsigned>(hash.bytes[i]));
        result += pair;
    }
    return result;
}

CString CSearch2Wnd::DateText(uint64 timestamp)
{
    if (timestamp == 0) return CString();
    CTime value(static_cast<time_t>(timestamp));
    return value.Format(_T("%Y-%m-%d %H:%M"));
}
