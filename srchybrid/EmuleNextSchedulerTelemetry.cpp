//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "EmuleNextSchedulerTelemetry.h"

#include <winsqlite3.h>
#include <chrono>

namespace
{
    size_t PendingCount(const std::deque<EmuleNextSchedulerEvent>& events,
        const std::deque<EmuleNextSchedulerOutcomeRecord>& outcomes, size_t applied)
    {
        return events.size() + outcomes.size() + applied;
    }
}

EmuleNextSchedulerEvent::EmuleNextSchedulerEvent()
    : timestamp(static_cast<uint64>(time(NULL)))
    , fileHashValid(false)
    , mode(ENSM_ANALYSIS_ONLY)
    , action(ENSA_NONE)
    , health(0)
    , attention(0)
    , discoveryBudget(0)
    , a4afScore(0)
    , rarePartIndex(static_cast<uint32>(-1))
    , applied(false)
{
    fileHash.fill(0);
}

EmuleNextSchedulerOutcomeRecord::EmuleNextSchedulerOutcomeRecord()
    : timestamp(static_cast<uint64>(time(NULL)))
    , fileHashValid(false)
    , action(ENSA_NONE)
    , windowSeconds(0)
    , bytesPerSecond(0.0)
    , usableSources(0)
{
    fileHash.fill(0);
}

CEmuleNextSchedulerTelemetry::AppliedPersistItem::AppliedPersistItem()
    : fileHashValid(false)
{
    fileHash.fill(0);
}

EmuleNextSchedulerTelemetrySummary::EmuleNextSchedulerTelemetrySummary()
    : decisions(0)
    , appliedInterventions(0)
    , discoveryBoosts(0)
    , a4afPreferences(0)
    , rarePartPreferences(0)
    , holds(0)
    , droppedPersistenceEvents(0)
    , retainedEvents(0)
    , pendingPersistenceEvents(0)
    , persistenceReady(false)
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
    , m_persistenceStarting(false)
    , m_lastPersistenceAttempt(0)
    , m_droppedPersistEvents(0)
{
}

CEmuleNextSchedulerTelemetry::~CEmuleNextSchedulerTelemetry()
{
    StopPersistence();
}

bool CEmuleNextSchedulerTelemetry::CopyHash(const unsigned char* source,
    std::array<unsigned char, 16>& destination)
{
    destination.fill(0);
    if (source == NULL)
        return false;
    unsigned char aggregate = 0;
    for (size_t i = 0; i < destination.size(); ++i) {
        destination[i] = source[i];
        aggregate |= source[i];
    }
    return aggregate != 0;
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
    const uint64 now = static_cast<uint64>(time(NULL));
    {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        if (databasePath == m_databasePath && m_persistThread.joinable()
            && (m_persistenceReady || m_persistenceStarting))
            return;
        if (!databasePath.IsEmpty() && databasePath == m_lastAttemptPath
            && !m_persistenceReady && !m_persistenceStarting
            && m_lastPersistenceAttempt != 0 && now >= m_lastPersistenceAttempt
            && now - m_lastPersistenceAttempt < 30)
            return;
    }

    StopPersistence();
    if (databasePath.IsEmpty())
        return;

    {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        m_databasePath = databasePath;
        m_lastAttemptPath = databasePath;
        m_lastPersistenceAttempt = now;
        m_stopPersistence = false;
        m_persistenceReady = false;
        m_persistenceStarting = true;
    }
    try {
        m_persistThread = std::thread(&CEmuleNextSchedulerTelemetry::PersistenceMain, this);
    }
    catch (...) {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        m_persistenceReady = false;
        m_persistenceStarting = false;
    }
}

bool CEmuleNextSchedulerTelemetry::PersistenceReady() const
{
    std::lock_guard<std::mutex> lock(m_persistMutex);
    return m_persistenceReady;
}

size_t CEmuleNextSchedulerTelemetry::PendingPersistenceEvents() const
{
    std::lock_guard<std::mutex> lock(m_persistMutex);
    return PendingCount(m_persistQueue, m_persistOutcomeQueue, m_persistAppliedQueue.size());
}

uint64 CEmuleNextSchedulerTelemetry::DroppedPersistenceEvents() const
{
    std::lock_guard<std::mutex> lock(m_persistMutex);
    return m_droppedPersistEvents;
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
        m_persistOutcomeQueue.clear();
        m_persistAppliedQueue.clear();
        m_databasePath.Empty();
        m_persistenceReady = false;
        m_persistenceStarting = false;
        m_stopPersistence = false;
    }
}

void CEmuleNextSchedulerTelemetry::QueuePersist(const EmuleNextSchedulerEvent& event)
{
    std::lock_guard<std::mutex> lock(m_persistMutex);
    if (!m_persistThread.joinable() || (!m_persistenceReady && !m_persistenceStarting)) {
        ++m_droppedPersistEvents;
        return;
    }
    if (PendingCount(m_persistQueue, m_persistOutcomeQueue, m_persistAppliedQueue.size()) >= 8192) {
        if (!m_persistQueue.empty()) m_persistQueue.pop_front();
        else if (!m_persistOutcomeQueue.empty()) m_persistOutcomeQueue.pop_front();
        else if (!m_persistAppliedQueue.empty()) m_persistAppliedQueue.pop_front();
        ++m_droppedPersistEvents;
    }
    m_persistQueue.push_back(event);
    m_persistCondition.notify_one();
}

void CEmuleNextSchedulerTelemetry::QueueOutcomePersist(const EmuleNextSchedulerOutcomeRecord& outcome)
{
    std::lock_guard<std::mutex> lock(m_persistMutex);
    if (!m_persistThread.joinable() || (!m_persistenceReady && !m_persistenceStarting)) {
        ++m_droppedPersistEvents;
        return;
    }
    if (PendingCount(m_persistQueue, m_persistOutcomeQueue, m_persistAppliedQueue.size()) >= 8192) {
        if (!m_persistQueue.empty()) m_persistQueue.pop_front();
        else if (!m_persistOutcomeQueue.empty()) m_persistOutcomeQueue.pop_front();
        else if (!m_persistAppliedQueue.empty()) m_persistAppliedQueue.pop_front();
        ++m_droppedPersistEvents;
    }
    m_persistOutcomeQueue.push_back(outcome);
    m_persistCondition.notify_one();
}

void CEmuleNextSchedulerTelemetry::QueueAppliedPersist(const unsigned char* fileHash, const CString& fileName)
{
    AppliedPersistItem item;
    item.fileHashValid = CopyHash(fileHash, item.fileHash);
    item.fileName = fileName;
    if (!item.fileHashValid && item.fileName.IsEmpty())
        return;

    std::lock_guard<std::mutex> lock(m_persistMutex);
    if (!m_persistThread.joinable() || (!m_persistenceReady && !m_persistenceStarting)) {
        ++m_droppedPersistEvents;
        return;
    }
    if (PendingCount(m_persistQueue, m_persistOutcomeQueue, m_persistAppliedQueue.size()) >= 8192) {
        if (!m_persistQueue.empty()) m_persistQueue.pop_front();
        else if (!m_persistOutcomeQueue.empty()) m_persistOutcomeQueue.pop_front();
        else if (!m_persistAppliedQueue.empty()) m_persistAppliedQueue.pop_front();
        ++m_droppedPersistEvents;
    }
    m_persistAppliedQueue.push_back(item);
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
    QueuePersist(event);
}

void CEmuleNextSchedulerTelemetry::RecordOutcomeBaseline(const unsigned char* fileHash, const CString& fileName,
    EmuleNextSchedulingAction action, uint64 timestamp, double bytesPerSecond, uint32 usableSources)
{
    EmuleNextSchedulerOutcomeRecord outcome;
    outcome.timestamp = timestamp;
    outcome.fileHashValid = CopyHash(fileHash, outcome.fileHash);
    outcome.fileName = fileName;
    outcome.action = action;
    outcome.windowSeconds = 0;
    outcome.bytesPerSecond = bytesPerSecond;
    outcome.usableSources = usableSources;
    QueueOutcomePersist(outcome);
}

void CEmuleNextSchedulerTelemetry::RecordOutcomeSample(const unsigned char* fileHash, const CString& fileName,
    EmuleNextSchedulingAction action, uint64 timestamp, uint32 windowSeconds,
    double bytesPerSecond, uint32 usableSources)
{
    EmuleNextSchedulerOutcomeRecord outcome;
    outcome.timestamp = timestamp;
    outcome.fileHashValid = CopyHash(fileHash, outcome.fileHash);
    outcome.fileName = fileName;
    outcome.action = action;
    outcome.windowSeconds = windowSeconds;
    outcome.bytesPerSecond = bytesPerSecond;
    outcome.usableSources = usableSources;
    QueueOutcomePersist(outcome);
}

void CEmuleNextSchedulerTelemetry::MarkAppliedIntervention(const unsigned char* fileHash, const CString& fileName)
{
    std::array<unsigned char, 16> key;
    const bool keyValid = CopyHash(fileHash, key);
    bool changed = false;
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        for (std::deque<EmuleNextSchedulerEvent>::reverse_iterator it = m_events.rbegin(); it != m_events.rend(); ++it) {
            const bool sameHash = keyValid && it->fileHashValid && it->fileHash == key;
            const bool legacyNameFallback = (!keyValid || !it->fileHashValid)
                && !fileName.IsEmpty() && it->fileName.CompareNoCase(fileName) == 0;
            if (!it->applied && (sameHash || legacyNameFallback)) {
                it->applied = true;
                changed = true;
                break;
            }
        }
        if (changed)
            ++m_interventions;
    }
    if (changed)
        QueueAppliedPersist(fileHash, fileName);
}

void CEmuleNextSchedulerTelemetry::Snapshot(std::deque<EmuleNextSchedulerEvent>& events) const
{
    std::lock_guard<std::mutex> lock(m_mutex);
    events = m_events;
}

void CEmuleNextSchedulerTelemetry::Summary(EmuleNextSchedulerTelemetrySummary& summary) const
{
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
    {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        summary.droppedPersistenceEvents = m_droppedPersistEvents;
        summary.pendingPersistenceEvents = PendingCount(m_persistQueue, m_persistOutcomeQueue, m_persistAppliedQueue.size());
        summary.persistenceReady = m_persistenceReady;
    }
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
            "id INTEGER PRIMARY KEY AUTOINCREMENT,ts INTEGER NOT NULL,file_name TEXT NOT NULL,file_hash BLOB,"
            "mode INTEGER NOT NULL,action INTEGER NOT NULL,health INTEGER NOT NULL,attention INTEGER NOT NULL,"
            "discovery_budget INTEGER NOT NULL,a4af_score INTEGER NOT NULL,rare_part_index INTEGER,"
            "applied INTEGER NOT NULL,reason TEXT);"
            "CREATE TABLE IF NOT EXISTS scheduler_outcomes("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,ts INTEGER NOT NULL,file_name TEXT NOT NULL,file_hash BLOB,"
            "action INTEGER NOT NULL,window_seconds INTEGER NOT NULL,bytes_per_second REAL NOT NULL,usable_sources INTEGER NOT NULL);";
        ready = sqlite3_exec(db, schema, NULL, NULL, NULL) == SQLITE_OK;
        if (ready) {
            sqlite3_exec(db, "ALTER TABLE scheduler_decisions ADD COLUMN file_hash BLOB", NULL, NULL, NULL);
            const char* indexes =
                "CREATE INDEX IF NOT EXISTS idx_scheduler_decisions_ts ON scheduler_decisions(ts DESC);"
                "CREATE INDEX IF NOT EXISTS idx_scheduler_decisions_file_applied ON scheduler_decisions(file_name,applied,id DESC);"
                "CREATE INDEX IF NOT EXISTS idx_scheduler_decisions_hash_applied ON scheduler_decisions(file_hash,applied,id DESC);"
                "CREATE INDEX IF NOT EXISTS idx_scheduler_outcomes_hash_ts ON scheduler_outcomes(file_hash,ts DESC);";
            ready = sqlite3_exec(db, indexes, NULL, NULL, NULL) == SQLITE_OK;
        }
    }

    {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        m_persistenceReady = ready;
        m_persistenceStarting = false;
    }

    uint32 pruneCounter = 0;
    while (ready) {
        std::deque<EmuleNextSchedulerEvent> batch;
        std::deque<EmuleNextSchedulerOutcomeRecord> outcomeBatch;
        std::deque<AppliedPersistItem> appliedBatch;
        {
            std::unique_lock<std::mutex> lock(m_persistMutex);
            m_persistCondition.wait_for(lock, std::chrono::milliseconds(500), [this]() {
                return m_stopPersistence || !m_persistQueue.empty()
                    || !m_persistOutcomeQueue.empty() || !m_persistAppliedQueue.empty();
            });
            size_t count = m_persistQueue.size() > 256 ? 256 : m_persistQueue.size();
            for (size_t i = 0; i < count; ++i) { batch.push_back(m_persistQueue.front()); m_persistQueue.pop_front(); }
            count = m_persistOutcomeQueue.size() > 256 ? 256 : m_persistOutcomeQueue.size();
            for (size_t i = 0; i < count; ++i) { outcomeBatch.push_back(m_persistOutcomeQueue.front()); m_persistOutcomeQueue.pop_front(); }
            count = m_persistAppliedQueue.size() > 256 ? 256 : m_persistAppliedQueue.size();
            for (size_t i = 0; i < count; ++i) { appliedBatch.push_back(m_persistAppliedQueue.front()); m_persistAppliedQueue.pop_front(); }
            if (m_stopPersistence && batch.empty() && outcomeBatch.empty() && appliedBatch.empty()
                && m_persistQueue.empty() && m_persistOutcomeQueue.empty() && m_persistAppliedQueue.empty())
                break;
        }
        if (batch.empty() && outcomeBatch.empty() && appliedBatch.empty())
            continue;

        if (sqlite3_exec(db, "BEGIN IMMEDIATE", NULL, NULL, NULL) != SQLITE_OK) {
            std::lock_guard<std::mutex> lock(m_persistMutex);
            m_droppedPersistEvents += static_cast<uint64>(batch.size() + outcomeBatch.size() + appliedBatch.size());
            continue;
        }

        bool batchOk = true;
        sqlite3_stmt* stmt = NULL;
        const char* insertSql =
            "INSERT INTO scheduler_decisions(ts,file_name,file_hash,mode,action,health,attention,discovery_budget,a4af_score,rare_part_index,applied,reason) "
            "VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12)";
        if (!batch.empty() && sqlite3_prepare_v2(db, insertSql, -1, &stmt, NULL) != SQLITE_OK)
            batchOk = false;
        if (batchOk && stmt != NULL) {
            for (std::deque<EmuleNextSchedulerEvent>::const_iterator it = batch.begin(); it != batch.end(); ++it) {
                sqlite3_reset(stmt); sqlite3_clear_bindings(stmt);
                sqlite3_bind_int64(stmt, 1, static_cast<sqlite3_int64>(it->timestamp));
                sqlite3_bind_text16(stmt, 2, it->fileName.GetString(), -1, SQLITE_TRANSIENT);
                if (it->fileHashValid) sqlite3_bind_blob(stmt, 3, it->fileHash.data(), 16, SQLITE_TRANSIENT); else sqlite3_bind_null(stmt, 3);
                sqlite3_bind_int(stmt, 4, static_cast<int>(it->mode));
                sqlite3_bind_int(stmt, 5, static_cast<int>(it->action));
                sqlite3_bind_int64(stmt, 6, static_cast<sqlite3_int64>(it->health));
                sqlite3_bind_int64(stmt, 7, static_cast<sqlite3_int64>(it->attention));
                sqlite3_bind_int64(stmt, 8, static_cast<sqlite3_int64>(it->discoveryBudget));
                sqlite3_bind_int64(stmt, 9, static_cast<sqlite3_int64>(it->a4afScore));
                if (it->rarePartIndex == static_cast<uint32>(-1)) sqlite3_bind_null(stmt, 10); else sqlite3_bind_int64(stmt, 10, it->rarePartIndex);
                sqlite3_bind_int(stmt, 11, it->applied ? 1 : 0);
                sqlite3_bind_text16(stmt, 12, it->reason.GetString(), -1, SQLITE_TRANSIENT);
                if (sqlite3_step(stmt) != SQLITE_DONE) { batchOk = false; break; }
            }
        }
        if (stmt != NULL) { sqlite3_finalize(stmt); stmt = NULL; }

        const char* outcomeSql =
            "INSERT INTO scheduler_outcomes(ts,file_name,file_hash,action,window_seconds,bytes_per_second,usable_sources) "
            "VALUES(?1,?2,?3,?4,?5,?6,?7)";
        if (batchOk && !outcomeBatch.empty() && sqlite3_prepare_v2(db, outcomeSql, -1, &stmt, NULL) != SQLITE_OK)
            batchOk = false;
        if (batchOk && stmt != NULL) {
            for (std::deque<EmuleNextSchedulerOutcomeRecord>::const_iterator it = outcomeBatch.begin(); it != outcomeBatch.end(); ++it) {
                sqlite3_reset(stmt); sqlite3_clear_bindings(stmt);
                sqlite3_bind_int64(stmt, 1, static_cast<sqlite3_int64>(it->timestamp));
                sqlite3_bind_text16(stmt, 2, it->fileName.GetString(), -1, SQLITE_TRANSIENT);
                if (it->fileHashValid) sqlite3_bind_blob(stmt, 3, it->fileHash.data(), 16, SQLITE_TRANSIENT); else sqlite3_bind_null(stmt, 3);
                sqlite3_bind_int(stmt, 4, static_cast<int>(it->action));
                sqlite3_bind_int64(stmt, 5, static_cast<sqlite3_int64>(it->windowSeconds));
                sqlite3_bind_double(stmt, 6, it->bytesPerSecond);
                sqlite3_bind_int64(stmt, 7, static_cast<sqlite3_int64>(it->usableSources));
                if (sqlite3_step(stmt) != SQLITE_DONE) { batchOk = false; break; }
            }
        }
        if (stmt != NULL) { sqlite3_finalize(stmt); stmt = NULL; }

        if (batchOk && !appliedBatch.empty()) {
            const char* updateSql =
                "UPDATE scheduler_decisions SET applied=1 WHERE id=(SELECT id FROM scheduler_decisions "
                "WHERE applied=0 AND ((?1 IS NOT NULL AND file_hash=?1) OR (?1 IS NULL AND file_name=?2 COLLATE NOCASE)) ORDER BY id DESC LIMIT 1)";
            if (sqlite3_prepare_v2(db, updateSql, -1, &stmt, NULL) != SQLITE_OK)
                batchOk = false;
            if (batchOk) {
                for (std::deque<AppliedPersistItem>::const_iterator it = appliedBatch.begin(); it != appliedBatch.end(); ++it) {
                    sqlite3_reset(stmt); sqlite3_clear_bindings(stmt);
                    if (it->fileHashValid) sqlite3_bind_blob(stmt, 1, it->fileHash.data(), 16, SQLITE_TRANSIENT); else sqlite3_bind_null(stmt, 1);
                    sqlite3_bind_text16(stmt, 2, it->fileName.GetString(), -1, SQLITE_TRANSIENT);
                    if (sqlite3_step(stmt) != SQLITE_DONE) { batchOk = false; break; }
                }
            }
        }
        if (stmt != NULL) sqlite3_finalize(stmt);

        if (batchOk) {
            if (sqlite3_exec(db, "COMMIT", NULL, NULL, NULL) != SQLITE_OK)
                batchOk = false;
        } else {
            sqlite3_exec(db, "ROLLBACK", NULL, NULL, NULL);
        }
        if (!batchOk) {
            sqlite3_exec(db, "ROLLBACK", NULL, NULL, NULL);
            std::lock_guard<std::mutex> lock(m_persistMutex);
            m_droppedPersistEvents += static_cast<uint64>(batch.size() + outcomeBatch.size() + appliedBatch.size());
        }

        if (++pruneCounter >= 64) {
            pruneCounter = 0;
            sqlite3_exec(db,
                "DELETE FROM scheduler_decisions WHERE id NOT IN (SELECT id FROM scheduler_decisions ORDER BY id DESC LIMIT 10000);"
                "DELETE FROM scheduler_outcomes WHERE id NOT IN (SELECT id FROM scheduler_outcomes ORDER BY id DESC LIMIT 20000);",
                NULL, NULL, NULL);
        }
    }

    if (db != NULL)
        sqlite3_close(db);
    {
        std::lock_guard<std::mutex> lock(m_persistMutex);
        m_persistenceReady = false;
        m_persistenceStarting = false;
    }
}