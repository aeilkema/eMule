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

struct EmuleNextInterventionOutcome
{
    EmuleNextSchedulingAction action;
    uint64 startedAt;
    double baselineBytesPerSecond;
    uint32 baselineUsableSources;
    bool measured30;
    double bytesPerSecond30;
    uint32 usableSources30;
    bool measured120;
    double bytesPerSecond120;
    uint32 usableSources120;

    EmuleNextInterventionOutcome();
};

struct EmuleNextSchedulerSnapshot
{
    EmuleNextSchedulingDecision decision;
    uint64 evaluatedAt;
    uint64 lastInterventionAt;
    uint64 lastDiscoveryAt;
    uint64 lastA4AFAt;
    uint64 lastRarePartAt;
    uint64 lastUsefulSourceAt;
    bool applied;

    EmuleNextSchedulerSnapshot();
};

struct EmuleNextSchedulerRuntimeStatus
{
    EmuleNextSchedulingMode mode;
    int profile;
    uint32 cooldownSeconds;
    uint32 maxFilesPerRound;
    uint32 minimumA4AFScore;
    bool sourceDiscovery;
    bool a4af;
    bool rareParts;
    bool historyEnabled;
    bool historyPersistenceReady;
    bool telemetryEnabled;
    bool telemetryPersistenceReady;
    uint32 trackedFiles;
    uint32 trackedOutcomes;
    uint32 historyFiles;
    uint64 historyGeneration;
    size_t historyPendingWrites;
    uint64 historyDroppedWrites;
    uint64 decisions;
    uint64 appliedInterventions;
    size_t telemetryPendingWrites;
    uint64 telemetryDroppedWrites;

    EmuleNextSchedulerRuntimeStatus();
};

class CEmuleNextSmartScheduler
{
public:
    CEmuleNextSmartScheduler();

    void Tick(CDownloadQueue* queue);
    bool ForceAnalyze(CDownloadQueue* queue, CPartFile* file);
    void ResetFileIntelligence(const unsigned char* fileHash, bool clearHistory = true);
    void ResetAllSessionIntelligence(bool clearHistory = false);
    uint16 AdjustPartRank(const CPartFile* file, UINT part, UINT frequency, uint16 legacyRank);
    bool PreferA4AFCandidate(const CPartFile* currentFile, const CPartFile* candidateFile, bool legacyPreference);
    bool GetSnapshot(const unsigned char* fileHash, EmuleNextSchedulerSnapshot& snapshot) const;
    bool GetOutcome(const unsigned char* fileHash, EmuleNextInterventionOutcome& outcome) const;
    void GetRuntimeStatus(EmuleNextSchedulerRuntimeStatus& status) const;
    CString GetRuntimeStatusText() const;
    static CString ProfileText(int profile);

    CEmuleNextSchedulerTelemetry& Telemetry();
    const CEmuleNextSchedulerTelemetry& Telemetry() const;
    CEmuleNextHistoryCache& History();
    const CEmuleNextHistoryCache& History() const;

private:
    typedef std::array<unsigned char, 16> Key;

    static bool MakeKey(const unsigned char* hash, Key& key);
    EmuleNextSchedulingSettings LoadSettings() const;
    uint32 LoadMaxFilesPerRound() const;
    void EvaluateFile(CDownloadQueue* queue, CPartFile* file, const EmuleNextSchedulingSettings& settings, uint64 now,
        bool historyEnabled, bool telemetryEnabled);
    void MarkApplied(const CPartFile* file, EmuleNextSchedulingAction action);
    void BeginOutcome(const CPartFile* file, EmuleNextSchedulingAction action, uint64 now);
    void UpdateOutcome(const CPartFile* file, const EmuleNextTransferInsight& insight, uint64 now);
    void PruneSnapshots(CDownloadQueue* queue, uint64 now);

    mutable std::mutex m_mutex;
    std::map<Key, EmuleNextSchedulerSnapshot> m_snapshots;
    std::map<Key, EmuleNextInterventionOutcome> m_outcomes;
    size_t m_roundRobinOffset;
    DWORD m_lastTick;
    DWORD m_lastPruneTick;
    CEmuleNextSchedulerTelemetry m_telemetry;
    CEmuleNextHistoryCache m_history;
};

extern CEmuleNextSmartScheduler theEmuleNextScheduler;
