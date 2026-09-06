//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "EmuleNextSchedulerTelemetryReader.h"

#include <winsqlite3.h>
#include <algorithm>
#include <cstring>

namespace
{
    sqlite3* OpenReadOnly(const CStringW& path)
    {
        if (path.IsEmpty())
            return NULL;
        sqlite3* db = NULL;
        if (sqlite3_open16(path.GetString(), &db) != SQLITE_OK) {
            if (db != NULL)
                sqlite3_close(db);
            return NULL;
        }
        sqlite3_busy_timeout(db, 1000);
        sqlite3_exec(db, "PRAGMA query_only=ON;", NULL, NULL, NULL);
        return db;
    }

    CString ColumnText(sqlite3_stmt* stmt, int column)
    {
        const TCHAR* value = static_cast<const TCHAR*>(sqlite3_column_text16(stmt, column));
        return value != NULL ? CString(value) : CString();
    }
}

CEmuleNextSchedulerTelemetryReader::CEmuleNextSchedulerTelemetryReader(const CStringW& databasePath)
    : m_databasePath(databasePath)
{
}

bool CEmuleNextSchedulerTelemetryReader::LoadRecentForFile(const unsigned char* fileHash,
    EmuleNextPersistedSchedulerBundle& result, size_t decisionLimit, size_t outcomeLimit) const
{
    result.decisions.clear();
    result.outcomes.clear();
    if (fileHash == NULL || m_databasePath.IsEmpty())
        return false;

    decisionLimit = std::max<size_t>(1, std::min<size_t>(100, decisionLimit));
    outcomeLimit = std::max<size_t>(1, std::min<size_t>(100, outcomeLimit));
    sqlite3* db = OpenReadOnly(m_databasePath);
    if (db == NULL)
        return false;

    bool ok = true;
    sqlite3_stmt* stmt = NULL;
    const char* decisionsSql =
        "SELECT ts,file_name,file_hash,mode,action,health,attention,discovery_budget,a4af_score,rare_part_index,applied,COALESCE(reason,'') "
        "FROM scheduler_decisions WHERE file_hash=?1 ORDER BY id DESC LIMIT ?2";
    if (sqlite3_prepare_v2(db, decisionsSql, -1, &stmt, NULL) == SQLITE_OK) {
        sqlite3_bind_blob(stmt, 1, fileHash, 16, SQLITE_TRANSIENT);
        sqlite3_bind_int64(stmt, 2, static_cast<sqlite3_int64>(decisionLimit));
        while (sqlite3_step(stmt) == SQLITE_ROW) {
            EmuleNextSchedulerEvent event;
            event.timestamp = static_cast<uint64>(sqlite3_column_int64(stmt, 0));
            event.fileName = ColumnText(stmt, 1);
            const void* hash = sqlite3_column_blob(stmt, 2);
            if (sqlite3_column_bytes(stmt, 2) == 16 && hash != NULL) {
                memcpy(event.fileHash.data(), hash, 16);
                event.fileHashValid = true;
            }
            event.mode = static_cast<EmuleNextSchedulingMode>(sqlite3_column_int(stmt, 3));
            event.action = static_cast<EmuleNextSchedulingAction>(sqlite3_column_int(stmt, 4));
            event.health = static_cast<uint32>(sqlite3_column_int64(stmt, 5));
            event.attention = static_cast<uint32>(sqlite3_column_int64(stmt, 6));
            event.discoveryBudget = static_cast<uint32>(sqlite3_column_int64(stmt, 7));
            event.a4afScore = static_cast<uint32>(sqlite3_column_int64(stmt, 8));
            event.rarePartIndex = sqlite3_column_type(stmt, 9) == SQLITE_NULL
                ? static_cast<uint32>(-1) : static_cast<uint32>(sqlite3_column_int64(stmt, 9));
            event.applied = sqlite3_column_int(stmt, 10) != 0;
            event.reason = ColumnText(stmt, 11);
            result.decisions.push_back(event);
        }
    } else {
        ok = false;
    }
    if (stmt != NULL) { sqlite3_finalize(stmt); stmt = NULL; }

    const char* outcomesSql =
        "SELECT ts,file_name,file_hash,action,window_seconds,bytes_per_second,usable_sources "
        "FROM scheduler_outcomes WHERE file_hash=?1 ORDER BY id DESC LIMIT ?2";
    if (ok && sqlite3_prepare_v2(db, outcomesSql, -1, &stmt, NULL) == SQLITE_OK) {
        sqlite3_bind_blob(stmt, 1, fileHash, 16, SQLITE_TRANSIENT);
        sqlite3_bind_int64(stmt, 2, static_cast<sqlite3_int64>(outcomeLimit));
        while (sqlite3_step(stmt) == SQLITE_ROW) {
            EmuleNextSchedulerOutcomeRecord outcome;
            outcome.timestamp = static_cast<uint64>(sqlite3_column_int64(stmt, 0));
            outcome.fileName = ColumnText(stmt, 1);
            const void* hash = sqlite3_column_blob(stmt, 2);
            if (sqlite3_column_bytes(stmt, 2) == 16 && hash != NULL) {
                memcpy(outcome.fileHash.data(), hash, 16);
                outcome.fileHashValid = true;
            }
            outcome.action = static_cast<EmuleNextSchedulingAction>(sqlite3_column_int(stmt, 3));
            outcome.windowSeconds = static_cast<uint32>(sqlite3_column_int64(stmt, 4));
            outcome.bytesPerSecond = sqlite3_column_double(stmt, 5);
            outcome.usableSources = static_cast<uint32>(sqlite3_column_int64(stmt, 6));
            result.outcomes.push_back(outcome);
        }
    } else if (ok) {
        ok = false;
    }
    if (stmt != NULL)
        sqlite3_finalize(stmt);
    sqlite3_close(db);
    return ok;
}
