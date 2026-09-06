//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "EmuleNextStressDiagnostics.h"
#include "ClientIndex.h"
#include "DownloadIndex.h"

#include <vector>
#include <stdint.h>

namespace
{
    void MakeHash(uint32 value, unsigned char hash[16])
    {
        for (int i = 0; i < 16; ++i)
            hash[i] = static_cast<unsigned char>((value >> ((i % 4) * 8)) ^ (0x5Du + i * 17u));
        hash[15] ^= static_cast<unsigned char>((value * 131u) & 0xFFu);
        if (value == 0)
            hash[0] = 1;
    }

    CUpDownClient* FakeClient(uint32 index)
    {
        return reinterpret_cast<CUpDownClient*>(static_cast<uintptr_t>(index + 1u));
    }

    CPartFile* FakeFile(uint32 index)
    {
        return reinterpret_cast<CPartFile*>(static_cast<uintptr_t>(0x100000u + index + 1u));
    }
}

EmuleNextStressDiagnosticsResult::EmuleNextStressDiagnosticsResult()
    : success(false), clientEntries(0), downloadEntries(0), registerMilliseconds(0),
      lookupMilliseconds(0), mutationMilliseconds(0)
{
}

bool CEmuleNextStressDiagnostics::RunIndexStress(uint32 clientEntries,
    uint32 downloadEntries,
    EmuleNextStressDiagnosticsResult& result)
{
    result = EmuleNextStressDiagnosticsResult();
    result.clientEntries = clientEntries;
    result.downloadEntries = downloadEntries;

    if (clientEntries == 0 || clientEntries > 20000 || downloadEntries == 0 || downloadEntries > 10000) {
        result.details = L"Stress bounds rejected; client range 1..20000, download range 1..10000.";
        return false;
    }

    CClientIndex clientIndex;
    CDownloadIndex downloadIndex;
    std::vector<std::array<unsigned char, 16> > clientHashes(clientEntries);
    std::vector<std::array<unsigned char, 16> > downloadHashes(downloadEntries);

    ULONGLONG started = ::GetTickCount64();
    for (uint32 i = 0; i < clientEntries; ++i) {
        unsigned char hash[16];
        MakeHash(i + 1u, hash);
        memcpy(clientHashes[i].data(), hash, 16);
        const uint32 ip = 0x0A000001u + i;
        const uint16 tcp = static_cast<uint16>(1000u + (i % 50000u));
        const uint16 udp = static_cast<uint16>(1100u + (i % 50000u));
        const uint16 kad = static_cast<uint16>(1200u + (i % 50000u));
        clientIndex.RegisterClient(FakeClient(i), hash, ip, tcp, udp, kad);
    }
    for (uint32 i = 0; i < downloadEntries; ++i) {
        unsigned char hash[16];
        MakeHash(0x40000000u + i + 1u, hash);
        memcpy(downloadHashes[i].data(), hash, 16);
        downloadIndex.RegisterFile(FakeFile(i), hash, i + 1u);
    }
    result.registerMilliseconds = static_cast<uint64>(::GetTickCount64() - started);

    if (!clientIndex.ValidateSize(clientEntries) || !downloadIndex.ValidateSize(downloadEntries)) {
        result.details = L"Registration count mismatch.";
        return false;
    }

    started = ::GetTickCount64();
    for (uint32 i = 0; i < clientEntries; ++i) {
        const uint32 ip = 0x0A000001u + i;
        const uint16 tcp = static_cast<uint16>(1000u + (i % 50000u));
        const uint16 udp = static_cast<uint16>(1100u + (i % 50000u));
        const uint16 kad = static_cast<uint16>(1200u + (i % 50000u));
        CUpDownClient* expected = FakeClient(i);
        if (clientIndex.FindByUserHash(clientHashes[i].data(), ip, tcp) != expected
            || clientIndex.FindByTcpEndpoint(ip, tcp) != expected
            || clientIndex.FindByUdpEndpoint(ip, udp) != expected
            || clientIndex.FindByKadEndpoint(ip, kad) != expected
            || clientIndex.FindAnyByIp(ip) != expected) {
            result.details.Format(L"Client lookup mismatch at index %u.", i);
            return false;
        }
    }
    for (uint32 i = 0; i < downloadEntries; ++i) {
        CPartFile* expected = FakeFile(i);
        if (downloadIndex.FindByHash(downloadHashes[i].data()) != expected
            || downloadIndex.FindByKadSearchId(i + 1u) != expected) {
            result.details.Format(L"Download lookup mismatch at index %u.", i);
            return false;
        }
    }
    result.lookupMilliseconds = static_cast<uint64>(::GetTickCount64() - started);

    started = ::GetTickCount64();
    for (uint32 i = 0; i < clientEntries; i += 5u) {
        const uint32 ip = 0x0B000001u + i;
        clientIndex.UpdateClient(FakeClient(i), clientHashes[i].data(), ip,
            static_cast<uint16>(2000u + (i % 50000u)),
            static_cast<uint16>(2100u + (i % 50000u)),
            static_cast<uint16>(2200u + (i % 50000u)));
    }
    for (uint32 i = 0; i < downloadEntries; i += 5u)
        downloadIndex.UpdateKadSearchId(FakeFile(i), 0x70000000u + i + 1u);

    uint32 removedClients = 0;
    for (uint32 i = 3u; i < clientEntries; i += 7u) {
        clientIndex.UnregisterClient(FakeClient(i));
        ++removedClients;
    }
    uint32 removedDownloads = 0;
    for (uint32 i = 3u; i < downloadEntries; i += 7u) {
        downloadIndex.UnregisterFile(FakeFile(i));
        ++removedDownloads;
    }
    result.mutationMilliseconds = static_cast<uint64>(::GetTickCount64() - started);

    if (!clientIndex.ValidateSize(static_cast<size_t>(clientEntries - removedClients))
        || !downloadIndex.ValidateSize(static_cast<size_t>(downloadEntries - removedDownloads))) {
        result.details = L"Mutation/unregister count mismatch.";
        return false;
    }

    for (uint32 i = 0; i < clientEntries; i += 97u) {
        const bool removed = i >= 3u && ((i - 3u) % 7u) == 0u;
        CUpDownClient* found = clientIndex.FindByUserHash(clientHashes[i].data());
        if ((removed && found != NULL) || (!removed && found != FakeClient(i))) {
            result.details.Format(L"Post-mutation client mismatch at index %u.", i);
            return false;
        }
    }
    for (uint32 i = 0; i < downloadEntries; i += 97u) {
        const bool removed = i >= 3u && ((i - 3u) % 7u) == 0u;
        CPartFile* found = downloadIndex.FindByHash(downloadHashes[i].data());
        if ((removed && found != NULL) || (!removed && found != FakeFile(i))) {
            result.details.Format(L"Post-mutation download mismatch at index %u.", i);
            return false;
        }
    }

    result.success = true;
    result.details.Format(L"PASS: %u client entries and %u download entries; register %I64u ms, lookup %I64u ms, mutate %I64u ms.",
        clientEntries, downloadEntries, result.registerMilliseconds,
        result.lookupMilliseconds, result.mutationMilliseconds);
    return true;
}
