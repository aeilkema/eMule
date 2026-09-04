//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "EmuleNextDatabase.h"
#include <unordered_map>
#include <vector>

class CUpDownClient;

struct EmuleNextEndpointKey
{
    uint32 ip;
    uint16 port;

    EmuleNextEndpointKey();
    EmuleNextEndpointKey(uint32 valueIp, uint16 valuePort);
    bool operator==(const EmuleNextEndpointKey& other) const;
};

struct EmuleNextHash16Hasher
{
    size_t operator()(const std::array<unsigned char, 16>& value) const;
};

struct EmuleNextEndpointHasher
{
    size_t operator()(const EmuleNextEndpointKey& value) const;
};

class CClientIndex
{
public:
    CClientIndex();

    void Clear();
    void RegisterClient(CUpDownClient* client,
        const unsigned char* userHash,
        uint32 connectIp,
        uint16 tcpPort,
        uint16 udpPort,
        uint16 kadPort);
    void UnregisterClient(CUpDownClient* client);
    void UpdateClient(CUpDownClient* client,
        const unsigned char* userHash,
        uint32 connectIp,
        uint16 tcpPort,
        uint16 udpPort,
        uint16 kadPort);

    CUpDownClient* FindByUserHash(const unsigned char* userHash,
        uint32 connectIp = 0, uint16 tcpPort = 0) const;
    CUpDownClient* FindByTcpEndpoint(uint32 ip, uint16 port) const;
    CUpDownClient* FindByUdpEndpoint(uint32 ip, uint16 port) const;
    CUpDownClient* FindByKadEndpoint(uint32 ip, uint16 port) const;
    CUpDownClient* FindAnyByIp(uint32 ip) const;

    size_t Size() const;
    bool ValidateSize(size_t expected) const;

private:
    struct Registration
    {
        EmuleNextHash16 hash;
        uint32 ip;
        uint16 tcpPort;
        uint16 udpPort;
        uint16 kadPort;
        Registration();
    };

    typedef std::unordered_map<std::array<unsigned char, 16>,
        std::vector<CUpDownClient*>, EmuleNextHash16Hasher> HashMap;
    typedef std::unordered_map<EmuleNextEndpointKey,
        CUpDownClient*, EmuleNextEndpointHasher> EndpointMap;
    typedef std::unordered_map<uint32,
        std::vector<CUpDownClient*> > IpMap;
    typedef std::unordered_map<CUpDownClient*, Registration> RegistrationMap;

    static void RemovePointer(std::vector<CUpDownClient*>& values, CUpDownClient* client);

    HashMap m_byUserHash;
    EndpointMap m_byTcpEndpoint;
    EndpointMap m_byUdpEndpoint;
    EndpointMap m_byKadEndpoint;
    IpMap m_byIp;
    RegistrationMap m_registrations;
};
