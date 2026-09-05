//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "EmuleNextDatabase.h"

#include <vector>

struct EmuleNextTransferHistoryRecord
{
    EmuleNextHash16 peerHash;
    EmuleNextHash16 fileHash;
    CStringW userName;
    CStringW fileName;
    CStringW direction;
    CStringW result;
    uint64 fileSize;
    uint64 bytesTransferred;
    uint32 averageBytesPerSecond;
    bool successful;
    uint64 startedAt;
    uint64 finishedAt;

    EmuleNextTransferHistoryRecord()
        : fileSize(0), bytesTransferred(0), averageBytesPerSecond(0),
          successful(false), startedAt(0), finishedAt(0)
    {
    }
};

class CDownloadIntelligenceService
{
public:
    explicit CDownloadIntelligenceService(const CStringW& databasePath);

    bool ListRecentTransfers(size_t limit,
        std::vector<EmuleNextTransferHistoryRecord>& transfers) const;

private:
    CStringW m_databasePath;
};
