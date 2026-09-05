//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "DownloadIntelligence.h"
#include <deque>
#include <mutex>

struct EmuleNextSchedulerEvent
{
    uint64 timestamp;
    CString fileName;
    EmuleNextSchedulingMode mode;
    EmuleNextSchedulingAction action;
    uint32 health;
    uint32 attention;
    uint32 discoveryBudget;
    CString reason;

    EmuleNextSchedulerEvent();
};

class CEmuleNextSchedulerTelemetry
{
public:
    CEmuleNextSchedulerTelemetry();

    void SetCapacity(size_t capacity);
    void Record(const EmuleNextSchedulerEvent& event);
    void Snapshot(std::deque<EmuleNextSchedulerEvent>& events) const;
    uint64 InterventionCount() const;
    uint64 DecisionCount() const;

private:
    mutable std::mutex m_mutex;
    std::deque<EmuleNextSchedulerEvent> m_events;
    size_t m_capacity;
    uint64 m_decisions;
    uint64 m_interventions;
};
