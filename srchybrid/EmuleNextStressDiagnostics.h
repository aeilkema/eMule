//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

struct EmuleNextStressDiagnosticsResult
{
    bool success;
    uint32 clientEntries;
    uint32 downloadEntries;
    uint32 writerEvents;
    uint64 registerMilliseconds;
    uint64 lookupMilliseconds;
    uint64 mutationMilliseconds;
    uint64 writerMilliseconds;
    CStringW details;

    EmuleNextStressDiagnosticsResult();
};

class CEmuleNextStressDiagnostics
{
public:
    // Pure in-memory deterministic index stress. Fake object addresses are
    // index keys only and are never dereferenced by CClientIndex/CDownloadIndex.
    static bool RunIndexStress(uint32 clientEntries,
        uint32 downloadEntries,
        EmuleNextStressDiagnosticsResult& result);

    // Uses a temporary disposable SQLite file and the real async database
    // writer. It never touches the user's production intelligence database.
    static bool RunWriterQueueStress(uint32 eventCount,
        EmuleNextStressDiagnosticsResult& result);
};
