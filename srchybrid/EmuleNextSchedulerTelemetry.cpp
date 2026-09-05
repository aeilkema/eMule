//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "EmuleNextSchedulerTelemetry.h"

EmuleNextSchedulerEvent::EmuleNextSchedulerEvent()
    : timestamp(static_cast<uint64>(time(NULL)))
    , mode(ENSM_ANALYSIS_ONLY)
    , action(ENSA_NONE)
    , health(0)
    , attention(0)
    , discoveryBudget(0)
{
}

CEmuleNextSchedulerTelemetry::CEmuleNextSchedulerTelemetry()
    : m_capacity(256)
    , m_decisions(0)
    , m_interventions(0)
{
}

void CEmuleNextSchedulerTelemetry::SetCapacity(size_t capacity)
{
    std::lock_guard<std::mutex> lock(m_mutex);
    m_capacity = capacity < 16 ? 16 : capacity;
    while (m_events.size() > m_capacity)
        m_events.pop_front();
}

void CEmuleNextSchedulerTelemetry::Record(const EmuleNextSchedulerEvent& event)
{
    std::lock_guard<std::mutex> lock(m_mutex);
    ++m_decisions;
    if (event.mode == ENSM_AUTOMATIC && event.action != ENSA_NONE && event.action != ENSA_HOLD_STEADY)
        ++m_interventions;
    m_events.push_back(event);
    while (m_events.size() > m_capacity)
        m_events.pop_front();
}

void CEmuleNextSchedulerTelemetry::Snapshot(std::deque<EmuleNextSchedulerEvent>& events) const
{
    std::lock_guard<std::mutex> lock(m_mutex);
    events = m_events;
}

uint64 CEmuleNextSchedulerTelemetry::InterventionCount() const
{
    std::lock_guard<std::mutex> lock(m_mutex);
    return m_interventions;
}

uint64 CEmuleNextSchedulerTelemetry::DecisionCount() const
{
    std::lock_guard<std::mutex> lock(m_mutex);
    return m_decisions;
}
