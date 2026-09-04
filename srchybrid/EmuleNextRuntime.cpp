//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//
//This program is free software; you can redistribute it and/or
//modify it under the terms of the GNU General Public License
//as published by the Free Software Foundation; either
//version 2 of the License, or (at your option) any later version.
#include "stdafx.h"
#include "EmuleNextRuntime.h"
#include "Preferences.h"
#include "Log.h"

CEmuleNextRuntime theEmuleNext;

CEmuleNextRuntime::CEmuleNextRuntime()
{
}

CEmuleNextRuntime::~CEmuleNextRuntime()
{
    Stop();
}

bool CEmuleNextRuntime::Start()
{
    if (m_database.IsRunning())
        return true;

    const CStringW databasePath = CStringW(thePrefs.GetMuleDirectory(EMULE_CONFIGDIR)) + L"emule-next.sqlite3";
    const bool started = m_database.Start(databasePath);
    if (started)
        AddLogLine(false, _T("eMule Next intelligence database: %s"), static_cast<LPCTSTR>(CString(databasePath)));
    else
        AddLogLine(true, _T("eMule Next intelligence database disabled: %s"), static_cast<LPCTSTR>(CString(m_database.GetLastError())));
    return started;
}

void CEmuleNextRuntime::Stop()
{
    m_database.Stop();
}

bool CEmuleNextRuntime::IsRunning() const
{
    return m_database.IsRunning();
}

CEmuleNextDatabase& CEmuleNextRuntime::Database()
{
    return m_database;
}

const CEmuleNextDatabase& CEmuleNextRuntime::Database() const
{
    return m_database;
}

void CEmuleNextRuntime::RecordPeerSeen(const unsigned char* userHash,
    LPCTSTR userName,
    const CString& clientSoftware,
    const CString& clientVersion,
    uint32 ip,
    uint16 tcpPort,
    uint16 udpPort,
    uint16 kadPort)
{
    EmuleNextPeerObservation observation;
    observation.userHash = EmuleNextHash16(userHash);
    if (!observation.userHash.valid)
        return;
    if (userName != NULL)
        observation.userName = CStringW(userName);
    observation.clientSoftware = CStringW(clientSoftware);
    observation.clientVersion = CStringW(clientVersion);
    observation.ip = ip;
    observation.tcpPort = tcpPort;
    observation.udpPort = udpPort;
    observation.kadPort = kadPort;
    m_database.RecordPeerSeen(observation);
}

void CEmuleNextRuntime::RecordFileSeen(const unsigned char* ed2kHash,
    uint64 fileSize,
    LPCTSTR fileName,
    const CString& aichHash)
{
    EmuleNextFileObservation observation;
    observation.ed2kHash = EmuleNextHash16(ed2kHash);
    if (!observation.ed2kHash.valid || fileSize == 0)
        return;
    observation.fileSize = fileSize;
    if (fileName != NULL)
        observation.fileName = CStringW(fileName);
    observation.aichHash = CStringW(aichHash);
    m_database.RecordFileSeen(observation);
}

void CEmuleNextRuntime::RecordPeerFileSeen(const unsigned char* peerHash,
    const unsigned char* ed2kHash,
    uint64 fileSize,
    LPCTSTR fileName,
    const CString& aichHash,
    LPCTSTR sourceKind)
{
    EmuleNextPeerFileObservation observation;
    observation.peerHash = EmuleNextHash16(peerHash);
    observation.fileHash = EmuleNextHash16(ed2kHash);
    if (!observation.peerHash.valid || !observation.fileHash.valid || fileSize == 0)
        return;
    observation.fileSize = fileSize;
    if (fileName != NULL)
        observation.fileName = CStringW(fileName);
    observation.aichHash = CStringW(aichHash);
    if (sourceKind != NULL)
        observation.sourceKind = CStringW(sourceKind);
    m_database.RecordPeerFileSeen(observation);
}
