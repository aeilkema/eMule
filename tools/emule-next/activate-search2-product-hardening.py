#!/usr/bin/env python3
"""Harden the Search 2.0 product materialization.

Runs after activate-search2-product.py. It ensures live legacy rows obey the
same request filters as historical rows, applies block rules to the unified
result in the background worker, exposes a max-peers filter, and adds bounded
bulk Favorite/Download-Later actions without synchronous SQLite work.
"""
from __future__ import annotations

import pathlib

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
        raise SystemExit(f"Search 2 hardening: anchor missing: {label}")
    return text.replace(old, new, 1)


def patch_service() -> None:
    header, henc = read(SERVICE_H)
    marker = "bool FilterBlocked(std::vector<EmuleNextUnifiedSearchResult>& rows) const;"
    if marker not in header:
        anchor = "    bool LoadRules(std::vector<EmuleNextSearchBlockRule>& rules) const;"
        if anchor not in header:
            raise SystemExit("Search 2 hardening: LoadRules API missing")
        header = header.replace(anchor, anchor + "\n    " + marker, 1)
        write(SERVICE_H, header, henc)

    cpp, cenc = read(SERVICE_CPP)
    if "CSearch2Service::FilterBlocked(std::vector<EmuleNextUnifiedSearchResult>& rows) const" not in cpp:
        anchor = "bool CSearch2Service::IsBlockedByRule(const EmuleNextSearchFileResult& file) const\n"
        pos = cpp.find(anchor)
        if pos < 0:
            raise SystemExit("Search 2 hardening: IsBlockedByRule implementation missing")
        method = '''bool CSearch2Service::FilterBlocked(std::vector<EmuleNextUnifiedSearchResult>& rows) const
{
    if (!EnsureSchema())
        return false;
    sqlite3* db = OpenSearchDb(m_database.GetDatabasePath());
    if (db == NULL)
        return false;
    std::vector<SearchRule> rules;
    const bool ok = LoadRules(db, rules);
    sqlite3_close(db);
    if (!ok)
        return false;
    rows.erase(std::remove_if(rows.begin(), rows.end(), [&rules](const EmuleNextUnifiedSearchResult& row) {
        return MatchesAnyRule(row, rules);
    }), rows.end());
    return true;
}

'''
        cpp = cpp[:pos] + method + cpp[pos:]
        write(SERVICE_CPP, cpp, cenc)


def patch_header() -> None:
    text, enc = read(WND_H)
    text = text.replace(
        "    void SnapshotLiveResults(std::vector<EmuleNextUnifiedSearchResult>& rows) const;",
        "    void SnapshotLiveResults(const EmuleNextSearchRequest& request, std::vector<EmuleNextUnifiedSearchResult>& rows) const;")
    text = text.replace(
        "    afx_msg void OnSearch2ContextMenu(CWnd* wnd, CPoint point);",
        "    afx_msg void OnContextMenu(CWnd* wnd, CPoint point);")
    if "CEdit m_maxSources;" not in text:
        anchor = "    CEdit m_minSources;"
        if anchor not in text:
            raise SystemExit("Search 2 hardening: min source control missing")
        text = text.replace(anchor, anchor + "\n    CStatic m_maxSourcesLabel;\n    CEdit m_maxSources;", 1)
    if "void ApplyBulkAction(bool favorite);" not in text:
        anchor = "    void ShowRulesMenu(CPoint point);"
        if anchor not in text:
            raise SystemExit("Search 2 hardening: rules helper missing")
        text = text.replace(anchor, anchor + "\n    void ApplyBulkAction(bool favorite);", 1)
    write(WND_H, text, enc)


def patch_cpp() -> None:
    text, enc = read(WND_CPP)
    text = text.replace(
        "void CSearch2Wnd::OnSearch2ContextMenu(CWnd* wnd, CPoint point)",
        "void CSearch2Wnd::OnContextMenu(CWnd* wnd, CPoint point)")

    worker_anchor = '''                if (!merged)
                    result->rows.push_back(row);
            }
        }
        if (result->ok && !context->savedSearchName.IsEmpty()) {'''
    worker_new = '''                if (!merged)
                    result->rows.push_back(row);
            }
            result->ok = service.FilterBlocked(result->rows);
        }
        if (result->ok && !context->savedSearchName.IsEmpty()) {'''
    text = replace_once(text, worker_anchor, worker_new, "background unified rule filter")

    create_anchor = '''        || !m_sourcesLabel.Create(_T("Min peers"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_minSources.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | WS_BORDER | ES_AUTOHSCROLL, empty, this, 0x7E74)
        || !m_savedMeta.Create'''
    create_new = '''        || !m_sourcesLabel.Create(_T("Min peers"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_minSources.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | WS_BORDER | ES_AUTOHSCROLL, empty, this, 0x7E74)
        || !m_maxSourcesLabel.Create(_T("Max peers"), WS_CHILD | WS_VISIBLE | SS_LEFT, empty, this)
        || !m_maxSources.Create(WS_CHILD | WS_VISIBLE | WS_TABSTOP | WS_BORDER | ES_AUTOHSCROLL, empty, this, 0x7E75)
        || !m_savedMeta.Create'''
    text = replace_once(text, create_anchor, create_new, "max peer controls")

    font_anchor = "    m_sourcesLabel.SetFont(font); m_minSources.SetFont(font); m_savedMeta.SetFont(font);"
    font_new = "    m_sourcesLabel.SetFont(font); m_minSources.SetFont(font); m_maxSourcesLabel.SetFont(font); m_maxSources.SetFont(font); m_savedMeta.SetFont(font);"
    text = replace_once(text, font_anchor, font_new, "max peer fonts")

    layout_anchor = '''    m_sourcesLabel.MoveWindow(margin + 164, filter2Top + 4, 60, 18);
    m_minSources.MoveWindow(margin + 226, filter2Top, 54, 24);
    const int savedLeft = max(margin + 290, cx - margin - 450);'''
    layout_new = '''    m_sourcesLabel.MoveWindow(margin + 164, filter2Top + 4, 60, 18);
    m_minSources.MoveWindow(margin + 226, filter2Top, 48, 24);
    m_maxSourcesLabel.MoveWindow(margin + 282, filter2Top + 4, 62, 18);
    m_maxSources.MoveWindow(margin + 346, filter2Top, 48, 24);
    const int savedLeft = max(margin + 404, cx - margin - 450);'''
    text = replace_once(text, layout_anchor, layout_new, "max peer layout")

    filter_anchor = '''    m_minSources.GetWindowText(value); value.Trim();
    if (!value.IsEmpty()) filter.minSources = static_cast<uint32>(max(0, _ttoi(value)));
    const int seen = m_lastSeen.GetCurSel();'''
    filter_new = '''    m_minSources.GetWindowText(value); value.Trim();
    if (!value.IsEmpty()) filter.minSources = static_cast<uint32>(max(0, _ttoi(value)));
    m_maxSources.GetWindowText(value); value.Trim();
    if (!value.IsEmpty()) filter.maxSources = static_cast<uint32>(max(0, _ttoi(value)));
    const int seen = m_lastSeen.GetCurSel();'''
    text = replace_once(text, filter_anchor, filter_new, "max peer CurrentFilter")

    apply_anchor = '''    if (search.filter.minSources != 0) { value.Format(_T("%u"), search.filter.minSources); m_minSources.SetWindowText(value); } else m_minSources.SetWindowText(_T(""));
    int seenSelection = 0;'''
    apply_new = '''    if (search.filter.minSources != 0) { value.Format(_T("%u"), search.filter.minSources); m_minSources.SetWindowText(value); } else m_minSources.SetWindowText(_T(""));
    if (search.filter.maxSources != 0) { value.Format(_T("%u"), search.filter.maxSources); m_maxSources.SetWindowText(value); } else m_maxSources.SetWindowText(_T(""));
    int seenSelection = 0;'''
    text = replace_once(text, apply_anchor, apply_new, "max peer saved filter")

    text = text.replace("SnapshotLiveResults(context->liveRows);", "SnapshotLiveResults(context->request, context->liveRows);")
    sig_old = "void CSearch2Wnd::SnapshotLiveResults(std::vector<EmuleNextUnifiedSearchResult>& rows) const"
    sig_new = "void CSearch2Wnd::SnapshotLiveResults(const EmuleNextSearchRequest& request, std::vector<EmuleNextUnifiedSearchResult>& rows) const"
    text = text.replace(sig_old, sig_new)

    insertion_anchor = '''        row.sourceFlags = live->IsKademlia() ? ENS2_SOURCE_LIVE_KAD : ENS2_SOURCE_LIVE_ED2K;
        if (live->GetKnownType() == CSearchFile::Downloaded)
            row.sourceFlags |= ENS2_SOURCE_PREVIOUSLY_DOWNLOADED;
        row.completedBefore = (row.sourceFlags & ENS2_SOURCE_PREVIOUSLY_DOWNLOADED) != 0;
        bool duplicate = false;'''
    insertion_new = '''        row.sourceFlags = live->IsKademlia() ? ENS2_SOURCE_LIVE_KAD : ENS2_SOURCE_LIVE_ED2K;
        if (live->GetKnownType() == CSearchFile::Downloaded)
            row.sourceFlags |= ENS2_SOURCE_PREVIOUSLY_DOWNLOADED;
        row.completedBefore = (row.sourceFlags & ENS2_SOURCE_PREVIOUSLY_DOWNLOADED) != 0;

        CString name(row.fileName);
        CString query(request.query);
        name.MakeLower(); query.MakeLower(); query.Trim();
        if (!query.IsEmpty() && name.Find(query) < 0)
            continue;
        if (request.filter.minSize != 0 && row.fileSize < request.filter.minSize)
            continue;
        if (request.filter.maxSize != 0 && row.fileSize > request.filter.maxSize)
            continue;
        if (!request.filter.extension.IsEmpty()) {
            CString extension(request.filter.extension);
            if (extension[0] != _T('.')) extension.Insert(0, _T('.'));
            if (CString(row.fileName).Right(extension.GetLength()).CompareNoCase(extension) != 0)
                continue;
        }
        if (request.filter.minSources != 0 && row.liveSourceCount < request.filter.minSources)
            continue;
        if (request.filter.maxSources != 0 && row.liveSourceCount > request.filter.maxSources)
            continue;
        if (request.filter.excludePreviouslyDownloaded && row.completedBefore)
            continue;
        // Favorites/Missing are historical/library predicates. A live legacy row
        // is not synchronously queried against SQLite on the GUI thread.
        if (request.filter.favoritesOnly || request.filter.missingOnly)
            continue;

        bool duplicate = false;'''
    text = replace_once(text, insertion_anchor, insertion_new, "live filter application")

    menu_anchor = '''    CMenu menu; menu.CreatePopupMenu();
    menu.AppendMenu(MF_STRING, 0x7E90, _T("Export selected"));
    menu.AppendMenu(MF_STRING, 0x7E91, _T("Export all results"));
    menu.AppendMenu(MF_SEPARATOR);
    menu.AppendMenu(MF_STRING, 0x7E92, _T("Manage block rules..."));'''
    menu_new = '''    CMenu menu; menu.CreatePopupMenu();
    menu.AppendMenu(MF_STRING, 0x7E90, _T("Export selected"));
    menu.AppendMenu(MF_STRING, 0x7E91, _T("Export all results"));
    menu.AppendMenu(MF_SEPARATOR);
    menu.AppendMenu(MF_STRING, 0x7E93, _T("Favorite selected"));
    menu.AppendMenu(MF_STRING, 0x7E94, _T("Add selected to Download Later"));
    menu.AppendMenu(MF_SEPARATOR);
    menu.AppendMenu(MF_STRING, 0x7E92, _T("Manage block rules..."));'''
    text = replace_once(text, menu_anchor, menu_new, "bulk menu entries")

    command_anchor = '''    if (command == 0x7E90) ExportRows(true);
    else if (command == 0x7E91) ExportRows(false);
    else if (command == 0x7E92) ShowRulesMenu(point);'''
    command_new = '''    if (command == 0x7E90) ExportRows(true);
    else if (command == 0x7E91) ExportRows(false);
    else if (command == 0x7E93) ApplyBulkAction(true);
    else if (command == 0x7E94) ApplyBulkAction(false);
    else if (command == 0x7E92) ShowRulesMenu(point);'''
    text = replace_once(text, command_anchor, command_new, "bulk menu dispatch")

    if "void CSearch2Wnd::ApplyBulkAction(bool favorite)" not in text:
        anchor = "void CSearch2Wnd::OnContextMenu(CWnd* wnd, CPoint point)"
        pos = text.find(anchor)
        if pos < 0:
            raise SystemExit("Search 2 hardening: context menu helper missing")
        helper = '''void CSearch2Wnd::ApplyBulkAction(bool favorite)
{
    unsigned changed = 0;
    POSITION pos = m_results.GetFirstSelectedItemPosition();
    while (pos != NULL && changed < 2000) {
        const int listIndex = m_results.GetNextSelectedItem(pos);
        const size_t index = static_cast<size_t>(m_results.GetItemData(listIndex));
        if (index >= m_rows.size())
            continue;
        EmuleNextUnifiedSearchResult& row = m_rows[index];
        if (favorite) {
            if (!row.favorite) {
                EmuleNextFavoriteRecord record;
                record.fileHash = row.fileHash;
                record.fileSize = row.fileSize;
                record.fileName = row.fileName;
                record.aichHash = row.aichHash;
                theEmuleNext.Database().SaveFavorite(record);
                row.favorite = true;
                ++changed;
            }
        }
        else {
            EmuleNextFileObservation file;
            file.ed2kHash = row.fileHash;
            file.fileSize = row.fileSize;
            file.fileName = row.fileName;
            file.aichHash = row.aichHash;
            theEmuleNext.Database().SaveDownloadLater(file);
            ++changed;
        }
    }
    PopulateResults();
    CString status;
    status.Format(favorite ? _T("Favorited %u selected results.") : _T("Queued %u selected results for Download Later."), changed);
    m_status.SetWindowText(status);
}

'''
        text = text[:pos] + helper + text[pos:]

    write(WND_CPP, text, enc)


def main() -> int:
    for path in (SERVICE_H, SERVICE_CPP, WND_H, WND_CPP):
        if not path.exists():
            raise SystemExit(f"Search 2 hardening: missing source {path}")
    patch_service()
    patch_header()
    patch_cpp()
    print("Search 2 live-filter parity, unified rule filtering, max-peers UI, MFC context menu and bounded bulk actions materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
