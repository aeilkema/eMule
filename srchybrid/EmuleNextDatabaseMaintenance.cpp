//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "EmuleNextDatabaseMaintenance.h"
#include "EmuleNextWinSqliteCompat.h"

#include <algorithm>
#include <vector>

namespace
{
    CStringW DirectoryOf(const CStringW& path)
    {
        const int slash = path.ReverseFind(L'\\');
        return slash >= 0 ? path.Left(slash) : CStringW();
    }

    uint64 FileTimeToUnix(const FILETIME& fileTime)
    {
        ULARGE_INTEGER value;
        value.HighPart = fileTime.dwHighDateTime;
        value.LowPart = fileTime.dwLowDateTime;
        if (value.QuadPart < 116444736000000000ui64)
            return 0;
        return (value.QuadPart - 116444736000000000ui64) / 10000000ui64;
    }

    struct BackupItem
    {
        CStringW path;
        FILETIME time;
    };

    std::vector<BackupItem> ListBackups(const CStringW& folder)
    {
        std::vector<BackupItem> items;
        CStringW pattern = folder + L"\\emule-next-backup-*.sqlite3";
        WIN32_FIND_DATAW data = {};
        HANDLE find = ::FindFirstFileW(pattern.GetString(), &data);
        if (find == INVALID_HANDLE_VALUE)
            return items;
        do {
            if ((data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) == 0) {
                BackupItem item;
                item.path = folder + L"\\" + data.cFileName;
                item.time = data.ftLastWriteTime;
                items.push_back(item);
            }
        } while (::FindNextFileW(find, &data));
        ::FindClose(find);
        std::sort(items.begin(), items.end(), [](const BackupItem& a, const BackupItem& b) {
            ULARGE_INTEGER av, bv;
            av.HighPart = a.time.dwHighDateTime; av.LowPart = a.time.dwLowDateTime;
            bv.HighPart = b.time.dwHighDateTime; bv.LowPart = b.time.dwLowDateTime;
            return av.QuadPart > bv.QuadPart;
        });
        return items;
    }

    CStringW TimestampedPath(const CStringW& folder, LPCWSTR kind)
    {
        SYSTEMTIME st = {};
        ::GetLocalTime(&st);
        CStringW path;
        path.Format(L"%s\\emule-next-%s-%04u%02u%02u-%02u%02u%02u.sqlite3",
            folder.GetString(), kind, st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond);
        return path;
    }

    bool BackupWithSqlite(const CStringW& sourcePath, const CStringW& destinationPath, CStringW& result)
    {
        sqlite3* source = NULL;
        sqlite3* destination = NULL;
        bool ok = sqlite3_open16(sourcePath.GetString(), &source) == SQLITE_OK;
        if (ok)
            ok = sqlite3_open16(destinationPath.GetString(), &destination) == SQLITE_OK;
        if (ok) {
            sqlite3_busy_timeout(source, 5000);
            sqlite3_busy_timeout(destination, 5000);
            sqlite3_backup* backup = sqlite3_backup_init(destination, "main", source, "main");
            if (backup != NULL) {
                const int step = sqlite3_backup_step(backup, -1);
                const int finish = sqlite3_backup_finish(backup);
                ok = step == SQLITE_DONE && finish == SQLITE_OK;
            }
            else
                ok = false;
        }
        if (destination != NULL)
            sqlite3_close(destination);
        if (source != NULL)
            sqlite3_close(source);
        if (!ok)
            result = L"SQLite backup API failed.";
        return ok;
    }

    uint64 CountQuery(sqlite3* db, const char* sql)
    {
        sqlite3_stmt* stmt = NULL;
        uint64 value = 0;
        if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK && sqlite3_step(stmt) == SQLITE_ROW)
            value = static_cast<uint64>(sqlite3_column_int64(stmt, 0));
        if (stmt != NULL)
            sqlite3_finalize(stmt);
        return value;
    }

    CStringW MetaValue(sqlite3* db, LPCSTR key)
    {
        sqlite3_stmt* stmt = NULL;
        CStringW value;
        if (sqlite3_prepare_v2(db, "SELECT value FROM maintenance_meta WHERE key=?1", -1, &stmt, NULL) == SQLITE_OK) {
            sqlite3_bind_text(stmt, 1, key, -1, SQLITE_TRANSIENT);
            if (sqlite3_step(stmt) == SQLITE_ROW) {
                const wchar_t* raw = static_cast<const wchar_t*>(sqlite3_column_text16(stmt, 0));
                if (raw != NULL)
                    value = raw;
            }
        }
        if (stmt != NULL)
            sqlite3_finalize(stmt);
        return value;
    }

    void RotateBackups(const CStringW& folder, size_t keep)
    {
        const std::vector<BackupItem> items = ListBackups(folder);
        for (size_t i = keep; i < items.size(); ++i)
            ::DeleteFileW(items[i].path.GetString());
    }
}

EmuleNextDatabaseMaintenanceSnapshot::EmuleNextDatabaseMaintenanceSnapshot()
    : schemaVersion(0), databaseBytes(0), walBytes(0), backupCount(0), lastBackupAt(0),
      lastIntegrityAt(0), peerCount(0), fileCount(0), libraryCount(0), transferCount(0),
      schedulerDecisionCount(0), schedulerOutcomeCount(0)
{
}

bool CEmuleNextDatabaseMaintenance::FileExists(const CStringW& path)
{
    const DWORD attributes = ::GetFileAttributesW(path.GetString());
    return attributes != INVALID_FILE_ATTRIBUTES && (attributes & FILE_ATTRIBUTE_DIRECTORY) == 0;
}

uint64 CEmuleNextDatabaseMaintenance::FileSize(const CStringW& path)
{
    WIN32_FILE_ATTRIBUTE_DATA data = {};
    if (!::GetFileAttributesExW(path.GetString(), GetFileExInfoStandard, &data))
        return 0;
    ULARGE_INTEGER size;
    size.HighPart = data.nFileSizeHigh;
    size.LowPart = data.nFileSizeLow;
    return size.QuadPart;
}

CStringW CEmuleNextDatabaseMaintenance::BackupFolderFor(const CStringW& databasePath)
{
    CStringW folder = DirectoryOf(databasePath);
    if (!folder.IsEmpty() && folder[folder.GetLength() - 1] != L'\\')
        folder += L"\\";
    folder += L"emule-next-backups";
    return folder;
}

bool CEmuleNextDatabaseMaintenance::EnsureBackupFolder(const CStringW& folder)
{
    if (::CreateDirectoryW(folder.GetString(), NULL))
        return true;
    return ::GetLastError() == ERROR_ALREADY_EXISTS;
}

bool CEmuleNextDatabaseMaintenance::CheckDatabaseFile(const CStringW& path, bool full, CStringW& result)
{
    result.Empty();
    if (!FileExists(path)) {
        result = L"Database file does not exist.";
        return false;
    }
    sqlite3* db = NULL;
    if (sqlite3_open16(path.GetString(), &db) != SQLITE_OK) {
        if (db != NULL)
            sqlite3_close(db);
        result = L"Unable to open database.";
        return false;
    }
    sqlite3_busy_timeout(db, 5000);
    sqlite3_stmt* stmt = NULL;
    const char* sql = full ? "PRAGMA integrity_check" : "PRAGMA quick_check";
    bool ok = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK;
    if (ok && sqlite3_step(stmt) == SQLITE_ROW) {
        const wchar_t* value = static_cast<const wchar_t*>(sqlite3_column_text16(stmt, 0));
        result = value != NULL ? CStringW(value) : CStringW();
        ok = result.CompareNoCase(L"ok") == 0;
    }
    else
        ok = false;
    if (stmt != NULL)
        sqlite3_finalize(stmt);
    sqlite3_close(db);
    if (!ok && result.IsEmpty())
        result = L"Integrity check failed.";
    return ok;
}

int CEmuleNextDatabaseMaintenance::ReadSchemaVersion(const CStringW& path)
{
    if (!FileExists(path))
        return 0;
    sqlite3* db = NULL;
    if (sqlite3_open16(path.GetString(), &db) != SQLITE_OK) {
        if (db != NULL) sqlite3_close(db);
        return 0;
    }
    sqlite3_stmt* stmt = NULL;
    int version = 0;
    if (sqlite3_prepare_v2(db, "SELECT value FROM schema_meta WHERE key='schema_version'", -1, &stmt, NULL) == SQLITE_OK
        && sqlite3_step(stmt) == SQLITE_ROW) {
        const wchar_t* raw = static_cast<const wchar_t*>(sqlite3_column_text16(stmt, 0));
        if (raw != NULL)
            version = _wtoi(raw);
    }
    if (stmt != NULL) sqlite3_finalize(stmt);
    sqlite3_close(db);
    return version;
}

bool CEmuleNextDatabaseMaintenance::CreateBackup(const CStringW& databasePath, LPCTSTR reason,
    CStringW& backupPath, CStringW& result, size_t keep)
{
    backupPath.Empty();
    if (!FileExists(databasePath)) {
        result = L"No intelligence database exists yet.";
        return false;
    }
    const CStringW folder = BackupFolderFor(databasePath);
    if (!EnsureBackupFolder(folder)) {
        result = L"Unable to create backup folder.";
        return false;
    }
    CStringW kind = L"backup-";
    kind += reason != NULL && *reason != 0 ? CStringW(reason) : CStringW(L"manual");
    backupPath = TimestampedPath(folder, kind);
    if (!BackupWithSqlite(databasePath, backupPath, result)) {
        ::DeleteFileW(backupPath.GetString());
        backupPath.Empty();
        return false;
    }
    CStringW validation;
    if (!CheckDatabaseFile(backupPath, false, validation)) {
        result = L"Backup rejected by quick_check: " + validation;
        ::DeleteFileW(backupPath.GetString());
        backupPath.Empty();
        return false;
    }
    RotateBackups(folder, keep);
    result = L"Validated backup created.";
    return true;
}

bool CEmuleNextDatabaseMaintenance::ShouldCreateAutomaticBackup(const CStringW& databasePath, uint64 maximumAgeSeconds)
{
    const std::vector<BackupItem> items = ListBackups(BackupFolderFor(databasePath));
    if (items.empty())
        return true;
    const uint64 newest = FileTimeToUnix(items.front().time);
    const uint64 now = static_cast<uint64>(time(NULL));
    return newest == 0 || now <= newest || now - newest >= maximumAgeSeconds;
}

bool CEmuleNextDatabaseMaintenance::RestoreBackup(const CStringW& backupPath, const CStringW& databasePath,
    CStringW& archivedPath, CStringW& result)
{
    archivedPath.Empty();
    CStringW validation;
    if (!CheckDatabaseFile(backupPath, true, validation)) {
        result = L"Backup rejected by integrity_check: " + validation;
        return false;
    }
    const CStringW folder = BackupFolderFor(databasePath);
    if (!EnsureBackupFolder(folder)) {
        result = L"Backup folder is unavailable.";
        return false;
    }
    if (FileExists(databasePath)) {
        archivedPath = TimestampedPath(folder, L"archive-pre-restore");
        if (!::MoveFileExW(databasePath.GetString(), archivedPath.GetString(), MOVEFILE_WRITE_THROUGH)) {
            result = L"Current database could not be archived; restore aborted.";
            return false;
        }
    }
    ::DeleteFileW((databasePath + L"-wal").GetString());
    ::DeleteFileW((databasePath + L"-shm").GetString());

    if (!BackupWithSqlite(backupPath, databasePath, result) || !CheckDatabaseFile(databasePath, true, validation)) {
        ::DeleteFileW(databasePath.GetString());
        if (!archivedPath.IsEmpty())
            ::MoveFileExW(archivedPath.GetString(), databasePath.GetString(), MOVEFILE_WRITE_THROUGH);
        result = L"Restore failed; previous database was preserved. " + result + L" " + validation;
        return false;
    }
    result = L"Backup restored and validated.";
    return true;
}

bool CEmuleNextDatabaseMaintenance::LoadSnapshot(const CStringW& databasePath, EmuleNextDatabaseMaintenanceSnapshot& snapshot)
{
    snapshot = EmuleNextDatabaseMaintenanceSnapshot();
    snapshot.databasePath = databasePath;
    snapshot.backupFolder = BackupFolderFor(databasePath);
    snapshot.databaseBytes = FileSize(databasePath);
    snapshot.walBytes = FileSize(databasePath + L"-wal");
    const std::vector<BackupItem> backups = ListBackups(snapshot.backupFolder);
    snapshot.backupCount = static_cast<uint32>(backups.size());
    if (!backups.empty())
        snapshot.lastBackupAt = FileTimeToUnix(backups.front().time);

    if (!FileExists(databasePath))
        return false;
    sqlite3* db = NULL;
    if (sqlite3_open16(databasePath.GetString(), &db) != SQLITE_OK) {
        if (db != NULL) sqlite3_close(db);
        return false;
    }
    sqlite3_busy_timeout(db, 3000);
    sqlite3_stmt* stmt = NULL;
    if (sqlite3_prepare_v2(db, "SELECT value FROM schema_meta WHERE key='schema_version'", -1, &stmt, NULL) == SQLITE_OK
        && sqlite3_step(stmt) == SQLITE_ROW) {
        const wchar_t* raw = static_cast<const wchar_t*>(sqlite3_column_text16(stmt, 0));
        if (raw != NULL) snapshot.schemaVersion = _wtoi(raw);
    }
    if (stmt != NULL) sqlite3_finalize(stmt);
    snapshot.peerCount = CountQuery(db, "SELECT COUNT(*) FROM peers");
    snapshot.fileCount = CountQuery(db, "SELECT COUNT(*) FROM files");
    snapshot.libraryCount = CountQuery(db, "SELECT COUNT(*) FROM library_entries");
    snapshot.transferCount = CountQuery(db, "SELECT COUNT(*) FROM transfer_sessions");
    snapshot.schedulerDecisionCount = CountQuery(db, "SELECT COUNT(*) FROM scheduler_decisions");
    snapshot.schedulerOutcomeCount = CountQuery(db, "SELECT COUNT(*) FROM scheduler_outcomes");
    snapshot.lastIntegrityResult = MetaValue(db, "last_integrity_result");
    snapshot.lastIntegrityAt = _wtoi64(MetaValue(db, "last_integrity_at"));
    sqlite3_close(db);
    return true;
}

bool CEmuleNextDatabaseMaintenance::PruneOldTelemetry(const CStringW& databasePath, uint64 olderThan,
    uint64& removedRows, CStringW& result)
{
    removedRows = 0;
    sqlite3* db = NULL;
    if (sqlite3_open16(databasePath.GetString(), &db) != SQLITE_OK) {
        if (db != NULL) sqlite3_close(db);
        result = L"Unable to open database for pruning.";
        return false;
    }
    sqlite3_busy_timeout(db, 5000);
    bool ok = sqlite3_exec(db, "BEGIN IMMEDIATE", NULL, NULL, NULL) == SQLITE_OK;
    sqlite3_stmt* stmt = NULL;
    const char* statements[] = {
        "DELETE FROM scheduler_decisions WHERE ts<?1",
        "DELETE FROM scheduler_outcomes WHERE ts<?1",
        "DELETE FROM transfer_sessions WHERE finished_at IS NOT NULL AND finished_at<?1 AND successful=0"
    };
    for (int i = 0; ok && i < _countof(statements); ++i) {
        if (sqlite3_prepare_v2(db, statements[i], -1, &stmt, NULL) != SQLITE_OK) {
            ok = false;
            break;
        }
        sqlite3_bind_int64(stmt, 1, static_cast<sqlite3_int64>(olderThan));
        ok = sqlite3_step(stmt) == SQLITE_DONE;
        if (ok)
            removedRows += static_cast<uint64>(sqlite3_changes(db));
        sqlite3_finalize(stmt);
        stmt = NULL;
    }
    if (stmt != NULL) sqlite3_finalize(stmt);
    if (ok)
        ok = sqlite3_exec(db, "COMMIT", NULL, NULL, NULL) == SQLITE_OK;
    if (!ok)
        sqlite3_exec(db, "ROLLBACK", NULL, NULL, NULL);
    sqlite3_close(db);
    if (ok)
        result.Format(L"Pruned %I64u old telemetry rows. Favorites, aliases and Library history were not touched.", removedRows);
    else
        result = L"Telemetry pruning failed.";
    return ok;
}

bool CEmuleNextDatabaseMaintenance::CheckpointWal(const CStringW& databasePath, CStringW& result)
{
    sqlite3* db = NULL;
    if (sqlite3_open16(databasePath.GetString(), &db) != SQLITE_OK) {
        if (db != NULL) sqlite3_close(db);
        result = L"Unable to open database for WAL checkpoint.";
        return false;
    }
    sqlite3_busy_timeout(db, 5000);
    const int rc = sqlite3_wal_checkpoint_v2(db, NULL, SQLITE_CHECKPOINT_TRUNCATE, NULL, NULL);
    sqlite3_close(db);
    result = rc == SQLITE_OK ? L"WAL checkpoint completed." : L"WAL checkpoint failed.";
    return rc == SQLITE_OK;
}

bool CEmuleNextDatabaseMaintenance::RecordIntegrityResult(const CStringW& databasePath, const CStringW& result, uint64 checkedAt)
{
    sqlite3* db = NULL;
    if (sqlite3_open16(databasePath.GetString(), &db) != SQLITE_OK) {
        if (db != NULL) sqlite3_close(db);
        return false;
    }
    sqlite3_busy_timeout(db, 5000);
    sqlite3_stmt* stmt = NULL;
    const char* sql = "INSERT OR REPLACE INTO maintenance_meta(key,value) VALUES(?1,?2)";
    bool ok = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK;
    if (ok) {
        sqlite3_bind_text(stmt, 1, "last_integrity_result", -1, SQLITE_TRANSIENT);
        sqlite3_bind_text16(stmt, 2, result.GetString(), -1, SQLITE_TRANSIENT);
        ok = sqlite3_step(stmt) == SQLITE_DONE;
    }
    if (stmt != NULL) sqlite3_finalize(stmt);
    stmt = NULL;
    CStringW timestamp; timestamp.Format(L"%I64u", checkedAt);
    if (ok && sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK) {
        sqlite3_bind_text(stmt, 1, "last_integrity_at", -1, SQLITE_TRANSIENT);
        sqlite3_bind_text16(stmt, 2, timestamp.GetString(), -1, SQLITE_TRANSIENT);
        ok = sqlite3_step(stmt) == SQLITE_DONE;
    }
    else
        ok = false;
    if (stmt != NULL) sqlite3_finalize(stmt);
    sqlite3_close(db);
    return ok;
}
