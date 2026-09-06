//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "EmuleNextSmartScheduler.h"
#include "EmuleNextTransferInsights.h"
#include "EmuleNextRuntime.h"
#include "UpDownClient.h"
#include "DownloadQueue.h"
#include "PartFile.h"
#include "emule.h"

#include <algorithm>
#include <set>

#ifdef min
#undef min
#endif
#ifdef max
#undef max
#endif

CEmuleNextSmartScheduler theEmuleNextScheduler;

EmuleNextInterventionOutcome::EmuleNextInterventionOutcome()
    : action(ENSA_NONE)
    , startedAt(0)
    , baselineBytesPerSecond(0.0)
    , baselineUsableSources(0)
    , measured30(false)
    , bytesPerSecond30(0.0)
    , usableSources30(0)
    , measured120(false)
    , bytesPerSecond120(0.0)
    , usableSources120(0)
{
}

EmuleNextSchedulerSnapshot::EmuleNextSchedulerSnapshot()
    : evaluatedAt(0)
    , lastInterventionAt(0)
    , lastDiscoveryAt(0)
    , lastA4AFAt(0)
    , lastRarePartAt(0)
    , lastUsefulSourceAt(0)
    , applied(false)
{
}

EmuleNextSchedulerRuntimeStatus::EmuleNextSchedulerRuntimeStatus()
    : mode(ENSM_ANALYSIS_ONLY)
    , profile(1)
    , cooldownSeconds(90)
    , maxFilesPerRound(8)
    , minimumA4AFScore(650)
    , sourceDiscovery(true)
    , a4af(true)
    , rareParts(true)
    , historyEnabled(true)
    , historyPersistenceReady(false)
    , telemetryEnabled(true)
    , telemetryPersistenceReady(false)
    , trackedFiles(0)
    , trackedOutcomes(0)
    , historyFiles(0)
    , historyGeneration(0)
    , historyPendingWrites(0)
    , historyDroppedWrites(0)
    , decisions(0)
    , appliedInterventions(0)
    , telemetryPendingWrites(0)
    , telemetryDroppedWrites(0)
{
}

CEmuleNextSmartScheduler::CEmuleNextSmartScheduler()
    : m_roundRobinOffset(0)
    , m_lastTick(0)
    , m_lastPruneTick(0)
{
}

bool CEmuleNextSmartScheduler::MakeKey(const unsigned char* hash, Key& key)
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

EmuleNextSchedulingSettings CEmuleNextSmartScheduler::LoadSettings() const
{
    EmuleNextSchedulingSettings settings;
    int mode = static_cast<int>(theApp.GetProfileInt(_T("eMule Next"), _T("SmartSchedulingMode"), ENSM_ANALYSIS_ONLY));
    if (mode < ENSM_ANALYSIS_ONLY) mode = ENSM_ANALYSIS_ONLY;
    if (mode > ENSM_AUTOMATIC) mode = ENSM_AUTOMATIC;
    settings.mode = static_cast<EmuleNextSchedulingMode>(mode);
    settings.sourceDiscovery = theApp.GetProfileInt(_T("eMule Next"), _T("SmartSourceDiscovery"), 1) != 0;
    settings.a4af = theApp.GetProfileInt(_T("eMule Next"), _T("SmartA4AF"), 1) != 0;
    settings.rareParts = theApp.GetProfileInt(_T("eMule Next"), _T("SmartRareParts"), 1) != 0;
    settings.etaHealthDisplay = theApp.GetProfileInt(_T("eMule Next"), _T("SmartEtaHealthDisplay"), 1) != 0;

    const int profile = static_cast<int>(theApp.GetProfileInt(_T("eMule Next"), _T("SmartSchedulerProfile"), 1));
    if (profile <= 0) {
        settings.normalDiscoveryBudget = 8;
        settings.maxDiscoveryBudget = 24;
        settings.minimumA4AFScore = 720;
        settings.minimumSourceQuality = 520;
        settings.interventionCooldownSeconds = 180;
    } else if (profile >= 2) {
        settings.normalDiscoveryBudget = 12;
        settings.maxDiscoveryBudget = 48;
        settings.minimumA4AFScore = 590;
        settings.minimumSourceQuality = 400;
        settings.interventionCooldownSeconds = 45;
    } else {
        settings.normalDiscoveryBudget = 10;
        settings.maxDiscoveryBudget = 36;
        settings.minimumA4AFScore = 650;
        settings.minimumSourceQuality = 450;
        settings.interventionCooldownSeconds = 90;
    }

    const UINT configuredCooldown = theApp.GetProfileInt(_T("eMule Next"), _T("SmartSchedulerCooldown"), 0);
    if (configuredCooldown > 0)
        settings.interventionCooldownSeconds = static_cast<uint32>(std::max<UINT>(30u, std::min<UINT>(1800u, configuredCooldown)));
    const UINT configuredA4AF = theApp.GetProfileInt(_T("eMule Next"), _T("SmartA4AFMinimumScore"), 0);
    if (configuredA4AF > 0)
        settings.minimumA4AFScore = static_cast<uint32>(std::max<UINT>(100u, std::min<UINT>(1000u, configuredA4AF)));
    return settings;
}

uint32 CEmuleNextSmartScheduler::LoadMaxFilesPerRound() const
{
    const UINT configured = theApp.GetProfileInt(_T("eMule Next"), _T("SmartSchedulerMaxFilesPerRound"), 8);
    return static_cast<uint32>(std::max<UINT>(1u, std::min<UINT>(32u, configured)));
}

CString CEmuleNextSmartScheduler::ProfileText(int profile)
{
    if (profile <= 0) return _T("Conservative");
    if (profile >= 2) return _T("Responsive");
    return _T("Balanced");
}

void CEmuleNextSmartScheduler::Tick(CDownloadQueue* queue)
{
    if (queue == NULL)
        return;
    const DWORD tick = ::GetTickCount();
    if (m_lastTick != 0 && tick - m_lastTick < 2000)
        return;
    m_lastTick = tick;

    const EmuleNextSchedulingSettings settings = LoadSettings();
    const bool historyEnabled = theApp.GetProfileInt(_T("eMule Next"), _T("SmartHistoryCache"), 1) != 0;
    const bool telemetryEnabled = theApp.GetProfileInt(_T("eMule Next"), _T("SmartTelemetry"), 1) != 0;
    const UINT telemetryCapacity = theApp.GetProfileInt(_T("eMule Next"), _T("SmartTelemetryCapacity"), 256);
    m_telemetry.SetCapacity(static_cast<size_t>(std::max<UINT>(16u, std::min<UINT>(4096u, telemetryCapacity))));

    CEmuleNextDatabase& database = theEmuleNextRuntime.Database();
    if (telemetryEnabled && database.IsRunning())
        m_telemetry.SetDatabasePath(database.GetDatabasePath());

    if (historyEnabled) {
        const UINT historyCapacity = theApp.GetProfileInt(_T("eMule Next"), _T("SmartHistoryCacheCapacity"), 4096);
        m_history.SetCapacity(static_cast<size_t>(std::max<UINT>(128u, std::min<UINT>(16384u, historyCapacity))));
        if (database.IsRunning())
            m_history.SetDatabasePath(database.GetDatabasePath());
    }

    const uint64 now = static_cast<uint64>(time(NULL));
    if (m_lastPruneTick == 0 || tick - m_lastPruneTick >= 30000) {
        PruneSnapshots(queue, now);
        m_lastPruneTick = tick;
    }

    const size_t total = static_cast<size_t>(queue->GetFileCount());
    if (total == 0)
        return;

    const size_t maxPerRound = static_cast<size_t>(LoadMaxFilesPerRound());
    const size_t count = std::min(maxPerRound, total);
    const size_t start = m_roundRobinOffset % total;
    POSITION pos = NULL;
    for (size_t skip = 0; skip < start; ++skip)
        queue->GetFileNext(pos);

    for (size_t processed = 0; processed < count; ++processed) {
        CPartFile* file = queue->GetFileNext(pos);
        if (file != NULL)
            EvaluateFile(queue, file, settings, now, historyEnabled, telemetryEnabled);
    }
    m_roundRobinOffset = (start + count) % total;
}

bool CEmuleNextSmartScheduler::ForceAnalyze(CDownloadQueue* queue, CPartFile* file)
{
    if (queue == NULL || file == NULL || file->GetStatus() == PS_COMPLETE)
        return false;
    EmuleNextSchedulingSettings settings = LoadSettings();
    settings.mode = ENSM_ANALYSIS_ONLY;
    const bool historyEnabled = theApp.GetProfileInt(_T("eMule Next"), _T("SmartHistoryCache"), 1) != 0;
    const bool telemetryEnabled = theApp.GetProfileInt(_T("eMule Next"), _T("SmartTelemetry"), 1) != 0;
    EvaluateFile(queue, file, settings, static_cast<uint64>(time(NULL)), historyEnabled, telemetryEnabled);
    return true;
}

void CEmuleNextSmartScheduler::ResetFileIntelligence(const unsigned char* fileHash, bool clearHistory)
{
    Key key;
    if (!MakeKey(fileHash, key))
        return;
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_snapshots.erase(key);
        m_outcomes.erase(key);
    }
    if (clearHistory)
        m_history.Remove(fileHash);
}

void CEmuleNextSmartScheduler::ResetAllSessionIntelligence(bool clearHistory)
{
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_snapshots.clear();
        m_outcomes.clear();
        m_roundRobinOffset = 0;
    }
    m_telemetry.Clear();
    if (clearHistory)
        m_history.Clear();
}

void CEmuleNextSmartScheduler::EvaluateFile(CDownloadQueue* queue, CPartFile* file,
    const EmuleNextSchedulingSettings& settings, uint64 now, bool historyEnabled, bool telemetryEnabled)
{
    if (file == NULL || file->GetStatus() == PS_COMPLETE)
        return;

    double historical = 0.0;
    if (historyEnabled) {
        m_history.Observe(file);
        historical = m_history.HistoricalBytesPerSecond(file->GetFileHash());
    }
    const EmuleNextTransferInsight insight = CEmuleNextTransferInsights::Build(file, historical);
    UpdateOutcome(file, insight, now);
    const EmuleNextSchedulingDecision decision = CDownloadIntelligence::EvaluateScheduling(
        insight.file, insight.parts, insight.bestSourceQuality, settings);

    Key key;
    if (!MakeKey(file->GetFileHash(), key))
        return;

    EmuleNextSchedulerSnapshot previous;
    bool hasPrevious = false;
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        const std::map<Key, EmuleNextSchedulerSnapshot>::const_iterator existing = m_snapshots.find(key);
        if (existing != m_snapshots.end()) {
            previous = existing->second;
            hasPrevious = true;
        }
    }

    const uint64 previousDiscovery = hasPrevious ? previous.lastDiscoveryAt : 0;
    const uint32 sinceDiscovery = previousDiscovery == 0 || now <= previousDiscovery
        ? 0xFFFFFFFFu : static_cast<uint32>(std::min<uint64>(0xFFFFFFFFui64, now - previousDiscovery));
    bool intervened = false;
    if (settings.mode == ENSM_AUTOMATIC
        && settings.sourceDiscovery
        && decision.discoveryChanged
        && decision.discoveryBudget > settings.normalDiscoveryBudget
        && insight.file.usableSources <= 3
        && CDownloadIntelligence::ShouldApplyDecision(decision, settings, sinceDiscovery)) {
        queue->SendLocalSrcRequest(file);
        intervened = true;
        BeginOutcome(file, ENSA_DISCOVERY_BOOST, now);
    }

    EmuleNextSchedulerSnapshot snapshot;
    snapshot.decision = decision;
    snapshot.evaluatedAt = now;
    if (hasPrevious) {
        snapshot.lastInterventionAt = previous.lastInterventionAt;
        snapshot.lastDiscoveryAt = previous.lastDiscoveryAt;
        snapshot.lastA4AFAt = previous.lastA4AFAt;
        snapshot.lastRarePartAt = previous.lastRarePartAt;
        snapshot.lastUsefulSourceAt = previous.lastUsefulSourceAt;
    }
    if (insight.file.usableSources > 0 && (insight.bestSourceQuality > 0 || insight.file.currentBytesPerSecond > 0.0))
        snapshot.lastUsefulSourceAt = now;
    if (intervened) {
        snapshot.lastInterventionAt = now;
        snapshot.lastDiscoveryAt = now;
    }
    snapshot.applied = intervened;
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_snapshots[key] = snapshot;
        if (m_snapshots.size() > 4096)
            m_snapshots.erase(m_snapshots.begin());
    }

    if (telemetryEnabled) {
        EmuleNextSchedulerEvent event;
        event.timestamp = now;
        event.fileName = file->GetFileName();
        event.fileHash = key;
        event.fileHashValid = true;
        event.mode = settings.mode;
        event.action = decision.primaryAction;
        event.health = decision.health;
        event.attention = decision.attention;
        event.discoveryBudget = decision.discoveryBudget;
        event.a4afScore = decision.a4afScore;
        event.rarePartIndex = decision.rarePartIndex;
        event.applied = intervened;
        event.reason = decision.reason;
        m_telemetry.Record(event);
    }
}

void CEmuleNextSmartScheduler::BeginOutcome(const CPartFile* file, EmuleNextSchedulingAction action, uint64 now)
{
    if (file == NULL)
        return;
    Key key;
    if (!MakeKey(file->GetFileHash(), key))
        return;
    EmuleNextInterventionOutcome outcome;
    outcome.action = action;
    outcome.startedAt = now;
    outcome.baselineBytesPerSecond = static_cast<double>(file->GetDatarate());
    const int valid = file->GetValidSourcesCount();
    outcome.baselineUsableSources = valid > 0 ? static_cast<uint32>(valid) : 0;
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_outcomes[key] = outcome;
    }
    m_telemetry.RecordOutcomeBaseline(file->GetFileHash(), file->GetFileName(), action,
        now, outcome.baselineBytesPerSecond, outcome.baselineUsableSources);
}

void CEmuleNextSmartScheduler::UpdateOutcome(const CPartFile* file, const EmuleNextTransferInsight& insight, uint64 now)
{
    if (file == NULL)
        return;
    Key key;
    if (!MakeKey(file->GetFileHash(), key))
        return;

    bool write30 = false;
    bool write120 = false;
    EmuleNextSchedulingAction action = ENSA_NONE;
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        std::map<Key, EmuleNextInterventionOutcome>::iterator it = m_outcomes.find(key);
        if (it == m_outcomes.end() || it->second.startedAt == 0 || now < it->second.startedAt)
            return;
        const uint64 elapsed = now - it->second.startedAt;
        action = it->second.action;
        if (!it->second.measured30 && elapsed >= 30) {
            it->second.measured30 = true;
            it->second.bytesPerSecond30 = insight.file.currentBytesPerSecond;
            it->second.usableSources30 = insight.file.usableSources;
            write30 = true;
        }
        if (!it->second.measured120 && elapsed >= 120) {
            it->second.measured120 = true;
            it->second.bytesPerSecond120 = insight.file.currentBytesPerSecond;
            it->second.usableSources120 = insight.file.usableSources;
            write120 = true;
        }
    }

    if (write30)
        m_telemetry.RecordOutcomeSample(file->GetFileHash(), file->GetFileName(), action,
            now, 30, insight.file.currentBytesPerSecond, insight.file.usableSources);
    if (write120)
        m_telemetry.RecordOutcomeSample(file->GetFileHash(), file->GetFileName(), action,
            now, 120, insight.file.currentBytesPerSecond, insight.file.usableSources);
}

void CEmuleNextSmartScheduler::MarkApplied(const CPartFile* file, EmuleNextSchedulingAction action)
{
    if (file == NULL)
        return;
    Key key;
    if (!MakeKey(file->GetFileHash(), key))
        return;
    const uint64 now = static_cast<uint64>(time(NULL));
    bool changed = false;
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        std::map<Key, EmuleNextSchedulerSnapshot>::iterator it = m_snapshots.find(key);
        if (it != m_snapshots.end()) {
            if (!it->second.applied)
                changed = true;
            it->second.applied = true;
            it->second.lastInterventionAt = now;
            if (action == ENSA_A4AF_PREFER)
                it->second.lastA4AFAt = now;
            else if (action == ENSA_RARE_PART_PROTECT)
                it->second.lastRarePartAt = now;
            else if (action == ENSA_DISCOVERY_BOOST)
                it->second.lastDiscoveryAt = now;
        }
    }
    if (changed) {
        BeginOutcome(file, action, now);
        if (theApp.GetProfileInt(_T("eMule Next"), _T("SmartTelemetry"), 1) != 0)
            m_telemetry.MarkAppliedIntervention(file->GetFileHash(), file->GetFileName());
    }
}

uint16 CEmuleNextSmartScheduler::AdjustPartRank(const CPartFile* file, UINT part, UINT frequency, uint16 legacyRank)
{
    if (file == NULL)
        return legacyRank;
    if (theApp.GetProfileInt(_T("eMule Next"), _T("SmartSchedulingMode"), ENSM_ANALYSIS_ONLY) != ENSM_AUTOMATIC
        || theApp.GetProfileInt(_T("eMule Next"), _T("SmartRareParts"), 1) == 0)
        return legacyRank;

    EmuleNextSchedulerSnapshot snapshot;
    if (!GetSnapshot(file->GetFileHash(), snapshot)
        || snapshot.decision.rarePartIndex == static_cast<uint32>(-1))
        return legacyRank;

    const UINT preferred = snapshot.decision.rarePartIndex;
    if (part != preferred)
        return legacyRank;

    const uint32 bonus = frequency <= 1 ? 1600u : (frequency == 2 ? 900u : 350u);
    const uint16 adjusted = static_cast<uint16>(legacyRank > bonus ? legacyRank - bonus : 0);
    if (adjusted != legacyRank)
        MarkApplied(file, ENSA_RARE_PART_PROTECT);
    return adjusted;
}

bool CEmuleNextSmartScheduler::PreferA4AFCandidate(const CPartFile* currentFile, const CPartFile* candidateFile, bool legacyPreference)
{
    if (candidateFile == NULL)
        return legacyPreference;
    if (theApp.GetProfileInt(_T("eMule Next"), _T("SmartSchedulingMode"), ENSM_ANALYSIS_ONLY) != ENSM_AUTOMATIC
        || theApp.GetProfileInt(_T("eMule Next"), _T("SmartA4AF"), 1) == 0)
        return legacyPreference;

    EmuleNextSchedulerSnapshot candidate;
    if (!GetSnapshot(candidateFile->GetFileHash(), candidate))
        return legacyPreference;

    const UINT configuredMinimum = theApp.GetProfileInt(_T("eMule Next"), _T("SmartA4AFMinimumScore"), 650);
    const uint32 minimumScore = static_cast<uint32>(configuredMinimum > 1000u ? 1000u : configuredMinimum);
    if (candidate.decision.a4afScore < minimumScore)
        return legacyPreference;

    EmuleNextSchedulerSnapshot current;
    const bool hasCurrent = currentFile != NULL && GetSnapshot(currentFile->GetFileHash(), current);
    const uint32 currentScore = hasCurrent ? current.decision.a4afScore : 0;
    const uint32 currentAttention = hasCurrent ? current.decision.attention : 0;

    if (!legacyPreference
        && candidate.decision.a4afScore >= currentScore + 80
        && candidate.decision.attention >= currentAttention) {
        MarkApplied(candidateFile, ENSA_A4AF_PREFER);
        return true;
    }
    return legacyPreference;
}

void CEmuleNextSmartScheduler::PruneSnapshots(CDownloadQueue* queue, uint64 now)
{
    if (queue == NULL)
        return;
    std::set<Key> active;
    for (POSITION pos = NULL; ;) {
        CPartFile* file = queue->GetFileNext(pos);
        if (file != NULL && file->GetStatus() != PS_COMPLETE) {
            Key key;
            if (MakeKey(file->GetFileHash(), key))
                active.insert(key);
        }
        if (pos == NULL)
            break;
    }

    std::lock_guard<std::mutex> lock(m_mutex);
    for (std::map<Key, EmuleNextSchedulerSnapshot>::iterator it = m_snapshots.begin(); it != m_snapshots.end(); ) {
        const bool inactive = active.find(it->first) == active.end();
        const bool stale = it->second.evaluatedAt != 0 && now > it->second.evaluatedAt
            && now - it->second.evaluatedAt > 900;
        if (inactive || stale) {
            m_outcomes.erase(it->first);
            it = m_snapshots.erase(it);
        } else {
            ++it;
        }
    }
    for (std::map<Key, EmuleNextInterventionOutcome>::iterator it = m_outcomes.begin(); it != m_outcomes.end(); ) {
        if (active.find(it->first) == active.end())
            it = m_outcomes.erase(it);
        else
            ++it;
    }
}

bool CEmuleNextSmartScheduler::GetSnapshot(const unsigned char* fileHash, EmuleNextSchedulerSnapshot& snapshot) const
{
    Key key;
    if (!MakeKey(fileHash, key))
        return false;
    std::lock_guard<std::mutex> lock(m_mutex);
    const std::map<Key, EmuleNextSchedulerSnapshot>::const_iterator it = m_snapshots.find(key);
    if (it == m_snapshots.end())
        return false;
    snapshot = it->second;
    return true;
}

bool CEmuleNextSmartScheduler::GetOutcome(const unsigned char* fileHash, EmuleNextInterventionOutcome& outcome) const
{
    Key key;
    if (!MakeKey(fileHash, key))
        return false;
    std::lock_guard<std::mutex> lock(m_mutex);
    const std::map<Key, EmuleNextInterventionOutcome>::const_iterator it = m_outcomes.find(key);
    if (it == m_outcomes.end())
        return false;
    outcome = it->second;
    return true;
}

void CEmuleNextSmartScheduler::GetRuntimeStatus(EmuleNextSchedulerRuntimeStatus& status) const
{
    const EmuleNextSchedulingSettings settings = LoadSettings();
    status.mode = settings.mode;
    status.profile = static_cast<int>(theApp.GetProfileInt(_T("eMule Next"), _T("SmartSchedulerProfile"), 1));
    status.cooldownSeconds = settings.interventionCooldownSeconds;
    status.maxFilesPerRound = LoadMaxFilesPerRound();
    status.minimumA4AFScore = settings.minimumA4AFScore;
    status.sourceDiscovery = settings.sourceDiscovery;
    status.a4af = settings.a4af;
    status.rareParts = settings.rareParts;
    status.historyEnabled = theApp.GetProfileInt(_T("eMule Next"), _T("SmartHistoryCache"), 1) != 0;
    status.historyPersistenceReady = m_history.PersistenceReady();
    status.historyFiles = static_cast<uint32>(m_history.Size());
    status.historyGeneration = m_history.Generation();
    status.historyPendingWrites = m_history.PendingPersistenceWrites();
    status.historyDroppedWrites = m_history.DroppedPersistenceWrites();
    status.telemetryEnabled = theApp.GetProfileInt(_T("eMule Next"), _T("SmartTelemetry"), 1) != 0;
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        status.trackedFiles = static_cast<uint32>(m_snapshots.size());
        status.trackedOutcomes = static_cast<uint32>(m_outcomes.size());
    }
    EmuleNextSchedulerTelemetrySummary telemetry;
    m_telemetry.Summary(telemetry);
    status.decisions = telemetry.decisions;
    status.appliedInterventions = telemetry.appliedInterventions;
    status.telemetryPersistenceReady = telemetry.persistenceReady;
    status.telemetryPendingWrites = telemetry.pendingPersistenceEvents;
    status.telemetryDroppedWrites = telemetry.droppedPersistenceEvents;
}

CString CEmuleNextSmartScheduler::GetRuntimeStatusText() const
{
    EmuleNextSchedulerRuntimeStatus status;
    GetRuntimeStatus(status);
    CString text;
    text.Format(_T("%s / %s | scan %u | cooldown %us | tracked %u outcomes %u | history %u%s q:%u drop:%llu gen:%llu | telemetry %s q:%u drop:%llu | decisions %llu | applied %llu"),
        (LPCTSTR)CDownloadIntelligence::SchedulingModeText(status.mode),
        (LPCTSTR)ProfileText(status.profile), status.maxFilesPerRound, status.cooldownSeconds,
        status.trackedFiles, status.trackedOutcomes,
        status.historyFiles, status.historyPersistenceReady ? _T(" persistent") : _T(" memory"),
        static_cast<unsigned int>(status.historyPendingWrites), status.historyDroppedWrites, status.historyGeneration,
        status.telemetryPersistenceReady ? _T("persistent") : _T("memory"),
        static_cast<unsigned int>(status.telemetryPendingWrites), status.telemetryDroppedWrites,
        status.decisions, status.appliedInterventions);
    return text;
}

CEmuleNextSchedulerTelemetry& CEmuleNextSmartScheduler::Telemetry() { return m_telemetry; }
const CEmuleNextSchedulerTelemetry& CEmuleNextSmartScheduler::Telemetry() const { return m_telemetry; }
CEmuleNextHistoryCache& CEmuleNextSmartScheduler::History() { return m_history; }
const CEmuleNextHistoryCache& CEmuleNextSmartScheduler::History() const { return m_history; }
