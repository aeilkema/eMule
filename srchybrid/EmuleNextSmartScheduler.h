//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "DownloadIntelligence.h"
#include "EmuleNextHistoryCache.h"
#include "EmuleNextSchedulerTelemetry.h"
#include <array>
#include <map>
#include <mutex>

class CDownloadQueue;
class CPartFile;

struct EmuleNextSchedulerSnapshot
{
    EmuleNextSchedulingDecision decision;
    uint64 evaluatedAt;
    uint64 lastInterventionAt;

    EmuleNextSchedulerSnapshot();
};

class CEmuleNextSmartScheduler
{
public:
    CEmuleNextSmartScheduler();

    void Tick(CDownloadQueue* queue);
    uint16 AdjustPartRank(const CPartFile* file, UINT part, UINT frequency, uint16 legacyRank) const;
    bool GetSnapshot(const unsigned char* fileHash, EmuleNextSchedulerSnapshot& snapshot) const;

    CEmuleNextSchedulerTelemetry& Telemetry();
    const CEmuleNextSchedulerTelemetry& Telemetry() const;
    CEmuleNextHistoryCache& History();
    const CEmuleNextHistoryCache& History() const;

private:
    typedef std::array<unsigned char, 16> Key;

    static bool MakeKey(const unsigned char* hash, Key& key);
    EmuleNextSchedulingSettings LoadSettings() const;
    void EvaluateFile(CDownloadQueue* queue, CPartFile* file, const EmuleNextSchedulingSettings& settings, uint64 now);

    mutable std::mutex m_mutex;
    std::map<Key, EmuleNextSchedulerSnapshot> m_snapshots;
    size_t m_roundRobinOffset;
    DWORD m_lastTick;
    CEmuleNextSchedulerTelemetry m_telemetry;
    CEmuleNextHistoryCache m_history;
};

extern CEmuleNextSmartScheduler theEmuleNextScheduler;
