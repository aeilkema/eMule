//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include <array>
#include <map>
#include <mutex>

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

    void Observe(const CPartFile* file);
    double HistoricalBytesPerSecond(const unsigned char* fileHash) const;
    size_t Size() const;
    void Clear();

private:
    typedef std::array<unsigned char, 16> Key;
    static bool MakeKey(const unsigned char* hash, Key& key);

    mutable std::mutex m_mutex;
    std::map<Key, EmuleNextFileHistory> m_files;
};
