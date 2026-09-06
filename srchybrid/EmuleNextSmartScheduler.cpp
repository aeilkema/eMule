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

#ifdef min
#undef min
#endif
#ifdef max
#undef max
#endif

CEmuleNextSmartScheduler theEmuleNextScheduler;

EmuleNextSchedulerSnapshot::EmuleNextSchedulerSnapshot()
    : evaluatedAt(0)
    , lastInterventionAt(0)
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

    const size_t total = static_cast<size_t>(queue->GetFileCount());
    if (total == 0)
        return;

    const size_t maxPerRound = static_cast<size_t>(LoadMaxFilesPerRound());
    const size_t count = std::min(maxPerRound, total);
    const size_t start = m_roundRobinOffset % total;
    POSITION pos = NULL;
    for (size_t skip = 0; skip < start; ++skip)
        queue->GetFileNext(pos);

    const uint64 now = static_cast<uint64>(time(NULL));
    for (size_t processed = 0; processed < count; ++processed) {
        CPartFile* file = queue->GetFileNext(pos);
        if (file != NULL)
            EvaluateFile(queue, file, settings, now, historyEnabled, telemetryEnabled);
    }
    m_roundRobinOffset = (start + count) % total;
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
    const EmuleNextSchedulingDecision decision = CDownloadIntelligence::EvaluateScheduling(
        insight.file, insight.parts, insight.bestSourceQuality, settings);

    Key key;
    if (!MakeKey(file->GetFileHash(), key))
        return;

    uint64 previousIntervention = 0;
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        const std::map<Key, EmuleNextSchedulerSnapshot>::const_iterator existing = m_snapshots.find(key);
        if (existing != m_snapshots.end())
            previousIntervention = existing->second.lastInterventionAt;
    }

    const uint32 since = previousIntervention == 0 || now <= previousIntervention
        ? 0xFFFFFFFFu : static_cast<uint32>(std::min<uint64>(0xFFFFFFFFui64, now - previousIntervention));
    bool intervened = false;
    if (settings.mode == ENSM_AUTOMATIC
        && settings.sourceDiscovery
        && decision.discoveryChanged
        && decision.discoveryBudget > settings.normalDiscoveryBudget
        && insight.file.usableSources <= 3
        && CDownloadIntelligence::ShouldApplyDecision(decision, settings, since)) {
        queue->SendLocalSrcRequest(file);
        intervened = true;
    }

    EmuleNextSchedulerSnapshot snapshot;
    snapshot.decision = decision;
    snapshot.evaluatedAt = now;
    snapshot.lastInterventionAt = intervened ? now : previousIntervention;
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

void CEmuleNextSmartScheduler::MarkApplied(const unsigned char* fileHash, const CString& fileName)
{
    Key key;
    if (!MakeKey(fileHash, key))
        return;
    bool changed = false;
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        std::map<Key, EmuleNextSchedulerSnapshot>::iterator it = m_snapshots.find(key);
        if (it != m_snapshots.end() && !it->second.applied) {
            it->second.applied = true;
            it->second.lastInterventionAt = static_cast<uint64>(time(NULL));
            changed = true;
        }
    }
    if (changed && theApp.GetProfileInt(_T("eMule Next"), _T("SmartTelemetry"), 1) != 0)
        m_telemetry.MarkAppliedIntervention(fileHash, fileName);
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
        MarkApplied(file->GetFileHash(), file->GetFileName());
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
        MarkApplied(candidateFile->GetFileHash(), candidateFile->GetFileName());
        return true;
    }
    return legacyPreference;
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
    text.Format(_T("%s / %s | scan %u | cooldown %us | tracked %u | history %u%s q:%u drop:%llu gen:%llu | telemetry %s q:%u drop:%llu | decisions %llu | applied %llu"),
        (LPCTSTR)CDownloadIntelligence::SchedulingModeText(status.mode),
        (LPCTSTR)ProfileText(status.profile), status.maxFilesPerRound, status.cooldownSeconds,
        status.trackedFiles, status.historyFiles, status.historyPersistenceReady ? _T(" persistent") : _T(" memory"),
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