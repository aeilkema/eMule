//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "FileLibraryService.h"

#include <winsqlite3.h>
#include <algorithm>

namespace
{
    uint64 LibraryNow()
    {
        return static_cast<uint64>(time(NULL));
    }

    CStringW SqlText(sqlite3_stmt* stmt, int column)
    {
        const wchar_t* value = static_cast<const wchar_t*>(sqlite3_column_text16(stmt, column));
        return value != NULL ? CStringW(value) : CStringW();
    }
}

EmuleNextLibraryItem::EmuleNextLibraryItem()
    : state(ENLS_UNKNOWN)
    , lastChecked(0)
{
}

CFileLibraryService::CFileLibraryService(CEmuleNextDatabase& database)
    : m_database(database)
    , m_host(NULL)
{
}

void CFileLibraryService::SetHost(IEmuleNextLibraryHost* host)
{
    m_host = host;
}

void CFileLibraryService::SetSearchRoots(const std::vector<CString>& roots)
{
    m_searchRoots = roots;
}

const std::vector<CString>& CFileLibraryService::GetSearchRoots() const
{
    return m_searchRoots;
}

bool CFileLibraryService::AddFavorite(const EmuleNextFavoriteRecord& favorite)
{
    if (!favorite.fileHash.valid || favorite.fileSize == 0)
        return false;
    m_database.SaveFavorite(favorite);
    return true;
}

void CFileLibraryService::RemoveFavorite(const EmuleNextHash16& hash, uint64 size)
{
    m_database.RemoveFavorite(hash, size);
}

void CFileLibraryService::AddDownloadLater(const EmuleNextFileObservation& file)
{
    if (file.ed2kHash.valid && file.fileSize != 0)
        m_database.SaveDownloadLater(file);
}

void CFileLibraryService::MarkCompleted(const EmuleNextFileObservation& file, const CString& localPath)
{
    if (file.ed2kHash.valid && file.fileSize != 0)
        m_database.MarkLibraryCompleted(file, CStringW(localPath));
}

bool CFileLibraryService::LoadFavorites(std::vector<EmuleNextLibraryItem>& items) const
{
    items.clear();
    const CStringW path = m_database.GetDatabasePath();
    if (path.IsEmpty())
        return false;

    sqlite3* db = NULL;
    if (sqlite3_open16(path.GetString(), &db) != SQLITE_OK) {
        if (db != NULL)
            sqlite3_close(db);
        return false;
    }
    sqlite3_busy_timeout(db, 3000);

    static const char sql[] =
        "SELECT f.ed2k_hash,f.size,COALESCE(f.canonical_name,''),COALESCE(f.aich_hash,''),"
        "COALESCE(fav.local_path,''),COALESCE(fav.tags,''),fav.auto_restore "
        "FROM favorites fav JOIN files f ON f.id=fav.file_id "
        "ORDER BY COALESCE(f.canonical_name,'') COLLATE NOCASE";

    sqlite3_stmt* stmt = NULL;
    const bool prepared = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK;
    if (prepared) {
        while (sqlite3_step(stmt) == SQLITE_ROW) {
            EmuleNextLibraryItem item;
            item.favorite.fileHash = EmuleNextHash16(
                static_cast<const unsigned char*>(sqlite3_column_blob(stmt, 0)));
            item.favorite.fileSize = static_cast<uint64>(sqlite3_column_int64(stmt, 1));
            item.favorite.fileName = SqlText(stmt, 2);
            item.favorite.aichHash = SqlText(stmt, 3);
            item.favorite.localPath = SqlText(stmt, 4);
            item.favorite.tags = SqlText(stmt, 5);
            item.favorite.autoRestore = sqlite3_column_int(stmt, 6) != 0;
            item.resolvedPath = CString(item.favorite.localPath);
            item.state = ENLS_UNKNOWN;
            items.push_back(item);
        }
    }

    if (stmt != NULL)
        sqlite3_finalize(stmt);
    sqlite3_close(db);
    return prepared;
}

bool CFileLibraryService::FileExistsWithSize(const CString& path, uint64 expectedSize, uint64* actualSize)
{
    if (path.IsEmpty())
        return false;

    WIN32_FILE_ATTRIBUTE_DATA data = {};
    if (!::GetFileAttributesEx(path, GetFileExInfoStandard, &data)
        || (data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0) {
        return false;
    }

    ULARGE_INTEGER size;
    size.HighPart = data.nFileSizeHigh;
    size.LowPart = data.nFileSizeLow;
    if (actualSize != NULL)
        *actualSize = size.QuadPart;
    return size.QuadPart == expectedSize;
}

bool CFileLibraryService::FindMovedFileRecursive(const CString& root,
    const CString& preferredName,
    const EmuleNextHash16& hash,
    uint64 size,
    CString& foundPath,
    uint32 depth) const
{
    if (m_host == NULL || root.IsEmpty() || depth > 12)
        return false;

    CString searchRoot(root);
    if (searchRoot.Right(1) != _T("\\"))
        searchRoot += _T("\\");

    WIN32_FIND_DATA findData = {};
    HANDLE find = ::FindFirstFile(searchRoot + _T("*"), &findData);
    if (find == INVALID_HANDLE_VALUE)
        return false;

    bool found = false;
    do {
        const CString name(findData.cFileName);
        if (name == _T(".") || name == _T(".."))
            continue;

        const CString fullPath = searchRoot + name;
        if ((findData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0) {
            if ((findData.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) == 0
                && FindMovedFileRecursive(fullPath, preferredName, hash, size, foundPath, depth + 1)) {
                found = true;
                break;
            }
            continue;
        }

        ULARGE_INTEGER actualSize;
        actualSize.HighPart = findData.nFileSizeHigh;
        actualSize.LowPart = findData.nFileSizeLow;
        if (actualSize.QuadPart != size)
            continue;

        // Prefer the historical name first, but never trust it as identity.
        if (!preferredName.IsEmpty() && name.CompareNoCase(preferredName) != 0)
            continue;

        if (m_host->VerifyEd2kHash(fullPath, hash, size)) {
            foundPath = fullPath;
            found = true;
            break;
        }
    } while (::FindNextFile(find, &findData));

    ::FindClose(find);
    if (found)
        return true;

    // A renamed file may still have the exact content. Run a second pass for
    // size-matching candidates only; the expensive hash is still the final
    // identity check.
    find = ::FindFirstFile(searchRoot + _T("*"), &findData);
    if (find == INVALID_HANDLE_VALUE)
        return false;

    do {
        const CString name(findData.cFileName);
        if (name == _T(".") || name == _T("..")
            || (findData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0)
            continue;

        ULARGE_INTEGER actualSize;
        actualSize.HighPart = findData.nFileSizeHigh;
        actualSize.LowPart = findData.nFileSizeLow;
        if (actualSize.QuadPart != size)
            continue;

        const CString fullPath = searchRoot + name;
        if (m_host->VerifyEd2kHash(fullPath, hash, size)) {
            foundPath = fullPath;
            found = true;
            break;
        }
    } while (::FindNextFile(find, &findData));

    ::FindClose(find);
    return found;
}

bool CFileLibraryService::FindMovedFile(EmuleNextLibraryItem& item, CString& foundPath) const
{
    if (m_host == NULL)
        return false;

    for (size_t i = 0; i < m_searchRoots.size(); ++i) {
        if (FindMovedFileRecursive(m_searchRoots[i], CString(item.favorite.fileName),
            item.favorite.fileHash, item.favorite.fileSize, foundPath, 0)) {
            return true;
        }
    }
    return false;
}

EmuleNextLibraryState CFileLibraryService::CheckFavorite(EmuleNextLibraryItem& item,
    bool searchForMovedFile)
{
    item.lastChecked = LibraryNow();
    uint64 actualSize = 0;
    const CString currentPath(item.favorite.localPath);

    if (!currentPath.IsEmpty()) {
        WIN32_FILE_ATTRIBUTE_DATA data = {};
        if (::GetFileAttributesEx(currentPath, GetFileExInfoStandard, &data)
            && (data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) == 0) {
            ULARGE_INTEGER size;
            size.HighPart = data.nFileSizeHigh;
            size.LowPart = data.nFileSizeLow;
            actualSize = size.QuadPart;
            if (actualSize == item.favorite.fileSize) {
                item.state = ENLS_PRESENT;
                item.resolvedPath = currentPath;
                return item.state;
            }
            item.state = ENLS_SIZE_MISMATCH;
        }
        else
            item.state = ENLS_MISSING;
    }
    else
        item.state = ENLS_MISSING;

    if (!searchForMovedFile)
        return item.state;

    CString movedPath;
    if (FindMovedFile(item, movedPath)) {
        item.resolvedPath = movedPath;
        item.favorite.localPath = CStringW(movedPath);
        item.state = ENLS_RELINKED;
        m_database.SaveFavorite(item.favorite);
        return item.state;
    }

    item.resolvedPath.Empty();
    return item.state;
}

uint32 CFileLibraryService::CheckAllFavorites(std::vector<EmuleNextLibraryItem>& items,
    bool searchForMovedFiles)
{
    uint32 missing = 0;
    for (size_t i = 0; i < items.size(); ++i) {
        const EmuleNextLibraryState state = CheckFavorite(items[i], searchForMovedFiles);
        if (state == ENLS_MISSING || state == ENLS_SIZE_MISMATCH || state == ENLS_HASH_MISMATCH)
            ++missing;
    }
    return missing;
}

bool CFileLibraryService::RestoreMissing(EmuleNextLibraryItem& item)
{
    if (m_host == NULL)
        return false;

    const EmuleNextLibraryState state = CheckFavorite(item, true);
    if (state == ENLS_PRESENT || state == ENLS_RELINKED)
        return true;

    return m_host->AddDownloadFromIdentity(item.favorite);
}

uint32 CFileLibraryService::AutoRestoreMissing(std::vector<EmuleNextLibraryItem>& items,
    uint32 maxAddsPerPass)
{
    if (m_host == NULL || maxAddsPerPass == 0)
        return 0;

    uint32 added = 0;
    for (size_t i = 0; i < items.size() && added < maxAddsPerPass; ++i) {
        if (!items[i].favorite.autoRestore)
            continue;

        const EmuleNextLibraryState state = CheckFavorite(items[i], true);
        if (state == ENLS_PRESENT || state == ENLS_RELINKED)
            continue;

        if (m_host->AddDownloadFromIdentity(items[i].favorite))
            ++added;
    }
    return added;
}
