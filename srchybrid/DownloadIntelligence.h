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
};
