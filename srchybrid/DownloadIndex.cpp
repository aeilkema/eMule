//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "DownloadIndex.h"

CDownloadIndex::Registration::Registration()
    : kadSearchId(0)
{
}

CDownloadIndex::CDownloadIndex()
{
}

void CDownloadIndex::Clear()
{
    m_byHash.clear();
    m_byKadSearchId.clear();
    m_registrations.clear();
}

void CDownloadIndex::RegisterFile(CPartFile* file,
    const unsigned char* ed2kHash,
    uint32 kadSearchId)
{
    if (file == NULL)
        return;

    if (m_registrations.find(file) != m_registrations.end())
        UnregisterFile(file);

    Registration registration;
    registration.hash = EmuleNextHash16(ed2kHash);
    registration.kadSearchId = kadSearchId;
    m_registrations[file] = registration;

    if (registration.hash.valid)
        m_byHash[registration.hash.bytes] = file;
    if (kadSearchId != 0)
        m_byKadSearchId[kadSearchId] = file;
}

void CDownloadIndex::UnregisterFile(CPartFile* file)
{
    RegistrationMap::iterator registrationIt = m_registrations.find(file);
    if (registrationIt == m_registrations.end())
        return;

    const Registration registration = registrationIt->second;
    if (registration.hash.valid) {
        HashMap::iterator it = m_byHash.find(registration.hash.bytes);
        if (it != m_byHash.end() && it->second == file)
            m_byHash.erase(it);
    }
    if (registration.kadSearchId != 0) {
        KadMap::iterator it = m_byKadSearchId.find(registration.kadSearchId);
        if (it != m_byKadSearchId.end() && it->second == file)
            m_byKadSearchId.erase(it);
    }
    m_registrations.erase(registrationIt);
}

void CDownloadIndex::UpdateKadSearchId(CPartFile* file, uint32 kadSearchId)
{
    RegistrationMap::iterator registrationIt = m_registrations.find(file);
    if (registrationIt == m_registrations.end())
        return;

    if (registrationIt->second.kadSearchId != 0) {
        KadMap::iterator old = m_byKadSearchId.find(registrationIt->second.kadSearchId);
        if (old != m_byKadSearchId.end() && old->second == file)
            m_byKadSearchId.erase(old);
    }

    registrationIt->second.kadSearchId = kadSearchId;
    if (kadSearchId != 0)
        m_byKadSearchId[kadSearchId] = file;
}

CPartFile* CDownloadIndex::FindByHash(const unsigned char* ed2kHash) const
{
    const EmuleNextHash16 hash(ed2kHash);
    if (!hash.valid)
        return NULL;
    HashMap::const_iterator it = m_byHash.find(hash.bytes);
    return it != m_byHash.end() ? it->second : NULL;
}

CPartFile* CDownloadIndex::FindByKadSearchId(uint32 kadSearchId) const
{
    if (kadSearchId == 0)
        return NULL;
    KadMap::const_iterator it = m_byKadSearchId.find(kadSearchId);
    return it != m_byKadSearchId.end() ? it->second : NULL;
}

size_t CDownloadIndex::Size() const
{
    return m_registrations.size();
}

bool CDownloadIndex::ValidateSize(size_t expected) const
{
    return Size() == expected;
}
