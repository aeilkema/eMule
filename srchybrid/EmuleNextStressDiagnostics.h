//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

struct EmuleNextStressDiagnosticsResult
{
    bool success;
    uint32 clientEntries;
    uint32 downloadEntries;
    uint64 registerMilliseconds;
    uint64 lookupMilliseconds;
    uint64 mutationMilliseconds;
    CStringW details;

    EmuleNextStressDiagnosticsResult();
};

class CEmuleNextStressDiagnostics
{
public:
    // Pure in-memory deterministic stress test. No network, SQLite, files or
    // scheduler actions are touched. Fake object addresses are index keys only
    // and are never dereferenced by CClientIndex/CDownloadIndex.
    static bool RunIndexStress(uint32 clientEntries,
        uint32 downloadEntries,
        EmuleNextStressDiagnosticsResult& result);
};
