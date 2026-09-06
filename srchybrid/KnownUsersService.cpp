//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later

#include "stdafx.h"
#include "KnownUsersService.h"
#include "EmuleNextWinSqliteCompat.h"

namespace
{
    const int kMaximumKnownUsers = 2000;
    const int kMaximumKnownFilesPerUser = 2000;
    const sqlite3_int64 kRecentSeconds = 7 * 24 * 60 * 60;

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

    sqlite3* OpenWrite(const CStringW& path)
    {
        if (path.IsEmpty())
            return NULL;
        sqlite3* database = NULL;
        if (sqlite3_open16(path.GetString(), &database) != SQLITE_OK) {
            if (database != NULL)
                sqlite3_close(database);
            return NULL;
        }
        sqlite3_busy_timeout(database, 3000);
        sqlite3_exec(database, "PRAGMA foreign_keys=ON;", NULL, NULL, NULL);
        return database;
    }

    EmuleNextHash16 ColumnHash(sqlite3_stmt* statement, int column)
    {
        const void* value = sqlite3_column_blob(statement, column);
        const int bytes = sqlite3_column_bytes(statement, column);
        return bytes == 16 && value != NULL
            ? EmuleNextHash16(static_cast<const unsigned char*>(value)) : EmuleNextHash16();
    }
}

CKnownUsersService::CKnownUsersService(const CStringW& databasePath)
    : m_databasePath(databasePath)
{
}

bool CKnownUsersService::ListUsers(EmuleNextKnownUsersQuery query,
    std::vector<EmuleNextKnownUserRecord>& users) const
{
    users.clear();
    sqlite3* database = OpenReadOnly(m_databasePath);
    if (database == NULL)
        return false;

    // peer_file_totals collapses source_kind duplicates once. The latest
    // endpoint lookup is backed by peer_endpoints' unique peer-first index.
    // Current/history is intentionally not encoded here; that state is live.
    static const char sql[] =
        "WITH peer_file_totals AS ("
        " SELECT d.peer_id,COUNT(*) AS file_count,COALESCE(SUM(f.size),0) AS total_bytes"
        " FROM (SELECT peer_id,file_id FROM peer_files GROUP BY peer_id,file_id) d"
        " JOIN files f ON f.id=d.file_id GROUP BY d.peer_id"
        ") "
        "SELECT p.user_hash,COALESCE(p.username,''),COALESCE(p.client_software,''),"
        "COALESCE(p.client_version,''),p.first_seen,p.last_seen,"
        "COALESCE(t.file_count,0),COALESCE(t.total_bytes,0),"
        "COALESCE(pm.alias,''),COALESCE(pm.favorite,0),"
        "COALESCE(pe.ip,0),COALESCE(pe.tcp_port,0),COALESCE(pe.udp_port,0),"
        "COALESCE(pe.kad_port,0),COALESCE(pe.first_seen,0),COALESCE(pe.last_seen,0) "
        "FROM peers p "
        "LEFT JOIN peer_file_totals t ON t.peer_id=p.id "
        "LEFT JOIN peer_metadata pm ON pm.user_hash=p.user_hash "
        "LEFT JOIN peer_endpoints pe ON pe.id=("
        " SELECT pe2.id FROM peer_endpoints pe2 WHERE pe2.peer_id=p.id"
        " ORDER BY pe2.last_seen DESC,pe2.id DESC LIMIT 1) "
        "WHERE (?1=0 OR (?1=1 AND COALESCE(pm.favorite,0)<>0)"
        " OR (?1=2 AND p.last_seen>=CAST(strftime('%s','now') AS INTEGER)-?2)) "
        "ORDER BY p.last_seen DESC,p.id DESC LIMIT ?3";

    sqlite3_stmt* statement = NULL;
    bool ok = sqlite3_prepare_v2(database, sql, -1, &statement, NULL) == SQLITE_OK;
    if (ok) {
        sqlite3_bind_int(statement, 1, static_cast<int>(query));
        sqlite3_bind_int64(statement, 2, kRecentSeconds);
        sqlite3_bind_int(statement, 3, kMaximumKnownUsers);
        while (sqlite3_step(statement) == SQLITE_ROW) {
            EmuleNextKnownUserRecord item;
            item.userHash = ColumnHash(statement, 0);
            if (!item.userHash.valid)
                continue;
            item.userName = ColumnText(statement, 1);
            item.clientSoftware = ColumnText(statement, 2);
            item.clientVersion = ColumnText(statement, 3);
            item.firstSeen = static_cast<uint64>(sqlite3_column_int64(statement, 4));
            item.lastSeen = static_cast<uint64>(sqlite3_column_int64(statement, 5));
            item.fileCount = static_cast<uint32>(sqlite3_column_int64(statement, 6));
            item.totalBytes = static_cast<uint64>(sqlite3_column_int64(statement, 7));
            item.alias = ColumnText(statement, 8);
            item.favorite = sqlite3_column_int(statement, 9) != 0;
            item.endpointIp = static_cast<uint32>(sqlite3_column_int64(statement, 10));
            item.endpointTcpPort = static_cast<uint16>(sqlite3_column_int(statement, 11));
            item.endpointUdpPort = static_cast<uint16>(sqlite3_column_int(statement, 12));
            item.endpointKadPort = static_cast<uint16>(sqlite3_column_int(statement, 13));
            item.endpointFirstSeen = static_cast<uint64>(sqlite3_column_int64(statement, 14));
            item.endpointLastSeen = static_cast<uint64>(sqlite3_column_int64(statement, 15));
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
        "f.size,MIN(pf.first_seen),MAX(pf.last_seen),COALESCE(MAX(pf.last_verified),0) "
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
            item.lastVerified = static_cast<uint64>(sqlite3_column_int64(statement, 6));
            files.push_back(item);
        }
    }

    if (statement != NULL)
        sqlite3_finalize(statement);
    sqlite3_close(database);
    return ok;
}

bool CKnownUsersService::DeletePeerHistory(const EmuleNextHash16& peerHash) const
{
    if (!peerHash.valid)
        return false;
    sqlite3* database = OpenWrite(m_databasePath);
    if (database == NULL)
        return false;

    sqlite3_stmt* statement = NULL;
    bool ok = sqlite3_exec(database, "BEGIN IMMEDIATE", NULL, NULL, NULL) == SQLITE_OK;
    if (ok)
        ok = sqlite3_prepare_v2(database, "DELETE FROM peers WHERE user_hash=?1", -1, &statement, NULL) == SQLITE_OK;
    if (ok) {
        sqlite3_bind_blob(statement, 1, peerHash.bytes.data(), 16, SQLITE_TRANSIENT);
        ok = sqlite3_step(statement) == SQLITE_DONE;
    }
    if (statement != NULL)
        sqlite3_finalize(statement);
    if (ok)
        ok = sqlite3_exec(database, "COMMIT", NULL, NULL, NULL) == SQLITE_OK;
    else
        sqlite3_exec(database, "ROLLBACK", NULL, NULL, NULL);
    sqlite3_close(database);
    return ok;
}
