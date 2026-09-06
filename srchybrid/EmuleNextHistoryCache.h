//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include <array>
#include <condition_variable>
#include <deque>
#include <map>
#include <mutex>
#include <thread>

class CPartFile;

struct EmuleNextFileHistory
{
    double ewmaBytesPerSecond;
    uint32 samples;
    uint64 lastObserved;

    EmuleNextFileHistory();
};

class CEmuleNextHistoryCache
{
public:
    CEmuleNextHistoryCache();
    ~CEmuleNextHistoryCache();

    void SetCapacity(size_t capacity);
    void SetDatabasePath(const CStringW& databasePath);
    void Observe(const CPartFile* file);
    double HistoricalBytesPerSecond(const unsigned char* fileHash) const;
    bool GetHistory(const unsigned char* fileHash, EmuleNextFileHistory& history) const;
    size_t Size() const;
    uint64 Generation() const;
    bool PersistenceReady() const;
    size_t PendingPersistenceWrites() const;
    uint64 DroppedPersistenceWrites() const;
    void Clear();

private:
    typedef std::array<unsigned char, 16> Key;
    struct PersistItem
    {
        Key key;
        EmuleNextFileHistory history;
    };

    static bool MakeKey(const unsigned char* hash, Key& key);
    void EnforceCapacityLocked();
    void QueuePersistLocked(const Key& key, const EmuleNextFileHistory& history);
    void StopPersistence();
    void PersistenceMain();

    mutable std::mutex m_mutex;
    std::map<Key, EmuleNextFileHistory> m_files;
    size_t m_capacity;
    uint64 m_generation;

    mutable std::mutex m_persistMutex;
    std::condition_variable m_persistCondition;
    std::deque<PersistItem> m_persistQueue;
    std::thread m_persistThread;
    CStringW m_databasePath;
    bool m_stopPersistence;
    bool m_persistenceReady;
    bool m_persistenceStarting;
    uint64 m_droppedPersistWrites;
};
