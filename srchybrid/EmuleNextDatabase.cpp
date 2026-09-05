//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//
//This program is free software; you can redistribute it and/or
//modify it under the terms of the GNU General Public License
//as published by the Free Software Foundation; either
//version 2 of the License, or (at your option) any later version.
#include "stdafx.h"
#include "EmuleNextDatabase.h"

#include <winsqlite3.h>
#include <algorithm>
#include <atomic>
#include <condition_variable>
#include <deque>
#include <mutex>
#include <thread>

namespace
{
    uint64 NowSeconds()
    {
        return static_cast<uint64>(time(NULL));
    }

    bool HashIsValid(const unsigned char* hash)
    {
        if (hash == NULL)
            return false;
        unsigned char aggregate = 0;
        for (size_t i = 0; i < 16; ++i)
            aggregate |= hash[i];
        return aggregate != 0;
    }

    bool ExecSql(sqlite3* db, const char* sql, CStringW* error = NULL)
    {
        char* rawError = NULL;
        const int rc = sqlite3_exec(db, sql, NULL, NULL, &rawError);
        if (rc == SQLITE_OK)
            return true;

        if (error != NULL) {
            if (rawError != NULL)
                *error = CStringW(CA2W(rawError, CP_UTF8));
            else
                error->Format(L"SQLite error %d", rc);
        }
        if (rawError != NULL)
            sqlite3_free(rawError);
        return false;
    }

    void BindHash(sqlite3_stmt* stmt, int index, const EmuleNextHash16& hash)
    {
        sqlite3_bind_blob(stmt, index, hash.bytes.data(), 16, SQLITE_TRANSIENT);
    }

    void BindText(sqlite3_stmt* stmt, int index, const CStringW& text)
    {
        if (text.IsEmpty())
            sqlite3_bind_null(stmt, index);
        else
            sqlite3_bind_text16(stmt, index, text.GetString(), -1, SQLITE_TRANSIENT);
    }

    CStringW ColumnText(sqlite3_stmt* stmt, int column)
    {
        const wchar_t* value = static_cast<const wchar_t*>(sqlite3_column_text16(stmt, column));
        return value != NULL ? CStringW(value) : CStringW();
    }

    enum class EventKind
    {
        PeerSeen,
        FileSeen,
        PeerFileSeen,
        Transfer,
        SaveFavorite,
        RemoveFavorite,
        DownloadLater,
        LibraryCompleted
    };

    struct DatabaseEvent
    {
        EventKind kind;
        EmuleNextPeerObservation peer;
        EmuleNextFileObservation file;
        EmuleNextPeerFileObservation peerFile;
        EmuleNextTransferObservation transfer;
        EmuleNextFavoriteRecord favorite;
        EmuleNextHash16 hash;
        uint64 fileSize;
        CStringW localPath;

        explicit DatabaseEvent(EventKind value)
            : kind(value), fileSize(0)
        {
        }
    };
}

EmuleNextHash16::EmuleNextHash16()
    : valid(false)
{
    bytes.fill(0);
}

EmuleNextHash16::EmuleNextHash16(const unsigned char* hash)
    : valid(HashIsValid(hash))
{
    bytes.fill(0);
    if (hash != NULL)
        memcpy(bytes.data(), hash, bytes.size());
}

EmuleNextPeerObservation::EmuleNextPeerObservation()
    : ip(0), tcpPort(0), udpPort(0), kadPort(0), seenAt(NowSeconds())
{
}

EmuleNextFileObservation::EmuleNextFileObservation()
    : fileSize(0), seenAt(NowSeconds())
{
}

EmuleNextPeerFileObservation::EmuleNextPeerFileObservation()
    : fileSize(0), seenAt(NowSeconds())
{
}

EmuleNextTransferObservation::EmuleNextTransferObservation()
    : fileSize(0), bytesTransferred(0), averageBytesPerSecond(0), successful(false), startedAt(0), finishedAt(NowSeconds())
{
}

EmuleNextFavoriteRecord::EmuleNextFavoriteRecord()
    : fileSize(0), autoRestore(false)
{
}

class CEmuleNextDatabase::Impl
{
public:
    Impl()
        : m_stop(false), m_running(false), m_initDone(false), m_initSucceeded(false)
    {
    }

    ~Impl()
    {
        Stop();
    }

    bool Start(const CStringW& databasePath)
    {
        Stop();
        {
            std::lock_guard<std::mutex> lock(m_mutex);
            m_databasePath = databasePath;
            m_stop = false;
            m_initDone = false;
            m_initSucceeded = false;
            m_lastError.Empty();
        }

        try {
            m_thread = std::thread(&Impl::WriterMain, this);
        }
        catch (...) {
            SetError(L"Unable to start SQLite writer thread");
            return false;
        }

        std::unique_lock<std::mutex> lock(m_mutex);
        m_initCondition.wait(lock, [this]() { return m_initDone; });
        return m_initSucceeded;
    }

    void Stop()
    {
        {
            std::lock_guard<std::mutex> lock(m_mutex);
            if (!m_thread.joinable()) {
                m_running = false;
                return;
            }
            m_stop = true;
        }
        m_condition.notify_all();
        m_thread.join();
        m_running = false;
    }

    bool IsRunning() const
    {
        return m_running.load();
    }

    CStringW GetLastError() const
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        return m_lastError;
    }

    CStringW GetDatabasePath() const
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        return m_databasePath;
    }

    void Queue(DatabaseEvent&& event)
    {
        if (!m_running.load())
            return;
        {
            std::lock_guard<std::mutex> lock(m_mutex);
            // Bound memory use if a damaged peer or import floods observations.
            if (m_queue.size() >= 50000) {
                m_lastError = L"eMule Next database queue reached safety limit; oldest event discarded";
                m_queue.pop_front();
            }
            m_queue.push_back(std::move(event));
        }
        m_condition.notify_one();
    }

    bool SearchFiles(const CStringW& text, size_t limit, size_t offset,
        std::vector<EmuleNextSearchFileResult>& results) const
    {
        results.clear();
        sqlite3* db = OpenReadConnection();
        if (db == NULL)
            return false;

        const char* sql =
            "SELECT f.ed2k_hash,f.size,COALESCE(f.canonical_name,''),COALESCE(f.aich_hash,''),"
            "f.first_seen,f.last_seen,"
            "(SELECT COUNT(DISTINCT pf.peer_id) FROM peer_files pf WHERE pf.file_id=f.id),"
            "EXISTS(SELECT 1 FROM favorites fav WHERE fav.file_id=f.id),"
            "EXISTS(SELECT 1 FROM library_entries le WHERE le.file_id=f.id AND le.completed_at IS NOT NULL) "
            "FROM files f WHERE (?1='' OR f.canonical_name LIKE ?2 COLLATE NOCASE OR "
            "EXISTS(SELECT 1 FROM file_names fn WHERE fn.file_id=f.id AND fn.name LIKE ?2 COLLATE NOCASE)) "
            "AND NOT EXISTS(SELECT 1 FROM blocked_hashes bh WHERE bh.ed2k_hash=f.ed2k_hash AND bh.size=f.size) "
            "ORDER BY f.last_seen DESC LIMIT ?3 OFFSET ?4";

        sqlite3_stmt* stmt = NULL;
        bool ok = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK;
        if (ok) {
            BindText(stmt, 1, text);
            CStringW like = L"%" + text + L"%";
            BindText(stmt, 2, like);
            sqlite3_bind_int64(stmt, 3, static_cast<sqlite3_int64>(limit));
            sqlite3_bind_int64(stmt, 4, static_cast<sqlite3_int64>(offset));

            while (sqlite3_step(stmt) == SQLITE_ROW) {
                EmuleNextSearchFileResult item;
                item.fileHash = EmuleNextHash16(static_cast<const unsigned char*>(sqlite3_column_blob(stmt, 0)));
                item.fileSize = static_cast<uint64>(sqlite3_column_int64(stmt, 1));
                item.fileName = ColumnText(stmt, 2);
                item.aichHash = ColumnText(stmt, 3);
                item.firstSeen = static_cast<uint64>(sqlite3_column_int64(stmt, 4));
                item.lastSeen = static_cast<uint64>(sqlite3_column_int64(stmt, 5));
                item.historicalPeerCount = static_cast<uint32>(sqlite3_column_int(stmt, 6));
                item.favorite = sqlite3_column_int(stmt, 7) != 0;
                item.completedBefore = sqlite3_column_int(stmt, 8) != 0;
                results.push_back(item);
            }
        }
        if (stmt != NULL)
            sqlite3_finalize(stmt);
        sqlite3_close(db);
        return ok;
    }

    bool HasCompletedFile(const EmuleNextHash16& hash, uint64 fileSize) const
    {
        return QueryFileFlag(hash, fileSize,
            "SELECT EXISTS(SELECT 1 FROM library_entries le JOIN files f ON f.id=le.file_id "
            "WHERE f.ed2k_hash=?1 AND f.size=?2 AND le.completed_at IS NOT NULL)");
    }

    bool IsFavorite(const EmuleNextHash16& hash, uint64 fileSize) const
    {
        return QueryFileFlag(hash, fileSize,
            "SELECT EXISTS(SELECT 1 FROM favorites fav JOIN files f ON f.id=fav.file_id "
            "WHERE f.ed2k_hash=?1 AND f.size=?2)");
    }

    bool IntegrityCheck(CStringW& result) const
    {
        result.Empty();
        sqlite3* db = OpenReadConnection();
        if (db == NULL)
            return false;
        sqlite3_stmt* stmt = NULL;
        const bool prepared = sqlite3_prepare_v2(db, "PRAGMA integrity_check", -1, &stmt, NULL) == SQLITE_OK;
        bool ok = false;
        if (prepared && sqlite3_step(stmt) == SQLITE_ROW) {
            result = ColumnText(stmt, 0);
            ok = result.CompareNoCase(L"ok") == 0;
        }
        if (stmt != NULL)
            sqlite3_finalize(stmt);
        sqlite3_close(db);
        return ok;
    }

    bool BackupTo(const CStringW& destinationPath) const
    {
        sqlite3* source = OpenReadConnection();
        if (source == NULL)
            return false;
        sqlite3* destination = NULL;
        bool ok = sqlite3_open16(destinationPath.GetString(), &destination) == SQLITE_OK;
        if (ok) {
            sqlite3_backup* backup = sqlite3_backup_init(destination, "main", source, "main");
            if (backup != NULL) {
                const int rc = sqlite3_backup_step(backup, -1);
                ok = rc == SQLITE_DONE;
                sqlite3_backup_finish(backup);
            }
            else
                ok = false;
        }
        if (destination != NULL)
            sqlite3_close(destination);
        sqlite3_close(source);
        return ok;
    }

private:
    void SetError(const CStringW& message)
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_lastError = message;
    }

    sqlite3* OpenReadConnection() const
    {
        CStringW path;
        {
            std::lock_guard<std::mutex> lock(m_mutex);
            path = m_databasePath;
        }
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

    bool QueryFileFlag(const EmuleNextHash16& hash, uint64 fileSize, const char* sql) const
    {
        if (!hash.valid)
            return false;
        sqlite3* db = OpenReadConnection();
        if (db == NULL)
            return false;
        sqlite3_stmt* stmt = NULL;
        bool value = false;
        if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK) {
            BindHash(stmt, 1, hash);
            sqlite3_bind_int64(stmt, 2, static_cast<sqlite3_int64>(fileSize));
            if (sqlite3_step(stmt) == SQLITE_ROW)
                value = sqlite3_column_int(stmt, 0) != 0;
        }
        if (stmt != NULL)
            sqlite3_finalize(stmt);
        sqlite3_close(db);
        return value;
    }

    bool Initialize(sqlite3* db)
    {
        CStringW error;
        if (!ExecSql(db, "PRAGMA journal_mode=WAL;", &error)
            || !ExecSql(db, "PRAGMA synchronous=NORMAL;", &error)
            || !ExecSql(db, "PRAGMA foreign_keys=ON;", &error)
            || !ExecSql(db, "PRAGMA temp_store=MEMORY;", &error)
            || !ExecSql(db, "PRAGMA busy_timeout=5000;", &error)) {
            SetError(error);
            return false;
        }

        static const char schema[] =
            "BEGIN IMMEDIATE;"
            "CREATE TABLE IF NOT EXISTS schema_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);"
            "INSERT OR REPLACE INTO schema_meta(key,value) VALUES('schema_version','1');"
            "CREATE TABLE IF NOT EXISTS peers("
            " id INTEGER PRIMARY KEY,user_hash BLOB NOT NULL UNIQUE,username TEXT,client_software TEXT,client_version TEXT,"
            " first_seen INTEGER NOT NULL,last_seen INTEGER NOT NULL);"
            "CREATE TABLE IF NOT EXISTS peer_endpoints("
            " id INTEGER PRIMARY KEY,peer_id INTEGER NOT NULL REFERENCES peers(id) ON DELETE CASCADE,"
            " ip INTEGER NOT NULL,tcp_port INTEGER NOT NULL DEFAULT 0,udp_port INTEGER NOT NULL DEFAULT 0,kad_port INTEGER NOT NULL DEFAULT 0,"
            " first_seen INTEGER NOT NULL,last_seen INTEGER NOT NULL,UNIQUE(peer_id,ip,tcp_port,udp_port,kad_port));"
            "CREATE INDEX IF NOT EXISTS idx_peer_endpoints_ip ON peer_endpoints(ip,tcp_port);"
            "CREATE TABLE IF NOT EXISTS files("
            " id INTEGER PRIMARY KEY,ed2k_hash BLOB NOT NULL,size INTEGER NOT NULL,aich_hash TEXT,canonical_name TEXT,"
            " first_seen INTEGER NOT NULL,last_seen INTEGER NOT NULL,UNIQUE(ed2k_hash,size));"
            "CREATE INDEX IF NOT EXISTS idx_files_last_seen ON files(last_seen DESC);"
            "CREATE TABLE IF NOT EXISTS file_names("
            " file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,name TEXT NOT NULL,first_seen INTEGER NOT NULL,last_seen INTEGER NOT NULL,"
            " PRIMARY KEY(file_id,name));"
            "CREATE INDEX IF NOT EXISTS idx_file_names_name ON file_names(name COLLATE NOCASE);"
            "CREATE TABLE IF NOT EXISTS peer_files("
            " peer_id INTEGER NOT NULL REFERENCES peers(id) ON DELETE CASCADE,file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,"
            " source_kind TEXT NOT NULL DEFAULT 'unknown',first_seen INTEGER NOT NULL,last_seen INTEGER NOT NULL,last_verified INTEGER,"
            " PRIMARY KEY(peer_id,file_id,source_kind));"
            "CREATE INDEX IF NOT EXISTS idx_peer_files_file ON peer_files(file_id,last_seen DESC);"
            "CREATE TABLE IF NOT EXISTS source_history("
            " peer_id INTEGER NOT NULL REFERENCES peers(id) ON DELETE CASCADE,file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,"
            " successful_sessions INTEGER NOT NULL DEFAULT 0,failed_sessions INTEGER NOT NULL DEFAULT 0,bytes_received INTEGER NOT NULL DEFAULT 0,"
            " ewma_bps REAL NOT NULL DEFAULT 0,last_success INTEGER,last_failure INTEGER,PRIMARY KEY(peer_id,file_id));"
            "CREATE TABLE IF NOT EXISTS transfer_sessions("
            " id INTEGER PRIMARY KEY,peer_id INTEGER REFERENCES peers(id) ON DELETE SET NULL,file_id INTEGER REFERENCES files(id) ON DELETE SET NULL,"
            " direction TEXT NOT NULL,started_at INTEGER,finished_at INTEGER,bytes_transferred INTEGER NOT NULL DEFAULT 0,average_bps INTEGER NOT NULL DEFAULT 0,"
            " successful INTEGER NOT NULL DEFAULT 0,result TEXT);"
            "CREATE INDEX IF NOT EXISTS idx_transfer_sessions_file ON transfer_sessions(file_id,finished_at DESC);"
            "CREATE TABLE IF NOT EXISTS favorites("
            " file_id INTEGER PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE,local_path TEXT,tags TEXT,auto_restore INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL);"
            "CREATE TABLE IF NOT EXISTS library_entries("
            " file_id INTEGER PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE,local_path TEXT,completed_at INTEGER,last_verified INTEGER,missing_since INTEGER);"
            "CREATE TABLE IF NOT EXISTS download_later("
            " file_id INTEGER PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE,added_at INTEGER NOT NULL,priority INTEGER NOT NULL DEFAULT 0);"
            "CREATE TABLE IF NOT EXISTS blocked_hashes("
            " ed2k_hash BLOB NOT NULL,size INTEGER NOT NULL,reason TEXT,created_at INTEGER NOT NULL,PRIMARY KEY(ed2k_hash,size));"
            "CREATE TABLE IF NOT EXISTS saved_searches("
            " id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,query TEXT NOT NULL,filters_json TEXT,last_run INTEGER,last_result_seen INTEGER);"
            "CREATE TABLE IF NOT EXISTS peer_share_scans("
            " peer_id INTEGER PRIMARY KEY REFERENCES peers(id) ON DELETE CASCADE,status TEXT NOT NULL DEFAULT 'unknown',"
            " last_requested INTEGER,last_completed INTEGER,next_allowed INTEGER,last_error TEXT);"
            "COMMIT;";

        if (!ExecSql(db, schema, &error)) {
            ExecSql(db, "ROLLBACK;");
            SetError(error);
            return false;
        }
        return true;
    }

    sqlite3_int64 EnsurePeer(sqlite3* db, const EmuleNextPeerObservation& peer)
    {
        if (!peer.userHash.valid)
            return 0;
        const uint64 seen = peer.seenAt != 0 ? peer.seenAt : NowSeconds();
        sqlite3_stmt* stmt = NULL;
        const char* insertSql = "INSERT OR IGNORE INTO peers(user_hash,username,client_software,client_version,first_seen,last_seen) VALUES(?1,?2,?3,?4,?5,?5)";
        if (sqlite3_prepare_v2(db, insertSql, -1, &stmt, NULL) == SQLITE_OK) {
            BindHash(stmt, 1, peer.userHash); BindText(stmt, 2, peer.userName); BindText(stmt, 3, peer.clientSoftware); BindText(stmt, 4, peer.clientVersion);
            sqlite3_bind_int64(stmt, 5, static_cast<sqlite3_int64>(seen)); sqlite3_step(stmt);
        }
        sqlite3_finalize(stmt); stmt = NULL;

        const char* updateSql = "UPDATE peers SET username=COALESCE(?2,username),client_software=COALESCE(?3,client_software),client_version=COALESCE(?4,client_version),last_seen=MAX(last_seen,?5) WHERE user_hash=?1";
        if (sqlite3_prepare_v2(db, updateSql, -1, &stmt, NULL) == SQLITE_OK) {
            BindHash(stmt, 1, peer.userHash); BindText(stmt, 2, peer.userName); BindText(stmt, 3, peer.clientSoftware); BindText(stmt, 4, peer.clientVersion);
            sqlite3_bind_int64(stmt, 5, static_cast<sqlite3_int64>(seen)); sqlite3_step(stmt);
        }
        sqlite3_finalize(stmt); stmt = NULL;

        sqlite3_int64 peerId = 0;
        if (sqlite3_prepare_v2(db, "SELECT id FROM peers WHERE user_hash=?1", -1, &stmt, NULL) == SQLITE_OK) {
            BindHash(stmt, 1, peer.userHash);
            if (sqlite3_step(stmt) == SQLITE_ROW)
                peerId = sqlite3_column_int64(stmt, 0);
        }
        sqlite3_finalize(stmt); stmt = NULL;

        if (peerId != 0 && peer.ip != 0) {
            const char* endpointInsert = "INSERT OR IGNORE INTO peer_endpoints(peer_id,ip,tcp_port,udp_port,kad_port,first_seen,last_seen) VALUES(?1,?2,?3,?4,?5,?6,?6)";
            if (sqlite3_prepare_v2(db, endpointInsert, -1, &stmt, NULL) == SQLITE_OK) {
                sqlite3_bind_int64(stmt, 1, peerId); sqlite3_bind_int64(stmt, 2, peer.ip); sqlite3_bind_int(stmt, 3, peer.tcpPort);
                sqlite3_bind_int(stmt, 4, peer.udpPort); sqlite3_bind_int(stmt, 5, peer.kadPort); sqlite3_bind_int64(stmt, 6, static_cast<sqlite3_int64>(seen)); sqlite3_step(stmt);
            }
            sqlite3_finalize(stmt); stmt = NULL;
            const char* endpointUpdate = "UPDATE peer_endpoints SET last_seen=MAX(last_seen,?6) WHERE peer_id=?1 AND ip=?2 AND tcp_port=?3 AND udp_port=?4 AND kad_port=?5";
            if (sqlite3_prepare_v2(db, endpointUpdate, -1, &stmt, NULL) == SQLITE_OK) {
                sqlite3_bind_int64(stmt, 1, peerId); sqlite3_bind_int64(stmt, 2, peer.ip); sqlite3_bind_int(stmt, 3, peer.tcpPort);
                sqlite3_bind_int(stmt, 4, peer.udpPort); sqlite3_bind_int(stmt, 5, peer.kadPort); sqlite3_bind_int64(stmt, 6, static_cast<sqlite3_int64>(seen)); sqlite3_step(stmt);
            }
            sqlite3_finalize(stmt);
        }
        return peerId;
    }

    sqlite3_int64 EnsureFile(sqlite3* db, const EmuleNextFileObservation& file)
    {
        if (!file.ed2kHash.valid || file.fileSize == 0)
            return 0;
        const uint64 seen = file.seenAt != 0 ? file.seenAt : NowSeconds();
        sqlite3_stmt* stmt = NULL;
        const char* insertSql = "INSERT OR IGNORE INTO files(ed2k_hash,size,aich_hash,canonical_name,first_seen,last_seen) VALUES(?1,?2,?3,?4,?5,?5)";
        if (sqlite3_prepare_v2(db, insertSql, -1, &stmt, NULL) == SQLITE_OK) {
            BindHash(stmt, 1, file.ed2kHash); sqlite3_bind_int64(stmt, 2, static_cast<sqlite3_int64>(file.fileSize)); BindText(stmt, 3, file.aichHash); BindText(stmt, 4, file.fileName);
            sqlite3_bind_int64(stmt, 5, static_cast<sqlite3_int64>(seen)); sqlite3_step(stmt);
        }
        sqlite3_finalize(stmt); stmt = NULL;
        const char* updateSql = "UPDATE files SET aich_hash=COALESCE(?3,aich_hash),canonical_name=COALESCE(?4,canonical_name),last_seen=MAX(last_seen,?5) WHERE ed2k_hash=?1 AND size=?2";
        if (sqlite3_prepare_v2(db, updateSql, -1, &stmt, NULL) == SQLITE_OK) {
            BindHash(stmt, 1, file.ed2kHash); sqlite3_bind_int64(stmt, 2, static_cast<sqlite3_int64>(file.fileSize)); BindText(stmt, 3, file.aichHash); BindText(stmt, 4, file.fileName);
            sqlite3_bind_int64(stmt, 5, static_cast<sqlite3_int64>(seen)); sqlite3_step(stmt);
        }
        sqlite3_finalize(stmt); stmt = NULL;
        sqlite3_int64 fileId = 0;
        if (sqlite3_prepare_v2(db, "SELECT id FROM files WHERE ed2k_hash=?1 AND size=?2", -1, &stmt, NULL) == SQLITE_OK) {
            BindHash(stmt, 1, file.ed2kHash); sqlite3_bind_int64(stmt, 2, static_cast<sqlite3_int64>(file.fileSize));
            if (sqlite3_step(stmt) == SQLITE_ROW)
                fileId = sqlite3_column_int64(stmt, 0);
        }
        sqlite3_finalize(stmt); stmt = NULL;
        if (fileId != 0 && !file.fileName.IsEmpty()) {
            if (sqlite3_prepare_v2(db, "INSERT OR IGNORE INTO file_names(file_id,name,first_seen,last_seen) VALUES(?1,?2,?3,?3)", -1, &stmt, NULL) == SQLITE_OK) {
                sqlite3_bind_int64(stmt, 1, fileId); BindText(stmt, 2, file.fileName); sqlite3_bind_int64(stmt, 3, static_cast<sqlite3_int64>(seen)); sqlite3_step(stmt);
            }
            sqlite3_finalize(stmt); stmt = NULL;
            if (sqlite3_prepare_v2(db, "UPDATE file_names SET last_seen=MAX(last_seen,?3) WHERE file_id=?1 AND name=?2", -1, &stmt, NULL) == SQLITE_OK) {
                sqlite3_bind_int64(stmt, 1, fileId); BindText(stmt, 2, file.fileName); sqlite3_bind_int64(stmt, 3, static_cast<sqlite3_int64>(seen)); sqlite3_step(stmt);
            }
            sqlite3_finalize(stmt);
        }
        return fileId;
    }

    void ProcessEvent(sqlite3* db, const DatabaseEvent& event)
    {
        if (event.kind == EventKind::PeerSeen) {
            EnsurePeer(db, event.peer);
            return;
        }
        if (event.kind == EventKind::FileSeen) {
            EnsureFile(db, event.file);
            return;
        }
        if (event.kind == EventKind::PeerFileSeen) {
            EmuleNextPeerObservation peer; peer.userHash = event.peerFile.peerHash; peer.seenAt = event.peerFile.seenAt;
            EmuleNextFileObservation file; file.ed2kHash = event.peerFile.fileHash; file.fileSize = event.peerFile.fileSize; file.fileName = event.peerFile.fileName; file.aichHash = event.peerFile.aichHash; file.seenAt = event.peerFile.seenAt;
            const sqlite3_int64 peerId = EnsurePeer(db, peer);
            const sqlite3_int64 fileId = EnsureFile(db, file);
            if (peerId != 0 && fileId != 0) {
                sqlite3_stmt* stmt = NULL;
                const char* sql = "INSERT OR IGNORE INTO peer_files(peer_id,file_id,source_kind,first_seen,last_seen,last_verified) VALUES(?1,?2,COALESCE(?3,'unknown'),?4,?4,?4)";
                if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK) {
                    sqlite3_bind_int64(stmt, 1, peerId); sqlite3_bind_int64(stmt, 2, fileId); BindText(stmt, 3, event.peerFile.sourceKind); sqlite3_bind_int64(stmt, 4, static_cast<sqlite3_int64>(event.peerFile.seenAt)); sqlite3_step(stmt);
                }
                sqlite3_finalize(stmt); stmt = NULL;
                if (sqlite3_prepare_v2(db, "UPDATE peer_files SET last_seen=MAX(last_seen,?4),last_verified=?4 WHERE peer_id=?1 AND file_id=?2 AND source_kind=COALESCE(?3,'unknown')", -1, &stmt, NULL) == SQLITE_OK) {
                    sqlite3_bind_int64(stmt, 1, peerId); sqlite3_bind_int64(stmt, 2, fileId); BindText(stmt, 3, event.peerFile.sourceKind); sqlite3_bind_int64(stmt, 4, static_cast<sqlite3_int64>(event.peerFile.seenAt)); sqlite3_step(stmt);
                }
                sqlite3_finalize(stmt);
            }
            return;
        }
        if (event.kind == EventKind::Transfer) {
            EmuleNextPeerObservation peer; peer.userHash = event.transfer.peerHash; peer.seenAt = event.transfer.finishedAt;
            EmuleNextFileObservation file; file.ed2kHash = event.transfer.fileHash; file.fileSize = event.transfer.fileSize; file.seenAt = event.transfer.finishedAt;
            const sqlite3_int64 peerId = EnsurePeer(db, peer); const sqlite3_int64 fileId = EnsureFile(db, file);
            sqlite3_stmt* stmt = NULL;
            if (sqlite3_prepare_v2(db, "INSERT INTO transfer_sessions(peer_id,file_id,direction,started_at,finished_at,bytes_transferred,average_bps,successful,result) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9)", -1, &stmt, NULL) == SQLITE_OK) {
                if (peerId != 0) sqlite3_bind_int64(stmt, 1, peerId); else sqlite3_bind_null(stmt, 1);
                if (fileId != 0) sqlite3_bind_int64(stmt, 2, fileId); else sqlite3_bind_null(stmt, 2);
                BindText(stmt, 3, event.transfer.direction); sqlite3_bind_int64(stmt, 4, static_cast<sqlite3_int64>(event.transfer.startedAt)); sqlite3_bind_int64(stmt, 5, static_cast<sqlite3_int64>(event.transfer.finishedAt));
                sqlite3_bind_int64(stmt, 6, static_cast<sqlite3_int64>(event.transfer.bytesTransferred)); sqlite3_bind_int(stmt, 7, event.transfer.averageBytesPerSecond); sqlite3_bind_int(stmt, 8, event.transfer.successful ? 1 : 0); BindText(stmt, 9, event.transfer.result); sqlite3_step(stmt);
            }
            sqlite3_finalize(stmt); stmt = NULL;
            if (peerId != 0 && fileId != 0) {
                if (sqlite3_prepare_v2(db, "INSERT OR IGNORE INTO source_history(peer_id,file_id) VALUES(?1,?2)", -1, &stmt, NULL) == SQLITE_OK) {
                    sqlite3_bind_int64(stmt, 1, peerId); sqlite3_bind_int64(stmt, 2, fileId); sqlite3_step(stmt);
                }
                sqlite3_finalize(stmt); stmt = NULL;
                const char* update = event.transfer.successful
                    ? "UPDATE source_history SET successful_sessions=successful_sessions+1,bytes_received=bytes_received+?3,ewma_bps=CASE WHEN ewma_bps=0 THEN ?4 ELSE ewma_bps*0.75+?4*0.25 END,last_success=?5 WHERE peer_id=?1 AND file_id=?2"
                    : "UPDATE source_history SET failed_sessions=failed_sessions+1,last_failure=?5 WHERE peer_id=?1 AND file_id=?2";
                if (sqlite3_prepare_v2(db, update, -1, &stmt, NULL) == SQLITE_OK) {
                    sqlite3_bind_int64(stmt, 1, peerId); sqlite3_bind_int64(stmt, 2, fileId); sqlite3_bind_int64(stmt, 3, static_cast<sqlite3_int64>(event.transfer.bytesTransferred)); sqlite3_bind_int(stmt, 4, event.transfer.averageBytesPerSecond); sqlite3_bind_int64(stmt, 5, static_cast<sqlite3_int64>(event.transfer.finishedAt)); sqlite3_step(stmt);
                }
                sqlite3_finalize(stmt);
            }
            return;
        }

        EmuleNextFileObservation file;
        if (event.kind == EventKind::SaveFavorite) {
            file.ed2kHash = event.favorite.fileHash; file.fileSize = event.favorite.fileSize; file.fileName = event.favorite.fileName; file.aichHash = event.favorite.aichHash;
        }
        else
            file = event.file;
        const sqlite3_int64 fileId = EnsureFile(db, file);
        sqlite3_stmt* stmt = NULL;
        if (event.kind == EventKind::SaveFavorite && fileId != 0) {
            if (sqlite3_prepare_v2(db, "INSERT OR REPLACE INTO favorites(file_id,local_path,tags,auto_restore,created_at) VALUES(?1,?2,?3,?4,COALESCE((SELECT created_at FROM favorites WHERE file_id=?1),?5))", -1, &stmt, NULL) == SQLITE_OK) {
                sqlite3_bind_int64(stmt, 1, fileId); BindText(stmt, 2, event.favorite.localPath); BindText(stmt, 3, event.favorite.tags); sqlite3_bind_int(stmt, 4, event.favorite.autoRestore ? 1 : 0); sqlite3_bind_int64(stmt, 5, static_cast<sqlite3_int64>(NowSeconds())); sqlite3_step(stmt);
            }
        }
        else if (event.kind == EventKind::RemoveFavorite && event.hash.valid) {
            if (sqlite3_prepare_v2(db, "DELETE FROM favorites WHERE file_id=(SELECT id FROM files WHERE ed2k_hash=?1 AND size=?2)", -1, &stmt, NULL) == SQLITE_OK) {
                BindHash(stmt, 1, event.hash); sqlite3_bind_int64(stmt, 2, static_cast<sqlite3_int64>(event.fileSize)); sqlite3_step(stmt);
            }
        }
        else if (event.kind == EventKind::DownloadLater && fileId != 0) {
            if (sqlite3_prepare_v2(db, "INSERT OR REPLACE INTO download_later(file_id,added_at,priority) VALUES(?1,?2,COALESCE((SELECT priority FROM download_later WHERE file_id=?1),0))", -1, &stmt, NULL) == SQLITE_OK) {
                sqlite3_bind_int64(stmt, 1, fileId); sqlite3_bind_int64(stmt, 2, static_cast<sqlite3_int64>(NowSeconds())); sqlite3_step(stmt);
            }
        }
        else if (event.kind == EventKind::LibraryCompleted && fileId != 0) {
            if (sqlite3_prepare_v2(db, "INSERT OR REPLACE INTO library_entries(file_id,local_path,completed_at,last_verified,missing_since) VALUES(?1,?2,?3,?3,NULL)", -1, &stmt, NULL) == SQLITE_OK) {
                sqlite3_bind_int64(stmt, 1, fileId); BindText(stmt, 2, event.localPath); sqlite3_bind_int64(stmt, 3, static_cast<sqlite3_int64>(NowSeconds())); sqlite3_step(stmt);
            }
        }
        if (stmt != NULL)
            sqlite3_finalize(stmt);
    }

    void WriterMain()
    {
        sqlite3* db = NULL;
        CStringW path;
        {
            std::lock_guard<std::mutex> lock(m_mutex);
            path = m_databasePath;
        }
        bool ready = sqlite3_open16(path.GetString(), &db) == SQLITE_OK;
        if (ready)
            ready = Initialize(db);
        else
            SetError(L"Unable to open eMule Next SQLite database");

        {
            std::lock_guard<std::mutex> lock(m_mutex);
            m_initSucceeded = ready;
            m_initDone = true;
            m_running = ready;
        }
        m_initCondition.notify_all();
        if (!ready) {
            if (db != NULL)
                sqlite3_close(db);
            return;
        }

        for (;;) {
            std::deque<DatabaseEvent> batch;
            {
                std::unique_lock<std::mutex> lock(m_mutex);
                m_condition.wait_for(lock, std::chrono::milliseconds(250), [this]() { return m_stop || !m_queue.empty(); });
                const size_t batchSize = std::min<size_t>(m_queue.size(), 512);
                for (size_t i = 0; i < batchSize; ++i) {
                    batch.push_back(std::move(m_queue.front()));
                    m_queue.pop_front();
                }
                if (m_stop && batch.empty() && m_queue.empty())
                    break;
            }
            if (!batch.empty()) {
                ExecSql(db, "BEGIN IMMEDIATE;");
                for (std::deque<DatabaseEvent>::const_iterator it = batch.begin(); it != batch.end(); ++it)
                    ProcessEvent(db, *it);
                if (!ExecSql(db, "COMMIT;"))
                    ExecSql(db, "ROLLBACK;");
            }
        }
        sqlite3_wal_checkpoint_v2(db, NULL, SQLITE_CHECKPOINT_PASSIVE, NULL, NULL);
        sqlite3_close(db);
        m_running = false;
    }

    mutable std::mutex m_mutex;
    std::condition_variable m_condition;
    std::condition_variable m_initCondition;
    std::deque<DatabaseEvent> m_queue;
    std::thread m_thread;
    bool m_stop;
    std::atomic<bool> m_running;
    bool m_initDone;
    bool m_initSucceeded;
    CStringW m_databasePath;
    CStringW m_lastError;
};

CEmuleNextDatabase::CEmuleNextDatabase()
    : m_impl(new Impl())
{
}

CEmuleNextDatabase::~CEmuleNextDatabase()
{
    delete m_impl;
}

bool CEmuleNextDatabase::Start(const CStringW& databasePath) { return m_impl->Start(databasePath); }
void CEmuleNextDatabase::Stop() { m_impl->Stop(); }
bool CEmuleNextDatabase::IsRunning() const { return m_impl->IsRunning(); }
CStringW CEmuleNextDatabase::GetLastError() const { return m_impl->GetLastError(); }
CStringW CEmuleNextDatabase::GetDatabasePath() const { return m_impl->GetDatabasePath(); }

void CEmuleNextDatabase::RecordPeerSeen(const EmuleNextPeerObservation& observation) { DatabaseEvent e(EventKind::PeerSeen); e.peer = observation; m_impl->Queue(std::move(e)); }
void CEmuleNextDatabase::RecordFileSeen(const EmuleNextFileObservation& observation) { DatabaseEvent e(EventKind::FileSeen); e.file = observation; m_impl->Queue(std::move(e)); }
void CEmuleNextDatabase::RecordPeerFileSeen(const EmuleNextPeerFileObservation& observation) { DatabaseEvent e(EventKind::PeerFileSeen); e.peerFile = observation; m_impl->Queue(std::move(e)); }
void CEmuleNextDatabase::RecordTransfer(const EmuleNextTransferObservation& observation) { DatabaseEvent e(EventKind::Transfer); e.transfer = observation; m_impl->Queue(std::move(e)); }
void CEmuleNextDatabase::SaveFavorite(const EmuleNextFavoriteRecord& favorite) { DatabaseEvent e(EventKind::SaveFavorite); e.favorite = favorite; m_impl->Queue(std::move(e)); }
void CEmuleNextDatabase::RemoveFavorite(const EmuleNextHash16& fileHash, uint64 fileSize) { DatabaseEvent e(EventKind::RemoveFavorite); e.hash = fileHash; e.fileSize = fileSize; m_impl->Queue(std::move(e)); }
void CEmuleNextDatabase::SaveDownloadLater(const EmuleNextFileObservation& file) { DatabaseEvent e(EventKind::DownloadLater); e.file = file; m_impl->Queue(std::move(e)); }
void CEmuleNextDatabase::MarkLibraryCompleted(const EmuleNextFileObservation& file, const CStringW& localPath) { DatabaseEvent e(EventKind::LibraryCompleted); e.file = file; e.localPath = localPath; m_impl->Queue(std::move(e)); }

bool CEmuleNextDatabase::SearchFiles(const CStringW& text, size_t limit, size_t offset, std::vector<EmuleNextSearchFileResult>& results) const { return m_impl->SearchFiles(text, limit, offset, results); }
bool CEmuleNextDatabase::HasCompletedFile(const EmuleNextHash16& fileHash, uint64 fileSize) const { return m_impl->HasCompletedFile(fileHash, fileSize); }
bool CEmuleNextDatabase::IsFavorite(const EmuleNextHash16& fileHash, uint64 fileSize) const { return m_impl->IsFavorite(fileHash, fileSize); }
bool CEmuleNextDatabase::IntegrityCheck(CStringW& result) const { return m_impl->IntegrityCheck(result); }
bool CEmuleNextDatabase::BackupTo(const CStringW& destinationPath) const { return m_impl->BackupTo(destinationPath); }
