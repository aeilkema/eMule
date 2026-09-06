//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later

#include "stdafx.h"
#include "KnownUsersService.h"

#include <winsqlite3.h>

namespace
{
    const int kMaximumKnownUsers = 5000;
    const int kMaximumKnownFilesPerUser = 5000;

    CStringW ColumnText(sqlite3_stmt* statement, int column)
    {
        const wchar_t* value = static_cast<const wchar_t*>(sqlite3_column_text16(statement, column));
        return value != NULL ? CStringW(value) : CStringW();
    }

    sqlite3* OpenReadOnly(const CStringW& path)
    {
        if (path.IsEmpty())
            return NULL;

        sqlite3* database = NULL;
        if (sqlite3_open16(path.GetString(), &database) != SQLITE_OK) {
            if (database != NULL)
                sqlite3_close(database);
            return NULL;
        }

        sqlite3_busy_timeout(database, 750);
        sqlite3_exec(database, "PRAGMA query_only=ON;", NULL, NULL, NULL);
        return database;
    }

    EmuleNextHash16 ColumnHash(sqlite3_stmt* statement, int column)
    {
        const void* value = sqlite3_column_blob(statement, column);
        const int bytes = sqlite3_column_bytes(statement, column);
        return bytes == 16 ? EmuleNextHash16(static_cast<const unsigned char*>(value)) : EmuleNextHash16();
    }
}

CKnownUsersService::CKnownUsersService(const CStringW& databasePath)
    : m_databasePath(databasePath)
{
}

bool CKnownUsersService::ListUsers(std::vector<EmuleNextKnownUserRecord>& users) const
{
    users.clear();
    sqlite3* database = OpenReadOnly(m_databasePath);
    if (database == NULL)
        return false;

    // Collapse source_kind duplicates before aggregation. This avoids two
    // correlated subqueries for every peer and keeps one file counted/summed
    // once even when it was learned through multiple discovery paths.
    static const char sql[] =
        "SELECT p.user_hash,COALESCE(p.username,''),p.first_seen,p.last_seen,"
        "COUNT(pf.file_id),COALESCE(SUM(f.size),0) "
        "FROM peers p "
        "JOIN (SELECT peer_id,file_id FROM peer_files GROUP BY peer_id,file_id) pf ON pf.peer_id=p.id "
        "JOIN files f ON f.id=pf.file_id "
        "GROUP BY p.id "
        "ORDER BY p.last_seen DESC LIMIT ?1";

    sqlite3_stmt* statement = NULL;
    bool ok = sqlite3_prepare_v2(database, sql, -1, &statement, NULL) == SQLITE_OK;
    if (ok) {
        sqlite3_bind_int(statement, 1, kMaximumKnownUsers);
        while (sqlite3_step(statement) == SQLITE_ROW) {
            EmuleNextKnownUserRecord item;
            item.userHash = ColumnHash(statement, 0);
            if (!item.userHash.valid)
                continue;
            item.userName = ColumnText(statement, 1);
            item.firstSeen = static_cast<uint64>(sqlite3_column_int64(statement, 2));
            item.lastSeen = static_cast<uint64>(sqlite3_column_int64(statement, 3));
            item.fileCount = static_cast<uint32>(sqlite3_column_int(statement, 4));
            item.totalBytes = static_cast<uint64>(sqlite3_column_int64(statement, 5));
            users.push_back(item);
        }
    }

    if (statement != NULL)
        sqlite3_finalize(statement);
    sqlite3_close(database);
    return ok;
}

bool CKnownUsersService::ListFiles(const EmuleNextHash16& peerHash,
    std::vector<EmuleNextKnownFileRecord>& files) const
{
    files.clear();
    if (!peerHash.valid)
        return false;

    sqlite3* database = OpenReadOnly(m_databasePath);
    if (database == NULL)
        return false;

    static const char sql[] =
        "SELECT f.ed2k_hash,COALESCE(f.canonical_name,''),COALESCE(f.aich_hash,''),"
        "f.size,MIN(pf.first_seen),MAX(pf.last_seen) "
        "FROM peer_files pf "
        "JOIN peers p ON p.id=pf.peer_id "
        "JOIN files f ON f.id=pf.file_id "
        "WHERE p.user_hash=?1 "
        "GROUP BY f.id "
        "ORDER BY MAX(pf.last_seen) DESC,f.canonical_name COLLATE NOCASE "
        "LIMIT ?2";

    sqlite3_stmt* statement = NULL;
    bool ok = sqlite3_prepare_v2(database, sql, -1, &statement, NULL) == SQLITE_OK;
    if (ok) {
        sqlite3_bind_blob(statement, 1, peerHash.bytes.data(), 16, SQLITE_TRANSIENT);
        sqlite3_bind_int(statement, 2, kMaximumKnownFilesPerUser);
        while (sqlite3_step(statement) == SQLITE_ROW) {
            EmuleNextKnownFileRecord item;
            item.fileHash = ColumnHash(statement, 0);
            if (!item.fileHash.valid)
                continue;
            item.fileName = ColumnText(statement, 1);
            item.aichHash = ColumnText(statement, 2);
            item.fileSize = static_cast<uint64>(sqlite3_column_int64(statement, 3));
            item.firstSeen = static_cast<uint64>(sqlite3_column_int64(statement, 4));
            item.lastSeen = static_cast<uint64>(sqlite3_column_int64(statement, 5));
            files.push_back(item);
        }
    }

    if (statement != NULL)
        sqlite3_finalize(statement);
    sqlite3_close(database);
    return ok;
}