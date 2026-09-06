//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "EmuleNextDatabase.h"

#include <vector>

enum EmuleNextKnownUsersQuery
{
    ENKUQ_ALL = 0,
    ENKUQ_FAVORITES,
    ENKUQ_RECENT
};

struct EmuleNextKnownUserRecord
{
    EmuleNextHash16 userHash;
    CStringW userName;
    CStringW alias;
    CStringW clientSoftware;
    CStringW clientVersion;
    uint64 firstSeen;
    uint64 lastSeen;
    uint32 fileCount;
    uint64 totalBytes;
    bool favorite;
    uint32 endpointIp;
    uint16 endpointTcpPort;
    uint16 endpointUdpPort;
    uint16 endpointKadPort;
    uint64 endpointFirstSeen;
    uint64 endpointLastSeen;

    EmuleNextKnownUserRecord()
        : firstSeen(0), lastSeen(0), fileCount(0), totalBytes(0), favorite(false)
        , endpointIp(0), endpointTcpPort(0), endpointUdpPort(0), endpointKadPort(0)
        , endpointFirstSeen(0), endpointLastSeen(0)
    {
    }
};

struct EmuleNextKnownFileRecord
{
    EmuleNextHash16 fileHash;
    CStringW fileName;
    CStringW aichHash;
    uint64 fileSize;
    uint64 firstSeen;
    uint64 lastSeen;
    uint64 lastVerified;

    EmuleNextKnownFileRecord()
        : fileSize(0), firstSeen(0), lastSeen(0), lastVerified(0)
    {
    }
};

class CKnownUsersService
{
public:
    explicit CKnownUsersService(const CStringW& databasePath);

    // Reads are bounded and query-only. Current-vs-history is intentionally
    // resolved by the UI against CClientList, not inferred from stale SQLite.
    bool ListUsers(EmuleNextKnownUsersQuery query,
        std::vector<EmuleNextKnownUserRecord>& users) const;
    bool ListFiles(const EmuleNextHash16& peerHash,
        std::vector<EmuleNextKnownFileRecord>& files) const;

    // Used only from the Known Users background delete worker. Peer metadata
    // (alias/favorite) is deliberately retained so local user annotations are
    // not destroyed together with observed network history.
    bool DeletePeerHistory(const EmuleNextHash16& peerHash) const;

private:
    CStringW m_databasePath;
};
