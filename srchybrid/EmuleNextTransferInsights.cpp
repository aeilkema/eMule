//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "EmuleNextTransferInsights.h"
#include "UpDownClient.h"
#include "PartFile.h"

#include <algorithm>

namespace
{
    const uint32 kMaxSourceQualitySamples = 32;
    const UINT kMaxPartChecksPerSource = 256;
    const uint32 kUsefulPartsSaturation = 8;

    uint32 BuildBoundedBestSourceQuality(const CPartFile* file)
    {
        if (file == NULL)
            return 0;

        uint32 sampled = 0;
        uint32 best = 0;
        POSITION pos = file->srclist.GetHeadPosition();
        while (pos != NULL && sampled < kMaxSourceQualitySamples) {
            CUpDownClient* client = file->srclist.GetNext(pos);
            if (client == NULL)
                continue;

            EmuleNextSourceSignals source;
            source.currentBytesPerSecond = static_cast<double>(client->GetDownloadDatarate());
            source.remoteQueueRank = client->GetRemoteQueueRank();
            const EDownloadState state = client->GetDownloadState();
            source.connected = state == DS_CONNECTED || state == DS_DOWNLOADING || state == DS_REQHASHSET;
            source.currentlyTransferring = state == DS_DOWNLOADING;

            const UINT clientParts = client->GetPartCount();
            const UINT maxPartChecks = clientParts < kMaxPartChecksPerSource ? clientParts : kMaxPartChecksPerSource;
            for (UINT part = 0; part < maxPartChecks && source.usefulPartCount < kUsefulPartsSaturation; ++part) {
                if (!file->IsComplete(part) && client->IsPartAvailable(part))
                    ++source.usefulPartCount;
            }

            const uint32 quality = CDownloadIntelligence::SourceQuality(source);
            if (quality > best)
                best = quality;
            ++sampled;
        }
        return best;
    }
}

EmuleNextTransferInsight::EmuleNextTransferInsight()
    : stall(ENSR_NONE)
    , health(0)
    , attention(0)
    , bestSourceQuality(0)
    , bytesRemaining(0)
{
}

EmuleNextTransferInsight CEmuleNextTransferInsights::Build(const CPartFile* file, double historicalBytesPerSecond)
{
    EmuleNextTransferInsight insight;
    if (file == NULL)
        return insight;

    insight.file.totalSources = file->GetSourceCount();
    const int validSources = file->GetValidSourcesCount();
    insight.file.usableSources = validSources > 0 ? static_cast<uint32>(validSources) : 0;
    insight.file.queuedSources = file->GetSrcStatisticsValue(DS_ONQUEUE);
    insight.file.connectionFailures = file->GetSrcStatisticsValue(DS_ERROR)
        + file->GetSrcStatisticsValue(DS_TOOMANYCONNS)
        + file->GetSrcStatisticsValue(DS_TOOMANYCONNSKAD);
    insight.file.a4afCandidates = file->GetSrcA4AFCount();
    insight.file.currentBytesPerSecond = static_cast<double>(file->GetDatarate());
    insight.file.historicalBytesPerSecond = historicalBytesPerSecond;
    insight.file.completionRatio = static_cast<double>(file->GetPercentCompleted()) / 100.0;
    insight.file.hashing = file->GetStatus() == PS_HASHING
        || file->GetStatus() == PS_WAITINGFORHASH
        || file->GetFileOp() == PFOP_HASHING;
    insight.file.highPriority = file->GetDownPriority() == PR_HIGH
        || file->GetDownPriority() == PR_VERYHIGH;
    insight.file.kadResultsLastCycle = 1;

    insight.bestSourceQuality = BuildBoundedBestSourceQuality(file);

    const UINT partCount = file->GetPartCount();
    insight.parts.resize(partCount);
    for (UINT part = 0; part < partCount; ++part) {
        EmuleNextPartSignals& p = insight.parts[part];
        if (file->IsComplete(part)) {
            p.independentSources = 65535;
            p.reliableSources = 65535;
            p.bestSourceQuality = 1000.0;
            p.completionImpact = 0.0;
            p.requestedNow = true;
            continue;
        }
        p.independentSources = file->GetPartSourceFrequency(part);
        p.reliableSources = p.independentSources;
        p.bestSourceQuality = static_cast<double>(insight.bestSourceQuality);
        p.completionImpact = partCount > 0 ? 1.0 / static_cast<double>(partCount) : 0.0;
        ++insight.file.neededParts;
        if (p.independentSources <= 2)
            ++insight.file.rareNeededParts;
    }

    insight.bytesRemaining = file->GetFileSize() > file->GetCompletedSize()
        ? file->GetFileSize() - file->GetCompletedSize() : 0;
    insight.health = CDownloadIntelligence::FileAvailabilityHealth(insight.file);
    insight.attention = CDownloadIntelligence::AttentionScore(insight.file);
    insight.stall = CDownloadIntelligence::DiagnoseStall(insight.file);
    insight.eta = CDownloadIntelligence::EstimateEta(insight.file, insight.bytesRemaining);
    return insight;
}
