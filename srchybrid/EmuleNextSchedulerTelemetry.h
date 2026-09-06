//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "DownloadIntelligence.h"
#include <condition_variable>
#include <deque>
#include <mutex>
#include <thread>

struct EmuleNextSchedulerEvent
{
    uint64 timestamp;
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

struct EmuleNextSchedulerTelemetrySummary
{
    uint64 decisions;
    uint64 appliedInterventions;
    uint64 discoveryBoosts;
    uint64 a4afPreferences;
    uint64 rarePartPreferences;
    uint64 holds;
    size_t retainedEvents;

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
    void Record(const EmuleNextSchedulerEvent& event);
    void MarkAppliedIntervention();
    void Snapshot(std::deque<EmuleNextSchedulerEvent>& events) const;
    void Summary(EmuleNextSchedulerTelemetrySummary& summary) const;
    void Clear();
    uint64 InterventionCount() const;
    uint64 DecisionCount() const;

private:
    void QueuePersist(const EmuleNextSchedulerEvent& event);
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
    std::thread m_persistThread;
    CStringW m_databasePath;
    bool m_stopPersistence;
    bool m_persistenceReady;
};
