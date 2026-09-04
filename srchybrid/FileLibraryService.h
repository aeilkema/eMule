//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "EmuleNextDatabase.h"
#include <vector>

enum EmuleNextLibraryState
{
    ENLS_PRESENT = 0,
    ENLS_MISSING,
    ENLS_RELINKED,
    ENLS_SIZE_MISMATCH,
    ENLS_HASH_MISMATCH,
    ENLS_UNKNOWN
};

struct EmuleNextLibraryItem
{
    EmuleNextFavoriteRecord favorite;
    EmuleNextLibraryState state;
    CString resolvedPath;
    uint64 lastChecked;

    EmuleNextLibraryItem();
};

class IEmuleNextLibraryHost
{
public:
    virtual ~IEmuleNextLibraryHost() {}

    // Hash verification can be expensive and is only requested for a candidate
    // whose size already matches. Implementations should use eMule's normal
    // hashing/AICH worker rather than hashing on the GUI/network thread.
    virtual bool VerifyEd2kHash(const CString& path,
        const EmuleNextHash16& expectedHash,
        uint64 expectedSize) = 0;

    // Recreate a normal eD2K download using the content identity. Known peer
    // history is only a source hint; it is never assumed to still be valid.
    virtual bool AddDownloadFromIdentity(const EmuleNextFavoriteRecord& favorite) = 0;
};

class CFileLibraryService
{
public:
    explicit CFileLibraryService(CEmuleNextDatabase& database);

    void SetHost(IEmuleNextLibraryHost* host);
    void SetSearchRoots(const std::vector<CString>& roots);
    const std::vector<CString>& GetSearchRoots() const;

    bool AddFavorite(const EmuleNextFavoriteRecord& favorite);
    void RemoveFavorite(const EmuleNextHash16& hash, uint64 size);
    void AddDownloadLater(const EmuleNextFileObservation& file);
    void MarkCompleted(const EmuleNextFileObservation& file, const CString& localPath);

    bool LoadFavorites(std::vector<EmuleNextLibraryItem>& items) const;
    EmuleNextLibraryState CheckFavorite(EmuleNextLibraryItem& item, bool searchForMovedFile);
    uint32 CheckAllFavorites(std::vector<EmuleNextLibraryItem>& items, bool searchForMovedFiles);

    bool RestoreMissing(EmuleNextLibraryItem& item);
    uint32 AutoRestoreMissing(std::vector<EmuleNextLibraryItem>& items, uint32 maxAddsPerPass = 3);

private:
    static bool FileExistsWithSize(const CString& path, uint64 expectedSize, uint64* actualSize = NULL);
    bool FindMovedFile(EmuleNextLibraryItem& item, CString& foundPath) const;
    bool FindMovedFileRecursive(const CString& root, const CString& preferredName,
        const EmuleNextHash16& hash, uint64 size, CString& foundPath, uint32 depth) const;

    CEmuleNextDatabase& m_database;
    IEmuleNextLibraryHost* m_host;
    std::vector<CString> m_searchRoots;
};
