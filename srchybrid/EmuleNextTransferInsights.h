//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "DownloadIntelligence.h"
#include <vector>

class CPartFile;

struct EmuleNextTransferInsight
{
    EmuleNextFileSignals file;
    std::vector<EmuleNextPartSignals> parts;
    EmuleNextEta eta;
    EmuleNextStallReason stall;
    uint32 health;
    uint32 attention;
    uint32 bestSourceQuality;
    uint32 averageSourceQuality;
    uint32 sampledSources;
    uint32 strongSources;
    uint32 normalSources;
    uint32 weakSources;
    uint32 failedSources;
    uint32 transferringSources;
    uint64 bytesRemaining;

    EmuleNextTransferInsight();
};

class CEmuleNextTransferInsights
{
public:
    static EmuleNextTransferInsight Build(const CPartFile* file, double historicalBytesPerSecond = 0.0);
};
