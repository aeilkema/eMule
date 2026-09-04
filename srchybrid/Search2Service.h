//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "EmuleNextDatabase.h"
#include <vector>

enum EmuleNextSearchBlockRuleType
{
    ENSBR_NAME_CONTAINS = 0,
    ENSBR_EXTENSION,
    ENSBR_REGEX
};

struct EmuleNextSearchFilter
{
    uint64 minSize;
    uint64 maxSize;
    bool excludePreviouslyDownloaded;
    bool favoritesOnly;
    bool missingOnly;

    EmuleNextSearchFilter();
};

struct EmuleNextSearchRequest
{
    CString query;
    EmuleNextSearchFilter filter;
    size_t maximumResults; // 0 means unlimited (paged internally)
    size_t pageSize;

    EmuleNextSearchRequest();
};

struct EmuleNextSavedSearch
{
    CString name;
    CString query;
    EmuleNextSearchFilter filter;
    uint64 lastRun;
    uint64 lastResultSeen;

    EmuleNextSavedSearch();
};

class CSearch2Service
{
public:
    explicit CSearch2Service(CEmuleNextDatabase& database);

    bool SearchHistory(const EmuleNextSearchRequest& request,
        std::vector<EmuleNextSearchFileResult>& results) const;

    bool AddHashBlock(const EmuleNextHash16& hash, uint64 size, LPCTSTR reason = NULL);
    bool RemoveHashBlock(const EmuleNextHash16& hash, uint64 size);
    bool AddRule(EmuleNextSearchBlockRuleType type, LPCTSTR pattern, LPCTSTR reason = NULL);
    bool RemoveRule(EmuleNextSearchBlockRuleType type, LPCTSTR pattern);
    bool IsBlockedByRule(const EmuleNextSearchFileResult& file) const;

    bool SaveSearch(const EmuleNextSavedSearch& search);
    bool DeleteSavedSearch(LPCTSTR name);
    bool LoadSavedSearches(std::vector<EmuleNextSavedSearch>& searches) const;
    bool MarkSearchRun(LPCTSTR name, uint64 newestResultSeen);

private:
    bool EnsureSchema() const;
    bool PassesFilter(const EmuleNextSearchFileResult& file,
        const EmuleNextSearchFilter& filter) const;

    CEmuleNextDatabase& m_database;
};
