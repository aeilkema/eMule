//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "Search2Service.h"

#include <winsqlite3.h>
#include <algorithm>
#include <regex>

namespace
{
    struct SearchRule
    {
        EmuleNextSearchBlockRuleType type;
        CString pattern;
    };

    uint64 SearchNow()
    {
        return static_cast<uint64>(time(NULL));
    }

    sqlite3* OpenSearchDb(const CStringW& path)
    {
        if (path.IsEmpty())
            return NULL;
        sqlite3* db = NULL;
        if (sqlite3_open16(path.GetString(), &db) != SQLITE_OK) {
            if (db != NULL)
                sqlite3_close(db);
            return NULL;
        }
        sqlite3_busy_timeout(db, 3000);
        return db;
    }

    void BindText16(sqlite3_stmt* stmt, int index, const CString& value)
    {
        if (value.IsEmpty())
            sqlite3_bind_null(stmt, index);
        else
            sqlite3_bind_text16(stmt, index, value.GetString(), -1, SQLITE_TRANSIENT);
    }

    CString ColumnCString(sqlite3_stmt* stmt, int column)
    {
        const TCHAR* value = static_cast<const TCHAR*>(sqlite3_column_text16(stmt, column));
        return value != NULL ? CString(value) : CString();
    }

    CString EncodeFilter(const EmuleNextSearchFilter& filter)
    {
        CString value;
        value.Format(_T("{\"min\":%I64u,\"max\":%I64u,\"downloaded\":%u,\"favorite\":%u,\"missing\":%u}"),
            filter.minSize, filter.maxSize,
            filter.excludePreviouslyDownloaded ? 1U : 0U,
            filter.favoritesOnly ? 1U : 0U,
            filter.missingOnly ? 1U : 0U);
        return value;
    }

    EmuleNextSearchFilter DecodeFilter(const CString& value)
    {
        EmuleNextSearchFilter filter;
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

    bool LoadRules(sqlite3* db, std::vector<SearchRule>& rules)
    {
        rules.clear();
        sqlite3_stmt* stmt = NULL;
        if (sqlite3_prepare_v2(db,
            "SELECT rule_type,pattern FROM search_block_rules ORDER BY id",
            -1, &stmt, NULL) != SQLITE_OK) {
            return false;
        }
        while (sqlite3_step(stmt) == SQLITE_ROW) {
            SearchRule rule;
            rule.type = static_cast<EmuleNextSearchBlockRuleType>(sqlite3_column_int(stmt, 0));
            rule.pattern = ColumnCString(stmt, 1);
            rules.push_back(rule);
        }
        sqlite3_finalize(stmt);
        return true;
    }

    bool MatchesRule(const EmuleNextSearchFileResult& file, const SearchRule& rule)
    {
        CString value(file.fileName);
        switch (rule.type) {
        case ENSBR_NAME_CONTAINS:
        {
            CString lhs(value);
            CString rhs(rule.pattern);
            lhs.MakeLower();
            rhs.MakeLower();
            return !rhs.IsEmpty() && lhs.Find(rhs) >= 0;
        }
        case ENSBR_EXTENSION:
        {
            CString extension(rule.pattern);
            if (!extension.IsEmpty() && extension[0] != _T('.'))
                extension.Insert(0, _T('.'));
            return !extension.IsEmpty()
                && value.Right(extension.GetLength()).CompareNoCase(extension) == 0;
        }
        case ENSBR_REGEX:
            try {
                return std::regex_search(std::wstring(value.GetString()),
                    std::wregex(rule.pattern.GetString(), std::regex_constants::icase));
            }
            catch (const std::regex_error&) {
                // Invalid rules never block content. They can be corrected in
                // settings without making search unusable.
                return false;
            }
        default:
            return false;
        }
    }

    bool MatchesAnyRule(const EmuleNextSearchFileResult& file,
        const std::vector<SearchRule>& rules)
    {
        for (size_t i = 0; i < rules.size(); ++i)
            if (MatchesRule(file, rules[i]))
                return true;
        return false;
    }
}

EmuleNextSearchFilter::EmuleNextSearchFilter()
    : minSize(0)
    , maxSize(0)
    , excludePreviouslyDownloaded(false)
    , favoritesOnly(false)
    , missingOnly(false)
{
}

EmuleNextSearchRequest::EmuleNextSearchRequest()
    : maximumResults(500)
    , pageSize(500)
{
}

EmuleNextSavedSearch::EmuleNextSavedSearch()
    : lastRun(0)
    , lastResultSeen(0)
{
}

CSearch2Service::CSearch2Service(CEmuleNextDatabase& database)
    : m_database(database)
{
    EnsureSchema();
}

bool CSearch2Service::EnsureSchema() const
{
    sqlite3* db = OpenSearchDb(m_database.GetDatabasePath());
    if (db == NULL)
        return false;

    static const char sql[] =
        "CREATE TABLE IF NOT EXISTS search_block_rules("
        " id INTEGER PRIMARY KEY,rule_type INTEGER NOT NULL,pattern TEXT NOT NULL,reason TEXT,created_at INTEGER NOT NULL,"
        " UNIQUE(rule_type,pattern));";
    const bool ok = sqlite3_exec(db, sql, NULL, NULL, NULL) == SQLITE_OK;
    sqlite3_close(db);
    return ok;
}

bool CSearch2Service::PassesFilter(const EmuleNextSearchFileResult& file,
    const EmuleNextSearchFilter& filter) const
{
    if (filter.minSize != 0 && file.fileSize < filter.minSize)
        return false;
    if (filter.maxSize != 0 && file.fileSize > filter.maxSize)
        return false;
    if (filter.excludePreviouslyDownloaded && file.completedBefore)
        return false;
    if (filter.favoritesOnly && !file.favorite)
        return false;
    // Historical Search 2.0 does not pretend to know current filesystem state
    // from a stale database row. "missing only" therefore means content which
    // was completed before and is a candidate for Library missing/relink logic.
    if (filter.missingOnly && !file.completedBefore)
        return false;
    return true;
}

bool CSearch2Service::SearchHistory(const EmuleNextSearchRequest& request,
    std::vector<EmuleNextSearchFileResult>& results) const
{
    results.clear();
    if (!EnsureSchema())
        return false;

    sqlite3* ruleDb = OpenSearchDb(m_database.GetDatabasePath());
    if (ruleDb == NULL)
        return false;
    std::vector<SearchRule> rules;
    const bool rulesLoaded = LoadRules(ruleDb, rules);
    sqlite3_close(ruleDb);
    if (!rulesLoaded)
        return false;

    const size_t pageSize = std::max<size_t>(50, std::min<size_t>(5000,
        request.pageSize == 0 ? 500 : request.pageSize));
    size_t offset = 0;

    for (;;) {
        std::vector<EmuleNextSearchFileResult> page;
        if (!m_database.SearchFiles(CStringW(request.query), pageSize, offset, page))
            return false;
        if (page.empty())
            break;

        for (size_t i = 0; i < page.size(); ++i) {
            if (!PassesFilter(page[i], request.filter) || MatchesAnyRule(page[i], rules))
                continue;
            results.push_back(page[i]);
            if (request.maximumResults != 0 && results.size() >= request.maximumResults)
                return true;
        }

        offset += page.size();
        if (page.size() < pageSize)
            break;
    }
    return true;
}

bool CSearch2Service::AddHashBlock(const EmuleNextHash16& hash, uint64 size, LPCTSTR reason)
{
    if (!hash.valid || size == 0)
        return false;
    sqlite3* db = OpenSearchDb(m_database.GetDatabasePath());
    if (db == NULL)
        return false;
    sqlite3_stmt* stmt = NULL;
    bool ok = sqlite3_prepare_v2(db,
        "INSERT OR REPLACE INTO blocked_hashes(ed2k_hash,size,reason,created_at) VALUES(?1,?2,?3,?4)",
        -1, &stmt, NULL) == SQLITE_OK;
    if (ok) {
        sqlite3_bind_blob(stmt, 1, hash.bytes.data(), 16, SQLITE_TRANSIENT);
        sqlite3_bind_int64(stmt, 2, static_cast<sqlite3_int64>(size));
        if (reason != NULL && *reason != _T('\0'))
            sqlite3_bind_text16(stmt, 3, reason, -1, SQLITE_TRANSIENT);
        else
            sqlite3_bind_null(stmt, 3);
        sqlite3_bind_int64(stmt, 4, static_cast<sqlite3_int64>(SearchNow()));
        ok = sqlite3_step(stmt) == SQLITE_DONE;
    }
    if (stmt != NULL)
        sqlite3_finalize(stmt);
    sqlite3_close(db);
    return ok;
}

bool CSearch2Service::RemoveHashBlock(const EmuleNextHash16& hash, uint64 size)
{
    if (!hash.valid || size == 0)
        return false;
    sqlite3* db = OpenSearchDb(m_database.GetDatabasePath());
    if (db == NULL)
        return false;
    sqlite3_stmt* stmt = NULL;
    bool ok = sqlite3_prepare_v2(db,
        "DELETE FROM blocked_hashes WHERE ed2k_hash=?1 AND size=?2",
        -1, &stmt, NULL) == SQLITE_OK;
    if (ok) {
        sqlite3_bind_blob(stmt, 1, hash.bytes.data(), 16, SQLITE_TRANSIENT);
        sqlite3_bind_int64(stmt, 2, static_cast<sqlite3_int64>(size));
        ok = sqlite3_step(stmt) == SQLITE_DONE;
    }
    if (stmt != NULL)
        sqlite3_finalize(stmt);
    sqlite3_close(db);
    return ok;
}

bool CSearch2Service::AddRule(EmuleNextSearchBlockRuleType type, LPCTSTR pattern, LPCTSTR reason)
{
    if (pattern == NULL || *pattern == _T('\0') || !EnsureSchema())
        return false;
    if (type == ENSBR_REGEX) {
        try {
            std::wregex test(pattern, std::regex_constants::icase);
            (void)test;
        }
        catch (const std::regex_error&) {
            return false;
        }
    }

    sqlite3* db = OpenSearchDb(m_database.GetDatabasePath());
    if (db == NULL)
        return false;
    sqlite3_stmt* stmt = NULL;
    bool ok = sqlite3_prepare_v2(db,
        "INSERT OR REPLACE INTO search_block_rules(rule_type,pattern,reason,created_at) VALUES(?1,?2,?3,?4)",
        -1, &stmt, NULL) == SQLITE_OK;
    if (ok) {
        sqlite3_bind_int(stmt, 1, static_cast<int>(type));
        sqlite3_bind_text16(stmt, 2, pattern, -1, SQLITE_TRANSIENT);
        if (reason != NULL && *reason != _T('\0'))
            sqlite3_bind_text16(stmt, 3, reason, -1, SQLITE_TRANSIENT);
        else
            sqlite3_bind_null(stmt, 3);
        sqlite3_bind_int64(stmt, 4, static_cast<sqlite3_int64>(SearchNow()));
        ok = sqlite3_step(stmt) == SQLITE_DONE;
    }
    if (stmt != NULL)
        sqlite3_finalize(stmt);
    sqlite3_close(db);
    return ok;
}

bool CSearch2Service::RemoveRule(EmuleNextSearchBlockRuleType type, LPCTSTR pattern)
{
    if (pattern == NULL || !EnsureSchema())
        return false;
    sqlite3* db = OpenSearchDb(m_database.GetDatabasePath());
    if (db == NULL)
        return false;
    sqlite3_stmt* stmt = NULL;
    bool ok = sqlite3_prepare_v2(db,
        "DELETE FROM search_block_rules WHERE rule_type=?1 AND pattern=?2",
        -1, &stmt, NULL) == SQLITE_OK;
    if (ok) {
        sqlite3_bind_int(stmt, 1, static_cast<int>(type));
        sqlite3_bind_text16(stmt, 2, pattern, -1, SQLITE_TRANSIENT);
        ok = sqlite3_step(stmt) == SQLITE_DONE;
    }
    if (stmt != NULL)
        sqlite3_finalize(stmt);
    sqlite3_close(db);
    return ok;
}

bool CSearch2Service::IsBlockedByRule(const EmuleNextSearchFileResult& file) const
{
    if (!EnsureSchema())
        return false;
    sqlite3* db = OpenSearchDb(m_database.GetDatabasePath());
    if (db == NULL)
        return false;
    std::vector<SearchRule> rules;
    const bool ok = LoadRules(db, rules);
    sqlite3_close(db);
    return ok && MatchesAnyRule(file, rules);
}

bool CSearch2Service::SaveSearch(const EmuleNextSavedSearch& search)
{
    if (search.name.IsEmpty() || search.query.IsEmpty())
        return false;
    sqlite3* db = OpenSearchDb(m_database.GetDatabasePath());
    if (db == NULL)
        return false;
    sqlite3_stmt* stmt = NULL;
    bool ok = sqlite3_prepare_v2(db,
        "INSERT OR REPLACE INTO saved_searches(id,name,query,filters_json,last_run,last_result_seen) "
        "VALUES((SELECT id FROM saved_searches WHERE name=?1),?1,?2,?3,"
        "COALESCE((SELECT last_run FROM saved_searches WHERE name=?1),?4),"
        "COALESCE((SELECT last_result_seen FROM saved_searches WHERE name=?1),?5))",
        -1, &stmt, NULL) == SQLITE_OK;
    if (ok) {
        BindText16(stmt, 1, search.name);
        BindText16(stmt, 2, search.query);
        BindText16(stmt, 3, EncodeFilter(search.filter));
        sqlite3_bind_int64(stmt, 4, static_cast<sqlite3_int64>(search.lastRun));
        sqlite3_bind_int64(stmt, 5, static_cast<sqlite3_int64>(search.lastResultSeen));
        ok = sqlite3_step(stmt) == SQLITE_DONE;
    }
    if (stmt != NULL)
        sqlite3_finalize(stmt);
    sqlite3_close(db);
    return ok;
}

bool CSearch2Service::DeleteSavedSearch(LPCTSTR name)
{
    if (name == NULL || *name == _T('\0'))
        return false;
    sqlite3* db = OpenSearchDb(m_database.GetDatabasePath());
    if (db == NULL)
        return false;
    sqlite3_stmt* stmt = NULL;
    bool ok = sqlite3_prepare_v2(db, "DELETE FROM saved_searches WHERE name=?1", -1, &stmt, NULL) == SQLITE_OK;
    if (ok) {
        sqlite3_bind_text16(stmt, 1, name, -1, SQLITE_TRANSIENT);
        ok = sqlite3_step(stmt) == SQLITE_DONE;
    }
    if (stmt != NULL)
        sqlite3_finalize(stmt);
    sqlite3_close(db);
    return ok;
}

bool CSearch2Service::LoadSavedSearches(std::vector<EmuleNextSavedSearch>& searches) const
{
    searches.clear();
    sqlite3* db = OpenSearchDb(m_database.GetDatabasePath());
    if (db == NULL)
        return false;
    sqlite3_stmt* stmt = NULL;
    const bool prepared = sqlite3_prepare_v2(db,
        "SELECT name,query,COALESCE(filters_json,''),COALESCE(last_run,0),COALESCE(last_result_seen,0) FROM saved_searches ORDER BY name COLLATE NOCASE",
        -1, &stmt, NULL) == SQLITE_OK;
    if (prepared) {
        while (sqlite3_step(stmt) == SQLITE_ROW) {
            EmuleNextSavedSearch search;
            search.name = ColumnCString(stmt, 0);
            search.query = ColumnCString(stmt, 1);
            search.filter = DecodeFilter(ColumnCString(stmt, 2));
            search.lastRun = static_cast<uint64>(sqlite3_column_int64(stmt, 3));
            search.lastResultSeen = static_cast<uint64>(sqlite3_column_int64(stmt, 4));
            searches.push_back(search);
        }
    }
    if (stmt != NULL)
        sqlite3_finalize(stmt);
    sqlite3_close(db);
    return prepared;
}

bool CSearch2Service::MarkSearchRun(LPCTSTR name, uint64 newestResultSeen)
{
    if (name == NULL || *name == _T('\0'))
        return false;
    sqlite3* db = OpenSearchDb(m_database.GetDatabasePath());
    if (db == NULL)
        return false;
    sqlite3_stmt* stmt = NULL;
    bool ok = sqlite3_prepare_v2(db,
        "UPDATE saved_searches SET last_run=?2,last_result_seen=MAX(COALESCE(last_result_seen,0),?3) WHERE name=?1",
        -1, &stmt, NULL) == SQLITE_OK;
    if (ok) {
        sqlite3_bind_text16(stmt, 1, name, -1, SQLITE_TRANSIENT);
        sqlite3_bind_int64(stmt, 2, static_cast<sqlite3_int64>(SearchNow()));
        sqlite3_bind_int64(stmt, 3, static_cast<sqlite3_int64>(newestResultSeen));
        ok = sqlite3_step(stmt) == SQLITE_DONE && sqlite3_changes(db) > 0;
    }
    if (stmt != NULL)
        sqlite3_finalize(stmt);
    sqlite3_close(db);
    return ok;
}
