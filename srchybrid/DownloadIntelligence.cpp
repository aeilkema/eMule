//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "DownloadIntelligence.h"

#include <algorithm>
#include <cmath>

// Legacy Windows/MFC headers may define min/max as macros. They corrupt
// qualified std::min/std::max expressions in this translation unit.
#ifdef min
#undef min
#endif
#ifdef max
#undef max
#endif

namespace
{
    double Clamp01(double value)
    {
        if (value < 0.0)
            return 0.0;
        if (value > 1.0)
            return 1.0;
        return value;
    }

    uint32 Score1000(double value)
    {
        const double bounded = Clamp01(value);
        return static_cast<uint32>(bounded * 1000.0 + 0.5);
    }
}

EmuleNextSourceSignals::EmuleNextSourceSignals()
    : currentBytesPerSecond(0.0)
    , historicalEwmaBytesPerSecond(0.0)
    , successfulSessions(0)
    , failedSessions(0)
    , recentTimeouts(0)
    , usefulPartCount(0)
    , remoteQueueRank(0)
    , secondsSinceLastSuccess(0)
    , corruptionEvents(0)
    , connected(false)
    , currentlyTransferring(false)
    , secureIdentified(false)
{
}

EmuleNextPartSignals::EmuleNextPartSignals()
    : independentSources(0)
    , reliableSources(0)
    , bestSourceQuality(0.0)
    , completionImpact(0.0)
    , requestedNow(false)
{
}

EmuleNextFileSignals::EmuleNextFileSignals()
    : totalSources(0)
    , usableSources(0)
    , queuedSources(0)
    , neededParts(0)
    , rareNeededParts(0)
    , connectionFailures(0)
    , kadResultsLastCycle(0)
    , a4afCandidates(0)
    , completionRatio(0.0)
    , currentBytesPerSecond(0.0)
    , historicalBytesPerSecond(0.0)
    , diskPressure(0.0)
    , hashing(false)
    , favorite(false)
    , highPriority(false)
{
}

EmuleNextEta::EmuleNextEta()
    : known(false), seconds(0), confidencePercent(0)
{
}

uint32 CDownloadIntelligence::SourceQuality(const EmuleNextSourceSignals& source)
{
    // 1 MiB/s already earns most of the speed component; higher rates still
    // help but do not overwhelm reliability and part usefulness.
    const double currentSpeed = Clamp01(source.currentBytesPerSecond / (1024.0 * 1024.0));
    const double historicSpeed = Clamp01(source.historicalEwmaBytesPerSecond / (768.0 * 1024.0));
    const double totalSessions = static_cast<double>(source.successfulSessions + source.failedSessions);
    const double reliability = totalSessions > 0.0
        ? static_cast<double>(source.successfulSessions) / totalSessions
        : 0.50;
    const double usefulParts = Clamp01(static_cast<double>(source.usefulPartCount) / 8.0);
    const double freshness = 1.0 / (1.0 + static_cast<double>(source.secondsSinceLastSuccess) / 86400.0);
    const double queuePenalty = source.remoteQueueRank == 0
        ? 0.0
        : Clamp01(static_cast<double>(source.remoteQueueRank) / 5000.0);
    const double timeoutPenalty = Clamp01(static_cast<double>(source.recentTimeouts) / 5.0);
    const double corruptionPenalty = Clamp01(static_cast<double>(source.corruptionEvents) / 3.0);

    double score =
        0.18 * currentSpeed +
        0.14 * historicSpeed +
        0.25 * reliability +
        0.19 * usefulParts +
        0.10 * freshness +
        (source.connected ? 0.05 : 0.0) +
        (source.currentlyTransferring ? 0.07 : 0.0) +
        (source.secureIdentified ? 0.02 : 0.0) -
        0.04 * queuePenalty -
        0.08 * timeoutPenalty -
        0.12 * corruptionPenalty;

    return Score1000(score);
}

uint32 CDownloadIntelligence::PartRisk(const EmuleNextPartSignals& part)
{
    if (part.independentSources == 0)
        return 1000;

    const double scarcity = 1.0 / static_cast<double>(part.independentSources);
    const double reliableScarcity = part.reliableSources == 0
        ? 1.0
        : 1.0 / static_cast<double>(part.reliableSources);
    const double sourceFragility = 1.0 - Clamp01(part.bestSourceQuality / 1000.0);
    const double impact = Clamp01(part.completionImpact);

    double risk = 0.43 * scarcity + 0.30 * reliableScarcity + 0.17 * sourceFragility + 0.10 * impact;
    // Do not schedule the same block twice merely because endgame is urgent.
    if (part.requestedNow)
        risk *= 0.35;
    return Score1000(risk);
}

uint32 CDownloadIntelligence::FileAvailabilityHealth(const EmuleNextFileSignals& file)
{
    if (file.neededParts == 0)
        return 1000;
    if (file.usableSources == 0)
        return 0;

    const double sources = Clamp01(static_cast<double>(file.usableSources) / 20.0);
    const double coverage = 1.0 - Clamp01(static_cast<double>(file.rareNeededParts) /
        static_cast<double>(std::max<uint32>(1, file.neededParts)));
    const double transfer = Clamp01(file.currentBytesPerSecond / (512.0 * 1024.0));
    const double failures = Clamp01(static_cast<double>(file.connectionFailures) / 10.0);
    const double disk = Clamp01(file.diskPressure);

    return Score1000(0.42 * sources + 0.38 * coverage + 0.20 * transfer - 0.12 * failures - 0.10 * disk);
}

uint32 CDownloadIntelligence::SourceDiscoveryBudget(const EmuleNextFileSignals& file, uint32 normalBudget)
{
    if (normalBudget == 0)
        return 0;

    double multiplier = 1.0;
    if (file.usableSources == 0)
        multiplier = 4.0;
    else if (file.usableSources <= 3)
        multiplier = 2.5;
    else if (file.usableSources <= 8)
        multiplier = 1.5;
    else if (file.usableSources >= 50)
        multiplier = 0.35;
    else if (file.usableSources >= 20)
        multiplier = 0.65;

    if (file.rareNeededParts > 0)
        multiplier += std::min(1.5, 0.25 * static_cast<double>(file.rareNeededParts));
    if (file.completionRatio >= 0.95 && file.neededParts > 0)
        multiplier += 0.75; // endgame discovery boost
    if (file.currentBytesPerSecond > 2.0 * 1024.0 * 1024.0 && file.rareNeededParts == 0)
        multiplier *= 0.65; // already healthy; save Kad/server traffic

    multiplier = std::max(0.25, std::min(4.0, multiplier));
    return std::max<uint32>(1, static_cast<uint32>(normalBudget * multiplier + 0.5));
}

uint32 CDownloadIntelligence::A4AFPriority(const EmuleNextFileSignals& file, uint32 sourceQuality)
{
    double score = 0.25 * Clamp01(static_cast<double>(sourceQuality) / 1000.0);
    score += 0.20 * Clamp01(file.completionRatio);
    score += file.favorite ? 0.16 : 0.0;
    score += file.highPriority ? 0.14 : 0.0;
    score += file.rareNeededParts > 0 ? 0.17 : 0.0;
    score += file.usableSources <= 3 ? 0.08 : 0.0;
    if (file.hashing || file.neededParts == 0)
        score *= 0.10;
    return Score1000(score);
}

EmuleNextStallReason CDownloadIntelligence::DiagnoseStall(const EmuleNextFileSignals& file)
{
    if (file.hashing)
        return ENSR_HASHING;
    if (file.diskPressure >= 0.90)
        return ENSR_DISK_LIMITED;
    if (file.neededParts == 0)
        return ENSR_NONE;
    if (file.totalSources == 0)
        return file.kadResultsLastCycle == 0 ? ENSR_KAD_DISCOVERY_FAILURE : ENSR_NO_SOURCES;
    if (file.usableSources == 0 && file.a4afCandidates > 0)
        return ENSR_A4AF_CONFLICT;
    if (file.usableSources == 0)
        return ENSR_NO_NEEDED_PARTS;
    if (file.rareNeededParts > 0)
        return ENSR_RARE_PARTS;
    if (file.queuedSources >= file.usableSources && file.currentBytesPerSecond <= 0.0)
        return ENSR_ALL_REMOTE_QUEUED;
    if (file.connectionFailures >= std::max<uint32>(3, file.usableSources))
        return ENSR_CONNECTION_FAILURE;
    return ENSR_NONE;
}

EmuleNextEta CDownloadIntelligence::EstimateEta(const EmuleNextFileSignals& file, uint64 bytesRemaining)
{
    EmuleNextEta eta;
    if (bytesRemaining == 0) {
        eta.known = true;
        eta.seconds = 0;
        eta.confidencePercent = 100;
        eta.reason = _T("complete");
        return eta;
    }

    const EmuleNextStallReason stall = DiagnoseStall(file);
    if (stall == ENSR_NO_SOURCES || stall == ENSR_KAD_DISCOVERY_FAILURE || stall == ENSR_NO_NEEDED_PARTS) {
        eta.reason = file.rareNeededParts > 0
            ? _T("rare part currently has no usable source")
            : _T("no usable source currently available");
        return eta;
    }

    double rate = 0.0;
    if (file.currentBytesPerSecond > 0.0 && file.historicalBytesPerSecond > 0.0)
        rate = file.currentBytesPerSecond * 0.72 + file.historicalBytesPerSecond * 0.28;
    else
        rate = std::max(file.currentBytesPerSecond, file.historicalBytesPerSecond * 0.65);

    if (rate < 1024.0) {
        eta.reason = _T("transfer rate is not stable enough yet");
        return eta;
    }

    double riskFactor = 1.0;
    if (file.rareNeededParts > 0)
        riskFactor += std::min(1.0, 0.18 * static_cast<double>(file.rareNeededParts));
    if (file.queuedSources > file.usableSources / 2)
        riskFactor += 0.15;
    if (file.diskPressure > 0.70)
        riskFactor += 0.15;

    eta.known = true;
    eta.seconds = static_cast<uint64>((static_cast<double>(bytesRemaining) / rate) * riskFactor + 0.5);

    int confidence = 45;
    confidence += static_cast<int>(std::min<uint32>(25, file.usableSources * 3));
    if (file.currentBytesPerSecond > 0.0 && file.historicalBytesPerSecond > 0.0)
        confidence += 15;
    confidence -= static_cast<int>(std::min<uint32>(30, file.rareNeededParts * 8));
    confidence -= static_cast<int>(Clamp01(file.diskPressure) * 15.0);
    confidence = std::max(5, std::min(95, confidence));
    eta.confidencePercent = static_cast<uint8>(confidence);
    eta.reason.Format(_T("%u usable source%s; %u rare needed part%s"),
        file.usableSources, file.usableSources == 1 ? _T("") : _T("s"),
        file.rareNeededParts, file.rareNeededParts == 1 ? _T("") : _T("s"));
    return eta;
}

uint32 CDownloadIntelligence::ChooseRarestRiskPart(const std::vector<EmuleNextPartSignals>& parts)
{
    if (parts.empty())
        return static_cast<uint32>(-1);

    uint32 bestIndex = static_cast<uint32>(-1);
    uint32 bestRisk = 0;
    bool foundUnrequested = false;
    for (size_t i = 0; i < parts.size(); ++i) {
        if (foundUnrequested && parts[i].requestedNow)
            continue;
        const uint32 risk = PartRisk(parts[i]);
        if (!parts[i].requestedNow && !foundUnrequested) {
            foundUnrequested = true;
            bestIndex = static_cast<uint32>(i);
            bestRisk = risk;
            continue;
        }
        if ((parts[i].requestedNow == !foundUnrequested) && risk > bestRisk) {
            bestIndex = static_cast<uint32>(i);
            bestRisk = risk;
        }
    }
    return bestIndex;
}
