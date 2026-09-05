//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//
//This program is free software; you can redistribute it and/or
//modify it under the terms of the GNU General Public License
//as published by the Free Software Foundation; either
//version 2 of the License, or (at your option) any later version.
#include "stdafx.h"
#include "EmuleNextRuntime.h"
#include "Preferences.h"
#include "Log.h"

#include <winsqlite3.h>

CEmuleNextRuntime theEmuleNext;

namespace
{
    uint64 RuntimeNowSeconds()
    {
        return static_cast<uint64>(time(NULL));
    }

    void BindRuntimeHash(sqlite3_stmt* stmt, int index, const EmuleNextHash16& hash)
    {
        sqlite3_bind_blob(stmt, index, hash.bytes.data(), 16, SQLITE_TRANSIENT);
    }

    void BindRuntimeText(sqlite3_stmt* stmt, int index, const CStringW& text)
    {
        sqlite3_bind_text16(stmt, index, text.GetString(), -1, SQLITE_TRANSIENT);
    }
}

CEmuleNextRuntime::CEmuleNextRuntime()
{
}

CEmuleNextRuntime::~CEmuleNextRuntime()
{
    Stop();
}

bool CEmuleNextRuntime::Start()
{
    if (m_database.IsRunning())
        return true;

    const CStringW databasePath = CStringW(thePrefs.GetMuleDirectory(EMULE_CONFIGDIR)) + L"emule-next.sqlite3";
    const bool started = m_database.Start(databasePath);
    if (started) {
        InitializePeerMetadata();
        AddLogLine(false, _T("eMule Next intelligence database: %s"), static_cast<LPCTSTR>(CString(databasePath)));
    }
    else
        AddLogLine(true, _T("eMule Next intelligence database disabled: %s"), static_cast<LPCTSTR>(CString(m_database.GetLastError())));
    return started;
}

void CEmuleNextRuntime::Stop()
{
    {
        std::lock_guard<std::mutex> lock(m_autoShareMutex);
        m_autoShareRequests.clear();
    }
    {
        std::lock_guard<std::mutex> lock(m_peerMetadataMutex);
        m_peerAliases.clear();
        m_peerFavorites.clear();
    }
    m_database.Stop();
}

bool CEmuleNextRuntime::IsRunning() const
{
    return m_database.IsRunning();
}

CEmuleNextDatabase& CEmuleNextRuntime::Database()
{
    return m_database;
}

const CEmuleNextDatabase& CEmuleNextRuntime::Database() const
{
    return m_database;
}

bool CEmuleNextRuntime::InitializePeerMetadata()
{
    if (!m_database.IsRunning())
        return false;

    sqlite3* db = NULL;
    const CStringW path = m_database.GetDatabasePath();
    if (sqlite3_open16(path.GetString(), &db) != SQLITE_OK) {
        if (db != NULL)
            sqlite3_close(db);
        return false;
    }

    sqlite3_busy_timeout(db, 3000);
    const char* schema =
        "CREATE TABLE IF NOT EXISTS peer_metadata("
        "user_hash BLOB PRIMARY KEY,"
        "alias TEXT NOT NULL DEFAULT '',"
        "favorite INTEGER NOT NULL DEFAULT 0,"
        "updated_at INTEGER NOT NULL);";
    const bool schemaOk = sqlite3_exec(db, schema, NULL, NULL, NULL) == SQLITE_OK;

    std::map<std::array<unsigned char, 16>, CStringW> aliases;
    std::map<std::array<unsigned char, 16>, bool> favorites;
    if (schemaOk) {
        sqlite3_stmt* stmt = NULL;
        if (sqlite3_prepare_v2(db, "SELECT user_hash,alias,favorite FROM peer_metadata", -1, &stmt, NULL) == SQLITE_OK) {
            while (sqlite3_step(stmt) == SQLITE_ROW) {
                const void* rawHash = sqlite3_column_blob(stmt, 0);
                const int hashSize = sqlite3_column_bytes(stmt, 0);
                if (rawHash == NULL || hashSize != 16)
                    continue;

                std::array<unsigned char, 16> key;
                memcpy(key.data(), rawHash, key.size());
                const wchar_t* rawAlias = static_cast<const wchar_t*>(sqlite3_column_text16(stmt, 1));
                if (rawAlias != NULL && *rawAlias != L'\0')
                    aliases[key] = CStringW(rawAlias);
                if (sqlite3_column_int(stmt, 2) != 0)
                    favorites[key] = true;
            }
        }
        if (stmt != NULL)
            sqlite3_finalize(stmt);
    }

    sqlite3_close(db);
    if (!schemaOk)
        return false;

    {
        std::lock_guard<std::mutex> lock(m_peerMetadataMutex);
        m_peerAliases.swap(aliases);
        m_peerFavorites.swap(favorites);
    }
    return true;
}

bool CEmuleNextRuntime::SavePeerMetadata(const EmuleNextHash16& hash, const CStringW& alias, bool favorite)
{
    if (!m_database.IsRunning() || !hash.valid)
        return false;

    sqlite3* db = NULL;
    const CStringW path = m_database.GetDatabasePath();
    if (sqlite3_open16(path.GetString(), &db) != SQLITE_OK) {
        if (db != NULL)
            sqlite3_close(db);
        return false;
    }

    sqlite3_busy_timeout(db, 3000);
    const char* schema =
        "CREATE TABLE IF NOT EXISTS peer_metadata("
        "user_hash BLOB PRIMARY KEY,alias TEXT NOT NULL DEFAULT '',favorite INTEGER NOT NULL DEFAULT 0,updated_at INTEGER NOT NULL);";
    bool ok = sqlite3_exec(db, schema, NULL, NULL, NULL) == SQLITE_OK;
    sqlite3_stmt* stmt = NULL;
    if (ok) {
        const char* sql =
            "INSERT OR REPLACE INTO peer_metadata(user_hash,alias,favorite,updated_at) "
            "VALUES(?1,?2,?3,?4)";
        ok = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK;
        if (ok) {
            BindRuntimeHash(stmt, 1, hash);
            BindRuntimeText(stmt, 2, alias);
            sqlite3_bind_int(stmt, 3, favorite ? 1 : 0);
            sqlite3_bind_int64(stmt, 4, static_cast<sqlite3_int64>(RuntimeNowSeconds()));
            ok = sqlite3_step(stmt) == SQLITE_DONE;
        }
    }
    if (stmt != NULL)
        sqlite3_finalize(stmt);
    sqlite3_close(db);
    return ok;
}

bool CEmuleNextRuntime::GetPeerAlias(const unsigned char* userHash, CString& alias) const
{
    alias.Empty();
    EmuleNextHash16 hash(userHash);
    if (!hash.valid)
        return false;

    std::lock_guard<std::mutex> lock(m_peerMetadataMutex);
    const std::map<std::array<unsigned char, 16>, CStringW>::const_iterator it = m_peerAliases.find(hash.bytes);
    if (it == m_peerAliases.end())
        return false;
    alias = CString(it->second);
    return !alias.IsEmpty();
}

bool CEmuleNextRuntime::SetPeerAlias(const unsigned char* userHash, const CString& alias)
{
    EmuleNextHash16 hash(userHash);
    if (!hash.valid)
        return false;

    CString trimmed(alias);
    trimmed.Trim();
    if (trimmed.GetLength() > 128)
        trimmed = trimmed.Left(128);

    bool favorite = false;
    {
        std::lock_guard<std::mutex> lock(m_peerMetadataMutex);
        const std::map<std::array<unsigned char, 16>, bool>::const_iterator it = m_peerFavorites.find(hash.bytes);
        favorite = it != m_peerFavorites.end() && it->second;
    }

    if (!SavePeerMetadata(hash, CStringW(trimmed), favorite))
        return false;

    std::lock_guard<std::mutex> lock(m_peerMetadataMutex);
    if (trimmed.IsEmpty())
        m_peerAliases.erase(hash.bytes);
    else
        m_peerAliases[hash.bytes] = CStringW(trimmed);
    return true;
}

bool CEmuleNextRuntime::IsPeerFavorite(const unsigned char* userHash) const
{
    EmuleNextHash16 hash(userHash);
    if (!hash.valid)
        return false;

    std::lock_guard<std::mutex> lock(m_peerMetadataMutex);
    const std::map<std::array<unsigned char, 16>, bool>::const_iterator it = m_peerFavorites.find(hash.bytes);
    return it != m_peerFavorites.end() && it->second;
}

bool CEmuleNextRuntime::SetPeerFavorite(const unsigned char* userHash, bool favorite)
{
    EmuleNextHash16 hash(userHash);
    if (!hash.valid)
        return false;

    CStringW alias;
    {
        std::lock_guard<std::mutex> lock(m_peerMetadataMutex);
        const std::map<std::array<unsigned char, 16>, CStringW>::const_iterator it = m_peerAliases.find(hash.bytes);
        if (it != m_peerAliases.end())
            alias = it->second;
    }

    if (!SavePeerMetadata(hash, alias, favorite))
        return false;

    std::lock_guard<std::mutex> lock(m_peerMetadataMutex);
    if (favorite)
        m_peerFavorites[hash.bytes] = true;
    else
        m_peerFavorites.erase(hash.bytes);
    return true;
}

void CEmuleNextRuntime::RecordPeerSeen(const unsigned char* userHash,
    LPCTSTR userName,
    const CString& clientSoftware,
    const CString& clientVersion,
    uint32 ip,
    uint16 tcpPort,
    uint16 udpPort,
    uint16 kadPort)
{
    EmuleNextPeerObservation observation;
    observation.userHash = EmuleNextHash16(userHash);
    if (!observation.userHash.valid)
        return;
    if (userName != NULL)
        observation.userName = CStringW(userName);
    observation.clientSoftware = CStringW(clientSoftware);
    observation.clientVersion = CStringW(clientVersion);
    observation.ip = ip;
    observation.tcpPort = tcpPort;
    observation.udpPort = udpPort;
    observation.kadPort = kadPort;
    m_database.RecordPeerSeen(observation);
}

void CEmuleNextRuntime::RecordFileSeen(const unsigned char* ed2kHash,
    uint64 fileSize,
    LPCTSTR fileName,
    const CString& aichHash)
{
    EmuleNextFileObservation observation;
    observation.ed2kHash = EmuleNextHash16(ed2kHash);
    if (!observation.ed2kHash.valid || fileSize == 0)
        return;
    observation.fileSize = fileSize;
    if (fileName != NULL)
        observation.fileName = CStringW(fileName);
    observation.aichHash = CStringW(aichHash);
    m_database.RecordFileSeen(observation);
}

void CEmuleNextRuntime::RecordPeerFileSeen(const unsigned char* peerHash,
    const unsigned char* ed2kHash,
    uint64 fileSize,
    LPCTSTR fileName,
    const CString& aichHash,
    LPCTSTR sourceKind)
{
    EmuleNextPeerFileObservation observation;
    observation.peerHash = EmuleNextHash16(peerHash);
    observation.fileHash = EmuleNextHash16(ed2kHash);
    if (!observation.peerHash.valid || !observation.fileHash.valid || fileSize == 0)
        return;
    observation.fileSize = fileSize;
    if (fileName != NULL)
        observation.fileName = CStringW(fileName);
    observation.aichHash = CStringW(aichHash);
    if (sourceKind != NULL)
        observation.sourceKind = CStringW(sourceKind);
    m_database.RecordPeerFileSeen(observation);
}

void CEmuleNextRuntime::MarkAutomaticPeerShareRequest(const unsigned char* peerHash, uint64 ttlSeconds)
{
    EmuleNextHash16 hash(peerHash);
    if (!hash.valid)
        return;

    if (ttlSeconds < 30)
        ttlSeconds = 30;

    std::lock_guard<std::mutex> lock(m_autoShareMutex);
    m_autoShareRequests[hash.bytes] = RuntimeNowSeconds() + ttlSeconds;
}

bool CEmuleNextRuntime::IsAutomaticPeerShareRequest(const unsigned char* peerHash) const
{
    EmuleNextHash16 hash(peerHash);
    if (!hash.valid)
        return false;

    const uint64 now = RuntimeNowSeconds();
    std::lock_guard<std::mutex> lock(m_autoShareMutex);
    const std::map<std::array<unsigned char, 16>, uint64>::iterator it = m_autoShareRequests.find(hash.bytes);
    if (it == m_autoShareRequests.end())
        return false;
    if (it->second < now) {
        m_autoShareRequests.erase(it);
        return false;
    }
    return true;
}

void CEmuleNextRuntime::CompleteAutomaticPeerShareRequest(const unsigned char* peerHash)
{
    EmuleNextHash16 hash(peerHash);
    if (!hash.valid)
        return;

    std::lock_guard<std::mutex> lock(m_autoShareMutex);
    m_autoShareRequests.erase(hash.bytes);
}
