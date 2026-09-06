#!/usr/bin/env python3
"""Move Search 2 saved-search and hash-block mutations off the MFC UI thread."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "srchybrid"
CPP = SRC / "Search2Wnd.cpp"
HEADER = SRC / "Search2Wnd.h"


def read_text(path: pathlib.Path) -> tuple[str, str]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def write_text(path: pathlib.Path, text: str, encoding: str) -> None:
    path.write_bytes(text.encode(encoding))


def patch_header() -> None:
    text, encoding = read_text(HEADER)
    changed = False

    handler = "    afx_msg LRESULT OnSearchActionFinished(WPARAM, LPARAM value);"
    if handler not in text:
        anchor = "    afx_msg LRESULT OnSavedSearchesLoaded(WPARAM, LPARAM value);"
        if anchor not in text:
            raise SystemExit("Search 2 actions: background metadata handler anchor missing")
        text = text.replace(anchor, anchor + "\n" + handler, 1)
        changed = True

    member = "    bool m_actionLoading;"
    if member not in text:
        anchor = "    bool m_savedSearchesLoading;"
        if anchor not in text:
            raise SystemExit("Search 2 actions: metadata loading-state anchor missing")
        text = text.replace(anchor, anchor + "\n" + member, 1)
        changed = True

    if changed:
        write_text(HEADER, text, encoding)


def patch_cpp() -> None:
    text, encoding = read_text(CPP)
    changed = False

    message = "    const UINT WM_EN_SEARCH2_ACTION_FINISHED = WM_APP + 0x572;"
    if message not in text:
        anchor = "    const UINT WM_EN_SEARCH2_SAVED_LOADED = WM_APP + 0x571;"
        if anchor not in text:
            raise SystemExit("Search 2 actions: metadata message anchor missing")
        text = text.replace(anchor, anchor + "\n" + message, 1)
        changed = True

    worker_block = '''
    enum Search2BackgroundAction
    {
        ENS2_ACTION_SAVE_SEARCH = 1,
        ENS2_ACTION_DELETE_SEARCH,
        ENS2_ACTION_BLOCK_HASH
    };

    struct SearchActionContext
    {
        HWND target;
        Search2BackgroundAction action;
        EmuleNextSavedSearch savedSearch;
        CString name;
        EmuleNextHash16 fileHash;
        uint64 fileSize;
        SearchActionContext() : target(NULL), action(ENS2_ACTION_SAVE_SEARCH), fileSize(0) {}
    };

    struct SearchActionResult
    {
        Search2BackgroundAction action;
        bool ok;
        CString name;
        EmuleNextHash16 fileHash;
        uint64 fileSize;
        SearchActionResult() : action(ENS2_ACTION_SAVE_SEARCH), ok(false), fileSize(0) {}
    };

    UINT AFX_CDECL SearchActionWorker(LPVOID value)
    {
        std::unique_ptr<SearchActionContext> context(static_cast<SearchActionContext*>(value));
        std::unique_ptr<SearchActionResult> result(new SearchActionResult);
        result->action = context->action;
        result->name = context->name;
        result->fileHash = context->fileHash;
        result->fileSize = context->fileSize;

        CSearch2Service service(theEmuleNext.Database());
        switch (context->action) {
        case ENS2_ACTION_SAVE_SEARCH:
            result->ok = service.SaveSearch(context->savedSearch);
            break;
        case ENS2_ACTION_DELETE_SEARCH:
            result->ok = service.DeleteSavedSearch(context->name);
            break;
        case ENS2_ACTION_BLOCK_HASH:
            result->ok = service.AddHashBlock(context->fileHash, context->fileSize, _T("Blocked from Search 2"));
            break;
        default:
            result->ok = false;
            break;
        }

        if (::IsWindow(context->target)
            && ::PostMessage(context->target, WM_EN_SEARCH2_ACTION_FINISHED, 0, reinterpret_cast<LPARAM>(result.get()))) {
            result.release();
        }
        return 0;
    }
'''
    if "struct SearchActionContext" not in text:
        anchor = "    struct SavedSearchLoadContext\n"
        pos = text.find(anchor)
        if pos < 0:
            raise SystemExit("Search 2 actions: background metadata struct anchor missing")
        text = text[:pos] + worker_block + "\n" + text[pos:]
        changed = True

    map_line = "    ON_MESSAGE(WM_EN_SEARCH2_ACTION_FINISHED, OnSearchActionFinished)"
    if map_line not in text:
        anchor = "    ON_MESSAGE(WM_EN_SEARCH2_SAVED_LOADED, OnSavedSearchesLoaded)"
        if anchor not in text:
            raise SystemExit("Search 2 actions: background metadata message-map anchor missing")
        text = text.replace(anchor, anchor + "\n" + map_line, 1)
        changed = True

    ctor_old = '''CSearch2Wnd::CSearch2Wnd()
    : m_loading(false)
    , m_savedSearchesLoading(false)
{
}'''
    ctor_new = '''CSearch2Wnd::CSearch2Wnd()
    : m_loading(false)
    , m_savedSearchesLoading(false)
    , m_actionLoading(false)
{
}'''
    if ctor_old in text:
        text = text.replace(ctor_old, ctor_new, 1)
        changed = True
    elif "m_actionLoading(false)" not in text:
        raise SystemExit("Search 2 actions: constructor anchor changed unexpectedly")

    save_old = '''void CSearch2Wnd::OnSaveSearchClicked()
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
}'''
    save_new = '''void CSearch2Wnd::OnSaveSearchClicked()
{
    if (!theEmuleNext.IsRunning() || m_actionLoading)
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

    std::unique_ptr<SearchActionContext> context(new SearchActionContext);
    context->target = m_hWnd;
    context->action = ENS2_ACTION_SAVE_SEARCH;
    context->name = name;
    context->savedSearch.name = name;
    context->savedSearch.query = query;
    context->savedSearch.filter = CurrentFilter();
    m_actionLoading = true;
    m_saveSearch.EnableWindow(FALSE);
    m_deleteSearch.EnableWindow(FALSE);
    m_status.SetWindowText(_T("Saving search in the background..."));
    if (AfxBeginThread(SearchActionWorker, context.get(), THREAD_PRIORITY_BELOW_NORMAL) == NULL) {
        m_actionLoading = false;
        m_saveSearch.EnableWindow(TRUE);
        m_deleteSearch.EnableWindow(TRUE);
        m_status.SetWindowText(_T("Unable to start saved-search update."));
        return;
    }
    context.release();
}'''
    if save_old in text:
        text = text.replace(save_old, save_new, 1)
        changed = True
    elif "context->action = ENS2_ACTION_SAVE_SEARCH" not in text:
        raise SystemExit("Search 2 actions: save action changed unexpectedly")

    delete_old = '''void CSearch2Wnd::OnDeleteSearchClicked()
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
}'''
    delete_new = '''void CSearch2Wnd::OnDeleteSearchClicked()
{
    if (!theEmuleNext.IsRunning() || m_actionLoading)
        return;

    CString name;
    m_savedSearch.GetWindowText(name);
    name.Trim();
    if (name.IsEmpty()) {
        m_status.SetWindowText(_T("Select a saved search to delete."));
        return;
    }

    std::unique_ptr<SearchActionContext> context(new SearchActionContext);
    context->target = m_hWnd;
    context->action = ENS2_ACTION_DELETE_SEARCH;
    context->name = name;
    m_actionLoading = true;
    m_saveSearch.EnableWindow(FALSE);
    m_deleteSearch.EnableWindow(FALSE);
    m_status.SetWindowText(_T("Deleting saved search in the background..."));
    if (AfxBeginThread(SearchActionWorker, context.get(), THREAD_PRIORITY_BELOW_NORMAL) == NULL) {
        m_actionLoading = false;
        m_saveSearch.EnableWindow(TRUE);
        m_deleteSearch.EnableWindow(TRUE);
        m_status.SetWindowText(_T("Unable to start saved-search update."));
        return;
    }
    context.release();
}'''
    if delete_old in text:
        text = text.replace(delete_old, delete_new, 1)
        changed = True
    elif "context->action = ENS2_ACTION_DELETE_SEARCH" not in text:
        raise SystemExit("Search 2 actions: delete action changed unexpectedly")

    block_old = '''void CSearch2Wnd::OnBlockClicked()
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
}'''
    block_new = '''void CSearch2Wnd::OnBlockClicked()
{
    const int index = SelectedIndex();
    if (index < 0 || m_actionLoading)
        return;
    const EmuleNextSearchFileResult& row = m_rows[static_cast<size_t>(index)];
    std::unique_ptr<SearchActionContext> context(new SearchActionContext);
    context->target = m_hWnd;
    context->action = ENS2_ACTION_BLOCK_HASH;
    context->fileHash = row.fileHash;
    context->fileSize = row.fileSize;
    m_actionLoading = true;
    UpdateActionButtons();
    m_status.SetWindowText(_T("Blocking hash in the background..."));
    if (AfxBeginThread(SearchActionWorker, context.get(), THREAD_PRIORITY_BELOW_NORMAL) == NULL) {
        m_actionLoading = false;
        UpdateActionButtons();
        m_status.SetWindowText(_T("Unable to start block update."));
        return;
    }
    context.release();
}'''
    if block_old in text:
        text = text.replace(block_old, block_new, 1)
        changed = True
    elif "context->action = ENS2_ACTION_BLOCK_HASH" not in text:
        raise SystemExit("Search 2 actions: block action changed unexpectedly")

    # Disable row actions while a background mutation is in flight.
    action_enable_old = "    const BOOL enabled = index >= 0 ? TRUE : FALSE;"
    action_enable_new = "    const BOOL enabled = index >= 0 && !m_actionLoading ? TRUE : FALSE;"
    if action_enable_old in text:
        text = text.replace(action_enable_old, action_enable_new, 1)
        changed = True
    elif action_enable_new not in text:
        raise SystemExit("Search 2 actions: action-button state anchor missing")

    handler = '''
LRESULT CSearch2Wnd::OnSearchActionFinished(WPARAM, LPARAM value)
{
    std::unique_ptr<SearchActionResult> result(reinterpret_cast<SearchActionResult*>(value));
    m_actionLoading = false;
    m_saveSearch.EnableWindow(TRUE);
    m_deleteSearch.EnableWindow(TRUE);
    UpdateActionButtons();
    if (result.get() == NULL || !result->ok) {
        m_status.SetWindowText(_T("Search 2 background update failed."));
        return 0;
    }

    if (result->action == ENS2_ACTION_SAVE_SEARCH) {
        m_savedSearch.SetWindowText(result->name);
        ReloadSavedSearches();
        CString status;
        status.Format(_T("Saved search '%s'."), static_cast<LPCTSTR>(result->name));
        m_status.SetWindowText(status);
    }
    else if (result->action == ENS2_ACTION_DELETE_SEARCH) {
        m_savedSearch.SetWindowText(_T(""));
        ReloadSavedSearches();
        m_status.SetWindowText(_T("Saved search deleted."));
    }
    else if (result->action == ENS2_ACTION_BLOCK_HASH) {
        for (std::vector<EmuleNextSearchFileResult>::iterator it = m_rows.begin(); it != m_rows.end(); ++it) {
            if (it->fileHash.valid && result->fileHash.valid
                && it->fileHash.bytes == result->fileHash.bytes
                && it->fileSize == result->fileSize) {
                m_rows.erase(it);
                break;
            }
        }
        PopulateResults();
        m_status.SetWindowText(_T("Hash blocked from historical search."));
    }
    return 0;
}
'''
    if "LRESULT CSearch2Wnd::OnSearchActionFinished" not in text:
        anchor = "CString CSearch2Wnd::HashText(const EmuleNextHash16& hash)"
        pos = text.find(anchor)
        if pos < 0:
            raise SystemExit("Search 2 actions: output handler anchor missing")
        text = text[:pos] + handler + "\n" + text[pos:]
        changed = True

    if changed:
        write_text(CPP, text, encoding)


def main() -> int:
    if not CPP.exists() or not HEADER.exists():
        raise SystemExit("Search 2 actions: Search2Wnd sources missing")
    patch_header()
    patch_cpp()
    print("Search 2 SQLite actions background worker materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())