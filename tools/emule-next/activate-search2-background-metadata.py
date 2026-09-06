#!/usr/bin/env python3
"""Move Search 2 saved-search metadata refresh to a background worker.

Search queries were already asynchronous, but opening/refreshing Search 2 still
loaded saved-search rows synchronously on the MFC UI thread. This activator
keeps the same service/API while moving that recurring metadata read off-thread.

The activator is intentionally tolerant of both the original Search2Wnd source
shape and the newer materialized view shape. Repeated activation must be a
no-op once the worker contract is present.
"""
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

    marker = "afx_msg LRESULT OnSavedSearchesLoaded(WPARAM, LPARAM value);"
    if marker not in text:
        anchor = "    afx_msg LRESULT OnSearchLoaded(WPARAM, LPARAM value);"
        if anchor not in text:
            raise SystemExit("Search 2 metadata: message-handler header anchor missing")
        text = text.replace(anchor, anchor + "\n    " + marker, 1)
        changed = True

    populate = "    void PopulateSavedSearches(const CString& previous);"
    if populate not in text:
        anchor = "    void ReloadSavedSearches();"
        if anchor not in text:
            raise SystemExit("Search 2 metadata: ReloadSavedSearches header anchor missing")
        text = text.replace(anchor, anchor + "\n" + populate, 1)
        changed = True

    loading = "    bool m_savedSearchesLoading;"
    if loading not in text:
        anchor = "    bool m_loading;"
        if anchor not in text:
            raise SystemExit("Search 2 metadata: loading-state header anchor missing")
        text = text.replace(anchor, anchor + "\n" + loading, 1)
        changed = True

    if changed:
        write_text(HEADER, text, encoding)


def patch_cpp() -> None:
    text, encoding = read_text(CPP)
    changed = False

    message = "    const UINT WM_EN_SEARCH2_SAVED_LOADED = WM_APP + 0x571;"
    if message not in text:
        anchor = "    const UINT WM_EN_SEARCH2_LOADED = WM_APP + 0x570;"
        if anchor not in text:
            raise SystemExit("Search 2 metadata: message id anchor missing")
        text = text.replace(anchor, anchor + "\n" + message, 1)
        changed = True

    structs = '''
    struct SavedSearchLoadContext
    {
        HWND target;
        CString previous;
    };

    struct SavedSearchLoadResult
    {
        bool ok;
        CString previous;
        std::vector<EmuleNextSavedSearch> searches;
        SavedSearchLoadResult() : ok(false) {}
    };

    UINT AFX_CDECL SavedSearchLoadWorker(LPVOID value)
    {
        std::unique_ptr<SavedSearchLoadContext> context(static_cast<SavedSearchLoadContext*>(value));
        std::unique_ptr<SavedSearchLoadResult> result(new SavedSearchLoadResult);
        result->previous = context->previous;
        CSearch2Service service(theEmuleNext.Database());
        result->ok = service.LoadSavedSearches(result->searches);
        if (::IsWindow(context->target)
            && ::PostMessage(context->target, WM_EN_SEARCH2_SAVED_LOADED, 0, reinterpret_cast<LPARAM>(result.get()))) {
            result.release();
        }
        return 0;
    }
'''
    if "struct SavedSearchLoadContext" not in text:
        # Search2Wnd has existed in two source shapes. Older activators used
        # SearchResult as their insertion point; the materialized view groups
        # SearchContext first. Accept either while keeping deterministic output.
        anchors = (
            "    struct SearchContext\n",
            "    struct SearchResult\n",
        )
        pos = -1
        for anchor in anchors:
            pos = text.find(anchor)
            if pos >= 0:
                break
        if pos < 0:
            raise SystemExit("Search 2 metadata: worker insertion anchor missing")
        text = text[:pos] + structs + "\n" + text[pos:]
        changed = True

    message_map = "    ON_MESSAGE(WM_EN_SEARCH2_SAVED_LOADED, OnSavedSearchesLoaded)"
    if message_map not in text:
        anchor = "    ON_MESSAGE(WM_EN_SEARCH2_LOADED, OnSearchLoaded)"
        if anchor not in text:
            raise SystemExit("Search 2 metadata: message-map anchor missing")
        text = text.replace(anchor, anchor + "\n" + message_map, 1)
        changed = True

    ctor_old = '''CSearch2Wnd::CSearch2Wnd()
    : m_loading(false)
{
}'''
    ctor_new = '''CSearch2Wnd::CSearch2Wnd()
    : m_loading(false)
    , m_savedSearchesLoading(false)
{
}'''
    if ctor_old in text:
        text = text.replace(ctor_old, ctor_new, 1)
        changed = True
    elif "m_savedSearchesLoading(false)" not in text:
        raise SystemExit("Search 2 metadata: constructor anchor changed unexpectedly")

    old_reload = '''void CSearch2Wnd::ReloadSavedSearches()
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
}'''
    new_reload = '''void CSearch2Wnd::ReloadSavedSearches()
{
    if (!::IsWindow(m_savedSearch.m_hWnd) || !theEmuleNext.IsRunning() || m_savedSearchesLoading)
        return;

    std::unique_ptr<SavedSearchLoadContext> context(new SavedSearchLoadContext);
    context->target = m_hWnd;
    m_savedSearch.GetWindowText(context->previous);
    m_savedSearchesLoading = true;
    if (AfxBeginThread(SavedSearchLoadWorker, context.get(), THREAD_PRIORITY_BELOW_NORMAL) == NULL) {
        m_savedSearchesLoading = false;
        return;
    }
    context.release();
}

LRESULT CSearch2Wnd::OnSavedSearchesLoaded(WPARAM, LPARAM value)
{
    std::unique_ptr<SavedSearchLoadResult> result(reinterpret_cast<SavedSearchLoadResult*>(value));
    m_savedSearchesLoading = false;
    if (result.get() == NULL || !result->ok)
        return 0;
    m_savedSearches.swap(result->searches);
    PopulateSavedSearches(result->previous);
    return 0;
}

void CSearch2Wnd::PopulateSavedSearches(const CString& previous)
{
    if (!::IsWindow(m_savedSearch.m_hWnd))
        return;
    m_savedSearch.ResetContent();
    for (size_t i = 0; i < m_savedSearches.size(); ++i)
        m_savedSearch.AddString(m_savedSearches[i].name);

    const int selected = previous.IsEmpty() ? -1 : m_savedSearch.FindStringExact(-1, previous);
    if (selected >= 0)
        m_savedSearch.SetCurSel(selected);
    else
        m_savedSearch.SetWindowText(previous);
}'''
    if old_reload in text:
        text = text.replace(old_reload, new_reload, 1)
        changed = True
    elif not all(marker in text for marker in (
        "OnSavedSearchesLoaded",
        "SavedSearchLoadWorker",
        "PopulateSavedSearches",
        "m_savedSearchesLoading",
    )):
        raise SystemExit("Search 2 metadata: ReloadSavedSearches implementation changed unexpectedly")

    if changed:
        write_text(CPP, text, encoding)


def main() -> int:
    if not CPP.exists() or not HEADER.exists():
        raise SystemExit("Search 2 metadata: Search2Wnd sources missing")
    patch_header()
    patch_cpp()
    print("Search 2 saved-search metadata background refresh materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
