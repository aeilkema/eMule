//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "EmuleNextDatabase.h"

struct EmuleNextDatabaseMaintenanceSnapshot
{
    int schemaVersion;
    uint64 databaseBytes;
    uint64 walBytes;
    uint32 backupCount;
    uint64 lastBackupAt;
    uint64 lastIntegrityAt;
    CStringW lastIntegrityResult;
    uint64 peerCount;
    uint64 fileCount;
    uint64 libraryCount;
    uint64 transferCount;
    uint64 schedulerDecisionCount;
    uint64 schedulerOutcomeCount;
    CStringW databasePath;
    CStringW backupFolder;

    EmuleNextDatabaseMaintenanceSnapshot();
};

class CEmuleNextDatabaseMaintenance
{
public:
    static bool FileExists(const CStringW& path);
    static uint64 FileSize(const CStringW& path);
    static CStringW BackupFolderFor(const CStringW& databasePath);
    static bool EnsureBackupFolder(const CStringW& folder);

    static bool CheckDatabaseFile(const CStringW& path, bool full, CStringW& result);
    static int ReadSchemaVersion(const CStringW& path);
    static bool CreateBackup(const CStringW& databasePath, LPCTSTR reason,
        CStringW& backupPath, CStringW& result, size_t keep = 5);
    static bool ShouldCreateAutomaticBackup(const CStringW& databasePath, uint64 maximumAgeSeconds);
    static bool RestoreBackup(const CStringW& backupPath, const CStringW& databasePath,
        CStringW& archivedPath, CStringW& result);
    static bool LoadSnapshot(const CStringW& databasePath, EmuleNextDatabaseMaintenanceSnapshot& snapshot);
    static bool PruneOldTelemetry(const CStringW& databasePath, uint64 olderThan,
        uint64& removedRows, CStringW& result);
    static bool CheckpointWal(const CStringW& databasePath, CStringW& result);
    static bool RecordIntegrityResult(const CStringW& databasePath, const CStringW& result, uint64 checkedAt);
};
