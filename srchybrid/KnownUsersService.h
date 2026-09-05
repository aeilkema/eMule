//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "EmuleNextDatabase.h"

#include <vector>

struct EmuleNextKnownUserRecord
{
    EmuleNextHash16 userHash;
    CStringW userName;
    uint64 firstSeen;
    uint64 lastSeen;
    uint32 fileCount;
    uint64 totalBytes;

    EmuleNextKnownUserRecord()
        : firstSeen(0), lastSeen(0), fileCount(0), totalBytes(0)
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

    EmuleNextKnownFileRecord()
        : fileSize(0), firstSeen(0), lastSeen(0)
    {
    }
};

class CKnownUsersService
{
public:
    explicit CKnownUsersService(const CStringW& databasePath);

    bool ListUsers(std::vector<EmuleNextKnownUserRecord>& users) const;
    bool ListFiles(const EmuleNextHash16& peerHash,
        std::vector<EmuleNextKnownFileRecord>& files) const;

private:
    CStringW m_databasePath;
};
