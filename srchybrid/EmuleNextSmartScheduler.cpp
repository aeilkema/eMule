//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "EmuleNextSmartScheduler.h"
#include "EmuleNextTransferInsights.h"
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
    int mode = theApp.GetProfileInt(_T("eMule Next"), _T("SmartSchedulingMode"), ENSM_ANALYSIS_ONLY);
    if (mode < ENSM_ANALYSIS_ONLY) mode = ENSM_ANALYSIS_ONLY;
    if (mode > ENSM_AUTOMATIC) mode = ENSM_AUTOMATIC;
    settings.mode = static_cast<EmuleNextSchedulingMode>(mode);
    settings.sourceDiscovery = theApp.GetProfileInt(_T("eMule Next"), _T("SmartSourceDiscovery"), 1) != 0;
    settings.a4af = theApp.GetProfileInt(_T("eMule Next"), _T("SmartA4AF"), 1) != 0;
    settings.rareParts = theApp.GetProfileInt(_T("eMule Next"), _T("SmartRareParts"), 1) != 0;
    settings.etaHealthDisplay = theApp.GetProfileInt(_T("eMule Next"), _T("SmartEtaHealthDisplay"), 1) != 0;

    const int profile = theApp.GetProfileInt(_T("eMule Next"), _T("SmartSchedulerProfile"), 1);
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

    const int configuredCooldown = theApp.GetProfileInt(_T("eMule Next"), _T("SmartSchedulerCooldown"), 0);
    if (configuredCooldown > 0)
        settings.interventionCooldownSeconds = static_cast<uint32>(std::max(30, std::min(1800, configuredCooldown)));
    return settings;
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
    const size_t total = static_cast<size_t>(queue->GetFileCount());
    if (total == 0)
        return;

    const size_t maxPerRound = 8;
    const size_t count = std::min(maxPerRound, total);
    const size_t start = m_roundRobinOffset % total;
    POSITION pos = NULL;
    for (size_t skip = 0; skip < start; ++skip)
        queue->GetFileNext(pos);

    const uint64 now = static_cast<uint64>(time(NULL));
    for (size_t processed = 0; processed < count; ++processed) {
        CPartFile* file = queue->GetFileNext(pos);
        if (file != NULL)
            EvaluateFile(queue, file, settings, now);
    }
    m_roundRobinOffset = (start + count) % total;
}

void CEmuleNextSmartScheduler::EvaluateFile(CDownloadQueue* queue, CPartFile* file,
    const EmuleNextSchedulingSettings& settings, uint64 now)
{
    if (file == NULL || file->GetStatus() == PS_COMPLETE)
        return;

    m_history.Observe(file);
    const double historical = m_history.HistoricalBytesPerSecond(file->GetFileHash());
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
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_snapshots[key] = snapshot;
        if (m_snapshots.size() > 4096)
            m_snapshots.erase(m_snapshots.begin());
    }

    EmuleNextSchedulerEvent event;
    event.timestamp = now;
    event.fileName = file->GetFileName();
    event.mode = settings.mode;
    event.action = decision.primaryAction;
    event.health = decision.health;
    event.attention = decision.attention;
    event.discoveryBudget = decision.discoveryBudget;
    event.reason = decision.reason;
    m_telemetry.Record(event);
}

uint16 CEmuleNextSmartScheduler::AdjustPartRank(const CPartFile* file, UINT part, UINT frequency, uint16 legacyRank) const
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
    return static_cast<uint16>(legacyRank > bonus ? legacyRank - bonus : 0);
}

bool CEmuleNextSmartScheduler::PreferA4AFCandidate(const CPartFile* currentFile, const CPartFile* candidateFile, bool legacyPreference) const
{
    if (candidateFile == NULL)
        return legacyPreference;
    if (theApp.GetProfileInt(_T("eMule Next"), _T("SmartSchedulingMode"), ENSM_ANALYSIS_ONLY) != ENSM_AUTOMATIC
        || theApp.GetProfileInt(_T("eMule Next"), _T("SmartA4AF"), 1) == 0)
        return legacyPreference;

    EmuleNextSchedulerSnapshot candidate;
    if (!GetSnapshot(candidateFile->GetFileHash(), candidate))
        return legacyPreference;

    const uint32 minimumScore = static_cast<uint32>(std::max(0,
        theApp.GetProfileInt(_T("eMule Next"), _T("SmartA4AFMinimumScore"), 650)));
    if (candidate.decision.a4afScore < minimumScore)
        return legacyPreference;

    EmuleNextSchedulerSnapshot current;
    const bool hasCurrent = currentFile != NULL && GetSnapshot(currentFile->GetFileHash(), current);
    const uint32 currentScore = hasCurrent ? current.decision.a4afScore : 0;
    const uint32 currentAttention = hasCurrent ? current.decision.attention : 0;

    if (candidate.decision.a4afScore >= currentScore + 80
        && candidate.decision.attention >= currentAttention)
        return true;
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

CEmuleNextSchedulerTelemetry& CEmuleNextSmartScheduler::Telemetry() { return m_telemetry; }
const CEmuleNextSchedulerTelemetry& CEmuleNextSmartScheduler::Telemetry() const { return m_telemetry; }
CEmuleNextHistoryCache& CEmuleNextSmartScheduler::History() { return m_history; }
const CEmuleNextHistoryCache& CEmuleNextSmartScheduler::History() const { return m_history; }
