//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "DownloadIntelligence.h"
#include <array>
#include <condition_variable>
#include <deque>
#include <mutex>
#include <thread>
#include <vector>

struct EmuleNextSchedulerEvent
{
    uint64 timestamp;
    std::array<unsigned char, 16> fileHash;
    bool fileHashValid;
    CString fileName;
    EmuleNextSchedulingMode mode;
    EmuleNextSchedulingAction action;
    uint32 health;
    uint32 attention;
    uint32 discoveryBudget;
    uint32 a4afScore;
    uint32 rarePartIndex;
    bool applied;
    CString reason;

    EmuleNextSchedulerEvent();
};

struct EmuleNextSchedulerOutcomeRecord
{
    uint64 timestamp;
    std::array<unsigned char, 16> fileHash;
    bool fileHashValid;
    CString fileName;
    EmuleNextSchedulingAction action;
    uint32 windowSeconds;
    double bytesPerSecond;
    uint32 usableSources;

    EmuleNextSchedulerOutcomeRecord();
};

struct EmuleNextSchedulerTelemetrySummary
{
    uint64 decisions;
    uint64 appliedInterventions;
    uint64 discoveryBoosts;
    uint64 a4afPreferences;
    uint64 rarePartPreferences;
    uint64 holds;
    uint64 droppedPersistenceEvents;
    size_t retainedEvents;
    size_t pendingPersistenceEvents;
    bool persistenceReady;

    EmuleNextSchedulerTelemetrySummary();
};

class CEmuleNextSchedulerTelemetry
{
public:
    CEmuleNextSchedulerTelemetry();
    ~CEmuleNextSchedulerTelemetry();

    void SetCapacity(size_t capacity);
    void SetDatabasePath(const CStringW& databasePath);
    bool PersistenceReady() const;
    size_t PendingPersistenceEvents() const;
    uint64 DroppedPersistenceEvents() const;
    void Record(const EmuleNextSchedulerEvent& event);
    void RecordOutcomeBaseline(const unsigned char* fileHash, const CString& fileName,
        EmuleNextSchedulingAction action, uint64 timestamp, double bytesPerSecond, uint32 usableSources);
    void RecordOutcomeSample(const unsigned char* fileHash, const CString& fileName,
        EmuleNextSchedulingAction action, uint64 timestamp, uint32 windowSeconds,
        double bytesPerSecond, uint32 usableSources);
    void MarkAppliedIntervention(const unsigned char* fileHash, const CString& fileName);
    void Snapshot(std::deque<EmuleNextSchedulerEvent>& events) const;
    void Summary(EmuleNextSchedulerTelemetrySummary& summary) const;
    void Clear();
    uint64 InterventionCount() const;
    uint64 DecisionCount() const;

private:
    struct AppliedPersistItem
    {
        std::array<unsigned char, 16> fileHash;
        bool fileHashValid;
        CString fileName;
        AppliedPersistItem();
    };

    static bool CopyHash(const unsigned char* source, std::array<unsigned char, 16>& destination);
    void QueuePersist(const EmuleNextSchedulerEvent& event);
    void QueueOutcomePersist(const EmuleNextSchedulerOutcomeRecord& outcome);
    void QueueAppliedPersist(const unsigned char* fileHash, const CString& fileName);
    void StopPersistence();
    void PersistenceMain();

    mutable std::mutex m_mutex;
    std::deque<EmuleNextSchedulerEvent> m_events;
    size_t m_capacity;
    uint64 m_decisions;
    uint64 m_interventions;
    uint64 m_discoveryBoosts;
    uint64 m_a4afPreferences;
    uint64 m_rarePartPreferences;
    uint64 m_holds;

    mutable std::mutex m_persistMutex;
    std::condition_variable m_persistCondition;
    std::deque<EmuleNextSchedulerEvent> m_persistQueue;
    std::deque<EmuleNextSchedulerOutcomeRecord> m_persistOutcomeQueue;
    std::deque<AppliedPersistItem> m_persistAppliedQueue;
    std::thread m_persistThread;
    CStringW m_databasePath;
    CStringW m_lastAttemptPath;
    bool m_stopPersistence;
    bool m_persistenceReady;
    bool m_persistenceStarting;
    uint64 m_lastPersistenceAttempt;
    uint64 m_droppedPersistEvents;
};