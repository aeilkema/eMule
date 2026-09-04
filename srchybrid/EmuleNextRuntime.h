//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//
//This program is free software; you can redistribute it and/or
//modify it under the terms of the GNU General Public License
//as published by the Free Software Foundation; either
//version 2 of the License, or (at your option) any later version.
#pragma once

#include "EmuleNextDatabase.h"

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

private:
    CEmuleNextRuntime(const CEmuleNextRuntime&);
    CEmuleNextRuntime& operator=(const CEmuleNextRuntime&);

    CEmuleNextDatabase m_database;
};

extern CEmuleNextRuntime theEmuleNext;
