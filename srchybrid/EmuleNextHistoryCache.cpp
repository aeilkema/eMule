//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "EmuleNextHistoryCache.h"
#include "PartFile.h"

EmuleNextFileHistory::EmuleNextFileHistory()
    : ewmaBytesPerSecond(0.0)
    , samples(0)
    , lastObserved(0)
{
}

CEmuleNextHistoryCache::CEmuleNextHistoryCache()
{
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

void CEmuleNextHistoryCache::Observe(const CPartFile* file)
{
    if (file == NULL)
        return;
    Key key;
    if (!MakeKey(file->GetFileHash(), key))
        return;

    const double current = static_cast<double>(file->GetDatarate());
    const uint64 now = static_cast<uint64>(time(NULL));
    std::lock_guard<std::mutex> lock(m_mutex);
    EmuleNextFileHistory& item = m_files[key];
    if (item.samples == 0)
        item.ewmaBytesPerSecond = current;
    else
        item.ewmaBytesPerSecond = item.ewmaBytesPerSecond * 0.82 + current * 0.18;
    ++item.samples;
    item.lastObserved = now;

    if (m_files.size() > 4096) {
        std::map<Key, EmuleNextFileHistory>::iterator oldest = m_files.begin();
        for (std::map<Key, EmuleNextFileHistory>::iterator it = m_files.begin(); it != m_files.end(); ++it)
            if (it->second.lastObserved < oldest->second.lastObserved)
                oldest = it;
        m_files.erase(oldest);
    }
}

double CEmuleNextHistoryCache::HistoricalBytesPerSecond(const unsigned char* fileHash) const
{
    Key key;
    if (!MakeKey(fileHash, key))
        return 0.0;
    std::lock_guard<std::mutex> lock(m_mutex);
    const std::map<Key, EmuleNextFileHistory>::const_iterator it = m_files.find(key);
    return it == m_files.end() ? 0.0 : it->second.ewmaBytesPerSecond;
}

size_t CEmuleNextHistoryCache::Size() const
{
    std::lock_guard<std::mutex> lock(m_mutex);
    return m_files.size();
}

void CEmuleNextHistoryCache::Clear()
{
    std::lock_guard<std::mutex> lock(m_mutex);
    m_files.clear();
}
