#!/usr/bin/env python3
"""Materialize the complete Library 2.0 service and UI.

The four Library-owned source files are written as a coherent product surface
rather than incrementally substring-patched. Database writer mutations are
provided by activate-library2-database.py. Legacy eMule download handling stays
authoritative through CDownloadQueue::AddFileLinkToDownload.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"

HEADER = r'''//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "LibraryBrowserService.h"
#include <vector>

static const uint32 EMULENEXT_LIBRARY_VIEW_ID = 0x7FFFFF03u;
#define EMULENEXT_LIBRARY2_PRODUCT 1

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
    afx_msg void OnDestroy();
    afx_msg void OnSize(UINT type, int cx, int cy);
    afx_msg void OnTimer(UINT_PTR eventId);
    afx_msg BOOL OnEraseBkgnd(CDC* dc);
    afx_msg HBRUSH OnCtlColor(CDC* dc, CWnd* wnd, UINT ctlColor);
    afx_msg void OnRefreshClicked();
    afx_msg void OnFilterChanged();
    afx_msg void OnTextFilterChanged();
    afx_msg void OnFavoriteClicked();
    afx_msg void OnDownloadLaterClicked();
    afx_msg void OnDownloadAgainClicked();
    afx_msg void OnRelinkClicked();
    afx_msg void OnOpenLocationClicked();
    afx_msg void OnSelectionChanged(NMHDR* header, LRESULT* result);
    afx_msg void OnColumnClick(NMHDR* header, LRESULT* result);
    afx_msg void OnContextMenu(CWnd* wnd, CPoint point);
    afx_msg LRESULT OnLibraryLoaded(WPARAM, LPARAM value);
    afx_msg LRESULT OnRelinkVerified(WPARAM, LPARAM value);

private:
    void LayoutControls(int cx, int cy);
    void StartLoad();
    void PopulateRows();
    void SortRows();
    bool RowMatchesView(const EmuleNextLibraryBrowseRow& row) const;
    int SelectedIndex() const;
    std::vector<size_t> SelectedIndices(size_t limit = 2000) const;
    void UpdateActions();
    void SetFavoriteSelected(bool value);
    void SetDownloadLaterSelected(bool value);
    void DownloadSelectedAgain();
    void ExportRows(bool selectedOnly);
    void LoadViewState();
    void SaveViewState();
    void ApplyColumnWidths();
    CString StateText(const EmuleNextLibraryBrowseRow& row) const;
    static CString HashText(const EmuleNextHash16& hash);
    static CString DateText(uint64 timestamp);

    CStatic m_title;
    CStatic m_subtitle;
    CStatic m_viewLabel;
    CComboBox m_filter;
    CStatic m_findLabel;
    CEdit m_textFilter;
    CButton m_refresh;
    CStatic m_status;
    CListCtrl m_results;
    CButton m_favorite;
    CButton m_downloadLater;
    CButton m_downloadAgain;
    CButton m_relink;
    CButton m_openLocation;
    CBrush m_darkBrush;
    std::vector<EmuleNextLibraryBrowseRow> m_rows;
    EmuleNextLibraryViewFilter m_viewFilter;
    int m_sortColumn;
    bool m_sortAscending;
    bool m_loading;
    bool m_relinking;
    CString m_textFilterState;
};
'''

SERVICE_HEADER = r'''//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "EmuleNextDatabase.h"
#include <vector>

#define EMULENEXT_LIBRARY2_SERVICE 1

enum EmuleNextLibraryViewFilter
{
    ENLV_HISTORY = 0,
    ENLV_FAVORITES,
    ENLV_COMPLETED,
    ENLV_MISSING,
    ENLV_DOWNLOAD_LATER
};

struct EmuleNextLibraryBrowseRow
{
    EmuleNextHash16 fileHash;
    uint64 fileSize;
    CStringW fileName;
    CStringW aichHash;
    uint64 lastSeen;
    uint64 lastVerified;
    uint64 missingSince;
    uint32 recentPeerCount;
    bool favorite;
    bool completed;
    bool missing;
    bool availableAgain;
    bool downloadLater;
    CStringW localPath;

    EmuleNextLibraryBrowseRow();
};

class CLibraryBrowserService
{
public:
    explicit CLibraryBrowserService(const CStringW& databasePath);
    bool List(EmuleNextLibraryViewFilter filter,
        std::vector<EmuleNextLibraryBrowseRow>& rows,
        size_t maximumRows = 5000) const;

private:
    CStringW m_databasePath;
};
'''

SERVICE_CPP = r'''//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later

#include "stdafx.h"
#include "LibraryBrowserService.h"

#include <winsqlite3.h>

namespace
{
    static const size_t LIBRARY_SQL_LIMIT = 10000;

    CStringW ColumnText(sqlite3_stmt* statement, int column)
    {
        const wchar_t* value = static_cast<const wchar_t*>(sqlite3_column_text16(statement, column));
        return value != NULL ? CStringW(value) : CStringW();
    }

    EmuleNextHash16 ColumnHash(sqlite3_stmt* statement, int column)
    {
        const void* value = sqlite3_column_blob(statement, column);
        return sqlite3_column_bytes(statement, column) == 16
            ? EmuleNextHash16(static_cast<const unsigned char*>(value))
            : EmuleNextHash16();
    }

    bool FileMissing(const CStringW& path)
    {
        if (path.IsEmpty())
            return true;
        const DWORD attributes = ::GetFileAttributesW(path.GetString());
        return attributes == INVALID_FILE_ATTRIBUTES || (attributes & FILE_ATTRIBUTE_DIRECTORY) != 0;
    }

    bool PassesFilter(const EmuleNextLibraryBrowseRow& row, EmuleNextLibraryViewFilter filter)
    {
        switch (filter) {
        case ENLV_FAVORITES: return row.favorite;
        case ENLV_COMPLETED: return row.completed;
        case ENLV_MISSING: return row.completed && row.missing;
        case ENLV_DOWNLOAD_LATER: return row.downloadLater;
        case ENLV_HISTORY:
        default: return true;
        }
    }
}

EmuleNextLibraryBrowseRow::EmuleNextLibraryBrowseRow()
    : fileSize(0)
    , lastSeen(0)
    , lastVerified(0)
    , missingSince(0)
    , recentPeerCount(0)
    , favorite(false)
    , completed(false)
    , missing(false)
    , availableAgain(false)
    , downloadLater(false)
{
}

CLibraryBrowserService::CLibraryBrowserService(const CStringW& databasePath)
    : m_databasePath(databasePath)
{
}

bool CLibraryBrowserService::List(EmuleNextLibraryViewFilter filter,
    std::vector<EmuleNextLibraryBrowseRow>& rows,
    size_t maximumRows) const
{
    rows.clear();
    if (m_databasePath.IsEmpty())
        return false;

    sqlite3* database = NULL;
    if (sqlite3_open16(m_databasePath.GetString(), &database) != SQLITE_OK) {
        if (database != NULL)
            sqlite3_close(database);
        return false;
    }
    sqlite3_busy_timeout(database, 1000);
    sqlite3_exec(database, "PRAGMA query_only=ON;", NULL, NULL, NULL);

    static const char sql[] =
        "SELECT f.ed2k_hash,f.size,COALESCE(f.canonical_name,''),COALESCE(f.aich_hash,''),f.last_seen,"
        "EXISTS(SELECT 1 FROM favorites fav WHERE fav.file_id=f.id),"
        "CASE WHEN le.completed_at IS NULL THEN 0 ELSE 1 END,"
        "EXISTS(SELECT 1 FROM download_later dl WHERE dl.file_id=f.id),"
        "COALESCE(le.local_path,''),COALESCE(le.last_verified,0),COALESCE(le.missing_since,0),"
        "(SELECT COUNT(DISTINCT pf.peer_id) FROM peer_files pf WHERE pf.file_id=f.id AND pf.last_seen>=?1) "
        "FROM files f LEFT JOIN library_entries le ON le.file_id=f.id "
        "ORDER BY f.last_seen DESC LIMIT ?2";

    sqlite3_stmt* statement = NULL;
    bool ok = sqlite3_prepare_v2(database, sql, -1, &statement, NULL) == SQLITE_OK;
    if (ok) {
        const sqlite3_int64 recentCutoff = static_cast<sqlite3_int64>(time(NULL)) - (30LL * 24LL * 60LL * 60LL);
        sqlite3_bind_int64(statement, 1, recentCutoff);
        sqlite3_bind_int64(statement, 2, static_cast<sqlite3_int64>(LIBRARY_SQL_LIMIT));
        while (sqlite3_step(statement) == SQLITE_ROW) {
            EmuleNextLibraryBrowseRow row;
            row.fileHash = ColumnHash(statement, 0);
            if (!row.fileHash.valid)
                continue;
            row.fileSize = static_cast<uint64>(sqlite3_column_int64(statement, 1));
            row.fileName = ColumnText(statement, 2);
            row.aichHash = ColumnText(statement, 3);
            row.lastSeen = static_cast<uint64>(sqlite3_column_int64(statement, 4));
            row.favorite = sqlite3_column_int(statement, 5) != 0;
            row.completed = sqlite3_column_int(statement, 6) != 0;
            row.downloadLater = sqlite3_column_int(statement, 7) != 0;
            row.localPath = ColumnText(statement, 8);
            row.lastVerified = static_cast<uint64>(sqlite3_column_int64(statement, 9));
            row.missingSince = static_cast<uint64>(sqlite3_column_int64(statement, 10));
            row.recentPeerCount = static_cast<uint32>(sqlite3_column_int(statement, 11));
            row.missing = row.completed && FileMissing(row.localPath);
            row.availableAgain = row.completed && row.missing && row.recentPeerCount != 0;
            if (!PassesFilter(row, filter))
                continue;
            rows.push_back(row);
            if (maximumRows != 0 && rows.size() >= maximumRows)
                break;
        }
    }

    if (statement != NULL)
        sqlite3_finalize(statement);
    sqlite3_close(database);
    return ok;
}
'''

CPP = r'''//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later

#include "stdafx.h"
#include "FileLibraryWnd.h"
#include "DownloadQueue.h"
#include "ED2KLink.h"
#include "EmuleNextRuntime.h"
#include "EmuleNextTheme.h"
#include "EmuleNextUiMetrics.h"
#include "KnownFile.h"
#include "OtherFunctions.h"
#include "emule.h"

#include <algorithm>
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
        IDC_EN_LIBRARY_TEXT_FILTER,
        IDC_EN_LIBRARY_DOWNLOAD_AGAIN,
        IDC_EN_LIBRARY_RELINK
    };

    enum
    {
        ID_EN_LIBRARY_CTX_FAVORITE = 0x7EA0,
        ID_EN_LIBRARY_CTX_UNFAVORITE,
        ID_EN_LIBRARY_CTX_LATER,
        ID_EN_LIBRARY_CTX_UNLATER,
        ID_EN_LIBRARY_CTX_DOWNLOAD,
        ID_EN_LIBRARY_CTX_RELINK,
        ID_EN_LIBRARY_CTX_LOCATION,
        ID_EN_LIBRARY_CTX_EXPORT_SELECTED,
        ID_EN_LIBRARY_CTX_EXPORT_ALL
    };

    const UINT WM_EN_LIBRARY_LOADED = WM_APP + 0x571;
    const UINT WM_EN_LIBRARY_RELINKED = WM_APP + 0x572;
    const UINT_PTR EN_LIBRARY_FILTER_TIMER = 0x7E6F;
    const LPCTSTR PROFILE_SECTION = _T("eMule Next Library 2");
    const int LIBRARY_COLUMN_COUNT = 7;

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

    struct RelinkContext
    {
        HWND target;
        EmuleNextHash16 hash;
        uint64 fileSize;
        CStringW path;
        RelinkContext() : target(NULL), fileSize(0) {}
    };

    struct RelinkResult
    {
        EmuleNextHash16 hash;
        uint64 fileSize;
        CStringW path;
        bool readOk;
        bool sizeMatch;
        bool hashMatch;
        RelinkResult() : fileSize(0), readOk(false), sizeMatch(false), hashMatch(false) {}
    };

    UINT AFX_CDECL LibraryWorker(LPVOID value)
    {
        std::unique_ptr<LibraryContext> context(static_cast<LibraryContext*>(value));
        std::unique_ptr<LibraryResult> result(new LibraryResult);
        CLibraryBrowserService service(context->databasePath);
        result->ok = service.List(context->filter, result->rows, 5000);
        if (::IsWindow(context->target)
            && ::PostMessage(context->target, WM_EN_LIBRARY_LOADED, 0, reinterpret_cast<LPARAM>(result.get())))
            result.release();
        return 0;
    }

    UINT AFX_CDECL RelinkWorker(LPVOID value)
    {
        std::unique_ptr<RelinkContext> context(static_cast<RelinkContext*>(value));
        std::unique_ptr<RelinkResult> result(new RelinkResult);
        result->hash = context->hash;
        result->fileSize = context->fileSize;
        result->path = context->path;

        CString path(context->path);
        const int slash = max(path.ReverseFind(_T('\\')), path.ReverseFind(_T('/')));
        if (slash > 0 && slash + 1 < path.GetLength()) {
            CString directory = path.Left(slash);
            if (directory.GetLength() == 2 && directory[1] == _T(':'))
                directory += _T('\\');
            const CString name = path.Mid(slash + 1);
            CKnownFile candidate;
            result->readOk = candidate.CreateFromFile(directory, name, NULL);
            if (result->readOk) {
                result->sizeMatch = static_cast<uint64>(candidate.GetFileSize()) == context->fileSize;
                result->hashMatch = result->sizeMatch && context->hash.valid
                    && memcmp(candidate.GetFileHash(), context->hash.bytes.data(), 16) == 0;
            }
        }

        if (::IsWindow(context->target)
            && ::PostMessage(context->target, WM_EN_LIBRARY_RELINKED, 0, reinterpret_cast<LPARAM>(result.get())))
            result.release();
        return 0;
    }

    int CompareUInt64(uint64 left, uint64 right)
    {
        return left < right ? -1 : (left > right ? 1 : 0);
    }

    CString CsvEscape(const CString& value)
    {
        CString escaped(value);
        escaped.Replace(_T("\""), _T("\"\""));
        CString result;
        result.Format(_T("\"%s\""), static_cast<LPCTSTR>(escaped));
        return result;
    }

    bool SameIdentity(const EmuleNextLibraryBrowseRow& row, const EmuleNextHash16& hash, uint64 size)
    {
        return row.fileSize == size && row.fileHash.valid && hash.valid && row.fileHash.bytes == hash.bytes;
    }
}

BEGIN_MESSAGE_MAP(CFileLibraryWnd, CWnd)
    ON_WM_CREATE()
    ON_WM_DESTROY()
    ON_WM_SIZE()
    ON_WM_TIMER()
    ON_WM_ERASEBKGND()
    ON_WM_CTLCOLOR()
    ON_WM_CONTEXTMENU()
    ON_BN_CLICKED(IDC_EN_LIBRARY_REFRESH, OnRefreshClicked)
    ON_CBN_SELCHANGE(IDC_EN_LIBRARY_FILTER, OnFilterChanged)
    ON_EN_CHANGE(IDC_EN_LIBRARY_TEXT_FILTER, OnTextFilterChanged)
    ON_BN_CLICKED(IDC_EN_LIBRARY_FAVORITE, OnFavoriteClicked)
    ON_BN_CLICKED(IDC_EN_LIBRARY_LATER, OnDownloadLaterClicked)
    ON_BN_CLICKED(IDC_EN_LIBRARY_DOWNLOAD_AGAIN, OnDownloadAgainClicked)
    ON_BN_CLICKED(IDC_EN_LIBRARY_RELINK, OnRelinkClicked)
    ON_BN_CLICKED(IDC_EN_LIBRARY_LOCATION, OnOpenLocationClicked)
    ON_NOTIFY(LVN_ITEMCHANGED, IDC_EN_LIBRARY_RESULTS, OnSelectionChanged)
    ON_NOTIFY(LVN_COLUMNCLICK, IDC_EN_LIBRARY_RESULTS, OnColumnClick)
    ON_MESSAGE(WM_EN_LIBRARY_LOADED, OnLibraryLoaded)
    ON_MESSAGE(WM_EN_LIBRARY_RELINKED, OnRelinkVerified)
END_MESSAGE_MAP()

CFileLibraryWnd::CFileLibraryWnd()
    : m_viewFilter(ENLV_HISTORY)
    , m_sortColumn(3)
    , m_sortAscending(false)
    , m_loading(false)
    , m_relinking(false)
{
}

CFileLibraryWnd::~CFileLibraryWnd()
{
    if (::IsWindow(m_hWnd))
        KillTimer(EN_LIBRARY_FILTER_TIMER);
}

bool CFileLibraryWnd::Create(CWnd* parent)
{
    if (parent == NULL)
        return false;
    const CString className = AfxRegisterWndClass(CS_DBLCLKS, ::LoadCursor(NULL, IDC_ARROW),
        reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1), NULL);
    CRect empty(0, 0, 0, 0);
    return CWnd::CreateEx(0, className, _T("eMule Next File Library 2.0"),
        WS_CHILD | WS_CLIPCHILDREN | WS_CLIPSIBLINGS, empty, parent, 0) != FALSE;
}

int CFileLibraryWnd::OnCreate(LPCREATESTRUCT createStruct)
{
    if (CWnd::OnCreate(createStruct) == -1)
        return -1;

    m_darkBrush.CreateSolidBrush(CEmuleNextTheme::BackgroundColor());
    CRect empty(0, 0, 0, 0);
    if (!m_title.Create(_T("Library 2.0"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_subtitle.Create(_T("History, favorites, missing files, availability and Download Later by ED2K hash + size."),
            WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_viewLabel.Create(_T("View"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_filter.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST, empty, this, IDC_EN_LIBRARY_FILTER)
        || !m_findLabel.Create(_T("Find"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_textFilter.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | WS_BORDER | ES_AUTOHSCROLL, empty, this, IDC_EN_LIBRARY_TEXT_FILTER)
        || !m_refresh.Create(_T("Verify paths"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_LIBRARY_REFRESH)
        || !m_status.Create(_T("Ready."), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_results.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | LVS_REPORT | LVS_SHOWSELALWAYS, empty, this, IDC_EN_LIBRARY_RESULTS)
        || !m_favorite.Create(_T("Favorite selected"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_LIBRARY_FAVORITE)
        || !m_downloadLater.Create(_T("Download Later"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_LIBRARY_LATER)
        || !m_downloadAgain.Create(_T("Download again"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_LIBRARY_DOWNLOAD_AGAIN)
        || !m_relink.Create(_T("Relink..."), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_LIBRARY_RELINK)
        || !m_openLocation.Create(_T("Open location"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON, empty, this, IDC_EN_LIBRARY_LOCATION))
        return -1;

    CFont* font = CFont::FromHandle(static_cast<HFONT>(::GetStockObject(DEFAULT_GUI_FONT)));
    m_title.SetFont(font); m_subtitle.SetFont(font); m_viewLabel.SetFont(font); m_filter.SetFont(font);
    m_findLabel.SetFont(font); m_textFilter.SetFont(font); m_refresh.SetFont(font); m_status.SetFont(font);
    m_results.SetFont(font); m_favorite.SetFont(font); m_downloadLater.SetFont(font); m_downloadAgain.SetFont(font);
    m_relink.SetFont(font); m_openLocation.SetFont(font);

    m_filter.AddString(_T("History"));
    m_filter.AddString(_T("Favorites"));
    m_filter.AddString(_T("Completed"));
    m_filter.AddString(_T("Missing"));
    m_filter.AddString(_T("Download Later"));

    m_results.SetExtendedStyle(LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_GRIDLINES);
    m_results.InsertColumn(0, _T("File"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 330));
    m_results.InsertColumn(1, _T("Size"), LVCFMT_RIGHT, CEmuleNextUiMetrics::Scale(m_hWnd, 95));
    m_results.InsertColumn(2, _T("State"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 125));
    m_results.InsertColumn(3, _T("Last seen"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 135));
    m_results.InsertColumn(4, _T("Peers 30d"), LVCFMT_RIGHT, CEmuleNextUiMetrics::Scale(m_hWnd, 78));
    m_results.InsertColumn(5, _T("Local path"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 300));
    m_results.InsertColumn(6, _T("ED2K hash"), LVCFMT_LEFT, CEmuleNextUiMetrics::Scale(m_hWnd, 245));

    LoadViewState();
    ApplyColumnWidths();
    m_filter.SetCurSel(static_cast<int>(m_viewFilter));
    m_textFilter.SetWindowText(m_textFilterState);
    UpdateActions();
    CEmuleNextTheme::ApplyToWindow(m_hWnd);
    Refresh(true);
    return 0;
}

void CFileLibraryWnd::OnDestroy()
{
    SaveViewState();
    KillTimer(EN_LIBRARY_FILTER_TIMER);
    CWnd::OnDestroy();
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
    const int margin = CEmuleNextUiMetrics::Scale(m_hWnd, 12);
    const int titleTop = CEmuleNextUiMetrics::Scale(m_hWnd, 10);
    const int controlsTop = CEmuleNextUiMetrics::Scale(m_hWnd, 58);
    const int statusTop = CEmuleNextUiMetrics::Scale(m_hWnd, 91);
    const int listTop = CEmuleNextUiMetrics::Scale(m_hWnd, 115);
    const int actionHeight = CEmuleNextUiMetrics::Scale(m_hWnd, 30);
    const int gap = CEmuleNextUiMetrics::Scale(m_hWnd, 8);
    const int actionTop = max(listTop + CEmuleNextUiMetrics::Scale(m_hWnd, 70), cy - margin - actionHeight);

    m_title.MoveWindow(margin, titleTop, max(CEmuleNextUiMetrics::Scale(m_hWnd, 160), cx - margin * 2), CEmuleNextUiMetrics::Scale(m_hWnd, 22));
    m_subtitle.MoveWindow(margin, titleTop + CEmuleNextUiMetrics::Scale(m_hWnd, 24), max(CEmuleNextUiMetrics::Scale(m_hWnd, 160), cx - margin * 2), CEmuleNextUiMetrics::Scale(m_hWnd, 18));

    m_viewLabel.MoveWindow(margin, controlsTop + CEmuleNextUiMetrics::Scale(m_hWnd, 5), CEmuleNextUiMetrics::Scale(m_hWnd, 34), CEmuleNextUiMetrics::Scale(m_hWnd, 18));
    m_filter.MoveWindow(margin + CEmuleNextUiMetrics::Scale(m_hWnd, 38), controlsTop, CEmuleNextUiMetrics::Scale(m_hWnd, 160), CEmuleNextUiMetrics::Scale(m_hWnd, 240));
    m_findLabel.MoveWindow(margin + CEmuleNextUiMetrics::Scale(m_hWnd, 212), controlsTop + CEmuleNextUiMetrics::Scale(m_hWnd, 5), CEmuleNextUiMetrics::Scale(m_hWnd, 30), CEmuleNextUiMetrics::Scale(m_hWnd, 18));
    const int refreshWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 100);
    m_textFilter.MoveWindow(margin + CEmuleNextUiMetrics::Scale(m_hWnd, 246), controlsTop,
        max(CEmuleNextUiMetrics::Scale(m_hWnd, 120), cx - (margin + CEmuleNextUiMetrics::Scale(m_hWnd, 246)) - refreshWidth - gap), CEmuleNextUiMetrics::Scale(m_hWnd, 25));
    m_refresh.MoveWindow(max(margin, cx - margin - refreshWidth), controlsTop, refreshWidth, CEmuleNextUiMetrics::Scale(m_hWnd, 25));

    m_status.MoveWindow(margin, statusTop, max(CEmuleNextUiMetrics::Scale(m_hWnd, 100), cx - margin * 2), CEmuleNextUiMetrics::Scale(m_hWnd, 18));
    m_results.MoveWindow(margin, listTop, max(0, cx - margin * 2), max(CEmuleNextUiMetrics::Scale(m_hWnd, 60), actionTop - listTop - gap));

    int x = margin;
    const int favoriteWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 126);
    const int laterWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 126);
    const int downloadWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 118);
    const int relinkWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 90);
    const int locationWidth = CEmuleNextUiMetrics::Scale(m_hWnd, 112);
    m_favorite.MoveWindow(x, actionTop, favoriteWidth, actionHeight); x += favoriteWidth + gap;
    m_downloadLater.MoveWindow(x, actionTop, laterWidth, actionHeight); x += laterWidth + gap;
    m_downloadAgain.MoveWindow(x, actionTop, downloadWidth, actionHeight); x += downloadWidth + gap;
    m_relink.MoveWindow(x, actionTop, relinkWidth, actionHeight); x += relinkWidth + gap;
    m_openLocation.MoveWindow(x, actionTop, locationWidth, actionHeight);
}

void CFileLibraryWnd::OnTimer(UINT_PTR eventId)
{
    if (eventId == EN_LIBRARY_FILTER_TIMER) {
        KillTimer(EN_LIBRARY_FILTER_TIMER);
        if (!m_loading) {
            m_textFilter.GetWindowText(m_textFilterState);
            PopulateRows();
            SaveViewState();
        }
        return;
    }
    CWnd::OnTimer(eventId);
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
    int selected = m_filter.GetCurSel();
    if (selected < ENLV_HISTORY || selected > ENLV_DOWNLOAD_LATER)
        selected = ENLV_HISTORY;
    m_viewFilter = static_cast<EmuleNextLibraryViewFilter>(selected);
    SaveViewState();
    StartLoad();
}

void CFileLibraryWnd::OnTextFilterChanged()
{
    KillTimer(EN_LIBRARY_FILTER_TIMER);
    SetTimer(EN_LIBRARY_FILTER_TIMER, 250, NULL);
}

void CFileLibraryWnd::StartLoad()
{
    if (m_loading || !theEmuleNext.IsRunning())
        return;
    std::unique_ptr<LibraryContext> context(new LibraryContext);
    context->target = m_hWnd;
    context->databasePath = theEmuleNext.Database().GetDatabasePath();
    context->filter = m_viewFilter;
    m_loading = true;
    m_refresh.EnableWindow(FALSE);
    m_status.SetWindowText(_T("Reading Library and verifying local paths in the background..."));
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
    const uint64 now = static_cast<uint64>(time(NULL));
    for (size_t i = 0; i < m_rows.size(); ++i) {
        const EmuleNextLibraryBrowseRow& row = m_rows[i];
        if (!row.completed)
            continue;
        const bool persistedMissing = row.missingSince != 0;
        if (persistedMissing != row.missing || row.lastVerified == 0 || now > row.lastVerified + 3600)
            theEmuleNext.Database().UpdateLibraryVerification(row.fileHash, row.fileSize, row.missing);
    }
    KillTimer(EN_LIBRARY_FILTER_TIMER);
    PopulateRows();
    return 0;
}

bool CFileLibraryWnd::RowMatchesView(const EmuleNextLibraryBrowseRow& row) const
{
    switch (m_viewFilter) {
    case ENLV_FAVORITES: return row.favorite;
    case ENLV_COMPLETED: return row.completed;
    case ENLV_MISSING: return row.completed && row.missing;
    case ENLV_DOWNLOAD_LATER: return row.downloadLater;
    case ENLV_HISTORY:
    default: return true;
    }
}

CString CFileLibraryWnd::StateText(const EmuleNextLibraryBrowseRow& row) const
{
    if (row.completed && row.missing && row.availableAgain)
        return _T("Available again");
    if (row.completed && row.missing)
        return _T("Missing");
    if (row.completed)
        return _T("Completed");
    if (row.downloadLater)
        return _T("Download later");
    if (row.favorite)
        return _T("Favorite");
    return _T("History");
}

void CFileLibraryWnd::SortRows()
{
    const int column = m_sortColumn;
    const bool ascending = m_sortAscending;
    std::stable_sort(m_rows.begin(), m_rows.end(), [this, column, ascending](const EmuleNextLibraryBrowseRow& a, const EmuleNextLibraryBrowseRow& b) {
        int value = 0;
        switch (column) {
        case 0: value = CString(a.fileName).CompareNoCase(CString(b.fileName)); break;
        case 1: value = CompareUInt64(a.fileSize, b.fileSize); break;
        case 2: value = StateText(a).CompareNoCase(StateText(b)); break;
        case 3: value = CompareUInt64(a.lastSeen, b.lastSeen); break;
        case 4: value = static_cast<int>(a.recentPeerCount) - static_cast<int>(b.recentPeerCount); break;
        case 5: value = CString(a.localPath).CompareNoCase(CString(b.localPath)); break;
        case 6: value = memcmp(a.fileHash.bytes.data(), b.fileHash.bytes.data(), 16); break;
        default: value = 0; break;
        }
        return ascending ? value < 0 : value > 0;
    });
}

void CFileLibraryWnd::PopulateRows()
{
    CString needle;
    m_textFilter.GetWindowText(needle);
    needle.Trim();
    needle.MakeLower();
    SortRows();

    m_results.SetRedraw(FALSE);
    m_results.DeleteAllItems();
    unsigned displayed = 0;
    for (size_t i = 0; i < m_rows.size(); ++i) {
        const EmuleNextLibraryBrowseRow& file = m_rows[i];
        if (!RowMatchesView(file))
            continue;
        CString name(file.fileName);
        if (name.IsEmpty())
            name = _T("<unnamed>");
        if (!needle.IsEmpty()) {
            CString haystack(name);
            haystack += _T(" "); haystack += CString(file.localPath);
            haystack += _T(" "); haystack += HashText(file.fileHash);
            haystack.MakeLower();
            if (haystack.Find(needle) < 0)
                continue;
        }
        const int row = m_results.InsertItem(static_cast<int>(displayed), name);
        m_results.SetItemData(row, static_cast<DWORD_PTR>(i));
        m_results.SetItemText(row, 1, CastItoXBytes(file.fileSize, false, false, 1));
        m_results.SetItemText(row, 2, StateText(file));
        m_results.SetItemText(row, 3, DateText(file.lastSeen));
        CString peers; peers.Format(_T("%u"), file.recentPeerCount); m_results.SetItemText(row, 4, peers);
        m_results.SetItemText(row, 5, CString(file.localPath));
        m_results.SetItemText(row, 6, HashText(file.fileHash));
        ++displayed;
    }
    m_results.SetRedraw(TRUE);
    m_results.Invalidate(FALSE);
    UpdateActions();

    CString status;
    status.Format(_T("%u files shown; %u loaded. Filesystem checks ran outside the GUI thread."), displayed, static_cast<unsigned>(m_rows.size()));
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

std::vector<size_t> CFileLibraryWnd::SelectedIndices(size_t limit) const
{
    std::vector<size_t> indices;
    POSITION position = m_results.GetFirstSelectedItemPosition();
    while (position != NULL && indices.size() < limit) {
        const int listIndex = m_results.GetNextSelectedItem(position);
        const DWORD_PTR value = m_results.GetItemData(listIndex);
        if (value < m_rows.size())
            indices.push_back(static_cast<size_t>(value));
    }
    return indices;
}

void CFileLibraryWnd::UpdateActions()
{
    const std::vector<size_t> selected = SelectedIndices();
    const BOOL any = selected.empty() ? FALSE : TRUE;
    bool allFavorite = any != FALSE;
    bool allLater = any != FALSE;
    for (size_t i = 0; i < selected.size(); ++i) {
        allFavorite = allFavorite && m_rows[selected[i]].favorite;
        allLater = allLater && m_rows[selected[i]].downloadLater;
    }
    m_favorite.EnableWindow(any);
    m_downloadLater.EnableWindow(any);
    m_downloadAgain.EnableWindow(any && !m_relinking);
    m_favorite.SetWindowText(allFavorite ? _T("Unfavorite selected") : _T("Favorite selected"));
    m_downloadLater.SetWindowText(allLater ? _T("Remove Download Later") : _T("Add Download Later"));

    const int index = SelectedIndex();
    const bool single = selected.size() == 1 && index >= 0;
    const bool relinkable = single && m_rows[static_cast<size_t>(index)].completed && m_rows[static_cast<size_t>(index)].missing;
    m_relink.EnableWindow(relinkable && !m_relinking);
    m_openLocation.EnableWindow(single && !m_rows[static_cast<size_t>(index)].localPath.IsEmpty() && !m_rows[static_cast<size_t>(index)].missing);
}

void CFileLibraryWnd::OnSelectionChanged(NMHDR*, LRESULT* result)
{
    UpdateActions();
    *result = 0;
}

void CFileLibraryWnd::OnColumnClick(NMHDR* header, LRESULT* result)
{
    const NMLISTVIEW* click = reinterpret_cast<const NMLISTVIEW*>(header);
    if (click->iSubItem == m_sortColumn)
        m_sortAscending = !m_sortAscending;
    else {
        m_sortColumn = click->iSubItem;
        m_sortAscending = click->iSubItem == 0 || click->iSubItem == 2 || click->iSubItem == 5 || click->iSubItem == 6;
    }
    PopulateRows();
    SaveViewState();
    *result = 0;
}

void CFileLibraryWnd::SetFavoriteSelected(bool value)
{
    const std::vector<size_t> selected = SelectedIndices();
    unsigned changed = 0;
    for (size_t i = 0; i < selected.size() && changed < 2000; ++i) {
        EmuleNextLibraryBrowseRow& row = m_rows[selected[i]];
        if (row.favorite == value)
            continue;
        if (value) {
            EmuleNextFavoriteRecord favorite;
            favorite.fileHash = row.fileHash; favorite.fileSize = row.fileSize; favorite.fileName = row.fileName;
            favorite.aichHash = row.aichHash; favorite.localPath = row.localPath;
            theEmuleNext.Database().SaveFavorite(favorite);
        }
        else
            theEmuleNext.Database().RemoveFavorite(row.fileHash, row.fileSize);
        row.favorite = value;
        ++changed;
    }
    PopulateRows();
    CString status; status.Format(value ? _T("Favorited %u selected files.") : _T("Removed favorite from %u selected files."), changed);
    m_status.SetWindowText(status);
}

void CFileLibraryWnd::SetDownloadLaterSelected(bool value)
{
    const std::vector<size_t> selected = SelectedIndices();
    unsigned changed = 0;
    for (size_t i = 0; i < selected.size() && changed < 2000; ++i) {
        EmuleNextLibraryBrowseRow& row = m_rows[selected[i]];
        if (row.downloadLater == value)
            continue;
        if (value) {
            EmuleNextFileObservation file;
            file.ed2kHash = row.fileHash; file.fileSize = row.fileSize; file.fileName = row.fileName; file.aichHash = row.aichHash;
            theEmuleNext.Database().SaveDownloadLater(file);
        }
        else
            theEmuleNext.Database().RemoveDownloadLater(row.fileHash, row.fileSize);
        row.downloadLater = value;
        ++changed;
    }
    PopulateRows();
    CString status; status.Format(value ? _T("Added %u selected files to Download Later.") : _T("Removed %u selected files from Download Later."), changed);
    m_status.SetWindowText(status);
}

void CFileLibraryWnd::OnFavoriteClicked()
{
    const std::vector<size_t> selected = SelectedIndices();
    if (selected.empty()) return;
    bool allFavorite = true;
    for (size_t i = 0; i < selected.size(); ++i) allFavorite = allFavorite && m_rows[selected[i]].favorite;
    SetFavoriteSelected(!allFavorite);
}

void CFileLibraryWnd::OnDownloadLaterClicked()
{
    const std::vector<size_t> selected = SelectedIndices();
    if (selected.empty()) return;
    bool allLater = true;
    for (size_t i = 0; i < selected.size(); ++i) allLater = allLater && m_rows[selected[i]].downloadLater;
    SetDownloadLaterSelected(!allLater);
}

void CFileLibraryWnd::DownloadSelectedAgain()
{
    if (theApp.downloadqueue == NULL)
        return;
    const std::vector<size_t> selected = SelectedIndices();
    unsigned added = 0;
    unsigned existing = 0;
    unsigned failed = 0;
    for (size_t i = 0; i < selected.size() && i < 2000; ++i) {
        EmuleNextLibraryBrowseRow& row = m_rows[selected[i]];
        if (!row.fileHash.valid || row.fileSize == 0) { ++failed; continue; }
        if (theApp.downloadqueue->IsFileExisting(row.fileHash.bytes.data(), false)) { ++existing; continue; }
        CString name(row.fileName); if (name.IsEmpty()) name = HashText(row.fileHash);
        CString size; size.Format(_T("%I64u"), row.fileSize);
        const CString hash = HashText(row.fileHash);
        CStringArray params;
        try {
            CED2KFileLink link(name, size, hash, params, NULL);
            theApp.downloadqueue->AddFileLinkToDownload(link);
            if (row.downloadLater) {
                theEmuleNext.Database().RemoveDownloadLater(row.fileHash, row.fileSize);
                row.downloadLater = false;
            }
            ++added;
        }
        catch (...) {
            ++failed;
        }
    }
    PopulateRows();
    CString status; status.Format(_T("Download again: %u added, %u already queued, %u failed."), added, existing, failed);
    m_status.SetWindowText(status);
}

void CFileLibraryWnd::OnDownloadAgainClicked()
{
    DownloadSelectedAgain();
}

void CFileLibraryWnd::OnRelinkClicked()
{
    const int index = SelectedIndex();
    if (index < 0 || m_relinking)
        return;
    const EmuleNextLibraryBrowseRow& row = m_rows[static_cast<size_t>(index)];
    if (!row.completed || !row.missing)
        return;

    CString initialName(row.fileName);
    CFileDialog dialog(TRUE, NULL, initialName, OFN_FILEMUSTEXIST | OFN_HIDEREADONLY,
        _T("All files (*.*)|*.*||"), this);
    if (dialog.DoModal() != IDOK)
        return;

    std::unique_ptr<RelinkContext> context(new RelinkContext);
    context->target = m_hWnd;
    context->hash = row.fileHash;
    context->fileSize = row.fileSize;
    context->path = CStringW(dialog.GetPathName());
    m_relinking = true;
    UpdateActions();
    m_status.SetWindowText(_T("Hashing selected file in the background before relink..."));
    if (AfxBeginThread(RelinkWorker, context.get(), THREAD_PRIORITY_BELOW_NORMAL) == NULL) {
        m_relinking = false;
        UpdateActions();
        m_status.SetWindowText(_T("Unable to start relink verification."));
        return;
    }
    context.release();
}

LRESULT CFileLibraryWnd::OnRelinkVerified(WPARAM, LPARAM value)
{
    std::unique_ptr<RelinkResult> result(reinterpret_cast<RelinkResult*>(value));
    m_relinking = false;
    if (result.get() == NULL || !result->readOk) {
        m_status.SetWindowText(_T("Relink failed: selected file could not be hashed."));
        UpdateActions();
        return 0;
    }
    if (!result->sizeMatch || !result->hashMatch) {
        m_status.SetWindowText(_T("Relink rejected: ED2K hash + size do not match the Library file."));
        UpdateActions();
        return 0;
    }
    theEmuleNext.Database().RelinkLibraryFile(result->hash, result->fileSize, result->path);
    for (size_t i = 0; i < m_rows.size(); ++i) {
        if (SameIdentity(m_rows[i], result->hash, result->fileSize)) {
            m_rows[i].localPath = result->path;
            m_rows[i].missing = false;
            m_rows[i].missingSince = 0;
            m_rows[i].availableAgain = false;
            break;
        }
    }
    PopulateRows();
    m_status.SetWindowText(_T("Relink verified by ED2K hash + size and saved."));
    return 0;
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

void CFileLibraryWnd::ExportRows(bool selectedOnly)
{
    CFileDialog dialog(FALSE, _T("csv"), _T("emule-next-library.csv"), OFN_OVERWRITEPROMPT | OFN_HIDEREADONLY,
        _T("CSV files (*.csv)|*.csv|All files (*.*)|*.*||"), this);
    if (dialog.DoModal() != IDOK)
        return;
    CFile file;
    if (!file.Open(dialog.GetPathName(), CFile::modeCreate | CFile::modeWrite | CFile::shareDenyWrite)) {
        m_status.SetWindowText(_T("CSV export could not be opened."));
        return;
    }
#ifdef _UNICODE
    const wchar_t bom = 0xFEFF;
    file.Write(&bom, sizeof(bom));
#endif
    CString header = _T("File,Size,State,Last seen,Peers 30d,Local path,ED2K hash\r\n");
#ifdef _UNICODE
    file.Write(header.GetString(), static_cast<UINT>(header.GetLength() * sizeof(wchar_t)));
#else
    file.Write(header.GetString(), header.GetLength());
#endif
    std::vector<size_t> selected = selectedOnly ? SelectedIndices(2000) : std::vector<size_t>();
    unsigned written = 0;
    for (size_t i = 0; i < m_rows.size(); ++i) {
        if (!RowMatchesView(m_rows[i])) continue;
        if (selectedOnly && std::find(selected.begin(), selected.end(), i) == selected.end()) continue;
        CString line;
        CString size; size.Format(_T("%I64u"), m_rows[i].fileSize);
        CString peers; peers.Format(_T("%u"), m_rows[i].recentPeerCount);
        line = CsvEscape(CString(m_rows[i].fileName)) + _T(",") + CsvEscape(size) + _T(",")
            + CsvEscape(StateText(m_rows[i])) + _T(",") + CsvEscape(DateText(m_rows[i].lastSeen)) + _T(",")
            + CsvEscape(peers) + _T(",") + CsvEscape(CString(m_rows[i].localPath)) + _T(",")
            + CsvEscape(HashText(m_rows[i].fileHash)) + _T("\r\n");
#ifdef _UNICODE
        file.Write(line.GetString(), static_cast<UINT>(line.GetLength() * sizeof(wchar_t)));
#else
        file.Write(line.GetString(), line.GetLength());
#endif
        ++written;
    }
    file.Close();
    CString status; status.Format(_T("Exported %u Library rows."), written); m_status.SetWindowText(status);
}

void CFileLibraryWnd::OnContextMenu(CWnd* wnd, CPoint point)
{
    (void)wnd;
    const std::vector<size_t> selected = SelectedIndices();
    if (selected.empty())
        return;
    if (point.x == -1 && point.y == -1) {
        const int item = m_results.GetNextItem(-1, LVNI_SELECTED);
        CRect rect; if (item >= 0 && m_results.GetItemRect(item, &rect, LVIR_BOUNDS)) {
            point = rect.CenterPoint(); m_results.ClientToScreen(&point);
        }
    }
    CMenu menu; menu.CreatePopupMenu();
    menu.AppendMenu(MF_STRING, ID_EN_LIBRARY_CTX_FAVORITE, _T("Favorite selected"));
    menu.AppendMenu(MF_STRING, ID_EN_LIBRARY_CTX_UNFAVORITE, _T("Unfavorite selected"));
    menu.AppendMenu(MF_SEPARATOR);
    menu.AppendMenu(MF_STRING, ID_EN_LIBRARY_CTX_LATER, _T("Add selected to Download Later"));
    menu.AppendMenu(MF_STRING, ID_EN_LIBRARY_CTX_UNLATER, _T("Remove selected from Download Later"));
    menu.AppendMenu(MF_STRING, ID_EN_LIBRARY_CTX_DOWNLOAD, _T("Download selected again"));
    if (selected.size() == 1 && m_rows[selected[0]].completed && m_rows[selected[0]].missing)
        menu.AppendMenu(MF_STRING, ID_EN_LIBRARY_CTX_RELINK, _T("Relink missing file..."));
    if (selected.size() == 1 && !m_rows[selected[0]].localPath.IsEmpty() && !m_rows[selected[0]].missing)
        menu.AppendMenu(MF_STRING, ID_EN_LIBRARY_CTX_LOCATION, _T("Open location"));
    menu.AppendMenu(MF_SEPARATOR);
    menu.AppendMenu(MF_STRING, ID_EN_LIBRARY_CTX_EXPORT_SELECTED, _T("Export selected"));
    menu.AppendMenu(MF_STRING, ID_EN_LIBRARY_CTX_EXPORT_ALL, _T("Export current view"));
    const UINT command = menu.TrackPopupMenu(TPM_RETURNCMD | TPM_RIGHTBUTTON, point.x, point.y, this);
    switch (command) {
    case ID_EN_LIBRARY_CTX_FAVORITE: SetFavoriteSelected(true); break;
    case ID_EN_LIBRARY_CTX_UNFAVORITE: SetFavoriteSelected(false); break;
    case ID_EN_LIBRARY_CTX_LATER: SetDownloadLaterSelected(true); break;
    case ID_EN_LIBRARY_CTX_UNLATER: SetDownloadLaterSelected(false); break;
    case ID_EN_LIBRARY_CTX_DOWNLOAD: DownloadSelectedAgain(); break;
    case ID_EN_LIBRARY_CTX_RELINK: OnRelinkClicked(); break;
    case ID_EN_LIBRARY_CTX_LOCATION: OnOpenLocationClicked(); break;
    case ID_EN_LIBRARY_CTX_EXPORT_SELECTED: ExportRows(true); break;
    case ID_EN_LIBRARY_CTX_EXPORT_ALL: ExportRows(false); break;
    default: break;
    }
}

void CFileLibraryWnd::LoadViewState()
{
    int view = theApp.GetProfileInt(PROFILE_SECTION, _T("View"), ENLV_HISTORY);
    if (view < ENLV_HISTORY || view > ENLV_DOWNLOAD_LATER) view = ENLV_HISTORY;
    m_viewFilter = static_cast<EmuleNextLibraryViewFilter>(view);
    m_sortColumn = theApp.GetProfileInt(PROFILE_SECTION, _T("SortColumn"), 3);
    if (m_sortColumn < 0 || m_sortColumn >= LIBRARY_COLUMN_COUNT) m_sortColumn = 3;
    m_sortAscending = theApp.GetProfileInt(PROFILE_SECTION, _T("SortAscending"), 0) != 0;
    m_textFilterState = theApp.GetProfileString(PROFILE_SECTION, _T("TextFilter"), _T(""));
}

void CFileLibraryWnd::SaveViewState()
{
    theApp.WriteProfileInt(PROFILE_SECTION, _T("View"), static_cast<int>(m_viewFilter));
    theApp.WriteProfileInt(PROFILE_SECTION, _T("SortColumn"), m_sortColumn);
    theApp.WriteProfileInt(PROFILE_SECTION, _T("SortAscending"), m_sortAscending ? 1 : 0);
    CString text; if (::IsWindow(m_textFilter.m_hWnd)) m_textFilter.GetWindowText(text); else text = m_textFilterState;
    theApp.WriteProfileString(PROFILE_SECTION, _T("TextFilter"), text);
    if (::IsWindow(m_results.m_hWnd)) {
        for (int i = 0; i < LIBRARY_COLUMN_COUNT; ++i) {
            CString key; key.Format(_T("ColumnWidth%d"), i);
            theApp.WriteProfileInt(PROFILE_SECTION, key, m_results.GetColumnWidth(i));
        }
    }
}

void CFileLibraryWnd::ApplyColumnWidths()
{
    if (!::IsWindow(m_results.m_hWnd)) return;
    for (int i = 0; i < LIBRARY_COLUMN_COUNT; ++i) {
        CString key; key.Format(_T("ColumnWidth%d"), i);
        const int stored = theApp.GetProfileInt(PROFILE_SECTION, key, 0);
        if (stored >= CEmuleNextUiMetrics::Scale(m_hWnd, 36) && stored <= CEmuleNextUiMetrics::Scale(m_hWnd, 900))
            m_results.SetColumnWidth(i, stored);
    }
}

CString CFileLibraryWnd::HashText(const EmuleNextHash16& hash)
{
    CString result;
    if (!hash.valid) return result;
    for (size_t i = 0; i < hash.bytes.size(); ++i) {
        CString pair; pair.Format(_T("%02X"), static_cast<unsigned>(hash.bytes[i])); result += pair;
    }
    return result;
}

CString CFileLibraryWnd::DateText(uint64 timestamp)
{
    if (timestamp == 0) return CString();
    CTime value(static_cast<time_t>(timestamp));
    return value.Format(_T("%Y-%m-%d %H:%M"));
}
'''


def write_file(name: str, content: str) -> None:
    path = SRC / name
    if not path.exists():
        raise SystemExit(f"Library 2 product: missing {path}")
    path.write_bytes(content.encode("utf-8"))


def main() -> int:
    write_file("FileLibraryWnd.h", HEADER)
    write_file("FileLibraryWnd.cpp", CPP)
    write_file("LibraryBrowserService.h", SERVICE_HEADER)
    write_file("LibraryBrowserService.cpp", SERVICE_CPP)
    print("Library 2.0 product UI, background path verification, recovery and availability model materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
