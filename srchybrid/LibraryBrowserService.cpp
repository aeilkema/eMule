//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later

#include "stdafx.h"
#include "LibraryBrowserService.h"

#include <winsqlite3.h>

namespace
{
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
    , favorite(false)
    , completed(false)
    , missing(false)
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
        "COALESCE(le.local_path,'') "
        "FROM files f LEFT JOIN library_entries le ON le.file_id=f.id "
        "ORDER BY f.last_seen DESC LIMIT 10000";

    sqlite3_stmt* statement = NULL;
    bool ok = sqlite3_prepare_v2(database, sql, -1, &statement, NULL) == SQLITE_OK;
    if (ok) {
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
            row.missing = row.completed && FileMissing(row.localPath);
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
