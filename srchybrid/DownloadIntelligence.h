//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include <vector>

enum EmuleNextStallReason
{
    ENSR_NONE = 0,
    ENSR_NO_SOURCES,
    ENSR_NO_NEEDED_PARTS,
    ENSR_ALL_REMOTE_QUEUED,
    ENSR_RARE_PARTS,
    ENSR_CONNECTION_FAILURE,
    ENSR_KAD_DISCOVERY_FAILURE,
    ENSR_DISK_LIMITED,
    ENSR_HASHING,
    ENSR_A4AF_CONFLICT
};

enum EmuleNextSchedulingMode
{
    ENSM_ANALYSIS_ONLY = 0,
    ENSM_ASSIST = 1,
    ENSM_AUTOMATIC = 2
};

enum EmuleNextSchedulingAction
{
    ENSA_NONE = 0,
    ENSA_DISCOVERY_BOOST,
    ENSA_DISCOVERY_REDUCE,
    ENSA_A4AF_PREFER,
    ENSA_RARE_PART_PROTECT,
    ENSA_HOLD_STEADY
};

struct EmuleNextSourceSignals
{
    double currentBytesPerSecond;
    double historicalEwmaBytesPerSecond;
    uint32 successfulSessions;
    uint32 failedSessions;
    uint32 recentTimeouts;
    uint32 usefulPartCount;
    uint32 remoteQueueRank;
    uint32 secondsSinceLastSuccess;
    uint32 corruptionEvents;
    bool connected;
    bool currentlyTransferring;
    bool secureIdentified;

    EmuleNextSourceSignals();
};

struct EmuleNextPartSignals
{
    uint32 independentSources;
    uint32 reliableSources;
    double bestSourceQuality;
    double completionImpact;
    bool requestedNow;

    EmuleNextPartSignals();
};

struct EmuleNextFileSignals
{
    uint32 totalSources;
    uint32 usableSources;
    uint32 queuedSources;
    uint32 neededParts;
    uint32 rareNeededParts;
    uint32 connectionFailures;
    uint32 kadResultsLastCycle;
    uint32 a4afCandidates;
    double completionRatio;
    double currentBytesPerSecond;
    double historicalBytesPerSecond;
    double diskPressure;
    bool hashing;
    bool favorite;
    bool highPriority;

    EmuleNextFileSignals();
};

struct EmuleNextEta
{
    bool known;
    uint64 seconds;
    uint8 confidencePercent;
    CString reason;

    EmuleNextEta();
};

struct EmuleNextSchedulingSettings
{
    EmuleNextSchedulingMode mode;
    bool sourceDiscovery;
    bool a4af;
    bool rareParts;
    bool etaHealthDisplay;
    uint32 normalDiscoveryBudget;
    uint32 maxDiscoveryBudget;
    uint32 minimumA4AFScore;
    uint32 minimumSourceQuality;
    uint32 interventionCooldownSeconds;

    EmuleNextSchedulingSettings();
};

struct EmuleNextSchedulingDecision
{
    EmuleNextSchedulingAction primaryAction;
    uint32 discoveryBudget;
    uint32 a4afScore;
    uint32 rarePartIndex;
    uint32 health;
    uint32 attention;
    bool mayIntervene;
    bool discoveryChanged;
    bool a4afPreferred;
    bool rarePartPreferred;
    CString reason;

    EmuleNextSchedulingDecision();
};

class CDownloadIntelligence
{
public:
    // Scores use 0..1000. The model is deliberately deterministic so debug
    // builds and tests can compare scheduler decisions exactly.
    static uint32 SourceQuality(const EmuleNextSourceSignals& source);
    static uint32 PartRisk(const EmuleNextPartSignals& part);
    static uint32 FileAvailabilityHealth(const EmuleNextFileSignals& file);
    static uint32 SourceDiscoveryBudget(const EmuleNextFileSignals& file, uint32 normalBudget);
    static uint32 A4AFPriority(const EmuleNextFileSignals& file, uint32 sourceQuality);
    static EmuleNextStallReason DiagnoseStall(const EmuleNextFileSignals& file);
    static EmuleNextEta EstimateEta(const EmuleNextFileSignals& file, uint64 bytesRemaining);
    static uint32 ChooseRarestRiskPart(const std::vector<EmuleNextPartSignals>& parts);

    // Smart Scheduling policy layer. This intentionally returns a decision and
    // never mutates legacy networking state itself. Call sites remain explicit,
    // auditable and individually feature-gated.
    static uint32 AttentionScore(const EmuleNextFileSignals& file);
    static EmuleNextSchedulingDecision EvaluateScheduling(
        const EmuleNextFileSignals& file,
        const std::vector<EmuleNextPartSignals>& parts,
        uint32 bestSourceQuality,
        const EmuleNextSchedulingSettings& settings);
    static bool ShouldApplyDecision(
        const EmuleNextSchedulingDecision& decision,
        const EmuleNextSchedulingSettings& settings,
        uint32 secondsSinceLastIntervention);
    static CString SchedulingModeText(EmuleNextSchedulingMode mode);
    static CString SchedulingActionText(EmuleNextSchedulingAction action);
};
