//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "ClientIndex.h"
#include <unordered_map>

class CPartFile;

class CDownloadIndex
{
public:
    CDownloadIndex();

    void Clear();
    void RegisterFile(CPartFile* file, const unsigned char* ed2kHash, uint32 kadSearchId = 0);
    void UnregisterFile(CPartFile* file);
    void UpdateKadSearchId(CPartFile* file, uint32 kadSearchId);

    CPartFile* FindByHash(const unsigned char* ed2kHash) const;
    CPartFile* FindByKadSearchId(uint32 kadSearchId) const;

    size_t Size() const;
    bool ValidateSize(size_t expected) const;

private:
    struct Registration
    {
        EmuleNextHash16 hash;
        uint32 kadSearchId;
        Registration();
    };

    typedef std::unordered_map<std::array<unsigned char, 16>,
        CPartFile*, EmuleNextHash16Hasher> HashMap;
    typedef std::unordered_map<uint32, CPartFile*> KadMap;
    typedef std::unordered_map<CPartFile*, Registration> RegistrationMap;

    HashMap m_byHash;
    KadMap m_byKadSearchId;
    RegistrationMap m_registrations;
};
