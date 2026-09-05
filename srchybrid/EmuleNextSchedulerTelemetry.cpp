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
    , a4afScore(0)
    , rarePartIndex(static_cast<uint32>(-1))
    , applied(false)
{
}

EmuleNextSchedulerTelemetrySummary::EmuleNextSchedulerTelemetrySummary()
    : decisions(0)
    , appliedInterventions(0)
    , discoveryBoosts(0)
    , a4afPreferences(0)
    , rarePartPreferences(0)
    , holds(0)
    , retainedEvents(0)
{
}

CEmuleNextSchedulerTelemetry::CEmuleNextSchedulerTelemetry()
    : m_capacity(256)
    , m_decisions(0)
    , m_interventions(0)
    , m_discoveryBoosts(0)
    , m_a4afPreferences(0)
    , m_rarePartPreferences(0)
    , m_holds(0)
{
}

void CEmuleNextSchedulerTelemetry::SetCapacity(size_t capacity)
{
    std::lock_guard<std::mutex> lock(m_mutex);
    m_capacity = capacity < 16 ? 16 : (capacity > 4096 ? 4096 : capacity);
    while (m_events.size() > m_capacity)
        m_events.pop_front();
}

void CEmuleNextSchedulerTelemetry::Record(const EmuleNextSchedulerEvent& event)
{
    std::lock_guard<std::mutex> lock(m_mutex);
    ++m_decisions;
    if (event.applied)
        ++m_interventions;
    switch (event.action) {
    case ENSA_DISCOVERY_BOOST: ++m_discoveryBoosts; break;
    case ENSA_A4AF_PREFER: ++m_a4afPreferences; break;
    case ENSA_RARE_PART_PROTECT: ++m_rarePartPreferences; break;
    case ENSA_HOLD_STEADY: ++m_holds; break;
    default: break;
    }
    m_events.push_back(event);
    while (m_events.size() > m_capacity)
        m_events.pop_front();
}

void CEmuleNextSchedulerTelemetry::MarkAppliedIntervention()
{
    std::lock_guard<std::mutex> lock(m_mutex);
    ++m_interventions;
}

void CEmuleNextSchedulerTelemetry::Snapshot(std::deque<EmuleNextSchedulerEvent>& events) const
{
    std::lock_guard<std::mutex> lock(m_mutex);
    events = m_events;
}

void CEmuleNextSchedulerTelemetry::Summary(EmuleNextSchedulerTelemetrySummary& summary) const
{
    std::lock_guard<std::mutex> lock(m_mutex);
    summary.decisions = m_decisions;
    summary.appliedInterventions = m_interventions;
    summary.discoveryBoosts = m_discoveryBoosts;
    summary.a4afPreferences = m_a4afPreferences;
    summary.rarePartPreferences = m_rarePartPreferences;
    summary.holds = m_holds;
    summary.retainedEvents = m_events.size();
}

void CEmuleNextSchedulerTelemetry::Clear()
{
    std::lock_guard<std::mutex> lock(m_mutex);
    m_events.clear();
    m_decisions = 0;
    m_interventions = 0;
    m_discoveryBoosts = 0;
    m_a4afPreferences = 0;
    m_rarePartPreferences = 0;
    m_holds = 0;
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
