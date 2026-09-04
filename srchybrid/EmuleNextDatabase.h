//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//
//This program is free software; you can redistribute it and/or
//modify it under the terms of the GNU General Public License
//as published by the Free Software Foundation; either
//version 2 of the License, or (at your option) any later version.
#pragma once

#include <array>
#include <vector>

struct EmuleNextHash16
{
    std::array<unsigned char, 16> bytes;
    bool valid;

    EmuleNextHash16();
    explicit EmuleNextHash16(const unsigned char* hash);
};

struct EmuleNextPeerObservation
{
    EmuleNextHash16 userHash;
    CStringW userName;
    CStringW clientSoftware;
    CStringW clientVersion;
    uint32 ip;
    uint16 tcpPort;
    uint16 udpPort;
    uint16 kadPort;
    uint64 seenAt;

    EmuleNextPeerObservation();
};

struct EmuleNextFileObservation
{
    EmuleNextHash16 ed2kHash;
    uint64 fileSize;
    CStringW fileName;
    CStringW aichHash;
    uint64 seenAt;

    EmuleNextFileObservation();
};

struct EmuleNextPeerFileObservation
{
    EmuleNextHash16 peerHash;
    EmuleNextHash16 fileHash;
    uint64 fileSize;
    CStringW fileName;
    CStringW aichHash;
    CStringW sourceKind;
    uint64 seenAt;

    EmuleNextPeerFileObservation();
};

struct EmuleNextTransferObservation
{
    EmuleNextHash16 peerHash;
    EmuleNextHash16 fileHash;
    uint64 fileSize;
    uint64 bytesTransferred;
    uint32 averageBytesPerSecond;
    bool successful;
    CStringW direction;
    CStringW result;
    uint64 startedAt;
    uint64 finishedAt;

    EmuleNextTransferObservation();
};

struct EmuleNextFavoriteRecord
{
    EmuleNextHash16 fileHash;
    uint64 fileSize;
    CStringW fileName;
    CStringW aichHash;
    CStringW localPath;
    CStringW tags;
    bool autoRestore;

    EmuleNextFavoriteRecord();
};

struct EmuleNextSearchFileResult
{
    EmuleNextHash16 fileHash;
    uint64 fileSize;
    CStringW fileName;
    CStringW aichHash;
    uint64 firstSeen;
    uint64 lastSeen;
    uint32 historicalPeerCount;
    bool favorite;
    bool completedBefore;
};

class CEmuleNextDatabase
{
public:
    CEmuleNextDatabase();
    ~CEmuleNextDatabase();

    bool Start(const CStringW& databasePath);
    void Stop();
    bool IsRunning() const;
    CStringW GetLastError() const;
    CStringW GetDatabasePath() const;

    // All Record* calls are non-blocking. They only copy an event into the
    // database writer queue and are safe to call from the eMule core thread.
    void RecordPeerSeen(const EmuleNextPeerObservation& observation);
    void RecordFileSeen(const EmuleNextFileObservation& observation);
    void RecordPeerFileSeen(const EmuleNextPeerFileObservation& observation);
    void RecordTransfer(const EmuleNextTransferObservation& observation);
    void SaveFavorite(const EmuleNextFavoriteRecord& favorite);
    void RemoveFavorite(const EmuleNextHash16& fileHash, uint64 fileSize);
    void SaveDownloadLater(const EmuleNextFileObservation& file);
    void MarkLibraryCompleted(const EmuleNextFileObservation& file, const CStringW& localPath);

    // Read operations use a separate short-lived SQLite connection so GUI
    // reads never share the writer connection or block network processing.
    bool SearchFiles(const CStringW& text, size_t limit, size_t offset,
        std::vector<EmuleNextSearchFileResult>& results) const;
    bool HasCompletedFile(const EmuleNextHash16& fileHash, uint64 fileSize) const;
    bool IsFavorite(const EmuleNextHash16& fileHash, uint64 fileSize) const;

    bool IntegrityCheck(CStringW& result) const;
    bool BackupTo(const CStringW& destinationPath) const;

private:
    CEmuleNextDatabase(const CEmuleNextDatabase&);
    CEmuleNextDatabase& operator=(const CEmuleNextDatabase&);

    class Impl;
    Impl* m_impl;
};
