//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "EmuleNextHistoryCache.h"
#include "PartFile.h"

#include <winsqlite3.h>
#include <algorithm>

EmuleNextFileHistory::EmuleNextFileHistory()
    : ewmaBytesPerSecond(0.0)
    , samples(0)
    , lastObserved(0)
{
}

CEmuleNextHistoryCache::CEmuleNextHistoryCache()
    : m_capacity(4096)
    , m_generation(0)
    , m_stopPersistence(false)
    , m_persistenceReady(false)
{
}

CEmuleNextHistoryCache::~CEmuleNextHistoryCache()
{
    StopPersistence();
}

bool CEmuleNextHistoryCache::MakeKey(const unsigned char* hash, Key& key)
{
    if (hash == NULL)
        return false;
    unsigned char aggregate = 0;
    for (size_t i = 0; i < key.size(); ++i) {
        key[i] = hash[i];
        aggregate |= hash[i];
    }
    return aggregate != 0;
}

void CEmuleNextHistoryCache::SetCapacity(size_t capacity)
{
    std::lock_guard<std::mutex> lock(m_mutex);
    m_capacity = std::max<size_t>(128, std::min<size_t>(16384, capacity));
    EnforceCapacityLocked();
}

void CEmuleNextHistoryCache::SetDatabasePath(const CStringW& databasePath)
{
    {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        if (databasePath == m_databasePath && m_persistThread.joinable())
            return;
    }

    StopPersistence();
    if (databasePath.IsEmpty())
        return;

    {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        m_databasePath = databasePath;
        m_stopPersistence = false;
        m_persistenceReady = false;
    }
    try {
        m_persistThread = std::thread(&CEmuleNextHistoryCache::PersistenceMain, this);
    }
    catch (...) {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        m_persistenceReady = false;
    }
}

void CEmuleNextHistoryCache::StopPersistence()
{
    {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        m_stopPersistence = true;
    }
    m_persistCondition.notify_all();
    if (m_persistThread.joinable())
        m_persistThread.join();
    {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        m_persistQueue.clear();
        m_databasePath.Empty();
        m_persistenceReady = false;
        m_stopPersistence = false;
    }
}

void CEmuleNextHistoryCache::Observe(const CPartFile* file)
{
    if (file == NULL)
        return;
    Key key;
    if (!MakeKey(file->GetFileHash(), key))
        return;

    const double current = static_cast<double>(file->GetDatarate());
    const uint64 now = static_cast<uint64>(time(NULL));
    EmuleNextFileHistory snapshot;
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        EmuleNextFileHistory& item = m_files[key];
        if (item.samples == 0)
            item.ewmaBytesPerSecond = current;
        else
            item.ewmaBytesPerSecond = item.ewmaBytesPerSecond * 0.82 + current * 0.18;
        ++item.samples;
        item.lastObserved = now;
        snapshot = item;
        ++m_generation;
        EnforceCapacityLocked();
    }

    // Persistence is deliberately outside the cache lock and only enqueues a
    // small value object. No SQLite work runs on the scheduler/core thread.
    QueuePersistLocked(key, snapshot);
}

void CEmuleNextHistoryCache::QueuePersistLocked(const Key& key, const EmuleNextFileHistory& history)
{
    std::lock_guard<std::mutex> lock(m_persistMutex);
    if (!m_persistThread.joinable())
        return;
    if (m_persistQueue.size() >= 8192)
        m_persistQueue.pop_front();
    PersistItem item;
    item.key = key;
    item.history = history;
    m_persistQueue.push_back(item);
    m_persistCondition.notify_one();
}

void CEmuleNextHistoryCache::EnforceCapacityLocked()
{
    while (m_files.size() > m_capacity && !m_files.empty()) {
        std::map<Key, EmuleNextFileHistory>::iterator oldest = m_files.begin();
        for (std::map<Key, EmuleNextFileHistory>::iterator it = m_files.begin(); it != m_files.end(); ++it)
            if (it->second.lastObserved < oldest->second.lastObserved)
                oldest = it;
        m_files.erase(oldest);
    }
}

double CEmuleNextHistoryCache::HistoricalBytesPerSecond(const unsigned char* fileHash) const
{
    EmuleNextFileHistory history;
    return GetHistory(fileHash, history) ? history.ewmaBytesPerSecond : 0.0;
}

bool CEmuleNextHistoryCache::GetHistory(const unsigned char* fileHash, EmuleNextFileHistory& history) const
{
    Key key;
    if (!MakeKey(fileHash, key))
        return false;
    std::lock_guard<std::mutex> lock(m_mutex);
    const std::map<Key, EmuleNextFileHistory>::const_iterator it = m_files.find(key);
    if (it == m_files.end())
        return false;
    history = it->second;
    return true;
}

size_t CEmuleNextHistoryCache::Size() const
{
    std::lock_guard<std::mutex> lock(m_mutex);
    return m_files.size();
}

uint64 CEmuleNextHistoryCache::Generation() const
{
    std::lock_guard<std::mutex> lock(m_mutex);
    return m_generation;
}

bool CEmuleNextHistoryCache::PersistenceReady() const
{
    std::lock_guard<std::mutex> lock(m_persistMutex);
    return m_persistenceReady;
}

void CEmuleNextHistoryCache::Clear()
{
    std::lock_guard<std::mutex> lock(m_mutex);
    m_files.clear();
    ++m_generation;
}

void CEmuleNextHistoryCache::PersistenceMain()
{
    CStringW path;
    {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        path = m_databasePath;
    }

    sqlite3* db = NULL;
    bool ready = sqlite3_open16(path.GetString(), &db) == SQLITE_OK;
    if (ready) {
        sqlite3_busy_timeout(db, 3000);
        const char* schema =
            "CREATE TABLE IF NOT EXISTS scheduler_file_history("
            "file_hash BLOB PRIMARY KEY,ewma_bps REAL NOT NULL DEFAULT 0,"
            "samples INTEGER NOT NULL DEFAULT 0,last_observed INTEGER NOT NULL DEFAULT 0);";
        ready = sqlite3_exec(db, schema, NULL, NULL, NULL) == SQLITE_OK;
    }

    if (ready) {
        sqlite3_stmt* stmt = NULL;
        if (sqlite3_prepare_v2(db,
            "SELECT file_hash,ewma_bps,samples,last_observed FROM scheduler_file_history ORDER BY last_observed DESC LIMIT 16384",
            -1, &stmt, NULL) == SQLITE_OK) {
            std::lock_guard<std::mutex> lock(m_mutex);
            while (sqlite3_step(stmt) == SQLITE_ROW) {
                const unsigned char* hash = static_cast<const unsigned char*>(sqlite3_column_blob(stmt, 0));
                const int bytes = sqlite3_column_bytes(stmt, 0);
                Key key;
                if (bytes != 16 || !MakeKey(hash, key))
                    continue;
                EmuleNextFileHistory persisted;
                persisted.ewmaBytesPerSecond = sqlite3_column_double(stmt, 1);
                persisted.samples = static_cast<uint32>(sqlite3_column_int64(stmt, 2));
                persisted.lastObserved = static_cast<uint64>(sqlite3_column_int64(stmt, 3));
                std::map<Key, EmuleNextFileHistory>::iterator existing = m_files.find(key);
                if (existing == m_files.end() || persisted.lastObserved > existing->second.lastObserved)
                    m_files[key] = persisted;
            }
            EnforceCapacityLocked();
            ++m_generation;
        }
        if (stmt != NULL)
            sqlite3_finalize(stmt);
    }

    {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        m_persistenceReady = ready;
    }

    while (ready) {
        std::deque<PersistItem> batch;
        {
            std::unique_lock<std::mutex> lock(m_persistMutex);
            m_persistCondition.wait_for(lock, std::chrono::milliseconds(500), [this]() {
                return m_stopPersistence || !m_persistQueue.empty();
            });
            const size_t count = std::min<size_t>(256, m_persistQueue.size());
            for (size_t i = 0; i < count; ++i) {
                batch.push_back(m_persistQueue.front());
                m_persistQueue.pop_front();
            }
            if (m_stopPersistence && batch.empty() && m_persistQueue.empty())
                break;
        }
        if (batch.empty())
            continue;

        sqlite3_exec(db, "BEGIN IMMEDIATE", NULL, NULL, NULL);
        sqlite3_stmt* stmt = NULL;
        const char* sql =
            "INSERT INTO scheduler_file_history(file_hash,ewma_bps,samples,last_observed) VALUES(?1,?2,?3,?4) "
            "ON CONFLICT(file_hash) DO UPDATE SET ewma_bps=excluded.ewma_bps,samples=excluded.samples,last_observed=excluded.last_observed "
            "WHERE excluded.last_observed>=scheduler_file_history.last_observed";
        if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK) {
            for (std::deque<PersistItem>::const_iterator it = batch.begin(); it != batch.end(); ++it) {
                sqlite3_reset(stmt);
                sqlite3_clear_bindings(stmt);
                sqlite3_bind_blob(stmt, 1, it->key.data(), 16, SQLITE_TRANSIENT);
                sqlite3_bind_double(stmt, 2, it->history.ewmaBytesPerSecond);
                sqlite3_bind_int64(stmt, 3, static_cast<sqlite3_int64>(it->history.samples));
                sqlite3_bind_int64(stmt, 4, static_cast<sqlite3_int64>(it->history.lastObserved));
                sqlite3_step(stmt);
            }
        }
        if (stmt != NULL)
            sqlite3_finalize(stmt);
        sqlite3_exec(db, "COMMIT", NULL, NULL, NULL);
    }

    if (db != NULL)
        sqlite3_close(db);
    {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        m_persistenceReady = false;
    }
}
