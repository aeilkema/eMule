//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "EmuleNextSchedulerTelemetry.h"

#include <winsqlite3.h>
#include <chrono>

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
    , m_stopPersistence(false)
    , m_persistenceReady(false)
{
}

CEmuleNextSchedulerTelemetry::~CEmuleNextSchedulerTelemetry()
{
    StopPersistence();
}

void CEmuleNextSchedulerTelemetry::SetCapacity(size_t capacity)
{
    std::lock_guard<std::mutex> lock(m_mutex);
    m_capacity = capacity < 16 ? 16 : (capacity > 4096 ? 4096 : capacity);
    while (m_events.size() > m_capacity)
        m_events.pop_front();
}

void CEmuleNextSchedulerTelemetry::SetDatabasePath(const CStringW& databasePath)
{
    {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        if (databasePath == m_databasePath && m_persistThread.joinable())
            return;
    }

    StopPersistence();
    if (databasePath.IsEmpty())
        return;

    {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        m_databasePath = databasePath;
        m_stopPersistence = false;
        m_persistenceReady = false;
    }
    try {
        m_persistThread = std::thread(&CEmuleNextSchedulerTelemetry::PersistenceMain, this);
    }
    catch (...) {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        m_persistenceReady = false;
    }
}

bool CEmuleNextSchedulerTelemetry::PersistenceReady() const
{
    std::lock_guard<std::mutex> lock(m_persistMutex);
    return m_persistenceReady;
}

void CEmuleNextSchedulerTelemetry::StopPersistence()
{
    {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        m_stopPersistence = true;
    }
    m_persistCondition.notify_all();
    if (m_persistThread.joinable())
        m_persistThread.join();
    {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        m_persistQueue.clear();
        m_databasePath.Empty();
        m_persistenceReady = false;
        m_stopPersistence = false;
    }
}

void CEmuleNextSchedulerTelemetry::QueuePersist(const EmuleNextSchedulerEvent& event)
{
    std::lock_guard<std::mutex> lock(m_persistMutex);
    if (!m_persistThread.joinable())
        return;
    if (m_persistQueue.size() >= 8192)
        m_persistQueue.pop_front();
    m_persistQueue.push_back(event);
    m_persistCondition.notify_one();
}

void CEmuleNextSchedulerTelemetry::Record(const EmuleNextSchedulerEvent& event)
{
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

    // Scheduler/core code only enqueues a copy. SQLite stays on the worker.
    QueuePersist(event);
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

void CEmuleNextSchedulerTelemetry::PersistenceMain()
{
    CStringW path;
    {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        path = m_databasePath;
    }

    sqlite3* db = NULL;
    bool ready = sqlite3_open16(path.GetString(), &db) == SQLITE_OK;
    if (ready) {
        sqlite3_busy_timeout(db, 3000);
        const char* schema =
            "CREATE TABLE IF NOT EXISTS scheduler_decisions("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,ts INTEGER NOT NULL,file_name TEXT NOT NULL,"
            "mode INTEGER NOT NULL,action INTEGER NOT NULL,health INTEGER NOT NULL,attention INTEGER NOT NULL,"
            "discovery_budget INTEGER NOT NULL,a4af_score INTEGER NOT NULL,rare_part_index INTEGER,"
            "applied INTEGER NOT NULL,reason TEXT);"
            "CREATE INDEX IF NOT EXISTS idx_scheduler_decisions_ts ON scheduler_decisions(ts DESC);";
        ready = sqlite3_exec(db, schema, NULL, NULL, NULL) == SQLITE_OK;
    }

    {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        m_persistenceReady = ready;
    }

    uint32 pruneCounter = 0;
    while (ready) {
        std::deque<EmuleNextSchedulerEvent> batch;
        {
            std::unique_lock<std::mutex> lock(m_persistMutex);
            m_persistCondition.wait_for(lock, std::chrono::milliseconds(500), [this]() {
                return m_stopPersistence || !m_persistQueue.empty();
            });
            size_t count = m_persistQueue.size();
            if (count > 256)
                count = 256;
            for (size_t i = 0; i < count; ++i) {
                batch.push_back(m_persistQueue.front());
                m_persistQueue.pop_front();
            }
            if (m_stopPersistence && batch.empty() && m_persistQueue.empty())
                break;
        }
        if (batch.empty())
            continue;

        sqlite3_exec(db, "BEGIN IMMEDIATE", NULL, NULL, NULL);
        sqlite3_stmt* stmt = NULL;
        const char* sql =
            "INSERT INTO scheduler_decisions(ts,file_name,mode,action,health,attention,discovery_budget,a4af_score,rare_part_index,applied,reason) "
            "VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11)";
        if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK) {
            for (std::deque<EmuleNextSchedulerEvent>::const_iterator it = batch.begin(); it != batch.end(); ++it) {
                sqlite3_reset(stmt);
                sqlite3_clear_bindings(stmt);
                sqlite3_bind_int64(stmt, 1, static_cast<sqlite3_int64>(it->timestamp));
                sqlite3_bind_text16(stmt, 2, it->fileName.GetString(), -1, SQLITE_TRANSIENT);
                sqlite3_bind_int(stmt, 3, static_cast<int>(it->mode));
                sqlite3_bind_int(stmt, 4, static_cast<int>(it->action));
                sqlite3_bind_int64(stmt, 5, static_cast<sqlite3_int64>(it->health));
                sqlite3_bind_int64(stmt, 6, static_cast<sqlite3_int64>(it->attention));
                sqlite3_bind_int64(stmt, 7, static_cast<sqlite3_int64>(it->discoveryBudget));
                sqlite3_bind_int64(stmt, 8, static_cast<sqlite3_int64>(it->a4afScore));
                if (it->rarePartIndex == static_cast<uint32>(-1))
                    sqlite3_bind_null(stmt, 9);
                else
                    sqlite3_bind_int64(stmt, 9, static_cast<sqlite3_int64>(it->rarePartIndex));
                sqlite3_bind_int(stmt, 10, it->applied ? 1 : 0);
                sqlite3_bind_text16(stmt, 11, it->reason.GetString(), -1, SQLITE_TRANSIENT);
                sqlite3_step(stmt);
            }
        }
        if (stmt != NULL)
            sqlite3_finalize(stmt);
        sqlite3_exec(db, "COMMIT", NULL, NULL, NULL);

        if (++pruneCounter >= 20) {
            sqlite3_exec(db,
                "DELETE FROM scheduler_decisions WHERE id < (SELECT COALESCE(MAX(id),0)-10000 FROM scheduler_decisions)",
                NULL, NULL, NULL);
            pruneCounter = 0;
        }
    }

    if (db != NULL)
        sqlite3_close(db);
    {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        m_persistenceReady = false;
    }
}
