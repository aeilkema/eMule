//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "EmuleNextSchedulerTelemetry.h"
#include <vector>

struct EmuleNextPersistedSchedulerBundle
{
    std::vector<EmuleNextSchedulerEvent> decisions;
    std::vector<EmuleNextSchedulerOutcomeRecord> outcomes;
};

class CEmuleNextSchedulerTelemetryReader
{
public:
    explicit CEmuleNextSchedulerTelemetryReader(const CStringW& databasePath);

    bool LoadRecentForFile(const unsigned char* fileHash, EmuleNextPersistedSchedulerBundle& result,
        size_t decisionLimit = 24, size_t outcomeLimit = 24) const;

private:
    CStringW m_databasePath;
};
