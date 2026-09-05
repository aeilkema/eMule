//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later

#include "stdafx.h"
#include "DownloadIntelligenceService.h"

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
        const int bytes = sqlite3_column_bytes(statement, column);
        return bytes == 16 ? EmuleNextHash16(static_cast<const unsigned char*>(value)) : EmuleNextHash16();
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
}

CDownloadIntelligenceService::CDownloadIntelligenceService(const CStringW& databasePath)
    : m_databasePath(databasePath)
{
}

bool CDownloadIntelligenceService::ListRecentTransfers(size_t limit,
    std::vector<EmuleNextTransferHistoryRecord>& transfers) const
{
    transfers.clear();
    sqlite3* database = OpenReadOnly(m_databasePath);
    if (database == NULL)
        return false;

    static const char sql[] =
        "SELECT p.user_hash,f.ed2k_hash,COALESCE(p.username,''),COALESCE(f.canonical_name,''),"
        "COALESCE(f.size,0),ts.direction,ts.bytes_transferred,ts.average_bps,ts.successful,"
        "COALESCE(ts.result,''),COALESCE(ts.started_at,0),COALESCE(ts.finished_at,0) "
        "FROM transfer_sessions ts "
        "LEFT JOIN peers p ON p.id=ts.peer_id "
        "LEFT JOIN files f ON f.id=ts.file_id "
        "ORDER BY COALESCE(ts.finished_at,ts.started_at,0) DESC,ts.id DESC LIMIT ?1";

    sqlite3_stmt* statement = NULL;
    bool ok = sqlite3_prepare_v2(database, sql, -1, &statement, NULL) == SQLITE_OK;
    if (ok) {
        sqlite3_bind_int64(statement, 1, static_cast<sqlite3_int64>(limit));
        while (sqlite3_step(statement) == SQLITE_ROW) {
            EmuleNextTransferHistoryRecord item;
            item.peerHash = ColumnHash(statement, 0);
            item.fileHash = ColumnHash(statement, 1);
            item.userName = ColumnText(statement, 2);
            item.fileName = ColumnText(statement, 3);
            item.fileSize = static_cast<uint64>(sqlite3_column_int64(statement, 4));
            item.direction = ColumnText(statement, 5);
            item.bytesTransferred = static_cast<uint64>(sqlite3_column_int64(statement, 6));
            item.averageBytesPerSecond = static_cast<uint32>(sqlite3_column_int(statement, 7));
            item.successful = sqlite3_column_int(statement, 8) != 0;
            item.result = ColumnText(statement, 9);
            item.startedAt = static_cast<uint64>(sqlite3_column_int64(statement, 10));
            item.finishedAt = static_cast<uint64>(sqlite3_column_int64(statement, 11));
            transfers.push_back(item);
        }
    }

    if (statement != NULL)
        sqlite3_finalize(statement);
    sqlite3_close(database);
    return ok;
}
