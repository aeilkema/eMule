//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "ClientIndex.h"

#include <algorithm>

EmuleNextEndpointKey::EmuleNextEndpointKey()
    : ip(0), port(0)
{
}

EmuleNextEndpointKey::EmuleNextEndpointKey(uint32 valueIp, uint16 valuePort)
    : ip(valueIp), port(valuePort)
{
}

bool EmuleNextEndpointKey::operator==(const EmuleNextEndpointKey& other) const
{
    return ip == other.ip && port == other.port;
}

size_t EmuleNextHash16Hasher::operator()(const std::array<unsigned char, 16>& value) const
{
    // FNV-1a is fast, deterministic and sufficient for an in-memory index.
    size_t hash = sizeof(size_t) == 8
        ? static_cast<size_t>(1469598103934665603ull)
        : static_cast<size_t>(2166136261u);
    const size_t prime = sizeof(size_t) == 8
        ? static_cast<size_t>(1099511628211ull)
        : static_cast<size_t>(16777619u);
    for (size_t i = 0; i < value.size(); ++i) {
        hash ^= static_cast<size_t>(value[i]);
        hash *= prime;
    }
    return hash;
}

size_t EmuleNextEndpointHasher::operator()(const EmuleNextEndpointKey& value) const
{
    const size_t a = static_cast<size_t>(value.ip);
    const size_t b = static_cast<size_t>(value.port);
    return (a * static_cast<size_t>(2654435761u)) ^ (b + (a << 6) + (a >> 2));
}

CClientIndex::Registration::Registration()
    : ip(0), tcpPort(0), udpPort(0), kadPort(0)
{
}

CClientIndex::CClientIndex()
{
}

void CClientIndex::Clear()
{
    m_byUserHash.clear();
    m_byTcpEndpoint.clear();
    m_byUdpEndpoint.clear();
    m_byKadEndpoint.clear();
    m_byIp.clear();
    m_registrations.clear();
}

void CClientIndex::RemovePointer(std::vector<CUpDownClient*>& values, CUpDownClient* client)
{
    values.erase(std::remove(values.begin(), values.end(), client), values.end());
}

void CClientIndex::RegisterClient(CUpDownClient* client,
    const unsigned char* userHash,
    uint32 connectIp,
    uint16 tcpPort,
    uint16 udpPort,
    uint16 kadPort)
{
    if (client == NULL)
        return;

    if (m_registrations.find(client) != m_registrations.end())
        UnregisterClient(client);

    Registration registration;
    registration.hash = EmuleNextHash16(userHash);
    registration.ip = connectIp;
    registration.tcpPort = tcpPort;
    registration.udpPort = udpPort;
    registration.kadPort = kadPort;
    m_registrations[client] = registration;

    if (registration.hash.valid)
        m_byUserHash[registration.hash.bytes].push_back(client);
    if (connectIp != 0) {
        m_byIp[connectIp].push_back(client);
        if (tcpPort != 0)
            m_byTcpEndpoint[EmuleNextEndpointKey(connectIp, tcpPort)] = client;
        if (udpPort != 0)
            m_byUdpEndpoint[EmuleNextEndpointKey(connectIp, udpPort)] = client;
        if (kadPort != 0)
            m_byKadEndpoint[EmuleNextEndpointKey(connectIp, kadPort)] = client;
    }
}

void CClientIndex::UnregisterClient(CUpDownClient* client)
{
    RegistrationMap::iterator registrationIt = m_registrations.find(client);
    if (registrationIt == m_registrations.end())
        return;

    const Registration registration = registrationIt->second;
    if (registration.hash.valid) {
        HashMap::iterator it = m_byUserHash.find(registration.hash.bytes);
        if (it != m_byUserHash.end()) {
            RemovePointer(it->second, client);
            if (it->second.empty())
                m_byUserHash.erase(it);
        }
    }

    if (registration.ip != 0) {
        IpMap::iterator ipIt = m_byIp.find(registration.ip);
        if (ipIt != m_byIp.end()) {
            RemovePointer(ipIt->second, client);
            if (ipIt->second.empty())
                m_byIp.erase(ipIt);
        }

        if (registration.tcpPort != 0) {
            const EmuleNextEndpointKey key(registration.ip, registration.tcpPort);
            EndpointMap::iterator it = m_byTcpEndpoint.find(key);
            if (it != m_byTcpEndpoint.end() && it->second == client)
                m_byTcpEndpoint.erase(it);
        }
        if (registration.udpPort != 0) {
            const EmuleNextEndpointKey key(registration.ip, registration.udpPort);
            EndpointMap::iterator it = m_byUdpEndpoint.find(key);
            if (it != m_byUdpEndpoint.end() && it->second == client)
                m_byUdpEndpoint.erase(it);
        }
        if (registration.kadPort != 0) {
            const EmuleNextEndpointKey key(registration.ip, registration.kadPort);
            EndpointMap::iterator it = m_byKadEndpoint.find(key);
            if (it != m_byKadEndpoint.end() && it->second == client)
                m_byKadEndpoint.erase(it);
        }
    }

    m_registrations.erase(registrationIt);
}

void CClientIndex::UpdateClient(CUpDownClient* client,
    const unsigned char* userHash,
    uint32 connectIp,
    uint16 tcpPort,
    uint16 udpPort,
    uint16 kadPort)
{
    UnregisterClient(client);
    RegisterClient(client, userHash, connectIp, tcpPort, udpPort, kadPort);
}

CUpDownClient* CClientIndex::FindByUserHash(const unsigned char* userHash,
    uint32 connectIp, uint16 tcpPort) const
{
    const EmuleNextHash16 hash(userHash);
    if (!hash.valid)
        return NULL;
    HashMap::const_iterator it = m_byUserHash.find(hash.bytes);
    if (it == m_byUserHash.end())
        return NULL;

    CUpDownClient* fallback = NULL;
    for (size_t i = 0; i < it->second.size(); ++i) {
        CUpDownClient* client = it->second[i];
        RegistrationMap::const_iterator reg = m_registrations.find(client);
        if (reg == m_registrations.end())
            continue;
        if (fallback == NULL)
            fallback = client;
        if ((connectIp == 0 || reg->second.ip == connectIp)
            && (tcpPort == 0 || reg->second.tcpPort == tcpPort)) {
            return client;
        }
    }
    return fallback;
}

CUpDownClient* CClientIndex::FindByTcpEndpoint(uint32 ip, uint16 port) const
{
    EndpointMap::const_iterator it = m_byTcpEndpoint.find(EmuleNextEndpointKey(ip, port));
    return it != m_byTcpEndpoint.end() ? it->second : NULL;
}

CUpDownClient* CClientIndex::FindByUdpEndpoint(uint32 ip, uint16 port) const
{
    EndpointMap::const_iterator it = m_byUdpEndpoint.find(EmuleNextEndpointKey(ip, port));
    return it != m_byUdpEndpoint.end() ? it->second : NULL;
}

CUpDownClient* CClientIndex::FindByKadEndpoint(uint32 ip, uint16 port) const
{
    EndpointMap::const_iterator it = m_byKadEndpoint.find(EmuleNextEndpointKey(ip, port));
    return it != m_byKadEndpoint.end() ? it->second : NULL;
}

CUpDownClient* CClientIndex::FindAnyByIp(uint32 ip) const
{
    IpMap::const_iterator it = m_byIp.find(ip);
    if (it == m_byIp.end() || it->second.empty())
        return NULL;
    return it->second.front();
}

size_t CClientIndex::Size() const
{
    return m_registrations.size();
}

bool CClientIndex::ValidateSize(size_t expected) const
{
    return Size() == expected;
}
