//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//
//This program is free software; you can redistribute it and/or
//modify it under the terms of the GNU General Public License
//as published by the Free Software Foundation; either
//version 2 of the License, or (at your option) any later version.
#pragma once

#include "EmuleNextDatabase.h"

#include <map>
#include <mutex>

class CEmuleNextRuntime
{
public:
    CEmuleNextRuntime();
    ~CEmuleNextRuntime();

    bool Start();
    void Stop();
    bool IsRunning() const;

    CEmuleNextDatabase& Database();
    const CEmuleNextDatabase& Database() const;

    void RecordPeerSeen(const unsigned char* userHash,
        LPCTSTR userName,
        const CString& clientSoftware,
        const CString& clientVersion,
        uint32 ip,
        uint16 tcpPort,
        uint16 udpPort,
        uint16 kadPort);

    void RecordFileSeen(const unsigned char* ed2kHash,
        uint64 fileSize,
        LPCTSTR fileName,
        const CString& aichHash = CString());

    void RecordPeerFileSeen(const unsigned char* peerHash,
        const unsigned char* ed2kHash,
        uint64 fileSize,
        LPCTSTR fileName,
        const CString& aichHash,
        LPCTSTR sourceKind);

    // Automatic peer-share discovery is deliberately separated from the
    // legacy/manual "View Shared Files" flow. SearchList uses this short-lived
    // marker to persist an automatic response without creating a user search
    // tab or doing thousands of synchronous GUI inserts.
    void MarkAutomaticPeerShareRequest(const unsigned char* peerHash, uint64 ttlSeconds = 180);
    bool IsAutomaticPeerShareRequest(const unsigned char* peerHash) const;
    void CompleteAutomaticPeerShareRequest(const unsigned char* peerHash);

private:
    CEmuleNextRuntime(const CEmuleNextRuntime&);
    CEmuleNextRuntime& operator=(const CEmuleNextRuntime&);

    CEmuleNextDatabase m_database;

    mutable std::mutex m_autoShareMutex;
    mutable std::map<std::array<unsigned char, 16>, uint64> m_autoShareRequests;
};

extern CEmuleNextRuntime theEmuleNext;
