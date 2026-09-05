//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "EmuleNextTransferInsights.h"
#include "PartFile.h"

#include <algorithm>

EmuleNextTransferInsight::EmuleNextTransferInsight()
    : stall(ENSR_NONE)
    , health(0)
    , attention(0)
    , bestSourceQuality(500)
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

    const UINT partCount = file->GetPartCount();
    insight.parts.reserve(partCount);
    for (UINT part = 0; part < partCount; ++part) {
        if (file->IsComplete(part))
            continue;
        EmuleNextPartSignals p;
        p.independentSources = file->GetPartSourceFrequency(part);
        p.reliableSources = p.independentSources;
        p.bestSourceQuality = 500.0;
        p.completionImpact = partCount > 0 ? 1.0 / static_cast<double>(partCount) : 0.0;
        insight.parts.push_back(p);
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
