#!/usr/bin/env python3
"""Materialize the complete Search 2.0 product surface.

The legacy eD2K/Kad search engine remains authoritative. Search 2 takes a
bounded snapshot of the currently visible legacy result list and merges it by
ED2K hash + size with the historical database result set in its existing
background worker. No network/protocol path is replaced or duplicated.
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
SERVICE_H = SRC / "Search2Service.h"
SERVICE_CPP = SRC / "Search2Service.cpp"
WND_H = SRC / "Search2Wnd.h"
WND_CPP = SRC / "Search2Wnd.cpp"


def read(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def write(path: pathlib.Path, text: str, encoding: str) -> None:
    path.write_bytes(text.encode(encoding))


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f"Search 2 product: anchor missing: {label}")
    return text.replace(old, new, 1)


def insert_after(text: str, anchor: str, addition: str, marker: str) -> str:
    if marker in text:
        return text
    if anchor not in text:
        raise SystemExit(f"Search 2 product: insertion anchor missing for {marker}")
    return text.replace(anchor, anchor + addition, 1)


def patch_service_header() -> None:
    text, enc = read(SERVICE_H)
    if "ENS2_SOURCE_LIVE_ED2K" not in text:
        anchor = '''enum EmuleNextSearchBlockRuleType
{
    ENSBR_NAME_CONTAINS = 0,
    ENSBR_EXTENSION,
    ENSBR_REGEX
};
'''
        addition = '''

enum EmuleNextSearchSourceFlags
{
    ENS2_SOURCE_NONE = 0,
    ENS2_SOURCE_LIVE_ED2K = 1 << 0,
    ENS2_SOURCE_LIVE_KAD = 1 << 1,
    ENS2_SOURCE_HISTORICAL = 1 << 2,
    ENS2_SOURCE_PREVIOUSLY_DOWNLOADED = 1 << 3,
    ENS2_SOURCE_KNOWN_PEER = 1 << 4
};

struct EmuleNextSearchBlockRule
{
    EmuleNextSearchBlockRuleType type;
    CString pattern;
    CString reason;
    uint64 createdAt;
    EmuleNextSearchBlockRule() : type(ENSBR_NAME_CONTAINS), createdAt(0) {}
};

struct EmuleNextUnifiedSearchResult : public EmuleNextSearchFileResult
{
    uint32 sourceFlags;
    uint32 liveSourceCount;
    EmuleNextUnifiedSearchResult() : sourceFlags(ENS2_SOURCE_NONE), liveSourceCount(0) {}
};
'''
        text = text.replace(anchor, anchor + addition, 1)

    filter_old = '''    uint64 minSize;
    uint64 maxSize;
    bool excludePreviouslyDownloaded;'''
    filter_new = '''    uint64 minSize;
    uint64 maxSize;
    CString extension;
    uint64 lastSeenAfter;
    uint32 minSources;
    uint32 maxSources;
    bool excludePreviouslyDownloaded;'''
    text = replace_once(text, filter_old, filter_new, "extended filter fields")

    if "LoadRules(std::vector<EmuleNextSearchBlockRule>& rules) const;" not in text:
        anchor = "    bool IsBlockedByRule(const EmuleNextSearchFileResult& file) const;"
        text = insert_after(text, anchor, "\n    bool LoadRules(std::vector<EmuleNextSearchBlockRule>& rules) const;", "LoadRules(std::vector<EmuleNextSearchBlockRule>& rules) const;")
    write(SERVICE_H, text, enc)


def patch_service_cpp() -> None:
    text, enc = read(SERVICE_CPP)

    ctor_old = '''EmuleNextSearchFilter::EmuleNextSearchFilter()
    : minSize(0)
    , maxSize(0)
    , excludePreviouslyDownloaded(false)'''
    ctor_new = '''EmuleNextSearchFilter::EmuleNextSearchFilter()
    : minSize(0)
    , maxSize(0)
    , lastSeenAfter(0)
    , minSources(0)
    , maxSources(0)
    , excludePreviouslyDownloaded(false)'''
    text = replace_once(text, ctor_old, ctor_new, "filter constructor")

    if "v2;%I64u;%I64u;%u;%u;%u;%s;%I64u;%u;%u" not in text:
        pattern = re.compile(r"    CString EncodeFilter\(const EmuleNextSearchFilter& filter\)\n    \{.*?\n    \}\n\n    EmuleNextSearchFilter DecodeFilter\(const CString& value\)\n    \{.*?\n    \}\n", re.S)
        replacement = r'''    CString EncodeFilter(const EmuleNextSearchFilter& filter)
    {
        CString extension(filter.extension);
        extension.Replace(_T(";"), _T(""));
        CString value;
        value.Format(_T("v2;%I64u;%I64u;%u;%u;%u;%s;%I64u;%u;%u"),
            filter.minSize, filter.maxSize,
            filter.excludePreviouslyDownloaded ? 1U : 0U,
            filter.favoritesOnly ? 1U : 0U,
            filter.missingOnly ? 1U : 0U,
            static_cast<LPCTSTR>(extension), filter.lastSeenAfter,
            filter.minSources, filter.maxSources);
        return value;
    }

    EmuleNextSearchFilter DecodeFilter(const CString& value)
    {
        EmuleNextSearchFilter filter;
        if (value.Left(3) == _T("v2;")) {
            int pos = 0;
            CString token = value.Tokenize(_T(";"), pos); // v2
            token = value.Tokenize(_T(";"), pos); filter.minSize = _tstoi64(token);
            token = value.Tokenize(_T(";"), pos); filter.maxSize = _tstoi64(token);
            token = value.Tokenize(_T(";"), pos); filter.excludePreviouslyDownloaded = _ttoi(token) != 0;
            token = value.Tokenize(_T(";"), pos); filter.favoritesOnly = _ttoi(token) != 0;
            token = value.Tokenize(_T(";"), pos); filter.missingOnly = _ttoi(token) != 0;
            filter.extension = value.Tokenize(_T(";"), pos);
            token = value.Tokenize(_T(";"), pos); filter.lastSeenAfter = _tstoi64(token);
            token = value.Tokenize(_T(";"), pos); filter.minSources = static_cast<uint32>(_ttoi(token));
            token = value.Tokenize(_T(";"), pos); filter.maxSources = static_cast<uint32>(_ttoi(token));
            return filter;
        }

        unsigned downloaded = 0;
        unsigned favorite = 0;
        unsigned missing = 0;
        uint64 minimum = 0;
        uint64 maximum = 0;
        if (_stscanf(value,
            _T("{\"min\":%I64u,\"max\":%I64u,\"downloaded\":%u,\"favorite\":%u,\"missing\":%u}"),
            &minimum, &maximum, &downloaded, &favorite, &missing) == 5) {
            filter.minSize = minimum;
            filter.maxSize = maximum;
            filter.excludePreviouslyDownloaded = downloaded != 0;
            filter.favoritesOnly = favorite != 0;
            filter.missingOnly = missing != 0;
        }
        return filter;
    }
'''
        text, count = pattern.subn(replacement, text, count=1)
        if count != 1:
            raise SystemExit("Search 2 product: filter codec function block not found")

    filter_anchor = '''    if (filter.maxSize != 0 && file.fileSize > filter.maxSize)
        return false;
'''
    filter_add = '''    if (!filter.extension.IsEmpty()) {
        CString extension(filter.extension);
        if (extension[0] != _T('.'))
            extension.Insert(0, _T('.'));
        if (CString(file.fileName).Right(extension.GetLength()).CompareNoCase(extension) != 0)
            return false;
    }
    if (filter.lastSeenAfter != 0 && file.lastSeen < filter.lastSeenAfter)
        return false;
    if (filter.minSources != 0 && file.historicalPeerCount < filter.minSources)
        return false;
    if (filter.maxSources != 0 && file.historicalPeerCount > filter.maxSources)
        return false;
'''
    if "filter.lastSeenAfter != 0" not in text:
        if filter_anchor not in text:
            raise SystemExit("Search 2 product: filter body anchor missing")
        text = text.replace(filter_anchor, filter_anchor + filter_add, 1)

    if "CSearch2Service::LoadRules(std::vector<EmuleNextSearchBlockRule>& rules) const" not in text:
        anchor = "bool CSearch2Service::IsBlockedByRule(const EmuleNextSearchFileResult& file) const\n"
        pos = text.find(anchor)
        if pos < 0:
            raise SystemExit("Search 2 product: IsBlockedByRule anchor missing")
        method = '''bool CSearch2Service::LoadRules(std::vector<EmuleNextSearchBlockRule>& rules) const
{
    rules.clear();
    if (!EnsureSchema())
        return false;
    sqlite3* db = OpenSearchDb(m_database.GetDatabasePath());
    if (db == NULL)
        return false;
    sqlite3_stmt* stmt = NULL;
    bool ok = sqlite3_prepare_v2(db,
        "SELECT rule_type,pattern,COALESCE(reason,''),created_at FROM search_block_rules ORDER BY created_at DESC,id DESC",
        -1, &stmt, NULL) == SQLITE_OK;
    while (ok && sqlite3_step(stmt) == SQLITE_ROW) {
        EmuleNextSearchBlockRule rule;
        rule.type = static_cast<EmuleNextSearchBlockRuleType>(sqlite3_column_int(stmt, 0));
        rule.pattern = ColumnCString(stmt, 1);
        rule.reason = ColumnCString(stmt, 2);
        rule.createdAt = static_cast<uint64>(sqlite3_column_int64(stmt, 3));
        rules.push_back(rule);
    }
    if (stmt != NULL)
        sqlite3_finalize(stmt);
    sqlite3_close(db);
    return ok;
}

'''
        text = text[:pos] + method + text[pos:]

    write(SERVICE_CPP, text, enc)


def patch_wnd_header() -> None:
    text, enc = read(WND_H)
    if "OnSearch2ColumnClick" not in text:
        anchor = "    afx_msg void OnResultSelectionChanged(NMHDR* header, LRESULT* result);"
        addition = '''
    afx_msg void OnSearch2ColumnClick(NMHDR* header, LRESULT* result);
    afx_msg void OnSearch2ContextMenu(CWnd* wnd, CPoint point);
    afx_msg void OnExportClicked();
    afx_msg void OnRulesClicked();'''
        text = insert_after(text, anchor, addition, "OnSearch2ColumnClick")

    if "SnapshotLiveResults" not in text:
        anchor = "    void PopulateResults();"
        addition = '''
    void SnapshotLiveResults(std::vector<EmuleNextUnifiedSearchResult>& rows) const;
    void SortRows();
    CString SourceText(const EmuleNextUnifiedSearchResult& row) const;
    void ExportRows(bool selectedOnly);
    void ShowRulesMenu(CPoint point);'''
        text = insert_after(text, anchor, addition, "SnapshotLiveResults")

    controls_anchor = "    CButton m_missingOnly;"
    controls_add = '''
    CStatic m_extensionLabel;
    CEdit m_extension;
    CStatic m_minSizeLabel;
    CEdit m_minSize;
    CStatic m_maxSizeLabel;
    CEdit m_maxSize;
    CStatic m_lastSeenLabel;
    CComboBox m_lastSeen;
    CStatic m_sourcesLabel;
    CEdit m_minSources;
    CStatic m_savedMeta;'''
    if "CEdit m_extension;" not in text:
        text = insert_after(text, controls_anchor, controls_add, "CEdit m_extension;")

    if "CButton m_export;" not in text:
        anchor = "    CButton m_block;"
        text = insert_after(text, anchor, "\n    CButton m_export;\n    CButton m_rules;", "CButton m_export;")

    text = text.replace("std::vector<EmuleNextSearchFileResult> m_rows;", "std::vector<EmuleNextUnifiedSearchResult> m_rows;")
    if "int m_sortColumn;" not in text:
        anchor = "    bool m_actionLoading;" if "    bool m_actionLoading;" in text else "    bool m_loading;"
        text = insert_after(text, anchor, "\n    int m_sortColumn;\n    bool m_sortAscending;", "int m_sortColumn;")
    write(WND_H, text, enc)


def patch_wnd_cpp() -> None:
    text, enc = read(WND_CPP)
    if '#include "SearchFile.h"' not in text:
        text = text.replace('#include "emule.h"', '#include "emule.h"\n#include "SearchResultsWnd.h"\n#include "SearchListCtrl.h"\n#include "SearchFile.h"', 1)
    if "#include <algorithm>" not in text:
        text = text.replace("#include <memory>", "#include <memory>\n#include <algorithm>", 1)

    enum_anchor = "        IDC_EN_SEARCH2_BLOCK\n"
    if "IDC_EN_SEARCH2_EXPORT" not in text:
        text = text.replace(enum_anchor, "        IDC_EN_SEARCH2_BLOCK,\n        IDC_EN_SEARCH2_EXPORT,\n        IDC_EN_SEARCH2_RULES\n", 1)

    if "std::vector<EmuleNextUnifiedSearchResult> liveRows;" not in text:
        old = '''    struct SearchContext
    {
        HWND target;
        EmuleNextSearchRequest request;
        CString savedSearchName;
    };'''
        new = '''    struct SearchContext
    {
        HWND target;
        EmuleNextSearchRequest request;
        CString savedSearchName;
        uint64 savedLastResultSeen;
        std::vector<EmuleNextUnifiedSearchResult> liveRows;
        SearchContext() : target(NULL), savedLastResultSeen(0) {}
    };'''
        text = replace_once(text, old, new, "SearchContext")

    result_old = '''    struct SearchResult
    {
        bool ok;
        std::vector<EmuleNextSearchFileResult> rows;
        SearchResult() : ok(false) {}
    };'''
    result_new = '''    struct SearchResult
    {
        bool ok;
        uint32 newSinceLastRun;
        std::vector<EmuleNextUnifiedSearchResult> rows;
        SearchResult() : ok(false), newSinceLastRun(0) {}
    };'''
    text = replace_once(text, result_old, result_new, "SearchResult")

    worker_old = '''        CSearch2Service service(theEmuleNext.Database());
        result->ok = service.SearchHistory(context->request, result->rows);
        if (result->ok && !context->savedSearchName.IsEmpty()) {
            uint64 newestSeen = 0;
            for (size_t i = 0; i < result->rows.size(); ++i) {
                if (result->rows[i].lastSeen > newestSeen)
                    newestSeen = result->rows[i].lastSeen;
            }
            service.MarkSearchRun(context->savedSearchName, newestSeen);
        }'''
    worker_new = '''        CSearch2Service service(theEmuleNext.Database());
        std::vector<EmuleNextSearchFileResult> historical;
        result->ok = service.SearchHistory(context->request, historical);
        if (result->ok) {
            result->rows = context->liveRows;
            for (size_t i = 0; i < historical.size(); ++i) {
                EmuleNextUnifiedSearchResult row;
                static_cast<EmuleNextSearchFileResult&>(row) = historical[i];
                row.sourceFlags = ENS2_SOURCE_HISTORICAL;
                if (row.completedBefore)
                    row.sourceFlags |= ENS2_SOURCE_PREVIOUSLY_DOWNLOADED;
                if (row.historicalPeerCount > 0)
                    row.sourceFlags |= ENS2_SOURCE_KNOWN_PEER;
                bool merged = false;
                for (size_t j = 0; j < result->rows.size(); ++j) {
                    EmuleNextUnifiedSearchResult& existing = result->rows[j];
                    if (existing.fileHash.valid && row.fileHash.valid
                        && existing.fileHash.bytes == row.fileHash.bytes && existing.fileSize == row.fileSize) {
                        existing.sourceFlags |= row.sourceFlags;
                        existing.favorite = existing.favorite || row.favorite;
                        existing.completedBefore = existing.completedBefore || row.completedBefore;
                        existing.historicalPeerCount = max(existing.historicalPeerCount, row.historicalPeerCount);
                        existing.firstSeen = existing.firstSeen == 0 ? row.firstSeen : min(existing.firstSeen, row.firstSeen);
                        existing.lastSeen = max(existing.lastSeen, row.lastSeen);
                        merged = true;
                        break;
                    }
                }
                if (!merged)
                    result->rows.push_back(row);
            }
        }
        if (result->ok && !context->savedSearchName.IsEmpty()) {
            uint64 newestSeen = 0;
            for (size_t i = 0; i < result->rows.size(); ++i) {
                if (result->rows[i].lastSeen > newestSeen)
                    newestSeen = result->rows[i].lastSeen;
                if (context->savedLastResultSeen != 0 && result->rows[i].lastSeen > context->savedLastResultSeen)
                    ++result->newSinceLastRun;
            }
            service.MarkSearchRun(context->savedSearchName, newestSeen);
        }'''
    text = replace_once(text, worker_old, worker_new, "unified worker merge")

    if "ON_NOTIFY(LVN_COLUMNCLICK, IDC_EN_SEARCH2_RESULTS" not in text:
        anchor = "    ON_NOTIFY(LVN_ITEMCHANGED, IDC_EN_SEARCH2_RESULTS, OnResultSelectionChanged)"
        text = insert_after(text, anchor, "\n    ON_NOTIFY(LVN_COLUMNCLICK, IDC_EN_SEARCH2_RESULTS, OnSearch2ColumnClick)\n    ON_WM_CONTEXTMENU()\n    ON_BN_CLICKED(IDC_EN_SEARCH2_EXPORT, OnExportClicked)\n    ON_BN_CLICKED(IDC_EN_SEARCH2_RULES, OnRulesClicked)", "ON_NOTIFY(LVN_COLUMNCLICK, IDC_EN_SEARCH2_RESULTS")

    if "m_sortColumn(-1)" not in text:
        text = re.sub(r"(CSearch2Wnd::CSearch2Wnd\(\)\n    : m_loading\(false\).*?)(\n\{\n\})", lambda m: m.group(1) + "\n    , m_sortColumn(-1)\n    , m_sortAscending(true)" + m.group(2), text, count=1, flags=re.S)

    create_anchor = '''        || !m_missingOnly.Create(_T("Missing only"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX,
            empty, this, IDC_EN_SEARCH2_MISSING)'''
    create_add = '''
        || !m_extensionLabel.Create(_T("Ext"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_extension.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | WS_BORDER | ES_AUTOHSCROLL, empty, this, 0x7E70)
        || !m_minSizeLabel.Create(_T("Min MB"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_minSize.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | WS_BORDER | ES_AUTOHSCROLL, empty, this, 0x7E71)
        || !m_maxSizeLabel.Create(_T("Max MB"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_maxSize.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | WS_BORDER | ES_AUTOHSCROLL, empty, this, 0x7E72)
        || !m_lastSeenLabel.Create(_T("Seen"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_lastSeen.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST, empty, this, 0x7E73)
        || !m_sourcesLabel.Create(_T("Min peers"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_minSources.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | WS_BORDER | ES_AUTOHSCROLL, empty, this, 0x7E74)
        || !m_savedMeta.Create(_T(""), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)'''
    if "!m_extension.Create(" not in text:
        if create_anchor not in text:
            raise SystemExit("Search 2 product: filter control create anchor missing")
        text = text.replace(create_anchor, create_anchor + create_add, 1)

    block_create = '''        || !m_block.Create(_T("Block hash"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_SEARCH2_BLOCK)) {'''
    block_new = '''        || !m_block.Create(_T("Block hash"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_SEARCH2_BLOCK)
        || !m_export.Create(_T("Export"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_SEARCH2_EXPORT)
        || !m_rules.Create(_T("Block rules"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
            empty, this, IDC_EN_SEARCH2_RULES)) {'''
    text = replace_once(text, block_create, block_new, "action control creation")

    font_anchor = "    m_favorite.SetFont(font); m_downloadLater.SetFont(font); m_block.SetFont(font);"
    font_new = '''    m_favorite.SetFont(font); m_downloadLater.SetFont(font); m_block.SetFont(font);
    m_extensionLabel.SetFont(font); m_extension.SetFont(font); m_minSizeLabel.SetFont(font); m_minSize.SetFont(font);
    m_maxSizeLabel.SetFont(font); m_maxSize.SetFont(font); m_lastSeenLabel.SetFont(font); m_lastSeen.SetFont(font);
    m_sourcesLabel.SetFont(font); m_minSources.SetFont(font); m_savedMeta.SetFont(font);
    m_export.SetFont(font); m_rules.SetFont(font);'''
    text = replace_once(text, font_anchor, font_new, "font setup")

    if "Last 24 hours" not in text:
        anchor = "    m_results.SetExtendedStyle(LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_GRIDLINES);"
        add = '''
    m_lastSeen.AddString(_T("Any time")); m_lastSeen.SetItemData(0, 0);
    m_lastSeen.AddString(_T("Last 24 hours")); m_lastSeen.SetItemData(1, 24 * 60 * 60);
    m_lastSeen.AddString(_T("Last 7 days")); m_lastSeen.SetItemData(2, 7 * 24 * 60 * 60);
    m_lastSeen.AddString(_T("Last 30 days")); m_lastSeen.SetItemData(3, 30 * 24 * 60 * 60);
    m_lastSeen.SetCurSel(0);'''
        text = insert_after(text, anchor, add, "Last 24 hours")

    text = text.replace("LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS", "LVS_REPORT | LVS_SHOWSELALWAYS")
    cols_old = '''    m_results.InsertColumn(3, _T("Last seen"), LVCFMT_LEFT, 135);
    m_results.InsertColumn(4, _T("Favorite"), LVCFMT_LEFT, 70);
    m_results.InsertColumn(5, _T("Downloaded"), LVCFMT_LEFT, 80);
    m_results.InsertColumn(6, _T("ED2K hash"), LVCFMT_LEFT, 245);'''
    cols_new = '''    m_results.InsertColumn(3, _T("Last seen"), LVCFMT_LEFT, 135);
    m_results.InsertColumn(4, _T("Source"), LVCFMT_LEFT, 185);
    m_results.InsertColumn(5, _T("Favorite"), LVCFMT_LEFT, 70);
    m_results.InsertColumn(6, _T("Downloaded"), LVCFMT_LEFT, 80);
    m_results.InsertColumn(7, _T("ED2K hash"), LVCFMT_LEFT, 245);'''
    text = replace_once(text, cols_old, cols_new, "provenance column")

    # Replace compact legacy layout with a two-row filter layout and action row.
    layout_pattern = re.compile(r"void CSearch2Wnd::LayoutControls\(int cx, int cy\)\n\{.*?\n\}\n\nBOOL CSearch2Wnd::OnEraseBkgnd", re.S)
    layout_new = '''void CSearch2Wnd::LayoutControls(int cx, int cy)
{
    const int margin = 12;
    const int queryTop = 58;
    const int queryHeight = 26;
    const int filterTop = 92;
    const int filter2Top = 120;
    const int statusTop = 150;
    const int listTop = 174;
    const int searchWidth = 104;
    const int actionHeight = 30;
    const int actionTop = max(listTop + 70, cy - margin - actionHeight);
    const int listHeight = max(60, actionTop - listTop - 8);

    m_title.MoveWindow(margin, 10, max(160, cx - margin * 2), 22);
    m_subtitle.MoveWindow(margin, 34, max(160, cx - margin * 2), 18);
    m_search.MoveWindow(max(margin, cx - margin - searchWidth), queryTop, searchWidth, queryHeight);
    m_query.MoveWindow(margin, queryTop, max(120, cx - margin * 3 - searchWidth), queryHeight);

    m_hideDownloaded.MoveWindow(margin, filterTop + 2, 124, 20);
    m_favoritesOnly.MoveWindow(margin + 132, filterTop + 2, 108, 20);
    m_missingOnly.MoveWindow(margin + 248, filterTop + 2, 96, 20);
    m_extensionLabel.MoveWindow(margin + 350, filterTop + 4, 26, 18);
    m_extension.MoveWindow(margin + 378, filterTop, 62, 24);
    m_minSizeLabel.MoveWindow(margin + 448, filterTop + 4, 48, 18);
    m_minSize.MoveWindow(margin + 498, filterTop, 62, 24);
    m_maxSizeLabel.MoveWindow(margin + 568, filterTop + 4, 50, 18);
    m_maxSize.MoveWindow(margin + 620, filterTop, 62, 24);

    m_lastSeenLabel.MoveWindow(margin, filter2Top + 4, 34, 18);
    m_lastSeen.MoveWindow(margin + 36, filter2Top, 120, 220);
    m_sourcesLabel.MoveWindow(margin + 164, filter2Top + 4, 60, 18);
    m_minSources.MoveWindow(margin + 226, filter2Top, 54, 24);
    const int savedLeft = max(margin + 290, cx - margin - 450);
    m_savedSearchLabel.MoveWindow(savedLeft, filter2Top + 4, 82, 18);
    m_savedSearch.MoveWindow(savedLeft + 84, filter2Top, 170, 220);
    m_saveSearch.MoveWindow(savedLeft + 260, filter2Top, 54, 24);
    m_deleteSearch.MoveWindow(savedLeft + 320, filter2Top, 58, 24);
    m_savedMeta.MoveWindow(savedLeft, filter2Top + 25, 378, 18);

    m_status.MoveWindow(margin, statusTop, max(100, cx - margin * 2), 18);
    m_results.MoveWindow(margin, listTop, max(0, cx - margin * 2), listHeight);
    m_favorite.MoveWindow(margin, actionTop, 108, actionHeight);
    m_downloadLater.MoveWindow(margin + 116, actionTop, 112, actionHeight);
    m_block.MoveWindow(margin + 236, actionTop, 96, actionHeight);
    m_export.MoveWindow(margin + 340, actionTop, 90, actionHeight);
    m_rules.MoveWindow(margin + 438, actionTop, 104, actionHeight);
}

BOOL CSearch2Wnd::OnEraseBkgnd'''
    text, count = layout_pattern.subn(layout_new, text, count=1)
    if count != 1 and "const int filter2Top = 120;" not in text:
        raise SystemExit("Search 2 product: layout function not found")

    current_pattern = re.compile(r"EmuleNextSearchFilter CSearch2Wnd::CurrentFilter\(\) const\n\{.*?\n\}", re.S)
    current_new = '''EmuleNextSearchFilter CSearch2Wnd::CurrentFilter() const
{
    EmuleNextSearchFilter filter;
    filter.excludePreviouslyDownloaded = m_hideDownloaded.GetCheck() == BST_CHECKED;
    filter.favoritesOnly = m_favoritesOnly.GetCheck() == BST_CHECKED;
    filter.missingOnly = m_missingOnly.GetCheck() == BST_CHECKED;
    m_extension.GetWindowText(filter.extension); filter.extension.Trim();
    CString value;
    m_minSize.GetWindowText(value); value.Trim();
    if (!value.IsEmpty()) filter.minSize = static_cast<uint64>(_tstof(value) * 1024.0 * 1024.0);
    m_maxSize.GetWindowText(value); value.Trim();
    if (!value.IsEmpty()) filter.maxSize = static_cast<uint64>(_tstof(value) * 1024.0 * 1024.0);
    m_minSources.GetWindowText(value); value.Trim();
    if (!value.IsEmpty()) filter.minSources = static_cast<uint32>(max(0, _ttoi(value)));
    const int seen = m_lastSeen.GetCurSel();
    if (seen > 0) {
        const uint64 seconds = static_cast<uint64>(m_lastSeen.GetItemData(seen));
        const uint64 now = static_cast<uint64>(time(NULL));
        filter.lastSeenAfter = now > seconds ? now - seconds : 0;
    }
    return filter;
}'''
    text, count = current_pattern.subn(current_new, text, count=1)
    if count != 1 and "filter.lastSeenAfter" not in text:
        raise SystemExit("Search 2 product: CurrentFilter not found")

    apply_old = '''    m_missingOnly.SetCheck(search.filter.missingOnly ? BST_CHECKED : BST_UNCHECKED);'''
    apply_new = '''    m_missingOnly.SetCheck(search.filter.missingOnly ? BST_CHECKED : BST_UNCHECKED);
    m_extension.SetWindowText(search.filter.extension);
    CString value;
    if (search.filter.minSize != 0) { value.Format(_T("%.1f"), search.filter.minSize / 1048576.0); m_minSize.SetWindowText(value); } else m_minSize.SetWindowText(_T(""));
    if (search.filter.maxSize != 0) { value.Format(_T("%.1f"), search.filter.maxSize / 1048576.0); m_maxSize.SetWindowText(value); } else m_maxSize.SetWindowText(_T(""));
    if (search.filter.minSources != 0) { value.Format(_T("%u"), search.filter.minSources); m_minSources.SetWindowText(value); } else m_minSources.SetWindowText(_T(""));
    int seenSelection = 0;
    if (search.filter.lastSeenAfter != 0) {
        const uint64 age = static_cast<uint64>(time(NULL)) > search.filter.lastSeenAfter ? static_cast<uint64>(time(NULL)) - search.filter.lastSeenAfter : 0;
        seenSelection = age <= 2 * 24 * 60 * 60 ? 1 : (age <= 10 * 24 * 60 * 60 ? 2 : 3);
    }
    m_lastSeen.SetCurSel(seenSelection);
    CString meta;
    meta.Format(_T("Last run: %s"), static_cast<LPCTSTR>(DateText(search.lastRun)));
    m_savedMeta.SetWindowText(meta);'''
    text = replace_once(text, apply_old, apply_new, "saved filter restore")

    start_anchor = '''    context->request.maximumResults = 2000;
    context->request.pageSize = 500;'''
    start_add = '''
    SnapshotLiveResults(context->liveRows);'''
    if "SnapshotLiveResults(context->liveRows);" not in text:
        text = insert_after(text, start_anchor, start_add, "SnapshotLiveResults(context->liveRows);")
    saved_old = '''    if (savedIndex >= 0 && static_cast<size_t>(savedIndex) < m_savedSearches.size())
        context->savedSearchName = m_savedSearches[static_cast<size_t>(savedIndex)].name;'''
    saved_new = '''    if (savedIndex >= 0 && static_cast<size_t>(savedIndex) < m_savedSearches.size()) {
        context->savedSearchName = m_savedSearches[static_cast<size_t>(savedIndex)].name;
        context->savedLastResultSeen = m_savedSearches[static_cast<size_t>(savedIndex)].lastResultSeen;
    }'''
    text = replace_once(text, saved_old, saved_new, "saved search delta context")

    loaded_old = '''    m_rows.swap(result->rows);
    PopulateResults();
    CString text;
    text.Format(_T("%u files found."), static_cast<unsigned>(m_rows.size()));'''
    loaded_new = '''    m_rows.swap(result->rows);
    SortRows();
    PopulateResults();
    CString text;
    if (result->newSinceLastRun != 0)
        text.Format(_T("%u files found; %u new since last run."), static_cast<unsigned>(m_rows.size()), result->newSinceLastRun);
    else
        text.Format(_T("%u files found."), static_cast<unsigned>(m_rows.size()));'''
    text = replace_once(text, loaded_old, loaded_new, "saved search delta status")

    populate_old = '''        m_results.SetItemText(row, 3, DateText(file.lastSeen));
        m_results.SetItemText(row, 4, file.favorite ? _T("Yes") : _T(""));
        m_results.SetItemText(row, 5, file.completedBefore ? _T("Yes") : _T(""));
        m_results.SetItemText(row, 6, HashText(file.fileHash));'''
    populate_new = '''        m_results.SetItemText(row, 3, DateText(file.lastSeen));
        m_results.SetItemText(row, 4, SourceText(file));
        m_results.SetItemText(row, 5, file.favorite ? _T("Yes") : _T(""));
        m_results.SetItemText(row, 6, file.completedBefore ? _T("Yes") : _T(""));
        m_results.SetItemText(row, 7, HashText(file.fileHash));'''
    text = replace_once(text, populate_old, populate_new, "source column population")
    text = text.replace("const EmuleNextSearchFileResult& file = m_rows[i];", "const EmuleNextUnifiedSearchResult& file = m_rows[i];")
    text = text.replace("std::vector<EmuleNextSearchFileResult>::iterator it = m_rows.begin()", "std::vector<EmuleNextUnifiedSearchResult>::iterator it = m_rows.begin()")

    if "void CSearch2Wnd::SnapshotLiveResults" not in text:
        anchor = "CString CSearch2Wnd::HashText(const EmuleNextHash16& hash)"
        pos = text.find(anchor)
        if pos < 0:
            raise SystemExit("Search 2 product: helper insertion anchor missing")
        helpers = r'''void CSearch2Wnd::SnapshotLiveResults(std::vector<EmuleNextUnifiedSearchResult>& rows) const
{
    rows.clear();
    const CSearchResultsWnd* host = DYNAMIC_DOWNCAST(CSearchResultsWnd, GetParent());
    if (host == NULL)
        return;
    const int count = min(host->searchlistctrl.GetItemCount(), 2000);
    for (int i = 0; i < count; ++i) {
        const SearchCtrlItem_Struct* item = reinterpret_cast<const SearchCtrlItem_Struct*>(host->searchlistctrl.GetItemData(i));
        if (item == NULL || item->value == NULL || (item->owner != NULL && item->owner != item->value))
            continue;
        const CSearchFile* live = item->value;
        EmuleNextUnifiedSearchResult row;
        row.fileHash = EmuleNextHash16(live->GetFileHash());
        row.fileSize = live->GetFileSize();
        row.fileName = live->GetFileName();
        row.lastSeen = static_cast<uint64>(time(NULL));
        row.firstSeen = row.lastSeen;
        row.liveSourceCount = live->GetSourceCount();
        row.historicalPeerCount = row.liveSourceCount;
        row.sourceFlags = live->IsKademlia() ? ENS2_SOURCE_LIVE_KAD : ENS2_SOURCE_LIVE_ED2K;
        if (live->GetKnownType() == CSearchFile::Downloaded)
            row.sourceFlags |= ENS2_SOURCE_PREVIOUSLY_DOWNLOADED;
        row.completedBefore = (row.sourceFlags & ENS2_SOURCE_PREVIOUSLY_DOWNLOADED) != 0;
        bool duplicate = false;
        for (size_t j = 0; j < rows.size(); ++j) {
            if (rows[j].fileHash.valid && row.fileHash.valid && rows[j].fileHash.bytes == row.fileHash.bytes && rows[j].fileSize == row.fileSize) {
                rows[j].sourceFlags |= row.sourceFlags;
                rows[j].liveSourceCount = max(rows[j].liveSourceCount, row.liveSourceCount);
                rows[j].historicalPeerCount = max(rows[j].historicalPeerCount, row.historicalPeerCount);
                duplicate = true;
                break;
            }
        }
        if (!duplicate)
            rows.push_back(row);
    }
}

CString CSearch2Wnd::SourceText(const EmuleNextUnifiedSearchResult& row) const
{
    CString text;
    if (row.sourceFlags & ENS2_SOURCE_LIVE_ED2K) text += _T("Live eD2K");
    if (row.sourceFlags & ENS2_SOURCE_LIVE_KAD) { if (!text.IsEmpty()) text += _T(" + "); text += _T("Live Kad"); }
    if (row.sourceFlags & ENS2_SOURCE_HISTORICAL) { if (!text.IsEmpty()) text += _T(" + "); text += _T("Historical"); }
    if (row.sourceFlags & ENS2_SOURCE_PREVIOUSLY_DOWNLOADED) { if (!text.IsEmpty()) text += _T(" + "); text += _T("Previously downloaded"); }
    if (row.sourceFlags & ENS2_SOURCE_KNOWN_PEER) { if (!text.IsEmpty()) text += _T(" + "); text += _T("Known peer"); }
    return text;
}

void CSearch2Wnd::SortRows()
{
    if (m_sortColumn < 0)
        return;
    const int column = m_sortColumn;
    const bool ascending = m_sortAscending;
    std::stable_sort(m_rows.begin(), m_rows.end(), [column, ascending](const EmuleNextUnifiedSearchResult& a, const EmuleNextUnifiedSearchResult& b) {
        int compare = 0;
        switch (column) {
        case 0: compare = CString(a.fileName).CompareNoCase(CString(b.fileName)); break;
        case 1: compare = a.fileSize < b.fileSize ? -1 : (a.fileSize > b.fileSize ? 1 : 0); break;
        case 2: compare = a.historicalPeerCount < b.historicalPeerCount ? -1 : (a.historicalPeerCount > b.historicalPeerCount ? 1 : 0); break;
        case 3: compare = a.lastSeen < b.lastSeen ? -1 : (a.lastSeen > b.lastSeen ? 1 : 0); break;
        case 4: compare = a.sourceFlags < b.sourceFlags ? -1 : (a.sourceFlags > b.sourceFlags ? 1 : 0); break;
        case 5: compare = a.favorite == b.favorite ? 0 : (a.favorite ? 1 : -1); break;
        case 6: compare = a.completedBefore == b.completedBefore ? 0 : (a.completedBefore ? 1 : -1); break;
        default: break;
        }
        return ascending ? compare < 0 : compare > 0;
    });
}

void CSearch2Wnd::OnSearch2ColumnClick(NMHDR* header, LRESULT* result)
{
    const NMLISTVIEW* view = reinterpret_cast<const NMLISTVIEW*>(header);
    if (m_sortColumn == view->iSubItem)
        m_sortAscending = !m_sortAscending;
    else {
        m_sortColumn = view->iSubItem;
        m_sortAscending = true;
    }
    SortRows();
    PopulateResults();
    *result = 0;
}

void CSearch2Wnd::ExportRows(bool selectedOnly)
{
    CFileDialog dialog(FALSE, _T("csv"), _T("emule-next-search.csv"), OFN_OVERWRITEPROMPT,
        _T("CSV files (*.csv)|*.csv|All files (*.*)|*.*||"), this);
    if (dialog.DoModal() != IDOK)
        return;
    CStdioFile file;
    if (!file.Open(dialog.GetPathName(), CFile::modeCreate | CFile::modeWrite | CFile::typeText)) {
        m_status.SetWindowText(_T("Export could not be opened."));
        return;
    }
    file.WriteString(_T("Name;Size;Peers;Last seen;Source;Favorite;Downloaded;ED2K hash\n"));
    unsigned written = 0;
    for (int listIndex = 0; listIndex < m_results.GetItemCount(); ++listIndex) {
        if (selectedOnly && (m_results.GetItemState(listIndex, LVIS_SELECTED) & LVIS_SELECTED) == 0)
            continue;
        const size_t index = static_cast<size_t>(m_results.GetItemData(listIndex));
        if (index >= m_rows.size())
            continue;
        const EmuleNextUnifiedSearchResult& row = m_rows[index];
        CString name(row.fileName); name.Replace(_T(";"), _T(",")); name.Replace(_T("\r"), _T(" ")); name.Replace(_T("\n"), _T(" "));
        CString line;
        line.Format(_T("%s;%I64u;%u;%s;%s;%s;%s;%s\n"), static_cast<LPCTSTR>(name), row.fileSize,
            row.historicalPeerCount, static_cast<LPCTSTR>(DateText(row.lastSeen)), static_cast<LPCTSTR>(SourceText(row)),
            row.favorite ? _T("Yes") : _T("No"), row.completedBefore ? _T("Yes") : _T("No"), static_cast<LPCTSTR>(HashText(row.fileHash)));
        file.WriteString(line);
        ++written;
    }
    file.Close();
    CString status; status.Format(_T("Exported %u search results."), written); m_status.SetWindowText(status);
}

void CSearch2Wnd::OnExportClicked()
{
    const bool selected = m_results.GetSelectedCount() > 0;
    ExportRows(selected);
}

void CSearch2Wnd::ShowRulesMenu(CPoint point)
{
    CMenu menu; menu.CreatePopupMenu();
    const int index = SelectedIndex();
    if (index >= 0) {
        CString name(m_rows[static_cast<size_t>(index)].fileName);
        const int dot = name.ReverseFind(_T('.'));
        if (dot >= 0) {
            CString extension = name.Mid(dot);
            CString caption; caption.Format(_T("Block extension %s"), static_cast<LPCTSTR>(extension));
            menu.AppendMenu(MF_STRING, 0x7EA0, caption);
        }
        menu.AppendMenu(MF_STRING, 0x7EA1, _T("Block files containing this name"));
        menu.AppendMenu(MF_SEPARATOR);
    }
    CSearch2Service service(theEmuleNext.Database());
    std::vector<EmuleNextSearchBlockRule> rules;
    service.LoadRules(rules);
    if (rules.empty())
        menu.AppendMenu(MF_STRING | MF_GRAYED, 0, _T("No active block rules"));
    else {
        menu.AppendMenu(MF_STRING | MF_GRAYED, 0, _T("Remove rule:"));
        for (size_t i = 0; i < rules.size() && i < 100; ++i) {
            CString caption; caption.Format(_T("  %s"), static_cast<LPCTSTR>(rules[i].pattern));
            menu.AppendMenu(MF_STRING, static_cast<UINT>(0x7EB0 + i), caption);
        }
    }
    const UINT command = menu.TrackPopupMenu(TPM_RETURNCMD | TPM_NONOTIFY, point.x, point.y, this);
    if (command == 0)
        return;
    if (command == 0x7EA0 && index >= 0) {
        CString name(m_rows[static_cast<size_t>(index)].fileName); const int dot = name.ReverseFind(_T('.'));
        if (dot >= 0) service.AddRule(ENSBR_EXTENSION, name.Mid(dot), _T("Search 2 extension rule"));
    }
    else if (command == 0x7EA1 && index >= 0) {
        CString name(m_rows[static_cast<size_t>(index)].fileName);
        service.AddRule(ENSBR_NAME_CONTAINS, name, _T("Search 2 name rule"));
    }
    else if (command >= 0x7EB0 && command < 0x7EB0 + rules.size()) {
        const EmuleNextSearchBlockRule& rule = rules[command - 0x7EB0];
        service.RemoveRule(rule.type, rule.pattern);
    }
    StartSearch();
}

void CSearch2Wnd::OnRulesClicked()
{
    CRect rect; m_rules.GetWindowRect(&rect); ShowRulesMenu(CPoint(rect.left, rect.bottom));
}

void CSearch2Wnd::OnSearch2ContextMenu(CWnd* wnd, CPoint point)
{
    if (wnd != &m_results)
        return;
    if (point.x == -1 && point.y == -1) { CRect rect; m_results.GetWindowRect(&rect); point = rect.TopLeft(); point.Offset(20, 20); }
    CMenu menu; menu.CreatePopupMenu();
    menu.AppendMenu(MF_STRING, 0x7E90, _T("Export selected"));
    menu.AppendMenu(MF_STRING, 0x7E91, _T("Export all results"));
    menu.AppendMenu(MF_SEPARATOR);
    menu.AppendMenu(MF_STRING, 0x7E92, _T("Manage block rules..."));
    const UINT command = menu.TrackPopupMenu(TPM_RETURNCMD | TPM_NONOTIFY, point.x, point.y, this);
    if (command == 0x7E90) ExportRows(true);
    else if (command == 0x7E91) ExportRows(false);
    else if (command == 0x7E92) ShowRulesMenu(point);
}

'''
        text = text[:pos] + helpers + text[pos:]

    write(WND_CPP, text, enc)


def main() -> int:
    for path in (SERVICE_H, SERVICE_CPP, WND_H, WND_CPP):
        if not path.exists():
            raise SystemExit(f"Search 2 product: source missing: {path}")
    patch_service_header()
    patch_service_cpp()
    patch_wnd_header()
    patch_wnd_cpp()
    print("Search 2 unified live/history model, filters, sort, saved delta, export/context actions and block-rule management materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
